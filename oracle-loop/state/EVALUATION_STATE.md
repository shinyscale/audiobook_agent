# Current Evaluation State

## Active Text
- **Name:** cask_of_amontillado
- **Attempt:** 1
- **Phase:** awaiting_fix
- **baseline_score:** 7.1
- **Competitive Mode:** multi

## Latest Scores
- Structure Detection: 8/10
- Character Extraction: 5/10 ← CRITICAL FAILURE
- Character Profiles: 5/10 ← CRITICAL FAILURE (missing protagonist)
- Chapter Summaries: 9/10
- Pronunciation Guide: 8/10
- HTML Presentation: 9/10
- **Overall: 7.1/10** (threshold: 8.0)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 7.1 | - | Baseline. Missing Montresor (narrator/protagonist) |

## Output Files
- HTML: ../output/cask_of_amontillado/report.html
- JSON: ../output/cask_of_amontillado/analysis.json

## Current Issues (Priority Order)

### CRITICAL
1. **Missing protagonist: Montresor**
   - Problem: The narrator and protagonist of the story is not in the character list
   - Evidence: The text contains "For the love of God, Montresor!" (Fortunato's plea) and "the catacombs of the Montresors" - the name appears explicitly
   - Current output: Only Fortunato (14 mentions) and Luchresi (4 mentions) are detected
   - Location: V2 character extraction pipeline (`src/pipeline/character_extraction_v2/`)
   - ID pattern: Need to check if Montresor was extracted then filtered, or never detected
   - Fix approach:
     1. Check if "Montresor" is being filtered by mention count threshold (appears ~5 times)
     2. First-person narrator detection should identify the "I" narrator and link to Montresor
     3. The pronunciation pipeline DID find "Montresor" and "Montresors" - so NER may have found it but character pipeline filtered it

2. **No narrator identified**
   - Problem: `is_narrator: false` for all characters; this is a first-person narrative
   - Evidence: Story opens with "THE thousand injuries of Fortunato I had borne" - clear first-person "I" narrator
   - Location: Narrator detection in `src/pipeline/character_extraction_v2/` or `src/analyzer.py`
   - Fix approach: First-person narrator detection should flag Montresor as narrator when the name is discovered

### HIGH
3. **Fortunato's physical description missing**
   - Problem: Physical description shows "unknown" but text explicitly describes him
   - Evidence: Text says "The man wore motley. He had on a tight-fitting parti-striped dress, and his head was surmounted by the conical cap and bells."
   - Location: Profile population stage in character extraction
   - Fix approach: Ensure physical descriptions are extracted from text evidence during profile building

4. **Fortunato incorrectly tagged as "antagonist"**
   - Problem: Fortunato is labeled as "antagonist" but he's actually the victim
   - Evidence: In the story, Montresor (the narrator) is the villain seeking revenge; Fortunato is the unsuspecting victim
   - Location: Role/tag assignment in character profiles
   - Fix approach: For first-person revenge narratives, the victim shouldn't be auto-tagged as antagonist

### MEDIUM
5. **Structure metadata fields are null**
   - Problem: `title`, `start_line`, `end_line` are all null for the single structure element
   - Evidence: `jq '.structure[]' analysis.json` shows all nulls
   - Location: Structure detection stage
   - Fix approach: For short stories, populate title from filename or extract from text header

### LOW
6. **Minor pronunciation false positives**
   - Problem: Common words "use", "close", "entrance" flagged (could be homographs but not in this context)
   - Evidence: These appear in pronunciation list but don't need special narrator guidance
   - Location: Pronunciation filtering stage
   - Fix approach: Add homograph context checking or increase threshold for common words

## Configuration Notes

From `_config`:
- Model: qwen2.5:32b (appropriate)
- `character_llm_chunk_chars`: 5000 (reasonable for short story)
- No obvious config issues causing the problems

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | (baseline) | - | 7.1/10 |

## Root Cause Analysis

The critical issue is that **Montresor is detected by NER** (appears in pronunciation guide) but **not included in character output**. This suggests:

1. The name was found during extraction but filtered out
2. Possible causes:
   - Mention count threshold too high (Montresor appears ~5 times vs Fortunato's 14)
   - First-person narrator "I" not being linked to the discovered name
   - Character confidence scoring filtered it out

Investigation needed in fix phase:
- Check `src/pipeline/character_extraction_v2/main_cast.py` for filtering thresholds
- Check narrator detection logic in analyzer.py
- Check if there's a minimum mention count that's excluding Montresor

## Next Action
Run PROMPT_fix.md to address Critical #1 (missing Montresor) - this single fix could resolve issues #1, #2, and potentially #4.
