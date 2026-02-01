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
- Structure Detection: 8/10 ✓
- Character Extraction: 5/10 ✗ (FAILING)
- Character Profiles: 7/10 ✗ (FAILING)
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 9/10 ✓
- HTML Presentation: 9/10 ✓
- **Overall: 7.4/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold)

## Current Issues (Priority Order)

### CRITICAL
1. **False character split: "Mr. White" and "the old man" are the same person**
   - Problem: `Mr. White` (10 mentions) and `the old man` (26 mentions) are listed as separate characters
   - Evidence: "The old man" is the narrative descriptor for Mr. White throughout the story. The profiling system even detected this - line 1684 in report.html shows `Mr. White (self)` as a relationship for "the old man", meaning the system knew they were the same person but didn't merge them.
   - IDs: `main_cast_0` (Mr. White) and `main_cast_5` (the old man) - both from main_cast pipeline
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` - the consolidated Pass 2 alias resolution should have caught this
   - Fix: Improve alias detection to recognize that "the old X" referring to a named "Mr. X" with spouse "Mrs. X" are the same person. Add heuristic: if "the old [descriptor]" has same family relationships (spouse, son) as a named character, they should merge.

2. **False alias assignment: "the old woman" wrongly assigned to "the old man"**
   - Problem: Character "the old man" has alias `the old woman` - but "the old woman" is Mrs. White, not Mr. White
   - Evidence: In the text, "the old man" and "the old woman" are DIFFERENT people (husband and wife). The alias resolution incorrectly grouped them.
   - IDs: `main_cast_5` (the old man with wrong alias)
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` - the `CONSOLIDATED_ALIAS_PROMPT` or Pass 2 processing
   - Fix: Add validation that "the old man" and "the old woman" are gender-distinct references and should NEVER be aliases of each other. The co-occurrence validation should also catch this - they appear in the same scenes as distinct actors.

### HIGH
3. **Missing alias: "Sergeant-Major Morris" for "Morris"**
   - Problem: Morris (5 mentions) is missing his full title "Sergeant-Major Morris" as an alias
   - Evidence: The text introduces him as "Sergeant-Major Morris" and then refers to him as just "Morris". The description correctly says "Sergeant-Major Morris" but the aliases list is empty.
   - ID: `supporting_0` (Morris) - from supporting cast pipeline
   - Location: `src/pipeline/character_extraction_v2/supporting.py` or alias resolution
   - Fix: Ensure title+name forms are captured as aliases during extraction

### MEDIUM
4. **Quote misattribution in "the old man" profile**
   - Problem: Quote "Never mind, dear" is listed under "the old man"'s example quotes, but this is spoken BY Mrs. White TO her husband (the old man)
   - Evidence: The full quote is "Never mind, dear," said his wife, soothingly" - the possessive "his wife" makes clear she's speaking
   - Location: `src/pipeline/character_profiling/` - quote extraction logic
   - Fix: Improve quote attribution to check for dialogue tags that indicate the speaker (e.g., "said his wife")

## Analysis Summary

The character extraction scored 5/10 due to a critical false split (Mr. White / the old man) that doubles the protagonist's entry and confuses their identity. The pipeline extracted "the old man" as a separate character even though:
1. "The old man" has the same spouse (Mrs. White), same son (Herbert), same physical description (thin grey beard)
2. The profiling system detected they were the same (`Mr. White (self)` relationship) but didn't act on it

The alias assignment of "the old woman" to "the old man" is a separate error that compounds the confusion.

### Root Cause Analysis

The V2 character extraction pipeline's consolidated Pass 2 should have caught this. Possible failure modes:
1. **LLM didn't recognize the pattern**: "the old man" as a narrative descriptor for a named character
2. **Co-occurrence validation didn't fire**: Mr. White and "the old man" may never appear in the same sentence (they're the same person!), so Jaccard would be 0.0, but this should BLOCK merge, not cause a split
3. **Gender-based alias merging**: The system incorrectly grouped "the old woman" with "the old man" based on similar phrasing

**Recommended fix approach:**
1. Add a defensive heuristic: If two characters share the exact same family relationships (same spouse, same children), they're likely the same person
2. Add gender validation: "the old man" and "the old woman" cannot be aliases of each other
3. Review the Pass 2 LLM prompt to ensure it understands that "the old X" can be a narrative reference to a named character

## Sanity Check Results

```
Structure elements: 3 (Parts I, II, III - CORRECT for this story)
Characters: 6
Main characters (>10 mentions): ['Herbert White', 'the old man']
All characters: [('Mr. White', 10), ('Mrs. White', 10), ('Herbert White', 14), ('the old man', 26), ('the monkey's paw', 5), ('Morris', 5)]
Narrators identified: [] (CORRECT - third-person narrative)
Characters from main_cast: 5
Characters from supporting_cast: 1
Pronunciations with IPA: 34/37
Characters with physical_description: 0/6
Characters with relationships: 6/6
```

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | (initial evaluation) | — | FAIL (7.4/10) |

## Next Action
Run PROMPT_fix.md to address the critical false split between Mr. White and "the old man" (Critical #1 and #2)
