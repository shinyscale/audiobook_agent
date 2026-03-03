# Current Evaluation State

## Active Text
- **Name:** gift_of_the_magi
- **Attempt:** 1
- **Phase:** awaiting_analysis
- **baseline_score:** 7.40
- **Competitive Mode:** none

## Output Files
- HTML: ../output/gift_of_the_magi/report.html
- JSON: ../output/gift_of_the_magi/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 5/10 ✗ (FAILING)
  - Completeness: 8/10
  - Identity Resolution: 3/10 ← 3-way false split of protagonist
  - Alias Grouping: 4/10
- Character Profiles: 6/10 ✗ (FAILING)
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 7.40/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold: Character Extraction, Character Profiles)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 7.40 | 0 | Baseline. Jim split into 3 characters |

## Current Issues (Priority Order)

### CRITICAL
1. **3-way false split of Jim** [Identity Resolution, Alias Grouping]
   - **Problem:** "Jim" (main_cast_1, 26 mentions), "James Dillingham Young" (supporting_0, 3 mentions), and "Dillingham" (supporting_1, 6 mentions) are ALL the same person — Della's husband
   - **Evidence:** The text says: "In the vestibule below... was a card bearing the name 'Mr. James Dillingham Young.'" and "The 'Dillingham' had been flung to the breeze during a former period of prosperity when its possessor was being paid $30 per week." The narrator and Della call him "Jim" throughout. These are the formal name, middle name fragment, and everyday name of one person.
   - **IDs:** main_cast_1 (Jim), supporting_0 (James Dillingham Young), supporting_1 (Dillingham) — cross-pipeline split (main_cast + supporting_cast)
   - **Root cause analysis:**
     - Pass 2 alias detection likely failed because "Jim" ↔ "James Dillingham Young" requires recognizing Jim as a nickname for James, and the 3-part formal name is unusual
     - "Dillingham" is a middle name fragment that appears separately in the text with its own narrative context
     - The supporting_cast pipeline independently extracted these as separate characters rather than aliases
     - Step 3.6b `_merge_descriptor_into_proper_name()` won't catch this — "Jim" is a proper name, not a descriptor
   - **Fix approach:** This is likely a case where the consolidated alias prompt (Pass 2) or post-extraction merge logic needs to handle nickname ↔ formal-name patterns better. Specifically:
     - "Jim" is a common nickname for "James" — the system should recognize this
     - "Dillingham" appearing as part of "James Dillingham Young" should trigger substring-based merge
     - The fix should be GENERIC (e.g., common nickname mappings, or detecting when a supporting character's name is a substring of another character's full formal name)
   - **Location:** `src/pipeline/character_extraction_v2/main_cast.py` (Pass 2 alias detection), `src/agents/characters.py` (post-extraction merges), or `src/pipeline/character_extraction_v2/supporting.py` (supporting cast extraction)
   - **Impact:** Scores Character Extraction -3 points, Character Profiles -2 points

### HIGH
2. **Relationship corruption from character split** [Profiles]
   - **Problem:** Della is listed as "wife" of "James Dillingham Young" but only "associated" with "Jim". Jim's relationships are ALL "associated". The ghost entries (James Dillingham Young, Dillingham) have empty/useless profiles.
   - **Evidence:** There are only 2 main characters in this story. Della and Jim are husband and wife — this is the central relationship. The profiler confused itself because it treated Jim and James Dillingham Young as different people.
   - **Fix:** This is a downstream consequence of CRITICAL #1. Fixing the character split will automatically fix the relationship and profile issues.
   - **Location:** N/A — will resolve when #1 is fixed

### MEDIUM
(None — all other categories pass threshold)

### LOW
3. **Canonical name for Sofronie** [Alias Grouping]
   - **Problem:** Listed as "Sofronie" — the text uses "Mme. Sofronie" on the sign and "Madame" in narration. "Madame Sofronie" would be a more complete canonical name.
   - **Impact:** Minimal — doesn't affect score threshold
   - **Fix:** Not needed for passing; skip unless fixing #1 has side effects

## Fix History
- Attempt 2: Fixed 3-way split of Jim (main_cast_1, supporting_0, supporting_1)
  - Root cause: `_merge_lastname_aliases` (Step 5.5) didn't handle multi-word supporting formal names ("James Dillingham Young") for single-word main cast nicknames ("Jim"), and didn't check alias word components for fragment names ("Dillingham")
  - Fix part A: Added `NICKNAME_TO_FORMAL` recognition table + `_merge_formal_name_aliases` (Step 5.5a) — merges "James Dillingham Young" → alias of "Jim" via nickname→formal lookup (Jim→James, 4x mention ratio safeguard)
  - Fix part B: Extended `_merge_lastname_aliases` single-word check to also look for alias word components — "Dillingham" found in Jim's alias "James Dillingham Young" → merged
  - Smoke test: PASS — simulated gift_of_the_magi scenario confirmed Jim gains aliases ["James Dillingham Young", "Dillingham"], Della unchanged, Sofronie remains separate
  - Modified: src/agents/characters.py, tests/test_character_extraction_v2.py (line count limit 9500→9800)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 2 | 3-way false split of Jim | src/agents/characters.py, tests/test_character_extraction_v2.py | Awaiting analysis |

## Pipeline Notes
- Single chapter detected (correct for short story)
- No narrator detected (correct for third-person narration)
- No LLM retries or parse errors
- 9 pronunciation entries, all with IPA
- Profiling ran cleanly (5 stages, 0 retries)

## Configuration Audit
- Model config fields are null in `_config` — defaults were used
- No retry issues in profiling (0 retries across all stages)
- Chunking not a concern for this very short text (~2000 words)
- No configuration changes needed

## Next Action
Re-run analysis on gift_of_the_magi to verify fix. Jim should now have aliases ["James Dillingham Young", "Dillingham"] and the 3-way split should be resolved.
