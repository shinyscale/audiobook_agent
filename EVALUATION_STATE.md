# Current Evaluation State

## Active Text
- **Name:** cask_of_amontillado
- **Attempt:** 1
- **Phase:** awaiting_fix
- **baseline_score:** 6.10

## Latest Scores
- Structure Detection: 9/10
- Character Extraction: 4/10 ← CRITICAL FAILURE
- Character Profiles: 4/10 ← CRITICAL FAILURE
- Chapter Summaries: 6/10
- Pronunciation Guide: 7/10
- HTML Presentation: 8/10
- **Overall: 6.10/10** (threshold: 8.0)

## Current Issues (Priority Order)

### CRITICAL

1. **"Amontillado" (a wine) is listed as a character**
   - Problem: The analysis created a character entry for "Amontillado" which is the Spanish sherry wine, NOT a person
   - Evidence: `characters[0].canonical_name` = "Amontillado" with 16 mentions
   - The description text is actually describing Montresor (the narrator) but attributed to the wine name
   - Location: Likely `src/pipeline/character_extraction/` - NER or LLM extraction is treating the title word as a character
   - Root cause: The word "Amontillado" appears frequently in the text (34 times) as part of dialogue about the wine, and the system incorrectly identified it as a character name
   - Fix approach: Add filtering to exclude common nouns/objects that appear in titles from character extraction, or improve the LLM prompt to distinguish between characters and objects

2. **Montresor NOT identified as narrator**
   - Problem: `is_narrator: false` for Montresor, but he IS the first-person narrator
   - Evidence: The story opens with "I had borne as I best could" and continues in first person throughout
   - The `plot_summary` incorrectly calls the narrator "Amontillado" instead of Montresor
   - Location: Likely `src/agents/summary_agent.py` or narrator detection logic
   - Fix approach: Narrator detection should look for first-person pronouns and identify which character uses "I"

3. **Montresor has NO profile content**
   - Problem: Montresor has zero descriptions, zero evidence, zero personality/voice guidance
   - Evidence: `characters[2]` (Montresor) has empty `descriptions`, `relationships`, `evidence` arrays
   - Only 1 mention_count when he should be the most mentioned character (as the narrator)
   - Location: Character extraction is failing to associate the narrator's actions with Montresor
   - Fix approach: Improve narrator-to-character linking - when a character is identified as narrator, their profile should be built from all first-person statements

### HIGH

4. **Luchresi missing from character list**
   - Problem: Luchresi is mentioned 6 times by name but not included in characters
   - Evidence: He appears in dialogue as a rival wine expert that Montresor uses to manipulate Fortunato
   - Location: Character extraction may be filtering by mention count or missing this name
   - Fix approach: Lower threshold or improve detection - he's clearly a named character

5. **Plot summary uses "Amontillado" as narrator name**
   - Problem: The `overview.plot_summary.plot_summary` field repeatedly says "Amontillado recounts..." and "Amontillado leads Fortunato..."
   - Evidence: This is a downstream effect of issue #1 - the summary agent used the wrong character as narrator
   - Location: `src/agents/summary_agent.py`
   - Fix approach: Fixing issue #1 and #2 should cascade to fix this

### MEDIUM

6. **Some pronunciation false positives**
   - Problem: Common words like "jingled", "filmy", "orbs", "leer" flagged unnecessarily
   - Evidence: 56 total pronunciations flagged, some are common English words
   - Location: `src/pipeline/pronunciation/` or pronunciation agent
   - Fix approach: Add word frequency filtering (as noted in ATTEMPT_1_SUMMARY.md)

7. **"Medoc" not flagged for pronunciation**
   - Problem: French wine region name not in pronunciation guide
   - Evidence: Appears in text ("a draught of the Medoc", "My own fancy grew warm with the Medoc")
   - Location: Pronunciation detection
   - Fix approach: Minor - improve foreign word detection

## Fix History
- (First attempt - no prior fixes)

## Next Action
**Phase:** awaiting_fix

Priority fix order:
1. Fix the "Amontillado as character" bug - this is the root cause of multiple issues
2. Fix narrator detection to properly identify Montresor
3. Ensure character profiles are generated for all characters including the narrator

The most impactful single fix would be preventing non-person entities (like the wine name from the title) from being extracted as characters. This would likely improve the score significantly by fixing issues #1, #2, #3, and #5 simultaneously.
