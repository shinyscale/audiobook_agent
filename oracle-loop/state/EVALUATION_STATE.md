# Current Evaluation State

## Active Text
- **Name:** john_g
- **Attempt:** 2
- **Phase:** awaiting_evaluation
- **baseline_score:** 7.80

## Output Files
- HTML: ../output/john_g/report.html
- JSON: ../output/john_g/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 7/10 ✗
  - Completeness: 7/10
  - Identity Resolution: 10/10
  - Alias Grouping: 7/10
- Character Profiles: 6/10 ✗
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 7/10 ✗
- HTML Presentation: 8.5/10 ✓
- **Overall: 7.80/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold: Characters, Profiles, Pronunciation)

## Current Issues (Priority Order)

### CRITICAL
(None)

### HIGH
1. **Missing character: Captain Adams** [Completeness]
   - Problem: Captain Adams is a named character with dialogue (lines 41-50 of source text) who gives Price the order to ride out. He appears in `characters_present` for the chapter but has no character entry.
   - Evidence: "Sergeant," said Captain Adams, with a half-turn of his desk-chair..." — he has a speaking role and drives the plot.
   - Location: Character extraction pipeline — likely filtered by low mention count (only ~2 mentions). F6 reconciliation should have caught him from `characters_present`.
   - Fix: This may be a threshold issue. Captain Adams appears in the summary's characters_present but wasn't promoted to a character entry.

2. **Wrong role assignments: Price=supporting, Richardson=protagonist** [Profiles]
   - Problem: First Sergeant Price is labeled "supporting" despite being the primary human character who drives all the action. Corporal Richardson is labeled "protagonist" despite appearing only in the final scene.
   - Evidence: Price has 4 mentions but dominates the narrative; Richardson has 4 mentions and only appears at the end.
   - Location: Role assignment logic in character profiling (`src/pipeline/character_extraction_v2/` or `analyzer.py` profile generation)
   - Fix: Role assignment should consider narrative prominence (dialogue lines, action involvement), not just mention count.

3. **Missing Richardson's speech patterns: "soft Southern tongue"** [Profiles]
   - Problem: The text explicitly states Richardson speaks in "his soft Southern tongue" (line 243), but speech_patterns is null.
   - Evidence: Direct quote from text: "rejoined Corporal Richardson, in his soft Southern tongue"
   - Location: Profile generation in `analyzer.py` (`_generate_character_profile`)
   - Fix: The LLM profiler should pick this up from the text. May be a low-confidence profile issue (noted as 0.30 confidence for Richardson).

4. **Missing Richardson's relationships** [Profiles]
   - Problem: Corporal Richardson has empty relationships `{}` but clearly has relationships to both John G. (caregiver) and First Sergeant Price (colleague/fellow caretaker).
   - Evidence: Richardson and Price spend three hours together caring for John G. Richardson is the farrier of the Troop.
   - Location: Profile generation — likely related to low confidence (0.30) for this character.

5. **Missing alias "the Sergeant" for First Sergeant Price** [Alias Grouping]
   - Problem: "the Sergeant" is used extensively throughout the text (lines 34, 83, 93, 100, 107, 114, 123, 136, 171, 187, 194, 196, 198, 208, 238) to refer to Price, but is not listed as an alias.
   - Evidence: 15+ uses of "the Sergeant" in text, all referring to Price.
   - Location: Alias detection in `src/pipeline/character_extraction_v2/main_cast.py` — titled descriptors like "the Sergeant" may be filtered by descriptor-blocking rules.

6. **Wrong IPA for "sharp-fanged"** [Pronunciation]
   - Problem: IPA shows /ʃɑːrp-feɪnd/ but "fanged" is pronounced /fæŋd/, not /feɪnd/.
   - Evidence: Standard English pronunciation — "fang" → /fæŋ/, "fanged" → /fæŋd/.
   - Location: LLM-generated IPA in pronunciation pipeline (`src/pipeline/pronunciation/enricher.py`)
   - Fix: Could add to KNOWN_IRREGULAR_IPA if this is a recurring LLM error, or this may be a one-off LLM mistake.

