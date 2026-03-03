# Current Evaluation State

## Active Text
- **Name:** a_camping_trip
- **Attempt:** 3
- **Phase:** awaiting_analysis
- **baseline_score:** 7.80
- **Competitive Mode:** none

## Output Files
- HTML: ../output/a_camping_trip/report.html
- JSON: ../output/a_camping_trip/analysis.json

## Latest Scores
- Structure Detection: 8/10 ✓
- Character Extraction: 6/10 ✗ (FAILING — REGRESSION from 7)
  - Completeness: 7/10
  - Identity Resolution: 5/10 ← 3-way split of Milton Jennings is primary blocker (regression from 6)
  - Alias Grouping: 6/10
- Character Profiles: 7/10 ✗ (FAILING — REGRESSION from 8)
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 7/10 ✗ (FAILING — no net improvement)
- HTML Presentation: 9/10 ✓
- **Overall: 7.45/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold: Characters, Profiles, Pronunciation)
**REGRESSION ALERT:** Overall 7.45 is 0.35 below baseline 7.80 (exceeds -0.3 threshold)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 7.80 | - | Baseline. 3 categories failing: Characters (6.5), Profiles (7), Pronunciation (7) |
| 2 | 7.75 | -0.05 | 2 categories failing: Characters (7, ↑0.5), Pronunciation (7, =). Profiles fixed (7→8). Narrator flag fixed. Boat-keeper/storm alias fixed. |
| 3 | 7.45 | -0.35 | **REGRESSION.** 3 categories failing: Characters (6, ↓1), Profiles (7, ↓1), Pronunciation (7, =). Milton Jennings now split 3 ways (was 2 in att.2). "Jennings" falsely flagged narrator (was fixed in att.2). |

## What Changed Attempt 2 → 3

### Code Fixes Applied (commit 85a5c53)
1. Added "milt"→"milton" to NICKNAME_TO_FORMAL in characters.py
2. Added nickname-firstname merge check in `_merge_lastname_aliases`
3. Raised compound detector min component length 3→4 in cmu_proposer.py
4. Added "es" suffix to `_is_common_derivation` in cmu_proposer.py

