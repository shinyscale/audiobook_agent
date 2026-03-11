# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 22
- **Phase:** awaiting_analysis
- **baseline_score:** 5.90

## Output Files
- HTML: ../output/gatsby/report.html
- JSON: ../output/gatsby/analysis.json
- Timestamped: output/gatsby_20260311_025616/

## Latest Scores
- Structure Detection: 10/10 ✓
- Character Extraction: 7/10 ✗
  - Completeness: 6/10 (George Wilson STILL missing — 21st attempt; Owl Eyes REGRESSION — 0 entries now, was 2 in attempt 20)
  - Identity Resolution: 9/10 (no false splits or merges)
  - Alias Grouping: 9/10 (clean)
- Character Profiles: 7.5/10 ✗ (Gatz↔Gatsby father/son FIXED ✓; but Wolfshiem fabricated friendships persist, Myrtle→Catherine still "associated" not "sister")
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 8.5/10 ✓ (148/149 with IPA)
- HTML Presentation: 8.5/10 ✓
- **Overall: 8.18/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold: Character Extraction 7.0, Character Profiles 7.5)

## What Changed in Attempt 22

### Fix BBB (George Wilson F6 blocker — last_name single-word exception) — APPLIED
- Modified `_is_likely_alias_of_existing` in `src/analyzer.py`: the `last_name == char_canonical` check now only fires when the existing char has a MULTI-WORD canonical name (`len(char_canonical.split()) > 1`).
- Previously: "George Wilson" was blocked because `last_name = "wilson"` matched single-word existing char "Wilson"
- Now: single-word existing chars like "Wilson" no longer block multi-word F6 candidates
- Step 4.5.9 will then absorb the single-word "Wilson" into "George Wilson" (canonical word-subset match)
- Expected: George Wilson appears in final character list

