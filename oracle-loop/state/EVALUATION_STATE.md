# Current Evaluation State

## Active Text
- **Name:** monkeys_paw
- **Attempt:** 4
- **Phase:** complete
- **baseline_score:** 7.4

## Output Files
- HTML: ../output/monkeys_paw/report.html
- JSON: ../output/monkeys_paw/analysis.json

## Latest Scores
- Structure Detection: 8/10 ✓
- Character Extraction: 8.5/10 ✓
  - Completeness: 9/10
  - Identity Resolution: 10/10
  - Alias Grouping: 7.5/10
- Character Profiles: 8/10 ✓
- Chapter Summaries: 9.5/10 ✓
- Pronunciation Guide: 9/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 8.6/10**

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** PASS — all categories at or above 8.0

## Evaluation Details

### Structure Detection: 8/10
- 3 parts correctly detected ✓ (The Monkey's Paw has 3 parts)
- Chapter titles show Arabic numerals ("1", "2", "3") instead of original Roman ("I", "II", "III") — cosmetic issue persisting from attempt 1
- Word counts and reading times present and reasonable

### Character Extraction: 8.5/10
**Completeness: 9/10**
- All 4 named human characters present: Mr. White (25), Mrs. White (21), Herbert White (15), Sergeant-Major Morris (5) ✓
- Monkey's paw extracted as symbolic force (17 mentions) — acceptable for narrator prep
- The unnamed Maw & Meggins representative is not extracted, which is fine (unnamed)

**Identity Resolution: 10/10**
- Phantom "The Old Man" character from attempt 3 is completely GONE ✓ — major fix success
- No false merges, no false splits
- All White family members correctly distinct
- Morris correctly separate from the White family

**Alias Grouping: 7.5/10**
- Mr. White: "the old man" ✓ (was missing in attempt 3, now restored)
- Mrs. White: "the old woman" ✓ (was missing in attempt 3, now restored)
- Herbert White: "Herbert", "the son" ✓
- Morris: "Morris" ✓
- Monkey's paw: "the paw" ✓, "the visitor" ✗ (refers to the Maw & Meggins representative in Ch 2), "the stranger" ✗ (refers to Morris/M&M rep, not the paw)
- The two wrong aliases are on the symbolic object, not on human characters — impact mitigated

### Character Profiles: 8/10
- Mr. White: Physical description ("thin grey beard"), personality (hospitable→anxious→protective), speech patterns (stammering, whispering hoarsely) all accurate ✓
- Mrs. White: Profile now captures full arc including Part III ("wildly emotional", "desperate", "determined", "obsessive") ✓ — was incomplete in attempt 3
- Herbert White: Physical description confusingly leads with Morris's description ("tall, burly man, rubicund complexion") before self-correcting. Personality accurate (lighthearted, witty, skeptical) ✓
- Morris: Accurate ("tall, burly man, beady eyes, ruddy face", grave about the paw) ✓
- Monkey's paw: Good characterization as malevolent entity ✓
- Family relationships ALL CORRECT: father/son/mother/husband/wife chain ✓
- Remaining issues: Herbert gender null (fix didn't take effect), Morris→paw="friend" (should be wary/associated), paw gender="male" (inanimate)

### Chapter Summaries: 9.5/10
- Part I: Accurately covers Morris's arrival, paw introduction, fakir's curse, first wish for £200, paw twisting ✓
- Part II: Correctly describes Herbert's death, Maw & Meggins visitor, £200 compensation, Mr. White collapsing ✓
- Part III: Captures Mrs. White's desperation, second wish, knocking at door, third wish, wail of disappointment ✓
- All summaries well-detailed and useful for narrator preparation
- No hallucinations detected

### Pronunciation Guide: 9/10
- Good flagging: fakir/fakirs, rubicund, antimacassar, condoled, bibulous, shamefacedly, avaricious ✓
- Proper nouns: Sergeant-Major, Meggins ✓
- Homographs: live, minute, separate correctly identified with both pronunciations ✓
- IPA provided for all 14 entries ✓
- No false positives

### HTML Presentation: 8.5/10
- Navigation functional ✓
- Character cards with aliases displayed ✓
- Chapter summaries with character tags ✓
- Minor: Arabic chapter titles instead of Roman

## What Improved from Attempt 3
1. **Phantom "The Old Man" eliminated** — descriptor merge fix worked ✓ (CRITICAL issue resolved)
2. **Mr. White alias "the old man" restored** ✓
3. **Mrs. White alias "the old woman" restored** ✓
4. **Family relationships correct** — father/son/mother/husband/wife chain intact ✓
5. **Mrs. White profile enriched** — now captures Part III emotional arc ✓
6. **Processing time halved** — 20m 43s vs 40m 1s in attempt 3

## Remaining Known Issues (not blocking pass)
- Herbert gender null (attempted fix in post_corrections.py didn't trigger)
- Monkey's paw aliases "the visitor"/"the stranger" incorrect
- Herbert physical description attributes Morris's appearance initially
- Morris→paw relationship "friend" is inaccurate
- Paw is_symbolic=false, gender="male" (inanimate object metadata)
- Chapter titles Arabic instead of Roman numerals

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 7.4 | — | Baseline — Morris dropped, visitor alias wrong, Mr. White no aliases |
| 2 | 8.25 | +0.85 | Morris restored, aliases fixed, but new relationship label error |
| 3 | 7.5 | +0.1 | Relationship fix worked ✓, but phantom "The Old Man" appeared (LLM non-determinism) |
| 4 | 8.6 | +1.2 | Phantom resolved ✓, all aliases restored ✓, relationships correct ✓ — **PASS** |

## Fix History
- Attempt 1 (monkeys_paw):
  - **Morris missing (Completeness)**: Added military/clerical ranks to `_add_title_stripped_aliases()` in `main_cast.py` so "Sergeant-Major Morris" gets "Morris" as auto-alias → enough mentions to pass grounding. Also added `not pc.id.startswith("main_cast_")` guard to `_convert_characters` evidence filter in `analyzer.py` — main_cast characters (LLM-vetted) are never dropped by the false-positive filter.
  - **Mrs. White gender (Profiles)**: Added second call to `enforce_gender_consistency` at end of Phase B `run_all` (after `_propagate_missing_reverses`) in `post_corrections.py` — catches any re-introduced gender mismatches.
  - **Pronunciation false positives**: Added "bedclothes", "instalment", "betokened" (and variants) to `COMMON_WORDS_WHITELIST` in `cmu_proposer.py`.

- Attempt 2 (monkeys_paw):
  - **Mr. White→Herbert "husband" (Profiles)**: Added `fix_family_spousal_triangle()` in `post_corrections.py` — if A→B="son"/"daughter" and B→C="wife"/"husband", set A→C=same child label. Also added `infer_gender_from_title()` for Mr./Mrs. title-based gender.
  - **Gender null (Profiles)**: Added `gender` field to Character model in `models.py`.

- Attempt 3 (monkeys_paw):
  - **Phantom "The Old Man" (Identity Resolution)**: Extended `_merge_descriptor_into_proper_name()` in `characters.py` to handle title-cased common-noun descriptors (e.g., "The Old Man"). Also added garbage alias reassignment for descriptors like "the old woman" to be reassigned to correct character (Mrs. White).
  - **Herbert gender (Profiles)**: Added relationship-based gender inference to `infer_gender_from_title()` — if relationship is "son"→male, "daughter"→female. (Did not trigger in attempt 4 — may need investigation)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | Morris missing (Completeness) | `main_cast.py`, `analyzer.py` | Fixed ✓ |
| 1 | Mrs. White gender (Profiles) | `post_corrections.py` | Fixed ✓ |
| 1 | Pronunciation false positives | `cmu_proposer.py` | Fixed ✓ |
| 2 | Mr. White→Herbert "husband" (Profiles) | `post_corrections.py`, `models.py` | Fixed ✓ |
| 2 | All genders null | `post_corrections.py`, `models.py` | Fixed ✓ |
| 3 | Phantom "The Old Man" (Identity Resolution) | `characters.py` | Fixed ✓ |
| 3 | Mrs. White missing alias (Alias Grouping) | `characters.py` | Fixed ✓ |
| 3 | Herbert gender null (Profiles) | `post_corrections.py` | No change (fix didn't trigger) |

## Configuration Audit
- Models: qwen3.5:35b-a3b (structure, pronunciation), qwen3.5:122b-a10b (chars, summaries, profiles) — appropriate
- Context length: 32768 — sufficient for this short story (3,954 words)
- Temperature: 0.7 — reasonable
- think_mode: false — correct for qwen3.5
- Duration: 20m 43s, 38 LLM calls, 83,243 tokens
- All 5 profiles at HIGH confidence
- No JSON parse failures
- No LLM retries

## Next Action
**PASS** — monkeys_paw complete. Ready to advance to next text (cask_of_amontillado).
