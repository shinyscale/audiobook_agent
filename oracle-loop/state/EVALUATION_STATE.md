# Current Evaluation State

## Active Text
- **Name:** gift_of_the_magi
- **Attempt:** 2
- **Phase:** awaiting_fix
- **baseline_score:** 8.2

## Output Files
- HTML: ../output/gift_of_the_magi/report.html
- JSON: ../output/gift_of_the_magi/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 6/10 ✗
  - Completeness: 8/10
  - Identity Resolution: 4/10 ← Jim split into 3 characters
  - Alias Grouping: 6/10
- Character Profiles: 5.5/10 ✗
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 8.5/10 ✓
- HTML Presentation: 8/10 ✓
- **Overall: 7.6/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold: Character Extraction 6/10, Character Profiles 5.5/10)

**Scoring note:** Attempt 1 scored Identity Resolution 9/10 despite JDY/Dillingham fragmentation being present — that was over-scored. The fragmentation existed in attempt 1 but was under-penalized because the evaluator focused on the Della issue. This attempt scores it accurately against the rubric.

## What Changed From Attempt 1

### Improvements
- **Della fix WORKED**: Della Young is now `main_cast_0` with role `protagonist` and alias "Della" (was F6 hash ID `360b4be7dd9d`, supporting, no aliases). The Pass 2 failure fallback alias in `main_cast.py` prevented the grounding gate from dropping her.

### Regressions
- **Spouse fix REGRESSED**: Jim↔Della relationship changed from "associated" (attempt 1) to "sister"/"sibling" (attempt 2). The `post_corrections.py` change may have opened a code path where shared surname "Young" triggers a sibling classification instead of the previous generic "associated." Both are wrong (correct: husband/wife), but "sister" is actively misleading for a narrator.

### Unchanged
- James Dillingham Young still a separate character (supporting_0, 3 mentions)
- Dillingham still a separate character (supporting_1, 6 mentions, incorrectly role="main")
- Jim↔Sofronie fabricated "associated" relationship
- Sofronie missing "Mme. Sofronie" / "Madame Sofronie" aliases

## Current Issues (Priority Order)

### CRITICAL
1. **Jim fragmented into 3 separate characters** [Identity Resolution]
   - Problem: "Jim Young" (main_cast_1, 26 mentions), "James Dillingham Young" (supporting_0, 3 mentions), and "Dillingham" (supporting_1, 6 mentions) are all the SAME person — Jim, Della's husband. The text explicitly states: "a card bearing the name 'Mr. James Dillingham Young'" and "The 'Dillingham' had been flung to the breeze during a former period of prosperity."
   - Evidence: Jim Young = James Dillingham Young = Mr. James Dillingham Young. "Dillingham" is his middle name used once descriptively.
   - Root cause: Step 5.5a `_merge_formal_name_aliases()` in `src/agents/characters.py` requires main_cast character to be **single-word** (e.g., just "Jim"). But Jim's canonical is "Jim Young" (two words), so the nickname→formal merge (Jim→James) never triggers. Supporting character "James Dillingham Young" (first word "James", formal of "Jim") should merge into "Jim Young" but the single-word gate blocks it.
   - Fix: Extend Step 5.5a to also handle **multi-word** main_cast characters. Check if the FIRST NAME of a multi-word main_cast canonical is a known nickname (Jim→James in NICKNAME_TO_FORMAL), and if any supporting character's first name is the formal equivalent AND they share a surname. If so, merge supporting into main_cast as alias.
   - Cascade: Fixing this should also resolve "Dillingham" via Step 5.5 `_merge_lastname_aliases()`, since once Jim has alias "James Dillingham Young," "Dillingham" becomes a word component of that alias and gets merged.
   - Cascade: Fixing this should also resolve the Jim↔Della "sister" relationship, since the profiler will see all Jim evidence in one character and generate the correct "husband" label.

### HIGH
2. **Jim↔Della relationship labeled "sister"/"sibling"** [Profiles — REGRESSION]
   - Problem: Della's relationship to Jim Young says "sister"; Jim's to Della says "sibling." They are husband and wife. The text says "her husband, Jim" and "his wife had been beauty to him."
   - Evidence: This is WORSE than attempt 1 which had "associated." The spouse fix in `post_corrections.py` may have introduced a code path where shared surname "Young" triggers sibling classification.
   - Root cause: Likely a combination of (a) character fragmentation causing the profiler to see Jim Young and James Dillingham Young as separate people who both have relationships with Della, and (b) `post_corrections.py` or `enforce_gender_consistency` incorrectly interpreting shared surname as sibling evidence.
   - Fix: Primarily cascades from CRITICAL #1. If Jim is one character with all his mentions and textual evidence, the profiler should correctly label the relationship as "husband"/"wife." If the issue persists after merge, investigate the `post_corrections.py` spouse label fix for unintended sibling classification.

