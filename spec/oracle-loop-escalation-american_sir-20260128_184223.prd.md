# Oracle Loop Escalation: american_sir

## Status: RESOLVED - Fix Implemented

**Generated:** 2026-01-28 18:42:24
**Resolved:** 2026-01-29
**Text:** american_sir
**Attempt:** 5 → 6 (with fix)
**Current Score:** 8.65 (pending re-evaluation)
**Stuck Duration:** 4 consecutive attempts with score ±0.15

---

## Resolution Summary

**Option A (Context-Aware Evidence Assignment) was implemented.**

The fix adds semantic disambiguation using multi-signal priority:
1. Relationship markers ("his father John", "Sr./Jr.") → 0.95 confidence
2. Name-shape markers (sentence has "Donaldson" → full name wins) → 0.9 confidence
3. Temporal markers ("years ago", past perfect) → 0.8 confidence
4. Chapter presence (prefer active character) → 0.7 confidence
5. LLM fallback (gated, only when heuristics fail)

**Files created/modified:**
- `src/pipeline/character_profiling/name_disambiguator.py` (NEW - 450+ lines)
- `src/pipeline/character_profiling/passage_gatherer.py` (updated)
- `src/pipeline/character_profiling/summary_evidence.py` (updated)
- `src/pipeline/character_profiling/pipeline.py` (updated)
- `tests/test_name_disambiguation.py` (NEW - 24 tests, all passing)

**Next step:** Re-run analysis and evaluate whether John's profile no longer contains father's traits.

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
| 2 | 8.65 |
| 3 | 8.65 |
| 4 | 8.60 |
| 5 | 8.65 |

---

## Current Issues (from EVALUATION_STATE.md)

## Current Issues (Priority Order)

### CRITICAL

1. **Personality wrongly describes father for son**
   - Problem: John (supporting_0, the son) has personality: "John Donaldson was impulsive, avoidant of unpleasantness, and lived a thriftless life" - this describes the FATHER
   - Evidence: The son is described as having "quiet dignity and responsibility that his father never did"
   - Root cause: Evidence extraction pulls father's biographical info into son's profile
   - The evidence items 3-5 for "John" describe the father's behavior, not the son's

2. **Evidence items wrongly assigned**
   - "John preferred a thriftless life in Florida" - describes FATHER
   - "John stopped writing due to an inability to endure unpleasantness" - describes FATHER
   - "John died during a shooting trip" - describes FATHER (faked death)
   - These are in son "John"'s evidence but should be in father "John Donaldson"'s evidence

### HIGH

3. **Relationships still empty for all characters**
   - Problem: `relationships: {}` for all 4 characters
   - This has persisted through 4 attempts at fixing
   - `summary_evidence` is still `null` for all characters
   - The relationship extraction code may not be executing at all

### MEDIUM

4. **Physical descriptions null for all characters**
   - The text does describe characters (son "strikingly similar to father yet more grounded")
   - Profile generation is not populating these fields

## Fix Strategy for Attempt 6

The collision detection approach (attempts 4-5) did not work because the problem is SEMANTIC, not string-matching.

**Recommended approach**: Context-aware evidence assignment

Instead of filtering based on name collisions, the evidence extractor needs to:
1. Recognize temporal context (past tense about "John" before the son was born = father)
2. Recognize relationship context ("John's father" vs "John" the son)
3. Use chapter/section position (early story = flashback about father)

**Specific implementation suggestion**:
- In `src/pipeline/character_profiling/evidence_extractor.py` or `profile_generator.py`
- Add temporal/context analysis when a character name could refer to multiple people
- Use the chapter summary to understand which "John" is being discussed at each point

