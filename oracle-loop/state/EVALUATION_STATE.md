# Current Evaluation State

## Active Text
- **Name:** masque_of_red_death
- **Attempt:** 1
- **Phase:** awaiting_fix
- **baseline_score:** 6.85
- **Competitive Mode:** none

## Output Files
- HTML: ../output/masque_of_red_death/report.html
- JSON: ../output/masque_of_red_death/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 3/10 ✗ (FAILING — catastrophic)
  - Completeness: 4/10
  - Identity Resolution: 2/10
  - Alias Grouping: 1/10
- Character Profiles: 5/10 ✗ (FAILING)
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 7.5/10 ✗ (FAILING)
- HTML Presentation: 8/10 ✓
- **Overall: 6.85/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold)

## Current Issues (Priority Order)

### CRITICAL
1. **The Red Death / masked figure is MISSING as a character** [Completeness]
   - Problem: The primary antagonist of the story — the personified Red Death plague that appears as a masked figure at the ball — is not extracted as a character at all
   - Evidence: The text describes it extensively: "tall and gaunt," "shrouded from head to foot in the habiliments of the grave," mask "resembling the countenance of a stiffened corpse," "dabbled in blood." It confronts Prospero and kills everyone. It is the most important entity after Prospero himself
   - Expected: A character entry for "the Red Death" with aliases "the masked figure", "the figure", "the intruder", "the mummer"
   - Location: `src/pipeline/character_extraction_v2/` — the LLM extraction or post-processing pipeline failed to produce this as a separate character. The EVALUATION_STATE pipeline notes show these aliases were BLOCKED from merging due to "symbolic entity core-noun mismatch" — so the pipeline tried but the blocking logic prevented correct grouping
   - Fix: The Red Death needs to be extracted as its own character. The blocking logic for symbolic entities may be too aggressive for personified forces that are clearly distinct characters

2. **Catastrophic false merge: clock absorbed Red Death, masked figure, courtiers** [Identity Resolution, Alias Grouping]
   - Problem: "the gigantic ebony clock" (main_cast_5) has aliases: "the clock", "the masked figure", "the figure", "the Red Death", "the courtiers" — 4 of 5 aliases are completely wrong entities
   - Evidence: The clock is an inanimate object in the black room. The masked figure is the antagonist. The Red Death is the plague personified. The courtiers are Prospero's guests. None of these are the clock
   - Location: `src/pipeline/character_extraction_v2/` — Pass 2 alias resolution or the LLM proposer incorrectly merged unrelated entities. `verify_aliases` in `main_cast.py` should have blocked these but didn't
   - Fix: The alias merge validation needs to prevent merging entities with fundamentally different natures (inanimate object ≠ person/force ≠ collective group). Also, "the courtiers" should never be an alias of a single object

### HIGH
3. **Prince Prospero incorrectly tagged as First-Person Narrator** [Profiles]
   - Problem: Prospero is marked `is_narrator: true` and displayed as "First-Person Narrator" in the HTML
   - Evidence: "The Masque of the Red Death" has a third-person omniscient narrator. Prospero is a character IN the story but does not narrate it. The text never uses first person from Prospero's perspective
   - Location: Narrator detection in the summary/analysis pipeline — likely `src/analyzer.py` narrator detection or the LLM-based narrator identification
   - Fix: Third-person narration should result in no character being tagged as narrator, or a note that the narrator is omniscient third-person

4. **Pronunciation false positives: common English words flagged** [Pronunciation]
   - Problem: "giddiest", "gaieties", "convulsed", "unutterable" are common English words that don't need pronunciation guidance
   - Evidence: These are standard vocabulary any English-speaking narrator would know
   - Location: `src/pipeline/pronunciation/cmu_proposer.py` — COMMON_WORDS_WHITELIST
   - Fix: Add "giddiest", "gaieties", "convulsed", "unutterable" to COMMON_WORDS_WHITELIST

### MEDIUM
5. **Two pronunciation entries missing IPA** [Pronunciation]
   - Problem: "produce" and "deliberate" have `null` IPA values
   - Evidence: These are homograph entries that should have IPA for both pronunciations
   - Location: Pronunciation pipeline IPA generation
   - Fix: Ensure homograph entries always get IPA populated

6. **Missing pronunciation: "arabesque"** [Pronunciation]
   - Problem: "arabesque" is used in the story and is a moderately unusual word relevant to Poe's aesthetic vocabulary
   - Location: Pronunciation pipeline detection
   - Fix: Low priority; may be in CMU dictionary already

## Priority Fix Order
1. Fix Critical #1 and #2 together — these are the same root cause (Red Death not extracted as separate character, wrong aliases on clock)
2. Fix High #3 — narrator detection for third-person stories
3. Fix High #4 — pronunciation false positives
4. Fix Medium #5 — missing IPA on homographs

## Fix History
(First attempt — no prior fixes)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| (none yet) | - | - | - |

## Pipeline Notes
- Analysis completed in 19m 59s (2,449 words — short story)
- Found 1 chapter (single continuous narrative, correct)
- Found 2 characters: Prince Prospero (6 mentions) and "the gigantic ebony clock" (16 mentions)
- BLOCKED alias warnings during character extraction showed the pipeline DID detect "the intruder", "the Red Death", "a masked figure" but blocked them from correct grouping
- "Failed to generate plot summary via LLM" (minor — narrator detection fallback)
- 0 LLM retries, high confidence on both characters
- Model: qwen3.5:122b-a10b for characters/summaries/profiles, qwen3.5:35b-a3b for structure/pronunciation

## Configuration Audit
- Models appropriate (122b for character extraction is the larger model)
- Context length 32768 is plenty for a 2,449-word short story
- Temperature 0.7 is standard
- No chunking issues (story fits in single chunk)
- No LLM retries — the model confidently produced wrong results
- 1 JSON parse failure in chapter detection (minor)

## Next Action
Run PROMPT_fix.md to address character extraction (Critical #1 and #2 — Red Death missing, wrong aliases on clock)
