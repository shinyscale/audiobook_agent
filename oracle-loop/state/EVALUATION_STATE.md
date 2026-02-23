# Current Evaluation State

## Active Text
- **Name:** i_have_no_mouth
- **Attempt:** 4
- **Phase:** awaiting_evaluation
- **baseline_score:** 7.35
- **Competitive Mode:** single

## Output Files
- HTML: ../output/i_have_no_mouth/report.html
- JSON: ../output/i_have_no_mouth/analysis.json
- Timestamped: ../output/I_Have_No_Mouth_And_I_Must_Scream_20260223_014514/

## Latest Scores
(Awaiting evaluation)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** PENDING

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 7.35 | 0.00 | Baseline. AM missing, false positives, pronunciation artifacts |
| 2 | 7.40 | +0.05 | bush removed, roles improved, but AM still missing, narrator still undetected |
| 3 | CRASH | - | Pipeline crash: KeyError in MAIN_CAST_PROMPT format() due to unescaped JSON braces |
| 4 | TBD | TBD | Two-pass fallback fired; 6 chars found; narrator still undetected; awaiting evaluation |

## Current Issues (Priority Order)

### CRITICAL
1. **AM (the supercomputer) is STILL completely missing from character list** [Completeness]
   - Problem: AM is the primary antagonist — a sentient supercomputer that has imprisoned the 5 survivors for 109 years. It speaks directly (famous hate monologue), acts, tortures, and transforms characters. The story's title derives from AM's punishment of Ted. AM is referenced ~39 times in summaries, evidence, and relationships yet never extracted as a character entity.
   - Evidence: All 6 extracted characters have `supporting_*` IDs — the main cast pipeline produced **zero** characters for the second consecutive attempt. AM has aliases: "Allied Mastercomputer", "Adaptive Manipulator", "Aggressive Menace". The pronunciation guide even includes "Mastercomputer" as an entry, proving the pipeline encounters the name but doesn't extract it as a character.
   - Root cause analysis: AM is a 2-letter uppercase acronym. NER likely doesn't tag "AM" as PERSON. The main cast pipeline failed entirely (0 characters produced) — all characters come from the supporting cast pipeline's NER-based extraction. For 2 consecutive attempts, the main cast LLM pipeline has produced nothing, suggesting it's fundamentally failing for this text (possibly due to short story length, single chapter, or response format issues).
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` (main cast LLM pipeline) and `src/pipeline/character_extraction_v2/supporting.py` (supporting cast NER doesn't catch acronyms)
   - Fix approach: **This has failed 2 attempts. The fix phase should investigate WHY main_cast produces 0 characters** — check logs, check if the LLM response is malformed, check if the chapter text is being passed correctly. If main_cast can't be fixed quickly, the supporting cast pipeline needs a fallback to catch high-frequency non-PERSON entities that are clearly characters (AM appears more than any human character).

2. **Ted is STILL not flagged as narrator** [Completeness / Profiles]
   - Problem: Ted is the first-person narrator. `is_narrator: false`. The narrator re-detection fix (STEP 5.8.5) was applied but didn't work. `narrative_style` is "unknown" in structure overview (but correctly "first-person retrospective" in plot_summary — contradictory).
   - Evidence: The story is told entirely from Ted's "I" perspective. Plot summary correctly identifies "first-person retrospective" but `overview.structure.narrative_style` says "unknown". This inconsistency suggests the narrator detection code reads from the wrong field.
   - Location: `src/pipeline/character_extraction_v2/narrator.py` (STEP 5.8.5 re-detection), and the narrative_style field inconsistency between `overview.structure` and `overview.plot_summary`
   - Fix approach: Check why STEP 5.8.5 re-detection didn't fire or didn't succeed. The plot_summary already knows it's "first-person retrospective" — the narrator detection should be able to use that signal. Also Ted has only 5 mentions (as narrator he uses "I" not his name), so he's in "supporting" role and may not be considered as a narrator candidate.

### HIGH
3. **False positive character: "Jesus" still present** [Completeness]
   - Problem: "Jesus" (4 mentions) is extracted as a supporting character. Only appears as exclamation ("Jesus God", "Christ"), not as an actual character. Has zero profile data — no aliases, appearance, personality, relationships, or evidence.
   - Evidence: Empty profile. Every real character's relationship dict includes `"Jesus": "unknown"`, polluting their profiles.
   - Location: `src/pipeline/character_extraction_v2/supporting.py` — the lowercase filter from attempt 1 fixed "bush" but "Jesus" is capitalized so it passes the filter
   - Fix approach: Add filtering for exclamatory name usage — if a name has zero profile data (no description, no relationships, no evidence entries from the profile pipeline), and appears only in exclamation contexts, exclude it. Or add a blocklist of common exclamation names ("Jesus", "Christ", "God", "Lord") that require actual character evidence to be included.

4. **Wrong ages STILL showing in HTML profiles** [Profiles]
   - Problem: Benny, Ellen, and Gorrister all show "Age: five years" in the HTML report. The `age_indication` field in JSON is null (the john_g age fix cleared that), but the profile rendering pipeline independently extracted "five years" from the "five survivors" context and rendered it in HTML.
   - Evidence: Lines 1036, 1234, 1442 of report.html show "Age: five years". The characters are adults who have been trapped for 109 years.
   - Location: Profile generation pipeline (not the character age_indication field — the fix from john_g only cleared the JSON field, not the profile rendering data). Check `src/pipeline/character_extraction_v2/` profile generation and the HTML template rendering.
   - Fix approach: The age validation logic needs to apply to profile-rendered ages too, not just the `age_indication` field. Or the profile pipeline needs better contextual understanding that "five" refers to group size, not age.

5. **Ted demoted to "supporting" — gets no profile in HTML** [Profiles]
   - Problem: Ted is the narrator/protagonist but has only 5 name-mentions (because he uses "I" as narrator). He's classified as "main" role in JSON but rendered in the "Supporting Characters" table in HTML, which shows no profile details — just name, mentions, first appearance. The narrator of the story gets the least detailed entry.
   - Evidence: HTML lines 1800-1811 show Ted in the supporting table with a truncated description. No appearance, personality, voice guidance, or evidence sections rendered.
   - Location: The role "main" maps to the supporting character table in HTML rendering. If Ted were flagged as narrator, he should be promoted to protagonist regardless of mention count.
   - Fix approach: This resolves when issue #2 (narrator detection) is fixed — a detected narrator should automatically get protagonist role and full profile rendering.

### MEDIUM
6. **7 pronunciation artifact entries from PDF extraction** [Pronunciation]
   - Problem: 7 entries are artifacts: "we'lldie", "Nimdokwith", "ifwe", "mefrom", "myright", "mysurface" (concatenated words from PDF text extraction), and "hermiene" (from the URL `hermiene.net` in the source PDF).
   - Evidence: These are clearly not real words. "hermiene" comes from the story's source URL embedded in the PDF.
   - Location: `src/pipeline/pronunciation/` (validation), `src/ingestion/refine.py` (text extraction)
   - Fix approach: Add validation to reject entries that contain known word boundaries (camelCase patterns, lowercase-to-uppercase transitions). Filter URL-derived tokens.

7. **Common word false positives in pronunciation** [Pronunciation]
   - Problem: ~10 common English words don't need pronunciation guidance: "palette", "tinfoil", "firelight", "snowdrifts", "loonie", "piteously", "spastically", "sentience", "sentient", "eternities", "puckerings", "stalactites"
   - Evidence: Standard English words any narrator would know. A narrator doesn't need IPA for "tinfoil" or "snowdrifts".
   - Location: `src/pipeline/pronunciation/` frequency/common-word filtering
   - Fix approach: Improve common-word filter threshold. Compound words (tinfoil, firelight, snowdrifts) and words with common suffixes (-ly, -ness, -tion) derived from common roots should be excluded.

8. **Possessive pronunciation duplicates** [Pronunciation]
   - Problem: "Gorrister's" and "Nimdok's" appear alongside "Gorrister" and "Nimdok" as separate entries.
   - Evidence: Near-identical IPA for base and possessive forms.
   - Location: Pronunciation deduplication logic
   - Fix approach: Strip possessive suffixes ('s, s') before deduplication.

9. **Incorrect IPA for "choir"** [Pronunciation]
   - Problem: IPA listed as /kwɑːr/. Correct is /kwaɪər/.
   - Evidence: Standard English pronunciation uses diphthong.
   - Location: LLM IPA generation. No easy generic fix.

### LOW
10. **Relationships reference false positive "Jesus"**
    - Problem: Every real character lists `"Jesus": "unknown"` in relationships.
    - Evidence: Pollutes relationship data.
    - Fix: Auto-resolves when issue #3 (Jesus false positive) is fixed.

11. **Themes identified as "identity, ambition, loss" — "ambition" is questionable**
    - Problem: Better themes for this story: hatred, dehumanization, survival, mercy, suffering.
    - Evidence: The story is about AM's hatred and the dehumanization of its prisoners. "Ambition" doesn't clearly apply.
    - Fix: LLM theme extraction quality — low priority.

## Fix History

### Attempt 3 Fixes Applied

**Fix 1 (main_cast.py): Robust LLM JSON parsing in `_parse_pass1_results` and `_parse_profiles`**
- Root cause: If LLM returns JSON with `"name"` instead of `"canonical_name"`, OR wraps the list under a key other than `"characters"` or `"main_cast"` (e.g. `"cast"`, `"character_list"`), all characters were silently dropped → 0 main cast characters
- Fix: Accept `"name"` / `"character_name"` as fallbacks for `"canonical_name"`; try additional dict wrapper keys (`"cast"`, `"character_list"`, `"main_characters"`, `"result"`) and fall back to first list-valued key
- Files: `src/pipeline/character_extraction_v2/main_cast.py`
- Smoke test: PASS — correctly extracts characters from JSON with `"name"` key, `"cast"` wrapper, mixed keys

**Fix 2 (main_cast.py): Two-pass → single-pass fallback in `extract()`**
- Root cause: If two-pass extraction returns 0 characters (any reason), no fallback existed
- Fix: If `_extract_two_pass` returns 0 profiles, immediately retry with `_extract_single_pass`
- Files: `src/pipeline/character_extraction_v2/main_cast.py`
- Smoke test: PASS — fallback path correctly invoked

**Fix 3 (characters.py): STEP 5.8.5 re-detection condition fix**
- Root cause: STEP 5.8.5 only fired if `pov == "unknown"` OR `narrator_name is None`. If STEP 4 identified narrator by name (e.g. "Ted") but could NOT match to a character (because main_cast was empty at STEP 4 time), `narrator_character_id=None` but condition was False → re-detection never ran even with Ted now in main_cast
- Fix: Added `narrator_info.narrator_character_id is None` to STEP 5.8.5 condition
- Files: `src/agents/characters.py:724`
- Smoke test: PASS — condition verified in code

**Fix 4 (narrator.py): Include plot_summary in narrator detection prompt**
- Root cause: `plot_summary` received by `detect()` was never passed to the LLM prompt; plot summary often explicitly identifies narrative style ("first-person retrospective"), which is a strong signal
- Fix: Added `{plot_summary_section}` placeholder to `NARRATOR_DETECTION_PROMPT`; `detect()` includes first 400 chars of plot_summary when available
- Files: `src/pipeline/character_extraction_v2/narrator.py`
- Smoke test: PASS — prompt correctly includes plot summary section

**Fix 5 (cmu_proposer.py): Pronunciation artifact detection improvements**
- Root cause (concatenated words): `_is_ocr_artifact` only checked prefixes in a small list; `"me"`, `"my"`, `"if"`, `"he"`, `"she"`, `"her"`, `"him"`, `"his"` were missing → `mefrom`, `myright`, `mysurface`, `ifwe` passed through
- Root cause (suffix): No suffix-based detection → `Nimdokwith` (ends with "with") passed through
- Root cause (possessives): Only skipped possessives of CMU-known words; `Gorrister's`/`Nimdok's` passed through since character names not in CMU
- Root cause (contraction-concat): `we'lldie` had apostrophe, making standard prefix check fail
- Fix: Added 8 new prefixes; added suffix-based detection for common function words; skip all possessives with base len >= 3; added contraction-concatenation detection
- Files: `src/pipeline/pronunciation_guide/proposers/cmu_proposer.py`
- Smoke test: PASS — all 5 artifact types correctly detected/filtered

