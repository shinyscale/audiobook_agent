#!/usr/bin/env python3
"""
Smoke test for Step 1.6 same-name character split.
Tests if the father/son John Donaldson split works correctly.
"""

import sys
sys.path.insert(0, "/home/zacharymandrews/Tools/audiobook_agent")

from src.agents.characters import CharacterAgent
from src.models import Character
from src.pipeline.chapter_summary.models import ChapterSummary

# Mock chapter summaries with disambiguated character references
summaries = [
    ChapterSummary(
        chapter_index=0,
        chapter_title="Section 1",
        summary="Uncle Bill receives a letter from young John Donaldson.",
        key_events=["Letter received"],
        primary_tone="reflective",
        secondary_tones=[],
        dialogue_density="medium",
        active_characters=["Uncle Bill", "John Donaldson (the son)"],
        mentioned_characters=[],
        pov_character="Uncle Bill",
        word_count=2500,
        estimated_duration_minutes=10.0,
        confidence=0.9
    ),
    ChapterSummary(
        chapter_index=1,
        chapter_title="Section 2",
        summary="Uncle Bill meets John Donaldson (the father) on the battlefield. John Donaldson (the son) drives the ambulance.",
        key_events=["Meeting on battlefield"],
        primary_tone="dramatic",
        secondary_tones=[],
        dialogue_density="high",
        active_characters=["Uncle Bill", "John Donaldson (the son)", "John Donaldson (the father)"],
        mentioned_characters=[],
        pov_character="Uncle Bill",
        word_count=3000,
        estimated_duration_minutes=12.0,
        confidence=0.9
    )
]

# Mock characters extracted by main cast (conflated into one)
characters = [
    Character(
        id="main_cast_0",
        canonical_name="Uncle Bill",
        role="protagonist",
        aliases=[],
        mention_count=10,
        first_appearance_chapter=0
    ),
    Character(
        id="main_cast_1",
        canonical_name="John Donaldson",  # Conflated father & son
        role="supporting",
        aliases=["the father"],  # Misleading - applies to conflated entry
        mention_count=8,
        first_appearance_chapter=0
    )
]

# Create agent instance
agent = CharacterAgent()

# Test the split method directly
print("=" * 60)
print("SMOKE TEST: Step 1.6 Same-Name Character Split")
print("=" * 60)
print(f"\nInput: {len(characters)} characters")
for char in characters:
    print(f"  - {char.canonical_name} (id={char.id}, aliases={char.aliases})")

print(f"\nSummary data:")
for i, summ in enumerate(summaries):
    print(f"  Section {i}: {summ.active_characters}")

print("\nRunning _split_disambiguated_same_name_characters()...")
result = agent._split_disambiguated_same_name_characters(characters, summaries)

print(f"\nOutput: {len(result)} characters")
for char in result:
    print(f"  - {char.canonical_name} (id={char.id}, aliases={char.aliases})")

# Verification
print("\n" + "=" * 60)
if len(result) == 3:  # Uncle Bill + 2 John Donaldsons
    john_chars = [c for c in result if "John Donaldson" in c.canonical_name]
    if len(john_chars) == 2:
        names = {c.canonical_name for c in john_chars}
        if "John Donaldson (the father)" in names and "John Donaldson (the son)" in names:
            print("✅ PASS: Father and son correctly split into 2 characters")
            sys.exit(0)
        else:
            print(f"❌ FAIL: John Donaldson split but labels wrong: {names}")
            sys.exit(1)
    else:
        print(f"❌ FAIL: Expected 2 John Donaldsons, got {len(john_chars)}")
        sys.exit(1)
else:
    print(f"❌ FAIL: Expected 3 total characters, got {len(result)}")
    sys.exit(1)
