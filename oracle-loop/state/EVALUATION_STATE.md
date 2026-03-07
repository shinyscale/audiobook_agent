# Current Evaluation State

## Active Text
- **Name:** i_have_no_mouth
- **Attempt:** 3
- **Phase:** awaiting_fix
- **baseline_score:** 6.35

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 6.5/10 ✗ (FAILING)
  - Completeness: 9/10
  - Identity Resolution: 5/10
  - Alias Grouping: 8/10
- Character Profiles: 7/10 ✗ (FAILING)
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 8/10 ✓
- **Overall: 7.8/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.35 | 0 | Baseline - duplicate Benny, wrong narrator, profile errors |
| 2 | 7.3 | +0.95 | Benny dedup fixed, narrator=Ted, but duplicate Ted appeared, profiles improved |
| 3 | 7.8 | +1.45 | Relationship vocab improved, pronunciation fixed, but duplicate Ted and AM role fixes didn't work |

## Current Issues (Priority Order)

### CRITICAL
1. **Duplicate "Ted" character — fix targeted wrong code path** [Identity Resolution]
   - Problem: main_cast_1 (Ted, narrator=True, role=protagonist, mentions=5) and main_cast_6 (Ted, narrator=False, role=main, mentions=5) still both present
   - Root cause: The attempt 3 fix added a same-name guard to STEP 5.8.5b (narrator promotion from supporting_cast). But the duplicate is created by STEP 5.8 (general promotion at `characters.py:1476-1494`) which runs BEFORE 5.8.5b. The general promotion loop `main_cast.extend(promoted_chars)` at line 1494 has NO same-name dedup check. A Ted fragment in supporting_cast with enough mentions gets promoted without checking if Ted already exists in main_cast.
   - Evidence: main_cast_6 has `role="main"` (assigned by promotion logic at line 1482), confirming it came from STEP 5.8 general promotion, not 5.8.5b narrator promotion
   - Location: `src/agents/characters.py` line 1476-1494 (STEP 5.8 general promotion loop)
   - Fix: Before adding to `promoted_chars`, check if a character with the same canonical_name already exists in main_cast. If so, merge mention counts and skip promotion (or merge into existing). This is the same pattern as the 5.8.5b fix but applied to the general promotion path.

### HIGH
2. **AM still labeled "protagonist" — adversarial label check misses "victim"** [Profiles]
   - Problem: The attempt 3 fix added post-profile adversarial role correction that checks if outgoing relationship labels are adversarial. But AM's outgoing labels are all "victim" (meaning the other characters are AM's victims). "victim" is NOT in `_ADVERSARIAL_LABELS`.
   - Evidence: AM relationships = `{'Ted': 'victim', 'Ellen': 'victim', ...}`. The check at `analyzer.py:2144-2148` finds 0 adversarial hits because "victim" isn't in the set `{tormentor, captor, oppressor, ...}`.
   - Root cause: The adversarial check looks for labels describing what AM IS (tormentor/captor), but AM's outgoing labels describe what others are TO AM (victim). When a non-narrator character labels ALL other characters as "victim", that character is the victimizer/antagonist.
   - Location: `src/analyzer.py` line 2134-2137 (`_ADVERSARIAL_LABELS` set)
   - Fix: Add "victim" to `_ADVERSARIAL_LABELS`. When a character's outgoing relationships are predominantly "victim" labels, that character is victimizing everyone — it's an antagonist. This is semantically correct: "Ted: victim" on AM means "AM victimizes Ted".

