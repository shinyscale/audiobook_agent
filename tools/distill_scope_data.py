#!/usr/bin/env python3
"""
distill_scope_data.py — Generate training data for the Scope scalpel.

Extracts chapter-level narrator type labels from books with known narrative
structures. Uses structural markers (chapter headers, diary attributions,
letter salutations) to create ground-truth labels without LLM assistance.

Labels:
  0: single_narrator     — One narrator throughout (majority of books)
  1: frame_narrator      — Outer/frame narrator (Walton, Lockwood, etc.)
  2: inner_narrator      — Primary inner narrator (Victor, Nelly Dean, etc.)
  3: deep_narrator       — Deeply embedded narrator (Creature, etc.)
  4: omniscient_interlude — Third-person omniscient in mixed narrative

Usage:
    python tools/distill_scope_data.py
    python tools/distill_scope_data.py --train  # Also train the model

Output:
    tools/distilled_scope.json
"""

import argparse
import json
import logging
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
OUTPUT_FILE = TOOLS_DIR / "distilled_scope.json"

# Label IDs matching SCALPEL_REGISTRY
SINGLE_NARRATOR = 0
FRAME_NARRATOR = 1
INNER_NARRATOR = 2
DEEP_NARRATOR = 3
OMNISCIENT_INTERLUDE = 4

LABEL_NAMES = {
    0: "single_narrator",
    1: "frame_narrator",
    2: "inner_narrator",
    3: "deep_narrator",
    4: "omniscient_interlude",
}


# ── Nested Narrative Book Definitions ────────────────────────────────────────
# Each book defines rules for labeling chapters by narrator type.
# These are hand-crafted based on known literary structure.

def label_frankenstein(chapters: list[dict]) -> list[dict]:
    """Frankenstein: Walton (letters) → Victor (chapters 1-10, 17-24) → Creature (11-16)."""
    labeled = []
    for ch in chapters:
        title = ch["title"].strip()
        # Skip past chapter/letter header to actual text content
        # Find first paragraph after the header line
        lines = ch["text"].split('\n')
        body_lines = []
        past_header = False
        for line in lines:
            if past_header:
                body_lines.append(line)
            elif line.strip() == '':
                if any(body_lines):
                    pass  # already collecting
                continue
            elif re.match(r'(Letter|Chapter)\s+', line.strip()):
                past_header = True
            else:
                body_lines.append(line)
        text_body = '\n'.join(body_lines).lstrip()

        if re.match(r'Letter', title, re.IGNORECASE):
            label = FRAME_NARRATOR
            narrator = "Robert Walton"
        elif re.match(r'Chapter\s+(1[1-6]|XI|XII|XIII|XIV|XV|XVI)\b', title):
            # Creature's narrative (chapters 11-16)
            # Creature narrates in quotes — check text body after header
            if text_body.startswith('"') or text_body.startswith('\u201c'):
                label = DEEP_NARRATOR
                narrator = "the creature"
            else:
                label = INNER_NARRATOR
                narrator = "Victor Frankenstein"
        else:
            label = INNER_NARRATOR
            narrator = "Victor Frankenstein"

        labeled.append({
            "text": ch["text"][:2000],
            "label": label,
            "label_name": LABEL_NAMES[label],
            "narrator": narrator,
            "book": "Frankenstein",
            "chapter": title,
        })
    return labeled


