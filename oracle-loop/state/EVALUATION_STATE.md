# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 5
- **Phase:** awaiting_fix
- **baseline_score:** 6.80

## Output Files
- HTML: ../output/gatsby/report.html
- JSON: ../output/gatsby/analysis.json

## Latest Scores
- Structure Detection: 8/10
- Character Extraction: 6.5/10 ← PRIMARY BLOCKER
- Character Profiles: 7/10
- Chapter Summaries: 9/10
- Pronunciation Guide: 6/10
- HTML Presentation: 8/10
- **Overall: 7.50/10** (threshold: 8.0)

## Progress Notes

**Attempt 5 Evaluation:**
- Wolfshiem merge SUCCESS: Now properly merged (32 mentions, aliases: Meyer Wolfshiem, Wolfshiem)
- Narrator filter FAILED: Still 5 narrator-related entries (7 mentions total)
- Sloane/Mr. Sloane merge FAILED: Still split (10 + 1 mentions)
- Owl-eyed variants FAILED: Still split (2 entries, 1 mention each)
- Middle initial handling unclear: "George B. Wilson" is canonical name (should be "George Wilson")

**Root Cause Analysis:**
The narrator filter function exists at line 457-503 in `src/agents/characters_v2.py` and looks correct:
```python
if "narrator" in canonical_lower:
    # filter out
```
However, narrator variants still appear in output. Possible causes:
1. Filter is called only on `supporting_cast` (line 218), but narrator variants may be in `main_cast`
2. Characters may be added after the filter is applied
3. The filter may not be running during analysis (caching issue?)

## Current Issues (Priority Order)

### CRITICAL
1. **Narrator variants not being filtered (7 mentions across 5 entries)**
   - Problem: "Narrator" (2), "the narrator" (2), "The narrator" (1), "Nick Carraway (narrator)" (1), "Narrator (Nick Carraway)" (1) all still exist
   - Evidence: These should be filtered by `_filter_narrator_variants()` which checks `if "narrator" in canonical_lower`
   - Location: `src/agents/characters_v2.py` lines 457-503 (filter) and line 218 (call site)
   - Root Cause: Filter is only called on `supporting_cast`, but narrator variants may be added:
     - After the filter in the pipeline
     - To main_cast instead of supporting_cast
     - During final merge steps
   - Fix: Apply narrator filter to FINAL merged character list, not just supporting_cast
   - Impact: Would immediately recover ~7 mentions and remove clutter

### HIGH
2. **Sloane / Mr. Sloane split (11 mentions total)**
   - Problem: "Sloane" (10) and "Mr. Sloane" (1) remain separate after attempt 5 fix
   - Evidence: Same character - Tom's acquaintance who visits Gatsby in Chapter 6
   - Location: V2 merge logic - the title-stripping fix from attempt 5 didn't work
   - Root Cause: Pass 1 merge logic may not be executing properly, or title stripping not applied
   - Fix: Debug why "Mr. Sloane" → "Sloane" merge isn't happening; likely needs explicit title removal before comparison

3. **Owl-eyed variants split (2 entries, 2 mentions)**
   - Problem: "Owl-eyed man" (1) and "The man with owl-eyed spectacles" (1) are separate
   - Evidence: Same character - the bespectacled man at Gatsby's party/funeral
   - Location: V2 deduplication or supporting cast merge
   - Fix: Add semantic similarity matching for descriptive character references

4. **"George B. Wilson" canonical name issue**
   - Problem: Canonical name is "George B. Wilson" (91) instead of "George Wilson"
   - Evidence: Common usage in text is "George Wilson" or just "Wilson", not "George B. Wilson"
   - Location: V2 Pass 0 middle initial handling - this was supposed to fix it
   - Fix: Pass 0 should rename canonical to the shorter form when merging middle initial variants

