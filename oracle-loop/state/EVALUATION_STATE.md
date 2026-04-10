# Current Evaluation State

## Active Text
- **Name:** monkeys_paw
- **Attempt:** 7
- **Phase:** awaiting_fix
- **baseline_score: 5.8**

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 8.5/10 ✓
  - Completeness: 9/10
  - Identity Resolution: 9.5/10
  - Alias Grouping: 8.5/10
- Character Profiles: 6.5/10 ✗ (FAILING — sole blocker)
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 8/10 ✓
- **Overall: 8.30/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (1 category below threshold: Character Profiles 6.5/10)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | FAIL | - | Pipeline crashed |
| 2 | 5.8 | - | First successful run — baseline set |
| 3 | 8.25 | +2.45 | Structure fixed, characters much improved, 2 categories still below 8.0 |
| 4 | 7.93 | +2.13 | Alias fix worked, but Herbert false split + wrong label appeared |
| 5 | 8.45 | +2.65 | Herbert split FIXED, Mrs. White→Herbert FIXED. Only Profiles still below 8.0 |
| 6 | 8.45 | +2.65 | Fix to _infer_rel + reject_unfounded_friend_labels applied but Morris still has NO "friend" relationship — fix INEFFECTIVE |
| 7 | 8.30 | +2.50 | Morris↔Mr. White "friend" FIXED ✓ — but parent-child relationships ALL WRONG (LLM non-determinism regression) |

## What Changed (Attempt 6 → 7)
- **FIX WORKED**: `_restore_evidence_based_friend_labels()` successfully injected Morris↔Mr. White "friend" relationship. Morris now has `{"the monkey's paw": "creation", "Mr. White": "friend"}` and Mr. White has `{"Sergeant-Major Morris": "friend"}` ✓
- **IMPROVED**: Mr. White physical description no longer contaminated with Morris's features ("beady of eye, rubicund of visage" gone; now correctly shows only "thin grey beard")
- **REGRESSION (LLM non-determinism)**: Parent-child relationships between White family members are ALL WRONG:
  - Mr. White→Herbert: "brother" (should be "father")
  - Herbert→Mr. White: "brother" (should be "son")
  - Mrs. White→Herbert: "daughter" (should be "mother")
  - Herbert→Mrs. White: "father" (should be "son")
- **EVIDENCE SAYS CORRECT THING**: Mr. White evidence: "He is the father of Herbert White". Herbert evidence: "Herbert is the son of Mr. and Mrs. White". The evidence arrays have the right information but the relationship labels in the output are wrong.
- **UNCHANGED**: paw "creation"/"creator" labels still wrong; all characters still "protagonist"; is_symbolic still False

## Root Cause Analysis: Why Parent-Child Relationships Are Wrong

The evidence arrays clearly contain the correct information:
- Mr. White evidence item: "He is the father of Herbert White" (confidence: high)
- Herbert evidence item: "Herbert is the son of Mr. and Mrs. White" (confidence: high)

Yet the final relationship labels are "brother"/"brother" (Mr. White↔Herbert) and "daughter"/"father" (Mrs. White↔Herbert). This is the SAME pattern as the Morris "friend" issue: correct information exists in evidence but is mangled by the post-corrections pipeline chain.

**Most likely failure chain:**
1. `extract_relationships_from_evidence` correctly sets Mr. White→Herbert = "father", Herbert→Mr. White = "son"
2. `verify_relationships_from_text` scans co-mention windows. In the text, Mr. White, Mrs. White, and Herbert are all in the same scenes. Windows containing "his wife", "his old friend", "father and son", "his mother" create competing signals.
3. Some combination of phrase counting, strong-family-evidence logic, or cross-character interference overrides the correct labels with wrong ones.
4. `enforce_gender_consistency` may then swap labels to match character gender (e.g., "sister"→"brother"), producing the observed "brother" labels.
5. The labels survive `reject_unfounded_familial_labels` because family keywords DO exist near the characters in text — just assigned to the wrong relationship type.

**Key insight:** This is the exact same class of problem as Morris's "friend" — the `_restore_evidence_based_friend_labels()` approach WORKS. Extending it to cover parent/child/son/daughter/mother/father keywords will fix this too.

## Current Issues (Priority Order)

### CRITICAL
1. **Parent-child relationships ALL wrong for White family** [Profiles — MAIN BLOCKER]
   - Problem: Mr. White→Herbert: "brother" (should be "father"); Herbert→Mr. White: "brother" (should be "son"); Mrs. White→Herbert: "daughter" (should be "mother"); Herbert→Mrs. White: "father" (should be "son")
   - Evidence: Mr. White evidence says "He is the father of Herbert White"; Herbert evidence says "Herbert is the son of Mr. and Mrs. White" — evidence arrays have correct info
   - Location: `src/pipeline/character_profiling/post_corrections.py` — the verify→reject→clean chain mangles the labels before final output
   - **Fix approach (RECOMMENDED)**: Extend `_restore_evidence_based_friend_labels()` to also restore parent/child relationships from evidence. Rename to `_restore_evidence_based_labels()`. Add parent/child/son/daughter/mother/father vocabulary. When evidence says "X is the father of Y", set X→Y = "father" and Y→X = "son" (with gender awareness: father/mother, son/daughter). This method already runs late in the pipeline (after clean_unknown_relationships, before _propagate_missing_reverses), so it will bypass the chain that mangles the labels.
   - Impact: Fixing this likely pushes Profiles from 6.5 → 8.0+ since the White family dynamics are the core of the story.

