# Current Evaluation State

## Active Text
- **Name:** berenice
- **Attempt:** 5
- **Phase:** complete
- **baseline_score:** 8.68

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 8.5/10 ✓
  - Completeness: 8/10
  - Identity Resolution: 10/10
  - Alias Grouping: 9/10
- Character Profiles: 8.5/10 ✓
- Chapter Summaries: 9.5/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 9/10 ✓
- **Overall: 8.80/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** PASS — all categories at or above threshold

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1       | 8.68  | —                   | Profiles fail: "cousin" relationship becomes "associated" in output |
| 2       | 8.43  | -0.25               | Profiles fail: narrator co-mention guard applied; relationship STILL "associated" |
| 3       | 8.45  | -0.23               | Profiles fail: extract_relationships_from_evidence() upgraded but fix misses because evidence statement with "cousin" doesn't name Berenice |
| 4       | 8.45  | -0.23               | Profiles fail: descriptions field now scanned correctly BUT reject_unfounded_familial_labels() overwrites "cousin" → "associated" |
| 5       | 8.80  | +0.12               | **PASS** — extended_family_terms + narrator exemption fix works; "cousin" preserved correctly |

## Current Issues (Priority Order)

### CRITICAL
(none)

### HIGH
(none)

### MEDIUM
1. **"The Teeth" not extracted** [Characters — Completeness]
   - LLM non-determinism; only 3 mentions in 3240-word text. Not a pipeline bug. Score still passes without it.

2. **Some common English words flagged as pronunciations** [Pronunciation]
   - "light-heartedness", "shrubberies", "refracted", "sentient", "emaciation", "unloveliness" are standard vocabulary.
   - Location: `src/pipeline/pronunciation/cmu_proposer.py` — COMMON_WORDS_WHITELIST
   - Not blocking.

### LOW
3. **Null chapter titles for single-section text** [Structure]
   - Both structure elements have `title: null`. Minor polish item.

4. **Egaeus has no speech_patterns** [Profiles]
   - As first-person narrator with no dialogue, this is expected behavior.

## Fix History
- Attempt 1: Added `"cousin"`, `"brother"`, `"sister"`, `"spouse"` to `_SYMMETRIC_RELATIONSHIPS` in post_corrections.py
  - Result: Correct fix but insufficient — different downgrade path active
  - Modified: src/pipeline/character_profiling/post_corrections.py
- Attempt 2: In `verify_relationships_from_text()`, skip family-label downgrade when `is_narrator=True` for either character
  - Result: Changed "acquaintance" to "associated" — NOT fixed, different label but still wrong
  - Modified: src/pipeline/character_profiling/post_corrections.py
- Attempt 3: Fix `extract_relationships_from_evidence()` to process generic labels AND detect family terms
  - Result: **DID NOT FIX** — evidence stmt with "cousin" lacks "Berenice"; descriptions field not scanned
  - Modified: src/pipeline/character_profiling/post_corrections.py
- Attempt 4: Extend `extract_relationships_from_evidence()` to ALSO scan `char.descriptions` field
  - Result: **FIX WORKS at extraction** — but `reject_unfounded_familial_labels()` overwrites "cousin" → "associated"
  - Modified: src/pipeline/character_profiling/post_corrections.py
- Attempt 5: Expand `sibling_terms` → `extended_family_terms` + narrator exemption in `reject_unfounded_familial_labels()`
  - Result: **FIXED** — "cousin" now preserved correctly; all 332 tests pass
  - Modified: src/pipeline/character_profiling/post_corrections.py

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | Profiles: cousin blocked by _SYMMETRIC_RELATIONSHIPS | post_corrections.py | Fixed but insufficient — different downgrade path active |
| 2 | Profiles: cousin downgraded to acquaintance by verify_relationships_from_text() | post_corrections.py | Changed "acquaintance" to "associated" — NOT fixed |
| 3 | Profiles: "associated" from LLM not upgraded by extract_relationships_from_evidence() | post_corrections.py | NOT fixed — evidence stmt lacks character name |
| 4 | Profiles: descriptions field not scanned by extract_relationships_from_evidence() | post_corrections.py | FIX WORKS at extraction — overwritten downstream |
| 5 | Profiles: reject_unfounded_familial_labels() unconditionally downgrades "cousin" | post_corrections.py | **FIXED** — extended_family_terms + narrator exemption |

## Configuration Audit
- Models: Appropriate (qwen3.5:122b-a10b for characters/summaries/profiles, qwen3.5:35b-a3b for structure/pronunciation)
- Context lengths: 32768 — sufficient for short story
- Temperature: 0.7 across the board — reasonable
- No LLM retries or parse failures
- All confidence=high for characters and profiles

## Next Action
Ready to advance to next text (gift_of_the_magi).
