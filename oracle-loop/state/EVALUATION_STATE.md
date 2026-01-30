# Current Evaluation State

## Active Text
- **Name:** john_g
- **Attempt:** 2
- **Phase:** awaiting_analysis
- **baseline_score:** 7.35

## Output Files
- HTML: ../output/john_g/report.html
- JSON: ../output/john_g/analysis.json

## Latest Scores
- Structure Detection: 10/10 ✓
- Character Extraction: 5/10 ✗ (FAILING)
- Character Profiles: 8/10 ✓
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 7/10 ✗ (FAILING)
- HTML Presentation: 9/10 ✓
- **Overall: 7.35/10** (weighted reference)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold)

## Current Issues (Priority Order)

### CRITICAL
1. **False character split: "John G." and "John" are listed as separate characters**
   - Problem: "John G." (15 mentions, id=supporting_0) and "John" (19 mentions, id=supporting_1) are listed as two distinct characters, but they are the SAME HORSE
   - Evidence: The text uses "John" as a short form of "John G." (e.g., "Come along, John, it's all right, old man!" at position 5905). Both entries have nearly identical profiles describing a 22-year-old veteran horse
   - Impact: This is a ~2 point deduction in Character Extraction (major character split error)
   - Location: `supporting_*` IDs indicate both came from supporting cast pipeline in `src/agents/characters.py`
   - Fix: The supporting cast alias resolution should recognize that "John" is a nickname/short form of "John G." - the period-terminated form "John G." should merge with bare "John"

### HIGH
2. **Pronunciation false positives: common words flagged unnecessarily**
   - Problem: Words like "Sergeant", "Corporal", "Price", "Adams", "Richardson" have IPA but don't need pronunciation guidance for a native English speaker. "forty-eight", "hill-town", "day-room" are also unnecessarily flagged
   - Evidence: First 10 entries include standard English words and common surnames that any narrator would know
   - Impact: ~1 point deduction in Pronunciation Guide (excessive false positives)
   - Location: `src/pipeline/pronunciation/` - filtering logic
   - Fix: Add better filtering to exclude common English military ranks and standard surnames

3. **Missing IPA for some entries**
   - Problem: 7/48 pronunciations lack IPA (e.g., "wind" - which is actually a homograph needing guidance)
   - Evidence: `jq '[.pronunciations[] | select(.ipa != null)] | length'` = 41
   - Impact: Minor deduction (~0.5 points)
   - Location: IPA generation in pronunciation pipeline
   - Fix: Ensure IPA generation covers all flagged words

### MEDIUM
4. **Minor characters lack profiles**
   - Problem: Corporal Richardson, Captain Adams, and First Sergeant Price have empty profiles (no appearance, personality, or voice guidance)
   - Evidence: These characters have mention_count=1 but are narratively important
   - Impact: Minor (~0.3 points) - they're supporting characters
   - Location: Profile generation thresholds
   - Note: This is borderline acceptable for a short story where John G. is the clear protagonist

### LOW
5. **Narrative style listed as "unknown" in structure overview**
   - Problem: Overview says "narrative_style": "unknown" but plot_summary correctly identifies "third-person limited"
   - Evidence: Inconsistency in metadata
   - Impact: Minimal

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 7.35 | 0.00 | Baseline - John G./John split is critical issue |

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 2 | John G./John character split | src/agents/characters.py | Added Pass 0.5 to merge period-terminated abbreviations |
| 2 | Pronunciation ranks filter | src/pipeline/pronunciation_guide/proposers/character_proposer.py | Added military ranks to title filter |

## Evaluation Details

### 1. Structure Detection: 10/10 ✓
- Correctly identified 1 chapter (this is a short story, not a novel)
- Chapter summary is accurate and comprehensive
- Word count (2,226) and duration estimate (14.84 min) are reasonable
- Characters present correctly lists the key figures including "John G. (horse)"

### 2. Character Extraction: 5/10 ✗
**Critical failure: "John G." and "John" are separate entries when they should be merged.**

