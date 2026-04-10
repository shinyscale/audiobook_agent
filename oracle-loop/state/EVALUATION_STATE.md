# Current Evaluation State

## Active Text
- **Name:** monkeys_paw
- **Attempt:** 7
- **Phase:** awaiting_evaluation
- **baseline_score: 5.8**

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 8.5/10 ✓
  - Completeness: 9/10
  - Identity Resolution: 9.5/10
  - Alias Grouping: 8.5/10
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
| 6 | 8.45 | +2.65 | Fix to _infer_rel + reject_unfounded_friend_labels applied but Morris still has NO "friend" relationship — fix INEFFECTIVE |

## What Changed (Attempt 5 → 6)
- **FIX APPLIED BUT INEFFECTIVE**: Added `_FRIEND_WORDS` to `_infer_rel()` and evidence-based exception in `reject_unfounded_friend_labels`. Morris STILL has no "friend" relationship with Mr. White. Relationships dict: `{"monkey's paw": "creation"}`.
- **IMPROVED**: monkey's paw no longer has hallucinated "squatting up on top of the wardrobe" feature — now correctly shows "Shrivelled; dirty; little."
- **UNCHANGED**: All other scores identical to attempt 5.

## Root Cause Analysis: Why the Fix Failed

The fix correctly targets two steps in the pipeline:
1. `_infer_rel()` now returns "friend" for evidence with "friend" words → Morris→Mr. White should get "friend" from `extract_relationships_from_evidence` (line 847)
2. `reject_unfounded_friend_labels` now has evidence-array exception → should keep "friend" even without text proximity

**BUT**: `verify_relationships_from_text` runs at line 869, BETWEEN these two steps. This method scans 500-char co-mention windows for relationship phrases and can OVERRIDE "friend" with a different term.

The most likely failure chain:
1. `extract_relationships_from_evidence` sets Morris→Mr.White = "friend" ✓
2. `verify_relationships_from_text` processes Morris→Mr.White pair:
   - In the Part I scene, Morris, Mr. White, Herbert, and Mrs. White are all present
   - `_all_rel_phrase_re` finds "his old friend" → "friend", but also finds "his wife", "his son", "father" in the same co-mention windows
   - If a family term (e.g., "son", "father") has higher count than "friend", it becomes `best`
   - At line 2221, `_strong_family_evidence` triggers if the family term appears 2+ times
   - No cross-tier guard fires (because "friend" is not in any family tier)
   - Override fires at line 2323: Morris→Mr.White = "father" (or "son" or whatever family term won)
3. `reject_unfounded_familial_labels` strips the hallucinated family label → "acquaintance"
4. `clean_unknown_relationships` removes "acquaintance"
5. `reject_unfounded_friend_labels` never sees "friend" — it was already overwritten in step 2

**Alternative failure path**: If `comention_count == 0` for Morris↔Mr.White (possible if `_build_name_patterns` fails to match hyphenated "Sergeant-Major" in source text), then line 2356 fires and downgrades "friend" to "associated" even without finding any relationship phrases.

## Current Issues (Priority Order)

### HIGH
1. **Sergeant-Major Morris has zero relationships with Mr. White** [Profiles — MAIN BLOCKER]
   - Problem: Morris.relationships = `{"monkey's paw": "creation"}`. No "Mr. White": "friend" despite evidence item ev-4-3 explicitly stating "Is a close friend of Mr. White".
   - Root cause: `verify_relationships_from_text` overrides or removes the "friend" label set by `extract_relationships_from_evidence`. See Root Cause Analysis above.
   - Location: `src/pipeline/character_profiling/post_corrections.py` — `verify_relationships_from_text()` at lines ~2083-2371
   - **Fix approach (NEW — previous approach was insufficient)**:
     - Option A (RECOMMENDED): Add a **late-stage evidence-based friend restoration** pass that runs AFTER `clean_unknown_relationships` (line 902) but BEFORE `_propagate_missing_reverses` (line 908). This new method scans each character's evidence array for "friend" + another character's name. If found and the relationship is missing/empty, it injects "friend". This completely bypasses the verify→reject→clean chain that strips the label.
     - Option B: In `verify_relationships_from_text`, add a guard that prevents overriding "friend" with a family term when the "friend" label originated from evidence mining. Would need a way to tag evidence-sourced labels.
     - Option C: In `verify_relationships_from_text`, when `cur_lower == "friend"` AND `found.get("friend", 0) > 0`, skip the override entirely (friend corroborated by text → keep it). This is simple but may have edge cases.
   - Impact: This is the SOLE issue preventing Character Profiles from reaching 8.0. Fixing it likely pushes profiles to 8.0+.

### MEDIUM
2. **Mr. White has Morris's physical features** [Profiles]
   - Problem: Mr. White's appearance shows "beady of eye, rubicund of visage" — these are Morris's features from the text "followed by a tall, burly man, beady of eye and rubicund of visage" (the tall, burly man is Morris, not Mr. White). Mr. White correctly has "thin grey beard" but the other features are cross-contaminated.
   - Location: Profile generation LLM in `src/analyzer.py` — `_generate_character_profile()` or post_corrections appearance propagation
   - Fix: Low priority — this is a profiler accuracy issue that would require more context-aware extraction.

3. **Morris→monkey's paw "creation" is semantically wrong** [Profiles]
   - Problem: Morris didn't create the paw. He possessed and brought it from India. A fakir created it.
   - Evidence: Text says "It had a spell put on it by an old fakir" — the fakir is the creator, not Morris.
   - Location: Evidence mining `_infer_rel()` or the `_CREATOR_LABEL_RE` / `_CREATION_LABEL_RE` patterns
   - Fix: Low priority — the "creation" label comes from evidence statement "Reveals the monkey's paw as a cursed object..." where the regex may be misinterpreting "cursed object" as a creation relationship.

