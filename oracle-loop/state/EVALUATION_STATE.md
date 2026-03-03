# Current Evaluation State

## Active Text
- **Name:** masque_of_red_death
- **Attempt:** 4
- **Phase:** awaiting_fix
- **baseline_score:** 6.85
- **Competitive Mode:** none

## Output Files
- HTML: ../output/masque_of_red_death/report.html
- JSON: ../output/masque_of_red_death/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 7/10 ✗
  - Completeness: 9/10
  - Identity Resolution: 10/10
  - Alias Grouping: 5/10
- Character Profiles: 8.5/10 ✓
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 8/10 ✓
- **Overall: 8.23/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (1 category below threshold — Character Extraction at 7/10)

**IMPROVEMENT from attempt 3:** Score recovered from 6.10 → 8.23 (+2.13). The regression recovery succeeded: The Red Death is now its own character, clock removed via is_symbolic, narrator detection correct. Only remaining blocker is alias quality.

## Evaluation Details

### Structure Detection: 9/10 ✓
"The Masque of the Red Death" is a continuous short story with no chapter divisions. The pipeline correctly identifies it as a single section with no false splits. Minor: "1 chapters" grammar in HTML.

### Character Extraction: 7/10 ✗

**Major improvement from attempt 3 (2/10 → 7/10).** Key wins:
- The Red Death exists as its own character entry with its own profile
- The clock correctly removed via is_symbolic detection
- No false merges between distinct entities
- Both significant characters present with accurate descriptions

**Completeness: 9/10** — Both significant characters present: Prince Prospero and The Red Death. No hallucinated characters. No missing named characters (the story has only two).

**Identity Resolution: 10/10** — Perfect. Prince Prospero and The Red Death correctly separated. The ebony clock correctly removed as symbolic object. No false merges, no false splits.

**Alias Grouping: 5/10** — Three wrong aliases and one missing alias:
- WRONG: "The Courtiers" is an alias of The Red Death — these are Prospero's party guests, a distinct group
- WRONG: "The Musicians" is an alias of The Red Death — these are musicians playing at the masquerade
- WRONG: "The Waltzers" is an alias of The Red Death — these are dancing guests
- CORRECT: "The Masked Figure" and "the figure" are valid aliases for The Red Death
- CORRECT: "the Prince" is a valid alias for Prince Prospero
- MISSING: "Prospero" (without "Prince") should be an alias — Poe uses both forms interchangeably

### Character Profiles: 8.5/10 ✓
- **Prince Prospero:** Accurate physical description ("bold and robust"), personality traits well-captured (happy/dauntless/sagacious → enraged), voice guidance with actual quotes ("Who dares?"), correct relationship to The Red Death. NOT marked as narrator (fixed from attempt 3).
- **The Red Death:** Excellent physical description drawn from the text (tall, gaunt, grave habiliments, stiffened corpse mask, vesture dabbled in blood). Personality appropriate (solemn, stealthy, domineering). Voice guidance correctly shows "unknown" since The Red Death doesn't speak.
- No invented information. Profiles are genuinely useful for narrator preparation.

### Chapter Summaries: 9/10 ✓
Comprehensive single summary capturing all key events: Prospero's retreat, castellated abbey, color-coded rooms, ebony clock's effect on guests, midnight appearance of masked figure, Prospero's confrontation and death, empty costume reveal, "Darkness, Decay, and the Red Death" holding dominion. Accurate. No hallucinations. Appropriate length.

### Pronunciation Guide: 8/10 ✓
17 entries, 15 with IPA. Good coverage: Prospero, sagacious, castellated, improvisatori, casements, masqueraders, piquancy, Hernani, out-Heroded, habiliments, impetuosity, cerements, blood-bedewed. Homographs flagged: live, close. 2 homographs (produce, deliberate) have null IPA — minor. No false positives.

### HTML Presentation: 8/10 ✓
- Navigation functional, tabs work, character profiles well-formatted with evidence citations
- Pronunciation guide well-organized
- "1 chapters" grammar error (minor)
- Alias display for The Red Death is misleading ("Also known as: The Masked Figure, the figure, The Courtiers, The Musicians, The Waltzers") — but this is a data quality issue scored under Character Extraction, not an HTML template problem