### Fix CCC (Myrtle→Catherine "associated" — sibling↔spousal cross-tier guard) — APPLIED
- Root cause (diagnosed): `verify_relationships_from_text` changed Myrtle→Catherine from "sister" to "husband" because a 500-char co-mention window contained "her husband" (referring to George Wilson's marriage, not Myrtle-Catherine). `enforce_gender_consistency` then changed "husband"→"wife". `_enforce_one_spouse_invariant` then downgraded to "associated".
- Fix: Added `_SIBLING_TIER` to `verify_relationships_from_text` cross-tier guards. "sister/brother/cousin/aunt/uncle/nephew/niece" labels cannot be overridden by spousal terms from co-mention window evidence, and vice versa.
- Verified: After fix, Myrtle→Catherine correctly = "sister"

### Fix DDD (Wolfshiem fabricated friendships — reject_unfounded_friend_labels) — APPLIED
- Added new `reject_unfounded_friend_labels()` method to `OutputCharacterCorrector` in `post_corrections.py`
- Logic: For each "friend" label A→B, check if both A's name, B's name, AND the word "friend" appear within 150 chars in source text. If not: downgrade to "associated".
- Runs after `verify_relationships_from_text` but before `reject_unfounded_familial_labels`
- Verified: Wolfshiem→Daisy/Tom/Jordan removed ✓; Wolfshiem→Nick (Gatsby's lunch scene) preserved ✓; Nick→Wolfshiem preserved ✓; Daisy↔Dan Cody removed ✓

## What Changed in Attempt 21

### Fix ZZ (George Wilson F6 blocker) — PARTIALLY EFFECTIVE
- Fix ZZ Part 2 (proper-noun guard in description-phrase check) likely worked for blocking the false-alias path
- BUT George Wilson is STILL MISSING from the 26-character output
- Summary text uses "George B. Wilson" (with middle initial "B.") in Ch II — this is a different surface form from "George Wilson"
- F6 text-scan may still be blocked by name-component check (Fix KK): "Wilson" is a component of existing "Myrtle Wilson"
- The full name "George B. Wilson" may also fail matching because of the middle initial

### Fix AAA (alias-aware char_by_name in propagate_missing_reverses) — NOT FULLY EFFECTIVE
- Myrtle→Catherine STILL "associated" (should be "sister")
- Catherine→Myrtle correctly says "sister" ✓
- The fix was supposed to enable propagation but it's not firing for this pair
- Possible: the relationship key is "Catherine" (not an alias), so original lookup worked fine — the bug is elsewhere

### Gatz↔Gatsby father/son — FIXED ✓
- Henry C. Gatz→Gatsby: "father" ✓
- Gatsby→Henry C. Gatz: "son" ✓
- This is a genuine improvement from attempt 20 where Gatz had 0 relationships

### Owl Eyes — REGRESSION ✗
- In attempt 20: 2 entries ("Man with owl-eyed glasses" + "Owl Eyes")
- In attempt 21: 0 entries — completely absent
- "the man with owl-eyed glasses" appears in Ch IX summary text
- LLM variance — neither Pass 1 nor F6 picked it up this run
- This is a regression

### Wolfshiem fabricated friendships — PERSISTENT
- Wolfshiem→Daisy "friend", →Tom "friend", →Jordan "friend", →Nick "friend" — all fabricated
- Daisy→Wolfshiem "friend", Tom→Wolfshiem "friend" — reciprocals also fabricated
- Dan Cody→Daisy "friend" and Daisy→Dan Cody "friend" — also fabricated
- Total: ~10 fabricated relationship entries persist

### Other
- "Nick Carraway, Nick Carraway" redundancy in Ch I summary still present
- Nick↔Daisy: no cousin relationship (persistent limitation)
- 26 characters (up from 25 in attempt 20) — the 26th appears to be "Servants" (F6 reconciled)

## Current Issues (Priority Order)

### CRITICAL

1. **George Wilson missing from character list — STILL not resolved after Fix ZZ** [Completeness]
   - Problem: George Wilson — Myrtle's husband, kills Gatsby, kills himself — is NOT in the 26-character output. Has been missing since attempt 19.
   - Evidence: Summary Ch II says "George B. Wilson" (with middle initial), Ch VII/VIII/IX mention "Wilson" multiple times. He appears in at least 4 chapter summaries.
   - Root cause analysis: Fix ZZ addressed the description-phrase blocker, but George Wilson is STILL missing. Two remaining blockers:
     1. **F6 name-component check (Fix KK)**: "Wilson" as a single word matches component of "Myrtle Wilson" → blocked. "George Wilson" or "George B. Wilson" as multi-word names — the surname "Wilson" still collides.
     2. **The name in text is "George B. Wilson"** (with middle initial) — may not be recognized as a standard first+last name pattern.
   - Location: `src/analyzer.py` — F6 reconciliation logic. The name-component check (Fix KK) needs a **same-surname-different-first-name exception**: when a found name like "George [B.] Wilson" shares a surname with existing "Myrtle Wilson" but has a DIFFERENT first name, it should be treated as a distinct character.
   - **Fix approach (Fix BBB): Same-surname different-person exception in F6 name-component check**
     - In the Fix KK component-check logic, when blocking a name because one of its words is a component of an existing character:
       1. Extract the SURNAME (last word) from the candidate name
       2. Find existing characters whose canonical name or aliases contain that surname
       3. If the candidate has a DIFFERENT first name from ALL matching existing characters → it's a different person → DO NOT block
       4. If the candidate is just a bare surname "Wilson" → still block (ambiguous)
     - Example: "George Wilson" → surname "Wilson" matches "Myrtle Wilson" → first name "George" ≠ "Myrtle" → allow through

2. **Owl Eyes completely missing — REGRESSION from attempt 20** [Completeness]
   - Problem: "the man with owl-eyed glasses" appears in Ch IX summary but NO character entry exists. In attempt 20 there were 2 entries (split). Now there are 0.
   - Evidence: Ch III (Gatsby's library) and Ch IX (funeral) both feature this character
   - Root cause: LLM variance — Pass 1 didn't extract him, and F6 text-scan didn't find a matchable name
   - Location: This is LLM variance, not a code bug. The name "man with owl-eyed glasses" is a descriptor, not a proper name. F6 looks for proper nouns.
   - Fix: No reliable code fix — this is LLM extraction variance. May self-correct on re-run.

### HIGH

3. **Wolfshiem fabricated friendships (10+ entries)** [Profiles]
   - Problem: Wolfshiem has "friend" with Daisy, Tom, Jordan, Nick. Reciprocals exist. Dan Cody↔Daisy "friend" also fabricated. ~10 fabricated entries.
   - Evidence: Wolfshiem appears in Ch IV (lunch with Gatsby+Nick) and Ch IX (refuses funeral). Never interacts with Daisy, Tom, Jordan. Dan Cody died before Gatsby met Daisy.
   - Root cause: LLM profiler hallucination — generates "friend" for characters in the same novel
   - Location: `src/analyzer.py` — `_generate_character_profile()` / LLM profiler
   - Fix approach: Post-correction heuristic — if a supporting/minor character has >3 "friend" relationships AND their chapter appearances don't overlap with the friend targets, demote to "associated". OR: add co-occurrence validation — only allow "friend" if both characters appear in at least one common chapter's active_characters or summary text.

4. **Myrtle→Catherine "associated" instead of "sister"** [Profiles]
   - Problem: Catherine→Myrtle correctly says "sister" ✓ but reverse is "associated" ✗
   - Evidence: They are sisters. The reciprocal should be "sister".
   - Root cause: Fix AAA expanded char_by_name to include aliases, but `_propagate_missing_reverses` may have another condition preventing override of existing non-null labels. The function may only fire when the target relationship is None, not when it's "associated".
   - Location: `src/pipeline/character_profiling/post_corrections.py` — `_propagate_missing_reverses`
   - Fix: Verify that the "override generic labels" logic from Fix RR (attempt 16) is working. Check if "associated" is in the list of generic labels that get overridden.

5. **Nick↔Daisy: no relationship (should be "cousin")** [Profiles]
   - Persistent across 21 attempts. First-person narrator limitation — Nick says "my cousin" but text says "I" not "Nick".
   - No reliable fix available.

### MEDIUM

6. **Daisy↔Dan Cody "friend" — fabricated** [Profiles]
   - Daisy and Dan Cody never interact. Cody died years before Gatsby met Daisy.
   - LLM profiler hallucination. Same root cause as issue #3.

7. **Nick→Wolfshiem "friend" — questionable** [Profiles]
   - Nick meets Wolfshiem once at lunch in Ch IV. "friend" is a stretch.
   - Minor — could be "associated".

8. **Ch I summary starts with "Nick Carraway, Nick Carraway"** [Summaries]
   - Redundant name repetition. Very minor cosmetic issue.

### LOW

9. **F6 clutter characters** [Completeness]
   - "Lutheran minister from Flushing" (1 mention), "West Egg postman" (1 mention), "New York reporter" (1 mention) — very minor characters
   - These are real characters from the text, not hallucinated, but add noise
   - Low impact — not worth fixing

## Fix Guidance for Attempt 22

**Two categories need fixing: Character Extraction (7.0→8.0) and Character Profiles (7.5→8.0).**

**Priority 1 — Fix BBB (CRITICAL): Same-surname different-person exception in F6 name-component check**

The George Wilson blocker is now clearly in the Fix KK name-component check. When F6 finds "George Wilson" or "George B. Wilson" in summary text, it checks if any word is a component of an existing character. "Wilson" matches "Myrtle Wilson" → blocked. But "George" ≠ "Myrtle" → these are DIFFERENT people.

In `src/analyzer.py`, find the Fix KK name-component check in the F6 logic. Add an exception:
```python
# When blocking because word W is a component of existing character E:
# If candidate name has a first name AND E has a first name AND they differ → different person → allow
# Only block if candidate is a bare surname (single word) or shares the same first name
```

This is the SAME logic described in Fix ZZ guidance for attempt 21, but Fix ZZ addressed a DIFFERENT blocker (description-phrase check). The name-component check (Fix KK) is the REMAINING blocker.

**Priority 2 — Fix CCC (HIGH): Verify _propagate_missing_reverses override logic**

Check `_propagate_missing_reverses` in `post_corrections.py`:
1. Is "associated" in the generic labels list that gets overridden?
2. Does the function actually fire when B→A already has a value (not None)?
3. Add debug logging to trace why Myrtle→Catherine "associated" is not being overridden to "sister"

**Priority 3 — Fix DDD (HIGH): Co-occurrence validation for "friend" relationships**

Add a post-correction step: if character X has >3 "friend" relationships AND X is supporting/minor cast, validate each "friend" by checking if both X and the friend target appear in at least one common chapter summary. If no co-occurrence → demote to "associated".

This would fix Wolfshiem's fabricated friendships and Daisy↔Dan Cody.

**Do NOT fix: Owl Eyes (LLM variance), Nick↔Daisy cousin (narrator limitation), Ch I redundancy (cosmetic), F6 clutter (valid characters).**

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
| 22 | TBD | TBD | Fix BBB (George Wilson last_name single-word exception), Fix CCC (sibling↔spousal guard), Fix DDD (reject_unfounded_friend_labels). |

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
- **Fix BBB: F6 last_name single-word exception** — APPLIED; modified `last_name == char_canonical` check to only fire for multi-word existing chars; single-word surname-only chars no longer block multi-word F6 candidates
- **Fix CCC: Sibling↔spousal cross-tier guard in verify_relationships_from_text** — APPLIED; added `_SIBLING_TIER` set; sibling labels cannot be overridden by spousal terms from co-mention windows
- **Fix DDD: `reject_unfounded_friend_labels` post-correction** — APPLIED; new method requires both names + "friend" within 150 chars in source text; removes fabricated Wolfshiem friendships

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

## Configuration Audit
- Model: `qwen3-next:80b-a3b-instruct-q8_0` for all agents (think_mode: false)
- Context length: 32768 — adequate for Gatsby's chapter sizes
- Temperature: 0.7 — reasonable
- Zero LLM retries — no prompt/schema failures

## Pipeline Notes (Attempt 21)
- Completed in 89m 9s
- 26 characters found (George Wilson NOT present despite Fix ZZ)
- Nick Carraway confirmed as narrator ✓
- 149 pronunciation flags (148 with IPA)
- Fix ZZ removed one blocker (description-phrase) but Fix KK component check still blocks "Wilson"
- Owl Eyes completely absent (regression from 2 entries in attempt 20)
- Gatz↔Gatsby father/son NOW CORRECT (improvement)

## Next Action
Run PROMPT_fix.md to address George Wilson (Fix BBB: same-surname exception in Fix KK component check) and relationship quality (Fix CCC: propagation debug, Fix DDD: co-occurrence validation for "friend").
