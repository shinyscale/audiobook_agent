# Current Evaluation State

## Active Text
- **Name:** masque_of_red_death
- **Attempt:** 1
- **Phase:** awaiting_fix
- **baseline_score:** 6.75

## Latest Scores
- Structure Detection: 10/10
- Character Extraction: 5/10 <- FAILING
- Character Profiles: 2/10 <- FAILING (cascading from character extraction)
- Chapter Summaries: 9/10
- Pronunciation Guide: 5/10 <- FAILING
- HTML Presentation: 9/10
- **Overall: 6.75/10** (threshold: 8.0)

## Current Issues (Priority Order)

### CRITICAL
1. **Prince Prospero mention count severely undercounted**
   - Problem: JSON shows 3 mentions but text has ~15+ references ("Prince Prospero", "the prince", "Prospero", "the duke")
   - Evidence: Text contains "Prince Prospero" (5+ times), "the prince" (multiple), "Prospero" alone (multiple), "the duke" (1+ time)
   - Location: `src/agents/character_agent.py` or `src/pipeline/character_extraction.py` - mention counting logic
   - Impact: Causes cascading failure - characters appear to have too few mentions, preventing profile generation
   - Fix: Ensure alias-aware mention counting includes all variant references

2. **No character profiles generated**
   - Problem: Report shows "Generated 0 character profiles (both characters below minimum mention threshold)"
   - Evidence: Prince Prospero is the PROTAGONIST of a 2,400-word story - should absolutely have a profile
   - Location: Profile generation threshold logic in `src/agents/` or profiling pipeline
   - Root cause: Mention count underestimation (Issue #1)
   - Fix: After fixing mention counts, profiles should generate. May also need to lower threshold for short stories.

3. **"the" flagged as a proper noun with 263 occurrences**
   - Problem: The definite article "the" is incorrectly listed in pronunciation guide as a proper noun
   - Evidence: Appears as first entry in Proper Nouns section of pronunciation guide
   - Location: `src/pipeline/pronunciation.py` or NER extraction - improper filtering of common words
   - Fix: Add exclusion list for common English articles (the, a, an) or improve proper noun detection logic

### HIGH
4. **Missing alias resolution for Prince Prospero**
   - Problem: "Prince Prospero", "the prince", "the duke", "Prospero" should all be aliases
   - Evidence: Text says "the duke's love of the bizarre" referring to same person as "Prince Prospero"
   - Location: `src/agents/character_agent.py` - alias resolution logic
   - Fix: Improve alias grouping to link titled references ("the prince", "the duke") with proper names

5. **Missing alias resolution for the mummer/Red Death figure**
   - Problem: "the mummer", "the figure", "the masked figure", "the intruder", "the stranger" should be grouped
   - Evidence: All these terms refer to the personified Red Death
   - Location: Same as above - alias resolution
   - Fix: Improve detection of definite article + noun phrases referring to same entity

6. **"away" incorrectly flagged as foreign word**
   - Problem: Common English word "away" is listed in Foreign Words section
   - Evidence: "away" is not a foreign word in any context
   - Location: `src/pipeline/pronunciation.py` - foreign word detection
   - Fix: Improve foreign word detection or add common word exclusion

### MEDIUM
7. **No IPA provided for any pronunciation entry**
   - Problem: All 75 entries have `ipa: null`
   - Evidence: Useful words like "improvisatori", "Prospero", "cerements" should have IPA
   - Location: Pronunciation pipeline - IPA generation stage
   - Fix: Enable/configure IPA generation, may need LLM call or dictionary lookup

8. **Too many common words in pronunciation guide**
   - Problem: 65 words in "Other" category including common words like "chiming", "evolutions", "dauntless"
   - Evidence: These are standard English words that don't need pronunciation help
   - Location: Pronunciation flagging logic
   - Fix: Improve filtering to focus on truly unusual words

9. **Themes are weak/generic**
   - Problem: Listed themes "identity, ambition, loss" miss the core allegory
   - Evidence: Central themes are: mortality, inevitability of death, hubris, wealth's impotence against death
   - Location: Summary/theme extraction
   - Fix: Low priority - themes are supplementary information

### LOW
10. **Timing table shows spurious rows**
    - Problem: "started_at" and "ended_at" rows in timing table have empty duration values
    - Location: HTML template formatting
    - Fix: Filter out non-duration timing entries from table display

11. **Main Characters stat shows 0**
    - Problem: Overview card shows "0 Main Characters" which is misleading
    - Evidence: Prince Prospero is the main character
    - Root cause: Cascading from mention count issue
    - Fix: Will resolve when character extraction is fixed

## Fix History
(First attempt - no previous fixes)

## Next Action
Run PROMPT_fix.md to address:
1. Character mention counting (Critical #1)
2. "the" proper noun false positive (Critical #3)
3. These two fixes should cascade to improve Character Profiles score and overall score

## Estimated Impact of Fixes
- Fixing mention counting + aliases: Characters 5->8, Profiles 2->7
- Fixing "the" false positive + filtering: Pronunciation 5->7
- Projected score after fixes: ~7.8-8.2
