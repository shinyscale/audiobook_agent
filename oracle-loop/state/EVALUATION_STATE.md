# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 22
- **Phase:** awaiting_fix
- **baseline_score:** 5.90

## Output Files
- HTML: ../output/gatsby/report.html
- JSON: ../output/gatsby/analysis.json
- Timestamped: output/gatsby_20260311_051335/

## Latest Scores
- Structure Detection: 10/10 ✓
- Character Extraction: 7.5/10 ✗
  - Completeness: 7/10 (George Wilson STILL missing — 22nd attempt)
  - Identity Resolution: 8/10 (James Gatz false split from Gatsby)
  - Alias Grouping: 9/10 (clean)
- Character Profiles: 8/10 ✓ (Fix CCC Myrtle→Catherine "sister" ✓; Fix DDD Wolfshiem friendships cleaned ✓; Tom↔Daisy husband/wife ✓)
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 8.5/10 ✓ (148/149 with IPA)
- HTML Presentation: 8.5/10 ✓
- **Overall: 8.48/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (1 category below threshold: Character Extraction 7.5)

## What Changed in Attempt 22

### Fix BBB (George Wilson F6 blocker — last_name single-word exception) — DID NOT RESOLVE
- The `last_name == char_canonical` check now correctly skips single-word existing chars
- BUT George Wilson is STILL missing from the 26-character output
- Detailed investigation: "George Wilson" IS in `characters_present` of the final JSON for Ch 2, 7, 8 (from `summary_obj.active_characters`)
- Simulation of `_is_likely_alias_of_existing("George Wilson")` against the FINAL character list returns False (not blocked)
- **Hypothesis**: At F6 runtime, the character list differs from the final list. There may be a bare "Wilson" supporting character or an intermediate state that blocks "George Wilson" through a path not exercised in the simulation
- **Fix approach**: Add diagnostic logging to F6 flow to trace exactly what happens to "George Wilson" — log every filter step

### Fix CCC (Myrtle→Catherine sibling↔spousal cross-tier guard) — EFFECTIVE ✓
- Myrtle→Catherine: "sister" ✓ (was "associated")
- Catherine→Myrtle: "sister" ✓ (was already correct)
- Cross-tier guard prevents co-mention "her husband" evidence from overriding sibling labels

### Fix DDD (reject_unfounded_friend_labels) — EFFECTIVE ✓
- Wolfshiem→Daisy/Tom/Jordan "friend" → REMOVED ✓
- Daisy↔Dan Cody "friend" → REMOVED ✓
- Wolfshiem→Gatsby "close friend" preserved ✓ (legitimate)
- Wolfshiem→Nick "friend" preserved ✓ (they meet at lunch in Ch IV)
- Nick→Wolfshiem "friend" preserved ✓
- Only 2 "friend" labels remain (both legitimate Wolfshiem connections)

### Owl Eyes — RECOVERED ✓
- Present again with 1 mention (F6 reconciled, ID 8cba5fccdb60)
- Recovery from attempt 21 regression (LLM variance)

