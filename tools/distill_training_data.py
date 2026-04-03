#!/usr/bin/env python3
"""
distill_training_data.py — LLM distillation pipeline for scalpel retraining.

For each Gutenberg text, runs the audiobook_agent LLM pipeline (scalpels disabled)
and extracts classification labels for Compass, Beacon, and Echo.

Also re-labels existing LiSCU compass data with a stricter prompt.

Usage:
    # Full pipeline (distillation + relabeling)
    python tools/distill_training_data.py

    # Distillation only (Gutenberg books)
    python tools/distill_training_data.py --distill-only

    # Re-labeling only (existing compass data)
    python tools/distill_training_data.py --relabel-only

    # Resume from where we left off
    python tools/distill_training_data.py --resume

Output:
    tools/distilled_compass.json   — moral valence labels
    tools/distilled_beacon.json    — POV/narrator labels
    tools/distilled_echo.json      — active vs mentioned labels
    tools/distilled_voice.json     — dialogue speaker attribution labels
    tools/relabeled_compass.json   — re-classified LiSCU entries
"""

import argparse
import json
import logging
import os
import re
import sys
import time
from pathlib import Path

# Add project root to path so we can import the pipeline
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.llm.client import LLMClient, LLMConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

TOOLS_DIR = Path(__file__).parent
CORPUS_DIR = TOOLS_DIR / "gutenberg_corpus"
CORPUS_META = CORPUS_DIR / "corpus_metadata.json"

# Output files
DISTILLED_COMPASS = TOOLS_DIR / "distilled_compass.json"
DISTILLED_BEACON = TOOLS_DIR / "distilled_beacon.json"
DISTILLED_ECHO = TOOLS_DIR / "distilled_echo.json"
DISTILLED_VOICE = TOOLS_DIR / "distilled_voice.json"
RELABELED_COMPASS = TOOLS_DIR / "relabeled_compass.json"
PROGRESS_FILE = TOOLS_DIR / "distill_progress.json"

# Label mappings (match scalpels.py SCALPEL_REGISTRY)
COMPASS_LABELS = ["protagonist", "antagonist", "morally_ambiguous", "victim", "neutral"]
BEACON_LABELS = ["first_person", "third_person", "third_person_omniscient", "epistolary"]
ECHO_LABELS = ["mentioned", "active"]
VOICE_LABELS = ["non_speaker", "speaker"]

# ── LLM Configuration ───────────────────────────────────────────────────────

DEFAULT_MODEL = "qwen3-next:80b-a3b-instruct-q8_0"
DEFAULT_BASE_URL = "http://localhost:11434"


def create_llm(model: str = DEFAULT_MODEL, base_url: str = DEFAULT_BASE_URL) -> LLMClient:
    """Create LLM client for distillation."""
    config = LLMConfig.ollama(model=model, base_url=base_url)
    config.temperature = 0.3  # Low temp for consistent classification
    config.max_tokens = 4096
    # Disable thinking if the config supports it (varies by codebase version)
    if hasattr(config, 'think'):
        config.think = False
    return LLMClient(config)


# ── Text Chunking ────────────────────────────────────────────────────────────

def split_into_chapters(text: str) -> list[dict]:
    """Split a book into approximate chapters."""
    # Try common chapter patterns
    patterns = [
        r'\n\s*(?:CHAPTER|Chapter)\s+[IVXLCDM\d]+[.\s]*(?:\n|[A-Z])',
        r'\n\s*(?:CHAPTER|Chapter)\s+\w+\s*\n',
        r'\n\s*(?:BOOK|Book|PART|Part)\s+[IVXLCDM\d]+',
    ]

    splits = []
    for pattern in patterns:
        matches = list(re.finditer(pattern, text))
        if len(matches) >= 3:  # Need at least 3 chapters
            splits = matches
            break

    if not splits:
        # Fallback: split by word count (~5000 words per chunk)
        words = text.split()
        chunk_size = 5000
        chapters = []
        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i:i + chunk_size])
            chapters.append({
                "index": len(chapters),
                "title": f"Section {len(chapters) + 1}",
                "text": chunk,
            })
        return chapters

    chapters = []
    for i, match in enumerate(splits):
        start = match.start()
        end = splits[i + 1].start() if i + 1 < len(splits) else len(text)
        chapter_text = text[start:end].strip()
        if len(chapter_text) > 200:  # Skip tiny fragments
            chapters.append({
                "index": len(chapters),
                "title": f"Chapter {len(chapters) + 1}",
                "text": chapter_text,
            })

    return chapters