def label_dracula(chapters: list[dict]) -> list[dict]:
    """Dracula: epistolary — narrator identified by diary/letter attribution in text."""
    narrator_patterns = [
        (r"jonathan harker.s journal", "Jonathan Harker", INNER_NARRATOR),
        (r"mina (murray|harker).s (journal|diary)", "Mina Harker", INNER_NARRATOR),
        (r"dr\.?\s*seward.s (diary|phonograph)", "Dr. Seward", INNER_NARRATOR),
        (r"lucy westenra.s diary", "Lucy Westenra", INNER_NARRATOR),
        (r"van helsing", "Van Helsing", INNER_NARRATOR),
        (r"letter,?\s+(mina|miss)", "Mina Harker", FRAME_NARRATOR),
        (r"letter,?\s+dr", "Dr. Seward", FRAME_NARRATOR),
        (r"cutting|telegram|newspaper|dailygraph", "document", OMNISCIENT_INTERLUDE),
    ]

    labeled = []
    for ch in chapters:
        # Search first 500 chars for diary/letter attribution
        header = ch["text"][:500]

        label = INNER_NARRATOR  # default
        narrator = "unknown"

        for pattern, name, lbl in narrator_patterns:
            if re.search(pattern, header, re.IGNORECASE):
                narrator = name
                label = lbl
                break

        labeled.append({
            "text": ch["text"][:2000],
            "label": label,
            "label_name": LABEL_NAMES[label],
            "narrator": narrator,
            "book": "Dracula",
            "chapter": ch["title"],
        })
    return labeled


def label_bleak_house(chapters: list[dict]) -> list[dict]:
    """Bleak House: alternating omniscient and Esther's first-person narrative."""
    # Esther's chapters have high first-person pronoun density and often
    # have "Esther's Narrative" in the title or open with "I"
    labeled = []
    for ch in chapters:
        title = ch["title"]
        text_start = ch["text"][:2000]

        # Count first-person pronouns in opening
        words = text_start.split()[:500]
        fp_count = sum(1 for w in words if w in ("I", "I,", "I."))
        fp_density = fp_count / max(len(words), 1)

        # Check title for "Esther" or "Narrative"
        is_esther = (
            "esther" in title.lower() or
            "narrative" in title.lower() or
            fp_density > 0.03  # Strong first-person signal
        )

        if is_esther:
            label = INNER_NARRATOR
            narrator = "Esther Summerson"
        else:
            label = OMNISCIENT_INTERLUDE
            narrator = "omniscient"

        labeled.append({
            "text": text_start,
            "label": label,
            "label_name": LABEL_NAMES[label],
            "narrator": narrator,
            "book": "Bleak House",
            "chapter": title,
        })
    return labeled


def label_wuthering_heights(chapters: list[dict]) -> list[dict]:
    """Wuthering Heights: Lockwood (1-3, 32-34) frames Nelly's narration."""
    labeled = []
    for i, ch in enumerate(chapters):
        ch_num = i + 1
        if ch_num <= 3 or ch_num >= 32:
            label = FRAME_NARRATOR
            narrator = "Lockwood"
        else:
            label = INNER_NARRATOR
            narrator = "Nelly Dean"

        labeled.append({
            "text": ch["text"][:2000],
            "label": label,
            "label_name": LABEL_NAMES[label],
            "narrator": narrator,
            "book": "Wuthering Heights",
            "chapter": ch["title"],
        })
    return labeled


def label_study_in_scarlet(chapters: list[dict]) -> list[dict]:
    """A Study in Scarlet: Watson Part I → third-person Utah Part II → Watson conclusion."""
    labeled = []
    in_part2 = False
    for ch in chapters:
        title = ch["text"][:500]

        if "COUNTRY OF THE SAINTS" in title or "ALKALI PLAIN" in title.upper():
            in_part2 = True
        if "CONTINUATION OF THE REMINISCENCES" in title.upper():
            in_part2 = False

        if in_part2:
            label = OMNISCIENT_INTERLUDE
            narrator = "omniscient"
        else:
            label = INNER_NARRATOR
            narrator = "Dr. Watson"

        labeled.append({
            "text": ch["text"][:2000],
            "label": label,
            "label_name": LABEL_NAMES[label],
            "narrator": narrator,
            "book": "A Study in Scarlet",
            "chapter": ch["title"],
        })
    return labeled


