# Current Evaluation State

## Active Text
- **Name:** cask_of_amontillado
- **Attempt:** 1 of 5
- **Phase:** awaiting_fix
- **baseline_score:** 6.45

## Output Files
- HTML: output/cask_of_amontillado/report.html
- JSON: output/cask_of_amontillado/analysis.json

## Latest Scores
- Structure Detection: 10/10
- Character Extraction: 2/10 ← CRITICAL FAILURE
- Character Profiles: 3/10 ← CRITICAL FAILURE
- Chapter Summaries: 9/10
- Pronunciation Guide: 8/10
- HTML Presentation: 9/10
- **Overall: 6.45/10** (threshold: 8.0)

## Current Issues (Priority Order)

### CRITICAL

1. **"Amontillado" (wine) identified as a main character**
   - Problem: The tool identified "Amontillado" (a type of sherry wine) as a main character with 16 mentions
   - Evidence: Amontillado is the wine used as bait to lure Fortunato - it's a thing, not a person. The word appears in the title "The Cask of Amontillado" and throughout as the object of Fortunato's desire.
   - Location: Likely `src/pipeline/character_extraction/` - NER is extracting the wine name as a character
   - Fix approach: The NER/character extraction needs to filter out non-person entities. "Amontillado" is tagged with proper noun mentions but it's never used with person-context verbs (doesn't speak, act, etc.)

2. **Montresor (actual narrator) demoted to "Supporting Character" with 1 mention**
   - Problem: Montresor is the first-person narrator and protagonist, but he's listed as a supporting character with only 1 mention
   - Evidence: The entire story is told from Montresor's perspective ("I vowed revenge", "I said", etc.). His name is only spoken once aloud ("For the love of God, Montresor!") but he IS the narrator.
   - Location: `src/pipeline/character_extraction/` and narrator detection logic
   - Fix approach: First-person narrators who are named characters need special handling. When a name appears in first-person narration context AND the narrator voice uses "I", that character should be flagged as potential narrator with high mention count.

3. **Narrator incorrectly identified as "Amontillado"**
   - Problem: The plot summary identifies the narrator as "Amontillado" instead of Montresor
   - Evidence: From overview.plot_summary: "Amontillado, the story's first-person narrator..."
   - Location: `src/agents/summary_agent.py` or narrator detection in character profiles
   - Fix approach: The narrator identification relies on character extraction. Once issue #1 is fixed, this should resolve.

### HIGH

4. **Luchresi missing from character list**
   - Problem: Luchresi (a rival wine connoisseur mentioned 6 times) is not in the character list
   - Evidence: He appears in pronunciation guide (6 occurrences) but not characters. He's mentioned as someone Fortunato competes with.
   - Location: Likely filtered by mention count threshold or role classification
   - Fix approach: Characters mentioned by name 6 times should be included as minor characters

### MEDIUM

5. **Profile content attributed to wrong entity**
   - Problem: The accurate Montresor profile ("calculated and vengeful individual") is attributed to "Amontillado"
   - Evidence: The profile describes the narrator accurately but is attached to the wine name
   - Location: This is a downstream effect of issue #1
   - Fix approach: Will resolve when character extraction is fixed

6. **Some common English words in pronunciation guide**
   - Problem: Words like "jingled", "orbs", "leer", "filmy" are flagged as pronunciation concerns
   - Evidence: These are standard English words that don't need special attention
   - Location: `src/agents/pronunciation_agent.py` or filtering logic
   - Fix approach: Add common word filtering (these appear in top 10,000 English words)

### LOW

7. **Latin motto split into separate entries**
   - Problem: "Nemo me impune lacessit" appears as separate words (impune, lacessit) rather than as a phrase
   - Evidence: The Montresor family motto should be treated as a unit
   - Location: Pronunciation detection
   - Fix approach: Detect multi-word foreign phrases

## Root Cause Analysis

The core issue is that NER is extracting "Amontillado" as a proper noun entity and the character extraction pipeline has no validation to distinguish between:
1. Person names (Montresor, Fortunato, Luchresi)
2. Object names (Amontillado - the wine)
3. Place names (the catacombs)

The validation should check:
- Does this entity perform actions (speak, move, think)?
- Is this entity referred to with person pronouns (he/she/they)?
- Does this entity appear in dialogue attribution?

For "Amontillado":
- Never speaks or acts
- Never uses person pronouns
- Appears only as object of desire ("a pipe of Amontillado", "the cask of Amontillado")

## Fix History
None - this is the first attempt

## Next Action
Run PROMPT_fix.md to address character extraction issues:
1. Filter non-person entities (objects, places) from character list
2. Improve narrator detection for first-person stories where narrator is named
3. Ensure named characters with 5+ mentions are included in character list
