# Current Evaluation State

## Active Text
- **Name:** gift_of_the_magi
- **Attempt:** 1
- **Phase:** awaiting_fix
- **baseline_score:** 7.50

## Latest Scores
- Structure Detection: 10/10 ✓
- Character Extraction: 5/10 ✗
- Character Profiles: 6/10 ✗
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 7/10 ✗
- HTML Presentation: 8.5/10 ✓
- **Overall: 7.50/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold)

## Current Issues (Priority Order)

### CRITICAL
1. **False character split: Jim / James Dillingham Young**
   - Problem: "Jim" (main_cast_1, 26 mentions) and "James Dillingham Young" (supporting_1, 3 mentions) are listed as separate characters. They are the same person.
   - Evidence: Text explicitly says "whenever Mr. James Dillingham Young came home and reached his flat above he was called 'Jim'" (line 32-33 of source text). The consolidated pass 2 alias resolution should have merged these.
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` - alias resolution in `_process_consolidated_pass2()` or `CONSOLIDATED_ALIAS_PROMPT`
   - Fix: The LLM should recognize "James Dillingham Young" as a full name variant of "Jim". This is a first-name/full-name alias pattern. The prompt or merge validation may need improvement for cases where a nickname (Jim) maps to a formal full name (James Dillingham Young).

2. **False character: "Dillingham" extracted as a person**
   - Problem: "Dillingham" (supporting_0, 6 mentions) is listed as a separate character. It is NOT a person - it's Jim's middle name discussed by the narrator.
   - Evidence: Text says "The 'Dillingham' had been flung to the breeze during a former period of prosperity when its possessor was being paid $30 per week" - it's used as a word/concept, not a person reference.
   - Location: `src/pipeline/character_extraction_v2/supporting.py` (supporting cast extraction) and/or NER pipeline upstream
   - Fix: The supporting cast extraction is picking up "Dillingham" from NER mentions where the narrator discusses the name itself, not a person. The LLM should distinguish between name-as-subject (discussing the name) vs name-as-person (referring to someone). This may require better prompt guidance about names being discussed *as words* vs names referring to characters.

### HIGH
3. **Wrong relationship type: "lover" instead of "husband/wife"**
   - Problem: Della and Jim are listed with relationship type "lover" but they are explicitly married.
   - Evidence: Text refers to "Mrs. James Dillingham Young" (line 34), Jim calls Della "my girl", and the story centers on a married couple buying Christmas gifts.
   - Location: `src/pipeline/character_profiling/` - relationship extraction
   - Fix: The relationship classification should recognize marriage indicators (Mrs., husband, wife) and use "husband"/"wife" or "spouse" instead of "lover".

### MEDIUM
4. **Pronunciation false positive: "week" classified as foreign word**
   - Problem: The common English word "week" is listed in the pronunciation guide under "Foreign Words" category.
   - Evidence: "week" is a basic English word. No narrator needs help pronouncing it.
   - Location: `src/pipeline/pronunciation/` - word classification
   - Fix: Common English words should be filtered. The classification logic incorrectly flagged "week" as foreign.

5. **Pronunciation false positives: common names (Jim, Della, Dell)**
   - Problem: "Jim", "Della", and "Dell" are flagged as pronunciation items. These are common English names that any narrator would know.
   - Evidence: These are standard English names with obvious pronunciation.
   - Location: `src/pipeline/pronunciation/` - proper noun flagging threshold
   - Fix: Names that are common English first names should not be flagged unless they have unusual pronunciation. "Jim" and "Dell" are completely standard.

### LOW
6. **HTML title shows "O. Henry" instead of "The Gift of the Magi"**
   - Problem: The page header displays the author name rather than the story title.
   - Evidence: The `<h1>` tag in the HTML shows "O. Henry" (from the first line of the text file).
   - Location: `src/export/` or wherever the title is extracted from the source text
   - Fix: Title extraction should look for the actual title, not just the first line of the file.

## Fix History
(First attempt - no previous fixes)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| (first attempt) | — | — | — |

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (correct per user config)
- No LLM retries or JSON parse failures across all stages
- No low-confidence items detected
- Chunking is appropriate for this short story (single chunk)
- No configuration issues identified

## Next Action
Run PROMPT_fix.md to address character extraction issues (Critical #1 and #2) and relationship type (High #3). Pronunciation issues (Medium #4 and #5) are secondary priority.
