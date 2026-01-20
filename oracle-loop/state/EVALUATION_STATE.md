# Current Evaluation State

## Active Text
- **Name:** monkeys_paw
- **Attempt:** 6
- **Phase:** awaiting_evaluation
- **baseline_score:** 6.275

## Latest Scores
- Structure Detection: 9/10
- Character Extraction: 5/10 ← FAILING
- Character Profiles: 6/10
- Chapter Summaries: 9/10
- Pronunciation Guide: 4/10 ← FAILING
- HTML Presentation: 9/10
- **Overall: 6.275/10** (threshold: 8.0)

## Score Breakdown

### Structure Detection: 9/10

**What works:**
- Correctly identified 3 chapters matching the original's I, II, III structure
- All chapters have HIGH confidence
- Word counts and durations are reasonable (1734, 936, 4182 words)
- Chapter boundaries appear accurate

**Minor issue:**
- Chapter 3 has unusually high word count (4182) because it includes the Project Gutenberg license text at the end. The chapter summary even mentions: "The chapter contains no reference to Project Gutenberg or its legal terms within the narrative context, and those terms are unrelated to the story's events." This suggests the text wasn't properly cleaned of boilerplate.

### Character Extraction: 5/10 ← CRITICAL ISSUES

**What works:**
- Mr. White, Mrs. White, Sergeant-Major Morris correctly identified
- Morris has aliases ["Morris", "the sergeant-major"] ✓
- "Stranger from Maw and Meggins" correctly identified as separate character

**CRITICAL ISSUES:**

1. **FALSE CHARACTER SPLIT: "White" vs "Mr. White"**
   - "Mr. White" (10 mentions) and "White" (44 mentions) are listed as SEPARATE characters
   - "White" entry has aliases: ["Herbert White", "Herbert"]
   - This is WRONG: "White" when used alone almost always refers to Mr. White (the father), NOT Herbert
   - Herbert should be his own entry, not merged as an alias of "White"
   - Evidence in the JSON shows "White" profile has quotes like "For God's sake don't let it in" which is clearly Mr. White (the father) in Chapter 3

2. **HERBERT WHITE IS NOT A MAIN CHARACTER ENTRY**
   - Herbert White, the son who dies, should be a distinct main character
   - Instead, "Herbert White" and "Herbert" are listed as aliases of the confusing "White" entry
   - Herbert is a CRITICAL character - his death is the central tragedy of the story

3. **Nonsensical "the stranger" entry with wrong aliases**
   - A character entry "the stranger" exists with aliases: ["the old man", "the old woman", "the soldier"]
   - This is COMPLETELY WRONG:
     - "the old man" refers to Mr. White in Chapter 3
     - "the old woman" refers to Mrs. White in Chapter 3
     - "the soldier" refers to Morris
   - These should NOT be merged together as they are THREE different people

4. **Orphan entry: "his wife"**
   - A character entry "his wife" (2 mentions) exists separately
   - This should be merged with "Mrs. White"

5. **Chapter 3 characters_present is wrong**
   - Shows: ["the old man", "the old woman"]
   - Should show: ["Mr. White", "Mrs. White"] (or link to main character entries)
   - This disconnect suggests the chapter-to-character linking is broken

### Character Profiles: 6/10

**What works:**
- Mr. White's profile is reasonably accurate: elderly, white-haired, thin grey beard
- Mrs. White's profile captures her emotional arc well
- Sergeant-Major Morris has good physical description and personality traits
- Voice guidance sections are helpful for narrators

**Issues:**

1. **"White" character profile is confused** - Describes an "elderly man with thin grey beard" making wishes... but also lists Herbert as an alias. The profile is a mashup of Mr. White and Herbert details.

2. **Profile says "White" is elderly with grey beard but aliases include young Herbert** - Herbert is clearly NOT elderly; he's the Whites' adult son who works at Maw and Meggins factory.

3. **Missing Herbert's actual profile** - No profile for Herbert White specifically, who should have: young adult, works at factory, playful/light-hearted personality, frivolous humor

4. **Missing relationships** - All relationship fields are empty `{}`. Should include:
   - Mr. White is married to Mrs. White
   - Herbert White is son of Mr. and Mrs. White
   - Morris is old friend of Mr. White (they knew each other 21 years ago)

