# Current Evaluation State

## Active Text
- **Name:** monkeys_paw
- **Attempt:** 5
- **Phase:** awaiting_analysis
- **baseline_score: 5.8**

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 8.5/10 ✓
  - Completeness: 9/10
  - Identity Resolution: 9.5/10 ← Herbert false split FIXED!
  - Alias Grouping: 8/10
- Character Profiles: 7.5/10 ✗ (FAILING — sole blocker)
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 8/10 ✓
- **Overall: 8.45/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (1 category below threshold: Character Profiles 7.5/10)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | FAIL | - | Pipeline crashed |
| 2 | 5.8 | - | First successful run — baseline set |
| 3 | 8.25 | +2.45 | Structure fixed, characters much improved, 2 categories still below 8.0 |
| 4 | 7.93 | +2.13 | Alias fix worked, but Herbert false split + wrong label appeared |
| 5 | 8.45 | +2.65 | Herbert split FIXED, Mrs. White→Herbert FIXED. Only Profiles still below 8.0 |

## What Changed (Attempt 4 → 5)
- **FIXED**: Herbert White false split is GONE — single entry (main_cast_2, 29 mentions) ✓
- **FIXED**: Mrs. White → Herbert relationship now correctly "mother" (was "daughter") ✓
- **NOT FIXED**: is_symbolic still False for monkey's paw — the OutputCharacter fix was applied but extraction pipeline may not be setting is_symbolic=True on the character object before serialization
- **NOT FIXED**: Morris still has zero relationships — `reject_unfounded_friend_labels` or profiler still not generating "friend" label
- **NOT FIXED**: All 5 characters still labeled "protagonist"

## Current Issues (Priority Order)

### HIGH
1. **Sergeant-Major Morris has zero relationships** [Profiles — MAIN BLOCKER]
   - Problem: Morris has `"relationships": {}`. The text explicitly says he is "his old friend the sergeant-major" — Mr. White's old friend. Evidence item ev-4-1 in the HTML correctly states "Is an old friend of Mr. White" but this fact isn't in the relationships dict.
   - Evidence: Part I: "His old friend the sergeant-major" and they share whiskey and war stories. The friendship is one of the most explicitly stated relationships in the text.
   - Location: Either (a) `_generate_character_profile()` in `src/analyzer.py` never generated the "friend" label for Morris, or (b) `reject_unfounded_friend_labels` in `src/pipeline/post_corrections.py` stripped it.
   - Diagnosis path: Check if the profiler generated "friend" but post-corrections removed it. The `reject_unfounded_friend_labels` method requires both character names + "friend" within 150 chars in source text. "His old friend the sergeant-major" has "friend" near "sergeant-major" but may not have "Mr. White" within 150 chars — it's attributed via "his" (possessive pronoun). The window check may fail because it looks for the literal name string.
   - Fix options: (a) If `reject_unfounded_friend_labels` is stripping it: widen the window or exempt cases where "friend" appears in a character's introduction sentence. (b) If the profiler never generated it: check the profile generation prompt. (c) Simplest: in `reject_unfounded_friend_labels`, consider that possessive pronouns ("his old friend") in the context of one character's scene establish friendship even without the literal name string nearby.
   - Impact: This is the SOLE issue preventing Character Profiles from reaching 8.0. Fixing this one issue likely pushes profiles to 8.0+.

### MEDIUM
2. **is_symbolic=False for monkey's paw persists** [Extraction metadata]
   - Problem: Despite the attempt 4 fix adding `is_symbolic=getattr(pc, "is_symbolic", False)` to OutputCharacter, the final JSON shows `is_symbolic: false`.
   - Evidence: Pipeline notes from attempt 5 say extraction had correct is_symbolic behavior (Rule 0.5 fired), but final output is still false.
   - Location: The chain is: extraction (characters.py) → profiling (analyzer.py) → OutputCharacter → JSON. The extraction may set is_symbolic=True but something resets it before OutputCharacter sees it, OR the pipeline character object doesn't have is_symbolic attribute at all (getattr default=False).
   - Fix: Add debug logging OR trace the character object from extraction through profiling to see where is_symbolic is lost. The most likely cause: the Character/MainCastProfile dataclass doesn't persist is_symbolic through all intermediate transformations in analyzer.py.
   - Impact: Minor for scoring — is_symbolic is metadata, not a profile accuracy issue. But it's been 2 attempts without fix, suggesting a deeper pipeline issue.

3. **All 5 characters labeled "protagonist"** [Extraction/Profiles]
   - Problem: Morris (`role: "protagonist"`) should be "supporting" — he appears only in Part I as a catalyst. The monkey's paw (`role: "protagonist"`) should be "antagonist" — it's the supernatural force causing harm.
   - Evidence: Morris delivers the paw and leaves. The paw grants wishes with twisted consequences. Mr. and Mrs. White are the actual protagonists.
   - Location: V2 character extraction role assignment in `src/pipeline/character_extraction_v2/main_cast.py` — the LLM prompt was updated in attempt 3 but the LLM consistently defaults to "protagonist" for all characters in a short story.
   - Fix: Consider a post-extraction role heuristic: (a) characters appearing in only 1 of N sections → "supporting", (b) is_symbolic=True entities with no dialogue → "antagonist" or "symbolic". Or: use a separate focused LLM call for role assignment with stronger prompting.
   - Impact: Medium — incorrect roles reduce narrator prep value but don't create factual errors.