3. **Ted has self-relationship "Ted: colleague"** [Profiles]
   - Problem: main_cast_1 Ted and main_cast_6 Ted both list "Ted: colleague" — a character referencing itself
   - Evidence: Artifact of duplicate Ted. The profiler sees two Teds and creates a relationship between them.
   - Location: Self-relationships should be filtered as a safety net
   - Fix: Fixing duplicate Ted (#1) is the primary fix. As a safety net, add a generic post-profile filter that removes self-relationships where relationship key == canonical_name.

### MEDIUM
4. **AM evidence says "AM is the creator and tormentor of the five humans"** [Profiles]
   - Problem: AM did not create the humans — it captured/imprisoned them. "creator" is wrong.
   - Evidence: AM is a supercomputer that gained sentience and wiped out humanity, keeping 5 survivors as prisoners
   - Severity: Medium — the evidence text is LLM-generated and partially inaccurate, but the relationship labels themselves are now correct ("victim")
   - Location: Evidence generation in profile pipeline

5. **Ellen's relationship "Gorrister: target of physical violence" is incorrect** [Profiles]
   - Problem: Gorrister does not commit physical violence against Ellen in the text. This is hallucinated.
   - Evidence: Gorrister is passive/depressive; no textual basis for him targeting Ellen with violence
   - Location: Profile generation LLM hallucination — single-instance error

### LOW
6. **Chapter title is null** [Structure]
   - Problem: Single section has `title: null` — could display the story title
   - Not blocking — single-section detection is correct

7. **Summary claims wind "killing Ellen"** [Summaries]
   - Problem: The summary says the wind kills Ellen during the hurricane sequence, but in the story Ellen survives until Ted kills her at the end
   - Evidence: Minor factual error in the summary
   - Severity: Low — doesn't materially affect narrator preparation

## What Improved from Attempt 2
- Relationship vocabulary improved — humans now use "captor"/"tormentor" for AM (was "creator") ✓
- Pronunciation false positives reduced (sentience, sentient, loonie, gibbered, etc. removed) ✓
- 5.8.5b narrator promotion now has same-name guard (correct but wrong path for this specific bug) ✓

## What Did NOT Improve from Attempt 2
- Duplicate Ted still present — fix targeted STEP 5.8.5b but the duplicate comes from STEP 5.8 general promotion
- AM still "protagonist" — adversarial label set doesn't include "victim" (AM's outgoing label for its targets)

## Fix History
- Attempt 2: Three connected fixes for character extraction and pronunciation
  1. **Exact-name dedup in `_merge_within_main_cast`** (`src/agents/characters.py` Pass -1) — Fixed Benny duplicate
  2. **Vocative pattern + narrator fallback** (`src/agents/characters.py`) — Fixed narrator detection but introduced duplicate Ted
  3. **Pronunciation fixes** (`cmu_proposer.py`, `enricher.py`) — Partially fixed false positives

- Attempt 3: Four fixes (two didn't take effect)
  1. **STEP 5.8.5b same-name guard** (`src/agents/characters.py`) — Code is correct but targets wrong path; duplicate Ted comes from STEP 5.8 general promotion
  2. **Post-profile adversarial role correction** (`src/analyzer.py`) — Code is correct but `_ADVERSARIAL_LABELS` doesn't include "victim"; AM's outgoing labels are all "victim"
  3. **Relationship vocabulary expanded** (`src/analyzer.py`) — WORKED: humans now use captor/tormentor/victim instead of "creator"
  4. **Pronunciation whitelist additions** (`cmu_proposer.py`) — WORKED: 7 more false positives removed

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 2 | Dup Benny | characters.py (Pass -1 dedup) | Fixed |
| 2 | Wrong narrator | characters.py (vocative + STEP 4.5b) | Fixed but introduced dup Ted |
| 2 | Pronunciation FPs | cmu_proposer.py, enricher.py | Partially fixed |
| 3 | Dup Ted | characters.py (STEP 5.8.5b same-name guard) | No change — wrong code path |
| 3 | AM wrong role | analyzer.py (post-profile adversarial role correction) | No change — "victim" not in label set |
| 3 | Relationship vocab | analyzer.py (captor/prisoner/tormentor/victim labels) | Fixed |
| 3 | Pronunciation FPs | cmu_proposer.py (7 more words whitelisted) | Fixed |

**Pattern detected:** STEP 5.8.5b was the wrong target for duplicate Ted. The general promotion at STEP 5.8 (line 1476-1494) is the actual source. Fix must target STEP 5.8.

## Next Action
Run PROMPT_fix.md to address:
1. CRITICAL: Add same-name dedup guard to STEP 5.8 general promotion (`characters.py:1476-1494`)
2. HIGH: Add "victim" to `_ADVERSARIAL_LABELS` (`analyzer.py:2134`)
3. HIGH: Add self-relationship filter as safety net

## Output Files
- HTML: ../output/i_have_no_mouth/report.html
- JSON: ../output/i_have_no_mouth/analysis.json

## Pipeline Notes
- Attempt 3 analysis completed successfully in 21m 35s
- Model: qwen3-next:80b-a3b-instruct-q8_0 (all agents)
- Competitive mode: none (baseline behavior)
- Ted detected as narrator (first-person)
- 7 characters extracted: AM (77), Benny (35), Ellen (30), Gorrister (29), Nimdok (17), Ted (5), Ted (5)
- 16 pronunciation flags (improved from previous attempts)
- Fixes needed: duplicate Ted guard at STEP 5.8, "victim" in adversarial labels, self-relationship filter
