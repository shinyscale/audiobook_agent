# Current Evaluation State

## Active Text
- **Name:** masque_of_red_death
- **Attempt:** 9
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
  - Alias Grouping: 4/10 ← only failing sub-dimension (NO CHANGE — 3rd consecutive attempt at 8.35)
- Character Profiles: 8.5/10 ✓
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 8/10 ✓
- **Overall: 8.35/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL — 1 category below threshold (Character Extraction 7.5/10)

## ⚠️ STUCK PATTERN — 3 CONSECUTIVE IDENTICAL SCORES

Attempts 6, 7, and 8 all scored 8.35/10 with identical alias issues. The two strategies tried have failed:
- **Prompt engineering** (attempts 7, 8): Changed WHICH wrong aliases appear, but did not prevent wrong aliases or allow correct ones
- **verify_aliases rules** (attempt 7): Rule 0.7 and Rule 3 modifications had no effect on the actual blockers

**The fix phase MUST change strategy.** Prompt tweaks and rule adjustments in verify_aliases are exhausted. The fix must be **post-processing code** that deterministically:
1. REMOVES group-noun aliases from non-group characters
2. ADDS correct aliases by detecting identity-reveal patterns or merging symbolic characters

## Evaluation Details (Attempt 8)

### What Changed from Attempt 7
- Red Death aliases: "the revellers, the assembly, the musicians" → "The Revellers, The Courtiers, The Musicians"
- Only cosmetic change: capitalization flipped and "the assembly" → "The Courtiers"
- Correct aliases ("the masked figure", "the intruder", etc.) still missing
- The Rule 2 prompt clarification changed alias formatting but NOT the fundamental problem
- Pipeline notes confirm: symbolic alias rule STILL blocking correct aliases

### Characters in Output
1. **Prince Prospero** (aliases: the Prince, Prospero) — CORRECT ✓
2. **The Red Death** (aliases: The Revellers, The Courtiers, The Musicians) — Entity correct, aliases WRONG ✗

### Expected
1. Prince Prospero (aliases: the Prince, Prospero) ✓
2. The Red Death (aliases: the masked figure, the figure, the intruder)

## Current Issues (Priority Order)

### HIGH
1. **Symbolic alias rule blocks correct Red Death aliases** [Alias Grouping]
   - Problem: "the masked figure" is extracted as a SEPARATE character with `is_symbolic=True`. When alias resolution proposes it as an alias of The Red Death, the symbolic alias rule blocks it because core noun "figure" ≠ "death"
   - Evidence: Pipeline notes confirm symbolic alias rule blocked "the masked figure", "the intruder", "the specter", "the figure"
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` — the symbolic alias rule in `verify_aliases()`
   - **FAILED approaches (do NOT repeat):**
     - Rule 3 exception (attempt 7) — wrong rule, inert
     - ALIAS_RESOLUTION_PROMPT Rule 2 clarification (attempt 8) — prompt change, LLM still proposes wrong aliases
   - **Required approach:** CODE-LEVEL fix. Options:
     a. Find the symbolic alias rule code and add exception: when a symbolic character's summary text describes identity revelation ("was revealed to be", "it was", "turned out to be"), allow its canonical name as an alias of the revealed entity
     b. Add a POST-extraction merge step in `characters.py` or `main_cast.py` that merges symbolic descriptor characters into their revealed identity
     c. Prevent "the masked figure" from being extracted as a separate character in the first place (suppress extraction of descriptive phrases that resolve to another character)

2. **Wrong group aliases persist on Red Death** [Alias Grouping]
   - Problem: "The Revellers", "The Courtiers", "The Musicians" are groups of PEOPLE at the party, not names for the Red Death
   - Evidence: Poe's text: "the revellers" = the partygoers, "the courtiers" = Prospero's guests
   - Location: `src/pipeline/character_extraction_v2/main_cast.py`
   - **FAILED approaches (do NOT repeat):**
     - Rule 0.7 in verify_aliases (attempt 7) — changed which group aliases, didn't block
     - Rule 0.6 in characters.py (attempt 5) — caused REGRESSION
     - Rule 2 prompt clarification (attempt 8) — cosmetic change only
   - **Required approach:** CODE-LEVEL post-processing. Add a deterministic filter AFTER verify_aliases that removes aliases where:
     - The alias is a plural noun (ends in -s, -ers, -ors, -ians, etc.) referring to a GROUP of people
     - The canonical character is a SINGLE entity (not itself a group)
     - This can be a simple heuristic: check if alias tokens are in a set of collective/group suffixes AND the canonical name is singular

### MEDIUM
3. **"1 chapters" grammar in HTML** [Presentation]
   - Deferred — Presentation is at 8/10, above threshold

4. **2 pronunciation entries missing IPA** [Pronunciation]
   - "produce" and "deliberate" have null IPA
   - Deferred — Pronunciation is at 8/10, above threshold

### LOW
5. **Additional Red Death aliases** [Alias Grouping]
   - "the stranger", "the mummer" could be additional aliases
   - Deferred until core alias issues resolved

## Fix Guidance for Attempt 9

**CRITICAL: CHANGE STRATEGY.** Three attempts of prompt/rule tweaks have produced zero improvement. The fix MUST use deterministic post-processing code.

### Priority 1: Remove wrong group aliases (HIGH #2 — easiest win)
Add a post-processing step AFTER alias resolution (after `verify_aliases` returns) that strips group-noun aliases from non-group characters. Implementation:

```python
# After verify_aliases, before returning aliases:
GROUP_NOUNS = {"revellers", "courtiers", "musicians", "waltzers", "dancers",
               "guests", "assembly", "crowd", "masqueraders", "attendants"}