def extract_passage_windows(text: str, n_windows: int = 3) -> list[str]:
    """Extract passage windows from different parts of the text for Beacon."""
    words = text.split()
    total = len(words)
    window_size = min(2000, total // (n_windows + 1))  # ~2000 words per window

    windows = []
    if total < 500:
        return [text]

    # Opening, middle, late sections
    positions = [0, total // 3, 2 * total // 3]
    for pos in positions[:n_windows]:
        end = min(pos + window_size, total)
        window = " ".join(words[pos:end])
        if len(window) > 200:
            windows.append(window)

    return windows if windows else [text[:10000]]


# ── Prompts ──────────────────────────────────────────────────────────────────

SUMMARIZE_CHAPTER_SYSTEM = """You are a literary analyst summarizing book chapters.
For each chapter, provide a concise summary and list characters.
Always respond with valid JSON. No other text."""

SUMMARIZE_CHAPTER_PROMPT = """Summarize this chapter from "{book_title}" by {author}.

CHAPTER TEXT (first ~3000 words):
{chapter_text}

Return JSON:
```json
{{
  "summary": "2-3 sentence summary of key events",
  "active_characters": ["characters who speak, act, or interact on-page"],
  "mentioned_characters": ["characters referenced but not physically present"],
  "pov_character": "name of POV character if first-person, else null"
}}
```

IMPORTANT:
- active_characters = characters who DO things in this chapter (speak, move, fight, etc.)
- mentioned_characters = characters talked about but not physically present
- Use canonical names (e.g., "Elizabeth Bennet" not "Lizzy")

Return ONLY valid JSON."""


CLASSIFY_VALENCE_SYSTEM = """You are a literary analyst classifying characters by MORAL ROLE based on ACTIONS.

Base classification ENTIRELY on what characters DO, not how they are described.

CLASSIFICATION RULES:
1. Primarily HARMFUL actions (murder, manipulation, cruelty, exploitation) → antagonist
2. Primarily BENEFICIAL actions (helping, sacrifice, protection, kindness) → protagonist
3. Both significant HARMFUL and BENEFICIAL actions → morally_ambiguous
4. Primarily receives harm from others → victim
5. Primarily NEUTRAL actions or insufficient evidence → neutral

IMPORTANT: Do NOT default to neutral. Most named characters in novels have moral significance.
- A character who suffers at others' hands is a VICTIM, not neutral
- A character who does both good and bad is MORALLY_AMBIGUOUS, not neutral
- Only truly minor or purely functional characters should be neutral

Always respond with valid JSON. No other text."""

CLASSIFY_VALENCE_PROMPT = """Classify the moral role of this character from "{book_title}".

CHARACTER: {character_name}

EVIDENCE FROM THE TEXT:
{evidence}

Return JSON:
```json
{{
  "valence": "protagonist/antagonist/morally_ambiguous/victim/neutral",
  "confidence": 0.0-1.0,
  "reasoning": "Brief explanation based on specific actions"
}}
```

Return ONLY valid JSON."""


DETECT_POV_SYSTEM = """You are a literary analyst determining narrative point of view.
Always respond with valid JSON. No other text."""

DETECT_POV_PROMPT = """Determine the narrative point of view of this text passage from "{book_title}" by {author}.

TEXT PASSAGE:
{passage}

Classify as one of:
- first_person: narrator uses "I", tells their own story
- third_person: narrator refers to characters as "he/she/they", follows one or few characters closely
- third_person_omniscient: narrator knows thoughts of multiple characters, god-like perspective
- epistolary: told through letters, diary entries, or documents

Return JSON:
```json
{{
  "pov": "first_person/third_person/third_person_omniscient/epistolary",
  "confidence": 0.0-1.0,
  "reasoning": "Brief explanation"
}}
```

Return ONLY valid JSON."""


RELABEL_COMPASS_SYSTEM = """You are a literary analyst reclassifying character moral roles.

Base classification ENTIRELY on what the character DOES (actions), not descriptions.

STRICT RULES — read carefully:
1. antagonist: Character commits harmful acts (murder, manipulation, cruelty, exploitation, deception)
2. protagonist: Character performs beneficial acts (helping, sacrifice, protection, honesty, kindness)
3. morally_ambiguous: Character does BOTH significant harmful AND beneficial things
4. victim: Character is primarily a RECIPIENT of others' harmful actions
5. neutral: ONLY for truly minor/functional characters with no moral actions

DO NOT classify as neutral unless the character genuinely has no moral impact.
Characters who suffer → victim (not neutral)
Characters who do both good and bad → morally_ambiguous (not neutral)
Characters who oppose the hero → antagonist (not neutral)

Always respond with valid JSON. No other text."""

IDENTIFY_SPEAKERS_SYSTEM = """You are a literary analyst identifying dialogue speakers.
For each passage containing quoted dialogue, determine which characters spoke.
Always respond with valid JSON. No other text."""

IDENTIFY_SPEAKERS_PROMPT = """Identify who speaks each line of dialogue in this passage from "{book_title}".

KNOWN CHARACTERS IN THIS CHAPTER:
{character_list}

PASSAGE:
{passage}

For each quoted dialogue line, identify the speaker.
Include ONLY dialogue that has a clear speaker attribution (said X, X replied, etc.)
or where the speaker is obvious from immediate context.

Return JSON:
```json
{{
  "speakers": [
    {{"character": "Name of speaker", "quote_snippet": "First few words of the quote..."}},
  ]
}}
```

RULES:
- Use the exact character name from the KNOWN CHARACTERS list
- Only include speakers you are confident about
- Include indirect speech ("Tom said that...") — the speaker is Tom
- Include internal monologue ("Tom thought, '...'") — the speaker is Tom
- For epistolary text (letters/diary entries), the letter writer is the speaker
- If a quote has no clear speaker, skip it

Return ONLY valid JSON."""


RELABEL_COMPASS_PROMPT = """Reclassify the moral role of this character.

CHARACTER: {character_name}
CURRENT LABEL: {current_label}

TEXT (from literary analysis):
{text}

Based on the ACTIONS described in this text, classify the character's moral role.
If the current label is "neutral", look harder for evidence of moral significance.
Cite specific actions before choosing.

Return JSON:
```json
{{
  "valence": "protagonist/antagonist/morally_ambiguous/victim/neutral",
  "confidence": 0.0-1.0,
  "reasoning": "Specific actions that justify this classification"
}}
```

Return ONLY valid JSON."""


# ── Progress Tracking ────────────────────────────────────────────────────────

def load_progress() -> dict:
    """Load progress state for resuming."""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return {"completed_books": [], "relabel_offset": 0}


def save_progress(progress: dict):
    """Save progress state."""
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f, indent=2)


def append_jsonl(filepath: Path, items: list[dict]):
    """Append items to a JSON list file (load, extend, save)."""
    existing = []
    if filepath.exists():
        with open(filepath) as f:
            existing = json.load(f)
    existing.extend(items)
    with open(filepath, "w") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)


