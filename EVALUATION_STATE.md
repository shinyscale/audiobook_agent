# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 1 of 5
- **Phase:** awaiting_evaluation

## Output Files
- HTML: output/gatsby/report.html
- JSON: output/gatsby/analysis.json
- Quality Report: output/gatsby_20260117_184020/quality.md

## Latest Scores
- Structure Detection: -/10
- Character Extraction: -/10
- Character Profiles: -/10
- Chapter Summaries: -/10
- Pronunciation Guide: -/10
- HTML Presentation: -/10
- **Overall: -/10** (threshold: 8.0)

## Current Issues (Priority Order)

### CRITICAL
(Awaiting evaluation)

### HIGH
(Awaiting evaluation)

### MEDIUM
(Awaiting evaluation)

### LOW
(Awaiting evaluation)

## Pipeline Notes (Attempt 1)
- Analysis completed in 103m 27s
- Total tokens: 666,252
- Detected 7 chapters (57 characters, 628 pronunciation flags)
- Warnings during run:
  - TOC validation: 87 entries detected but likely includes page numbers
  - StructureAgent: 3-4 errors found (refinement not yet implemented)
  - Multiple JSON parsing failures for character profiles (Gatsby, Myrtle, Michaelis, Sloane, Catherine, the butler)
  - Low confidence (0.30) profiles for several characters
  - Moral valence classification failed for Tom, Daisy, Wilson
  - LLM batch enrichment failed: failed to parse JSON
  - Narrator 'Nick Carraway' not found initially (later confirmed)
- Quality concerns: 6 low-confidence character profiles
- Bottleneck: Character Extraction (38.0% of time)

## Fix History
(No fixes yet - this is the first analysis)

## Next Action
Run PROMPT_evaluate.md to evaluate the analysis output
