# Current Evaluation State

## Active Text
- **Name:** i_have_no_mouth
- **Attempt:** 5
- **Phase:** awaiting_analysis
- **baseline_score:** 6.35

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 9/10 ✓
  - Completeness: 10/10
  - Identity Resolution: 10/10
  - Alias Grouping: 8/10
- Character Profiles: 5.5/10 ✗ (FAILING)
- Chapter Summaries: 8/10 ✓
- Pronunciation Guide: 8.5/10 ✓
- HTML Presentation: 8/10 ✓
- **Overall: 8.1/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (1 category below threshold)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.35 | 0 | Baseline - duplicate Benny, wrong narrator, profile errors |
| 2 | 7.3 | +0.95 | Benny dedup fixed, narrator=Ted, but duplicate Ted appeared, profiles improved |
| 3 | 7.8 | +1.45 | Relationship vocab improved, pronunciation fixed, but duplicate Ted and AM role fixes didn't work |
| 4 | 7.6 | +1.25 | Fixes did NOT take effect — duplicate Ted persists, AM still "protagonist" |
| 5 | 8.1 | +1.75 | Dup Ted FIXED, AM now antagonist, self-alias fixed. But 3 humans wrongly labeled antagonist |

## Current Issues (Priority Order)

### CRITICAL
1. **Ellen, Nimdok, Gorrister all wrongly labeled "antagonist"** [Profiles — Role Assignment]
   - Problem: 3 of 5 human victims are labeled "antagonist". Only Ted and Benny are correctly "protagonist". Ellen, Nimdok, and Gorrister are fellow prisoners/victims of AM, not antagonists.
   - Root cause: The LLM assigns "antagonist" (probably because all humans participate in violence at the end — Ted kills Benny/Gorrister/Ellen, Ellen kills Nimdok). The attempt 5 false-antagonist correction checks for zero adversarial evidence, but these characters DO have adversarial-looking labels:
     - Ellen outgoing: "enemy (killed in retaliation)" to Nimdok — "enemy" is in _ADVERSARIAL_LABELS
     - Nimdok outgoing: "enemy" to Ellen — same
     - Gorrister outgoing: "victim" to AM and Benny — "victim" was added to _ADVERSARIAL_LABELS in attempt 4
   - **The "victim" label in _ADVERSARIAL_LABELS is a catch-22**: Adding "victim" to detect AM's adversarial nature means actual VICTIMS (Gorrister) also appear to have adversarial evidence, blocking the false-antagonist correction.
   - **Fix approach — distinguish ACTIVE vs PASSIVE adversarial labels:**
     - ACTIVE labels (tormentor, captor, abuser, oppressor, persecutor) = evidence FOR antagonist role — the character is INFLICTING harm
     - PASSIVE labels (victim, enemy, target, prisoner) = NOT evidence for antagonist role — the character is RECEIVING harm or in mutual conflict
     - In the false-antagonist correction in `src/analyzer.py`, only count ACTIVE adversarial labels as evidence to KEEP the "antagonist" role. Characters whose only adversarial labels are passive (victim, enemy) should be relabeled to "protagonist"
     - "enemy" between two non-AM characters (Ellen↔Nimdok) is mutual conflict under duress, not antagonism
   - Location: `src/analyzer.py` — the post-profile adversarial role correction (added in attempt 3, modified in attempt 5)

### HIGH
2. **AM→Nimdok and AM→Benny still labeled "colleague"** [Profiles — Relationships]
   - Problem: AM torments all 5 humans equally, but AM→Nimdok: "colleague" and AM→Benny: "colleague" instead of "tormentor"
   - Evidence: AM→Ted and AM→Ellen are correctly "tormentor", AM→Gorrister is correctly "tormentor". Only Nimdok and Benny are wrong.
   - Location: Profile generation in `src/analyzer.py` — `_generate_character_profile()`
   - Note: This is an LLM output quality issue. The relationship vocabulary expansion from attempt 3 partially worked (3/5 now correct), but the LLM still defaults to "colleague" for some characters.
   - Possible fix: In the post-profile correction, if a character is confirmed "antagonist" (after role correction), any "colleague" labels from antagonist→non-antagonist should be flagged as suspicious and potentially relabeled based on the character's dominant outgoing label pattern (if 3/5 are "tormentor", the remaining 2 "colleague" labels are likely also "tormentor")