### MEDIUM
2. **Morris→monkey's paw "creation" is semantically wrong** [Profiles]
   - Problem: Morris didn't create the paw. A fakir created it. Morris possessed/brought it from India.
   - Location: Evidence mining `_infer_rel()` or `_CREATOR_LABEL_RE` / `_CREATION_LABEL_RE` patterns
   - Fix: Low priority — doesn't significantly impact narrator prep.

3. **All 5 main characters labeled "protagonist"** [Extraction/Profiles]
   - Problem: Morris should be "supporting" (appears only in Part I), paw should be "antagonist".
   - Location: V2 character extraction role assignment
   - Fix: Low priority for this text.

4. **is_symbolic=False for monkey's paw persists** [Extraction metadata]
   - Problem: Despite prior fixes, is_symbolic still False in final output.
   - Location: Character object transformation chain in analyzer.py
   - Fix: Low priority — metadata, not profile accuracy.

### LOW
5. **Ch3 character tags show aliases alongside canonical names** [Presentation]
   - Problem: Ch3 shows "the old man", "the old woman", "Mr. White" — aliases shown as separate tags.
6. **fakir/fakirs listed separately** [Pronunciation]
   - Minor duplication, both have correct IPA.
7. **narrative_style is null** [Metadata]

## Fix Priority for Attempt 8

**ONLY ONE FIX NEEDED**: Extend evidence-based label restoration to cover parent-child relationships (CRITICAL #1).

**Specific implementation:**
1. Rename `_restore_evidence_based_friend_labels()` → `_restore_evidence_based_labels()` (or add family logic to existing method)
2. Add family vocabulary: {"father", "mother", "parent", "son", "daughter", "child"}
3. For each character's evidence array, scan for statements matching pattern: "[character] is the {father|mother|son|daughter} of [other character]"
4. When found, set the correct relationship label with gender awareness:
   - "father of Y" → X→Y = "father", Y→X = "son" (if Y is male) or "daughter" (if Y is female)
   - "son of Y" → X→Y = "son", Y→X = "father" (if Y is male) or "mother" (if Y is female)
   - Use character gender from the character object if available, otherwise infer from names/aliases
5. Override current label if it's absent, "associated", "unknown", or a WRONG family label (e.g., "brother" when evidence says "father")
6. Keep the existing friend restoration logic alongside the new family logic
7. Wire into `run_all()` at same location (already after clean_unknown_relationships, before _propagate_missing_reverses)

**DO NOT attempt fixes for MEDIUM/LOW issues this round.**

## Fix History
- Attempt 1 fix: Fixed two crash-level bugs in analyzer.py (CharacterMap constructor) and summarizer.py (undefined `text` variable)
- Attempt 2 fix A: Added `roman_numeral_with_period` regex pattern to catch "I.", "II.", "III." section markers — CONFIRMED WORKING ✓
- Attempt 2 fix B: Fixed `_are_different_titled_people()` Case 2 to block "Herbert White" as alias of "Mr. White" — CONFIRMED WORKING ✓
- Attempt 2 fix C: Added Rule 1 blocked alias salvage logic for Mrs. White — CONFIRMED WORKING ✓
- Attempt 3 fix: Improved `CHARACTER_IDENTIFICATION_PROMPT` for is_symbolic and role guidance — is_symbolic now True during extraction ✓, but roles still wrong and is_symbolic lost in output
- Attempt 4 fix A: Added Fix EEE-b guard in STEP 3.95 (characters.py) — prevents Herbert White false split — CONFIRMED WORKING ✓
- Attempt 4 fix B: Added is_symbolic=getattr(pc, "is_symbolic", False) to OutputCharacter constructor — NOT WORKING (is_symbolic still False in output)
- Attempt 6 fix: Added `_FRIEND_WORDS` to `_infer_rel` + evidence exception in `reject_unfounded_friend_labels` — NOT WORKING alone (verify_relationships_from_text overrides before they take effect)
- Attempt 7 fix: Added `_restore_evidence_based_friend_labels()` — CONFIRMED WORKING ✓ (Morris↔Mr. White "friend" now present). But parent-child labels regressed due to LLM non-determinism — same pipeline chain mangles family labels too.

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
| 4→5 | Profiles: Mrs. White→Herbert "daughter" | (resolved by Herbert split fix) | Fixed ✓ (attempt 5) but regressed in attempt 7 |
| 5→6 | Profiles: Morris missing "friend" relationship | src/pipeline/character_profiling/post_corrections.py | NOT WORKING — _infer_rel fix + evidence exception correct in isolation, but verify_relationships_from_text overrides |
| 6→7 | Profiles: Morris missing "friend" relationship | src/pipeline/character_profiling/post_corrections.py | **FIXED ✓** — `_restore_evidence_based_friend_labels()` bypasses the pipeline chain |
| 7→? | Profiles: Parent-child relationships ALL wrong | src/pipeline/character_profiling/post_corrections.py | Pending — extend evidence-based restoration to cover family labels |

**PATTERN NOTE**: post_corrections.py `_restore_evidence_based_friend_labels()` approach is PROVEN. Extending it to cover family vocabulary is the natural next step. Same file, same method, same approach — NOT a stuck pattern; this is iterative improvement of a working solution.

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
Run PROMPT_fix.md to extend `_restore_evidence_based_friend_labels()` to also restore parent-child labels from evidence arrays.
