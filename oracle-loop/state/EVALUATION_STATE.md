# Current Evaluation State

## Active Text
- **Name:** frankenstein
- **Attempt:** 1
- **Phase:** awaiting_evaluation
- **baseline_score:** null
- **Competitive Mode:** none

## Output Files
- HTML: ../output/frankenstein/report.html
- JSON: ../output/frankenstein/analysis.json
- Generated: 2026-03-11 10:54 (runtime ~101 minutes)

## Pipeline Notes
- 28 chapters detected (TOC had 31 entries but only 27 boundaries found — 4 missed)
- 21 characters in output (24 from extraction + 3 added by F6 reconciliation)
- 20 profiles generated
- 219 pronunciation flags (159 unknown, 30 proper_noun, 15 foreign, 15 homograph)
- Narrator correctly identified as Robert Walton (frame narrator) ✓
- Victor is correctly non-narrator (71 mentions, subject of novel)
- "LLM marker proposer returned non-list: <class 'dict'>" — 30 warnings (structure proposer returning dict instead of list)
- "TOC enforcement: Only 27 total boundaries found but TOC expects 31" — some chapters may be missing
- "StructureAgent: 1 errors found but refinement not yet implemented" — minor
- Several "Removing contradictory relationship" entries:
  - Robert Walton↔Victor 'confidant' removed (symmetric non-asymmetric label)
  - Victor↔Alphonse 'parent' removed (both labeled parent — wrong)
  - Victor↔the creature 'creator' removed (both labeled creator — wrong)
  - Victor↔Caroline 'parent' removed (both labeled parent — wrong)
- Creature alias fragmentation: "the creature", "the fiend", "the daemon", "the dæmon", "the monster", "the wretch", "the demon", "the being" are ALL the same entity but person/non-person mismatch rules split them
- "the old man (De Lacey)" — parenthetical in canonical name causes parsing issues
- Ollama JSON array validation errors for pronunciation (LLM returning objects instead of arrays; retried multiple times)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| (none yet) | - | - | - |
