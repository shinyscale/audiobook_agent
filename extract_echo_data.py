"""
Extract training data for the Echo scalpel (character-in-chapter tagger).

For each book with an analysis.json:
1. Load the source text, strip Gutenberg headers
2. For each chapter, reconstruct text from offsets
3. For each character in the book's cast, check if they're mentioned in the chapter
4. Label: "active" if in characters_present, "mentioned" if name appears but not active
5. Extract ~500 char context around the most prominent mention
6. Output: echo_unified_dataset.json

Run on spark-987a where the data lives.
"""

import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path("/home/zacharymandrews/Tools/audiobook_agent")
OUTPUT_DIR = BASE / "output"
TEXT_DIR = BASE / "Test_Texts"

# Pick one canonical analysis per book (latest/best txt-based run)
CANONICAL_RUNS = {
    "dracula": "dracula",
    "frankenstein": "frankenstein",
    "gatsby": "gatsby",
    "monkeys_paw": "monkeys_paw",
    "american_sir": "american_sir",
    "berenice": "berenice",
    "cask_of_amontillado": "cask_of_amontillado",
    "gift_of_the_magi": "gift_of_the_magi",
    "masque_of_red_death": "masque_of_red_death",
    "john_g": "john_g",
    "a_camping_trip": "a_camping_trip",
    # Multiple oracle runs — pick latest good one
    "frankenstein_ebook": "Frankenstein_ebook_001",
    "gatsby_oracle": "gatsby_012",
    "see_the_light": "See the Light V-15 11-11-25_002",
    "east_of_eden": "East of Eden - East Of Eden_006",
    "i_have_no_mouth": "i_have_no_mouth",
}


def strip_gutenberg(text: str) -> str:
    """Strip Project Gutenberg header and footer."""
    start_markers = [
        "*** START OF THE PROJECT GUTENBERG EBOOK",
        "*** START OF THIS PROJECT GUTENBERG EBOOK",
        "***START OF THE PROJECT GUTENBERG EBOOK",
    ]
    end_markers = [
        "*** END OF THE PROJECT GUTENBERG EBOOK",
        "*** END OF THIS PROJECT GUTENBERG EBOOK",
        "***END OF THE PROJECT GUTENBERG EBOOK",
    ]

    for marker in start_markers:
        idx = text.find(marker)
        if idx != -1:
            # Find end of line after marker
            newline = text.find("\n", idx)
            if newline != -1:
                text = text[newline + 1:]
            break

    for marker in end_markers:
        idx = text.find(marker)
        if idx != -1:
            text = text[:idx]
            break

    return text.strip()


def load_source_text(analysis: dict) -> str | None:
    """Load and strip the source text for a book."""
    meta = analysis.get("metadata", {})
    source_file = meta.get("source_file", "")
    source_format = meta.get("source_format", "")

    if source_format != "txt":
        return None

    # Try relative to audiobook_agent dir
    path = BASE / source_file
    if not path.exists():
        path = TEXT_DIR / Path(source_file).name
    if not path.exists():
        print(f"  WARNING: source text not found: {source_file}")
        return None

    text = path.read_text(encoding="utf-8", errors="replace")
    return strip_gutenberg(text)


def get_character_names(analysis: dict) -> dict[str, list[str]]:
    """Extract canonical names and aliases for each character.
    Returns: {canonical_name: [canonical_name, alias1, alias2, ...]}
    """
    chars = analysis.get("characters", [])
    name_map = {}
    for c in chars:
        if isinstance(c, dict):
            canon = c.get("canonical_name", "")
            if not canon:
                continue
            aliases = c.get("aliases", [])
            all_names = [canon] + [a for a in aliases if a]
            name_map[canon] = all_names
        elif isinstance(c, str):
            name_map[c] = [c]
    return name_map


def find_mentions(text: str, names: list[str]) -> list[tuple[int, str]]:
    """Find all mentions of any name variant in text.
    Returns: [(position, matched_name), ...] sorted by position.
    """
    mentions = []
    text_lower = text.lower()
    for name in names:
        if len(name) < 2:
            continue
        # Use word boundary matching
        pattern = re.compile(r'\b' + re.escape(name) + r'\b', re.IGNORECASE)
        for m in pattern.finditer(text):
            mentions.append((m.start(), name))
    mentions.sort(key=lambda x: x[0])
    return mentions