def label_heart_of_darkness(text: str) -> list[dict]:
    """Heart of Darkness: frame narrator → Marlow. Split into synthetic sections."""
    # The book has no chapter markers, so we split by paragraph groups
    # Frame narrator is ~first 2000 chars, then Marlow takes over
    examples = []

    # Frame narrator opening
    examples.append({
        "text": text[:2000],
        "label": FRAME_NARRATOR,
        "label_name": LABEL_NAMES[FRAME_NARRATOR],
        "narrator": "unnamed frame narrator",
        "book": "Heart of Darkness",
        "chapter": "Opening",
    })

    # Marlow's narrative (bulk of text)
    marlow_start = text.find("Marlow")
    if marlow_start > 0:
        for offset in range(marlow_start, len(text) - 2000, 10000):
            examples.append({
                "text": text[offset:offset + 2000],
                "label": INNER_NARRATOR,
                "label_name": LABEL_NAMES[INNER_NARRATOR],
                "narrator": "Marlow",
                "book": "Heart of Darkness",
                "chapter": f"Section at {offset}",
            })

    return examples


def label_turn_of_the_screw(text: str) -> list[dict]:
    """Turn of the Screw: frame → governess manuscript."""
    examples = []

    # Prologue (frame narrator)
    examples.append({
        "text": text[:2000],
        "label": FRAME_NARRATOR,
        "label_name": LABEL_NAMES[FRAME_NARRATOR],
        "narrator": "frame narrator",
        "book": "The Turn of the Screw",
        "chapter": "Prologue",
    })

    # Governess narrative (bulk)
    for offset in range(5000, len(text) - 2000, 8000):
        examples.append({
            "text": text[offset:offset + 2000],
            "label": INNER_NARRATOR,
            "label_name": LABEL_NAMES[INNER_NARRATOR],
            "narrator": "the governess",
            "book": "The Turn of the Screw",
            "chapter": f"Section at {offset}",
        })

    return examples


# ── Chapter Splitting ────────────────────────────────────────────────────────

def split_chapters(text: str) -> list[dict]:
    """Split text into chapters by common header patterns."""
    patterns = [
        r'\n\s*((?:LETTER|Letter)\s+[IVXLCDM\d]+[.\s]*)',
        r'\n\s*((?:CHAPTER|Chapter)\s+[IVXLCDM\d]+[.\s]*)',
    ]

    all_matches = []
    for pattern in patterns:
        for m in re.finditer(pattern, text):
            all_matches.append(m)

    # Sort by position
    all_matches.sort(key=lambda m: m.start())

    if len(all_matches) < 2:
        return []

    # Deduplicate TOC entries (very short sections = TOC line)
    chapters = []
    for i, m in enumerate(all_matches):
        end = all_matches[i + 1].start() if i + 1 < len(all_matches) else len(text)
        section_text = text[m.start():end]
        if len(section_text) > 500:  # Skip TOC entries
            chapters.append({
                "title": m.group(1).strip(),
                "text": section_text,
            })

    return chapters


# ── Single-Narrator Books (Negative Examples) ───────────────────────────────

def label_single_narrator_book(text: str, title: str, pov: str) -> list[dict]:
    """Generate single_narrator examples from a non-nested book.

    These are crucial negative examples — the classifier needs to know what
    "normal" chapters look like so it doesn't hallucinate narrator transitions.
    """
    chapters = split_chapters(text)
    if not chapters:
        # No chapter markers — sample at regular intervals
        examples = []
        for offset in range(0, min(len(text), 100000), 10000):
            examples.append({
                "text": text[offset:offset + 2000],
                "label": SINGLE_NARRATOR,
                "label_name": LABEL_NAMES[SINGLE_NARRATOR],
                "narrator": "single",
                "book": title,
                "chapter": f"Section at {offset}",
            })
        return examples

    labeled = []
    for ch in chapters[:20]:  # Cap per book to avoid imbalance
        labeled.append({
            "text": ch["text"][:2000],
            "label": SINGLE_NARRATOR,
            "label_name": LABEL_NAMES[SINGLE_NARRATOR],
            "narrator": "single",
            "book": title,
            "chapter": ch["title"],
        })
    return labeled


# ── Main Pipeline ────────────────────────────────────────────────────────────

NESTED_LABELERS = {
    "frankenstein.txt": ("Frankenstein", label_frankenstein),
    "dracula.txt": ("Dracula", label_dracula),
    "bleak_house.txt": ("Bleak House", label_bleak_house),
    "wuthering_heights.txt": ("Wuthering Heights", label_wuthering_heights),
    "a_study_in_scarlet.txt": ("A Study in Scarlet", label_study_in_scarlet),
}

