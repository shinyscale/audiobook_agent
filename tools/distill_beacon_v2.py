#!/usr/bin/env python3
"""
distill_beacon_v2.py — Generate expanded Beacon training data from 83-book corpus.

Beacon classifies narrative POV (first_person / third_person / third_person_omniscient /
epistolary). Every book in our Gutenberg corpus has a known `expected_pov` in its
metadata, so we can generate hundreds of labeled passages per book without LLM calls.

Current Beacon training: 332 examples from 83 books (4 per book, heavy imbalance:
only 10 epistolary examples). This script generates 20-40 examples per book for a
target of ~2,500 new examples.

Usage:
    python tools/distill_beacon_v2.py              # Generate new data
    python tools/distill_beacon_v2.py --merge      # Also merge with existing
    python tools/distill_beacon_v2.py --samples N  # N passages per book (default 30)
"""

import argparse
import json
import logging
import random
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

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
DISTILLED_BEACON = TOOLS_DIR / "distilled_beacon.json"
OUTPUT_NEW = TOOLS_DIR / "distilled_beacon_v2.json"
OUTPUT_MERGED = TOOLS_DIR / "beacon_training_v2_merged.json"

# Label mapping (matches scalpels.py SCALPEL_REGISTRY)
LABEL2ID = {
    "first_person": 0,
    "third_person": 1,
    "third_person_omniscient": 2,
    "epistolary": 3,
}

# Passage sampling parameters
MIN_PASSAGE_CHARS = 800
MAX_PASSAGE_CHARS = 1500
DEFAULT_SAMPLES_PER_BOOK = 30

SEED = 42


def strip_gutenberg_metadata(text: str) -> str:
    """Remove Project Gutenberg preamble/postamble if present."""
    # Common start markers
    start_markers = [
        r'\*\*\* START OF (?:THE |THIS )?PROJECT GUTENBERG.*?\*\*\*',
        r'\*END\*THE SMALL PRINT.*?PROJECT GUTENBERG',
    ]
    for marker in start_markers:
        m = re.search(marker, text, re.IGNORECASE | re.DOTALL)
        if m:
            text = text[m.end():]
            break

    # End markers
    end_markers = [
        r'\*\*\* END OF (?:THE |THIS )?PROJECT GUTENBERG.*',
        r'End of (?:the )?Project Gutenberg',
    ]
    for marker in end_markers:
        m = re.search(marker, text, re.IGNORECASE | re.DOTALL)
        if m:
            text = text[:m.start()]
            break

    return text.strip()


