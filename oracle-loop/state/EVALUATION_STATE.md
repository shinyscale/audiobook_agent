# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 10
- **Phase:** awaiting_evaluation
- **baseline_score:** 5.90

## Output Files
- HTML: ../output/gatsby/report.html
- JSON: ../output/gatsby/analysis.json

## Latest Scores
- Structure Detection: 10/10 ✓
- Character Extraction: 7.5/10 ✗
  - Completeness: 8.5/10
  - Identity Resolution: 7/10
  - Alias Grouping: 7/10
- Character Profiles: 7/10 ✗
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 8.5/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 8.30/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold: Character Extraction 7.5/10, Character Profiles 7/10)

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

## What Changed in Attempt 9

### Fix V (Rule 0.5b person/non-person mismatch) — EFFECTIVE ✓
- Green light and Owl Eyes are now SEPARATE entries. main_cast_13 "The green light" has only alias "the light" (correct). F6 "Owl Eyes" (1 mention) exists independently.

### Fix W (Reciprocal spouse validation) — PARTIALLY EFFECTIVE
- Removed 4 non-reciprocated wrong spousal labels: Nick→Tom ✓, green light→Tom ✓, McKee→Wilson ✓, Sloane→Tom ✓
- But Gatsby↔Jordan ("husband"/"wife") survived because BOTH are wrong AND reciprocal — the check preserves mutual pairs
- Myrtle→Wilson "husband" also survived (wrong gender label — should be "wife") because Wilson→Myrtle "husband" reciprocates

### Fix X (Fuzzy Wolfsheim dedup) — EFFECTIVE ✓
- Triplication → single entry: supporting_10 "Wolfshiem" (32 mentions, alias: "Meyer Wolfshiem")
- NOTE: Merged character ended up in supporting_cast instead of main_cast (ID: supporting_10). With 32 mentions this should be main_cast, but it's a minor classification issue.

### Fix Y (F6 proper-noun filter) — EFFECTIVE ✓
- "gardener", "butler", "chauffeur", "New York reporter", "Lutheran minister", "the war veteran" — all eliminated

### Fix Z (Daisy Fay maiden-name matching) — EFFECTIVE ✓
- "Daisy Fay" is now an alias of Daisy (main_cast_2), not a separate F6 entry

### Tom "old sport" verbal tic — FIXED (possibly by LLM variance)
- Tom's verbal_tics are now: "old man", "I've got my man working on it now", "You think I'm pretty dumb, don't you?" — all correct for Tom

## Current Issues (Priority Order)

### CRITICAL

1. **Gatsby↔Jordan false spousal relationship (reciprocal but wrong)** [Profiles]
   - Problem: Gatsby→Jordan "husband" and Jordan→Gatsby "wife". They are NOT married. Jordan is Nick's romantic interest, not Gatsby's.
   - Why Fix W didn't catch it: Both characters list the other as spouse, so the reciprocal check preserves them.
   - Location: `src/pipeline/character_profiling/post_corrections.py`
   - Fix: Add a **mention-based plausibility check**: before accepting a reciprocal spousal pair, verify that both characters appear together in at least N chapters or have "married"/"wife"/"husband" keywords in their shared summary context. Alternatively: post-process to check that spousal pairs are NOT also in each other's "romantic interest" set — a "romantic interest" label from the LLM contradicts "married" (you wouldn't call your spouse a "romantic interest" in a novel context; that label implies pursuit, not marriage).

2. **Henry C. Gatz duplicated** [Identity Resolution]
   - Problem: main_cast_8 "Henry C. Gatz" (11 mentions) AND main_cast_8_parent "Henry C. Gatz (the father)" (2 mentions). These are the same person — Gatsby's father who arrives for the funeral.
   - The "parent" suffix on the ID suggests a semantic split went wrong.
   - Location: `src/agents/characters.py` — likely the semantic split logic created this
   - Fix: The split logic should not split a character whose only distinguishing feature is a parenthetical clarifier "(the father)". If the canonical names differ only by a parenthetical, they should remain merged.

### HIGH

