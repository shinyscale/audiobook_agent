# Current Evaluation State

## Active Text
- **Name:** john_g
- **Attempt:** 4
- **Phase:** awaiting_evaluation
- **baseline_score:** 7.55
- **Competitive Mode:** single

## Output Files
- HTML: ../output/john_g/report.html
- JSON: ../output/john_g/analysis.json
- Timestamped: ../output/John G - Katherine Mayo_20260222_232326/

## Pipeline Notes
- Completed in 11m 25s, 21 LLM calls, 31,600 tokens
- 2,228 words extracted (short text)
- 1 chapter detected (single chapter story)
- 5 characters total (John G. + 4 others)
- John G. (aka John) - 19 mentions ✓
- 13 pronunciation flags (7 homograph, 6 unknown)
- Universal deterministic age extraction applied (attempt 4 fix)

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 8.5/10 ✓
  - Completeness: 9/10
  - Identity Resolution: 9/10
  - Alias Grouping: 8/10
- Character Profiles: 7.5/10 ✗ (FAILING)
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 8.40/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (1 category below threshold: Profiles 7.5)

## What Improved (Attempt 2 → 3)
- Pronunciation: 6.5/10 → 8.0/10 (+1.5) — Greensburg removed, 6 false positives eliminated
- Verbal tics for John G.: empty list now (was Price's dialogue attributed to horse) ✓
- Overall: 8.15 → 8.40 (+0.25)

## What Didn't Improve
- age_indication for John G.: still "unknown" despite prompt format hint change — the LLM ignored the new hint
- sharp-fanged IPA: still wrong (`/feɪnd/` should be `/fæŋd/`)
- John G. still missing from chapter characters_present
- Richardson→John G. relationship still "unknown" from John G.'s perspective
- Richardson-Price relationship still characterized as "conflict"

## Current Issues (Priority Order)

### HIGH
1. **John G. age_indication still "unknown" — attempt 3 fix didn't take effect** [Profiles]
   - Problem: `age_indication: "unknown"` but John G. is explicitly 22 years old. The text says: "if you counted his twenty-two years by human standards he would be eighty-eight."
   - Evidence: The attempt 3 fix changed the format hint in `analyzer.py` and `generator.py` to accept exact ages, but the LLM still returned "unknown". The fix may not have been in the active codepath, or the LLM may need stronger prompting.
   - Location: Need to trace the ACTUAL codepath that generates `age_indication` for this text. Check:
     - `character_profiling/generator.py` — is the modified prompt actually being used?
     - `analyzer.py:3416, 3820` — are these the lines that run during profiling for this text?
     - Verify by adding a debug print or checking if the modified prompt appears in logs
   - Fix: The prompt change alone wasn't sufficient. Consider:
     (a) Adding "If the text states an explicit age (e.g. '22 years old'), use that exact value" to the prompt
     (b) Post-processing: scan evidence quotes for age patterns and override "unknown"
     (c) Verify the fix is in the right codepath — `age_indication` may be set by a DIFFERENT code section than what was modified
   - **This is the ONLY blocking issue.** Fixing this alone could push Profiles to 8.0.

2. **Richardson-Price relationship inaccurate** [Profiles]
   - Problem: Listed as "subordinate to / in professional conflict with" — the "conflict" characterization is wrong. The text shows mutual respect and philosophical exchange, not conflict.
   - Evidence: Richardson's dialogue with Price is warm and reflective, not adversarial
   - Location: Profile generation LLM output
   - Fix: LLM accuracy issue — hard to fix generically. Lower priority than age fix.

### MEDIUM
3. **John G.→Richardson relationship "unknown"** [Profiles]
   - Problem: Richardson→John G. = "caretaker" (correct), but John G.→Richardson = "unknown" (should be reverse: "cared for by" or similar)
   - Location: Profile generation — bidirectional relationship consistency
   - Fix: Post-processing: if A→B has a relationship, infer B→A reverse. Generic fix in relationship builder.

4. **sharp-fanged IPA wrong** [Pronunciation]
   - Problem: `/ʃɑːrp-feɪnd/` "SHARP-FAYND" — "fanged" should be /fæŋd/ (rhymes with "banged"), not /feɪnd/
   - Evidence: Standard American English: "fanged" = /fæŋd/. Note also wrong: says it "rhymes with 'fained'"
   - Location: Pronunciation LLM generation
   - Fix: LLM accuracy issue; doesn't block passing since Pronunciation is at 8.0

5. **John G. missing from chapter characters_present** [Presentation]
   - Problem: Chapter 1's characters list shows Price, Adams, Richardson, Two Troopers — but NOT John G., the title character and protagonist with 19 mentions
   - Evidence: HTML chapter card lists 4 characters, John G. absent
   - Location: Chapter summary character extraction (the characters_present list is generated during summary phase)
   - Fix: The summary text mentions John G. prominently but the extraction missed him. May be an LLM extraction issue in summary agent.

### LOW
6. **Missing pronunciation: "Allegheny"** — river name, commonly mispronounced
7. **"Tien Tsin" only partially flagged** — "Tsin" captured but not full "Tien Tsin"
8. **fetlock IPA uses British vowel** — `/ˈfɛt.lɒk/` should use American `/ˈfɛt.lɑːk/`

## Priority for Fix Phase

**To get Profiles from 7.5 → 8.0:** Fix issue #1 (age_indication). This is the single blocking issue. The age is explicitly stated in the text and should be captured. The attempt 3 prompt change didn't work — the fix phase needs to:
1. TRACE the actual codepath that sets `age_indication` for this text
2. Verify the modified code is actually being executed
3. Apply a stronger fix (either better prompting or post-processing extraction)

All other categories are at 8.0+. Only Profiles needs to improve.

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 7.55 | — (baseline) | 3 categories failing: Characters 6, Profiles 7, Pronunciation 7 |
| 2 | 8.15 | +0.60 | 2 categories failing: Profiles 7.5, Pronunciation 6.5. Character extraction fixed (+2.5) |
| 3 | 8.40 | +0.85 | 1 category failing: Profiles 7.5. Pronunciation fixed (+1.5). age_indication fix didn't work. |

## Fix History
- Attempt 2: Three fixes applied:
  1. **Newline normalization in NER entity names** — `supporting.py:extract():116`: changed `ent.text.strip()` to `re.sub(r"\s+", " ", ent.text).strip()`. **RESULT: FIXED** ✓
  2. **First-name+initial merge in supporting cast** — `characters.py:_merge_within_supporting_cast():~2681`: Added "firstname of initial name" pattern. **RESULT: FIXED** ✓
  3. **Greensburg German IPA fix** — `foreign_proposer.py:_validate_with_llm():264`: Updated LLM validation prompt for proper nouns. **RESULT: NO CHANGE** ✗ — Greensburg still has German IPA. Fix was in wrong codepath.
- Attempt 3: Three fixes applied:
  1. **Remove "-burg"/"-berg" from German suffix patterns** — `foreign_proposer.py:FOREIGN_PATTERNS["German"]`. **RESULT: FIXED** ✓ — Greensburg removed entirely.
  2. **Skip CMU-known words in CharacterProposer** — `character_proposer.py:__init__()`, `pipeline.py`. **RESULT: FIXED** ✓ — 6 false positives eliminated.
  3. **Improve age_indication prompt format hint** — `analyzer.py:3416`, `analyzer.py:3820`, `character_profiling/generator.py:129`. **RESULT: NO CHANGE** ✗ — age_indication still "unknown". Fix may not be in active codepath.

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 2 | false split John/John G. | supporting.py, characters.py | Fixed ✓ |
| 2 | newline alias | supporting.py | Fixed ✓ |
| 2 | Greensburg German IPA | foreign_proposer.py | No change ✗ — wrong codepath |
| 3 | Greensburg German IPA | foreign_proposer.py:FOREIGN_PATTERNS | Fixed ✓ — entry removed |
| 3 | false positive pronunciation entries | character_proposer.py, pipeline.py | Fixed ✓ — CMU filter works |
| 3 | John G. age "unknown" | analyzer.py, character_profiling/generator.py | No change ✗ — prompt hint ignored |

**PATTERN ALERT:** `age_indication` has been modified once (attempt 3) with no effect. The fix phase modified `analyzer.py` and `generator.py` but the LLM still outputs "unknown". Before attempting another prompt change, the fix phase MUST:
1. Confirm which codepath actually generates this field
2. Add debug logging or verify the modified prompt is being sent to the LLM
3. Consider a deterministic post-processing approach instead of relying on LLM

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (Ollama) for all stages — reasonable
- Profile generation: 9 LLM calls, 0 retries — healthy
- Character extraction: 2 LLM calls, 0 retries — fine for short text
- No concerning retry counts or parse failures

## Next Action
Re-run analysis to verify age_indication fix. Attempt 4 fix applied (see Fix History).

## Attempt 4 Fix Applied

**Phase:** awaiting_analysis

### Fix: Universal deterministic age extraction (analyzer.py)
- **Root cause:** Narrator appearance injection (lines 2578-2582) only runs for `is_narrator` characters and only matches qualitative keywords ("elderly", "old", "young"). Non-narrator characters like John G. (`supporting_0`) had no age post-processing fallback.
- **Fix type:** Algorithmic (deterministic post-processing) — universal, not book-specific
- **Modified:** `src/analyzer.py` — added universal age extraction pass after narrator appearance injection loop
- **What it does:** After all profiles are generated, iterates any character with `age_indication == "unknown"` or "". For each, searches `doc.text` near name occurrences for age patterns (both numeric: "22 years old", "22-year-old", and written: "twenty-two years old"). Updates `age_indication` if found.
- **Universality:** Works for any book with explicit age mentions regardless of genre, era, or vocabulary
- **Smoke test:** Regex unit tests pass for all forms including "twenty-two years old" and "twenty-two-year-old" ✓
- **Regression check:** All 139 non-pre-existing tests pass ✓
