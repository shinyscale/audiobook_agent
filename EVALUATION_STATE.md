# Current Evaluation State

## Active Text
- **Name:** frankenstein
- **Attempt:** 1 of 5
- **Phase:** awaiting_analysis

## Latest Scores
- Structure Detection: 10/10
- Character Extraction: 4/10 ← FAILING
- Character Profiles: 7/10
- Chapter Summaries: 9/10
- Pronunciation Guide: 3/10 ← FAILING
- HTML Presentation: 9/10
- **Overall: 6.35/10** (threshold: 8.0)

## Current Issues (Priority Order)

### CRITICAL
1. **Character alias resolution failure: Alphonse Frankenstein**
   - Problem: "my father" (46 mentions), "M. Frankenstein" (2 mentions), and "Alphonse Frankenstein" (1 mention) are listed as THREE separate characters
   - Evidence: These all refer to Victor's father, Alphonse Frankenstein - they should be merged as aliases
   - Location: Character extraction and alias resolution in `src/agents/character_agent.py`
   - Fix: Improve alias detection to recognize that "my father", "M. Frankenstein", and "Alphonse Frankenstein" refer to the same person

2. **Character alias resolution failure: Walton**
   - Problem: "Walton" (6 mentions) and "Captain Walton" (1 mention) are separate characters
   - Evidence: Both refer to Robert Walton, the Arctic explorer who narrates the frame story
   - Location: Character extraction alias resolution
   - Fix: Merge title variations ("Captain X") with base names

3. **Character inconsistency: Full names missing from character list**
   - Problem: "Victor Frankenstein", "Elizabeth Lavenza", "Henry Clerval" appear in chapter character lists but NOT in the main character database
   - Evidence: JSON shows "Victor" (28 mentions) but chapter summaries reference "Victor Frankenstein"
   - Location: Inconsistency between character extraction and chapter character assignment
   - Fix: Ensure canonical names match across all outputs OR ensure full names are properly aliased

### HIGH
4. **Massive pronunciation false positives**
   - Problem: Common English words flagged unnecessarily: "my", "man", "father", "old", "young", "mother", "girl", "woman", "creator", "stranger", "magistrate", "Uncle", "Child"
   - Evidence: 663 total pronunciations include dozens of everyday words that any narrator knows
   - Location: `src/agents/pronunciation_agent.py` filtering logic
   - Fix: Implement word frequency filter to exclude common English words (top 5000-10000 most common words)

5. **Missing character: William Frankenstein**
   - Problem: Victor's younger brother William (murder victim) appears in chapter summaries but not in main character profiles
   - Evidence: William appears in Chapter 7 character list as "William Frankenstein" but is missing from the 15 main character profiles
   - Location: Character profile generation threshold
   - Fix: Lower mention threshold or ensure plot-critical characters are always profiled

### MEDIUM
6. **Ambiguous character entry: "M."**
   - Problem: Character listed as just "M." with 23 mentions and no description
   - Evidence: This is likely "M. Waldman" or "M. Krempe" but listed separately
   - Location: Name extraction and resolution
   - Fix: Improve title/abbreviation handling to avoid extracting incomplete names

7. **Duplicate character entries: "the old man" vs "old man" vs "De Lacey"**
   - Problem: "the old man" (19 mentions), "old man" (2 mentions), and "De" (6 mentions) are separate
   - Evidence: These likely all refer to De Lacey, the blind father in the cottage
   - Location: Alias resolution for descriptive references
   - Fix: Improve resolution of descriptive phrases ("the old man") to canonical names

8. **Character split: "Father" vs "my father"**
   - Problem: "Father" (6 mentions) listed separately from "my father" (46 mentions)
   - Evidence: These are the same character (Alphonse Frankenstein) with different article usage
   - Location: Canonical name selection
   - Fix: Normalize "my X" and "X" and "the X" before creating separate entries

### LOW
9. **Profile confidence issues**
   - Problem: Elizabeth and Margaret have low confidence (0.30) due to JSON parsing failures
   - Evidence: Mentioned in pipeline notes
   - Location: Profile generation LLM output parsing
   - Fix: Improve JSON extraction robustness or prompt engineering

## Fix History
### Attempt 1: Fixed CLI output path handling
**Issue:** CLI ignored explicit `--html` and `--output` flags, creating timestamped directory instead

**Fix Applied:**
- Modified `src/cli.py` lines 367-368: Added `output_path.parent.mkdir(parents=True, exist_ok=True)` for JSON output
- Modified `src/cli.py` lines 397-398: Added `html_path.parent.mkdir(parents=True, exist_ok=True)` for HTML output

**Testing:** All 444 tests pass.

### Attempt 2: Enhanced alias candidate pair generation for relational descriptors
**Issue:** Critical #1, #2, #8 - Relational/familial descriptors like "my father", "Father" not being paired with proper names like "Alphonse Frankenstein" for alias resolution

**Root Cause:** The `_candidate_pairs_for_merge` function in `src/pipeline/character_extraction/consensus.py` only generated candidate pairs based on:
1. Token overlap (shared words)
2. Substring matching
3. Known nickname variants

Relational descriptors like "my father" share no tokens with "Alphonse Frankenstein", so they were never considered as candidates for the LLM pairwise merge decision.

**Fix Applied:**
- Modified `src/pipeline/character_extraction/consensus.py` lines 934-987
- Added new section in `_candidate_pairs_for_merge` to identify relational/familial descriptors (father, mother, uncle, etc.) and descriptive patterns (old man, creature, stranger, etc.)
- Pairs each relational/descriptive name with top 30 proper names for LLM evaluation
- The LLM's pairwise merge logic will decide if they actually refer to the same person based on context

**What This Fixes:**
- CRITICAL #1: "my father", "Father", "M. Frankenstein" will now be paired with "Alphonse Frankenstein" for LLM evaluation
- CRITICAL #2: "Captain Walton" will be paired with "Walton" (Captain is in DESCRIPTIVE_PATTERNS)
- MEDIUM #7: "the old man", "old man" will be paired with "De Lacey"
- MEDIUM #8: "Father" and "my father" will both be paired with proper names

**Testing:** All 444 tests pass.

## Previous Text: gatsby
- **Result:** FAILED after 5 attempts (4.05/10)
- **Status:** Marked complete in manifest.json

## Next Action
Re-run analysis to verify fix. The enhanced candidate pair generation should now allow the LLM to merge relational descriptors with proper character names.
