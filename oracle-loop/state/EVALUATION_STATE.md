# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 20
- **Phase:** awaiting_fix
- **baseline_score:** 5.90

## Output Files
- HTML: ../output/gatsby/report.html
- JSON: ../output/gatsby/analysis.json
- Timestamped: output/gatsby_20260311_003630/

## Latest Scores
- Structure Detection: 10/10 ✓
- Character Extraction: 7.5/10 ✗
  - Completeness: 7/10 (George Wilson STILL missing — 20th attempt)
  - Identity Resolution: 8/10 (Owl Eyes still split into 2 entries)
  - Alias Grouping: 9/10 (clean)
- Character Profiles: 7.5/10 ✗ (Tom↔Daisy FIXED ✓, but fabricated Wolfshiem friendships + missing reciprocals)
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 8.5/10 ✓ (148/149 with IPA)
- HTML Presentation: 8.5/10 ✓
- **Overall: 8.40/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold: Character Extraction 7.5, Character Profiles 7.5)

## What Changed in Attempt 20

### Fix XX (Named-spouse check) — EFFECTIVE ✓
- **Tom↔Daisy: "husband"/"wife" CORRECT** — the critical regression from attempt 19 is FIXED
- Tom→Daisy "husband" ✓, Daisy→Tom "wife" ✓
- No false spousals detected (Nick↔Myrtle gone ✓, George↔Catherine gone ✓, McKee→Myrtle gone ✓)
- Fix XX's proximity-based check correctly allows genuine spousal attribution while blocking third-party references

### Fix YY (Gender-opposite propagation) — NOT EXERCISED
- Gatsby→Henry C. Gatz has NO relationship at all now (Gatz has 0 relationships)
- The "daughter" bug can't manifest because no relationship was generated
- Fix YY's logic is in place but couldn't fire — neutral result

### George Wilson — STILL MISSING (attempt 20)
- "Wilson" appears 4+ times in summary text, "George Wilson" appears once (Ch IX)
- `active_characters` is EMPTY for ALL 9 chapters — the LLM summarizer generated no character metadata
- F6 text-scan found other names (Butler, Chauffeur, Gardener, Biloxi, etc.) but NOT Wilson
- Root cause: F6 name-component check (Fix KK, attempt 13) blocks "Wilson" because it's a surname component of existing "Myrtle Wilson". The full name "George Wilson" may also be blocked because "Wilson" matches.
- **This is now a CODE BUG, not just LLM variance** — Wilson appears in the text but F6 blocks it

### Fabricated Wolfshiem Friendships — NEW PATTERN IDENTIFIED
- Wolfshiem has "friend" relationships with Daisy, Tom, Jordan, Nick, and "protégé" with Chauffeur — ALL fabricated
- Wolfshiem interacts almost exclusively with Gatsby; has one scene with Nick
- 5+ fabricated "friend" labels from the LLM profiler for one character
- Reciprocal: Daisy→Wolfshiem "friend", Tom→Wolfshiem "friend", Jordan→Wolfshiem "friend" — all fabricated
- Total: ~10 fabricated Wolfshiem relationships across the character graph

### Other Issues
- Myrtle→Catherine "associated" (should be "sister"; reciprocal of Catherine→Myrtle "sister") — `_propagate_missing_reverses` not firing
- Nick↔Daisy: no relationship at all (should be "cousin") — persistent across attempts
- Daisy→Dan Cody "friend" — fabricated (Daisy has no interaction with Dan Cody)
- Henry C. Gatz has 0 relationships — missing father↔son with Gatsby
- "Nick Carraway, Nick Carraway" — redundant name at start of Ch I summary (minor)

## Current Issues (Priority Order)

### CRITICAL

