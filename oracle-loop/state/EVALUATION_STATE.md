# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 24
- **Phase:** awaiting_evaluation
- **baseline_score:** 5.90

## Output Files
- HTML: ../output/gatsby/report.html
- JSON: ../output/gatsby/analysis.json
- Generated: 2026-03-11 09:02 (runtime ~84 minutes)

## Latest Scores
- Structure Detection: 10/10 ✓
- Character Extraction: 8/10 ✓
  - Completeness: 7.5/10 (George Wilson still missing — 23rd attempt)
  - Identity Resolution: 9/10 (clean — James Gatz false split RESOLVED by LLM variance)
  - Alias Grouping: 9/10 (clean)
- Character Profiles: 7/10 ✗ (REGRESSION: Tom↔Jordan "husband/wife" WRONG; Gatsby↔Daisy relationship MISSING)
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 8.5/10 ✓ (147/149 with IPA)
- HTML Presentation: 8.5/10 ✓
- **Overall: 8.45/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (1 category below threshold: Character Profiles 7/10)

## What Changed in Attempt 23

### Fix EEE (George Wilson F6 first-name single-word exception) — DID NOT RESOLVE
- The first-name check `if first_name == char_canonical` now skips single-word chars
- BUT George Wilson is STILL missing from the 21-character output
- "George Wilson" appears in `characters_present` for Ch 2, 7, 8
- "Myrtle" (main_cast_5) has alias "Myrtle Wilson" — the shared "Wilson" surname may trigger a DIFFERENT blocker in `_is_likely_alias_of_existing` than the first-name or last-name checks
- **Root cause hypothesis**: `_is_likely_alias_of_existing("George Wilson")` encounters "Myrtle" whose alias list contains "Myrtle Wilson". The last_name of "George Wilson" is "wilson", which may match a word component in "Myrtle Wilson" through a substring or word-overlap check, causing the function to return True (blocked).
- **Fix approach**: Add diagnostic logging to F6 OR trace the exact code path where "George Wilson" is blocked by the Myrtle Wilson alias

### James Gatz false split — RESOLVED (LLM variance)
- James Gatz no longer appears as a separate F6-reconciled entry
- LLM variance: this run's summaries/Pass 1 didn't extract "James Gatz" as a separate character

### Montenegro false positive — NEW
- Montenegro (7 mentions, F6 ID 4e92f9d2cdf0) is a country, not a character
- Minor issue — it's mentioned in Gatsby's backstory ("little Montenegro")

