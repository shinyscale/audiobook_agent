# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 3
- **Phase:** awaiting_fix
- **baseline_score:** 6.55
- **Competitive Mode:** none

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 4/10 ✗ (FAILING — REGRESSION from 5/10)
  - Completeness: 4/10
  - Identity Resolution: 3/10 ← "American, sir" false character + narrator regression + Johnny still merged
  - Alias Grouping: 5/10
- Character Profiles: 4/10 ✗ (FAILING — REGRESSION from 5.5/10)
- Chapter Summaries: 5/10 ✗ (FAILING)
- Pronunciation Guide: 8.5/10 ✓
- HTML Presentation: 7.5/10 ✗ (FAILING — REGRESSION from 8.5/10)
- **Overall: 6.0/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (4 categories below threshold — REGRESSION from attempt 2)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.55 | 0 | Baseline. Narrator misidentification cascades into profiles + summaries |
| 2 | 6.6 | +0.05 | Narrator fix worked (Bill=narrator ✓, Bill profile correct ✓). But Johnny still missing, summary still wrong. |
| 3 | 6.0 | -0.55 | **REGRESSION.** "American, sir" false character stole narrator from Uncle Bill. Johnny still missing. |

## REGRESSION ALERT

**Score dropped from 6.6 → 6.0 (below baseline - 0.3 = 6.25). The attempt 3 fix should be REVERTED.**

The `_merge_lastname_aliases` exact_firstname guard (commit 1418ccf) caused:
1. NEW false positive: "American, sir" extracted as a character (was NOT present in attempt 2)
2. NARRATOR REGRESSION: "American, sir" tagged as narrator instead of Uncle Bill
3. Uncle Bill's physical description transferred to "American, sir"
4. NO IMPROVEMENT: Johnny (the son) still merged into John Donaldson (the father)

Likely mechanism: In attempt 2, the merge logic may have absorbed "American, sir" into Uncle Bill (since the phrase is associated with him). The attempt 3 guard, by blocking certain merges, prevented this valid absorption — exposing "American, sir" as a standalone false character.

## Current Issues (Priority Order)

### CRITICAL

1. **REVERT attempt 3 fix (commit 1418ccf) — it caused regressions without fixing the target issue** [REGRESSION]
   - Problem: The `_merge_lastname_aliases` exact_firstname guard introduced "American, sir" as a false character with narrator status, regressing 3 categories
   - Evidence: Attempt 2 had Uncle Bill correctly as narrator. Attempt 3 has "American, sir" as narrator.
   - Fix: `git revert 1418ccf` — return to attempt 2 codebase, then try a different approach
   - Location: `src/agents/characters.py` — `_merge_lastname_aliases()`

2. **Johnny (the son) MISSING — false-merged into father** [Identity Resolution / Completeness]
   - Problem: "John" (the son) merged into "John Donaldson" (the father) as an alias. They are different characters sharing a first name.
   - Evidence: Summary `characters_present` lists both "John" AND "John Donaldson (the father)" as separate entries. But final output has only "John Donaldson" with "John" as alias.
   - Root cause: `_merge_summary_name_fragments()` (Step 5.4.5 in characters.py) treats single-word "John" as fragment of multi-word "John Donaldson" and merges them.
   - Location: `src/agents/characters.py` — `_merge_summary_name_fragments()` (Step 5.4.5)
   - Fix approach: **Guard Step 5.4.5** — before merging a single-word fragment into a multi-word name, check if BOTH appear as separate entries in ANY summary's `characters_present` list. If the summarizer listed them separately, they are different characters and must NOT be merged. This is more targeted than the attempt 3 fix and won't affect other merges.