3. **Nimdok→AM and Benny→AM labeled "colleague"** [Profiles — Relationships]
   - Same issue from the victim side: Nimdok and Benny label AM as "colleague" when AM is their captor/tormentor
   - Fix: Similar consistency enforcement — if AM is confirmed antagonist, victim→AM relationships labeled "colleague" should be corrected to "captor" or "tormentor"

### MEDIUM
4. **Ellen→Gorrister: "victim of physical abuse" is incorrect** [Profiles — Relationships]
   - Problem: Gorrister does not physically abuse Ellen in the text. The humans are all victims of AM, not of each other (except the mercy killings at the end).
   - Severity: Medium — single incorrect relationship label, likely LLM hallucination

5. **Ted and AM have no physical description** [Profiles — Descriptions]
   - Ted: desc_len=0, AM: desc_len=0
   - Ted as first-person narrator rarely describes himself, so this is somewhat expected
   - AM is a computer/AI, so physical description is complex — the text describes AM's internal environment more than AM itself
   - Severity: Medium — not entirely fixable for first-person narrators

6. **Summary says "AM destroys its obsolete systems"** [Summaries]
   - In the text, they pass through AM's infrastructure (computer banks), but the characterization of AM "destroying obsolete systems" is a minor inaccuracy
   - Also: "he created them with sentience" — AM did not create the humans; it preserved/imprisoned them
   - Severity: Medium — minor factual inaccuracies in summary

### LOW
7. **Chapter title is null** [Structure]
   - Single section has `title: null` — could display the story title
   - Not blocking — single-section detection is correct

8. **"colleague" labels pervasive in non-AM relationships** [Profiles]
   - Gorrister→Ted/Ellen/Nimdok: "group member" — acceptable but "fellow prisoner" would be more accurate
   - This is cosmetic compared to the role and AM-relationship issues

## Fix History
- Attempt 2: Three connected fixes for character extraction and pronunciation
  1. **Exact-name dedup in `_merge_within_main_cast`** (`src/agents/characters.py` Pass -1) — Fixed Benny duplicate
  2. **Vocative pattern + narrator fallback** (`src/agents/characters.py`) — Fixed narrator detection but introduced duplicate Ted
  3. **Pronunciation fixes** (`cmu_proposer.py`, `enricher.py`) — Partially fixed false positives

