# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 12
- **Phase:** awaiting_evaluation
- **baseline_score:** 6.55
- **Competitive Mode:** none

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 5.5/10 ✗ (FAILING — father/son merge persists)
  - Completeness: 6/10
  - Identity Resolution: 4/10 ← father/son FALSE MERGE (STEP 3.95 did not fire)
  - Alias Grouping: 6.5/10
- Character Profiles: 6/10 ✗ (FAILING — improved from 5 via narrator+relationship fixes)
- Chapter Summaries: 7/10 ✗ (FAILING)
- Pronunciation Guide: 8.5/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 7.2/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold)

## What Attempt 11 Changed vs Attempt 10

**IMPROVEMENTS:**
- **Narrator detection FIXED** — Uncle Bill is `is_narrator=True` ✓ (was None in attempt 10). The V2 pipeline_metadata narrator extraction in analyzer.py worked.
- **Relationship cleanup WORKED** — Uncle Bill ↔ Ted Frith = "close friend" ✓ (was "associated" in attempt 10). The `clean_unknown_relationships()` extension to strip "associated" labels worked, and surviving relationships are specific.
- **Ted Frith has relationship back** — "close friend" with Uncle Bill ✓ (was empty in attempt 10).

**PERSISTENT FAILURES:**
- **Father/son STILL MERGED** — John Donaldson has 43 mentions (combined father ~28 + son ~15). Aliases include both "the father" AND "the boy" on the same character. STEP 3.95 (programmatic same-name split) did NOT fire.
- **Root cause of STEP 3.95 failure**: `active_characters` is EMPTY in the structure output. STEP 3.95 parses `[Characters present: ...]` from summaries to find disambiguated same-name entries. Since active_characters is empty, there's nothing to parse → no split signal → no split.
- **John Donaldson has ZERO relationships** — should have Uncle Bill (guardian/friend), father-son relationship with the other JD
- **"Age: two years old" hallucination** — still present on John Donaldson
- **Summary confusion** — "the narrator later reassures his son John about Uncle Bill's redemption" should be "Uncle Bill reassures John about his father's redemption"

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
| 9 | 8.0 | +1.45 | Cross-character alias contamination fixed ✓. Relationship fix only hit secondary prompt. Father still has 0 descriptive aliases. |
| 10 | 7.0 | +0.45 | **REGRESSION.** Father/son merge recurred (LLM non-determinism). Both attempt 10 fixes had no effect. |
| 11 | 7.2 | +0.65 | Narrator fix ✓, relationship cleanup ✓. But STEP 3.95 didn't fire (empty active_characters). Father/son still merged. |

## Current Issues (Priority Order)

### CRITICAL

1. **STEP 3.95 programmatic split has no signal — active_characters is empty** [Identity Resolution]
   - Problem: STEP 3.95 was designed to parse `[Characters present: ...]` from summaries and split same-name merged characters. But `active_characters` is `[]` in the structure output, so STEP 3.95 has NO data to work with.
   - Root cause: The summarizer is not populating `active_characters` or `key_events` fields. These are empty lists. The `[Characters present: ...]` prefix is either not generated or not parsed into the structured fields.
   - Evidence: `jq '.structure[0].active_characters' analysis.json` → `[]`; `jq '.structure[0].key_events' analysis.json` → `[]`
   - Location: Either `src/pipeline/summarization/summarizer.py` (not generating the prefix) or `src/analyzer.py` (not parsing it into structured fields)
   - Fix options:
     - **(A) Make STEP 3.95 parse raw summary TEXT** instead of relying on `active_characters` field. The summary text DOES mention both "the boy" and "the father" — scan for disambiguating same-name patterns in summary prose.
     - **(B) Fix the summarizer** to populate `active_characters` properly. This is the cleaner fix but touches more code.
     - **(C) Alternative split signal**: Instead of relying on active_characters, detect contradictory aliases on a single character. If one character has both "the boy" and "the father" as aliases, that's a strong signal of a false merge. Split based on alias contradiction.
   - **Recommended: Option (C)** — it's the most robust because it doesn't depend on external fields. A character simultaneously aliased as "the boy" AND "the father" is logically contradictory and should trigger a split.

