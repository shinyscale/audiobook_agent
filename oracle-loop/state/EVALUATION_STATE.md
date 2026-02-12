# Current Evaluation State

## Active Text
- **Name:** monkeys_paw
- **Attempt:** 3
- **Phase:** awaiting_fix
- **baseline_score:** 6.98

## Output Files
- HTML: ../output/monkeys_paw/report.html
- JSON: ../output/monkeys_paw/analysis.json

## Latest Scores
- Structure Detection: 8.5/10 ✓
- Character Extraction: 9/10 ✓
- Character Profiles: 8.5/10 ✓
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 7.5/10 ✗ (FAILING)
- HTML Presentation: 8/10 ✓
- **Overall: 8.48/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (1 category below threshold)

## Evaluation Details

### Structure Detection: 8.5/10 ✓

Unchanged from attempt 2. 3 parts correctly detected (I, II, III). Chapter 1 has title "I" but chapters 2 and 3 have `null` titles (should be "II" and "III"). Structure itself is correct and summaries are properly split.

### Character Extraction: 9/10 ✓

All significant characters correctly identified:
- **Main cast (6):** Mr. White (26 mentions), Herbert White (29), Mrs. White (10), Sergeant-Major Morris (13), the stranger (2), the monkey's paw (10)
- Aliases well-grouped: Mr. White = "the old man", "the husband"; Herbert = "Herbert", "son"; Morris = "Morris", "the sergeant-major"; the paw = "the paw"

Minor: Chapter 3's `characters_present` uses "the old man" and "the old woman" instead of canonical names. "the old woman" is NOT an alias of Mrs. White.

### Character Profiles: 8.5/10 ✓

Excellent structured profiles with `appearance`, `personality`, and `voice_guidance` sections:
- Mr. White: "thin grey beard", "frail physical presence", voice "quiet, trembling...shifts from gentle and weary to panicked and desperate" — all accurate
- Morris: relationship correctly "acquaintance" (not "victimizer")
- No spectacles hallucination, no misattributed quotes
- Rich voice guidance with dialect notes, verbal tics, example quotes

Minor: "the stranger" described as having "no visible empathy or remorse" — text says he was "visibly uneasy", suggesting discomfort, not cold indifference. Minor LLM interpretation issue.

### Chapter Summaries: 9/10 ✓

All 3 summaries accurate, detailed, and useful for narrator preparation:
- **Part I:** Correctly captures chess game, Morris's arrival, paw backstory, first wish, paw twisting
- **Part II:** Accurately describes Herbert leaving, stranger from Maw & Meggins, Herbert's death, £200 compensation
- **Part III:** Correctly captures grief, second wish, knocking, frantic search for paw, third wish, empty road

No hallucinated events. Good atmosphere. Appropriate length (130-180 words each).

### Pronunciation Guide: 7.5/10 ✗ (FAILING)

**Improvement from attempt 2:** 3 false positives removed (sideboard, sightless, mantelpiece). Fix confirmed working.

**Good entries (20/22):**
- Proper nouns: Herbert, Sergeant-Major, Morris, Meggins — all useful for narrator
- Essential story terms: fakir, antimacassar, rubicund — uncommon words correctly flagged
- Useful uncommon words: condoling, condoled, shamefacedly, betokened, avaricious, bibulous, apathetically, unlooked-for, Leastways, instalment
- Homographs: live, minute, separate — context-dependent pronunciation noted

**Remaining problems (2/22):**
1. **"himselfin"** — text processing artifact (should be "himself in"). Non-word with generated IPA.
2. **"beliefin"** — text processing artifact (should be "belief in"). Non-word with generated IPA.

These are upstream text refinement bugs, not pronunciation system failures. The pronunciation system correctly flagged them as unusual (they ARE non-words). But their presence reduces guide quality — a narrator seeing "himselfin: /hɪmˈsɛlfɪn/" would be confused.

### HTML Presentation: 8/10 ✓

Navigation functional, well-organized with tabs. Search and filtering work. Confidence badges displayed. Grammar correct ("3 chapters"). Minor: Chapter 3 shows "the old man" and "the old woman" instead of canonical names.

## Current Issues (Priority Order)

