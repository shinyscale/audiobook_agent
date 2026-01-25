#!/usr/bin/env python3
"""
Compare character extraction results between V1 and V2 implementations.

This script helps validate the migration from V1 to V2 by comparing:
- Character counts
- Character names and aliases
- Quality metrics between versions
"""

import json
import sys
from pathlib import Path
from typing import Dict, Set, List, Tuple
from collections import defaultdict


def load_analysis_result(file_path: Path) -> dict:
    """Load an analysis result JSON file."""
    with open(file_path, 'r') as f:
        return json.load(f)


def extract_characters(result: dict) -> Dict[str, Set[str]]:
    """Extract character names and their aliases from analysis result."""
    characters = {}
    
    if 'characters' in result:
        for char in result['characters']:
            name = char.get('name', '')
            if name:
                # Use frozenset to handle aliases consistently
                aliases = set(char.get('aliases', []))
                aliases.add(name)  # Include the main name in aliases
                characters[name] = aliases
    
    return characters


def find_character_matches(chars_v1: Dict[str, Set[str]], chars_v2: Dict[str, Set[str]]) -> Tuple[Dict[str, str], Set[str], Set[str]]:
    """
    Find matching characters between V1 and V2 based on name/alias overlap.
    
    Returns:
        - matched: Dict mapping V1 names to V2 names
        - v1_only: Set of V1 character names with no match in V2
        - v2_only: Set of V2 character names with no match in V1
    """
    matched = {}
    v1_matched = set()
    v2_matched = set()
    
    # Try to match characters based on alias overlap
    for v1_name, v1_aliases in chars_v1.items():
        best_match = None
        best_overlap = 0
        
        for v2_name, v2_aliases in chars_v2.items():
            if v2_name in v2_matched:
                continue
                
            overlap = len(v1_aliases & v2_aliases)
            if overlap > best_overlap:
                best_match = v2_name
                best_overlap = overlap
        
        if best_match and best_overlap > 0:
            matched[v1_name] = best_match
            v1_matched.add(v1_name)
            v2_matched.add(best_match)
    
    v1_only = set(chars_v1.keys()) - v1_matched
    v2_only = set(chars_v2.keys()) - v2_matched
    
    return matched, v1_only, v2_only


def compare_aliases(chars_v1: Dict[str, Set[str]], chars_v2: Dict[str, Set[str]], matched: Dict[str, str]) -> Dict[str, Dict[str, Set[str]]]:
    """Compare aliases for matched characters."""
    alias_comparison = {}
    
    for v1_name, v2_name in matched.items():
        v1_aliases = chars_v1[v1_name]
        v2_aliases = chars_v2[v2_name]
        
        alias_comparison[v1_name] = {
            'v1_only': v1_aliases - v2_aliases,
            'v2_only': v2_aliases - v1_aliases,
            'common': v1_aliases & v2_aliases
        }
    
    return alias_comparison


def print_comparison(chars_v1: Dict[str, Set[str]], chars_v2: Dict[str, Set[str]], 
                    matched: Dict[str, str], v1_only: Set[str], v2_only: Set[str],
                    alias_comparison: Dict[str, Dict[str, Set[str]]]):
    """Print detailed comparison results."""
    
    print("=" * 80)
    print("CHARACTER EXTRACTION COMPARISON: V1 vs V2")
    print("=" * 80)
    print()
    
    # Summary stats
    print(f"Total characters in V1: {len(chars_v1)}")
    print(f"Total characters in V2: {len(chars_v2)}")
    print(f"Matched characters: {len(matched)}")
    print(f"V1-only characters: {len(v1_only)}")
    print(f"V2-only characters: {len(v2_only)}")
    print()
    
    # Matched characters with alias comparison
    if matched:
        print("-" * 40)
        print("MATCHED CHARACTERS")
        print("-" * 40)
        
        for v1_name in sorted(matched.keys()):
            v2_name = matched[v1_name]
            alias_comp = alias_comparison[v1_name]
            
            print(f"\n{v1_name} ↔ {v2_name}")
            
            if alias_comp['common']:
                print(f"  Common aliases: {sorted(alias_comp['common'])}")
            
            if alias_comp['v1_only']:
                print(f"  V1-only aliases: {sorted(alias_comp['v1_only'])}")
                
            if alias_comp['v2_only']:
                print(f"  V2-only aliases: {sorted(alias_comp['v2_only'])}")
    
    # V1-only characters
    if v1_only:
        print("\n" + "-" * 40)
        print("V1-ONLY CHARACTERS (missing in V2)")
        print("-" * 40)
        
        for name in sorted(v1_only):
            aliases = sorted(chars_v1[name] - {name})  # Exclude the main name
            if aliases:
                print(f"  • {name} (aliases: {', '.join(aliases)})")
            else:
                print(f"  • {name}")
    
    # V2-only characters
    if v2_only:
        print("\n" + "-" * 40)
        print("V2-ONLY CHARACTERS (new in V2)")
        print("-" * 40)
        
        for name in sorted(v2_only):
            aliases = sorted(chars_v2[name] - {name})  # Exclude the main name
            if aliases:
                print(f"  • {name} (aliases: {', '.join(aliases)})")
            else:
                print(f"  • {name}")
    
    # Quality metrics
    print("\n" + "=" * 40)
    print("QUALITY METRICS")
    print("=" * 40)
    
    # Calculate match percentage
    total_unique = len(set(chars_v1.keys()) | set(chars_v2.keys()))
    if total_unique > 0:
        match_rate = len(matched) / total_unique * 100
        print(f"Character match rate: {match_rate:.1f}%")
    
    # Calculate alias coverage
    total_v1_aliases = sum(len(aliases) for aliases in chars_v1.values())
    total_v2_aliases = sum(len(aliases) for aliases in chars_v2.values())
    print(f"Total aliases in V1: {total_v1_aliases}")
    print(f"Total aliases in V2: {total_v2_aliases}")
    
    if total_v1_aliases > 0:
        alias_change = ((total_v2_aliases - total_v1_aliases) / total_v1_aliases) * 100
        print(f"Alias change: {alias_change:+.1f}%")


def main():
    """Main comparison function."""
    if len(sys.argv) != 3:
        print("Usage: python compare_characters.py <v1_result.json> <v2_result.json>")
        sys.exit(1)
    
    v1_path = Path(sys.argv[1])
    v2_path = Path(sys.argv[2])
    
    if not v1_path.exists():
        print(f"Error: V1 result file not found: {v1_path}")
        sys.exit(1)
        
    if not v2_path.exists():
        print(f"Error: V2 result file not found: {v2_path}")
        sys.exit(1)
    
    # Load results
    print(f"Loading V1 results from: {v1_path}")
    v1_result = load_analysis_result(v1_path)
    
    print(f"Loading V2 results from: {v2_path}")
    v2_result = load_analysis_result(v2_path)
    
    # Extract characters
    chars_v1 = extract_characters(v1_result)
    chars_v2 = extract_characters(v2_result)
    
    # Find matches and differences
    matched, v1_only, v2_only = find_character_matches(chars_v1, chars_v2)
    
    # Compare aliases for matched characters
    alias_comparison = compare_aliases(chars_v1, chars_v2, matched)
    
    # Print results
    print_comparison(chars_v1, chars_v2, matched, v1_only, v2_only, alias_comparison)


if __name__ == "__main__":
    main()
