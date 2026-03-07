# Current Evaluation State

## Active Text
- **Name:** john_g
- **Attempt:** 3
- **Phase:** awaiting_fix
- **baseline_score:** 7.80

## Output Files
- HTML: ../output/john_g/report.html
- JSON: ../output/john_g/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 8/10 ✓
  - Completeness: 8/10
  - Identity Resolution: 10/10
  - Alias Grouping: 7.5/10
- Character Profiles: 7.5/10 ✗
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 7.5/10 ✗
- HTML Presentation: 8.5/10 ✓
- **Overall: 8.33/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold: Profiles, Pronunciation)

## Current Issues (Priority Order)

### CRITICAL
(None)

### HIGH
1. **2 pronunciation entries still have null IPA despite KNOWN_IRREGULAR_IPA fixes** [Pronunciation]
   - Problem: "sharp-fanged" and "bolo-toothed" both have `ipa: null` in the output. These were added to KNOWN_IRREGULAR_IPA in attempts 2 and 3 respectively, and __pycache__ was cleared before the attempt 3 run, yet the output still has null IPA.
   - Evidence: `jq '.pronunciations[] | select(.ipa == null) | .word' analysis.json` returns "bolo-toothed" and "sharp-fanged". Meanwhile "produce" (added to HOMOGRAPH_IPA_MAP in attempt 3) now correctly has IPA — so the HOMOGRAPH path works but the KNOWN_IRREGULAR_IPA path does not.
   - Location: `src/pipeline/pronunciation_guide/enricher.py` — the `enrich_batch()` or `enrich_single()` static lookup for KNOWN_IRREGULAR_IPA. The lookup may be case-sensitive or hyphenated-word matching may fail. Or: the batch enrichment error fallback (which creates empty `PronunciationEnrichment(confidence=0.0)` entries) may be overwriting the static result.
   - Fix: Debug the enrichment code path for hyphenated words. Check if `enrich_batch()` processes KNOWN_IRREGULAR_IPA lookups BEFORE the LLM call, and whether the LLM error fallback overwrites the result. The fix for "produce" (HOMOGRAPH_IPA_MAP) works via a separate `enrich_homograph()` path that may not have the same overwrite bug. Add debug logging or directly trace the code path for "sharp-fanged" to find where the IPA gets dropped.

2. **Richardson missing speech_patterns "soft Southern tongue"** [Profiles]
   - Problem: Richardson now has HIGH confidence (was LOW/0.30 in attempt 2), so the LLM did generate a profile — but `speech_patterns` is still null. The LLM simply didn't extract this detail.
   - Evidence: Text explicitly says "rejoined Corporal Richardson, in his soft Southern tongue". Profile has HIGH confidence but null speech_patterns.
   - Location: `analyzer.py` (`_generate_character_profile`) — the profile prompt may not emphasize speech patterns enough, or the LLM response schema doesn't require it.
   - Fix: Two options: (a) Add a post-profile text scan for explicit speech pattern phrases like "in his/her [adjective] tongue/voice/accent/drawl" and inject them into the profile. This is more reliable than hoping the LLM extracts it. (b) Add "speech_patterns" as a required field in the profile prompt with an example. Option (a) is more robust — a regex scan for `in (his|her) (\w+ )+?(tongue|voice|accent|drawl|manner of speaking)` would catch this pattern universally.