# ── Dialogue Extraction ────────────────────────────────────────────────────

def extract_dialogue_passages(chapter_text: str, context_chars: int = 500) -> list[dict]:
    """Extract passages centered on quoted dialogue from chapter text.

    Returns list of dicts with 'passage' (text with context) and 'position' (char offset).
    """
    # Find quoted dialogue (double quotes, at least 5 chars inside)
    quote_pattern = re.compile(r'"([^"]{5,})"')
    passages = []
    seen_positions = set()

    for match in quote_pattern.finditer(chapter_text):
        start = max(0, match.start() - context_chars)
        end = min(len(chapter_text), match.end() + context_chars)

        # Deduplicate overlapping passages
        bucket = match.start() // context_chars
        if bucket in seen_positions:
            continue
        seen_positions.add(bucket)

        passages.append({
            "passage": chapter_text[start:end],
            "position": match.start(),
        })

    return passages


# ── Distillation Pipeline ───────────────────────────────────────────────────

def distill_book(
    llm: LLMClient,
    filepath: Path,
    meta: dict,
    voice_only: bool = False,
) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    """
    Run LLM pipeline on one book. Extract Compass, Beacon, Echo, and Voice labels.

    Returns:
        (compass_examples, beacon_examples, echo_examples, voice_examples)
    """
    title = meta["title"]
    author = meta["author"]
    expected_pov = meta["expected_pov"]

    text = filepath.read_text(encoding="utf-8", errors="replace")
    if len(text) < 5000:
        logger.warning(f"Skipping {title} — too short ({len(text)} chars)")
        return [], [], [], []

    logger.info(f"Processing: {title} by {author} ({len(text):,} chars)")

    # ── Step 1: Split into chapters ──────────────────────────────────────
    chapters = split_into_chapters(text)
    if not chapters:
        logger.warning(f"  No chapters found in {title}")
        return [], [], [], []

    logger.info(f"  Found {len(chapters)} chapters")

    # ── Step 2: Summarize chapters (extracts characters + summaries) ─────
    chapter_summaries = []
    all_characters = set()
    character_evidence = {}  # name -> list of passages
    active_by_chapter = {}   # chapter_idx -> set of active chars
    mentioned_by_chapter = {}  # chapter_idx -> set of mentioned chars

    # Process up to 30 chapters (enough for labeling, skip very long books)
    for ch in chapters[:30]:
        ch_text = ch["text"][:12000]  # Limit to ~3000 words

        prompt = SUMMARIZE_CHAPTER_PROMPT.format(
            book_title=title,
            author=author,
            chapter_text=ch_text,
        )

        result, response = llm.query_json(prompt, system=SUMMARIZE_CHAPTER_SYSTEM)
        if not response.success or result is None:
            logger.warning(f"  Chapter {ch['index']} summary failed: {response.error}")
            continue

        summary = result.get("summary", "")
        active = result.get("active_characters") or []
        mentioned = result.get("mentioned_characters") or []
        pov_char = result.get("pov_character")

        chapter_summaries.append({
            "index": ch["index"],
            "summary": summary,
            "active": active,
            "mentioned": mentioned,
            "pov_character": pov_char,
        })

        # Track characters and evidence
        ch_idx = ch["index"]
        active_by_chapter[ch_idx] = set(active)
        mentioned_by_chapter[ch_idx] = set(mentioned)

        for name in active + mentioned:
            all_characters.add(name)
            if name not in character_evidence:
                character_evidence[name] = []
            # Store summary as evidence for this character
            character_evidence[name].append(
                f"[Chapter {ch_idx + 1}] {summary}"
            )

    if not chapter_summaries:
        logger.warning(f"  No chapters summarized for {title}")
        return [], [], [], []

    logger.info(f"  Summarized {len(chapter_summaries)} chapters, "
                f"found {len(all_characters)} characters")

    # ── Step 3: Extract Compass labels (moral valence per character) ─────
    compass_examples = []
    for char_name in all_characters:
        evidence = character_evidence.get(char_name, [])
        if not evidence:
            continue

        # Format: "character_name [SEP] evidence passages"
        evidence_text = " ".join(evidence[:10])
        scalpel_text = f"{char_name} [SEP] {evidence_text}"

        prompt = CLASSIFY_VALENCE_PROMPT.format(
            book_title=title,
            character_name=char_name,
            evidence="\n".join(evidence[:10]),
        )

        result, response = llm.query_json(prompt, system=CLASSIFY_VALENCE_SYSTEM)
        if not response.success or result is None:
            continue

        valence = result.get("valence", "").lower().strip()
        confidence = float(result.get("confidence", 0.5))

        if valence not in COMPASS_LABELS:
            continue

        compass_examples.append({
            "text": scalpel_text,
            "label": valence,
            "source": "distillation",
            "book": title,
            "character_name": char_name,
            "confidence": confidence,
        })

    logger.info(f"  Compass: {len(compass_examples)} character labels")

    # ── Step 4: Extract Beacon labels (POV per passage window) ───────────
    beacon_examples = []
    windows = extract_passage_windows(text, n_windows=3)

    for i, window in enumerate(windows):
        # Truncate to reasonable size for the prompt
        window_text = window[:8000]

        prompt = DETECT_POV_PROMPT.format(
            book_title=title,
            author=author,
            passage=window_text,
        )

        result, response = llm.query_json(prompt, system=DETECT_POV_SYSTEM)
        if not response.success or result is None:
            continue

        pov = result.get("pov", "").lower().strip()
        confidence = float(result.get("confidence", 0.5))

        if pov not in BEACON_LABELS:
            continue

        # For beacon, the text fed to the scalpel is the passage itself
        # (the scalpel gets raw passage text, not summaries)
        beacon_examples.append({
            "text": window_text,
            "label": BEACON_LABELS.index(pov),
            "label_name": pov,
            "book": title,
            "author": author,
            "source": "distillation",
            "confidence": confidence,
        })

    # Also create a beacon example from concatenated chapter summaries
    # (this is how beacon is actually used in the pipeline)
    summary_texts = [cs["summary"] for cs in chapter_summaries[:4]]
    if summary_texts:
        combined = " ".join(summary_texts)
        prompt = DETECT_POV_PROMPT.format(
            book_title=title,
            author=author,
            passage=combined,
        )
        result, response = llm.query_json(prompt, system=DETECT_POV_SYSTEM)
        if response.success and result:
            pov = result.get("pov", "").lower().strip()
            confidence = float(result.get("confidence", 0.5))
            if pov in BEACON_LABELS:
                beacon_examples.append({
                    "text": combined,
                    "label": BEACON_LABELS.index(pov),
                    "label_name": pov,
                    "book": title,
                    "author": author,
                    "source": "distillation_summary",
                    "confidence": confidence,
                })

    logger.info(f"  Beacon: {len(beacon_examples)} POV labels")

    # ── Step 5: Extract Echo labels (active vs mentioned per char×chapter)
    echo_examples = []
    for cs in chapter_summaries:
        ch_idx = cs["index"]
        summary = cs["summary"]
        if not summary:
            continue

        active_set = active_by_chapter.get(ch_idx, set())
        mentioned_set = mentioned_by_chapter.get(ch_idx, set())

        for char_name in active_set:
            echo_text = f"{char_name} [SEP] {summary}"
            echo_examples.append({
                "text": echo_text,
                "label": 1,  # active
                "character": char_name,
                "matched_name": char_name,
                "book": title,
                "chapter_index": ch_idx,
                "chapter_title": cs.get("title", ""),
                "num_mentions": 1,  # approximate
            })

        for char_name in mentioned_set:
            echo_text = f"{char_name} [SEP] {summary}"
            echo_examples.append({
                "text": echo_text,
                "label": 0,  # mentioned
                "character": char_name,
                "matched_name": char_name,
                "book": title,
                "chapter_index": ch_idx,
                "chapter_title": cs.get("title", ""),
                "num_mentions": 1,
            })

    logger.info(f"  Echo: {len(echo_examples)} active/mentioned labels")

    # ── Step 6: Extract Voice labels (dialogue speaker attribution) ───
    voice_examples = []
    for ch in chapters[:30]:
        ch_text = ch["text"]
        ch_idx = ch["index"]

        # Get characters known to be in this chapter
        active_set = active_by_chapter.get(ch_idx, set())
        mentioned_set = mentioned_by_chapter.get(ch_idx, set())
        chapter_chars = active_set | mentioned_set
        if not chapter_chars:
            continue

        # Extract dialogue passages from this chapter
        dialogue_passages = extract_dialogue_passages(ch_text)
        if not dialogue_passages:
            continue

        # For each dialogue passage, ask LLM who spoke
        for dp in dialogue_passages:
            passage_text = dp["passage"]

            # Find which known characters appear in or near this passage
            chars_in_passage = set()
            passage_lower = passage_text.lower()
            for char_name in chapter_chars:
                # Check if any name part appears (handle "Tom Buchanan" matching "Tom")
                name_parts = char_name.split()
                if any(part.lower() in passage_lower for part in name_parts if len(part) > 2):
                    chars_in_passage.add(char_name)

            if not chars_in_passage:
                continue

            prompt = IDENTIFY_SPEAKERS_PROMPT.format(
                book_title=title,
                character_list="\n".join(f"- {c}" for c in sorted(chapter_chars)),
                passage=passage_text[:3000],
            )

            result, response = llm.query_json(prompt, system=IDENTIFY_SPEAKERS_SYSTEM)
            if not response.success or result is None:
                continue

            speakers_list = result.get("speakers") or []
            speaker_names = set()
            for s in speakers_list:
                sname = s.get("character", "")
                # Match to known character name (fuzzy: check if LLM name matches any known)
                for known in chapter_chars:
                    if sname.lower() == known.lower() or sname.lower() in known.lower() or known.lower() in sname.lower():
                        speaker_names.add(known)
                        break

            # Create positive examples (speaker) and negative examples (non-speaker)
            for char_name in chars_in_passage:
                voice_text = f"{char_name} [SEP] {passage_text}"
                is_speaker = char_name in speaker_names
                voice_examples.append({
                    "text": voice_text,
                    "label": 1 if is_speaker else 0,
                    "character": char_name,
                    "book": title,
                    "chapter_index": ch_idx,
                    "source": "distillation",
                })

    logger.info(f"  Voice: {len(voice_examples)} speaker/non-speaker labels")
    if voice_examples:
        speaker_count = sum(1 for v in voice_examples if v["label"] == 1)
        logger.info(f"    speaker={speaker_count}, non_speaker={len(voice_examples) - speaker_count}")

    return compass_examples, beacon_examples, echo_examples, voice_examples


