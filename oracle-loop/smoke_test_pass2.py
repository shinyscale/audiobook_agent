#!/usr/bin/env python3
"""Smoke test for Pass 2 disambiguation label fix."""

import json

# Simulate Pass 1 output - two characters with disambiguation labels
pass1_characters = [
    {
        "canonical_name": "John Donaldson (the father)",
        "role": "protagonist",
        "description": "An aging man who served in WWI and committed a past crime"
    },
    {
        "canonical_name": "John Donaldson (the son)",
        "role": "supporting",
        "description": "A young boy taken in by Uncle Bill after his father's death"
    }
]

# Check if the prompt would prevent the LLM from merging these
from src.pipeline.character_extraction_v2.main_cast import CONSOLIDATED_ALIAS_PROMPT

character_list = "\n".join(
    f"- {c['canonical_name']} (role: {c['role']}, description: {c['description']})"
    for c in pass1_characters
)

test_prompt = CONSOLIDATED_ALIAS_PROMPT.format(
    character_list=character_list,
    summaries="Chapter 1: Uncle Bill receives a letter from John (the son).\nChapter 2: Uncle Bill learns about John Donaldson (the father)'s death and takes in the boy."
)

# Print key section of the prompt
print("=== CONSOLIDATED_ALIAS_PROMPT MERGE RULES ===")
merge_rules_start = test_prompt.find("## Merge Rules")
merge_rules_end = test_prompt.find("## Chapter Summaries")
merge_section = test_prompt[merge_rules_start:merge_rules_end].strip()
print(merge_section)
print()

# Check if disambiguation guidance is present
if "disambiguation labels in parentheses" in test_prompt.lower():
    print("✓ PASS: Disambiguation label guidance is present in prompt")
    print("✓ The prompt now explicitly tells the LLM NOT to merge father and son")
else:
    print("✗ FAIL: Disambiguation label guidance is missing")
    exit(1)

print("\n=== SMOKE TEST RESULT ===")
print("✓ Prompt fix applied successfully")
print("✓ Pass 2 should now preserve split siblings (father vs son)")
