# Oracle Loop Escalation: american_sir

## Status: Requires Human Investigation

**Generated:** 2026-01-29 09:37:32
**Text:** american_sir
**Attempt:** 10
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
| 7 | 8.45 |
| 8 | 8.50 |
| 9 | 8.50 |
| 10 | 8.55 |

---

## Current Issues (from EVALUATION_STATE.md)

## Current Issues (Priority Order)

### CRITICAL

1. **"John" character entry contains narrator data instead of nephew data**
   - Problem: The character "John" (the teenage nephew) is populated with the NARRATOR's evidence and personality
   - Evidence: `is_narrator: true` on "John" entry, evidence says "The narrator is the same person who signed the letter as 'Uncle Bill'"
   - Location: Profile generation in `src/analyzer.py` - evidence gathering for "John" found narrator-perspective statements
   - Root cause: When searching for evidence about character "John", the system matched first-person narrator statements that mention "John" (as a reference), rather than passages ABOUT John as a character
   - Fix approach:
     - **Option A**: Check if gathered evidence is about the character (third-person) vs narrator talking TO/ABOUT the character (first-person)
     - **Option B**: Use the existing character descriptions/roles to filter - if a character is NOT marked as narrator, exclude narrator-perspective evidence
     - **Option C**: Cross-reference with chapter summary which correctly distinguishes "Narrator (Uncle Bill)" from "John Donaldson (the nephew)"

### HIGH

2. **Relationships still empty for all characters**
   - Problem: `relationships: {}` for all 4 characters
   - Evidence: Clear relationships exist:
     - John (nephew) is grandson of Uncle Bill
     - John (nephew) is son of John Donaldson
     - John Donaldson is brother of Uncle Bill
     - Joe Barron is fellow ambulance driver with John (nephew)
   - Location: `src/pipeline/character_profiling/` relationship extraction
   - Fix: May require correctly identifying which John is which before relationships can be derived

3. **Physical descriptions empty for all characters**
   - Problem: `physical_description: null` or `appearance.summary: "unknown"` for all characters
   - Evidence: Text provides descriptions:
     - John (nephew): resembles his father, has "charm"
     - John Donaldson (father): "shabby", "worn appearance", "physical beauty"
     - Uncle Bill: self-describes as elderly
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
| 8 | 8.50 | +0.55 | **NO IMPROVEMENT** - Substring filtering didn't fix profile confusion (3/10) |
| 9 | 8.50 | +0.55 | **NO IMPROVEMENT** - Disambiguation context in profile prompt didn't help (3/10) |
| 10 | 8.55 | +0.60 | **MINOR IMPROVEMENT** - John Donaldson profile now correct; "John" still has narrator data (5/10) |

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
| 9 | Disambiguation context in profile generation prompt | src/analyzer.py | **NO CHANGE** - Evidence already gathered incorrectly before prompt is used |
| 10 | Context-aware evidence disambiguation in gathering | src/analyzer.py | **PARTIAL** - John Donaldson now correct; "John" still has narrator data |

## Key Insight for Fix Phase

**The attempt 10 fix was in the right direction but incomplete.**

The evidence disambiguation helped separate "John" from "John Donaldson" (father vs son based on name components). But it didn't handle:
- **Narrator perspective contamination**: Evidence gathering for "John" found first-person narrator statements ABOUT John, not statements about John AS a character

**New approach needed:**
1. When gathering evidence for a character who is NOT the narrator
2. Filter out passages where the evidence is from narrator's first-person perspective
3. OR: Check if the passage describes the character (third person) vs addresses/mentions the character (narrator speaking TO or ABOUT them)

**Example of wrong evidence currently in "John" profile:**
- "The narrator repaid John's debts and hushed up a scandal" - This is ABOUT John from narrator's perspective, but it describes the NARRATOR's action, not John's character

**Example of correct evidence that SHOULD be in "John" profile:**
- "he encounters a mysterious, shabby American civilian" - This is John (nephew) AS a character acting in the story

---

## Fix History (Recent Attempts)

## Fix History

### Attempt 1: Fixed false John/John Donaldson merge ✓ (POST-PROCESSING)
- **Result:** Characters separated at post-processing, but profiles still confused

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

### Attempt 9: Character disambiguation context in profile generation prompt
- **Modified:** `src/analyzer.py` lines 2468-2516
- **Result:** NO IMPROVEMENT - Evidence already gathered incorrectly before prompt is used

### Attempt 10: Context-aware evidence disambiguation in gathering stage
- **Modified:** `src/analyzer.py` lines 2320-2355
- **Result:** PARTIAL - John Donaldson (father) profile now correct; "John" (nephew) still populated with narrator data
- **Why partial success:** Disambiguation separates father/son, but doesn't separate narrator-perspective evidence from character-perspective evidence

## Next Action

**Phase:** awaiting_fix

Fix the narrator perspective contamination in evidence gathering:
- When gathering evidence for character "John" who is NOT the narrator
- Filter out evidence that describes the NARRATOR's actions/thoughts
- Only include evidence that describes JOHN's actions/thoughts/characteristics

The chapter summary correctly identifies "Narrator (Uncle Bill)" and "John Donaldson (the nephew)" as separate - use this as a guide for evidence attribution.

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