def extract_context(text: str, position: int, context_chars: int = 500) -> str:
    """Extract context around a mention position."""
    half = context_chars // 2
    start = max(0, position - half)
    end = min(len(text), position + half)

    # Try to align to word boundaries
    if start > 0:
        space = text.rfind(" ", max(0, start - 20), start + 20)
        if space > 0:
            start = space + 1
    if end < len(text):
        space = text.find(" ", end - 10, end + 20)
        if space > 0:
            end = space

    return text[start:end].strip()


def process_book(run_name: str, book_key: str) -> list[dict]:
    """Process one book's analysis into training examples."""
    analysis_path = OUTPUT_DIR / run_name / "analysis.json"
    if not analysis_path.exists():
        print(f"  SKIP: {analysis_path} not found")
        return []

    analysis = json.load(open(analysis_path, encoding="utf-8"))

    # Load source text
    source_text = load_source_text(analysis)
    if source_text is None:
        print(f"  SKIP: no txt source for {run_name}")
        return []

    # Get character names
    char_names = get_character_names(analysis)
    if not char_names:
        print(f"  SKIP: no characters for {run_name}")
        return []

    chapters = analysis.get("structure", [])
    examples = []

    for ch in chapters:
        start = ch.get("start_position", 0)
        end = ch.get("end_position", 0)
        if end <= start:
            continue

        chapter_text = source_text[start:end]
        if len(chapter_text) < 50:
            continue

        ch_index = ch.get("index", 0)
        ch_title = ch.get("title", f"Chapter {ch_index}")
        characters_present = set(ch.get("characters_present", []))

        # Normalize characters_present for matching
        present_lower = {name.lower().strip() for name in characters_present}

        # For each character in the book's cast
        for canon_name, name_variants in char_names.items():
            # Find mentions in chapter text
            mentions = find_mentions(chapter_text, name_variants)
            if not mentions:
                continue  # Character not mentioned at all — skip

            # Determine label
            # Check if any variant of this character is in characters_present
            is_active = False
            for variant in name_variants:
                if variant.lower().strip() in present_lower:
                    is_active = True
                    break
            # Also check canonical name directly
            if canon_name in characters_present or canon_name.lower() in present_lower:
                is_active = True

            # Pick the most central mention for context extraction
            # (the one closest to the middle of the chapter)
            mid = len(chapter_text) // 2
            best_mention = min(mentions, key=lambda x: abs(x[0] - mid))
            context = extract_context(chapter_text, best_mention[0], context_chars=500)

            label = 1 if is_active else 0

            examples.append({
                "text": f"{canon_name} [SEP] {context}",
                "label": label,
                "character": canon_name,
                "matched_name": best_mention[1],
                "book": book_key,
                "chapter_index": ch_index,
                "chapter_title": str(ch_title),
                "num_mentions": len(mentions),
                "source": "audiobook_agent",
            })

    return examples


def main():
    all_examples = []

    for book_key, run_name in sorted(CANONICAL_RUNS.items()):
        print(f"Processing {book_key} ({run_name})...")
        examples = process_book(run_name, book_key)
        print(f"  → {len(examples)} examples")
        all_examples.extend(examples)

    # Stats
    print(f"\n{'=' * 60}")
    print(f"Total examples: {len(all_examples)}")
    labels = Counter(ex["label"] for ex in all_examples)
    print(f"  Active (1): {labels[1]}")
    print(f"  Mentioned (0): {labels[0]}")
    print(f"  Books: {len(set(ex['book'] for ex in all_examples))}")
    print(f"  Unique characters: {len(set(ex['character'] for ex in all_examples))}")

    # Per-book breakdown
    print(f"\nPer-book breakdown:")
    for book in sorted(set(ex["book"] for ex in all_examples)):
        book_ex = [ex for ex in all_examples if ex["book"] == book]
        book_active = sum(1 for ex in book_ex if ex["label"] == 1)
        book_mentioned = sum(1 for ex in book_ex if ex["label"] == 0)
        print(f"  {book}: {len(book_ex)} total ({book_active} active, {book_mentioned} mentioned)")

    # Save
    out_path = Path("/home/zacharymandrews/Tools/audiobook_agent/echo_unified_dataset.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_examples, f, indent=2, ensure_ascii=False)
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
