# Current Evaluation State

## Active Text
- **Name:** masque_of_red_death
- **Attempt:** 10
- **Phase:** awaiting_fix
- **baseline_score:** 6.85
- **Competitive Mode:** none

## Output Files
- HTML: ../output/masque_of_red_death/report.html
- JSON: ../output/masque_of_red_death/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 6/10 ✗ (FAILING)
  - Completeness: 6/10 ← Ebony Clock missing, hallucinated "Darkness", group nouns as characters
  - Identity Resolution: 6/10 ← "Darkness" fabricated as narrator, group nouns inflate list
  - Alias Grouping: 5/10 ← "the orchestra" wrong alias on Red Death, valid aliases missing
- Character Profiles: 6.5/10 ✗ (FAILING)
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 8/10 ✓
- **Overall: 7.68/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL — 2 categories below threshold (Character Extraction 6/10, Character Profiles 6.5/10)

## Comparison to Previous Attempts

| Attempt | Overall | Char Extract | Char Profiles | Key Diff |
|---------|---------|-------------|---------------|----------|
| 8 (best)| 8.35    | ~7.5        | ~8.5          | Had Ebony Clock, Red Death with wrong group aliases |
| 9       | 7.35    | 5           | 6             | Red Death MISSING (regression) |
| **10**  | **7.68**| **6**       | **6.5**       | Red Death restored, but Ebony Clock missing, "Darkness" hallucinated |

The revert succeeded in restoring The Red Death, but LLM non-determinism produced a different (worse) character set than attempt 8. Key differences from attempt 8:
- Ebony Clock not extracted (was present in attempts 4-8)
- "Darkness" fabricated as a 1-mention narrator character
- Group nouns (courtiers, musicians) appear as F6-reconciled characters instead of as aliases
- "the orchestra" is the new wrong alias on Red Death (instead of revellers/courtiers/musicians)

## Current Issues (Priority Order)

### CRITICAL
1. **Group nouns appearing as F6 characters** [Completeness, Identity Resolution]
   - Problem: "the courtiers" (id=2dc5504206d2) and "the musicians" (id=2c119eeb2375) are F6-reconciled characters. These are unnamed groups of people, not individual characters.
   - Evidence: Both have hash IDs (F6 reconciliation), 2-3 mentions each, no profiles
   - Location: F6 reconciliation in `src/analyzer.py` (~line 1197+). The `_is_valid_alias()` plural suffix filter in `characters.py` correctly blocks these as aliases, but F6 creates them as standalone characters with no equivalent filter.
   - Fix: Add a plural-group-noun filter to F6 character creation in `analyzer.py`. Before creating an F6 character, check if the name matches the same plural suffix patterns used in `_is_valid_alias()` (e.g., ends in -iers, -ians, -ers, -ors, etc.) AND is a lowercase descriptor (no proper-noun capitalization). If so, skip creating the character.
   - Impact: Removing 2 invalid characters improves Completeness and Identity Resolution by ~1 point each.

