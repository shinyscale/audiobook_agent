# Oracle Loop Escalation: american_sir

## Status: Requires Human Investigation

**Generated:** 2026-01-29 11:42:28
**Text:** american_sir
**Attempt:** 11
**Current Score:** 8.55
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
| 8 | 8.50 |
| 9 | 8.50 |
| 10 | 8.55 |
| 11 | 8.55 |

---

## Current Issues (from EVALUATION_STATE.md)

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

---

## Fix History (Recent Attempts)

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

**Phase:** awaiting_fix

Fix the same-name collision for "John":
1. When gathering evidence for "John" (the nephew), filter out backstory passages about the narrator's brother
2. Key signals:
   - Temporal: Past tense backstory → likely father; present action → likely nephew
   - Relationship: "my brother John", "poor John" → father; "the boy", "young John" → nephew
   - Context: If "John Donaldson" is a known character, bare "John" in past-tense backstory → attribute to John Donaldson

**Files to consider:**
- `src/pipeline/character_profiling/passage_gatherer.py` - evidence gathering logic
- `src/pipeline/character_profiling/name_disambiguator.py` - disambiguation logic (already exists)
- Possibly extend NameAmbiguityMap to handle short-form/long-form collision

**Test case:** After fix, "John" (nephew) evidence should include:
- "young John's note out of the scrap-basket"
- "all his charm were repeated in his son, but underlaid with a manliness"
- Evidence about ambulance driving, Croix de Guerre

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

