# Current Evaluation State

## Active Text
- **Name:** gift_of_the_magi
- **Attempt:** 2
- **Phase:** awaiting_evaluation
- **baseline_score:** 8.2

## Output Files
- HTML: ../output/gift_of_the_magi/report.html
- JSON: ../output/gift_of_the_magi/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 7.5/10 ✗
  - Completeness: 9/10
  - Identity Resolution: 9/10
  - Alias Grouping: 6/10
- Character Profiles: 7/10 ✗
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 8.5/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 8.2/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold: Character Extraction, Character Profiles)

## Current Issues (Priority Order)

### CRITICAL
1. **Della classified as "supporting" instead of protagonist** [Completeness / Identity Resolution]
   - Problem: Della has ID `360b4be7dd9d` (F6 reconciliation hash), meaning she was NOT found by the main character extraction pipeline. She was added from summaries during F6 reconciliation at analyzer.py:~1197. She has 20 mentions and is the story's co-protagonist — she should be `main_cast` with role `protagonist`.
   - Evidence: The pipeline log says "Pass 2 failed for Della Young, keeping without aliases" — Pass 1 found "Della Young" but Pass 2 (alias resolution) failed, and then she appears to have been dropped from main_cast. F6 then re-added her as just "Della" with a hash ID and "supporting" role.
   - Location: Character extraction pipeline. Likely the main_cast extraction found "Della Young" but she was lost during merge/cleanup steps (characters.py Steps 3.4–5.8). F6 partially recovered her but without proper role or aliases.
   - Fix: Investigate why "Della Young" was dropped from main_cast after Pass 1. The Pass 2 failure should not cause a character to disappear from main_cast — it should keep the Pass 1 result as-is.

### HIGH
2. **Della has zero aliases** [Alias Grouping]
   - Problem: Della's canonical name is "Della" with no aliases. The text uses "Della Young" multiple times. The full formal reference is "Mrs. James Dillingham Young." At minimum "Della Young" should be an alias.
   - Evidence: Pipeline log confirms "Pass 2 failed for Della Young, keeping without aliases"
   - Location: Pass 2 alias resolution in `src/pipeline/character_extraction_v2/main_cast.py`
   - Fix: Linked to CRITICAL #1 — if Della Young is properly retained from Pass 1, she should have canonical "Della Young" (or "Della") with appropriate aliases. The nickname merge (Step 5.5a) or summary-crossref merge (Step 5.4.5) should connect "Della" ↔ "Della Young".

3. **Jim ↔ Della relationship labeled "associated" instead of husband/wife** [Profiles]
   - Problem: Jim and Della are husband and wife — the text explicitly says "her husband Jim" and "his wife." The profiler labeled the relationship as "associated" which is vague and unhelpful for a narrator.
   - Evidence: Text: "her husband, Jim", "his wife had been beauty to him", evidence citation: "Jim is Della's husband"
   - Location: `_generate_character_profile()` in `src/analyzer.py` (~line 2764+) and/or `verify_relationships_from_text` in `src/pipeline/post_corrections.py`
   - Fix: The profiler's evidence correctly identifies "Jim is Della's husband" but the relationship label is "associated." This suggests the relationship label extraction or normalization is broken — it detects the relationship fact but assigns a generic label. Check if `verify_relationships_from_text` is overriding a correct label with "associated."

4. **Jim ↔ Sofronie fabricated relationship** [Profiles]
   - Problem: Jim has a relationship entry `"Sofronie": "associated"`. Jim never interacts with or mentions Sofronie in the text. Sofronie is the shopkeeper Della visits alone.
   - Evidence: Jim appears only at the end when he returns home. He has no scene with Sofronie.
   - Location: Same as #3 — profiler generating relationships for all character pairs regardless of actual interaction
   - Fix: The profiler should only create relationship entries when there is textual evidence of interaction or explicit reference. Likely needs a stricter evidence threshold in the profile prompt.

