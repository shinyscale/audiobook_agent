# Current Evaluation State

## Active Text
- **Name:** monkeys_paw
- **Attempt:** 2
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
- Pronunciation Guide: 6.5/10 ✗ (FAILING)
- HTML Presentation: 8/10 ✓
- **Overall: 8.38/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (1 category below threshold)

## Evaluation Details

### Structure Detection: 8.5/10 ✓

The critical fix worked — 3 parts are now correctly detected (I, II, III). Chapter 1 has title "I" but chapters 2 and 3 have `null` titles (should be "II" and "III"). This is cosmetic — the HTML renders "Chapter 2" and "Chapter 3" without the Roman numeral titles. The structure itself is correct and the summaries are properly split. Minor deduction for missing titles.

### Character Extraction: 9/10 ✓

All significant characters correctly identified:
- **Main cast (4):** Mr. White (42 mentions), Mrs. White (26), Herbert White (15), Sergeant-Major Morris (13) — all correct
- **Supporting (2):** "the stranger" (Maw & Meggins representative, 2 mentions), "the monkey's paw" (symbolic object/force, 5 mentions) — both appropriate

Aliases are well-grouped: Mr. White = "the old man", "White", "the husband"; Herbert = "Herbert", "the son"; Morris = "Morris", "the sergeant-major". No false splits, no false merges, no hallucinated characters.

Minor issue: Chapter 3's `characters_present` lists "the old woman" which is NOT listed as an alias of Mrs. White. This means the chapter tracking references an unlinked name variant. Similarly "the old man" appears correctly as a Mr. White alias but the asymmetry is notable.

### Character Profiles: 8.5/10 ✓

Major improvement over attempt 1:
- **No more spectacles hallucination** — Mr. White's appearance now correctly states "thin grey beard" and "frail physical presence"
- **No more misattributed Arabian Nights quote** — Herbert's quotes are all correctly his own lines
- **Morris's relationship to Mr. White is now "acquaintance"** (was "victimizer" in attempt 1) — Mr. White → Morris is "mentor" which is reasonable
- Voice guidance is excellent across all 4 main characters — tone, dialect, verbal tics, example quotes
- Morris's physical description ("beady of eye, rubicund of visage") is accurately pulled from the text

Minor issues:
- "the stranger" is described as a "villainous figure" — this is editorialized. He's a company representative delivering bad news under painful circumstances, not a villain. But this is a minor LLM interpretation issue.
- Mrs. White's personality description is somewhat harsh ("manipulative, emotionally volatile") — she's a grieving mother, but this is within the range of reasonable interpretation

### Chapter Summaries: 9/10 ✓

All 3 summaries are accurate, detailed, and useful for narrator preparation:
- **Part I:** Correctly captures the chess game, Morris's arrival, the paw's backstory, the first wish for £200, the paw twisting
- **Part II:** Accurately describes Herbert leaving for work, the stranger from Maw and Meggins, Herbert's death, the £200 compensation coincidence
- **Part III:** Correctly captures Mrs. White's demand to wish Herbert back, the knocking at the door, the third wish, the empty road

No hallucinated events. Tone and atmosphere well-conveyed. Lengths are appropriate (130-170 words each). Plot summary in overview is also excellent and accurate.

### Pronunciation Guide: 6.5/10 ✗ (FAILING)

**Good entries:**
- "fakir" (/fəˈkɪər/) — essential for this story, correctly flagged
- "rubicund" (/ruːˈbɪkʌnd/) — uncommon word, useful for narrator
- "antimacassar" (/ˌæn.ti.məˈkæs.ɑːr/) — period-specific term, excellent catch
- "condoling", "condoled" — less common words, appropriate
- "bibulous", "avaricious", "shamefacedly", "betokened", "apathetically" — legitimate uncommon words
- "Meggins" — proper noun from the story, useful
- Homographs "live", "minute", "separate" — good catches with context

**Problems:**
1. **"himselfin" and "beliefin"** — These are text refinement artifacts (concatenated "himself in" and "belief in"). Not real words. IPA generated for non-words.
2. **"sideboard"** — Common English word, false positive. Every narrator knows this word.
3. **"sightless"** — Common English word, false positive. Standard vocabulary.
4. **"mantelpiece"** — Common English word, false positive. Standard household term.
5. **3 entries lack IPA** — "live", "minute", "separate" have no IPA (homographs show alternate pronunciations in notes instead, which is fine but inconsistent format)

The false positives and text refinement artifacts bring this below threshold.

### HTML Presentation: 8/10 ✓

- Navigation works (tabs for Chapters, Characters, Pronunciations)
- Well-organized with main characters getting full profiles and supporting characters in table format
- Confidence badges and metadata displayed cleanly
- Grammar fixed: now says "3 chapters" (was "1 chapters" in attempt 1)
- Pronunciation guide has useful search and view-toggle features

Minor issues:
- Chapter 3 characters shown as "the old man" and "the old woman" — these should display as their canonical names (Mr. White, Mrs. White)
- "the old woman" is not a recognized alias of Mrs. White, so it shows as an unlinked reference

## Current Issues (Priority Order)

