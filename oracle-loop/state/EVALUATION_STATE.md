# Current Evaluation State

## Active Text
- **Name:** monkeys_paw
- **Attempt:** 1
- **Phase:** awaiting_fix
- **baseline_score:** 7.90

## Output Files
- HTML: ../output/monkeys_paw/report.html
- JSON: ../output/monkeys_paw/analysis.json

## Latest Scores
- Structure Detection: 8/10 ✓
- Character Extraction: 6/10 ✗ (FAILING)
- Character Profiles: 8/10 ✓
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 9/10 ✓
- HTML Presentation: 9/10 ✓
- **Overall: 7.90/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (1 category below threshold)

## Sanity Check Results
- Structure elements: 3 (correct for Parts I, II, III)
- Characters: 7
- Pronunciations: 37 (34 with IPA - 92% coverage)
- Main characters (>10 mentions): Herbert White, "the old man"
- Narrators identified: None (third-person narrative - correct)
- Characters from main_cast: 5
- Characters from supporting_cast: 1
- Characters from F6 reconciliation: 1

## Expected vs Actual Characters

| Expected Character | Found? | Notes |
|-------------------|--------|-------|
| Mr. White | ✓ | main_cast_0, 10 mentions |
| Mrs. White | ✓ | main_cast_1, 10 mentions |
| Herbert White | ✓ | main_cast_2, 14 mentions, alias "Herbert" |
| Sergeant-Major Morris | PARTIAL | Found as "Morris" (supporting_0), missing "Sergeant-Major Morris" alias |
| the monkey's paw | ✓ | Found as "the talisman" (main_cast_7) - acceptable |
| Stranger from Maw and Meggins | ✓ | F6 reconciled, 1 mention |
| **FALSE CHARACTER** | ✗ | "the old man" (main_cast_5) - **THIS IS MR. WHITE** |

## Current Issues (Priority Order)

