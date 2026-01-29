# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 12
- **Phase:** awaiting_evaluation
- **baseline_score:** 7.95
- **Competitive Mode:** single

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Latest Scores
- Structure Detection: 10/10 ✓
- Character Extraction: 9/10 ✓
- Character Profiles: 5/10 ✗ (FAILING - same-name collision, not narrator contamination)
- Chapter Summaries: 10/10 ✓
- Pronunciation Guide: 9/10 ✓
- HTML Presentation: 9/10 ✓
- **Overall: 8.55/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (1 category below threshold - Character Profiles at 5/10)

## Attempt 11 Analysis

### What the Narrator Filter FIXED ✓
The narrator perspective contamination filter worked correctly:
- "John" entry no longer has `is_narrator: true`
- Evidence no longer contains narrator self-descriptions ("I am stern, crabbed...")
- Uncle Bill profile is now separate and correctly describes the narrator

### What's STILL WRONG (Different Root Cause)

**The "John" (nephew) profile is populated with the FATHER's backstory, not the nephew's story.**

The evidence for "John" (supporting_0) includes:
- "John graduated from Yale with honors and prizes" → FATHER (backstory)
- "John planned to live in Italy since age seventeen" → FATHER
- "John went on a mining adventure in the south" → FATHER
- "John lived a thriftless life in Florida" → FATHER
- "John died in a fatal accident" → FATHER (fake death 15 years ago)
- "John had a two-year-old son" → FATHER (the son IS the nephew!)

The personality describes the FATHER: "impulsive, charming, financially irresponsible, dreamer"

**This is a DIFFERENT problem from narrator contamination:**
- The father is called just "John" in the narrator's early backstory (positions 2000-4800)
- The father is called "John Donaldson" in the nephew's later recounting (positions 11000+)
- The nephew is also named "John" (after his father)
- Evidence gathering matches "John" to ANY John in the text, getting the wrong person

**The NEPHEW's actual characteristics (NOT in the profile):**
- Teenage ambulance driver in WWI
- Won the Croix de Guerre for bravery
- Graduated from school (not Yale - that was his father)
- Discovers John Donaldson is his long-lost father
- Described as having "manliness, a force which poor John [father] never had"

### Why Previous Fixes Didn't Solve This

| Attempt | Fix | Why It Didn't Work for This Issue |
|---------|-----|-----------------------------------|
| 10 | Context-aware evidence disambiguation | Separated father/son based on name shape ("John" vs "John Donaldson"), but the father is ALSO called just "John" in the backstory |
| 11 | Narrator perspective filter | Fixed narrator "I did X" contamination, but this is name collision, not narrator perspective |

### Root Cause Analysis

