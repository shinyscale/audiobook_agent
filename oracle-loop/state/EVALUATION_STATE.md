# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 8
- **Phase:** awaiting_fix
- **baseline_score:** 7.95
- **Competitive Mode:** single

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Latest Scores
- Structure Detection: 10/10 ✓
- Character Extraction: 9/10 ✓
- Character Profiles: 3/10 ✗ (FAILING - Profile data completely inverted between John and John Donaldson)
- Chapter Summaries: 10/10 ✓
- Pronunciation Guide: 9/10 ✓
- HTML Presentation: 9/10 ✓
- **Overall: 8.50/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (1 category below threshold - Character Profiles at 3/10)

## Analysis of Attempt 8 Results

**FIX DID NOT WORK**: The substring filtering fix (filtering "John" matches inside "John Donaldson") did NOT solve the profile confusion problem.

### Evidence of Continued Profile Confusion

**John (the son) has FATHER's profile data:**
1. Personality says "impulsive, avoids unpleasantness, thriftless" - These are the FATHER's traits (he embezzled money and fled)
2. Evidence says "John had a lifelong dream to live in Italy" - This was the FATHER (he fled to Italy)
3. Evidence says "John avoided confrontation and stopped communicating after a financial incident" - This was the FATHER (embezzlement)
4. Evidence says "John died in a hunting accident, possibly suicide" - The FATHER died, the son survived!

**John Donaldson (the father) has SON's profile data:**
1. Description says "John Donaldson is a young man who served as a driver on the Piave front" - The SON was the ambulance driver, not the father!
2. Appearance says "towering stature", "young magnificence" - This describes the SON
3. "Resembles his father's physical beauty" - This describes the SON (who resembles HIS father), not the father himself

### Why the Fix Didn't Work

The substring filtering only prevents `\bJohn\b` from matching the "John" in "John Donaldson" when searching for mentions. But the profile generation prompt sends ALL evidence about both characters to the LLM, which then confuses them semantically.

The LLM sees passages like:
- "John had a dream to live in Italy" (about father, pre-flee)
- "John wrote asking me to come to commencement" (about son)

Without context about WHICH John is being discussed, the LLM assigns traits randomly.

### Root Cause

The profile generation stage in `src/pipeline/character_profiling/` is NOT using the disambiguation signals that are available:
1. The chapter summary correctly identifies both characters
2. The text provides context clues (commencement = son, Italy/fleeing = father)

The profile extraction prompt needs to:
1. Tell the LLM that "John" (alone) = the son (young, letter writer, ambulance driver)
2. Tell the LLM that "John Donaldson" = the father (older, deceased, fled to Italy)
3. OR pass the disambiguation as part of the character context

## Current Issues (Priority Order)

### CRITICAL

1. **Profile evidence completely inverted between John and John Donaldson**
   - Problem: Son has father's traits (impulsive, died, lived in Italy); father has son's traits (young ambulance driver)
   - Evidence:
     - John's personality: "impulsive, avoids unpleasantness, thriftless" → FATHER's traits
     - John's evidence: "died in hunting accident" → FATHER died, not son
     - John Donaldson's description: "young man who served as a driver" → SON was the driver
   - Location: `src/pipeline/character_profiling/` or `src/analyzer.py` profile generation stage
   - Root cause: LLM cannot distinguish passages about "John" (son) from passages about "John Donaldson" (father) without explicit guidance
   - Fix approach: **The profile extraction prompt must include character-specific disambiguation context**
     - Option A: Include character descriptions from extraction in profile prompt
     - Option B: Include the chapter summary (which correctly identifies both) as context
     - Option C: Add explicit rules: "For 'John' without surname: young man, school commencement, ambulance driver. For 'John Donaldson': older man, deceased, fled America."

### HIGH

