# Current Evaluation State

## Active Text
- **Name:** berenice
- **Attempt:** 1
- **Phase:** awaiting_evaluation

## Output Files
- HTML: output/berenice/report.html
- JSON: output/berenice/analysis.json

## Pipeline Notes
- Analysis completed successfully in 9m 45s
- Using models from gui_settings.json:
  - Structure: qwen3:30b-instruct
  - Characters: qwen3-next:80b-a3b-instruct-q8_0
  - Summaries: qwen3-next:80b-a3b-instruct-q8_0
  - Pronunciation: qwen3:30b-instruct

## Pipeline Results
- Chapters detected: 1
- Characters extracted: 2 (Berenice, Mad'selle Salle)
- Summaries generated: 1
- Character profiles: 1
- Pronunciation flags: 112
- Total tokens: 56,146
- LLM calls: 31
- Bottleneck: Character Extraction (58.1% of time)

## Warnings/Issues During Analysis
- LLM identity detection failed with 500 error during one stage (likely a retry)
- "No valid proposals - returning single chapter" message appeared
- Text is 3,240 words (short story)
