# Current Evaluation State

## Active Text
- **Name:** monkeys_paw
- **Attempt:** 1
- **Phase:** awaiting_fix
- **baseline_score:** 7.65
- **Competitive Mode:** single

## Output Files
- HTML: ../output/monkeys_paw/report.html
- JSON: ../output/monkeys_paw/analysis.json

## Latest Scores
- Structure Detection: 8/10 ✓
- Character Extraction: 6/10 ✗ (FAILING)
- Character Profiles: 7/10 ✗ (FAILING)
- Chapter Summaries: 10/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 9/10 ✓
- **Overall: 7.65/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold)

## Score Breakdown

### Structure Detection: 8/10 ✓
**Strengths:**
- Correct chapter count (3 parts)
- Accurate boundaries and word counts
- Good character tracking per chapter

**Issues:**
- Chapter titles are null; original text uses "Part I", "Part II", "Part III"
- Minor issue, doesn't block threshold

### Character Extraction: 6/10 ✗
**Strengths:**
- Core White family correctly identified (Mr. White, Mrs. White, Herbert White)
- Sergeant-Major Morris identified with correct alias "Morris"
- Herbert alias correctly grouped

**Critical Issues:**
- "the monkey's paw" is listed as a CHARACTER with role "antagonist" - this is an OBJECT/TALISMAN, not a character. Objects should not appear in the character list regardless of narrative importance.

**Minor Issues:**
- The stranger from "Maw and Meggins" who delivers news of Herbert's death appears in Ch. 2 summary but is not in character list (minor - he's essentially unnamed)

### Character Profiles: 7/10 ✗
**Strengths:**
- Mr. White: Excellent profile with appearance (elderly, thin grey beard), personality (volatile, impulsive), voice guidance, 9 evidence citations
- Mrs. White: Good profile with personality, voice guidance, 6 evidence citations
- Sergeant-Major Morris: Good description in supporting section

**Issues:**
- Herbert White: LOW confidence (0.30), profile failed to parse structured fields, only has a description paragraph. Missing appearance, personality sections, voice guidance, evidence citations
- The monkey's paw has an inappropriate character profile with "unknown" personality/voice guidance - makes no sense for an object

### Chapter Summaries: 10/10 ✓
**Strengths:**
- Excellent, detailed summaries for all 3 parts
- Accurate capture of key events (chess game, Morris's visit, the wish, Herbert's death, the knocking)
- Good narrator-useful details (atmosphere, emotional beats)
- Appropriate length (100-200 words each)
- No hallucinations detected

### Pronunciation Guide: 8/10 ✓
**Strengths:**
- 50 entries, 47 with IPA (94% coverage)
- Good proper nouns: fakirs, rubicund, Meggins, Laburnam
- Homographs section (3 entries)
- Helpful notes for each entry

**Minor Issues:**
- Some unnecessary flags: "slushy", "out-of-the-way", "to-night" - common/archaic words that experienced narrators wouldn't need
- Overall acceptable for threshold

### HTML Presentation: 9/10 ✓
**Strengths:**
- Clean navigation between sections
- Good character profile layout with evidence citations
- Pronunciation guide with multiple views (by type, by chapter)
- Search functionality

## Current Issues (Priority Order)

### CRITICAL
1. **Object "the monkey's paw" incorrectly classified as character**
   - Problem: The monkey's paw (13 mentions) is listed as a character with role "antagonist" and has a character profile
   - Evidence: The monkey's paw is an inanimate talisman/object, not a sentient character. It has no speech, no personality, no voice - it's a magical object that grants wishes
   - Location: Character extraction pipeline - likely `src/pipeline/character_extraction_v2/`
   - ID: `main_cast_4` → Fix in main cast pipeline
   - Fix: Add filtering to exclude inanimate objects from character lists. Objects mentioned frequently (talismans, weapons, vehicles) should be filtered out based on:
     - Lack of dialogue/speech
     - Lack of relationships with other characters
     - Classification as object/item in NER
     - Consider maintaining a separate "Notable Objects" section if tracking is desired

### HIGH
2. **Herbert White profile incomplete (LOW confidence)**
   - Problem: Herbert White has the most mentions (14) but lowest confidence (0.30) and missing structured profile fields
   - Evidence: Profile shows only a description paragraph; missing appearance, personality, voice guidance, evidence citations
   - Location: `src/pipeline/character_extraction_v2/` - profile generation failed to parse JSON per pipeline notes
   - Fix: Investigate why Herbert's profile JSON parsing failed. May need to improve error handling/retry logic in profile generation

### MEDIUM
3. **Chapter titles showing as null**
   - Problem: Structure has 3 chapters but all titles are null
   - Evidence: Original text uses "Part I", "Part II", "Part III" as section headers
   - Location: `src/pipeline/chapter_detection/` or structure agent
   - Fix: Improve regex patterns for "Part X" style chapter markers

## Fix History
(First attempt - no previous fixes)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | (initial analysis) | - | Baseline established |

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 7.65 | - | Baseline: Object as character, Herbert profile incomplete |

## Next Action
Run PROMPT_fix.md to address:
1. CRITICAL: Filter out "the monkey's paw" as it's an object, not a character
2. HIGH: Fix Herbert White profile generation
