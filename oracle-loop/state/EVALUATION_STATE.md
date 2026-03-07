# Current Evaluation State

## Active Text
- **Name:** i_have_no_mouth
- **Attempt:** 6
- **Phase:** awaiting_fix
- **baseline_score:** 6.35

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 10/10 ✓
  - Completeness: 10/10
  - Identity Resolution: 10/10
  - Alias Grouping: 10/10
- Character Profiles: 6/10 ✗ (FAILING)
- Chapter Summaries: 8/10 ✓
- Pronunciation Guide: 9/10 ✓
- HTML Presentation: 9/10 ✓
- **Overall: 8.4/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (Character Profiles below threshold)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.35 | 0 | Baseline - duplicate Benny, wrong narrator, profile errors |
| 2 | 7.3 | +0.95 | Benny dedup fixed, narrator=Ted, but duplicate Ted appeared, profiles improved |
| 3 | 7.8 | +1.45 | Relationship vocab improved, pronunciation fixed, but duplicate Ted and AM role fixes didn't work |
| 4 | 7.6 | +1.25 | Fixes did NOT take effect — duplicate Ted persists, AM still "protagonist" |
| 5 | 8.1 | +1.75 | Dup Ted FIXED, AM now antagonist, self-alias fixed. But 3 humans wrongly labeled antagonist |
| 6 | 8.4 | +2.05 | ACTIVE/PASSIVE fix did NOT work — semantic direction bug. 4 humans still "antagonist" |

## Current Issues (Priority Order)

