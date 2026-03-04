# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 8
- **Phase:** awaiting_fix
- **baseline_score:** 6.55
- **Competitive Mode:** none

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 6.5/10 ✗ (FAILING)
  - Completeness: 7/10
  - Identity Resolution: 7/10 ← father/son separated ✓ but cross-character aliases undermine it
  - Alias Grouping: 5/10 ← 3 wrong aliases on the son, father has zero aliases
- Character Profiles: 7.5/10 ✗ (FAILING)
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 8.5/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 7.85/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold)

## What Attempt 8 Changed vs Attempt 7

**Major improvements:**
- Father/son SPLIT WORKING ✓ — `John Donaldson (the son)` (76 mentions) and `John Donaldson` (father, 9 mentions) are now separate characters
- Plot summary NO LONGER FABRICATES false twist ✓ — correctly identifies the dying man as the boy's estranged father, NOT Uncle Bill as the biological father
- Chapter summary correctly attributes embedded narration ✓ — "John discovers that a dying stretcher-bearer... is actually his estranged father" (correctly attributed to the son, not the narrator)
- Uncle Bill's profile clean ✓ — no contamination from boy's war experience
- Narrator correct ✓ — Uncle Bill is narrator, no false secondary narrators
- Role assignment improved ✓ — John Donaldson (son) is now "protagonist" (was "supporting" in attempt 7)
- Margaret Donaldson mentioned in chapter summary ✓

**Still broken:**
- **Cross-character aliases on the son**: `John Donaldson (the son)` has aliases "John Donaldson (the father)", "the father", "the man" — these belong to the FATHER character, not the son
- **Father has ZERO aliases**: `John Donaldson` (the father, supporting_0) has no aliases at all. He should have descriptors like "the stretcher-bearer", "the volunteer", "the man", "the father"
- **Mention count imbalance**: Son has 76 mentions, father has only 9 — suggests some father mentions were counted under the son
- **Relationships still generic**: Bill→both Johns = "associated" (should be "guardian/uncle" for son, "friend/classmate" for father)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.55 | 0 | Baseline. Narrator misidentification cascades into profiles + summaries |
| 2 | 6.6 | +0.05 | Narrator fix worked (Bill=narrator ✓, Bill profile correct ✓). But Johnny still missing, summary still wrong. |
| 3 | 6.0 | -0.55 | **REGRESSION.** "American, sir" false character stole narrator from Uncle Bill. Johnny still missing. |
| 4 | 6.4 | -0.15 | Co-present guard fixed "American, sir" ✓, but narrator REGRESSED (Johnny instead of Bill). Johnny/John's Son false split. |
| 5 | 6.7 | +0.15 | Plot summary improved (correctly names Uncle Bill). But narrator metadata STILL wrong. Step 5.4.6 merged "the boy" into father. |
| 6 | 7.0 | +0.45 | Uncle Bill narrator ✓, merge direction fixed ✓. But John Donaldson false secondary narrator → profile catastrophe. |
| 7 | 6.9 | +0.35 | Narrator guard worked ✓ (John Donaldson not narrator). But boy disappeared (false merge), plot summary fabricates false twist. |
| 8 | 7.85 | +1.30 | Father/son split ✓, plot summary fixed ✓, summaries fixed ✓, profiles much improved ✓. Remaining: cross-character aliases, generic relationships. |

## Current Issues (Priority Order)

### CRITICAL

