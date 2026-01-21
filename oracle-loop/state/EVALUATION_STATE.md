# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 1
- **Phase:** awaiting_fix
- **baseline_score:** 6.65

## Latest Scores
- Structure Detection: 6/10
- Character Extraction: 5/10
- Character Profiles: 8/10
- Chapter Summaries: 8/10
- Pronunciation Guide: 6/10
- HTML Presentation: 8/10
- **Overall: 6.65/10** (threshold: 8.0)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.65 | - | First evaluation |

## Output Files
- HTML: ../output/gatsby/report.html
- JSON: ../output/gatsby/analysis.json

## Current Issues (Priority Order)

### CRITICAL

1. **False character split: Wilson variants**
   - Problem: "Wilson" (65 mentions), "George B. Wilson" (5 mentions), and "George" (8 mentions) are listed separately
   - Evidence: These all refer to George Wilson, the garage owner in the Valley of Ashes. The text uses "Wilson" as his common reference.
   - Location: Alias merging logic in character extraction (`src/pipeline/character_extraction.py` or `src/agents/character_agent.py`)
   - Fix: Improve alias resolution to recognize that "LastName" entries with high mention counts should merge with "FirstName LastName" entries for the same surname

2. **False character split: Baker variants**
   - Problem: "Baker" (28 mentions) and "Jordan Baker" (73 mentions) listed separately
   - Evidence: Jordan Baker is the only Baker in the novel. "Baker" is just her surname being used as reference.
   - Location: Same alias merging logic
   - Fix: LastName-only entries should be candidates to merge with FirstName-LastName entries when there's only one character with that surname

3. **False character split: Carraway variants**
   - Problem: "Carraway" (10 mentions) and "Nick Carraway" (24 mentions) listed separately
   - Evidence: Nick Carraway is the narrator and only Carraway in the book
   - Location: Same alias merging logic
   - Fix: Same as above - should be merged since there's only one Carraway

4. **False character split: Wolfshiem/Wolfsheim variants**
   - Problem: "Wolfshiem" (20 mentions) and "Meyer Wolfsheim" (5 mentions) listed separately
   - Evidence: Same character - the gangster associate of Gatsby. The spelling varies in the text but both refer to the same person.
   - Location: Same alias merging logic, also needs fuzzy matching for spelling variants
   - Fix: Fuzzy matching for surnames with similar spelling (Wolfshiem ≈ Wolfsheim)

5. **False character split: Mr. Gatsby**
   - Problem: "Mr. Gatsby" (1 mention) separate from "Jay Gatsby" (268 mentions)
   - Evidence: Same person - formal address vs. full name
   - Location: Title stripping in alias merging
   - Fix: "Mr./Mrs./Dr. [Surname]" should merge with "[FirstName] [Surname]" entries

### HIGH

6. **Structure detection found 11 chapters instead of 9**
   - Problem: The Great Gatsby has 9 chapters (I-IX), but the tool detected 11 structures
   - Evidence: Output shows "Chapter 1", "II", "III", "Chapter 4", "IV", "Chapter 6", "Chapter 7", "VI", "VII", "VIII", "IX" - duplicate entries
   - Location: Chapter detection in `src/pipeline/chapter_detection.py` or `src/agents/structure_agent.py`
   - Fix: Investigate why some chapters appear twice with different naming conventions; may be detecting both "CHAPTER I" and "I" as separate markers

7. **Four chapters have "None" for title**
   - Problem: Chapters 1, 4, 5, 6, 7 show "None" as title in the structure data
   - Evidence: `structure[0].title = "None"` instead of "I" or "Chapter I"
   - Location: Chapter title extraction logic
   - Fix: Roman numeral chapters should have the numeral as the title when no other title text exists

8. **Pronunciation guide has excessive false positives (675 entries)**
   - Problem: Common words incorrectly flagged: "Tom", "Daisy", "two", "West", "Egg", "yellow", "girls", "butler", "party", "war"
   - Evidence: These are standard English words that any narrator would know how to pronounce
   - Location: `src/pipeline/pronunciation.py` or `src/agents/pronunciation_agent.py`
   - Fix: Add filtering to exclude common English words (use a word frequency list); character names that are common English names shouldn't be flagged

### MEDIUM

9. **All pronunciation categories are "unknown"**
   - Problem: Every entry shows `category: unknown` instead of proper_noun, foreign, homograph, etc.
   - Evidence: `jq '.pronunciations[0].category' analysis.json` returns "unknown"
   - Location: Category assignment in pronunciation pipeline
   - Fix: Ensure category detection is working properly

10. **Physical descriptions missing for main characters**
    - Problem: Gatsby's appearance says "unknown" but the text describes him as "an elegant young roughneck" with a tan, pink suit, etc.
    - Evidence: `appearance.summary: "unknown"` in analysis.json
    - Location: Physical description extraction in character profiling
    - Fix: May need to extract physical details from chapter text, not just summaries

11. **Relationships field empty for all characters**
    - Problem: All characters have `relationships: {}` when there are clear relationships
    - Evidence: Tom is Daisy's husband, Gatsby is Daisy's former lover, Jordan is Nick's romantic interest, etc.
    - Location: Relationship extraction in character profiling
    - Fix: Relationship extraction may be disabled or not populated into the correct field

12. **Some pronunciation entries have None for IPA**
    - Problem: Last few entries show `ipa: None` (bass, entrance, polish, separate, moderate)
    - Evidence: These are homographs that need IPA but don't have it
    - Location: IPA generation for homographs
    - Fix: Ensure homographs get IPA for each pronunciation variant

## Pipeline Notes
- Analysis completed successfully in 64m 15s
- Used V2 character extraction (summary-driven)
- Found 11 chapters, 123 characters, 675 pronunciation flags
- 5 low-confidence character profiles
- Character Profiles stage had the most time (1728s) and was flagged as quality concern

## Fix History
(none yet)

## Next Action
Run PROMPT_fix.md to address character false splits (Critical #1-5) as highest priority. These account for the majority of the Character Extraction score penalty. Fixing alias merging for LastName-only entries to FirstName-LastName entries could recover ~2 points on Character Extraction, pushing overall score from 6.65 toward 7.5+.