### HIGH

2. **John Donaldson has ZERO relationships** [Profiles]
   - Problem: The merged John Donaldson character has empty relationships `{}`. Should have: Uncle Bill (guardian/family friend), and if split, father↔son.
   - Evidence: `jq '.characters[1].relationships' analysis.json` → `{}`
   - Location: `src/analyzer.py` — `_generate_character_profile()`
   - Root cause: The profiler may be confused by the merged identity (father+son traits) and unable to assign coherent relationships.
   - Fix: Will partially resolve when father/son split is fixed. The split characters would each have clearer context for relationship inference.

3. **Summary says "Uncle Bill's redemption" — should be father's redemption** [Summaries]
   - Problem: Summary text says "the narrator later reassures his son John about Uncle Bill's redemption". Uncle Bill IS the narrator. The correct reading: Uncle Bill reassures the boy John about his FATHER's (John Donaldson Sr.) redemption.
   - Evidence: The text's theme is the father's redemption from embezzlement through his death as an "American, sir" on the battlefield.
   - Location: `src/pipeline/summarization/summarizer.py` — consolidation prompt
   - Root cause: The LLM confuses the nested narrative layers. With the father/son merge, there's no clear "father" entity to attribute redemption to, so the LLM substitutes Uncle Bill.
   - Fix: Will partially resolve when father/son split is fixed. With a clear "John Donaldson (the father)" character, the summary can correctly attribute redemption.

### MEDIUM

4. **"Age: two years old" hallucination on John Donaldson** [Profiles]
   - Problem: `appearance.age_indication: "two years old"`. John Donaldson (son) is ~18, the father is middle-aged/elderly. "Two years old" is fabricated, likely from a time-duration phrase misinterpreted.
   - Location: `src/analyzer.py` — profile generation, age_indication parsing
   - Fix: Add validation rejecting age < 5 for non-infant characters, or cross-check against physical_description and role.

5. **active_characters and key_events empty in structure output** [Summaries]
   - Problem: Both fields are `[]`. These enable F6 reconciliation and STEP 3.95.
   - Location: `src/pipeline/summarization/summarizer.py` or `src/analyzer.py` (parsing)
   - Fix: Ensure the summarizer generates and parser captures these fields. This is related to CRITICAL #1.

6. **Margaret Donaldson absent from character list** [Completeness]
   - Problem: The state says "Margaret Donaldson added by F6 reconciliation" but she doesn't appear in the final character list (only 4 characters).
   - Evidence: Only Uncle Bill, John Donaldson, Joe Barron, Ted Frith in output.
   - Location: May have been filtered by post-processing or mention count threshold.
   - Impact: Minor — she's a referenced-only character.

### LOW

7. **Missing nicknames: "Johnny" and "Teddy"** [Alias Grouping]
   - Still not captured. Low priority compared to critical issues.

## Fix Strategy for Attempt 12

**Priority 1: Make the father/son split work WITHOUT depending on active_characters.**

