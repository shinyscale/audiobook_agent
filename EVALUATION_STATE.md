# Current Evaluation State

## Active Text
- **Name:** masque_of_red_death
- **Attempt:** 2
- **Phase:** awaiting_fix
- **baseline_score:** 6.75

## Latest Scores
- Structure Detection: 10/10
- Character Extraction: 5/10 ← FAILING
- Character Profiles: 2/10 ← FAILING (cascading from character extraction)
- Chapter Summaries: 9/10
- Pronunciation Guide: 6/10 ← IMPROVED (was 5)
- HTML Presentation: 8/10
- **Overall: 6.75/10** (threshold: 8.0)

## Score Delta from Attempt 1
- Structure: 10 → 10 (unchanged)
- Characters: 5 → 5 (unchanged)
- Profiles: 2 → 2 (unchanged)
- Summaries: 9 → 9 (unchanged)
- Pronunciation: 5 → 6 (+1 - "the" no longer flagged)
- Presentation: 9 → 8 (-1 - noticed timing table issues)
- **Overall: 6.75 → 6.75 (unchanged)**

## Fix Assessment from Attempt 1

### Fix 1: Cross-group epithet-to-proper-name resolution
**Status: DID NOT WORK**
- **Expected:** "the prince", "the duke" merged into "Prince Prospero", mention count ~15+
- **Actual:** "the Prince Prospero" still shows only 3 mentions, no aliases
- **Evidence:** Pronunciation guide shows "Prospero" with 18 occurrences, "Prince" with 9 occurrences, but character only has 3 mentions
- **Root cause:** The cross-group resolution was added but either:
  1. Not being called in the execution path
  2. Failing to find cross-group matches
  3. Not updating mention counts after merging

### Fix 2: Add articles to pronunciation whitelist
**Status: PARTIALLY WORKED**
- **Expected:** "the" removed from pronunciation guide
- **Actual:** ✅ "the" is no longer in the pronunciation guide
- **Remaining issue:** "away" is still flagged as a foreign word (not covered by article fix)

## Current Issues (Priority Order)

### CRITICAL
1. **Character mention counts are NOT using alias-aware counting**
   - Problem: "the Prince Prospero" shows 3 mentions, but the text contains:
     - "Prince Prospero" (5+ times)
     - "Prospero" alone (18 times per pronunciation guide)
     - "Prince" as title (9 times)
     - "the prince" (multiple times)
     - "the duke" (at least once - "the duke's love of the bizarre")
   - Evidence: Character shows 3 mentions while pronunciation shows 18 "Prospero" occurrences
   - Root cause: The mention count is counting exact matches of "the Prince Prospero" rather than any reference to the character
   - Location: `src/pipeline/character_extraction/consensus.py` - mention counting in `build_consensus()` or wherever mention_count is calculated
   - Impact: Characters appear to have too few mentions → profiles not generated → cascading failure
   - Fix approach: After building alias groups, recalculate mention_count as sum of all alias mention counts

2. **No character profiles generated (0 profiles)**
   - Problem: Report shows "Generated 0 character profiles (both characters below minimum mention threshold)"
   - Evidence: Prince Prospero is the PROTAGONIST of a 2,400-word story - he absolutely needs a profile
   - Root cause: Cascading from Issue #1 - mention counts are too low
   - Secondary cause: Profile threshold may be too high for short stories
   - Location: Profile generation threshold in `src/agents/` or profiling pipeline
   - Fix approach:
     1. First fix mention counting (Issue #1)
     2. Consider lowering profile threshold for short texts (<5000 words)

### HIGH
3. **No aliases recorded for either character**
   - Problem: Both characters show "—" for aliases despite clear alias relationships:
     - Prince Prospero = Prospero = the prince = the duke
     - the mummer = the figure = the masked figure = the intruder = the stranger = Red Death
   - Evidence: All these terms appear in the text referring to the same characters
   - Location: `src/pipeline/character_extraction/consensus.py` - alias resolution
   - Root cause: The cross-group resolution may be running but not populating the aliases list
   - Fix: Ensure aliases are populated when characters are merged across groups

4. **"away" incorrectly flagged as foreign word**
   - Problem: Common English word "away" is listed in Foreign Words section with note: "Note: 'away' is not German, but the context may suggest a foreign tone"
   - Evidence: "away" is a standard English word, not foreign
   - Location: `src/pipeline/pronunciation_guide/` - foreign word detection logic
   - Fix: Improve foreign word detection or add more common words to exclusion list

### MEDIUM
5. **Canonical name format includes leading article**
   - Problem: Character name is "the Prince Prospero" instead of "Prince Prospero"
   - Evidence: Leading "the" is awkward and non-standard
   - Location: Character name normalization logic
   - Fix: Strip leading articles from canonical names

6. **Too many common words in pronunciation guide (65 in "Other")**
   - Problem: Common words like "dauntless", "chiming", "evolutions", "girdled", "provisioned" are flagged
   - Evidence: These are standard English words that most narrators would know
   - Location: Pronunciation flagging threshold/filtering
   - Fix: Add word frequency filtering using a common English word list (top 5000 words)

7. **Generic themes miss the allegorical nature**
   - Problem: Listed themes "identity, ambition, loss" are generic
   - Actual themes: mortality, inevitability of death, hubris, wealth's impotence against death, denial of mortality
   - Location: Theme extraction in summary pipeline
   - Fix: Low priority - themes are supplementary

### LOW
8. **Timing table formatting issues**
   - Problem: "started_at" and "ended_at" rows show empty duration values
   - Problem: "4m 60s" should display as "5m 0s"
   - Location: HTML template timing table generation
   - Fix: Filter out timestamp entries, fix duration formatting

## Fix History

### Attempt 1 Fixes Applied
1. **Cross-group epithet resolution** (consensus.py) - Did not produce expected results
2. **Article filtering for pronunciation** (cmu_proposer.py) - Partially worked ("the" removed)

## Next Action
Run PROMPT_fix.md to address mention counting (Critical #1) - this is the root cause of both the character extraction and profile generation failures.

## Key Insight for Fix Phase
The pronunciation guide shows:
- "Prospero": 18 occurrences
- "Prince": 9 occurrences

But the character "the Prince Prospero" only shows 3 mentions.

This proves the mention counting is NOT aggregating across aliases. The character extraction is finding the references (otherwise pronunciation couldn't count them), but the final character object is not getting the aggregated count.

**Data flow to investigate:**
1. Where does `mention_count` get set on the Character object?
2. Is it before or after alias merging?
3. Are alias mention counts being summed into the primary character?
