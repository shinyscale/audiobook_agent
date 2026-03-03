# Current Evaluation State

## Active Text
- **Name:** berenice
- **Attempt:** 3
- **Phase:** awaiting_fix
- **baseline_score:** 8.68
- **Competitive Mode:** none

## Output Files
- HTML: ../output/berenice/report.html
- JSON: ../output/berenice/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 8/10 ✓
  - Completeness: 8.5/10
  - Identity Resolution: 7.5/10
  - Alias Grouping: 8/10
- Character Profiles: 7/10 ✗ (FAILING)
- Chapter Summaries: 9.5/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 9/10 ✓
- **Overall: 8.43/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (1 category below threshold: Character Profiles)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1       | 8.68  | —                   | Profiles fail: "cousin" relationship becomes "associated" in output |
| 2       | 8.43  | -0.25               | Profiles fail: attempt 2 fix (narrator co-mention guard) applied; relationship STILL "associated" — fix may have prevented "acquaintance" path but another path or LLM output produces "associated" |

## Current Issues (Priority Order)

### CRITICAL
(none)

### HIGH
1. **Egaeus↔Berenice relationship is "associated" instead of "cousin" — fix did NOT resolve** [Profiles]
   - Problem: ALL character relationships in the output are "associated" — a completely uninformative generic label. The defining relationship of the story (Egaeus and Berenice are cousins) is not captured in the structured relationship field.
   - Evidence:
     - The **summary** correctly says "his energetic cousin Berenice" ✓
     - The **profile source evidence** correctly says "Egaeus describes his relationship with Berenice as cousins growing up together" ✓
     - The **relationship field** says "associated" ✗
   - What happened: The attempt 2 fix added a narrator guard to `verify_relationships_from_text()` to prevent family labels being downgraded to "acquaintance". The relationship changed from "acquaintance" (attempt 1) to "associated" (attempt 2) — suggesting either (a) the LLM generated "associated" directly this run instead of "cousin", or (b) another code path in post_corrections.py is overwriting the label to "associated".
   - **Fix approach — the fix phase MUST investigate which code path produces "associated":**
     1. Add temporary DEBUG logging in `post_corrections.py` at the START and END of each correction step (`verify_relationships_from_text`, `remove_contradictory_relationships`, `enforce_gender_consistency`, `enforce_inverse_consistency`) to print the Egaeus↔Berenice relationship label at each stage
     2. Run the analysis to see where "cousin" (if the LLM generates it) gets overwritten to "associated", OR confirm that the LLM itself generates "associated"
     3. If the LLM generates "associated": Add a post-correction step that reads summary text for kinship terms (cousin, brother, sister, wife, husband, etc.) and upgrades generic labels ("associated", "acquaintance", "unknown") when textual evidence supports a specific term. This is robust against LLM non-determinism.
     4. If a code path overwrites it: Fix that specific code path with the same narrator guard pattern used in attempt 2
   - **IMPORTANT:** post_corrections.py has been modified 2 attempts in a row without fixing the root issue. The fix phase should consider whether the profiling LLM prompt itself needs adjustment, or whether a summary-text-based relationship upgrade is more reliable than defending against every downgrade path.
   - Location: `src/pipeline/character_profiling/post_corrections.py` (investigate full pipeline) and possibly `src/pipeline/character_profiling/` prompt code

### MEDIUM
2. **"The Servant Maiden" falsely merged as alias of "The Teeth"** [Characters — Identity Resolution]
   - Problem: "The Servant Maiden" and "a servant maiden" are listed as aliases of "The Teeth" (the symbolic obsession object). These are completely different — the servant maiden is a person who announces Berenice's death; the teeth are physical objects of obsession.
   - Evidence: In the text, the servant maiden appears "all in tears" to announce the death; "The Teeth" refers to Berenice's teeth that Egaeus obsessively fixates on and ultimately extracts.
   - Location: `src/pipeline/character_extraction_v2/` — alias grouping during extraction
   - Fix: Low priority — doesn't block the 8.0 threshold on profiles.

