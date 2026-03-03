# Current Evaluation State

## Active Text
- **Name:** masque_of_red_death
- **Attempt:** 1
- **Phase:** awaiting_analysis
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
1. ~~Critical #1 and #2~~ (FIXED — see Fix History below)
2. ~~High #3~~ (FIXED)
3. ~~High #4~~ (FIXED)
4. Fix Medium #5 — missing IPA on homographs (deferred to next iteration)

## Fix History
### Attempt 2 Fix (this run)

#### Fix 1: Rule 0.5 now only applies to is_symbolic=True objects
- **Problem:** Rule 0.5 semantic coherence check was applied to BOTH symbolic objects AND personified concepts. For personified forces like "the Red Death", this incorrectly blocked valid aliases like "the masked figure" (the Red Death's physical manifestation). Personified forces in literature can legitimately appear under different descriptive names.
- **Fix:** Changed `is_symbolic_or_personified = getattr(profile, "is_symbolic", False) or is_personified_concept(...)` to simply `if getattr(profile, "is_symbolic", False)`. Removed the `is_personified_concept()` function entirely.
- **Root cause:** `src/pipeline/character_extraction_v2/main_cast.py:verify_aliases()` ~line 840
- **Modified:** `src/pipeline/character_extraction_v2/main_cast.py`

#### Fix 2: Improved programmatic is_symbolic detection for multi-word descriptor phrases
- **Problem:** The clock ("the gigantic ebony clock") was LLM-assigned is_symbolic=False despite being a clearly inanimate object. Without is_symbolic=True, Rule 0.5 didn't apply to it, and the clock accepted wrong aliases ("the masked figure", "the Red Death", "the courtiers") from the LLM's Pass 2.
- **Fix:** Added a second programmatic is_symbolic correction: if name = article + 2+ modifier words + core noun where core noun is NOT in a small set of human-descriptor words ("man", "woman", "figure", "ghost", etc.) → is_symbolic=True. "the gigantic ebony clock" matches (4 words, "clock" not human).
- **Root cause:** `src/pipeline/character_extraction_v2/main_cast.py:_extract_two_pass()` ~line 481
- **Smoke test:** Logic verified — clock gets is_symbolic=True; "the old man", "the masked figure", "the Red Death" correctly NOT flagged as symbolic.

#### Fix 3: Narrator detection prompt clarification
- **Problem:** The NARRATOR_DETECTION_PROMPT NOTE said "judge by whose inner thoughts/fears are described" — this caused the LLM to mark Prospero as first-person narrator in the omniscient third-person Masque story, because his inner states (e.g., "shuddering with rage") are described.
- **Fix:** Replaced the ambiguous NOTE with a clearer explanation: first-person = character uses "I" directly; if described as "he/she" even when focusing on their emotions, it's third-person/omniscient.
- **Root cause:** `src/pipeline/character_extraction_v2/narrator.py:NARRATOR_DETECTION_PROMPT`
- **Modified:** `src/pipeline/character_extraction_v2/narrator.py`

#### Fix 4: Pronunciation whitelist additions
- **Problem:** "giddiest", "gaieties", "convulsed", "unutterable" were flagged as needing pronunciation guidance but are standard English words.
- **Fix:** Added these words (and their inflected forms) to COMMON_WORDS_WHITELIST in cmu_proposer.py.
- **Root cause:** `src/pipeline/pronunciation_guide/proposers/cmu_proposer.py:COMMON_WORDS_WHITELIST`
- **Modified:** `src/pipeline/pronunciation_guide/proposers/cmu_proposer.py`

**Test results:** 332 passed, 10 skipped (same pre-existing skips as before — no regressions)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 2 | Red Death missing, clock wrong aliases, narrator wrong, pronunciation FP | main_cast.py, narrator.py, cmu_proposer.py | Awaiting analysis |

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
Re-run analysis to verify fixes
