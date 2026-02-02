# Current Evaluation State

## Active Text
- **Name:** cask_of_amontillado
- **Attempt:** 1
- **Phase:** awaiting_fix
- **baseline_score:** 4.20

## Output Files
- HTML: ../output/cask_of_amontillado/report.html
- JSON: ../output/cask_of_amontillado/analysis.json

## Latest Scores
- Structure Detection: 7/10 ✗ (FAILING - below 8.0)
- Character Extraction: 2/10 ✗ (CRITICAL FAILURE)
- Character Profiles: 5/10 ✗ (FAILING)
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 9/10 ✓
- HTML Presentation: 7/10 ✗ (FAILING - presentation reflects extraction issues)
- **Overall: 4.20/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (4 categories below threshold)

## Current Issues (Priority Order)

### CRITICAL
1. **Narrator (Montresor) not detected by main_cast extraction**
   - Problem: Montresor, the first-person narrator and protagonist, was NOT detected by the character extraction pipeline
   - Evidence: His character has `id: e3bdcd5e8982` (12-char hash = F6 summary reconciliation), not `main_cast_*`
   - Evidence: Only 1 mention recorded, but he is the narrator of the ENTIRE story
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` - first-person narrator detection
   - Why this matters: The narrator's name "Montresor" appears explicitly in the text ("the name is Montresor", "my family's coat of arms Montresor")
   - Fix: The main_cast extraction needs to recognize first-person narrators when they explicitly name themselves in the text

### HIGH
2. **Montresor profile severely incomplete**
   - Problem: The narrator's profile has no relationships, voice guidance, or detailed traits
   - Evidence: `relationships: {}` when Montresor clearly has a relationship with Fortunato (revenge/enemy)
   - Evidence: No voice guidance for the character who speaks the most in the story
   - Location: `src/pipeline/character_profiling/` - profile generation for narrator characters
   - Fix: Narrator characters need profile extraction from their first-person speech patterns, not just third-person descriptions

3. **Structure detection shows "Chapter 1" for a chaptersless short story**
   - Problem: "The Cask of Amontillado" is a single short story with NO chapters
   - Evidence: Structure detected with `title: null` and labeled as "Chapter 1"
   - Location: `src/pipeline/chapter_detection/` - short story handling
   - Fix: For short stories without chapter breaks, detect as single unified work, not "Chapter 1"

### MEDIUM
4. **HTML presentation reflects upstream extraction issues**
   - Problem: Montresor's profile card is nearly empty compared to Fortunato's rich profile
   - Evidence: Fortunato has appearance, personality, voice guidance; Montresor has only a brief description
   - Location: This is a downstream effect of #1 and #2
   - Fix: Fixing upstream extraction issues will automatically fix this

## Fix History
(First attempt)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | (Initial evaluation) | N/A | Score: 4.20/10 |

## Experiment Context

This is experiment `exp_009_mixed_moe_competitive_chars` using:
- character_model: qwen3-next:80b-a3b-instruct-q8_0
- structure_model: qwen2.5:14b
- summary_model: qwen2.5:32b
- competitive_consensus: true (for characters only)

Previous experiments on this text:
- exp_001 (qwen3-next baseline): 9.95/10 (PASSED)
- exp_002 (qwen3-next competitive): 8.18/10 (PASSED)
- exp_003 (gpt-oss): 7.90/10 (failed)
- exp_004 (gpt-oss competitive): 9.45/10 (PASSED)
- exp_005 (nemotron): 9.30/10 (PASSED)
- exp_006 (nemotron competitive): 8.125/10 (failed)
- exp_007 (deepseek-r1): 5.45/10 (failed)
- exp_008 (mixed MoE fast): 4.20/10 (failed)

**Pattern observed:** Mixed-model configurations using smaller models for structure (qwen2.5:14b) and summaries (qwen2.5:32b) are failing. The configurations that passed use the same model throughout.

## Root Cause Analysis

The critical failures in this experiment appear to stem from:

1. **Mixed model coordination issue**: When different models are used for character extraction vs. summaries, the narrator detection may not propagate correctly through F6 reconciliation

2. **Smaller structure model**: qwen2.5:14b for structure may not have enough capability to properly identify single-work short stories vs. chaptered works

3. **Character extraction pipeline**: First-person narrator detection relies on summary data, but with different models, the handoff may be incomplete

## Next Action
This experiment (exp_009) should be marked as FAILED in experiments.json. The oracle loop should:
1. Mark this experiment as failed_screening
2. Move to the next experiment in the queue
3. If all experiments are exhausted, summarize findings for user review

**NOTE:** This is an EXPERIMENT evaluation, not a code fix loop. The pipeline code itself passed with other configurations (exp_001, exp_002, exp_004, exp_005). The issue is the MODEL CONFIGURATION, not the code.
