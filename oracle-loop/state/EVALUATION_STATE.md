# Current Evaluation State

## Active Text
- **Name:** masque_of_red_death
- **Attempt:** 3
- **Phase:** awaiting_fix
- **baseline_score:** 6.85
- **Competitive Mode:** none

## Output Files
- HTML: ../output/masque_of_red_death/report.html
- JSON: ../output/masque_of_red_death/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 2/10 ✗ (CATASTROPHIC REGRESSION)
  - Completeness: 3/10
  - Identity Resolution: 1/10
  - Alias Grouping: 1/10
- Character Profiles: 4/10 ✗
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 6/10 ✗
- **Overall: 6.10/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold — REGRESSION from attempt 2's 7.98)

**⚠️ REGRESSION ALERT:** Score 6.10 < baseline 6.85 - 0.3 = 6.55. The attempt 3 fix made things WORSE. The fix phase should auto-revert the last commit before applying new fixes.

## Evaluation Details

### Structure Detection: 9/10 ✓
"The Masque of the Red Death" is a continuous short story with no chapter divisions. The pipeline correctly identifies it as a single section. No false splits. Null title is acceptable for a continuous text. Minor: "1 chapters" grammar in HTML.

### Character Extraction: 2/10 ✗ (CATASTROPHIC REGRESSION)

**This is dramatically worse than attempt 2 (6/10) and even attempt 1 (3/10).**

**Completeness: 3/10** — The story has exactly two named characters: Prince Prospero and The Red Death. Only Prince Prospero exists as a standalone character. The Red Death — the story's TITULAR ANTAGONIST — is not its own character. It has been absorbed as an alias of "the giant ebony clock", an inanimate object. The clock itself should have been marked `is_symbolic=True` and removed (this was working in attempt 2 but regressed).

**Identity Resolution: 1/10** — The Red Death (a personified plague/supernatural entity that kills everyone) is falsely merged with the ebony clock (a timepiece that chimes hourly). These are entirely different entities with different narrative roles. The clock marks time; the Red Death kills. This is the worst possible merge error.

**Alias Grouping: 1/10** — The clock's alias list is: "the clock", "the Red Death", "the courtiers", "the musicians", "the waltzers". Every single alias except "the clock" is WRONG:
- "the Red Death" is the titular antagonist, not the clock
- "the courtiers" are Prospero's party guests
- "the musicians" play music at the masquerade
- "the waltzers" are dancing guests
Additionally, "Prospero" (without "Prince") is missing as an alias for Prince Prospero despite the title-stripping fix being applied in attempt 3.

### Character Profiles: 4/10 ✗
- Prince Prospero: Profile content is accurate ("bold and robust", personality evolution, speech patterns). However, he is WRONGLY labeled as "First-Person Narrator" — the story is told in THIRD person by an unnamed omniscient narrator. This was fixed in attempt 2 (narrator.py) but has regressed.
- The Red Death: Has NO profile because it doesn't exist as a character. This is a catastrophic gap — the story's main antagonist has no entry.
- The clock: Has an accurate-but-useless profile describing it as an inanimate object. This entity shouldn't be in the character list at all.

### Chapter Summaries: 9/10 ✓
Excellent summary capturing all key events: Prospero's retreat, the castellated abbey, seven color-coded rooms, the masked figure's appearance, Prospero's confrontation and death, the empty costume reveal, and "Darkness, Decay, and the Red Death" holding dominion. Accurate and useful for narrator preparation.

### Pronunciation Guide: 8/10 ✓
Good coverage: Prospero, improvisatori, castellated, habiliments, cerements, out-Heroded, piquancy, Hernani, blood-bedewed. 15/17 entries have IPA. 2 homograph entries (produce, deliberate) still have null IPA — minor. No false positives.

### HTML Presentation: 6/10 ✗
- Navigation functional, tabs work, pronunciation guide well-formatted
- Character section is deeply misleading: "the giant ebony clock — Also known as: the clock, the Red Death, the courtiers, the musicians, the waltzers" is nonsensical for narrator preparation
- Wrong narrator badge: "📖 First-Person Narrator" on Prince Prospero in a third-person story
- "1 chapters" grammar error

