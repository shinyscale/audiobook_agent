#!/usr/bin/env python3
"""
distill_dialogue_attribution.py — Generate CRF training data for dialogue speaker attribution.

For each Gutenberg text, extracts dialogue turns and asks the LLM to identify
speakers. Outputs labeled sequences suitable for sklearn-crfsuite training.

Usage:
    python tools/distill_dialogue_attribution.py
    python tools/distill_dialogue_attribution.py --resume
    python tools/distill_dialogue_attribution.py --train  # Generate data then train CRF

Output:
    tools/distilled_dialogue_attribution.json — labeled dialogue sequences
    models/attribution_crf/attribution_crf.pkl — trained CRF model (with --train)
"""

import argparse
import json
import logging
import os
import pickle
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.llm.client import LLMClient, LLMConfig
from src.pipeline.dialogue_attribution import (
    extract_dialogue_turns,
    extract_features,
    _find_character_in_context,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

TOOLS_DIR = Path(__file__).parent
CORPUS_DIR = TOOLS_DIR / "gutenberg_corpus"
CORPUS_META = CORPUS_DIR / "corpus_metadata.json"

OUTPUT_FILE = TOOLS_DIR / "distilled_dialogue_attribution.json"
PROGRESS_FILE = TOOLS_DIR / "dialogue_attribution_progress.json"
MODEL_DIR = PROJECT_ROOT / "models" / "attribution_crf"

DEFAULT_MODEL = "qwen3-next:80b-a3b-instruct-q8_0"
DEFAULT_BASE_URL = "http://localhost:11434"


IDENTIFY_SPEAKERS_SYSTEM = """You are a literary analyst identifying dialogue speakers.
Given a passage with multiple lines of quoted dialogue, determine which character speaks each quote.
Always respond with valid JSON. No other text."""

IDENTIFY_SPEAKERS_PROMPT = """Identify who speaks each quoted dialogue line in this passage from "{book_title}".

KNOWN CHARACTERS IN THIS CHAPTER:
{character_list}

PASSAGE:
{passage}

For EACH quoted dialogue line (text inside quotation marks), identify the speaker.
Use ONLY character names from the KNOWN CHARACTERS list above.
If a quote's speaker is unclear or ambiguous, set speaker to "UNKNOWN".

Return JSON:
```json
{{
  "attributions": [
    {{"quote_start": "First 5-8 words of the quote...", "speaker": "Character Name"}},
  ]
}}
```

RULES:
- Process quotes IN ORDER of appearance in the passage
- Use exact character names from the KNOWN CHARACTERS list
- Look for dialogue tags: "said X", "X replied", "asked X"
- Look for action beats: "X smiled. 'Hello'" — X is the speaker
- For alternating dialogue (A speaks, then B, then A), maintain the alternation
- For embedded/nested quotes (quote within a quote), attribute the outer quote
- If truly unclear, use "UNKNOWN"

Return ONLY valid JSON."""


def create_llm(model: str = DEFAULT_MODEL, base_url: str = DEFAULT_BASE_URL) -> LLMClient:
    config = LLMConfig.ollama(model=model, base_url=base_url)
    config.temperature = 0.1
    config.max_tokens = 4096
    if hasattr(config, 'think'):
        config.think = False
    return LLMClient(config)


def split_into_chapters(text: str) -> list[dict]:
    """Split text into chapters (simplified version from distill_training_data.py)."""
    patterns = [
        r'\n\s*(?:CHAPTER|Chapter)\s+[IVXLCDM\d]+[.\s]*(?:\n|[A-Z])',
        r'\n\s*(?:CHAPTER|Chapter)\s+\w+\s*\n',
        r'\n\s*(?:BOOK|Book|PART|Part)\s+[IVXLCDM\d]+',
    ]
    splits = []
    for pattern in patterns:
        matches = list(re.finditer(pattern, text))
        if len(matches) >= 3:
            splits = matches
            break

    if not splits:
        words = text.split()
        chapters = []
        for i in range(0, len(words), 5000):
            chunk = " ".join(words[i:i + 5000])
            chapters.append({"index": len(chapters), "title": f"Section {len(chapters) + 1}", "text": chunk})
        return chapters

    chapters = []
    for i, match in enumerate(splits):
        start = match.start()
        end = splits[i + 1].start() if i + 1 < len(splits) else len(text)
        chapter_text = text[start:end].strip()
        if len(chapter_text) > 200:
            chapters.append({"index": len(chapters), "title": f"Chapter {len(chapters) + 1}", "text": chapter_text})
    return chapters


def extract_characters_from_chapter(chapter_text: str, llm: LLMClient, book_title: str) -> list[str]:
    """Ask LLM to identify characters in a chapter."""
    # Take first 3000 chars as representative
    sample = chapter_text[:3000]
    prompt = f"""List all named characters who appear in this passage from "{book_title}".
Include characters who speak, act, or are directly addressed.
Do NOT include characters who are merely mentioned in passing.

PASSAGE:
{sample}

Return JSON:
```json
{{"characters": ["Name1", "Name2", ...]}}
```

Return ONLY valid JSON."""

    result, response = llm.query_json(prompt)
    if not response.success or result is None:
        return []
    return result.get("characters", [])


def label_chapter_dialogue(
    llm: LLMClient,
    chapter_text: str,
    characters: list[str],
    book_title: str,
    chapter_index: int,
) -> list[dict]:
    """Extract and label dialogue turns in one chapter.

    Returns a list of labeled turns (the training sequence for this chapter).
    """
    turns = extract_dialogue_turns(chapter_text)
    if not turns or not characters:
        return []

    # Process in windows of ~5 turns (enough context for the LLM, not too many)
    window_size = 5
    labeled_turns = []

    for win_start in range(0, len(turns), window_size):
        win_end = min(win_start + window_size, len(turns))
        window_turns = turns[win_start:win_end]

        # Build passage with quotes highlighted for the LLM
        first_pos = max(0, window_turns[0]["position"] - 200)
        last_pos = window_turns[-1]["position"] + len(window_turns[-1]["quote"]) + 200
        last_pos = min(last_pos, len(chapter_text))
        passage = chapter_text[first_pos:last_pos]

        if len(passage) < 20:
            continue

        prompt = IDENTIFY_SPEAKERS_PROMPT.format(
            book_title=book_title,
            character_list="\n".join(f"- {c}" for c in sorted(characters)),
            passage=passage[:4000],
        )

        result, response = llm.query_json(prompt, system=IDENTIFY_SPEAKERS_SYSTEM)
        if not response.success or result is None:
            continue

        attributions = result.get("attributions", [])

        # Match LLM attributions back to our extracted turns
        for turn in window_turns:
            quote_start_words = turn["quote"][:40].lower().strip()
            matched_speaker = "UNKNOWN"

            for attr in attributions:
                attr_start = attr.get("quote_start", "").lower().strip()
                if not attr_start:
                    continue
                # Fuzzy match: first few words overlap
                if (attr_start[:20] in quote_start_words or
                        quote_start_words[:20] in attr_start):
                    speaker_name = attr.get("speaker", "UNKNOWN")
                    # Validate against known characters (fuzzy)
                    for known in characters:
                        if (speaker_name.lower() == known.lower() or
                                speaker_name.lower() in known.lower() or
                                known.lower() in speaker_name.lower()):
                            matched_speaker = known
                            break
                    else:
                        if speaker_name != "UNKNOWN":
                            matched_speaker = speaker_name
                    break

            labeled_turns.append({
                "quote": turn["quote"][:500],
                "position": turn["position"],
                "pre_context": turn["pre_context"],
                "post_context": turn["post_context"],
                "speaker": matched_speaker,
                "chapter_index": chapter_index,
            })

    return labeled_turns


def distill_book(
    llm: LLMClient,
    filepath: Path,
    meta: dict,
) -> list[dict]:
    """Process one book: extract and label all dialogue sequences.

    Returns list of chapter sequences, each a list of labeled turns.
    """
    title = meta["title"]
    text = filepath.read_text(encoding="utf-8", errors="replace")

    if len(text) < 1000:
        logger.warning(f"  Skipping {title}: too short ({len(text)} chars)")
        return []

    logger.info(f"Processing: {title} by {meta['author']} ({len(text):,} chars)")

    chapters = split_into_chapters(text)
    logger.info(f"  {len(chapters)} chapters found")

    all_sequences = []

    for ch in chapters[:30]:  # Cap at 30 chapters per book
        ch_text = ch["text"]
        ch_idx = ch["index"]

        # Get characters for this chapter
        characters = extract_characters_from_chapter(ch_text, llm, title)
        if len(characters) < 2:
            continue

        # Label dialogue turns
        labeled = label_chapter_dialogue(llm, ch_text, characters, title, ch_idx)
        if not labeled:
            continue

        # Count speakers
        speakers = set(t["speaker"] for t in labeled if t["speaker"] != "UNKNOWN")
        unknown_count = sum(1 for t in labeled if t["speaker"] == "UNKNOWN")

        if speakers:
            all_sequences.append({
                "book": title,
                "chapter_index": ch_idx,
                "characters": characters,
                "turns": labeled,
            })

    total_turns = sum(len(s["turns"]) for s in all_sequences)
    total_known = sum(
        sum(1 for t in s["turns"] if t["speaker"] != "UNKNOWN")
        for s in all_sequences
    )
    logger.info(f"  Result: {len(all_sequences)} chapters, {total_turns} turns, {total_known} attributed")

    return all_sequences


def load_progress() -> dict:
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return {"completed_books": []}


def save_progress(progress: dict):
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f, indent=2)


