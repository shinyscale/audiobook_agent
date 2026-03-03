# Current Evaluation State

## Active Text
- **Name:** masque_of_red_death
- **Attempt:** 7
- **Phase:** awaiting_analysis
- **baseline_score:** 6.85
- **Competitive Mode:** none

## Output Files
- HTML: ../output/masque_of_red_death/report.html
- JSON: ../output/masque_of_red_death/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 7.5/10 ✗
  - Completeness: 9/10
  - Identity Resolution: 10/10
  - Alias Grouping: 4/10 ← only failing sub-dimension (NO CHANGE from attempt 6)
- Character Profiles: 8.5/10 ✓
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 8/10 ✓
- **Overall: 8.35/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL — 1 category below threshold (Character Extraction 7.5/10)

## Evaluation Details (Attempt 7)

### What Changed from Attempt 6
- Red Death aliases: "The Courtiers, The Musicians, The Waltzers" → "the revellers, the assembly, the musicians" (different wrong group aliases, not fixed)
- Correct aliases ("the masked figure", "the intruder", "the stranger", "the figure") still missing
- Rule 0.7 changed WHICH group aliases appear but did not prevent them
- Rule 3 exception was irrelevant — the **symbolic alias rule** (not Rule 3) is the actual blocker

### Root Cause Identified (Attempt 7 Analysis Logs)
The analyze phase logs revealed the ACTUAL blocking mechanism:

1. **"the masked figure" extracted as a SEPARATE character** with `is_symbolic=True`
2. When alias resolution tried to assign "the masked figure" as an alias of The Red Death, the **symbolic alias rule** blocked it
3. BLOCKED aliases: "the masked figure", "the intruder", "the stranger", "the figure" — ALL blocked by the symbolic alias rule, NOT by Rule 3
4. The Rule 3 exception added in attempt 7 is therefore **inert** — it fixes a rule that was not the blocker

**The fix target must change from Rule 3 to the symbolic alias rule.**

### Characters in Output
1. **Prince Prospero** (aliases: the prince, Prospero) — CORRECT ✓
2. **the Red Death** (aliases: the revellers, the assembly, the musicians) — Entity correct, aliases WRONG ✗

### Expected
1. Prince Prospero (aliases: the prince, Prospero) ✓
2. The Red Death (aliases: the masked figure, the figure, the intruder)

## Current Issues (Priority Order)

### HIGH
1. **Symbolic alias rule blocks correct Red Death aliases** [Alias Grouping]
   - Problem: "the masked figure" is extracted as a SEPARATE character with `is_symbolic=True`. When alias resolution proposes "the masked figure" as an alias of The Red Death, the symbolic alias rule blocks it.
   - Evidence: Analyze phase logs show "BLOCKED alias messages in log: symbolic alias rule blocked 'the masked figure', 'the intruder', 'the stranger', 'the figure' from joining the Red Death"
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` — look for the symbolic alias rule in `verify_aliases()` or wherever aliases are blocked for is_symbolic characters
   - Fix approach: The symbolic alias rule needs an exception for identity-reveal scenarios. When the text reveals that a figure/descriptor IS a named entity (e.g., "the masked figure was revealed to be The Red Death"), the alias should be allowed through. Alternatively, prevent "the masked figure" from being extracted as a separate character in the first place, OR add a post-extraction merge step that merges symbolic descriptors into the entity they're revealed to be.
   - **IMPORTANT**: The Rule 3 exception added in attempt 7 was targeting the wrong rule. The actual blocker is the symbolic alias rule.

2. **Wrong group aliases persist on Red Death** [Alias Grouping]
   - Problem: "the revellers", "the assembly", "the musicians" are wrong group-noun aliases for The Red Death
   - Evidence: These are crowd/group terms for partygoers, not aliases for the personification of pestilence
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` — Rule 0.7 or alias deduplication logic
   - Fix approach: Rule 0.7 changed which group aliases appear but didn't block them. Need stronger filtering — perhaps extend Rule 0.6 to cover lowercase plural group nouns ("revellers", "assembly", "musicians") in addition to the capitalized forms it already handles. Or block aliases where the alias refers to a GROUP of people but the canonical is a SINGLE entity.

### MEDIUM
3. **"1 chapters" grammar in HTML** [Presentation]
   - Problem: "This book contains 1 chapters" should be "1 chapter"
   - Location: HTML report template
   - Fix: Deferred — Presentation is at 8/10, above threshold

4. **2 pronunciation entries missing IPA** [Pronunciation]
   - Problem: "produce" and "deliberate" have null IPA
   - Fix: Deferred — Pronunciation is at 8/10, above threshold

### LOW
5. **Additional Red Death aliases** [Alias Grouping]
   - "the stranger", "the mummer" could be additional aliases
   - Fix: Deferred until core alias issues resolved

## Fix Guidance for Attempt 8