4. **monkey's paw features include hallucinated detail** [Profiles]
   - Problem: Physical features list includes "squatting up on top of the wardrobe" — this is from Herbert's joke ("something horrible squatting up on top of the wardrobe watching you"), not a description of the paw itself. The paw never sits on a wardrobe.
   - Evidence: Herbert's quote is clearly humorous speculation about what the wish might summon, not a physical description of the paw.
   - Location: Profile generation LLM in `src/analyzer.py` — `_generate_character_profile()`.
   - Fix: Low priority — the profiler LLM misattributed a quote as a physical description.

### LOW
5. **Chapter 3 character tags show aliases alongside canonical names** [Presentation]
   - Problem: Ch3 characters: "the old man", "the old woman", "Mr. White" — "the old man" is Mr. White's alias (appears twice under different names), "the old woman" is Mrs. White's alias (but "Mrs. White" doesn't appear).
   - Location: Chapter-to-character mapping in `src/analyzer.py` or HTML template.
   - Fix: When building chapter character lists, resolve aliases to canonical names and deduplicate.

6. **condoled IPA uses non-standard symbol** [Pronunciation]
   - Problem: /kənˈdōld/ uses /ō/ which is not standard IPA (should be /oʊ/ or /əʊ/).
   - Location: LLM pronunciation output normalization.

7. **fakir/fakirs listed separately** [Pronunciation]
   - Problem: Two entries for singular/plural with slightly different base vowel patterns.
   - Location: Pronunciation deduplication logic.

8. **narrative_style is null** [Metadata]
   - Problem: `narrative_style: null` instead of "third-person omniscient".
   - Location: Narrator detection in `src/analyzer.py`.

## Fix Priority for Attempt 6

**ONLY ONE FIX NEEDED**: Morris's missing "friend" relationship with Mr. White (HIGH #1). This is the sole blocker preventing Character Profiles from reaching 8.0, which is the ONLY failing category. All other categories are at or above 8.0.

Fix approach:
1. First diagnose: is the profiler generating a "friend" label that gets stripped by `reject_unfounded_friend_labels`? Or does the profiler never generate it?
2. If stripped by post-corrections: the window check for "his old friend the sergeant-major" likely fails because it searches for the literal name "Mr. White" near "friend", but the text uses "his" (possessive pronoun) — the name isn't nearby.
3. Most targeted fix: In `reject_unfounded_friend_labels`, when checking evidence for a "friend" label, also accept cases where "friend" appears in a character's descriptive introduction (e.g., "his old friend the sergeant-major") even without the other character's name within 150 chars. The possessive "his" establishes the relationship in context.

**DO NOT attempt fixes for MEDIUM/LOW issues this round** — we're at 8.45 overall with only 0.5 points needed on profiles. One surgical fix is all that's needed.

## Fix History
- Attempt 1 fix: Fixed two crash-level bugs in analyzer.py (CharacterMap constructor) and summarizer.py (undefined `text` variable)
- Attempt 2 fix A: Added `roman_numeral_with_period` regex pattern to catch "I.", "II.", "III." section markers — CONFIRMED WORKING ✓
- Attempt 2 fix B: Fixed `_are_different_titled_people()` Case 2 to block "Herbert White" as alias of "Mr. White" — CONFIRMED WORKING ✓
- Attempt 2 fix C: Added Rule 1 blocked alias salvage logic for Mrs. White — CONFIRMED WORKING ✓
- Attempt 3 fix: Improved `CHARACTER_IDENTIFICATION_PROMPT` for is_symbolic and role guidance — is_symbolic now True during extraction ✓, but roles still wrong and is_symbolic lost in output
- Attempt 4 fix A: Added Fix EEE-b guard in STEP 3.95 (characters.py) — prevents Herbert White false split — CONFIRMED WORKING ✓
- Attempt 4 fix B: Added is_symbolic=getattr(pc, "is_symbolic", False) to OutputCharacter constructor — NOT WORKING (is_symbolic still False in output)
- Attempt 6 fix: Added "friend" to `_infer_rel()` in `extract_relationships_from_evidence` + evidence-based exception in `reject_unfounded_friend_labels`
  - Root cause: `_infer_rel()` returned "associated" for "Is an old friend of Mr. White" (no "friend" in any word set), then `clean_unknown_relationships` removed "associated" → empty {}
  - Fix 1: Added `_FRIEND_WORDS` frozenset to `_infer_rel` so evidence statements with "friend" produce the "friend" relationship label
  - Fix 2: In `reject_unfounded_friend_labels`, added evidence-array exception: if char's evidence contains a statement with "friend" + other char's name, keep the label (trust LLM evidence over proximity heuristic)
  - Smoke test: All 381 tests pass (pre-existing test_no_complex_merge_heuristics failure confirmed unrelated)

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
| 4→5 | Characters: is_symbolic lost in output | src/analyzer.py | No change — is_symbolic still False |
| 4→5 | Profiles: Mrs. White→Herbert "daughter" | (resolved by Herbert split fix) | Fixed ✓ |
| 4→5 | Profiles: Morris missing friend relationship | (not addressed) | Still broken |
| 5→6 | Profiles: Morris missing "friend" relationship | src/pipeline/character_profiling/post_corrections.py | Applied fix — awaiting verification |

## Configuration Notes
- Model: qwen3-next:80b-a3b-instruct-q8_0 (Ollama) for all agents
- think_mode: false (correct for qwen3 family)
- Temperature: 0.7 across all agents
- No profiling quality concerns (0 retries across all stages)

## Output Files (Attempt 5)
- HTML: ../output/monkeys_paw/report.html
- JSON: ../output/monkeys_paw/analysis.json

## Next Action
Run PROMPT_analyze.md — re-analyze monkeys_paw to verify Morris now has "friend" relationship with Mr. White
