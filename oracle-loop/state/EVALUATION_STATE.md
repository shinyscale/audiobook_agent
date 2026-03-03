# Current Evaluation State

## Active Text
- **Name:** monkeys_paw
- **Attempt:** 3
- **Phase:** awaiting_fix
- **baseline_score:** 7.4

## Output Files
- HTML: ../output/monkeys_paw/report.html
- JSON: ../output/monkeys_paw/analysis.json

## Latest Scores
- Structure Detection: 8/10 ✓
- Character Extraction: 5/10 ✗ (FAILING — regression from attempt 2's 8/10)
  - Completeness: 7/10
  - Identity Resolution: 3/10 ← phantom "The Old Man" is primary blocker
  - Alias Grouping: 4/10
- Character Profiles: 7/10 ✗ (FAILING — relationship fix worked but phantom cascades)
- Chapter Summaries: 9.5/10 ✓
- Pronunciation Guide: 9/10 ✓
- HTML Presentation: 8/10 ✓
- **Overall: 7.5/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold: Character Extraction, Character Profiles)

## What Worked in Attempt 3
- **Relationship fix from attempt 2 is working:** Mr. White → Herbert = "father" ✓, Herbert → Mr. White = "son" ✓, Mrs. White → Herbert = "mother" ✓
- **Gender inference working:** Mr. White = male ✓, Mrs. White = female ✓, Morris = male ✓
- **Morris still present** as main_cast_3 with alias "Morris" ✓
- **Pronunciation clean** — no false positives, good IPA coverage

## What Regressed in Attempt 3
- **Phantom character "The Old Man" appeared** (main_cast_6, 41 mentions) — was NOT present in attempt 2
- Mr. White lost "the old man" alias (had it in attempt 2)
- Mrs. White lost "the old woman" alias (had it in attempt 2)
- Character Extraction dropped from 8/10 → 5/10 due to phantom
- This is LLM non-determinism: the character extraction LLM produced a different result this run

## Current Issues (Priority Order)

### CRITICAL
1. **Phantom character "The Old Man" is a false split of Mr. White** [Identity Resolution]
   - Problem: "The Old Man" (main_cast_6, 41 mentions) is extracted as a separate character from Mr. White (main_cast_0, 10 mentions). They are the same person — the text uses "the old man" as a descriptor for Mr. White throughout Parts II and III.
   - Evidence: "The Old Man" profile has Mr. White's physical description ("thin grey beard"), Mr. White's quotes ("I wish for two hundred pounds", "For God's sake don't let it in"), and Mr. White's personality. It IS Mr. White.
   - The text uses "the old man" far more often (41×) than "Mr. White" (10×), so the descriptor accumulated more mentions.
   - Root cause: LLM extracts "The Old Man" as a separate character in Pass 1. `_merge_descriptor_into_proper_name()` (Step 3.6b in `src/agents/characters.py`) only matches **all-lowercase** common-noun characters. "The Old Man" has title case → bypass. The function needs to also match title-cased common-noun descriptors like "The Old Man" where every word (after stripping articles) is a common English word, not a proper noun.
   - Additional signals for merge: same gender (male), same role (protagonist), physical description overlap ("thin grey beard"), Mr. White has title "Mr." which implies an old/adult man.
   - Fix approach: Extend `_merge_descriptor_into_proper_name()` to normalize case before the "no proper noun" check, OR add a new rule: if canonical_name.lower() starts with "the " and all remaining words are common English words (adjectives + nouns like "old man", "old woman", "young boy"), and a titled character (Mr./Mrs./Miss/Dr.) with matching gender exists → merge descriptor into titled character.
   - Location: `src/agents/characters.py` — `_merge_descriptor_into_proper_name()` (Step 3.6b)