5. **Stray Wilson entries**
   - Problem: "Wilson (referenced in actions)" (1 mention) separate from George/Myrtle Wilson
   - Evidence: Should be an alias of one of the Wilsons, not a separate entry
   - Location: Supporting cast cleanup
   - Fix: Filter entries with parenthetical clarifications like "(referenced in...)"

### MEDIUM
6. **Excessive pronunciation false positives (585 entries)**
   - Problem: Common English words flagged as pronunciation challenges
   - Evidence: "Butler" (20), "Chauffeur" (18), "Doctor" (10), "brown" (7), "Servants" (7)
   - Location: Pronunciation agent word filtering
   - Fix: Add exclusion list for common occupational titles and adjectives

7. **Chapter titles missing for I and V**
   - Problem: Chapters 1 and 5 show `null` title instead of "I" and "V"
   - Evidence: Structure JSON shows: `{"title": null, "start_line": null}` for these
   - Location: Structure agent chapter detection
   - Fix: Improve Roman numeral extraction

8. **Myrtle Wilson profile data corruption**
   - Problem: Description field contains embedded malformed JSON
   - Evidence: Raw text shows: `"Myrtle Wilson is a woman...\" appearance\": \"summary\": \"unknown..."`
   - Location: Profile generation or JSON serialization
   - Fix: Ensure profile fields are properly escaped/structured

9. **Stray Daisy entry**
   - Problem: "Daisy Buchanan (referenced in attempts to contact)" (1) is separate from main Daisy Buchanan (186)
   - Location: Supporting cast cleanup
   - Fix: Same fix as stray Wilson entries - filter parenthetical clarifications

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.80 | - | Initial evaluation - multiple character splits |
| 2 | 7.25 | +0.45 | Improvement but critical issues remain |
| 3 | 7.25 | +0.45 | Wilson fix did not take effect |
| 4 | 7.50 | +0.70 | Wilson fix partially worked; other splits remain |
| 5 | 7.50 | +0.70 | Wolfshiem merged; narrator filter failed; Sloane/Owl-eyed unfixed |

## Fix History

### Attempt 1 Fixes
- Added reverse pass to merge multi-word supporting→single-word main
- Added "the" prefix stripping in supporting→main merge
- Added institution exclusion list
- **Outcome:** Score improved 6.80 → 7.25

### Attempt 2 Fixes
- Added `_deduplicate_alias_canonical_conflicts()` method
- Added `_filter_narrator_variants()` method
- **Outcome:** Myrtle/McKee fixed

### Attempt 3 Fixes
- Added title-based disambiguation
- **Outcome:** Fix did not take effect

### Attempt 4 Fixes
- Updated `MAIN_CAST_PROMPT` to instruct LLM to include bare surnames as aliases
- Updated `_merge_lastname_aliases()` to merge bare surnames to all matching characters
- **Outcome:** Wilson now alias on both George and Myrtle Wilson

### Attempt 5 Fixes (Applied but PARTIAL SUCCESS)
- Simplified narrator filter: `if "narrator" in canonical_lower`
- Added Pass 0 middle initial handling
- Added title-stripping check in Pass 1
- **Outcome:** Wolfshiem merged correctly; narrator filter, Sloane, Owl-eyed still broken

## Next Action
Run PROMPT_fix.md to:
1. Move narrator filter to run on FINAL merged list (CRITICAL #1)
2. Debug why Sloane merge isn't working (HIGH #2)
3. Add parenthetical entry filter for "(referenced in...)" entries (HIGH #5)

## Strategic Note
To cross the 8.0 threshold from 7.50, we need approximately +0.50 points. The most impactful fixes:
- Fix narrator filter → Character Extraction 6.5 → 7.0 (+0.125 weighted)
- Fix Sloane merge → Character Extraction 7.0 → 7.5 (+0.125 weighted)
- Fix pronunciation false positives → Pronunciation 6 → 7 (+0.10 weighted)
- Combined: +0.35 points → 7.85 (still short)

We may also need to fix the profile data corruption (Character Profiles 7 → 8 = +0.15) to cross 8.0.
