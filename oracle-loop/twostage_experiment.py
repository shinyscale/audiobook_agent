#!/usr/bin/env python3
"""
Two-Stage Model Experiment

Tests a two-model pipeline approach: fast model (35b) for structure/pronunciation,
quality model (122b) for summaries/characters. Explicit model lifecycle management
prevents VRAM conflicts.

Usage:
    python oracle-loop/twostage_experiment.py "Test_Texts/The_Monkey's_Paw.txt"
    python oracle-loop/twostage_experiment.py "Test_Texts/The_Monkey's_Paw.txt" -o /tmp/result.json
    python oracle-loop/twostage_experiment.py "Test_Texts/The_Monkey's_Paw.txt" --fast-model qwen3.5:35b-a3b --quality-model qwen3.5:122b-a10b
    python oracle-loop/twostage_experiment.py "Test_Texts/The_Monkey's_Paw.txt" --skip-profiling --skip-pronunciation

Pipeline:
    1. Load fast model → Chapter detection
    2. Swap to quality model → Summaries, characters, profiles
    3. Swap back to fast model → Pronunciation guide
"""

import argparse
import json
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ollama_manager import load_model, unload_all

from src.llm.client import LLMClient, LLMConfig
from src.pipeline.chapter_detection.pipeline import ChapterDetectionPipeline
from src.pipeline.chapter_summary.models import ChapterSummary, ChapterSummaryMap
from src.pipeline.chapter_summary.summarizer import ChapterSummarizer
from src.pipeline.character_extraction.models import Character, CharacterMap, CharacterType
from src.pipeline.character_extraction_v2.main_cast import MainCastExtractor, MainCastProfile
from src.pipeline.character_profiling.pipeline import CharacterProfilingPipeline
from src.pipeline.pronunciation_guide.pipeline import PronunciationGuidePipeline


# =============================================================================
# TEXT LOADING (from character_experiment.py pattern)
# =============================================================================

def load_text(text_path: Path) -> str:
    """Load text from file, handling PDFs and stripping Gutenberg boilerplate."""
    from src.ingestion.refine import _strip_gutenberg_boilerplate

    if text_path.suffix.lower() == ".pdf":
        from src.ingestion.pdf import PDFIngester
        doc = PDFIngester().extract(text_path)
        text = doc.text
    else:
        text = text_path.read_text()

    cleaned, warnings = _strip_gutenberg_boilerplate(text)
    for w in warnings:
        print(f"  [boilerplate] {w}")
    return cleaned


# =============================================================================
# HELPER: Build ChapterSummaryMap from individual summaries
# =============================================================================

def build_summary_map(summaries: list[ChapterSummary], source_file: str) -> ChapterSummaryMap:
    """Build a ChapterSummaryMap from individual ChapterSummary objects."""
    total_words = sum(s.word_count for s in summaries)
    total_duration = sum(s.estimated_duration_minutes for s in summaries)

    tone_counts: dict[str, int] = Counter()
    for s in summaries:
        tone_counts[s.primary_tone] += 1

    char_appearances: dict[str, list[int]] = {}
    for s in summaries:
        for char_name in s.active_characters:
            if char_name not in char_appearances:
                char_appearances[char_name] = []
            char_appearances[char_name].append(s.chapter_index)

    return ChapterSummaryMap(
        summaries=summaries,
        total_chapters=len(summaries),
        total_word_count=total_words,
        total_duration_minutes=total_duration,
        overall_tones=dict(tone_counts),
        character_appearances=char_appearances,
        pipeline_metadata={
            "source_file": source_file,
            "generated_at": datetime.now().isoformat(),
        },
    )


# =============================================================================
# HELPER: Build V1 CharacterMap from MainCastProfile for pronunciation pipeline
# =============================================================================

