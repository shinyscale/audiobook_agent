# Current Evaluation State

## Active Text
- **Name:** masque_of_red_death
- **Attempt:** 2
- **Phase:** awaiting_evaluation
- **baseline_score:** 7.25
- **Competitive Mode:** multi

## Latest Scores
- Structure Detection: 9/10
- Character Extraction: 5/10 ← CRITICAL ISSUES
- Character Profiles: 6/10
- Chapter Summaries: 9/10
- Pronunciation Guide: 6/10
- HTML Presentation: 9/10
- **Overall: 7.25/10** (threshold: 8.0)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 7.25 | - | Character fragmentation, pronunciation false positives |

## Current Issues (Priority Order)

### CRITICAL

1. **Character fragmentation: masked figure duplicated**
   - Problem: "masked figure" (ID: `main_cast_2`, 8 mentions) and "the masked figure" (ID: `ca1c816399e5`, 1 mention) are listed as separate character entries
   - Evidence: These clearly refer to the same entity - the mysterious intruder at the masquerade
   - Location: The hash ID `ca1c816399e5` indicates F6 Summary Reconciliation (analyzer.py:1220-1240) created the duplicate during summary-to-character reconciliation
   - Fix: Improve deduplication logic to recognize "the X" and "X" as the same entity; normalize articles before comparison

2. **Character conceptual split: Red Death vs masked figure**
   - Problem: "the Red Death" (ID: `main_cast_1`) is listed as a separate character from "masked figure" (ID: `main_cast_2`), but in the story these are the SAME ENTITY revealed at the climax
   - Evidence: Poe writes "And now was acknowledged the presence of the Red Death" when the masked figure's identity is revealed - the masked figure IS the Red Death personified
   - Location: Main cast pipeline (`src/pipeline/character_extraction_v2/main_cast.py`) - created separate entries
   - Note: The "masked figure" entry correctly has "Red Death" as an alias, but the reverse merge didn't happen
   - Fix: This requires understanding character identity revelations - the system should recognize that when X is revealed to be Y, they should be merged

### HIGH

3. **Excessive pronunciation false positives**
   - Problem: Common English words flagged unnecessarily: "Death", "figure", "masked", "intruder", "chiming", "light-hearted", "magnificence", "evolutions", "dauntless"
   - Evidence: 72 pronunciation flags for a ~2,500 word story (nearly 3% flagged) is excessive for a narrator
   - Location: `src/pipeline/pronunciation/` - word filtering logic
   - Fix: Add frequency-based filtering using common word lists, or raise the threshold for what constitutes an "unusual" word

### MEDIUM

4. **Missing character profile structured data**
   - Problem: `physical_description` and `relationships` fields are empty (null) for all 4 character entries
   - Evidence: Sanity check shows 0/4 characters with physical_description, 0/4 with relationships
   - Note: Descriptions DO appear in the HTML table as prose, so the data exists somewhere but isn't in structured fields
   - Location: Profile enrichment stage - may be a field mapping issue
   - Fix: Verify profile enrichment populates the correct fields in the Character model

### LOW

5. **Structure title field is null**
   - Problem: The single structure element has `title: null` when it could capture "The Masque of the Red Death"
   - Evidence: Story title is clearly identifiable from the document
   - Location: Structure detection pipeline
   - Fix: Extract title from document metadata or first lines for short stories

## Output Files
- HTML: ../output/masque_of_red_death/report.html
- JSON: ../output/masque_of_red_death/analysis.json

## Pipeline Notes
Analysis completed in 25m 7s (Attempt 2).

Key observations:
- Found 4 characters: Prince Prospero, the Red Death, the courtiers, the musicians
- 69 pronunciation flags (63 unknown, 4 homograph, 2 proper_noun)
- Warning persists: "Early narrator detection failed: 'Character' object has no attribute 'descriptions'"
- Multi-model competitive consensus used for characters, structure, summaries stages

## Fix History

### Attempt 2 Fixes

1. **Character fragmentation (Critical #1)** - Fixed article normalization in F6 reconciliation
   - Root cause: `analyzer.py:1236-1266` - `_normalize_name_for_matching()` stripped titles but not articles ("the ", "a ", "an ")
   - Smoke test: PASS - "masked figure" and "the masked figure" now normalize to the same string
   - Modified: `src/analyzer.py`

2. **Character merge logic (Critical #2)** - Added alias-based deduplication
   - Root cause: `main_cast.py:1041-1162` - `merge_descriptive_entities()` only used semantic clusters, missed alias-based matches
   - Fix: If Profile A has alias "X" and Profile B has canonical "X" or "the X", they now merge
   - Smoke test: PASS - "masked figure" (alias: "Red Death") now merges with "the Red Death"
   - Modified: `src/pipeline/character_extraction_v2/main_cast.py`

3. **Pronunciation false positives (High #3)** - Skip word-splitting for descriptive character handles
   - Root cause: `character_proposer.py:54-102` - split all character names into words, flagging common words
   - Fix: Detect descriptive handles (names starting with articles or all-lowercase) and skip word-splitting
   - Smoke test: PASS - "the Red Death" and "masked figure" no longer flag individual words
   - Modified: `src/pipeline/pronunciation_guide/proposers/character_proposer.py`

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 2 | Critical #1: Article normalization | analyzer.py | Smoke test PASS |
| 2 | Critical #2: Alias-based merge | main_cast.py | Smoke test PASS |
| 2 | High #3: Descriptive handle filtering | character_proposer.py | Smoke test PASS |

## Next Action
Re-run analysis to verify fixes (Phase: awaiting_analysis)