def append_data(filepath: Path, items: list[dict]):
    existing = []
    if filepath.exists():
        with open(filepath) as f:
            existing = json.load(f)
    existing.extend(items)
    with open(filepath, "w") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)


def train_crf(data_path: Path, output_path: Path):
    """Train CRF model from labeled dialogue sequences."""
    import sklearn_crfsuite
    from sklearn_crfsuite import metrics as crf_metrics
    from sklearn.model_selection import train_test_split

    logger.info("Loading training data...")
    with open(data_path) as f:
        sequences = json.load(f)

    logger.info(f"  {len(sequences)} chapter sequences loaded")

    # Build feature sequences and label sequences
    X_all = []
    y_all = []

    for seq in sequences:
        characters = seq["characters"]
        turns = seq["turns"]
        if len(turns) < 2:
            continue

        features_seq = []
        labels_seq = []
        prev_speaker = None
        prev_prev_speaker = None

        for i, turn in enumerate(turns):
            feats = extract_features(
                turn, i, len(turns), characters,
                prev_speaker=prev_speaker,
                prev_prev_speaker=prev_prev_speaker,
            )
            features_seq.append(feats)
            labels_seq.append(turn["speaker"])
            prev_prev_speaker = prev_speaker
            prev_speaker = turn["speaker"]

        X_all.append(features_seq)
        y_all.append(labels_seq)

    if len(X_all) < 10:
        logger.error(f"Not enough training data: {len(X_all)} sequences")
        return

    # Train/test split by sequence (leave some chapters out)
    X_train, X_test, y_train, y_test = train_test_split(
        X_all, y_all, test_size=0.2, random_state=42,
    )

    logger.info(f"  Train: {len(X_train)} sequences, Test: {len(X_test)} sequences")

    # Train CRF
    crf = sklearn_crfsuite.CRF(
        algorithm='lbfgs',
        c1=0.1,
        c2=0.1,
        max_iterations=200,
        all_possible_transitions=True,
    )

    logger.info("Training CRF...")
    crf.fit(X_train, y_train)

    # Evaluate
    y_pred = crf.predict(X_test)

    # Flatten for metrics
    y_test_flat = [label for seq in y_test for label in seq]
    y_pred_flat = [label for seq in y_pred for label in seq]

    # Filter out UNKNOWN for scoring
    known_indices = [i for i, l in enumerate(y_test_flat) if l != "UNKNOWN"]
    if known_indices:
        y_test_known = [y_test_flat[i] for i in known_indices]
        y_pred_known = [y_pred_flat[i] for i in known_indices]

        labels = sorted(set(y_test_known + y_pred_known))
        report = crf_metrics.flat_classification_report(
            [y_test_known], [y_pred_known], labels=labels, digits=3,
        )
        logger.info(f"Classification report (excluding UNKNOWN):\n{report}")

    # Accuracy including UNKNOWN
    correct = sum(1 for a, b in zip(y_test_flat, y_pred_flat) if a == b)
    total = len(y_test_flat)
    logger.info(f"Overall accuracy: {correct}/{total} = {correct / total:.3f}")

    # Save model
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        pickle.dump(crf, f)
    logger.info(f"Model saved to {output_path}")

    # Print top features
    try:
        top_positive = crf.state_features_
        top_n = sorted(top_positive.items(), key=lambda x: abs(x[1]), reverse=True)[:20]
        logger.info("Top 20 features by weight:")
        for (attr, label), weight in top_n:
            logger.info(f"  {weight:+.3f} {attr} -> {label}")
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Distill dialogue attribution training data")
    parser.add_argument("--resume", action="store_true", help="Resume from progress")
    parser.add_argument("--train", action="store_true", help="Train CRF after distillation")
    parser.add_argument("--train-only", action="store_true", help="Only train (skip distillation)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="LLM model name")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="LLM API base URL")
    args = parser.parse_args()

    if args.train_only:
        import pickle  # noqa: F811
        train_crf(OUTPUT_FILE, MODEL_DIR / "attribution_crf.pkl")
        return

    if not CORPUS_META.exists():
        logger.error(f"Corpus metadata not found: {CORPUS_META}")
        logger.error("Run tools/curate_gutenberg.py first to build the corpus")
        sys.exit(1)

    with open(CORPUS_META) as f:
        corpus_meta = json.load(f)

    llm = create_llm(model=args.model, base_url=args.base_url)
    progress = load_progress() if args.resume else {"completed_books": []}

    total_sequences = 0
    total_turns = 0

    for filename, meta in sorted(corpus_meta.items()):
        if filename in progress["completed_books"]:
            logger.info(f"SKIP (already done): {meta['title']}")
            continue

        filepath = CORPUS_DIR / filename
        if not filepath.exists():
            logger.warning(f"File not found: {filepath}")
            continue

        try:
            sequences = distill_book(llm, filepath, meta)

            if sequences:
                append_data(OUTPUT_FILE, sequences)
                total_sequences += len(sequences)
                total_turns += sum(len(s["turns"]) for s in sequences)

            progress["completed_books"].append(filename)
            save_progress(progress)

        except Exception as e:
            logger.error(f"Failed on {meta['title']}: {e}")
            continue

    logger.info(f"\nDistillation complete: {total_sequences} sequences, {total_turns} turns")

    if args.train and OUTPUT_FILE.exists():
        import pickle  # noqa: F811
        train_crf(OUTPUT_FILE, MODEL_DIR / "attribution_crf.pkl")


if __name__ == "__main__":
    main()
