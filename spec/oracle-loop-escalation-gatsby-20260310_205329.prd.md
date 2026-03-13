# Oracle Loop Escalation: gatsby

## Status: Requires Human Investigation

**Generated:** 2026-03-10 20:53:29
**Text:** gatsby
**Attempt:** 18
**Current Score:** 8.45
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
| 15 | 8.53 |
| 16 | 8.53 |
| 17 | 8.53 |
| 18 | 8.45 |

---

## Current Issues (from EVALUATION_STATE.md)

## Current Issues (Priority Order)

### HIGH

1. **`verify_relationships_from_text` CREATES false spousal labels from keyword proximity** [Profiles]
   - Problem: When characters A and B co-occur near "husband"/"wife" text, the function assigns spousal labels even when the keyword refers to character C (not present in that text window). Removing the third-party check (Fix TT) made this WORSE.
   - Evidence: Nick↔Myrtle "husband/wife" (keyword refers to George), George↔Catherine "husband/wife" (keyword refers to George↔Myrtle relationship)
   - Root cause: The text-evidence step should NOT create spousal labels that the LLM profiler didn't suggest. It should only VALIDATE/UPGRADE existing labels.
   - Location: `src/pipeline/character_profiling/post_corrections.py` — `verify_relationships_from_text`
   - **Fix approach (Fix VV): Restrict spousal upgrades to LLM-confirmed pairs only.**
     In `verify_relationships_from_text`, when a spousal keyword is found in a co-mention window for pair A↔B:
     - Check if the LLM profiler's ORIGINAL output (before post-corrections) included a spousal or romantic label for A↔B
     - If the LLM gave "associated", "neighbor", or nothing for A↔B, do NOT upgrade to "husband"/"wife"
     - If the LLM gave "romantic interest", "lover", "husband", "wife", or similar, THEN the text evidence can confirm/upgrade to spousal
     - This prevents the text-evidence step from fabricating relationships the LLM didn't detect
   - Alternative: **Re-add the third-party check with a wider window (100-150 chars)** and ALSO keep competitive selection. The combination should work: third-party check blocks most false attributions, competitive selection handles the remaining Tom-vs-Gatsby competition.

2. **George↔Myrtle "associated" instead of "husband"/"wife"** [Profiles]
   - Problem: The novel's most important murdered couple has a generic label
   - Evidence: George kills himself after Myrtle's death. "Her husband" appears dozens of times
   - Root cause: Competitive selection may be awarding George's spousal slot to Catherine instead of Myrtle
   - Fix: Fixing issue #1 (preventing false George↔Catherine spousal) should free up the spousal label for George↔Myrtle

3. **Nick↔Daisy "brother"/"sister" instead of "cousin"** [Profiles]
   - Problem: Nick is Daisy's second cousin once removed, not her brother
   - Evidence: Ch. 1: "Daisy was my second cousin once removed"
   - Root cause: Likely LLM profiler output — the LLM chose "brother/sister" instead of "cousin"
   - Location: LLM profiler prompt or `_infer_rel` keyword matching
   - Fix: If the text contains "cousin" near a character pair, prefer "cousin" over "brother"/"sister". Or: add "cousin" as a valid family relationship label in the profiler prompt.

### MEDIUM

4. **Gatsby→Klipspringer/Lucille "employee" — wrong label** [Profiles]
   - Klipspringer is a freeloader, Lucille is a party guest. Neither is employed by Gatsby.
   - Impact: Minor characters, low severity

5. **Green light has Owl Eyes aliases ("The drunken man in the library", "the library")** [Identity Resolution]
   - These aliases belong to Owl Eyes, not the green light
   - Persistent issue across multiple attempts
   - Impact: Low — symbolic entity, minor confusion

6. **"Man with owl-eyed glasses" and "Owl Eyes" are separate F6 entries** [Identity Resolution]
   - These refer to the same character; should be merged
   - Impact: Low — both have 1 mention

