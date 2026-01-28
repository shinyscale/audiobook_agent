# Current Evaluation State

## Active Text
- **Name:** masque_of_red_death
- **Attempt:** 2
- **Phase:** awaiting_fix
- **baseline_score:** 7.52
- **Competitive Mode:** single

## Output Files
- HTML: ../output/masque_of_red_death/report.html
- JSON: ../output/masque_of_red_death/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 6/10 ✗ (FAILING)
- Character Profiles: 7.5/10 ✗ (FAILING)
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 9/10 ✓
- **Overall: 7.88/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 7.52 | 0.00 | Initial baseline - character extraction issues |
| 2 | 7.88 | +0.36 | Partial fix - courtiers separated, but ebony clock/narrator still aliases |

## Score Breakdown

### Structure Detection: 9/10 ✓
**Good:**
- Correctly identified this is a single continuous narrative without chapters
- Single structure element with complete text coverage (28-13811 positions)
- Word count accurate (2,443 words)

**Minor:**
- Title is null (could extract "The Masque of the Red Death" from the text header)

### Character Extraction: 6/10 ✗
**Improvement from Attempt 1:**
- "the courtiers" is now a separate character entry, NOT an alias of "the Red Death" ✓

**Remaining Issues:**
1. **FALSE ALIAS: "the ebony clock"** - The ebony clock is a physical object (a giant clock in the black chamber). It is NOT the Red Death. This is a semantically unrelated noun.
2. **FALSE ALIAS: "the narrator"** - This is a third-person narrated story. "The narrator" refers to the storytelling voice, NOT the personified disease. This is completely wrong.
3. **"the masked figure" still separate** - This character IS the Red Death in disguise. The story explicitly reveals this at the climax. However, with only 1 mention, this is a minor issue.

**Characters Detected:** 6 total
- Prince Prospero (main_cast_0) - CORRECT ✓
- the Red Death (main_cast_1) - Has wrong aliases: "ebony clock", "narrator" ✗
- the courtiers (F6 reconciled) - Now separate, CORRECT ✓
- the musicians (F6 reconciled) - Minor character, acceptable
- the waltzers (F6 reconciled) - Minor character, acceptable
- the masked figure (F6 reconciled) - Should be alias of Red Death, but low impact

**Why 6/10:** The fix removed one false alias but added a new one ("the narrator"). The core issue persists: semantically unrelated nouns are being merged as aliases of "the Red Death". The coherence check needs to be more aggressive.

### Character Profiles: 7.5/10 ✗
**Improvement from Attempt 1:**
- "the Red Death" now has rich `appearance` data with distinguishing features:
  - "vesture dabbled in blood"
  - "broad brow besprinkled with scarlet horror"
  - "corpse-like mask"
  - "grave cerements"
- Personality data is present for both main characters

**Remaining Issues:**
1. **Prince Prospero has unknown appearance** - Despite being described as "happy and dauntless and sagacious" (personality, not appearance), his physical presence is never described, so this is actually correct.
2. **All relationships still empty** - Clear narrative relationships exist:
   - Prospero → courtiers (master/protector)
   - Prospero → Red Death (victim/antagonist)
3. **"the masked figure" has null profile** - Expected for 1-mention F6 reconciled character

**Why 7.5/10:** Major improvement in appearance data extraction. The empty relationships are the main gap now.

### Chapter Summaries: 9/10 ✓
**Excellent:**
- Summary is comprehensive (182 words in structure, 3-paragraph narrative summary in overview)
- Captures all major story beats accurately:
  - The Red Death plague devastating the country
  - Prospero's retreat with 1000 courtiers
  - The seven colored rooms and the masked ball
  - The ebony clock's chilling effect
  - The appearance of the masked figure
  - The confrontation and Prospero's death
  - The revelation that the figure was empty
  - The death of all guests

**Minor:**
- Characters present list includes "the courtiers" which is now a separate character (acceptable, not an error)

### Pronunciation Guide: 8/10 ✓
**Good:**
- 45 pronunciation entries flagged
- 41/45 have IPA (91% coverage)
- Important terms correctly flagged: Prospero, improvisatori, castellated, arabesque
- IPA quality is good (/prəˈspɛr.oʊ/ for Prospero is correct)
- Notes field provides helpful narrator guidance

**Issues:**
- `term` and `category` fields are null for all entries (structural issue, low impact)
- 4 entries missing IPA

### HTML Presentation: 9/10 ✓
**Good:**
- Clean, professional dark theme
- Tab navigation works correctly
- 8 sections organized logically
- Sticky navigation bar
- Summary/overview is well-written and engaging
- Character profiles display correctly with expandable details

## Current Issues (Priority Order)

