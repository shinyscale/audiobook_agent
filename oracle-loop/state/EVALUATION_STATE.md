# Current Evaluation State

## Active Text
- **Name:** a_camping_trip
- **Attempt:** 2
- **Phase:** awaiting_analysis
- **baseline_score:** 7.80
- **Competitive Mode:** none

## Output Files
- HTML: ../output/a_camping_trip/report.html
- JSON: ../output/a_camping_trip/analysis.json

## Latest Scores
- Structure Detection: 8/10 ✓
- Character Extraction: 7/10 ✗ (FAILING)
  - Completeness: 7.5/10
  - Identity Resolution: 6/10 ← false split is primary blocker
  - Alias Grouping: 7/10
- Character Profiles: 8/10 ✓
- Chapter Summaries: 8/10 ✓
- Pronunciation Guide: 7/10 ✗ (FAILING)
- HTML Presentation: 9/10 ✓
- **Overall: 7.75/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold: Characters, Pronunciation)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 7.80 | - | Baseline. 3 categories failing: Characters (6.5), Profiles (7), Pronunciation (7) |
| 2 | 7.75 | -0.05 | 2 categories failing: Characters (7, ↑0.5), Pronunciation (7, =). Profiles fixed (7→8). Narrator flag fixed. Boat-keeper/storm alias fixed. |

## Changes from Attempt 1 → 2
- ✅ FIXED: "the boat-keeper" with bogus "the storm" alias removed entirely
- ✅ FIXED: Lincoln Stewart no longer falsely flagged as narrator (is_narrator: false)
- ✅ FIXED: Profiles now have excellent voice guidance with dialect notes, example quotes
- ✅ FIXED: Fabricated boat-keeper ↔ Knapp relationship gone (boat-keeper removed)
- ❌ STILL BROKEN: "Milt" (supporting_2) still separate from "Milton Jennings" (main_cast_1)
- ❌ STILL BROKEN: Missing parent characters (Mr. Stewart, Mr./Mrs. Jennings)
- ❌ STILL BROKEN: Missing archaic/nautical pronunciation entries
- ❌ STILL BROKEN: "wildernesses" false positive
- 🔶 NEW: Duplicate "Milton" in Milton Jennings' alias list
- 🔶 NEW: Lincoln's relationship list includes "Milt" as separate from "Milton Jennings"

## Current Issues (Priority Order)

### CRITICAL
1. **False split: "Milt" (supporting_2) is separate from "Milton Jennings" (main_cast_1)** [Identity Resolution]
   - Problem: "Milt" is listed as a supporting character with 2 mentions, but is clearly a nickname for Milton Jennings. The supporting character's own profile description says "Milt (Milton Jennings) is Lincoln Stewart's friend" — the LLM KNOWS they're the same person, but the pipeline didn't merge them.
   - Text evidence: line 29 "Hello, Milt," Lincoln returned" — Lincoln addresses Milton as "Milt" in dialogue. Line 54 "if you don't mind, Milt" — same pattern.
   - Consequence: Lincoln Stewart's relationship list includes BOTH "Milton Jennings (close friend)" and "Milt (close friend)" — listing the same person twice.
   - ID patterns: main_cast_1 (Milton Jennings) vs supporting_2 (Milt) — cross-pipeline merge needed.
   - Location: `src/agents/characters.py` — NICKNAME_TO_FORMAL dict or `_merge_formal_name_aliases()` (Step 5.5a). Also check `src/pipeline/character_extraction_v2/main_cast.py`.
   - Fix: Add "milt"→"milton" to NICKNAME_TO_FORMAL dictionary. "Milt" is a standard truncation of "Milton" (first syllable only), similar to how "Jim" maps to "James". Step 5.5a should then merge supporting "Milt" into main_cast "Milton Jennings" since it's a nickname match with large mention asymmetry (32 vs 2).