3. **Jim↔Sofronie fabricated relationship** [Profiles]
   - Problem: Jim has `"Sofronie": "associated"`. Jim never interacts with or mentions Sofronie. Sofronie is the shopkeeper Della visits alone.
   - Evidence: Jim appears only at the end when he returns home. He has no scene with Sofronie.
   - Location: `_generate_character_profile()` in `src/analyzer.py`
   - Fix: Not blocking — will likely persist but doesn't prevent passing if other issues are fixed. Could be addressed by stricter evidence threshold in profiler prompt.

### MEDIUM
4. **Sofronie missing titled aliases** [Alias Grouping]
   - Problem: "Mme. Sofronie" (shop sign) and "Madame Sofronie" (narration) are not listed as aliases.
   - Evidence: Text: "the sign read: 'Mme. Sofronie, Hair Goods of All Kinds.'"
   - Fix: Minor — title+name alias detection. Not blocking for passing threshold.

5. **Jim missing physical description** [Profiles]
   - Problem: Jim has `physical_description: null`. The text describes him as "thin and very serious," needing "a new overcoat," and "without gloves." He's twenty-two.
   - Fix: May improve naturally once Jim is a single character with all mentions consolidated. The profiler will have more context.

6. **Dillingham incorrectly tagged role="main"** [Identity Resolution]
   - Problem: "Dillingham" (a name fragment, not a character) has role="main" with 6 mentions. This inflates the main character count.
   - Fix: Cascades from CRITICAL #1 — will be merged into Jim Young.

## Fix History
- Attempt 1: Two fixes applied:
  1. Pass 2 failure fallback alias (`main_cast.py`): When Pass 2 LLM fails for a multi-word canonical name not starting with an article, add the first word as a minimal alias. This prevents the grounding gate from rejecting "Della Young" (which doesn't appear in raw text) when "Della" appears 20+ times.
     - Root cause: `main_cast.py:580-583` — Pass 2 failure leaves canonical "Della Young" with no aliases; grounding gate requires min 3 mentions of canonical; "Della Young" has 0 raw text hits → UNGROUNDED → dropped from main_cast
     - Smoke test: PASS — "Della Young" gets alias "Della"; "the creature" correctly skipped
     - **Result: FIXED** — Della Young now main_cast_0 protagonist with alias "Della"
  2. Spouse label text evidence check (`post_corrections.py`): `reject_unfounded_familial_labels` was unconditionally downgrading "husband"/"wife" labels to "associated" when canonical names share no surname (e.g., "Jim" and "Della" are first-name-only). Changed to use 500-char text evidence check for spouse labels (same window as `verify_relationships_from_text`).
     - Root cause: `post_corrections.py:2274-2281` — unconditional downgrade for non-extended-family labels without shared surname; Jim ("Jim") and Della ("Della") have no surname in their canonicals
     - Smoke test: PASS — is_spouse=True → goes to text evidence check, not unconditional downgrade
     - **Result: REGRESSION** — relationship changed from "associated" to "sister" (worse). But this may be caused by character fragmentation rather than the fix itself. Now Jim Young and Della Young DO share surname "Young," so a different code path fires.

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | Della dropped from main_cast | `main_cast.py` | Fixed ✓ |
| 1 | Jim↔Della "associated" spouse label | `post_corrections.py` | Regression (→ "sister") |

## Configuration Audit
- Models: qwen3.5:35b-a3b (structure, pronunciation), qwen3.5:122b-a10b (characters, summaries) — appropriate
- think_mode: false for all — correct for qwen3.5
- character_llm_chunk_chars: 5000 — fine for this short story (~8500 words)
- summary_chunk_words: 2500 — fine for single-chapter story
- No LLM retries recorded — good
- No profiling anomalies
- No configuration changes needed

## Next Action
Run PROMPT_fix.md to address CRITICAL #1 (Jim fragmentation in characters.py Step 5.5a). This is the primary blocker — fixing it should cascade-resolve HIGH #2 (sibling relationship) and MEDIUM #6 (Dillingham role). The fix should extend `_merge_formal_name_aliases()` to handle multi-word main_cast names where the first name is a known nickname.
