# Current Evaluation State

## Active Text
- **Name:** monkeys_paw
- **Attempt:** 1
- **Phase:** awaiting_analysis
- **baseline_score:** 8.08
- **Competitive Mode:** single

## Output Files
- HTML: ../output/monkeys_paw/report.html
- JSON: ../output/monkeys_paw/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 7/10 ✗
  - Completeness: 8/10
  - Identity Resolution: 7/10
  - Alias Grouping: 6/10
- Character Profiles: 6.5/10 ✗
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 8.5/10 ✓
- HTML Presentation: 9/10 ✓
- **Overall: 8.08/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold: Character Extraction 7/10, Character Profiles 6.5/10)

## Current Issues (Priority Order)

### CRITICAL
1. **False aliases on "the monkey's paw": "the visitor", "the old fakir", "an old fakir"** [Identity Resolution, Alias Grouping]
   - Problem: Three aliases incorrectly assigned to the monkey's paw entry
   - "the visitor" refers to the representative from Maw and Meggins who delivers news of Herbert's death in Part II — a separate human character
   - "the old fakir" / "an old fakir" refers to the Indian holy man who originally enchanted the paw — a distinct person, not the paw itself
   - Evidence: In the text, the fakir is described as a person who "wanted to show that fate ruled people's lives" and put a spell ON the paw. The visitor is described as "a well-dressed stranger" from the firm who walks up the path to deliver compensation news
   - Source: All characters have `main_cast_*` IDs, so this is a main_cast pipeline issue
   - Location: V2 character extraction pipeline — likely alias resolution in `src/pipeline/character_extraction_v2/` where the LLM is over-merging references to the paw
   - Fix approach: The alias verification should block aliases that refer to distinct entities mentioned in the text. "The visitor" and "the old fakir" are clearly separate beings from an inanimate object

### HIGH
2. **Herbert White's physical description is WRONG — attributed from Morris** [Profiles]
   - Problem: Herbert is described as "tall and burly" but this is Sergeant-Major Morris's description
   - Evidence: The text says Morris is "a tall, burly man, beady of eye and rubicund of visage." Herbert is never described as tall and burly — he's a young man who works at Maw and Meggins
   - Location: Profile generation in `src/analyzer.py` (`_generate_character_profile()`)
   - Fix approach: This is an LLM hallucination during profile generation — the model confused which character the physical description belongs to. This may be a prompt issue or a context/chunking issue where the physical description appears near Herbert's dialogue

3. **Mrs. White → Herbert relationship labeled "father" instead of "mother"** [Profiles]
   - Problem: Mrs. White's relationship entry for Herbert White says "father" — this is factually wrong. Mrs. White is Herbert's mother
   - Evidence: The text consistently refers to her as "mother" and Herbert as her "son". Herbert's own entry correctly says his relationship to Mrs. White is "son"
   - Location: Relationship generation in profile pipeline — the LLM used the wrong gendered label
   - Fix approach: Cross-validation of relationship labels (if A→B is "son", B→A should be "mother" not "father")

### MEDIUM
4. **Morris → monkey's paw relationship labeled "friend"** [Profiles]
   - Problem: Sergeant-Major Morris's relationship to the paw is labeled "friend" — semantically wrong. Morris was a previous owner/possessor of the paw, not its friend
   - Fix approach: "associated" or "previous owner" would be more accurate. The LLM's valid relationship labels may not include "previous owner" — check if label vocabulary is too restrictive

5. **Morris ↔ Mr. White relationship labeled "associated" instead of "friend"** [Profiles]
   - Problem: Morris and Mr. White are old friends — Morris visits them specifically. "associated" is too vague
   - Evidence: Text describes Morris arriving as a guest, sharing stories and drinks, suggesting a long friendship
   - Fix approach: May be a label vocabulary issue — "friend" is a valid label but wasn't selected

### LOW
6. **Mr. White and Mrs. White have zero aliases** [Alias Grouping]
   - Problem: The text frequently uses "the old man" for Mr. White and "the old woman"/"the old lady" for Mrs. White. These were blocked by verification rules per the analysis notes
   - This is a known trade-off — the verification rules correctly block ambiguous descriptive phrases in general, but for this story they're unambiguous
   - Not worth fixing for 8.0 threshold — too risky to loosen verification rules

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 8.08 | 0 | Baseline. Characters 7/10, Profiles 6.5/10 failing |

## Fix History
- Attempt 1 (Fix A): Clarified `is_symbolic: true` in CHARACTER_IDENTIFICATION_PROMPT for non-person entities
  - Root cause: `src/pipeline/character_extraction_v2/main_cast.py:CHARACTER_IDENTIFICATION_PROMPT` rule 1 — LLM not instructed to set is_symbolic=true for objects, so semantic coherence check (Rule 0.5) never activated, allowing "the visitor" and "the old fakir" to pass as aliases of the paw
  - Smoke test: PASS — prompt clarification is minimal (one sentence appended to rule 1), tests all pass
  - Modified: `src/pipeline/character_extraction_v2/main_cast.py`

- Attempt 1 (Fix B): Extended `enforce_gender_consistency` to detect gender from canonical name titles (Mr./Mrs./Ms./Miss)
  - Root cause: `src/pipeline/character_profiling/post_corrections.py:enforce_gender_consistency` — read gender only from `char.descriptions` text excerpts; "Mrs. White" has no female pronouns in description text, so is_female=False, "father" label not corrected
  - Fix: also check canonical_name for "mrs."/"ms."/"miss " → is_female, "mr." (not "mrs.") → is_male
  - Additionally improved: changed "unknown" correction to gender-appropriate reverse label ("father"→"mother", etc.)
  - Smoke test: PASS — 325 tests pass including updated TestEnforceGenderConsistency tests
  - Modified: `src/pipeline/character_profiling/post_corrections.py`, `tests/test_post_corrections.py`

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 (Fix A) | False aliases on monkey's paw [Critical #1] | main_cast.py (CHARACTER_IDENTIFICATION_PROMPT) | Awaiting re-analysis |
| 1 (Fix B) | Mrs. White "father" → "mother" [High #3] | post_corrections.py, test_post_corrections.py | Awaiting re-analysis |

## Configuration Audit
- Models: qwen3.5:35b-a3b (structure, pronunciation), qwen3.5:122b-a10b (characters, summaries) — appropriate sizing
- Context: 32768 for all agents — sufficient for a short story
- Temperature: 0.7 for all — reasonable
- Zero LLM retries across all stages — good
- No profiling red flags

## Next Action
Re-run analysis on monkeys_paw to verify:
- Fix A: monkey's paw gets is_symbolic=true → "the visitor" and "the old fakir" blocked by Rule 0.5 → Identity Resolution + Alias Grouping improve
- Fix B: Mrs. White relationship to Herbert corrected from "father" to "mother" → Profiles improve
- Still open: Herbert's wrong physical description (#2), Morris labels (#4, #5)