### HIGH
2. **Missing pronunciation entries for archaic/nautical terms** [Pronunciation]
   - Problem: Four words important for narrator prep are completely absent:
     - "bowlders" (lines 234, 293) — archaic spelling of "boulders"; narrator MUST know to pronounce it as "boulders"
     - "popple" (line 20) — dialectal/regional word for "poplar tree"
     - "luff" (line 454) — nautical term with footnote [111-1] in text indicating it needs explanation
     - "gunwhale" (line 409) — commonly mispronounced; correct: "GUN-ul" not "gun-whale"
   - Location: `src/pipeline/pronunciation/` — CMU proposer + LLM proposer
   - Fix: These words are genuinely unusual and should NOT be in the CMU dictionary. Investigate why CMU proposer missed them — possibly filtered by confidence threshold or character-level patterns. These would push Pronunciation from 7 → 8.

3. **Missing characters: Mr. Stewart, Mr. Jennings, Mrs. Jennings** [Completeness]
   - Problem: Three named, speaking characters entirely absent from output.
   - Evidence:
     - Mr. Stewart (Lincoln's father): line 69 "Mr. Stewart had consented" — named, referenced in Ch1 summary by proper name
     - Mr. Jennings (Milton's father): lines 136-137 "said Mr. Jennings" — named, has dialogue
     - Mrs. Jennings (Milton's mother): lines 117, 120-126, 165-168, 525-526 — named, multiple dialogue lines
   - Note: Ch1 summary correctly lists "Mr. Stewart" in characters_present, but he doesn't appear in the character list. Mr./Mrs. Jennings aren't even in chapter summaries' characters_present.
   - Location: Summarizer prompt (not capturing Mr./Mrs. Jennings by proper name) + F6 reconciliation thresholds
   - Fix: These are 1-2 mention characters but have dialogue. For short texts, the extraction threshold may be too aggressive. However, these are lower priority than #1 and #2 for crossing the 8.0 threshold.

### MEDIUM
4. **Duplicate "Milton" in Milton Jennings' alias list** [Alias Grouping]
   - Problem: `aliases: ["Milton", "Milton", "Jennings"]` — "Milton" appears twice.
   - Location: Alias deduplication in character extraction pipeline
   - Fix: Simple dedup of alias list. Low effort, minor quality issue.

5. **"Knapp" should be "Captain Knapp"** [Alias Grouping]
   - Problem: Character listed as "Knapp" (supporting_3) but always referred to as "Captain Knapp" in text (lines 45, 103).
   - Location: Title-stripping logic — too aggressive for military/rank titles.
   - Fix: Preserve "Captain" in canonical name for rank titles.

6. **"Stewart" as standalone alias for Lincoln Stewart** [Alias Grouping]
   - Problem: Lincoln is never called just "Stewart" in text. "Stewart" only appears in "Mr. Stewart" (his father) and "Lincoln Stewart" (full name).
   - Location: Programmatic surname-as-alias logic in V2 pipeline
   - Fix: Surname-as-alias should check if another character uses that surname with a title.

### LOW
7. **"wildernesses" flagged as pronunciation entry** [Pronunciation]
   - Problem: Standard English word, false positive.
   - Fix: Add to COMMON_WORDS_WHITELIST in `src/pipeline/pronunciation/cmu_proposer.py`.

8. **Missing IPA for "lead" and "desert"** [Pronunciation]
   - Problem: Two homograph entries have `ipa: null` — they should have IPA like the other homographs.
   - Fix: Ensure LLM proposer generates IPA for all homograph entries.

## Fix Priority for Crossing 8.0

**Characters (7 → 8):** Fix CRITICAL #1 (Milt/Milton merge). This alone could push Identity Resolution from 6 → 8 and overall Characters from 7 → 8. The missing parents (HIGH #3) are important but won't block the 8.0 threshold by themselves.

**Pronunciation (7 → 8):** Fix HIGH #2 (add 4 missing archaic/nautical terms). Adding bowlders, popple, luff, gunwhale would push coverage from 7 → 8. Remove "wildernesses" (LOW #7) while at it.

**Minimum fixes needed to pass: #1 and #2.**

## Fix History
- Attempt 1→2: External changes (commit 3cb3fb5) restored grounding threshold=3, length-adaptive alias context. Fixed narrator flag, removed boat-keeper character, improved profiles.

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1→2 (external) | Grounding threshold, alias context | characters.py, main_cast.py | Partial fix: narrator and boat-keeper fixed, Milt split persists |
| 2→3 | Milt/Milton false split (Identity Resolution) | characters.py | Added "milt"→"milton" to NICKNAME_TO_FORMAL + nickname-firstname merge step |
| 2→3 | Missing pronunciation entries (gunwhale, bowlders) | cmu_proposer.py | Raised compound detector min component length 3→4; require base-after-strip-s ≥ 4 chars |
| 2→3 | wildernesses false positive | cmu_proposer.py | Added "es" to _is_common_derivation suffix list |

## External Changes Applied
Commit `3cb3fb5` was applied outside the oracle loop after attempt 1 evaluation:
- Restored `min_grounding_mentions: 1 → 3` (baseline value that passed 11 prior texts)
- Made alias context length-adaptive: short texts (≤5 chapters) now use ALL summaries as context instead of a sample
- Cap reduced from 10,000 to 6,000 chars
- Files changed: `src/agents/characters.py`, `src/pipeline/character_extraction_v2/main_cast.py`

## Configuration Audit
- Models: qwen3.5:35b-a3b (structure, pronunciation), qwen3.5:122b-a10b (characters, summaries, profiles) — appropriate
- think_mode: false for all agents ✓
- character_llm_chunk_chars: 5000 — appropriate for short text
- summary_chunk_words: 2500 — appropriate
- No LLM retries (0 across all stages) ✓
- No JSON parse failures ✓
- All profiling stages: high confidence dominant ✓

## Next Action
Re-run analysis to verify fixes

## Fix History (Attempt 2 → 3)
### CRITICAL #1: Milt/Milton false split
- **Root cause:** `characters.py:_merge_lastname_aliases()` only checked exact first-name matches, not nickname→formal-name matches. "Milt" (supporting, 2 mentions) couldn't be merged into "Milton Jennings" (main cast, 32 mentions).
- **Fix:**
  1. Added `"milt": "milton"` to `NICKNAME_TO_FORMAL` dict in `characters.py:72`
  2. Added nickname-firstname check in `_merge_lastname_aliases` (after exact_firstname block): when a single-word supporting char's name is a NICKNAME and the formal name matches the FIRST WORD of a multi-word main cast char, it's merged.
  3. Added mention count guard: merge only fires when main has ≥ 4x more mentions than supporting (mirrors Step 5.5a safeguard).
- **Smoke test PASS:** "Milt" correctly merged as alias of "Milton Jennings" with [Milton, Jennings, Milt] aliases. Supporting cast "Milt" removed. Mention count guard prevents wrong merges when ratio < 4x.
- **Modified:** `src/agents/characters.py`

### HIGH #2: Missing pronunciation entries (bowlders, gunwhale)
- **Root cause:** `cmu_proposer.py:_is_closed_compound()` was too aggressive:
  - "gunwhale" → falsely detected as "gun"(3) + "whale"(5) compound (min component was 3 chars)
  - "bowlders" → falsely detected as "bowl"(4) + "ders" where "ders"[:-1]="der"(3-char CMU word) passes the plural-strip check
- **Fix 1:** Raised minimum component length from 3 → 4 chars. Short CMU entries (abbreviations, foreign articles like "der") can no longer anchor compound splits. Fixes "gunwhale" (gun=3 < 4 → skipped).
- **Fix 2:** Added requirement that base-after-strip-s must be ≥ 4 chars. Fixes "bowlders" where "ders"→"der"(3 chars) is blocked.
- **Fix 3:** Added "es" to suffix list in `_is_common_derivation`. "wildernesses"→"wilderness" (in CMU) is now correctly identified as a standard English derivation, removing the false positive.
- **Smoke test PASS:** bowlders=FLAGGED=True, gunwhale=FLAGGED=True, wildernesses=FLAGGED=False(derivation), firelight=compound=True(correctly not flagged).
- **Modified:** `src/pipeline/pronunciation_guide/proposers/cmu_proposer.py`
- **Note:** "luff" and "popple" are IN the CMU dictionary, so they won't be caught by CMU proposer. They'd need an LLM proposer. Not addressed in this attempt.