2. **Relationships still empty for all characters**
   - Problem: `relationships: {}` for all 4 characters
   - Evidence: Clear relationships in text:
     - John Donaldson is John's father
     - Uncle Bill is John's great-uncle/guardian
     - Joe Barron is John's fellow ambulance driver
   - Location: `src/pipeline/character_profiling/` relationship extraction
   - Fix: This may be fixed once profile confusion is resolved

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 7.95 | - | Baseline. Critical: John/John Donaldson false merge |
| 2 | 8.65 | +0.70 | Character extraction FIXED (9/10). Profiles failing (7/10) |
| 3 | 8.65 | +0.70 | No change. Prompt simplification didn't improve relationships |
| 4 | 8.60 | +0.65 | Profiles dropped to 5/10 due to evidence confusion |
| 5 | 8.65 | +0.70 | Collision fix helped slightly but semantic confusion remains |
| 6 | 7.15 | -0.80 | **REGRESSION**: Character extraction broke (4/10) |
| 7 | 8.45 | +0.50 | Character extraction FIXED (9/10). Profiles still confused (4/10) |
| 8 | 8.50 | +0.55 | **NO IMPROVEMENT** - Substring filtering didn't fix profile confusion (3/10) |

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | False merge of John/John Donaldson | src/agents/characters.py | **FIXED** at post-processing layer |
| 2 | Empty relationships - added character context | src/analyzer.py | **No change** - Relationships still empty |
| 3 | Empty relationships - simplified prompt | src/analyzer.py | **No change** - Relationships still empty |
| 4 | Empty relationships - enhanced upstream data | src/pipeline/character_profiling/summary_evidence.py | **REGRESSION** - summary_evidence still null, profile data confused |
| 5 | Profile evidence confused between characters | src/analyzer.py, src/pipeline/character_profiling/summary_evidence.py | **Partial** - Collision detection added but semantic confusion remains |
| 6 | Semantic disambiguation for same-name chars | name_disambiguator.py (NEW), passage_gatherer.py, summary_evidence.py, pipeline.py | **REGRESSION** - Fixed wrong layer; extraction now merging |
| 7 | Character extraction V2 prompt - family name guidance | src/pipeline/character_extraction_v2/main_cast.py | **FIXED** - Two Johns now extracted separately |
| 8 | Profile mention search substring filtering | src/analyzer.py | **NO CHANGE** - Did not fix semantic confusion in profile generation |

## Fix Strategy for Attempt 9

**Target**: Profile generation prompt must include character disambiguation context

The substring filtering approach (attempt 8) was necessary but not sufficient. The LLM still cannot distinguish between passages discussing the father vs the son without explicit guidance about WHO each character is.

**The key insight**: The chapter summary ALREADY correctly distinguishes them:
- "his deceased brother's grandson, John, who asks him to attend his school commencement"
- "his beloved cousin John Donaldson—whose financial ruin and eventual death left the narrator as guardian"

**Approach**: When generating profiles, include character-specific context from the extraction/summary:

For John (son):
- "John is the young grandson/nephew who writes asking for help"
- "He joins the ambulance service, graduates from school"
- Passages about commencement, letters, ambulance driving → attribute to John

For John Donaldson (father):
- "John Donaldson is the father who embezzled money and fled to Italy"
- "He died during WWI as a stretcher-bearer"
- Passages about fleeing, financial ruin, death in Italy → attribute to John Donaldson

**Files to investigate:**
1. `src/analyzer.py` - profile generation stage (~line 2300+)
2. `src/pipeline/character_profiling/pipeline.py` - how profiles are built
3. Check if the chapter summary is available to pass as context

**This is NOT a keyword list violation** - we're passing existing, extracted context to help the LLM disambiguate, not hardcoding book-specific logic.

## Fix History

### Attempt 1: Fixed false John/John Donaldson merge ✓ (POST-PROCESSING)
- **Result:** Characters separated at post-processing, but LLM later merged them upstream

### Attempts 2-5: Profile/Relationship fixes
- Various attempts, see modification history
- Relationships still empty after all attempts

### Attempt 6: Context-Aware Evidence Disambiguation (WRONG LAYER)
- **Result:** REGRESSION - Fixed profile layer but broke extraction layer

### Attempt 7: Fixed CHARACTER_IDENTIFICATION_PROMPT for family name overlap ✓
- **Modified:** `src/pipeline/character_extraction_v2/main_cast.py` lines 77-86
- **Result:** FIXED - "John" and "John Donaldson" now correctly separate

### Attempt 8: Substring filtering in profile mention search
- **Modified:** `src/analyzer.py` lines 2304-2310
- **Result:** NO IMPROVEMENT - Profile data still inverted between John and John Donaldson
- **Why it failed:** Substring filtering prevents matching "John" in "John Donaldson", but the LLM still semantically confuses which passages describe which character

## Next Action
**Phase:** awaiting_fix

Run PROMPT_fix.md to add character context/disambiguation to the profile generation prompt. The LLM needs to know WHO each "John" character is before attributing evidence to their profiles.
