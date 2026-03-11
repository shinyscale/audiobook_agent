# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 18
- **Phase:** awaiting_fix
- **baseline_score:** 5.90

## Output Files
- HTML: ../output/gatsby/report.html
- JSON: ../output/gatsby/analysis.json
- Timestamped: output/gatsby_20260310_161224/

## Latest Scores
- Structure Detection: 10/10 ✓
- Character Extraction: 8/10 ✓
  - Completeness: 8.5/10 (George Wilson now present ✓, James Gatz alias ✓)
  - Identity Resolution: 8/10 (green light has Owl Eyes aliases merged in — persistent)
  - Alias Grouping: 8.5/10
- Character Profiles: 7/10 ✗ (FAILING — spousal whack-a-mole continues)
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 8.5/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 8.45/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (1 category below threshold: Character Profiles 7/10)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 5.90 | - | Baseline. Profiles catastrophic, character identity broken |
| 2 | 6.73 | +0.83 | Relationships partially improved for main cast. Core narrator/Gatsby issues UNFIXED |
| 3 | 7.20 | +1.30 | Narrator FIXED (Nick ✓). Gatsby still supporting. "colleague" spam persists |
| 4 | 6.93 | +1.03 | REGRESSION: Gatsby promoted but narrator BROKE AGAIN. Colleague filter FAILED |
| 5 | 7.08 | +1.18 | Narrator FIXED ✓ (Fix I/J). Colleague filter STILL FAILED (192 remain). No speech patterns. |
| 6 | 7.15 | +1.25 | Colleague injection FIXED (192→30). But 47 wrong spousal labels EXPOSED underneath. |
| 7 | 7.45 | +1.55 | Spouse errors halved (47→23). But speech patterns 0/33, Wolfsheim still dup, Gatsby still supporting. |
| 8 | 7.75 | +1.85 | Gatsby promoted ✓, colleagues eliminated ✓. Green light+Owl Eyes merge, 6 wrong spouse labels remain. |
| 9 | 8.30 | +2.40 | Green/Owl split ✓, Wolfsheim dedup ✓, F6 clutter ✓, 4/6 wrong spouses fixed. Gatz dup and Gatsby↔Jordan remain. |
| 10 | 8.05 | +2.15 | Gatz dedup ✓, Gatsby↔Jordan spousal ✓, alias cleanup ✓. BUT narrator REGRESSED, Wolfsheim dup REGRESSED, 11 fabricated family rels. |
| 11 | 7.93 | +2.03 | Narrator guard overshot (Gatsby→Gatz instead of Nick). Wolfsheim dedup STILL broken. Fabricated rels reduced but not eliminated. |
| 12 | 7.68 | +1.78 | Narrator FIXED ✓ (Nick). But "Tom" F6 dup (191 mentions) newly identified. Wolfsheim STILL duplicated (5th failure). Fabricated rels persist (Gatsby↔Jordan spouse). |
| 13 | 8.40 | +2.50 | **BREAKTHROUGH**: Tom F6 dup FIXED ✓, Wolfsheim dedup FINALLY FIXED ✓. Character Extraction passes 8.0. Only Profiles (7/10) remains below threshold. |
| 14 | 8.40 | +2.50 | Fix MM (gender word-boundary) worked: Myrtle/Catherine gender correct. But "close friend" instead of "sister" (LLM variance). NEW fabrication: Gatsby↔Cody "romantic interest". Net: same score. |
| 15 | 8.53 | +2.63 | Fix NN/OO/PP effective: Cody↔Gatsby "mentor/protégé" ✓, Catherine→Myrtle "sister" ✓, Tom→Catherine romantic GONE ✓. But NEW: Gatsby↔Tom "husband" fabricated. Profiles 7→7.5. |
| 16 | 8.53 | +2.63 | Fix QQ effective (same-gender guard): Gatsby↔Tom "husband" GONE ✓. But spousal label SHIFTED to Gatsby↔Daisy "husband"/"wife" — wrong pair. Net: no change. |
| 17 | 8.53 | +2.63 | Fix SS (third-party spousal) + Myrtle→Catherine "sister" FIXED ✓. But Gatsby↔Daisy "husband"/"wife" PERSISTS. NEW: green light↔McKee "husband" (nonsensical). Net: no change. |
| 18 | 8.45 | +2.55 | Fix TT (spousal overhaul): Tom↔Daisy "husband/wife" CORRECT ✓. Gatsby↔Daisy spousal GONE ✓. BUT NEW: Nick↔Myrtle "husband/wife", George↔Catherine "husband/wife", Nick↔Daisy "brother/sister". Net: slight regression. |

