# Current Evaluation State

## Active Text
- **Name:** gift_of_the_magi
- **Attempt:** 5
- **Phase:** awaiting_evaluation
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
- Character Profiles: 7.5/10 ✗ ← ONLY FAILING CATEGORY
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 8.5/10 ✓
- HTML Presentation: 9/10 ✓
- **Overall: 8.6/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (1 category below threshold: Character Profiles 7.5/10)

## What Changed From Attempt 3

### Improvements
- **Jim physical description NOW PRESENT**: Jim is described as "thin and very serious," needing a new overcoat, without gloves. This was missing in attempt 2.
- **"meretricious" IPA improved**: Now `/ˌmɛr.əˈtrɪʃ.əs/` (was `/məˈtrɪt.ʃi.əs/`). Much closer to correct.
- **Profiler evidence is correct**: Evidence clearly states "Jim is the husband of Della Young" with the direct quote about Mr./Mrs. James Dillingham Young. Also "Della is married to Jim." The LLM is doing its job.

### Still Broken
- **Jim↔Della relationship still "associated" instead of "husband"/"wife"** — the surname-matching fix in `reject_unfounded_familial_labels` was CORRECT but addresses the WRONG bottleneck (see root cause below).

## Root Cause Analysis (Attempt 3 Fix)

The attempt 3 fix to `reject_unfounded_familial_labels` (alias-aware surname matching) is logically correct — Jim's alias "James Dillingham Young" shares surname "Young" with Della Young. **However, this function never gets a chance to preserve the label** because:

1. **Line 764**: `extract_relationships_from_evidence()` correctly sets Jim→Della = "husband" (from evidence "Jim is the husband of Della Young")
2. **Line 775**: `add_cooccurrence_relationships()` **unconditionally overwrites** Jim→Della = "associated" (line 999: `char_a.relationships[char_b.canonical_name] = "associated"` — no check for existing non-generic labels)
3. **Line 779**: `reject_unfounded_familial_labels()` sees "associated" (not a family term) → skips the entry entirely

The fix must be in `add_cooccurrence_relationships` (line 999), NOT in `reject_unfounded_familial_labels`.

## Current Issues (Priority Order)

### HIGH
1. **Jim↔Della relationship labeled "associated" instead of "husband"/"wife"** [Profiles — PRIMARY BLOCKER]
   - Problem: `add_cooccurrence_relationships()` at line 999 of `post_corrections.py` unconditionally sets `char_a.relationships[char_b.canonical_name] = "associated"` without checking if a more specific label was already set by `extract_relationships_from_evidence()`.
   - Evidence: Profiler evidence correctly says "Jim is the husband of Della Young" (high confidence, with direct quote). But `add_cooccurrence_relationships` runs after and overwrites with "associated."
   - Location: `src/pipeline/character_profiling/post_corrections.py`, method `add_cooccurrence_relationships()`, line ~999
   - Fix: Before setting "associated" at line 999, check if a non-generic relationship already exists for the pair. If `char_a.relationships.get(char_b.canonical_name)` is already a specific label (not in `{"associated", "acquaintance", "unknown", ""}` or None), skip the overwrite. Same for the reverse direction at line 1000.
   - Impact: Fixing this alone should push Profiles from 7.5/10 → 8.5+/10.

### MEDIUM
2. **Fabricated Sofronie↔magi and Jim↔Sofronie relationships** [Profiles]
   - Problem: Sofronie has relationships to "the magi" ("associated") and Jim ("associated") — neither of these exist in the text. Sofronie interacts only with Della (hair purchase scene).
   - Evidence: Jim never meets Sofronie. The magi are a biblical allusion, not a character Sofronie interacts with.
   - Location: Likely `add_cooccurrence_relationships()` — single-chapter story means all characters co-occur in the same summary, triggering spurious associations.
   - Fix: Not blocking for pass threshold. Could increase `min_shared` for very short texts or add a mention-proximity check.

3. **Sofronie missing titled aliases** [Alias Grouping]
   - Problem: "Mme. Sofronie" and "Madame Sofronie" not listed as aliases.
   - Evidence: Text says "the sign read: 'Mme. Sofronie, Hair Goods of All Kinds.'"
   - Fix: Minor — title+name alias detection. Not blocking.

### LOW
4. **Jim missing "Mr. James Dillingham Young" alias** [Alias Grouping]
   - Problem: Text uses "Mr. James Dillingham Young" but only "James Dillingham Young" is an alias.
   - Fix: Title-prefix alias detection. Not blocking.

