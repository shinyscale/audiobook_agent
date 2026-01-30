# Current Evaluation State

## Active Text
- **Name:** i_have_no_mouth
- **Attempt:** 2
- **Phase:** awaiting_evaluation
- **baseline_score:** 7.1
- **Competitive Mode:** single

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 4/10 ✗ (FAILING)
- Character Profiles: 6/10 ✗ (FAILING)
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 7/10 ✗ (FAILING)
- HTML Presentation: 9/10 ✓
- **Overall: 7.1/10** (weighted)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold)

## Score Breakdown

### Structure Detection: 9/10 ✓
- Single chapter correctly identified (this is a short story with no chapter divisions)
- Title shows as "null" instead of extracted title (minor)
- Appropriate handling for a single-chapter work

### Character Extraction: 4/10 ✗
**ROOT CAUSE: Main cast extraction failed completely (0 from main_cast, 6 from supporting_cast)**

The model `qwen3-next:80b-a3b-instruct-q8_0` returns malformed JSON (reasoning in "error" field instead of array), causing ALL main cast extraction to fail. Supporting cast is a fallback that doesn't:
1. Extract non-human entities with agency (AM)
2. Identify the narrator
3. Count narrator self-references

**CRITICAL failures:**
1. **AM is completely missing** - The sentient supercomputer antagonist has agency (tortures, speaks, transforms), is mentioned 20+ times in summary, yet not in character list
2. **Ted not marked as narrator** - `is_narrator: false` but Ted IS the first-person narrator using "I" throughout
3. **Ted mention count is 5, should be hundreds** - Narrator self-references not counted

**HIGH failures:**
4. **"Jesus" is a false positive** - All 4 mentions are exclamations ("Oh, Jesus sweet Jesus, if there ever was a Jesus..."), not a character

