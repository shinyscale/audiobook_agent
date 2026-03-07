# Current Evaluation State

## Active Text
- **Name:** i_have_no_mouth
- **Attempt:** 9
- **Phase:** awaiting_analysis
- **baseline_score:** 6.35
- **Competitive Mode:** none

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 6.5/10 ✗
  - Completeness: 8/10
  - Identity Resolution: 7/10
  - Alias Grouping: 7/10
- Character Profiles: 6.5/10 ✗
- Chapter Summaries: 5.5/10 ✗
- Pronunciation Guide: 8.5/10 ✓
- HTML Presentation: 9/10 ✓
- **Overall: 7.25/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold)

## Regression Analysis
Attempt 8 scored 8.50 with only profiles failing. Attempt 9 **regressed** because the LLM detected Ellen as narrator instead of Ted. This is the same non-deterministic narrator detection issue seen in attempt 7 ("the ice caverns" replacing Ted). The colleague label fix in analyzer.py DID partially work (most relationships now say captor/tormentor/victim instead of colleague), but the narrator regression overwhelms the improvement.

**Key cascade**: Wrong narrator (Ellen) → summary attributes Ted's climactic actions to Ellen → Ted demoted to supporting_0 with 5 mentions → Ted's profile is thin → AM↔Ted relationships still "colleague" (fix only targets antagonist↔protagonist pairs, but Ted has role="main" not "protagonist")

## Current Issues (Priority Order)

### CRITICAL
1. **REGRESSION: Ellen detected as narrator instead of Ted** [Character Extraction — Identity Resolution]
   - Problem: "Detected narrator: Ellen (first-person)" in analysis logs. Ted is the actual first-person narrator of the story.
   - Evidence: Ted narrates the entire story ("I" = Ted). Ellen is a character Ted describes. The summary says "Ellen kills Benny, Gorrister, Ellen, and Nimdok" — Ellen killing herself is nonsensical; it's Ted who performs the mercy killing.
   - Root cause: LLM non-determinism in narrator detection. This same class of issue appeared in attempt 7 (Ted replaced by "the ice caverns"). The STEP 4.25b vocative expansion fix from attempt 8 should catch this but apparently didn't fire this time.
   - Impact: Cascades into summaries (wrong protagonist), profiles (Ted deprioritized), and relationships (Ted not treated as protagonist).
   - Location: `src/agents/characters.py` — narrator detection logic (STEP 4.25b, STEP 5.8.6)
   - Fix approach: The narrator detection needs to be MORE ROBUST against LLM variation. Consider: (a) hardening the vocative check to be more aggressive, (b) adding a post-hoc validation that checks if the detected narrator appears as "I" in the actual text, (c) if a character has very few explicit name mentions but the text is first-person, they're likely the narrator (Ted has 5 mentions in a first-person story — classic narrator pattern).

2. **Summary attributes Ted's actions to Ellen** [Summaries — Accuracy]
   - Problem: Summary says "Ellen to kill Benny, Gorrister, Ellen, and Nimdok with ice spears" — Ellen killing herself is self-contradictory. Actually Ted kills the others.
   - Evidence: In the story, Ted (narrator) performs the mercy killing with Ellen's brief help, then AM transforms Ted (not Ellen) into the blob.
   - Root cause: Downstream of narrator misidentification. If narrator = Ellen, the LLM attributes all first-person actions to Ellen.
   - Score impact: Drops summaries from ~8 to 5.5.

### HIGH
3. **AM→Ted and Ted→AM relationships still "colleague"** [Profiles — Relationships]
   - Problem: The colleague→role-appropriate fix only fires for antagonist↔protagonist pairs. Ted has role="main" (not "protagonist"), so the fix doesn't apply to him.
   - Evidence: AM→Ted: "colleague", Ted→AM: "colleague". All other AM↔human relationships correctly say "victim"/"tormentor"/"captor".
   - Location: `src/analyzer.py` — post-profile colleague replacement logic
   - Fix approach: The colleague replacement should also apply when one character is antagonist and the other has role="main" or is the narrator character.