### CRITICAL
1. **FALSE ALIAS: "the ebony clock" merged with "the Red Death"**
   - Problem: The Red Death has aliases ["the ebony clock", "the narrator"]
   - Evidence: The ebony clock is a massive clock in the black chamber that chimes hourly, causing revelers to stop dancing. It is a PHYSICAL OBJECT, not the personified plague.
   - ID: main_cast_1 (from main cast pipeline)
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` - verify_aliases semantic coherence check
   - Why fix didn't work: The fix added detection for personified concepts (death, plague, etc.) but "ebony clock" somehow still passed. Need to investigate why.
   - Verification: `jq '.characters[] | select(.canonical_name == "the Red Death") | .aliases' ../output/masque_of_red_death/analysis.json`

2. **FALSE ALIAS: "the narrator" merged with "the Red Death"**
   - Problem: "the narrator" is listed as an alias of "the Red Death"
   - Evidence: This is a third-person narrated story. The narrator is the storytelling voice, NOT the plague. There's no in-story narrator as a character.
   - ID: main_cast_1
   - Location: Same as above
   - Fix: The semantic coherence check should reject "narrator" as it has no semantic relationship to "death/plague/Red Death"
   - Note: This may be a NEW regression - attempt 1 had ["the ebony clock", "the courtiers"] not ["the ebony clock", "the narrator"]

### HIGH
3. **Relationships empty for all characters**
   - Problem: All characters have `relationships: {}`
   - Evidence: Clear narrative relationships exist:
     - Prospero leads/protects the courtiers
     - Red Death destroys/kills Prospero
   - Location: Character profile enrichment stage (F4 or profile sampling)
   - Fix: Profile enrichment needs to extract relationships from context

### MEDIUM
4. **Pronunciation entries missing `term` field**
   - Problem: All pronunciations have `word` but `term` is null
   - Example: `{"term": null, "ipa": "/prəˈspɛroʊ/", "word": "Prospero"}`
   - Location: Pronunciation pipeline output format
   - Fix: Ensure `term` is populated (may be field name mismatch)

### LOW
5. **"the masked figure" could be alias of Red Death**
   - Problem: Listed as separate character with 1 mention
   - Evidence: Story reveals masked figure IS the Red Death
   - Reason to defer: Only 1 mention, complex narrative-reveal logic required
   - Impact: <0.5 points

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | (initial analysis) | - | Character extraction: 5/10, Profiles: 6/10 |
| 2 | Critical: False aliases on Red Death | src/pipeline/character_extraction_v2/main_cast.py | **Partial** - "courtiers" removed, but "ebony clock" persists and "narrator" added |
| 3 | Critical: False aliases "ebony clock" and "narrator" | src/pipeline/character_extraction_v2/main_cast.py | **Pending verification** - Added hard programmatic blocks for meta-references and object keywords |

## Fix Analysis - Attempt 2 Result

### What the fix did:
- Extended semantic coherence check to detect personified concepts (death, plague, fear, etc.)
- Should block semantically unrelated aliases like "ebony clock" (core noun: "clock")

### What actually happened:
- "the courtiers" was REMOVED as an alias ✓
- "the ebony clock" STILL present as an alias ✗
- "the narrator" is a NEW false alias ✗

### Hypothesis for failure:
1. The semantic coherence check may be running AFTER alias assignment, not blocking the merge
2. The "personified concept" detection may only check the canonical name, not each alias candidate
3. There may be multiple paths for alias addition (Pass 1, Pass 2, F6 reconciliation) and only one is filtered

### Next fix should:
1. Add debug logging to verify_aliases to see what's being blocked vs allowed
2. Ensure the coherence check runs on EVERY proposed alias before merging
3. Add explicit rejection of "narrator" as an alias for any character (narrators are metadata, not characters in most cases)

## Notes
The fix for cask_of_amontillado's semantic coherence check worked there but has partial/inconsistent results on this text. The issue is that different alias sources (main cast Pass 2, F6 reconciliation) may not all be subject to the same filtering.

The "the narrator" alias is particularly problematic because:
1. This story has no character narrator (third-person omniscient)
2. Even if there were a narrator, they wouldn't be "the Red Death"
3. This suggests the LLM is hallucinating this merge, and the coherence check isn't catching it

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (appropriate for this text size)
- Context: 32768 (sufficient)
- Temperature: 0.7 (standard)
- Profiling shows 0 low confidence items, 0 retries (good)

## Fix Applied - Attempt 3

### Root Cause
- **Location:** `src/pipeline/character_extraction_v2/main_cast.py:verify_aliases()`
- **Problem:** LLM in Pass 2 proposes invalid aliases ("ebony clock", "narrator"), and the existing semantic coherence check had gaps
- **Why semantic check failed:** The check only handles substring/plural relationships, not categorical filtering (objects vs characters, meta-references)

### Fix Implemented
Added two **programmatic hard blocks** in verify_aliases() (RULE 0.4 and RULE 0.45):

1. **Meta-reference block:** Blocks "narrator", "the narrator", "reader", "audience" as aliases
   - These are storytelling devices, never character references
   - Universal rule: applies to any text

2. **Object keyword block:** Blocks aliases containing object keywords (clock, door, mirror, etc.) when canonical name doesn't
   - Prevents physical objects from becoming aliases of characters
   - Allows symbolic objects IF they're the canonical name (e.g., "the monkey's paw")

### Smoke Test Results
**PASS** - Tested with "the Red Death" having aliases ["the ebony clock", "the narrator", "Death", "the Red Death itself"]:
- ✓ "the ebony clock" BLOCKED (object keyword: clock)
- ✓ "the narrator" BLOCKED (meta-reference)
- ✓ "Death" ALLOWED (valid alias)
- ✓ "the Red Death itself" ALLOWED (valid alias)

### Expected Outcome
Character extraction should improve from 6/10 to 8+/10 by eliminating the two false aliases.

## Next Action
**Phase:** awaiting_analysis

Re-run analysis to verify fix effectiveness.
