# Current Evaluation State

## Active Text
- **Name:** a_camping_trip
- **Attempt:** 1
- **Phase:** awaiting_fix
- **baseline_score:** 8.625

## Latest Scores
- Structure Detection: 10/10 ✓
- Character Extraction: 8/10 ✓
- Character Profiles: 6.5/10 ✗ (FAILING)
- Chapter Summaries: 9.5/10 ✓
- Pronunciation Guide: 8.5/10 ✓
- HTML Presentation: 9/10 ✓
- **Overall: 8.625/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (1 category below threshold)

## Current Issues (Priority Order)

### CRITICAL
(None)

### HIGH
1. **Character profiles missing structured data for 3/4 main characters**
   - Problem: Lincoln Stewart, Milton Jennings, and Rance all have `physical_description: null`, `relationships: {}`, and other empty profile fields despite being the main cast
   - Evidence: Only Bert (4th main character) has a populated profile with voice guidance, personality traits, and source evidence
   - Pipeline notes indicate: "JSON parsing failures for some character profiles (moral valence classification failed)"
   - Character confidence: Lincoln Stewart (low), Milton Jennings (low), Rance (low), Bert (high)
   - The basic profile text descriptions ARE present (e.g., "Lincoln Stewart is the first-person narrator...") but structured fields (appearance, personality, voice guidance) are missing
   - Location: `src/pipeline/character_extraction_v2/` - likely the profile enrichment stage
   - Fix: Investigate why JSON parsing failed for these profiles. The pipeline was able to generate profile text but failed to populate structured fields. This may be a prompt issue, schema validation issue, or retry exhaustion.

### MEDIUM
2. **Minor characters Mrs. Jennings and Mr. Jennings not extracted**
   - Problem: Mrs. Jennings (who serves the boys breakfast, has dialogue) and Mr. Jennings (who owns the house, speaks to boys) are missing from character list
   - Evidence: "Mrs. Jennings set out some bread and milk", "Well, see't you do, said Mr. Jennings"
   - These are named, speaking characters with narrative significance
   - Location: Character extraction thresholds may be filtering single-mention characters too aggressively
   - Fix: Consider whether dialogue presence should boost extraction priority

3. **Low confidence across main characters**
   - Problem: 3 of 4 main characters marked as "low" confidence
   - Evidence: Only Bert has "high" confidence
   - This may be a symptom of the JSON parsing failures noted above
   - Location: Confidence scoring in character extraction pipeline

### LOW
4. **Borderline over-extraction of anonymous characters**
   - Problem: "young man with oars" and "boat-keeper" are extracted (1 mention each)
   - These are functional descriptions, not named characters
   - However, "boat-keeper" does have dialogue, so extraction is defensible
   - Fix: Consider if anonymous single-mention speakers should be demoted to "background" tier

## Fix History
(First attempt - no prior fixes)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | (initial analysis) | N/A | Baseline established |

## Next Action
Run PROMPT_fix.md to address character profile population failures (HIGH #1).

The fix phase should:
1. Investigate why JSON parsing failed for character profiles in the V2 pipeline
2. Check `src/pipeline/character_extraction_v2/` for profile enrichment logic
3. Look at the specific error handling when "moral valence classification failed"
4. Ensure profile structured fields (appearance, personality, voice guidance) are populated even if some sub-fields fail
