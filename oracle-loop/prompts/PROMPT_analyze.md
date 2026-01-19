# Phase: ANALYZE

You are running the audiobook analysis pipeline on a test text as part of an autonomous improvement loop.

## 0. Orient

0a. Read `EVALUATION_STATE.md` to understand current state.
0b. Read `manifest.json` to identify the current active text.
0c. Read `AGENTS.md` for operational commands and codebase navigation.
0d. Read `~/.config/audiobook_prep/gui_settings.json` to get model configuration.

## 1. Run Analysis

If EVALUATION_STATE.md shows phase is `awaiting_analysis` or this is a fresh start:

1. Identify the current text from manifest.json (first incomplete text)
2. Extract model configuration from `~/.config/audiobook_prep/gui_settings.json`:
   - `agent_models.structure` → `--structure-model`
   - `agent_models.characters` → `--character-model`
   - `agent_models.summaries` → `--summary-model`
   - `agent_models.pronunciation` → `--pronunciation-model`

3. Run the full analysis pipeline with explicit model flags:
   ```bash
   # Replace {text_file}, {book_name}, and model values from manifest and gui_settings.json
   audiobook-prep analyze {text_file} \
     --html output/{book_name}/report.html \
     --output output/{book_name}/analysis.json \
     --structure-model {structure_model} \
     --character-model {character_model} \
     --summary-model {summary_model} \
     --pronunciation-model {pronunciation_model}
   ```

   Example using models from gui_settings.json:
   ```bash
   audiobook-prep analyze Test_Texts/gatsby.txt \
     --html output/gatsby/report.html \
     --output output/gatsby/analysis.json \
     --structure-model "qwen3:30b-instruct" \
     --character-model "qwen3-next:80b-a3b-instruct-q8_0" \
     --summary-model "qwen3-next:80b-a3b-instruct-q8_0" \
     --pronunciation-model "qwen3:30b-instruct"
   ```

4. Wait for completion (this may take 10-60 minutes depending on text length and model)
5. Verify output exists:
   - `output/{book_name}/report.html`
   - `output/{book_name}/analysis.json`

## 2. Update State

Update `EVALUATION_STATE.md`:
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

## Output Files
- HTML: output/gatsby/report.html
- JSON: output/gatsby/analysis.json

## Pipeline Notes
- (Note any warnings or issues from the analysis run)
```

## 3. Exit

Commit changes and exit cleanly. The loop will restart with PROMPT_evaluate.md.

```bash
git add EVALUATION_STATE.md output/
git commit -m "Analysis complete: {book_name} attempt {n}"
```

## Important Notes

- **Do NOT** evaluate the output yourself - that's the next phase
- **Do NOT** make any code changes - just run the analysis
- If the pipeline fails, document the error in EVALUATION_STATE.md and set phase to `awaiting_fix`
- If output files already exist from a previous run, they will be overwritten