3. **Invalid alias "the Buchanans' house" on Tom Buchanan** [Alias Grouping]
   - Problem: main_cast_3 Tom Buchanan has alias "the Buchanans' house" — a location, not a person reference
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` verify_aliases
   - Fix: Block aliases containing location/building words ("house", "mansion", "home", "estate", "property", "place") when the canonical name is a person. A person alias should reference the person, not their property.

4. **"Buchanan" shared alias on both Tom and Daisy** [Alias Grouping]
   - Problem: Both main_cast_2 (Daisy) and main_cast_3 (Tom) have "Buchanan" as alias. This creates ambiguity.
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` or `src/agents/characters.py`
   - Fix: If a surname-only alias appears on 2+ characters, remove it from all of them (or keep only on the character most commonly referred to by surname alone — in Gatsby, "Buchanan" standalone usually means the family generally, not one person specifically).

5. **Myrtle→Wilson labeled "husband" (wrong gender)** [Profiles]
   - Problem: Myrtle lists Wilson as "husband" but she IS the wife. Should be Myrtle→Wilson "wife".
   - This is a gender consistency issue — `enforce_gender_consistency` should catch this but may not if it only looks at the label holder's gender, not the relationship direction.
   - Location: `src/pipeline/character_profiling/post_corrections.py`
   - Fix: In `enforce_gender_consistency`, when A→B is "husband" and A is female, flip to "wife". The "husband" label on Myrtle means "B is my husband" — but the data structure stores it as "A's relationship TO B" where the value is A's ROLE, not B's role. Need to clarify which convention is in use and ensure consistency.

6. **Jordan Baker has duplicate "Jordan" alias** [Alias Grouping]
   - Problem: Alias list is `["Jordan", "Jordan", "Baker"]` — "Jordan" appears twice
   - Location: Post-processing dedup in `src/agents/characters.py`
   - Fix: Simple `list(set(...))` dedup on aliases before final output.

### MEDIUM