4. **All 5 main characters labeled "protagonist"** [Extraction/Profiles]
   - Problem: Morris should be "supporting" (appears only in Part I), paw should be "antagonist".
   - Location: V2 character extraction role assignment
   - Fix: Low priority for this text — doesn't affect profile accuracy score.

5. **is_symbolic=False for monkey's paw persists** [Extraction metadata]
   - Problem: Despite prior fixes, is_symbolic still False in final output.
   - Location: Character object transformation chain in analyzer.py
   - Fix: Low priority — metadata, not profile accuracy.

### LOW
6. **Ch3 character tags show aliases alongside canonical names** [Presentation]
   - Problem: Ch3 shows "the old man", "the old woman", "Mr. White" — "the old man" is Mr. White's alias (duplicate).
7. **condoled IPA uses non-standard /ō/** [Pronunciation]
8. **fakir/fakirs listed separately** [Pronunciation]
9. **narrative_style is null** [Metadata]

## Fix Priority for Attempt 7

**ONLY ONE FIX NEEDED**: Morris's missing "friend" relationship with Mr. White (HIGH #1).

**CRITICAL CHANGE FROM PREVIOUS APPROACH**: Do NOT modify `_infer_rel` or `reject_unfounded_friend_labels` further — those fixes are already in place and correct. The problem is that `verify_relationships_from_text` overrides/removes the "friend" label BEFORE `reject_unfounded_friend_labels` can protect it.

**Recommended fix: Late-stage evidence-based friend restoration**
1. Add a new method `_restore_evidence_based_friend_labels(self, characters)` to `OutputCharacterCorrector`
2. For each character, scan evidence array for statements containing "friend" + another character's name
3. If the character has NO relationship (or "associated"/"unknown") with that other character, set it to "friend"
4. Wire this method into `run_all()` AFTER `clean_unknown_relationships` (line 902) and BEFORE `_propagate_missing_reverses` (line 908)
5. This guarantees evidence-based "friend" labels survive the entire correction chain

**DO NOT attempt fixes for MEDIUM/LOW issues this round.**

## Fix History
- Attempt 1 fix: Fixed two crash-level bugs in analyzer.py (CharacterMap constructor) and summarizer.py (undefined `text` variable)
- Attempt 2 fix A: Added `roman_numeral_with_period` regex pattern to catch "I.", "II.", "III." section markers — CONFIRMED WORKING ✓
- Attempt 2 fix B: Fixed `_are_different_titled_people()` Case 2 to block "Herbert White" as alias of "Mr. White" — CONFIRMED WORKING ✓
- Attempt 2 fix C: Added Rule 1 blocked alias salvage logic for Mrs. White — CONFIRMED WORKING ✓
- Attempt 3 fix: Improved `CHARACTER_IDENTIFICATION_PROMPT` for is_symbolic and role guidance — is_symbolic now True during extraction ✓, but roles still wrong and is_symbolic lost in output
- Attempt 4 fix A: Added Fix EEE-b guard in STEP 3.95 (characters.py) — prevents Herbert White false split — CONFIRMED WORKING ✓
- Attempt 4 fix B: Added is_symbolic=getattr(pc, "is_symbolic", False) to OutputCharacter constructor — NOT WORKING (is_symbolic still False in output)
- Attempt 6 fix: Added `_FRIEND_WORDS` to `_infer_rel` + evidence exception in `reject_unfounded_friend_labels` — **NOT WORKING** (Morris still has empty friendship). Root cause: `verify_relationships_from_text` overrides the "friend" label before the evidence exception can protect it.
- Attempt 7 fix: Added `_restore_evidence_based_friend_labels()` to `OutputCharacterCorrector`. Runs in `run_all()` AFTER `clean_unknown_relationships` and BEFORE `_propagate_missing_reverses`. Scans each character's evidence array for "friend" vocabulary co-occurring with another character's name; if the relationship is currently absent/generic, injects "friend". This bypasses the verify→reject→clean chain that was stripping the label. `_propagate_missing_reverses` then symmetrically adds Mr.White→Morris: "friend".

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
| 5→6 | Profiles: Morris missing "friend" relationship | src/pipeline/character_profiling/post_corrections.py | **NOT WORKING** — _infer_rel fix + evidence exception correct in isolation, but verify_relationships_from_text overrides before they take effect |

**STUCK PATTERN ALERT**: post_corrections.py has been modified for Morris's "friend" once without success. The fix phase modified the WRONG methods — _infer_rel and reject_unfounded_friend_labels are downstream/upstream of the actual blocker (verify_relationships_from_text). Next fix MUST target a different code path (late-stage restoration) or the correct method (verify_relationships_from_text itself).

## Configuration Notes
- Model: qwen3-next:80b-a3b-instruct-q8_0 (Ollama) for all agents
- think_mode: false (correct for qwen3 family)
- Temperature: 0.7 across all agents
- No profiling quality concerns (0 retries across all stages)

## Output Files (Attempt 7)
- HTML: ../output/monkeys_paw/report.html
- JSON: ../output/monkeys_paw/analysis.json

## Pipeline Notes (Attempt 7)
- Completed in 18m 17s, 5 characters found (Mr. White, Mrs. White, Herbert White, Sergeant-Major Morris, monkey's paw)
- Non-fatal warnings: LLM marker proposer returned non-list (x2); Step 6.95 narrator fix skipped (method missing)
- No crashes or blocking errors

## Next Action
Run PROMPT_fix.md to add late-stage evidence-based friend restoration in post_corrections.py run_all()
