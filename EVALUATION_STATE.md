# Current Evaluation State

## Active Text
- **Name:** cask_of_amontillado
- **Attempt:** 2 of 5
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

## REGRESSION DETECTED
- **Previous (Attempt 1):** 6.45/10
- **Current (Attempt 2):** 5.95/10
- **Delta:** -0.50 points

**The Attempt 2 fix made things WORSE.** The enhanced object detection heuristic in `validator.py` did NOT filter out "Amontillado" as expected. The issue persists exactly as before.

## Current Issues (Priority Order)

### CRITICAL

1. **"Amontillado" (wine) still identified as a main character**
   - Problem: The tool identified "Amontillado" (a type of sherry wine) as a main character with 16 mentions
   - Evidence: Amontillado is NOT a person. It's the wine used as bait. The title "The Cask of Amontillado" refers to a BARREL OF WINE.
   - Location: `src/pipeline/character_extraction/validator.py` - The heuristic fix from Attempt 2 is not working
   - Why Attempt 2 failed: The heuristic checks for object patterns like "a pipe of Amontillado" but spaCy's NER extracted "Amontillado" standalone, not in phrase context. The regex may not be matching correctly, OR the LLM validation is still overriding the heuristic result.
   - Fix approach: Need to trace the actual execution path. Add logging OR use a different approach entirely - check if the entity EVER performs person-like actions (speaks, thinks, moves) in the text.

2. **Montresor (actual narrator) still demoted to 1 mention**
   - Problem: Montresor is the first-person narrator and protagonist, but listed with only 1 mention
   - Evidence: The entire story is told from Montresor's perspective ("I vowed revenge", "I said", etc.). His name is only spoken once ("For the love of God, Montresor!") but HE is the narrator.
   - Location: Narrator detection is NOT connected to character extraction
   - Fix approach: First-person narrator detection needs enhancement. When a story is first-person ("I" narration) AND a character name is mentioned in dialogue addressing the narrator, that character should be flagged as the narrator with boosted mention count.

3. **Narrator still incorrectly identified as "Amontillado" in plot_summary**
   - Problem: From `overview.plot_summary`: "Amontillado, the story's first-person narrator..."
   - Evidence: Montresor is the narrator, not the wine
   - Location: `src/agents/summary_agent.py` - narrator identification
   - Fix approach: This is downstream of issue #1. If Amontillado is removed from characters, the summary won't call it the narrator.

### HIGH

4. **Luchresi still missing from character list**
   - Problem: Luchresi (rival wine expert) mentioned 6 times but not in characters
   - Evidence: Appears in pronunciation guide (6 occurrences) but not characters
   - Location: Likely filtered by mention count threshold
   - Fix approach: Lower mention threshold OR add logic to include characters mentioned by name even with low counts

### MEDIUM

5. **Montresor's profile content attributed to "Amontillado"**
   - Problem: The accurate narrator profile is assigned to wrong entity
   - Evidence: Profile says "The character is the first-person narrator" but attached to "Amontillado"
   - Fix approach: Downstream of #1

6. **~35-40% pronunciation false positives**
   - Problem: Common words like "jingled", "orbs", "leer", "filmy" flagged
   - Evidence: 56 words flagged, ~20 are standard English
   - Location: `src/agents/pronunciation_agent.py`
   - Fix approach: Common word frequency filtering (top 5000-10000 English words)

## Root Cause Analysis

### Why Attempt 2 Fix Failed

The fix in Attempt 2 added heuristics to `validator.py` to detect object patterns:
```python
# Added in Attempt 2 - lines 218-263
# Checks for patterns like "a pipe of X", "the X", "of X"
# Should have rejected "Amontillado" based on object_pattern_count
```

**Possible failure modes:**
1. The regex patterns aren't matching the actual text context
2. The heuristic runs AFTER LLM validation already accepted it
3. The mention_boost override the rejection
4. The code path isn't being executed at all

**Recommended investigation:**
- Add debug logging to see if the heuristic code is even being reached
- Print the actual object_pattern_count and person_context_count for "Amontillado"
- Verify the heuristic runs BEFORE or can override LLM acceptance

### The Core Problem

The system has TWO separate issues:

1. **Object vs Person discrimination:** NER extracts "Amontillado" as PERSON. The validator doesn't have strong enough filters to reject it. The fix needs to be MORE aggressive - perhaps checking if the entity EVER performs person-like verbs (said, thought, walked, felt) anywhere in the text.

2. **First-person narrator detection:** The narrator is implicit in first-person stories. "Montresor" appears once by name but IS the narrator. The system needs narrator-specific logic: when addressee mentions a name ("Montresor!") in dialogue with the first-person narrator, that's the narrator's identity.

## Fix History

### Attempt 2: Enhanced object/non-person entity filtering (FAILED - REGRESSION)
**Date:** 2026-01-18
**Modified:** `src/pipeline/character_extraction/validator.py`
**Result:** Score dropped from 6.45 to 5.95 (-0.50 points)
**Why it failed:** The heuristic either isn't executing or isn't strong enough to override other signals

## Next Action

**REVERT Attempt 2 changes** (score regressed beyond 0.3 threshold), then:

1. **Diagnose why the fix didn't work:**
   - Add temporary debug logging to trace "Amontillado" through validation
   - Check if heuristic code is being reached
   - Check actual pattern match counts

2. **Stronger object detection:**
   - Instead of pattern matching, scan full text for person-like verbs near the entity name
   - If entity NEVER speaks, thinks, or performs actions → reject as character

3. **First-person narrator detection:**
   - Detect first-person narrative ("I" as subject)
   - Find dialogue addressing narrator ("For the love of God, [NAME]!")
   - That name = narrator identity, boost mention count to reflect "I" instances