5. **Della missing "Mrs. James Dillingham Young" alias** [Alias Grouping]
   - Problem: Text uses "Mrs. James Dillingham Young" but this isn't listed as an alias for Della.
   - Fix: Cross-character titled reference detection. Not blocking.

## Fix History
- Attempt 1: Two fixes applied:
  1. Pass 2 failure fallback alias (`main_cast.py`): → **FIXED** Della Young now main_cast_0 with alias "Della"
  2. Spouse label text evidence check (`post_corrections.py`): → **REGRESSION** (sister/sibling in attempt 2, now "associated" in attempt 3)
- Attempt 2: Extended `_merge_formal_name_aliases()` in `src/agents/characters.py` for multi-word main_cast names → **FIXED** Jim now has aliases "James Dillingham Young" and "Dillingham"
- Attempt 3: Extended `_surnames()` in `reject_unfounded_familial_labels()` to include aliases → **No effect** (correct fix, wrong bottleneck — "husband" was already overwritten to "associated" before this function runs)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | Della dropped from main_cast | `main_cast.py` | Fixed ✓ |
| 1 | Jim↔Della spouse label | `post_corrections.py` (reject_unfounded_familial_labels) | Regression → "sister" |
| 2 | Jim fragmented into 3 characters | `characters.py` | Fixed ✓ |
| 3 | Jim↔Della spouse label (surname matching) | `post_corrections.py` (reject_unfounded_familial_labels) | No effect — wrong bottleneck |
| 4 | Jim↔Della spouse label (cooccurrence overwrite) | `post_corrections.py` (add_cooccurrence_relationships) | Wrong root cause |
| 5 | Jim↔Della spouse label (verify_relationships cross-tier) | `post_corrections.py` (verify_relationships_from_text, _infer_rel) | **APPLIED** |

**Note:** `post_corrections.py` modified in attempts 1 and 3, but different functions. Attempt 4 targets a THIRD function (`add_cooccurrence_relationships`) which is the actual root cause. The attempt 3 fix was correct code but addressed downstream of the real problem.

## Configuration Audit
- Models: qwen3.5:35b-a3b (structure, pronunciation), qwen3.5:122b-a10b (characters, summaries) — appropriate
- think_mode: false for all — correct for qwen3.5
- character_llm_chunk_chars: 5000 — fine for this short story
- summary_chunk_words: 2500 — fine for single-chapter story
- No configuration changes needed
- Profiling: 4 HIGH confidence items, 0 LOW confidence, 0 retries — pipeline is healthy

## Actual Root Cause (Attempt 5)

The real problem was NOT in `add_cooccurrence_relationships` (the check at lines 981-984 correctly skipped already-set pairs).

The actual flow:
1. `extract_relationships_from_evidence`: Jim→Della = "husband" ✓; Della→Jim = "associated" (evidence "Della is married to Jim" — "married" had no family term match)
2. `verify_relationships_from_text`: In Jim+Della co-mention windows, "father" and "grandfather" (from "his father's watch") appeared 4× each, overriding "husband" → "father" (and "associated" → "father" for Della)
3. `fix_bidirectional_parent_labels`: Both = "father" → converts to "associated"

## Fixes Applied (Attempt 5)

1. **Cross-tier guard: spousal → parent/child** (`verify_relationships_from_text`):
   - Added symmetric guard: don't override spousal label (husband/wife/spouse) with parent/child label (father/mother/son/daughter) from co-mention windows
   - The existing guard only blocked parent/child → spousal; this is the symmetric case
   - Universal: any book with a couple + passages about one partner's ancestors would benefit

2. **"married" → "spouse" in `_infer_rel`** (`extract_relationships_from_evidence`):
   - Added "married"/"marries"/"spouse" detection before family terms loop
   - Returns "spouse" (neutral) so gender-appropriate term can be assigned later
   - Without this, "Della is married to Jim" → "associated" (generic) → not protected by spousal guard

## Pipeline Notes (Attempt 5)
- Health check fix applied: `analyzer.py` now sets `config.think = False` on default client to avoid empty responses from qwen3.5 thinking mode
- 4 characters extracted: Della Young (alias: Della), Jim Young (aliases: Jim, James Dillingham Young), Sofronie, The magi
- Pass 2 failed for Della Young (keeping without aliases) — not blocking
- No narrator identified (correct — 3rd-person narrative)
- 4 profiles generated (4 HIGH confidence)
- Runtime: 28m 7s

## Next Action
Evaluate output.
