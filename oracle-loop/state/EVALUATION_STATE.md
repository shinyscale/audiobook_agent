# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 1
- **Phase:** awaiting_evaluation
- **baseline_score:** null
- **Competitive Mode:** single

## Output Files
- HTML: ../output/gatsby/report.html
- JSON: ../output/gatsby/analysis.json

## Latest Scores
(Awaiting evaluation)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| (none yet) | - | - | - |

## Pipeline Notes
- Analysis completed in 100m 6s
- 9 chapters detected
- 22 characters extracted (25 found, some merged)
- 134 pronunciation flags
- Key character: Jay Gatsby (aka Gatsby, James Gatz) - 275 mentions
- Warnings:
  - "LLM marker proposer returned non-list: dict" (20x) — structure agent response parsing issue
  - "Two-pass extraction returned 0 characters; retrying with single-pass" — character extraction fallback triggered
  - "V2 Step 3.1 FALLBACK: main_cast empty after grounding" — simplified prompt fallback used
  - "Narrator 'Nick Carraway' identified but NOT found in main_cast" — resolved on second pass
  - LLM timeout on Jay Gatsby profile (attempt 1/3) — retried and succeeded
  - Various pronunciation JSON format errors (model returned objects not arrays)

## Fix History

### flowers_for_algernon — Deferred (image-based PDF, no OCR available)
- **Issue:** Flowers_For_Algernon.pdf is a scanned/image-based PDF — 0 words extracted
- **Root cause:** Missing system dependency: tesseract-ocr (required by ocrmypdf / pytesseract)
- **Action:** Moved flowers_for_algernon to the END of manifest.texts so the loop continues with
  text-extractable books (gatsby, frankenstein, dracula, etc.) first
- **Resolution:** When tesseract is installed (`sudo apt install tesseract-ocr && pip install ocrmypdf`),
  flowers_for_algernon will be re-attempted. The manifest entry has a `note` field documenting this.
- **Modified:** oracle-loop/state/manifest.json (reordered texts array)
