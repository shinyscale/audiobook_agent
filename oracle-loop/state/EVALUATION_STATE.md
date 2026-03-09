# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 16
- **Phase:** awaiting_evaluation
- **baseline_score:** 5.90

## Output Files
- HTML: ../output/gatsby/report.html
- JSON: ../output/gatsby/analysis.json
- Timestamped: output/gatsby_20260308_210438/

## Latest Scores
- Structure Detection: 10/10 ✓
- Character Extraction: 8/10 ✓
  - Completeness: 7.5/10 (George Wilson still missing)
  - Identity Resolution: 9/10
  - Alias Grouping: 8/10 (Gatsby missing "James Gatz" alias — LLM variance)
- Character Profiles: 7.5/10 ✗ (FAILING)
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 8.5/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 8.53/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (1 category below threshold: Character Profiles 7.5/10)

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

## What Changed in Attempt 15

### Fix NN (word-boundary in `_infer_rel`) — EFFECTIVE ✓
- "affairs" no longer substring-matches "affair" → Dan Cody↔Gatsby "romantic interest" ELIMINATED
- Gatsby→Dan Cody now correctly "protégé", Dan Cody→Gatsby now "mentor"

### Fix OO (tighter romantic keyword window) — EFFECTIVE ✓
- Tom→Jordan Baker no longer "romantic interest" (now "associated")
- Tom→Catherine "romantic interest" GONE entirely

### Fix PP (strong family evidence override) — EFFECTIVE ✓
- Catherine→Myrtle now correctly "sister"
- BUT Myrtle→Catherine is "associated" (reciprocal not generated)

### Previous fixes holding stable
- Narrator: Nick Carraway ✓ (5th consecutive stable attempt)
- Gatsby: main_cast protagonist ✓ (but "James Gatz" alias LOST this run — LLM variance)
- Daisy: aliases include Daisy Fay ✓
- Tom: alias "Tom" ✓, no F6 dup ✓
- Wolfsheim: single entry with aliases ✓

### NEW issues this run
- Gatsby→Tom Buchanan "husband" — FABRICATED. They are rivals/antagonists. Gatsby is having an affair with Tom's wife.
- Tom Buchanan→Gatsby "husband" — same fabrication, reciprocal
- Daisy↔Tom "associated" — should be "wife"/"husband" (key relationship mislabeled as vague)
- Tom→Myrtle "associated" — should be "affair" or "romantic interest"
- Wolfshiem→Tom "friend", Wolfshiem→Jordan "friend" — fabricated (no interactions in text)
- The green light→Mr. McKee "associated" — nonsensical

## Current Issues (Priority Order)

### HIGH

