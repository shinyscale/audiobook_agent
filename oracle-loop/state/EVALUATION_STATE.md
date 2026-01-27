# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 3
- **Phase:** awaiting_fix
- **baseline_score:** 6.95
- **Competitive Mode:** single

## Output Files
- HTML: ../output/gatsby/report.html
- JSON: ../output/gatsby/analysis.json

## Latest Scores
- Structure Detection: 8/10 ✓
- Character Extraction: 6/10 ✗ (FAILING)
- Character Profiles: 4/10 ✗ (FAILING)
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 8/10 ✓
- **Overall: 6.95/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.95 | 0.00 | Initial - Characters & Profiles failing |
| 2 | 6.95 | 0.00 | Fix did NOT work - Gatsby/Daisy still from supporting_cast |
| 3 | 6.95 | 0.00 | Some fixes worked (Eckleburg filtered), but core issues remain |

## Attempt 3 Evaluation Summary

### What Improved (Fixes that worked):
1. ✅ **Eckleburg billboard filtered** - No longer in character list (was `main_cast_8`)
2. ✅ **Gatsby aliases correct** - Jay Gatsby has ["Gatsby", "James Gatz"]
3. ✅ **IPA coverage improved** - 537/556 (96.6%), only 19 missing

### What Did NOT Improve:
1. ❌ **Daisy's canonical name** - Still just "Daisy" with NO aliases (should be "Daisy Buchanan")
2. ❌ **Character roles incorrect** - Gatsby/Daisy have `role: "supporting"` instead of protagonist/main
3. ❌ **Character IDs unchanged** - Gatsby (`supporting_9`) and Daisy (`supporting_1`) still from supporting_cast
4. ❌ **Physical descriptions 0/29** - Profile sampling fix may have run but data still empty
5. ❌ **Relationships 0/29** - Same as above

### New Issues Discovered:
6. ❌ **Tom's canonical name** - Listed as "Tom" instead of "Tom Buchanan"
7. ❌ **Non-character extractions** - "Town Tattle" (magazine), generic descriptions (butler, chauffeur, etc.)
8. ❌ **Owl Eyes missing** - Named minor character at party and funeral not extracted

---

## Current Issues (Priority Order)

### CRITICAL

1. **Daisy missing full name and ALL aliases**
   - Problem: Listed as "Daisy" with `aliases: []`, should be "Daisy Buchanan" with aliases ["Daisy", "Daisy Fay"]
   - Evidence: Chapter summaries correctly use "Daisy Buchanan" in `characters_present` for all chapters
   - Root cause: F6 reconciliation is NOT updating canonical_name when summary uses fuller name
   - Location: `src/analyzer.py` - F6 reconciliation logic (around line 1220-1240)
   - Fix: When F6 finds a summary name that is LONGER than character's canonical_name, update canonical_name

2. **Tom missing full name in canonical**
   - Problem: Listed as "Tom" with aliases ["Tom Buchanan", "Buchanan"]
   - Evidence: This is backwards - "Tom Buchanan" should be canonical, "Tom" should be alias
   - Root cause: Supporting cast extraction uses first-seen form as canonical
   - Location: `src/pipeline/character_extraction_v2/supporting.py` or F6 reconciliation
   - Fix: When alias is longer and more complete than canonical, swap them

3. **Gatsby and Daisy roles are "supporting" instead of protagonist/main**
   - Problem: The title character Jay Gatsby has `role: "supporting"`, Daisy also "supporting"
   - Evidence: Gatsby is THE protagonist (title character, 267 mentions), Daisy is central (179 mentions)
   - Root cause: Promotion step upgraded from "minor" to "supporting" but not to protagonist/main
   - Location: `src/agents/characters.py` - promotion logic added in attempt 2
   - Fix: Characters with 200+ mentions should be "protagonist" or "main", not just "supporting"

### HIGH

4. **Physical descriptions completely empty (0/29)**
   - Problem: Every character has `physical_description: null`
   - Evidence: Text has clear descriptions - Tom Buchanan: "a sturdy straw-haired man of thirty with a rather hard mouth and a supercilious manner. Two shining arrogant eyes..."
   - Root cause: Profile extraction may be looking in wrong field, or prompt not returning appearance data
   - Location: `src/pipeline/character_profiles.py` - appearance extraction
   - Fix: Debug profile extraction - check if LLM returns appearance data and if it's being saved

5. **Relationships completely empty (0/29)**
   - Problem: Every character has `relationships: {}`
   - Evidence: Clear relationships exist - Tom+Daisy married, Gatsby loves Daisy, Myrtle+Tom affair
   - Root cause: Same as above - profile extraction not populating this field
   - Location: `src/pipeline/character_profiles.py` - relationship extraction
   - Fix: Same investigation as #4

6. **Non-character extractions from F6 reconciliation**
   - Problem: 7 non-characters extracted with hash IDs:
     - "Town Tattle" (magazine, 3 mentions)
     - "The tenor and contralto performers" (generic group)
     - "The two girls in yellow dresses" (generic description)
     - "the chauffeur", "the gardener", "the movie star", "the butler" (generic roles)
   - Evidence: These are all from F6 reconciliation (12-char hash IDs)
   - Location: `src/analyzer.py` - F6 reconciliation (around line 1220-1240)
   - Fix: Add filter in F6 to exclude generic descriptions ("the X") and known non-person patterns

