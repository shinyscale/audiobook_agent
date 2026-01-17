# Phase: ANALYZE

You are running the audiobook analysis pipeline on a test text as part of an autonomous improvement loop.

## 0. Orient

0a. Read `EVALUATION_STATE.md` to understand current state.
0b. Read `manifest.json` to identify the current active text.
0c. Read `AGENTS.md` for operational commands and codebase navigation.

## 1. Run Analysis

If EVALUATION_STATE.md shows phase is `awaiting_analysis` or this is a fresh start:

1. Identify the current text from manifest.json (first incomplete text)
2. Run the full analysis pipeline:
   ```bash
   # Replace {text_file} and {book_name} with actual values from manifest
   audiobook-prep analyze {text_file} --html output/{book_name}/report.html --output output/{book_name}/analysis.json
   ```

   Example for gatsby:
   ```bash
   audiobook-prep analyze Test_Texts/gatsby.txt --html output/gatsby/report.html --output output/gatsby/analysis.json
   ```

3. Wait for completion (this may take 10-60 minutes depending on text length and model)
4. Verify output exists:
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
- **Attempt:** 1 of 5
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
