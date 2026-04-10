# Current Evaluation State

## Active Text
- **Name:** monkeys_paw
- **Attempt:** 4
- **Phase:** awaiting_analysis
- **baseline_score: 5.8**

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 7/10 ✗
  - Completeness: 7.5/10
  - Identity Resolution: 5.5/10 ← false split is primary blocker
  - Alias Grouping: 8/10
- Character Profiles: 6.5/10 ✗
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 8/10 ✓
- **Overall: 7.93/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold: Character Extraction 7/10, Character Profiles 6.5/10)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | FAIL | - | Pipeline crashed |
| 2 | 5.8 | - | First successful run — baseline set |
| 3 | 8.25 | +2.45 | Structure fixed, characters much improved, 2 categories still below 8.0 |
| 4 | 7.93 | +2.13 | Alias fix worked (stranger/visitor gone), but Herbert White false split + wrong label appeared |

## What Changed (Attempt 3 → 4)
- **IMPROVED**: monkey's paw aliases — "the stranger" and "the visitor" no longer aliased to paw ✓
- **IMPROVED**: "a cursed talisman" and "the talisman" blocked by Rule 0.5 ✓
- **REGRESSED**: Herbert White now falsely split into two characters with wrong "(the father)" label
- **UNCHANGED**: Morris still has zero relationships
- **UNCHANGED**: monkey's paw role still "protagonist", is_symbolic=False in output
- **UNCHANGED**: Mrs. White → Herbert relationship says "daughter" instead of "mother"

## Current Issues (Priority Order)

