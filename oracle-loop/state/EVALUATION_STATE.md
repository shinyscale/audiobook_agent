# Current Evaluation State

## Active Text
- **Name:** gift_of_the_magi
- **Attempt:** 3
- **Phase:** awaiting_analysis
- **baseline_score:** 8.2

## Output Files
- HTML: ../output/gift_of_the_magi/report.html
- JSON: ../output/gift_of_the_magi/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 8.5/10 ✓
  - Completeness: 9/10
  - Identity Resolution: 9/10
  - Alias Grouping: 8/10
- Character Profiles: 7/10 ✗ ← ONLY FAILING CATEGORY
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 9/10 ✓
- **Overall: 8.475/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (1 category below threshold: Character Profiles 7/10)

## What Changed From Attempt 2

### Improvements
- **Jim merge fix WORKED**: Jim (main_cast_1, 32 mentions) now correctly has aliases "James Dillingham Young" and "Dillingham." No more character fragmentation. Identity Resolution improved from 4/10 → 9/10.
- **Sibling label FIXED**: Jim↔Della relationship is now "associated" (was "sister"/"sibling" in attempt 2). Still wrong, but no longer actively misleading.
- **Dillingham merged**: No longer a separate character inflating main cast count.

### Unchanged
- Jim↔Della relationship still not "husband"/"wife" — now "associated"
- Jim missing physical description (text says "thin and very serious," "twenty-two," "needed a new overcoat," "without gloves")
- Sofronie↔magi fabricated "associated" relationship persists
- Sofronie still missing "Mme. Sofronie"/"Madame Sofronie" aliases

## Current Issues (Priority Order)

### HIGH
1. **Jim↔Della relationship labeled "associated" instead of "husband"/"wife"** [Profiles — PRIMARY BLOCKER]
   - Problem: Della→Jim and Jim→Della both say "associated." They are husband and wife. The text says "her husband, Jim" and "his wife had been beauty to him." The profiler evidence even correctly states: "Jim is the husband of Della Young" with the quote "But whenever Mr. James Dillingham Young came home and reached his flat above he was called 'Jim' and greatly hugged by Mrs. James Dillingham Young."
   - Evidence: The profiler LLM correctly identified "husband" but the label was downgraded by post_corrections.
   - Root cause: `reject_unfounded_familial_labels` in `src/pipeline/post_corrections.py` checks for shared surnames between canonical names. Jim's canonical is "Jim" (no surname) and Della's canonical is "Della Young." With no shared surname, the spouse label gets downgraded to "associated." Jim now has alias "James Dillingham Young" (which contains "Young"), but post_corrections likely only checks canonical names, not aliases, for surname matching.
   - Fix: In `reject_unfounded_familial_labels`, when checking for shared surnames between two characters, also check the character's **aliases** for surname components. If Jim's alias "James Dillingham Young" shares surname "Young" with Della's canonical "Della Young," the spouse label should be preserved rather than downgraded. Alternatively, use the text evidence check (which the attempt 1 fix was supposed to add) — the co-mention window should find "husband" or "wife" near their names.
   - Impact: Fixing this alone should push Profiles from 7/10 → 8+/10.

### MEDIUM
2. **Jim missing physical description** [Profiles]
   - Problem: Jim's physical_description says "Physical description is not provided in the text" — this is factually wrong. The text contains: "He was thin and very serious," "Poor fellow, he was only twenty-two—and to be burdened with a family!" "He needed a new overcoat and he was without gloves."
   - Evidence: The profiler evidence list doesn't include these textual details, suggesting the LLM didn't extract them.
   - Root cause: These physical details are scattered in the narrator's commentary early in the story (before Jim's physical appearance scene). The profiler may weight character-introduction scenes more heavily than narrator asides.
   - Fix: Not blocking for pass threshold — fixing the relationship alone should push profiles to 8/10. This would push profiles higher (toward 9) but is not required.

3. **Sofronie missing titled aliases** [Alias Grouping]
   - Problem: "Mme. Sofronie" (shop sign) and "Madame Sofronie" (narration) not listed as aliases.
   - Evidence: Text says "the sign read: 'Mme. Sofronie, Hair Goods of All Kinds.'"
   - Fix: Minor — title+name alias detection. Not blocking.

4. **Fabricated Sofronie↔magi relationship** [Profiles]
   - Problem: Sofronie has "The magi": "associated" and The magi has "Sofronie": "associated." These entities have no relationship in the text.
   - Fix: Profiler evidence threshold issue. Not blocking for pass threshold.

5. **"meretricious" IPA slightly incorrect** [Pronunciation]
   - Problem: IPA given as `/məˈtrɪt.ʃi.əs/` — the standard pronunciation is /ˌmɛr.ɪˈtrɪʃ.əs/ (stress on third syllable, not second).
   - Fix: Minor LLM accuracy issue. Not blocking.

## Fix History
- Attempt 1: Two fixes applied:
  1. Pass 2 failure fallback alias (`main_cast.py`): → **FIXED** Della Young now main_cast_0 with alias "Della"
  2. Spouse label text evidence check (`post_corrections.py`): → **REGRESSION** (sister/sibling in attempt 2, now "associated" in attempt 3)
- Attempt 2: Extended `_merge_formal_name_aliases()` in `src/agents/characters.py` for multi-word main_cast names → **FIXED** Jim now has aliases "James Dillingham Young" and "Dillingham"

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | Della dropped from main_cast | `main_cast.py` | Fixed ✓ |
| 1 | Jim↔Della "associated" spouse label | `post_corrections.py` | Regression → "sister" (attempt 2), now "associated" (attempt 3) |
| 2 | Jim fragmented into 3 characters | `characters.py` | Fixed ✓ |

**Note:** `post_corrections.py` has been modified once (attempt 1) and the spouse label is still wrong. The root cause was misidentified — the surname check needs to consider aliases, not just canonicals. This is the SAME file but a DIFFERENT code path (alias-aware surname matching vs. text evidence check).

## Configuration Audit
- Models: qwen3.5:35b-a3b (structure, pronunciation), qwen3.5:122b-a10b (characters, summaries) — appropriate
- think_mode: false for all — correct for qwen3.5
- character_llm_chunk_chars: 5000 — fine for this short story
- summary_chunk_words: 2500 — fine for single-chapter story
- No configuration changes needed

## Fix History (continued)
- Attempt 3: Extended `_surnames()` usage in `reject_unfounded_familial_labels()` to include aliases for both `char` and `other_char`. Jim's alias "James Dillingham Young" now contributes "young" and "dillingham" to `char_surnames`, which intersects Della Young's "young" → spouse label preserved without downgrade.
  - Root cause: `post_corrections.py:reject_unfounded_familial_labels():2249` — `_surnames()` was only called on canonical names, missing surname evidence in aliases.
  - Smoke test: 332 tests pass, 0 failures.
  - Modified: `src/pipeline/character_profiling/post_corrections.py`

## Next Action
Re-run analysis to verify Jim↔Della now has "husband"/"wife" labels and Character Profiles reaches 8/10.