# ── Compass Re-labeling ─────────────────────────────────────────────────────

def relabel_compass_dataset(
    llm: LLMClient,
    dataset_path: Path,
    output_path: Path,
    resume_offset: int = 0,
    batch_size: int = 50,
) -> int:
    """
    Re-label existing compass dataset entries using stricter LLM prompt.

    Only re-labels entries from LiSCU source (the ones with neutral bias).
    Returns the number of entries processed.
    """
    if not dataset_path.exists():
        logger.error(f"Compass dataset not found: {dataset_path}")
        return 0

    with open(dataset_path) as f:
        data = json.load(f)

    # Find LiSCU entries (source contains "liscu" or "shmoop" or "sparknotes")
    # and entries currently labeled neutral
    candidates = []
    for i, entry in enumerate(data):
        source = entry.get("source", "").lower()
        label = entry.get("label", "")
        # Re-label all LiSCU/academic entries, prioritizing neutrals
        if any(s in source for s in ["liscu", "shmoop", "sparknotes", "litbank"]):
            candidates.append((i, entry))

    logger.info(f"Found {len(candidates)} LiSCU entries to re-label "
                f"(resuming from offset {resume_offset})")

    # Load existing relabeled data
    relabeled = []
    if output_path.exists():
        with open(output_path) as f:
            relabeled = json.load(f)

    processed = 0
    changed = 0
    for batch_start in range(resume_offset, len(candidates), batch_size):
        batch = candidates[batch_start:batch_start + batch_size]

        for idx, entry in batch:
            text = entry.get("text", "")
            current_label = entry.get("label", "neutral")
            char_name = entry.get("character_name", "Unknown")

            prompt = RELABEL_COMPASS_PROMPT.format(
                character_name=char_name,
                current_label=current_label,
                text=text[:3000],
            )

            result, response = llm.query_json(prompt, system=RELABEL_COMPASS_SYSTEM)

            new_label = current_label  # default: keep existing
            confidence = 0.5
            if response.success and result:
                valence = result.get("valence", "").lower().strip()
                confidence = float(result.get("confidence", 0.5))
                if valence in COMPASS_LABELS:
                    new_label = valence

            if new_label != current_label:
                changed += 1

            relabeled.append({
                "original_index": idx,
                "text": text,
                "label": new_label,
                "original_label": current_label,
                "source": entry.get("source", ""),
                "book": entry.get("book", ""),
                "character_name": char_name,
                "confidence": confidence,
                "relabeled": new_label != current_label,
            })
            processed += 1

        # Save progress after each batch
        with open(output_path, "w") as f:
            json.dump(relabeled, f, indent=2, ensure_ascii=False)

        logger.info(f"  Re-labeled {processed}/{len(candidates)} "
                    f"({changed} changed so far)")

        # Save progress offset
        progress = load_progress()
        progress["relabel_offset"] = batch_start + len(batch)
        save_progress(progress)

    label_dist = {}
    for r in relabeled:
        label_dist[r["label"]] = label_dist.get(r["label"], 0) + 1
    logger.info(f"Re-labeling complete: {processed} processed, {changed} changed")
    logger.info(f"  New distribution: {label_dist}")

    return processed