3. **Richardson missing Price relationship** [Profiles]
   - Problem: Richardson's relationships only has `{"John G.": "caretaker"}`. The attempt 3 fix added `add_text_window_cooccurrence_relationships` to post_corrections.py, but Richardson→Price "colleague" was NOT added.
   - Evidence: Price→Richardson relationship is also missing. They serve together (Richardson is the farrier under Price's command). The co-occurrence fix either didn't fire or the mention positions didn't overlap within the 600-char window.
   - Location: `src/pipeline/post_corrections.py` — `add_text_window_cooccurrence_relationships`. Possible causes: (a) Richardson and Price mentions may not appear within 600 chars of each other in the source text, (b) the function may not be finding mention positions for these characters, (c) the function may have a bug.
   - Fix: Investigate why the co-occurrence scan didn't find Richardson+Price. The text has them together throughout — they're riding together, crossing the bridge together. Check if the mention search is finding positions for both. If the window is too small, increase it. Or: since Price's relationships already include John G. and Two Troopers (from LLM profiling), and Richardson has John G. (from LLM), the issue is that the LLM profiler doesn't see them as directly related. The co-occurrence fix should handle this.

### MEDIUM
4. **"the Sergeant" alias missing for Price** [Alias Grouping]
   - Problem: "the Sergeant" is used 15+ times in text to refer to Price but not listed as alias.
   - Location: `main_cast.py` — descriptor-blocking rules. Acceptable tradeoff for generic descriptor.

5. **No personality_traits for any character** [Profiles]
   - Problem: All characters have `personality_traits: null`. John G. is described as "plucky", "alert", etc. in physical_description but personality_traits is empty.
   - This is minor — the physical_description field captures some personality aspects already.

### LOW
6. **"John G." self-alias** [Alias Grouping]
   - John G.'s alias list includes "John G." (canonical name as own alias). Minor cosmetic issue.

7. **"Local Power" as character name** [Completeness]
   - "Local Power" is a generic descriptor for a local official, not a proper name. Borderline extraction.

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 7.80 | N/A | First run - 3 categories failing |
| 2 | 8.25 | +0.45 | Characters fixed (8.0), Profiles and Pronunciation still failing |
| 3 | 8.33 | +0.53 | Profiles improved (7→7.5), Pronunciation unchanged (7.5) |

## Fix History
- Attempt 2: Three fixes applied:
  1. **Captain Adams (Completeness)**: Exempted `chapter_summary_reconciliation` characters from evidence filter in `_convert_characters()`. Root cause: `analyzer.py:_convert_characters():4086-4096`.
  2. **Alias grouping (Completeness/Alias)**: Extended `_add_title_stripped_aliases` for multi-word compound ranks ("First Sergeant Price" -> "Price", "Sergeant Price"). Root cause: `main_cast.py:_add_title_stripped_aliases():1320-1330`.
  3. **IPA sharp-fanged (Pronunciation)**: Added to KNOWN_IRREGULAR_IPA with `/ˈʃɑːrp.fæŋd/`. Root cause: `enricher.py:KNOWN_IRREGULAR_IPA`. **NOTE: Fix is in code but IPA is still null in output — enricher may have errored for the batch.**

- Attempt 3: Four fixes applied:
  1. **Pronunciation "bolo-toothed"** (null IPA): Added to KNOWN_IRREGULAR_IPA with `/ˈboʊ.loʊ.tuːθt/`.
  2. **Pronunciation "produce"** (null IPA): Added to HOMOGRAPH_IPA_MAP with both stress variants. **WORKED — produce now has IPA.**
  3. **Pronunciation "sharp-fanged"** (null IPA): Cleared __pycache__. **DID NOT WORK — still null.**
  4. **Richardson missing Price relationship** (Profiles): Added `add_text_window_cooccurrence_relationships` to post_corrections.py. **DID NOT WORK — Richardson still only has John G.**

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 2 | Captain Adams missing | analyzer.py | Fixed |
| 2 | Alias grouping (compound ranks) | main_cast.py | Fixed |
| 2 | IPA sharp-fanged | enricher.py | No change — IPA still null |
| 3 | IPA bolo-toothed | enricher.py | No change — IPA still null |
| 3 | IPA produce | enricher.py (HOMOGRAPH_IPA_MAP) | Fixed |
| 3 | IPA sharp-fanged (__pycache__) | cleared cache | No change — IPA still null |
| 3 | Richardson→Price relationship | post_corrections.py | No change — relationship not added |

**PATTERN DETECTED:** KNOWN_IRREGULAR_IPA lookups are NOT working for hyphenated words (sharp-fanged, bolo-toothed) despite code being present. HOMOGRAPH_IPA_MAP works fine (produce). The fix phase MUST trace the actual code path for KNOWN_IRREGULAR_IPA to find where the value gets dropped — do NOT just add more entries or clear cache again.

**PATTERN DETECTED:** post_corrections.py co-occurrence fix did not produce results. The fix phase must verify the function actually executes and check the mention positions for Richardson and Price.

## Configuration Notes
- Model: qwen3-next:80b-a3b-instruct-q8_0 (all agents)
- Config: max_tokens=8192, context_length=32768, think_mode=false
- Character Profiles: 4H/0M/0L confidence (all HIGH — improved from attempt 2)
- 6 characters total, 4 profiles generated
- 13 pronunciation words flagged
- No pipeline errors (exit code 0)

## Next Action
Run PROMPT_fix.md to address:
1. **PRIORITY 1**: Debug KNOWN_IRREGULAR_IPA code path for hyphenated words (enricher.py) — this has failed 2 attempts, need root cause
2. **PRIORITY 2**: Debug post_corrections.py co-occurrence function — verify it runs and finds mentions
3. **PRIORITY 3**: Add post-profile text scan for explicit speech pattern phrases (Richardson "soft Southern tongue")
