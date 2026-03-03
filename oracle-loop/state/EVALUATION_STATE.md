# Current Evaluation State

## Active Text
- **Name:** berenice
- **Attempt:** 1
- **Phase:** awaiting_evaluation
- **baseline_score:** 8.68
- **Competitive Mode:** none

## Output Files
- HTML: ../output/berenice/report.html
- JSON: ../output/berenice/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 9/10 ✓
  - Completeness: 9/10
  - Identity Resolution: 10/10
  - Alias Grouping: 9/10
- Character Profiles: 7.5/10 ✗ (FAILING)
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 9/10 ✓
- **Overall: 8.68/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (1 category below threshold: Character Profiles)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1       | 8.68  | —                   | Profiles fail: "cousin" relationship blocked → "associated" |

## Current Issues (Priority Order)

### CRITICAL
(none)

### HIGH
1. **Egaeus↔Berenice relationship labeled "associated" instead of "cousin" / "betrothed"** [Profiles]
   - Problem: The LLM correctly generated "cousin" for both Egaeus→Berenice and Berenice→Egaeus, but `remove_contradictory_relationships()` in post_corrections.py deleted both labels because "cousin" is NOT in `_SYMMETRIC_RELATIONSHIPS`. The fallback label "associated" is uninformative.
   - Evidence: Pipeline log says "Relationship 'cousin' blocked: both Egaeus→Berenice and Berenice→Egaeus labeled 'cousin' — removed as logically impossible symmetric non-symmetric label." But cousins IS a symmetric relationship — if A is B's cousin, B is A's cousin.
   - Location: `src/pipeline/character_profiling/post_corrections.py`, line ~60 — `_SYMMETRIC_RELATIONSHIPS` frozenset
   - Fix: Add `"cousin"` to `_SYMMETRIC_RELATIONSHIPS`. Also consider adding other missing symmetric family terms: `"classmate"`, `"roommate"`, `"playmate"`, `"betrothed"`, `"fiancé"`, `"fiancée"`, `"lover"`, `"spouse"`, `"husband and wife"` — but at minimum `"cousin"` is required to unblock this text.
   - Note: `RELATIONSHIP_REVERSES` dict already has `"cousin": "cousin"` (line ~24), confirming it's symmetric. The symmetric set just wasn't updated to match.

### MEDIUM
2. **Some common English words flagged as pronunciations** [Pronunciation]
   - Problem: Words like "shrubberies", "light-heartedness", "sentient", "refracted" are standard English — false positives for a narrator.
   - Evidence: 26 of 44 entries categorized as "Other/unknown" — some are genuinely unusual (simoom, phantasma, pertinaciously) but others are common vocabulary.
   - Location: `src/pipeline/pronunciation/cmu_proposer.py` — COMMON_WORDS_WHITELIST
   - Fix: Add "shrubberies", "light-heartedness", "sentient", "refracted" to the whitelist. Low priority — score is 8/10 already.

### LOW
3. **Null chapter title for single-section text** [Structure]
   - Problem: The single structure element has `title: null`. While acceptable, labeling it with the story title ("Berenice") would be more informative.
   - Not blocking — score is 9/10.

## Fix History
- Attempt 1: Added `"cousin"`, `"brother"`, `"sister"`, `"spouse"` to `_SYMMETRIC_RELATIONSHIPS` in post_corrections.py
  - Root cause: `post_corrections.py:_SYMMETRIC_RELATIONSHIPS:line 60` was missing "cousin"; LLM correctly labeled both Egaeus→Berenice AND Berenice→Egaeus as "cousin", but `remove_contradictory_relationships()` deleted both because "cousin" wasn't in the symmetric set, replacing with fallback "associated"
  - Also added "brother", "sister", "spouse" — all listed as self-reversing in RELATIONSHIP_REVERSES but missing from _SYMMETRIC_RELATIONSHIPS (same inconsistency, different terms)
  - Smoke test: N/A (trivial data-only fix to a frozenset)
  - Modified: src/pipeline/character_profiling/post_corrections.py

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | Profiles: cousin blocked as contradictory | post_corrections.py | Awaiting analysis |

## Pipeline Notes
- Analysis completed in 23m 35s
- 4 characters found: Egaeus, Berenice, The servant maiden, Ebn Zaiat
- 44 pronunciation flags (26 unknown, 13 proper noun, 5 foreign)
- Low confidence profile for Ebn Zaiat (0.15) — sparse character
- Blocked aliases: 'the disfigured body' (hallucinated), 'a servant' (semantic mismatch), 'the maiden' (not in summaries), 'the physician' (not in summaries)
- Models: structure/pronunciation=qwen3.5:35b-a3b, characters/summaries=qwen3.5:122b-a10b

## Next Action
Evaluate output — verify cousin relationship is now correctly labeled (not "associated").