# Books that need full-text (no chapter markers)
FULLTEXT_LABELERS = {
    "heart_of_darkness.txt": ("Heart of Darkness", label_heart_of_darkness),
    "the_turn_of_the_screw.txt": ("The Turn of the Screw", label_turn_of_the_screw),
}


def main():
    parser = argparse.ArgumentParser(description="Generate scope scalpel training data")
    parser.add_argument("--train", action="store_true", help="Also train the model")
    args = parser.parse_args()

    if not CORPUS_META.exists():
        logger.error(f"Corpus metadata not found: {CORPUS_META}")
        sys.exit(1)

    with open(CORPUS_META) as f:
        corpus_meta = json.load(f)

    all_examples = []

    # 1. Process nested-narrative books (ground truth from structure)
    logger.info("=== Processing nested-narrative books ===")
    for filename, (book_title, labeler) in NESTED_LABELERS.items():
        filepath = CORPUS_DIR / filename
        if not filepath.exists():
            logger.warning(f"Missing: {filepath}")
            continue

        text = filepath.read_text(encoding="utf-8", errors="replace")
        chapters = split_chapters(text)
        if not chapters:
            logger.warning(f"No chapters found in {filename}")
            continue

        labeled = labeler(chapters)
        all_examples.extend(labeled)

        # Count by label
        counts = {}
        for ex in labeled:
            lname = ex["label_name"]
            counts[lname] = counts.get(lname, 0) + 1
        logger.info(f"  {book_title}: {len(labeled)} chapters — {counts}")

    # 2. Process full-text books (no chapter markers)
    logger.info("\n=== Processing full-text nested books ===")
    for filename, (book_title, labeler) in FULLTEXT_LABELERS.items():
        filepath = CORPUS_DIR / filename
        if not filepath.exists():
            logger.warning(f"Missing: {filepath}")
            continue

        text = filepath.read_text(encoding="utf-8", errors="replace")
        labeled = labeler(text)
        all_examples.extend(labeled)
        logger.info(f"  {book_title}: {len(labeled)} sections")

    # 3. Process single-narrator books (negative examples)
    logger.info("\n=== Processing single-narrator books (negative examples) ===")
    single_count = 0
    # We want roughly balanced classes, so limit single-narrator examples
    # to ~2x the nested examples
    nested_count = len(all_examples)
    max_single = nested_count * 2

    for filename, meta in sorted(corpus_meta.items()):
        if filename in NESTED_LABELERS or filename in FULLTEXT_LABELERS:
            continue
        if single_count >= max_single:
            break

        filepath = CORPUS_DIR / filename
        if not filepath.exists():
            continue

        text = filepath.read_text(encoding="utf-8", errors="replace")
        pov = meta.get("expected_pov", "third_person")
        labeled = label_single_narrator_book(text, meta["title"], pov)

        all_examples.extend(labeled)
        single_count += len(labeled)
        logger.info(f"  {meta['title']}: {len(labeled)} chapters (single_narrator)")

    # Summary
    logger.info(f"\n=== Summary ===")
    total_by_label = {}
    for ex in all_examples:
        lname = ex["label_name"]
        total_by_label[lname] = total_by_label.get(lname, 0) + 1

    logger.info(f"Total examples: {len(all_examples)}")
    for label_name, count in sorted(total_by_label.items()):
        pct = count / len(all_examples) * 100
        logger.info(f"  {label_name}: {count} ({pct:.1f}%)")

    books = set(ex["book"] for ex in all_examples)
    logger.info(f"Books represented: {len(books)}")

    # Save
    with open(OUTPUT_FILE, "w") as f:
        json.dump(all_examples, f, indent=2, ensure_ascii=False)
    logger.info(f"\nSaved to {OUTPUT_FILE}")

    if args.train:
        logger.info("\n=== Training scope model ===")
        logger.info("(Training is done via autoresearch on zandrews-114)")
        logger.info(f"SCP {OUTPUT_FILE} to zandrews-114, then run autoresearch loop")


if __name__ == "__main__":
    main()