### HIGH
1. **Pronunciation false positives: "sideboard", "sightless", "mantelpiece"**
   - Problem: Common English words flagged for pronunciation guidance. These are standard vocabulary any narrator would know without help.
   - Evidence: All three are common words with straightforward pronunciation
   - Location: `src/pipeline/pronunciation/` — word frequency filtering
   - Fix: These should be caught by the common word exception list or frequency-based filtering. "sideboard" (rank ~8000), "sightless" (rank ~12000), "mantelpiece" (rank ~10000) are all well within normal vocabulary.

2. **Pronunciation artifacts: "himselfin" and "beliefin" are concatenated words**
   - Problem: Text refinement merged "himself in" → "himselfin" and "belief in" → "beliefin". The pronunciation system correctly flags these as unusual (they ARE non-words), but the root cause is upstream.
   - Evidence: These "words" don't exist in English. They're artifacts of `src/ingestion/refine.py` incorrectly removing spaces.
   - Location: `src/ingestion/refine.py` — text refinement concatenating words at line breaks
   - Fix: Fix the upstream text refinement bug that strips spaces between words. Alternatively, add a heuristic to detect and skip words that look like concatenations (contains a real word prefix + real word suffix with no separator). The refinement fix is the proper solution.

### MEDIUM
3. **Chapter 3 characters_present uses unlinked aliases**
   - Problem: Chapter 3's `characters_present` lists "the old man" and "the old woman" instead of canonical names. "the old man" is a Mr. White alias but "the old woman" is NOT listed as a Mrs. White alias, so it displays as an unresolved reference in the HTML.
   - Evidence: `jq '.structure[2].characters_present'` shows `["the old man", "the old woman"]`; Mrs. White's aliases are only `["White"]`
   - Location: Summary agent's character presence detection OR alias resolution
   - Fix: Either add "the old woman" as an alias of Mrs. White, or normalize `characters_present` to canonical names using the alias map before export.

4. **Chapters 2 and 3 have null titles**
   - Problem: Structure shows title "I" for chapter 1 but `null` for chapters 2 and 3. They should be "II" and "III".
   - Evidence: `jq '.structure[] | .title'` shows `"I"`, `null`, `null`
   - Location: `src/pipeline/chapter_detection/` — title extraction for Roman numeral patterns
   - Fix: The regex fix correctly detected the pattern but may only be extracting the title for the first match. Check if all detected markers get their title populated.

### LOW
5. **"the stranger" described as "villainous"**
   - Problem: The Maw & Meggins representative is described as "a villainous figure who delivers devastating news with cold formality, exploiting social decorum to mask his role in a fatal tragedy." He's just a company representative — there's no evidence he's villainous or "exploiting" anything.
   - Evidence: The text shows him as uncomfortable and reluctant: "visibly uneasy"
   - Location: Character profiling LLM interpretation
   - Fix: LLM temperature or prompt issue — minor, doesn't affect narrator preparation significantly

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.98 | - | Baseline. Structure detection major failure (3 parts → 1 chapter) |
| 2 | 8.38 | +1.40 | Structure fixed. Profiles improved. Pronunciation still failing (6.5/10) |

## Fix History
- Attempt 1 → 2: Fixed structure detection for Roman numerals with periods (I., II., III.)
  - Root cause: `src/pipeline/chapter_detection/proposers/regex.py` - `_extract_title()` method did not handle `pattern_type == "roman_numeral_with_period"`, causing titles to retain trailing period which broke sequential pattern detection
  - Modified: `src/pipeline/chapter_detection/proposers/regex.py` line 301
  - Test suite: All 298 tests pass (10 skipped)
  - Cascades: Structure fix resolved chapter summaries (3 per-part summaries now generated) and fixed "1 chapters" grammar

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | Structure detection missed I./II./III. markers | `src/pipeline/chapter_detection/proposers/regex.py` | Fixed: 3 parts detected. Score 4→8.5 |
| 1 | Chapter summaries lack granularity (cascade) | (resolved by structure fix) | Fixed: 3 summaries generated. Score 7→9 |
| 1 | Morris "victimizer" relationship | (resolved by re-run with different LLM generation) | Fixed: Now "acquaintance"/"mentor" |
| 1 | Spectacles hallucination | (resolved by re-run) | Fixed: No longer present |
| 1 | Misattributed Arabian Nights quote | (resolved by re-run) | Fixed: No longer present |

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (MoE) — appropriate
- No retries or JSON parse failures in main stages
- LLM batch enrichment failed in pronunciation stage (JSON parsing error) — may explain some pronunciation quality issues
- All characters high confidence — good
- `character_llm_chunk_chars: 5000` — adequate for this short story
- Temperatures at 0.7 across all agents — acceptable

## Next Action
Run PROMPT_fix.md to address pronunciation false positives (HIGH #1, #2). Focus on:
1. Adding "sideboard", "sightless", "mantelpiece" to common word exceptions or improving frequency filtering
2. Fixing text refinement concatenation bug ("himselfin", "beliefin") in `src/ingestion/refine.py`
These two fixes should bring Pronunciation from 6.5 to 8.0+.
