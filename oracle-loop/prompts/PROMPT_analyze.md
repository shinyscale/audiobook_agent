# Phase: ANALYZE

You are running the audiobook analysis pipeline on a test text as part of an autonomous improvement loop.

## 0. Orient

**Context Budget:** You have a limited context budget. Be efficient:
- Read only the files you need for this phase (state files, manifest, config)
- Don't explore the codebase - the analyze phase just runs the pipeline
- Don't read source code files - that's for the fix phase

0a. Read `state/EVALUATION_STATE.md` to understand current state.
0b. Read `state/manifest.json` to identify the current active text.
0c. Read `state/USER_NOTES.md` for any instructions from the user (if it exists and has content other than "(No notes)").
0d. Read `../AGENTS.md` for operational commands and codebase navigation.
0e. Read `~/.config/audiobook_prep/gui_settings.json` to get model configuration.

## 0.5 Initialize State for New Text

**IMPORTANT:** If starting a NEW text (different from what's in EVALUATION_STATE.md, or state shows `complete`), update the state file IMMEDIATELY before running analysis:

```markdown
# Current Evaluation State

## Active Text
- **Name:** {book_name}
- **Attempt:** 1
- **Phase:** awaiting_analysis
- **baseline_score:** null
- **Competitive Mode:** {competitive_mode}

## Latest Scores
(Awaiting first analysis)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| (none yet) | - | - | - |

## Notes
Starting analysis for {book_name}.
```

This ensures the monitor shows the correct text immediately, not after analysis completes.

## 1. Run Analysis

If `state/EVALUATION_STATE.md` shows phase is `awaiting_analysis` or this is a fresh start:

1. Identify the current text from `state/manifest.json` (first incomplete text)

2. **Resolve the input file path**:
   - The manifest stores paths relative to repo root (e.g., `Test_Texts/gatsby.txt`)
   - Since we run from `oracle-loop/`, prefix with `../` to get `../Test_Texts/gatsby.txt`
   - If `{text_file}` exists as-is, use it
   - Else if `../{text_file}` exists, use `../{text_file}`
   - Else fail loudly and document the missing path in `state/EVALUATION_STATE.md`

3. Extract model configuration from `~/.config/audiobook_prep/gui_settings.json`:
   - `agent_models.structure` → `--structure-model`
   - `agent_models.characters` → `--character-model`
   - `agent_models.summaries` → `--summary-model`
   - `agent_models.pronunciation` → `--pronunciation-model`

4. Check competitive consensus mode from `state/manifest.json`:
   - `competitive_mode: "none"` → No competitive flags (baseline behavior)
   - `competitive_mode: "single"` → Add `--competitive-consensus` (same model, 3 temperatures)
   - `competitive_mode: "multi"` → Add `--competitive-model` for each entry in `competitive_models` array

   **Format for multi mode:** Each entry in `competitive_models` is `"model:temp"`:
   - `qwen3:30b-instruct:0.5` → `--competitive-model "qwen3:30b-instruct:0.5"`
   - `deepseek-r1:32b:0.7` → `--competitive-model "deepseek-r1:32b:0.7"`
   - etc.

   **Competitive stages:** Check `competitive_stages` array to add stage-specific flags:
   - `"characters"` in array → add `--competitive-consensus` (character extraction uses multi-model voting)
   - `"structure"` in array → add `--competitive-structure` (chapter boundary detection uses multi-model voting)
   - `"summaries"` in array → add `--competitive-summaries` (chapter summary generation uses multi-model voting)

   **IMPORTANT:** You MUST add the stage-specific flags based on `competitive_stages` array!
   If the array is `["characters", "structure", "summaries"]`, add ALL THREE flags.

   Or if all three stages are enabled, you can use `--competitive-all` instead of listing each flag.

   **Note:** In multi-model mode, prompt style (strict/contextual/inclusive) is automatically
   set to "neutral" for all models. Different model architectures provide natural diversity,
   so artificial prompt bias is unnecessary.

5. Run the full analysis pipeline with explicit model flags:
   ```bash
   # Replace {text_file}, {book_name}, and model values from manifest and gui_settings.json
   # Note: {text_file} should be prefixed with ../ since we run from oracle-loop/
   # Add competitive flags based on competitive_mode setting
   audiobook-prep analyze ../{text_file} \
     --html ../output/{book_name}/report.html \
     --output ../output/{book_name}/analysis.json \
     {competitive_flags} \
     --structure-model {structure_model} \
     --character-model {character_model} \
     --summary-model {summary_model} \
     --pronunciation-model {pronunciation_model}
   ```

   Where `{competitive_flags}` is determined by `competitive_mode` AND `competitive_stages`:
   - **"none"**: (empty - no flags)
   - **"single"**: `--competitive-consensus` (uses same model at 3 temperatures)
   - **"multi"**: Multiple `--competitive-model` flags, one per entry in `competitive_models`

   **PLUS stage-specific flags from `competitive_stages` array:**
   - `"characters"` → `--competitive-consensus`
   - `"structure"` → `--competitive-structure`
   - `"summaries"` → `--competitive-summaries`

   For example, if `competitive_stages: ["characters", "structure", "summaries"]`, you MUST add:
   `--competitive-consensus --competitive-structure --competitive-summaries`

   **Example with mode "none" (baseline):**
   ```bash
   audiobook-prep analyze ../Test_Texts/gatsby.txt \
     --html ../output/gatsby/report.html \
     --output ../output/gatsby/analysis.json \
     --structure-model "qwen3:30b-instruct" \
     --character-model "qwen3-next:80b-a3b-instruct-q8_0" \
     --summary-model "qwen3-next:80b-a3b-instruct-q8_0" \
     --pronunciation-model "qwen3:30b-instruct"
   ```

   **Example with mode "single":**
   ```bash
   audiobook-prep analyze ../Test_Texts/gatsby.txt \
     --html ../output/gatsby/report.html \
     --output ../output/gatsby/analysis.json \
     --competitive-consensus \
     --structure-model "qwen3:30b-instruct" \
     --character-model "qwen3-next:80b-a3b-instruct-q8_0" \
     --summary-model "qwen3-next:80b-a3b-instruct-q8_0" \
     --pronunciation-model "qwen3:30b-instruct"
   ```

   **Example with mode "multi" and stages ["characters", "structure", "summaries"]:**
   ```bash
   audiobook-prep analyze ../Test_Texts/gatsby.txt \
     --html ../output/gatsby/report.html \
     --output ../output/gatsby/analysis.json \
     --competitive-model "qwen3:30b-instruct:0.5" \
     --competitive-model "deepseek-r1:32b:0.7" \
     --competitive-model "gemma3:27b:0.9" \
     --competitive-consensus \
     --competitive-structure \
     --competitive-summaries \
     --structure-model "qwen3:30b-instruct" \
     --character-model "qwen3-next:80b-a3b-instruct-q8_0" \
     --summary-model "qwen3-next:80b-a3b-instruct-q8_0" \
     --pronunciation-model "qwen3:30b-instruct"
   ```

   **Alternative using --competitive-all (when all 3 stages enabled):**
   ```bash
   audiobook-prep analyze ../Test_Texts/gatsby.txt \
     --html ../output/gatsby/report.html \
     --output ../output/gatsby/analysis.json \
     --competitive-model "qwen3:30b-instruct:0.5" \
     --competitive-model "deepseek-r1:32b:0.7" \
     --competitive-model "gemma3:27b:0.9" \
     --competitive-all \
     --structure-model "qwen3:30b-instruct" \
     --character-model "qwen3-next:80b-a3b-instruct-q8_0" \
     --summary-model "qwen3-next:80b-a3b-instruct-q8_0" \
     --pronunciation-model "qwen3:30b-instruct"
   ```

   Output will show:
   ```
   Multi-model consensus: ENABLED (3 diverse models)
     Mode: neutral (model diversity provides natural variation)
     - qwen3:30b-instruct @ 0.5
     - deepseek-r1:32b @ 0.7
     - gemma3:27b @ 0.9
   ```

   **Note on Character Extraction:**
   - Uses summary-driven approach for character extraction
   - Summaries run automatically before character extraction
   - See `oracle-loop/docs/CODEBASE_SUMMARY.md` for architecture details

   **Note on Competitive Consensus Modes:**
   - **"none"**: No competitive consensus (baseline behavior, single model decides)
   - **"single"**: `--competitive-consensus` runs the same model 3x at different temperatures (0.5, 0.7, 0.9)
   - **"multi"**: `--competitive-model` runs diverse models (qwen3, deepseek-r1, gemma3) for true model diversity

   For both "single" and "multi" modes:
   - Each merge/alias decision requires 2/3 (supermajority) agreement
   - This prevents single-LLM hallucinations from causing false merges
   - Particularly effective for preventing errors like "Mr. McKee" aliased to "Mr. Sloane"

6. Wait for completion (this may take 10-60 minutes depending on text length and model)
7. Verify output exists:
   - `../output/{book_name}/report.html`
   - `../output/{book_name}/analysis.json`

## 2. Update State

Update `state/EVALUATION_STATE.md`:
- Set `**Phase:**` to `awaiting_evaluation`
- Increment attempt counter if this is a re-run
- Note any pipeline errors or warnings that occurred
- Record the output file paths

Example update:
```markdown
## Active Text
- **Name:** gatsby
- **Attempt:** 1
- **Phase:** awaiting_evaluation
- **Competitive Mode:** multi

## Output Files
- HTML: ../output/gatsby/report.html
- JSON: ../output/gatsby/analysis.json

## Pipeline Notes
- (Note any warnings or issues from the analysis run)
```

## 3. Exit

Commit changes and exit cleanly. The loop will restart with PROMPT_evaluate.md.

```bash
git add state/EVALUATION_STATE.md ../output/
git commit -m "Analyze: {book_name} attempt {n} - complete"
```

## Important Notes

- **Do NOT** evaluate the output yourself - that's the next phase
- **Do NOT** make any code changes - just run the analysis
- If the pipeline fails, document the error in `state/EVALUATION_STATE.md` and set phase to `awaiting_fix`
- If output files already exist from a previous run, they will be overwritten