2. **"Darkness" hallucinated as character and narrator** [Completeness, Identity Resolution]
   - Problem: "Darkness" (id=main_cast_7, 1 mention, is_narrator=True) is extracted as a character and marked as narrator. "Darkness" appears exactly once in the final sentence: "And Darkness and Decay and the Red Death held illimitable dominion over all." It is a poetic personification in a single line, not a character. The story uses 3rd-person omniscient narration — no named narrator.
   - Evidence: 1 mention, low confidence (0.15 per pipeline notes), no physical description, no relationships, no profile content
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` (extracted as main_cast) and narrator detection
   - Fix: Two-pronged approach:
     1. **Minimum mention threshold for main cast**: Characters with ≤ 1 mention and very low confidence should be filtered before profile generation. Check if there's already a threshold and whether it's being applied.
     2. **Narrator validation**: A character with 1 mention cannot be the narrator. The narrator detection logic should require a minimum threshold of mentions or textual evidence (e.g., first-person pronoun usage attributed to the character).
   - Impact: Removing 1 invalid character + fixing narrator assignment improves both sub-dimensions.

### HIGH
3. **"the orchestra" as Red Death alias** [Alias Grouping]
   - Problem: The Red Death's only alias is "the orchestra" — a group of musicians who PLAY during the ball. They are victims of the Red Death, not the Red Death itself. This alias is completely wrong.
   - Evidence: In the text, "the orchestra" refers to the musicians who pause when the ebony clock strikes. They are separate from the masked figure who IS the Red Death.
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` — alias resolution pass
   - Fix: "the orchestra" is a collective noun (like "the army", "the crew") but doesn't match the existing -ers/-ors suffix filter. Options:
     1. Add common collective nouns to a blocklist in `_is_valid_alias()` or `verify_aliases()`
     2. OR add a semantic check: if the alias appears in summaries as a SEPARATE entity acting independently from the canonical character, block it
     3. The simpler approach: the alias "the orchestra" should fail Rule 2 (must co-occur in at least one summary with the canonical) because the orchestra is described independently from the Red Death. Verify whether Rule 2 is being applied correctly.
   - Impact: Fixing this improves Alias Grouping by ~1.5 points.

4. **Missing valid Red Death aliases** [Alias Grouping]
   - Problem: The Red Death should have aliases like "the masked figure", "the intruder", "the figure", "the mummer", "the stranger" — these all refer to the Red Death when it appears at the ball. Currently zero valid aliases.
   - Evidence: The text uses these terms interchangeably to describe the Red Death's appearance at the masquerade. The summary correctly mentions "a masked figure dressed as the Red Death."
   - Root cause: The alias resolution prompt/LLM isn't proposing these, OR verify_aliases is blocking them. Per pipeline notes: "the masked figure" aliases blocked as "semantically unrelated (core noun mismatch)."
   - Location: `verify_aliases()` in `main_cast.py` — the "core noun mismatch" check is too strict for symbolic/metaphorical identities where a "figure" IS the personification of "death"
   - Fix: The core-noun check should be relaxed for `is_symbolic=True` characters, or for cases where the summary explicitly states identity (e.g., "a masked figure dressed as the Red Death" = identity link).
   - Impact: Adding valid aliases improves Alias Grouping by ~1 point.

5. **The Ebony Clock missing** [Completeness]
   - Problem: The Ebony Clock was present in attempts 4-8 but is absent in attempt 10. It is a significant symbolic element — its hourly chiming drives the story's tension and foreshadows doom.
   - Evidence: The summary mentions "an ebony clock in the westernmost chamber chimes every hour, momentarily silencing the orchestra and causing the guests to grow pale and uneasy." The text references the clock multiple times.
   - Root cause: LLM non-determinism — the extraction model didn't identify it this run. This is NOT a code regression (the code was reverted to pre-attempt-9 state, which previously extracted the clock).
   - Location: LLM extraction in main_cast.py (Pass 1)
   - Fix: This is harder to address deterministically. Options:
     1. Re-run analysis (may extract it next time)
     2. Lower the extraction threshold for symbolic/object entities
     3. Add a post-extraction "significant object" pass that checks summaries for frequently-mentioned objects
   - Impact: Having the Ebony Clock would improve Completeness by ~1 point.

6. **Red Death and Ebony Clock not marked is_symbolic** [Identity Resolution]
   - Problem: The Red Death (`is_symbolic: false`) is a personified pestilence — it should be `is_symbolic: true`. The Ebony Clock (when present) should also be symbolic.
   - Evidence: Previous attempts (2-4) correctly marked these as symbolic
   - Location: `is_symbolic` detection in main_cast.py
   - Fix: Check if the is_symbolic detection rules were affected by the revert. The symbolic detection improvements from attempt 2/4 should still be in the codebase.

### MEDIUM
7. **"1 chapters" grammar in HTML** [Presentation]
   - Deferred — Presentation is at 8/10, above threshold

8. **2 pronunciation entries missing IPA** [Pronunciation]
   - "produce" and "deliberate" have null IPA (homographs)
   - Deferred — Pronunciation is at 8/10, above threshold