## Current Issues (Priority Order)

### CRITICAL
1. **The Red Death absorbed as alias of clock — not its own character** [Identity Resolution, Completeness]
   - Problem: "the Red Death" appears as an alias of "the giant ebony clock" instead of being its own character entity. The titular antagonist of the story doesn't exist as a character.
   - Evidence: JSON shows `main_cast_5: "the giant ebony clock"` with aliases including "the Red Death". There is no separate Red Death character entry.
   - Root cause: The `is_symbolic` detection that worked in attempt 2 (marking the clock as symbolic and removing it) has REGRESSED. The clock has `is_symbolic: false`. Since the clock survived as a character, the LLM's Pass 2 merged The Red Death into it as an alias. This is likely because:
     (a) The attempt 3 code changes to `main_cast.py` may have inadvertently broken the is_symbolic detection logic, OR
     (b) The LLM produced a different extraction this run where the clock wasn't flagged as symbolic
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` — is_symbolic detection + Pass 1 extraction
   - Fix approach: **REVERT attempt 3 commit first** (score regressed below baseline - 0.3). Then investigate why is_symbolic broke. The is_symbolic detection must reliably mark "the giant ebony clock" as symbolic, which removes it from the character list, which prevents the Red Death from being merged into it.

2. **Wrong aliases on the clock: "the courtiers", "the musicians", "the waltzers"** [Alias Grouping]
   - Problem: Plural group nouns describing party guests are aliases of the clock. Rule 0.6 (added in attempt 3) was supposed to block these, but either the rule didn't fire because the canonical is "the giant ebony clock" (not a singular person), or the code changes didn't apply correctly.
   - Evidence: JSON shows these as aliases of main_cast_5
   - Root cause: Same regression as issue #1 — if the clock were properly removed, these aliases wouldn't exist
   - Fix: Resolves automatically if issue #1 is fixed (clock removed as symbolic entity)

3. **Narrator detection regressed — Prince Prospero marked as first-person narrator** [Profiles]
   - Problem: `is_narrator: True` for Prince Prospero. The story is told in THIRD person ("the 'Red Death' had long devastated the country", "But the Prince Prospero was happy and dauntless and sagacious"). Prospero is never the narrator.
   - Evidence: Attempt 2 fixed this ("Third-person narration correctly identified, narrator=None"). Now it's back.
   - Root cause: The narrator detection code was in `narrator.py` (attempt 2), but attempt 3 only changed `main_cast.py`. Possible LLM non-determinism — the narrator detection LLM may have produced a different answer this run. Or the narrator detection prompt/logic was affected by the main_cast.py changes.
   - Location: `src/pipeline/character_extraction_v2/narrator.py`
   - Fix: After reverting attempt 3, verify if the narrator detection still works. If not, investigate further.

### HIGH
4. **Missing alias: "Prospero" for Prince Prospero** [Alias Grouping]
   - Problem: "Prospero" (without the title "Prince") is not listed as an alias despite the title-stripping code added in attempt 3
   - Evidence: Only alias is "the Prince". Poe uses "Prospero" (without "Prince") throughout the text.
   - Root cause: The title-stripping code may have produced "the Prince" instead of "Prospero", or "Prospero" was produced but blocked by a rule
   - Fix: After revert, re-examine the title-stripping approach

5. **Missing "the masked figure" / "the stranger" as aliases for The Red Death** [Alias Grouping]
   - Problem: The Red Death's physical manifestation at the masquerade is described as "a masked figure" and "the stranger". These should be aliases.
   - Evidence: Poe reveals the masked figure IS the Red Death: "And now was acknowledged the presence of the Red Death."
   - Fix: Deferred until The Red Death exists as its own character (depends on fix #1)

### MEDIUM
6. **Two pronunciation entries missing IPA** [Pronunciation]
   - Problem: "produce" and "deliberate" have null IPA values
   - Location: Pronunciation pipeline IPA generation
   - Fix: Ensure homograph entries always get IPA populated

## Priority Fix Order
1. **REVERT** attempt 3 commit (regression auto-revert) — restores attempt 2 state
2. Re-apply ONLY the fixes that were working: Rule 0.6 (group noun blocking) and title-stripping
3. Investigate why is_symbolic detection is non-deterministic across runs
4. Address narrator detection stability
5. Address masked figure aliases (if time permits)

## Fix History
### Attempt 3 (REGRESSION — score dropped from 7.98 to 6.10)
1. **RULE 0.6: Block plural group noun aliases** — Added to verify_aliases() but the clock survived as a character (is_symbolic regression), so the group nouns ended up as clock aliases where Rule 0.6 may not have applied correctly
2. **Title-stripped aliases** — Added _add_title_stripped_aliases() but alias produced was "the Prince" not "Prospero"
3. **Pass 2 prompt changes** — May have contributed to LLM extracting differently

### Attempt 2 (Previous Best: 7.98/10)
1. **Rule 0.5 scoped to is_symbolic=True only** → Fixed: The Red Death no longer blocked by personified concept check
2. **Programmatic is_symbolic for multi-word descriptors** → Fixed: Clock correctly marked is_symbolic=True and removed
3. **Narrator detection prompt** → Fixed: Third-person narration correctly identified (narrator=None)
4. **Pronunciation whitelist** → Fixed: 4 common words no longer false positives

### Attempt 1 (Baseline: 6.85/10)
- Character Extraction: 3/10 (catastrophic — clock as character, Red Death missing aliases, wrong narrator)
- Profiles: 5/10
- Pronunciation: 7.5/10
- Overall: 6.85/10

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 3 | Wrong group aliases on Red Death | main_cast.py | REGRESSION — clock survived, aliases on clock instead |
| 3 | Missing "Prospero" alias for Prince Prospero | main_cast.py | Partial — got "the Prince" but not "Prospero" |
| 3 | Pass 2 prompt: improve alias proposals | main_cast.py | REGRESSION — may have caused LLM to produce worse extraction |
| 2 | Rule 0.5 over-blocking personified concepts | main_cast.py | Fixed ✓ |
| 2 | Clock not marked is_symbolic | main_cast.py | Fixed in attempt 2, REGRESSED in attempt 3 |
| 2 | Wrong narrator detection | narrator.py | Fixed in attempt 2, REGRESSED in attempt 3 |
| 2 | Pronunciation false positives | cmu_proposer.py | Fixed ✓ (stable) |

## Score Progression
- Attempt 1: 6.85/10 (baseline)
- Attempt 2: 7.98/10 (+1.13)
- Attempt 3: 6.10/10 (-1.88) ← REGRESSION, below baseline

## Configuration Audit
- Models: qwen3.5:122b-a10b for characters, qwen3.5:35b-a3b for structure/pronunciation
- Context length 32768 sufficient for 2,449-word short story
- Temperature 0.7 standard
- No chunking issues
- **Root cause is NOT model/config** — the is_symbolic detection logic regressed due to code changes in attempt 3

## Pipeline Notes (Attempt 3)
- Analysis completed successfully in 21m 54s (exit code 0)
- 2 characters found: "Prince Prospero" and "the giant ebony clock"
- WARNING: "the Red Death" appears as an alias for "the giant ebony clock" — Red Death not extracted as its own character
- WARNING: "the masked figure" alias proposals blocked by Rule 3 (claiming aliases already on the clock)
- Multiple BLOCKED alias messages from verify_aliases
- Models: structure=qwen3.5:35b-a3b, characters=qwen3.5:122b-a10b, summaries=qwen3.5:122b-a10b, pronunciation=qwen3.5:35b-a3b

## Next Action
Fix phase should:
1. Auto-revert attempt 3 commit (score 6.10 < baseline 6.85 - 0.3)
2. From the attempt 2 codebase, carefully re-apply fixes for the remaining issues (Rule 0.6, title-stripping) WITHOUT breaking is_symbolic detection
3. Investigate LLM non-determinism in is_symbolic and narrator detection — may need more robust heuristics