3. **Some common English words flagged as pronunciations** [Pronunciation]
   - Problem: "light-heartedness", "shrubberies", "refracted", "sentient" are standard English vocabulary — false positives.
   - Evidence: These words are commonly known and wouldn't trip up a narrator.
   - Location: `src/pipeline/pronunciation/cmu_proposer.py` — COMMON_WORDS_WHITELIST
   - Fix: Add these words to the whitelist. Low priority — score is 8/10 already.

### LOW
4. **Ebn Zaiat has "associated" relationship with The Teeth** [Profiles]
   - Problem: Ebn Zaiat is a poet quoted in the epigraph. He has no in-story connection to The Teeth or any other character.
   - Not blocking — dominated by the main Egaeus↔Berenice issue.

5. **Null chapter title for single-section text** [Structure]
   - Problem: The single structure element has `title: null`. Labeling it "Berenice" would be more informative.
   - Not blocking — score is 9/10.

6. **Egaeus has no physical_description** [Profiles]
   - Problem: As first-person narrator, Egaeus doesn't describe his own appearance much. The text does mention he's sickly, melancholic, and lives in gloom — but `physical_description` is null.
   - Partially excusable for 1st-person narration. Not blocking on its own.

## Fix History
- Attempt 1: Added `"cousin"`, `"brother"`, `"sister"`, `"spouse"` to `_SYMMETRIC_RELATIONSHIPS` in post_corrections.py
  - Root cause: `post_corrections.py:_SYMMETRIC_RELATIONSHIPS:line 60` was missing "cousin"
  - Result: Correct fix but insufficient — the relationship was being downgraded BEFORE reaching remove_contradictory_relationships()
  - Modified: src/pipeline/character_profiling/post_corrections.py
- Attempt 2: In `verify_relationships_from_text()`, skip family-label downgrade when `is_narrator=True` for either character
  - Root cause: `post_corrections.py:verify_relationships_from_text():line 1698` — narrator names rarely appear in raw text
  - Result: Relationship changed from "acquaintance" to "associated" — suggests fix addressed one path but another path or LLM non-determinism still produces wrong label
  - Modified: src/pipeline/character_profiling/post_corrections.py

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | Profiles: cousin blocked by _SYMMETRIC_RELATIONSHIPS | post_corrections.py | Fixed but insufficient — different downgrade path active |
| 2 | Profiles: cousin downgraded to acquaintance by verify_relationships_from_text() | post_corrections.py | Changed "acquaintance" to "associated" — NOT fixed, different label but still wrong |

**WARNING: post_corrections.py modified 2x without success. Fix phase MUST investigate the full pipeline (including LLM output and all post-correction steps) before making another blind fix to the same file.**

## Pipeline Notes (Attempt 2 — current output)
- Analysis completed in 15m 17s
- 4 characters found: Egaeus (narrator), Berenice, The Teeth (aka The Servant Maiden), Ebn Zaiat
- 44 pronunciation flags (26 unknown, 13 proper noun, 5 foreign), all with IPA
- Low confidence profile for Ebn Zaiat (0.15) — sparse character
- Narrator detection: Egaeus confirmed as narrator via summaries despite only 1 raw text mention
- Models: structure/pronunciation=qwen3.5:35b-a3b, characters/summaries=qwen3.5:122b-a10b
- Profile evidence correctly captures "cousins growing up together" but relationship field says "associated"
- ALL 5 relationship entries across all characters show "associated" — no specific labels at all

## Next Action
Run PROMPT_fix.md. Fix phase MUST:
1. First INVESTIGATE where "associated" comes from (debug logging through post_corrections pipeline)
2. Then apply a targeted fix based on findings
3. If the LLM is generating "associated" directly, implement a summary-text-based relationship upgrade as a post-correction
