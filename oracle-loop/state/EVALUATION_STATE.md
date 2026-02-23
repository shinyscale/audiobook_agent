# Current Evaluation State

## Active Text
- **Name:** john_g
- **Attempt:** 2
- **Phase:** awaiting_analysis
- **baseline_score:** 7.55
- **Competitive Mode:** single

## Output Files
- HTML: ../output/john_g/report.html
- JSON: ../output/john_g/analysis.json
- Timestamped: ../output/John G - Katherine Mayo_20260222_222918/

## Pipeline Notes
- Completed in 11m 44s, 29 LLM calls, 34,719 tokens
- 2,228 words extracted (short text)
- 1 chapter detected (single chapter story)
- 5 characters total (John G. + 4 others)
- John G. (aka John) - 19 mentions — false split RESOLVED ✓
- Newline alias artifact RESOLVED ✓
- 4 profiles generated with HIGH confidence
- 20 pronunciation flags (7 homograph, 6 proper_noun, 6 unknown, 1 foreign)
- Greensburg IPA fix DID NOT TAKE EFFECT — still German pronunciation

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 8.5/10 ✓
  - Completeness: 9/10
  - Identity Resolution: 9/10
  - Alias Grouping: 8/10
- Character Profiles: 7.5/10 ✗ (FAILING)
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 6.5/10 ✗ (FAILING)
- HTML Presentation: 8.5/10 ✓
- **Overall: 8.15/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold: Profiles 7.5, Pronunciation 6.5)

## What Improved (Attempt 1 → 2)
- Character Extraction: 6/10 → 8.5/10 (+2.5) — John/John G. merge worked perfectly
- "John\nG." newline alias eliminated
- Plot summary no longer claims "John G. collapses" (previous hallucination fixed)
- Overall: 7.55 → 8.15 (+0.60)

## What Didn't Improve
- Greensburg pronunciation: Still German IPA despite fix to foreign_proposer.py — fix may not have been in the right codepath
- Sergeant IPA: Still wrong (`/səˈdʒɑːrənt/` "suh-JAR-ent")
- sharp-fanged IPA: Still wrong (`/feɪŋd/` "FAYND")
- 6 common-word false positives still present in pronunciation
- John G. still missing from chapter characters_present
- Profile age for John G. says "young" — he's 22 (ancient for a horse)

## Current Issues (Priority Order)

### HIGH
1. **Greensburg IPA still German — fix didn't take effect** [Pronunciation]
   - Problem: IPA is `/ˈɡʁɛnˌbʊʁk/` "GREHN-buurk" with notes referencing "guttural G like German Garten" and "ü is rounded and pronounced with lips puckered." This is an American city in Pennsylvania.
   - Evidence: Correct pronunciation is `/ˈɡriːnzbɜːrɡ/` "GREENZ-burg"
   - The attempt 2 fix modified `foreign_proposer.py:_validate_with_llm()` but Greensburg still has German IPA. The entry has `type: null` — it may not be going through the foreign proposer at all, or the LLM is generating the IPA in a different codepath.
   - Location: Need to trace WHERE Greensburg's IPA is actually generated. Check all pronunciation proposers, not just foreign_proposer.py. The `type: null` suggests it might come from `proper_noun_proposer.py` or the main pronunciation pipeline.
   - Fix: Identify which proposer is generating this entry and ensure proper nouns in American English text get American English IPA.

