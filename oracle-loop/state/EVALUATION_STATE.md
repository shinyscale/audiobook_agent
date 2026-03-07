# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 1
- **Phase:** awaiting_evaluation
- **baseline_score:** null
- **Competitive Mode:** none

## Output Files
- HTML: ../output/gatsby/report.html
- JSON: ../output/gatsby/analysis.json

## Latest Scores
(Awaiting evaluation)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| (none yet) | - | - | - |

## Notes
Analysis complete (89m 16s, 303 LLM calls, 643K tokens).

### Pipeline Stats
- 51,257 words extracted; 9 chapters detected (correct)
- 32 characters found (24 from extraction + 12 added by F6)
- 150 pronunciation flags

### Known Issues (Pre-Evaluation)

**CRITICAL - False narrator:**
- V2 pipeline identified `Doctor T. J. Eckleburg` as narrator (a billboard advertisement character, NOT a person)
- Nick Carraway is the actual first-person narrator of The Great Gatsby
- Line 129: "Narrator (from V2 pipeline): Doctor T. J. Eckleburg"
- Line 137: "Narrator already identified by V2 pipeline: Doctor T. J. Eckleburg (skipping re-detection)"
- Line 145: "No definitive narrator identified from plot summary" (finalizing step also failed)

**SIGNIFICANT - James Gatz alias blocked:**
- Line 26: "BLOCKED alias: 'James Gatz' and 'Jay Gatsby' appear in summaries but NEVER co-occur in the same chapter and have no name overlap"
- James Gatz IS Jay Gatsby's real birth name — this is a key identity reveal in the novel
- Co-occurrence check blocks it because Gatsby's real name is only revealed in one chapter (Ch 6)

**MINOR - Odd alias for Tom Buchanan:**
- "the Buchanans' house" listed as alias for Tom Buchanan (should not be an alias)

**MINOR - Pronunciation json_mode errors:**
- Model refused to invent IPA for obscure proper nouns (Croirier, Vladmir, Chrysties)
- 116 of 150 flags have MEDIUM confidence (model preamble/refusal in json_mode validation)

### Character Summary (key characters)
- Nick Carraway (aka Nick, Carraway) - 34 mentions — narrator, but NOT tagged as such
- Daisy Buchanan (aka Daisy, Daisy Fay) - 208 mentions
- Tom Buchanan (aka Tom, the Buchanans' house) - 198 mentions
- Jordan Baker (aka Jordan, Baker) - 101 mentions
- Myrtle Wilson (aka Myrtle, the woman) - 30 mentions