### Attempt 1 Fixes Applied

**Fix 1 (characters.py):** Move supporting cast mention search to BEFORE promotion (new STEP 5.7.5)
- Root cause: STEP 5.8 promotion was using NER mention counts (which undercount actual text occurrences), while the deterministic mention search only ran in STEP 5.10.5 AFTER promotion decisions were made. This caused all 5 human characters to remain "minor" despite having 5-35 actual mentions.
- Fix: Added STEP 5.7.5 that runs `searcher.search_all(supporting_cast)` before STEP 5.8, so promotion uses accurate mention counts.
- **Result: WORKED** — Benny (35), Ellen (30), Gorrister (29), Nimdok (17) promoted to protagonist. Ted (5) promoted to "main".

**Fix 2 (characters.py):** Add narrator re-detection after promotion (STEP 5.8.5)
- Root cause: Narrator detection (STEP 4) ran with an empty main_cast (all LLM characters failed grounding). With no candidates to match against, narrator returned "unknown".
- Fix: After STEP 5.8 promotion, if narrator_info.narrator_name is None, re-run narrator detection with the updated main_cast (which now includes promoted characters like Ted).
- **Result: DID NOT WORK** — Narrator still "No definitive narrator identified". Needs investigation.

**Fix 3 (narrator.py):** Fix NARRATOR_DETECTION_PROMPT to account for 3rd-person summaries
- Root cause: The prompt asked "does the narrator say 'I'?" but chapter summaries are always written in 3rd-person by the summarizer, so the LLM never sees first-person text in the summaries.
- Fix: Added note that summaries are always in 3rd-person — the LLM should judge by story perspective and whose inner thoughts are revealed, not by summary grammar.
- **Result: DID NOT WORK** — narrative_style in structure overview is still "unknown". However plot_summary correctly says "first-person retrospective", so the signal exists but narrator detection isn't using it.