2. **Sergeant IPA completely wrong** [Pronunciation]
   - Problem: `/səˈdʒɑːrənt/` "suh-JAR-ent" — stress on wrong syllable, wrong vowel pattern
   - Evidence: Correct is `/ˈsɑːr.dʒənt/` "SAR-jent" — stress on first syllable
   - Location: Pronunciation LLM generation (likely proper_noun proposer since it's a rank/title)
   - Fix: This is an LLM accuracy issue. Could be addressed by dictionary lookup for common English words, or by filtering "Sergeant" as a false positive (it's a common word that doesn't need pronunciation guidance)

3. **sharp-fanged IPA wrong** [Pronunciation]
   - Problem: `/ʃɑːrp-feɪŋd/` "SHARP-FAYND" — "fanged" should be /fæŋd/ (rhymes with "banged"), not /feɪŋd/ (rhymes with "frayed"). Note incorrectly says "the 'g' is silent"
   - Evidence: Standard American English: "fanged" = /fæŋd/
   - Location: Pronunciation LLM generation
   - Fix: LLM accuracy issue; consider dictionary-based verification for compound words

4. **6 common-word false positive pronunciation entries** [Pronunciation]
   - Problem: "Sergeant", "Price", "Corporal", "Richardson", "Troopers", "Adams" — all common English words/surnames/ranks. A professional narrator knows these.
   - Evidence: These entries add noise and reduce signal-to-noise ratio (6/20 = 30% false positives)
   - Location: Pronunciation flagging in `src/pipeline/pronunciation.py` or proposers
   - Fix: Add a common-word filter for military ranks and common English surnames. Or increase the "unusualness" threshold.

5. **John G. age listed as "young"** [Profiles]
   - Problem: The profile shows `Age: young` but John G. is 22 years old. The text explicitly states: "if you counted his twenty-two years by human standards he would be eighty-eight." He is very old for a horse.
   - Evidence: Text clearly describes his age and implies he's elderly
   - Location: Profile generation in character profiles pipeline
   - Fix: LLM accuracy issue — the profile agent may be confused because 22 seems young for a human. The text explicitly states his age; the LLM should capture it accurately.

6. **Richardson-Price relationship inaccurate** [Profiles]
   - Problem: Listed as "colleague with conflicting priorities" — should be warm subordinate-superior relationship. Richardson is a Corporal, Price is a First Sergeant. The text shows mutual respect, humor, and camaraderie.
   - Evidence: Their dialogue shows bantering and gentle philosophy, not conflict
   - Location: Profile generation
   - Fix: LLM accuracy issue in relationship characterization

### MEDIUM
7. **John G.-Richardson relationship listed as "unknown"** [Profiles]
   - Problem: From John G.'s perspective, Richardson is listed as relationship "unknown." Richardson spends 3 hours tending to John G. — the relationship is clearly "caretaker."
   - Evidence: Richardson's profile correctly lists "John G.: caretaker" but the reverse direction is "unknown"
   - Location: Profile generation — bidirectional relationship consistency
   - Fix: If one character has relationship X→Y, the reverse Y→X should be inferred

8. **John G. missing from chapter characters_present** [Presentation]
   - Problem: Chapter 1's characters list shows Price, Adams, Richardson, Two Troopers — but NOT John G., the title character and protagonist
   - Evidence: HTML chapter card lists 4 characters, John G. absent
   - Location: Chapter summary character extraction
   - Fix: John G. is mentioned extensively in the chapter — should be in characters_present

9. **"Verbal tics" for John G. are Price's dialogue** [Profiles]
   - Problem: The "verbal tics" section shows "Come along, John, it's all right, old man!" — these are words spoken BY Price TO John G., not by the horse. This is confusing for narrator prep.
   - Evidence: John G. is a horse and doesn't speak
   - Location: Profile generation — the LLM attached quotes to the wrong character
   - Fix: LLM accuracy issue; quotes should be attributed to the speaker (Price), not the addressee

### LOW
10. **Missing pronunciation: "Allegheny"** — river name, commonly mispronounced
11. **"Tien Tsin" only partially flagged** — "Tsin" captured but not full "Tien Tsin"

## Priority for Fix Phase

**To get Pronunciation from 6.5 → 8.0:** Fix Greensburg IPA (#1), remove false positive common words (#4). These two fixes alone would bring pronunciation to ~8.0 by eliminating the worst IPA error and improving signal-to-noise ratio. Sergeant/sharp-fanged IPA (#2, #3) are LLM accuracy issues that are harder to fix generically.

**To get Profiles from 7.5 → 8.0:** Fix John G. age (#5) is the most impactful single fix. The relationship issues (#6, #7) and verbal tics (#9) are LLM accuracy issues that are harder to fix generically without novel-specific prompting.

**Recommended focus:** Issues #1 and #4 (pronunciation) are most actionable with generic code changes. Issue #5 (age) may be hard to fix generically.

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 7.55 | — (baseline) | 3 categories failing: Characters 6, Profiles 7, Pronunciation 7 |
| 2 | 8.15 | +0.60 | 2 categories failing: Profiles 7.5, Pronunciation 6.5. Character extraction fixed (+2.5) |

## Fix History
- Attempt 2: Three fixes applied:
  1. **Newline normalization in NER entity names** — `supporting.py:extract():116`: changed `ent.text.strip()` to `re.sub(r"\s+", " ", ent.text).strip()`. **RESULT: FIXED** ✓
  2. **First-name+initial merge in supporting cast** — `characters.py:_merge_within_supporting_cast():~2681`: Added "firstname of initial name" pattern. **RESULT: FIXED** ✓
  3. **Greensburg German IPA fix** — `foreign_proposer.py:_validate_with_llm():264`: Updated LLM validation prompt for proper nouns. **RESULT: NO CHANGE** ✗ — Greensburg still has German IPA. The fix was likely in the wrong codepath (entry has `type: null`, may not use foreign_proposer).
- Attempt 3: Three fixes applied:
  1. **Remove "-burg"/"-berg" from German suffix patterns** — `foreign_proposer.py:FOREIGN_PATTERNS["German"]`: These suffixes are overwhelmingly Americanized (Pittsburgh, Gettysburg, Spielberg). Genuine German words still detected via article patterns (der/die/das). Greensburg entry removed entirely. **Root cause:** pattern match was too broad.
  2. **Skip CMU-known words in CharacterProposer** — `character_proposer.py:__init__()`: Auto-loads CMU dictionary; skips character name words that are in CMU (e.g., "Price", "Sergeant", "Corporal", "Richardson", "Adams", "Troopers"). Also updated `pipeline.py` to share CMU dict from CMUProposer. Reduces false positives from 6/20 to 0. **Root cause:** CharacterProposer had no universal filter for standard English words.
  3. **Improve age_indication to capture exact stated age** — `analyzer.py:3416`, `analyzer.py:3820`, `character_profiling/generator.py:129`: Changed format hint from `"young/middle-aged/elderly/unknown"` to include explicit age extraction. LLM should now capture "22 years old" verbatim from text instead of categorizing as "young". **Root cause:** prompt format hint forced LLM to categorize rather than quote text.

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 2 | false split John/John G. | supporting.py, characters.py | Fixed ✓ |
| 2 | newline alias | supporting.py | Fixed ✓ |
| 2 | Greensburg German IPA | foreign_proposer.py | No change ✗ — wrong codepath |
| 3 | Greensburg German IPA | foreign_proposer.py:FOREIGN_PATTERNS | Removed -burg/-berg patterns |
| 3 | false positive pronunciation entries | character_proposer.py, pipeline.py | CMU dictionary filter added |
| 3 | John G. age "young" vs "22 years old" | analyzer.py, character_profiling/generator.py | age_indication prompt updated |

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (Ollama) for all stages — reasonable
- Profile generation: 9 LLM calls, 4 HIGH confidence, 0 retries — healthy
- Character extraction: 2 LLM calls, 2 MEDIUM confidence, 0 retries — fine for short text
- No concerning retry counts or parse failures

## Next Action
Re-run analysis to verify fixes: Pronunciation (Greensburg removed, 6 false positives eliminated) and Profiles (age_indication now captures exact stated age).