## What Changed in Attempt 18

### Fix TT (Remove third-party check + competitive spousal selection) — MIXED
- Tom↔Daisy "husband"/"wife" — NOW CORRECT ✓ (was "associated" for 4+ attempts)
- Gatsby↔Daisy spousal — GONE ✓ (competitive selection correctly chose Tom over Gatsby)
- Green light↔McKee spousal — GONE ✓ (Fix UU unknown-gender guard worked)
- BUT removing the third-party check allowed `verify_relationships_from_text` to assign "husband"/"wife" to ANY pair that co-occurs near a spousal keyword, even when the keyword refers to a third character

### NEW Regressions from Fix TT
- **Nick→Myrtle "husband" / Myrtle→Nick "wife"** — COMPLETELY WRONG. In Ch. 2 apartment scene, Nick and Myrtle co-occur near "husband" text (referring to George Wilson), and the text-evidence step incorrectly assigns spousal to Nick↔Myrtle.
- **Nick→Daisy "brother" / Daisy→Nick "sister"** — WRONG. Nick is Daisy's second cousin once removed, not brother/sister. The LLM profiler likely generated this (not from text-evidence), but it's inaccurate.
- **George→Catherine "husband" / Catherine→George "wife"** — WRONG. Catherine is Myrtle's sister. George and Catherine co-occur in Ch. 2 and Ch. 9 near spousal keywords referring to George↔Myrtle.
- **George↔Myrtle "associated"** — WRONG. Should be "husband"/"wife". The actual married couple lost their spousal label, possibly because competitive selection awarded spousal to George↔Catherine instead.

### Fix UU (Unknown-gender spousal guard) — EFFECTIVE ✓
- Green light↔McKee "associated" ✓ (was "husband")

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
| 6 | Disable cooccurrence colleague injection | `src/pipeline/character_profiling/post_corrections.py` | **FIXED** ✓ (192→30) |
| 6 | Block " and " pair-reference aliases | `src/pipeline/character_extraction_v2/main_cast.py` | **FIXED** ✓ |
| 7 | NameError `_VAGUE_REL_LABELS` | `src/analyzer.py` | **FIXED** ✓ |
| 7 | Spouse evidence window | `src/pipeline/character_profiling/post_corrections.py` | Partial (47→23 spouse errors) |
| 7 | Speech patterns prompt | `src/analyzer.py` | **FAILED** — evaluator error |
| 7 | Wolfsheim alias absorption | `src/agents/characters.py` (STEP 5.6.9) | **FAILED** — still duplicated |
| 8 | Gatsby canonical rename | `src/analyzer.py` | **FIXED** ✓ |
| 8 | One-spouse invariant | `src/pipeline/character_profiling/post_corrections.py` | Partial (23→10, but 6 still wrong) |
| 8 | Colleague → associated | `src/pipeline/character_profiling/post_corrections.py` | **FIXED** ✓ |
| 8 | Second-pass alias absorption | `src/agents/characters.py` (STEP 5.9.9) | Partial (main entry fixed, 2 extras remain) |
| 9 | Green light / Owl Eyes split | `src/pipeline/character_extraction_v2/main_cast.py` | **FIXED** ✓ |
| 9 | Reciprocal spouse validation | `src/pipeline/character_profiling/post_corrections.py` | Partial (10→6 labels) |
| 9 | Fuzzy Wolfsheim dedup | `src/agents/characters.py` (STEP 5.9.9) | **FIXED** ✓ but REGRESSED |
| 9 | F6 proper-noun filter | `src/analyzer.py` | **FIXED** ✓ |
| 9 | Daisy Fay maiden-name match | `src/analyzer.py` | **FIXED** ✓ |
| 10 | Henry C. Gatz dedup | `src/agents/characters.py` | **FIXED** ✓ |
| 10 | Gatsby↔Jordan false spousal | `src/pipeline/character_profiling/post_corrections.py` | **FIXED** ✓ |
| 10 | Jordan duplicate alias | `src/agents/characters.py` | **FIXED** ✓ |
| 10 | Buchanans' house possessive alias | `src/pipeline/character_extraction_v2/main_cast.py` | **FIXED** ✓ |
| 11 | Narrator max-mention guard | `src/pipeline/character_extraction_v2/narrator.py` | **OVERSHOT** |
| 11 | Fuzzy Wolfsheim dedup STEP 5.6.9 | `src/agents/characters.py` | **COMPLETELY INEFFECTIVE** |
| 12 | Narrator chapter-spread guard | `src/agents/characters.py` | **FIXED** ✓ |
| 12 | Heuristic narrator max-mention guard | `src/agents/characters.py` | **FIXED** ✓ |
| 12 | STEP 5.12 cross-cast alias dedup | `src/agents/characters.py` | **COMPLETELY INEFFECTIVE** |
| 12 | Shared single-word alias dedup | `src/agents/characters.py` | **FIXED** ✓ |
| 13 | Tom F6 duplicate | `src/analyzer.py` | **FIXED** ✓ |
| 13 | Wolfsheim post-extraction dedup | `src/analyzer.py` | **FIXED** ✓ |
| 14 | Gender word-boundary (" man ") | `src/pipeline/character_profiling/post_corrections.py` | **PARTIALLY EFFECTIVE** |
| 15 | Word-boundary in _infer_rel | `src/pipeline/character_profiling/post_corrections.py` | **EFFECTIVE** ✓ (Cody↔Gatsby romantic → mentor) |
| 15 | Tighter romantic keyword window | `src/pipeline/character_profiling/post_corrections.py` | **EFFECTIVE** ✓ (Tom romantic false positives removed) |
| 15 | Strong family evidence override | `src/pipeline/character_profiling/post_corrections.py` | **EFFECTIVE** ✓ (Catherine→Myrtle "sister", but no reciprocal) |
| 16 | Same-gender spousal guard | `src/pipeline/character_profiling/post_corrections.py` | **EFFECTIVE** ✓ (Gatsby↔Tom "husband" blocked) |
| 16 | _propagate_missing_reverses overwrites generics | `src/pipeline/character_profiling/post_corrections.py` | **EFFECTIVE** (took effect in attempt 17) |
| 17 | Third-party spousal attribution (30-char) | `src/pipeline/character_profiling/post_corrections.py` | **PARTIALLY EFFECTIVE** (Wolfshiem friends gone, but Gatsby↔Daisy persists) |
| 17 | Dead code cleanup (STEP 5.9.9, 5.12) | `src/agents/characters.py` | **EFFECTIVE** ✓ (-150 lines) |
| 18 | Remove third-party check + competitive selection | `src/pipeline/character_profiling/post_corrections.py` | **MIXED** (Tom↔Daisy ✓, but new false spousals) |
| 18 | Unknown-gender spousal guard | `src/pipeline/character_profiling/post_corrections.py` | **EFFECTIVE** ✓ |

