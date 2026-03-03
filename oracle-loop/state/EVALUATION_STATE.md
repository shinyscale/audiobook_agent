# Current Evaluation State

## Active Text
- **Name:** masque_of_red_death
- **Attempt:** 13
- **Phase:** awaiting_fix
- **baseline_score:** 6.85
- **Competitive Mode:** none

## Output Files
- HTML: ../output/masque_of_red_death/report.html
- JSON: ../output/masque_of_red_death/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 6.5/10 ✗
  - Completeness: 7/10
  - Identity Resolution: 8/10
  - Alias Grouping: 5/10
- Character Profiles: 7/10 ✗
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 9/10 ✓
- **Overall: 7.98/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold: Characters 6.5, Profiles 7)

## Evaluation Details

### Structure Detection: 9/10 ✓
Continuous short story correctly identified as single section. No artificial splits.

### Character Extraction: 6.5/10 ✗

**Completeness (7/10):** Two of three expected entities present. Prince Prospero ✓, the Red Death ✓. The Ebony Clock is **MISSING** — it was present in attempt 12 (main_cast_3, 25 mentions) but has been filtered out. The Clock is a major symbolic presence that chimes each hour, stopping all revelry, and symbolizes the inevitability of death. Per rubric, significant symbolic objects ARE valid extractions.

**Identity Resolution (8/10):** Major improvement — the Red Death is now a STANDALONE character (main_cast_2), no longer falsely merged into the Ebony Clock. This was the CRITICAL issue in attempts 9-12 and the attempt 13 `is_symbolic` fix partially worked. No false merges or splits among present characters.

**Alias Grouping (5/10):** Two problems:
1. **Wrong alias "the crowd" on the Red Death** — "the crowd" refers to the courtiers/revelers at the masquerade ball, NOT the Red Death. This is a false alias.
2. **Missing valid aliases for the Red Death** — "the masked figure", "the intruder", "the mummer", "the stranger" are all textual references to the Red Death. These are blocked by core noun mismatch rules ("figure"/"intruder" ≠ "death"), a known issue from attempts 7-8.

### Character Profiles: 7/10 ✗
- Prospero: "bold and robust" — accurate but **incomplete**. Text also says "happy and dauntless and sagacious." Relationship "the Red Death: enemy" ✓
- The Red Death: Excellent physical description — "tall, gaunt, shrouded... habiliments of the grave... mask resembling stiffened corpse... scarlet horror... blood." Very accurate. ✓
- The Red Death has `is_symbolic: false` — should be True (personified plague/supernatural force)
- **Missing Ebony Clock profile entirely** — drops score since 1 of 3 significant entities has no profile
- Profile quality for existing characters is decent but Prospero is thin

### Chapter Summaries: 9/10 ✓
Excellent summary of the complete story: captures the plague, the retreat, the seven colored rooms, the masquerade, the masked figure's appearance, Prospero's confrontation and death, the discovery that the figure is empty, and the ending with "Darkness and Decay and the Red Death." Themes correctly identified. Good length.

### Pronunciation Guide: 8/10 ✓
17 entries, 15 with IPA. Good selections: Prospero, sagacious, castellated, improvisatori, Hernani, out-Heroded, habiliments, cerements, blood-bedewed, piquancy — all genuinely unusual. Homographs (live, close) correctly flagged. Two homographs (produce, deliberate) have null IPA — minor gap.

### HTML Presentation: 9/10 ✓
Well-organized with tabbed navigation, relationship cards, performance timing table, model information. Clean layout.

## Current Issues (Priority Order)

### CRITICAL
1. **Ebony Clock MISSING from output** [Completeness]
   - Problem: The Ebony Clock was extracted (4 characters found during extraction) but filtered out of final output. Only 2 of 4 characters survive. In attempt 12, the Clock was `main_cast_3` with 25 mentions.
   - Evidence: `jq '.characters | length'` → 2. Pipeline notes confirm "4 characters found during extraction; 2 in final output."
   - Root cause hypothesis: The attempt 13 fix marked the Clock as `is_symbolic=True` via artifact core noun detection. Then Rule 0.5 in `verify_aliases` blocked all its wrong aliases (Red Death, masked figure, etc.). Without those inflated aliases/mentions, the Clock may have fallen below a mention or grounding threshold and been filtered out. Alternatively, the Clock was merged INTO the Red Death in the within-main merge step.
   - Location: Investigate filtering/merge in `src/agents/characters.py` (post-extraction filtering) and `src/pipeline/character_extraction_v2/main_cast.py` (within-main merge). Check if a minimum mention threshold is removing it. Also check `src/pipeline/character_extraction_v2/grounding.py` for grounding-based filtering.
   - Fix approach: **Debug which step removes the Clock.** Add temporary logging to trace the 4→2 character reduction. The Clock has legitimate mentions ("the clock", "the ebony clock") and should survive filtering. If a mention threshold is the issue, ensure `is_symbolic` characters get their OWN mentions counted (not alias-inflated ones).
   - Impact: +1.5 on Characters (Completeness 7→9), +1 on Profiles (Clock profile would be generated)