## Current Issues (Priority Order)

### CRITICAL
1. **Wrong aliases on The Red Death: "The Courtiers", "The Musicians", "The Waltzers"** [Alias Grouping]
   - Problem: Three plural group nouns naming GROUPS OF PARTY GUESTS are listed as aliases of The Red Death. These are entirely distinct entities — the courtiers are Prospero's friends, the musicians play music, the waltzers are dancing guests. None of these are alternate names for The Red Death.
   - Evidence: JSON shows `main_cast_2: "The Red Death"` with aliases `["The Masked Figure", "the figure", "The Courtiers", "The Musicians", "The Waltzers"]`
   - **Diagnostic — smoke test vs reality mismatch:** Attempt 4 added Rule 0.6 to block plural group noun aliases. The smoke test passed (7/7 cases). BUT these aliases still appeared in the final output. This means one of:
     (a) Rule 0.6 is in `verify_aliases()` but these aliases are being added by a DIFFERENT code path that doesn't go through verify_aliases (e.g., Pass 2 `_process_consolidated_pass2`, F6 reconciliation, or summary-based active_characters matching)
     (b) Rule 0.6 fires but its condition doesn't match the capitalized forms ("The Courtiers" vs "the courtiers")
     (c) The aliases are added AFTER verify_aliases runs
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` — investigate which code path adds these aliases. Check whether `_process_consolidated_pass2()` bypasses `verify_aliases()`. Check whether active_characters from summaries get matched as aliases.
   - Fix: Find the actual code path that adds these aliases and apply Rule 0.6 blocking there. If they come from Pass 2, add the check to `_process_consolidated_pass2()`. If from summary reconciliation, add to that stage.

### HIGH
2. **Missing alias: "Prospero" for Prince Prospero** [Alias Grouping]
   - Problem: "Prospero" (without the title "Prince") is not listed as an alias. Poe uses "Prospero" alone frequently (e.g., "But the Prince Prospero was happy" vs later references to just "Prospero").
   - Evidence: Only alias is "the Prince". The pronunciation guide even has "Prospero" as a standalone entry, confirming the name appears without "Prince" in the text.
   - **Diagnostic — same smoke test vs reality pattern:** Attempt 4 re-added `_add_title_stripped_aliases()` which should produce "Prospero" from "Prince Prospero". Smoke test passed (5/5 cases). But the alias doesn't appear in output. Same root cause as issue #1 — the title-stripped alias is either:
     (a) Being overwritten by a later stage that sets the final alias list
     (b) Not being called in the actual pipeline execution path
     (c) Being filtered out by a rule (though Rule 3 has a substring exemption)
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` — `_add_title_stripped_aliases()` and the pipeline execution flow
   - Fix: Trace the actual execution path. Add logging or debug output to confirm `_add_title_stripped_aliases()` runs and produces "Prospero". Then verify it survives through the rest of the pipeline.

### MEDIUM
3. **Two pronunciation entries missing IPA** [Pronunciation]
   - Problem: "produce" and "deliberate" have null IPA values
   - These are homographs correctly flagged but missing their IPA entries
   - Location: Pronunciation pipeline IPA generation
   - Fix: Ensure homograph entries always get IPA populated for both pronunciations

4. **"1 chapters" grammar error in HTML** [Presentation]
   - Problem: HTML says "This book contains 1 chapters" instead of "1 chapter" or "1 section"
   - Location: HTML report template
   - Fix: Add singular/plural handling for chapter count

### LOW
5. **Missing "the stranger" / "the mummer" as additional aliases for The Red Death** [Alias Grouping]
   - Problem: Poe also describes the masked figure as "the mummer" and refers to "the stranger" — these could be additional useful aliases
   - Fix: Deferred — fixing issues #1 and #2 alone should bring Alias Grouping to 8+

## What's Needed to Pass

Character Extraction is at 7/10 (only failing category). To reach 8/10:
- Fix issue #1 (remove 3 wrong aliases) → Alias Grouping jumps from 5 to ~8
- Fix issue #2 (add "Prospero" alias) → Alias Grouping reaches ~9
- With Alias Grouping at 8-9, Completeness at 9, and Identity Resolution at 10, overall Character Extraction reaches 9/10

