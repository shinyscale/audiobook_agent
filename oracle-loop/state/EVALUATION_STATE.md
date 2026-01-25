# Current Evaluation State

## Active Text
- **Name:** cask_of_amontillado
- **Attempt:** 2
- **Phase:** awaiting_evaluation
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

## Pipeline Notes (Attempt 2)
- Completed successfully in 18m 10s
- Multi-model competitive consensus enabled (3 models: qwen3:30b, deepseek-r1:32b, gemma3:27b)
- Competitive stages: characters, structure, summaries
- **Montresor detected!** Narrator confirmed as first-person
- 3 characters found (up from 2 in attempt 1)
- 1 character added from chapter summaries (likely Montresor)
- Warning: "Early narrator detection failed: 'Character' object has no attribute 'descriptions'" (non-fatal)
- Warning: "LLM batch enrichment failed: failed to parse JSON" (non-fatal)

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
| 2 | Missing Montresor (CRITICAL #1, #2) | `src/pipeline/chapter_summary/summarizer.py` | Pending re-analysis |

## Fix History

### Attempt 2: Fixed summary anonymization of first-person narrators

**Root Cause Analysis (COMPLETE):**
- **Symptom:** Montresor (narrator/protagonist) not in character list
- **Data flow trace:**
  1. Montresor appears in pronunciation guide (NER found it in raw text: 3 mentions)
  2. Montresor missing from character list
  3. Main cast extraction (V2) reads FROM SUMMARIES, not raw text
  4. **Root cause found in:** `src/pipeline/chapter_summary/summarizer.py` prompts
- **Root cause:** Summary generator anonymized the narrator as "the narrator" instead of using "Montresor"
  - Main cast LLM correctly followed Rule 14 and created character "the narrator"
  - Grounding gate searched for "the narrator" in raw text → 0 matches (word "narrator" never appears)
  - With 0 < min_mentions (3), "the narrator" was filtered as ungrounded/hallucinated
  - Meanwhile "Montresor" appears 3x in text but never in summary, so V2 never extracted it
- **Confidence:** HIGH

**Fix Applied:**
- Modified: `src/pipeline/chapter_summary/summarizer.py`
- Updated `CHUNK_SUMMARY_PROMPT` and `CONSOLIDATE_PROMPT` to add:
  > **FIRST-PERSON NARRATORS**: If the text is told in first person ("I", "we") and the narrator's name is revealed in the text (e.g., another character addresses them by name, or they introduce themselves), USE THAT NAME in your summary instead of "the narrator". Only use "the narrator" if their name is not revealed in this section.

**Expected Impact:**
- Should fix CRITICAL #1 (missing Montresor)
- Should fix CRITICAL #2 (no narrator identified) - Montresor will be extracted and narrator detection can match them
- May improve HIGH #4 (Fortunato labeled antagonist) - once Montresor is present, role assignment may be more accurate

**Smoke Test:** Unable to run full pipeline smoke test due to model config. Verified prompt changes applied correctly. Ready for full re-analysis.

## Next Action
Re-run analysis to verify fix (set phase to `awaiting_analysis`)
