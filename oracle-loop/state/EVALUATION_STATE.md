# Current Evaluation State

## Active Text
- **Name:** masque_of_red_death
- **Attempt:** 3
- **Phase:** awaiting_fix
- **baseline_score:** 7.52
- **Competitive Mode:** single

## Output Files
- HTML: ../output/masque_of_red_death/report.html
- JSON: ../output/masque_of_red_death/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 7/10 ✗ (FAILING)
- Character Profiles: 7.5/10 ✗ (FAILING)
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 9/10 ✓
- **Overall: 8.03/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 7.52 | 0.00 | Initial baseline - character extraction issues |
| 2 | 7.88 | +0.36 | Partial fix - courtiers separated, but ebony clock/narrator still aliases |
| 3 | 8.03 | +0.51 | Improvement - "narrator" removed, but "ebony clock" persists |

## Score Breakdown

### Structure Detection: 9/10 ✓
**Good:**
- Correctly identified this is a single continuous narrative without chapters
- Single structure element with complete text coverage
- Word count accurate (2,443 words)

**Minor:**
- Title is null (could extract "The Masque of the Red Death" from text header)

### Character Extraction: 7/10 ✗
**Improvement from Attempt 2:**
- "the narrator" is NO LONGER an alias of "the Red Death" ✓
- "The masked figure (Red Death)" now explicitly notes the connection in its name

**Remaining Issue:**
1. **FALSE ALIAS: "the ebony clock"** - The ebony clock is a physical object (a giant clock in the black chamber). It is NOT the Red Death.

**Characters Detected:** 3 total
- Prince Prospero (main_cast_0) - CORRECT ✓, alias "the Prince Prospero"
- the Red Death (main_cast_1) - Has wrong alias: "the ebony clock" ✗
- The masked figure (Red Death) (F6 reconciled) - Acceptable (1 mention, name clarifies relationship)

**Why 7/10 (up from 6/10):** The removal of "the narrator" as a false alias is a significant improvement. One false alias remains vs. two previously. The explicit "(Red Death)" notation on the masked figure shows improved understanding.

