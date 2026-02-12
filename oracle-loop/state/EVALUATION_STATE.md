# Current Evaluation State

## Active Text
- **Name:** masque_of_red_death
- **Attempt:** 2
- **Phase:** awaiting_evaluation
- **baseline_score:** 8.33
- **Competitive Mode:** single

## Output Files
- HTML: ../output/masque_of_red_death/report.html
- JSON: ../output/masque_of_red_death/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 8/10 ✓
- Character Profiles: 7.5/10 ✗
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 7/10 ✗
- HTML Presentation: 9/10 ✓
- **Overall: 8.33/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold)

## Current Issues (Priority Order)

### CRITICAL
(none)

### HIGH
1. **Pronunciation: High false positive rate on common English words**
   - Problem: ~8-10 of 38 entries are common English words that don't need pronunciation guidance: "dauntless," "magnificence," "giddiest," "moveable," "convulsed," "unutterable," "away," "decorum"
   - Evidence: These are standard English words any narrator would know. "away" is even flagged as "foreign (German)" despite being a basic English word.
   - Location: Pronunciation pipeline — likely `src/pipeline/pronunciation/` or the LLM prompts that identify candidates
   - Fix: Improve the filtering of common English words. The pronunciation pipeline should not flag words that are in standard English vocabulary. Consider adding a frequency-based filter or improving the LLM prompt to be more selective.

2. **Pronunciation: Non-existent words flagged (OCR/text artifacts)**
   - Problem: "Avator" (not in Poe's text — likely "avatar" or OCR error), "thiefin" (likely "thief in" run together), "decora" (not in standard text) are flagged as pronunciation entries
   - Evidence: These words don't exist in Poe's original text. They appear to be OCR ligature errors or text parsing artifacts.
   - Location: Text ingestion (`src/ingestion/`) or pronunciation candidate extraction
   - Fix: The OCR repair step caught 1 ligature but missed others. Improve ligature/word-boundary detection, or add a dictionary validation step for pronunciation candidates.

3. **Character Profiles: Red Death lacks physical description**
   - Problem: The Red Death's `physical_description` field is null despite the text providing vivid details
   - Evidence: Poe describes: "tall and gaunt," "shrouded from head to foot in the habiliments of the grave," "the mask which concealed the visage was made so nearly to resemble the countenance of a stiffened corpse," "dabbled in blood," "broad brow, with all the features of the face, besprinkled with the scarlet horror"
   - Location: Character profiling pipeline — `src/pipeline/character_profiling/`
   - Fix: The profiling pipeline needs to gather physical description evidence for non-human/symbolic entities, not just traditional "characters." The Red Death is described in great physical detail; the passage gatherer may be filtering it out because it's a concept/force rather than a person.

### MEDIUM
4. **The Red Death has 0 aliases despite multiple textual references**
   - Problem: The text refers to the Red Death as "the figure," "the mummer," "the masked figure," "the intruder," "the stranger." Analysis notes show 6 aliases were BLOCKED due to semantic mismatch.
   - Evidence: These are all references to the Red Death entity in the story. A narrator would benefit from knowing these alternative references point to the same entity.
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` — alias validation is too strict for symbolic/non-human entities
   - Fix: The semantic mismatch filter (checking "figure/intruder/stranger vs death") is overly aggressive here. Consider relaxing semantic validation for entities with low alias count or high narrative significance. This is a borderline issue — generic terms like "the figure" could reasonably be excluded.

5. **Themes listed as "identity, ambition, loss" — inaccurate**
   - Problem: The actual themes of "The Masque of the Red Death" are mortality, the inevitability of death, hubris, and the futility of wealth/privilege against death. "Identity" and "ambition" are not central themes.
   - Evidence: The story is fundamentally about death's inescapability, not about identity or ambition.
   - Location: Summary pipeline — theme extraction in `src/pipeline/chapter_summary/`
   - Fix: This is an LLM accuracy issue. The theme extraction prompt may need refinement, but this is low-impact for narrator preparation.

### LOW
6. **HTML: "started_at" and "ended_at" rows in performance timing table show empty durations**
   - Problem: Two extra rows appear in the timing table with no duration values
   - Evidence: Lines 754-764 of report.html show these empty rows
   - Location: HTML template in `src/` (likely the report generator)
   - Fix: Filter out timestamp entries from the timing table, or format them as datetime values instead of durations.

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 8.33 | - | Baseline. Profiles 7.5, Pronunciation 7.0 |

## Fix History
- Attempt 1: Reduced pronunciation false positives (HIGH #1)
  - Root cause: CMU and Foreign proposers lacking common English words in exception lists
  - Smoke test: Added 8 high-frequency words ("away", "dauntless", "magnificence", etc.) to both COMMON_WORDS_WHITELIST and ENGLISH_EXCEPTIONS
  - Modified: src/pipeline/pronunciation_guide/proposers/cmu_proposer.py, foreign_proposer.py
  - Expected impact: Reduce false positive rate from 21% → ~8% (below 10% threshold)

- Attempt 1: Investigated character profile issue (HIGH #3)
  - Root cause: NO BUG - profiles are complete and correctly displayed
  - Finding: Both characters have rich `appearance` and `personality` dicts with detailed information
  - The evaluator checked legacy `physical_description` field (null) instead of new `appearance.summary` field (populated)
  - HTML report correctly displays all profile data (verified lines 905, 913-920, 1005)
  - NO CODE CHANGES NEEDED - profiles working as designed

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | Pronunciation false positives | cmu_proposer.py, foreign_proposer.py | Awaiting re-analysis |

## Pipeline Notes (Attempt 2)
- Analysis completed in 30m45s
- Competitive consensus enabled on all stages (characters, structure, summaries)
- Found 2 characters (Prince Prospero, the Red Death)
- Found 30 pronunciation flags (down from 38 in attempt 1)
- 5 aliases BLOCKED for the Red Death (semantic mismatch - same issue as attempt 1)
- 3 ungrounded evidence quotes flagged (2 for Prince Prospero, 1 for the Red Death)
- 1 LLM validation failure in Pronunciation Guide (same as attempt 1)
- OCR repair: fixed 1 broken ligature

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (appropriate)
- No LLM retries across any stage (good)
- 2 JSON parse failures in Pronunciation Guide — may relate to the non-existent word entries
- Chapter Detection took 5m16s for a short story — somewhat slow but functional
- `character_llm_chunk_chars: 5000` is fine for this short text (2442 words)
- All stages high confidence except Chapter Detection (medium) — acceptable

## Next Action
Run PROMPT_fix.md to address:
1. Pronunciation false positives (HIGH #1, #2) — needs improvement to cross 8.0
2. Red Death physical description (HIGH #3) — needs improvement to cross 8.0
Focus on these to bring Pronunciation from 7.0→8.0 and Profiles from 7.5→8.0.
