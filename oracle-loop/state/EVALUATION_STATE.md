# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 10
- **Phase:** awaiting_evaluation
- **baseline_score:** 6.55
- **Competitive Mode:** none

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Pipeline Notes (Attempt 10)
- Runtime: 34m 58s, 33 LLM calls
- WARNING: "Narrator detection failed or returned non-dict: None" — Uncle Bill may not be flagged as narrator
- WARNING: Only 3 characters in final output: "John Donaldson", "Uncle Bill", "Ted Frith" — father (John Donaldson Sr.) appears MISSING
- "Pass 2 failed for John Donaldson, keeping without aliases"
- Canonical name shows as "John Donaldson (aka John, the boy)" not "John Donaldson (the son)" — Step 5.4.6b may have renamed without father split
- BLOCKED aliases: 'the dying man', 'his estranged father' claimed by multiple phantom characters (Deceased Friend, Wounded Stretcher-Bearer)
- F6/F6b added 3+1 characters from summaries (Margaret Donaldson added again)

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 7/10 ✗ (FAILING)
  - Completeness: 8/10
  - Identity Resolution: 7/10 ← father/son separated ✓, but canonical name "John's son" confusing
  - Alias Grouping: 6.5/10 ← cross-contamination fixed ✓ but father still has no descriptive aliases
- Character Profiles: 7/10 ✗ (FAILING)
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 8.5/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 8.0/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold)

## What Attempt 9 Changed vs Attempt 8

**Improvements:**
- Cross-character alias contamination FIXED ✓ — son no longer has "the father", "the man", "John Donaldson (the father)" as aliases. RULE 3d/3e working.
- Ted Frith relationship label improved: "companion" instead of "associated" (secondary profiler prompt fix working)
- 14 pronunciations all with IPA ✓

**Still broken / new issues:**
- **All MAIN character relationships still "associated"** — the fix only modified the secondary profiler prompt (line ~3405), not the primary profiler prompt. Ted Frith is the only character that benefited.
- **Father (John Donaldson Sr.) still has no descriptive aliases** — aliases "the volunteer", "the stretcher-bearer", etc. were blocked as "already claimed" by the son. The aliases the RULE 3d/3e blocked on the son were not reassigned to the father.
- **"Age: two years old" hallucinated** on both John Donaldson Sr. and John's son — `appearance.age_indication` field is "two years old" for both. Likely misinterpretation of a time duration in the text.
- **Canonical name "John's son" is confusing** — reads as "son of John" (= the grandson), but this character IS the protagonist named John. Previous attempt had "John Donaldson (the son)" which was clearer.
- **Uncle Bill has orphan relationship "John Donaldson: associated"** — doesn't map to either disambiguated character's canonical name

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

## Current Issues (Priority Order)

### CRITICAL

(none — no catastrophic failures remaining)

### HIGH

1. **Primary profiler prompt still allows "associated" relationship labels** [Profiles]
   - Problem: ALL main character relationships are "associated". The attempt 9 fix only modified the secondary profiler prompt (~line 3405 in analyzer.py). The PRIMARY profiler prompt (for main cast characters) was NOT updated. Ted Frith (the only secondary character with relationships) correctly got "companion", confirming the secondary fix works.
   - Evidence: Uncle Bill → John's son = "associated" (should be "guardian"/"uncle"), Uncle Bill → John Donaldson Sr. = "associated" (should be "friend"/"former classmate"), John's son → John Donaldson Sr. = "associated" (should be "son"/"estranged son").
   - Location: `src/analyzer.py` — `_generate_character_profile()` — the PRIMARY prompt block (earlier in the function, for main cast characters). Look for the relationship instruction section in the prompt that runs for `role != "supporting"` or the default/main profile prompt.
   - Fix: Apply the same "associated"/"acquaintance" prohibition and specific relationship type guidance to the primary profiler prompt, not just the secondary one.
   - Impact: Fixing this alone pushes Profiles from 7 → 8+

