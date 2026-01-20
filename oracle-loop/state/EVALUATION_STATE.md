# Current Evaluation State

## Active Text
- **Name:** monkeys_paw
- **Attempt:** 12
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

Adjusted to 6.70 due to no improvement from previous attempt (fix was in wrong code path).

## Evaluation Details

### Structure Detection: 9/10
- **Expected:** 3 parts (I, II, III)
- **Actual:** 3 chapters correctly detected
- **Issue:** Chapter 3 includes Project Gutenberg boilerplate (~2500 words of legal text)
- This is a minor issue but notable - the back matter detection should strip this

### Character Extraction: 5/10
- **Expected characters:** Mr. White, Mrs. White, Herbert (son), Sergeant-Major Morris, the stranger (Maw and Meggins representative)
- **Critical problems:**
  1. "White" with alias "Herbert White" (43 mentions) - **WRONG**: "White" alone should be Mr. White, Herbert White is his SON
  2. "Herbert" separate (12 mentions) - should be merged with Herbert White
  3. "the soldier" has aliases "the old man" and "the old woman" - **COMPLETELY WRONG**:
     - "the soldier" = Sergeant-Major Morris
     - "the old man" = Mr. White in Part III
     - "the old woman" = Mrs. White in Part III
  4. "his wife" is an orphan entry - should be Mrs. White
- **Good:** Sergeant-Major Morris correctly has aliases Morris and "the sergeant-major"

### Character Profiles: 6/10
- Mr. White and Mrs. White have LOW confidence with minimal profiles
- The "White" entry has profiles that describe an old man with thin grey beard - this is Mr. White's description applied to the wrong character
- Herbert's profile is reasonable
- Sergeant-Major Morris has a good detailed profile

### Chapter Summaries: 8/10
- Part I summary is accurate and comprehensive
- Part II summary is accurate
- Part III summary correctly captures events but includes mention of Project Gutenberg legal text contamination

### Pronunciation Guide: 4/10
- **False positives:** "his" (99 occurrences!), "old" (42), "man" (23), "wife" (15), "woman" (11), "soldier" (5)
- These common English words should NOT be flagged
- **Legitimate entries:** "rubicund", "fakir/fakirs", "antimacassar", "bibulous", "condoled" - these ARE useful
- **Boilerplate contamination:** "GutenbergTM" flagged 57 times, plus legal terms like "MERCHANTABILITY", "PGLAF"
- Homograph handling (read, wind, house) is actually good

### HTML Presentation: 9/10
- Navigation works
- Layout is clean
- Information is logically organized

## ROOT CAUSE ANALYSIS: Why Attempt 11 Fix Did Not Work

**The fix was placed in the WRONG code path.**

### What the Fix Added
`is_ambiguous_lastname_only()` function at line 1150 of `consensus.py`, which correctly detects ambiguous last names.

### Where It's Called
Line 1192 inside `score_with_alpha_first()`, which is used by `_heuristic_alias_resolution()` at line 1199.

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

The LLM path calls `_validate_merge()` to validate LLM-proposed merges. Lines 1623-1648 contain:

```python
if is_single_word1 and not is_single_word2:
    single_word = list(significant1)[0]
    multi_words = significant2

    if single_word in multi_words:  # "white" in {"herbert", "white"} → TRUE!
        return True, 0.90  # AUTOMATICALLY APPROVES MERGE
```

This auto-approves "White" merging with "Herbert White" because "white" appears in both names.

## Current Issues (Priority Order)

### CRITICAL

1. **`_validate_merge()` auto-approves family name merges (STILL UNFIXED)**
   - Problem: "White" + "Herbert White" auto-merged because "white" appears in both
   - Location: `src/pipeline/character_extraction/consensus.py` lines 1623-1648
   - Evidence: `is_ambiguous_lastname_only()` fix exists but is in heuristic path, not LLM path
   - Fix: Add ambiguity check to `_validate_merge()` BEFORE auto-approval at line 1630:
     ```python
     if single_word in multi_words:
         # NEW: Check if this single-word name is ambiguous
         # (i.e., multiple people share this last name)
         lastname_count = sum(1 for n in name_groups.keys()
                             if len(n.split()) > 1 and n.split()[-1].lower() == single_word.lower())
         if lastname_count > 1:
             logger.debug(f"Rejecting auto-merge: '{single_word}' shared by {lastname_count} full names")
             # Don't auto-approve - let other validation logic handle it
         else:
             return True, 0.90  # High confidence
     ```

2. **"the soldier" wrongly merged with "the old man" and "the old woman"**
   - Problem: Three DIFFERENT character references merged into one
   - Evidence: "the soldier" is Morris; "the old man"/"the old woman" are Mr./Mrs. White in Chapter 3
   - Location: Epithet resolution in `_llm_epithet_resolution()` or `_resolve_epithet_groups()`
   - Fix: Add gender conflict check - "the old man" vs "the old woman" cannot be the same person

### HIGH

3. **"Herbert" and "Herbert White" are falsely split**
   - Problem: "Herbert" (12 mentions) exists separately from "Herbert White" (aliased under "White")
   - This is downstream of Critical #1 - once "White" stops absorbing "Herbert White", this should self-resolve
   - If not, need to ensure first-name-only references merge with full names

4. **Common English words flagged as proper nouns**
   - Problem: "his" (99x), "old" (42x), "man" (23x), "wife" (15x), "woman" (11x), "soldier" (5x) all flagged
   - Root cause: Likely extracted from broken character entries ("the old man", "his wife")
   - Location: `src/pipeline/pronunciation/` - character name word extraction
   - Fix: Add stopword filtering using a common English word list (top 5000-10000 words)

5. **Project Gutenberg boilerplate contamination**
   - Problem: Chapter 3 includes ~2500 words of legal text; "GutenbergTM" flagged 57 times
   - Location: `src/ingestion/` - back matter detection
   - Fix: Add patterns to detect and strip Project Gutenberg license text

### MEDIUM

6. **"his wife" orphan character entry**
   - Should merge with "Mrs. White"
   - Downstream of epithet/relational handling issues

7. **Empty relationship fields**
   - All characters have `"relationships": {}`
   - Not critical for narrator preparation but would be nice

8. **Mr. White and Mrs. White have LOW confidence**
   - They exist as separate entries but with minimal profiles
   - May improve once character extraction is fixed

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

**REQUIRED: Add ambiguity check to `_validate_merge()` in the LLM path**

The fix must go at lines 1623-1648 in `src/pipeline/character_extraction/consensus.py`.

Before auto-approving a merge where a single-word name appears in a multi-word name (line 1630), check:

1. Is this single word a LAST NAME (appears at end of multi-word names)?
2. Are there MULTIPLE full names with this last name?
3. If yes to both → REJECT the auto-approval, let other validation logic handle it

This is the same logic as `is_ambiguous_lastname_only()` but applied to the correct code path.

**Secondary fix:** Add common English stopword filtering to pronunciation pipeline to eliminate false positives.

Run `PROMPT_fix.md` targeting Critical #1 in `_validate_merge()`.
