# Current Evaluation State

## Active Text
- **Name:** monkeys_paw
- **Attempt:** 3
- **Phase:** awaiting_evaluation
- **baseline_score: 5.8**

## Latest Scores
- Structure Detection: 5/10 ✗
- Character Extraction: 4/10 ✗
  - Completeness: 5/10
  - Identity Resolution: 3/10
  - Alias Grouping: 4/10
- Character Profiles: 5/10 ✗
- Chapter Summaries: 7/10 ✗
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 5.8/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (4 categories below threshold)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | FAIL | - | Pipeline crashed |
| 2 | 5.8 | - | First successful run — baseline set |

## Current Issues (Priority Order)

### CRITICAL

1. **Mrs. White completely missing from character list** [Completeness, Identity Resolution]
   - Problem: Mrs. White is a major character who drives the climactic action (demands the 2nd wish, rushes to open the door). She appears in the summary's "Characters" tag but is absent from the character list entirely.
   - Evidence: The analysis notes from attempt 2 state she was "detected, blocked as alias of Mr. White by Rule 0.4 (different titled people), then dropped." Rule 0.4 correctly identified her as different from Mr. White, but she was not retained as a separate character.
   - Location: V2 character extraction pipeline — likely `src/pipeline/character_extraction_v2/main_cast.py` or the orchestration code that handles rejected aliases. When an alias is blocked by Rule 0.4, the rejected name should be checked for independent character status.
   - Fix: When Rule 0.4 (or any rule) blocks an alias because it identifies a DIFFERENT person, the pipeline should create or retain that name as an independent character rather than silently dropping it.

2. **"Herbert White" falsely listed as alias of "Mr. White"** [Identity Resolution, Alias Grouping]
   - Problem: Herbert White (the son, 14 mentions) is incorrectly assigned as an alias of Mr. White (the father, 12 mentions). They are father and son — distinct characters who share a surname.
   - Evidence: `analysis.json` shows Mr. White (main_cast_0) has aliases: ["Herbert White"]. Meanwhile Herbert White also exists as a separate supporting character (supporting_0). This contradictory state means the alias was added but the character wasn't removed.
   - Location: V2 alias resolution in `src/pipeline/character_extraction_v2/main_cast.py` — the LLM proposed "Herbert White" as alias of "Mr. White" and the pipeline accepted it despite them having different first names/titles.
   - Fix: A name like "Herbert White" should NOT be accepted as alias of "Mr. White" — they share a surname but "Herbert" is not a title variant of "Mr." The pipeline should have a rule: if the existing canonical uses a title (Mr./Mrs./Dr.) and the proposed alias uses a different first name, they are likely different people.

3. **3-part structure not detected** [Structure]
   - Problem: The source text has clear section markers "I.", "II.", "III." at lines 45, 284, 411. The pipeline found no structure and treated the entire 3,954-word story as a single untitled chapter.
   - Evidence: `grep -n "^I\.\|^II\.\|^III\." "Test_Texts/The_Monkey's_Paw.txt"` shows markers at lines 45, 284, 411.
   - Location: Structure detection in `src/pipeline/chapter_detection/` — likely the regex patterns in marker detection don't match standalone Roman numeral markers like "I.", "II.", "III." on their own lines.
   - Fix: Add regex pattern for standalone Roman numerals with period (e.g., `^(I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII)\.\s*$`) as valid section markers.

### HIGH

