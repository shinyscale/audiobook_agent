# Current Evaluation State

## Active Text
- **Name:** monkeys_paw
- **Attempt:** 1
- **Phase:** awaiting_fix
- **baseline_score:** 6.65

## Output Files
- HTML: ../output/monkeys_paw/report.html
- JSON: ../output/monkeys_paw/analysis.json

## Latest Scores
- Structure Detection: 9/10
- Character Extraction: 4/10 ← FAILING
- Character Profiles: 5/10 ← FAILING
- Chapter Summaries: 8/10
- Pronunciation Guide: 6/10
- HTML Presentation: 9/10
- **Overall: 6.65/10** (threshold: 8.0)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.65 | 0.00 | Baseline - Mr. White missing (merged with Mrs. White) |

## Current Issues (Priority Order)

### CRITICAL
1. **False character merge: Mr. White merged into Mrs. White**
   - Problem: Mr. White (the protagonist who makes all 3 wishes) is listed as an alias of Mrs. White
   - Evidence: In analysis.json, Mrs. White's aliases array contains "Mr. White"
   - This is catastrophic - Mr. White is the primary actor: he rescues the paw, makes all wishes, is haunted by the face in the fire, makes the crucial third wish
   - The system incorrectly treated "Mr. White" and "Mrs. White" as aliases because they share the surname "White"
   - Location: `src/pipeline/character_extraction_v2/` - alias resolution logic
   - Fix: Characters with different titles (Mr./Mrs./Miss/Dr.) before the same surname should NEVER be merged - these typically represent different people (spouses, siblings)

### HIGH
2. **Chapter 3 character references use generic terms instead of names**
   - Problem: Chapter 3's `characters_present` lists "the old man" and "the old woman" instead of "Mr. White" and "Mrs. White"
   - Evidence: `jq '.structure[2].characters_present'` returns `["the old man", "the old woman"]`
   - This is related to the character extraction issue - if Mr. White doesn't exist as a character, the system can't link "the old man" to him
   - Location: Character linking in summary generation or character presence detection
   - Fix: After fixing character extraction, verify character linking in summaries uses canonical names

3. **Missing character: The stranger from Maw and Meggins**
   - Problem: The man who delivers news of Herbert's death is not extracted as a character
   - Evidence: He's mentioned in the chapter 2 summary and chapter 2's characters_present lists "The stranger", but he has no character entry
   - He's a minor character but appears in multiple paragraphs with dialogue
   - Location: Character extraction threshold or filtering
   - Fix: May resolve automatically once core extraction is fixed, or may need threshold adjustment

### MEDIUM
4. **Pronunciation guide missing IPA for all entries**
   - Problem: All 52 pronunciation entries have `ipa: null`
   - Evidence: `jq '.pronunciations[:5] | .[].ipa'` returns all nulls
   - Location: `src/pipeline/pronunciation_detection.py` or related
   - Fix: Enable IPA generation or check why it's not being populated

5. **Missing key pronunciation terms**
   - Problem: "fakir" (Indian holy man who enchanted the paw) and "rubicund" (describing Morris) are not flagged
   - These are genuinely unusual words a narrator would need help with
   - Location: Pronunciation detection rules or word list

6. **Chapter titles are null**
   - Problem: Structure entries have `title: null` instead of "I", "II", "III"
   - Evidence: The original text uses Roman numerals for part divisions
   - Minor issue but worth fixing for completeness
   - Location: Chapter detection regex or title extraction

### LOW
7. **Some unnecessary pronunciation flags**
   - "to-night" (archaic spelling, pronounced normally)
   - "slushy" (common English word)
   - "out-of-the-way" (common phrase)
   - These are false positives that clutter the pronunciation guide

## Pipeline Notes
Analysis completed successfully in 10m 11s using V2 character extraction.

### Key Statistics:
- 3,954 words analyzed
- 3 chapters detected
- 3 characters extracted (V2 summary-driven approach)
- 3 character profiles generated
- 52 pronunciation flags
- 22 LLM calls total (45,106 tokens)

## Fix History
(No fixes yet - this is attempt 1)

## Next Action
Run PROMPT_fix.md to address the CRITICAL character merge issue. The Mr./Mrs. title distinction must be respected during alias resolution - characters with different titles before the same surname are almost always different people.

**Root Cause Analysis:**
The V2 character extraction pipeline appears to merge characters too aggressively based on shared surnames. The alias resolution needs to:
1. Check for title prefixes (Mr., Mrs., Miss, Ms., Dr., etc.)
2. Treat different titles + same surname as DIFFERENT characters (not aliases)
3. This is a common pattern: Mr. and Mrs. Smith, Dr. and Mrs. Watson, etc.
