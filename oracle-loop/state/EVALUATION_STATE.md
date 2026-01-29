# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 12
- **Phase:** awaiting_fix
- **baseline_score:** 7.95
- **Competitive Mode:** single

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Latest Scores
- Structure Detection: 10/10 ✓
- Character Extraction: 9/10 ✓
- Character Profiles: 4/10 ✗ (FAILING - evidence for nephew has father's backstory)
- Chapter Summaries: 10/10 ✓
- Pronunciation Guide: 9/10 ✓
- HTML Presentation: 9/10 ✓
- **Overall: 8.65/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (Character Profiles at 4/10)

## Attempt 12 Analysis

### Why the Chapter-Range Prior FIX FAILED

The chapter-range prior couldn't work because:
1. **All characters are supporting cast** - IDs are `supporting_0`, `supporting_1`, etc.
2. **Supporting cast has empty `chapters_present`** - Line 2987 in `characters.py` sets `chapters_present=[]`
3. **Disambiguation signal has no data** - The prior checks `chapters_present` but it's always empty

### Root Cause (UNCHANGED)

**"John" in the backstory refers to the FATHER, not the nephew.**

Text structure:
- Positions 2000-5000: Narrator tells backstory about "my brother John" (the FATHER)
- Positions 11000+: Nephew's account where father is called "John Donaldson"

Evidence for "John" (nephew profile) still has:
- "John graduated from Yale" (pos 2005) → FATHER
- "John planned to live in Italy" (pos 2451) → FATHER
- "John died in an accident" (pos 3689) → FATHER's fake death
- "John had a two-year-old son" (pos 3909) → FATHER (the son IS the nephew!)

**What SHOULD be in nephew's profile:**
- WWI ambulance driver (age 18)
- Won Croix de Guerre
- Discovered John Donaldson (father) alive on Piave front
- "All John Donaldson's physical beauty...repeated in his son, but underlaid with a manliness"

## Current Issues (Priority Order)

### CRITICAL

1. **"John" profile contains father's backstory instead of nephew's story**
   - Problem: Evidence for "John" (the nephew) matches any "John" in the text, getting the father's backstory
   - Evidence: All 11 evidence statements describe the father (Yale, thriftless life, fake death, had a son)
   - Root cause: Father is called just "John" in backstory (pos 2000-5000), nephew is also "John"
   - Location: Evidence gathering in `src/pipeline/character_profiling/passage_gatherer.py` or `summary_evidence.py`
   - Fix approach: **SEE ESCALATION RECOMMENDATION BELOW**

### HIGH

2. **Relationships empty for all characters**
   - Problem: `relationships: {}` for all 4 characters
   - Evidence: Clear relationships exist (John grandson of Uncle Bill; John Donaldson brother of Uncle Bill)
   - Location: `src/pipeline/character_profiling/` relationship extraction

3. **Physical descriptions empty for all characters**
   - Problem: `appearance.summary: "unknown"` for all characters
   - Evidence: Text provides: "All John Donaldson's physical beauty, all his charm were repeated in his son, but underlaid with a manliness"
   - Location: Profile generation

### MEDIUM

4. **`chapters_present` not populated for supporting cast**
   - Problem: Line 2987 in `characters.py` sets `chapters_present=[]` for all supporting cast
   - Impact: Chapter-range disambiguation signal has no data to work with
   - Location: `src/agents/characters.py:2987`

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
| 11 | 8.55 | +0.60 | Narrator filter worked but "John" now has FATHER's backstory (5/10) |
| 12 | 8.65 | +0.70 | Chapter-range prior FAILED - supporting cast has no `chapters_present` data |

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
| 11 | Narrator perspective contamination filter | perspective_filter.py (NEW), pipeline.py, passage_gatherer.py, summary_evidence.py, identifier.py, generator.py | **PARTIAL** |
| 12 | Chapter-range prior + expanded context | passage_gatherer.py, name_disambiguator.py, summary_evidence.py, llm/client.py | **FAILED** - data dependency not met |

## Fix History Summary

**12 attempts have tried 6 different approaches to fix same-name evidence collision:**

1. **Post-processing merge fix** (attempt 1) - Fixed character extraction ✓
2. **Prompt engineering** (attempts 2, 3, 9) - No effect on evidence gathering
3. **Upstream pipeline changes** (attempts 4, 5, 6) - Caused regressions
4. **Main cast prompt fix** (attempt 7) - Fixed extraction ✓
5. **Filtering/disambiguation heuristics** (attempts 8, 10, 11, 12) - Partial or no effect
6. **Narrator filter** (attempt 11) - Fixed narrator contamination, revealed father/son collision ✓

## ESCALATION RECOMMENDATION

**This issue requires architectural change, not heuristic tuning.**

The problem: When two characters share a name, evidence gathering cannot distinguish them with text position, temporal markers, or chapter presence because:
1. Both characters are called "John" in their respective narrative sections
2. The backstory about "John" (father) dominates positions 2000-5000
3. Supporting cast characters don't have `chapters_present` populated

**Recommended architectural fix:**

**Option A: Pre-merge ambiguous references at extraction time**
- When "John" and "John Donaldson" are both detected
- And they share a relationship (chapter summary says "narrator's brother John" = "John Donaldson")
- Treat bare "John" in backstory as an alias for "John Donaldson"
- The nephew profile then gets only present-day "John" references

**Option B: Evidence attribution based on narrative context**
- Use chapter summary to identify which "John" is being discussed
- Summary says: "his late brother's son, John" (nephew) vs "John Donaldson" (father)
- Route evidence to correct profile based on summary's narrative structure

**Option C: Explicit same-name merge at profiling time**
- Detect when two profiles have the same short name
- Use generation context (backstory vs present action) to merge evidence correctly
- Apply to "John" (nephew) and "John Donaldson" (father) where backstory-John = John Donaldson

**Relevant code locations:**
- `src/pipeline/character_profiling/identifier.py` - character identification
- `src/agents/characters.py:2977-2995` - supporting cast conversion (populate `chapters_present`)
- `src/pipeline/character_profiling/summary_evidence.py` - evidence gathering
- `src/analyzer.py` - profile generation orchestration

## Next Action

**ESCALATE** - This issue has been attempted 12 times without resolution. The fix phase should:

1. Read `spec/oracle-loop-escalation-american_sir-20260129_*.prd.md` for prior escalation context
2. Consider generating a new escalation PRD if prior ones don't cover the architectural fix needed
3. Focus on Option A (pre-merge at extraction) or Option B (summary-guided attribution) as most promising

The current profiling pipeline cannot distinguish same-name characters with different temporal scopes without upstream changes to how character identity is tracked through the extraction→profiling pipeline.
