# Current Evaluation State

## Active Text
- **Name:** i_have_no_mouth
- **Attempt:** 9
- **Phase:** awaiting_evaluation
- **baseline_score:** 6.35
- **Competitive Mode:** none

## Latest Scores
(Awaiting evaluation — attempt 9)

**Pass Criteria:** ALL categories must be >= 8.0

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
| 9 | TBD | TBD | AM "colleague" → "captor"/"tormentor" fix applied. ⚠️ WARNING: Ellen detected as narrator (not Ted) — possible regression |

## Pipeline Notes (Attempt 9)
- Analysis completed in 20m 23s
- 6 characters found: AM (77), Ellen (30), Nimdok (17), Gorrister (29), Benny (35), + 1 more (Ted?)
- ⚠️ **POSSIBLE REGRESSION**: "Narrator (from V2 pipeline): Ellen" — Ted was narrator in attempt 8
- "Detected narrator: Ellen (first-person)" — LLM narrator detection said Ellen
- "No definitive narrator identified from plot summary" — final step
- Contradictory relationship removed: AM→Gorrister=victim AND Gorrister→AM=victim
- All alias blocks look correct (pronouns, hallucinated aliases, comma phrases)

## Current Issues (Priority Order)

### HIGH
1. **AM's relationships to Ellen, Nimdok, Gorrister, Benny are all "colleague"** [Profiles — Relationships]
   - Fix applied in attempt 9: post-profile colleague→role-appropriate label replacement
   - Check if fix worked

2. **Possible narrator regression: Ellen instead of Ted** [Character Extraction]
   - Attempt 8 fixed Ted detection via vocative expansion
   - But this run says "Narrator (from V2 pipeline): Ellen"
   - Check the JSON output to confirm narrator assignment

### MEDIUM
3. **Summary uses "first-person narrator" instead of "Ted"** [Summaries — Accuracy]
   - Score impact: ~0.5 points on summaries (already at 8, so not blocking).

4. **No speech patterns noted for any character** [Profiles — Completeness]
   - AM's distinctive speech style not captured.
   - Score impact: ~0.5 points on profiles.

5. **Ellen→Gorrister: "victim of abuse"** [Profiles — Accuracy]
   - No clear textual evidence.
   - Score impact: Minor.

### LOW
6. **Chapter title is null** [Structure]
   - Single section has `title: null`.
   - Not blocking.

7. **No aliases for any character** [Character Extraction — Alias Grouping]
   - AM could have "Allied Mastercomputer" as an alias.
   - Not blocking.

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
  1. **ACTIVE vs PASSIVE adversarial labels** (`src/analyzer.py:2177-2213`) — Code correctly separates label sets, BUT has semantic direction bug: checks outgoing relationship values for "tormentor" (an active label), not realizing that outgoing "tormentor" means "my target IS a tormentor" (I'm the victim), not "I am a tormentor"
  2. **Consistency enforcement for colleague labels** (`src/analyzer.py:2215-2285`) — Depends on correct role assignment which didn't happen, so consistency enforcement had no effect

- Attempt 7: Direction-aware aggressor labels fix — **Did NOT fix roles**
  1. **Direction-aware _OUTGOING_AGGRESSOR_LABELS + _INCOMING_AGGRESSOR_LABELS** (`src/analyzer.py:2184-2223`) — Code is correct in principle, but threshold `_own_adv == 0` is too strict. All 4 humans have exactly 1 "victim" match from mercy killing relationships, so _own_adv=1 and correction doesn't fire.
  2. **New regression**: Ted replaced by "the ice caverns" — model-dependent output variation, not caused by code change

- Attempt 8: Two robustness fixes — **BOTH WORKED**
  1. **STEP 4.25b: narrator vocative check expansion** (`src/agents/characters.py:829-874`) — Ted restored as narrator. Fixed.
  2. **False-antagonist threshold raised** (`src/analyzer.py:2218`) — All 4 humans now correctly "protagonist". Fixed.

- Attempt 9: Colleague label replacement for antagonist↔protagonist relationships
  1. **Post-profile colleague→role-appropriate label replacement** (`src/analyzer.py`) — TBD (awaiting evaluation)

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
| 6 | Ellen/Nimdok/Gorrister/Benny wrong role | analyzer.py (ACTIVE vs PASSIVE adversarial labels) | **No change** — semantic direction bug |
| 6 | AM→Nimdok/Benny "colleague" | analyzer.py (consistency enforcement) | **No change** — depends on correct roles |
| 7 | Benny/Gorrister/Ellen/Nimdok wrong role | analyzer.py (direction-aware labels) | **No change** — threshold too strict (_own_adv==0 vs ==1 from mercy kills) |
| 7 | Ted missing / "the ice caverns" narrator | NEW REGRESSION | Model output variation — Ted not extracted |
| 8 | Ted missing / wrong narrator | characters.py (STEP 4.25b vocative expansion) | **Fixed** |
| 8 | Benny/Gorrister/Ellen/Nimdok wrong role | analyzer.py (threshold <=1) | **Fixed** |
| 9 | AM "colleague" → "captor"/"tormentor" | analyzer.py (post-profile colleague replacement) | TBD |

## Next Action
Evaluate attempt 9 output. Check: (1) AM relationship labels, (2) narrator assignment (Ellen vs Ted).

## Output Files
- HTML: ../output/i_have_no_mouth/report.html
- JSON: ../output/i_have_no_mouth/analysis.json
