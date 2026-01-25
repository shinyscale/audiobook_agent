# Audiobook Prep Scripts

This directory contains utility scripts for the audiobook preparation system.

## compare_characters.py

A script to compare character extraction results between V1 and V2 implementations.

### Usage

```bash
python scripts/compare_characters.py <v1_result.json> <v2_result.json>
```

### Features

- Compares character counts between versions
- Matches characters based on name/alias overlap
- Shows V1-only and V2-only characters
- Compares aliases for matched characters
- Provides quality metrics (match rate, alias coverage)

### Example Output

```
================================================================================
CHARACTER EXTRACTION COMPARISON: V1 vs V2
================================================================================

Total characters in V1: 4
Total characters in V2: 4
Matched characters: 3
V1-only characters: 1
V2-only characters: 1

----------------------------------------
MATCHED CHARACTERS
----------------------------------------

Elizabeth Bennet ↔ Elizabeth Bennet
  Common aliases: ['Eliza', 'Elizabeth Bennet', 'Lizzy', 'Miss Bennet']
  V2-only aliases: ['Miss Elizabeth Bennet']

[... more matched characters ...]

----------------------------------------
V1-ONLY CHARACTERS (missing in V2)
----------------------------------------
  • Mr. Wickham (aliases: George Wickham, Wickham)

----------------------------------------
V2-ONLY CHARACTERS (new in V2)
----------------------------------------
  • Mr. Bingley (aliases: Bingley, Charles Bingley)

========================================
QUALITY METRICS
========================================
Character match rate: 50.0%
Total aliases in V1: 12
Total aliases in V2: 14
Alias change: +16.7%
```

### Use Cases

1. **Migration Validation**: Verify that V2 extraction maintains or improves upon V1 results
2. **Quality Assessment**: Check if V2 finds more characters or better aliases
3. **Regression Testing**: Ensure V2 doesn't lose important characters from V1
4. **Performance Comparison**: See how alias detection improves between versions

### Implementation Notes

- Characters are matched based on alias overlap (including main name)
- The script handles missing fields gracefully (e.g., no aliases array)
- Works with standard audiobook-prep analysis output JSON files
