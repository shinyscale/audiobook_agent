# Current Evaluation State

## Active Text
- **Name:** masque_of_red_death
- **Attempt:** 11
- **Phase:** awaiting_fix
- **baseline_score:** 6.85
- **Competitive Mode:** none

## Output Files
- HTML: ../output/masque_of_red_death/report.html
- JSON: ../output/masque_of_red_death/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 4/10 ✗ (FAILING — REGRESSION from attempt 10's 6/10)
  - Completeness: 5/10
  - Identity Resolution: 2/10 ← catastrophic false merge is the primary blocker
  - Alias Grouping: 3/10
- Character Profiles: 5/10 ✗ (FAILING)
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 8/10 ✓
- **Overall: 6.95/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL — 2 categories below threshold (Character Extraction 4/10, Character Profiles 5/10)

## Comparison to Previous Attempts

| Attempt | Overall | Char Extract | Char Profiles | Key Diff |
|---------|---------|-------------|---------------|----------|
| 6-8 (best)| 8.35  | ~7.5        | ~8.5          | Had both Clock and Red Death as separate characters |
| 9       | 7.35    | 5           | 6             | Red Death MISSING (regression) |
| 10      | 7.68    | 6           | 6.5           | Red Death restored but Darkness hallucinated, group nouns |
| **11**  | **6.95**| **4**       | **5**         | **Red Death merged INTO Ebony Clock — CATASTROPHIC** |

## Root Cause Analysis (Attempt 11)

The four fixes from attempt 11 produced mixed results:

| Fix | Intended Effect | Actual Result |
|-----|----------------|---------------|
| F6 plural group noun filter | Block courtiers/musicians as F6 characters | ✓ WORKED — 0 F6 characters |
| min_grounding_mentions = 2 | Filter "Darkness" (1 mention) | ✓ Darkness filtered BUT ✗ **also filtered The Red Death** |
| Narrator min-mention guard | Prevent 1-mention characters from being narrator | ✓ Works but doesn't fix Prospero (12 mentions) being wrongly tagged |
| "stra" suffix for collective nouns | Block "the orchestra" as alias | ✓ No orchestra alias BUT ✗ LLM proposed "The Red Death" as Clock alias instead |

**The critical regression chain:**
1. The LLM extracted The Red Death as a main_cast character (confirmed: "BLOCKED aliases for Red Death" in pipeline notes means alias validation processed it)
2. `min_grounding_mentions=2` filtered The Red Death from the final character list (it may have had only 1-2 exact text mentions as "The Red Death" — the text uses many variant forms like "the pestilence", etc.)
3. During Pass 2 alias resolution, the LLM proposed "The Red Death" as an alias of "The Ebony Clock"
4. Since The Red Death was no longer a standalone character, Rule 0.5 (alias can't be another character's canonical) did NOT block it
5. The alias was accepted → **catastrophic false merge**: The Red Death (personified plague, title antagonist) merged into The Ebony Clock (a timepiece)

**Why this is worse than attempt 10:** In attempt 10 (min_grounding_mentions=1), The Red Death was its own character with 12 mentions. The "Darkness" issue (-1 point) was far less severe than losing The Red Death entirely (-3 points).

## Current Issues (Priority Order)

### CRITICAL
1. **The Red Death falsely merged into The Ebony Clock as alias** [Identity Resolution, Completeness]
   - Problem: "The Red Death" (personified plague, title antagonist) is listed as an ALIAS of "The Ebony Clock" (a timepiece). These are completely unrelated entities. The Red Death is a masked figure that kills everyone; the Ebony Clock is a clock that chimes hourly. This is the worst possible false merge.
   - Evidence: `jq '.characters[1].aliases'` → `["the clock", "The Red Death"]`. The Ebony Clock has mention_count: 24 (inflated by Red Death mentions counted through alias). Only 2 characters in the entire output.
   - Root cause: `min_grounding_mentions=2` (set in attempt 11 fix #2) filtered The Red Death as a standalone character. Without it as a separate character, Rule 0.5 couldn't block the alias proposal. The LLM then merged it into the Clock.
   - Location: `src/agents/characters.py` line 79 — `self.min_grounding_mentions` default changed from 1 to 2
   - Fix: **Revert `min_grounding_mentions` from 2 back to 1.** The grounding threshold was too aggressive for this text. The Red Death may appear by exact name only 1-2 times while being referenced via descriptors ("the masked figure", "the intruder") dozens of times. A blanket threshold of 2 is unsafe.
   - Impact: Restoring The Red Death as standalone character would improve Character Extraction from 4/10 to ~6-7/10 and Profiles from 5/10 to ~7/10.

2. **Safety net: Block alias proposals where alias has more text mentions than canonical** [Identity Resolution]
   - Problem: Even if fix #1 works, we need a safety check to prevent this class of false merge from ever happening again. "The Red Death" is mentioned more frequently than "The Ebony Clock" — a more-mentioned entity should NEVER be demoted to an alias of a less-mentioned one.
   - Evidence: Universal invariant — aliases are alternative (usually less common) ways to refer to a character. If entity A has more text mentions than entity B, A should not be an alias of B.
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` — `verify_aliases()` function
   - Fix: Add a new rule (e.g., Rule 0.8): Before accepting an alias, check if the proposed alias text appears MORE times in the source text than the canonical character's name. If so, BLOCK the alias. This requires passing text mention counts to verify_aliases.
   - Impact: Prevents this entire class of catastrophic merge. Future-proofs against similar LLM errors.

### HIGH
3. **Prince Prospero incorrectly marked as narrator** [Profiles, Presentation]
   - Problem: `is_narrator: true` for Prince Prospero. The story uses 3rd-person omniscient narration — "The 'Red Death' had long devastated the country." No character narrates.
   - Evidence: HTML shows "📖 First-Person Narrator" tag on Prospero. The story never uses first person.
   - Location: `src/pipeline/character_extraction_v2/narrator.py` — the narrator detection LLM wrongly identifies Prospero
   - Fix: The narrator guard from attempt 11 only checks mention count (≤1). For 3rd-person omniscient stories, the narrator detector should recognize the absence of first-person narration and set is_narrator=False for all characters. However, this is a lower-priority fix — it affects Profiles (-0.5) and Presentation (-0.25) but isn't the main blocker.
   - Impact: ~0.5 point improvement on Profiles.

4. **Missing valid Red Death aliases** [Alias Grouping]
   - Problem: Even when The Red Death is its own character (as in attempt 10), it has no valid aliases. "the masked figure", "the intruder", "the stranger", "the mummer" — all are blocked by core noun mismatch ("figure" ≠ "death").
   - Evidence: Pipeline notes: "BLOCKED aliases for Red Death: masked figure, stranger, intruder, figure (core noun mismatch still blocking)"
   - Location: `verify_aliases()` in main_cast.py — core noun comparison too strict for symbolic entities
   - Fix: For `is_symbolic=True` characters, relax core noun matching. Or add a rule that if the summary text explicitly identifies two names as the same entity ("a figure dressed as the Red Death"), allow the alias.
   - Impact: ~1 point improvement on Alias Grouping.
   - Note: This has been attempted in attempts 7-8 without success. May require a different approach.

### MEDIUM
5. **Duplicate alias "the Prince" in Prospero's alias list** [Alias Grouping]
   - Problem: `aliases: ["the Prince", "Prospero", "the Prince"]` — "the Prince" appears twice
   - Location: Deduplication in alias processing
   - Fix: Add dedup step before finalizing aliases
   - Deferred — minor impact (~0.25 points)

6. **Prospero's physical description is minimal** [Profiles]
   - Problem: "Described as a bold and robust man." — The text says more: "happy and dauntless and sagacious"
   - Location: Profile generation in analyzer.py
   - Deferred — will improve when character list is corrected

7. **2 pronunciation entries missing IPA** [Pronunciation]
   - "produce" and "deliberate" (homographs) have null IPA
   - Deferred — Pronunciation is at 8/10, above threshold

8. **"casements" IPA may be incorrect** [Pronunciation]
   - Listed as /ˈseɪmɛnts/ — should be /ˈkeɪsmənts/ (starts with /k/ not /s/)
   - Deferred — minor issue

## Fix Guidance for Attempt 12

### Priority 1: REVERT min_grounding_mentions to 1 (CRITICAL #1)
In `src/agents/characters.py`, change `self.min_grounding_mentions` default back from 2 to 1.

This is the single most impactful fix. The attempt 11 change to 2 was too aggressive — it correctly filtered "Darkness" (1 mention) but also filtered The Red Death, triggering the catastrophic false merge.

**Side effect:** "Darkness" may reappear as a 1-mention character. This is a minor issue (~-0.5 points) compared to losing The Red Death entirely (~-3 points).

### Priority 2: Add alias mention-count safety check (CRITICAL #2)
In `verify_aliases()` in `src/pipeline/character_extraction_v2/main_cast.py`, add a rule that blocks an alias proposal if the proposed alias text appears more frequently in the source text than the canonical character's name.

This prevents the class of error where a more-prominent entity gets demoted to an alias of a less-prominent one. It would have prevented "The Red Death" (many mentions) from being aliased to "The Ebony Clock" (fewer direct mentions).

**Implementation:** This requires access to text mention counts in verify_aliases. The function may need a new parameter for mention counts or access to the summary/source text to count occurrences.

### Priority 3: Skip if time permits — address narrator detection (HIGH #3)
For 3rd-person omniscient stories, no character should be marked as narrator. The narrator detector should check for first-person pronoun usage in the text and only assign narrator status when first-person narration is confirmed.

### Constraints
- Do NOT modify prompts in ways that are novel-specific
- Changes must be generic (work for any text)
- Keep changes minimal — Priority 1 is a one-line revert
- Test with `pytest --ignore=tests/test_semantic_conflicts.py --ignore=tests/test_pdf_ingestion.py --ignore=tests/test_refine.py`

## Fix History

### Attempt 11 (Score: 6.95/10 — REGRESSION from 7.68)
1. **F6 plural group noun filter** in `src/analyzer.py`: ✓ WORKED — no F6 group characters
2. **min_grounding_mentions = 2** in `src/agents/characters.py`: ✗ OVER-FILTERED — The Red Death removed, causing catastrophic merge into Clock
3. **Narrator min-mention guard** in `src/pipeline/character_extraction_v2/narrator.py`: ✓ Works for 1-mention case, but doesn't prevent wrong narrator for 12-mention Prospero
4. **"stra" suffix** in `main_cast.py` and `characters.py`: ✓ WORKED — "the orchestra" alias blocked

### Attempt 10 (Score: 7.68/10 — improvement from 7.35, but below best of 8.35)
1. **REVERTED symbolic reveal merge** in main_cast.py: ✓ Red Death restored
2. **KEPT plural suffix filter**: ✓ Still works
3. **New issues from LLM non-determinism**: Ebony Clock missing, "Darkness" hallucinated, "the orchestra" wrong alias

### Attempt 9 (Score: 7.35/10 — REGRESSION from 8.35)
1. Plural group noun filter in characters.py: ✓ WORKED — keep
2. Symbolic descriptor reveal merge in main_cast.py: ✗ REGRESSION — Red Death MISSING — REVERTED

### Attempt 8 (Score: 8.35/10 — NO CHANGE from attempt 7)
1. ALIAS_RESOLUTION_PROMPT Rule 2 clarification: No change — cosmetic only

### Attempt 7 (Score: 8.35/10 — NO CHANGE from attempt 6)
1. Rule 0.7 in verify_aliases: Partial — changed which aliases, didn't fix
2. Rule 3 exception in ALIAS_RESOLUTION_PROMPT: No change — wrong rule targeted

### Attempt 6 (Score: 8.35/10 — IMPROVEMENT from 6.60)
1. REVERTED characters.py Rule 0.6 — Restored The Red Death
2. KEPT grounding.py substring alias exemption

### Attempt 5 (Score: 6.60/10 — REGRESSION from 8.23)
1. Rule 0.6 in characters.py caused regression
2. grounding.py fix worked

### Attempt 4 (Score: 8.23/10 — PREVIOUS BEST before attempt 6)
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
| 11 | F6 plural group noun filter | analyzer.py | ✓ Worked — no F6 group characters |
| 11 | min_grounding_mentions = 2 | characters.py | ✗ OVER-FILTERED — Red Death removed, merged into Clock |
| 11 | Narrator min-mention guard | narrator.py | ✓ Works for 1-mention, doesn't fix 12-mention Prospero |
| 11 | "stra" suffix for collective nouns | main_cast.py, characters.py | ✓ Worked — orchestra alias blocked |
| 10 | Revert symbolic merge (restore Red Death) | main_cast.py | ✓ Red Death restored |
| 10 | Keep plural suffix filter | (no change) | ✓ Still works |
| 9 | Group aliases: plural suffix filter in _is_valid_alias | characters.py | ✓ WORKED — keep |
| 9 | Blocked aliases: symbolic reveal merge in extract() | main_cast.py | ✗ REGRESSION — REVERTED |
| 8 | Group nouns as aliases: Rule 2 prompt clarification | main_cast.py | No change — cosmetic only |
| 7 | Wrong group aliases: Rule 0.7 in verify_aliases | main_cast.py | Partial — changed which aliases |
| 7 | Missing correct aliases: Rule 3 exception | main_cast.py | No change — wrong rule |
| 6 | Revert characters.py regression | characters.py (reverted) | Fixed ✓ |
| 6 | Keep grounding.py fix | (no change) | Fixed ✓ |
| 5 | Wrong group aliases on Red Death | characters.py (_is_valid_alias) | REGRESSION |
| 5 | Missing "Prospero" alias | grounding.py | Fixed ✓ |
| 4 | Revert attempt 3 regression | main_cast.py | Fixed ✓ |
| 4 | is_symbolic detection improvement | main_cast.py | Fixed ✓ |
| 3 | Wrong group aliases on Red Death | main_cast.py | REGRESSION |
| 2 | Rule 0.5 over-blocking | main_cast.py | Fixed ✓ |
| 2 | Clock not marked is_symbolic | main_cast.py | Fixed ✓ |
| 2 | Wrong narrator detection | narrator.py | Fixed ✓ |
| 2 | Pronunciation false positives | cmu_proposer.py | Fixed ✓ |

**Pattern analysis:**
- `characters.py` min_grounding_mentions change caused regression — REVERT immediately
- The grounding threshold approach is too blunt for filtering noise characters — need a more targeted mechanism
- The best scores (8.23, 8.35) all used min_grounding_mentions=1 (the original default)
- Priority 2 (alias mention-count safety check) would prevent this entire class of error generically

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

## Configuration Audit
- Models: qwen3.5:122b-a10b for characters/summaries, qwen3.5:35b-a3b for structure/pronunciation
- Context length 32768 sufficient for 2,449-word short story
- Temperature 0.7 standard
- 0 LLM retries across all stages
- No chunking issues
- **Root cause is NOT model/config** — the regression is caused by min_grounding_mentions=2 filtering The Red Death

## Next Action
Run PROMPT_fix.md to:
1. REVERT min_grounding_mentions from 2 to 1 (one-line change in characters.py)
2. Add alias mention-count safety check in verify_aliases() to prevent more-mentioned entities from being demoted to aliases