### Character Profiles: 7.5/10 ✗
**Good:**
- "the Red Death" has rich `appearance` data with distinguishing features
- Personality data is present for both main characters
- Prince Prospero correctly has "unknown" appearance (he's not physically described in the text)

**Remaining Issues:**
1. **All relationships still empty** - Clear narrative relationships exist:
   - Prospero → Red Death (victim/nemesis)
   - Prospero → courtiers (protector/host)

**Why 7.5/10:** Appearance and personality extraction is good. Empty relationships remain the main gap.

### Chapter Summaries: 9/10 ✓
**Excellent:**
- Summary is comprehensive (1316 characters) and accurate
- Captures all major story beats:
  - The Red Death plague devastating the country
  - Prospero's retreat with 1000 courtiers into fortified abbey
  - The seven colored rooms and masked ball
  - The ebony clock's chilling effect on revelers
  - The mysterious masked figure appearing as Red Death itself
  - Prospero's pursuit and death
  - The revelation the figure was empty
  - The death of all guests

### Pronunciation Guide: 8/10 ✓
**Good:**
- 45 pronunciation entries flagged
- 41/45 have IPA (91% coverage)
- Important terms correctly flagged: Prospero, improvisatori, castellated, arabesque
- IPA quality is good

**Issues:**
- `term` and `category` fields are null for all entries (structural, low impact)
- 4 entries missing IPA

### HTML Presentation: 9/10 ✓
**Good:**
- Clean, professional dark theme
- Tab navigation works correctly
- Character profiles display correctly with expandable details
- Summary/overview is well-written and engaging

## Current Issues (Priority Order)

### CRITICAL
1. **FALSE ALIAS: "the ebony clock" merged with "the Red Death"**
   - Problem: Despite the object keyword block implemented in attempt 3, "the ebony clock" still appears as an alias
   - Evidence: The ebony clock is a massive clock in the black chamber that chimes hourly. It is a PHYSICAL OBJECT.
   - ID: main_cast_1 (from main cast pipeline)
   - **Root Cause Analysis:**
     - The fix added object keyword blocking to `verify_aliases()`
     - But `merge_descriptive_entities()` runs AFTER `verify_aliases()` (line 382 vs 377 in main_cast.py)
     - The merge adds aliases without re-verification
     - The "ebony clock" may be added during this post-verification merge step
   - **Verification needed:** Check if "the ebony clock" comes from:
     a. Initial Pass 1/Pass 2 LLM output (verify_aliases should catch it)
     b. merge_descriptive_entities() adding it as an alias from another profile
     c. F6 reconciliation adding it later
   - Location: `src/pipeline/character_extraction_v2/main_cast.py`
   - Fix: Either:
     1. Move verify_aliases to run AFTER merge_descriptive_entities, OR
     2. Add alias filtering logic inside merge_descriptive_entities, OR
     3. Run verify_aliases a second time after merging

### HIGH
2. **Relationships empty for all characters**
   - Problem: All characters have `relationships: {}`
   - Evidence: Clear narrative relationships exist:
     - Prospero is the host/protector of the courtiers
     - Red Death kills Prospero and all guests
   - Location: Character profile enrichment stage (F4 or profile sampling)
   - Fix: Profile enrichment needs to extract relationships from context

### MEDIUM
3. **Pronunciation entries missing `term` field**
   - Problem: All pronunciations have `word` but `term` is null
   - Location: Pronunciation pipeline output format
   - Impact: Low - word field works fine

### LOW
4. **Structure title is null**
   - Could extract "The Masque of the Red Death" from text header
   - Impact: Minimal

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | (initial analysis) | - | Character extraction: 5/10, Profiles: 6/10 |
| 2 | Critical: False aliases on Red Death | src/pipeline/character_extraction_v2/main_cast.py | **Partial** - "courtiers" removed, but "ebony clock" persists and "narrator" added |
| 3 | Critical: False aliases "ebony clock" and "narrator" | src/pipeline/character_extraction_v2/main_cast.py (verify_aliases) | **Partial** - "narrator" BLOCKED successfully, "ebony clock" STILL PRESENT |

## Fix Analysis - Attempt 3 Result

### What the fix did:
1. Added meta-reference block (RULE 0.4) - blocks "narrator", "reader", "audience"
2. Added object keyword block (RULE 0.45) - blocks aliases containing object keywords (clock, door, mirror, etc.)

### What actually happened:
- ✓ "the narrator" BLOCKED successfully (meta-reference rule worked)
- ✗ "the ebony clock" STILL PRESENT despite containing "clock"

### Hypothesis for failure:
The object keyword blocking logic IS correct, but it runs in verify_aliases() which executes at line 377. AFTER this, merge_descriptive_entities() runs at line 382 and can add new aliases without verification:

```python
# Line 377: verify_aliases runs (blocks bad aliases)
profiles = self.verify_aliases(profiles, chapter_summaries)

# Line 382: merge_descriptive_entities runs AFTER (adds unverified aliases)
profiles = self.merge_descriptive_entities(profiles)
```

The merge function at lines 1192-1194:
```python
canonical_profile.aliases.append(other.canonical_name)
canonical_profile.aliases.extend(other.aliases)
```

**If there was a separate profile for "the ebony clock" (incorrectly detected as a character), it would be merged into "the Red Death" and added as an alias, bypassing all verification.**

### Next fix should:
1. **Investigate:** Add logging to determine where "the ebony clock" alias originates
   - Is it in the initial LLM output?
   - Is it added during merge_descriptive_entities?
2. **Fix:** Either:
   - Run verify_aliases AFTER merge_descriptive_entities
   - Or add object/meta-reference blocking inside merge_descriptive_entities
   - Or filter aliases inside _filter_non_sentient_entities (which currently filters whole profiles, not aliases)

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (appropriate for this text size)
- Context: 32768 (sufficient)
- Temperature: 0.7 (standard)
- Profiling shows 0 low confidence items, 0 retries (good)

## Next Action
**Phase:** awaiting_fix

Fix priority: Critical #1 (false alias "the ebony clock")
- The fix needs to trace WHERE "the ebony clock" is being added
- Then apply blocking logic at that location OR reorder the processing steps
