# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 12
- **Phase:** awaiting_analysis
- **baseline_score:** 5.90

## Output Files
- HTML: ../output/gatsby/report.html
- JSON: ../output/gatsby/analysis.json

## Latest Scores
- Structure Detection: 10/10 ✓
- Character Extraction: 5.5/10 ✗
  - Completeness: 7/10
  - Identity Resolution: 4/10 ← Tom split + Wolfsheim dup
  - Alias Grouping: 7/10
- Character Profiles: 6/10 ✗
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 8.5/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 7.68/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold: Character Extraction 5.5/10, Character Profiles 6/10)

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

## What Changed in Attempt 12

### Fix GG (Chapter-spread narrator guard) — EFFECTIVE ✓
- Correctly blocked Henry C. Gatz as narrator (appears only in final chapters)
- Nick Carraway now correctly identified as narrator with `is_narrator: true`
- First stable narrator fix in 4 attempts

### Fix HH (Heuristic narrator max-mention guard) — EFFECTIVE ✓
- Correctly skipped Gatsby (265 mentions) and selected Nick (34 mentions, first_appearance_chapter=0)
- Works in tandem with Fix GG

### Fix II (STEP 5.12 cross-cast alias dedup for Wolfsheim) — COMPLETELY INEFFECTIVE
- supporting_1 "Wolfshiem" (32 mentions) STILL exists alongside main_cast_7 "Meyer Wolfsheim" (6 mentions)
- This is the 5th consecutive attempt to fix Wolfsheim dedup (attempts 7, 8, 9, 10, 11, 12)
- main_cast_7 has alias "Meyer Wolfshiem" — the supporting char's canonical should match via word-subset
- **The code is either not being reached or the match logic is failing silently**

### Fix JJ (Shared single-word alias dedup) — EFFECTIVE ✓
- "Buchanan" correctly removed from both Tom and Daisy

### NEW ISSUE: "Tom" F6 duplicate (d9ffaca46d59, 191 mentions)
- F6 reconciliation added "Tom" as a separate character from "Tom Buchanan" (main_cast_3, 196 mentions)
- This was likely present in previous attempts but not flagged by the evaluator
- The "Tom" entry has its own profile, relationships (some correct: Tom→Daisy "husband", some wrong: Wilson→Tom "romantic interest")
- Creates self-referencing relationships: Tom↔Tom Buchanan "associated"
- This single issue causes massive damage to both Character Extraction AND Character Profiles scores

## Current Issues (Priority Order)

### CRITICAL

1. **"Tom" F6 duplicate: 191 mentions, separate from Tom Buchanan (196 mentions)** [Identity Resolution, Profiles]
   - Problem: F6 reconciliation (hash ID d9ffaca46d59) added "Tom" as a new character. "Tom Buchanan" already exists as main_cast_3 with 196 mentions. "Tom" is simply how the narrator refers to Tom Buchanan informally.
   - Evidence: "Tom" has relationships to Gatsby (rival), Daisy (husband), Myrtle (romantic interest) — identical to Tom Buchanan's role. Tom→Tom Buchanan "associated" is self-referencing.
   - Impact: This single issue destroys Identity Resolution (two entries for same person with ~400 combined mentions) AND Profiles (relationships split across entries, self-referencing).
   - Location: `src/analyzer.py` F6 reconciliation at ~line 1197. F6 adds characters found in summaries' `active_characters` that don't match existing characters. "Tom" should match "Tom Buchanan" since "Tom" is a first-name component.
   - Fix: In F6 reconciliation, before adding a new character, check if the candidate name is a **first-name or last-name component** of any existing character's canonical_name or aliases. "Tom" is the first word of "Tom Buchanan" → skip adding it. This is a simple `any(candidate.lower() in existing_name.lower().split() for existing_name in all_known_names)` check.

2. **Wolfsheim STILL duplicated (6th consecutive attempt)** [Identity Resolution]
   - Problem: main_cast_7 "Meyer Wolfsheim" (6 mentions) AND supporting_1 "Wolfshiem" (32 mentions) both exist.
   - Evidence: main_cast_7 has alias "Meyer Wolfshiem" — the exact canonical of supporting_1 minus the first name.
   - This has been attempted in attempts 7, 8, 9 (worked then regressed), 10, 11, 12. STEP 5.6.9, 5.9.9, and 5.12 all failed.
   - Location: `src/agents/characters.py` — multiple dedup steps have been added but none work
   - Fix: **ESCALATION REQUIRED** — Instead of adding yet another dedup step in characters.py, fix this in `src/analyzer.py` POST-extraction. After `analyze_characters_v2()` returns, iterate all characters: for each pair where one name is a substring of the other's canonical or alias, merge the shorter-named entry into the longer. This bypasses whatever is broken in the V2 pipeline's internal dedup.
   - **MUST ADD DEBUG LOGGING** to verify whether STEP 5.12 code is actually reached. The pattern of 6 consecutive failures suggests the code path is never executed.

### HIGH

3. **Gatsby→Jordan Baker "husband" / Jordan→Gatsby "wife"** [Profiles]
   - Problem: Gatsby and Jordan are NOT married. This is a completely fabricated spousal relationship.
   - This was fixed in attempt 10 (Fix BB) but has REGRESSED.
   - Location: `src/pipeline/character_profiling/post_corrections.py` — the reciprocal spouse validation may have been overridden
   - Fix: The one-spouse invariant (Fix S) should catch this — Gatsby's spouse should be Daisy only. Verify Fix BB/S code is still intact and functional.

