# Current Evaluation State

## Active Text
- **Name:** masque_of_red_death
- **Attempt:** 1
- **Phase:** awaiting_analysis
- **baseline_score:** 8.50
- **Competitive Mode:** none

## Output Files
- HTML: ../output/masque_of_red_death/report.html
- JSON: ../output/masque_of_red_death/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 9/10 ✓
  - Completeness: 9/10
  - Identity Resolution: 10/10
  - Alias Grouping: 8/10
- Character Profiles: 7/10 ✗ (FAILING)
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 8/10 ✓
- **Overall: 8.50/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (Character Profiles below threshold)

## Current Issues (Priority Order)

### CRITICAL
1. **Missing Prospero ↔ Red Death antagonistic relationship** [Profiles]
   - Problem: The relationship grid shows NO connection between Prince Prospero and The Red Death. Prospero only has a relationship with "the courtiers" (close friend), and The Red Death only has a relationship with "the courtiers" (associated). The central conflict of the entire story — prince defies personified death, confronts the masked figure, and dies — has no relationship entry.
   - Evidence: In the story, Prospero directly confronts the Red Death figure, chases it through the seven chambers, and is killed. This is THE relationship of the story.
   - Location: `src/pipeline/character_extraction_v2/` profiling stage, and/or `src/post_corrections.py` (`verify_relationships_from_text`)
   - Fix: The profiler should detect the antagonistic relationship between Prospero and The Red Death. In a 2400-word text, co-mention windows in `verify_relationships_from_text` should capture this. Check if the issue is that The Red Death is treated as a non-person entity and skipped by relationship detection.

### HIGH
2. **Thin Prince Prospero profile** [Profiles]
   - Problem: Profile says "bold and robust man" but Poe writes "happy and dauntless and sagacious." Profile misses his defiant character, his rage at the masked figure, and his climactic fatal confrontation. "Robust" is not in the source text.
   - Evidence: Text says "the Prince Prospero was happy and dauntless and sagacious" — profile should capture sagacity and dauntlessness
   - Location: Profile generation LLM prompts in `src/pipeline/character_extraction_v2/` or `analyzer.py` (`_generate_character_profile()`)
   - Fix: May improve on re-run with same code (LLM stochasticity). If persistent, check if profile generation has sufficient context for short texts.

3. **Vague/inaccurate relationship labels** [Profiles]
   - Problem: "close friend" for Prospero ↔ courtiers is inaccurate — they are his court subjects/guests he summoned ("summoned to his presence about a thousand hale and light-hearted friends from among the knights and dames of his court"). "Associated" for Red Death ↔ courtiers is meaningless — the Red Death kills them all.
   - Evidence: Text clearly establishes lord/subject dynamic and lethal antagonism
   - Location: Profile generation and `src/post_corrections.py` relationship labeling
   - Fix: May partially resolve with better Prospero↔Red Death relationship. "Associated" label is a known vague fallback.

### MEDIUM
4. **"The masked figure" not listed as alias for The Red Death** [Alias Grouping]
   - Problem: The masked figure and The Red Death are the same entity (revealed at the climax). The summary's active_characters lists "the masked figure" separately, but it's not an alias of The Red Death in the character output.
   - Evidence: The story's climax reveals the masked figure IS the Red Death personified
   - Location: Alias detection in `src/pipeline/character_extraction_v2/main_cast.py` — Rule 0.5 (core noun mismatch) blocks "figure"↔"death" aliases
   - Fix: Post-extraction merge similar to `merge_reveal_characters()` in twostage_experiment.py. This was already solved for this exact pattern in previous experiments.

5. **All characters grouped as "Supporting" in HTML** [Presentation]
   - Problem: The HTML groups all 3 characters under "Supporting Characters" despite JSON having roles: protagonist (Prospero), antagonist (Red Death), supporting (courtiers). Low mention counts in a short story (<10 each) cause the HTML template to classify all as supporting.
   - Evidence: JSON has `role: "protagonist"` for Prospero and `role: "antagonist"` for Red Death
   - Location: HTML template in `src/` (report generation)
   - Fix: Template should use the `role` field to group characters, not just mention counts

## Fix History
- Attempt 2: Fixed missing Prospero↔Red Death relationship and HTML character grouping
  - Root cause 1: `add_cooccurrence_relationships` uses `min_shared=3` (default), but Masque has only 1 chapter — shared count never reaches 3, so the pair is never linked. Fix: adaptive `min_shared = max(1, min(3, n_chapters // 3))`.
  - Root cause 2: HTML groups characters by `mention_count >= 10`, but short story characters all have <10 mentions → all appear under "Supporting". Fix: also include characters with role=protagonist/antagonist.
  - Smoke test: PASS — Prospero↔Red Death added as "associated" with min_shared=1; HTML groups Prospero+RedDeath as Main, courtiers as Supporting.
  - Modified: `src/pipeline/character_profiling/post_corrections.py`, `src/export/html_report.py`
  - Tests: 332 passed, 0 failed

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| (first attempt) | — | — | — |
| 2 | Missing Prospero↔RedDeath relationship; HTML grouping | post_corrections.py, html_report.py | awaiting_analysis |

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 8.50 | — | Profiles 7/10 failing; missing Prospero↔Red Death relationship |

## Next Action
Re-run analysis to verify fixes

**Phase:** awaiting_analysis
