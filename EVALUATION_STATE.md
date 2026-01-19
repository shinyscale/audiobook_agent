# Current Evaluation State

## Active Text
- **Name:** cask_of_amontillado
- **Attempt:** 2
- **Phase:** awaiting_fix
- **baseline_score:** 6.10

## Latest Scores
- Structure Detection: 9/10
- Character Extraction: 4/10 ← CRITICAL FAILURE
- Character Profiles: 4/10 ← CRITICAL FAILURE
- Chapter Summaries: 6/10
- Pronunciation Guide: 7/10
- HTML Presentation: 8/10
- **Overall: 6.10/10** (threshold: 8.0)

## Current Issues (Priority Order)

### CRITICAL

1. **"Amontillado" (a wine) is listed as a character**
   - Problem: The analysis created a character entry for "Amontillado" which is the Spanish sherry wine, NOT a person
   - Evidence: `characters[0].canonical_name` = "Amontillado" with 16 mentions
   - The description text is actually describing Montresor (the narrator) but attributed to the wine name
   - Location: Likely `src/pipeline/character_extraction/` - NER or LLM extraction is treating the title word as a character
   - Root cause: The word "Amontillado" appears frequently in the text (34 times) as part of dialogue about the wine, and the system incorrectly identified it as a character name
   - Fix approach: Add filtering to exclude common nouns/objects that appear in titles from character extraction, or improve the LLM prompt to distinguish between characters and objects

2. **Montresor NOT identified as narrator**
   - Problem: `is_narrator: false` for Montresor, but he IS the first-person narrator
   - Evidence: The story opens with "I had borne as I best could" and continues in first person throughout
   - The `plot_summary` incorrectly calls the narrator "Amontillado" instead of Montresor
   - Location: Likely `src/agents/summary_agent.py` or narrator detection logic
   - Fix approach: Narrator detection should look for first-person pronouns and identify which character uses "I"

3. **Montresor has NO profile content**
   - Problem: Montresor has zero descriptions, zero evidence, zero personality/voice guidance
   - Evidence: `characters[2]` (Montresor) has empty `descriptions`, `relationships`, `evidence` arrays
   - Only 1 mention_count when he should be the most mentioned character (as the narrator)
   - Location: Character extraction is failing to associate the narrator's actions with Montresor
   - Fix approach: Improve narrator-to-character linking - when a character is identified as narrator, their profile should be built from all first-person statements

### HIGH

4. **Luchresi missing from character list**
   - Problem: Luchresi is mentioned 6 times by name but not included in characters
   - Evidence: He appears in dialogue as a rival wine expert that Montresor uses to manipulate Fortunato
   - Location: Character extraction may be filtering by mention count or missing this name
   - Fix approach: Lower threshold or improve detection - he's clearly a named character

5. **Plot summary uses "Amontillado" as narrator name**
   - Problem: The `overview.plot_summary.plot_summary` field repeatedly says "Amontillado recounts..." and "Amontillado leads Fortunato..."
   - Evidence: This is a downstream effect of issue #1 - the summary agent used the wrong character as narrator
   - Location: `src/agents/summary_agent.py`
   - Fix approach: Fixing issue #1 and #2 should cascade to fix this

### MEDIUM

6. **Some pronunciation false positives**
   - Problem: Common words like "jingled", "filmy", "orbs", "leer" flagged unnecessarily
   - Evidence: 56 total pronunciations flagged, some are common English words
   - Location: `src/pipeline/pronunciation/` or pronunciation agent
   - Fix approach: Add word frequency filtering (as noted in ATTEMPT_1_SUMMARY.md)

7. **"Medoc" not flagged for pronunciation**
   - Problem: French wine region name not in pronunciation guide
   - Evidence: Appears in text ("a draught of the Medoc", "My own fancy grew warm with the Medoc")
   - Location: Pronunciation detection
   - Fix approach: Minor - improve foreign word detection

## Fix History

### Attempt 1 (2026-01-18): Fixed validator heuristic for non-person entities

**Root Cause Analysis:**
- Issue #1 ("Amontillado as character"):
  - Traced from: `output/cask_of_amontillado/analysis.json` → `CharacterMap.characters[0]` → `CharacterExtractionPipeline` → `CharacterValidator._heuristic_validation()` line 167
  - **Root cause:** Heuristic at line 167-178 auto-accepted any name with 10+ mentions and 3+ dialogue occurrences WITHOUT LLM validation
  - "Amontillado" (wine) had 16 mentions and appeared in dialogue ("Amontillado!" when discussing the wine), triggering false acceptance
  - Confidence: HIGH

- Issue #2 (Montresor not narrator):
  - **Root cause:** Cascading failure from Issue #1
  - Narrator detector received corrupted character list with "Amontillado" (16 mentions) vs "Montresor" (1 mention)
  - LLM picked "Amontillado" as narrator due to higher prominence
  - Confidence: HIGH

- Issue #3 (Montresor missing profile):
  - **Root cause:** NER limitation - "Montresor" name appears only once explicitly in text (when Fortunato cries "For the love of God, Montresor!")
  - All first-person narration uses "I", "my" which NER doesn't attribute to Montresor
  - Confidence: HIGH (fundamental NER limitation, requires different approach to fix)