1. **George Wilson missing from character list — F6 blocks surname component** [Completeness]
   - Problem: George Wilson — Myrtle's husband, kills Gatsby, kills himself — is NOT in the 25-character output. He's been missing in attempts 19 and 20.
   - Evidence: "Wilson" appears 4+ times in summary text. "George Wilson" appears once. But `active_characters` metadata is empty for all chapters. F6 text-scan finds other names but blocks "Wilson" as a component of existing "Myrtle Wilson".
   - Root cause: Fix KK (attempt 13) added a name-component check to F6 that blocks single-word names matching components of existing characters. "Wilson" matches "Myrtle Wilson". The full name "George Wilson" may also fail the check because its surname component "Wilson" collides.
   - Location: `src/analyzer.py` — F6 reconciliation logic (~line 1197+). The name-component check needs an exception: if a FULL NAME (first + last) is found in summary text where the last name matches an existing character, but the FIRST name is DIFFERENT, treat it as a DISTINCT character.
   - **Fix approach (Fix ZZ): Same-surname, different-first-name exception in F6**
     - When F6 text-scan finds "George Wilson" in summary text:
       1. Check if "Wilson" is a component of existing character "Myrtle Wilson" — YES
       2. Check if "George" is part of "Myrtle Wilson" — NO
       3. Since "George Wilson" has a DIFFERENT first name from "Myrtle Wilson", it's a different person → DO NOT block
     - This is the same logic the pipeline already uses elsewhere (shared surname = different people if different first names, per CLAUDE.md guidance)

### HIGH

2. **Fabricated Wolfshiem friendships (10+ entries)** [Profiles]
   - Problem: Wolfshiem has fabricated "friend" relationships with Daisy, Tom, Jordan, Nick, and "protégé" with Chauffeur. Reciprocals exist too. ~10 fabricated entries total.
   - Evidence: Wolfshiem appears in Ch 4 (lunch with Gatsby+Nick) and Ch 9 (refuses to attend funeral). He never directly interacts with Daisy, Tom, Jordan, or Chauffeur.
   - Root cause: LLM profiler hallucination — generates "friend" for characters that appear in the same book even if they never interact
   - Location: `src/analyzer.py` — `_generate_character_profile()` / LLM profiler prompt
   - Fix: Hard to fix at source (LLM behavior). Possible post-correction: if a character has >4 "friend" relationships and is a minor/supporting character, flag as suspicious and demote to "associated". OR: add a co-occurrence threshold — only allow "friend" if both characters appear in the same chapter's active_characters.