## Configuration Audit
- Model: `qwen3-next:80b-a3b-instruct-q8_0` for all agents (think_mode: false)
- Context length: 32768 — adequate for Gatsby's chapter sizes
- Temperature: 0.7 — reasonable
- Zero LLM retries — no prompt/schema failures

## Next Action
Re-run analysis to verify Fix VV + Fix WW.

### Attempt 19 fixes
- **Fix VV: Block generic→spousal upgrade in `verify_relationships_from_text`** — addresses issues #1 and #2
  - Root cause: `verify_relationships_from_text` was upgrading "associated" (set by `add_cooccurrence_relationships`) to "husband"/"wife" when co-mention windows contained spousal keywords referring to a THIRD character's marriage
  - Fix: In the `else` block (line 2062), added guard: if `best_is_spousal and cur_lower in _generic_labels`, block upgrade and log debug message
  - Expected fix: Nick↔Myrtle "husband/wife" GONE ✓, George↔Catherine "husband/wife" GONE ✓, George↔Myrtle "husband/wife" PRESERVED (LLM gives directly) ✓
  - Modified: `src/pipeline/character_profiling/post_corrections.py` (~line 2062)
  - Smoke test: 332 passed, 0 failed

- **Fix WW: Add "second"/"third" to `_all_rel_phrase_re` modifiers + "cousin" to profiler prompt** — addresses issue #3
  - Root cause: "my second cousin once removed" didn't match `_all_rel_phrase_re` (pattern only handled "late/dear/best/close/old/trusted" modifiers, not "second"). LLM profiler also didn't have "cousin" as an example label.
  - Fix: Added `second\s+|third\s+` to optional modifiers in `_all_rel_phrase_re`; added "cousin" to profiler prompt examples and familial labels list
  - Expected fix: Nick→Daisy "cousin" (was "brother"), Daisy→Nick "cousin" (was "sister")
  - Modified: `src/pipeline/character_profiling/post_corrections.py` (line 163), `src/analyzer.py` (lines 3666, 3689)
  - Smoke test: 332 passed, 0 failed

**Phase:** awaiting_analysis
