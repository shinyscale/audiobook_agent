# Current Evaluation State

## Active Text
- **Name:** a_camping_trip
- **Attempt:** 4
- **Phase:** awaiting_analysis
- **baseline_score:** 7.80
- **Competitive Mode:** none

## Output Files
- HTML: ../output/a_camping_trip/report.html
- JSON: ../output/a_camping_trip/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 6.5/10 ✗ (FAILING)
  - Completeness: 7/10
  - Identity Resolution: 6/10 ← Milton/Milt split + false narrator are primary blockers
  - Alias Grouping: 6.5/10
- Character Profiles: 7/10 ✗ (FAILING)
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 7/10 ✗ (FAILING)
- HTML Presentation: 9/10 ✓
- **Overall: 7.8/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold: Characters 6.5, Profiles 7, Pronunciation 7)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 7.80 | - | Baseline. 3 categories failing: Characters (6.5), Profiles (7), Pronunciation (7) |
| 2 | 7.75 | -0.05 | 2 categories failing: Characters (7, ↑0.5), Pronunciation (7, =). Profiles fixed (7→8). Narrator flag fixed. Boat-keeper/storm alias fixed. |
| 3 | 7.45 | -0.35 | **REGRESSION.** 3 categories failing: Characters (6, ↓1), Profiles (7, ↓1), Pronunciation (7, =). Milton Jennings now split 3 ways (was 2 in att.2). |
| 4 | 7.80 | 0.00 | Recovery from regression. Parents (Mr./Mrs. Jennings) newly extracted ✓. Milton still split 2 ways but "Jennings" standalone eliminated. Pronunciation fixes in code but NOT taking effect in output. |

## What Changed Attempt 3 → 4

### Code Fixes Applied (commit edc8dad)
1. Reverted characters.py regression, re-applied cmu_proposer.py pronunciation fixes
2. Added Step 5.4.5 `_merge_summary_name_fragments` — cross-references summary character lists
3. Re-added NICKNAME_TO_FORMAL "milt"→"milton" + nickname merge
4. Added "lead"/"desert" to HOMOGRAPH_IPA_MAP in enricher.py
5. Added gunwale/gunwhale to KNOWN_IRREGULAR_IPA in enricher.py

### What Improved
- ✅ Parents extracted: Mr. Jennings (5 mentions, main_cast_5) and Mrs. Jennings (4 mentions, main_cast_6) — NEW characters not in any previous attempt
- ✅ "Jennings" standalone fragment eliminated (was supporting_1 in attempt 3)
- ✅ Milton split reduced from 3-way (attempt 3) back to 2-way
- ✅ Lincoln and Milton profiles now have personality, voice guidance, speech patterns, example quotes
- ✅ Recovery from attempt 3's regression (7.45 → 7.80)

### What Did NOT Work
- ❌ `_merge_summary_name_fragments` DID NOT FIRE: summary has "Milton Jennings" in characters_present, cast has "Milton" (supporting_0, 23 mentions) — but NO standalone "Jennings" character exists (only "Mr. Jennings" / "Mrs. Jennings"). Algorithm requires ALL words to have matching single-word fragments. With "Jennings" only existing in multi-word names, the merge can't find the second fragment.
- ❌ KNOWN_IRREGULAR_IPA did not override gunwhale: output IPA is /ˈɡʌnˌhoʊl/ (wrong), expected /ˈɡʌn.əl/. Code has the override at enricher.py:203,324 but it's not taking effect.
- ❌ HOMOGRAPH_IPA_MAP did not populate lead/desert: both still have null IPA despite entries at enricher.py:70-71. The map is checked at line 372 but output shows null.
- ❌ Mr. Jennings falsely flagged is_narrator=true (3rd-person omniscient text — NO character is the narrator)
- ❌ "Milt" (supporting_2, 2 mentions) still separate from "Milton" (supporting_0, 23 mentions)

### Root Cause Analysis
1. **Summary-crossref merge failure**: LLM non-determinism. This run produced "Mr. Jennings" and "Mrs. Jennings" (correct parent characters) instead of a bare "Jennings" entry. The merge algorithm was designed for the attempt-3 scenario (bare "Jennings" fragment) but this run's different extraction broke the assumption.
2. **Pronunciation overrides not taking effect**: The code changes ARE in enricher.py but the output doesn't reflect them. Possible causes: (a) different code path than enrich_batch/enrich_single, (b) override applied but then overwritten by LLM result, (c) the pronunciation pipeline doesn't call the enricher for these specific entries. **Fix phase MUST debug this — add logging or trace the code path.**
3. **False narrator on Mr. Jennings**: The narrator detection logic may be misattributing 3rd-person narration to a character with low mentions. This was fixed for "Jennings" in attempt 2 but re-appears on a different character.

## Current Issues (Priority Order)

