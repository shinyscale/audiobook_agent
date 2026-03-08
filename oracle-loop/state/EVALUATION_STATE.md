# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 11
- **Phase:** awaiting_fix
- **baseline_score:** 5.90

## Output Files
- HTML: ../output/gatsby/report.html
- JSON: ../output/gatsby/analysis.json

## Latest Scores
- Structure Detection: 10/10 ✓
- Character Extraction: 6.5/10 ✗
  - Completeness: 7/10
  - Identity Resolution: 6/10
  - Alias Grouping: 7/10
- Character Profiles: 6/10 ✗
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 8.5/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 7.93/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold: Character Extraction 6.5/10, Character Profiles 6/10)

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

## What Changed in Attempt 11

### Fix EE (Narrator programmatic guard) — PARTIALLY EFFECTIVE / OVERSHOT
- Correctly blocked Jay Gatsby as narrator (264 mentions, max-mention guard fired ✓)
- BUT fallback picked Henry C. Gatz (13 mentions, `is_narrator: true`) instead of Nick Carraway (34 mentions)
- Root cause: The guard clears the narrator but the downstream fallback logic doesn't correctly identify Nick. Nick has 34 mentions but the fallback may be picking the first character below the threshold, or Gatz is being selected by a different heuristic.
- Nick has `is_narrator: false` — the narrator detection completely misses the actual first-person narrator.

### Fix FF (Fuzzy Wolfsheim dedup STEP 5.6.9) — COMPLETELY INEFFECTIVE
- main_cast_7 "Meyer Wolfsheim" (6 mentions) AND supporting_2 "Wolfshiem" (32 mentions) BOTH still exist
- The fix was supposed to catch "Wolfshiem"/"Wolfsheim" via fuzzy match in STEP 5.6.9
- Possible causes: (a) the code path isn't reached, (b) names_similar threshold doesn't match, (c) the merge happens but creates a new entry instead of absorbing
- Meyer Wolfsheim even has alias "Meyer Wolfshiem" and "Wolfsheim" — yet the supporting entry still exists separately

### Fabricated relationships — PARTIALLY IMPROVED
- The 11 fabricated family labels from attempt 10 (Gatsby→Catherine "brother", etc.) are mostly gone
- But NEW fabrications appeared: Tom→Catherine "brother" (wrong), Wolfshiem→everyone "friend"
- The narrator fix partially worked (Gatsby no longer narrator) so the narrator bypass no longer shields fabricated rels
- But Henry C. Gatz as narrator may be shielding HIS fabricated rels instead

## Current Issues (Priority Order)

### CRITICAL

