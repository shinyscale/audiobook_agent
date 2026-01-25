# Oracle Loop Attempt 1 Summary

**Purpose:** This document records what was tried during the first oracle loop run so future attempts can learn from these results and avoid repeating failed approaches.

---

## Executive Summary

| Metric | Value |
|--------|-------|
| **Date Range** | January 17-18, 2026 |
| **Total Iterations** | 31 |
| **Texts Attempted** | Gatsby (5 attempts), Frankenstein (5 attempts) |
| **Texts Passed** | 0 |
| **Quality Threshold** | 8.0/10 |

### Final Scores
- **Gatsby:** 5.15 → **4.05** (WORSE by 1.1 points) ❌
- **Frankenstein:** started at ~6.25 → **6.75** (minimal improvement) ❌

### Key Finding
The loop made Gatsby **significantly worse** and Frankenstein barely better. The fundamental issue is that **fixes kept causing regressions** in other areas, and there was no mechanism to detect or rollback these regressions.

---

## Results by Text

### Gatsby (5 attempts, FAILED)

| Attempt | Score | Commit | Fix Description | Outcome |
|---------|-------|--------|-----------------|---------|
| 1 | 5.15 | - | Baseline run | Chapter count wrong (7 instead of 9) |
| 2 | 4.65 | `9bde9e5` | Prioritize hard boundary titles | ✓ Fixed chapters 7→9, ✗ Broke Wilson merge |
| 3 | 4.65 | `9a29656` | Prevent family member merging | ✗ Created James Gatz/Gatsby split |
| 4 | 4.65 | `31233a9` | Filter ambiguous last-name-only entries | ✗ ZERO impact |
| 5 | 4.05 | Unknown | Unknown changes | ✗ Chapter count regressed 9→6 |

**Critical Issues Never Resolved:**
- James Gatz and Gatsby remained split (birth name vs known name)
- Narrator identified as "elevator boy" instead of Nick Carraway
- 626 pronunciation false positives

### Frankenstein (5 attempts, FAILED)

| Attempt | Score | Commit | Fix Description | Outcome |
|---------|-------|--------|-----------------|---------|
| 1 | N/A | `0d162f3` | CLI output path fix | ✓ SUCCESS |
| 2 | ~6.25 | `4e3cf44` | Relational descriptor candidate pairing | ✓ PARTIAL - creature/monster merged |
| 3 | 6.25 | `ba1215a` | Validation logic for relational merges | ✗ ZERO impact |
| 4 | 6.25 | `432f7c1` | Diagnostic logging only | ✗ WASTED - no actual fixes |
| 5 | 6.75 | `d501086` | Move relational pairing to execute first | ✗ ZERO impact |

**Critical Issues Never Resolved:**
- Alphonse Frankenstein fragmented into 5 entries ("my father", "Father", "M.", "M. Frankenstein", "Alphonse Frankenstein")
- William Frankenstein missing from character list
- Henry Clerval split into 3 entries
- 664 pronunciation false positives (~50% common English words)

---

## Approaches That FAILED (DO NOT RETRY)

### 1. Filter ambiguous last-name-only entries
**Commit:** `31233a9`
**Rationale:** Remove single-word names like "Wilson" when both "George Wilson" and "Myrtle Wilson" exist.
**Result:** ZERO impact on character merging.
**Why it failed:** The problem wasn't in candidate generation - the LLM was already rejecting merges.

### 2. Block family member merges globally
**Commit:** `9a29656`
**Rationale:** Reject any merge where two names share a last name but have different first names.
**Result:** Over-aggressive - caused James Gatz to be split from Gatsby.
**Why it failed:** Too broad - blocked valid merges (birth names, aliases) along with invalid ones.

```python
# This logic was TOO AGGRESSIVE:
if last1 == last2 and first1 != first2:
    return False  # Different first names, same last = different people
# Problem: "James Gatz" and "Jay Gatsby" have different first names but ARE the same person
```

