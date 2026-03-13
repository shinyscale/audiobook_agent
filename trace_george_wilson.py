#!/usr/bin/env python3
"""Simulate F6 processing for George Wilson with actual Gatsby data."""
import json, re

with open("output/gatsby/analysis.json") as f:
    data = json.load(f)

characters = data["characters"]

# 1. Check existing_names
existing_names = set()
for char in characters:
    cn = char["canonical_name"]
    existing_names.add(cn.lower())
    for alias in char.get("aliases", []):
        existing_names.add(alias.lower())

name = "George Wilson"
print(f"1. Is '{name.lower()}' in existing_names? {name.lower() in existing_names}")

# 2. Check summary chars
summary_chars = set()
for ch in data.get("structure", []):
    for cp in ch.get("characters_present", []):
        summary_chars.add(cp.strip())
print(f"2. Is '{name}' in summary characters? {name in summary_chars}")
wilson_chars = [c for c in summary_chars if "wilson" in c.lower()]
print(f"   All Wilson-related: {wilson_chars}")

# 3. Trace _is_likely_alias_of_existing
print(f"\n3. Tracing _is_likely_alias_of_existing('{name}'):")
clean_lower = name.lower().strip()
name_parts = clean_lower.split()
first_name = name_parts[0]
last_name = name_parts[-1]

blocked = False
for i, char in enumerate(characters):
    char_canonical = char["canonical_name"].lower().strip()

    if clean_lower == char_canonical:
        print(f"   BLOCKED by exact match: {char['canonical_name']}")
        blocked = True; break

    if len(name_parts) >= 2:
        if first_name == char_canonical and len(char_canonical.split()) > 1:
            print(f"   BLOCKED by first-name match: {char['canonical_name']}")
            blocked = True; break

        if last_name == char_canonical and len(char_canonical.split()) > 1:
            print(f"   BLOCKED by last-name match: {char['canonical_name']}")
            blocked = True; break

        char_name_parts = char_canonical.split()
        if (len(char_name_parts) >= 2
            and first_name == char_name_parts[0]
            and last_name != char_name_parts[-1]):
            print(f"   BLOCKED by maiden-name check: {char['canonical_name']}")
            blocked = True; break

if not blocked:
    print("   Passed all in-loop checks")
    # Post-loop checks use stale char
    last_char = characters[-1]
    print(f"   Stale char (last): {last_char['canonical_name']} aliases={last_char.get('aliases',[])}")

    stopwords = {"the", "a", "an", "this", "that", "these", "those", "my", "your", "his", "her", "their", "our"}
    adjectives = {"old", "young", "mysterious", "masked", "red", "black", "white", "great", "little", "big", "small"}
    core_words = set(clean_lower.split()) - stopwords - adjectives

    alias_blocked = False
    for alias in last_char.get("aliases", []):
        alias_lower = alias.lower().strip()
        alias_core = set(alias_lower.split()) - stopwords - adjectives
        if alias_core and alias_core.issubset(core_words):
            print(f"   BLOCKED by alias core-word: '{alias}' core={alias_core} in {core_words}")
            alias_blocked = True; break

    if not alias_blocked:
        print("   -> Function returns FALSE (George Wilson ALLOWED)")

# 4. F6c check
print(f"\n4. F6c safety-net check:")
_f6c_canonical_words = set()
for char in characters:
    cn = char["canonical_name"].lower().strip()
    for w in cn.split():
        w = w.strip(".,;:'\"()")
        if len(w) > 3:
            _f6c_canonical_words.add(w)

_f6c_cand_words = set()
for w in name.split():
    w2 = w.strip(".,;:'\"()").lower()
    if len(w2) > 3:
        _f6c_cand_words.add(w2)

overlap = _f6c_cand_words & _f6c_canonical_words
print(f"   Candidate words: {_f6c_cand_words}")
print(f"   Canonical words: {sorted(_f6c_canonical_words)}")
print(f"   Overlap: {overlap}")
if overlap:
    print(f"   -> F6c SKIPS George Wilson!")
else:
    print(f"   -> F6c would ALLOW George Wilson")

# 5. Also check existing_aliases for F6c
_f6c_existing_aliases = set()
for char in characters:
    for alias in char.get("aliases", []):
        _f6c_existing_aliases.add(alias.lower().strip())
print(f"\n5. Is '{name.lower()}' in F6c existing aliases? {name.lower() in _f6c_existing_aliases}")
print(f"   Wilson-related aliases: {[a for a in _f6c_existing_aliases if 'wilson' in a]}")
