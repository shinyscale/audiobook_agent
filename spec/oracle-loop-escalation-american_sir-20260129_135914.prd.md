# Oracle Loop Escalation: american_sir

## Status: Requires Human Investigation

**Generated:** 2026-01-29 13:59:14
**Text:** american_sir
**Attempt:** 12
**Current Score:** 8.65
**Stuck Duration:** 4 consecutive attempts with score ±0.15

---

## Why This Escalation Was Triggered

The oracle loop has been stuck on the same score (±0.15) for 4 consecutive attempts. This indicates:

1. The fixes being attempted are not addressing the root cause
2. The root cause may be in a code layer the loop hasn't been examining
3. Human investigation is needed to identify blind spots

---

## Recent Score History

| Attempt | Score |
|---------|-------|
| 9 | 8.50 |
| 10 | 8.55 |
| 11 | 8.55 |
| 12 | 8.65 |

---

## Current Issues (from EVALUATION_STATE.md)

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

---

## Fix History (Recent Attempts)

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

---

## Code Analysis

### Files Modified During Fix Attempts (last 7 days)

```

```

### Files NOT Modified (Potential Blind Spots)

These key pipeline files have NOT been touched during fix attempts. The bug may be here:

```
src/ingestion/base.py
src/ingestion/refine.py
src/pipeline/chapter_detection/profiler.py
src/pipeline/chapter_detection/proposers/regex.py
src/pipeline/chapter_detection/proposers/llm.py
src/pipeline/chapter_detection/validator.py
src/pipeline/chapter_detection/consensus.py
src/pipeline/chapter_detection/pipeline.py
src/agents/structure.py
src/analyzer.py
```

**IMPORTANT:** When fixes in one layer don't work, the bug is often in an upstream layer:
- If `consensus.py` fixes don't work → check `profiler.py`, `proposers/`, or `ingestion/`
- If `character_extraction` fixes don't work → check `ingestion/` text normalization
- If structure detection fails → check if ingestion is destroying formatting

---

## Recommended Investigation Steps

1. **Check data flow from ingestion to detection:**
   ```bash
   # Verify source text has expected patterns
   grep -n "^[[:space:]]*V[[:space:]]*$" Test_Texts/american_sir.txt

   # Check what ingestion does to the text
   LOG_LEVEL=DEBUG python -c "
   from src.ingestion import ingest_document
   text = ingest_document('Test_Texts/american_sir.txt')
   # Check if patterns survive
   import re
   centered = re.findall(r'^\s{10,}[IVXLC]+\s*$', text, re.MULTILINE)
   print(f'Centered roman numerals after ingestion: {len(centered)}')
   print(centered[:5])
   "
   ```

2. **Run isolated pipeline tests:**
   ```bash
   # Test structure detection in isolation
   python -c "
   from src.pipeline.chapter_detection.pipeline import ChapterDetectionPipeline
   from src.pipeline.llm import LLMClient, LLMConfig

   with open('Test_Texts/american_sir.txt', 'r') as f:
       text = f.read()

   config = LLMConfig.ollama(model='qwen3:4b-instruct')
   pipeline = ChapterDetectionPipeline(llm_client=LLMClient(config))
   result = pipeline.run(text)

   for ch in result.chapters:
       print(f'{ch.index}: {ch.title}, {ch.word_count} words')
   "
   ```

3. **Compare isolated test vs full CLI:**
   - If isolated test passes but CLI fails, bug is in ingestion or agent layer
   - If both fail, bug is in the pipeline itself

4. **Add diagnostic logging to blind spot files:**
   - Add logging to ingestion showing text patterns before/after normalization
   - Add logging to profiler showing TOC detection and front_matter_end

---

## State Files for Reference

- `oracle-loop/state/EVALUATION_STATE.md` - Full evaluation state
- `oracle-loop/state/manifest.json` - Test manifest
- `oracle-loop/state/checkpoints.json` - Checkpoint history
- `oracle-loop/logs/` - Recent iteration logs

---

## Resolution

Once the root cause is identified and fixed:

1. Update this PRD with the resolution
2. Restart the oracle loop: `cd oracle-loop && ./oracle-loop.sh`
3. The loop will continue from where it left off