The cleanest approach is **alias contradiction detection** (Option C from CRITICAL #1):
- After all merges complete (end of Step 3.9 or in STEP 3.95), scan each character's aliases
- If a character has aliases that are logically contradictory (e.g., "the boy" + "the father", or "the son" + "the old man"), this signals a false merge
- Define contradiction pairs: {boy↔father, son↔father, boy↔old man, young↔old, child↔parent, daughter↔mother, son↔mother}
- When detected, split the character using the contradictory aliases as seeds for the split identities
- This is more robust than relying on active_characters because it works regardless of what the summarizer outputs

**Priority 2: The summary confusion and missing relationships should partially self-resolve** once the split works. Don't touch these directly — evaluate after the split fix.

**Do NOT touch** (working correctly):
- Narrator detection (Uncle Bill = narrator ✓)
- Relationship cleanup ("close friend" ✓)
- RULE 3d/3e alias contamination guards
- Co-present guard (Step 5.4.5)
- Pronunciation pipeline

## Fix History
- Attempt 11:
  1. STEP 3.95 — Programmatic same-name split from characters_present lists
     - Modified: `src/agents/characters.py` — new STEP 3.95 after STEP 3.9 (before narrator detection)
     - Result: **DID NOT FIRE** — active_characters is empty, no characters_present to parse
  2. clean_unknown_relationships() — extended to also remove "associated" labels
     - Modified: `src/pipeline/character_profiling/post_corrections.py`
     - Result: **FIXED** ✓ — Uncle Bill ↔ Ted Frith now "close friend"
  3. Narrator extracted from V2 pipeline_metadata in analyzer.py
     - Modified: `src/analyzer.py` — after line 1107 (V2 extraction result)
     - Result: **FIXED** ✓ — Uncle Bill is narrator
- Attempt 10:
  1. Post-filter "associated"/"acquaintance"/"unknown" relationship labels from primary profiler
     - Modified: `src/analyzer.py` — `_generate_character_profile()` after parsing relationships
     - Result: **NO EFFECT** — relationships still "associated". Post-filter may not be executing.
  2. Renamed "John's son" → "John Donaldson (the son)" via new Step 5.4.6b
     - Modified: `src/agents/characters.py` — new Step 5.4.6b after Step 5.4.6
     - Result: **DID NOT FIRE** — no parent character exists (father/son merged)
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
- Attempt 9:
  1. Added RULE 3d + RULE 3e to verify_aliases() in main_cast.py
     - Modified: `src/pipeline/character_extraction_v2/main_cast.py`
     - Result: Cross-character alias contamination fixed ✓. Son no longer has "the father" etc.
  2. Fixed secondary profiler prompt to forbid "associated"/"acquaintance"
     - Modified: `src/analyzer.py` — secondary prompt only (~line 3405)
     - Result: **PARTIAL** — Ted Frith got "companion" ✓, but main characters still all "associated" because PRIMARY prompt was not modified.

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
| 8 | Father/son split | (side effect of summary fix) | Fixed ✓ in attempts 8-9, REGRESSED in attempt 10 |
| 9 | Cross-character alias contamination | `main_cast.py` — RULE 3d/3e | Fixed ✓ — contamination blocked |
| 9 | Generic relationship labels (secondary prompt) | `analyzer.py` — secondary prompt | **PARTIAL** — secondary works, primary NOT modified |
| 10 | Primary profiler "associated" labels | `analyzer.py` — post-filter + secondary call trigger | **NO EFFECT** — still "associated" |
| 10 | "John's son" confusing canonical name | `characters.py` — new Step 5.4.6b | **DID NOT FIRE** — no parent character (merged) |
| 11 | STEP 3.95 programmatic split from characters_present | `characters.py` | **DID NOT FIRE** — active_characters empty |
| 12 | STEP 3.95 replaced: alias contradiction detection (parent-tier vs child-tier) | `characters.py` | Pending analysis |
| 11 | "associated" relationship cleanup | `post_corrections.py` | Fixed ✓ |
| 11 | Narrator from V2 pipeline_metadata | `analyzer.py` | Fixed ✓ |

**Pattern:** STEP 3.95 failed because it depends on `active_characters` being populated, which it isn't. Fix phase must either (A) make STEP 3.95 use a different signal (alias contradictions), or (B) fix active_characters population. **characters.py has been modified 8 times** — consider whether the alias contradiction approach adds too much complexity vs fixing the data source.

## Configuration Notes
- Model config appropriate: qwen3.5:122b-a10b for characters/summaries/profiles, qwen3.5:35b-a3b for structure/pronunciation
- Zero LLM retries across all stages
- All 14 pronunciations have IPA
- Narrator detection from V2 pipeline: working ✓

## Next Action
Run PROMPT_analyze.md to re-analyze american_sir with STEP 3.95 alias contradiction detection