**The text has a temporal name shift:**
- Early story (narrator's backstory): Father = "John" → Evidence gathered for "John" profile
- Late story (nephew's account): Father = "John Donaldson" → Evidence gathered for "John Donaldson" profile
- Throughout: Nephew = "John" or "young John" → SHOULD get nephew's profile

**The disambiguation needs to:**
1. Recognize when "John" in early backstory is being discussed as a PAST person (the narrator's brother)
2. vs "John" in the current action (the nephew doing things NOW)
3. Use temporal markers: past tense backstory vs present action
4. Use relationship markers: "my brother John" (father) vs "the boy John" / "young John" (nephew)

## Current Issues (Priority Order)

### CRITICAL

1. **"John" profile contains father's backstory instead of nephew's story**
   - Problem: Evidence for "John" (the nephew) matches any "John" in the text, predominantly getting the father's backstory which uses just "John"
   - Evidence: All 12 evidence statements describe the father (Yale graduate, thriftless life, fake death, had a son)
   - Location: `src/pipeline/character_profiling/passage_gatherer.py` or `summary_evidence.py` - name matching logic
   - Root cause: The father is called "John" in the narrator's backstory (early) and "John Donaldson" in the nephew's recounting (late). The nephew is also "John". Evidence for "John" grabs the father's backstory.
   - Fix approach:
     - **Option A**: Use temporal context - backstory about "John" (past tense, 15+ years ago) → attribute to John Donaldson
     - **Option B**: Use the NameAmbiguityMap to recognize "John" is ambiguous when "John Donaldson" exists, then use relationship/context clues
     - **Option C**: Cross-reference with the chapter summary which correctly says "narrator's brother John" (father) vs "the boy John" (nephew)
     - **Key insight**: When a character has both short form (John) and long form (John Donaldson), evidence using the short form in backstory context likely refers to the full-name character

### HIGH

2. **Relationships still empty for all characters**
   - Problem: `relationships: {}` for all 4 characters
   - Evidence: Clear relationships exist (John grandson of Uncle Bill, son of John Donaldson; John Donaldson brother of Uncle Bill)
   - Location: `src/pipeline/character_profiling/` relationship extraction
   - Fix: May require correctly attributing "John" evidence first

3. **Physical descriptions still "unknown" for all characters**
   - Problem: `appearance.summary: "unknown"` for all characters
   - Evidence: Text provides: "All John Donaldson's physical beauty, all his charm were repeated in his son, but underlaid with a manliness, a force"
   - Location: Profile generation in `src/analyzer.py`

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
| 8 | 8.50 | +0.55 | Substring filtering didn't fix profile confusion (3/10) |
| 9 | 8.50 | +0.55 | Disambiguation context in profile prompt didn't help (3/10) |
| 10 | 8.55 | +0.60 | John Donaldson profile now correct; "John" still has narrator data (5/10) |
| 11 | 8.55 | +0.60 | **Narrator filter worked** but "John" now has FATHER's backstory instead (5/10) |
| 12 | TBD | TBD | Chapter-range prior + larger context + surrounding sentences for temporal |

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | False merge of John/John Donaldson | src/agents/characters.py | **FIXED** at post-processing layer |
| 2 | Empty relationships - added character context | src/analyzer.py | **No change** |
| 3 | Empty relationships - simplified prompt | src/analyzer.py | **No change** |
| 4 | Empty relationships - enhanced upstream data | src/pipeline/character_profiling/summary_evidence.py | **REGRESSION** |
| 5 | Profile evidence confused between characters | src/analyzer.py, src/pipeline/character_profiling/summary_evidence.py | **Partial** |
| 6 | Semantic disambiguation for same-name chars | name_disambiguator.py, passage_gatherer.py, summary_evidence.py, pipeline.py | **REGRESSION** |
| 7 | CHARACTER_IDENTIFICATION_PROMPT family name guidance | src/pipeline/character_extraction_v2/main_cast.py | **FIXED** |
| 8 | Substring filtering in profile mention search | src/analyzer.py | **NO CHANGE** |
| 9 | Disambiguation context in profile generation prompt | src/analyzer.py | **NO CHANGE** |
| 10 | Context-aware evidence disambiguation in gathering | src/analyzer.py | **PARTIAL** |
| 11 | Narrator perspective contamination filter | perspective_filter.py (NEW), pipeline.py, passage_gatherer.py, summary_evidence.py, identifier.py, generator.py | **PARTIAL** - Fixed narrator contamination, but revealed same-name father/son collision |
| 12 | Chapter-range prior + expanded context for same-name disambiguation | passage_gatherer.py (context 500→2000), name_disambiguator.py (chapter-range signal, surrounding_context), summary_evidence.py (pass surrounding sentences), llm/client.py (temperature override) | **PENDING** |

## Key Insight for Fix Phase

**The narrator contamination filter WORKED - it exposed the underlying same-name collision problem.**

The story has THREE Johns:
1. **"John" (the father, past)** - Narrator's brother, called just "John" in the backstory
2. **"John Donaldson" (the father, present)** - Same person when his full name is revealed in the nephew's account
3. **"John" (the nephew, present)** - Named after his father, called "John" or "young John"

**Current problem:** Evidence gathering for character "John" (the nephew) matches:
- "John graduated from Yale" → Father in backstory (WRONG)
- "John lived thriftless life" → Father in backstory (WRONG)
- "young John's note" → Nephew (CORRECT)

**The fix needs to:**
1. Recognize that when "John Donaldson" exists as a full character, bare "John" references in BACKSTORY context likely refer to John Donaldson (the father)
2. Distinguish "John" in present action (nephew doing things) from "John" in past narration (father's history)
3. Use qualifiers: "young John" → nephew, "my brother John" → father, "John Donaldson" → father

## Fix History

### Attempt 1: Fixed false John/John Donaldson merge ✓ (POST-PROCESSING)
- **Result:** Characters separated, but profiles still confused

### Attempts 2-5: Profile/Relationship fixes
- Various attempts, see modification history
- Relationships still empty after all attempts

### Attempt 6: Context-Aware Evidence Disambiguation (WRONG LAYER)
- **Result:** REGRESSION - Fixed profile layer but broke extraction layer

### Attempt 7: Fixed CHARACTER_IDENTIFICATION_PROMPT for family name overlap ✓
- **Modified:** `src/pipeline/character_extraction_v2/main_cast.py` lines 77-86
- **Result:** FIXED - "John" and "John Donaldson" now correctly separate

### Attempts 8-9: Profile disambiguation attempts
- **Result:** NO IMPROVEMENT - Evidence already gathered incorrectly

### Attempt 10: Context-aware evidence disambiguation
- **Result:** PARTIAL - Separated father/son when full name used, but not when "John" alone is used

### Attempt 11: Narrator perspective contamination filter ✓
- **Result:** PARTIAL SUCCESS - Fixed narrator "I did X" contamination
- **New issue revealed:** Father's backstory (using just "John") still attributed to nephew's profile
- **This is progress:** We've eliminated narrator contamination and can now see the pure same-name collision problem

## Next Action

**Phase:** awaiting_evaluation

**Attempt 12 analysis completed** - Pipeline ran with enhanced same-name disambiguation:

1. **Larger passage context (2000 chars)** - `passage_gatherer.py`
   - Increased from 500 to 2000 chars around each mention
   - More context helps capture nearby identity cues

2. **Chapter-range prior (0.85 confidence)** - `name_disambiguator.py`
   - Uses `chapters_present` from IdentifiedCharacter
   - If only one candidate appears in the current chapter, prefer them
   - Key for father (early chapters) vs nephew (later chapters)

3. **Surrounding context for temporal markers** - `name_disambiguator.py`, `summary_evidence.py`
   - Looks at 2 sentences before target for temporal cues
   - "Years ago... John graduated" → temporal marker spans sentences

4. **Low temperature (0.1) for LLM disambiguation** - `llm/client.py`
   - Added per-call temperature override
   - Classification tasks use low temp for deterministic results

**Files modified:**
- `src/pipeline/character_profiling/passage_gatherer.py` - context_window 500→2000
- `src/pipeline/character_profiling/name_disambiguator.py` - chapter-range signal, surrounding_context, stats
- `src/pipeline/character_profiling/summary_evidence.py` - pass surrounding sentences to disambiguator
- `src/llm/client.py` - temperature override parameter

**Test case:** After fix, "John" (nephew) evidence should include:
- "young John's note out of the scrap-basket"
- "all his charm were repeated in his son, but underlaid with a manliness"
- Evidence about ambulance driving, Croix de Guerre

**Expected improvement:** Chapter-range prior should correctly attribute:
- Early chapter "John" references → John Donaldson (father appears in ch 1-2 backstory)
- Later chapter "John" references → John (nephew appears in ch 3+ present-day action)
