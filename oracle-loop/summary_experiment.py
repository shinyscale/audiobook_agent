#!/usr/bin/env python3
"""
Summary Generation Experiment (End-to-End)

Tests which summary model produces the best summaries for downstream character
extraction. Uses a fixed extraction model (qwen2.5:32b) so that differences
in results are driven by summary quality, not extraction quality.

Two-phase design:
  Phase 1: Load each summary model, generate summaries for all texts
  Phase 2: Load extraction model once, run character extraction on every
           model's summaries, score extraction results against ground truth

Usage:
    python oracle-loop/summary_experiment.py           # Run all models on all texts
    python oracle-loop/summary_experiment.py --quick   # Quick test: 2 models, 2 texts
    python oracle-loop/summary_experiment.py berenice  # Run all models on one text
    python oracle-loop/summary_experiment.py --resume  # Resume from crash, skip completed

Results saved to: oracle-loop/state/summary_results.json
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.llm.client import LLMClient, LLMConfig
from src.pipeline.chapter_detection.pipeline import ChapterDetectionPipeline
from src.pipeline.chapter_summary.summarizer import ChapterSummarizer
from src.pipeline.chapter_summary.models import ChapterSummary
from src.pipeline.character_extraction_v2.main_cast import MainCastExtractor, MainCastProfile


# =============================================================================
# GROUND TRUTH - Expected characters for each test text
# =============================================================================

EXPECTED_CHARACTERS = {
    "cask_of_amontillado": {
        "required": ["Montresor", "Fortunato"],
        "forbidden": [],
        "aliases": {
            "Montresor": ["the narrator"],
            "Fortunato": [],
        },
    },
    "gift_of_the_magi": {
        "required": ["Della", "Jim"],
        "forbidden": [],
        "aliases": {
            "Della": ["Mrs. James Dillingham Young"],
            "Jim": ["James Dillingham Young", "Mr. James Dillingham Young"],
        },
    },
    "monkeys_paw": {
        "required": ["Mr. White", "Mrs. White", "Herbert White", "Sergeant-Major Morris"],
        "forbidden": [],
        "aliases": {
            "Mr. White": ["the old man", "father"],
            "Mrs. White": ["the old woman", "mother"],
            "Herbert White": ["Herbert"],
            "Sergeant-Major Morris": ["Morris", "the sergeant-major"],
        },
    },
    "berenice": {
        "required": ["Egaeus", "Berenice"],
        "forbidden": ["Mad'selle Salle"],
        "aliases": {
            "Egaeus": ["the narrator"],
            "Berenice": [],
        },
    },
    "masque_of_red_death": {
        "required": ["Prince Prospero", "the Red Death"],
        "forbidden": [],
        "aliases": {
            "Prince Prospero": ["Prospero"],
            "the Red Death": ["Red Death"],
        },
    },
    "i_have_no_mouth": {
        "required": ["AM", "Ted", "Gorrister", "Benny", "Nimdok", "Ellen"],
        "forbidden": [],
        "aliases": {
            "AM": ["the computer", "Allied Mastercomputer"],
            "Ted": ["the narrator"],
        },
    },
}


# =============================================================================
# MODELS TO TEST (as summary generators)
# =============================================================================

MODELS = [
    # Small models
    "qwen2.5:7b",
    "qwen2.5:14b",
    "qwen3:14b",
    # Medium models
    "mistral-small3.2:24b",
    "qwen3:30b-instruct",
    "qwen2.5:32b",
    # Large models
    "qwen3-next:80b-a3b-instruct-q8_0",
    "gpt-oss:120b",
]

# Fixed extraction model - used to score all summaries equally
EXTRACTION_MODEL = "qwen2.5:32b"


# =============================================================================
# TEST TEXTS
# =============================================================================

TEST_TEXTS = {
    "cask_of_amontillado": Path("/home/zacharymandrews/Tools/audiobook_agent/Test_Texts/The Cask of Amontillado - Poe.txt"),
    "gift_of_the_magi": Path("/home/zacharymandrews/Tools/audiobook_agent/Test_Texts/The Gift of the Magi - O_Henry.txt"),
    "monkeys_paw": Path("/home/zacharymandrews/Tools/audiobook_agent/Test_Texts/The_Monkey's_Paw.txt"),
    "berenice": Path("/home/zacharymandrews/Tools/audiobook_agent/Test_Texts/Berenice - Poe.txt"),
    "masque_of_red_death": Path("/home/zacharymandrews/Tools/audiobook_agent/Test_Texts/Masque of the Red Death - Poe.txt"),
    "i_have_no_mouth": Path("/home/zacharymandrews/Tools/audiobook_agent/Test_Texts/I_Have_No_Mouth_And_I_Must_Scream.pdf"),
}


# =============================================================================
# OUTPUT PATHS
# =============================================================================

OUTPUT_PATH = Path(__file__).parent / "state" / "summary_results.json"
STRUCTURE_CACHE_DIR = Path(__file__).parent / "state" / "structure_cache"


# =============================================================================
# STRUCTURE CACHING (chapters)
# =============================================================================

def get_structure_cache_path(text_name: str) -> Path:
    """Get the path to the cached structure file for a text."""
    return STRUCTURE_CACHE_DIR / f"{text_name}.json"


def load_cached_structure(text_name: str) -> Optional[list[dict]]:
    """Load cached chapter structure if it exists."""
    cache_path = get_structure_cache_path(text_name)
    if cache_path.exists():
        try:
            with open(cache_path) as f:
                data = json.load(f)
                return data.get("chapters", [])
        except (json.JSONDecodeError, IOError) as e:
            print(f"  Warning: Failed to load cached structure: {e}")
    return None


def save_structure_to_cache(text_name: str, chapters: list[dict]) -> None:
    """Save chapter structure to cache."""
    STRUCTURE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = get_structure_cache_path(text_name)

    data = {
        "text_name": text_name,
        "generated_at": datetime.now().isoformat(),
        "chapters": chapters,
    }

    with open(cache_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"  Cached {len(chapters)} chapters to {cache_path}")


def detect_chapters(text: str, text_name: str) -> list[dict]:
    """Detect chapters in text, using cache if available."""
    # Try to load from cache first
    cached = load_cached_structure(text_name)
    if cached:
        print(f"  Loaded {len(cached)} cached chapters")
        return cached

    # Detect chapters using deterministic pipeline (no LLM variance)
    print(f"  Detecting chapters...")
    pipeline = ChapterDetectionPipeline.deterministic_only()
    chapter_map = pipeline.run(text, source_file=text_name)

    if not chapter_map or not chapter_map.chapters:
        print(f"  No chapters detected, treating as single chapter")
        chapters = [{
            "index": 0,
            "title": "Full Text",
            "start": 0,
            "end": len(text),
        }]
    else:
        chapters = []
        for ch in chapter_map.chapters:
            chapters.append({
                "index": ch.index,
                "title": ch.title or f"Chapter {ch.index + 1}",
                "start": ch.start_position,
                "end": ch.end_position,
            })

    # Cache for future use
    save_structure_to_cache(text_name, chapters)
    return chapters


# =============================================================================
# MODEL LOADING
# =============================================================================

MAX_LOAD_RETRIES = 3
LOAD_RETRY_DELAY = 30  # seconds - give Ollama time to finish unloading large models
LOAD_TIMEOUT = 300  # seconds - allow time for large model swaps


def load_model(model: str, base_url: str = "http://localhost:11434") -> tuple[bool, float, str]:
    """Load a model and measure the loading time.

    Returns:
        Tuple of (success, load_time_seconds, message)
    """
    import httpx

    print(f"  Loading model {model}...")

    load_start = time.time()
    last_error = None

    timeout = httpx.Timeout(connect=30.0, read=LOAD_TIMEOUT, write=30.0, pool=30.0)

    for attempt in range(MAX_LOAD_RETRIES):
        if attempt > 0:
            print(f"  Load retry {attempt}/{MAX_LOAD_RETRIES-1} after {LOAD_RETRY_DELAY}s delay...")
            time.sleep(LOAD_RETRY_DELAY)

        try:
            with httpx.Client(base_url=base_url, timeout=timeout) as client:
                response = client.post(
                    "/api/generate",
                    json={
                        "model": model,
                        "prompt": "Hello. Reply with just 'OK'.",
                        "stream": False,
                    },
                )

            load_time = time.time() - load_start

            if response.status_code == 200:
                print(f"  Model loaded in {load_time:.1f}s (attempt {attempt + 1})")
                return True, load_time, "Model loaded"
            else:
                last_error = f"HTTP {response.status_code}: {response.text[:200]}"
                print(f"  Load attempt {attempt + 1} failed: {last_error}")
                # Retry on any non-200 - model swap errors have various messages
                continue

        except httpx.TimeoutException as e:
            last_error = f"Timeout after {LOAD_TIMEOUT}s: {e}"
            print(f"  Load TIMEOUT (attempt {attempt + 1}): {last_error}")
            continue

        except Exception as e:
            last_error = str(e)
            print(f"  Load EXCEPTION (attempt {attempt + 1}): {e}")

    load_time = time.time() - load_start
    print(f"  Load FAILED after {MAX_LOAD_RETRIES} attempts ({load_time:.1f}s): {last_error}")
    return False, load_time, last_error or "Unknown error"


# =============================================================================
# PHASE 1: SUMMARY GENERATION
# =============================================================================

def generate_summaries(
    text: str,
    chapters: list[dict],
    model: str,
) -> tuple[list[str], float]:
    """Generate summaries for all chapters using the specified model.

    Model must already be loaded (caller handles load_model).

    Returns:
        Tuple of (summary_strings, analysis_time_seconds)
        Each summary string includes the [Characters: ...] annotation.
    """
    llm_config = LLMConfig.ollama(model=model)
    llm_client = LLMClient(llm_config)

    start = time.time()

    summarizer = ChapterSummarizer(
        llm_client=llm_client,
        summary_length="detailed",
    )

    summary_strings = []
    for ch in chapters:
        chapter_text = text[ch["start"]:ch["end"]]
        summary = summarizer.summarize_chapter(
            chapter_text=chapter_text,
            chapter_index=ch["index"],
            chapter_title=ch["title"],
        )

        # Build summary text with character list (as expected by MainCastExtractor)
        chars_list = (summary.active_characters or []) + (summary.mentioned_characters or [])
        if chars_list:
            chars_str = f"\n[Characters: {', '.join(chars_list)}]"
        else:
            chars_str = ""

        summary_strings.append(f"{summary.summary}{chars_str}")

    elapsed = time.time() - start
    return summary_strings, elapsed


# =============================================================================
# PHASE 2: CHARACTER EXTRACTION & SCORING
# =============================================================================

def run_extraction(summaries: list[str], model: str) -> tuple[list[MainCastProfile], float]:
    """Run character extraction on summaries using the specified model.

    Model must already be loaded (caller handles load_model).

    Returns:
        Tuple of (profiles, analysis_time_seconds)
    """
    llm_config = LLMConfig.ollama(model=model)
    llm_client = LLMClient(llm_config)

    start = time.time()
    extractor = MainCastExtractor(llm_client=llm_client)
    profiles = extractor.extract(
        chapter_summaries=summaries,
        use_two_pass=True,
    )
    elapsed = time.time() - start
    return profiles, elapsed


def normalize_name(name: str) -> str:
    """Normalize a character name for comparison."""
    return name.lower().strip()


def names_match(name1: str, name2: str) -> bool:
    """Check if two names match (case-insensitive, handles substrings)."""
    n1 = normalize_name(name1)
    n2 = normalize_name(name2)
    if n1 == n2:
        return True
    if n1 in n2 or n2 in n1:
        return True
    return False


def find_character(profiles: list[MainCastProfile], target_name: str) -> Optional[MainCastProfile]:
    """Find a character profile matching the target name (including aliases)."""
    for profile in profiles:
        if names_match(profile.canonical_name, target_name):
            return profile
        for alias in profile.aliases:
            if names_match(alias, target_name):
                return profile
    return None


def score_extraction(profiles: list[MainCastProfile], expected: dict) -> dict:
    """Score character extraction results against ground truth.

    Metrics (weights):
    - Recall (40%): Found all required characters?
    - Precision (30%): No hallucinated characters?
    - Alias Quality (30%): Are aliases correctly grouped?

    Returns:
        Dictionary with scores and details
    """
    required = expected["required"]
    forbidden = expected.get("forbidden", [])
    expected_aliases = expected.get("aliases", {})

    # Check required characters (recall)
    found_required = []
    missing_required = []
    for req_name in required:
        if find_character(profiles, req_name):
            found_required.append(req_name)
        else:
            missing_required.append(req_name)

    recall_score = len(found_required) / len(required) if required else 1.0

    # Check for forbidden characters (precision)
    hallucinations = []
    for forbidden_name in forbidden:
        if find_character(profiles, forbidden_name):
            hallucinations.append(forbidden_name)

    precision_score = 0.0 if hallucinations else 1.0

    # Check alias quality
    alias_scores = []
    for char_name, expected_char_aliases in expected_aliases.items():
        profile = find_character(profiles, char_name)
        if not profile or not expected_char_aliases:
            continue

        found_aliases = 0
        for exp_alias in expected_char_aliases:
            if any(names_match(a, exp_alias) for a in profile.aliases):
                found_aliases += 1

        if expected_char_aliases:
            alias_scores.append(found_aliases / len(expected_char_aliases))

    alias_quality = sum(alias_scores) / len(alias_scores) if alias_scores else 1.0

    # Calculate overall score (weighted average, scale to 0-10)
    overall = (
        recall_score * 0.40 +
        precision_score * 0.30 +
        alias_quality * 0.30
    ) * 10.0

    # Determine status
    if recall_score == 1.0 and precision_score == 1.0:
        status = "PASS"
    elif recall_score >= 0.75 and precision_score == 1.0:
        status = "PARTIAL"
    else:
        status = "FAIL"

    return {
        "recall": round(recall_score * 10, 2),
        "precision": round(precision_score * 10, 2),
        "alias_quality": round(alias_quality * 10, 2),
        "overall": round(overall, 2),
        "status": status,
        "characters_found": [p.canonical_name for p in profiles],
        "required_found": found_required,
        "required_missing": missing_required,
        "hallucinations": hallucinations,
    }


# =============================================================================
# RESULTS MANAGEMENT
# =============================================================================

def load_existing_results() -> Optional[dict]:
    """Load existing results file if it exists."""
    if OUTPUT_PATH.exists():
        try:
            with open(OUTPUT_PATH) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None
    return None


def is_completed(results: dict, text_name: str, model: str) -> bool:
    """Check if a text/model combination has already been completed."""
    if text_name not in results.get("texts", {}):
        return False
    model_result = results["texts"][text_name].get("models", {}).get(model)
    if model_result is None:
        return False
    return model_result.get("status") not in (None, "ERROR", "LOAD_FAILED")


def generate_summary_stats(results: dict, models_to_test: list, texts_to_test: list) -> dict:
    """Generate summary statistics from results."""
    summary = {
        "extraction_model": EXTRACTION_MODEL,
        "models_tested": len(models_to_test),
        "texts_tested": len(texts_to_test),
        "champion_model": None,
        "model_rankings": {},
        "perfect_models": [],
    }

    model_sizes = {
        "qwen2.5:7b": 4.7,
        "qwen2.5:14b": 9.0,
        "qwen3:14b": 9.3,
        "mistral-small3.2:24b": 15,
        "qwen3:30b-instruct": 18,
        "qwen2.5:32b": 20,
        "qwen3-next:80b-a3b-instruct-q8_0": 84,
        "gpt-oss:120b": 120,
    }

    model_scores = {}

    for model in models_to_test:
        scores = []
        summary_times = []
        extraction_times = []
        pass_count = 0

        for text_name in texts_to_test:
            if text_name in results.get("texts", {}):
                model_result = results["texts"][text_name].get("models", {}).get(model)
                if model_result and "overall" in model_result:
                    scores.append(model_result["overall"])
                    if model_result.get("status") == "PASS":
                        pass_count += 1
                    if "summary_time" in model_result:
                        summary_times.append(model_result["summary_time"])
                    if "extraction_time" in model_result:
                        extraction_times.append(model_result["extraction_time"])

        if scores:
            avg_score = sum(scores) / len(scores)
            model_scores[model] = avg_score

            ranking_entry = {
                "avg_score": round(avg_score, 2),
                "pass_count": pass_count,
                "total_texts": len(texts_to_test),
                "size_gb": model_sizes.get(model, "unknown"),
            }

            if summary_times:
                ranking_entry["avg_summary_time"] = round(sum(summary_times) / len(summary_times), 2)
            if extraction_times:
                ranking_entry["avg_extraction_time"] = round(sum(extraction_times) / len(extraction_times), 2)

            summary["model_rankings"][model] = ranking_entry

        if pass_count == len(texts_to_test):
            summary["perfect_models"].append(model)

    if model_scores:
        summary["champion_model"] = max(model_scores, key=model_scores.get)

    return summary


def save_results(results: dict, models_to_test: list, texts_to_test: list):
    """Save results incrementally with updated summary."""
    results["summary"] = generate_summary_stats(results, models_to_test, texts_to_test)

    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(results, f, indent=2)


# =============================================================================
# TEXT LOADING
# =============================================================================

def load_text(text_path: Path) -> str:
    """Load text from file, handling PDFs specially.

    Also strips Project Gutenberg boilerplate to match production pipeline behavior.
    """
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
# MAIN
# =============================================================================

def main():
    # Parse command line args
    models_to_test = MODELS
    texts_to_test = list(TEST_TEXTS.keys())
    resume_mode = False

    args = sys.argv[1:]
    if "--resume" in args:
        resume_mode = True
        args.remove("--resume")

    # Check for --model option
    model_filter = None
    for i, arg in enumerate(args):
        if arg == "--model" and i + 1 < len(args):
            model_filter = args[i + 1]
            args = args[:i] + args[i+2:]
            break
        elif arg.startswith("--model="):
            model_filter = arg.split("=", 1)[1]
            args.remove(arg)
            break

    if model_filter:
        matching = [m for m in MODELS if model_filter in m]
        if matching:
            models_to_test = matching
            print(f"Filtering to model(s): {models_to_test}")
        else:
            print(f"WARNING: No model matching '{model_filter}' found in MODELS")
            print(f"Available: {MODELS}")
            return

    if args:
        if args[0] == "--quick":
            texts_to_test = ["cask_of_amontillado", "gift_of_the_magi"]
            models_to_test = ["qwen3:30b-instruct", "qwen2.5:14b"]
        elif args[0] in TEST_TEXTS:
            texts_to_test = [args[0]]

    # Initialize or load results
    if resume_mode:
        existing = load_existing_results()
        if existing:
            results = existing
            results["resumed_at"] = datetime.now().isoformat()
            print("Resuming from existing results...")
        else:
            print("No existing results found, starting fresh...")
            results = {
                "experiment_date": datetime.now().strftime("%Y-%m-%d"),
                "experiment_timestamp": datetime.now().isoformat(),
                "extraction_model": EXTRACTION_MODEL,
                "texts": {},
                "summary": {},
            }
    else:
        results = {
            "experiment_date": datetime.now().strftime("%Y-%m-%d"),
            "experiment_timestamp": datetime.now().isoformat(),
            "extraction_model": EXTRACTION_MODEL,
            "texts": {},
            "summary": {},
        }

    print("=" * 70)
    print("SUMMARY MODEL EXPERIMENT (End-to-End)")
    print("=" * 70)
    print(f"Texts: {texts_to_test}")
    print(f"Summary models: {len(models_to_test)} models")
    print(f"Extraction model: {EXTRACTION_MODEL} (fixed)")
    print(f"Scoring: character extraction quality on generated summaries")
    if resume_mode:
        print("Mode: RESUME (skipping completed combinations)")
    print("=" * 70)

    # =========================================================================
    # PRE-LOAD: Load all texts and detect chapters
    # =========================================================================
    loaded_texts = {}  # text_name -> (text, chapters, expected)
    for text_name in texts_to_test:
        text_path = TEST_TEXTS[text_name]
        expected = EXPECTED_CHARACTERS[text_name]

        print(f"\n[LOAD] {text_name}")

        if not text_path.exists():
            print(f"  ERROR: Text file not found: {text_path}")
            continue

        try:
            text = load_text(text_path)
        except Exception as e:
            print(f"  ERROR loading text: {e}")
            continue

        print(f"  Size: {len(text):,} characters")

        # Initialize text entry in results
        if text_name not in results["texts"]:
            results["texts"][text_name] = {
                "expected": {
                    "required": expected["required"],
                },
                "char_count": len(text),
                "models": {},
            }
        else:
            if "models" not in results["texts"][text_name]:
                results["texts"][text_name]["models"] = {}

        # Detect/load chapters (cached, deterministic)
        try:
            chapters = detect_chapters(text, text_name)
            print(f"  {len(chapters)} chapters")
        except Exception as e:
            print(f"  ERROR detecting chapters: {e}")
            continue

        loaded_texts[text_name] = (text, chapters, expected)

    print(f"\nLoaded {len(loaded_texts)}/{len(texts_to_test)} texts successfully")

    # Save immediately so the monitor sees the new format
    save_results(results, models_to_test, texts_to_test)

    # =========================================================================
    # PHASE 1: Generate summaries with each model
    # =========================================================================
    print(f"\n{'='*70}")
    print("PHASE 1: SUMMARY GENERATION")
    print(f"{'='*70}")

    # model -> {text_name -> (summary_strings, time)}
    model_summaries = {}

    for model in models_to_test:
        model_short = model.split(":")[0]

        print(f"\n{'='*70}")
        print(f"SUMMARY MODEL: {model}")
        print(f"{'='*70}")

        # Check if all texts already have results for this model (resume)
        if resume_mode:
            all_done = all(
                is_completed(results, text_name, model)
                for text_name in loaded_texts
            )
            if all_done:
                print(f"  All texts already completed, skipping generation")
                continue

        # Load model once for all texts
        load_success, load_time, load_msg = load_model(model)
        if not load_success:
            print(f"  LOAD FAILED: {load_msg}")
            print(f"  Skipping all texts for this model")
            for text_name in loaded_texts:
                results["texts"][text_name]["models"][model] = {
                    "status": "LOAD_FAILED",
                    "load_time_seconds": round(load_time, 2),
                    "load_success": False,
                }
            save_results(results, models_to_test, texts_to_test)
            continue

        print(f"  Loaded in {load_time:.1f}s")

        model_summaries[model] = {}

        for text_name, (text, chapters, expected) in loaded_texts.items():
            if resume_mode and is_completed(results, text_name, model):
                print(f"\n  [{text_name}] SKIPPED (already completed)")
                continue

            print(f"\n  [{text_name}] Summarizing ({len(chapters)} chapters)...")

            try:
                summary_strings, summary_time = generate_summaries(text, chapters, model)
                model_summaries[model][text_name] = (summary_strings, summary_time)
                print(f"    Generated {len(summary_strings)} summaries in {summary_time:.1f}s")

                # Show summary lengths as a quality indicator
                total_chars = sum(len(s) for s in summary_strings)
                print(f"    Total summary length: {total_chars:,} chars")

            except Exception as e:
                print(f"    ERROR: {e}")
                import traceback
                traceback.print_exc()
                results["texts"][text_name]["models"][model] = {"error": str(e), "status": "ERROR"}
                save_results(results, models_to_test, texts_to_test)

    # =========================================================================
    # PHASE 2: Extract characters and score (fixed extraction model)
    # =========================================================================
    # Only run if there are summaries to score
    models_to_score = [m for m in models_to_test if m in model_summaries and model_summaries[m]]
    if not models_to_score:
        print("\nNo new summaries to score (all completed or failed)")
    else:
        print(f"\n{'='*70}")
        print(f"PHASE 2: CHARACTER EXTRACTION (using {EXTRACTION_MODEL})")
        print(f"{'='*70}")

        # Load extraction model once
        load_success, load_time, load_msg = load_model(EXTRACTION_MODEL)
        if not load_success:
            print(f"  FATAL: Extraction model failed to load: {load_msg}")
            print(f"  Cannot score any summaries!")
        else:
            print(f"  Extraction model loaded in {load_time:.1f}s")

            for model in models_to_score:
                model_short = model.split(":")[0]
                print(f"\n  --- Scoring summaries from: {model} ---")

                for text_name, (summary_strings, summary_time) in model_summaries[model].items():
                    expected = loaded_texts[text_name][2]  # (text, chapters, expected)

                    print(f"\n  [{text_name}] Extracting characters...")

                    try:
                        profiles, extraction_time = run_extraction(summary_strings, EXTRACTION_MODEL)
                        score = score_extraction(profiles, expected)

                        results["texts"][text_name]["models"][model] = {
                            **score,
                            "summary_time": round(summary_time, 2),
                            "extraction_time": round(extraction_time, 2),
                            "load_success": True,
                            "num_summaries": len(summary_strings),
                            "total_summary_chars": sum(len(s) for s in summary_strings),
                        }

                        print(f"    Found: {score['characters_found']}")
                        print(f"    Status: {score['status']} | Overall: {score['overall']:.1f}/10")
                        print(f"    Recall: {score['recall']:.1f} | Precision: {score['precision']:.1f} | "
                              f"Alias: {score['alias_quality']:.1f}")
                        print(f"    Summary: {summary_time:.1f}s | Extraction: {extraction_time:.1f}s")
                        if score['required_missing']:
                            print(f"    Missing: {score['required_missing']}")
                        if score['hallucinations']:
                            print(f"    HALLUCINATIONS: {score['hallucinations']}")

                    except Exception as e:
                        print(f"    ERROR: {e}")
                        import traceback
                        traceback.print_exc()
                        results["texts"][text_name]["models"][model] = {"error": str(e), "status": "ERROR"}

                    save_results(results, models_to_test, texts_to_test)

    # =========================================================================
    # SUMMARY TABLE
    # =========================================================================
    print("\n" + "=" * 70)
    print(f"RESULTS (extraction model: {EXTRACTION_MODEL})")
    print("=" * 70)

    header = f"{'Summary Model':<35}"
    for text_name in texts_to_test:
        short_name = text_name[:8]
        header += f" | {short_name:>8}"
    header += f" | {'Avg':>6}"
    print(header)
    print("-" * len(header))

    for model in models_to_test:
        model_short = model.split(":")[0][:33]
        row = f"{model_short:<35}"
        scores = []

        for text_name in texts_to_test:
            if text_name in results["texts"] and model in results["texts"][text_name]["models"]:
                r = results["texts"][text_name]["models"][model]
                if "error" in r:
                    row += f" | {'ERR':>8}"
                elif r.get("status") == "LOAD_FAILED":
                    row += f" | {'LOAD':>8}"
                elif "overall" in r:
                    status_marker = "+" if r["status"] == "PASS" else "-"
                    row += f" | {r['overall']:.1f}{status_marker:>3}"
                    scores.append(r["overall"])
                else:
                    row += f" | {'?':>8}"
            else:
                row += f" | {'-':>8}"

        if scores:
            avg = sum(scores) / len(scores)
            row += f" | {avg:>6.1f}"
        else:
            row += f" | {'-':>6}"

        print(row)

    # Print key findings
    print("\n" + "-" * 70)
    print("KEY FINDINGS:")
    if results["summary"].get("champion_model"):
        print(f"  Best summary model: {results['summary']['champion_model']}")
    if results["summary"].get("perfect_models"):
        print(f"  Perfect models: {', '.join(results['summary']['perfect_models'])}")

    save_results(results, models_to_test, texts_to_test)
    print(f"\nFull results saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
