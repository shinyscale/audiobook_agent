# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 8
- **Phase:** awaiting_analysis
- **baseline_score:** 7.95
- **Competitive Mode:** single

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Latest Scores
- Structure Detection: 10/10 ✓
- Character Extraction: 9/10 ✓ (FIXED! John and John Donaldson now separate)
- Character Profiles: 4/10 ✗ (FAILING - profile data confused between father/son)
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 9/10 ✓
- HTML Presentation: 9/10 ✓
- **Overall: 8.45/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (1 category below threshold - Character Profiles)

## Analysis of Attempt 7 Results

**MAJOR PROGRESS**: Character extraction fix WORKED - "John" and "John Donaldson" are now correctly separated as two distinct characters.

### What's Working Now
1. Character EXTRACTION is correct - 4 characters, properly separated
2. Uncle Bill correctly identified as narrator with alias "Bill"
3. Chapter summary is excellent
4. Pronunciation guide has good coverage with IPA

### What's Still Broken
The PROFILE GENERATION stage is confusing evidence between John (son) and John Donaldson (father):

**Evidence of profile confusion:**

1. **John (the son) has FATHER's traits:**
   - Age: "middle-aged" - WRONG (John is ~17-18 at school commencement)
   - Personality: "John Donaldson was impulsive, avoidant of discomfort" - FATHER's description
   - Description: "deceased man" - FATHER died, not son

2. **John Donaldson (the father) has SON's traits:**
   - Appearance: "Physically resembles his father" - This describes the SON, not father

3. **Relationships empty for ALL characters** - Uncle/nephew, father/son not captured

### Root Cause Analysis

The profile generation in `src/pipeline/character_profiling/` is:
1. Extracting passages that mention "John" or "John Donaldson"
2. Failing to disambiguate which "John" is being described
3. Attributing evidence to wrong character based on substring matching

The existing `name_disambiguator.py` (added in attempt 6) is not being used effectively, OR the LLM in profile generation is ignoring disambiguation signals.

## Current Issues (Priority Order)

### CRITICAL

1. **Profile evidence crossed between John and John Donaldson**
   - Problem: Son (John) has father's profile data; father has some of son's data
   - Evidence:
     - John's age is "middle-aged" (should be ~18, graduating school)
     - John's personality says "John Donaldson was impulsive" (father's traits)
     - John's description says "deceased man" (father died, not son)
   - Location: `src/pipeline/character_profiling/` - evidence attribution
   - Root cause: Passages mentioning "John" being attributed to wrong character
   - Fix approach: Profile generation must use the same disambiguation signals as extraction:
     - "John" alone = the son (young man, letter writer, ambulance driver)
     - "John Donaldson" = the father (deceased, fled, met in Italy)

### HIGH

2. **Relationships empty for all characters**
   - Problem: `relationships: {}` for all 4 characters
   - Evidence:
     - John Donaldson is John's father (explicitly stated in summary)
     - Uncle Bill is John's great-uncle (stated in text)
     - Joe Barron is John's fellow ambulance driver
   - Location: `src/pipeline/character_profiling/` - relationship extraction
   - Fix: After profile confusion is fixed, verify relationship extraction works

### MEDIUM

3. **Physical descriptions null for all characters**
   - Problem: `physical_description: null` but `appearance.summary` has data
   - Evidence: Father was described as having "physical beauty" and "charm"
   - This may be a field mapping issue rather than extraction failure

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
| 8 | Profile mention search substring filtering | src/analyzer.py | FIX APPLIED - mentions now avoid "John" in "John Donaldson" |

## Fix Strategy for Attempt 8

**Target**: Profile generation disambiguation

The character EXTRACTION now correctly separates John and John Donaldson. But the PROFILE GENERATION assigns evidence to the wrong character.

**Key insight**: When extracting profiles, the system must distinguish:
- **"John"** (no surname) → the SON (young, letter writer, ambulance driver)
- **"John Donaldson"** → the FATHER (older, deceased, found in Italy)

**The disambiguation signals are available:**
1. Chapter summaries correctly list "John" and "John Donaldson" as separate characters_present
2. The plot summary describes their relationship
3. Context words: "father", "son", "his father John Donaldson"

**Approaches to try:**
1. Check if `name_disambiguator.py` is being invoked during profile generation
2. If it is, check if its signals are being honored by the LLM
3. If not, add explicit disambiguation in the profile extraction prompt:
   - "When the text mentions 'John' without 'Donaldson', attribute to the younger character"
   - "When the text mentions 'John Donaldson' or discusses someone deceased/fleeing, attribute to the father"

**File to investigate:** `src/pipeline/character_profiling/pipeline.py` - check how profiles are generated and whether disambiguation is applied.

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
- **New issue:** Profile generation still confuses evidence between them

### Attempt 8: Fixed profile mention search to avoid substring matches
- **Root cause:** Profile generation regex `\bJohn\b` matched BOTH "John" (son) and "John" in "John Donaldson" (father)
- **Modified:** `src/analyzer.py` lines 2304-2310 → added substring filtering logic
- **Fix:** When searching for character mentions during profile generation, filter out matches that are part of a longer character name
- **Example:** "John" now only matches standalone "John", NOT "John" in "John Donaldson"
- **Smoke test:** PASS - Verified with synthetic test that "John" correctly excludes "John Donaldson" matches
- **Universality:** Yes - helps ANY book with substring name overlaps (e.g., "Ames" vs "Cathy Ames", "José" vs "José Arcadio")

## Next Action
**Phase:** awaiting_analysis

Re-run analysis to verify profile generation correctly attributes evidence to John (son) vs John Donaldson (father).
