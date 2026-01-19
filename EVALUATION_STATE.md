# Current Evaluation State

## Active Text
- **Name:** cask_of_amontillado
- **Attempt:** 7
- **Phase:** awaiting_fix
- **baseline_score:** 6.45

## Output Files
- HTML: output/cask_of_amontillado/report.html
- JSON: output/cask_of_amontillado/analysis.json

## Latest Scores
- Structure Detection: 10/10
- Character Extraction: 2/10 ← CRITICAL FAILURE
- Character Profiles: 3/10 ← CRITICAL FAILURE
- Chapter Summaries: 7/10
- Pronunciation Guide: 7/10
- HTML Presentation: 9/10
- **Overall: 5.95/10** (threshold: 8.0)

## Score History
| Attempt | Score | Delta | Notes |
|---------|-------|-------|-------|
| 1 (baseline) | 6.45 | - | Initial run |
| 2 | 5.95 | -0.50 | Object detection heuristic failed, REVERTED |
| 3 | 5.95 | 0.00 | Person-action verb detection added |
| 4 | - | - | Fixed JSON format parsing for LLM validation |
| 5 | - | - | Pipeline error (empty array from LLM) |
| 6 | - | - | Pipeline issues |
| 7 | 5.95 | 0.00 | Pipeline completed, same issues persist |

## Current Issues (Priority Order)

### CRITICAL

1. **"Amontillado" (wine) falsely identified as main character with 16 mentions**
   - Problem: The tool identified "Amontillado" - a type of dry sherry wine - as the main character and narrator
   - Evidence: Amontillado is NOT a person. The title "The Cask of Amontillado" refers to a BARREL OF WINE used as bait to lure Fortunato
   - Root cause: spaCy NER extracts "Amontillado" as a proper noun. The heuristics in validator.py (person-action detection, object-pattern detection) are NOT successfully filtering it out
   - Why fixes failed: Multiple attempts to add heuristics have not worked:
     - Attempt 2: Object pattern detection (e.g., "a pipe of Amontillado") - didn't match contexts
     - Attempt 3: Person-action verb detection - Amontillado doesn't perform actions but still passes validation
   - The LLM validation is accepting "Amontillado" as a valid character
   - **NEW APPROACH NEEDED**: The issue is that wine references like "The Amontillado!" (exclamation about the wine) are being counted as "mentions" of a character. Need to:
     a) Check if entity is EVER the grammatical subject of a verb (not just object)
     b) Check if entity appears in dialogue quotes where it's being addressed
     c) Add a blacklist of common nouns that appear as proper nouns (wines, places, objects)

2. **Montresor (actual narrator/protagonist) has only 1 mention and is demoted to "supporting character"**
   - Problem: Montresor tells the entire story in first person ("I vowed revenge", "I said", etc.) but is listed with only 1 mention
   - Evidence: His name appears once in dialogue: "For the love of God, Montresor!" - this is Fortunato addressing him
   - Root cause: First-person narrator detection is not connected to character mention counting
   - Fix approach: When a first-person narrative is detected AND a name is spoken in dialogue addressing the narrator (second-person direct address), that character should be:
     a) Identified as the narrator
     b) Given a boosted mention count representing all first-person pronouns
     c) Moved to main characters

3. **Narrator incorrectly identified as "Amontillado" in plot_summary**
   - Problem: Overview plot_summary states "Amontillado recounts the chilling tale..."
   - Evidence: Montresor is the narrator. The wine does not narrate anything.
   - Location: src/agents/summary_agent.py - narrator identification
   - This is downstream of issue #1. If Amontillado is rejected as a character, it won't be used as narrator.

### HIGH

4. **Luchresi missing from character list**
   - Problem: Luchresi (wine connoisseur rival) is mentioned 6 times by name but not in characters
   - Evidence: He appears in the pronunciation guide with 6 occurrences
   - Location: Character extraction mention count threshold
   - Fix: Lower threshold or add named character detection regardless of count

### MEDIUM