### MEDIUM
5. **Sofronie missing "Madame Sofronie" / "Mme. Sofronie" aliases** [Alias Grouping]
   - Problem: The text uses "Mme. Sofronie" (on the shop sign) and "Madame" (in narration). These are title+name combinations that should be aliases.
   - Evidence: Text: "the sign read: 'Mme. Sofronie, Hair Goods of All Kinds.'" and "Madame, large, too white, chilly"
   - Location: Pass 2 alias resolution or title-stripped alias logic in main_cast.py
   - Fix: Minor — could be handled by title alias detection. Not blocking since "Sofronie" alone is recognizable.

6. **Della ↔ Sofronie relationship labeled "partner"** [Profiles]
   - Problem: Della is Sofronie's customer, not "partner." Sofronie's profile says "business transaction partner" (closer) but Della's says just "partner" which implies a different relationship.
   - Evidence: Della sells her hair to Sofronie — it's a business transaction.
   - Location: Same profiling code as #3/#4
   - Fix: Will likely be resolved along with #3 and #4

### LOW
7. **Jim missing physical description details** [Profiles]
   - Problem: Jim's physical description only mentions his watch and leather strap. The text also describes him as "thin and very serious" and needing "a new overcoat" and "gloves."
   - Evidence: Text: "Poor fellow, he was only twenty-two—and to be burdened with a family! He needed a new overcoat and he was without gloves."
   - Fix: Minor profile completeness issue, won't block passing threshold.

## Fix History
- Attempt 1: Two fixes applied:
  1. Pass 2 failure fallback alias (`main_cast.py`): When Pass 2 LLM fails for a multi-word canonical name not starting with an article, add the first word as a minimal alias. This prevents the grounding gate from rejecting "Della Young" (which doesn't appear in raw text) when "Della" appears 20+ times.
     - Root cause: `main_cast.py:580-583` — Pass 2 failure leaves canonical "Della Young" with no aliases; grounding gate requires min 3 mentions of canonical; "Della Young" has 0 raw text hits → UNGROUNDED → dropped from main_cast
     - Smoke test: PASS — "Della Young" gets alias "Della"; "the creature" correctly skipped
  2. Spouse label text evidence check (`post_corrections.py`): `reject_unfounded_familial_labels` was unconditionally downgrading "husband"/"wife" labels to "associated" when canonical names share no surname (e.g., "Jim" and "Della" are first-name-only). Changed to use 500-char text evidence check for spouse labels (same window as `verify_relationships_from_text`).
     - Root cause: `post_corrections.py:2274-2281` — unconditional downgrade for non-extended-family labels without shared surname; Jim ("Jim") and Della ("Della") have no surname in their canonicals
     - Smoke test: PASS — is_spouse=True → goes to text evidence check, not unconditional downgrade

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | Della dropped from main_cast; Jim↔Della "associated" | `main_cast.py`, `post_corrections.py` | awaiting_analysis |

## Configuration Audit
- Models: qwen3.5:35b-a3b (structure, pronunciation), qwen3.5:122b-a10b (characters, summaries) — appropriate
- think_mode: false for all — correct for qwen3.5
- character_llm_chunk_chars: 5000 — fine for this short story (~8500 words)
- summary_chunk_words: 2500 — fine for single-chapter story
- No LLM retries recorded — good
- No profiling anomalies

## Pipeline Notes (Attempt 2)
- Della Young: present with alias "Della" (20 mentions) — CRITICAL fix appears to work
- Jim Young: present with alias "Jim" (26 mentions)
- WARNING: "James Dillingham Young" (3 mentions) appears as a SEPARATE character from Jim Young — Jim's full name should be an alias, not a separate character
- WARNING: "Dillingham" (6 mentions) appears as a separate character — likely fragment from "James Dillingham Young" nameplate
- The Magi: present (4 mentions)
- Total: 6 characters extracted
- Runtime: 14m 7s

## Next Action
Evaluate attempt 2 output for score improvement.
