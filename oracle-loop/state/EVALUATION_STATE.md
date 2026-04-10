# Current Evaluation State

## Active Text
- **Name:** monkeys_paw
- **Attempt:** 3
- **Phase:** awaiting_fix
- **baseline_score: 5.8**

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 7.5/10 ✗
  - Completeness: 8.5/10
  - Identity Resolution: 7/10
  - Alias Grouping: 7/10
- Character Profiles: 7.5/10 ✗
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 8.25/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold: Character Extraction, Character Profiles)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | FAIL | - | Pipeline crashed |
| 2 | 5.8 | - | First successful run — baseline set |
| 3 | 8.25 | +2.45 | Structure fixed, characters much improved, 2 categories still below 8.0 |

## Current Issues (Priority Order)

### CRITICAL

1. **"the stranger" and "the visitor" falsely aliased to the monkey's paw** [Identity Resolution, Alias Grouping]
   - Problem: The monkey's paw (main_cast_5) has aliases `["the paw", "the stranger", "the visitor"]`. "The stranger" and "the visitor" in Part II refer to the Maw and Meggins representative who delivers news of Herbert's death — a human character, not the paw.
   - Evidence: Chapter 2 summary explicitly says "the arrival of a well-dressed stranger" who is "representing the firm 'Maw and Meggins'". The stranger is the company representative, not the supernatural object.
   - Location: V2 alias resolution — the LLM proposed these aliases and the pipeline accepted them. The core issue is that human-descriptor aliases ("stranger", "visitor", "man") should not be assigned to non-human/symbolic entities.
   - Fix approach: This needs a rule in `src/pipeline/character_extraction_v2/main_cast.py` (verify_aliases or a post-verification check): if the canonical character is a non-human entity (object, force, symbolic — detectable by lack of human names, or by `is_symbolic=True`), then aliases that are clearly human descriptors (stranger, visitor, man, woman, figure, gentleman, etc.) should be blocked. Alternatively, since the stranger already maps to Maw and Meggins contextually, the pipeline could recognize that "the stranger" appears in summaries where "Maw and Meggins" is the active entity and block the alias.

### HIGH

