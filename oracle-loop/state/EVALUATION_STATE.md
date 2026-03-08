# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 13
- **Phase:** awaiting_analysis
- **baseline_score:** 5.90

## Output Files
- HTML: ../output/gatsby/report.html
- JSON: ../output/gatsby/analysis.json
- Timestamped: output/gatsby_20260308_151658/

## Latest Scores
- Structure Detection: 10/10 ✓
- Character Extraction: 8/10 ✓
  - Completeness: 8/10
  - Identity Resolution: 8.5/10
  - Alias Grouping: 8/10
- Character Profiles: 7/10 ✗ (FAILING)
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 8.5/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 8.40/10** (reference only)

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
| 13 | 8.40 | +2.50 | **BREAKTHROUGH**: Tom F6 dup FIXED ✓, Wolfsheim dedup FINALLY FIXED ✓ (7th attempt). Character Extraction passes 8.0. Only Profiles (7/10) remains below threshold. |

## What Changed in Attempt 13

### Fix KK (F6 single-word name component check) — EFFECTIVE ✓
- "Tom" is now an alias of "Tom Buchanan" (main_cast_3, 196 mentions)
- No separate "Tom" F6 entry exists
- The critical F6 duplicate that destroyed Identity Resolution in attempt 12 is completely resolved

### Fix LL (Step 4.5.9 post-extraction word-subset dedup) — EFFECTIVE ✓
- Only ONE Wolfsheim entry: main_cast_7 "Meyer Wolfsheim" (32 mentions) with alias "Meyer Wolfshiem"
- The supporting_1 "Wolfshiem" entry is GONE — successfully merged
- **THIS ENDS THE 7-ATTEMPT STUCK PATTERN** — escalation to analyzer.py post-extraction merge (bypassing V2 pipeline internals) was the correct strategy

### Previous fixes holding stable
- Narrator: Nick Carraway ✓ (3rd consecutive stable attempt)
- Gatsby: main_cast protagonist with aliases James Gatz, Jay Gatsby ✓
- Daisy: aliases include Daisy Fay, Daisy Buchanan ✓
- No Gatsby↔Jordan false spousal (Fix BB holding) ✓

## Current Issues (Priority Order)

### HIGH

1. **Myrtle↔Catherine "brother" — wrong gender** [Profiles]
   - Problem: Catherine is Myrtle's SISTER, not brother. Both are female.
   - Root cause: Both Myrtle and Catherine have `gender: null` in the output. The `enforce_gender_consistency` post-correction cannot fix "brother"→"sister" without knowing both characters are female.
   - Location: `src/pipeline/character_profiling/post_corrections.py` — `enforce_gender_consistency`
   - Fix: The profiler needs to infer gender from context. Myrtle is described as a woman (Mrs. Wilson), Catherine as "her sister." Alternatively, add a fallback: if a "brother" relationship exists between two characters and the OTHER character's name/description/text strongly implies female, override to "sister." Or: improve gender extraction in `_generate_character_profile()` to set gender based on pronouns/titles.

2. **Daisy→Dan Cody "friend" — FABRICATED** [Profiles]
   - Problem: Daisy and Dan Cody never interact in the text. Cody dies before Gatsby meets Daisy.
   - Location: `src/analyzer.py` profile generation
   - Fix: This is an LLM hallucination. The profiler generates relationship entries for characters who co-appear in the same chapter summaries but have no actual relationship. A text-evidence requirement (must find both names within N characters of each other in actual text) would catch this.

3. **George Wilson→Myrtle "associated" — should be "husband"** [Profiles]
   - Problem: George Wilson is Myrtle Wilson's husband. "associated" is far too vague.
   - Root cause: Likely the spouse evidence window (Fix O) is too tight at 150 chars, or the text evidence for their marriage isn't found in the right window.
   - Location: `src/pipeline/character_profiling/post_corrections.py`

