# Current Evaluation State

## Active Text
- **Name:** monkeys_paw
- **Attempt:** 1
- **Phase:** awaiting_fix
- **baseline_score:** 7.4

## Output Files
- HTML: ../output/monkeys_paw/report.html
- JSON: ../output/monkeys_paw/analysis.json

## Latest Scores
- Structure Detection: 3/10 ✗ (CRITICAL FAILURE)
- Character Extraction: 9/10 ✓
- Character Profiles: 6/10 ✗ (FAILING)
- Chapter Summaries: 8/10 ✓
- Pronunciation Guide: 9/10 ✓
- HTML Presentation: 9/10 ✓
- **Overall: 7.4/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold)

## Current Issues (Priority Order)

### CRITICAL
1. **Structure Detection: Missed 2 of 3 parts (I., II., III.)**
   - Problem: The source text has three clearly marked parts: "I." (line 45), "II." (line 284), "III." (line 411). Only 1 chapter was detected.
   - Evidence: `jq '.structure | length'` returns 1. Source text has `grep -En "^I\.|^II\.|^III\."` returning 3 matches.
   - Impact: 67% of structure missed. Score: 3/10
   - Location: `src/pipeline/chapter_detection/proposers/llm.py` - Roman numeral marker detection
   - Root Cause: The MARKER_SYSTEM_PROMPT regex patterns may not match single Roman numeral patterns like "I." followed by newline. Current patterns expect "Chapter" or "CHAPTER" prefix.
   - Fix: Add Roman numeral standalone patterns to marker detection: `^(I|II|III|IV|V|VI|VII|VIII|IX|X)\.?\s*$`

### HIGH
2. **Character Profiles: Sergeant-Major Morris missing physical description**
   - Problem: Morris is described as "a tall, burly man, beady of eye and rubicund of visage" in the text, but his profile has `appearance: null`, `personality: null`, `voice_guidance: null`
   - Evidence: `jq '.characters[] | select(.canonical_name | contains("Morris")) | .appearance'` returns `null`
   - Impact: Missing key profile data for a significant character. Narrator needs to know Morris is tall and burly.
   - Location: `src/pipeline/character_profiling/` - Profile extraction likely filtered Morris due to low mention count (5)
   - Fix: Ensure profile extraction runs for all main_cast characters regardless of mention count, or lower threshold for short stories

3. **Character Profiles: Mrs. White has incomplete profile**
   - Problem: Mrs. White (protagonist's spouse, 10 mentions) has `appearance: null`, `personality: null`, `voice_guidance: null`
   - Evidence: `jq '.characters[1]'` shows null fields
   - Impact: Missing profile for major character
   - Location: Same as above

### MEDIUM
4. **Herbert White role incorrectly listed as "supporting"**
   - Problem: Herbert is central to the story (his death and resurrection attempt drive the entire plot). He has 15 mentions and should be "protagonist" or at least "major".
   - Evidence: `jq '.characters[2].role'` returns "supporting"
   - Impact: Minor - doesn't affect narrator preparation significantly
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` - role assignment logic

5. **No narrator identified**
   - Problem: `is_narrator: false` for all characters. This is correct for third-person narrative but `narrative_style: "unknown"` in structure suggests the system didn't confidently identify the POV.
   - Evidence: Overview shows `narrative_style: "third-person omniscient"` in plot_summary but `narrative_style: "unknown"` in structure
   - Impact: Minor inconsistency
   - Location: `src/pipeline/chapter_detection/` or structure agent

### LOW
6. **Some profile relationships using odd values**
   - Problem: Mrs. White has `"Herbert White": "mother"` (should be "son" from her perspective)
   - Evidence: Relationship value represents her role, not Herbert's
   - Impact: Confusing but minor
   - Location: `src/pipeline/character_profiling/` relationship extraction

## Analysis Details

### Structure (3/10)
The text clearly has three parts marked with Roman numerals (I., II., III.), each representing a distinct time period and dramatic arc:
- Part I: Morris arrives, brings the paw, Mr. White makes first wish
- Part II: Next morning, Herbert goes to work, stranger brings news of death and £200 compensation
- Part III: Burial, Mrs. White demands second wish, knocking at door, third wish

Only detecting 1 chapter means a narrator would have no sense of this structure. This is a critical failure.

### Characters (9/10)
All expected characters present:
- Mr. White (protagonist) ✓
- Mrs. White ✓
- Herbert White ✓
- Sergeant-Major Morris ✓
- The stranger/company rep ✓
- The monkey's paw (symbolic object) ✓

No false splits or merges. The monkey's paw is correctly identified as an antagonist/symbolic force. Good aliases detected (Herbert = "the son", the paw = "the paw").

### Profiles (6/10)
- Mr. White: Full profile with appearance, personality, voice_guidance ✓
- Herbert White: Partial profile (personality, some appearance) ✓
- The monkey's paw: Good symbolic description ✓
- Mrs. White: Missing all profile data ✗
- Sergeant-Major Morris: Missing all profile data despite clear text description ✗
- Stranger: Missing (acceptable - very minor character)

Only 2/5 significant characters have usable profiles.

### Summaries (8/10)
The single summary is comprehensive and accurate, covering all major events from all three parts. It correctly captures:
- Chess game opening
- Morris's arrival with the paw
- First wish for £200
- Herbert's death notification
- £200 compensation
- Second wish for Herbert's return
- Knocking at door
- Third wish

The summary is actually too comprehensive - it covers events that would be in Parts II and III if structure was detected. For a narrator, having one summary for the whole story works, but loses the per-part breakdown.

### Pronunciation (9/10)
Excellent coverage:
- 34/37 entries have IPA
- Key words flagged: "fakir", "rubicund", "Meggins", "condoling"
- Proper nouns: Herbert, Morris
- Period spelling: "to-night"
- Some minor false positives like "out-of-the-way" but harmless

### Presentation (9/10)
HTML report is functional with proper navigation, character lists, and pronunciation guide. Structure section is limited due to detection failure but presents what was found correctly.

## Fix History
(First attempt - no prior fixes)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | (initial evaluation) | N/A | Baseline scores established |

## Configuration Audit

### Model Used
- gpt-oss:120b (via Ollama) for all stages

### Issues Noted
- 7 LLM calls for structure detection but only 1 chapter found with medium confidence
- No JSON parse failures or retries, suggesting the LLM is responding correctly but the prompts aren't matching Roman numeral patterns

## Next Action
Run PROMPT_fix.md to address Critical #1: Add Roman numeral standalone pattern detection to chapter marker system