def extract_clean_passages(
    text: str,
    num_samples: int,
    rng: random.Random,
) -> list[str]:
    """Extract `num_samples` clean prose passages from the book.

    Samples at random positions to get coverage across the whole book.
    Tries to start/end at paragraph boundaries for cleaner passages.
    """
    text = strip_gutenberg_metadata(text)

    # Skip table of contents area (first ~5% of text often contains TOC)
    skip_chars = min(len(text) // 20, 5000)
    usable_text = text[skip_chars:]

    if len(usable_text) < MIN_PASSAGE_CHARS * 2:
        return [usable_text[:MAX_PASSAGE_CHARS]] if usable_text else []

    # Generate random start positions
    passages = []
    seen_positions = set()
    attempts = 0

    while len(passages) < num_samples and attempts < num_samples * 4:
        attempts += 1

        # Random start, but keep samples distributed
        target_pos = rng.randint(0, len(usable_text) - MAX_PASSAGE_CHARS)

        # Bucket to avoid overlapping samples
        bucket = target_pos // (MAX_PASSAGE_CHARS // 2)
        if bucket in seen_positions:
            continue
        seen_positions.add(bucket)

        passage_len = rng.randint(MIN_PASSAGE_CHARS, MAX_PASSAGE_CHARS)

        # Try to snap start to paragraph boundary
        start = target_pos
        for offset in range(min(200, passage_len // 4)):
            if usable_text[target_pos + offset:target_pos + offset + 2] == "\n\n":
                start = target_pos + offset + 2
                break

        end = min(start + passage_len, len(usable_text))

        # Try to snap end to paragraph boundary
        for offset in range(min(200, passage_len // 4)):
            check_pos = end - offset
            if usable_text[check_pos:check_pos + 2] == "\n\n":
                end = check_pos
                break

        passage = usable_text[start:end].strip()

        # Skip if too short or mostly whitespace
        if len(passage) < MIN_PASSAGE_CHARS // 2:
            continue

        # Skip if looks like TOC (lots of chapter headings close together)
        chapter_count = len(re.findall(r'\bCHAPTER\b|\bChapter\b', passage[:500]))
        if chapter_count > 3:
            continue

        passages.append(passage)

    return passages


def distill_book(
    filepath: Path,
    meta: dict,
    num_samples: int,
    rng: random.Random,
) -> list[dict]:
    """Generate beacon training examples from one book."""
    title = meta["title"]
    author = meta.get("author", "Unknown")
    pov = meta.get("expected_pov")

    if pov not in LABEL2ID:
        logger.warning(f"  Skipping {title}: unknown POV '{pov}'")
        return []

    label_id = LABEL2ID[pov]

    try:
        text = filepath.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        logger.error(f"  Failed to read {filepath}: {e}")
        return []

    passages = extract_clean_passages(text, num_samples, rng)

    examples = []
    for passage in passages:
        examples.append({
            "text": passage,
            "label": label_id,
            "label_name": pov,
            "book": title,
            "author": author,
            "source": "corpus_sampling_v2",
            "confidence": 1.0,  # Ground truth from corpus metadata
        })

    return examples


def main():
    parser = argparse.ArgumentParser(description="Generate Beacon v2 training data from corpus")
    parser.add_argument("--samples", type=int, default=DEFAULT_SAMPLES_PER_BOOK,
                        help="Number of passages to sample per book")
    parser.add_argument("--merge", action="store_true",
                        help="Merge with existing distilled_beacon.json")
    args = parser.parse_args()

    if not CORPUS_META.exists():
        logger.error(f"Corpus metadata not found: {CORPUS_META}")
        sys.exit(1)

    with open(CORPUS_META) as f:
        corpus_meta = json.load(f)

    logger.info(f"Generating {args.samples} passages per book from {len(corpus_meta)} books")

    rng = random.Random(SEED)
    all_examples = []
    book_count = 0
    skipped = 0

    # Track POV distribution
    from collections import Counter
    pov_counts = Counter()

    for filename, meta in sorted(corpus_meta.items()):
        filepath = CORPUS_DIR / filename
        if not filepath.exists():
            logger.warning(f"Missing: {filepath}")
            skipped += 1
            continue

        examples = distill_book(filepath, meta, args.samples, rng)
        if examples:
            all_examples.extend(examples)
            book_count += 1
            pov_counts[meta["expected_pov"]] += len(examples)

    logger.info(f"\n=== Summary ===")
    logger.info(f"Books processed: {book_count} (skipped {skipped})")
    logger.info(f"Total new examples: {len(all_examples)}")
    logger.info(f"POV distribution:")
    for pov, count in sorted(pov_counts.items(), key=lambda x: -x[1]):
        pct = count / len(all_examples) * 100
        logger.info(f"  {pov}: {count} ({pct:.1f}%)")

    # Save new data
    with open(OUTPUT_NEW, "w") as f:
        json.dump(all_examples, f, indent=2, ensure_ascii=False)
    logger.info(f"\nSaved new examples to {OUTPUT_NEW}")

    # Optionally merge with existing
    if args.merge:
        existing = []
        if DISTILLED_BEACON.exists():
            with open(DISTILLED_BEACON) as f:
                existing = json.load(f)
            logger.info(f"\nLoaded {len(existing)} existing examples from {DISTILLED_BEACON}")

        merged = existing + all_examples
        logger.info(f"Merged total: {len(merged)} examples")

        # Distribution of merged dataset
        merged_counts = Counter()
        for ex in merged:
            merged_counts[ex.get("label_name", "unknown")] += 1
        logger.info(f"Merged POV distribution:")
        for pov, count in sorted(merged_counts.items(), key=lambda x: -x[1]):
            pct = count / len(merged) * 100
            logger.info(f"  {pov}: {count} ({pct:.1f}%)")

        with open(OUTPUT_MERGED, "w") as f:
            json.dump(merged, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved merged dataset to {OUTPUT_MERGED}")


if __name__ == "__main__":
    main()