def build_character_map(profiles: list[MainCastProfile], total_chapters: int) -> CharacterMap:
    """Build a V1 CharacterMap from MainCastProfile results."""
    characters = []
    for i, profile in enumerate(profiles):
        char = Character(
            id=f"twostage_{i}",
            canonical_name=profile.canonical_name,
            aliases=profile.aliases,
            mentions=[],
            first_appearance_chapter=1,
            mention_count=0,
            chapters_present=list(range(1, total_chapters + 1)),
            confidence=0.9,
            supporting_strategies=["twostage_experiment"],
            description=profile.description,
            character_type=CharacterType.STORY,
            role=profile.role,
        )
        characters.append(char)

    return CharacterMap(
        characters=characters,
        low_confidence_characters=[],
        total_mentions=0,
        total_chapters=total_chapters,
        pipeline_metadata={"source": "twostage_experiment"},
    )


# =============================================================================
# MAIN PIPELINE
# =============================================================================

def run_twostage(
    text_path: Path,
    output_path: Path,
    fast_model: str,
    quality_model: str,
    skip_profiling: bool = False,
    skip_pronunciation: bool = False,
) -> dict:
    """Run the two-stage experiment pipeline."""
    timing = {}
    results = {
        "experiment": "twostage",
        "timestamp": datetime.now().isoformat(),
        "input_file": str(text_path),
        "fast_model": fast_model,
        "quality_model": quality_model,
    }

    text_name = text_path.stem

    # =========================================================================
    # Stage 0: Load and refine text
    # =========================================================================
    print("\n" + "=" * 70)
    print("STAGE 0: TEXT INGESTION")
    print("=" * 70)

    t0 = time.time()
    text = load_text(text_path)
    timing["ingestion"] = time.time() - t0

    print(f"  Text: {text_name}")
    print(f"  Size: {len(text):,} characters ({len(text.split()):,} words)")
    print(f"  Time: {timing['ingestion']:.1f}s")

    # =========================================================================
    # Stage 1: Load fast model + chapter detection
    # =========================================================================
    print("\n" + "=" * 70)
    print(f"STAGE 1: CHAPTER DETECTION ({fast_model})")
    print("=" * 70)

    t0 = time.time()
    success, load_time, msg = load_model(fast_model)
    timing["fast_model_load_1"] = load_time
    if not success:
        print(f"  FATAL: Failed to load fast model: {msg}")
        results["error"] = f"Fast model load failed: {msg}"
        return results

    print(f"  Model loaded in {load_time:.1f}s")

    t1 = time.time()
    fast_config_stage1 = LLMConfig.ollama(model=fast_model)
    fast_config_stage1.think = False  # Disable thinking mode for qwen3.5 models
    fast_client_stage1 = LLMClient(fast_config_stage1)
    chapter_pipeline = ChapterDetectionPipeline(llm_client=fast_client_stage1)
    chapter_map = chapter_pipeline.run(text, source_file=text_name)
    timing["chapter_detection"] = time.time() - t1

    if not chapter_map or not chapter_map.chapters:
        print(f"  FATAL: No chapters detected")
        results["error"] = "No chapters detected by fast model"
        return results

    print(f"  Chapters found: {len(chapter_map.chapters)}")
    for ch in chapter_map.chapters:
        title = ch.title or f"Chapter {ch.index}"
        print(f"    [{ch.index}] {title} ({ch.word_count:,} words)")
    print(f"  Detection time: {timing['chapter_detection']:.1f}s")

    # =========================================================================
    # Stage 2: Swap to quality model
    # =========================================================================
    print("\n" + "=" * 70)
    print(f"STAGE 2: MODEL SWAP -> {quality_model}")
    print("=" * 70)

    t0 = time.time()
    unload_all()
    # Quality model is large (81GB), give it up to 10 minutes to load
    success, load_time, msg = load_model(quality_model, load_timeout=600)
    timing["quality_model_load"] = time.time() - t0
    if not success:
        print(f"  FATAL: Failed to load quality model: {msg}")
        results["error"] = f"Quality model load failed: {msg}"
        return results
    print(f"  Model swapped in {timing['quality_model_load']:.1f}s (load: {load_time:.1f}s)")

    # =========================================================================
    # Stage 3: Chapter Summarization (quality model)
    # =========================================================================
    print("\n" + "=" * 70)
    print(f"STAGE 3: CHAPTER SUMMARIZATION ({quality_model})")
    print("=" * 70)

    # Two separate configs for the quality model:
    # - No-think for summarization (think=True fills the context window and produces empty content)
    # - Think=True for character extraction (reasoning helps identify symbolic objects like the Ebony Clock)
    quality_config_no_think = LLMConfig.ollama(model=quality_model)
    quality_config_no_think.think = False
    quality_client_no_think = LLMClient(quality_config_no_think)

    quality_config_think = LLMConfig.ollama(model=quality_model)
    quality_config_think.think = False  # think=False for character extraction (think=True too slow + JSON mode broken)
    quality_client = LLMClient(quality_config_think)

    summarizer = ChapterSummarizer(
        llm_client=quality_client_no_think,
        summary_length="detailed",
    )

    t0 = time.time()
    chapter_summaries = []   # ChapterSummary objects
    summary_strings = []     # Plain text for MainCastExtractor

    for i, chapter in enumerate(chapter_map.chapters):
        start = chapter.start_position
        end = chapter.end_position if chapter.end_position else len(text)
        chapter_text = text[start:end]
        chapter_title = chapter.title or f"Chapter {chapter.index}"

        print(f"  Summarizing [{chapter.index}] {chapter_title[:40]}... ", end="", flush=True)
        t_ch = time.time()

        summary = summarizer.summarize_chapter(
            chapter_text=chapter_text,
            chapter_index=chapter.index,
            chapter_title=chapter_title,
        )
        chapter_summaries.append(summary)

        # Build summary text with character list (MainCastExtractor format)
        chars_list = summary.active_characters + summary.mentioned_characters
        chars_str = f"\n[Characters: {', '.join(chars_list)}]" if chars_list else ""
        # Append key_events so Pass 1 sees explicit entity names (e.g. "a giant ebony clock")
        # that the summarizer classified as events rather than active characters.
        key_events_str = ""
        if summary.key_events:
            key_events_str = "\n[Key events: " + "; ".join(summary.key_events) + "]"
        summary_strings.append(f"{summary.summary}{key_events_str}{chars_str}")

        print(f"{time.time() - t_ch:.1f}s")

    timing["summarization"] = time.time() - t0
    print(f"  Total summarization time: {timing['summarization']:.1f}s")

    # Build ChapterSummaryMap for profiling pipeline
    summary_map = build_summary_map(chapter_summaries, text_name)

    # =========================================================================
    # Stage 4: Main Cast Extraction (quality model)
    # =========================================================================
    print("\n" + "=" * 70)
    print(f"STAGE 4: CHARACTER EXTRACTION ({quality_model})")
    print("=" * 70)

    t0 = time.time()
    extractor = MainCastExtractor(llm_client=quality_client)
    main_cast = extractor.extract(
        chapter_summaries=summary_strings,
        use_two_pass=True,
    )
    timing["character_extraction"] = time.time() - t0

    print(f"  Characters found: {len(main_cast)}")
    for profile in main_cast:
        aliases_str = f" (aka {', '.join(profile.aliases[:3])})" if profile.aliases else ""
        print(f"    {profile.canonical_name}{aliases_str} [{profile.role}]")
    print(f"  Extraction time: {timing['character_extraction']:.1f}s")

    # =========================================================================
    # Stage 5: Character Profiling (quality model, optional)
    # =========================================================================
    profile_map = None
    if not skip_profiling:
        print("\n" + "=" * 70)
        print(f"STAGE 5: CHARACTER PROFILING ({quality_model})")
        print("=" * 70)

        t0 = time.time()
        profiling_pipeline = CharacterProfilingPipeline(
            llm_client=quality_client_no_think,  # no-think for profiling (long prompts exhaust context)
            generate_rich_profiles=True,
        )

        try:
            profile_map = profiling_pipeline.run(
                full_text=text,
                chapter_map=chapter_map,
                summary_map=summary_map,
                source_file=text_name,
            )
            timing["character_profiling"] = time.time() - t0

            print(f"  Profiles generated: {len(profile_map.profiles)}")
            for profile in profile_map.profiles:
                print(f"    {profile.canonical_name} [{profile.role}]")
            print(f"  Profiling time: {timing['character_profiling']:.1f}s")
        except Exception as e:
            timing["character_profiling"] = time.time() - t0
            print(f"  ERROR during profiling: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("\n  [Skipping character profiling]")

    # =========================================================================
    # Stage 6: Swap back to fast model for pronunciation
    # =========================================================================
    pronunciation_map = None
    if not skip_pronunciation:
        print("\n" + "=" * 70)
        print(f"STAGE 6: MODEL SWAP -> {fast_model}")
        print("=" * 70)

        t0 = time.time()
        unload_all()
        success, load_time, msg = load_model(fast_model)
        timing["fast_model_load_2"] = time.time() - t0

        if not success:
            print(f"  WARNING: Failed to reload fast model: {msg}")
            print(f"  Skipping pronunciation stage")
        else:
            print(f"  Model swapped in {timing['fast_model_load_2']:.1f}s")

            # =================================================================
            # Stage 7: Pronunciation Guide (fast model)
            # =================================================================
            print("\n" + "=" * 70)
            print(f"STAGE 7: PRONUNCIATION GUIDE ({fast_model})")
            print("=" * 70)

            fast_config = LLMConfig.ollama(model=fast_model)
            fast_config.think = False  # Disable thinking mode for qwen3.5 models
            fast_client = LLMClient(fast_config)

            # Build V1 CharacterMap from MainCastProfile for pronunciation pipeline
            character_map = build_character_map(main_cast, len(chapter_map.chapters))

            t0 = time.time()
            try:
                pronunciation_pipeline = PronunciationGuidePipeline(
                    llm_client=fast_client,
                )

                pronunciation_map, _ = pronunciation_pipeline.run(
                    full_text=text,
                    chapter_map=chapter_map,
                    character_map=character_map,
                    source_file=text_name,
                )
                timing["pronunciation"] = time.time() - t0

                print(f"  Pronunciation entries: {len(pronunciation_map.entries)}")
                print(f"  Low confidence: {len(pronunciation_map.low_confidence_entries)}")
                print(f"  Pronunciation time: {timing['pronunciation']:.1f}s")
            except Exception as e:
                timing["pronunciation"] = time.time() - t0
                print(f"  ERROR during pronunciation: {e}")
                import traceback
                traceback.print_exc()
    else:
        print("\n  [Skipping pronunciation guide]")

    # =========================================================================
    # Stage 8: Assemble and export
    # =========================================================================
    print("\n" + "=" * 70)
    print("STAGE 8: EXPORT")
    print("=" * 70)

    # Unload models
    unload_all()

    # Calculate total time
    total_time = sum(timing.values())
    timing["total"] = total_time

    # Build full output
    output = {
        "metadata": {
            "experiment": "twostage",
            "timestamp": results["timestamp"],
            "input_file": str(text_path),
            "text_name": text_name,
            "text_size": len(text),
            "word_count": len(text.split()),
            "fast_model": fast_model,
            "quality_model": quality_model,
            "skip_profiling": skip_profiling,
            "skip_pronunciation": skip_pronunciation,
        },
        "timing": {k: round(v, 2) for k, v in timing.items()},
        "chapters": {
            "count": len(chapter_map.chapters),
            "details": [
                {
                    "index": ch.index,
                    "title": ch.title,
                    "start_position": ch.start_position,
                    "end_position": ch.end_position,
                    "word_count": ch.word_count,
                }
                for ch in chapter_map.chapters
            ],
        },
        "summaries": [s.to_dict() for s in chapter_summaries],
        "characters": {
            "count": len(main_cast),
            "main_cast": [
                {
                    "canonical_name": p.canonical_name,
                    "aliases": p.aliases,
                    "role": p.role,
                    "description": p.description,
                    "is_unnamed": p.is_unnamed,
                    "is_symbolic": p.is_symbolic,
                }
                for p in main_cast
            ],
        },
    }

    if profile_map:
        output["character_profiles"] = profile_map.to_dict()
    if pronunciation_map:
        output["pronunciation"] = pronunciation_map.to_dict()

    # Save
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n  Output saved to: {output_path}")
    print(f"  Total time: {total_time:.1f}s ({total_time / 60:.1f} minutes)")

    # Print timing breakdown
    print("\n" + "-" * 40)
    print("TIMING BREAKDOWN")
    print("-" * 40)
    for stage, t in sorted(timing.items(), key=lambda x: -x[1]):
        if stage == "total":
            continue
        pct = (t / total_time) * 100 if total_time > 0 else 0
        print(f"  {stage:<25} {t:>7.1f}s  ({pct:>4.1f}%)")
    print(f"  {'TOTAL':<25} {total_time:>7.1f}s")

    return results


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Two-stage model experiment for audiobook analysis pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "Test_Texts/The_Monkey's_Paw.txt"
  %(prog)s "Test_Texts/The_Monkey's_Paw.txt" -o /tmp/result.json
  %(prog)s "Test_Texts/The_Monkey's_Paw.txt" --fast-model qwen3.5:35b-a3b --quality-model qwen3.5:122b-a10b
  %(prog)s "Test_Texts/The_Monkey's_Paw.txt" --skip-profiling --skip-pronunciation
        """,
    )
    parser.add_argument("input", type=Path, help="Path to text file")
    parser.add_argument("-o", "--output", type=Path, default=None, help="Output JSON path")
    parser.add_argument(
        "--fast-model", default="qwen3.5:35b-a3b",
        help="Model for structure + pronunciation (default: qwen3.5:35b-a3b)",
    )
    parser.add_argument(
        "--quality-model", default="qwen3.5:122b-a10b",
        help="Model for summaries + characters (default: qwen3.5:122b-a10b)",
    )
    parser.add_argument(
        "--skip-profiling", action="store_true",
        help="Skip rich character profiling (faster iteration)",
    )
    parser.add_argument(
        "--skip-pronunciation", action="store_true",
        help="Skip pronunciation guide (faster iteration)",
    )
    args = parser.parse_args()

    # Validate input
    if not args.input.exists():
        print(f"ERROR: Input file not found: {args.input}")
        sys.exit(1)

    # Default output path
    if args.output is None:
        text_name = args.input.stem.replace(" ", "_")
        args.output = Path(f"/tmp/twostage_{text_name}.json")

    print("=" * 70)
    print("TWO-STAGE MODEL EXPERIMENT")
    print("=" * 70)
    print(f"  Input:               {args.input}")
    print(f"  Output:              {args.output}")
    print(f"  Fast model:          {args.fast_model}")
    print(f"  Quality model:       {args.quality_model}")
    print(f"  Skip profiling:      {args.skip_profiling}")
    print(f"  Skip pronunciation:  {args.skip_pronunciation}")
    print("=" * 70)

    results = run_twostage(
        text_path=args.input,
        output_path=args.output,
        fast_model=args.fast_model,
        quality_model=args.quality_model,
        skip_profiling=args.skip_profiling,
        skip_pronunciation=args.skip_pronunciation,
    )

    if "error" in results:
        print(f"\nEXPERIMENT FAILED: {results['error']}")
        sys.exit(1)
    else:
        print("\nEXPERIMENT COMPLETE")


if __name__ == "__main__":
    main()