1. **Fabricated relationship: Gatsby↔Tom "husband"** [Profiles]
   - Problem: Both Gatsby and Tom list each other as "husband". This is completely wrong — they are rivals. Gatsby is pursuing Tom's wife Daisy.
   - Root cause: LLM profiler hallucinating. The word "husband" appears frequently near Tom (as Daisy's husband) and the LLM incorrectly assigns it to the Gatsby↔Tom pair.
   - Location: `src/pipeline/character_profiling/post_corrections.py`
   - Fix: **Same-gender spousal guard**. If two characters both have `gender: "male"` (or both "female"), block "husband"/"wife"/"spouse" labels between them. Both Gatsby and Tom have `gender: "male"`. This is a universal invariant for pre-modern literature (which this tool primarily processes). Alternatively, use the one-spouse invariant: if Tom is already Daisy's husband, he can't also be Gatsby's husband.

2. **Daisy↔Tom mislabeled as "associated"** [Profiles]
   - Problem: The most central relationship in the novel (married couple) is labeled "associated" instead of "wife"/"husband"
   - Evidence: "her husband" appears dozens of times near Tom+Daisy co-mentions
   - Location: `src/pipeline/character_profiling/post_corrections.py` — `verify_relationships_from_text` should be catching explicit spousal evidence
   - Fix: The family-evidence override (Fix PP) should work here too — "husband"/"wife" terms near co-mentions should override "associated". May need to lower the threshold from 2 occurrences to 1 for spousal terms.

3. **Myrtle→Catherine "associated" (should be "sister")** [Profiles]
   - Problem: Fix PP correctly set Catherine→Myrtle to "sister" but didn't set the reciprocal
   - Fix: When Fix PP detects family evidence and overrides a label, also check and override the reciprocal relationship. If A→B is "sister", then B→A should also be "sister".

### MEDIUM

4. **Nick and Gatsby physical_description: null** [Profiles]
   - Problem: Two protagonists lack physical descriptions. Gatsby is described ("elegant young rough-neck," "rare smile," "tanned skin"). Nick describes himself less but has some details.
   - Location: `src/analyzer.py` — `_generate_character_profile()` — LLM variance
   - Fix: Low priority. This is LLM non-determinism. Could add a fallback re-prompt for null descriptions.

5. **Wolfshiem fabricated friendships** [Profiles]
   - Problem: Wolfshiem→Tom "friend" and Wolfshiem→Jordan "friend" — these characters don't interact in the text
   - Low impact — "friend" is vague and Wolfshiem is a minor character

6. **Green light→Mr. McKee "associated"** [Profiles]
   - Problem: Nonsensical relationship between a symbol and a minor character
   - Low impact

7. **George Wilson missing from character list** [Completeness]
   - Problem: Significant character not extracted (appears in Ch 2, 7, 8, 9; kills Gatsby)
   - Note: George Wilson IS mentioned in chapter summaries ("garage owner George Wilson") so the text contains him
   - This is LLM variance in character extraction — no code change targeted this

### LOW

8. **Gatsby missing "James Gatz" alias** [Alias Grouping]
   - Was present in attempt 14, gone in attempt 15 — LLM variance
   - Henry C. Gatz has "Gatz" alias which is correct, but Gatsby should also have "James Gatz"

## Fix Guidance for Attempt 16

**Focus ONLY on getting Character Profiles from 7.5/10 to 8/10.** All other categories pass.

**Fix 1 (CRITICAL): Same-gender spousal guard in post_corrections.py**
- In the one-spouse invariant or as a new check: if character A and character B both have the same gender (both male or both female), block "husband"/"wife"/"spouse" labels between them
- This eliminates the Gatsby↔Tom "husband" fabrication
- Universal: valid for all literature this tool processes

**Fix 2 (HIGH): Reciprocal family-evidence override**
- When Fix PP detects family evidence and overrides A→B's label (e.g., Catherine→Myrtle "sister"), also override B→A's label (Myrtle→Catherine should become "sister")
- This is in `verify_relationships_from_text` in post_corrections.py
- Universal: if textual evidence says A is B's sister, B is also A's sister

**Fix 3 (HIGH): Lower family-evidence threshold for spousal terms**
- Fix PP requires 2+ family term occurrences to override. For "husband"/"wife", even 1 explicit mention near co-occurring names should suffice, because these labels are rarely ambiguous
- This should fix Daisy↔Tom "associated" → "wife"/"husband"
- OR: ensure the one-spouse invariant runs AFTER verify_relationships_from_text so that textual evidence has a chance to set the correct spousal label first

Fixing issues 1-3 removes 2 fabricated labels and adds 2-3 correct labels. That should push profiles to 8/10.

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
- **Fix QQ: Same-gender spousal guard in `_enforce_one_spouse_invariant`** — removes Gatsby↔Tom "husband" (both male → impossible)
- **Fix RR: `_propagate_missing_reverses` overwrites generic labels** — Myrtle→Catherine "associated" → "sister"; also enables Daisy→Tom propagation

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
| 16 | Same-gender spousal guard | `src/pipeline/character_profiling/post_corrections.py` | Pending |
| 16 | _propagate_missing_reverses overwrites generics | `src/pipeline/character_profiling/post_corrections.py` | Pending |

## Configuration Audit
- Model: `qwen3-next:80b-a3b-instruct-q8_0` for all agents (think_mode: false)
- Context length: 32768 — adequate for Gatsby's chapter sizes
- Temperature: 0.7 — reasonable
- Zero LLM retries — no prompt/schema failures
- Mr. McKee still LOW CONFIDENCE (0.30) — JSON parse failure during profiling

## Next Action
Run PROMPT_analyze.md to verify fixes QQ and RR.