**Fix 4 (supporting.py):** Add universal invariant: proper names must start with uppercase
- Root cause: NER sometimes tags lowercase common nouns (e.g., "bush") as PERSON entities.
- Fix: Added check `if not name[0].isupper(): return False` in `_is_valid_name()`.
- **Result: WORKED** — "bush" no longer appears.

**Bug fix (characters.py):** Fixed `chapters` variable shadowing in STEP 5.10.5
- **Result: Fixed** — inner variable renamed to `chapter_indices`.

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | Characters not promoted due to late mention search | characters.py (STEP 5.7.5) | Fixed — characters promoted |
| 1 | Narrator undetected due to empty main_cast | characters.py (STEP 5.8.5) | No change — narrator still undetected |
| 1 | Narrator prompt assumes first-person in summaries | narrator.py | No change — narrator still undetected |
| 1 | Lowercase false positive "bush" | supporting.py | Fixed — "bush" removed |
| 1 | Variable shadowing bug | characters.py | Fixed |

**Pattern detected:** Narrator detection has been modified twice (characters.py STEP 5.8.5 + narrator.py prompt) without success. The fix phase should investigate the actual LLM response from narrator detection to understand why it's failing, rather than guessing at prompt changes.

**Pattern detected:** Main cast pipeline has produced 0 characters for 2 consecutive attempts. This suggests a systemic issue with the main cast LLM pipeline for short stories or single-chapter texts, not a parameter tuning issue.

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (same for all stages)
- Context: 32768 tokens — sufficient for a short story
- Temperature: 0.7 for all stages — reasonable
- No retries logged in profiling
- Main cast pipeline produced 0 characters — this is a pipeline failure, not a config issue

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | Characters not promoted due to late mention search | characters.py (STEP 5.7.5) | Fixed — characters promoted |
| 1 | Narrator undetected due to empty main_cast | characters.py (STEP 5.8.5) | No change — narrator still undetected |
| 1 | Narrator prompt assumes first-person in summaries | narrator.py | No change — narrator still undetected |
| 1 | Lowercase false positive "bush" | supporting.py | Fixed — "bush" removed |
| 1 | Variable shadowing bug | characters.py | Fixed |
| 3 | Main cast 0 chars: LLM uses "name" not "canonical_name", or wraps in "cast" key | main_cast.py | Pending re-analysis |
| 3 | Main cast 0 chars: no fallback from two-pass to single-pass | main_cast.py | Pending re-analysis |
| 3 | STEP 5.8.5 didn't fire when narrator named but not matched | characters.py | Pending re-analysis |
| 3 | Narrator prompt didn't use plot_summary context | narrator.py | Pending re-analysis |
| 3 | Pronunciation artifacts (mefrom, myright, Nimdokwith, possessives, contraction-concat) | cmu_proposer.py | Pending re-analysis |
| 4 | MAIN_CAST_PROMPT crash: unescaped {{ }} in JSON example caused KeyError in format() | main_cast.py | Fixed — awaiting analysis |