2. **Sergeant-Major Morris missing "friend" relationship to Mr. White** [Profiles]
   - Problem: Morris has `"relationships": {}` — zero relationships. The text explicitly establishes him as "his old friend the sergeant-major" (Mr. White's old friend).
   - Evidence: Part I: Morris arrives as an old friend of Mr. White; they share whiskey and stories. The summary correctly says "Sergeant-Major Morris arrives."
   - Location: Profile generation in `src/analyzer.py` — `_generate_character_profile()`. The relationship extraction likely missed the "old friend" reference because Morris appears in only one section.
   - Fix: May be a profiler LLM issue (relationship not extracted from text). Could also be a post-corrections issue where `reject_unfounded_friend_labels` is too aggressive and removed a legitimate "friend" label.

3. **All characters classified as "protagonist"** [Profiles]
   - Problem: Every character including Morris, the monkey's paw, and Maw and Meggins has `role: "protagonist"`. Morris is a supporting catalyst, the monkey's paw is an antagonistic force/object, and Maw and Meggins is a minor supporting entity.
   - Evidence: `jq '.characters[].role' analysis.json` → all return "protagonist"
   - Location: Role assignment in V2 character extraction pipeline or profiling.
   - Fix: Role classification should distinguish protagonist (Mr./Mrs. White, Herbert) from supporting (Morris, Maw and Meggins) and antagonist (the monkey's paw). This may be an LLM prompt issue in role assignment.

4. **monkey's paw `is_symbolic` should be `true`** [Identity Resolution]
   - Problem: `is_symbolic: false` for the monkey's paw. It is a supernatural object/force, not a regular character. Marking it symbolic would help downstream logic (e.g., blocking human-descriptor aliases).
   - Evidence: The paw is explicitly described as "a mummified talisman enchanted by a fakir."
   - Location: V2 character extraction — symbolic entity detection.
   - Fix: The pipeline's symbolic detection criteria may not fire for named objects. If it checked for non-human canonical names (object nouns like "paw", "ring", "clock"), it could set `is_symbolic=True`.

### MEDIUM

5. **Chapter 3 character list shows aliases alongside canonical names** [Presentation]
   - Problem: Ch3 characters listed as: "the old man", "the old woman", "Mr. White". "The old man" is an alias of Mr. White (so Mr. White appears twice under different names), and "the old woman" is Mrs. White's alias but "Mrs. White" doesn't appear.
   - Evidence: HTML report lines 914-924 show the Ch3 character tags.
   - Location: Summary → character mapping in `src/analyzer.py` or HTML template generation. The summarizer used descriptors instead of canonical names in Ch3, and the pipeline didn't resolve them back.
   - Fix: When building chapter character lists, resolve aliases to canonical names and deduplicate.

6. **rubicund IPA stress incorrect** [Pronunciation]
   - Problem: Listed as /ruːˈbɪkʌnd/ (stress on 2nd syllable) but standard pronunciation is /ˈruː.bɪ.kənd/ (stress on 1st syllable).
   - Location: LLM-generated IPA in pronunciation enricher.
   - Fix: Add "rubicund" to `KNOWN_IRREGULAR_IPA` in `src/pipeline/pronunciation/enricher.py` with correct IPA /ˈruː.bɪ.kənd/.

7. **fakir/fakirs listed as separate entries with inconsistent IPA** [Pronunciation]
   - Problem: "fakir" → /fəˈkɪər/ and "fakirs" → /ˈfɑː.kɪrz/. Different vowel patterns for the same root word, and the plural is redundant.
   - Location: Pronunciation deduplication logic.
   - Fix: Deduplicate singular/plural forms; use consistent IPA (standard: /fəˈkɪər/).

### LOW

8. **narrative_style is null** [Profiles]
   - Problem: `narrative_style: null` instead of "third-person" or "third-person omniscient". Correct detection but null representation.
   - Location: Narrator detection in `src/analyzer.py`.

9. **"Chapters have descriptive titles" label** [Presentation]
   - Problem: HTML says "Chapters have descriptive titles" but "I.", "II.", "III." are Roman numeral markers, not descriptive titles.
   - Location: HTML template generation logic that classifies title types.

## Fix History
- Attempt 1 fix: Fixed two crash-level bugs in analyzer.py (CharacterMap constructor) and summarizer.py (undefined `text` variable)
- Attempt 2 fix A: Added `roman_numeral_with_period` regex pattern to catch "I.", "II.", "III." section markers — CONFIRMED WORKING ✓
- Attempt 2 fix B: Fixed `_are_different_titled_people()` Case 2 to block "Herbert White" as alias of "Mr. White" — CONFIRMED WORKING ✓
- Attempt 2 fix C: Added Rule 1 blocked alias salvage logic for Mrs. White — CONFIRMED WORKING ✓

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1→2 | Pipeline crash: summarizer `text` undefined | src/pipeline/summarizer.py | Fixed ✓ |
| 1→2 | Pipeline crash: CharacterMap invalid kwargs | src/analyzer.py | Fixed ✓ |
| 2→3 | Structure: "I.", "II.", "III." not detected | src/pipeline/chapter_detection/proposers/regex.py | Fixed ✓ (9/10) |
| 2→3 | Characters: Herbert White false alias of Mr. White | src/pipeline/character_extraction_v2/main_cast.py | Fixed ✓ |
| 2→3 | Characters: Mrs. White missing (dropped by Rule 1) | src/pipeline/character_extraction_v2/main_cast.py | Fixed ✓ |

## What Improved (Attempt 2 → 3)
- Structure: 5/10 → 9/10 (3 parts correctly detected)
- Characters: 4/10 → 7.5/10 (Mrs. White present, Herbert separated, Morris has full title)
- Profiles: 5/10 → 7.5/10 (family relationships now correct)
- Summaries: 7/10 → 9/10 (per-section summaries instead of single block)
- Overall: 5.8/10 → 8.25/10

## Configuration Notes
- Model: qwen3-next:80b-a3b-instruct-q8_0 (Ollama) for all agents
- think_mode: false (correct for qwen3 family)
- Temperature: 0.7 across all agents — may be too high for character extraction (consider 0.3-0.5)
- No profiling quality concerns (0 retries, 0 JSON parse failures, all HIGH confidence)
- Profile generation took 526s (8.7 min) — most expensive stage

## Output Files (Attempt 3)
- HTML: ../output/monkeys_paw/report.html
- JSON: ../output/monkeys_paw/analysis.json

## Next Action
Run PROMPT_fix.md to address:
1. CRITICAL: Remove "the stranger"/"the visitor" from monkey's paw aliases (false human-descriptor aliases on non-human entity)
2. HIGH: Morris missing "friend" relationship to Mr. White
3. HIGH: Role classification — not everything should be "protagonist"
Focus on #1 (character extraction → 8.0) and #2 (profiles → 8.0) as minimum to pass.
