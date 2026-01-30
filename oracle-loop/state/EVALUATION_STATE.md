# Current Evaluation State

## Active Text
- **Name:** i_have_no_mouth
- **Attempt:** 1
- **Phase:** awaiting_evaluation
- **baseline_score:** null
- **Competitive Mode:** single

## Latest Scores
(Awaiting first analysis)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| (none yet) | - | - | - |

## Notes
Starting analysis for i_have_no_mouth with JSON-compatible model (qwen2.5:32b-instruct-q8_0).

### Fixes Applied Before This Run

**1. Non-Human Entity Examples (Summarizer Prompts)**
- File: `src/pipeline/chapter_summary/summarizer.py`
- Changed JSON examples from `["Michael", "Sarah", "Dr. Patterson"]` to `["Michael", "Sarah", "HAL", "the Monster"]`
- Added guidance note about including AI systems, creatures, supernatural beings in active_characters
- Expected impact: AM (sentient supercomputer) should now appear in `characters_present`

**2. JSON-Capable Model Fallback**
- Files: `src/agents/config.py`, `src/analyzer.py`, `src/agents/characters.py`, `src/pipeline/character_extraction_v2/main_cast.py`, `src/pipeline/chapter_summary/summarizer.py`, `src/cli.py`
- Added `--json-model` CLI flag for user-configurable JSON fallback
- Not used in this run since primary model is JSON-compatible

**3. Model Configuration Update**
- File: `~/.config/audiobook_prep/gui_settings.json`
- Changed from: `qwen3-next:80b-a3b-instruct-q8_0` (JSON incompatible)
- Changed to: `qwen2.5:32b-instruct-q8_0` (JSON compatible)
- Expected impact: Main cast extraction should succeed, Ted identified as narrator

### Expected Outcomes
- AM in character list (non-human entity fix)
- Ted marked as narrator with correct mention count (main cast extraction working)
- Character Extraction: 5/10 → 8+/10
- Overall score: 7.5/10 → 8+/10 (PASS threshold)

## Configuration Notes
- Model: qwen2.5:32b-instruct-q8_0 (JSON compatible)
- Competitive Mode: single (same model, 3 temperatures)
- Competitive Stages: characters, structure, summaries

## Output Files
- HTML: ../output/i_have_no_mouth/report.html
- JSON: ../output/i_have_no_mouth/analysis.json

## Pipeline Notes
- Analysis completed in 39m 22s
- Characters found: 6 (Benny, Ellen, Gorrister, Nimdok, Ted, +1 more)
- Ted detected as first-person narrator
- 1 chapter detected
- Warnings: "Narrator 'Ted' identified but NOT found in main_cast" (may indicate main cast extraction issue)
- Warnings: "LLM marker proposer returned non-list: <class 'dict'>" (structure detection format issue)
- Pronunciation flags: 56 words