1. **Cross-character alias contamination: "the father" aliases on son character** [Alias Grouping + Identity Resolution]
   - Problem: `John Donaldson (the son)` has aliases `["John", "the boy", "orphan", "ambulance driver", "John Donaldson (the father)", "the father", "the man"]`. The last three belong to the FATHER character, not the son.
   - Evidence: "John Donaldson (the father)" is literally the disambiguation form of the OTHER character entry. "the father" and "the man" are descriptors used in the text for the dying stretcher-bearer (the father), not the boy.
   - Impact: A narrator reading this alias list would believe the son IS the father — undermining the entire character separation.
   - Root cause: The LLM in Pass 2 alias resolution likely proposed "the father" and "the man" as aliases of the main-cast "John Donaldson (the son)" because the text uses these descriptors near mentions of "John Donaldson". The verify_aliases Rule 3 (cross-character alias check) may not check across main_cast/supporting_cast boundaries, or the father's canonical name "John Donaldson" doesn't contain "the father" so the check misses it.
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` — verify_aliases(), or `src/agents/characters.py` — post-merge alias dedup
   - Fix approach: Two options:
     - (a) In verify_aliases or a post-merge step, block any alias of character A that contains the disambiguating suffix of character B (e.g., if "John Donaldson (the son)" has alias "the father" and another character is "John Donaldson" with role-descriptors referencing fatherhood, block it)
     - (b) Simpler: after main_cast + supporting_cast are merged, run a cross-character alias dedup that removes from character A any alias that is a substring of character B's canonical_name or that matches character B's role/descriptor
     - (c) Simplest: if another character's canonical_name contains the same base name (e.g., both "John Donaldson"), block descriptor-only aliases ("the father", "the man") from being assigned to either — they're ambiguous

### HIGH

2. **Father character has ZERO aliases** [Alias Grouping]
   - Problem: `John Donaldson` (supporting_0, 9 mentions) has no aliases at all. In the text he is referred to as "the volunteer", "the stretcher-bearer", "the man", "the dark-skinned volunteer", "the father".
   - Evidence: The father appears in the war narrative under multiple descriptors before his identity is revealed.
   - Impact: A narrator wouldn't know that these text references point to this character.
   - Location: Supporting cast alias resolution — `src/pipeline/character_extraction_v2/` or F6 reconciliation
   - Fix approach: Either the LLM needs to propose these aliases for the supporting character, or the aliases incorrectly assigned to the son (issue #1) should be reassigned to the father.

3. **Relationships still all generic ("associated")** [Profiles]
   - Problem: Uncle Bill's relationships to both Johns are "associated". Should be:
     - Bill → son: "guardian" or "uncle figure"
     - Bill → father: "friend" or "former classmate"
     - Son → Bill: "nephew" or "ward"
   - Evidence: The text explicitly establishes Bill as the boy's guardian ("take in his orphaned nephew") and Bill and John Sr. as friends from Yale ("shared a room and life with for twelve years after both graduated from Yale").
   - Location: `src/pipeline/profiling/` or `_generate_character_profile()` in `src/analyzer.py`
   - Fix approach: The profiler prompt may need stronger guidance to extract specific relationship types rather than defaulting to "associated". This is a prompt improvement, not a logic fix.
   - Note: Fixing this alone could push Profiles from 7.5 → 8+

### MEDIUM

4. **Mention count imbalance: son 76, father 9** [Identity Resolution]
   - Problem: The son has 76 mentions in a ~5000-word story, which seems inflated. The father appears throughout the war narrative and likely has more than 9 mentions. Some father mentions may be counted under the son.
   - Impact: Low — mention counts are metadata, not narrator-facing. But it indicates imperfect identity resolution at the mention-counting level.
   - Fix: This would likely self-correct if the alias assignment (issue #1) is fixed, since mentions are counted per alias.

5. **Margaret Donaldson absent from character list** [Completeness]
   - Problem: Mentioned by name in the chapter 1 summary ("John's widow, Margaret Donaldson") but not in the character list. The evaluation state from the analyze phase noted "Margaret Donaldson added via F6b ✓" but she's not in the final output.
   - Impact: Very minor — she appears in one sentence and dies before the main narrative.
   - Fix: Low priority. May have been filtered by mention count threshold.

### LOW

6. **Missing nicknames: "Johnny" and "Teddy"** [Alias Grouping]
   - Problem: The boy is called "Johnny" in the text, Ted Frith is called "Teddy". Neither alias appears.
   - Fix: NICKNAME_TO_FORMAL dict additions or LLM prompt improvement.

## Fix Strategy for Attempt 9

**ROOT CAUSE**: The cross-character alias contamination (issue #1) is the single highest-leverage fix. It affects both Character Extraction and Character Profiles scores.

**RECOMMENDED APPROACH — Fix alias assignment:**

1. **Fix cross-character aliases** (CRITICAL): After main_cast and supporting_cast are merged, add a validation step that removes aliases from character A that match or are substrings of character B's canonical name when both share the same base name. Specifically: if `John Donaldson (the son)` and `John Donaldson` both exist, any alias on the son that contains "the father" or matches the father's descriptors should be blocked.

2. **Fix relationship labels** (HIGH): In the profiler prompt, replace generic "associated" with specific relationship types by providing stronger guidance. The text explicitly uses "uncle", "guardian", "friend", "classmate" — these should be extractable.

3. **Do NOT touch** (working correctly):
   - narrator.py (all fixes stable across attempts 6-8)
   - characters.py Step 5.4.5 (co-present guard)
   - characters.py Step 5.4.6 (merge direction)
   - summarizer.py (attempt 8 nested narration fix working)

## Fix History
- Attempt 2: Fixed narrator detection to trust explicit "narrator, known as [Name]" identification
  - Modified: `src/pipeline/character_extraction_v2/narrator.py`
  - Result: Fixed — Bill is now narrator ✓
- Attempt 3: Added exact_firstname guard to `_merge_lastname_aliases`
  - Modified: `src/agents/characters.py` — `_merge_lastname_aliases()`
  - Result: **REGRESSION** — "American, sir" false character, narrator shifted. REVERTED.
- Attempt 4: Reverted attempt 3, then applied co-present guard to `_merge_summary_name_fragments()` (Step 5.4.5)
  - Modified: `src/agents/characters.py` — `_merge_summary_name_fragments()`
  - Result: "American, sir" gone ✓, narrator regressed ✗, Johnny/John's Son false split ✗
- Attempt 5:
  1. Improved narrator prompt: added frame-narrative clarification
     - Modified: `src/pipeline/character_extraction_v2/narrator.py`
  2. Added Step 4.26 low-mention narrator guard (CRASHED: `'list' object has no attribute 'get'`)
     - Modified: `src/agents/characters.py` — new Step 4.26 block
  3. Added Step 5.4.6 possessive-descriptor merge (WRONG DIRECTION: merged into father not son)
     - Modified: `src/agents/characters.py` — new Step 5.4.6 block
  - Result: Plot summary improved ✓. Narrator still wrong ✗. "the boy" on father instead of son ✗.
- Attempt 6:
  1. Fixed `narrator.py detect()` crash (list vs dict unwrapping)
     - Modified: `src/pipeline/character_extraction_v2/narrator.py`
  2. Raised min-mention narrator guard from ≤1 to ≤2
     - Modified: `src/pipeline/character_extraction_v2/narrator.py`
  3. Fixed Step 5.4.6 merge direction (descriptor→proper name)
     - Modified: `src/agents/characters.py`
  - Result: Uncle Bill narrator ✓. Merge direction fixed ✓. But John Donaldson false secondary narrator → profile catastrophe.
- Attempt 7:
  1. Added mention-count guard for secondary narrators in `update_characters_with_narrator()`
     - Modified: `src/pipeline/character_extraction_v2/narrator.py`
     - Result: John Donaldson no longer false secondary narrator ✓. Profiles improved (4.5→6) ✓.
     - New: Boy (Johnny) disappeared — merged into father. Plot summary fabricated false twist.
- Attempt 8:
  1. Added Step 5.9.5 role assignment fix — mention-count-based role upgrades for main_cast
     - Modified: `src/agents/characters.py`
     - Result: John Donaldson (son) now "protagonist" ✓
  2. Added nested narration guidance to summarizer CHUNK+CONSOLIDATE prompts
     - Modified: `src/pipeline/summarization/summarizer.py`
     - Result: Chapter summaries correctly attribute embedded narrative to the boy ✓, plot summary no longer fabricated ✓

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 2 | Wrong narrator (Uncle Bill vs Johnny) | `narrator.py` | Fixed — Bill is now narrator ✓ |
| 3 | Johnny missing — exact_firstname guard | `characters.py` | **REGRESSION** — REVERTED |
| 4 | Johnny false-merged — co-present guard Step 5.4.5 | `characters.py` | "American, sir" gone ✓, narrator regressed ✗ |
| 5 | Narrator guard (Step 4.26) | `characters.py` | **BUG** — crashed, never fired |
| 5 | Possessive-descriptor merge (Step 5.4.6) | `characters.py` | **WRONG DIRECTION** |
| 5 | Narrator prompt (frame narrative) | `narrator.py` | Partial — prompt works but code guard fails |
| 6 | narrator.py detect() crash | `narrator.py` | Fixed ✓ |
| 6 | Min-mention narrator guard ≤2 | `narrator.py` | Fixed ✓ |
| 6 | Step 5.4.6 merge direction | `characters.py` | Fixed ✓ |
| 7 | John Donaldson false secondary narrator | `narrator.py` | Fixed ✓ — mention-count guard blocks correctly |
| 7 | Boy disappeared (false merge with father) | (not yet attempted) | **NEW ISSUE** |
| 7 | Plot summary fabrication | (not yet attempted) | **NEW ISSUE** |
| 8 | Role assignment: John Donaldson (28 mentions) was "supporting" | `characters.py` — Step 5.9.5 | Fixed ✓ |
| 8 | Chapter summary nested narration | `summarizer.py` — prompts | Fixed ✓ — summaries now correct |
| 8 | Father/son split | (side effect of summary fix) | Fixed ✓ — now separate characters |
| 8 | Cross-character aliases on son | (not yet attempted) | **NEW ISSUE** |
| 8 | Generic relationship labels | (not yet attempted) | **NEW ISSUE** |

**Pattern:** narrator.py and summarizer.py fixes are stable. Remaining issues are in alias resolution (main_cast.py or characters.py) and profiler prompts (analyzer.py).

## Configuration Notes
- Model config appropriate: qwen3.5:122b-a10b for characters/summaries/profiles, qwen3.5:35b-a3b for structure/pronunciation
- Zero LLM retries across all stages
- All 13 pronunciations have IPA
- Runtime: ~12 min (36 LLM calls)

## Next Action
Run PROMPT_fix.md to address cross-character alias contamination (Critical #1) and generic relationship labels (High #3).