### James Gatz — NEW FALSE SPLIT
- Separate entry (ID cbff004f6102, F6 reconciled) with 4 mentions
- Has relationships: Dan Cody "employee", Henry C. Gatz "child"
- Should be merged into Gatsby (James Gatz = Jay Gatsby's birth name)
- Gatz and Cody relationships incorrectly point to "James Gatz" instead of "Gatsby"

## Current Issues (Priority Order)

### CRITICAL

1. **George Wilson missing from character list — 22nd attempt** [Completeness]
   - Problem: George Wilson — Myrtle's husband, kills Gatsby, kills himself — is NOT in the 26-character output
   - Evidence: "George Wilson" appears in `characters_present` for chapters 2, 7, 8 in the final JSON. The HTML shows him tagged in chapters 2, 7, 8, 9 summaries.
   - Root cause: UNKNOWN despite extensive code analysis. Simulation of `_is_likely_alias_of_existing` against final character list shows he should NOT be blocked. The blocker likely exists at F6 runtime when the character list is in a different intermediate state (possibly including a bare "Wilson" supporting character that gets absorbed later).
   - Location: `src/analyzer.py` — F6 reconciliation flow (lines 1225-1804)
   - **Fix approach (Fix EEE): Add diagnostic logging to F6 flow**
     1. At the start of F6, log ALL entries in `existing_names` that contain "wilson" (case-insensitive)
     2. At each filter step (existing_names check, generic descriptor, synonym, _is_likely_alias_of_existing), log whether "George Wilson" passes or fails
     3. Inside `_is_likely_alias_of_existing`, for multi-word candidates, log which specific check triggers a return True
     4. Run analysis with logging enabled, capture the output, and identify the exact blocker
     5. THEN apply a targeted fix based on the identified blocker
   - **Alternative approach (Fix EEE-alt): Direct F6 injection bypass**
     - After the F6 `missing_names` loop, add a SECOND pass that checks `characters_present` from the structure data against the character list
     - Characters in `characters_present` that have proper nouns AND appear in 3+ chapters but are NOT in the character list should be force-added
     - This bypasses whatever blocker exists in the current F6 filter chain

### HIGH

2. **James Gatz false split from Gatsby** [Identity Resolution]
   - Problem: "James Gatz" (4 mentions, F6 reconciled) is a separate entry from "Gatsby" (266 mentions). James Gatz is Jay Gatsby's birth name.
   - Evidence: Chapter 6 reveals "James Gatz — that was really, or at least legally, his name"
   - Root cause: F6 added "James Gatz" as a new character. The pipeline doesn't recognize "James Gatz" as an alias of "Jay Gatsby" because they share no name components (James ≠ Jay, Gatz ≠ Gatsby).
   - Location: `src/analyzer.py` — Step 4.5.9 word-subset dedup doesn't fire because no words overlap. The birth name → stage name pattern is not handled.
   - Fix: In Step 4.5.9 or a new post-step, check if an F6-reconciled character's relationships (e.g., Henry C. Gatz "child") point to another character (Gatz→Gatsby) via shared surname components. OR: handle in `_is_likely_alias_of_existing` — if candidate "James Gatz" shares a surname component "Gatz" with existing "Henry C. Gatz" AND another character "Gatsby" has a relationship with "Henry C. Gatz", infer James Gatz = Gatsby.
   - **Simpler fix**: This is a known biographical alias (James Gatz = Jay Gatsby) that the LLM should have caught in Pass 2. Since it's F6-reconciled, it bypassed Pass 2. Add a post-F6 check: if an F6 character has the same surname as an existing character's alias or relationship target, flag for merge.

### MEDIUM

3. **Nick↔Daisy: no relationship (should be "cousin")** [Profiles]
   - Persistent across 22 attempts. First-person narrator limitation.
   - No reliable fix available.

4. **Gatsby→Daisy "associated" (should be "romantic interest")** [Profiles]
   - The central romantic relationship of the novel is labeled generically
   - LLM profiler limitation — conservative labeling
   - Low priority since Profiles now passes 8.0 threshold

5. **Ch I summary starts with "Nick Carraway, Nick Carraway"** [Summaries]
   - Redundant name repetition. Very minor cosmetic issue.

### LOW

6. **F6 clutter characters** [Completeness]
   - Ripley Snell (1 mention), Mrs. Claud Roosevelt (1 mention), Benny McClenahan (1 mention), Mrs. Ulysses Swett (1 mention) — real but extremely minor party guests
   - Not hallucinated, just noise. Not worth fixing.

## Fix Guidance for Attempt 23

**Only ONE category needs fixing: Character Extraction (7.5→8.0). Profiles now passes at 8.0 ✓.**

**Priority 1 — Fix EEE (CRITICAL): Diagnose and fix George Wilson F6 blocker**

The George Wilson issue has persisted for 4 attempts despite multiple fix attempts. The root cause remains unidentified. Two approaches:

**Approach A (Diagnostic first):** Add temporary diagnostic logging to trace what happens to "George Wilson" in the F6 flow:
```python
# At start of F6, after building existing_names:
_wilson_names = [n for n in existing_names if 'wilson' in n]
logger.warning(f"F6-DIAG: existing_names with 'wilson': {_wilson_names}")

# At each filter check for "George Wilson":
if 'george wilson' in name.lower():
    logger.warning(f"F6-DIAG: '{name}' checking existing_names: {name.lower() in existing_names}")
    logger.warning(f"F6-DIAG: '{name}' normalized: {_normalize_name_for_matching(name)} in existing: {_normalize_name_for_matching(name) in existing_names}")
```

Then run analysis, capture logs, identify the exact blocker.

**Approach B (Bypass):** After the main F6 loop, add a safety-net pass:
- For each character in `characters_present` across ALL chapters, if a name:
  1. Contains at least one proper noun (capitalized word)
  2. Appears in `characters_present` for ≥ 2 chapters
  3. Is NOT already in the character list (exact or normalized match)
  4. Is NOT a substring/superset of an existing character with the SAME first name
- Then force-add it via `_f6_add_character`
- This would catch George Wilson (proper noun, 3 chapters, not in list, different first name from "Myrtle Wilson")

**Recommend Approach A first** to understand the root cause, then apply a targeted fix.

**Priority 2 — Fix FFF (HIGH): James Gatz → Gatsby merge**

After F6 adds characters and Step 4.5.9 runs, add a check:
- For each F6-reconciled character (hash ID), check if its `relationships` reference another character
- If the F6 char has a relationship like "Henry C. Gatz: child" and an existing main_cast char also has "Henry C. Gatz: father/son" → they share a family connection → merge the F6 char into the main_cast char as an alias
- This is a universal pattern: if two characters independently claim familial relationships with the same third character, they may be the same person

**Do NOT fix: Nick↔Daisy cousin (narrator limitation), Gatsby→Daisy label (Profiles passes), Ch I redundancy (cosmetic), F6 clutter (valid characters).**

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
| 17 | Third-party spousal attribution (30-char) | `src/pipeline/character_profiling/post_corrections.py` | **PARTIALLY EFFECTIVE** |
| 17 | Dead code cleanup (STEP 5.9.9, 5.12) | `src/agents/characters.py` | **EFFECTIVE** ✓ (-150 lines) |
| 18 | Remove third-party check + competitive selection | `src/pipeline/character_profiling/post_corrections.py` | **MIXED** |
| 18 | Unknown-gender spousal guard | `src/pipeline/character_profiling/post_corrections.py` | **EFFECTIVE** ✓ |
| 19 | Block generic→spousal upgrade | `src/pipeline/character_profiling/post_corrections.py` | **TOO AGGRESSIVE** |
| 19 | Cousin label support | `src/pipeline/character_profiling/post_corrections.py`, `src/analyzer.py` | **DID NOT TAKE EFFECT** |
| 20 | Named-spouse proximity check | `src/pipeline/character_profiling/post_corrections.py` | **EFFECTIVE** ✓ |
| 20 | Gender-opposite propagation | `src/pipeline/character_profiling/post_corrections.py` | **NOT EXERCISED** |
| 21 | F6 description-phrase proper-noun guard (Fix ZZ-2) | `src/analyzer.py` | **EFFECTIVE** (blocker removed) |
| 21 | STEP 4.5.9 F6-protection transfer (Fix ZZ-3) | `src/analyzer.py` | **EFFECTIVE** (F6 chars survive) |
| 21 | Leading-only initial stripping (Fix ZZ-1) | `src/analyzer.py` | **EFFECTIVE** (middle initials preserved) |
| 21 | Alias-aware char_by_name (Fix AAA) | `src/pipeline/character_profiling/post_corrections.py` | **NOT EFFECTIVE** (Myrtle→Catherine still "associated") |
| 22 | F6 last_name single-word exception (Fix BBB) | `src/analyzer.py` | **DID NOT RESOLVE** (George Wilson still missing) |
| 22 | Sibling↔spousal cross-tier guard (Fix CCC) | `src/pipeline/character_profiling/post_corrections.py` | **EFFECTIVE** ✓ (Myrtle→Catherine sister) |
| 22 | reject_unfounded_friend_labels (Fix DDD) | `src/pipeline/character_profiling/post_corrections.py` | **EFFECTIVE** ✓ (fabricated friendships removed) |

## Configuration Audit
- Model: `qwen3-next:80b-a3b-instruct-q8_0` for all agents (think_mode: false)
- Context length: 32768 — adequate for Gatsby's chapter sizes
- Temperature: 0.7 — reasonable
- Zero LLM retries — no prompt/schema failures

## Pipeline Notes (Attempt 22)
- 26 characters found — George Wilson: STILL MISSING
- Nick Carraway confirmed as narrator ✓
- 149 pronunciation flags (148 with IPA)
- Fix BBB applied but George Wilson NOT resolved
- Fix CCC effective (Myrtle→Catherine sister ✓)
- Fix DDD effective (Wolfshiem friendships cleaned ✓)
- Owl Eyes recovered (1 mention, F6 reconciled)
- James Gatz new false split from Gatsby (4 mentions, F6 reconciled)
- Profiles now at 8.0 threshold ✓ — only Character Extraction remains below

## Next Action
Run PROMPT_fix.md to diagnose and fix George Wilson F6 blocker (Fix EEE: diagnostic logging + targeted fix). Secondary: James Gatz false split (Fix FFF).
