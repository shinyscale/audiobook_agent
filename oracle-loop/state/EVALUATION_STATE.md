# Current Evaluation State

## Active Text
- **Name:** monkeys_paw
- **Attempt:** 8
- **Phase:** awaiting_fix
- **baseline_score: 5.8**

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 8/10 ✓
  - Completeness: 9/10
  - Identity Resolution: 8/10
  - Alias Grouping: 7.5/10
- Character Profiles: 7.5/10 ✗ (FAILING — sole blocker)
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 8/10 ✓
- **Overall: 8.33/10** (reference only)

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
| 7 | 8.30 | +2.50 | Morris↔Mr. White "friend" FIXED ✓ — but parent-child relationships ALL WRONG (LLM non-determinism regression) |
| 8 | 8.33 | +2.53 | Parent-child fix WORKED ✓ — White family relationships all correct. Two new issues: (a) Morris "friend" REGRESSED (evidence not produced this run), (b) Mr. White→paw "son" nonsensical label |

## What Changed (Attempt 7 → 8)

- **FIX WORKED**: `_restore_evidence_based_labels()` successfully restored ALL White family parent-child relationships:
  - Mr. White→Herbert: "father" ✓ (was "brother")
  - Herbert→Mr. White: "son" ✓ (was "brother")
  - Mrs. White→Herbert: "mother" ✓ (was "daughter")
  - Herbert→Mrs. White: "son" ✓ (was "father")
- **REGRESSION**: Morris relationships now EMPTY {} — in attempt 7 he had `{"the monkey's paw": "creation", "Mr. White": "friend"}`. The evidence-based friend restoration can't fire because Morris's evidence items this run don't contain "friend" keyword. This is LLM non-determinism in the profiling stage.
- **NEW ISSUE**: Mr. White→paw: "son", paw→Mr. White: "parent" — completely nonsensical family labels between a human and an object. Likely cause: `verify_relationships_from_text` scanning co-mention windows finds "his son" near "paw" (e.g., "use the paw to bring back his son") and assigns "son" as label.
- **PERSISTENT**: paw aliases include "the stranger" and "the man" — these are the unnamed Maw & Meggins representative in Part II, NOT the paw.
- **PERSISTENT**: All 5 main characters labeled "protagonist"; is_symbolic=False for paw.

## Current Issues (Priority Order)

### CRITICAL
1. **Mr. White → paw "son" and paw → Mr. White "parent" — nonsensical family labels** [Profiles — MAIN BLOCKER]
   - Problem: The monkey's paw is an object, not a family member. "son" and "parent" labels between a human character and a supernatural object are absurd and would confuse a narrator.
   - Evidence: `jq '.characters[] | select(.canonical_name == "Mr. White") | .relationships' analysis.json` → `{"the monkey's paw": "son"}`
   - Root cause: Most likely `verify_relationships_from_text` scans co-mention windows and finds "his son" near "paw" in text like "use the paw to bring back his son". The phrase "his son" refers to Herbert, but the window associates it with the paw.
   - Location: `src/pipeline/character_profiling/post_corrections.py`
   - **Fix approach**: Add a post-correction step (or integrate into `_restore_evidence_based_labels()`) that **clears family labels (father/mother/son/daughter/brother/sister/parent/child) between human characters and non-human entities**. Detection heuristic: if a character's canonical_name starts with "the " + common noun (the monkey's paw, the ring, etc.) AND has no proper noun component, it's a non-human entity. Family labels involving such entities should be cleared to "associated" or removed entirely. This is a universal rule — objects cannot have family relationships.

### HIGH
2. **Morris has EMPTY relationships — "friend" label lost** [Profiles]
   - Problem: In attempt 7, Morris had `{"Mr. White": "friend"}` (correctly restored by evidence-based restoration). In attempt 8, Morris's evidence items don't contain "friend" keyword, so the restoration can't fire.
   - Evidence: Morris's 7 evidence items this run: none mention "friend" or relationship to Mr. White as friend.
   - Root cause: LLM non-determinism in profiling stage — different evidence text produced each run.
   - Location: `src/pipeline/character_profiling/post_corrections.py` — `_restore_evidence_based_labels()`
   - **Fix approach**: Extend the evidence-based restoration to also scan **summary text** (not just evidence arrays) for friend patterns. The summaries consistently describe Morris visiting the White family and sharing drinks/stories — a co-mention of Morris + Mr. White near friendship-indicating words ("old friend", "visits", "guest") in summaries should trigger "friend" label restoration. This is more resilient than depending on the profiler's evidence arrays.
   - **Alternative simpler approach**: In `_restore_evidence_based_labels()`, also check the character's description text (not just evidence) for friend keywords. Morris's description mentions him visiting the Whites.