### CRITICAL
1. **Milton/Milt false split — summary-crossref merge not firing** [Identity Resolution]
   - Problem: "Milton" (supporting_0, 23 mentions) and "Milt" (supporting_2, 2 mentions) are the same person ("Milton Jennings"). Milton is the 2nd most important character (25 combined mentions) but is stuck in supporting cast with incomplete name.
   - Evidence: Summary says "Milton Jennings" in characters_present. "Hello, Milt" in text = nickname. Profiler for "Milt" entry even says "Milt (Milton Jennings)".
   - Root cause: `_merge_summary_name_fragments` requires ALL words of summary name to have matching single-word fragments. "Jennings" doesn't exist as a single-word character (only "Mr. Jennings" / "Mrs. Jennings"), so merge doesn't fire.
   - Location: `src/agents/characters.py` — `_merge_summary_name_fragments` (Step 5.4.5)
   - Fix: Make the algorithm more flexible. If ONE word of a multi-word summary name matches a single-word fragment with ≥10 mentions, rename that character to the full summary name and promote to main cast. Then the existing NICKNAME_TO_FORMAL merge can handle "Milt" → "Milton".
   - **Alternative approach**: After Step 5.4.5, add a simpler check: if a single-word supporting character's name appears as a word in `characters_present` multi-word names AND has ≥10 mentions, rename it to the full summary name.

### HIGH
2. **Mr. Jennings falsely flagged as first-person narrator** [Identity Resolution / Profiles]
   - Problem: "A Camping Trip" is third-person omniscient. No character is the narrator. `is_narrator: true` on Mr. Jennings (5 mentions) is completely wrong.
   - Evidence: Text uses "he/they/the boys" not "I" for narrative voice.
   - This was fixed for "Jennings" in attempt 2 but now re-appears on "Mr. Jennings".
   - Location: Narrator detection logic — likely in character extraction or post-processing
   - Fix: The narrator detection should have higher confidence threshold for 3rd-person texts. If text has no 1st-person narrative voice, no character should be flagged as narrator.

3. **Pronunciation overrides (KNOWN_IRREGULAR_IPA + HOMOGRAPH_IPA_MAP) not taking effect** [Pronunciation]
   - Problem: gunwhale IPA = /ˈɡʌnˌhoʊl/ (WRONG, should be /ˈɡʌn.əl/). "lead" and "desert" have null IPA. Code has the correct overrides but they're not appearing in output.
   - Evidence: enricher.py has KNOWN_IRREGULAR_IPA at line 78 (gunwale/gunwhale) and HOMOGRAPH_IPA_MAP at line 70 (lead/desert). Checked at lines 203, 324, 372. Output doesn't reflect them.
   - Location: `src/pipeline/pronunciation_guide/enricher.py` — the override code paths aren't being reached
   - Fix: **Debug this first.** Add temporary logging to verify whether `enrich_batch()`/`enrich_single()` is called for these words. Possible causes: (a) pronunciation entries created AFTER enrichment, (b) homograph entries use a different code path that bypasses enrichment, (c) entries overwritten after enrichment. The fix may be as simple as ensuring the override is checked at the right stage.

### MEDIUM
4. **"Stewart" as standalone alias for Lincoln Stewart** [Alias Grouping]
   - Problem: Lincoln Stewart has alias "Stewart" — but in the text, "Stewart" alone never refers to Lincoln. "Mr. Stewart" is his father. Bare "Stewart" could cause narrator confusion.
   - Location: V2 pipeline surname-as-alias logic
   - Fix: Lower priority than critical items. Only strip surname alias if no other character uses that surname with a title.

5. **"Knapp" should be "Captain Knapp"** [Alias Grouping]
   - Problem: Character canonical name is "Knapp" but text and profile both say "Captain Knapp" / "old soldier". Title stripping too aggressive for military/rank titles.
   - Location: Title stripping logic in V2 pipeline
   - Fix: Military/rank titles (Captain, Sergeant, etc.) should be preserved in canonical names.

6. **Mrs. Jennings → Milton relationship is "associated" not "mother/son"** [Profiles]
   - Problem: Milton's source evidence says "Milton is the son of Mrs. Jennings" but relationship is "associated".
   - Evidence: The profiler identified the relationship in evidence but the relationship extractor didn't capture it correctly.
   - Location: Relationship extraction in post-corrections or profiler

### LOW
7. **Milton has no physical description — it's on the "Milt" entry** [Profiles]
   - Problem: "Milt" has "perfect horseman, easy rider" description that belongs to Milton.
   - Downstream symptom of CRITICAL #1. Fixing the split fixes this.

8. **Lincoln's relationship list shows both "Milton" and "Milt" as separate friends** [Profiles]
   - Downstream symptom of CRITICAL #1. Fixing the split fixes this.

## Fix Priority for Crossing 8.0

The three failing categories are Characters (6.5), Profiles (7), and Pronunciation (7). The minimum needed:

1. **Fix summary-crossref merge** (CRITICAL #1) → Characters jumps to ~8 (Milton merged, promoted to main cast, correct name). Profiles automatically improves to ~8 (merged profile, no duplicate relationships).
2. **Fix narrator detection** (HIGH #2) → Characters +0.5, Profiles +0.5
3. **Debug pronunciation overrides** (HIGH #3) → Pronunciation jumps to ~8 (gunwhale correct IPA, lead/desert get IPA)

All three must succeed for a pass. #1 is the highest-leverage fix.

## Fix History
- Attempt 1→2: External changes (commit 3cb3fb5) restored grounding threshold=3, length-adaptive alias context. Fixed narrator flag, removed boat-keeper character, improved profiles.
- Attempt 2→3: Added milt→milton to NICKNAME_TO_FORMAL, nickname-firstname merge in _merge_lastname_aliases, pronunciation compound detector fixes. **RESULT: Character regression (Milton Jennings split 3 ways).**
- Attempt 3→4: Reverted characters.py regression, re-applied pronunciation fixes, added summary-crossref merge step, added lead/desert to HOMOGRAPH_IPA_MAP, added gunwale/gunwhale to KNOWN_IRREGULAR_IPA. **RESULT: Partial recovery. Parents extracted, 3-way split reduced to 2-way. But summary-crossref merge didn't fire (LLM produced different character set). Pronunciation overrides not taking effect.**
- Attempt 4→5: (1) Extended `_merge_summary_name_fragments` with partial match (one strong fragment ≥10 mentions); fixed early-return bug; (2) Added POV guard to STEP 5.8.6 to prevent false narrator in 3rd-person texts; (3) Fixed `enrich_batch()` merge order so KNOWN_IRREGULAR_IPA always overrides LLM results. 332 tests pass.

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1→2 (external) | Grounding threshold, alias context | characters.py, main_cast.py | Partial fix: narrator and boat-keeper fixed, Milt split persists |
| 2→3 | Milt/Milton false split | characters.py | **REGRESSION**: Milton Jennings split 3 ways. LLM non-determinism. |
| 2→3 | Missing pronunciation (gunwhale, bowlders) | cmu_proposer.py | **Fixed**: Both flagged. But gunwhale IPA wrong. |
| 2→3 | wildernesses false positive | cmu_proposer.py | **Fixed**: No longer flagged. |
| 3→4 | Summary-crossref merge | characters.py | **No effect**: Merge step added but didn't fire (no bare "Jennings" fragment) |
| 3→4 | gunwhale IPA | enricher.py (KNOWN_IRREGULAR_IPA) | **No effect**: Override in code but output still wrong IPA |
| 3→4 | lead/desert null IPA | enricher.py (HOMOGRAPH_IPA_MAP) | **No effect**: Override in code but output still null |
| 3→4 | NICKNAME_TO_FORMAL "milt" | characters.py | **No effect**: Needs upstream merge to fire |
| 4→5 | Summary-crossref partial match + early-return bug | characters.py | **Applied**: Partial match fires for "Milton"(23 mentions); early-return fixed to allow promotion |
| 4→5 | STEP 5.8.6 false narrator guard | characters.py | **Applied**: `narrator_info.pov not in ("third-person", "omniscient")` guard added |
| 4→5 | enrich_batch merge order | enricher.py | **Applied**: Static overrides now win over LLM results |

**PATTERN: enricher.py modified twice without effect.** The fix phase MUST trace the pronunciation code path to verify the overrides are actually reached at runtime.

## Configuration Audit
- Models: qwen3.5:35b-a3b (structure, pronunciation), qwen3.5:122b-a10b (characters, summaries, profiles) — appropriate
- think_mode: false for all agents ✓
- character_llm_chunk_chars: 5000 — appropriate for short text
- summary_chunk_words: 2500 — appropriate
- No LLM retries (0 across all stages) ✓
- No JSON parse failures ✓

## Next Action
Run PROMPT_analyze.md. Three fixes applied (attempt 4→5):
1. `_merge_summary_name_fragments` extended with partial match — if exactly ONE word of a multi-word summary name has a single-word character with ≥10 mentions, rename it to the full summary name and promote to main cast. Also fixed early return bug (returned before promotion when no subordinates). Smoke test: "Milton" (23 mentions) → "Milton Jennings", promoted to main cast, "Milt" stays in supporting for NICKNAME_TO_FORMAL merge.
2. STEP 5.8.6 false narrator guard — added `narrator_info.pov not in ("third-person", "omniscient")` to prevent heuristic firing in 3rd-person texts.
3. `enrich_batch()` merge order fixed — `llm_enrichments.update(enrichments)` now ensures static KNOWN_IRREGULAR_IPA overrides win over LLM (previously LLM could overwrite static results if it returned extra words).