7. **Nick Carraway physical_description: null** [Profiles]
   - Persistent — Nick describes himself minimally

### LOW

8. **Chapter I summary repeats "Nick Carraway, Nick Carraway"** [Summaries]
   - Minor formatting issue in summary text

## Fix Guidance for Attempt 19

**Focus ONLY on getting Character Profiles from 7/10 to 8/10.** All other categories pass.

**The spousal whack-a-mole is now in its 5th iteration (attempts 14-18). Each fix solves the targeted pair but creates new false spousals on different pairs. The root cause is clear: `verify_relationships_from_text` should NOT create new spousal labels — it should only validate existing ones.**

**Fix VV (HIGH — addresses issues #1, #2): Restrict spousal creation in `verify_relationships_from_text`**

The function currently detects "husband"/"wife" keywords in co-mention windows and UPGRADES any relationship to spousal. This is wrong — it should only CONFIRM spousal labels that the LLM profiler already suggested.

Implementation:
1. In `verify_relationships_from_text`, track which relationships came from the LLM profiler's original output vs. post-correction additions
2. When a spousal keyword is found in a co-mention window for pair A↔B, check if the LLM's original label for A↔B was romantic or spousal (e.g., "husband", "wife", "spouse", "romantic interest", "lover", "fiancé/fiancée")
3. If the LLM gave a non-romantic label ("associated", "neighbor", "friend", etc.) or no label at all, do NOT upgrade to "husband"/"wife" — keep the original label
4. This prevents Nick↔Myrtle (LLM: no relationship), George↔Catherine (LLM: no relationship) from getting false spousal labels
5. Tom↔Daisy should still work because the LLM profiler likely gives them a spousal or romantic label already

**Alternative simpler approach**: Re-add the third-party check but with a MUCH wider window (150 chars instead of 30/50). Keep competitive selection. The wider window should catch cases where the actual spouse's name appears further from the keyword.

**Fix WW (MEDIUM — addresses issue #3): Cousin label support**
If `_infer_rel` detects "cousin" keyword evidence, use "cousin" instead of "brother"/"sister". Add "cousin" to the set of valid family relationship types.

## Fix History

### Attempt 2 fixes
- **Fix A: STEP 4.26 narrator threshold** — INEFFECTIVE (wrong layer)
- **Fix B: STEP 5.11 promotion** — INEFFECTIVE (code not firing)

---

## Fix History (Recent Attempts)

## Fix History

### Attempt 2 fixes
- **Fix A: STEP 4.26 narrator threshold** — INEFFECTIVE (wrong layer)
- **Fix B: STEP 5.11 promotion** — INEFFECTIVE (code not firing)
- **Fix C: Relationship label override guard** — PARTIALLY EFFECTIVE

### Attempt 3 fixes
- **Fix D: Narrator layered defense (narrator.py + characters.py)** — EFFECTIVE ✓ (but regressed in attempt 4)
- **Fix E: "colleague" forbidden in profiler prompt** — INEFFECTIVE (LLM ignores forbidden list)
- **Fix F: STEP 5.11 diagnostic logging** — ADDED but promotion still didn't fire

### Attempt 4 fixes
- **Fix G: Role safety net in analyzer.py** — PARTIALLY EFFECTIVE (Gatsby promoted ✓, but caused narrator regression and role inflation)
- **Fix H: "colleague" post-processing filter** — COMPLETELY INEFFECTIVE (198 "colleague" entries remain)

### Attempt 5 fixes
- **Fix I: Relative mention guard in narrator.py** — EFFECTIVE ✓
- **Fix J: Step 6.6 narrator fallback minimum raised to 20** — EFFECTIVE ✓
- **Fix K: Colleague substring filter** — INEFFECTIVE (192 remain, down from 198)

### Attempt 6 fixes
- **Fix L: Disabled `add_text_window_cooccurrence_relationships()` in post_corrections.py** — **EFFECTIVE ✓** (192→30 colleague entries)
- **Fix M: Block " and " pair-reference aliases in verify_aliases()** — **EFFECTIVE ✓** ("Tom and Daisy" removed)

### Attempt 7 fixes
- **Fix N: `_VAGUE_REL_LABELS` NameError** — **EFFECTIVE ✓** (Jordan profile generates)
- **Fix O: Spouse evidence window 500→150 chars** — **PARTIALLY EFFECTIVE** (47→23 wrong spouse labels)
- **Fix P: Speech patterns prompt** — **COMPLETELY FAILED** (0/33 still) — Note: voice_guidance field was populated all along; evaluator checked wrong field name
- **Fix Q: STEP 5.6.9 alias absorption** — **FAILED** (Wolfsheim still duplicated)

### Attempt 8 fixes
- **Fix R: Canonical rename (James Gatz → Gatsby)** — **EFFECTIVE ✓** (Gatsby promoted to main_cast protagonist)
- **Fix S: One-spouse invariant** — **PARTIALLY EFFECTIVE** (23→10 spousal labels, but 6 still wrong)
- **Fix T: Colleague → associated** — **EFFECTIVE ✓** (colleague count: 0)
- **Fix U: Second-pass alias absorption (STEP 5.9.9)** — **PARTIALLY EFFECTIVE** (main Wolfshiem entry has 32 mentions, but 2 extra entries remain)

### Attempt 9 fixes
- **Fix V: Rule 0.5b person/non-person mismatch** — **EFFECTIVE ✓** (green light and Owl Eyes separated)
- **Fix W: Reciprocal spouse validation** — **PARTIALLY EFFECTIVE** (10→6 spousal labels; 4 removed, but Gatsby↔Jordan and Myrtle gender wrong persist)
- **Fix X: Fuzzy Wolfsheim dedup** — **EFFECTIVE ✓** (3 entries → 1) — BUT REGRESSED in attempt 10
- **Fix Y: F6 proper-noun filter** — **EFFECTIVE ✓** (6 clutter entries removed)
- **Fix Z: Daisy Fay maiden-name match** — **EFFECTIVE ✓** (Daisy Fay → alias of Daisy)

### Attempt 10 fixes
- **Fix AA: STEP 3.95b Pattern C/D guard** — **EFFECTIVE ✓** (Henry C. Gatz dedup)
- **Fix BB: Spousal text-evidence check** — **EFFECTIVE ✓** (Gatsby↔Jordan spousal removed)
- **Fix CC: Alias dedup** — **EFFECTIVE ✓** (Jordan duplicate alias removed)
- **Fix DD: Possessive-reference blocker Rule 0.5c** — **EFFECTIVE ✓** (Buchanans' house removed)

### Attempt 11 fixes
- **Fix EE: Max-mention narrator guard** — **OVERSHOT** (blocked Gatsby ✓ but fallback picked Gatz instead of Nick)
- **Fix FF: STEP 5.6.9 fuzzy Wolfsheim dedup** — **COMPLETELY INEFFECTIVE** (both entries still exist)

### Attempt 12 fixes
- **Fix GG: Chapter-spread narrator guard** — **EFFECTIVE ✓** (Gatz blocked, Nick correctly selected)
- **Fix HH: Heuristic narrator max-mention guard** — **EFFECTIVE ✓** (Nick selected over Gatsby)
- **Fix II: STEP 5.12 cross-cast alias dedup** — **COMPLETELY INEFFECTIVE** (Wolfsheim still duplicated)
- **Fix JJ: Shared single-word alias dedup** — **EFFECTIVE ✓** (Buchanan removed from both Tom and Daisy)

### Attempt 13 fixes
- **Fix KK: F6 single-word name component check** — **EFFECTIVE ✓** (Tom F6 dup eliminated)
- **Fix LL: Step 4.5.9 post-extraction word-subset dedup** — **EFFECTIVE ✓** (Wolfsheim FINALLY deduped after 7 attempts)

### Attempt 14 fixes
- **Fix MM: `" man "` word-boundary in MALE_INDICATORS** — **PARTIALLY EFFECTIVE** (gender inference correct, but LLM generated "close friend" instead of "brother" so gender-correction path not exercised)

### Attempt 15 fixes
- **Fix NN: Word-boundary matching in `_infer_rel`** — **EFFECTIVE ✓** (Gatsby↔Cody "romantic interest" → "mentor"/"protégé")
- **Fix OO: Tighter romantic keyword window** — **EFFECTIVE ✓** (Tom→Jordan/Catherine "romantic interest" eliminated)
- **Fix PP: Strong family evidence override** — **EFFECTIVE ✓** (Catherine→Myrtle "sister" ✓, but reciprocal missing)

### Attempt 16 fixes
- **Fix QQ: Same-gender spousal guard in `_enforce_one_spouse_invariant`** — **EFFECTIVE ✓** (Gatsby↔Tom "husband" blocked)
- **Fix RR: `_propagate_missing_reverses` overwrites generic labels** — **EFFECTIVE** (took effect in attempt 17: Myrtle→Catherine now "sister" ✓)

### Attempt 17 fixes
- **Fix SS: Third-party spousal attribution (30-char window)** — **PARTIALLY EFFECTIVE** (Wolfshiem friendships gone ✓, but Gatsby↔Daisy "husband"/"wife" persists — window too narrow)
- **Dead code cleanup** — **EFFECTIVE ✓** (-150 lines, STEP 5.9.9 and STEP 5.12 removed)

### Attempt 18 fixes
- **Fix TT: Remove third-party check + competitive spousal selection** — **MIXED** (Tom↔Daisy "husband/wife" CORRECT ✓, Gatsby↔Daisy spousal GONE ✓, but NEW false spousals: Nick↔Myrtle, George↔Catherine)
- **Fix UU: Unknown-gender spousal guard** — **EFFECTIVE ✓** (green light↔McKee "associated")
- **Fix TT-bonus: Spousal-keyword competitive selection** — **EFFECTIVE for Gatsby↔Daisy** but doesn't prevent false spousals on unrelated pairs

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 2 | False narrator (Eckleburg) | `src/agents/characters.py` (STEP 4.26 threshold) | No change — wrong layer |
| 2 | Gatsby wrong cast tier | `src/agents/characters.py` (STEP 5.11 new) | No change — code not firing |
| 2 | Relationship labels all "husband" | `src/pipeline/character_profiling/post_corrections.py` | Partial fix — main cast improved |
| 3 | False narrator | `src/pipeline/character_extraction_v2/narrator.py`, `src/agents/characters.py` | **FIXED** ✓ |
| 3 | "colleague" spam | `src/analyzer.py` (profiler prompt) | No change — LLM ignores forbidden list |
| 3 | Gatsby promotion diagnostic | `src/agents/characters.py` (STEP 5.11 logging) | No change — promotion still doesn't fire |
| 4 | Gatsby promotion safety net | `src/analyzer.py` (before Step 4.6) | Partially effective — Gatsby promoted but narrator regressed |
| 4 | "colleague" post-processing filter | `src/analyzer.py` (two locations) | **FAILED** — 198 "colleague" entries remain |
| 5 | Narrator mention guard | `src/pipeline/character_extraction_v2/narrator.py` | **FIXED** ✓ |
| 5 | Narrator fallback minimum | `src/agents/characters.py` (STEP 6.6) | **FIXED** ✓ |
| 5 | Colleague substring filter | `src/analyzer.py` (two locations) | **FAILED** — 192 "colleague" remain |

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
   grep -n "^[[:space:]]*V[[:space:]]*$" Test_Texts/gatsby.txt

   # Check what ingestion does to the text
   LOG_LEVEL=DEBUG python -c "
   from src.ingestion import ingest_document
   text = ingest_document('Test_Texts/gatsby.txt')
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

   with open('Test_Texts/gatsby.txt', 'r') as f:
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