4. **Myrtle↔Catherine "brother" — wrong gender** [Profiles]
   - Problem: Catherine is Myrtle's SISTER, not brother. Both are female.
   - Location: `src/pipeline/character_profiling/post_corrections.py` — `enforce_gender_consistency` should fix "brother" → "sister" for two female characters
   - Fix: Verify that both Myrtle and Catherine have `gender: "female"` set, which would trigger the gender consistency fix. If Catherine's gender is unknown/male, that's the root cause.

5. **Fabricated relationships persist** [Profiles]
   - Daisy→Dan Cody "friend" — FABRICATED (they never interact in the text)
   - Daisy→Wolfshiem "friend" — FABRICATED
   - Wilson→Tom "romantic interest" — WRONG (business relationship)
   - Wolfshiem→Meyer Wolfsheim "friend" — self-referencing from Wolfsheim dup (fixes with issue #2)
   - Wolfshiem→Daisy/Jordan/Tom/Nick "friend" — all fabricated
   - Location: `src/analyzer.py` profile generation, `src/pipeline/character_profiling/post_corrections.py`
   - Fix: The Wolfshiem fabrications will be eliminated when Wolfsheim dedup is fixed (#2). For Daisy→Dan Cody and Wilson→Tom "romantic interest", these are LLM hallucinations in the profiler. A text-evidence requirement for non-obvious relationships could help.

6. **Tom Buchanan verbal tic "old sport" is WRONG** [Profiles]
   - Problem: "old sport" is Gatsby's iconic catchphrase, not Tom's. Tom explicitly says "Don't you call me 'old sport'!" — he's reacting to Gatsby using it.
   - Location: `src/analyzer.py` profile generation (voice_guidance extraction)
   - Fix: This is an LLM hallucination. Low priority — fixing the Tom duplicate (#1) may resolve it since the profiler would have better context.

### MEDIUM

7. **Missing physical descriptions for Nick and Gatsby** [Profiles]
   - Nick: As narrator, self-description is sparse — acceptable
   - Gatsby: "an elegant young rough-neck, a year or two over thirty" + "tanned skin and short hair" — text provides description but profiler missed it
   - Location: `src/analyzer.py` profiler prompt
   - Fix: LLM variance. May improve with Tom duplicate fix reducing noise.

8. **Gatsby missing "James Gatz" alias** [Alias Grouping]
   - Problem: Gatsby's aliases are only ["Jay Gatsby"]. His birth name "James Gatz" is narratively important (Ch6 reveals his real identity).
   - Location: V2 extraction or alias enrichment in characters.py
   - Fix: Low priority — narrator would understand from context. Henry C. Gatz has alias "Gatz" which partially covers this.

9. **Ch1 summary duplicated name** [Summaries]
   - "The chapter opens with Nick Carraway, Nick Carraway, reflecting" — name appears twice
   - LLM output quirk. Minor.

10. **F6 clutter: Servants (7 mentions), Man with owl-eyed glasses (1)** [Completeness]
    - "Servants" is a generic role, not a character. "Man with owl-eyed glasses" should ideally be "Owl Eyes".
    - Low priority.

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

**STUCK PATTERN ALERT:** Wolfsheim dedup has been attempted in attempts 7, 8, 9, 10, 11, 12 — all targeting `src/agents/characters.py`. Fix X (attempt 9) worked once but regressed. All subsequent fixes completely ineffective. **ESCALATION MANDATORY**: Fix must move to `src/analyzer.py` post-extraction merge, bypassing V2 pipeline internals entirely. Must add debug logging first to understand why STEP 5.12 isn't working.

**STUCK PATTERN ALERT:** "Tom" F6 duplicate is a NEW critical issue. F6 reconciliation in `src/analyzer.py` does not check if candidate names are first/last name components of existing characters. This is a straightforward fix in analyzer.py.

## Configuration Audit
- Model: `qwen3-next:80b-a3b-instruct-q8_0` for all agents (think_mode: false)
- Context length: 32768 — adequate for Gatsby's chapter sizes
- Temperature: 0.7 — reasonable
- Zero LLM retries — no prompt/schema failures
- Tom profile: LOW CONFIDENCE (0.30) — JSON parse failure during profiling — but Tom Buchanan profile exists

### Attempt 13 fixes
- **Fix KK: F6 single-word name component check** — Added to `_is_likely_alias_of_existing()` in analyzer.py. Single-word candidates (e.g., "Tom") that match a word in an existing multi-word character's canonical name (e.g., "Tom Buchanan") are now correctly identified as existing characters and NOT added as duplicates.
- **Fix LL: Step 4.5.9 post-extraction word-subset dedup** — Added to analyzer.py between Step 4.5.5 and Step 4.6. After all alias enrichment is complete, merges any character whose canonical words are a strict subset of another character's canonical or alias words. "Wolfshiem" canonical {"wolfshiem"} ⊆ alias "Meyer Wolfshiem" {"meyer","wolfshiem"} → merged. Safety net for any remaining V2 pipeline dedup failures.

## Next Action
Re-run analysis to verify fixes.