### Profile REGRESSION: Tom↔Jordan false spousal
- Tom Buchanan → Jordan Baker: "husband" (WRONG — Tom's wife is Daisy)
- Jordan Baker → Tom Buchanan: "wife" (WRONG)
- Tom Buchanan → Daisy Buchanan: "associated" (should be "husband")
- Daisy Buchanan → Tom Buchanan: "associated" (should be "wife")
- In attempt 22, Tom↔Daisy was correctly "husband/wife" — this is a REGRESSION
- Root cause: LLM variance in the profiler. The `verify_relationships_from_text` spousal detection is picking up Jordan in proximity to spousal keywords near Tom, instead of Daisy.

### Gatsby↔Daisy relationship MISSING
- Gatsby has no relationship entry for Daisy Buchanan at all
- The central romantic relationship of the novel is absent
- This has been a persistent issue across many attempts

### Improvements
- Nick↔Daisy "cousin" ✓ (present and correct!)
- Myrtle↔Catherine "sister" ✓ (Fix CCC holding)
- Ch I summary no longer has "Nick Carraway, Nick Carraway" double name
- Wolfsheim friendships still clean (Fix DDD holding)

## Current Issues (Priority Order)

### CRITICAL

1. **George Wilson missing from character list — 23rd attempt** [Completeness]
   - Problem: George Wilson — Myrtle's husband, kills Gatsby, kills himself — is NOT in the 21-character output
   - Evidence: "George Wilson" appears in `characters_present` for chapters 2, 7, 8. The HTML summaries mention him by name. But no character entry exists.
   - Root cause: STILL UNKNOWN. Fix BBB (last-name single-word) and Fix EEE (first-name single-word) both applied but insufficient. The blocker is likely a DIFFERENT check in `_is_likely_alias_of_existing` — possibly the word-overlap/substring check matching "Wilson" from "George Wilson" against Myrtle's alias "Myrtle Wilson".
   - Location: `src/analyzer.py` — `_is_likely_alias_of_existing()` and F6 flow
   - **Fix approach (Fix GGG): Diagnostic-first — add targeted logging**
     1. In `_is_likely_alias_of_existing`, add a conditional log for any candidate containing "wilson" (case-insensitive):
        - Log which existing character triggered the `return True`
        - Log which specific check (first_name, last_name, word_overlap, substring, synonym, etc.) returned True
     2. Run analysis, capture logs, identify the EXACT blocker
     3. Apply targeted fix based on findings
   - **Alternative (Fix GGG-alt): Force-add characters_present entries**
     - After the main F6 loop, scan `characters_present` across all chapters
     - For names appearing in 2+ chapters that aren't in the character list and contain a proper noun, force-add them
     - This bypasses whatever hidden blocker exists

### HIGH

2. **Tom↔Jordan false spousal / Tom↔Daisy "associated" (REGRESSION)** [Profiles]
   - Problem: Tom Buchanan → Jordan Baker labeled "husband"; should be Tom → Daisy Buchanan "husband"
   - Evidence: Tom Buchanan is married to Daisy, not Jordan. This was correct in attempt 22.
   - Root cause: LLM profiler variance + `verify_relationships_from_text` spousal detection picking wrong pair
   - Location: `src/pipeline/character_profiling/post_corrections.py` — `verify_relationships_from_text` and spousal selection logic
   - Fix: The competitive spousal selection (Fix TT-bonus) should pick the strongest-evidence spouse pair. If Tom↔Daisy has more co-mentions with spousal keywords than Tom↔Jordan, Daisy should win. The regression suggests the competitive selection is not robust enough OR the LLM profiler seeded "husband" for Jordan first.

3. **Gatsby↔Daisy relationship missing** [Profiles]
   - Problem: Gatsby has relationships with Nick, Cody, Tom, Sloane, Lucille, Jordan — but NOT Daisy
   - Evidence: The entire novel revolves around Gatsby's romantic pursuit of Daisy
   - Root cause: LLM profiler does not generate a Gatsby→Daisy relationship; post-corrections don't add one
   - Location: `src/analyzer.py` (`_generate_character_profile`) or `src/pipeline/character_profiling/post_corrections.py`
   - Fix: This is a recurring gap. The profiler prompt may need to explicitly ask about romantic/obsessive relationships for the protagonist, or post-corrections should detect high co-mention pairs with romantic keywords and add the label.

### MEDIUM

4. **Montenegro false positive (country extracted as character)** [Completeness]
   - Problem: "Montenegro" (7 mentions, F6 ID 4e92f9d2cdf0) is a country, not a character
   - Evidence: "little Montenegro" is referenced in Gatsby's war backstory
   - Location: `src/analyzer.py` — F6 reconciliation should filter place names
   - Fix: The F6 proper-noun filter could check against a list of known country/place names, or verify NER label is PERSON not GPE

5. **Gatsby→Tom "associated" and similar vague labels** [Profiles]
   - Tom and Gatsby are rivals for Daisy. "associated" is technically not wrong but misses the narrative tension.
   - Low priority since Profiles would pass at 8.0 if issues #2 and #3 are fixed.

## Fix Guidance for Attempt 24

**TWO categories need fixing: Character Extraction (George Wilson) and Profiles (Tom↔Jordan spousal regression, Gatsby↔Daisy missing).**

**Priority 1 — Fix GGG (CRITICAL): Diagnose George Wilson F6 blocker once and for all**

This has persisted for 5+ attempts. Fixes BBB and EEE addressed the first-name and last-name single-word checks but the character is still blocked. The DIAGNOSTIC approach is now mandatory:

```python
# In _is_likely_alias_of_existing, add at the TOP of the function:
if 'wilson' in name.lower():
    logger.warning(f"F6-DIAG: Checking '{name}' against {len(characters)} existing characters")

# Then before each `return True`, add:
if 'wilson' in name.lower():
    logger.warning(f"F6-DIAG: '{name}' BLOCKED by check '{check_name}' against char '{char.canonical_name}' (aliases={char.aliases})")
```

Run analysis, grep logs for "F6-DIAG", identify the exact check, then apply a targeted fix.

If diagnostic approach is too slow, use the BYPASS approach: after the main F6 loop, add a safety-net pass over `characters_present` entries appearing in 2+ chapters.

**Priority 2 — Fix HHH (HIGH): Stabilize Tom↔Daisy spousal against LLM variance**

The spousal detection regresses across attempts because the LLM profiler seeds different pairs. Consider:
- In `verify_relationships_from_text`, when detecting a spousal relationship for character X, if X already has a spousal label from the LLM profiler, only UPGRADE it (never replace with a different spouse) unless the new evidence is overwhelming
- OR: after all post-corrections, add a final "strongest spouse wins" pass that checks all spousal pairs for a character and keeps only the one with the most textual evidence

**Priority 3 — Fix III (HIGH): Gatsby↔Daisy relationship injection**

If co-mention analysis shows Gatsby and Daisy co-appear frequently with romantic keywords ("love", "kiss", "longing"), inject a "romantic interest" label. This could be a post-correction step.

**Do NOT fix: Montenegro (minor), vague "associated" labels (cosmetic), F6 clutter characters (valid).**

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
- **Fix GGG: F6c safety-net pass** (`src/analyzer.py`) — Adds characters appearing as `active_characters` in 2+ distinct chapters that are NOT already in character list (by canonical name, alias, or shared word component). Bypasses `_is_likely_alias_of_existing` entirely. George Wilson (3 chapters, 3+ text mentions) should pass.
- **Fix HHH: Ratio-based spouse correction in `_enforce_one_spouse_invariant`** (`src/pipeline/character_profiling/post_corrections.py`) — Extends `len == 1` spousal key case to swap labeled spouse when alternative has `alt_evidence >= max(current_evidence * 1.5, 5)`. Tom→Jordan (18 windows) vs Tom→Daisy (37 windows): 37 >= 27 → swap fires.

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
| 24 | F6c safety-net (2+ chapter active chars) | `src/analyzer.py` | Pending |
| 24 | Ratio-based spouse correction | `src/pipeline/character_profiling/post_corrections.py` | Pending |

**George Wilson F6 blocker: 3 fix attempts (BBB, EEE, +prior) across `src/analyzer.py` — ESCALATION NEEDED**
The same file has been modified 3+ times without success. The fix phase MUST use diagnostic logging to identify the exact blocker before attempting another code fix.

## Configuration Audit
- Model: `qwen3-next:80b-a3b-instruct-q8_0` for all agents (think_mode: false)
- Context length: 32768 — adequate for Gatsby's chapter sizes
- Temperature: 0.7 — reasonable
- Zero LLM retries — no prompt/schema failures

## Pipeline Notes (Attempt 24)
- **26 characters found** (up from 21 in attempt 23) — F6c safety-net added 8 from chapter summaries
- Nick Carraway confirmed as narrator ✓
- 149 pronunciation flags
- James Gatz reappeared as referenced character (from summaries)
- 1 low-confidence character profile
- Tom Buchanan still has "the Buchanans' house" alias (cosmetic)
- Runtime: 84m 23s

## Pipeline Notes (Attempt 23)
- 21 characters found — George Wilson: STILL MISSING (23rd attempt)
- Nick Carraway confirmed as narrator ✓
- 149 pronunciation flags (147 with IPA)
- James Gatz false split RESOLVED (LLM variance — not extracted this run)
- Montenegro (country) extracted as character with 7 mentions — false positive
- Tom↔Jordan false spousal REGRESSION from attempt 22
- Gatsby↔Daisy relationship entirely absent
- Runtime: ~87 minutes

## Next Action
Run PROMPT_analyze.md for attempt 24.

**Fixes applied for attempt 24:**
- Fix GGG: F6c safety-net in `src/analyzer.py` — George Wilson should appear for the first time
- Fix HHH: Ratio-based spouse swap in `_enforce_one_spouse_invariant` — Tom↔Daisy "husband/wife" should be restored
- Fix III (NOT YET FIXED): Gatsby↔Daisy relationship still missing — will revisit if attempt 24 still fails on Profiles