2. **"The Old Man" has completely wrong aliases** [Alias Grouping]
   - Problem: Aliases of "The Old Man" are: "The Monkey's Paw", "the paw", "The Visitor", "The Old Woman" — ALL wrong.
   - "The Monkey's Paw" / "the paw" = the talisman object, not Mr. White
   - "The Visitor" = Morris (Part I) and the Maw & Meggins representative (Part II), not Mr. White
   - "The Old Woman" = Mrs. White's descriptor, not Mr. White's
   - Impact: Once the phantom character is merged into Mr. White, these aliases would transfer — they must NOT be inherited. The merge must discard aliases that don't belong to the target.
   - Fix approach: When merging descriptor into proper name, only transfer the canonical_name as an alias (e.g., "The Old Man" → alias of Mr. White). Do NOT inherit existing aliases from the descriptor character — they were likely mis-assigned by the LLM. This is consistent with existing behavior: MEMORY.md notes "Garbage aliases from descriptor are NOT inherited (only canonical_name added as alias)".
   - Location: `src/agents/characters.py` — `_merge_descriptor_into_proper_name()` (Step 3.6b)

### HIGH
3. **Mr. White has zero aliases** [Alias Grouping]
   - Problem: Mr. White should have "the old man" as alias. In attempt 2, it was assigned correctly.
   - Root cause: Direct consequence of CRITICAL #1 — "the old man" was claimed by the phantom character, blocking it from Mr. White via Rule 3.
   - Fix: Resolving CRITICAL #1 (merging phantom into Mr. White) will automatically make "the old man" an alias of Mr. White.

4. **Mrs. White has zero aliases** [Alias Grouping]
   - Problem: Mrs. White should have "the old woman" as alias. In attempt 2, it was assigned correctly.
   - Root cause: "The Old Woman" was claimed as alias of the phantom "The Old Man" character, blocking it from Mrs. White.
   - Fix: After CRITICAL #1 is resolved and "The Old Woman" is discarded as a garbage alias, "the old woman" should become available for Mrs. White. However, this depends on whether Pass 2 re-proposes it. If "the old woman" was only proposed because "The Old Man" existed, it may need programmatic injection similar to `_add_title_stripped_aliases()`.

5. **Herbert White gender is null** [Profiles]
   - Problem: Herbert doesn't have Mr./Mrs. title, so `infer_gender_from_title()` can't set gender.
   - Evidence: Text says "his son Herbert" — clearly male.
   - Fix: Extend `infer_gender_from_title()` to also check relationship labels: if character's relationship to someone is "son" → male, "daughter" → female. Or check alias keywords: "his son" contains "son" → male.
   - Location: `src/pipeline/character_profiling/post_corrections.py` — `infer_gender_from_title()`

### MEDIUM
6. **Mrs. White profile incomplete for Part III** [Profiles]
   - Problem: Personality says "practical concern and anxiety when dealing with unexpected visitors." This misses Part III entirely: her desperate realization about the wishes, frantic urging of Mr. White to wish Herbert back, physical struggle to unbolt the door, and wail of disappointment.
   - Impact: A narrator needs to understand her dramatic arc from composed housewife → desperate grieving mother → frantic woman fighting to open the door.
   - This is a profile generation quality issue, not a pipeline bug. May improve if phantom character is resolved (freeing up "the old woman" context for her profile).
   - Location: `src/analyzer.py` — `_generate_character_profile()`

7. **Mr. White → "The Old Man" relationship = "associated"** [Profiles]
   - Problem: Nonsensical — they are the same person.
   - Fix: Automatically resolved when CRITICAL #1 merges the phantom.

8. **Chapter titles: "1" / "2" / "3" instead of "I" / "II" / "III"** [Structure]
   - Problem: The Monkey's Paw uses Roman numerals (I, II, III) in the original text. Titles show Arabic.
   - Same issue as attempts 1 and 2.
   - Location: `src/pipeline/chapter_detection/consensus.py` — `_clean_title()`
   - Low priority — doesn't affect narrator usability significantly.

