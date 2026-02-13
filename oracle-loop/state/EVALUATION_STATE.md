# Current Evaluation State

## Active Text
- **Name:** monkeys_paw
- **Attempt:** 4
- **Phase:** complete
- **baseline_score:** 6.98

## Output Files
- HTML: ../output/monkeys_paw/report.html
- JSON: ../output/monkeys_paw/analysis.json

## Latest Scores
- Structure Detection: 8.5/10 ✓
- Character Extraction: 9/10 ✓
- Character Profiles: 8.5/10 ✓
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 8/10 ✓
- **Overall: 8.63/10**

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** PASS — All categories at or above threshold

## Evaluation Details

### Structure Detection: 8.5/10 ✓

3 parts correctly detected (I, II, III). Chapter 1 has title "I", Chapter 2 has title "II". Chapter 3 still has `null` title (should be "III"). Structure boundaries are correct with properly split content.

### Character Extraction: 9/10 ✓

All significant characters correctly identified:
- **Main cast (6):** Mr. White (10 mentions), Mrs. White (10), Herbert White (14), Sergeant-Major Morris (13), the stranger (2), the monkey's paw (5)
- Aliases well-grouped: Herbert = "Herbert"; Morris = "Morris", "the sergeant-major"
- No false splits, no false merges, no hallucinated characters

Minor: "the old man" and "the old woman" not captured as aliases for Mr./Mrs. White, affecting Chapter 3 characters_present.

### Character Profiles: 8.5/10 ✓

Well-structured profiles with personality summaries, traits, temperament, moral alignment, key behaviors, speech patterns, and evidence quotes. All evidence quotes are from the actual text.

- Mr. White: Accurate characterization as impulsive and grief-driven
- Mrs. White: Good characterization as nurturing and emotionally attuned
- Herbert: Accurate portrayal as irreverent and dismissive of superstition
- Morris: Well-captured moral ambiguity and guilt

Minor: physical_description null for all characters (sparse physical details in text). The stranger's moral_alignment "villainous" is slightly off — he's a reluctant messenger, not a villain.

### Chapter Summaries: 9/10 ✓

All 3 summaries accurate, detailed, and useful for narrator preparation:
- **Part I** (152 words): Chess game, Morris's arrival, paw backstory, first wish for £200, paw twisting
- **Part II** (147 words): Herbert leaving for work, stranger from Maw & Meggins, Herbert's death, £200 compensation
- **Part III** (121 words): Grief, second wish, knocking, frantic search for paw, third wish, empty street

No hallucinated events. Good atmospheric detail. Appropriate lengths.

Minor: Chapter 3 characters_present shows ["the old man", "the old woman"] instead of canonical names.

### Pronunciation Guide: 8/10 ✓

**Fix confirmed!** "himselfin" and "beliefin" removed by improved _is_ocr_artifact() heuristic. All 20 remaining entries are legitimate:
- Proper nouns (4): Herbert, Sergeant-Major, Morris, Meggins
- Uncommon words (10): fakir, antimacassar, rubicund, condoling, condoled, shamefacedly, betokened, avaricious, bibulous, apathetically
- Useful terms (3): unlooked-for, Leastways, instalment
- Homographs (3): live, minute, separate — IPA correctly null (context-dependent)

17/20 have IPA. Zero false positives.

### HTML Presentation: 8/10 ✓

Navigation functional, well-organized with tabs. Search and filtering work. Minor: Chapter 3 shows "the old man" and "the old woman" instead of canonical names.

## Remaining Issues (Not Blocking — Below Threshold for Fix)

### MEDIUM
1. **Chapter 3 characters_present uses unlinked aliases** — "the old man" and "the old woman" instead of canonical names Mr. White and Mrs. White
2. **Chapter 3 has null title** — should be "III"
3. **The stranger's moral_alignment "villainous"** — text shows nervousness/reluctance, not villainy

### LOW
4. **physical_description null for all characters** — text has sparse physical details; reasonable behavior
5. **Mrs. White moral_alignment "heroic"** — arguably "desperate" would be more accurate

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.98 | — | Baseline. Structure detection major failure (3 parts → 1 chapter) |
| 2 | 8.38 | +1.40 | Structure fixed. Profiles improved. Pronunciation still failing (6.5/10) |
| 3 | 8.48 | +1.50 | 3 pronunciation false positives fixed. Artifacts remain (7.5/10) |
| 4 | 8.63 | +1.65 | Pronunciation artifacts fixed. All categories PASS. |

## Fix History
- Attempt 1 → 2: Fixed structure detection for Roman numerals with periods (I., II., III.)
  - Modified: `src/pipeline/chapter_detection/proposers/regex.py` line 301
  - Result: Structure 4→8.5, Summaries 7→9

- Attempt 2 → 3: Added "sideboard", "sightless", "mantelpiece" to pronunciation whitelist
  - Modified: `src/pipeline/pronunciation_guide/proposers/cmu_proposer.py`
  - Result: Pronunciation 6.5→7.5 (3 false positives removed, 2 artifacts remain)

- Attempt 3 → 4: Improved OCR artifact detection for concatenated words
  - Modified: `src/pipeline/pronunciation_guide/proposers/cmu_proposer.py` lines 651-686
  - Changes: Reduced min_part_length from 3 to 2, fixed validation logic for CMU dict OR whitelist, added "belief" to whitelist
  - Result: Pronunciation 7.5→8.0 (artifacts "himselfin" and "beliefin" removed)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | Structure detection missed I./II./III. markers | `src/pipeline/chapter_detection/proposers/regex.py` | Fixed: 3 parts detected. Score 4→8.5 |
| 2 | Pronunciation false positives (sideboard, sightless, mantelpiece) | `src/pipeline/pronunciation_guide/proposers/cmu_proposer.py` | Fixed: 3 entries removed. Score 6.5→7.5 |
| 2 | Concatenation artifacts (himselfin, beliefin) | (investigated but not fixed - root cause not found) | No change |
| 3 | Concatenation artifacts (himselfin, beliefin) | `src/pipeline/pronunciation_guide/proposers/cmu_proposer.py` | Fixed: _is_ocr_artifact() improved. Score 7.5→8.0 |

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (MoE) — appropriate
- No LLM retries in any stage — clean execution
- Stage durations: Chapter Detection 301s, Summaries 240s, Characters 173s, Profiles 717s, Pronunciation 112s
- Temperatures at 0.7 across all agents — acceptable
- Total: 60 LLM calls, 93,348 tokens

## Next Action
Text PASSED. Ready to advance to next text (gift_of_the_magi).