**Key investigation for fix phase:** The critical diagnostic is that BOTH Rule 0.6 and title-stripping passed smoke tests but didn't work in the actual pipeline run. The fix phase MUST trace the actual execution path to find where aliases are being added/overwritten. Don't just add more unit tests — the unit tests already pass. The problem is integration-level.

## Fix History

### Attempt 4 (Score: 8.23/10 — UP from 6.10)
1. **Reverted attempt 3 main_cast.py** — restored to attempt 2 state
2. **Improved is_symbolic detection** — lowered threshold, added all_lowercase check → Clock correctly removed ✓
3. **Re-added Rule 0.6** — plural group noun blocking → Smoke tests pass but aliases still appear in output ✗
4. **Re-added _add_title_stripped_aliases()** → Smoke tests pass but "Prospero" not in output ✗
5. **Kept original ALIAS_RESOLUTION_PROMPT** — avoided the attempt 3 regression

### Attempt 3 (REGRESSION — 6.10/10)
1. Rule 0.6, title-stripping, and prompt changes caused regression
2. Auto-reverted in attempt 4

### Attempt 2 (Previous Best before attempt 4: 7.98/10)
1. Rule 0.5 scoped to is_symbolic=True only ✓
2. Programmatic is_symbolic for multi-word descriptors ✓
3. Narrator detection prompt → Third-person correctly identified ✓
4. Pronunciation whitelist → 4 common words removed ✓

### Attempt 1 (Baseline: 6.85/10)
- Character Extraction: 3/10
- Profiles: 5/10
- Pronunciation: 7.5/10

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 4 | Revert attempt 3 regression | main_cast.py | Fixed ✓ (clock removed, Red Death as own character) |
| 4 | is_symbolic detection improvement | main_cast.py | Fixed ✓ |
| 4 | Rule 0.6 re-added | main_cast.py | Smoke test pass, but aliases still in output ✗ |
| 4 | Title-stripping re-added | main_cast.py | Smoke test pass, but "Prospero" not in output ✗ |
| 3 | Wrong group aliases on Red Death | main_cast.py | REGRESSION |
| 3 | Missing "Prospero" alias | main_cast.py | Partial |
| 3 | Pass 2 prompt changes | main_cast.py | REGRESSION |
| 2 | Rule 0.5 over-blocking | main_cast.py | Fixed ✓ |
| 2 | Clock not marked is_symbolic | main_cast.py | Fixed ✓ |
| 2 | Wrong narrator detection | narrator.py | Fixed ✓ |
| 2 | Pronunciation false positives | cmu_proposer.py | Fixed ✓ |

**Pattern detected:** main_cast.py has been modified in all 4 attempts. Rule 0.6 and title-stripping both pass unit/smoke tests but fail integration. The fix phase must investigate the actual pipeline execution path, not just add more unit-level patches.

## Score Progression
- Attempt 1: 6.85/10 (baseline)
- Attempt 2: 7.98/10 (+1.13)
- Attempt 3: 6.10/10 (-1.88) ← REGRESSION, auto-reverted
- Attempt 4: 8.23/10 (+2.13 from attempt 3, +0.25 from attempt 2) ← NEW BEST

## Configuration Audit
- Models: qwen3.5:122b-a10b for characters/summaries, qwen3.5:35b-a3b for structure/pronunciation
- Context length 32768 sufficient for 2,449-word short story
- Temperature 0.7 standard
- 0 LLM retries across all stages
- No chunking issues
- **Root cause is NOT model/config** — the remaining issue is pure code-path: smoke-tested alias fixes don't apply to the actual pipeline execution path

## Next Action
Run PROMPT_fix.md to fix alias grouping issues. **Key directive for fix phase:** Don't just patch verify_aliases — TRACE the actual code path that produces the final alias list. The aliases "The Courtiers", "The Musicians", "The Waltzers" and the absence of "Prospero" indicate the final alias list is set by code AFTER verify_aliases runs. Find that code and fix it there.
