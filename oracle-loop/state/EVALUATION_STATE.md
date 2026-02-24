# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 1
- **Phase:** awaiting_analysis
- **baseline_score:** null
- **Competitive Mode:** single

## Output Files
- HTML: ../output/gatsby/report.html
- JSON: ../output/gatsby/analysis.json

## Latest Scores
(Awaiting first analysis)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| (none yet) | - | - | - |

## Notes
Starting analysis for gatsby.

## Fix History

### flowers_for_algernon — Deferred (image-based PDF, no OCR available)
- **Issue:** Flowers_For_Algernon.pdf is a scanned/image-based PDF — 0 words extracted
- **Root cause:** Missing system dependency: tesseract-ocr (required by ocrmypdf / pytesseract)
- **Action:** Moved flowers_for_algernon to the END of manifest.texts so the loop continues with
  text-extractable books (gatsby, frankenstein, dracula, etc.) first
- **Resolution:** When tesseract is installed (`sudo apt install tesseract-ocr && pip install ocrmypdf`),
  flowers_for_algernon will be re-attempted. The manifest entry has a `note` field documenting this.
- **Modified:** oracle-loop/state/manifest.json (reordered texts array)