3. **Myrtle→Catherine "associated" instead of "sister"** [Profiles]
   - Problem: Catherine→Myrtle correctly says "sister" but the reverse is "associated"
   - Evidence: They are sisters — this should be reciprocal
   - Root cause: `_propagate_missing_reverses` should handle this but may have a bug — perhaps it only fires when no relationship exists (Myrtle→Catherine has "associated", which is non-null, so it's skipped)
   - Location: `src/pipeline/character_profiling/post_corrections.py` — `_propagate_missing_reverses`
   - **Fix approach: In `_propagate_missing_reverses`, when A→B has a specific label ("sister") but B→A has only a generic label ("associated"), override B→A with the appropriate reciprocal**

4. **Henry C. Gatz has 0 relationships — missing father↔son** [Profiles]
   - Problem: Gatz has no relationships at all. Should have father↔son with Gatsby.
   - Evidence: Gatz arrives for his son's funeral, shares memorabilia about "Jimmy" — clearly father
   - Root cause: LLM profiler didn't generate any relationships for Gatz. `_propagate_missing_reverses` can't help because there's no Gatsby→Gatz relationship either.
   - Location: LLM profiler output variance. May self-correct on re-run.

5. **Nick↔Daisy: no relationship (should be "cousin")** [Profiles]
   - Problem: Persistent across multiple attempts. Fix WW added cousin support but hasn't taken effect.
   - Evidence: Ch. 1: "Daisy was my second cousin once removed"
   - Root cause: First-person narrator limitation — Nick says "my cousin" but "Nick" doesn't appear in the text near "cousin" (he uses "I")
   - Location: This is a fundamental limitation of text-evidence-based relationship detection for first-person narrators

### MEDIUM

6. **Daisy→Dan Cody "friend" — fabricated** [Profiles]
   - Daisy and Dan Cody have no direct relationship. Dan Cody died before Gatsby met Daisy.
   - Source: LLM profiler hallucination
   - Impact: Minor

7. **"Man with owl-eyed glasses" and "Owl Eyes" are separate entries** [Identity Resolution]
   - Persistent across multiple attempts. Both have 1 mention.
   - Impact: Low — minor character duplication

8. **Ch I summary starts with "Nick Carraway, Nick Carraway"** [Summaries]
   - Redundant name repetition at the start of the first chapter summary
   - Impact: Very low — cosmetic

## Fix Guidance for Attempt 21

**Two categories need fixing: Character Extraction (7.5→8.0) and Character Profiles (7.5→8.0).**

**Fix ZZ (CRITICAL — addresses issue #1): Same-surname different-first-name exception in F6**

In the F6 text-scan logic in `src/analyzer.py`, when a name found in summary text is blocked because its surname is a component of an existing character:
1. Check if the found name has a DIFFERENT first name from the existing character
2. If yes → different person → allow through (do NOT block)
3. If the found name is just a bare surname "Wilson" → still block (could refer to either)

This should restore George Wilson to the character list without introducing duplicates.

**Fix AAA (HIGH — addresses issue #3): Override generic labels in `_propagate_missing_reverses`**

In `_propagate_missing_reverses` in `post_corrections.py`:
- Currently only fires when B→A relationship is MISSING (None/empty)
- Should ALSO fire when B→A has a GENERIC label ("associated", "acquaintance") but A→B has a SPECIFIC label ("sister", "brother", "father", etc.)
- When A→B = "sister" and B→A = "associated", override B→A with the reciprocal of "sister" = "sister"

**No code fix for Wolfshiem friendships (issue #2)** — LLM profiler hallucination. May improve on re-run. If persistent after attempt 21, consider a post-correction heuristic that limits "friend" relationships for minor characters.

**No code fix for Gatz relationships (issue #4) or Nick↔Daisy (issue #5)** — LLM variance and first-person narrator limitation respectively.

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
| 19 | Block generic→spousal upgrade | `src/pipeline/character_profiling/post_corrections.py` | **TOO AGGRESSIVE** (blocked false + legitimate spousals) |
| 19 | Cousin label support | `src/pipeline/character_profiling/post_corrections.py`, `src/analyzer.py` | **DID NOT TAKE EFFECT** |
| 20 | Named-spouse proximity check | `src/pipeline/character_profiling/post_corrections.py` | **EFFECTIVE** ✓ (Tom↔Daisy restored, no false spousals) |
| 20 | Gender-opposite propagation | `src/pipeline/character_profiling/post_corrections.py` | **NOT EXERCISED** (Gatz has 0 rels) |

## Configuration Audit
- Model: `qwen3-next:80b-a3b-instruct-q8_0` for all agents (think_mode: false)
- Context length: 32768 — adequate for Gatsby's chapter sizes
- Temperature: 0.7 — reasonable
- Zero LLM retries — no prompt/schema failures

## Pipeline Notes (Attempt 20)
- Completed in 87m 57s
- 25 characters found (George Wilson NOT present)
- Nick Carraway confirmed as narrator ✓
- James Gatz added as referenced character ✓
- 149 pronunciation flags
- Fix XX effective ✓, Fix YY not exercised
- active_characters metadata EMPTY for all chapters — LLM summarizer didn't populate it

## Next Action
Run PROMPT_fix.md to address:
1. Fix ZZ: Same-surname different-first-name exception in F6 (George Wilson)
2. Fix AAA: Override generic labels in `_propagate_missing_reverses` (Myrtle→Catherine "sister")
