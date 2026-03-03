# Current Evaluation State

## Active Text
- **Name:** a_camping_trip
- **Attempt:** 1
- **Phase:** awaiting_fix
- **baseline_score:** 7.80
- **Competitive Mode:** none

## Output Files
- HTML: ../output/a_camping_trip/report.html
- JSON: ../output/a_camping_trip/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 6.5/10 ✗ (FAILING)
  - Completeness: 7/10
  - Identity Resolution: 6/10
  - Alias Grouping: 6/10
- Character Profiles: 7/10 ✗ (FAILING)
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 7/10 ✗ (FAILING)
- HTML Presentation: 9/10 ✓
- **Overall: 7.80/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold: Characters, Profiles, Pronunciation)

## Current Issues (Priority Order)

### CRITICAL
1. **False split: "Milt" (supporting_4) is separate from "Milton Jennings" (main_cast_1)** [Identity Resolution]
   - Problem: "Milt" is listed as a separate character with 2 mentions, but it's clearly a nickname for Milton Jennings. Text evidence: line 29 "Hello, Milt," Lincoln returned" — Lincoln addresses Milton as "Milt" in dialogue. Line 54 "if you don't mind, Milt" — same pattern.
   - Evidence: "Milt" is a standard truncation of "Milton" (like "Jim" for "James")
   - Location: `src/pipeline/character_extraction_v2/` — nickname-to-formal merge logic. Check if "Milt"→"Milton" is in NICKNAME_TO_FORMAL dict. Also `src/agents/characters.py` Step 5.5a `_merge_formal_name_aliases()`.
   - Fix: Add "milt"→"milton" to the NICKNAME_TO_FORMAL dictionary, or improve the truncation-matching logic to recognize single-syllable truncations of multi-syllable names.

2. **Bogus alias: "the storm" listed as alias for "the boat-keeper" (main_cast_5)** [Alias Grouping]
   - Problem: "the storm" is a weather event in the story, not an alias for the boat-keeper character. These are completely unrelated concepts.
   - Evidence: The boat-keeper appears at line 473 ("The boat-keeper jeered at them"). The storm is a weather event described from lines 338-470. They are not the same entity.
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` — verify_aliases should block this. The core noun "storm" vs "boat-keeper" should trigger Rule 0.5.
   - Fix: Investigate why verify_aliases didn't block this. The storm/boat-keeper core nouns share no overlap. This may be a Pass 2 LLM hallucination that bypassed verification.

### HIGH
3. **Missing characters: Mr. Stewart, Mr. Jennings, Mrs. Jennings** [Completeness]
   - Problem: Three named, speaking characters are entirely absent from the output.
   - Evidence:
     - Mr. Stewart (Lincoln's father): line 69 "Mr. Stewart had consented" — named, grants trip permission
     - Mr. Jennings (Milton's father): lines 136-137 "said Mr. Jennings" — named, has dialogue
     - Mrs. Jennings (Milton's mother): lines 117, 120-126, 525-526 "said she" — named, multiple lines of dialogue
   - The summarizer listed "Lincoln's father" in characters_present but not by proper name. Mr./Mrs. Jennings completely absent from characters_present.
   - Location: Summarizer prompt (summary not capturing all named characters) + character extraction thresholds
   - Fix: These are low-mention characters (1-2 mentions each by proper name) but have dialogue. They may be below the extraction threshold. Check if the summarizer can be encouraged to use proper names, or if F6/F6b reconciliation thresholds need adjustment for short texts.

4. **Wrong narrator flag on Lincoln Stewart** [Identity Resolution]
   - Problem: Lincoln Stewart is flagged as `is_narrator: true`, but this is a third-person narrative.
   - Evidence: The story uses third-person pronouns throughout: "Lincoln was tired. His neck ached" (line 17), "Lincoln was so tickled he not only leaped the fence" (line 61). The final commentary "Of such changeful stuff are the plans of youth!" (line 537) is from an omniscient third-person narrator, not Lincoln.
   - The HTML summary incorrectly says "Lincoln Stewart begins his recollection" — treating it as first-person when it's not.
   - Location: Narrator detection logic in the pipeline
   - Fix: The narrator detector may be conflating "third-person limited protagonist" with "first-person narrator". For a story with no first-person pronouns ("I", "my"), no character should be flagged as narrator.

5. **Missing pronunciation entries for archaic/nautical terms** [Pronunciation]
   - Problem: Several words important for narrator prep are not flagged:
     - "bowlders" (lines 234, 293) — archaic spelling of "boulders", narrator needs to know to pronounce it as "boulders"
     - "popple" (line 20) — dialectal/regional word for "poplar tree", unusual word
     - "luff" (line 454) — nautical term, even has a footnote [111-1] in the text indicating it needs explanation
     - "gunwhale" (line 409) — commonly mispronounced; correct pronunciation is "GUN-ul" not "gun-whale"
   - Location: Pronunciation pipeline — CMU proposer + LLM proposer
   - Fix: These words are genuinely unusual and should be caught by the CMU proposer (unlikely to be in CMU dict). Investigate why they were missed — possibly filtered out or below confidence threshold.

### MEDIUM
6. **"Knapp" should be "Captain Knapp"** [Alias Grouping]
   - Problem: The character is listed as "Knapp" (supporting_5) but is always referred to as "Captain Knapp" in the text (lines 45, 103).
   - Fix: Title should be retained in canonical name. Check if title-stripping is too aggressive for military/rank titles.

7. **Missing speech patterns/dialect notes** [Profiles]
   - Problem: No speech_patterns noted for any character, but the text is rich in dialect: g-dropping ("goin'", "workin'", "talkin'"), contractions ("ain't", "d'ye", "see't"), informal speech patterns. This is highly relevant for audiobook narrator preparation.
   - Location: Character profiling prompt in analyzer.py
   - Fix: The profiler should detect and note dialectal speech when present. This may improve naturally if other fixes raise quality.

8. **"Stewart" as standalone alias for Lincoln Stewart** [Alias Grouping]
   - Problem: Lincoln is never called just "Stewart" in the text. The surname "Stewart" only appears in "Mr. Stewart" (his father). This alias could cause confusion.
   - Location: Alias generation in V2 pipeline — programmatic surname-as-alias logic
   - Fix: Minor; the surname-as-alias logic should check if another character uses that surname with a title.

9. **Fabricated relationship: boat-keeper ↔ Knapp** [Profiles]
   - Problem: The boat-keeper's profile lists "Knapp: associated" as a relationship, but these characters never interact in the text.
   - Location: Profile generation in analyzer.py — the LLM is fabricating co-occurrence relationships
   - Fix: This is a known pattern (see MEMORY.md on profile generation). May resolve with other character fixes.

### LOW
10. **"wildernesses" flagged as pronunciation entry** [Pronunciation]
    - Problem: Standard English word, false positive
    - Fix: Add to COMMON_WORDS_WHITELIST in cmu_proposer.py

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 7.80 | - | Baseline. 3 categories failing: Characters (6.5), Profiles (7), Pronunciation (7) |

## Fix History
(No fixes yet — first attempt)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| (none yet) | - | - | - |

## Next Action
Run PROMPT_fix.md to address Critical #1 (Milt/Milton false split), Critical #2 (the storm bogus alias), and High #3-5 (missing characters, wrong narrator, missing pronunciation entries). Fixing the character extraction issues is the highest priority since Characters (6.5) is the furthest below threshold.
