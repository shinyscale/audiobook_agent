# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 19
- **Phase:** awaiting_analysis
- **baseline_score:** 5.90

## Output Files
- HTML: ../output/gatsby/report.html
- JSON: ../output/gatsby/analysis.json
- Timestamped: output/gatsby_20260310_225523/

## Latest Scores
- Structure Detection: 10/10 ✓
- Character Extraction: 7.5/10 ✗ (George Wilson missing, Montenegro false positive)
  - Completeness: 7/10 (George Wilson missing — key character in climax)
  - Identity Resolution: 8/10 (Owl Eyes still split into 2 entries)
  - Alias Grouping: 9/10 (clean: James Gatz ✓, Daisy Fay ✓, Wolfshiem spelling ✓)
- Character Profiles: 6.5/10 ✗ (Tom↔Daisy REGRESSED to "associated", multiple wrong labels)
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 8.5/10 ✓ (148/149 with IPA)
- HTML Presentation: 8.5/10 ✓
- **Overall: 8.10/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold: Character Extraction 7.5, Character Profiles 6.5)

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

## What Changed in Attempt 19

### Fix VV (Block generic→spousal upgrade) — TOO AGGRESSIVE
- **Intended**: Block false spousals where "associated" pairs get upgraded to "husband"/"wife" from third-party keyword proximity
- **Actual effect**: Blocked ALL generic→spousal upgrades, including the LEGITIMATE Tom↔Daisy upgrade
- Nick↔Myrtle false spousal: GONE ✓
- George↔Catherine false spousal: GONE ✓
- **Tom↔Daisy: REGRESSED from "husband"/"wife" to "associated"** — because the LLM profiler gave them "associated" (a generic label), and Fix VV blocks all generic→spousal upgrades
- Mr. McKee→Myrtle Wilson: "husband" — NEW false spousal (likely came from LLM profiler, not text-evidence)
- Net: traded 2 false spousals for 1 major correct spousal regression

### Fix WW (Cousin label support) — DID NOT TAKE EFFECT
- Nick↔Daisy has NO relationship at all in the output
- The cousin regex fix in `_all_rel_phrase_re` only works if `verify_relationships_from_text` finds Nick and Daisy co-occurring in a text window with "cousin" — but Nick and Daisy may not co-occur near "my second cousin once removed" (Nick narrates this about himself)
- The profiler prompt change adding "cousin" also didn't produce a cousin label — LLM variance

### George Wilson MISSING — LLM VARIANCE
- George Wilson appears by name in chapter 2, 7, 8 summaries but NOT in `active_characters` metadata
- Without `active_characters` listing, F6 reconciliation doesn't detect him
- This is NOT a code bug — it's LLM variance in the summarizer's character list generation
- George Wilson was present in attempt 18; disappeared in attempt 19

### Other Issues
- Gatsby→Henry C. Gatz: "daughter" — WRONG (should be "son"; gender inference failed)
- Daisy→Dan Cody: "friend" — FABRICATED (no direct relationship in novel)
- Myrtle→Catherine: "associated" — should be "sister" (reciprocal of Catherine→Myrtle "sister")
- Montenegro: listed as character (it's a country — Wolfsheim's medal context)

## Current Issues (Priority Order)

### CRITICAL

1. **Fix VV REGRESSION: Tom↔Daisy "associated" instead of "husband"/"wife"** [Profiles]
   - Problem: Fix VV blocks ALL generic→spousal upgrades. The LLM profiler gives Tom↔Daisy "associated" (a generic label). When `verify_relationships_from_text` finds spousal keywords near Tom+Daisy co-mentions, the upgrade is blocked because "associated" is in `_generic_labels`.
   - Evidence: Attempt 18 had Tom↔Daisy "husband"/"wife" CORRECT. Attempt 19 has "associated".
   - Root cause: Fix VV's guard `if best_is_spousal and cur_lower in _generic_labels: block` is too broad. It should block upgrades ONLY when the spousal keyword refers to a THIRD character, not when it genuinely refers to the A↔B pair.
   - Location: `src/pipeline/character_profiling/post_corrections.py` — `verify_relationships_from_text` (~line 2062)
   - **Fix approach (Fix XX): Replace the blanket generic-label block with a NAMED-SPOUSE check.**
     Instead of blocking all generic→spousal upgrades, check if either character's NAME appears within ~30 chars of the spousal keyword ("husband"/"wife"/"spouse"/"married"):
     - If the spousal keyword appears as "her husband [NAME_B]" or "[NAME_A]'s wife" or "married to [NAME]", ALLOW the upgrade (the text directly attributes the spousal role to this pair)
     - If the spousal keyword appears WITHOUT either character's name nearby (just "husband" or "wife" floating in the co-mention window), BLOCK the upgrade (likely refers to a third party)
     - This preserves Fix VV's protection against false attribution while allowing legitimate spousal evidence