# ── Merge Utility ────────────────────────────────────────────────────────────

def merge_datasets(
    existing_path: Path | None,
    distilled_path: Path,
    relabeled_path: Path | None,
    output_path: Path,
    dataset_type: str,
):
    """Merge existing + distilled + relabeled data into unified dataset."""
    merged = []

    # Load existing data
    if existing_path and existing_path.exists():
        with open(existing_path) as f:
            existing = json.load(f)
        logger.info(f"  Existing {dataset_type}: {len(existing)} entries")

        if dataset_type == "compass" and relabeled_path and relabeled_path.exists():
            # For compass: replace LiSCU entries with relabeled versions
            with open(relabeled_path) as f:
                relabeled = json.load(f)

            # Build lookup of relabeled indices
            relabeled_indices = {r["original_index"]: r for r in relabeled}

            for i, entry in enumerate(existing):
                if i in relabeled_indices:
                    r = relabeled_indices[i]
                    merged.append({
                        "text": r["text"],
                        "label": r["label"],
                        "source": r["source"],
                        "book": r["book"],
                        "character_name": r["character_name"],
                        "confidence": r["confidence"],
                    })
                else:
                    merged.append(entry)

            logger.info(f"  Applied {len(relabeled_indices)} relabeled entries")
        else:
            merged.extend(existing)

    # Load distilled data
    if distilled_path.exists():
        with open(distilled_path) as f:
            distilled = json.load(f)
        logger.info(f"  Distilled {dataset_type}: {len(distilled)} entries")
        merged.extend(distilled)

    # Save merged
    with open(output_path, "w") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
    logger.info(f"  Merged {dataset_type}: {len(merged)} total entries → {output_path}")

    # Print distribution
    label_key = "label"
    dist = {}
    for entry in merged:
        lbl = entry.get(label_key, "unknown")
        dist[lbl] = dist.get(lbl, 0) + 1
    logger.info(f"  Distribution: {dist}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="LLM distillation for scalpel retraining")
    parser.add_argument("--distill-only", action="store_true",
                        help="Only run Gutenberg distillation")
    parser.add_argument("--relabel-only", action="store_true",
                        help="Only run compass re-labeling")
    parser.add_argument("--merge-only", action="store_true",
                        help="Only merge existing results (no LLM calls)")
    parser.add_argument("--resume", action="store_true",
                        help="Resume from last progress checkpoint")
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        help=f"LLM model name (default: {DEFAULT_MODEL})")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL,
                        help=f"Ollama base URL (default: {DEFAULT_BASE_URL})")
    parser.add_argument("--compass-dataset", type=Path, default=None,
                        help="Path to existing compass_unified_dataset.json for re-labeling")
    parser.add_argument("--echo-dataset", type=Path, default=None,
                        help="Path to existing echo_unified_dataset.json for merging")
    parser.add_argument("--beacon-dataset", type=Path, default=None,
                        help="Path to existing beacon_training_data.json for merging")
    parser.add_argument("--voice-only", action="store_true",
                        help="Only run Voice (dialogue speaker) distillation")
    args = parser.parse_args()

    start_time = time.time()
    progress = load_progress() if args.resume else {"completed_books": [], "relabel_offset": 0}

    if not args.merge_only:
        llm = create_llm(model=args.model, base_url=args.base_url)

        # Test connection
        ok, msg = llm.test_connection()
        if not ok:
            logger.error(f"LLM connection failed: {msg}")
            sys.exit(1)
        logger.info(f"LLM connected: {msg}")

    # ── Phase 1: Gutenberg Distillation ──────────────────────────────────
    if not args.relabel_only and not args.merge_only:
        if not CORPUS_META.exists():
            logger.error(f"Corpus metadata not found: {CORPUS_META}")
            logger.error("Run curate_gutenberg.py first!")
            sys.exit(1)

        with open(CORPUS_META) as f:
            corpus_meta = json.load(f)

        logger.info(f"\n{'='*60}")
        logger.info(f"Phase 1: Gutenberg Distillation ({len(corpus_meta)} books)")
        logger.info(f"{'='*60}")

        total_compass = 0
        total_beacon = 0
        total_echo = 0
        total_voice = 0
        books_done = 0

        # For --voice-only, use a separate progress key to avoid skipping books
        progress_key = "completed_books_voice" if args.voice_only else "completed_books"
        if args.voice_only and progress_key not in progress:
            progress[progress_key] = []

        for filename, meta in sorted(corpus_meta.items()):
            if filename in progress.get(progress_key, []):
                logger.info(f"SKIP (already done): {meta['title']}")
                continue

            filepath = CORPUS_DIR / filename
            if not filepath.exists():
                logger.warning(f"SKIP (file missing): {filename}")
                continue

            try:
                compass, beacon, echo, voice = distill_book(
                    llm, filepath, meta, voice_only=args.voice_only,
                )
            except Exception as e:
                logger.error(f"FAILED on {meta['title']}: {e}")
                continue

            # Append results
            if compass and not args.voice_only:
                append_jsonl(DISTILLED_COMPASS, compass)
                total_compass += len(compass)
            if beacon and not args.voice_only:
                append_jsonl(DISTILLED_BEACON, beacon)
                total_beacon += len(beacon)
            if echo and not args.voice_only:
                append_jsonl(DISTILLED_ECHO, echo)
                total_echo += len(echo)
            if voice:
                append_jsonl(DISTILLED_VOICE, voice)
                total_voice += len(voice)

            books_done += 1
            progress[progress_key].append(filename)
            save_progress(progress)

            elapsed = time.time() - start_time
            logger.info(f"  [{books_done}] Totals: compass={total_compass}, "
                        f"beacon={total_beacon}, echo={total_echo}, "
                        f"voice={total_voice} "
                        f"({elapsed / 60:.1f}min elapsed)")

        logger.info(f"\nDistillation complete: {books_done} books processed")
        logger.info(f"  Compass: {total_compass} examples → {DISTILLED_COMPASS}")
        logger.info(f"  Beacon: {total_beacon} examples → {DISTILLED_BEACON}")
        logger.info(f"  Echo: {total_echo} examples → {DISTILLED_ECHO}")
        logger.info(f"  Voice: {total_voice} examples → {DISTILLED_VOICE}")

    # ── Phase 2: Compass Re-labeling ─────────────────────────────────────
    if not args.distill_only and not args.merge_only and not args.voice_only:
        compass_dataset = args.compass_dataset
        if compass_dataset is None:
            # Try common locations
            candidates = [
                Path("/home/zacharymandrews/Tools/audiobook_agent/data/compass_unified_dataset.json"),
                TOOLS_DIR / "compass_unified_dataset.json",
            ]
            for c in candidates:
                if c.exists():
                    compass_dataset = c
                    break

        if compass_dataset and compass_dataset.exists():
            logger.info(f"\n{'='*60}")
            logger.info(f"Phase 2: Compass Re-labeling")
            logger.info(f"{'='*60}")

            relabel_compass_dataset(
                llm,
                compass_dataset,
                RELABELED_COMPASS,
                resume_offset=progress.get("relabel_offset", 0),
            )
        else:
            logger.warning("Compass dataset not found — skipping re-labeling. "
                          "Use --compass-dataset to specify path.")

    # ── Phase 3: Merge ───────────────────────────────────────────────────
    if args.merge_only or (not args.distill_only and not args.relabel_only):
        logger.info(f"\n{'='*60}")
        logger.info(f"Phase 3: Merge datasets")
        logger.info(f"{'='*60}")

        # Compass merge
        if DISTILLED_COMPASS.exists() or RELABELED_COMPASS.exists():
            merge_datasets(
                existing_path=args.compass_dataset,
                distilled_path=DISTILLED_COMPASS,
                relabeled_path=RELABELED_COMPASS,
                output_path=TOOLS_DIR / "compass_unified_merged.json",
                dataset_type="compass",
            )

        # Beacon merge
        if DISTILLED_BEACON.exists():
            merge_datasets(
                existing_path=args.beacon_dataset,
                distilled_path=DISTILLED_BEACON,
                relabeled_path=None,
                output_path=TOOLS_DIR / "beacon_training_merged.json",
                dataset_type="beacon",
            )

        # Echo merge
        if DISTILLED_ECHO.exists():
            merge_datasets(
                existing_path=args.echo_dataset,
                distilled_path=DISTILLED_ECHO,
                relabeled_path=None,
                output_path=TOOLS_DIR / "echo_unified_merged.json",
                dataset_type="echo",
            )

        # Voice merge
        if DISTILLED_VOICE.exists():
            merge_datasets(
                existing_path=None,
                distilled_path=DISTILLED_VOICE,
                relabeled_path=None,
                output_path=TOOLS_DIR / "voice_unified_dataset.json",
                dataset_type="voice",
            )

    elapsed = time.time() - start_time
    logger.info(f"\nTotal time: {elapsed / 60:.1f} minutes ({elapsed / 3600:.1f} hours)")


if __name__ == "__main__":
    main()
