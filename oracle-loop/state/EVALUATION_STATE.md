# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 24
- **Phase:** complete
- **baseline_score:** 5.90

## Output Files
- HTML: ../output/gatsby/report.html
- JSON: ../output/gatsby/analysis.json
- Generated: 2026-03-11 09:02 (runtime ~84 minutes)

## Latest Scores
- Structure Detection: 10/10 ✓
- Character Extraction: 8/10 ✓
  - Completeness: 7.5/10 (George Wilson still missing — 24th attempt, but all other major chars present)
  - Identity Resolution: 9/10 (no false splits or merges)
  - Alias Grouping: 8.5/10 (clean; "the Buchanans' house" alias cosmetic)
- Character Profiles: 8/10 ✓ (IMPROVED from 7/10: Tom↔Daisy husband/wife FIXED ✓, Gatsby↔Daisy now present)
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 8.5/10 ✓ (148/149 with IPA)
- HTML Presentation: 8.5/10 ✓
- **Overall: 8.60/10**

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** PASS — all categories at or above 8.0

## What Changed in Attempt 24

### Fix GGG (F6c safety-net) — PARTIALLY EFFECTIVE
- F6c safety-net fired and added 8 characters from chapter summaries (Slagle, Young Parke, Lutheran minister, Policeman, Mrs. Ulysses Swett, Ferdie, Stella, Owl Eyes)
- Character count: 21 → 26
- BUT George Wilson was NOT added despite appearing in `characters_present` for 4 chapters (II, VII, VIII, IX)
- Root cause: F6c's word-overlap check or text-mention threshold (full phrase "George Wilson" may appear < 2 times in source text, while "Wilson" alone appears frequently)

### Fix HHH (ratio-based spouse correction) — EFFECTIVE ✓
- Tom Buchanan → Daisy: "husband" ✓ (was "associated" in attempt 23)
- Daisy → Tom Buchanan: "wife" ✓
- Tom → Jordan Baker: no longer "husband" ✓ (false spousal regression FIXED)
- No new false spousal pairs introduced

### Gatsby↔Daisy relationship — IMPROVED
- Gatsby → Daisy: "associated" (was completely MISSING in attempt 23)
- Label is weak ("associated" instead of "romantic interest") but presence is an improvement

### Montenegro — RESOLVED
- No longer in character list (was a false positive country extraction in attempt 23)

## Known Gaps (Not Blocking)
1. **George Wilson missing** — Major character (kills Gatsby) absent after 24 attempts. F6c safety-net nearly solved it but word-overlap/text-mention check still blocks. The overall Character Extraction score holds at 8/10 because Identity Resolution (9) and Alias Grouping (8.5) compensate.
2. **Gatsby↔Daisy "associated"** — Central romantic relationship labeled generically. Not wrong, but "romantic interest" would be more useful for narrator.
3. **Gatsby has no physical_description** — Fitzgerald describes him in detail but profiler didn't capture it.
4. **Myrtle's physical_description** — Incorrectly attributes Catherine's appearance details to Myrtle (model self-corrected in the description text but the wrong attribution is still there).
5. **F6c clutter** — Several single-mention characters added (Slagle, Young Parke, Mrs. Ulysses Swett, Stella) that are extremely minor.

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
| 18 | 8.45 | +2.55 | Fix TT (spousal overhaul): Tom↔Daisy "husband/wife" CORRECT ✓. Gatsby↔Daisy spousal GONE ✓. BUT NEW: Nick↔Myrtle, George↔Catherine false spousals. Net: slight regression. |
| 19 | 8.10 | +2.20 | Fix VV (block generic→spousal upgrade) solved false spousals BUT also blocked legitimate Tom↔Daisy. George Wilson MISSING (LLM variance). Net: regression from 8.45. |
| 20 | 8.40 | +2.50 | Fix XX EFFECTIVE ✓ (Tom↔Daisy husband/wife restored). No false spousals. But George Wilson still missing (F6 bug). Profiles improved 6.5→7.5 but fabricated Wolfshiem friendships persist. |
| 21 | 8.18 | +2.28 | Fix ZZ partially effective (description-phrase blocker removed). Fix AAA not exercised. BUT George Wilson STILL missing (Fix KK component check remains). Owl Eyes REGRESSION (2→0 entries). Gatz↔Gatsby father/son FIXED ✓. |
| 22 | 8.48 | +2.58 | Fix CCC EFFECTIVE ✓ (Myrtle→Catherine sister). Fix DDD EFFECTIVE ✓ (Wolfshiem friends cleaned). Profiles now 8.0 ✓. BUT George Wilson STILL missing. James Gatz false split NEW. Owl Eyes recovered. |
| 23 | 8.45 | +2.55 | Fix EEE DID NOT RESOLVE George Wilson. James Gatz false split RESOLVED (LLM variance). BUT Tom↔Jordan false spousal REGRESSION drops Profiles to 7/10. |
| 24 | 8.60 | +2.70 | **PASS**: Fix HHH EFFECTIVE ✓ (Tom↔Daisy husband/wife restored, no false spousals). Fix GGG partially effective (8 chars added, but George Wilson still blocked). All categories ≥ 8.0. |

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

### Attempt 19 fixes
- **Fix VV: Block generic→spousal upgrade** — **TOO AGGRESSIVE** (blocked false spousals ✓ but also blocked legitimate Tom↔Daisy ✗)
- **Fix WW: Cousin label support** — **DID NOT TAKE EFFECT** (no Nick↔Daisy relationship generated at all)