### LOW
9. **Monkey's paw not marked is_symbolic** [Character Metadata]
   - Problem: `is_symbolic: false` for an inanimate cursed object.
   - Impact: Minimal.

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 7.4 | — | Baseline — Morris dropped, visitor alias wrong, Mr. White no aliases |
| 2 | 8.25 | +0.85 | Morris restored, aliases fixed, but new relationship label error |
| 3 | 7.5 | +0.1 | Relationship fix worked ✓, but phantom "The Old Man" appeared (LLM non-determinism) |

## Fix History
- Attempt 1 (monkeys_paw):
  - **Morris missing (Completeness)**: Added military/clerical ranks to `_add_title_stripped_aliases()` in `main_cast.py` so "Sergeant-Major Morris" gets "Morris" as auto-alias → enough mentions to pass grounding. Also added `not pc.id.startswith("main_cast_")` guard to `_convert_characters` evidence filter in `analyzer.py` — main_cast characters (LLM-vetted) are never dropped by the false-positive filter.
  - **Mrs. White gender (Profiles)**: Added second call to `enforce_gender_consistency` at end of Phase B `run_all` (after `_propagate_missing_reverses`) in `post_corrections.py` — catches any re-introduced gender mismatches.
  - **Pronunciation false positives**: Added "bedclothes", "instalment", "betokened" (and variants) to `COMMON_WORDS_WHITELIST` in `cmu_proposer.py`.

- Attempt 2 (monkeys_paw):
  - **Mr. White→Herbert "husband" (Profiles)**: Added `fix_family_spousal_triangle()` in `post_corrections.py` — if A→B="son"/"daughter" and B→C="wife"/"husband", set A→C=same child label. Also added `infer_gender_from_title()` for Mr./Mrs. title-based gender.
  - **Gender null (Profiles)**: Added `gender` field to Character model in `models.py`.

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | Morris missing (Completeness) | `main_cast.py`, `analyzer.py` | Fixed ✓ |
| 1 | Mrs. White gender (Profiles) | `post_corrections.py` | Fixed ✓ |
| 1 | Pronunciation false positives | `cmu_proposer.py` | Fixed ✓ |
| 2 | Mr. White→Herbert "husband" (Profiles) | `post_corrections.py`, `models.py` | Fixed ✓ |
| 2 | All genders null | `post_corrections.py`, `models.py` | Fixed ✓ |
| 3 | Phantom "The Old Man" (Identity Resolution) | TBD — `characters.py` `_merge_descriptor_into_proper_name()` | Pending |

**Pattern note:** The phantom character problem has appeared before (see MEMORY.md "Phantom Character Pattern"). The existing `_merge_descriptor_into_proper_name()` was designed for this but only matches all-lowercase names. Extending to title-case should be a targeted, safe change.

## Configuration Audit
- Models: qwen3.5:35b-a3b (structure, pronunciation), qwen3.5:122b-a10b (chars, summaries, profiles) — appropriate
- Context length: 32768 — sufficient for this short story (3,954 words)
- Temperature: 0.7 — reasonable
- think_mode: false — correct for qwen3.5
- Duration: 40m 1s, 38 LLM calls, 83,859 tokens
- All 5 profiles at HIGH confidence
- No JSON parse failures

## Pipeline Notes (Attempt 3)
- Duration: 40m 1s, 38 LLM calls, 83,859 tokens
- 5 characters found: Mr. White (10), Mrs. White (10), Herbert White (19), Sergeant-Major Morris (5), The Old Man (41)
- Morris: ✓ present as "Sergeant-Major Morris (aka Morris)"
- WARNING: "The Old Man" exists as a SEPARATE character (canonical "The Old Man") with "The Monkey's Paw" and "the paw" as aliases (41 mentions)
- Mr. White aliases: NONE — "the old man" blocked because it's claimed by "The Old Man" character
- Mrs. White aliases: NONE — "the old woman" blocked as already claimed
- Herbert White aliases: "Herbert", "his son", "the son"
- Relationships NOW CORRECT: father/son/mother chain ✓

## Next Action
Run PROMPT_fix.md to extend `_merge_descriptor_into_proper_name()` to handle title-cased common-noun descriptors like "The Old Man" → merge into Mr. White.
