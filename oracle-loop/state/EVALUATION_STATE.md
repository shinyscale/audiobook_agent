# Current Evaluation State

## Active Text
- **Name:** monkeys_paw
- **Attempt:** 11
- **Phase:** awaiting_fix
- **baseline_score:** 6.275

## Latest Scores

- Structure Detection: 9/10
- Character Extraction: 5/10 ← FAILING
- Character Profiles: 6/10
- Chapter Summaries: 8/10
- Pronunciation Guide: 4/10 ← FAILING
- HTML Presentation: 9/10
- **Overall: 6.70/10** (threshold: 8.0)

## Score Calculation

```
Overall = (9 × 0.20) + (5 × 0.25) + (6 × 0.15) + (8 × 0.20) + (4 × 0.10) + (9 × 0.10)
        = 1.80 + 1.25 + 0.90 + 1.60 + 0.40 + 0.90
        = 6.85/10
```

Adjusted to 6.70 due to critical regression (fix didn't work).

## ROOT CAUSE ANALYSIS: Why Attempt 11 Fix Did Not Work

**CRITICAL FINDING:** The fix in commit 4a1dfd3 was placed in the WRONG code path.

### What the Fix Did
Added `is_ambiguous_lastname_only()` function at line 1150 of `consensus.py`, which correctly detects that "White" is ambiguous when "Herbert White" exists.

### Where the Fix Is Called
The function is called at line 1192 inside `score_with_alpha_first()`, which is used by `_heuristic_alias_resolution()` at line 1199.

### Why It Doesn't Work
The actual analysis uses `_llm_alias_resolution_pairwise()` (LLM path), NOT `_heuristic_alias_resolution()` (heuristic path).

**Control flow (line 391-396):**
```python
if self.use_llm_alias_resolution and len(proper_name_groups) > 1:
    alias_groups = self._llm_alias_resolution(proper_name_groups)  # ← THIS IS USED
else:
    alias_groups = self._heuristic_alias_resolution(...)  # ← Fix is here, NOT used
```

### The REAL Bug: `_validate_merge()` lines 1623-1648

In the LLM path, the `_validate_merge()` function has this logic:

```python
# Lines 1623-1636 in consensus.py
if is_single_word1 and not is_single_word2:
    single_word = list(significant1)[0]
    multi_words = significant2

    if single_word in multi_words:  # "white" in {"herbert", "white"} → TRUE!
        return True, 0.90  # AUTOMATICALLY APPROVES MERGE
```

This means when comparing "White" vs "Herbert White":
- `single_word = "white"`
- `multi_words = {"herbert", "white"}`
- `"white" in {"herbert", "white"}` → **TRUE**
- Returns `(True, 0.90)` → **Merge accepted!**

The LLM path assumes any single-word name that appears in a multi-word name is "likely the same person". This is WRONG for family names like "White" which could refer to Mr. White, Mrs. White, OR Herbert White.

### The Fix Must Go in `_validate_merge()`

The ambiguity check needs to be added to `_validate_merge()` around line 1623-1648. Before auto-approving based on single-word appearing in multi-word, check if there are MULTIPLE people with that last name.

## Current Issues (Priority Order)

### CRITICAL

1. **FIX IN WRONG CODE PATH: `_validate_merge()` auto-approves family name merges**
   - Problem: "White" (single-word) + "Herbert White" (multi-word) auto-merges because "white" appears in both
   - Location: `src/pipeline/character_extraction/consensus.py` lines 1623-1648
   - The `is_ambiguous_lastname_only()` fix was added to heuristic path, but LLM path is used
   - Fix: Add ambiguity check to `_validate_merge()` BEFORE the single-word-in-multi-word auto-approval

2. **"the soldier" wrongly merged with "the old man" and "the old woman"**
   - Problem: `"the soldier" (3 mentions) - aliases: ['the old man', 'the old woman']`
   - Evidence: "the soldier" is Morris; "the old man"/"the old woman" are Mr./Mrs. White in Chapter 3
   - These are THREE DIFFERENT character references
   - Location: Epithet resolution in `_llm_epithet_resolution()`

3. **"Herbert" and "Herbert White" are falsely split**
   - Problem: "Herbert" (12 mentions) is separate from "Herbert White" (aliased under "White")
   - Evidence: These refer to the same person - the son who dies
   - Downstream of Critical #1 - once "White" stops absorbing "Herbert White", this may self-resolve

### HIGH

4. **Pronunciation flagging common English words**
   - Problem: "his", "old", "man", "wife", "woman" all flagged as proper nouns
   - Root cause: Words from broken character entries being extracted
   - Location: `src/pipeline/pronunciation/` - character name word extraction
   - Fix: Add stopword filtering for common English words before flagging

5. **Project Gutenberg boilerplate contamination**
   - Problem: Chapter 3 includes ~2500 words of legal text; "GutenbergTM" flagged 57 times
   - Location: `src/ingestion/` - front/back matter detection
   - Fix: Improve boilerplate detection patterns for Project Gutenberg texts

### MEDIUM

6. **"his wife" is an orphan character entry**
   - Should merge with "Mrs. White"
   - Downstream of epithet handling issues

7. **Empty relationship fields**
   - All characters have `"relationships": {}`

## Fix History

| Attempt | Fix | Outcome |
|---------|-----|---------|
| 1-4 | Various pipeline errors | Failed to run |
| 5 | First successful run | 6.275 baseline |
| 6 | Re-evaluated with consistent rubric | 7.05 |
| 7-9 | Various fix attempts | 7.05 |
| 10 | Case sensitivity fix | 7.05 |
| 11 | `is_ambiguous_lastname_only()` in heuristic path | **6.70** - FIX IN WRONG CODE PATH |

## Score History

| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 5 | 6.275* | baseline | First successful run |
| 6 | 7.05 | +0.775 | Re-evaluated |
| 10 | 7.05 | +0.775 | Case sensitivity fix didn't help |
| 11 | 6.70 | +0.425 | Regression - fix in wrong code path |

## Next Action

**REQUIRED: Move the ambiguity check from heuristic path to `_validate_merge()` in LLM path**

The fix needs to be at lines 1623-1648 in `consensus.py`. Before auto-approving a merge where a single-word name appears in a multi-word name, check:

1. Is this single word a LAST NAME (appears at end of the multi-word name)?
2. Are there OTHER characters in the text with this same last name?
3. If yes to both → REJECT the auto-approval, let LLM decide

Example implementation sketch:
```python
# Around line 1623, BEFORE auto-approving single-word-in-multi-word
if single_word == multi_words[-1]:  # Single word is the LAST name
    # Check if multiple people share this last name
    lastname_count = sum(1 for n in name_groups.keys()
                        if n.split()[-1].lower() == single_word)
    if lastname_count > 1:
        # Ambiguous - don't auto-approve
        logger.debug(f"Rejecting auto-merge: '{single_word}' is shared by {lastname_count} characters")
        # Let it fall through to chapter overlap checks instead
```

Run `PROMPT_fix.md` targeting the REAL location of the bug.