### CRITICAL
1. **False character split: "the old man" should be Mr. White**
   - Problem: "the old man" is extracted as separate character (main_cast_5, 26 mentions) from Mr. White (main_cast_0, 10 mentions)
   - Evidence: In W.W. Jacobs' text, "the old man" is the narrator's third-person descriptor for Mr. White: "The old man rose with hospitable haste" (Part I), etc.
   - Impact: Combined, Mr. White should have ~36 mentions, making him the clear protagonist
   - Cascade: This causes Chapter 3 to list "the old man" instead of "Mr. White" in characters_present
   - ID Pattern: main_cast_5 → Fix in main_cast pipeline
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` - Pass 2 alias resolution should merge "the old man" → Mr. White
   - Fix: Consolidated alias resolution (Pass 2) should be taught that generic descriptors like "the old man" in conjunction with a proper name (Mr. White) should merge into the proper name

2. **Incorrect alias: "the old woman" merged as alias of "the old man"**
   - Problem: "the old woman" is listed as alias of "the old man" (see analysis.json main_cast_5)
   - Evidence: "The old woman" refers to MRS. White, not Mr. White. They are husband and wife.
   - Impact: Narrator preparing would think "the old woman" = "the old man" which is factually wrong
   - Location: Same as above - alias resolution logic
   - Fix: Co-occurrence validation should block this merge (man ≠ woman, never co-occur as same entity)

### HIGH
3. **Chapter 3 characters mislabeled**
   - Problem: Chapter 3 (Part III) lists `["the old man", "the old woman"]` instead of `["Mr. White", "Mrs. White"]`
   - Evidence: jq output shows structure[2].characters_present = ["the old man", "the old woman"]
   - Impact: Narrator sees unfamiliar names for established characters in final chapter
   - Root cause: This is a downstream effect of issues #1 and #2 - if "the old man" merged into Mr. White, summarizer would use the canonical name
   - Location: `src/pipeline/chapter_summary/summarizer.py` - should map characters to canonical names

### MEDIUM
4. **Morris missing "Sergeant-Major Morris" alias**
   - Problem: Character is listed as just "Morris" (supporting_0, 5 mentions) but "Sergeant-Major Morris" is his introduction
   - Evidence: Text has 9 occurrences of "sergeant-major" referring to Morris
   - Impact: Minor - narrator would understand, but title+name should be captured as alias
   - Location: Supporting cast extraction or alias resolution

5. **Structure titles are null**
   - Problem: All three structure elements have `title: null` instead of "Part I", "Part II", "Part III"
   - Evidence: Source text has "I.", "II.", "III." as markers
   - Impact: HTML shows unlabeled parts; minor usability issue
   - Location: `src/pipeline/chapter_detection/proposers/regex.py` - should capture Roman numerals as titles

## Detailed Category Scores

### Structure Detection: 8/10 ✓
- ✓ All 3 parts detected (I, II, III)
- ✓ No merged or split sections
- ✗ Titles are null (should be "Part I", "Part II", "Part III")
- Minor issue only - structure boundaries are correct

### Character Extraction: 6/10 ✗
- ✓ Mr. White, Mrs. White, Herbert White extracted correctly
- ✓ The talisman (monkey's paw) extracted as symbolic object
- ✓ Stranger from Maw and Meggins captured
- ✗ **CRITICAL:** "the old man" not merged with Mr. White (false split)
- ✗ **CRITICAL:** "the old woman" incorrectly aliased to "the old man" (wrong merge)
- ✗ Morris missing "Sergeant-Major Morris" alias

### Character Profiles: 8/10 ✓
- ✓ Mr. White profile is rich with personality, voice guidance, dialect notes
- ✓ Mrs. White has accurate personality and relationships
- ✓ Herbert White has playful personality captured with quotes
- ✓ "the old man" profile (which should be Mr. White) has appropriate details
- ✓ Voice guidance present for major characters
- ✗ Some relationship confusion (Mr. White lists "the old man" as friend - himself)
- Overall profiles are useful despite character split issue

### Chapter Summaries: 9/10 ✓
- ✓ Part I summary captures Morris's arrival, paw's introduction, first wish
- ✓ Part II summary captures Herbert's death, compensation of 200 pounds
- ✓ Part III summary captures grief, second wish, knocking, third wish
- ✓ All key plot points present
- ✓ No hallucinated events
- ✓ Appropriate length and narrator-useful details

### Pronunciation Guide: 9/10 ✓
- ✓ 37 entries, 34 with IPA (92% coverage)
- ✓ Proper nouns: Herbert, Morris
- ✓ Period vocabulary: rubicund, fakir, condoling
- ✓ Archaic spellings: to-night, instalment
- ✓ Homographs noted: live, minute, separate
- ✓ Company name: Meggins (/ˈmɛɡɪnz/)
- ✗ 3 entries missing IPA (minor)

### HTML Presentation: 9/10 ✓
- ✓ Navigation functional (chapters, characters, pronunciation tabs)
- ✓ Typography readable
- ✓ Information logically organized
- ✓ Profile sections well-formatted with voice guidance
- ✓ Pronunciation guide has search and filter functionality
- ✗ Character relationship shows self-reference (Mr. White → the old man as friend)

## Fix History
- This is the first fresh evaluation after analysis regeneration

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| (none yet) | - | - | - |

## Configuration Audit

### Model Configuration
- Using qwen3-next:80b-a3b-instruct-q8_0 as configured
- Model handles JSON extraction correctly

### Key Observation
The "old man"/"old woman" extraction pattern suggests the main_cast LLM identified narrative descriptors as distinct characters. The consolidated alias resolution (Pass 2) should have merged these with the proper names (Mr. White, Mrs. White) based on:
1. Co-occurrence in scenes (they're always present together with their named versions)
2. Relationship signals ("the old man rose" immediately followed by "Mr. White" references)
3. Gender disambiguation (man ≠ woman, so "the old woman" cannot be alias of "the old man")

## Next Action
Run PROMPT_fix.md to address:
1. CRITICAL: "the old man" → Mr. White merge (main_cast alias resolution)
2. CRITICAL: Block "the old woman" from being aliased to "the old man" (gender mismatch)
3. HIGH: Ensure chapter summaries use canonical names