2. **Mr. McKee→Myrtle Wilson "husband" — false spousal from LLM** [Profiles]
   - Problem: LLM profiler generated "husband" for McKee→Myrtle Wilson. McKee is a photographer, not Myrtle's husband.
   - Evidence: Mr. McKee appears only in Ch. 2 apartment scene. George Wilson is Myrtle's husband.
   - Root cause: LLM hallucination in profiler output — the text-evidence step is NOT the source here (McKee→"Myrtle Wilson" uses full name which isn't a character ID)
   - Location: LLM profiler output — hard to fix with post-correction alone
   - Fix: This may resolve naturally if Fix XX allows George Wilson (when present) to win the spousal slot via competitive selection

### HIGH

3. **George Wilson missing from character list** [Completeness]
   - Problem: George Wilson — Myrtle's husband, kills Gatsby, kills himself — is not extracted as a character
   - Evidence: Named in chapter 2, 7, 8 summaries. Not in `active_characters` metadata.
   - Root cause: LLM variance in both character extraction AND summary `active_characters` list. Not a code bug.
   - Impact: Major completeness gap. George Wilson is essential to the plot.
   - Fix: This is LLM variance and may self-correct on re-run. No code change needed specifically — but if it persists, consider: a text-scan fallback in F6 that searches summary TEXT (not just active_characters metadata) for proper nouns that match known character name patterns.

4. **Gatsby→Henry C. Gatz "daughter" — wrong gender** [Profiles]
   - Problem: Gatsby is Henry C. Gatz's SON, not daughter. Gender inference failed.
   - Evidence: Henry C. Gatz→Gatsby correctly says "father"
   - Root cause: `_propagate_missing_reverses` or `enforce_gender_consistency` generated "daughter" instead of "son" — likely because Gatsby's gender wasn't inferred correctly in this direction
   - Location: `src/pipeline/character_profiling/post_corrections.py`
   - Fix: When propagating a "father" reverse, the child label should default to "son" if the child character has male indicators (Mr., masculine name patterns), or check the reciprocal relationship direction

5. **Nick↔Daisy: no relationship (should be "cousin")** [Profiles]
   - Problem: Fix WW added cousin support but no Nick↔Daisy relationship exists at all
   - Evidence: Ch. 1 narrator: "Daisy was my second cousin once removed"
   - Root cause: Nick narrates about Daisy in first person — the co-mention window may not contain both names near "cousin" (Nick says "my second cousin" referring to Daisy, but "Nick" doesn't appear — he's the narrator using "I")
   - Fix: First-person narrator text-evidence is inherently hard. Alternative: ensure the LLM profiler generates this relationship. The profiler prompt already includes "cousin" (Fix WW), so re-running may help. If persistent, add a narrator-specific heuristic: when the narrator uses "my cousin/my second cousin" near a character name, attribute a cousin relationship.

### MEDIUM

6. **Myrtle→Catherine "associated" (should be "sister")** [Profiles]
   - Catherine→Myrtle correctly says "sister" but the reverse is just "associated"
   - `_propagate_missing_reverses` should have fixed this — may not be firing for this pair
   - Location: `src/pipeline/character_profiling/post_corrections.py`

7. **Daisy→Dan Cody "friend" — fabricated relationship** [Profiles]
   - Daisy and Dan Cody have no direct relationship in the novel. Dan Cody is Gatsby's mentor from his youth.
   - Source: LLM profiler hallucination
   - Impact: Minor — Dan Cody is a minor character

8. **Montenegro listed as character** [Completeness]
   - Montenegro is a country (context: Wolfsheim's decoration from Montenegro)
   - 7 mentions as an entity but it's a place, not a person/character
   - Impact: Low — minor clutter

9. **"Man with owl-eyed glasses" and "Owl Eyes" are separate entries** [Identity Resolution]
   - Persistent across multiple attempts. Both have 1 mention.
   - Impact: Low — minor character duplication

## Fix Guidance for Attempt 20

**Two categories need fixing: Character Extraction (7.5→8.0) and Character Profiles (6.5→8.0).**

The profile score is the primary blocker. Character Extraction 7.5 is borderline — if George Wilson returns on re-run (LLM variance), it could reach 8.0 without code changes.

**Fix XX (CRITICAL — addresses issue #1): Named-spouse check in `verify_relationships_from_text`**

Replace the blanket `_generic_labels` block from Fix VV with a smarter check:

```python
# Instead of: if best_is_spousal and cur_lower in _generic_labels: BLOCK
# Do: if best_is_spousal and cur_lower in _generic_labels:
#       Check if either character's name appears within 30 chars of the spousal keyword
#       If yes: ALLOW (genuine attribution)
#       If no: BLOCK (third-party reference)
```

Implementation sketch:
1. When a spousal keyword is found in a co-mention window, record its position in the text
2. Check ±30 characters around the spousal keyword for either character's name (first name, last name, or canonical name)
3. If a name IS found near the keyword → the text is directly attributing the spousal role to this pair → ALLOW the upgrade
4. If NO name is found near the keyword → the keyword likely refers to a third character → BLOCK

Example: "her husband George Wilson's run-down garage" — "husband" + "George Wilson" nearby → if George↔Myrtle pair, ALLOW. If Nick↔Myrtle pair, Nick's name NOT near "husband" → BLOCK.

Example: "Tom Buchanan... his wife Daisy" — "wife" + "Daisy" nearby → Tom↔Daisy pair, ALLOW.

**Fix YY (MEDIUM — addresses issue #4): Gender-correct child label propagation**

In `_propagate_missing_reverses` or `enforce_gender_consistency`: when generating the reverse of "father"→"son"/"daughter", check the child character's gender indicators before defaulting. If child has male indicators (name "Gatsby"/"Jay Gatsby", no feminine markers), use "son" not "daughter".

**No code fix for George Wilson (issue #3)** — LLM variance. Re-running analysis may restore him. If he's still missing after attempt 20, escalate.

**No code fix for Nick↔Daisy cousin (issue #5)** — First-person narrator limitation. May resolve with LLM variance on re-run now that "cousin" is in the profiler prompt.

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
- **Fix XX: Named-spouse check in `verify_relationships_from_text`** — replaces Fix VV's blanket block with proximity check: spousal upgrade from generic allowed only when the OTHER character's name appears within 30 chars of the spousal keyword in a co-mention window. Tracks `_spousal_kw_hits` during scan and checks `pat_b.search(nearby)` at decision point. Modified: `src/pipeline/character_profiling/post_corrections.py`
- **Fix YY: Gender-opposite override in `_propagate_missing_reverses`** — extends override condition to include gender-mismatched labels (e.g., if LLM set "daughter" but reverse of "father" should be "son", override it). Universal invariant: A→B = "father" requires B→A = "son" or "daughter", never the wrong-gender variant. Modified: `src/pipeline/character_profiling/post_corrections.py`

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

## Configuration Audit
- Model: `qwen3-next:80b-a3b-instruct-q8_0` for all agents (think_mode: false)
- Context length: 32768 — adequate for Gatsby's chapter sizes
- Temperature: 0.7 — reasonable
- Zero LLM retries — no prompt/schema failures

## Next Action
Run analysis to verify Fix XX + Fix YY effectiveness.

**KEY INSIGHT from 6 attempts at spousal attribution (attempts 14-19):**
The `verify_relationships_from_text` function's co-mention window approach is fundamentally flawed for spousal detection. The window captures "husband"/"wife" keywords but cannot reliably determine WHO the keyword refers to. Each fix has traded one set of wrong pairs for another. Fix XX (checking if a character's name appears near the keyword) is the most promising approach because it uses direct textual attribution rather than proximity alone.
