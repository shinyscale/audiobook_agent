# Current Evaluation State

## Active Text
- **Name:** a_camping_trip
- **Attempt:** 1
- **Phase:** awaiting_fix
- **baseline_score:** 8.08
- **Competitive Mode:** single

## Latest Scores
- Structure Detection: 10/10 ✓
- Character Extraction: 6.5/10 ✗ (FAILING)
- Character Profiles: 7/10 ✗ (FAILING)
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 8.5/10 ✓
- HTML Presentation: 9/10 ✓
- **Overall: 8.08/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold)

## Current Issues (Priority Order)

### CRITICAL
1. **False character split: "Milt" is a separate entry from "Milton Jennings"**
   - Problem: "Milt" (supporting_0, 2 mentions) is listed as a separate character from "Milton Jennings" (main_cast_1, 32 mentions)
   - Evidence: In the text, line 29: `"Hello, Milt," Lincoln returned` — this is Lincoln greeting Milton Jennings. Line 54: `"Well, now, if you don't mind, Milt"` — again addressing Milton. "Milt" is a nickname for Milton.
   - ID patterns: "Milt" is `supporting_0` (supporting cast pipeline), "Milton Jennings" is `main_cast_1` (main cast pipeline)
   - Location: Cross-pipeline alias resolution. The main cast identified "Milton Jennings" with aliases ["Milton", "Jennings"], and the supporting cast independently extracted "Milt" without recognizing it as a nickname for Milton.
   - Fix: This is a cross-pipeline merge issue. The F6 reconciliation step (analyzer.py) or alias verification should recognize "Milt" as a nickname for "Milton"/"Milton Jennings". This is a substring/nickname match pattern (Milt → Milton).

### HIGH
2. **Bert's profile has misattributed physical description**
   - Problem: Bert's appearance says "brown as a leather glove" but this description is about Lincoln in the narration ("Working all day in a level field like this, with the sun burning one's neck brown as a leather glove"). This is a generic narration, not describing Bert.
   - Evidence: The text at lines 12-14 describes the narrator's generic observation about working in fields, then at line 7 it's Lincoln who's working the plow. Bert isn't introduced until line 43.
   - Location: `src/pipeline/character_profiling/` — passage gathering or evidence attribution
   - Fix: The profiling pipeline incorrectly attributed a narrator observation to Bert. This may be a passage-gathering issue where generic narration gets assigned to the wrong character.

3. **Milton Jennings has "Jennings" as an alias — ambiguous with Mr./Mrs. Jennings**
   - Problem: "Jennings" is listed as an alias for Milton Jennings, but the text also has Mr. Jennings (Milton's father) and Mrs. Jennings (Milton's mother) as distinct characters. The bare surname "Jennings" could refer to any of them.
   - Evidence: Line 79: "Mr. Jennings's house" — Mr. Jennings is clearly a different character. Having "Jennings" as Milton's alias creates ambiguity.
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` — alias extraction
   - Fix: When a character shares a surname with other distinct characters (Mr. Jennings, Mrs. Jennings), the bare surname should NOT be assigned as an alias to any single character. Similarly, "Stewart" as an alias for Lincoln Stewart is problematic since there's a "Mr. Stewart" mentioned.

### MEDIUM
4. **Bert's full name "Bert Jenks" not captured**
   - Problem: The text says "Bert Jenks will lend us his boat" (line 43), establishing Bert's full name. But the character entry uses only "Bert" as canonical name with no aliases. Lincoln's relationship list has "Bert Jenks (ally)" showing the system found the name, but it wasn't used for Bert's entry.
   - Evidence: Line 43 clearly gives the full name.
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` — full name resolution
   - Fix: When a first-name-only character has a full name mentioned elsewhere in the text, the canonical name should be updated to the full name, or at minimum the full name should be an alias.

5. **"kitchen" flagged as pronunciation entry — false positive**
   - Problem: "kitchen" (/ˈkɪtʃən/) is a common English word that doesn't need pronunciation guidance for a narrator. It's not unusual, foreign, or a homograph.
   - Location: `src/pipeline/pronunciation/` — false positive filtering
   - Fix: Common English words should not be flagged. This is a minor false positive.

6. **All character profiles have null physical_description, personality_traits, speech_patterns in JSON**
   - Problem: The JSON `physical_description`, `personality_traits`, and `speech_patterns` fields are all null for every character, yet the HTML report shows rich profile content (appearance, personality, voice guidance). The profile data exists but is stored in different fields than expected.
   - Evidence: `jq '.characters[] | .physical_description' analysis.json` returns null for all, but HTML shows "Lincoln is a sixteen-year-old farm boy..."
   - Location: Likely a data model mismatch — profile data is stored in sub-fields that the JSON serialization handles differently
   - Fix: Not critical for HTML output quality, but the JSON should be consistent. This may be by design (profiles stored in a nested structure).

### LOW
7. **Narrative style says "unknown" in structure overview but "first-person retrospective" in plot summary**
   - Problem: The structure overview says `narrative_style: "unknown"` but the plot summary section correctly identifies it as a third-person narrative (the story is actually third-person limited, focused on Lincoln). The plot summary incorrectly says "first-person retrospective."
   - Evidence: The text uses "he" and "Lincoln" throughout — it's third-person, not first-person. The `pipeline_metadata.narrator_pov` correctly says "third-person."
   - Location: `src/pipeline/chapter_summary/` or `src/analyzer.py` — narrative style detection
   - Fix: Minor inconsistency. The plot summary's "first-person retrospective" label is incorrect — it should be "third-person limited" or "third-person omniscient."

## Fix History
(First attempt — no prior fixes)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| (none yet) | - | - | - |

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (user-configured, DO NOT CHANGE)
- No LLM retries or JSON parse failures in character extraction
- 1 JSON parse failure in pronunciation enrichment (non-critical)
- Profiling was the bottleneck (16m 24s, 43% of total time)
- All confidence scores are high for characters — the pipeline is confident but has a cross-pipeline split issue

## Next Action
Run PROMPT_fix.md to address:
1. CRITICAL: Merge "Milt" into "Milton Jennings" (cross-pipeline alias resolution)
2. HIGH: Fix surname-only alias assignment when multiple characters share the surname
3. HIGH: Fix misattributed profile descriptions