4. **Herbert White classified as supporting instead of main** [Completeness]
   - Problem: Herbert has 14 mentions (highest in the story) and is central to the plot — his death is the pivotal event. He's listed as supporting_0 instead of main cast.
   - Evidence: `analysis.json` shows Herbert White with ID "supporting_0" despite having the most mentions of any character.
   - Location: V2 pipeline main_cast vs supporting classification logic.
   - Fix: May resolve naturally if the Herbert White alias issue (#2) is fixed, since his mentions would no longer be conflated with Mr. White's.

5. **Morris missing full title "Sergeant-Major"** [Alias Grouping]
   - Problem: Canonical name is just "Morris" but the text consistently uses "Sergeant-Major Morris." The title is important for narrator voice (military bearing).
   - Evidence: `analysis.json` shows Morris (supporting_1) with no aliases. The summary correctly uses "Sergeant-Major Morris."
   - Location: V2 character extraction — title detection or canonical name selection.
   - Fix: Pipeline should prefer the full titled form "Sergeant-Major Morris" as canonical, or at minimum include it as an alias.

6. **Mr. White's relationships are wrong/incomplete** [Profiles]
   - Problem: Only relationship listed is "monkey's paw: creation" — which is semantically wrong (Mr. White didn't create the paw). Missing: Herbert (son), Mrs. White (wife), Morris (friend).
   - Evidence: `analysis.json` shows `"relationships": {"the monkey's paw": "creation"}` for Mr. White.
   - Location: Profile generation in `src/analyzer.py` — `_generate_character_profile()`.
   - Fix: Relationship extraction needs to correctly identify family relationships from the text (explicit references to "his son Herbert", "his wife", "his old friend").

### MEDIUM

7. **Herbert White has zero relationships** [Profiles]
   - Problem: No relationships listed despite being Mr. White's son and Mrs. White's son.
   - Evidence: `analysis.json` shows `"relationships": {}` for Herbert White.
   - Location: Profile generation — may improve if character extraction issues are fixed first.

8. **Chapter summary is one block instead of three** [Summaries]
   - Problem: The summary covers the entire story in one 170-word paragraph. A narrator would benefit from per-section summaries for each of the 3 parts.
   - Evidence: Only 1 chapter-card in report.html.
   - Depends on: Fix #3 (structure detection). Once 3 parts are detected, summaries will naturally split.

9. **"rubicund" IPA stress likely incorrect** [Pronunciation]
   - Problem: Listed as /ruːˈbɪkʌnd/ (stress on 2nd syllable) but standard pronunciation is /ˈruː.bɪ.kənd/ (stress on 1st syllable).
   - Location: LLM-generated IPA in pronunciation enricher.

10. **fakir/fakirs listed as separate entries** [Pronunciation]
    - Problem: Both singular "fakir" and plural "fakirs" are listed separately with essentially the same IPA. This is redundant.
    - Location: Pronunciation deduplication logic.

### LOW

11. **Grammar: "This book contains 1 chapters"** [Presentation]
    - Problem: Should be "1 chapter" (singular).
    - Location: HTML template generation.

12. **Monkey's paw labeled "protagonist"** [Profiles]
    - Problem: The monkey's paw is more accurately an antagonistic force/object, not a protagonist. It's the source of tragedy.
    - Location: Role assignment in character extraction.

## Fix History
- Attempt 1 fix: Fixed two crash-level bugs in analyzer.py (CharacterMap constructor) and summarizer.py (undefined `text` variable)
- Attempt 2 fix A: Added `roman_numeral_with_period` regex pattern (`^\s*([IVXLC]+)\.\s*$`, confidence 0.90, hard boundary) to catch "I.", "II.", "III." section markers
  - Root cause: `src/pipeline/chapter_detection/proposers/regex.py` — no pattern matched period-terminated Roman numerals
  - Smoke test: PASS — pattern confirmed added, 381/381 tests pass
- Attempt 2 fix B: Fixed `_are_different_titled_people()` Case 2 to block multi-word untitled names ("Herbert White") from being aliases of titled names ("Mr. White") when they share a surname
  - Root cause: `src/pipeline/character_extraction_v2/main_cast.py:_are_different_titled_people()` lines 2057-2074 — `surname1 in name2_lower` was True for "white" in "herbert white", bypassing the block
  - Smoke test: PASS — all 7 test cases correct (Herbert White, Samuel Johnson, Gatsby, etc.)
- Attempt 2 fix C: Added Rule 1 blocked alias salvage logic — when `_are_different_titled_people()` blocks an alias, the alias is saved and a new character profile is created if not already in cast
  - Root cause: `src/pipeline/character_extraction_v2/main_cast.py:verify_aliases()` — Rule 1 dropped "Mrs. White" without creating a separate character
  - Universal: grounding gate is the safety net (0-mention hallucinations will be rejected)
  - Smoke test: PASS — `_rule1_blocked_names` instance variable present, salvage block present in extract()

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1→2 | Pipeline crash: summarizer `text` undefined | src/pipeline/summarizer.py | Fixed |
| 1→2 | Pipeline crash: CharacterMap invalid kwargs | src/analyzer.py | Fixed |
| 2→3 | Structure: "I.", "II.", "III." not detected | src/pipeline/chapter_detection/proposers/regex.py | Awaiting analysis |
| 2→3 | Characters: Herbert White false alias of Mr. White | src/pipeline/character_extraction_v2/main_cast.py | Awaiting analysis |
| 2→3 | Characters: Mrs. White missing (dropped by Rule 1) | src/pipeline/character_extraction_v2/main_cast.py | Awaiting analysis |

## Configuration Notes
- Model: qwen3-next:80b-a3b-instruct-q8_0 (Ollama) for all agents
- think_mode: false (correct for qwen3 family)
- Temperature: 0.7 across all agents — may be too high for character extraction (consider 0.3-0.5)
- No profiling quality concerns flagged

## Output Files (Attempt 3)
- HTML: ../output/monkeys_paw/report.html
- JSON: ../output/monkeys_paw/analysis.json

## Pipeline Notes (Attempt 3)
- 3 chapters detected ✓ (Roman numeral "I.", "II.", "III." fix confirmed working)
- Mrs. White present as main character (26 mentions) ✓ (Rule 1 salvage fix confirmed working)
- Herbert White listed separately from Mr. White (15 mentions, aliases: Herbert, the son) ✓
- Sergeant-Major Morris with full title in aliases ✓
- Contradictory relationships logged: Mr. White→Herbert White='child' AND Herbert White→Mr. White='child' (both sides assigned 'child' instead of parent/child)
- "Step 6.95 structural narrator fix failed: type object 'ChapterSummarizer' has no attribute '_fix_narrator_attribution'" (minor)
- 6 total characters including Maw and Meggins (added via F6 reconciliation)
- the monkey's paw aliases include 'the stranger' (may be incorrect)
- Run time: 18m 47s

## Next Action
Evaluate attempt 3 output.