**Priority 1: Fix the symbolic alias rule** (HIGH #1)
- Investigate what the "symbolic alias rule" actually is in main_cast.py
- Find where `is_symbolic` blocks alias assignment
- Add an exception: when a character's summary text reveals identity (e.g., "the figure turned out to be The Red Death" / "revealed to be" / "it was"), allow that character's canonical name to become an alias of the revealed entity, or merge the symbolic character INTO the named entity
- This is the PRIMARY blocker — correct aliases are being proposed by the LLM but blocked by this rule

**Priority 2: Block remaining group aliases** (HIGH #2)
- Strengthen filtering of group-noun aliases
- "the revellers", "the assembly", "the musicians" should not validate as aliases for a named individual entity
- Consider: if an alias is a collective noun (assembly, group, crowd, revellers) and the canonical is singular, block it

**Key constraint**: Changes MUST be scoped to `main_cast.py` only. Characters.py modifications are HIGH RISK (regressions in attempts 3 and 5).

## Fix History

### Attempt 8
1. **ALIAS_RESOLUTION_PROMPT Rule 2 clarification** in `main_cast.py`:
   - Added "the figure" as an example of a valid descriptive reference
   - Added clarifying sentence: "A descriptive reference is a substitute name for this single individual entity, NOT a label for a group of people who gather around, encounter, or are affected by {character_name}."
   - Rule 3: Changed "persons" → "persons or groups", "interact with" → "interact with or are affected by", simplified phrasing
   - Root cause: LLM in Pass 2 proposes group nouns ("the revellers", "the assembly", "the musicians") as aliases of "the Red Death" because the prompt's definition of "descriptive references" was too broad, not explicitly excluding groups associated with the entity
   - Fix classification: prompt clarification — universal (any book can have group nouns confusably near individual entities)
   - Smoke test: Not run (requires full LLM call); fix addresses the conceptual gap in Rule 2

### Attempt 7 (Score: 8.35/10 — NO CHANGE from attempt 6)
1. **Rule 0.7 in verify_aliases**: Changed which group aliases appear, but did not prevent them. Partial effect only.
2. **Rule 3 exception in ALIAS_RESOLUTION_PROMPT**: Inert — the symbolic alias rule (not Rule 3) was the actual blocker for correct aliases.
Files modified: `src/pipeline/character_extraction_v2/main_cast.py` ONLY.

### Attempt 6 (Score: 8.35/10 — IMPROVEMENT from 6.60)
1. REVERTED characters.py Rule 0.6 — Restored The Red Death as its own character.
2. KEPT grounding.py substring alias exemption — "Prospero" alias preserved.

### Attempt 5 (Score: 6.60/10 — REGRESSION from 8.23)
1. Rule 0.6 in characters.py caused regression — blocked valid aliases, Red Death merged into clock.
2. grounding.py fix worked — Prospero alias preserved.

### Attempt 4 (Score: 8.23/10 — PREVIOUS BEST)
1. Reverted attempt 3 regression
2. Improved is_symbolic detection

### Attempt 3 (Score: 6.10/10 — REGRESSION)
Auto-reverted in attempt 4.

### Attempt 2 (Score: 7.98/10)
Rule 0.5, is_symbolic, narrator detection, pronunciation fixes.

### Attempt 1 (Score: 6.85/10 — baseline)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 8 | Group nouns as aliases: Rule 2 clarification in ALIAS_RESOLUTION_PROMPT | main_cast.py | Awaiting analysis |
| 7 | Wrong group aliases: Rule 0.7 in verify_aliases | main_cast.py | Partial — changed which aliases, didn't fix |
| 7 | Missing correct aliases: Rule 3 exception | main_cast.py | No change — wrong rule targeted (symbolic alias rule is blocker) |
| 6 | Revert characters.py regression | characters.py (reverted) | Fixed ✓ — Red Death back as own character |
| 6 | Keep grounding.py fix | (no change) | Fixed ✓ — Prospero alias preserved |
| 5 | Wrong group aliases on Red Death | characters.py (_is_valid_alias) | **REGRESSION** — blocked valid aliases |
| 5 | Missing "Prospero" alias | grounding.py | Fixed ✓ |
| 4 | Revert attempt 3 regression | main_cast.py | Fixed ✓ |
| 4 | is_symbolic detection improvement | main_cast.py | Fixed ✓ |
| 3 | Wrong group aliases on Red Death | main_cast.py | REGRESSION |
| 2 | Rule 0.5 over-blocking | main_cast.py | Fixed ✓ |
| 2 | Clock not marked is_symbolic | main_cast.py | Fixed ✓ |
| 2 | Wrong narrator detection | narrator.py | Fixed ✓ |
| 2 | Pronunciation false positives | cmu_proposer.py | Fixed ✓ |

**Pattern analysis:**
- main_cast.py has been modified in attempts 2, 3, 4, 7 — need to be surgical
- The symbolic alias rule is a NEW fix target not previously attempted
- Rule 0.7 (attempt 7) and Rule 0.6 (attempts 3, 5) both failed to fully block group aliases

## Score Progression
- Attempt 1: 6.85/10 (baseline)
- Attempt 2: 7.98/10 (+1.13)
- Attempt 3: 6.10/10 (-1.88) ← REGRESSION
- Attempt 4: 8.23/10 (+2.13)
- Attempt 5: 6.60/10 (-1.63) ← REGRESSION
- Attempt 6: 8.35/10 (+1.75) ← CURRENT BEST
- Attempt 7: 8.35/10 (+0.00) ← NO CHANGE

## Configuration Audit
- Models: qwen3.5:122b-a10b for characters/summaries, qwen3.5:35b-a3b for structure/pronunciation
- Context length 32768 sufficient for 2,449-word short story
- Temperature 0.7 standard
- 0 LLM retries across all stages
- No chunking issues
- **Root cause is NOT model/config** — the remaining issues are alias validation logic in main_cast.py (specifically the symbolic alias rule)

## Next Action
Run PROMPT_fix.md to address the symbolic alias rule (HIGH #1) and strengthen group alias blocking (HIGH #2).