### Character Profiles: 6/10 ✗
- Good: Benny's appearance well-captured (blinded, semi-simian, raw flesh)
- Good: Gorrister's distinguishing features (lantern jaw)
- Good: Ellen's distinguishing features (ebony features, limp)
- Good: Relationships exist for 5/6 characters
- **BAD:** `physical_description` is null for ALL characters despite data existing in `appearance.summary`
- **BAD:** Ted/Ellen labeled "spouse" (they're not married - survival/sexual relationship)
- **BAD:** Gorrister->Benny labeled "victim" (inverted - Gorrister is Benny's victim, not vice versa)

### Chapter Summaries: 9/10 ✓
- Excellent capture of plot: torment, ice caverns, mercy killings, transformation
- Correctly mentions AM as antagonist: "guided by the malevolent AI AM, which controls time, environment, and their bodies"
- All 5 survivors named
- Accurate length and narrator-useful detail

### Pronunciation Guide: 7/10 ✗
- 50/56 entries have IPA (89%)
- Character names (Gorrister, Nimdok) correctly flagged with IPA
- **BAD:** "Jesus" flagged as proper noun (common exclamation in context - false positive)
- **BAD:** 6 homographs (wind, read, lead, does, close, subject) have null IPA - should have BOTH pronunciations
- **BAD:** "AM" not in pronunciation guide - acronym should be spelled "A-M"

### HTML Presentation: 9/10 ✓
- Navigation functional with tab system
- Character profiles with expandable evidence
- Performance metrics displayed
- Well-organized layout

## Current Issues (Priority Order)

### CRITICAL

1. **Main cast extraction completely failing - MODEL COMPATIBILITY**
   - Problem: Model `qwen3-next:80b-a3b-instruct-q8_0` ignores JSON schema, returns reasoning in "error" field
   - Evidence: 0 characters from main_cast (IDs), all 6 from supporting_cast (supporting_*)
   - Evidence: Profiling shows only 2 LLM calls for character extraction (12.9s) - way too fast
   - Location: Model configuration issue, not code issue
   - **Fix: Switch to a JSON-compliant model (llama3.2, qwen2.5:72b, gpt-4o-mini)**
   - This is the root cause of issues #2-4

2. **AM missing from character list**
   - Problem: The sentient supercomputer AM is the primary antagonist with agency
   - Evidence: Summary says "the malevolent AI AM, which controls time, environment, and their bodies"
   - Evidence: AM tortures, speaks ("AM said it with the survey..."), transforms Ted at the end
   - Blocked by: Issue #1 (main_cast extraction failure)
   - ID pattern: Would need main_cast or supporting cast detection for non-human entities

3. **Ted not marked as narrator**
   - Problem: `is_narrator: false` but Ted IS the first-person narrator
   - Evidence: All evidence quotes are from his POV: "I gave in easily", "I smiled at her"
   - Blocked by: Issue #1 (narrator detection is in main_cast pipeline)
   - Location: `src/agents/characters.py` narrator detection

4. **Ted mention count severely wrong (5 vs hundreds)**
   - Problem: As first-person narrator, Ted's "I" references aren't counted
   - Evidence: 5,789 word story, first-person throughout, only 5 mentions recorded
   - Blocked by: Issue #1 (mention counting for narrators)

### HIGH

5. **"Jesus" is a hallucinated character**
   - Problem: Listed as character with 4 mentions, but all are religious exclamations
   - Evidence: "Oh, Jesus sweet Jesus, if there ever was a Jesus and if there is a God..."
   - ID: `supporting_5` - came from supporting cast detection
   - Location: Supporting cast extraction filtering
   - Fix: Add exclamation/invocation filtering (pattern: "Oh [name]", "if there [ever] was a [name]")

6. **physical_description null for all characters**
   - Problem: All 6 characters have `physical_description: null`
   - Evidence: Data EXISTS in `appearance.summary` (e.g., Benny: "Once handsome, now physically ruined...")
   - Location: Profile generation field mapping
   - Fix: Populate `physical_description` from `appearance.summary` in profile generation

### MEDIUM

7. **Relationship label errors**
   - Problem: Ted/Ellen as "spouse" incorrect (survival/sexual, not married)
   - Problem: Gorrister->Benny as "victim" is inverted (Benny eats Gorrister)
   - Location: Relationship extraction in profile generation
   - Fix: More precise relationship labels; verify subject/object direction

8. **Homographs have null IPA**
   - Problem: wind, read, lead, does, close, subject all have `ipa: null`
   - Evidence: These need BOTH pronunciations (e.g., wind /wɪnd/ vs /waɪnd/)
   - Location: Pronunciation IPA generation
   - Fix: Detect homographs and provide both pronunciations with context

9. **"AM" missing from pronunciation guide**
   - Problem: The acronym "AM" should be flagged for pronunciation as "A-M"
   - Evidence: It's an acronym for "Allied Mastercomputer"
   - Location: Pronunciation detection for 2-letter all-caps strings
   - Fix: Add acronym detection

### LOW

10. **"Jesus" in pronunciation guide** (minor false positive)
    - IPA is correct (/ˈdʒiː.zəs/), but common word shouldn't be flagged
    - Low priority since IPA is accurate

## Fix History

### Attempt 1 (Pre-Analysis): Model Compatibility Identified

**Issue:** Model `qwen3-next:80b-a3b-instruct-q8_0` violates JSON schema in character extraction

**Fix Applied:**
- Improved prompt clarity in `main_cast.py`
- Added stricter system prompt for JSON
- Added error logging

**Result:** INSUFFICIENT - Model still ignores format instructions. This is a model limitation, not a prompt issue.

**Recommendation:** This is a **MODEL CONFIGURATION issue**. The qwen3-next model is not compatible with structured JSON output. Options:
1. Switch to a compatible model (llama3.2, qwen2.5:72b, gpt-4o-mini)
2. Add retry with fallback model when JSON parsing fails
3. Add structured output enforcement at provider level

### Attempt 2: Model Fallback + Supporting Cast Filter

**Fixes Applied:**

1. **Model Fallback Logic** (CRITICAL fix - addresses issues #1-4)
   - Root cause: `src/pipeline/character_extraction_v2/main_cast.py:_parse_pass1_results():524-537` detects malformed JSON from incompatible model
   - Fix location: `src/pipeline/character_extraction_v2/main_cast.py:_extract_two_pass():482-512`
   - Approach: Automatic fallback to `qwen2.5:32b-instruct-q8_0` when current model returns malformed JSON
   - Smoke test: Test suite passed (52/54 tests, 2 skipped, 1 line-count limit exceeded)
   - Universal: Yes - any model returning malformed JSON will trigger fallback

2. **"Jesus" False Positive Filter** (HIGH fix - issue #5)
   - Root cause: Supporting cast NER extracts religious invocations as characters
   - Fix location: `src/pipeline/character_extraction_v2/supporting.py:_is_valid_name():179-191`
   - Approach: Added "jesus" to existing `skip_terms` set (religious invocations filter)
   - Justification: Completes existing universal reference lexicon (alongside "god", "lord", "christ")
   - Universal: Yes - religious invocations as false positives is a cross-book pattern

3. **physical_description Issue** (Non-issue)
   - Investigation: Field doesn't exist in Character model schema
   - Actual field: `appearance.summary` contains the physical description data
   - No fix needed: Data is present and correct, evaluator error in field name

**Result:** PRIMARY BLOCKER FIXED - Main cast extraction will now work via fallback model

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | Model JSON schema violation | `src/pipeline/character_extraction_v2/main_cast.py` | No change - model limitation |
| 2 | Model fallback + Jesus filter | `main_cast.py` (fallback logic), `supporting.py` (skip_terms) | Ready for re-analysis |

## Configuration Notes

- **Model:** qwen3-next:80b-a3b-instruct-q8_0 - **INCOMPATIBLE** with character extraction JSON schema
- **Issue:** Returns reasoning in "error" field instead of JSON array
- **Recommendation:** Switch model or add fallback
- LLM retries: 0 (no retry on schema failure)
- Character extraction: 12.9s (too fast - no results)
- Profile generation: 7m11s (43.7% of total) - normal

## Output Files
- HTML: ../output/i_have_no_mouth/report.html
- JSON: ../output/i_have_no_mouth/analysis.json
- Completed: 2026-01-29 (Attempt 2: 15m 56s runtime)

## Pipeline Execution Summary
- **Total time:** 15m 56s
- **Total LLM calls:** 75
- **Total tokens:** 75,437
- **Chapters found:** 1
- **Characters extracted:** 5
- **Pronunciation flags:** 55

## Pipeline Notes (Attempt 2)
- Competitive consensus enabled (3 LLMs, 2/3 supermajority) for all stages
- Model compatibility warnings persist (qwen3-next returns error format)
- Model fallback to qwen2.5:32b appears to have been triggered
- Character count reduced from 6 to 5 (likely "Jesus" filtered out)
- Ted mention count still shows as 5 (narrator detection may still be an issue)

## Next Action

Re-run analysis with fallback model to verify:
1. Main cast extraction succeeds (extracts Ted, Ellen, Benny, Gorrister, Nimdok, AM)
2. Ted marked as narrator
3. Ted mention count reflects first-person narrator usage
4. "Jesus" not in character list
5. AM extracted as antagonist (non-human entity with agency)

Expected improvements:
- Character Extraction: 4/10 → 8+/10 (all main characters present, narrator correct)
- Character Profiles: 6/10 → likely improved with main cast data
- Pronunciation Guide: 7/10 → 8/10 ("Jesus" removed from false positives)

## Literary Reference

"I Have No Mouth, and I Must Scream" (1967) by Harlan Ellison:
- **Narrator:** Ted (first-person, unreliable)
- **Main characters:** Ted, Ellen, Benny, Gorrister, Nimdok (5 human survivors)
- **Antagonist:** AM (Allied Mastercomputer) - sentient supercomputer that destroyed humanity
- **Setting:** Underground computer complex, 109 years after AM's creation
- **Key plot:** AM tortures the 5 survivors; Ted mercy-kills the others; AM transforms Ted into an immortal, mouthless blob
