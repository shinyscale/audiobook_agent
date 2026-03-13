# Oracle Loop Escalation: gatsby

## Status: Requires Human Investigation

**Generated:** 2026-03-10 16:18:44
**Text:** gatsby
**Attempt:** 17
**Current Score:** 8.53
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
| 14 | 8.40 |
| 15 | 8.53 |
| 16 | 8.53 |
| 17 | 8.53 |

---

## Current Issues (from EVALUATION_STATE.md)

## Current Issues (Priority Order)

### HIGH

1. **Gatsby→Daisy "husband" / Daisy→Gatsby "wife" — STILL WRONG** [Profiles]
   - Problem: Gatsby is labeled as Daisy's husband. Tom Buchanan is Daisy's husband. Gatsby is her former lover.
   - Root cause: Fix SS's 30-char window for third-party name detection is too narrow. In many text passages, "her husband" appears with Gatsby+Daisy in proximity but Tom's name is further than 30 chars away. The LLM profiler may also directly generate "husband" for Gatsby→Daisy.
   - Evidence: This is the 3rd consecutive attempt where this label appears. Blocking on other pairs just shifts it here.
   - Location: `src/pipeline/character_profiling/post_corrections.py` — `verify_relationships_from_text` and/or LLM profiler output
   - Fix approach: **Two-pronged fix:**
     (a) Widen the third-party search radius from 30 chars to 80 chars in Fix SS
     (b) Add a post-correction rule: if character A→B has "husband"/"wife" AND B→A does NOT have the reciprocal spousal label from the LLM profiler, demote to "romantic interest". Real married couples will have BOTH sides labeled "husband"/"wife" by the LLM. In Gatsby's case, the LLM gives Gatsby→Daisy "husband" but Daisy→Gatsby gets "wife" only from reciprocal propagation, not from original LLM output.
   - Alternative simpler fix: In `verify_relationships_from_text`, when a spousal keyword is found between A and B, check if ANY other character pair (e.g., Tom↔Daisy) has stronger spousal evidence (more windows with spousal keywords). If so, suppress the weaker pair's spousal label. Tom↔Daisy will always have more "husband" windows than Gatsby↔Daisy.

2. **Tom↔Daisy "associated" — should be "husband"/"wife"** [Profiles]
   - Problem: The novel's actual married couple gets vague "associated" label
   - Evidence: "her husband" appears dozens of times when Daisy and Tom co-occur
   - Location: Same as #1 — if Fix SS correctly attributes spousal labels to Tom↔Daisy, this resolves
   - Fix: Ensure `verify_relationships_from_text` checks Tom↔Daisy windows and upgrades "associated" to "husband"/"wife"

3. **Green light↔Mr. McKee "husband" — NONSENSICAL** [Profiles]
   - Problem: A symbolic entity (green light) is labeled as "husband" of Mr. McKee
   - Root cause: `verify_relationships_from_text` is applying spousal detection to symbolic/non-person entities
   - Location: `src/pipeline/character_profiling/post_corrections.py`
   - Fix: Skip spousal relationship inference for characters with `is_symbolic=True` or whose canonical name starts with "The green light", "Doctor T. J. Eckleburg", etc. More universally: skip spousal inference when either character's `role` is not "protagonist"/"main"/"supporting" with a person-like name, or when either character has `is_symbolic=True`.

### MEDIUM

4. **Mr. McKee→Myrtle "nephew" — FABRICATED** [Profiles]
   - Problem: McKee is not Myrtle's nephew. Mrs. McKee mentions "my nephew" in conversation, which the pipeline misattributes.
   - Location: LLM profiler or `_infer_rel` keyword detection
   - Impact: Minor character, low severity

5. **Dan Cody→Daisy "friend" — FABRICATED** [Profiles]
   - Problem: Dan Cody died years before Gatsby met Daisy. They never met.
   - Location: LLM profiler fabrication
   - Impact: Minor, but contributes to profile noise

6. **Gatsby→Klipspringer/Lucille "employee" — WRONG relationship type** [Profiles]
   - Problem: Klipspringer is a freeloader who lives at Gatsby's house, not an employee. Lucille is a party guest.
   - Impact: Minor inaccuracy

7. **Nick Carraway physical_description: null** [Profiles]
   - Problem: The narrator/protagonist lacks a physical description
   - Note: Nick describes himself minimally in the text, so this may be partially justified. But he does mention being "thirty" and gives some self-description.

### LOW

8. **Gatsby missing "James Gatz" alias** [Alias Grouping]
   - LLM variance — was present in attempt 14, absent since attempt 15

9. **George Wilson missing from character list** [Completeness]
   - LLM variance in extraction — significant character (kills Gatsby) but not extracted

10. **T. J. Eckleburg / Doctor T. J. Eckleburg's eyes — potential duplicate** [Identity Resolution]
    - Two entries for the same billboard. Low impact since both are symbolic.

## Fix Guidance for Attempt 18

**Focus ONLY on getting Character Profiles from 7.5/10 to 8/10.** All other categories pass.

**The spousal label whack-a-mole is now in its 4th iteration. Previous targeted fixes (same-gender guard, one-spouse invariant, third-party 30-char check) just move the problem. A more robust approach is needed.**

**Fix TT (HIGH — addresses issues #1, #2, #3): Spousal label validation overhaul**

The core problem: `verify_relationships_from_text` detects "husband"/"wife" keywords in co-mention windows and assigns them to whichever character pair happens to be in that window. But in Gatsby, "her husband" almost always refers to Tom, even when the window also contains Gatsby's name.

**Proposed fix — competitive spousal attribution:**
In `verify_relationships_from_text`, after collecting ALL spousal keyword hits across ALL character pair windows:
1. For each character X who appears as target of a "husband" or "wife" label from multiple source characters, keep ONLY the source character with the MOST spousal keyword evidence windows
2. Example: If Gatsby→Daisy has 3 windows with "husband" and Tom→Daisy has 8 windows with "husband", keep only Tom→Daisy "husband" and demote Gatsby→Daisy to "romantic interest" (or leave as whatever the LLM gave)
3. This is universal: the character with the most textual evidence of being someone's spouse wins

**Additionally:** Skip spousal inference entirely for characters where `is_symbolic=True` (fixes green light↔McKee nonsense, issue #3).

**Fix UU (MEDIUM — addresses issue #3 specifically): Symbolic entity relationship guard**
In `verify_relationships_from_text` or in the post-correction pipeline, add a guard:
- If either character in a pair has `is_symbolic=True`, do NOT apply spousal/family relationship inference
- Symbolic entities can have "symbolic focus", "antagonist", "manifestation" type relationships but not "husband"/"wife"/"nephew"/etc.

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
| 6 | Disable cooccurrence colleague injection | `src/pipeline/character_profiling/post_corrections.py` | **FIXED** ✓ (192→30) |
| 6 | Block " and " pair-reference aliases | `src/pipeline/character_extraction_v2/main_cast.py` | **FIXED** ✓ |
| 7 | NameError `_VAGUE_REL_LABELS` | `src/analyzer.py` | **FIXED** ✓ |
| 7 | Spouse evidence window | `src/pipeline/character_profiling/post_corrections.py` | Partial (47→23 spouse errors) |
| 7 | Speech patterns prompt | `src/analyzer.py` | **FAILED** — evaluator error |

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

