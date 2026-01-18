# Current Evaluation State

## Active Text
- **Name:** frankenstein
- **Attempt:** 2 of 5
- **Phase:** awaiting_fix

## Latest Scores
- Structure Detection: 10/10
- Character Extraction: 4/10 ← FAILING
- Character Profiles: 6/10 ← FAILING
- Chapter Summaries: 9/10
- Pronunciation Guide: 3/10 ← FAILING
- HTML Presentation: 9/10
- **Overall: 6.9/10** (threshold: 8.0)

## Current Issues (Priority Order)

### CRITICAL
1. **Character alias resolution failure: Alphonse Frankenstein fragmented**
   - Problem: "my father" (50 mentions), "Father" (6 mentions), "M. Frankenstein" (2 mentions), and "Alphonse Frankenstein" (1 mention) are listed as FOUR separate characters
   - Evidence: All refer to Victor's father, Alphonse Frankenstein. They should be merged with proper name as canonical
   - Location: Character extraction and alias resolution in `src/agents/character_agent.py` or `src/pipeline/character_extraction/consensus.py`
   - Fix: The Attempt 2 enhancement to `_candidate_pairs_for_merge` did NOT successfully resolve this. The relational descriptors ("my father", "Father") are still not being merged with the proper name ("Alphonse Frankenstein"). Need to investigate why the LLM pairwise merge is rejecting these pairs, or why pairs aren't being generated correctly.
   - Impact: -1.5 points (core character badly fragmented)

2. **Missing character: William Frankenstein**
   - Problem: Victor's younger brother William (murder victim in Chapter 8) appears in chapter summaries but has NO character profile in the main character list
   - Evidence: Chapter 7 and 8 summaries reference "William Frankenstein" explicitly. He is a critical plot character.
   - Location: Character profile generation threshold in character agent, or character extraction missing him entirely
   - Fix: Check mention count threshold - William may have low mentions since he dies early but is plot-critical. May need to profile all characters who appear in chapter summaries, or lower mention threshold.
   - Impact: -0.8 points (major plot character completely absent)

3. **Massive pronunciation false positives**
   - Problem: Common English words flagged unnecessarily: "my", "man", "father", "old", "young", "child", "mother", "girl", "woman", "creature", "monster", "stranger", "creator", "magistrate", "Uncle"
   - Evidence: 663 total pronunciations with estimated 400+ false positives (60%+ false positive rate)
   - Location: `src/agents/pronunciation_agent.py` filtering logic
   - Fix: Implement word frequency filter using common English word lists (e.g., top 5000-10000 most common words). Exclude: articles, possessives, common nouns, common adjectives, common family terms. Only flag: proper nouns (names, places), foreign terms, technical/archaic terms, homographs with context.
   - Impact: -0.7 points (guide unusable due to noise)

### HIGH
4. **Title/honorific splits: Walton**
   - Problem: "Walton" (6 mentions) and "Captain Walton" (1 mention) are separate characters
   - Evidence: Both refer to Robert Walton, the Arctic explorer and frame narrator
   - Location: Character extraction alias resolution for titles
   - Fix: Improve title detection to merge "Title Name" with "Name" (Captain, Mr., Mrs., Madame, M., Dr., etc.)
   - Impact: -0.15 points

5. **Title/honorific splits: Clerval**
   - Problem: "Clerval" (55 mentions) and "M. Clerval" (2 mentions) are separate characters
   - Evidence: Both refer to Henry Clerval, Victor's best friend
   - Location: Same as #4
   - Fix: Same as #4
   - Impact: -0.15 points

6. **Nonsense character entry: "M."**
   - Problem: "M." listed as standalone character with 23 mentions and no description
   - Evidence: This is an incomplete name extraction - likely fragments from "M. Waldman", "M. Krempe", "M. Frankenstein"
   - Location: Name extraction and validation in character extraction
   - Fix: Filter out standalone titles/honorifics that aren't followed by a name. "M." alone should never be a character.
   - Impact: -0.3 points

7. **Character alias resolution failure: Caroline Frankenstein**
   - Problem: "my mother" (10 mentions) and "Madame Frankenstein" (1 mention) are separate characters
   - Evidence: Both refer to Caroline Beaufort Frankenstein, Victor's mother
   - Location: Same root cause as Critical #1
   - Fix: Same approach as Critical #1
   - Impact: -0.2 points

### MEDIUM
8. **De Lacey fragmentation**
   - Problem: "De Lacey" (9 mentions), "De" (6 mentions), and "old man" (2 mentions) are separate
   - Evidence: All refer to the blind father in the cottage where the Creature learns language
   - Location: Name extraction creating incomplete "De" + descriptor resolution for "old man"
   - Fix: Improve compound name handling for "De Lacey", "Van Helsing" style names. Merge descriptive references.
   - Impact: -0.1 points