### Attempt 20 fixes
- **Fix XX: Named-spouse check in `verify_relationships_from_text`** — **EFFECTIVE ✓** (Tom↔Daisy "husband/wife" restored, no false spousals)
- **Fix YY: Gender-opposite override in `_propagate_missing_reverses`** — **NOT EXERCISED** (Gatz has 0 relationships, so gender override couldn't fire)

### Attempt 21 fixes
- **Fix ZZ Part 1: Leading-only initial stripping** — **EFFECTIVE** (middle initials preserved)
- **Fix ZZ Part 2: Proper-noun guard in description-phrase check** — **EFFECTIVE** (description-phrase blocker removed for proper names)
- **Fix ZZ Part 3: F6-protection transfer in STEP 4.5.9** — **EFFECTIVE** (F6 chars survive absorption)
- **Fix AAA: Alias-aware char_by_name in propagate_missing_reverses** — **NOT EFFECTIVE** (Myrtle→Catherine still "associated")

### Attempt 22 fixes
- **Fix BBB: F6 last_name single-word exception** — **DID NOT RESOLVE** (George Wilson still missing; the actual blocker is elsewhere)
- **Fix CCC: Sibling↔spousal cross-tier guard in verify_relationships_from_text** — **EFFECTIVE ✓** (Myrtle→Catherine "sister" restored)
- **Fix DDD: `reject_unfounded_friend_labels` post-correction** — **EFFECTIVE ✓** (fabricated Wolfshiem friendships removed; 10+ entries cleaned)

### Attempt 23 fixes
- **Fix EEE: F6 first-name single-word exception** — **DID NOT RESOLVE** (George Wilson still missing; third failed attempt at this issue)

### Attempt 24 fixes
- **Fix GGG: F6c safety-net pass** — **PARTIALLY EFFECTIVE** (added 8 chars from summaries; George Wilson still blocked by word-overlap or text-mention threshold)
- **Fix HHH: Ratio-based spouse correction** — **EFFECTIVE ✓** (Tom↔Daisy "husband/wife" restored; Tom↔Jordan false spousal eliminated)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 2 | False narrator (Eckleburg) | `src/agents/characters.py` (STEP 4.26 threshold) | No change — wrong layer |
| 2 | Gatsby wrong cast tier | `src/agents/characters.py` (STEP 5.11 new) | No change — code not firing |
| 2 | Relationship labels all "husband" | `src/pipeline/character_profiling/post_corrections.py` | Partial fix — main cast improved |
| 3 | False narrator | `src/pipeline/character_extraction_v2/narrator.py`, `src/agents/characters.py` | **FIXED** ✓ |
| 3 | "colleague" spam | `src/analyzer.py` (profiler prompt) | No change — LLM ignores forbidden list |
| 4 | Gatsby promotion safety net | `src/analyzer.py` (before Step 4.6) | Partially effective |
| 5 | Narrator mention guard | `src/pipeline/character_extraction_v2/narrator.py` | **FIXED** ✓ |
| 6 | Disable cooccurrence colleague injection | `src/pipeline/character_profiling/post_corrections.py` | **FIXED** ✓ |
| 7 | Spouse evidence window | `src/pipeline/character_profiling/post_corrections.py` | Partial |
| 8 | Gatsby canonical rename | `src/analyzer.py` | **FIXED** ✓ |
| 9 | Green light / Owl Eyes split | `src/pipeline/character_extraction_v2/main_cast.py` | **FIXED** ✓ |
| 10 | Henry C. Gatz dedup | `src/agents/characters.py` | **FIXED** ✓ |
| 12 | Narrator chapter-spread guard | `src/agents/characters.py` | **FIXED** ✓ |
| 13 | Tom F6 dup / Wolfsheim dedup | `src/analyzer.py` | **FIXED** ✓ |
| 15 | Romantic/family keyword fixes | `src/pipeline/character_profiling/post_corrections.py` | **FIXED** ✓ |
| 16 | Same-gender spousal guard | `src/pipeline/character_profiling/post_corrections.py` | **FIXED** ✓ |
| 18 | Competitive spousal selection | `src/pipeline/character_profiling/post_corrections.py` | **MIXED** |
| 20 | Named-spouse proximity check | `src/pipeline/character_profiling/post_corrections.py` | **FIXED** ✓ |
| 21 | F6 description-phrase proper-noun guard | `src/analyzer.py` | **FIXED** ✓ |
| 22 | F6 last_name single-word exception | `src/analyzer.py` | **DID NOT RESOLVE** |
| 22 | Sibling↔spousal cross-tier guard | `src/pipeline/character_profiling/post_corrections.py` | **FIXED** ✓ |
| 22 | reject_unfounded_friend_labels | `src/pipeline/character_profiling/post_corrections.py` | **FIXED** ✓ |
| 23 | F6 first-name single-word exception | `src/analyzer.py` | **DID NOT RESOLVE** |
| 24 | F6c safety-net (2+ chapter active chars) | `src/analyzer.py` | **PARTIAL** (8 added, George Wilson still blocked) |
| 24 | Ratio-based spouse correction | `src/pipeline/character_profiling/post_corrections.py` | **FIXED** ✓ |

## Configuration Audit
- Model: `qwen3-next:80b-a3b-instruct-q8_0` for all agents (think_mode: false)
- Context length: 32768 — adequate for Gatsby's chapter sizes
- Temperature: 0.7 — reasonable
- Zero LLM retries — no prompt/schema failures

## Next Action
gatsby PASSES with 8.60/10. All categories ≥ 8.0. Ready to advance to next text (frankenstein).