### 3. Adding diagnostic logging without implementing fixes
**Commit:** `432f7c1`
**Rationale:** Add logging to understand why merges weren't happening.
**Result:** WASTED ATTEMPT - logging added but never analyzed or acted upon.
**Lesson:** Don't commit diagnostic-only changes. Analyze, then fix, then commit.

### 4. Moving relational pairing code position
**Commit:** `d501086`
**Rationale:** The relational pairing code wasn't executing because earlier stages filled the max_pairs limit.
**Result:** ZERO impact - pairs ARE now generated, but LLM still rejects the merges.
**Why it failed:** The bottleneck is NOT pair generation. The LLM merge decision is rejecting valid pairs.

### 5. Validation logic changes for relational descriptors
**Commit:** `ba1215a`
**Rationale:** Allow merges with no shared words if they're relational descriptors with chapter overlap.
**Result:** ZERO impact.
**Why it failed:** Validation was already allowing the pairs. The LLM merge decision is the bottleneck.

---

## Approaches That WORKED (PRESERVE)

### 1. Creature/monster/wretch epithet merging
**Commit:** `4e3cf44` (partial success)
**What it did:** Added relational/descriptive term detection to candidate pair generation.
**Result:** Successfully merged "the creature", "the monster", "the wretch" as aliases.
**Status:** PRESERVED through all subsequent attempts.

```python
# This worked for descriptive epithets:
DESCRIPTIVE_PATTERNS = {
    'creature', 'monster', 'fiend', 'wretch', 'stranger', ...
}
# Successfully paired "the creature" with "the monster" for LLM evaluation
# LLM correctly decided they were the same character
```

### 2. CLI output path fix
**Commit:** `0d162f3`
**What it did:** Ensured parent directories exist for CLI output paths.
**Result:** SUCCESS - CLI now respects explicit `--html` and `--output` flags.

---

## Root Cause Analysis

### Why fixes kept failing

The diagnostic logging from attempt 4 revealed:

1. **Candidate pairs ARE being generated** - The pairing code works
2. **Validation logic IS allowing them** - Pairs pass validation
3. **LLM pairwise merge decision is REJECTING them** - This is the actual bottleneck

The LLM (qwen3-next:80b) is asked "Are 'my father' and 'Alphonse Frankenstein' the same person?" and says NO, despite them clearly being the same character.

**Possible causes:**
- Insufficient context provided to LLM for merge decision
- LLM prompt doesn't emphasize narrative context
- Model may need few-shot examples of relational descriptor merges

### Why fixes caused regressions

1. **Coupled components:** Character extraction and chapter detection share code in `consensus.py`
2. **No integration testing:** Unit tests pass but full pipeline breaks
3. **No regression gate:** Score drops weren't detected or acted upon

---

## Unresolved Core Issues

### Character Fragmentation
| Issue | Example | Root Cause |
|-------|---------|------------|
| Relational descriptors | "my father" ≠ "Alphonse Frankenstein" | LLM rejecting valid merges |
| Title variations | "M. Clerval" ≠ "Clerval" | LLM rejecting valid merges |
| Birth names | "James Gatz" ≠ "Gatsby" | LLM rejecting valid merges |

### Missing Characters
- William Frankenstein appears in chapter summaries but not character list
- Likely filtered by mention count threshold

### Pronunciation False Positives
- 50%+ of flagged words are common English (my, man, father, old, young, child)
- No word frequency filtering implemented
- Should use a common English word list to filter

---

## Git Commits Reference

### Character Extraction Fixes (src/pipeline/character_extraction/consensus.py)

| SHA | Date | Description | Impact |
|-----|------|-------------|--------|
| `d501086` | Jan 18 06:18 | Prioritize relational descriptor pairing | ZERO |
| `432f7c1` | Jan 18 05:07 | Add diagnostic logging | WASTED |
| `ba1215a` | Jan 18 03:45 | Allow relational merges with chapter overlap | ZERO |
| `4e3cf44` | Jan 18 02:36 | Enhance alias candidate pair generation | PARTIAL ✓ |
| `cd860e0` | Jan 18 02:33 | Block family member merges (early validation) | Unknown |
| `9bf7131` | Jan 17 21:28 | Debug logging for character merging | None |
| `31233a9` | Jan 17 21:34 | Filter ambiguous last-name-only entries | ZERO |
| `9a29656` | Jan 17 20:21 | Prevent family member merging | REGRESSION |