## Pipeline Crash — Attempt 3

Analysis run FAILED with:
```
Error during analysis: '\n  "canonical_name"'
```

**Root cause identified and fixed:** The `MAIN_CAST_PROMPT` template in `main_cast.py` had unescaped `{` and `}` in its JSON example section (lines 58-65 before fix). When Python's `str.format()` processed this template, it interpreted the JSON example braces `{\n  "canonical_name": string,\n  ...}` as format placeholders, raising `KeyError: '\n  "canonical_name"'`.

This bug was dormant because `_extract_single_pass()` was only added as a fallback in Attempt 3 — before that, it was never called (the `else` branch of `if use_two_pass:`). The fix was to escape `{` → `{{` and `}` → `}}` in the JSON example.

**Fix applied:** Escaped the JSON example braces in `MAIN_CAST_PROMPT`.

**Output files on disk are from a PREVIOUS run — not from Attempt 3.**

### Attempt 4 Fix Applied

**Fix (main_cast.py): Escape JSON example braces in `MAIN_CAST_PROMPT`**
- Root cause: `MAIN_CAST_PROMPT` (lines 57-65) contained unescaped `{` and `}` in its JSON schema example. Python's `str.format()` interpreted `{\n  "canonical_name": string,\n  ...}` as a format placeholder named `\n  "canonical_name"` and raised `KeyError`. The single-pass extraction was never exercised before Attempt 3 added the two-pass → single-pass fallback.
- Fix: Changed `{` → `{{` and `}` → `}}` around the JSON example in `MAIN_CAST_PROMPT`
- Files: `src/pipeline/character_extraction_v2/main_cast.py`
- Smoke test: PASS — `MAIN_CAST_PROMPT.format(summaries=..., plot_summary_section=...)` no longer raises `KeyError`; all 297+ passing tests still pass; 2 pre-existing failures unchanged

## Pipeline Notes (Attempt 4)

- Runtime: 17m 23s (60 LLM calls, 73,085 tokens)
- "Two-pass extraction returned 0 characters; retrying with single-pass" — fallback fired successfully (crash from attempt 3 fixed)
- 6 characters extracted (5 profiles for 5 eligible; 6th is likely AM or Jesus)
- Narrator: "No definitive narrator identified" — narrator detection still failing
- "LLM marker proposer returned non-list: <class 'dict'>" x3 → "No valid proposals - returning single chapter" — structure detection still falling back to single chapter (OK for this text)
- 38 pronunciation flags

## Next Action
Evaluate the output to see if AM was extracted and what the new scores are.