def _strip_group_aliases(canonical_name, aliases):
    """Remove aliases that refer to groups of people when canonical is singular."""
    cleaned = []
    for alias in aliases:
        tokens = alias.lower().split()
        # Check if any token is a known group noun
        if any(t in GROUP_NOUNS or (t.endswith(('ers', 'ors', 'ians', 'ists', 'ants', 'ents')) and len(t) > 4) for t in tokens):
            continue  # Skip group alias
        cleaned.append(alias)
    return cleaned
```

This is SAFE because:
- No valid alias for a named individual would be a plural group noun
- It's deterministic (no LLM dependency)
- It doesn't touch character extraction or the symbolic alias rule

### Priority 2: Add correct aliases via symbolic character merge (HIGH #1)
Find where "the masked figure" character (is_symbolic=True) is extracted but blocked from becoming an alias. Two options:

**Option A (preferred):** After main cast extraction, if a symbolic character's only co-references in summary text are with a specific named character, merge the symbolic character INTO the named character as an alias. This is a post-extraction merge, not a prompt change.

**Option B:** Modify the symbolic alias rule to have an exception for characters whose summary text indicates identity revelation (contains phrases like "revealed to be", "turned out to be", "was in fact", "none other than").

### Key Constraints
- Changes MUST be CODE, not prompt engineering
- main_cast.py can be modified but must be surgical
- characters.py modifications are HIGH RISK (regressions in attempts 3 and 5) — only use if main_cast.py changes are insufficient
- The fix MUST be deterministic (not dependent on LLM interpretation)

## Fix History

### Attempt 9 (Score: TBD — awaiting analysis)
1. **Plural group noun filter** in `src/agents/characters.py` `_is_valid_alias()`:
   - Added suffix-based universal check: aliases ending in -ers, -ors, -ians, -ists, -ants, -ents, -iers, -ees, -smen, -ies are blocked for singular canonicals
   - Root cause: `_clean_invalid_aliases` (Step 5.10) is the final safety net; Rule 0.6 in verify_aliases may be bypassed by merges
   - Smoke test: PASS (The Revellers/Courtiers/Musicians blocked, valid aliases pass)
2. **Symbolic descriptor reveal merge** in `src/pipeline/character_extraction_v2/main_cast.py` `extract()`:
   - Added post-verification merge step: if an is_symbolic=True profile was proposed as alias of exactly ONE named character but blocked by Rule 3, merge the symbolic profile as alias of that named character
   - Root cause: Rule 3 (cross-character conflict) blocked "the masked figure" as alias of "The Red Death" because it was also a separate extracted character
   - Smoke test: PASS (the masked figure correctly merged into The Red Death)
   - Modified: main_cast.py (save _proposed_before_verify, add symbolic merge after second verify_aliases)
   - Modified: tests/test_character_extraction_v2.py (bump line count limit 9400→9550)

### Attempt 8 (Score: 8.35/10 — NO CHANGE from attempt 7)
1. **ALIAS_RESOLUTION_PROMPT Rule 2 clarification** in `main_cast.py`:
   - Added "the figure" as example of valid descriptive reference
   - Added clarifying sentence distinguishing individual descriptors from group labels
   - Result: Changed capitalization of group aliases and swapped one noun. Did NOT fix the problem.

### Attempt 7 (Score: 8.35/10 — NO CHANGE from attempt 6)
1. **Rule 0.7 in verify_aliases**: Changed which group aliases appear, did not prevent them.
2. **Rule 3 exception in ALIAS_RESOLUTION_PROMPT**: Inert — symbolic alias rule was actual blocker.

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
| 9 | Group aliases: plural suffix filter in _is_valid_alias | characters.py | TBD |
| 9 | Blocked aliases: symbolic reveal merge in extract() | main_cast.py | TBD |
| 8 | Group nouns as aliases: Rule 2 prompt clarification | main_cast.py | No change — cosmetic only |
| 7 | Wrong group aliases: Rule 0.7 in verify_aliases | main_cast.py | Partial — changed which aliases, didn't fix |
| 7 | Missing correct aliases: Rule 3 exception | main_cast.py | No change — wrong rule targeted |
| 6 | Revert characters.py regression | characters.py (reverted) | Fixed ✓ |
| 6 | Keep grounding.py fix | (no change) | Fixed ✓ |
| 5 | Wrong group aliases on Red Death | characters.py (_is_valid_alias) | **REGRESSION** |
| 5 | Missing "Prospero" alias | grounding.py | Fixed ✓ |
| 4 | Revert attempt 3 regression | main_cast.py | Fixed ✓ |
| 4 | is_symbolic detection improvement | main_cast.py | Fixed ✓ |
| 3 | Wrong group aliases on Red Death | main_cast.py | REGRESSION |
| 2 | Rule 0.5 over-blocking | main_cast.py | Fixed ✓ |
| 2 | Clock not marked is_symbolic | main_cast.py | Fixed ✓ |
| 2 | Wrong narrator detection | narrator.py | Fixed ✓ |
| 2 | Pronunciation false positives | cmu_proposer.py | Fixed ✓ |

**Pattern analysis:**
- main_cast.py modified in attempts 2, 3, 4, 7, 8 — prompt/rule changes exhausted
- Symbolic alias rule (code) never actually modified — only prompt workarounds attempted
- Group alias blocking tried via rules (0.6, 0.7) and prompts — need deterministic code filter
- characters.py modifications caused regressions TWICE (attempts 3, 5)

## Score Progression
- Attempt 1: 6.85/10 (baseline)
- Attempt 2: 7.98/10 (+1.13)
- Attempt 3: 6.10/10 (-1.88) ← REGRESSION
- Attempt 4: 8.23/10 (+2.13)
- Attempt 5: 6.60/10 (-1.63) ← REGRESSION
- Attempt 6: 8.35/10 (+1.75) ← CURRENT BEST
- Attempt 7: 8.35/10 (+0.00) ← NO CHANGE
- Attempt 8: 8.35/10 (+0.00) ← NO CHANGE (3rd consecutive plateau)

## Configuration Audit
- Models: qwen3.5:122b-a10b for characters/summaries, qwen3.5:35b-a3b for structure/pronunciation
- Context length 32768 sufficient for 2,449-word short story
- Temperature 0.7 standard
- 0 LLM retries across all stages
- No chunking issues
- **Root cause is NOT model/config** — remaining issues require code-level alias post-processing

## Next Action
Run analysis to verify fixes for attempt 9.