4. **Tom Buchanan verbal tic "old sport" is WRONG** [Profiles]
   - Problem: "old sport" is GATSBY's iconic catchphrase. Tom explicitly rejects it: "Don't you call me 'old sport'!" The LLM assigned it to Tom's verbal_tics AND included it in example_quotes ("I've got something to tell you, old sport—") which is actually Gatsby speaking.
   - Location: `src/analyzer.py` profile generation (voice_guidance extraction)
   - Fix: LLM hallucination. Could add a post-processing step that checks if a verbal tic attributed to character A is actually a known tic of character B (i.e., appears in B's quotes far more frequently). More practically: the profiler prompt could instruct "only include verbal tics from quotes DIRECTLY attributed to this character."

5. **Gatsby missing physical description** [Profiles]
   - Problem: Gatsby has `physical_description: null` but the text describes him: "an elegant young rough-neck, a year or two over thirty," "tanned skin and short hair," "one of those rare smiles."
   - Location: `src/analyzer.py` profiler prompt
   - Fix: LLM variance. The profiler should be picking these up. May need to ensure the right text chunks are passed to the profiler for Gatsby's description.

### MEDIUM

6. **Myrtle's physical description confuses her with Catherine** [Profiles]
   - Problem: Profile states "Myrtle Wilson is described as having a 'solid, sticky bob of red hair' and a 'complexion powdered milky white,' but these details refer to Catherine, not Myrtle." The profiler correctly identified the confusion but then failed to provide Myrtle's ACTUAL description ("faintly stout, but she carried her surplus flesh sensuously").
   - Location: `src/analyzer.py` profiler prompt
   - Fix: LLM issue. The profiler recognized the wrong description but didn't find the right one.

7. **Ch3 summary duplicated name** [Summaries]
   - "The chapter opens with Nick Carraway, Nick, receiving" — name appears in both canonical and alias form
   - LLM output quirk. Minor.

8. **Owl Eyes fragmentation** [Completeness]
   - "Owl Eyes" (1 mention), "Man with owl-eyed glasses" (1 mention), "Drunken library guest" (1 mention) — potentially the same character, fragmented across F6 entries
   - Very low priority given 1-mention counts.

9. **F6 role-based entries** [Completeness]
   - "Butler" (20 mentions), "Chauffeur" (10 mentions), "Gardener" (5 mentions) — roles, not named characters
   - Acceptable for narrator prep (narrator needs to voice these roles) but cluttery

### LOW

10. **Dan Cody→James Gatz "employer" references alias, not canonical** [Profiles]
    - Dan Cody's relationship lists "James Gatz" (an alias) instead of "Gatsby" (canonical name)
    - Minor inconsistency.

## Fix Guidance for Attempt 14

**Focus ONLY on getting Character Profiles from 7/10 to 8/10.** All other categories pass.

The most impactful fixes:

1. **Gender inference for Myrtle and Catherine** — If the profiler or post-corrections can infer gender from titles (Mrs.), pronouns (she/her), or sibling labels, "brother"→"sister" fix triggers automatically. This is the highest-impact single fix.

2. **Fabricated relationship pruning** — Daisy→Dan Cody "friend" is invented. A simple post-correction rule: if character A and character B never co-appear in the same chapter's `active_characters` list, remove any profiler-generated relationship between them (except for characters connected by family/reputation like Henry C. Gatz→Gatsby).

3. **Tom's "old sport" verbal tic** — Post-processing: if a verbal tic string (e.g., "old sport") appears more frequently in another character's quotes, remove it from the current character's tics.

Fixing issues 1-2 would likely push Profiles to 8/10. Issue 3 is a nice-to-have.

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

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 2 | False narrator (Eckleburg) | `src/agents/characters.py` (STEP 4.26 threshold) | No change — wrong layer |
| 2 | Gatsby wrong cast tier | `src/agents/characters.py` (STEP 5.11 new) | No change — code not firing |
| 2 | Relationship labels all "husband" | `src/pipeline/character_profiling/post_corrections.py` | Partial fix — main cast improved |
| 3 | False narrator | `src/pipeline/character_extraction_v2/narrator.py`, `src/agents/characters.py` | **FIXED** ✓ |
| 3 | "colleague" spam | `src/analyzer.py` (profiler prompt) | No change — LLM ignores forbidden list |
| 3 | Gatsby promotion diagnostic | `src/agents/characters.py` (STEP 5.11 logging) | No change — promotion still doesn't fire |
| 4 | Gatsby promotion safety net | `src/analyzer.py` (before Step 4.6) | **Partially effective** — Gatsby promoted but narrator regressed |
| 4 | "colleague" post-processing filter | `src/analyzer.py` (two locations) | **FAILED** — 198 "colleague" entries remain |
| 5 | Narrator mention guard | `src/pipeline/character_extraction_v2/narrator.py` | **FIXED** ✓ |
| 5 | Narrator fallback minimum | `src/agents/characters.py` (STEP 6.6) | **FIXED** ✓ |
| 5 | Colleague substring filter | `src/analyzer.py` (two locations) | **FAILED** — 192 "colleague" remain |
| 6 | Disable cooccurrence colleague injection | `src/pipeline/character_profiling/post_corrections.py` | **FIXED** ✓ (192→30) |
| 6 | Block " and " pair-reference aliases | `src/pipeline/character_extraction_v2/main_cast.py` | **FIXED** ✓ |
| 7 | NameError `_VAGUE_REL_LABELS` | `src/analyzer.py` | **FIXED** ✓ |
| 7 | Spouse evidence window | `src/pipeline/character_profiling/post_corrections.py` | Partial (47→23 spouse errors) |
| 7 | Speech patterns prompt | `src/analyzer.py` | **FAILED** — evaluator error (voice_guidance was populated) |
| 7 | Wolfsheim alias absorption | `src/agents/characters.py` (STEP 5.6.9) | **FAILED** — still duplicated |
| 8 | Gatsby canonical rename | `src/analyzer.py` | **FIXED** ✓ |
| 8 | One-spouse invariant | `src/pipeline/character_profiling/post_corrections.py` | Partial (23→10, but 6 still wrong) |
| 8 | Colleague → associated | `src/pipeline/character_profiling/post_corrections.py` | **FIXED** ✓ |
| 8 | Second-pass alias absorption | `src/agents/characters.py` (STEP 5.9.9) | Partial (main entry fixed, 2 extras remain) |
| 9 | Green light / Owl Eyes split | `src/pipeline/character_extraction_v2/main_cast.py` | **FIXED** ✓ |
| 9 | Reciprocal spouse validation | `src/pipeline/character_profiling/post_corrections.py` | Partial (10→6 labels; 4 removed) |
| 9 | Fuzzy Wolfsheim dedup | `src/agents/characters.py` (STEP 5.9.9) | **FIXED** ✓ but REGRESSED in attempt 10 |
| 9 | F6 proper-noun filter | `src/analyzer.py` | **FIXED** ✓ |
| 9 | Daisy Fay maiden-name match | `src/analyzer.py` | **FIXED** ✓ |
| 10 | Henry C. Gatz dedup | `src/agents/characters.py` | **FIXED** ✓ |
| 10 | Gatsby↔Jordan false spousal | `src/pipeline/character_profiling/post_corrections.py` | **FIXED** ✓ |
| 10 | Jordan duplicate alias | `src/agents/characters.py` | **FIXED** ✓ |
| 10 | Buchanans' house possessive alias | `src/pipeline/character_extraction_v2/main_cast.py` | **FIXED** ✓ |
| 11 | Narrator max-mention guard | `src/pipeline/character_extraction_v2/narrator.py` | **OVERSHOT** — blocked Gatsby, fallback picked Gatz |
| 11 | Fuzzy Wolfsheim dedup STEP 5.6.9 | `src/agents/characters.py` | **COMPLETELY INEFFECTIVE** — both entries remain |
| 12 | Narrator chapter-spread guard | `src/agents/characters.py` | **FIXED** ✓ |
| 12 | Heuristic narrator max-mention guard | `src/agents/characters.py` | **FIXED** ✓ |
| 12 | STEP 5.12 cross-cast alias dedup | `src/agents/characters.py` | **COMPLETELY INEFFECTIVE** — Wolfsheim still duplicated |
| 12 | Shared single-word alias dedup | `src/agents/characters.py` | **FIXED** ✓ |
| 13 | Tom F6 duplicate | `src/analyzer.py` | **FIXED** ✓ |
| 13 | Wolfsheim post-extraction dedup | `src/analyzer.py` | **FIXED** ✓ |

## Configuration Audit
- Model: `qwen3-next:80b-a3b-instruct-q8_0` for all agents (think_mode: false)
- Context length: 32768 — adequate for Gatsby's chapter sizes
- Temperature: 0.7 — reasonable
- Zero LLM retries — no prompt/schema failures
- Mr. McKee still LOW CONFIDENCE (0.30) — JSON parse failure during profiling

## Fix History (continued)

### Attempt 14 fixes
- **Fix MM: `" man "` word-boundary in MALE_INDICATORS** — `post_corrections.py:92`
  - Bug: `"man"` (no spaces) is a substring of `"woman"`, so any character described as "a woman who..." had `is_male=True` AND `is_female=True` simultaneously
  - Effect: Both Myrtle and Catherine showed `is_male=is_female=True`, so `enforce_gender_consistency` never fired to correct "brother"→"sister"
  - Fix: Changed `"man"` → `" man "` (with surrounding spaces) to enforce word boundaries
  - All 332 tests pass with no regressions
  - Smoke test: Myrtle is_male=False, is_female=True ✓; Catherine is_male=False, is_female=True ✓; Tom is_male=True, is_female=False ✓

## Next Action
Re-run analysis to verify Fix MM (Myrtle/Catherine "brother"→"sister" correction)