4. **Ted has no physical description or meaningful profile** [Profiles — Completeness]
   - Problem: Ted is supporting_0 with role="main", no physical_description, generic relationships.
   - Root cause: Downstream of narrator misidentification — Ted treated as minor character.
   - Fix: Fixing narrator detection (CRITICAL #1) should fix this automatically.

### MEDIUM
5. **Ellen→Gorrister: "victim of physical abuse by"** [Profiles — Accuracy]
   - Not clearly supported by the text. May be a hallucinated relationship.

6. **No aliases for any character** [Character Extraction — Alias Grouping]
   - AM could have "Allied Mastercomputer" as alias. Minor issue.

7. **No speech patterns noted** [Profiles — Completeness]
   - AM has a distinctive megalomaniacal speech style. Not captured.

### LOW
8. **Chapter title is null** [Structure]
   - Single section has `title: null`. Minor cosmetic issue.

## Fix Priority
The CRITICAL issue is narrator detection robustness. This is the THIRD time narrator detection has been unreliable (attempt 7: Ted→ice caverns, attempt 9: Ted→Ellen). The fix must make narrator detection deterministic or add stronger fallback logic. Since the text analysis itself is non-deterministic (LLM-based), the post-extraction narrator validation needs to be hardened.

**Suggested approach**: After all narrator detection heuristics run, add a validation step: if the detected narrator has many explicit name mentions (>15) AND there exists a character with very few mentions (< 10) in a first-person text, the low-mention character is more likely the narrator (narrators use "I" not their own name). This pattern is universal, not novel-specific.

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.35 | 0 | Baseline - duplicate Benny, wrong narrator, profile errors |
| 2 | 7.3 | +0.95 | Benny dedup fixed, narrator=Ted, but duplicate Ted appeared, profiles improved |
| 3 | 7.8 | +1.45 | Relationship vocab improved, pronunciation fixed, but duplicate Ted and AM role fixes didn't work |
| 4 | 7.6 | +1.25 | Fixes did NOT take effect — duplicate Ted persists, AM still "protagonist" |
| 5 | 8.1 | +1.75 | Dup Ted FIXED, AM now antagonist, self-alias fixed. But 3 humans wrongly labeled antagonist |
| 6 | 8.4 | +2.05 | ACTIVE/PASSIVE fix did NOT work — semantic direction bug. 4 humans still "antagonist" |
| 7 | 6.65 | +0.30 | REGRESSION: Ted missing (replaced by "the ice caverns"), 4 humans still antagonist |
| 8 | 8.50 | +2.15 | Ted restored, all roles correct. Only profiles failing (AM "colleague" labels) |
| 9 | 7.25 | +0.90 | REGRESSION: Ellen detected as narrator (not Ted). Colleague fix partially worked but narrator cascade drops 3 categories |

## Pipeline Notes (Attempt 9)
- Analysis completed in 20m 23s
- 6 characters found: AM (77), Ellen (30), Nimdok (17), Gorrister (29), Benny (35), Ted (5)
- REGRESSION: "Narrator (from V2 pipeline): Ellen" — Ted was narrator in attempt 8
- "Detected narrator: Ellen (first-person)" — LLM narrator detection said Ellen
- Contradictory relationship removed: AM→Gorrister=victim AND Gorrister→AM=victim
- Colleague fix DID work for most relationships (captor/tormentor/victim) but not AM↔Ted

## Fix History
- Attempt 2: Three connected fixes for character extraction and pronunciation
  1. **Exact-name dedup in `_merge_within_main_cast`** (`src/agents/characters.py` Pass -1) — Fixed Benny duplicate
  2. **Vocative pattern + narrator fallback** (`src/agents/characters.py`) — Fixed narrator detection but introduced duplicate Ted
  3. **Pronunciation fixes** (`cmu_proposer.py`, `enricher.py`) — Partially fixed false positives

- Attempt 3: Four fixes (two didn't take effect)
  1. **STEP 5.8.5b same-name guard** (`src/agents/characters.py`) — Code is correct but targets wrong path; duplicate Ted comes from STEP 5.8.6
  2. **Post-profile adversarial role correction** (`src/analyzer.py`) — Code is correct but `_ADVERSARIAL_LABELS` doesn't include "victim"
  3. **Relationship vocabulary expanded** (`src/analyzer.py`) — WORKED: but LLM still uses "colleague" as fallback
  4. **Pronunciation whitelist additions** (`cmu_proposer.py`) — WORKED

- Attempt 4: Three fixes — **NONE took effect on the actual problem**
  1. **STEP 5.8 same-name dedup** (`src/agents/characters.py:1476-1494`) — Targeted supporting→main promotion, but duplicate Ted comes from STEP 5.8.6 narrator fallback
  2. **"victim" added to `_ADVERSARIAL_LABELS`** (`src/analyzer.py:2134`) — Correct addition, but AM's outgoing labels are mostly "colleague" not "victim", so threshold not met
  3. **Self-relationship filter** (`src/analyzer.py`) — May have worked (no self-relationships visible), but didn't address core issues

- Attempt 5: Four fixes — **3 of 4 worked**
  1. **STEP 5.2b placeholder→existing merge** (`src/agents/characters.py`) — WORKED: No duplicate Ted
  2. **Incoming adversarial label check** (`src/analyzer.py`) — WORKED: AM now correctly "antagonist"
  3. **False antagonist correction** (`src/analyzer.py`) — PARTIALLY WORKED: Benny fixed, Ellen/Nimdok/Gorrister still "antagonist" because they have adversarial-looking labels (enemy, victim)
  4. **Self-alias filter** (`src/agents/characters.py:_is_valid_alias`) — WORKED: No AM self-alias

- Attempt 6: Two fixes — **Neither took effect**
  1. **ACTIVE vs PASSIVE adversarial labels** (`src/analyzer.py:2177-2213`) — Code correctly separates label sets, BUT has semantic direction bug
  2. **Consistency enforcement for colleague labels** (`src/analyzer.py:2215-2285`) — Depends on correct role assignment which didn't happen

- Attempt 7: Direction-aware aggressor labels fix — **Did NOT fix roles**
  1. **Direction-aware _OUTGOING_AGGRESSOR_LABELS + _INCOMING_AGGRESSOR_LABELS** (`src/analyzer.py:2184-2223`) — threshold too strict

- Attempt 8: Two robustness fixes — **BOTH WORKED**
  1. **STEP 4.25b: narrator vocative check expansion** (`src/agents/characters.py:829-874`) — Ted restored as narrator. Fixed.
  2. **False-antagonist threshold raised** (`src/analyzer.py:2218`) — All 4 humans now correctly "protagonist". Fixed.

- Attempt 9: Colleague label replacement for antagonist↔protagonist relationships
  1. **Post-profile colleague→role-appropriate label replacement** (`src/analyzer.py`) — PARTIALLY WORKED: Most relationships now correct (captor/tormentor/victim), but AM↔Ted still "colleague" because Ted has role="main" not "protagonist"
  2. **REGRESSION**: Ellen detected as narrator instead of Ted — LLM non-determinism, same class of issue as attempt 7

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
| 4 | Self-relationship | analyzer.py (post-profile filter) | Likely worked |
| 5 | Dup Ted | characters.py (STEP 5.2b placeholder merge) | **Fixed** |
| 5 | AM wrong role | analyzer.py (incoming adversarial check) | **Fixed** |
| 5 | False antagonist | analyzer.py (zero adversarial evidence check) | **Partial** |
| 5 | AM self-alias | characters.py (_is_valid_alias) | **Fixed** |
| 6 | Wrong roles | analyzer.py (ACTIVE vs PASSIVE labels) | **No change** — semantic direction bug |
| 6 | Colleague labels | analyzer.py (consistency enforcement) | **No change** |
| 7 | Wrong roles | analyzer.py (direction-aware labels) | **No change** — threshold too strict |
| 7 | Ted missing | NEW REGRESSION | Model output variation |
| 8 | Ted missing | characters.py (STEP 4.25b vocative expansion) | **Fixed** |
| 8 | Wrong roles | analyzer.py (threshold <=1) | **Fixed** |
| 9 | Colleague labels | analyzer.py (post-profile colleague replacement) | **Partial** — works for protagonist pairs, not for Ted (role="main") |
| 9 | Narrator regression | NEW REGRESSION | Ellen detected as narrator instead of Ted — LLM non-determinism |

## Next Action
Re-run analysis to verify fix. Two fixes applied:
1. STEP 4.27 (characters.py): Mention-ratio narrator validation — catches when assigned narrator has ≥15 mentions, another character has ≤7 mentions, with ≥3x discrepancy (Ellen=30, Ted=5 → ratio=6x → Ted correctly reassigned as narrator).
2. Expanded _all_protagonists (analyzer.py:2234): Now includes role="main" characters so AM↔Ted colleague labels are corrected alongside other antagonist↔protagonist pairs.
