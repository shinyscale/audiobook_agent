# Oracle Loop Escalation: gatsby

## Status: Requires Human Investigation

**Generated:** 2026-03-08 21:10:35
**Text:** gatsby
**Attempt:** 16
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
| 13 | 8.40 |
| 14 | 8.40 |
| 15 | 8.53 |
| 16 | 8.53 |

---

## Current Issues (from EVALUATION_STATE.md)

## Current Issues (Priority Order)

### HIGH

1. **Gatsby→Daisy "husband" / Daisy→Gatsby "wife" — WRONG** [Profiles]
   - Problem: Gatsby is labeled as Daisy's husband. In the novel, TOM is Daisy's husband. Gatsby is her former lover and current romantic interest.
   - Root cause: Text windows with Gatsby+Daisy mentions contain "her husband" (referring to Tom). `_infer_rel` or the LLM profiler attributes the "husband" label to Gatsby instead of Tom.
   - Location: `src/pipeline/character_profiling/post_corrections.py` — `verify_relationships_from_text` and/or `_infer_rel`
   - Fix approach: **Third-party spousal attribution check.** When "husband"/"wife" is found in a text window between characters A and B, check if a THIRD character's name also appears in the same window near the spousal term. If "her husband" is followed by/preceded by "Tom" (or any other character name), attribute the spousal relationship to Tom↔Daisy instead of Gatsby↔Daisy. This is universal: "her husband [NAME]" should attribute to [NAME], not the other character in the window.

2. **Tom↔Daisy "associated" — should be "husband"/"wife"** [Profiles]
   - Problem: The novel's central married couple gets a vague "associated" label
   - Evidence: "her husband" appears dozens of times near Tom+Daisy co-mentions
   - Location: Same as above — if fix #1 correctly attributes "husband" to Tom↔Daisy instead of Gatsby↔Daisy, this resolves automatically
   - Fix: Ensure `verify_relationships_from_text` checks Tom↔Daisy windows and finds strong "husband"/"wife" evidence

3. **Myrtle→Catherine still "associated" (should be "sister")** [Profiles]
   - Problem: Fix RR was supposed to propagate Catherine→Myrtle "sister" to the reverse, but didn't
   - Evidence: Catherine→Myrtle correctly shows "sister", but Myrtle→Catherine shows "associated"
   - Location: `src/pipeline/character_profiling/post_corrections.py` — `_propagate_missing_reverses`
   - Fix: Debug why propagation didn't fire. Likely the reverse relationship already existed as "associated" and the function doesn't overwrite existing labels. Must overwrite generic labels ("associated") with specific ones ("sister").

### MEDIUM

4. **Fabricated Wolfshiem friendships** [Profiles]
   - Problem: Wolfshiem→Tom "friend", Wolfshiem→Jordan "friend", Wolfshiem→Daisy "friend", Wolfshiem→Nick "friend" — none of these interactions exist in the text (except brief Nick encounter)
   - Location: LLM profiler generates these; `verify_relationships_from_text` should catch and remove unsupported labels
   - Low individual impact but contributes to overall profile noise

5. **Dan Cody→Daisy "friend"** [Profiles]
   - Problem: Dan Cody died years before Gatsby met Daisy. They cannot be friends.
   - Location: LLM profiler fabrication
   - Low individual impact

6. **Nick and Gatsby physical_description: null** [Profiles]
   - Problem: Two protagonists lack physical descriptions. Gatsby is described in the text.
   - Location: LLM variance in `_generate_character_profile()`

7. **Tom alias "the Buchanans' house"** [Alias Grouping]
   - Problem: Possessive building reference incorrectly grouped as Tom's alias
   - Note: Fix DD was supposed to block this; likely LLM variance re-introduced it

### LOW

8. **Gatsby missing "James Gatz" alias** [Alias Grouping]
   - LLM variance (was present in attempt 14, absent in 15-16)

9. **George Wilson missing from character list** [Completeness]
   - LLM variance in extraction — mentioned in summaries but not extracted as character

## Fix Guidance for Attempt 17

**Focus ONLY on getting Character Profiles from 7.5/10 to 8/10.** All other categories pass.

**The spousal label has now shifted across 3 different pairs over multiple attempts. Targeted blocks (same-gender guard, one-spouse invariant) just move the problem. The fix must address the ROOT CAUSE.**

**Fix 1 (CRITICAL): Third-party spousal attribution in `verify_relationships_from_text`**
When checking a text window between characters A and B and finding a spousal keyword ("husband", "wife", "spouse"):
1. Check if ANY other character's name appears in the same window within ~30 chars of the spousal keyword
2. If yes (e.g., "her husband Tom" in a Gatsby+Daisy window), attribute the spousal relationship to that third character + the relevant party, NOT to A↔B
3. If no third character, proceed with normal attribution to A↔B
4. This is universal: disambiguates possessive spousal references across all texts

**Fix 2 (HIGH): Debug and fix `_propagate_missing_reverses` for Myrtle→Catherine**
- Catherine→Myrtle = "sister" but Myrtle→Catherine = "associated"
- The propagation function should overwrite "associated" with "sister" (specific > generic)
- Check if the function skips when a reverse relationship already exists, even if it's a vague label
- Fix: only skip propagation if the existing reverse label is SPECIFIC (not "associated"/"unknown"/"acquaintance")

**Fix 3 (MEDIUM): If Fix 1 correctly attributes "husband" to Tom↔Daisy, verify the one-spouse invariant doesn't then REMOVE it**
- The one-spouse invariant from Fix S (attempt 8) may conflict if Gatsby↔Daisy still has "husband" from LLM
- Ensure ordering: verify_relationships_from_text runs FIRST (corrects attribution), THEN one-spouse invariant cleans up any remaining duplicates

Fixing #1 and #2 removes 2 fabricated labels (Gatsby↔Daisy "husband"/"wife"), adds 2 correct labels (Tom↔Daisy "husband"/"wife"), and adds 1 correct label (Myrtle→Catherine "sister"). That's a net improvement of +5 correct relationship entries, which should push profiles to 8/10.

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
- **Fix RR: `_propagate_missing_reverses` overwrites generic labels** — **PARTIALLY EFFECTIVE** (Myrtle→Catherine still "associated")

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
| 7 | Wolfsheim alias absorption | `src/agents/characters.py` (STEP 5.6.9) | **FAILED** — still duplicated |
| 8 | Gatsby canonical rename | `src/analyzer.py` | **FIXED** ✓ |
| 8 | One-spouse invariant | `src/pipeline/character_profiling/post_corrections.py` | Partial (23→10, but 6 still wrong) |
| 8 | Colleague → associated | `src/pipeline/character_profiling/post_corrections.py` | **FIXED** ✓ |

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