- Attempt 3: Four fixes (two didn't take effect)
  1. **STEP 5.8.5b same-name guard** (`src/agents/characters.py`) — Code is correct but targets wrong path; duplicate Ted comes from STEP 5.8 general promotion → WRONG, actually comes from STEP 5.8.6
  2. **Post-profile adversarial role correction** (`src/analyzer.py`) — Code is correct but `_ADVERSARIAL_LABELS` doesn't include "victim"
  3. **Relationship vocabulary expanded** (`src/analyzer.py`) — WORKED: but LLM still uses "colleague" as fallback
  4. **Pronunciation whitelist additions** (`cmu_proposer.py`) — WORKED

- Attempt 4: Three fixes — **NONE took effect on the actual problem**
  1. **STEP 5.8 same-name dedup** (`src/agents/characters.py:1476-1494`) — Targeted supporting→main promotion, but duplicate Ted comes from STEP 5.8.6 narrator fallback
  2. **"victim" added to `_ADVERSARIAL_LABELS`** (`src/analyzer.py:2134`) — Correct addition, but AM's outgoing labels are mostly "colleague" not "victim", so threshold not met
  3. **Self-relationship filter** (`src/analyzer.py`) — May have worked (no self-relationships visible), but didn't address core issues

- Attempt 6: Two fixes (awaiting verification)
  1. **ACTIVE vs PASSIVE adversarial labels** (`src/analyzer.py:2177-2213`) — False-antagonist correction now uses `_ACTIVE_ADVERSARIAL_LABELS` (no "enemy"/"victim") so Ellen/Nimdok/Gorrister (who only have "enemy"/"victim" labels) are correctly relabeled to "protagonist"
  2. **Consistency enforcement for colleague labels** (`src/analyzer.py:2215-2285`) — If antagonist has ≥2 active adversarial labels to protagonists but some "colleague" labels, replace "colleague" with dominant active label; same for inverse protagonist→antagonist direction
  - Root cause: `_ADVERSARIAL_LABELS` included "enemy" and "victim" (passive labels), blocking false-antagonist correction for victim characters
  - Smoke test: 332 tests pass

- Attempt 5: Four fixes — **3 of 4 worked**
  1. **STEP 5.2b placeholder→existing merge** (`src/agents/characters.py`) — WORKED: No duplicate Ted
  2. **Incoming adversarial label check** (`src/analyzer.py`) — WORKED: AM now correctly "antagonist"
  3. **False antagonist correction** (`src/analyzer.py`) — PARTIALLY WORKED: Benny corrected to "protagonist", but Ellen/Nimdok/Gorrister still "antagonist" because they have adversarial-looking labels (enemy, victim)
  4. **Self-alias filter** (`src/agents/characters.py:_is_valid_alias`) — WORKED: No AM self-alias

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 2 | Dup Benny | characters.py (Pass -1 dedup) | Fixed |
| 2 | Wrong narrator | characters.py (vocative + STEP 4.5b) | Fixed but introduced dup Ted |
| 2 | Pronunciation FPs | cmu_proposer.py, enricher.py | Partially fixed |
| 3 | Dup Ted | characters.py (STEP 5.8.5b same-name guard) | No change — wrong code path |
| 3 | AM wrong role | analyzer.py (post-profile adversarial role correction) | No change — "victim" not in label set |
| 3 | Relationship vocab | analyzer.py (captor/prisoner/tormentor/victim labels) | Fixed vocab but LLM ignores it |
| 3 | Pronunciation FPs | cmu_proposer.py (7 more words whitelisted) | Fixed |
| 4 | Dup Ted | characters.py (STEP 5.8 promotion dedup) | No change — wrong code path AGAIN |
| 4 | AM wrong role | analyzer.py ("victim" in _ADVERSARIAL_LABELS) | No change — AM labels are "colleague" not "victim" |
| 4 | Self-relationship | analyzer.py (post-profile filter) | Likely worked (no self-rels visible) |
| 5 | Dup Ted | characters.py (STEP 5.2b placeholder merge) | **Fixed** |
| 5 | AM wrong role | analyzer.py (incoming adversarial check) | **Fixed** — AM now "antagonist" |
| 5 | False antagonist | analyzer.py (zero adversarial evidence check) | **Partial** — Benny fixed, Ellen/Nimdok/Gorrister still "antagonist" |
| 5 | AM self-alias | characters.py (_is_valid_alias) | **Fixed** |
| 6 | Ellen/Nimdok/Gorrister wrong role | analyzer.py (ACTIVE vs PASSIVE adversarial labels) | Pending |
| 6 | AM→Nimdok/Benny "colleague" | analyzer.py (consistency enforcement) | Pending |

## Next Action
Re-run analysis to verify fixes from attempt 6.

## Output Files
- HTML: ../output/i_have_no_mouth/report.html
- JSON: ../output/i_have_no_mouth/analysis.json

## Pipeline Notes
- Attempt 5 analysis completed successfully in 19m 8s
- Model: qwen3-next:80b-a3b-instruct-q8_0 (all agents)
- 6 characters total (Ted, AM, Ellen, Nimdok, Gorrister, Benny) — duplicate Ted fixed
- AM has alias "I Am" — self-alias filter working
- Ted correctly identified as first-person narrator
- 16 pronunciation flags — all reasonable
- Contradictory relationship pairs removed: AM↔Nimdok tormentor, AM↔Benny tormentor