3. **"American, sir" is a false positive character — it's a dialogue phrase, not a person** [Completeness]
   - Problem: "American, sir" is an Italian soldier's response (like "Yes sir, American sir"), not a character name. It has 5 "mentions" which are all dialogue utterances of this phrase.
   - Evidence: The phrase appears in exchanges like soldiers asking/stating nationality. It has no physical description, no backstory, no agency.
   - Location: Pass 1 character extraction — the LLM incorrectly identifies this recurring phrase as a character name
   - Fix approach: After reverting attempt 3, this should resolve (attempt 2 didn't have this false positive). If it persists, add post-extraction filter for phrases containing commas that aren't valid character names.

4. **Summary factual errors: "Bill dying" and "grandfather" vs "father"** [Summaries]
   - Problem: Plot summary says "death of the narrator, Uncle Bill" and "narrator comforts the dying Uncle Bill." Bill does NOT die. The dying man is John Donaldson (the father). Also "John asks if God has forgiven his grandfather" — it's father, not grandfather.
   - Evidence: In the text, Bill narrates from home in New York. The dying scene is John Donaldson at an Italian dressing station. Johnny says "The man I was helping to die was my father."
   - Location: Summary generation — `src/pipeline/summarizer/`
   - Fix approach: This is hard because summaries generate before character extraction. Options:
     1. Post-character-extraction summary regeneration for `plot_summary` only
     2. Improved nested narrative prompting in summarizer
   - Priority: Address AFTER character issues are resolved

### HIGH

5. **All relationships generic ("associated", "uncle") — no family terms correct** [Profiles]
   - Problem: Bill → John Donaldson = "uncle" (should be "cousin"). "American, sir" → John Donaldson = "uncle" (wrong character entirely). No father-son relationship exists because Johnny is missing.
   - Evidence: Text says Bill and John "shared a room for a dozen years" at Yale (cousins). "The man I was helping to die was my father."
   - Location: `src/analyzer.py` → `_generate_character_profile()`
   - Fix approach: Will partially resolve when Johnny is restored. "Uncle" vs "cousin" confusion comes from Bill being called "Uncle Bill" by Johnny, but his relationship to JOHN DONALDSON is cousin, not uncle.

6. **Role assignments wrong: Ted Frith (5 mentions) = "main", John Donaldson (29 mentions) = "supporting"** [Identity Resolution]
   - Problem: Most-mentioned non-narrator character has role "supporting" while a 5-mention minor character has role "main."
   - Fix approach: Will likely resolve once Johnny is restored and "American, sir" is removed — mention counts will redistribute.

### MEDIUM

7. **John Donaldson's profile mixes father and son** [Profiles]
   - Problem: Profile describes "'charming boy' and 'beautiful youngster' in youth" (the father) AND "physical beauty later seen repeated in his son" — all under one merged entry.
   - Fix approach: Resolves if Johnny is restored as separate character.

8. **Margaret Donaldson missing** [Completeness]
   - Problem: John's wife and Johnny's mother, mentioned by name, not in output.
   - Impact: Minor — background character.

### LOW

9. **Null chapter title for single-section text** [Structure]
   - Impact: Very minor presentation issue.

## Fix Strategy for Attempt 4

**Step 1: REVERT** commit 1418ccf to restore attempt 2 codebase (where Bill was correctly narrator).

**Step 2: Targeted fix for Johnny merge** — Guard `_merge_summary_name_fragments()` (Step 5.4.5):
- Before merging single-word fragment "X" into multi-word name "X Y", check all summaries' `characters_present` lists
- If ANY summary lists BOTH "X" and "X Y" (or "X Y (qualifier)") as separate entries, BLOCK the merge
- This preserves the merge for normal cases (e.g., "Jim" → "Jim Dillingham Young") where the summarizer does NOT list them separately
- Only blocks when there's explicit evidence they're different characters

**Step 3: Re-analyze** and evaluate.

## Fix History
- Attempt 2: Fixed narrator detection to trust explicit "narrator, known as [Name]" identification
  - Modified: `src/pipeline/character_extraction_v2/narrator.py:NARRATOR_DETECTION_PROMPT`
  - Result: Narrator fix WORKED — Bill correctly identified ✓
- Attempt 3: Added exact_firstname guard to `_merge_lastname_aliases`
  - Modified: `src/agents/characters.py` — `_merge_lastname_aliases()`
  - Result: **REGRESSION** — "American, sir" appeared as false character, stole narrator. Johnny NOT fixed. REVERT NEEDED.

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 2 | Wrong narrator (Uncle Bill vs Johnny) | `src/pipeline/character_extraction_v2/narrator.py` | Fixed — Bill is now narrator ✓ |
<<<<<<< HEAD
| 2 | Johnny missing (false merge) | (not yet attempted) | Still broken |
| 3 | Johnny missing — `_merge_lastname_aliases` exact_firstname guard | `src/agents/characters.py` | **REGRESSION** — "American, sir" false character, narrator shifted. REVERT. |
=======
| 2 | Johnny missing (false merge) | (not yet attempted) | Still broken — Johnny merged into father |
| 2 | Summary errors (Bill dying) | (not yet attempted) | Still broken — summary not re-generated |

## Root Cause Analysis

**Primary blocker: Johnny false-merged into father (Issue #1)**

The pipeline's merge logic in `characters.py` sees "John" (single-word character = the son) as a name fragment of "John Donaldson" (multi-word character = the father) and merges them. This is a correct heuristic in MOST cases (e.g., "Jim" → "Jim Dillingham Young") but WRONG when father and son share the same first name.

The key signal that these are different characters is in `characters_present`: the summarizer listed BOTH "John" AND "John Donaldson (the father)" in the same section. If both appear as separate entries in the same summary, they must be separate characters. The merge logic should check this.

**Merge steps that could be responsible (check in order):**
1. `_merge_summary_name_fragments()` (Step 5.4.5) — most likely. Merges single-word fragments into multi-word canonical names from summary character lists.
2. `_merge_formal_name_aliases()` (Step 5.5a) — less likely but possible. Merges formal names into nicknames.
3. `_merge_lastname_aliases()` (Step 5.5) — possible. "John" could be treated as a component.

**Secondary blocker: Summary errors (Issue #2)**

Summaries are generated BEFORE character extraction (pipeline order: Structure → Summary → Characters). The summary LLM is confused by:
- Frame/nested narrative (Bill narrates, Johnny's war story is quoted dialogue)
- Same-name characters (father and son both "John Donaldson")
- The dying man's identity (father, not Bill)

The narrator fix improved character extraction but could NOT retroactively fix already-generated summaries. The `plot_summary` in the overview is derived from chapter summaries, so it inherits their errors.
>>>>>>> parent of 1418ccf (Fix: guard exact_firstname merge when summary lists names as separate characters)

## Configuration Notes
- Model config appropriate: qwen3.5:122b-a10b for characters/summaries/profiles, qwen3.5:35b-a3b for structure/pronunciation
- Zero LLM retries across all stages
- All 14 pronunciations have IPA
- Runtime: 10m 32s (36 LLM calls)

## Next Action
<<<<<<< HEAD
1. REVERT commit 1418ccf
2. Apply targeted fix to `_merge_summary_name_fragments()` (Step 5.4.5) — guard against merging when summary lists names separately
3. Re-analyze and evaluate
=======
Run PROMPT_fix.md to address Issue #1 (Johnny false-merged into father). The fix should:
1. Add a guard in `_merge_summary_name_fragments()` (and related merge functions) to prevent merging characters that appear as **separate entries** in the same summary's `characters_present` list
2. This is the highest-impact fix — restoring Johnny as a character should cascade improvements to profiles, relationships, and role assignments
3. Summary errors (Issue #2) may need a separate approach since summaries are generated before character extraction
>>>>>>> parent of 1418ccf (Fix: guard exact_firstname merge when summary lists names as separate characters)
