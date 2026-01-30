# Current Evaluation State

## Active Text
- **Name:** i_have_no_mouth
- **Attempt:** 1
- **Phase:** awaiting_evaluation
- **baseline_score:** null
- **Competitive Mode:** single

## Output Files
- HTML: ../output/i_have_no_mouth/report.html
- JSON: ../output/i_have_no_mouth/analysis.json

## Pipeline Notes

**Analysis completed in 16m40s**

**Structure Detection Warnings:**
- LLM marker proposer returned non-list (dict instead) - 3 attempts
- Defaulted to single chapter detection
- This is a short story, so single chapter is likely correct

**Quality Metrics:**
- Total LLM calls: 76
- Total tokens: 76,451
- Bottleneck: Character Profiles (45.7% of time)

**Results Summary:**
- Duration: 36 minutes (5,789 words)
- Chapters: 1
- Characters: 6 (Benny, Ellen, Gorrister, Nimdok, Ted, + 1 more)
- Pronunciation flags: 56 (42 unknown, 6 proper_noun, 6 homograph, 2 foreign)
- Warnings: Removed repeating header, rejoined 47 split words at line breaks

**Competitive Consensus:**
- Mode: single (same model, 3 temperatures)
- Stages: characters, structure, summaries (all enabled via --competitive-all)
