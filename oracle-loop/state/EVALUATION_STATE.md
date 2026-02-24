# Current Evaluation State

## Active Text
- **Name:** flowers_for_algernon
- **Attempt:** 1
- **Phase:** awaiting_fix
- **baseline_score:** null
- **Competitive Mode:** single

## Output Files
- HTML: ../output/flowers_for_algernon/report.html
- JSON: ../output/flowers_for_algernon/analysis.json

## Pipeline Notes
- **CRITICAL FAILURE:** `Flowers_For_Algernon.pdf` is a scanned/image-based PDF
- ALL 23 pages returned: "No text extracted (contains images, may need OCR)"
- Result: 0 words extracted, 0 characters found, 0 chapters (fell back to 1)
- The pipeline completed without crashing but produced empty/useless output
- Pipeline recommended: `--pdf-ocr` flag for OCR fallback

## Error
```
⚠️  Page 1-23: No text extracted (contains images, may need OCR)
⚠️  Low text extraction rate (0%). Consider using --pdf-ocr for OCR fallback.
Extracted 0 words
Found 1 chapters (fallback)
Found 0 characters
```

## Fix Options
1. **Use `--pdf-ocr` flag** if the pipeline supports it (check CLI for this option)
2. **Replace the PDF** with a text-extractable version of Flowers for Algernon
3. **Skip this text** and update manifest to mark as skipped/problematic

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | FAIL | - | Image-based PDF — 0 words extracted, requires OCR |