5. **Narrator profile content assigned to wrong entity**
   - Problem: The accurate description of the first-person narrator is attached to "Amontillado"
   - Evidence: Profile says "The character is the first-person narrator" but attached to the wine
   - Fix: Downstream of #1 - fix character identification first

6. **~40% pronunciation false positives**
   - Problem: Common English words flagged (jingled, orbs, leer, filmy, recoiling, etc.)
   - Evidence: 56 words flagged, ~20-25 are standard English vocabulary
   - Location: src/agents/pronunciation_agent.py
   - Fix: Add common word frequency filtering (top 5000-10000 English words)

## Root Cause Analysis - Why 7 Attempts Have Not Fixed This

### The Core Problem

The character extraction system has **three layers of validation**:
1. **spaCy NER extraction** - extracts "Amontillado" as PERSON entity
2. **Heuristic validation** - attempts to filter non-persons
3. **LLM validation** - final decision on entity validity

**The heuristics are not working because:**

1. **Object pattern detection** (Attempt 2): Looks for "a pipe of Amontillado" patterns, but the actual mentions often use just "The Amontillado!" or "Amontillado!" as exclamations, which don't match the object patterns.

2. **Person-action detection** (Attempt 3): Checks if entity performs person-like actions (speaks, walks, thinks). But the check is looking for "{name} {verb}" patterns like "Amontillado said". The wine never has this pattern, BUT it's still being passed through because the heuristic only rejects entities with 5+ mentions AND 0 dialogue tags AND 0 person-actions. The issue may be:
   - The heuristic isn't being reached (code path issue)
   - The rejection criteria are still not strict enough
   - LLM validation overrides the heuristic rejection

**The LLM validation is likely accepting "Amontillado" because:**
- The context includes phrases like "The Amontillado!" which sounds like a character being named
- Without understanding the story, an LLM might interpret "Amontillado" as a valid name
- The prompt may not give enough context about what the entity actually IS in the text

### What Hasn't Been Tried

1. **Semantic role analysis**: Check if entity is EVER the grammatical SUBJECT (not object) of an action verb
2. **Named entity type verification**: Ask LLM "Is 'Amontillado' a person, place, thing, or concept?" before asking "Is it a character?"
3. **Common noun blacklist**: Maintain a list of nouns that commonly appear capitalized but aren't people (wines, brands, places)
4. **Context analysis for narrator detection**: Check if entity is addressed in second-person within dialogue ("For the love of God, Montresor!") to identify narrator

## Fix History

### Attempt 7: Pipeline completed, awaiting fix
**Date:** 2026-01-18
**Result:** Pipeline ran successfully but same issues persist
**Score:** 5.95/10 (no change from attempt 3)

### Attempt 4-6: Infrastructure fixes
- Fixed LLM validation JSON format parsing
- Handled empty array responses from LLM
- Pipeline stability improvements

### Attempt 3: Person-action verb detection
**Date:** 2026-01-18
**Modified:** src/pipeline/character_extraction/validator.py (lines 212-241)
**Result:** Added but did not filter out Amontillado
**Score:** 5.95/10

### Attempt 2: Enhanced object/non-person entity filtering (REVERTED)
**Date:** 2026-01-18
**Modified:** src/pipeline/character_extraction/validator.py
**Result:** Regression - score dropped from 6.45 to 5.95
**Status:** REVERTED

### Attempt 1: Baseline
**Score:** 6.45/10

## Next Action

**Run PROMPT_fix.md** to address:

1. **Priority 1**: Implement semantic role analysis - check if "Amontillado" is EVER the grammatical subject of an action verb. Wine is always an OBJECT ("received a pipe of Amontillado", "tasting the Amontillado") never a SUBJECT doing things.

2. **Priority 2**: Enhance narrator detection - when detecting a first-person narrative, search for dialogue where someone addresses the narrator by name. Pattern: `"..., {Name}!"` or `"{Name}!"` inside quotes = likely narrator's name.

3. **Priority 3**: Lower character mention threshold to include Luchresi (6 mentions).

**NOTE**: After 7 attempts on this text, consider whether to:
- Continue with targeted fixes
- Skip to next text and return later
- Investigate if the LLM model choice affects results