The story's protagonist is "John G." - a 22-year-old veteran horse of the Pennsylvania State Police. The text uses both "John G." and "John" interchangeably to refer to this same horse:
- "John G., on that diluvian night, was twenty-two years old"
- "Come along, John, it's all right, old man!"

Both character entries (supporting_0 and supporting_1) have nearly identical profiles describing the same horse. This is a clear false split.

**Expected characters:**
- ✓ John G. (should be single entry with "John" as alias)
- ✓ First Sergeant Price
- ✓ Captain Adams
- ✓ Corporal Richardson

**Found but problematic:**
- John G. (15 mentions) - partial
- John (19 mentions) - should be merged with above

### 3. Character Profiles: 8/10 ✓
The profiles for John G. and "John" are actually quite good - they correctly identify:
- The horse's age (22 years old)
- Physical traits (clean-limbed, alert, plucky)
- Relationships with Price and Richardson
- Key evidence quotes from the text

The main issue is that these profiles exist separately rather than combined.

Minor characters lack profiles but this is acceptable given their limited narrative presence.

### 4. Chapter Summaries: 9/10 ✓
The single chapter summary is excellent:
- Captures the main plot (dangerous mission, bridge crossing, false alarm)
- Identifies key characters and their roles
- Notes the philosophical ending about human duty to animals
- Appropriate length and detail level

### 5. Pronunciation Guide: 7/10 ✗
**Issues:**
- **False positives:** Common words like "Sergeant", "Corporal", "Price", "Adams" don't need pronunciation help
- **Missing IPA:** 7 entries lack IPA guidance
- **Homographs:** "wind" is flagged but lacks IPA - this IS a valid entry as it's a homograph

**Good entries:**
- "Greensburg" - locale name, reasonable to flag
- Period terms that might be unfamiliar

**Should be removed:**
- Military ranks (Sergeant, Corporal) - standard English
- Common surnames (Price, Adams, Richardson)
- Compound words (hill-town, day-room) - self-explanatory

### 6. HTML Presentation: 9/10 ✓
- Navigation works correctly
- Clean, professional dark theme
- Character profiles and summaries well-organized
- Pronunciation guide is functional

## Fix Summary (Attempt 2)

### Fix 1: Character Split (John G. / John)
**Root Cause:** `src/agents/characters.py:_merge_within_supporting_cast()` had two merge passes:
- Pass 1: Last-name-only → full name (skipped "John G." because it contains a space)
- Pass 2: Spelling variants (failed because "John G." vs "John" = 72.7% similarity, below 85% threshold)

**Solution:** Added Pass 0.5 to handle period-terminated abbreviations:
- Normalizes names by stripping trailing period-terminated initials (e.g., " G.", " F.")
- "John G." → "john" matches "John" → "john"
- Merges the one with fewer mentions into the one with more
- **Universal fix**: Works for any period-terminated abbreviation (e.g., "John F. Kennedy" → "Kennedy")

**Smoke test:** PASSED - "John G." (15 mentions) correctly merged into "John" (19 mentions) as alias

**Files modified:**
- `src/agents/characters.py` (lines 2590-2650, added Pass 0.5 before Pass 1)

### Fix 2: Pronunciation Ranks Filter
**Root Cause:** `src/pipeline/pronunciation_guide/proposers/character_proposer.py` filtered civilian titles ("Mr", "Dr") but not military ranks

**Solution:** Extended title filter to include military ranks:
- Added: sergeant, corporal, captain, lieutenant, colonel, major, general, private, admiral, commander
- This is a **universal reference lexicon** (ALLOWED per fix philosophy) - ranks are stable across many books
- Not a keyword deny-list - these words help normalize character names, not filter vocabulary

**Smoke test:** PASSED - "Sergeant", "Corporal", "Captain" filtered; "Price", "Adams", "Richardson" kept

**Files modified:**
- `src/pipeline/pronunciation_guide/proposers/character_proposer.py` (lines 104-123)

### Expected Impact
- **Character Extraction:** 5/10 → 8+/10 (fixing major split error worth ~2-3 points)
- **Pronunciation Guide:** 7/10 → 8+/10 (filtering ranks worth ~1 point)

## Next Action
Re-run analysis to verify fixes work on actual text
