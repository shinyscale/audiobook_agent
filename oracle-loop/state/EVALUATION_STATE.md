# Current Evaluation State

## Active Text
- **Name:** masque_of_red_death
- **Attempt:** 12
- **Phase:** awaiting_fix
- **baseline_score:** 6.85
- **Competitive Mode:** none

## Output Files
- HTML: ../output/masque_of_red_death/report.html
- JSON: ../output/masque_of_red_death/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 4/10 ✗
  - Completeness: 5/10
  - Identity Resolution: 3/10 ← catastrophic false merge persists
  - Alias Grouping: 3/10
- Character Profiles: 5.5/10 ✗
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 7.0/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (Character Extraction 4/10, Character Profiles 5.5/10)

## Pipeline Notes (Attempt 12)
- Analysis completed in 18m 0s (28 LLM calls, 44,921 tokens)
- 4 characters found during extraction, 2 in final output (IDs main_cast_0, main_cast_3 survived; IDs 1, 2 filtered/merged)
- Final 2 characters: Prince Prospero (6 mentions), The Ebony Clock (25 mentions)
- The Ebony Clock aliases: "the clock", "The Masked Figure", "masked figure", "the figure", "The Red Death" — **4 of 5 are WRONG**
- **The Red Death STILL falsely merged into Ebony Clock** despite reverting min_grounding_mentions
- POV guard fix WORKED: Prospero `is_narrator: false` ✓
- BLOCKED aliases logged for Red Death's own aliases (core noun mismatch)
- "casements" IPA now correct (/ˈkeɪs.mənts/) ✓

## Root Cause Analysis (Attempt 12)

The `min_grounding_mentions` revert from 2→1 did NOT fix the core problem. The Red Death is still being merged into the Ebony Clock. This means the previous root cause analysis (attempt 11) was **wrong** — the grounding threshold was NOT the primary cause.

**Revised root cause:** The LLM-driven within-main merge step (characters.py Step 3.5) is merging The Red Death and The Masked Figure into The Ebony Clock. Even with min_grounding_mentions=1:
1. 4 characters extracted: Prince Prospero (main_cast_0), ??? (main_cast_1), ??? (main_cast_2), The Ebony Clock (main_cast_3)
2. main_cast_1 and main_cast_2 were The Red Death and The Masked Figure
3. During within-main merge / Pass 2 alias resolution, the LLM proposes merging them into the Clock
4. Rule 0.5 ("alias can't be another character's canonical") should block this, but either:
   - (a) The merge happens in a step BEFORE verify_aliases runs, or
   - (b) The merges happen sequentially — one entity is merged first, removing it from the canonical list, then the second merge isn't blocked because the first entity's canonical no longer exists, or
   - (c) Rule 0.5 string matching doesn't exactly match (case, articles, etc.)
5. All three wrong aliases end up on the Clock

**The POV guard fix is confirmed working.** Prospero is no longer marked as narrator in this 3rd-person narrative.

**Key insight for fix phase:** This is attempt 12 and the same core issue (Red Death merged into Clock) has persisted across attempts 9-12 despite different fix approaches. The fix phase MUST investigate the actual merge mechanism — not just change thresholds. Debug logging should show EXACTLY where and why The Red Death stops being a standalone character.

## Current Issues (Priority Order)

### CRITICAL
1. **The Red Death falsely merged into The Ebony Clock** [Identity Resolution, Completeness]
   - Problem: "The Red Death" (personified plague, title antagonist), "The Masked Figure", "masked figure", and "the figure" are ALL listed as aliases of "The Ebony Clock" (a timepiece). Only 2 characters remain when there should be at least 3.
   - Evidence: `jq '.characters[1].aliases'` → `["the clock", "The Masked Figure", "masked figure", "the figure", "The Red Death"]`
   - Root cause: The within-main merge step merges The Red Death and The Masked Figure into the Clock. The `min_grounding_mentions` revert did NOT fix this — the merge happens regardless of grounding threshold.
   - Location: `src/agents/characters.py` — within-main merge step (Step 3.5) or `src/pipeline/character_extraction_v2/main_cast.py` — `_process_consolidated_pass2()` or `verify_aliases()`
   - Fix approach: **The fix phase MUST add debug logging to trace exactly where the merge happens**, then apply a targeted block. Three potential generic fixes (try in order):
     - **(A) Rule 0.5 investigation:** Verify Rule 0.5 is actually running and matching. Add temporary debug logging to `verify_aliases()` to see if "The Red Death" alias proposal reaches Rule 0.5 and why it passes. Fix any string matching issues (case sensitivity, article handling).
     - **(B) Mention-count guard (new Rule 0.8):** Add a rule in `verify_aliases()` that blocks an alias if the alias text has a HIGHER mention count than the canonical character's name. "The Red Death" appears more often than "The Ebony Clock" in the source text. This is a universal invariant — aliases are typically less-frequent references.
     - **(C) Within-main merge guard:** If the merge happens in a bulk merge step rather than verify_aliases, add a check there: do not merge two characters that were both extracted as SEPARATE main_cast entries (they were split for a reason).
   - Impact: +3 points on Character Extraction, +2 on Profiles

