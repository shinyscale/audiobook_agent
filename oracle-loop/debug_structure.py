#!/usr/bin/env python3
"""Quick diagnostic to see what chapter detection is finding."""

import sys
sys.path.insert(0, "/home/zacharymandrews/Tools/audiobook_agent/src")

from pipeline.chapter_detection.profiler import DocumentProfiler

# Load text directly
with open("/home/zacharymandrews/Tools/audiobook_agent/Test_Texts/gatsby.txt", "r", encoding="utf-8") as f:
    text = f.read()

# Profile it
profiler = DocumentProfiler(llm_client=None)
profile = profiler.profile(text)

print("=" * 80)
print("DOCUMENT PROFILE")
print("=" * 80)
print(f"Total length: {len(text)} chars")
print(f"Front matter end: {profile.front_matter_end}")
print(f"Back matter start: {profile.back_matter_start}")
print()

if profile.table_of_contents:
    print("TABLE OF CONTENTS")
    print(f"  Position: {profile.table_of_contents.toc_start_position} - {profile.table_of_contents.toc_end_position}")
    print(f"  Confidence: {profile.table_of_contents.confidence}")
    print(f"  Entries ({len(profile.table_of_contents.entries)}):")
    for entry in profile.table_of_contents.entries:
        print(f"    - '{entry.title}' (position: {entry.position_in_toc})")
else:
    print("No TOC found")

print()
print("=" * 80)
print("CHECKING ACTUAL CHAPTER MARKERS IN TEXT")
print("=" * 80)

import re
# Find centered Roman numerals (the actual chapter markers)
for match in re.finditer(r'^\s{20,}([IVXLCDM]+)\s*$', text[:100000], re.MULTILINE):
    pos = match.start()
    numeral = match.group(1)
    context_start = max(0, pos - 100)
    context_end = min(len(text), pos + 200)
    context = text[context_start:context_end].replace('\n', '\\n')
    print(f"Position {pos}: '{numeral}'")
    print(f"  Context: ...{context}...")
    print()