### HIGH
1. **Text refinement concatenation artifacts create non-word pronunciation entries**
   - Problem: "himselfin" and "beliefin" appear in pronunciation guide. These are "himself in" and "belief in" with spaces stripped during text processing.
   - Evidence: Source text has proper spacing. Output concatenates words at some boundary.
   - Location: `src/ingestion/refine.py` — text refinement is concatenating words. Previous investigation (attempt 2) could not pinpoint the exact location despite extensive tracing.
   - Alternative fix: Add a concatenation detection heuristic in the pronunciation filtering stage. If a "word" can be split into two real English words at a boundary, skip it. This treats the symptom but is more tractable than the upstream bug.
   - Impact: Fixing this should bring pronunciation from 7.5 → 8.0+

   **Previous investigation results (from attempt 2 fix notes):**
   - Source file has proper spacing: "himself in" and "belief in" with spaces
   - PDF-specific code (_rejoin_split_words, _dehyphenate) should NOT run for TXT files
   - `_should_merge()` logic returns False for these cases when tested in isolation
   - Concatenation source was NOT found after extensive tracing
   - Recommendation: Either add diagnostic logging OR add concatenation detection heuristic in pronunciation filter

### MEDIUM
2. **Chapter 3 characters_present uses unlinked aliases**
   - Problem: `characters_present` shows `["the old man", "the old woman"]` instead of canonical names
   - "the old woman" is NOT in Mrs. White's alias list
   - Location: Summary agent character presence detection or alias normalization
   - Fix: Normalize characters_present to canonical names using alias map

3. **Chapters 2 and 3 have null titles**
   - Problem: Structure shows title "I" for chapter 1 but `null` for chapters 2 and 3
   - Location: `src/pipeline/chapter_detection/` — title extraction
   - Fix: Ensure all detected Roman numeral markers get their title populated

### LOW
4. **"the stranger" characterized without empathy when text shows unease**
   - Problem: Profile says "no visible empathy or remorse" but text says "visibly uneasy"
   - Location: LLM profiling interpretation
   - Fix: Minor, doesn't significantly affect narrator preparation

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.98 | - | Baseline. Structure detection major failure (3 parts → 1 chapter) |
| 2 | 8.38 | +1.40 | Structure fixed. Profiles improved. Pronunciation still failing (6.5/10) |
| 3 | 8.48 | +1.50 | 3 pronunciation false positives fixed. Artifacts remain (7.5/10) |

## Fix History
- Attempt 1 → 2: Fixed structure detection for Roman numerals with periods (I., II., III.)
  - Modified: `src/pipeline/chapter_detection/proposers/regex.py` line 301
  - Result: Structure 4→8.5, Summaries 7→9

- Attempt 2 → 3: Added "sideboard", "sightless", "mantelpiece" to pronunciation whitelist
  - Modified: `src/pipeline/pronunciation_guide/proposers/cmu_proposer.py`
  - Result: Pronunciation 6.5→7.5 (3 false positives removed, 2 artifacts remain)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | Structure detection missed I./II./III. markers | `src/pipeline/chapter_detection/proposers/regex.py` | Fixed: 3 parts detected. Score 4→8.5 |
| 2 | Pronunciation false positives (sideboard, sightless, mantelpiece) | `src/pipeline/pronunciation_guide/proposers/cmu_proposer.py` | Fixed: 3 entries removed. Score 6.5→7.5 |
| 2 | Concatenation artifacts (himselfin, beliefin) | (investigated but not fixed - root cause not found) | No change: artifacts still present |

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (MoE) — appropriate
- No LLM retries in any stage — clean execution
- Stage durations: Chapter Detection 313s, Summaries 229s, Characters 286s, Profiles 772s, Pronunciation 115s
- `character_llm_chunk_chars: 5000` — adequate for this short story
- Temperatures at 0.7 across all agents — acceptable

## Next Action
Run PROMPT_fix.md to address concatenation artifacts in pronunciation (HIGH #1). Two approaches:
1. **Preferred:** Add concatenation detection heuristic in pronunciation filtering — if a candidate "word" can be decomposed into two common English words, skip it. This is tractable and targeted.
2. **Alternative:** Add diagnostic logging to text refinement pipeline to find upstream concatenation source. Previous investigation failed to find it.

The fix needs to bring pronunciation from 7.5 → 8.0+ (remove 2 non-word artifacts).