1. **Narrator STILL WRONG: Henry C. Gatz instead of Nick Carraway** [Profiles, Characters]
   - Problem: main_cast_8 "Henry C. Gatz" has `is_narrator: true`. Nick (main_cast_0) has `is_narrator: false`. Nick Carraway is the actual first-person narrator.
   - Fix EE correctly blocked Gatsby but the fallback selected Gatz instead of Nick.
   - This is the 4th narrator failure (attempts 4, 10, 11). The narrator pipeline needs a fundamentally different approach for Gatsby.
   - Nick has 34 mentions (low because he's narrating as "I"), Gatz has 13 mentions.
   - Location: `src/pipeline/character_extraction_v2/narrator.py` (fallback logic after guard clears wrong narrator), `src/agents/characters.py` (STEP 6.6 narrator assignment)
   - Fix: The max-mention guard in Fix EE clears the narrator but the fallback doesn't have enough signal to find Nick. The issue is that Nick's 34 mentions are mostly in third-person references BY other characters — but as narrator, most of his "presence" is as "I". Two approaches:
     (a) In `_parse_result`: after the max-mention guard fires and clears narrator, look for a character whose name appears in the first chapter's first few paragraphs AND has moderate mentions (15-50 range for a 9-chapter novel). Nick is introduced in Ch1's opening.
     (b) In STEP 6.6 fallback: when `narrator_character_id` is None and narrative is first-person, prefer characters who appear in chapter 1 AND whose mention count is moderate (not the highest, not the lowest). Nick at 34 fits; Gatz at 13 only appears in final chapters.
     (c) Chapter-spread heuristic: The true narrator should appear across ALL or nearly all chapters. Gatz only appears in Ch9. Nick appears in all 9 chapters.

2. **Wolfsheim STILL duplicated (4th consecutive failure)** [Identity Resolution]
   - Problem: main_cast_7 "Meyer Wolfsheim" (6 mentions) AND supporting_2 "Wolfshiem" (32 mentions). Same person.
   - Fix FF (STEP 5.6.9 fuzzy dedup) was COMPLETELY INEFFECTIVE. Fix X (attempt 9) also didn't persist.
   - Notably, main_cast_7 already has alias "Meyer Wolfshiem" — the exact canonical name of supporting_2 — yet the dedup doesn't catch it.
   - Location: `src/agents/characters.py` — the STEP 5.6.9 fuzzy match OR a simpler approach: exact alias-to-canonical match
   - Fix: **Simplest approach that MUST work**: Before STEP 5.8 promotion, iterate all supporting characters. For each supporting char, check if its canonical_name (lowercased) matches ANY alias (lowercased) of any main_cast character. If match found, absorb the supporting char's mention_count into the main_cast char and remove the supporting char. "Wolfshiem" matches main_cast_7's alias "Meyer Wolfshiem" (contains "Wolfshiem"). This is a straightforward substring/exact check, not fuzzy.
   - **IMPORTANT**: Verify Fix FF code is actually being reached by adding a debug log. The fix may have been applied to wrong step number or has an early-return bug.

### HIGH

3. **"James" ghost character (F6 hash d52e32f3a96a)** [Identity Resolution]
   - Problem: F6 reconciliation added "James" (6 mentions) as a separate character. This is likely "James Gatz" fragments.
   - James has relationships: Nick=friend, Gatsby=friend — clearly a fragment of James Gatz.
   - Location: `src/analyzer.py` (F6 reconciliation at ~line 1197)
   - Fix: F6 should check if a single-word name being added is a component of an existing character's alias. "James" appears in Gatsby's relationship as "James Gatz: previous identity". Either (a) F6 should check existing relationships for identity markers, or (b) "James" should match Henry C. Gatz's alias "Gatz" → not a match. Actually, "James" is a common first name — F6 should skip single common first names that don't have a surname, OR check if the name is a component of any existing character's known aliases.

4. **"Buchanan" shared alias on both Tom and Daisy** [Alias Grouping]
   - Problem: Both main_cast_2 (Daisy) and main_cast_3 (Tom Buchanan) have "Buchanan" as alias.
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` or `src/agents/characters.py`
   - Fix: Post-extraction dedup: if a surname-only alias appears on 2+ characters, remove it from all of them.

5. **Missing physical descriptions for Nick, Gatsby, Myrtle** [Profiles]
   - Nick: narrator, so self-description is rare — acceptable to be sparse
   - Gatsby: "an elegant young rough-neck, a year or two over thirty" + "tanned skin, short hair" — text provides description but not captured
   - Myrtle: "middle thirties, and faintly stout... carried her surplus flesh sensuously" — explicit text description not captured
   - Location: `src/analyzer.py` profiler prompt/context
   - Fix: May be an LLM variance issue. Could add a second-pass physical description extraction for main characters with empty descriptions.

6. **Fabricated relationships persist** [Profiles]
   - Tom→Catherine "brother" — WRONG (Catherine is Myrtle's sister)
   - Tom→Jordan Baker "romantic interest" — WRONG (no romantic interest)
   - Daisy→Dan Cody "friend" — FABRICATED (they never meet)
   - Wolfshiem (supporting_2) has "friend" relationships to Daisy, Tom, Jordan, Nick, Meyer Wolfsheim — all fabricated
   - Location: `src/pipeline/character_profiling/post_corrections.py`, `src/analyzer.py`
   - Fix: The Wolfshiem fabrications will be eliminated when Wolfsheim dedup is fixed (issue #2). For Tom→Catherine "brother" and Tom→Jordan "romantic interest", the text-evidence check should catch these but may not have sufficient signal. Consider: for "brother"/"sister" labels, require that the label word appears in the same sentence/paragraph as both characters.

### MEDIUM

7. **F6 clutter: Gardener, Chauffeur, Butler (20 mentions!), Ferdie, Vladmir Tostoff** [Completeness]
   - These are very minor characters/roles. "Butler" at 20 mentions seems inflated (likely generic "butler" references counted as character mentions).
   - Not blocking — a narrator might find these useful. But "Butler" and "Chauffeur" are roles, not characters.
   - Location: `src/analyzer.py` F6 reconciliation
   - Fix: LOW priority. Could filter generic role words ("butler", "chauffeur", "gardener") from F6 promotion.

8. **Wolfshiem duplicate creates nonsense relationships** [Profiles]
   - Meyer Wolfsheim→Wolfshiem "friend" and Wolfshiem→Meyer Wolfsheim "friend" — same person talking to themselves
   - This is a downstream effect of issue #2. Fixing the dedup eliminates these.

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

**STUCK PATTERN ALERT:** Wolfsheim dedup has been attempted in attempts 7, 8, 9, 10, 11 — all targeting `src/agents/characters.py`. Fix X (attempt 9) worked once but regressed. Fix FF (attempt 11) was completely ineffective. The fix phase MUST verify the code path is reached (add logging) and consider an alternative approach: exact alias-to-canonical matching instead of fuzzy matching.

**STUCK PATTERN ALERT:** Narrator detection has failed in attempts 1, 2, 4, 10, 11. Fixes have targeted `narrator.py` and `characters.py` STEP 6.6. The narrator pipeline needs a chapter-spread heuristic: the true first-person narrator appears in ALL chapters, not just the final one. Gatz only appears in Ch9; Nick appears in all 9.

## Configuration Audit
- Model: `qwen3-next:80b-a3b-instruct-q8_0` for all agents (think_mode: false)
- Context length: 32768 — adequate for Gatsby's chapter sizes
- Temperature: 0.7 — reasonable
- Zero LLM retries — no prompt/schema failures

## Next Action
Run PROMPT_fix.md to address:
1. **CRITICAL #1**: Narrator fix — add chapter-spread heuristic (narrator must appear in most chapters; Gatz only in Ch9 → disqualified)
2. **CRITICAL #2**: Wolfsheim dedup — use exact alias-to-canonical match (not fuzzy), verify code path reached with logging
3. **HIGH #3**: "James" ghost — F6 should skip single common first names or check against existing character aliases
4. **HIGH #4**: Shared "Buchanan" alias dedup
