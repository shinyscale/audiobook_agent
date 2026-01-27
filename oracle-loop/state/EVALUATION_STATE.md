# Current Evaluation State

## Active Text
- **Name:** masque_of_red_death
- **Attempt:** 3
- **Phase:** awaiting_evaluation
- **baseline_score:** 8.65
- **Competitive Mode:** single

## Output Files
- HTML: ../output/masque_of_red_death/report.html
- JSON: ../output/masque_of_red_death/analysis.json

## Pipeline Notes (Attempt 3)
- Analysis completed successfully in 10m 6s
- Competitive consensus: ENABLED (3 LLMs, 2/3 supermajority) on characters, structure, summaries stages
- Character count: 5 characters detected
- Key observation: "the Red Death" now shows alias "(aka the figure)" - description-based matching may have resolved the split
- Structure: 1 chapter (expected for short story)

## Latest Scores
- Structure Detection: 10/10 ✓
- Character Extraction: 7/10 ✗ (FAILING)
- Character Profiles: 8/10 ✓
- Chapter Summaries: 10/10 ✓
- Pronunciation Guide: 9/10 ✓
- HTML Presentation: 10/10 ✓
- **Overall: 8.85/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (1 category below threshold)

## Current Issues (Priority Order)

### CRITICAL

1. **False character split: "the masked figure" and "the Red Death" are the same entity (STILL PRESENT)**
   - Problem: "the Red Death" (ID: main_cast_1, 5 mentions) and "the masked figure" (ID: ca1c816399e5, 1 mention) are still listed as separate characters
   - Evidence: In Poe's story, the mysterious masked figure at the ball IS the Red Death personified. The text explicitly reveals this when revelers find "the grave-cerements and corpse-like mask" are empty - the masked figure was Death itself
   - ID Analysis: "the masked figure" has a 12-char hash ID indicating it came from F6 Summary Reconciliation

   **Why Previous Fix Failed:**
   - The Attempt 1 fix added partial alias matching to check if summary names are variants of existing aliases
   - But "the Red Death" now only has alias `["the intruder"]` - it no longer has "the figure" as an alias
   - Without "the figure" as an alias, the partial matching has nothing to match "the masked figure" against

   **Root Cause Analysis:**
   - The issue is upstream in the main character extraction, not just F6 reconciliation
   - The character extraction pipeline should recognize that "the masked figure" is a synonym/alias for "the Red Death" based on the text's climactic reveal
   - The description field already notes: "It manifests as a masked figure whose appearance mimics the disease's symptoms" - this semantic connection should inform alias assignment

   **Fix Approach Options:**
   - **Option A (Preferred):** Add "the masked figure" and "the figure" as aliases during main_cast character extraction when the description mentions "masked figure"
   - **Option B:** Enhance F6 reconciliation to check if a summary character name appears within the description of an existing character
   - **Option C:** Add semantic similarity matching between summary names and existing character descriptions in F6

   Location: Primary fix in `src/pipeline/character_extraction_v2/main_cast.py` (alias generation) or `src/analyzer.py` F6 reconciliation (description-based matching)

### MEDIUM

2. **Prince Prospero listed as "Supporting" instead of "Main" character**
   - Problem: Both main characters (Prospero and the Red Death) are classified as "Supporting Characters" in the HTML
   - Evidence: Prince Prospero is the protagonist with 6 mentions (highest count); the Red Death is the antagonist
   - Location: Character classification threshold logic
   - Impact: Minor for short stories, but unusual presentation

3. **Minor pronunciation false positives**
   - Problem: Common English words like "chiming," "dauntless," "girdled" are flagged
   - Evidence: These have straightforward pronunciations narrators would know
   - Impact: Low - only 4-5 false positives out of 69 entries

### LOW

4. **"Avator" appears to be OCR/source text error**
   - Problem: "Avator" flagged but Poe wrote "Avatar" ("Blood was its Avatar")
   - Evidence: Likely OCR error in source text
   - Location: Source text quality issue, not pipeline issue

## Fix History

### Attempt 1
**Issue:** False character split - "the masked figure" and "the Red Death" should be the same entity

**Fix Applied:**
- Added partial alias matching logic to `_is_likely_alias_of_existing()` function in analyzer.py
- Extracts core words from both summary name and existing aliases (filtering stopwords and adjectives)
- Checks if alias core words are subset of summary name core words

**Result:** Fix did NOT resolve the issue because:
- "the Red Death" no longer has "the figure" as an alias (only "the intruder" now)
- Without "the figure" alias, partial matching had nothing to match against
- The fix logic was correct but the upstream alias assignment changed

### Attempt 2
**Issue:** False character split - "the masked figure" and "the Red Death" are the same entity

**Root Cause:**
- Main cast LLM proposed aliases including "corpse-like figure" (visible in consensus log)
- Grounding gate filtered out "corpse-like figure" because it couldn't find exact text matches
- Character ended up with only alias: ["the intruder"]
- F6 reconciliation found "the masked figure" in chapter summary
- F6 partial alias matching couldn't match "masked figure" against "the intruder" (no shared words)
- F6 created new character with hash ID ca1c816399e5
- **KEY INSIGHT:** The character's description already contains "manifests as a masked figure" - this semantic connection was not being used for matching

**Fix Applied:**
- Added description-based matching to `_is_likely_alias_of_existing()` in analyzer.py (lines ~1567-1580)
- If a summary character name (minus articles) appears verbatim in an existing character's description, treat as same entity
- Example: "the masked figure" → "masked figure" found in description text
- Smoke test: Unit test confirmed "masked figure" matches "the Red Death" via description lookup

**Modified:** src/analyzer.py (F6 reconciliation, description-based matching)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | False character split (masked figure / Red Death) | src/analyzer.py (F6 reconciliation) | No change - alias changed upstream |
| 2 | False character split (masked figure / Red Death) | src/analyzer.py (F6 reconciliation - description matching) | Pending re-analysis |

**Pattern Detected:** Aliases proposed by LLM are filtered by grounding gate, causing F6 to miss matches. Solution: Use character descriptions (which persist after grounding) as fallback matching signal.

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 8.65 | - | Baseline. Character Extraction 7/10 due to masked figure / Red Death split |
| 2 | 8.85 | +0.20 | Minor improvement but critical issue persists |

## Next Action
Re-run analysis to verify Attempt 2 fix resolves the "masked figure" / "Red Death" split