### Chapter Summaries: 9/10

**What works:**
- All three chapter summaries are accurate and capture key events
- Chapter 1: Correctly describes the setup, Morris's arrival, the monkey's paw, the first wish
- Chapter 2: Accurately captures the Maw and Meggins representative's visit, Herbert's death, the £200 coincidence
- Chapter 3: Captures the grief, second wish, knocking, third wish, ambiguous ending

**Minor issues:**
- Chapter 3 summary mentions "The chapter contains no reference to Project Gutenberg..." which is meta-commentary that shouldn't be in a chapter summary
- Summaries are on the long side but still useful for narrators

### Pronunciation Guide: 4/10 ← CRITICAL ISSUES

**Major problems:**

1. **COMMON WORD FALSE POSITIVES (50%+ of entries)**
   The pronunciation guide flags these extremely common English words as "proper_noun":
   - "his" (99 occurrences) - This is a basic pronoun!
   - "old" (42 occurrences) - Common adjective
   - "from" (38 occurrences) - Common preposition
   - "man" (23 occurrences) - Common noun
   - "wife" (15 occurrences) - Common noun
   - "woman" (11 occurrences) - Common noun
   - "soldier" (5 occurrences) - Common noun

2. **Project Gutenberg boilerplate contamination**
   Many pronunciation entries are from the Gutenberg license, not the story:
   - "GutenbergTM" (57 occurrences!)
   - "eBooks" (7 occurrences)
   - "AS-IS", "MERCHANTABILITY", "nonproprietary", "unenforceability"

   These are legal/technical terms from the appendix, not words a narrator needs help with.

3. **80 pronunciation entries is excessive for a 7000-word short story**
   - Most are false positives
   - A reasonable guide would have 10-20 entries max

**What actually IS useful:**
- "fakir" / "fakirs" - correctly flagged, good IPA /ˈfɑːkɪr/
- "rubicund" - correctly flagged as unusual
- "antimacassar" - correctly flagged, useful for narrator
- "bibulous" - correctly flagged
- "Laburnam" - correctly flagged (the villa name)
- Homograph entries (house, read, wind, live, minute, etc.) are legitimate and helpful

### HTML Presentation: 9/10

**What works:**
- Clean, professional dark theme
- Tab navigation works (Overview, Chapters, Characters, Pronunciations)
- Statistics are clearly displayed
- Performance timing breakdown is helpful
- Model usage information is transparent
- Character profiles are well-formatted with collapsible evidence
- Chapter summaries are readable

**Minor issues:**
- "started_at" and "ended_at" rows in timing table show empty values
- Some empty sections (relationships shows "No explicit relationships detected")

---

## Current Issues (Priority Order)

### CRITICAL

1. **False character split and merge: "White" vs "Mr. White" vs Herbert**
   - Problem: "Mr. White" (father) and "White" are separate entries, with "Herbert" wrongly aliased to "White"
   - Evidence: The "White" entry (44 mentions) has quotes from the father in Chapter 3 ("For God's sake don't let it in") but lists Herbert as alias
   - Location: `src/pipeline/character_extraction/consensus.py` - alias merging logic
   - Fix: "White" alone should merge with "Mr. White" (same person). "Herbert White" / "Herbert" should be a SEPARATE character entry.

2. **Completely wrong "the stranger" character with nonsense aliases**
   - Problem: Entry "the stranger" has aliases ["the old man", "the old woman", "the soldier"] - these are 3 different people!
   - Evidence: "the old man" = Mr. White, "the old woman" = Mrs. White, "the soldier" = Morris
   - Location: `src/pipeline/character_extraction/consensus.py` - LLM merge decision or candidate pairing
   - Fix: These descriptive references should merge to their correct character entries, not create a new combined entry