### Pronunciation Improvements (Fix WORKED)
- ✅ "bowlders" now flagged with correct IPA /ˈboʊldərz/
- ✅ "gunwhale" now flagged (but IPA is WRONG — see issue #3 below)
- ✅ "wildernesses" false positive removed

### Character Regression (Fix FAILED — made things WORSE)
- ❌ **REGRESSION:** "Milton Jennings" (main_cast_1 in attempt 2) no longer exists as a character at all
- ❌ **REGRESSION:** Now split into THREE fragments: "Milton" (supporting_0, 23 mentions) + "Jennings" (supporting_1, 10 mentions) + "Milt" (supporting_3, 2 mentions)
- ❌ **REGRESSION:** "Jennings" falsely flagged as is_narrator=true (was fixed in attempt 2, now re-broken)
- ❌ **REGRESSION:** All Milton-related characters demoted from main_cast to supporting
- ❌ Lincoln's relationship list shows "Milton", "Milt", and "Jennings" as 3 separate people
- Note: Summary correctly says "Milton Jennings" — the summarizer knows it's one person, extraction doesn't

### Root Cause Analysis
The character regression is most likely **LLM non-determinism**, not a code bug:
- The code fix (NICKNAME_TO_FORMAL) only ADDS merge logic, cannot cause splits
- The LLM extraction this run produced "Milton" and "Jennings" as separate entities
- In attempt 2, the LLM had produced "Milton Jennings" as one entity
- The nickname merge couldn't fire because its target "Milton Jennings" never existed
- The gap in IDs (no main_cast_1) suggests a character was extracted to main_cast but then removed/demoted

## Current Issues (Priority Order)

### CRITICAL
1. **3-way false split: Milton (supporting_0) + Jennings (supporting_1) + Milt (supporting_3) are ALL "Milton Jennings"** [Identity Resolution]
   - Problem: The text's second most important character is fragmented across 3 entries totaling 35 mentions. In attempt 2 this was a 2-way split; now it's worse.
   - Evidence: The summary itself says "Milton Jennings" as one person. Line 29 "Hello, Milt" = nickname. "Mr. Jennings" / "Mrs. Jennings" are the PARENTS (different people), but bare "Jennings" in context refers to Milton's surname.
   - ID patterns: supporting_0, supporting_1, supporting_3 — all in supporting cast pipeline
   - The existing `_merge_lastname_aliases` and NICKNAME_TO_FORMAL logic failed because "Milton Jennings" was never produced as a single entity by the LLM this run.
   - **Needed fix:** A more robust post-extraction merge that can consolidate "FirstName" + "LastName" fragments when the summary references "FirstName LastName" as one character. Check summary `characters_present` for full names and merge matching first-name + last-name fragments.
   - Location: `src/agents/characters.py` — needs a new merge step that cross-references summary character lists

2. **"Jennings" falsely flagged as first-person narrator** [Identity Resolution / Profiles]
   - Problem: "A Camping Trip" is a third-person omniscient narrative. No character is the narrator. "Jennings" (supporting_1) has `is_narrator: true` — completely wrong.
   - Evidence: The text never uses "I" in a narrative voice attributed to any character.
   - This was FIXED in attempt 2 (Lincoln Stewart's narrator flag was removed). Now "Jennings" has the false flag.
   - Location: Narrator detection logic — may be attributing 3rd-person narration to a character

### HIGH
3. **Gunwhale IPA is WRONG — defeats the purpose of flagging it** [Pronunciation]
   - Problem: IPA given as /ˈɡʌn.weɪl/ (literally "gun-whale"). The correct pronunciation is /ˈɡʌn.əl/ ("gunnel"). This is the #1 reason narrators need this word flagged — to NOT read it as "gun-whale".
   - Note says: "The 'wh' is pronounced as a 'w' sound, and 'ale' rhymes with 'pail'" — this is wrong.
   - Location: LLM proposer generating IPA in `src/pipeline/pronunciation_guide/`
   - Fix: Could add gunwhale/gunwale to a special-case pronunciation map, or improve the LLM prompt to note that "gunwale" is a nautical term pronounced "gunnel"

4. **"lead" and "desert" homographs have null IPA** [Pronunciation]
   - Problem: Both entries have `ipa: null` while all other homographs (wind, bass, read, live, close, minute) have IPA.
   - Location: LLM proposer — inconsistent IPA generation for homographs
   - Fix: Ensure all homograph entries get IPA generated

5. **Missing parent characters: Mr. Stewart, Mr. Jennings, Mrs. Jennings** [Completeness]
   - Same as attempt 2, still missing
   - These are named, speaking characters but have very low mention counts
   - Lower priority than the Milton split for crossing 8.0

### MEDIUM
6. **"Stewart" as standalone alias for Lincoln Stewart** [Alias Grouping]
   - Problem: Lincoln is never called just "Stewart" — only "Lincoln Stewart" (full name) or "Lincoln". "Stewart" alone appears only in "Mr. Stewart" (his father).
   - Location: Programmatic surname-as-alias logic in V2 pipeline

7. **"Knapp" should be "Captain Knapp"** [Alias Grouping]
   - Same as attempt 2, still not fixed
   - Title stripping too aggressive for military/rank titles

### LOW
8. **Milton's profile duplicated across "Milton" and "Jennings" entries** [Profiles]
   - The "Jennings" entry's personality section literally says "Milton is depicted as..." — the profiler KNOWS they're the same person
   - This is a downstream symptom of the CRITICAL #1 split. Fixing #1 fixes this.

## Fix Priority for Crossing 8.0

**Given the regression, the FIRST action must be to revert commit 85a5c53 and re-analyze.** The pronunciation fix was correct but the LLM non-determinism produced a worse character extraction. After revert:

1. **Re-apply ONLY the pronunciation fixes** (cmu_proposer.py changes) — these demonstrably worked
2. **Add a summary-crossref merge step** in characters.py that reconciles extraction fragments against summary `characters_present` lists. When summary says "Milton Jennings" but extraction has separate "Milton" and "Jennings", merge them.
3. **Fix gunwhale IPA** — either hardcode or improve LLM prompt
4. Re-analyze

**The Milt→Milton NICKNAME_TO_FORMAL fix is still correct** but it needs the upstream merge to produce "Milton Jennings" first. Apply it AFTER the summary-crossref merge is in place.

## Fix History
- Attempt 1→2: External changes (commit 3cb3fb5) restored grounding threshold=3, length-adaptive alias context. Fixed narrator flag, removed boat-keeper character, improved profiles.
- Attempt 2→3: Added milt→milton to NICKNAME_TO_FORMAL, nickname-firstname merge in _merge_lastname_aliases, pronunciation compound detector fixes. **RESULT: Character regression (Milton Jennings split 3 ways), Pronunciation partially improved.**

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1→2 (external) | Grounding threshold, alias context | characters.py, main_cast.py | Partial fix: narrator and boat-keeper fixed, Milt split persists |
| 2→3 | Milt/Milton false split | characters.py | **REGRESSION**: Milton Jennings now split 3 ways (was 2). Likely LLM non-determinism, not code bug. |
| 2→3 | Missing pronunciation (gunwhale, bowlders) | cmu_proposer.py | **Fixed**: Both now flagged. But gunwhale IPA is wrong. |
| 2→3 | wildernesses false positive | cmu_proposer.py | **Fixed**: No longer flagged. |

## Configuration Audit
- Models: qwen3.5:35b-a3b (structure, pronunciation), qwen3.5:122b-a10b (characters, summaries, profiles) — appropriate
- think_mode: false for all agents ✓
- character_llm_chunk_chars: 5000 — appropriate for short text
- summary_chunk_words: 2500 — appropriate
- No LLM retries (0 across all stages) ✓
- No JSON parse failures ✓
- All profiling stages: high confidence dominant ✓

## Next Action
Re-run analysis (phase: awaiting_analysis).

## Fix History (Attempt 3→4)

### Changes Applied
1. **Reverted commit 85a5c53 characters.py changes** — removed the nickname merge that caused regression (needed "Milton Jennings" in main cast to work, but LLM never produced it this run)
2. **Re-applied cmu_proposer.py pronunciation fixes** (compound detector min 3→4, "es" suffix)
3. **Added Step 5.4.5 `_merge_summary_name_fragments`** in characters.py — cross-references summary `[Characters present: ...]` lists against single-word cast fragments; merges "Milton"+"Jennings" → "Milton Jennings" and promotes to main cast
4. **Re-added NICKNAME_TO_FORMAL "milt"→"milton"** + nickname check in `_merge_lastname_aliases` — after step 5.4.5 creates "Milton Jennings" in main cast, "Milt" merges via nickname lookup
5. **Added "lead"/"desert" to HOMOGRAPH_IPA_MAP** — fixes null IPA for these homographs
6. **Added KNOWN_IRREGULAR_IPA** with gunwale/gunwhale (IPA: /ˈɡʌn.əl/) — overrides LLM's incorrect "gun-whale" pronunciation

### Smoke Test: PASS
- Summary-crossref merged "Milton"+"Jennings" → "Milton Jennings" (33 mentions) in main cast
- gunwhale IPA = /ˈɡʌn.əl/ (correct); "lead"/"desert" now have IPA in HOMOGRAPH_IPA_MAP
- 332 tests pass