### MEDIUM
3. **Paw aliases "the stranger" and "the man" are wrong** [Character Extraction — Alias Grouping]
   - Problem: In Part II, "the stranger" and "the man" refer to the unnamed Maw & Meggins representative, not the monkey's paw.
   - Location: V2 character extraction alias resolution
   - Fix: Lower priority — would require changes to alias detection. The paw's other aliases ("the paw") are correct.

4. **All 5 main characters labeled "protagonist"** [Extraction/Profiles]
   - Morris should be "supporting", paw should be "antagonist". Low impact.

5. **is_symbolic=False for monkey's paw** [Extraction metadata]
   - Persistent across attempts. Low impact.

### LOW
6. **Ch3 character tags show aliases alongside canonical names** [Presentation]
7. **fakir/fakirs listed separately** [Pronunciation]
8. **narrative_style is null** [Metadata]

## Fix Priority for Attempt 9

**TWO FIXES NEEDED** (both in `post_corrections.py`):

### Fix A: Clear nonsensical family labels between humans and objects (CRITICAL #1)

Add a cleanup step that runs after `_restore_evidence_based_labels()` and before `_propagate_missing_reverses()`:

```python
def _clear_object_family_labels(self, characters):
    """Clear family labels between human characters and non-human entities.
    Objects (the monkey's paw, the ring, etc.) cannot have family relationships."""
    FAMILY_LABELS = {"father", "mother", "son", "daughter", "brother", "sister",
                     "parent", "child", "husband", "wife"}
    # Detect non-human entities: canonical name is "the X" with no proper noun
    object_names = set()
    for char in characters:
        name = char.get("canonical_name", "") if isinstance(char, dict) else getattr(char, "canonical_name", "")
        # "the monkey's paw", "the paw" etc — starts with "the " + no uppercase word after
        words = name.split()
        if len(words) >= 2 and words[0].lower() == "the" and not any(w[0].isupper() for w in words[1:]):
            object_names.add(name)
    
    for char in characters:
        rels = char.get("relationships", {}) if isinstance(char, dict) else getattr(char, "relationships", {})
        char_name = char.get("canonical_name", "") if isinstance(char, dict) else getattr(char, "canonical_name", "")
        for target, label in list(rels.items()):
            if label.lower() in FAMILY_LABELS:
                if char_name in object_names or target in object_names:
                    rels[target] = "associated"  # or del rels[target]
```

### Fix B: Extend friend restoration to check summaries (HIGH #2)

In `_restore_evidence_based_labels()`, after checking evidence arrays for "friend" keywords, ALSO check whether the chapter summaries mention both characters near friendship-indicating words. The summaries are deterministic (produced in an earlier stage) and consistently describe Morris visiting the Whites.

**Implementation hint**: The summary text is available in the pipeline context. Scan for co-mentions of Morris + Mr. White within 200 chars where words like "friend", "old friend", "guest", "visits" appear nearby.

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
- Attempt 8 fix: Extended `_restore_evidence_based_labels()` to restore parent-child from evidence — CONFIRMED WORKING ✓ (all White family labels correct). But Morris "friend" regressed (evidence didn't contain "friend" this run) and new "Mr. White→paw: son" appeared.

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
| 7→8 | Profiles: Parent-child relationships ALL wrong | src/pipeline/character_profiling/post_corrections.py | **FIXED ✓** — Extended evidence-based restoration to cover family labels |
| 8→9 | Profiles: Mr. White→paw "son" nonsensical | src/pipeline/character_profiling/post_corrections.py | Pending — add _clear_object_family_labels() |
| 8→9 | Profiles: Morris "friend" regressed | src/pipeline/character_profiling/post_corrections.py | Pending — extend friend restoration to check summaries |

**PATTERN NOTE**: post_corrections.py is the correct file for these fixes. Fix A (_clear_object_family_labels) is a new universal invariant. Fix B (summary-based friend restoration) extends the proven evidence-based approach. Same file, consistent pattern — NOT a stuck loop.

## Configuration Notes
- Model: qwen3-next:80b-a3b-instruct-q8_0 (Ollama) for all agents
- think_mode: false (correct for qwen3 family)
- Temperature: 0.7 across all agents
- No profiling quality concerns (0 retries across all stages)

## Output Files (Attempt 8)
- HTML: ../output/monkeys_paw/report.html
- JSON: ../output/monkeys_paw/analysis.json

## Next Action
Run PROMPT_fix.md to address: (A) nonsensical object-family labels, (B) Morris "friend" regression.