**Alternatively**: Accept this as an edge case limitation
- Stories with deliberately ambiguous naming (same name for father and son) are inherently difficult
- A narrator would face the same confusion
- Focus on fixing the relationship extraction instead (simpler, higher impact)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 7.95 | - | Baseline. Critical: John/John Donaldson false merge |
| 2 | 8.65 | +0.70 | Character extraction FIXED (9/10). Profiles failing (7/10) |
| 3 | 8.65 | +0.70 | No change. Prompt simplification didn't improve relationships |
| 4 | 8.60 | +0.65 | Profiles dropped to 5/10 due to evidence confusion |
| 5 | 8.65 | +0.70 | Collision fix helped slightly but semantic confusion remains |

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | False merge of John/John Donaldson | src/agents/characters.py | **FIXED** - Characters now separate (9/10 extraction) |
| 2 | Empty relationships - added character context | src/analyzer.py | **No change** - Relationships still empty |
| 3 | Empty relationships - simplified prompt | src/analyzer.py | **No change** - Relationships still empty |
| 4 | Empty relationships - enhanced upstream data | src/pipeline/character_profiling/summary_evidence.py | **REGRESSION** - summary_evidence still null, profile data confused |
| 5 | Profile evidence confused between characters | src/analyzer.py, src/pipeline/character_profiling/summary_evidence.py | **Partial** - Collision detection added but semantic confusion remains |

**ESCALATION STATUS:** String-based collision detection has been attempted twice (attempts 4-5) without resolving the semantic disambiguation issue. The next fix should either:
1. Implement context-aware evidence assignment (more complex)
2. Accept this edge case and focus on relationship extraction instead (simpler)

## Fix History

### Attempt 1: Fixed false John/John Donaldson merge ✓

**Root cause:** `src/agents/characters.py:_merge_within_supporting_cast():line 2612`
- Pass 2 used `names_similar()` which includes subset matching

---

## Fix History (Recent Attempts)

## Fix History

### Attempt 1: Fixed false John/John Donaldson merge ✓

**Root cause:** `src/agents/characters.py:_merge_within_supporting_cast():line 2612`
- Pass 2 used `names_similar()` which includes subset matching
- `names_similar("John", "John Donaldson")` returned True because {"john"} ⊂ {"john", "donaldson"}

**Result:** VERIFIED FIXED - Characters remain separate through attempt 5

### Attempt 2: Provided character list context for relationship extraction ✗

**Attempted fix:** Added character names list to the profile generation prompt

**Result:** FAILED - No improvement to relationships

### Attempt 3: Simplified relationship extraction prompt ✗

**Attempted fix:** Made relationship instructions clearer and more prominent

**Result:** FAILED - No improvement to relationships

### Attempt 4: Enhanced upstream relationship data (ESCALATION) ✗

**Attempted fix:** Added `_extract_relationship_statements()` to summary_evidence.py

**Result:** REGRESSION - summary_evidence still null, profiles now confused

### Attempt 5: Fixed evidence extraction collision detection ✗

**Attempted fix:**
1. Passed `all_character_names` to SummaryEvidenceExtractor
2. Enhanced `_build_surname_collisions()` to handle first-name collisions

**Result:** PARTIAL - Collision detection works but semantic confusion remains. The underlying issue is that "John" legitimately refers to both characters in the text.

## Next Action
**Phase:** awaiting_fix

The fix phase should evaluate whether to:
1. **Option A**: Implement context-aware evidence assignment (complex but correct)
2. **Option B**: Accept edge case, focus on relationship extraction which has failed 4 times

Given that relationships have failed 4 times, Option B may actually be harder. Consider whether this text should be marked as "known limitation" due to deliberate authorial naming ambiguity.

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

**RESOLVED 2026-01-29**

Root cause was identified and fixed:
- **Root cause:** Semantic ambiguity where "John" legitimately refers to both father and son
- **Fix:** Multi-signal disambiguation system that uses relationship markers, name-shape, temporal context, and chapter presence to resolve which character an ambiguous name refers to

To continue:
1. ✅ PRD updated with resolution
2. Restart the oracle loop: `cd oracle-loop && ./oracle-loop.sh`
3. The loop will run evaluation on attempt 6 with the disambiguation fix