### MEDIUM
7. **Price→Two Troopers relationship labeled "employee"** [Profiles]
   - Problem: The relationship label "employee" is incorrect for a military context. Should be "subordinate" or "commands".
   - Evidence: Price is the First Sergeant; the troopers follow his orders.
   - Location: Profile generation prompt in `analyzer.py`

8. **Missing IPA for "bolo-toothed" and "produce"** [Pronunciation]
   - Problem: Two pronunciation entries have null IPA values.
   - Location: `src/pipeline/pronunciation/enricher.py` — LLM failed to generate IPA for these.

### LOW
9. **Missing "Johnny boy" alias for John G.** [Alias Grouping]
   - Problem: "Johnny boy" used once (line 161) as an endearment for John G. Minor alias gap.

10. **Voice guidance for John G. (a horse) shows "unknown" for tone/dialect** [Presentation]
    - Problem: Voice guidance section is not meaningful for a non-speaking animal character.
    - This is a minor presentation oddity, not worth fixing.

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 7.80 | N/A | First run — 3 categories failing |

## Fix History
- Attempt 2: Three fixes applied:
  1. **Captain Adams (Completeness)**: F6 adds Captain Adams from `active_characters`, but the post-profiling evidence filter in `_convert_characters()` discards him (mention_count=1 ≤ 5, no evidence, non-main_cast ID). Fixed by exempting characters with `supporting_strategies=["chapter_summary_reconciliation"]` from the evidence filter. Root cause: `analyzer.py:_convert_characters():4086-4096`.
  2. **Alias grouping (Completeness/Alias)**: `_add_title_stripped_aliases` only handled single-word title prefixes. "First Sergeant Price" → words[0]="First" not in titles → no alias added. Extended to handle multi-word compound ranks: adds "Price" and "Sergeant Price" as aliases for "First Sergeant Price". Both survive verify_aliases Rule 2 bypass (substring of canonical). Root cause: `main_cast.py:_add_title_stripped_aliases():1320-1330`.
  3. **IPA sharp-fanged (Pronunciation)**: LLM produced /ʃɑːrp-feɪnd/ (treating "-fanged" like silent-g "feigned"). Added "sharp-fanged" and "fanged" to KNOWN_IRREGULAR_IPA with correct /ˈʃɑːrp.fæŋd/. Root cause: `enricher.py:KNOWN_IRREGULAR_IPA`.
  - Smoke test: Logic verified by code trace; cannot run full pipeline without re-analysis.
  - Note: Profiles at 6/10 likely needs re-run — Richardson's profile data is trapped in `descriptions[0].text` as malformed JSON (LLM output parsing failure at low confidence=0.30). Role assignments (Price=supporting, Richardson=protagonist) are LLM decisions not fixed by current code.

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 2 | Captain Adams, alias grouping, IPA | analyzer.py, main_cast.py, enricher.py | Awaiting re-analysis |

## Configuration Notes
- Model: qwen3-next:80b-a3b-instruct-q8_0 (all agents)
- Config: max_tokens=8192, context_length=32768, think_mode=false
- No LLM retries needed (0 retries across all stages)
- Character Profiles took 669s (11 min) — disproportionately long for 4 characters
- Richardson profile has LOW confidence (0.30) — likely root cause of missing speech patterns and relationships

## Pipeline Notes (Attempt 2)
- Captain Adams: NOW PRESENT (fix worked) — 1 mention
- Price aliases: "Price, Sergeant Price" listed (compound rank fix worked)
- "the Sergeant" alias still NOT listed — still open issue
- Character Profiles: 3H/1M confidence (Richardson still medium confidence)
- Pronunciation: 13 flags (7 homograph, 5 unknown, 1 proper_noun)
- Run time: 11m 55s

## Next Action
Run PROMPT_evaluate.md to score attempt 2.