### Chapter Detection Fixes (src/pipeline/chapter_detection/)

| SHA | Date | Description | Impact |
|-----|------|-------------|--------|
| `9bde9e5` | Jan 17 20:18 | Prioritize hard boundary titles | REGRESSION (9→6 chapters) |

### CLI Fixes (src/cli.py)

| SHA | Date | Description | Impact |
|-----|------|-------------|--------|
| `0d162f3` | Jan 17 18:43 | Ensure parent dirs for output paths | SUCCESS ✓ |

---

## Code Snippets

### Family Member Blocking (FAILED - Too Aggressive)
**Commit:** `9a29656`
```python
# Added to _validate_merge() in consensus.py
# Problem: This blocked valid merges like "James Gatz" + "Jay Gatsby"

def get_first_last(words: list[str]) -> tuple[str, str]:
    titles = {'mr', 'mrs', 'ms', 'miss', 'dr', 'sir', 'lady', 'lord'}
    start_idx = 1 if (words[0].rstrip('.').lower() in titles and len(words) > 1) else 0
    first = words[start_idx] if start_idx < len(words) else ""
    last = words[-1] if len(words) > start_idx else ""
    return first, last

first1, last1 = get_first_last(words1)
first2, last2 = get_first_last(words2)

# THIS WAS TOO AGGRESSIVE:
if first1 and last1 and first2 and last2:
    if last1 == last2 and first1 != first2:
        return False, 0.05  # Rejected merges that should have been allowed
```

### Relational Descriptor Pairing (PARTIAL SUCCESS)
**Commit:** `4e3cf44`
```python
# Added to _candidate_pairs_for_merge() in consensus.py
# This WORKED for creature/monster, but failed for family relations

RELATIONAL_TERMS = {
    'father', 'mother', 'son', 'daughter', 'brother', 'sister',
    'uncle', 'aunt', 'grandfather', 'grandmother', 'cousin',
    'husband', 'wife', 'friend', 'companion',
}

DESCRIPTIVE_PATTERNS = {
    'creature', 'monster', 'fiend', 'wretch', 'stranger',  # These WORKED
    'captain', 'professor', 'doctor', 'detective',
}

# Pairs generated correctly, but LLM rejected family relation merges
# while accepting creature/monster merges
```

---

## Recommendations for Next Attempt

### Priority 1: Investigate LLM Merge Decisions
The pairs are generated and validated. The LLM is rejecting them. Need to:
- Examine the prompt given to LLM for merge decisions
- Add more context (chapter summaries, surrounding text)
- Consider few-shot examples of relational descriptor merges

### Priority 2: Add Pronunciation Word Frequency Filter
This is a separate, isolated fix that won't affect character extraction:
- Use a common English word list (top 5000-10000 words)
- Filter out common words before pronunciation flagging
- Should immediately improve pronunciation score from 3/10 to 6-7/10

### Priority 3: Implement Regression Protection
Before any fix:
1. Record baseline score
2. Apply fix
3. Run full evaluation
4. If score drops > 0.3 points, auto-revert

### Priority 4: Preserve What Works
- Keep creature/monster/wretch epithet merging
- Keep CLI output path fix
- Don't modify chapter detection until character issues are resolved

---

## Lessons Learned

1. **Unit tests are not enough** - All 444 tests passed while output quality degraded
2. **One fix can break multiple things** - Character and chapter detection are coupled
3. **Diagnostic logging without action wastes attempts** - Analyze and fix in the same iteration
4. **The LLM is the bottleneck** - For character merging, the LLM merge decision is what's failing
5. **Regression protection is essential** - The loop needs to detect and rollback harmful changes