### HIGH
2. **Missing valid Red Death aliases** [Alias Grouping]
   - Problem: When The Red Death IS a standalone character (attempts 4-8), it has NO aliases. "the masked figure", "the intruder", "the stranger" are all blocked by core noun mismatch ("figure"/"intruder"/"stranger" ≠ "death").
   - Evidence: Pipeline notes across multiple attempts show BLOCKED aliases for Red Death
   - Location: `verify_aliases()` in main_cast.py — core noun comparison
   - Fix: For `is_symbolic=True` characters, relax core noun matching. The text explicitly states the masked figure IS the Red Death — these are narrative synonyms, not regular aliases.
   - Impact: ~1 point on Alias Grouping (can wait until after CRITICAL #1 is fixed)
   - Note: Attempted in attempts 7-8 without success. May need a different approach — e.g., co-reference resolution based on summary text context.

3. **Prospero's physical description incomplete** [Profiles]
   - Problem: "bold and robust" — text also says "happy and dauntless and sagacious"
   - Location: Profile generation in analyzer.py
   - Impact: ~0.25 points. Fix naturally after character list is corrected.

### MEDIUM
4. **2 pronunciation entries missing IPA** [Pronunciation]
   - "produce" and "deliberate" (homographs) have null IPA
   - Impact: minor. Pronunciation at 8/10, above threshold.

5. **Prince Prospero's relationship listed as "The Ebony Clock: antagonist"** [Profiles]
   - Problem: The Red Death is the antagonist, not the Clock. This will self-correct when character list is fixed.

## Fix Guidance for Attempt 13

### MANDATORY: Debug the merge mechanism (CRITICAL #1)

The fix phase has been trying different approaches for 4 attempts (9-12) without resolving this. **Before applying ANY fix, the fix phase MUST:**

1. **Add temporary debug logging** to trace the merge path:
   ```python
   # In characters.py within-main merge (Step 3.5) — log merge proposals
   # In main_cast.py verify_aliases() — log Rule 0.5 checks
   # In main_cast.py _process_consolidated_pass2() — log merge decisions
   ```

2. **Run the analysis with logging** (or read existing logs if available) to answer:
   - At what step does The Red Death stop being a standalone character?
   - Does Rule 0.5 see the "The Red Death" → "The Ebony Clock" alias proposal?
   - If yes, why doesn't it block it?
   - If no, which step merges them BEFORE verify_aliases?

3. **Only then apply a targeted fix** based on what the debug reveals.

### Probable fix: Mention-count guard (Rule 0.8)

Regardless of root cause, adding a mention-count guard in `verify_aliases()` is a **safe, generic fix** that would prevent this class of error:

```python
# Rule 0.8: Block alias if it has more text mentions than the canonical
# Universal invariant: aliases are alternative (usually less common) references
if alias_mention_count > canonical_mention_count:
    return False  # Block — more-prominent entity should not be an alias
```

This requires passing mention counts to `verify_aliases()`. Check if `mention_count` data is available in the context passed to this function.

### Constraints
- Do NOT modify prompts in ways that are novel-specific
- Changes must be generic (work for any text)
- Test with `pytest --ignore=tests/test_semantic_conflicts.py --ignore=tests/test_pdf_ingestion.py --ignore=tests/test_refine.py`
- **INVESTIGATE before fixing** — 4 attempts at blind fixes have failed

## Fix History

### Attempt 12 (Score: 7.0/10 — marginal improvement from 6.95)
1. **REVERT min_grounding_mentions to 1** in `src/agents/characters.py`:
   - Result: ✗ DID NOT FIX — The Red Death still merged into Clock. Grounding threshold was NOT the root cause.
2. **POV guard for narrator assignment** in `src/pipeline/character_extraction_v2/narrator.py`:
   - Result: ✓ WORKED — Prospero no longer marked as narrator (+0.5 on Profiles)

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
| 12 | Revert min_grounding_mentions from 2 to 1 | characters.py | ✗ DID NOT FIX — merge persists |
| 12 | POV guard: narrator only set for first-person/epistolary | narrator.py | ✓ WORKED — Prospero no longer narrator |
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
- **main_cast.py and characters.py have been modified 15+ times** across attempts without resolving the Red Death merge
- The best scores (8.23, 8.35) were achieved in attempts 4-8 — the merge problem is **intermittent and LLM-dependent**
- Attempts 9-12 consistently show the merge, suggesting a code change between attempt 8 and 9 destabilized the pipeline
- The fix phase MUST investigate what changed between attempt 8 (8.35, working) and attempt 9 (7.35, broken)
- Specifically: attempt 9 added two changes — plural filter (kept, works) and symbolic reveal merge (reverted). But even after reverting the reveal merge, the problem persists in attempts 10-12.
- **Hypothesis:** LLM non-determinism is a major factor. The same code can produce different character merges on different runs. A robust fix needs to be a HARD BLOCK (like Rule 0.5 or a mention-count guard) rather than relying on the LLM to make the right merge decision.

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
- Attempt 12: 7.0/10 (+0.05) ← POV fix helped, merge persists

## Configuration Audit
- Models: qwen3.5:122b-a10b for characters/summaries, qwen3.5:35b-a3b for structure/pronunciation
- Context length 32768 sufficient for 2,449-word short story
- Temperature 0.7 standard
- 0 LLM retries across all stages
- No chunking issues
- **Root cause is NOT model/config** — the problem is in the alias merge logic failing to block cross-entity merges

## Next Action
Run PROMPT_fix.md to address the Red Death merge (CRITICAL #1). **Fix phase MUST debug the merge mechanism before applying fixes.**
