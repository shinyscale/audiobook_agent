"""
Test the relationship extraction fix for american_sir (v2 - with self-filter).
"""

import json
import re

def extract_relationships_from_evidence(evidence, all_character_names, current_character_name):
    """
    Simulate the extraction logic added to analyzer.py (with self-filter)
    """
    relationships = {}
    
    rel_keywords = [
        "father", "mother", "son", "daughter",
        "uncle", "aunt", "nephew", "niece",
        "cousin", "brother", "sister",
        "husband", "wife", "spouse",
        "guardian", "ward"
    ]
    
    # Filter out current character to avoid self-references
    char_name_lower = {name.lower(): name for name in all_character_names if name.lower() != current_character_name.lower()}
    
    for ev in evidence:
        statement = ev.get("statement", "").lower()
        
        for rel_type in rel_keywords:
            if rel_type not in statement:
                continue
            
            for char_lower, char_name in char_name_lower.items():
                if char_lower in statement:
                    
                    if re.search(rf"is\s+(?:the\s+)?{rel_type}", statement):
                        if char_name not in relationships:
                            relationships[char_name] = rel_type
                    
                    elif re.search(rf"{char_lower}\s+(?:is|was|has been)", statement):
                        if char_name not in relationships:
                            relationships[char_name] = rel_type
                    
                    elif re.search(rf"(?:his|her|their)\s+{rel_type}", statement) or re.search(rf"\w+'s\s+{rel_type}", statement):
                        if char_name not in relationships:
                            relationships[char_name] = rel_type
                    
                    elif re.search(rf"{rel_type}\s+(?:named|called)\s+{char_lower}", statement):
                        if char_name not in relationships:
                            relationships[char_name] = rel_type
    
    return relationships

# Load the analysis data
with open("output/american_sir/analysis.json") as f:
    data = json.load(f)

all_character_names = [c["canonical_name"] for c in data["characters"]]

print("Testing relationship extraction on american_sir (with self-filter)\n")
print("="*60)

total_extracted = 0
for char in data["characters"]:
    name = char["canonical_name"]
    evidence = char.get("evidence", [])
    current_rels = char.get("relationships", {})
    
    print(f"\n{name}:")
    print(f"  Current: {current_rels if current_rels else '(empty)'}")
    
    if not current_rels:
        extracted = extract_relationships_from_evidence(evidence, all_character_names, name)
        if extracted:
            print(f"  Will extract: {extracted}")
            total_extracted += len(extracted)
        else:
            print(f"  Will extract: (none)")

print("\n" + "="*60)
print(f"\nTotal relationships extracted: {total_extracted}")
print("\nProfile scoring impact:")
print("  - Baseline: 7/10 (all relationships empty)")
print(f"  - With fix: {total_extracted} relationships populated")
print("  - Expected: 8-9/10 (relationships present and accurate)")