7. **Fabricated relationships on Daisy** [Profiles]
   - Daisy→Dan Cody "friend" — Daisy and Dan Cody never meet (Cody dies before Gatsby meets Daisy)
   - Daisy→Myrtle "romantic interest" — incorrect (they barely interact; Tom's affair with Myrtle is the connection)
   - Tom→Wilson "romantic interest" — incorrect (Tom's affair is with Myrtle, not George Wilson)
   - These are LLM fabrications from co-occurrence proximity.
   - Location: `src/analyzer.py` profiler or `src/pipeline/character_profiling/post_corrections.py`

8. **Missing physical descriptions for Gatsby and Myrtle** [Profiles]
   - Gatsby: "an elegant young roughneck, a year or two over thirty" + tan, short hair
   - Myrtle: "middle thirties, faintly stout, carried her surplus flesh sensuously"
   - These descriptions exist in the text but weren't captured.
   - Location: `src/analyzer.py` profiler context window or prompting

9. **Doctor Eckleburg and Green Light both labeled "protagonist"** [Character Extraction]
   - These are symbolic entities, not protagonists. Should be labeled "symbolic" or "minor".
   - Minor impact — doesn't affect narrator preparation significantly.

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
- **Fix X: Fuzzy Wolfsheim dedup** — **EFFECTIVE ✓** (3 entries → 1)
- **Fix Y: F6 proper-noun filter** — **EFFECTIVE ✓** (6 clutter entries removed)
- **Fix Z: Daisy Fay maiden-name match** — **EFFECTIVE ✓** (Daisy Fay → alias of Daisy)

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
| 9 | Fuzzy Wolfsheim dedup | `src/agents/characters.py` (STEP 5.9.9) | **FIXED** ✓ |
| 9 | F6 proper-noun filter | `src/analyzer.py` | **FIXED** ✓ |
| 9 | Daisy Fay maiden-name match | `src/analyzer.py` | **FIXED** ✓ |

## Configuration Audit
- Model: `qwen3-next:80b-a3b-instruct-q8_0` for all agents (think_mode: false)
- Context length: 32768 — adequate for Gatsby's chapter sizes
- Temperature: 0.7 — reasonable
- Zero LLM retries — no prompt/schema failures

## Priority Fix Order for Attempt 10

**The two blocking categories are Character Extraction (7.5/10) and Profiles (7/10).**

### Character Extraction (7.5 → 8+)

1. **Fix Henry C. Gatz duplication** — The `main_cast_8_parent` split needs to be prevented or merged. This is ~0.5 points to Identity Resolution.
2. **Block "the Buchanans' house" alias** — Location-word filter in alias validation. ~0.25 points.
3. **Remove shared "Buchanan" alias** — Dedup shared surname aliases. ~0.25 points.
4. **Dedup "Jordan" duplicate alias** — Trivial `set()` dedup. ~0.1 points.

### Profiles (7 → 8+)

5. **Fix Gatsby↔Jordan false spousal** — Add a cross-validation: if A→B is "romantic interest" AND A→B is "spouse" (or vice versa), the spousal label contradicts the romantic interest. Downgrade spouse to romantic interest. Alternatively: for reciprocal spouse pairs, verify "married"/"wedding"/"wife"/"husband" appears in shared chapter summaries.
6. **Fix Myrtle→Wilson gender label** — Myrtle (female) lists Wilson as "husband" in the "A's role relative to B" sense, but if the convention is "B's role to A", then it's correct. Clarify and fix.
7. **Remove fabricated Daisy relationships** — Daisy→Dan Cody, Daisy→Myrtle "romantic interest", Tom→Wilson "romantic interest" are all wrong. These may require tighter evidence requirements in the profiler.

## Attempt 10 fixes

### Fix AA: STEP 3.95b Pattern C/D guard (Henry C. Gatz duplication)
- **Root cause:** STEP 3.95b Pattern C fires on "Henry C. Gatz's son" (normal parent reference), wrongly splitting Henry C. Gatz into "Henry C. Gatz" + "Henry C. Gatz (the father)"
- **Fix:** Separated strong (A/B/E) from weak (C/D) patterns. If only weak patterns match AND the character has no child-tier aliases, skip the split.
- **Files:** `src/agents/characters.py` (lines ~607-700)
- **Smoke test:** All 332 tests pass

### Fix BB: Spousal text-evidence check (Gatsby↔Jordan false spousal)
- **Root cause:** Gatsby↔Jordan are both labeled "husband"/"wife" reciprocally, so reciprocal check preserves them. No marriage evidence exists in text.
- **Fix:** After reciprocal check, for surviving reciprocal spousal pairs verify marriage-keyword evidence ("married", "wife", "husband", "wedding", etc.) in source text near both names. No evidence → downgrade both to "associated".
- **Files:** `src/pipeline/character_profiling/post_corrections.py` (after line 982)
- **Smoke test:** All 332 tests pass

### Fix CC: Alias dedup (Jordan duplicate "Jordan" alias)
- **Root cause:** No deduplication of alias lists before output
- **Fix:** `aliases=list(dict.fromkeys(char.aliases or []))` in `_convert_to_pipeline_characters`
- **Files:** `src/agents/characters.py` (line ~5624, 5669)

### Fix DD: Possessive-reference blocker (Buchanans' house alias)
- **Root cause:** "the Buchanans' house" passed verify_aliases because no rule checks possessive-reference structure
- **Fix:** Rule 0.5c — if alias contains possessive form of any word from canonical name AND the last word is not part of canonical name, block (universal linguistic invariant)
- **Files:** `src/pipeline/character_extraction_v2/main_cast.py` (before Rule 1)

## Pipeline Notes (Attempt 10)
- Analysis completed in 91m 28s
- **WARNING: Narrator detected as "Jay Gatsby" (should be Nick Carraway)** — possible regression
- Wilson profile failed JSON parse (low confidence 0.30)
- James Gatz alias still blocked (never co-occurs with Jay Gatsby in same chapter per Rule 2a)
- 24 characters found (23 + 4 from F6 reconciliation)
- Output: `../output/gatsby/analysis.json`, `../output/gatsby/report.html`

## Next Action
Evaluate attempt 10 output.
