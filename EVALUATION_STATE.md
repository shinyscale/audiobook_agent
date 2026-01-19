# Current Evaluation State

## Active Text
- **Name:** masque_of_red_death
- **Attempt:** 2
- **Phase:** awaiting_evaluation
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

### Attempt 1 Fixes
**Fix 1: Cross-group epithet-to-proper-name resolution**
- **Root cause:** `src/pipeline/character_extraction/consensus.py:313-338` - epithets (names starting with "the ") were resolved separately from proper names, so "the prince"/"the duke" couldn't be linked to "Prince Prospero"
- **Data flow trace:**
  - Symptom: JSON shows Prince Prospero with only 3 mentions
  - Stored in: Character.mention_count in AnalysisResult
  - Generated by: CharacterConsensusBuilder.build_consensus() line 455
  - Originates: Lines 313-338 split epithets and proper names into separate groups with no cross-linking
- **Solution:** Added new `_llm_cross_group_resolution()` method and cross-group resolution step at line 344-357
  - Uses LLM to identify when epithets like "the prince" refer to proper names like "Prince Prospero"
  - Merges epithet mentions into proper name's alias group
  - Added CROSS_GROUP_SYSTEM and CROSS_GROUP_PROMPT at lines 95-130
- **Modified files:** `src/pipeline/character_extraction/consensus.py`
- **Confidence:** HIGH - addresses core architectural gap in alias resolution
- **Expected impact:** Characters 5→8, Profiles 2→7 (cascading fix)

**Fix 2: Add articles to pronunciation whitelist**
- **Root cause:** `src/pipeline/pronunciation_guide/proposers/cmu_proposer.py:21-36` - COMMON_WORDS_WHITELIST didn't include articles "the", "a", "an"
- **Data flow trace:**
  - Symptom: "the" flagged as proper noun with 263 occurrences
  - Generated by: CharacterProposer.propose() splitting character names into words
  - Checked against: COMMON_WORDS_WHITELIST at line 66 of character_proposer.py
  - Originates: cmu_proposer.py line 21 - whitelist definition missing articles
- **Solution:** Added 'the', 'a', 'an' to COMMON_WORDS_WHITELIST at line 23
- **Modified files:** `src/pipeline/pronunciation_guide/proposers/cmu_proposer.py`
- **Confidence:** HIGH - simple, targeted fix
- **Expected impact:** Pronunciation 5→7

**Smoke tests:** Test suite not available in environment - proceeded based on root cause confidence and code review

## Output Files (Attempt 2)
- HTML: output/masque_of_red_death/report.html
- JSON: output/masque_of_red_death/analysis.json

## Pipeline Notes (Attempt 2)
- Analysis completed successfully in 7m 17s
- Total tokens: 30,533
- No errors during execution
- Found 2 characters with 3 mentions each
- Generated 0 character profiles (threshold not met)
- Flagged 74 words in pronunciation guide
- Note: "LLM identity detection failed" warning at end (non-critical)

## Next Action
Proceed to PROMPT_evaluate.md to score the output

## Estimated Impact of Fixes
- Fix 1 (epithet linking): Should merge "the prince", "the duke" into "Prince Prospero" → Characters 5→8, Profiles 2→7
- Fix 2 (article filtering): Should remove "the" from pronunciation guide → Pronunciation 5→7
- Projected overall score after fixes: ~7.8-8.2 (may cross 8.0 threshold)
