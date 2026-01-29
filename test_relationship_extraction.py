"""
Test the relationship extraction fix for american_sir.

This script simulates the relationship extraction post-processing
to verify it would work correctly on the current data.
"""

import json
import re

def extract_relationships_from_evidence(evidence, all_character_names):
    """
    Simulate the extraction logic added to analyzer.py
    """
    relationships = {}
    
    rel_keywords = [
        "father", "mother", "son", "daughter",
        "uncle", "aunt", "nephew", "niece",
        "cousin", "brother", "sister",
        "husband", "wife", "spouse",
        "guardian", "ward"
    ]
    
    char_name_lower = {name.lower(): name for name in all_character_names}
    
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

print("Testing relationship extraction on american_sir\n")
print("="*60)

for char in data["characters"]:
    name = char["canonical_name"]
    evidence = char.get("evidence", [])
    current_rels = char.get("relationships", {})
    
    print(f"\n{name}:")
    print(f"  Current relationships: {current_rels}")
    
    # Simulate post-processing
    if not current_rels:
        extracted = extract_relationships_from_evidence(evidence, all_character_names)
        if extracted:
            print(f"  POST-PROCESSING would extract: {extracted}")
        else:
            print(f"  POST-PROCESSING would extract: (none)")
    else:
        print(f"  (already has relationships, no post-processing needed)")

print("\n" + "="*60)
print("\nExpected relationships for passing:")
print("  - John → Uncle Bill or John Donaldson (at least 1)")
print("  - Uncle Bill → John or John Donaldson (at least 1)")
print("  - John Donaldson → John (father)")
print("\nSummary: If 2-3 relationships are extracted, Profile score should improve to 8+/10")