**Changes Made:**
- File: `src/pipeline/character_extraction/validator.py`
- Line 165-178: **Removed** overly aggressive heuristic that auto-accepted high-mention-count names without LLM validation
- Line 39-54: **Enhanced** validation system prompt to explicitly reject objects, food, drink, places
- Line 66-69: **Enhanced** validation prompt template to ask LLM to distinguish between people and objects being discussed

**Smoke Test Results (PASS):**
- Ran analysis on "The Cask of Amontillado - Poe.txt" with qwen2.5:32b
- ✅ "Amontillado" removed from character list (went from 3 to 2 characters)
- ✅ Narrator correctly identified as "Montresor" in plot summary
- ✅ Plot summary says "The story is narrated by Montresor" (not "Amontillado")
- ❌ Montresor still has only 1 mention (NER limitation - deferred as separate issue)

**Full Test Suite: PASSED**
- 444 tests passed, 11 skipped, 1 warning
- No regressions introduced

**Issues Addressed:**
- ✅ Issue #1: Fixed (Amontillado no longer extracted as character)
- ✅ Issue #2: Fixed (Montresor correctly identified as narrator in plot summary)
- ✅ Issue #5: Fixed (plot summary now uses "Montresor" not "Amontillado")
- ⏸️ Issue #3: Partially addressed (narrator identified but profile still thin due to 1 mention - NER limitation)

## Attempt 2 (2026-01-18): NER extracting invalid character name "--yes"

**Pipeline Failure:**
- Analysis failed during character extraction phase
- Error: `LLM validation returned invalid JSON for '--yes' after 3 attempts: Invalid JSON: got list`

**Root Cause Analysis:**
- Location: Text line 166 of "The Cask of Amontillado - Poe.txt"
- Context: Fortunato's dialogue: "He! he! he! --he! he! he! --yes, the Amontillado..."
- spaCy NER tagged "--yes" as a PERSON entity (incorrect)
- The string "--yes" passed `_is_valid_name()` check (60% alphabetic ratio: 3 of 5 chars)
- Went to LLM validation, but LLM returned invalid JSON format (list instead of dict)

**Why Previous Fix Didn't Address This:**
- Previous fix (Attempt 1) only removed the heuristic auto-acceptance
- Did not add filtering for names starting with punctuation
- spaCy occasionally mis-tags punctuation-heavy fragments as PERSON entities

**Proposed Fix:**
- Add check in `_is_valid_name()` (src/pipeline/character_extraction/proposers/ner.py:237)
- Reject names that start or end with non-alphabetic characters
- Example: `if not name[0].isalpha() or not name[-1].isalpha(): return False`

## Attempt 2 Analysis Run (2026-01-18): FAILED - NER bug still present

**Error Encountered:**
```
LLM validation attempt 1 for '--yes' returned invalid JSON: got list
LLM validation attempt 2 for '--yes' returned invalid JSON: got list
LLM validation attempt 3 for '--yes' returned invalid JSON: got list
Validation failed for '--yes': LLM validation returned invalid JSON for '--yes' after 3 attempts: Invalid JSON: got list
Error during analysis: LLM validation returned invalid JSON for '--yes' after 3 attempts: Invalid JSON: got list
```

**Analysis:**
- Confirmed the bug documented in Attempt 2 is still present
- NER is extracting "--yes" from text and sending it to LLM validation
- Current `_is_valid_name()` function (line 237-257) accepts "--yes" because:
  - It has 5 characters (passes `len(name) < 2` check on line 239)
  - It has 3 alphabetic characters, giving 60% ratio (passes 50% threshold on line 254)
- The proposed fix (reject names starting/ending with non-alphabetic chars) is NOT yet implemented
- Fix needs to be applied before analysis can proceed

## Attempt 2 Fix (2026-01-18): Reject names with leading/trailing punctuation

**Root Cause:**
- Location: `src/pipeline/character_extraction/proposers/ner.py` line 237 `_is_valid_name()` function
- Root cause: Function only checked for 50% alphabetic characters, allowing "--yes" (60% alphabetic) to pass
- Confidence: HIGH

**Changes Made:**
- File: `src/pipeline/character_extraction/proposers/ner.py`
- Lines 242-245: **Added** check to reject names that start or end with non-alphabetic characters
- This filters out spaCy mis-tagged dialogue fragments like "--yes", "--he", etc.

**Smoke Test Results (PASS):**
```
✓ "--yes"    rejected (expected: reject)
✓ "yes--"    rejected (expected: reject)
✓ "--he"     rejected (expected: reject)
✓ "Montresor" accepted (expected: accept)
✓ "Fortunato" accepted (expected: accept)
```

**Full Test Suite: PASSED**
- 444 tests passed, 11 skipped, 1 warning
- No regressions introduced

**Issue Addressed:**
- ✅ Pipeline failure: NER extracting invalid character name "--yes"

## Next Action
**Phase:** awaiting_analysis

Re-run analysis to verify the fix allows the pipeline to complete successfully.