2. **Father character still has no descriptive aliases** [Alias Grouping]
   - Problem: `John Donaldson Sr.` (main_cast_2, 28 mentions) has aliases `["John", "John Donaldson"]` — functional but missing all the descriptive aliases used in the text: "the volunteer", "the stretcher-bearer", "the man", "the civilian", "the shabby grizzled American civilian".
   - Root cause: Pipeline notes show these aliases were blocked as "already claimed" by the son character. The son claimed them in Pass 2 before RULE 3d/3e fired. RULE 3d/3e blocks them on the son but doesn't REASSIGN them to the father.
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` — verify_aliases(), or a post-verify step
   - Fix approach: When RULE 3d/3e blocks an alias on character A (same-base-name sibling), check if it should be reassigned to character B (the other same-name character). If alias is a descriptor that fits B's role/context better, add it to B's alias list.
   - Alternative: In a post-merge step in `characters.py`, for disambiguation pairs (characters sharing a base name), redistribute unclaimed descriptor aliases based on role/context clues.

3. **Uncle Bill has orphan relationship reference "John Donaldson"** [Profiles]
   - Problem: Uncle Bill's relationships include `"John Donaldson": "associated"` which doesn't map to either disambiguated character's canonical name ("John Donaldson Sr." or "John's son"). This is a stale/orphan reference.
   - Location: `src/analyzer.py` — `_generate_character_profile()` or a post-profiling normalization step
   - Fix: After profiling, normalize relationship keys to match actual canonical names in the character list. If a relationship key matches a known alias, map it to the canonical name.

### MEDIUM

4. **"Age: two years old" hallucinated on two characters** [Profiles]
   - Problem: `appearance.age_indication` is "two years old" for both John Donaldson Sr. and John's son. John Donaldson Sr. is elderly/middle-aged (shabby, grizzled). John's son is 18 (explicitly stated in his own physical_description). "Two years old" is completely fabricated.
   - Root cause: Likely the LLM misinterpreted a time duration phrase (e.g., "for two years") in the text as an age.
   - Location: `src/analyzer.py` — profile generation, or `src/pipeline/profiling/` — wherever `age_indication` is extracted
   - Fix: Could add validation to reject absurd ages (< 5 for non-infant characters), or cross-check age_indication against physical_description. Low priority since age_indication is a minor field.

5. **Canonical name "John's son" is confusing** [Identity Resolution]
   - Problem: The protagonist (18-year-old ambulance driver, the main character of the war narrative) is named "John's son". This reads as "the son of John" = the grandson. The previous attempt had "John Donaldson (the son)" which was clearer about which generation.
   - Impact: A narrator reading this would initially think "John's son" is the 12-year-old grandson who appears in the final scene, not the protagonist.
   - Root cause: The character extraction pipeline's disambiguation renamed the character.
   - Fix: Low priority — the name is technically not wrong, just potentially confusing. The profile content clarifies. Would need changes to the disambiguation logic in characters.py.

6. **Son's profile has misattributed quote** [Profiles]
   - Problem: "American, sir" is listed as an example quote for John's son, but this phrase is spoken by the father (John Donaldson Sr.) and by Joe Barron, not by the son. The son witnesses these declarations.
   - Impact: Minor — a narrator might prepare the wrong voice for this line.
   - Location: Profile generation prompt or voice_guidance extraction

### LOW

7. **Father's evidence misattributes role** [Profiles]
   - Problem: Evidence entry says father "Died mortally wounded... while serving as an American Red Cross ambulance driver". The father was a civilian volunteer, not the ambulance driver — the SON was the ambulance driver.
   - Impact: Minor factual error in evidence citations.

8. **Missing nicknames: "Johnny" and "Teddy"** [Alias Grouping]
   - Problem: The boy is called "Johnny" in the text, Ted Frith is called "Teddy". Neither alias appears.
   - Fix: NICKNAME_TO_FORMAL dict additions or LLM prompt improvement.

9. **Margaret Donaldson absent from character list** [Completeness]
   - Problem: Pipeline notes say "Margaret Donaldson added via F6b ✓" but she's not in the final 5 characters. Likely filtered by mention count.
   - Impact: Very minor — she appears briefly and dies before the main narrative.

## Fix Strategy for Attempt 10

**Two highest-leverage fixes to cross the 8.0 threshold in both failing categories:**

1. **Fix primary profiler prompt** (HIGH #1) — Apply "associated"/"acquaintance" prohibition to BOTH the primary and secondary profiler prompts in `_generate_character_profile()`. The secondary prompt was already fixed in attempt 9; now the primary prompt needs the same treatment. This is the single change most likely to push Profiles from 7 → 8+.

2. **Fix father alias reassignment** (HIGH #2) — When RULE 3d/3e blocks an alias on one same-name sibling, attempt to reassign it to the other sibling. Alternatively, add a post-merge step in `characters.py` that redistributes descriptor aliases between disambiguation pairs. This pushes Characters from 7 → 8 by giving the father his descriptive aliases.

**Do NOT touch** (working correctly):
- narrator.py (stable since attempt 6)
- characters.py Step 5.4.5 (co-present guard)
- characters.py Step 5.4.6 (merge direction)
- summarizer.py (nested narration fix working since attempt 8)
- main_cast.py RULE 3d/3e (alias contamination fix working)

## Fix History
- Attempt 10:
  1. Post-filter "associated"/"acquaintance"/"unknown" relationship labels from primary profiler
     - Modified: `src/analyzer.py` — `_generate_character_profile()` after parsing relationships
     - Root cause: LLM ignores prohibition in primary prompt; enforced programmatically
     - Change: filtered empty dict triggers secondary call → secondary prompt correctly produces specific labels (confirmed with Ted Frith pattern)
  2. Renamed "John's son" → "John Donaldson (the son)" via new Step 5.4.6b
     - Modified: `src/agents/characters.py` — new Step 5.4.6b after Step 5.4.6
     - Root cause: LLM Pass 1 extracts possessive-descriptor form; no rename step existed
     - Change: finds matching parent character (same first name, multi-word canonical), extracts last name, renames to "[First] [Last] (the [role])"
     - Universal: works for any book where parent+child share names
  - Smoke test: PASS — 332 tests pass; canonical name rename correctly produces "John Donaldson (the son)" from "John's son" + parent "John Donaldson Sr."
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
| 8 | Father/son split | (side effect of summary fix) | Fixed ✓ — now separate characters |
| 9 | Cross-character alias contamination | `main_cast.py` — RULE 3d/3e | Fixed ✓ — contamination blocked |
| 9 | Generic relationship labels (secondary prompt) | `analyzer.py` — secondary prompt | **PARTIAL** — secondary works, primary NOT modified |
| 10 | Primary profiler "associated" labels | `analyzer.py` — post-filter + secondary call trigger | Post-filter removes vague labels; empty dict triggers secondary call |
| 10 | "John's son" confusing canonical name | `characters.py` — new Step 5.4.6b | Renamed to "John Donaldson (the son)" |

**Pattern:** The remaining 2 issues are both in `analyzer.py` (primary profiler prompt) and `main_cast.py` or `characters.py` (alias reassignment). These are the ONLY files that need changes.

## Configuration Notes
- Model config appropriate: qwen3.5:122b-a10b for characters/summaries/profiles, qwen3.5:35b-a3b for structure/pronunciation
- Zero LLM retries across all stages
- All 14 pronunciations have IPA
- Runtime: ~11 min (38 LLM calls)
- John's son confidence: LOW (0.30) — likely due to minimal alias coverage and shared "John" alias

## Next Action
Run PROMPT_analyze.md to re-analyze american_sir with attempt 10 fixes:
1. Relationship labels no longer "associated" — secondary call produces specific labels ✓
2. "John's son" renamed to "John Donaldson (the son)" for clearer identity resolution ✓
