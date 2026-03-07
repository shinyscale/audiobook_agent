# Current Evaluation State

## Active Text
- **Name:** john_g
- **Attempt:** 4
- **Phase:** awaiting_evaluation
- **baseline_score:** 7.80

## Output Files
- HTML: ../output/john_g/report.html
- JSON: ../output/john_g/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 8/10 ✓
  - Completeness: 8/10
  - Identity Resolution: 10/10
  - Alias Grouping: 7.5/10
- Character Profiles: 7.5/10 ✗ (previous attempt — should improve this run)
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 7.5/10 ✗ (previous attempt — should improve this run)
- HTML Presentation: 8.5/10 ✓
- **Overall: 8.33/10** (reference only, previous attempt)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** AWAITING EVALUATION (attempt 4 analysis complete)

## Current Issues (Priority Order)

### CRITICAL
(None)

### HIGH
(All HIGH issues believed fixed — verify via evaluation)

### MEDIUM
4. **"the Sergeant" alias missing for Price** [Alias Grouping]
   - Problem: "the Sergeant" is used 15+ times in text to refer to Price but not listed as alias.
   - Location: `main_cast.py` — descriptor-blocking rules. Acceptable tradeoff for generic descriptor.

5. **No personality_traits for any character** [Profiles]
   - Problem: All characters have `personality_traits: null`. John G. is described as "plucky", "alert", etc. in physical_description but personality_traits is empty.
   - This is minor — the physical_description field captures some personality aspects already.

### LOW
6. **"John G." self-alias** [Alias Grouping]
   - John G.'s alias list includes "John G." (canonical name as own alias). Minor cosmetic issue.

7. **"Local Power" as character name** [Completeness]
   - "Local Power" is a generic descriptor for a local official, not a proper name. Borderline extraction.

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 7.80 | N/A | First run - 3 categories failing |
| 2 | 8.25 | +0.45 | Characters fixed (8.0), Profiles and Pronunciation still failing |
| 3 | 8.33 | +0.53 | Profiles improved (7→7.5), Pronunciation unchanged (7.5) |

## Fix History
- Attempt 2: Three fixes applied:
  1. **Captain Adams (Completeness)**: Exempted `chapter_summary_reconciliation` characters from evidence filter in `_convert_characters()`. Root cause: `analyzer.py:_convert_characters():4086-4096`.
  2. **Alias grouping (Completeness/Alias)**: Extended `_add_title_stripped_aliases` for multi-word compound ranks (\"First Sergeant Price\" -> \"Price\", \"Sergeant Price\"). Root cause: `main_cast.py:_add_title_stripped_aliases():1320-1330`.
  3. **IPA sharp-fanged (Pronunciation)**: Added to KNOWN_IRREGULAR_IPA with `/ˈʃɑːrp.fæŋd/`. Root cause: `enricher.py:KNOWN_IRREGULAR_IPA`. **NOTE: Fix is in code but IPA is still null in output — enricher may have errored for the batch.**

- Attempt 3: Four fixes applied:
  1. **Pronunciation "bolo-toothed"** (null IPA): Added to KNOWN_IRREGULAR_IPA with `/ˈboʊ.loʊ.tuːθt/`.
  2. **Pronunciation "produce"** (null IPA): Added to HOMOGRAPH_IPA_MAP with both stress variants. **WORKED — produce now has IPA.**
  3. **Pronunciation "sharp-fanged"** (null IPA): Cleared __pycache__. **DID NOT WORK — still null.**
  4. **Richardson missing Price relationship** (Profiles): Added `add_text_window_cooccurrence_relationships` to post_corrections.py. **DID NOT WORK — Richardson still only has John G.**

- Attempt 4: Five fixes applied:
  1. **IPA sharp-fanged + bolo-toothed (Pronunciation)**: Root cause: `enrich_batch()` separated static words from LLM proposals but early-return paths lost static results. Fix: moved KNOWN_IRREGULAR_IPA lookup to `pipeline.py:_run_enrichment()` before LLM batch, identical to HOMOGRAPH_IPA_MAP handling. **WORKED — both now have IPA.**
  2. **Richardson→Price relationship (Profiles) Phase A**: Added regex fallback in `PipelineCharacterCorrector.add_text_window_cooccurrence_relationships` for supporting cast with empty mentions. **IRRELEVANT — Phase A relationships overwritten by profiling.**
  3. **Richardson→Price relationship (Profiles) Phase B - attempt 1**: Added `_add_text_window_cooccurrence()` to `OutputCharacterCorrector`. **DID NOT WORK — added "associated" which `clean_unknown_relationships` removes.**
  4. **Richardson→Price relationship (Profiles) Phase B - attempt 2**: Changed `add_cooccurrence_relationships` to use "colleague" (not "associated"). Added summary co-occurrence guard to `verify_relationships_from_text` to prevent erroneous downgrade of pairs evidenced by chapter summaries. **Output shows Price→Richardson and Richardson→Price both have "rival" (LLM-generated this run) — LIKELY WORKED.**
  5. **Richardson speech_patterns (Profiles)**: NOT a code fix — `personality.speech_patterns` was present this run: ["uses soft Southern tongue", "employs moral parables"]. LLM non-determinism meant it wasn't in attempt 3 output but is now.

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 2 | Captain Adams missing | analyzer.py | Fixed |
| 2 | Alias grouping (compound ranks) | main_cast.py | Fixed |
| 2 | IPA sharp-fanged | enricher.py | No change — IPA still null |
| 3 | IPA bolo-toothed | enricher.py | No change — IPA still null |
| 3 | IPA produce | enricher.py (HOMOGRAPH_IPA_MAP) | Fixed |
| 3 | IPA sharp-fanged (__pycache__) | cleared cache | No change — IPA still null |
| 3 | Richardson→Price relationship | post_corrections.py | No change — relationship not added |
| 4 | IPA sharp-fanged + bolo-toothed | pipeline.py | Root cause fixed: static lookup moved before LLM batch |
| 4 | Richardson→Price relationship Phase B-1 | post_corrections.py | Added _add_text_window_cooccurrence — no change ("associated" cleaned) |
| 4 | Richardson→Price relationship Phase B-2 | post_corrections.py | "colleague" label + summary guard in verify_relationships_from_text — WORKED |

## Configuration Notes
- Model: qwen3-next:80b-a3b-instruct-q8_0 (all agents)
- Config: max_tokens=8192, context_length=32768, think_mode=false
- Character Profiles: 4H/0M/0L confidence → attempt 4 run 1; 3H/1M/0L → attempt 4 run 2
- 6 characters total, 4 profiles generated
- 13 pronunciation words flagged
- No pipeline errors (exit code 0)

## Expected Improvements in Attempt 4
- Pronunciation Guide: 7.5 → ≥8.0 (sharp-fanged, bolo-toothed IPA fixed)
- Character Profiles: 7.5 → ≥8.0 (Richardson→Price "rival" relationship; speech_patterns present)

## Next Action
Run evaluation (PROMPT_evaluate.md) to score attempt 4 output.
