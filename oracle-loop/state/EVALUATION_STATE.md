# Current Evaluation State

## Active Text
- **Name:** i_have_no_mouth
- **Attempt:** 4
- **Phase:** awaiting_analysis
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
   - **FIXED in attempt 4** — STEP 5.8 general promotion now checks `main_cast_names_lower` before promoting; merges mention_count into existing and skips duplicate

### HIGH
2. **AM still labeled "protagonist" — adversarial label check misses "victim"** [Profiles]
   - **FIXED in attempt 4** — "victim" added to `_ADVERSARIAL_LABELS`; AM's outgoing "victim" labels now trigger antagonist relabeling

3. **Ted has self-relationship "Ted: colleague"** [Profiles]
   - **FIXED in attempt 4** — Post-profile self-relationship filter added; removes any relationship key == character's own canonical name

### MEDIUM
4. **AM evidence says "AM is the creator and tormentor of the five humans"** [Profiles]
   - Problem: AM did not create the humans — it captured/imprisoned them. "creator" is wrong.
   - Severity: Medium — LLM-generated evidence text; relationship labels are now correct ("victim")
   - Location: Evidence generation in profile pipeline

5. **Ellen's relationship "Gorrister: target of physical violence" is incorrect** [Profiles]
   - Problem: Gorrister does not commit physical violence against Ellen in the text. Hallucinated.
   - Location: Profile generation LLM hallucination — single-instance error

### LOW
6. **Chapter title is null** [Structure]
   - Problem: Single section has `title: null` — could display the story title
   - Not blocking — single-section detection is correct

7. **Summary claims wind "killing Ellen"** [Summaries]
   - Problem: Minor factual error in the summary
   - Severity: Low — doesn't materially affect narrator preparation

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

- Attempt 4: Three fixes
  1. **STEP 5.8 same-name dedup** (`src/agents/characters.py:1476-1494`) — Added `main_cast_names_lower` set check before promotion; merges mention_count into existing entry and skips duplicate promotion
     - Root cause: STEP 5.8 general promotion loop had no same-name guard; supporting_cast Ted fragment with ≥ threshold mentions was promoted unconditionally
     - Smoke test: 332 tests pass, no regressions
  2. **"victim" added to `_ADVERSARIAL_LABELS`** (`src/analyzer.py:2134`) — When AM's outgoing relationship labels are all "victim", now correctly triggers protagonist→antagonist relabeling
     - Root cause: "victim" describes what others are TO AM, semantically meaning AM is the victimizer/antagonist
  3. **Self-relationship filter** (`src/analyzer.py`) — Post-profile pass removes relationship keys matching own canonical_name
     - Root cause: artifact of duplicate characters being profiled together

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
| 4 | Dup Ted | characters.py (STEP 5.8 same-name dedup) | Targeted correct path |
| 4 | AM wrong role | analyzer.py ("victim" in _ADVERSARIAL_LABELS) | Fixed label set |
| 4 | Self-relationship | analyzer.py (post-profile filter) | Added safety net |

## Next Action
Re-run analysis (PROMPT_analyze.md) to verify all three fixes.

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