### HIGH
2. **Wrong alias "the crowd" on the Red Death** [Alias Grouping]
   - Problem: "the crowd" refers to the courtiers at the masquerade, NOT the Red Death. This is a completely incorrect alias assignment.
   - Evidence: `jq '.characters[1].aliases'` → `["the crowd"]`
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` — LLM Pass 2 alias resolution or `_process_consolidated_pass2()`
   - Fix: The core noun of "the crowd" is "crowd" — this is semantically unrelated to "death". The existing core noun mismatch rules should catch this but apparently don't (perhaps "crowd" isn't checked, or the rule only applies to `is_symbolic` characters). Add "crowd" type nouns to the blocked patterns, or strengthen Rule 0.5 to catch collective nouns being assigned to individual/symbolic entities.
   - Impact: +1 on Alias Grouping

3. **Missing valid Red Death aliases** [Alias Grouping]
   - Problem: "the masked figure", "the intruder", "the stranger", "the mummer" are all textual references to the Red Death but are blocked by core noun mismatch ("figure"/"intruder" ≠ "death").
   - Evidence: Pipeline notes across attempts 7-13 show BLOCKED aliases for Red Death
   - Location: `verify_aliases()` in main_cast.py — core noun comparison logic
   - Fix: Known persistent issue. For `is_symbolic=True` characters, the core noun matching is too strict. These are narrative synonyms established by the text, not regular aliases. Consider: (a) relaxing core noun matching for symbolic characters when the LLM has high confidence, or (b) using co-reference resolution from summary text.
   - Impact: +1-2 on Alias Grouping. Can be deferred if fixing #1 and #2 brings Characters to 8.0.
   - Note: Attempted in attempts 7-8 without success. This is a hard problem.

### MEDIUM
4. **Prospero's physical description incomplete** [Profiles]
   - Problem: Only "bold and robust" — text also says "happy and dauntless and sagacious"
   - Location: Profile generation in analyzer.py
   - Impact: ~0.25 points. Will partially self-correct if character list is fixed (profile regeneration).

5. **Red Death not marked `is_symbolic`** [Completeness/Data Quality]
   - Problem: `is_symbolic: false` for a personified supernatural force
   - Evidence: `jq '.characters[1].is_symbolic'` → false
   - Location: `is_symbolic` detection in main_cast.py — "death" may not match artifact noun patterns
   - Impact: Minor for scoring but affects downstream alias logic. If `is_symbolic` were True, alias rules would apply differently.

6. **2 pronunciation entries missing IPA** [Pronunciation]
   - "produce" and "deliberate" (homographs) have null IPA
   - Impact: Minor. Pronunciation is at 8/10, above threshold.

## Progress Analysis (Attempt 13 vs 12)

| Metric | Attempt 12 | Attempt 13 | Change |
|--------|-----------|-----------|--------|
| Characters | 2 | 2 | Same count |
| Red Death standalone | No (merged into Clock) | Yes (standalone) | ✓ IMPROVED |
| Ebony Clock present | Yes (with wrong aliases) | No (missing) | ✗ REGRESSED |
| Wrong aliases on Clock | 4 wrong aliases | N/A (missing) | N/A |
| Red Death aliases | N/A (merged) | 1 wrong ("the crowd") | Mixed |

**Net assessment:** The `is_symbolic` artifact noun fix PARTIALLY worked — it correctly unmerged the Red Death from the Clock. But it had the side effect of making the Clock disappear entirely. The fix overcorrected: it blocked the Clock's inflated aliases but then something removed the Clock as a character.

## Fix History

### Attempt 13 (Score: 7.98/10 — improvement from 7.0)
1. **Artifact core noun `is_symbolic` detection** in main_cast.py:
   - Result: ✓ PARTIALLY WORKED — Red Death now standalone (unmerged from Clock)
   - Side effect: ✗ Ebony Clock now MISSING entirely — filtering removed it after alias cleanup
   - New issue: Red Death has wrong alias "the crowd"

### Attempt 12 (Score: 7.0/10 — marginal improvement from 6.95)
1. **REVERT min_grounding_mentions to 1** in characters.py: ✗ DID NOT FIX
2. **POV guard for narrator assignment** in narrator.py: ✓ WORKED

### Attempt 11 (Score: 6.95/10 — REGRESSION from 7.68)
1. F6 plural group noun filter in analyzer.py: ✓ WORKED
2. min_grounding_mentions = 2 in characters.py: ✗ OVER-FILTERED
3. Narrator min-mention guard in narrator.py: ✓ Works for 1-mention case
4. "stra" suffix in main_cast.py and characters.py: ✓ WORKED

### Attempt 10 (Score: 7.68/10)
1. REVERTED symbolic reveal merge: ✓ Red Death restored
2. KEPT plural suffix filter: ✓

### Attempt 9 (Score: 7.35/10 — REGRESSION)
1. Plural group noun filter: ✓ WORKED
2. Symbolic descriptor reveal merge: ✗ REGRESSION — REVERTED

### Attempt 8 (Score: 8.35/10 — BEST)
1. Rule 2 prompt clarification: No change

### Attempt 7 (Score: 8.35/10)
1. Rule 0.7 in verify_aliases: Partial
2. Rule 3 exception: No change

### Attempt 6 (Score: 8.35/10 — tied BEST)
1. REVERTED characters.py Rule 0.6: ✓
2. KEPT grounding.py fix: ✓

### Attempts 1-5: See previous evaluation state

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 13 | Artifact core noun `is_symbolic` detection | main_cast.py | ✓ Partially (Red Death unmerged) / ✗ Clock missing |
| 12 | Revert min_grounding_mentions from 2 to 1 | characters.py | ✗ DID NOT FIX |
| 12 | POV guard: narrator only for 1st-person/epistolary | narrator.py | ✓ WORKED |
| 11 | F6 plural group noun filter | analyzer.py | ✓ Worked |
| 11 | min_grounding_mentions = 2 | characters.py | ✗ OVER-FILTERED |
| 11 | Narrator min-mention guard | narrator.py | ✓ Works for 1-mention |
| 11 | "stra" suffix for collective nouns | main_cast.py, characters.py | ✓ Worked |
| 10 | Revert symbolic merge | main_cast.py | ✓ Red Death restored |
| 9 | Group aliases: plural suffix filter | characters.py | ✓ WORKED |
| 9 | Symbolic descriptor reveal merge | main_cast.py | ✗ REGRESSION — REVERTED |
| 8 | Rule 2 prompt clarification | main_cast.py | No change |
| 7 | Rule 0.7 in verify_aliases | main_cast.py | Partial |
| 7 | Rule 3 exception | main_cast.py | No change |
| 6 | Revert characters.py regression | characters.py | Fixed ✓ |
| 6 | Keep grounding.py fix | (no change) | Fixed ✓ |
| 5 | Wrong group aliases on Red Death | characters.py | REGRESSION |
| 5 | Missing "Prospero" alias | grounding.py | Fixed ✓ |
| 4 | Revert attempt 3 regression | main_cast.py | Fixed ✓ |
| 4 | is_symbolic detection improvement | main_cast.py | Fixed ✓ |
| 3 | Wrong group aliases on Red Death | main_cast.py | REGRESSION |
| 2 | Rule 0.5 over-blocking | main_cast.py | Fixed ✓ |
| 2 | Clock not marked is_symbolic | main_cast.py | Fixed ✓ |
| 2 | Wrong narrator detection | narrator.py | Fixed ✓ |
| 2 | Pronunciation false positives | cmu_proposer.py | Fixed ✓ |

**Pattern analysis:**
- main_cast.py has been modified 12+ times across attempts
- The `is_symbolic` fix in attempt 13 is the first time the Red Death has been successfully unmerged since attempt 8
- The Clock disappearing is a NEW problem — previous attempts always had the Clock present
- Fix phase should investigate the 4→2 character filtering, NOT re-modify alias resolution logic
- The "the crowd" false alias is likely from LLM Pass 2 and should be catchable with core noun rules

## Score Progression
- Attempt 1: 6.85/10 (baseline)
- Attempt 2: 7.98/10 (+1.13)
- Attempt 3: 6.10/10 (-1.88) ← REGRESSION
- Attempt 4: 8.23/10 (+2.13)
- Attempt 5: 6.60/10 (-1.63) ← REGRESSION
- Attempt 6: 8.35/10 (+1.75) ← BEST
- Attempt 7: 8.35/10 (+0.00)
- Attempt 8: 8.35/10 (+0.00)
- Attempt 9: 7.35/10 (-1.00) ← REGRESSION
- Attempt 10: 7.68/10 (+0.33)
- Attempt 11: 6.95/10 (-0.73) ← REGRESSION
- Attempt 12: 7.0/10 (+0.05)
- Attempt 13: 7.98/10 (+0.98) ← Red Death unmerged, but Clock missing

## Configuration Audit
- Models: qwen3.5:122b-a10b for characters/summaries, qwen3.5:35b-a3b for structure/pronunciation
- Context length 32768 sufficient for 2,449-word short story
- Temperature 0.7 standard
- 0 LLM retries across all stages
- No chunking issues
- **Root cause is NOT model/config** — the issues are in character filtering and alias resolution logic

## Next Action
Run PROMPT_fix.md to address:
1. **CRITICAL: Investigate why the Ebony Clock was filtered out** — debug the 4→2 character reduction path
2. **HIGH: Block "the crowd" as an alias for the Red Death** — core noun mismatch should catch this