9. **Prospero relationships with group nouns** [Profiles]
   - Problem: Prospero's relationships list "the courtiers: close friend" and "the musicians: associated" — these are groups, not individual characters. Missing key relationship: "the Red Death: antagonist"
   - This will partly resolve when group nouns are removed from characters

## Fix Guidance for Attempt 11

### Priority 1: Filter group nouns from F6 (CRITICAL #1)
Add a plural-group-noun check to F6 character creation in `src/analyzer.py`. Before creating an F6 character, apply the same plural suffix filter used in `_is_valid_alias()`. This prevents group nouns like "the courtiers", "the musicians", "the revellers" from becoming standalone characters.

Look for the F6 reconciliation code around line 1197+ in analyzer.py. When a missing character name is about to be added, check:
```python
# Pseudocode
if name_is_plural_group_noun(missing_name):
    continue  # skip this F6 character
```

Use the same suffix patterns from `_is_valid_alias()` in characters.py.

### Priority 2: Filter 1-mention low-confidence characters (CRITICAL #2)
"Darkness" has 1 mention and was extracted as a main_cast character. A main_cast character with ≤ 1 mention is almost certainly noise. Add a minimum mention threshold (e.g., ≥ 2 mentions) for main_cast extraction, or filter characters with very low confidence (< 0.2) and ≤ 1 mention.

Also fix narrator detection: a 1-mention character should never be tagged as narrator.

### Priority 3: Fix "the orchestra" alias (HIGH #3)
Verify whether the existing alias validation (Rule 2 co-occurrence, core noun matching) should catch "the orchestra" as an invalid alias for the Red Death. If not, add a collective-noun check. "orchestra" is not a person and shouldn't be an alias for any character.

### Priority 4: Address missing Red Death aliases (HIGH #4)
The core-noun mismatch check blocks "the masked figure" as an alias for "the Red Death" because "figure" ≠ "death". For `is_symbolic=True` characters, this check should be relaxed — symbolic entities often have aliases with different core nouns (the personification vs. the disguise).

### Constraints
- Do NOT modify prompts in ways that are novel-specific
- Changes must be generic (work for any text)
- Keep changes minimal — focus on the 2-3 fixes that cross 8.0
- Test with `pytest --ignore=tests/test_semantic_conflicts.py --ignore=tests/test_pdf_ingestion.py --ignore=tests/test_refine.py`

## Fix History

### Attempt 10 (Score: 7.68/10 — improvement from 7.35, but below best of 8.35)
1. **REVERTED symbolic reveal merge** in `src/pipeline/character_extraction_v2/main_cast.py`:
   - Removed `_proposed_before_verify` saving logic and `SYMBOLIC DESCRIPTOR MERGE` block
   - Result: ✓ The Red Death restored to character list
2. **KEPT plural group noun filter** in `src/agents/characters.py` (_is_valid_alias):
   - Result: ✓ Group nouns not assigned as aliases (but still created as F6 characters)
3. Test limit: 9550 → 9500
4. **New issues from LLM non-determinism**: Ebony Clock missing, "Darkness" hallucinated, "the orchestra" wrong alias

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
- F6 reconciliation (`analyzer.py`) has NEVER been modified in this loop — it's a fresh target for fixing group noun characters
- "Darkness" hallucination is new — requires a mention-count or confidence filter
- main_cast.py continues to be the most-modified and most-regressed file — be very careful with changes
- The best scores (8.23, 8.35) came from MINIMAL targeted changes, not large refactors

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

## Configuration Audit
- Models: qwen3.5:122b-a10b for characters/summaries, qwen3.5:35b-a3b for structure/pronunciation
- Context length 32768 sufficient for 2,449-word short story
- Temperature 0.7 standard
- 0 LLM retries across all stages
- No chunking issues
- **Root cause is NOT model/config** — remaining issues require code-level filtering in F6 and alias validation

## Next Action
Run PROMPT_fix.md to address CRITICAL #1 (F6 group noun filter) and CRITICAL #2 (1-mention character filter), then HIGH #3 (orchestra alias).
