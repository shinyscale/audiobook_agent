# Current Evaluation State

## Active Text
- **Name:** monkeys_paw
- **Attempt:** 1
- **Phase:** awaiting_evaluation
- **baseline_score:** null
- **Competitive Mode:** none

## Output Files
- HTML: ../output/monkeys_paw/report.html
- JSON: ../output/monkeys_paw/analysis.json

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | TBD | - | Baseline |

## Pipeline Notes
- Analysis completed in 28m 39s
- Found 3 chapters (correct — W.W. Jacobs story has 3 parts)
- Found 5 characters in extraction, 4 in final output (Sergeant-Major Morris dropped due to low confidence profile: 0.30)
- Pass 2 failed for Mr. White (kept without aliases)
- Failed to parse JSON response for Sergeant-Major Morris (LLM JSON parse error)
- LLM identity detection failed (returned None)
- "the monkey's paw" listed as a character with "the visitor" as an alias — "the visitor" is actually Sergeant-Major Morris, not the paw
- BLOCKED aliases: 'his wife'/'the wife' for Mrs. White (different titled people — correct block), 'the figure'/'the dead man' for Herbert White (not in summaries), 'the talisman' for monkey's paw (different core noun — correct block), 'the fakir' for 'the holy fakir' (not in summaries)
- Gutenberg boilerplate removed (46.7% of file was license text)
- 17 pronunciation entries flagged
- 1 low-confidence profile (Sergeant-Major Morris)
- Removed contradictory parent-child relationships (parent→child and child→parent both labeled "child")

## Potential Issues to Watch in Evaluation
1. Sergeant-Major Morris missing from final output (only 4 of 5 characters shown) — he is a major character in the story
2. "the visitor" incorrectly aliased to "the monkey's paw" rather than to Sergeant-Major Morris
3. Mr. White has no aliases despite being called "the old man" in text
4. Relationship labels: parent→child and child→parent both said "child" (contradictory inverse — corrected by pipeline but may indicate profile quality issues)
