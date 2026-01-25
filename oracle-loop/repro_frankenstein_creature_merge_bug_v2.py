#!/usr/bin/env python3
"""
Deterministic repro for the Frankenstein creature/De Lacey merge bug mechanics.

This does NOT call any LLMs. It exercises the v2 post-processing helpers directly:
- _split_semantic_conflicts() creates split_* stubs (current behavior)
- MentionSearcher can then ground the split stubs
- _merge_within_main_cast() pass4 can merge descriptive synonyms (creature/monster/etc.)
"""

import sys

# Ensure package imports work (repo root contains the `src/` package)
sys.path.insert(0, "/home/zacharymandrews/Tools/audiobook_agent")

from src.agents.characters import CharacterAgent
from src.models import Character
from src.pipeline.character_extraction_v2.mention_search import MentionSearcher


def _focus_dump(chars: list[Character]) -> list[tuple[str, list[str], int, str]]:
    out = []
    for c in chars:
        blob = (c.canonical_name + " " + " ".join(c.aliases)).lower()
        if any(k in blob for k in ("creature", "monster", "fiend", "daemon", "wretch", "being", "lacey", "old man")):
            out.append((c.canonical_name, list(c.aliases), int(c.mention_count or 0), c.id))
    return out


def main() -> int:
    text_path = "/home/zacharymandrews/Tools/audiobook_agent/Test_Texts/Frankenstein_ebook.txt"
    with open(text_path, "r", encoding="utf-8", errors="ignore") as f:
        full_text = f.read()

    agent = CharacterAgent(llm_client=None)

    # Minimal main_cast fixture matching the broken output pattern.
    main_cast = [
        Character(
            id="main_old_man",
            canonical_name="the old man (De Lacey)",
            aliases=["the old man", "the creature"],
            role="supporting",
            mention_count=34,
            confidence="medium",
        ),
        Character(
            id="main_monster",
            canonical_name="the monster",
            aliases=[],
            role="supporting",
            mention_count=3,
            confidence="medium",
        ),
        Character(
            id="main_creature_implied",
            canonical_name="the creature (implied)",
            aliases=[],
            role="supporting",
            mention_count=1,
            confidence="medium",
        ),
        Character(
            id="main_creature_bare",
            canonical_name="creature",
            aliases=[],
            role="supporting",
            mention_count=1,
            confidence="medium",
        ),
    ]

    print("=== BEFORE semantic split (focused) ===")
    for row in _focus_dump(main_cast):
        print(row)

    main_cast_after_split, split_count = agent._split_semantic_conflicts(main_cast)
    print(f"\n=== AFTER semantic split (split_count={split_count}) (focused) ===")
    for row in _focus_dump(main_cast_after_split):
        print(row)

    # Show the orphan-creation mechanism: split_* stubs start with 0 mentions.
    split_stubs = [c for c in main_cast_after_split if c.id.startswith("split_")]
    print(f"\nSplit stubs: {len(split_stubs)}")
    for c in split_stubs:
        print((c.canonical_name, c.aliases, c.mention_count, c.id))

    # Ground split stubs and then merge descriptive synonyms within main cast.
    searcher = MentionSearcher(full_text, chapters=None)
    for c in split_stubs:
        r = searcher.search_character(c)
        c.mention_count = r.total_mentions
        c.mentions = r.mentions

    merged, aliases_added = agent._merge_within_main_cast(main_cast_after_split)
    # Mirror the real pipeline behavior: after aliases are added, re-search mentions.
    for char_id in aliases_added:
        c = next((x for x in merged if x.id == char_id), None)
        if c:
            r = searcher.search_character(c)
            c.mention_count = r.total_mentions
            c.mentions = r.mentions
    print(f"\n=== AFTER grounding split stubs + within-main merge (aliases_added={len(aliases_added)}) (focused) ===")
    for row in _focus_dump(merged):
        print(row)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