### CRITICAL
1. **FALSE SPLIT: Herbert White split into two characters with wrong label** [Identity Resolution]
   - Problem: "Herbert White (the father)" (`main_cast_2_parent`, 27 mentions) and "Herbert White" (`4e195cae6189`, 2 mentions) are listed as separate characters. Herbert is the **SON** of Mr. and Mrs. White — NOT a father. There is only ONE Herbert White in the story.
   - Evidence: The text explicitly establishes Herbert as Mr. and Mrs. White's young adult son who works at Maw and Meggins and dies in a machinery accident. There is no second Herbert.
   - ID pattern: `main_cast_2_parent` — the `_parent` suffix indicates the V2 pipeline's same-name disambiguation logic (`characters.py`) incorrectly created a parent/child split for Herbert. The pipeline likely saw "father" near "Herbert" in text (referring to Herbert's father Mr. White, not to Herbert himself being a father) and triggered the split.
   - Location: `src/pipeline/character_extraction_v2/characters.py` — look for same-name disambiguation logic that appends `_parent` suffix to character IDs. The split is being triggered when "father" appears near a character's name but refers to ANOTHER character's role (Mr. White is the father, Herbert is the son).
   - Fix: The same-name split should not fire when there is only ONE instance of a name in the extraction. It should require evidence of TWO distinct individuals with the same name (different ages, different time periods, explicit "Sr."/"Jr." markers). A single character having a relative who is "father" does not mean the character IS a father-named-Herbert.
   - Impact: This single issue drags down Identity Resolution (5.5), Character Profiles (phantom empty profile), and indirectly Completeness (Herbert's real profile data split across two entries).

### HIGH
2. **Mrs. White → Herbert White relationship labeled "daughter"** [Profiles]
   - Problem: Mrs. White's relationship to Herbert White shows `"daughter"` — this is WRONG. Mrs. White is Herbert's MOTHER. The relationship label should be "mother".
   - Evidence: The text establishes Mrs. White as the mother throughout: she grieves his death, demands the second wish to bring her son back.
   - Location: Profile generation in `src/analyzer.py` — `_generate_character_profile()` or relationship post-corrections in `src/pipeline/post_corrections.py`.
   - Fix: The profiler LLM may have confused the relationship direction (it set the label from Herbert's perspective "daughter" instead of Mrs. White's perspective "mother"). Or `enforce_gender_consistency` may have incorrectly swapped a label.
   - Note: This may self-resolve once the Herbert split (CRITICAL #1) is fixed — the split likely confuses the profiler about who is who.

3. **Sergeant-Major Morris has zero relationships** [Profiles]
   - Problem: Morris has `"relationships": {}`. The text explicitly says he is "his old friend the sergeant-major" — Mr. White's old friend.
   - Evidence: Part I: Morris arrives as an old friend, they share whiskey and stories. The summary correctly notes this.
   - Location: Either `_generate_character_profile()` didn't extract the friendship, or `reject_unfounded_friend_labels` in `src/pipeline/post_corrections.py` removed it.
   - Fix: Check if `reject_unfounded_friend_labels` is being too aggressive. The text has "his old friend" directly adjacent to Morris's name — this should pass the 150-char window check. If the profiler never generated the label, it's a prompt issue.

4. **monkey's paw is_symbolic=False in final output** [Identity Resolution]
   - Problem: Despite the prompt fix making is_symbolic=True during extraction (confirmed by pipeline notes: Rule 0.5 fired correctly), the final analysis.json shows `is_symbolic: false`.
   - Evidence: Pipeline notes say "BLOCKED aliases: 'a cursed talisman' and 'the talisman' were blocked by Rule 0.5 (is_symbolic=True now active)". But final JSON has `is_symbolic: false`.
   - Location: Something between extraction and final output is resetting is_symbolic. Check profiling stage in `src/analyzer.py` — the profile generation or character serialization may overwrite is_symbolic.
   - Fix: Ensure is_symbolic is preserved through the entire pipeline. The profile generation step should not reset character metadata flags.

### MEDIUM
5. **Role classification still wrong for Morris and monkey's paw** [Profiles]
   - Problem: Morris (`role: "protagonist"`) should be "supporting" — he's a catalyst who appears only in Part I. monkey's paw (`role: "protagonist"`) should be "antagonist" — it's the supernatural force causing harm.
   - Evidence: Morris delivers the paw and leaves; he doesn't drive the central conflict. The paw is the antagonistic force.
   - Location: V2 character extraction role assignment in `src/pipeline/character_extraction_v2/main_cast.py` — the `CHARACTER_IDENTIFICATION_PROMPT` was updated in attempt 3 but roles are still wrong.
   - Fix: The LLM may be ignoring role guidance. Consider: (a) a post-extraction role correction pass, or (b) stronger prompt emphasis. For a short story with 5 main characters, labeling all as "protagonist" suggests the LLM defaults to "protagonist" when uncertain.

6. **monkey's paw → Mr. White relationship labeled "creator"** [Profiles]
   - Problem: Mr. White did not create the monkey's paw. A holy fakir enchanted it. Morris brought it from India.
   - Evidence: Text says the fakir put a spell on the paw; Morris acquired it in India.
   - Location: Profile generation LLM output.
   - Fix: Minor — may self-resolve with better is_symbolic handling.

7. **Chapter 3 character tags show aliases alongside canonical names** [Presentation]
   - Problem: Ch3 characters: "the old man", "the old woman", "Mr. White". "The old man" is Mr. White's alias (appears twice under different names), "the old woman" is Mrs. White's alias (but "Mrs. White" doesn't appear).
   - Location: Chapter-to-character mapping in `src/analyzer.py` or HTML template. The summarizer used descriptors in Ch3 and the pipeline didn't resolve them to canonical names.
   - Fix: When building chapter character lists, resolve aliases to canonical names and deduplicate.

8. **fakir/fakirs listed as separate pronunciation entries** [Pronunciation]
   - Problem: "fakir" → /fəˈkɪər/ and "fakirs" → /fəˈkɪrz/ — different base vowel patterns for singular/plural.
   - Location: Pronunciation deduplication in `src/pipeline/pronunciation/`.
   - Fix: Deduplicate singular/plural forms.

### LOW
9. **narrative_style is null** [Profiles]
   - Problem: `narrative_style: null` instead of "third-person omniscient".
   - Location: Narrator detection in `src/analyzer.py`.

10. **"Chapters have descriptive titles" label** [Presentation]
    - Problem: HTML says "Chapters have descriptive titles" but "I.", "II.", "III." are Roman numeral markers.
    - Location: HTML template title classification logic.

11. **condoled IPA uses non-standard symbol** [Pronunciation]
    - Problem: /kənˈdōld/ uses /ō/ which is not standard IPA (should be /oʊ/ or /əʊ/).
    - Location: LLM pronunciation output normalization.

## Fix Priority for Attempt 5

Focus on the two failing categories (Character Extraction and Character Profiles). The CRITICAL Herbert split (#1) is the highest-impact fix — resolving it will likely improve both categories by 1+ points each:

1. **Fix Herbert White false split** — trace the `_parent` suffix logic in characters.py, understand why it fires for a single Herbert, and prevent false same-name splits when there's only one individual
2. **Fix is_symbolic preservation** — ensure is_symbolic=True survives from extraction to final output
3. **Check Morris relationship** — verify whether reject_unfounded_friend_labels is stripping a legitimate "friend" label
4. **Fix Mrs. White→Herbert "daughter" relationship** — may self-resolve with #1, but verify

If #1-#4 are fixed, Character Extraction should reach 8+ (no false split, correct symbolic flag) and Character Profiles should reach 8+ (correct relationships, Morris friendship).

## Fix History
- Attempt 1 fix: Fixed two crash-level bugs in analyzer.py (CharacterMap constructor) and summarizer.py (undefined `text` variable)
- Attempt 2 fix A: Added `roman_numeral_with_period` regex pattern to catch "I.", "II.", "III." section markers — CONFIRMED WORKING ✓
- Attempt 2 fix B: Fixed `_are_different_titled_people()` Case 2 to block "Herbert White" as alias of "Mr. White" — CONFIRMED WORKING ✓
- Attempt 2 fix C: Added Rule 1 blocked alias salvage logic for Mrs. White — CONFIRMED WORKING ✓
- Attempt 3 fix: Improved `CHARACTER_IDENTIFICATION_PROMPT` for is_symbolic and role guidance — is_symbolic now True during extraction ✓, but roles still wrong and is_symbolic lost in output
- Attempt 4 fix A: Added Fix EEE-b guard in STEP 3.95 (characters.py) — if summary text identifies character as "their son/daughter FirstName", skip the parent-child split (prevents Herbert White false split)
  - Root cause: LLM assigned "the father" alias to Herbert (from "Herbert's father's army friend" in summary), PLUS "the son" alias (correct), triggering STEP 3.95 alias contradiction split
  - Smoke test: verified guard matches "their son Herbert" in Ch1 summary ✓
- Attempt 4 fix B: Added is_symbolic=getattr(pc, "is_symbolic", False) to OutputCharacter constructor in analyzer.py
  - Root cause: OutputCharacter was built without passing is_symbolic, so it defaulted to False even when the pipeline character had is_symbolic=True

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1→2 | Pipeline crash: summarizer `text` undefined | src/pipeline/summarizer.py | Fixed ✓ |
| 1→2 | Pipeline crash: CharacterMap invalid kwargs | src/analyzer.py | Fixed ✓ |
| 2→3 | Structure: "I.", "II.", "III." not detected | src/pipeline/chapter_detection/proposers/regex.py | Fixed ✓ (9/10) |
| 2→3 | Characters: Herbert White false alias of Mr. White | src/pipeline/character_extraction_v2/main_cast.py | Fixed ✓ |
| 2→3 | Characters: Mrs. White missing (dropped by Rule 1) | src/pipeline/character_extraction_v2/main_cast.py | Fixed ✓ |
| 3→4 | Characters: is_symbolic prompt guidance | src/pipeline/character_extraction_v2/main_cast.py | Partial — is_symbolic True during extraction but lost in output |
| 3→4 | Characters: role classification prompt | src/pipeline/character_extraction_v2/main_cast.py | No change — roles still wrong |
| 4→5 | Characters: Herbert White false split | src/agents/characters.py | Fixed ✓ — Fix EEE-b guard added |
| 4→5 | Characters: is_symbolic lost in output | src/analyzer.py | Fixed ✓ — is_symbolic now passed to OutputCharacter |
| 4→5 | Profiles: Morris missing friend relationship | src/pipeline/post_corrections.py (likely) | Pending |

## Configuration Notes
- Model: qwen3-next:80b-a3b-instruct-q8_0 (Ollama) for all agents
- think_mode: false (correct for qwen3 family)
- Temperature: 0.7 across all agents — may be too high for character extraction (consider 0.3-0.5)
- No profiling quality concerns (0 retries across all stages)
- Profile generation took 446s (7.4 min) — most expensive stage

## Output Files (Attempt 4)
- HTML: ../output/monkeys_paw/report.html
- JSON: ../output/monkeys_paw/analysis.json

## Next Action
Re-run analysis (PROMPT_analyze.md) to verify fixes:
- Herbert White false split should be gone (single Herbert, no "the father" label)
- monkey's paw is_symbolic should be True in final output
- Mrs. White→Herbert "daughter" relationship may self-resolve with Herbert split fixed
- Morris relationships may improve with profile regeneration