9. **Inconsistent canonical names using possessive descriptors**
   - Problem: "my father", "my mother" used as canonical names instead of "Alphonse Frankenstein", "Caroline Frankenstein"
   - Evidence: Character profiles show "my father" and "my mother" as main headings
   - Location: Canonical name selection in consensus.py
   - Fix: Prefer proper names over relational descriptors when selecting canonical name
   - Impact: Usability issue (included in scoring above)

## Fix History
### Attempt 1: Fixed CLI output path handling
**Issue:** CLI ignored explicit `--html` and `--output` flags, creating timestamped directory instead

**Fix Applied:**
- Modified `src/cli.py` lines 367-368: Added `output_path.parent.mkdir(parents=True, exist_ok=True)` for JSON output
- Modified `src/cli.py` lines 397-398: Added `html_path.parent.mkdir(parents=True, exist_ok=True)` for HTML output

**Testing:** All 444 tests pass.

**Result:** PASSED - CLI now respects explicit output paths

### Attempt 2: Enhanced alias candidate pair generation for relational descriptors
**Issue:** Critical #1 from Attempt 1 - Relational/familial descriptors like "my father", "Father" not being paired with proper names like "Alphonse Frankenstein" for alias resolution

**Root Cause:** The `_candidate_pairs_for_merge` function in `src/pipeline/character_extraction/consensus.py` only generated candidate pairs based on:
1. Token overlap (shared words)
2. Substring matching
3. Known nickname variants

Relational descriptors like "my father" share no tokens with "Alphonse Frankenstein", so they were never considered as candidates for the LLM pairwise merge decision.

**Fix Applied:**
- Modified `src/pipeline/character_extraction/consensus.py` lines 934-987
- Added new section in `_candidate_pairs_for_merge` to identify relational/familial descriptors (father, mother, uncle, etc.) and descriptive patterns (old man, creature, stranger, etc.)
- Pairs each relational/descriptive name with top 30 proper names for LLM evaluation
- The LLM's pairwise merge logic decides if they actually refer to the same person based on context

**What This Should Fix:**
- CRITICAL #1: "my father", "Father", "M. Frankenstein" should be paired with "Alphonse Frankenstein" for LLM evaluation
- CRITICAL #2: "Captain Walton" should be paired with "Walton" (Captain is in DESCRIPTIVE_PATTERNS)
- MEDIUM #7: "the old man", "old man" should be paired with "De Lacey"
- MEDIUM #8: "Father" and "my father" should both be paired with proper names

**Testing:** All 444 tests pass.

**Result:** PARTIAL SUCCESS
- ✅ "the creature" successfully merged with "the monster" and "the wretch" (aliases: "the monster, the wretch")
- ❌ "my father" (50), "Father" (6), "M. Frankenstein" (2), "Alphonse Frankenstein" (1) still separate
- ❌ "Walton" (6) and "Captain Walton" (1) still separate
- ❌ "Clerval" (55) and "M. Clerval" (2) still separate

**Analysis:** The candidate pair generation is now working (proven by "the creature" merging correctly), but the LLM pairwise merge decision is rejecting merges for "my father" + "Alphonse Frankenstein". This suggests:
1. Insufficient context being provided to LLM for pairwise decision
2. LLM prompt not emphasizing familial/relational descriptor merging strongly enough
3. Confidence threshold too high for accepting merges
4. Need to examine actual LLM pairwise merge prompts and responses

## Previous Text: gatsby
- **Result:** FAILED after 5 attempts (4.05/10)
- **Status:** Marked complete in manifest.json

## Output Files (Attempt 2)
- HTML: output/frankenstein/report.html
- JSON: output/frankenstein/analysis.json

## Pipeline Notes (Attempt 2)
- Analysis completed successfully in 63m 51s
- Pipeline metrics: 368 LLM calls, 865,482 tokens
- Structure: 25 chapters detected ✓
- Characters: 49 characters found (many are splits/fragments)
- Character profiles: 14 profiles generated (missing William Frankenstein)
- Pronunciations: 663 words flagged (60%+ false positives)
- Narrator detected: Victor Frankenstein (first-person) ✓
- Models used: qwen3-next:80b for character extraction, qwen3:30b for other tasks

## Next Action
Run PROMPT_fix.md to address:
1. CRITICAL #1: Investigate why LLM pairwise merge is rejecting "my father" + "Alphonse Frankenstein" despite candidate pairs being generated
2. CRITICAL #2: Fix William Frankenstein missing from character profiles
3. CRITICAL #3: Add word frequency filter to pronunciation agent to eliminate common English words