3. **Pronunciation flagging common English words**
   - Problem: Words like "his", "old", "from", "man", "wife", "woman" are flagged as needing pronunciation help
   - Evidence: "his" has 99 occurrences and is marked as "proper_noun" (it's a pronoun!)
   - Location: `src/pipeline/pronunciation/` - word filtering logic
   - Fix: Add common English word frequency filter (top 5000-10000 words should be excluded)

### HIGH

4. **Project Gutenberg boilerplate contamination**
   - Problem: Legal text from Gutenberg license is analyzed as story content
   - Evidence: "GutenbergTM" flagged 57 times, Chapter 3 summary mentions it, pronunciation guide full of legal terms
   - Location: `src/ingestion/refine.py` - text cleaning
   - Fix: Add Gutenberg license detection and removal during text refinement

5. **Herbert White missing as distinct character**
   - Problem: Herbert is the victim whose death drives the plot - he should be a main character with his own profile
   - Evidence: He appears in Chapters 1 and 2, has dialogue, has personality (frivolous, playful)
   - Location: Character extraction - he's been absorbed into wrong "White" entry
   - Fix: Resolving CRITICAL #1 should fix this

### MEDIUM

6. **Chapter 3 character linking shows "the old man/woman" instead of actual names**
   - Problem: `characters_present` for Chapter 3 lists ["the old man", "the old woman"] not ["Mr. White", "Mrs. White"]
   - Evidence: HTML report shows these descriptive terms instead of character names
   - Location: Chapter-to-character linking logic
   - Fix: Resolve character names to canonical entries

7. **Missing relationship data**
   - Problem: All relationship fields are empty `{}`
   - Evidence: Mr./Mrs. White are married, Herbert is their son, Morris is old friend - none captured
   - Location: `src/agents/character_agent.py` or relationship extraction
   - Fix: May need relationship extraction pass or better prompting

8. **"his wife" orphan character entry**
   - Problem: "his wife" (2 mentions) exists as separate character
   - Evidence: Should obviously merge with "Mrs. White"
   - Location: Character merging logic
   - Fix: Improve relational descriptor handling to merge "his wife" → "Mrs. White"

### LOW

9. **Chapter summary meta-commentary**
   - Problem: Chapter 3 summary includes "The chapter contains no reference to Project Gutenberg..."
   - Evidence: This is LLM meta-commentary, not plot summary
   - Location: Summary generation prompts
   - Fix: Add instruction to avoid meta-commentary about text formatting

10. **Timing table empty values**
    - Problem: "started_at" and "ended_at" rows show no duration
    - Evidence: HTML report timing section
    - Location: HTML export template
    - Fix: Either populate these or hide empty rows

---

## Fix History

### Attempt 1 → 2: Fixed character validation for company names
- Added "Companies, businesses, or organizations" to VALIDATION_SYSTEM_PROMPT rejection criteria
- Result: Pipeline still failed with same error

### Attempt 2 → 3: Fixed LLM response type handling and added explicit examples
- Made `_extract_json()` type-safe (returns None for lists)
- Added explicit JSON examples to validation prompt
- Result: NEW error - LLM responses truncated

### Attempt 3 → 4: Applied max_tokens from AgentConfig to LLMConfig
- Fixed configuration propagation bug
- Increased default max_tokens to 8192
- Result: SAME truncation error

### Attempt 4 → 5: Reduced character extraction chunk size
- Reduced `character_llm_chunk_chars` from 8000 to 5000
- Result: Pipeline completed successfully (this evaluation)

### Attempt 5 → 6: Fixed character merging prompts for title variants and family relationships

**Root Cause Analysis:**

1. **Issue #1: "Mr. White" vs "White" not merged (SHOULD BE SAME)**
   - **Symptom:** Same person split into 2 entries
   - **Data flow trace:**
     1. Appears in: HTML report character list
     2. Stored in: `AnalysisResult.characters`
     3. Generated by: `CharacterAgent.run()`
     4. **Originates in:** `src/pipeline/character_extraction/consensus.py:_llm_pairwise_merge_decision()` line 974
   - **Root cause:** The `PAIRWISE_ALIAS_PROMPT` says "If the only overlap is a last name, be VERY cautious (family members/spouses share last names)". LLM sees "Mr. White" vs "White" and thinks "only share a last name" → could be family → REJECTS merge. Title handling logic didn't properly communicate that "Mr. White" = title + "White" = same person.
   - **Confidence:** HIGH

2. **Issue #2: "Herbert" merged with "White" (SHOULD BE DIFFERENT - father vs son)**
   - **Symptom:** Son's name merged as alias of father
   - **Root cause:** Prompt says "A bare FIRST name can merge with a full name". LLM sees "Herbert" → "Herbert White" → merge, then "White" also matches "Herbert White" → chain merge. Misses that these are DIFFERENT people with family relationship.
   - **Confidence:** HIGH

3. **Issue #3: "the stranger" has aliases ["the old man", "the old woman", "the soldier"] (3 DIFFERENT PEOPLE)**
   - **Symptom:** Generic epithets incorrectly merged
   - **Root cause:** `_llm_epithet_resolution()` context windows too small (140 chars), generic descriptors merged without enough evidence
   - **Confidence:** HIGH

4. **Issue #4: Pronunciation false positives (DOWNSTREAM of character issues)**
   - **Symptom:** Common words like "his", "old", "man" flagged as proper nouns
   - **Root cause:** `src/analysis/pronunciation.py:139-146` flags ALL words from character names. Nonsense characters like "the old man", "his wife" split into common English words → ALL flagged
   - **This is a DOWNSTREAM SYMPTOM** - fix character extraction and this mostly disappears
   - **Confidence:** HIGH

**Fix Applied:**
- Modified: `src/pipeline/character_extraction/consensus.py`
- Changes:
  1. **PAIRWISE_ALIAS_PROMPT** (lines 152-185):
     - Added explicit TITLE VARIANTS rule: "Mr. Smith" and "Smith" ARE the same person
     - Added clarifying examples for family relationships
     - Added FAMILY RELATIONSHIPS rule: Check contexts for parent/child, husband/wife relationships
  2. **EPITHET_ALIAS_PROMPT** (lines 76-99):
     - Added CRITICAL WARNINGS section emphasizing generic descriptors often refer to different characters
     - Added guidance to only merge when contexts CLEARLY show same entity
  3. **Epithet context size** (line 1980):
     - Increased from 140 to 250 chars to capture relationship/scene information
- **Smoke test:** All 444 unit tests PASSED
- **Expected outcome:**
  - "Mr. White" and "White" should now merge correctly
  - "Herbert White" should be separate from "White" (father)
  - Generic epithets like "the old man", "the old woman" should not merge together
  - Should reduce pronunciation false positives as downstream effect

---

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | FAILED | - | LLM validation error for 'Maw and Meggins' |
| 2 | FAILED | - | Same error - fix insufficient |
| 3 | FAILED | - | NEW: LLM responses truncated |
| 4 | FAILED | - | SAME truncation error |
| 5 | 6.275 | baseline | First successful run - character merging issues |
| 6 | PENDING | - | Analysis complete, awaiting evaluation |

---

## Configuration Audit

### Models Used
- Structure: qwen3:30b-instruct (appropriate)
- Characters: qwen3-next:80b-a3b-instruct-q8_0 (large model, good)
- Summaries: qwen3-next:80b-a3b-instruct-q8_0 (good)
- Pronunciation: qwen3:30b-instruct (appropriate)

### Potential Config Issues
- `character_llm_chunk_chars` = 5000 (reduced in attempt 5, may be working)
- Pronunciation word filtering appears to have no common word exclusion list

---

## Attempt 6 Execution Details

### Output Files
- HTML: ../output/monkeys_paw/report.html
- JSON: ../output/monkeys_paw/analysis.json

### Pipeline Performance
- Total time: 14m 52s
- Total LLM calls: 53
- Total tokens: 101,621
- Bottleneck: Character Extraction (45.9% of time)

### Pipeline Warnings/Errors
- LLM identity detection failed (server error 500)
- Failed to parse JSON response for "White" character profile
- Low confidence profile for "White": 0.30
- Moral valence classification failed for Sergeant-Major Morris

### Quick Observations (from console output)
- Still shows "White" separate from "Mr. White"
- "White" still has aliases ["Herbert White", "Herbert"]
- "his wife" still separate character entry
- 80 pronunciation flags (unchanged from attempt 5)
- Character extraction issues appear unresolved despite prompt improvements

---

## Next Action

Run PROMPT_fix.md to address:
1. **Priority 1**: Fix character merging to correctly handle "White" family members
2. **Priority 2**: Add common English word filter to pronunciation
3. **Priority 3**: Add Gutenberg license text removal to ingestion

Focus on CRITICAL issues first - character extraction is the biggest score drag (5/10).
