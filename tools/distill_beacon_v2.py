#!/usr/bin/env python3
"""
distill_beacon_v2.py — Smarter Beacon training data from 83-book corpus.

Key improvements over the naive version:
1. **Targeted sampling**: Prefer chapter openings where POV signals are strongest
2. **Epistolary bias**: Sample passages containing letter/diary markers for epistolary class
3. **Skip mixed-POV books**: Bleak House and A Study in Scarlet have alternating POVs — too noisy
4. **Quality filtering**: Skip passages that look like TOC, frontmatter, or low-content

Current Beacon training: 332 examples from 83 books, mostly noisy.
This generates ~1,500 high-quality examples targeted at clear POV signals.
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

OUTPUT_NEW = TOOLS_DIR / "distilled_beacon_v2.json"
OUTPUT_MERGED = TOOLS_DIR / "beacon_training_v2_merged.json"
DISTILLED_BEACON = TOOLS_DIR / "distilled_beacon.json"

LABEL2ID = {
    "first_person": 0,
    "third_person": 1,
    "third_person_omniscient": 2,
    "epistolary": 3,
}

# Books with mixed/alternating POVs — skip because book-level label is noisy
# Bleak House: alternates Esther (first-person) and omniscient chapters
# A Study in Scarlet: Watson (first) → Utah (third) → Watson
# Frankenstein: Walton letters (epistolary) → Victor (first) → Creature (first in quotes)
SKIP_BOOKS = {
    "bleak_house.txt",
    "a_study_in_scarlet.txt",
}

# Target samples per book (more for minority classes)
SAMPLES_PER_BOOK = {
    "first_person": 20,
    "third_person": 15,
    "third_person_omniscient": 20,
    "epistolary": 40,  # Boost minority class
}

PASSAGE_MIN_CHARS = 800
PASSAGE_MAX_CHARS = 1500
SEED = 42


def strip_gutenberg_metadata(text: str) -> str:
    """Remove Project Gutenberg preamble/postamble."""
    start_markers = [
        r'\*\*\* START OF (?:THE |THIS )?PROJECT GUTENBERG.*?\*\*\*',
    ]
    for marker in start_markers:
        m = re.search(marker, text, re.IGNORECASE | re.DOTALL)
        if m:
            text = text[m.end():]
            break

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


def looks_like_prose(passage: str) -> bool:
    """Filter out TOC, frontmatter, chapter lists."""
    lines = [l.strip() for l in passage.split('\n') if l.strip()]
    if len(lines) < 3:
        return False

    # If most lines are short (TOC-like), reject
    short_lines = sum(1 for l in lines if len(l) < 50)
    if short_lines > len(lines) * 0.7:
        return False

    # Too many chapter headings = TOC area
    chapter_count = len(re.findall(r'\b(?:CHAPTER|Chapter)\s+[IVXLCDM\d]+', passage))
    if chapter_count > 3:
        return False

    return True


def find_chapter_openings(text: str, num_samples: int) -> list[str]:
    """Find passages at chapter/section openings — strongest POV signal."""
    patterns = [
        r'\n\s*(?:CHAPTER|Chapter)\s+[IVXLCDM\d]+[.\s]*\n',
        r'\n\s*(?:LETTER|Letter)\s+[IVXLCDM\d]+[.\s]*\n',
        r'\n\s*(?:BOOK|Book|PART|Part)\s+[IVXLCDM\d]+[.\s]*\n',
    ]

    chapter_starts = []
    for pattern in patterns:
        for m in re.finditer(pattern, text):
            chapter_starts.append(m.end())

    chapter_starts.sort()

    # Dedupe (same position from different patterns)
    seen = set()
    passages = []
    for start in chapter_starts:
        bucket = start // 2000
        if bucket in seen:
            continue
        seen.add(bucket)

        end = min(start + PASSAGE_MAX_CHARS, len(text))
        passage = text[start:end].strip()

        if len(passage) < PASSAGE_MIN_CHARS:
            continue
        if not looks_like_prose(passage):
            continue

        passages.append(passage)

    return passages[:num_samples]


def find_random_passages(text: str, num_samples: int, rng: random.Random) -> list[str]:
    """Sample random passages from book body (fallback when no chapter markers)."""
    # Skip first 5% and last 2% to avoid front/back matter
    usable = text[len(text) // 20:int(len(text) * 0.98)]

    if len(usable) < PASSAGE_MIN_CHARS * 2:
        return []

    passages = []
    attempts = 0
    seen_buckets = set()

    while len(passages) < num_samples and attempts < num_samples * 6:
        attempts += 1
        target = rng.randint(0, len(usable) - PASSAGE_MAX_CHARS)
        bucket = target // (PASSAGE_MAX_CHARS // 2)
        if bucket in seen_buckets:
            continue
        seen_buckets.add(bucket)

        # Snap to paragraph boundary
        start = target
        for offset in range(min(200, PASSAGE_MAX_CHARS // 4)):
            if usable[target + offset:target + offset + 2] == "\n\n":
                start = target + offset + 2
                break

        end = min(start + rng.randint(PASSAGE_MIN_CHARS, PASSAGE_MAX_CHARS), len(usable))
        passage = usable[start:end].strip()

        if len(passage) < PASSAGE_MIN_CHARS // 2:
            continue
        if not looks_like_prose(passage):
            continue

        passages.append(passage)

    return passages


def find_epistolary_passages(text: str, num_samples: int) -> list[str]:
    """Find passages containing letter/diary markers for epistolary books."""
    markers = [
        r'(?:LETTER|Letter)\s+[IVXLCDM\d]+',
        r'_[A-Z][a-z]+ \d+[a-z]*[,.]',  # Dates like "_May 3,_"
        r'My dear \w+[,.]',
        r'Dear \w+[,.]',
        r'[A-Z][a-z]+\'s (?:Journal|Diary)',
        r'(?:Journal|Diary) entry',
        r'entry \d+',
        r'(?:St|Mr)\. Petersburg',  # Letter datelines
    ]

    passages = []
    seen_buckets = set()

    for pattern in markers:
        for m in re.finditer(pattern, text):
            pos = m.start()
            bucket = pos // 2500
            if bucket in seen_buckets:
                continue
            seen_buckets.add(bucket)

            start = max(0, pos - 100)
            end = min(len(text), pos + PASSAGE_MAX_CHARS - 100)
            passage = text[start:end].strip()

            if len(passage) < PASSAGE_MIN_CHARS:
                continue
            if looks_like_prose(passage):
                passages.append(passage)

            if len(passages) >= num_samples:
                return passages

    return passages


def distill_book(
    filepath: Path,
    meta: dict,
    rng: random.Random,
) -> list[dict]:
    title = meta["title"]
    author = meta.get("author", "Unknown")
    pov = meta.get("expected_pov")

    if pov not in LABEL2ID:
        return []

    target_samples = SAMPLES_PER_BOOK.get(pov, 15)
    label_id = LABEL2ID[pov]

    try:
        text = filepath.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        logger.error(f"  Failed to read {filepath}: {e}")
        return []

    text = strip_gutenberg_metadata(text)

    # Strategy depends on POV type
    if pov == "epistolary":
        # For epistolary, find passages near letter/diary markers
        passages = find_epistolary_passages(text, target_samples)
        # Supplement with chapter openings if under target
        if len(passages) < target_samples:
            extra = find_chapter_openings(text, target_samples - len(passages))
            passages.extend(extra)
    else:
        # For other POVs, prefer chapter openings (strong signal)
        # then fall back to random sampling
        passages = find_chapter_openings(text, target_samples)
        if len(passages) < target_samples // 2:
            random_passages = find_random_passages(
                text, target_samples - len(passages), rng,
            )
            passages.extend(random_passages)

    examples = []
    for passage in passages:
        examples.append({
            "text": passage,
            "label": label_id,
            "label_name": pov,
            "book": title,
            "author": author,
            "source": "corpus_targeted_v2",
            "confidence": 1.0,
        })

    return examples


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--merge", action="store_true",
                        help="Merge with existing distilled_beacon.json")
    args = parser.parse_args()

    if not CORPUS_META.exists():
        logger.error(f"Corpus metadata not found: {CORPUS_META}")
        sys.exit(1)

    with open(CORPUS_META) as f:
        corpus_meta = json.load(f)

    rng = random.Random(SEED)
    all_examples = []
    book_count = 0
    skipped = 0

    from collections import Counter
    pov_counts = Counter()

    for filename, meta in sorted(corpus_meta.items()):
        if filename in SKIP_BOOKS:
            logger.info(f"SKIP (mixed POV): {meta['title']}")
            skipped += 1
            continue

        filepath = CORPUS_DIR / filename
        if not filepath.exists():
            continue

        examples = distill_book(filepath, meta, rng)
        if examples:
            all_examples.extend(examples)
            book_count += 1
            pov_counts[meta["expected_pov"]] += len(examples)

    logger.info(f"\n=== Summary ===")
    logger.info(f"Books processed: {book_count} (skipped {skipped})")
    logger.info(f"Total examples: {len(all_examples)}")
    logger.info(f"POV distribution:")
    for pov, count in sorted(pov_counts.items(), key=lambda x: -x[1]):
        pct = count / len(all_examples) * 100
        logger.info(f"  {pov}: {count} ({pct:.1f}%)")

    with open(OUTPUT_NEW, "w") as f:
        json.dump(all_examples, f, indent=2, ensure_ascii=False)
    logger.info(f"\nSaved to {OUTPUT_NEW}")

    if args.merge:
        existing = []
        if DISTILLED_BEACON.exists():
            with open(DISTILLED_BEACON) as f:
                existing = json.load(f)
            logger.info(f"\nLoaded {len(existing)} existing examples")

        merged = existing + all_examples
        merged_counts = Counter()
        for ex in merged:
            merged_counts[ex.get("label_name", "unknown")] += 1
        logger.info(f"Merged total: {len(merged)}")
        for pov, count in sorted(merged_counts.items(), key=lambda x: -x[1]):
            pct = count / len(merged) * 100
            logger.info(f"  {pov}: {count} ({pct:.1f}%)")

        with open(OUTPUT_MERGED, "w") as f:
            json.dump(merged, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved merged dataset to {OUTPUT_MERGED}")


if __name__ == "__main__":
    main()