### CRITICAL
1. **Benny, Gorrister, Ellen, Nimdok all wrongly labeled "antagonist"** [Profiles — Role Assignment]
   - Problem: 4 of 5 human victims are labeled "antagonist". Only Ted is correctly "protagonist". All four are fellow prisoners/victims of AM, not antagonists.
   - Root cause: **Semantic direction bug in false-antagonist correction** (analyzer.py:2192-2213). The code checks outgoing relationship VALUES for `_ACTIVE_ADVERSARIAL_LABELS` (which includes "tormentor", "captor", etc.). But when Benny has `relationships["AM"] = "tormentor"`, it means AM is Benny's tormentor — Benny is the VICTIM. The code wrongly counts "tormentor" in the outgoing value as evidence that Benny is adversarial.
   - The relationship dict convention is `relationships[target_name] = label_describing_what_target_is_to_me`. So:
     - Outgoing "tormentor" = "my target is my tormentor" → I am a victim (NOT aggressor evidence)
     - Outgoing "victim" = "my target is my victim" → I am the aggressor (IS aggressor evidence)
   - All 4 humans have `relationships["AM"] = "tormentor"`, so `_own_adv >= 1` for all of them, blocking the correction.
   - **Fix: Use direction-aware label sets:**
     - `OUTGOING_AGGRESSOR_LABELS = {"victim", "prisoner", "captive", "subordinate", "target", "prey", "servant"}` — labels that describe the TARGET as being beneath/harmed by the character
     - `INCOMING_AGGRESSOR_LABELS = {"tormentor", "captor", "oppressor", "persecutor", "jailer", "warden", "abuser", "enslaver", "tyrant", "predator", "antagonist", "villain"}` — labels that OTHERS apply to describe THIS character as the aggressor
     - `_own_adv` should use `OUTGOING_AGGRESSOR_LABELS` (checking the character's outgoing values)
     - `_in_adv` should use `INCOMING_AGGRESSOR_LABELS` (checking what others label this character as)
   - Verification: With this fix:
     - AM: _own_adv=5 ("victim" x5, in OUTGOING set), _in_adv=4 ("tormentor" x4, in INCOMING set) → stays antagonist ✓
     - Benny: _own_adv=0 ("romantic interest", "tormentor" — neither in OUTGOING set), _in_adv=0 (AM labels Benny as "victim" — not in INCOMING set) → relabeled protagonist ✓
     - Same logic applies to Gorrister, Ellen, Nimdok → all relabeled protagonist ✓
   - Location: `src/analyzer.py:2180-2213` — replace single `_ACTIVE_ADVERSARIAL_LABELS` with two direction-aware sets

### MEDIUM
2. **"Ellen is physically abused by Gorrister" — hallucinated evidence** [Profiles — Evidence]
   - Problem: Evidence item ev-4-4 claims Gorrister physically abuses Ellen. This is not in the source text. The humans are all victims of AM, not of each other.
   - Severity: Medium — single hallucinated evidence item, not blocking the 8.0 threshold by itself.

3. **Ted and AM have no physical description** [Profiles — Descriptions]
   - Ted: first-person narrator rarely describes himself — expected limitation
   - AM: a computer/AI — the text describes AM's internal environment, not AM's physical form
   - Severity: Medium — not fixable without hallucinating content

4. **Gorrister→Ted: "colleague" label** [Profiles — Relationships]
   - "Fellow prisoner" or "fellow victim" would be more accurate than "colleague"
   - Severity: Medium — cosmetic, not blocking

### LOW
5. **Chapter title is null** [Structure]
   - Single section has `title: null` — could display the story title
   - Not blocking — single-section detection is correct

6. **Summary minor inaccuracy: Benny "obliterated" at memory cube** [Summaries]
   - Summary says Benny was "obliterated" (killed) by AM at the memory cube. In the text, Benny is blinded but survives; he is killed later by Ted in the mercy killing.
   - Severity: Low — the overall arc is correct, but this detail conflates two events

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
  3. **False antagonist correction** (`src/analyzer.py`) — PARTIALLY WORKED: Benny corrected to "protagonist", but Ellen/Nimdok/Gorrister still "antagonist" because they have adversarial-looking labels (enemy, victim)
  4. **Self-alias filter** (`src/agents/characters.py:_is_valid_alias`) — WORKED: No AM self-alias

- Attempt 6: Two fixes — **Neither took effect**
  1. **ACTIVE vs PASSIVE adversarial labels** (`src/analyzer.py:2177-2213`) — Code correctly separates label sets, BUT has semantic direction bug: checks outgoing relationship values for "tormentor" (an active label), not realizing that outgoing "tormentor" means "my target IS a tormentor" (I'm the victim), not "I am a tormentor"
  2. **Consistency enforcement for colleague labels** (`src/analyzer.py:2215-2285`) — Depends on correct role assignment which didn't happen, so consistency enforcement had no effect

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
| 6 | Ellen/Nimdok/Gorrister/Benny wrong role | analyzer.py (ACTIVE vs PASSIVE adversarial labels) | **No change** — semantic direction bug: outgoing "tormentor" means target is my tormentor, not I am a tormentor |
| 6 | AM→Nimdok/Benny "colleague" | analyzer.py (consistency enforcement) | **No change** — depends on correct roles |

## Next Action
Run PROMPT_fix.md to fix the semantic direction bug in false-antagonist correction (Critical #1). Replace single `_ACTIVE_ADVERSARIAL_LABELS` with two direction-aware sets: `_OUTGOING_AGGRESSOR_LABELS` for checking what a character labels their targets as (aggressor evidence = "victim", "prisoner", etc.) and `_INCOMING_AGGRESSOR_LABELS` for checking what others label this character as (aggressor evidence = "tormentor", "captor", etc.).

## Output Files
- HTML: ../output/i_have_no_mouth/report.html
- JSON: ../output/i_have_no_mouth/analysis.json

## Pipeline Notes
- Attempt 6 analysis completed successfully in 16m 6s
- Model: qwen3-next:80b-a3b-instruct-q8_0 (all agents)
- 6 characters total (AM, Benny, Gorrister, Ellen, Nimdok, Ted) — narrator Ted correctly identified
- 16 pronunciation flags
- Relationship data in analysis.json is exported as strings (target names only), not dicts — relationship types are only visible in HTML