7. **Missing named character: Owl Eyes**
   - Problem: The "owl-eyed man" / "Owl-eyes" appears in Chapter 3 (library) and Chapter 9 (funeral)
   - Evidence: "Owl-eyes spoke to me by the gate" - clearly a named character reference
   - Impact: Minor character but narratively significant (only other attendee at funeral)
   - Location: May be filtered by mention threshold or not recognized as proper name
   - Fix: Either lower threshold or add special handling for descriptive nicknames

### MEDIUM

8. **Chapter titles null for chapters 2-9**
   - Problem: Chapter 1 has title "I" but chapters 2-9 have `title: null`
   - Evidence: All chapters should have Roman numeral titles (I through IX)
   - Location: Structure detection - title extraction
   - Fix: Ensure Roman numeral detection works for all chapters, not just first

9. **Characters from supporting_cast never promoted to main_cast ID**
   - Problem: Gatsby is `supporting_9`, Daisy is `supporting_1` despite being main characters
   - Evidence: The promotion step increases role but doesn't change ID
   - Impact: Low - ID is internal, but indicates promotion is partial
   - Note: This is a symptom, not root cause - fixing main_cast extraction is the real solution

### LOW

10. **Owl-eyed man alias issue**
    - If Owl Eyes is extracted, "the owl-eyed man" should be an alias
    - Very minor character, low priority

---

## Fix History

### Attempt 1 Fixes
**Fix: Enhanced main cast extraction prompt with mandatory inclusions** - FAILED
- Changes made: Added "CRITICAL - MANDATORY INCLUSIONS" section to main_cast.py prompt
- Expected result: Gatsby and Daisy extracted by main_cast with correct roles
- Actual result: Neither change took effect - Gatsby/Daisy still from supporting_cast
- Conclusion: Prompt-only fixes are not effective for this LLM

### Attempt 2 Fixes

**Fix 1: Post-processing character promotion (CRITICAL #1, #3)** - PARTIAL
- Changes made: Added Step 5.8 in `characters.py` to promote characters with ≥50 mentions
- Expected result: Gatsby and Daisy promoted to main_cast with role="supporting"
- Actual result: Role changed to "supporting" but ID unchanged, and role should be higher
- Conclusion: Promotion worked but threshold too conservative

**Fix 2: Non-sentient object filter (CRITICAL #5)** - SUCCESS ✓
- Changes made: Added Step 5.9 in `characters.py` to filter billboards/objects
- Expected result: Eckleburg removed from character list
- Actual result: Eckleburg correctly removed
- Conclusion: Fix worked as designed

**Fix 3: Always include first mention in profile generation (HIGH #4)** - UNKNOWN
- Changes made: Modified mention sampling in `analyzer.py` to always include first mention
- Expected result: Physical descriptions populated
- Actual result: Still 0/29 with physical_description
- Conclusion: Root cause is elsewhere - profile extraction itself is not extracting appearance data

---

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | Prompt-based main cast | `src/pipeline/character_extraction_v2/main_cast.py` | **No change** |
| 2 | Character promotion | `src/agents/characters.py` | **Partial** - role changed but not to correct level |
| 2 | Object filter | `src/agents/characters.py` | **Fixed** - Eckleburg removed |
| 2 | Profile sampling | `src/analyzer.py` | **No change** - still 0 descriptions |

**Pattern Detected:**
- Profile extraction is fundamentally not working - need to investigate the profile pipeline itself
- F6 reconciliation is creating issues (wrong canonical names, non-characters)
- Main cast LLM is unreliable, promotion is a workaround that needs tuning

---

## Root Cause Analysis

### Primary Failure: Profile Extraction (Character Profiles 4/10)
The profile pipeline IS generating personality data (9/29 have personality traits) but is NOT generating:
- Physical descriptions (0/29)
- Relationships (0/29)

This suggests the LLM prompt in profile extraction either:
1. Doesn't ask for these fields
2. Returns them in wrong format
3. Code doesn't save them correctly

**Investigation needed:** Read `src/pipeline/character_profiles.py` to understand:
- What fields does the prompt request?
- How are responses parsed and saved?
- Is there an appearance/physical_description field mismatch?

### Secondary Failure: Character Extraction (6/10)
Main cast extraction is unreliable. Supporting cast (NER-based) works but:
1. Uses first-seen name as canonical (often incomplete)
2. Roles are hardcoded as "minor" regardless of importance
3. F6 reconciliation adds non-characters from summaries

**Fix direction:**
1. Tune promotion thresholds (200+ mentions → protagonist, 100+ → main)
2. Add canonical name normalization (prefer full names from any source)
3. Add filter in F6 for generic/non-character patterns

---

## Next Action
**Phase:** awaiting_fix

Priority fixes for attempt 4:
1. **CRITICAL** - Investigate and fix profile extraction (physical_description, relationships)
2. **CRITICAL** - Fix canonical name handling (Daisy → Daisy Buchanan, Tom → Tom Buchanan)
3. **HIGH** - Tune promotion thresholds for role assignment
4. **HIGH** - Add F6 filter for non-character patterns
