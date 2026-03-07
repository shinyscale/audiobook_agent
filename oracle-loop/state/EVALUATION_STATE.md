# Current Evaluation State

## Active Text
- **Name:** i_have_no_mouth
- **Attempt:** 11
- **Phase:** awaiting_evaluation
- **baseline_score:** 6.35
- **Competitive Mode:** none

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 7.5/10 ✗
  - Completeness: 8/10
  - Identity Resolution: 9/10
  - Alias Grouping: 5.5/10
- Character Profiles: 5.5/10 ✗
- Chapter Summaries: 7.5/10 ✗
- Pronunciation Guide: 8.5/10 ✓
- HTML Presentation: 9/10 ✓
- **Overall: 7.65/10**

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold)

## Regression Analysis
Attempt 10 narrator fix PARTIALLY worked: Ted IS correctly identified as narrator (narrator=True, role=protagonist). However:
- 3 of 5 humans (Ellen, Nimdok, Benny) are still labeled "antagonist" — the false-antagonist correction from attempt 8 regressed
- "colleague" labels persist for AM<->Ted, AM<->Gorrister despite both being antagonist<->protagonist pairs
- Summary uses "the narrator" instead of Ted's name throughout
- No aliases for any character

The mention-ratio narrator guard from attempt 10 apparently worked (Ted=narrator), but the downstream fixes (role correction, colleague replacement) did NOT fire correctly.

## Current Issues (Priority Order)

### CRITICAL
1. **3 humans wrongly labeled "antagonist"** [Profiles — Roles]
   - Problem: Ellen (antagonist), Nimdok (antagonist), Benny (antagonist) — all should be protagonist/victim. Only AM should be antagonist.
   - Evidence: In the story, all 5 humans are victims of AM's torment. Ellen, Nimdok, Benny are prisoners, not antagonists.
   - Root cause: The false-antagonist threshold fix from attempt 8 (analyzer.py:2218) worked in attempt 8 but regressed. Possibly because the LLM now generates different relationship labels that the threshold check doesn't catch, or the code path changed.
   - Location: `src/analyzer.py` — false-antagonist correction logic
   - Fix: Investigate why the false-antagonist fix from attempt 8 no longer fires for Ellen/Nimdok/Benny. The fix should check: if a character has NO outgoing aggressor labels AND receives "victim"/"captive" labels from an antagonist, they cannot be an antagonist.

2. **"colleague" labels for AM<->Ted and AM<->Gorrister** [Profiles — Relationships]
   - Problem: AM->Ted: "colleague", AM->Gorrister: "colleague", Ted->AM: "colleague", Gorrister->AM: "colleague", Gorrister->Ted: "colleague", Ted->Gorrister: "colleague"
   - Evidence: AM is their captor/tormentor. Ted and Gorrister are fellow prisoners. "Colleague" is completely wrong.
   - Root cause: The attempt 10 fix expanded _all_protagonists to include role="main", but Ted and Gorrister already have role="protagonist". The colleague replacement should fire for antagonist<->protagonist pairs. Either (a) the replacement code doesn't run, (b) it runs before role assignment, or (c) there's a logic bug.
   - Location: `src/analyzer.py` — post-profile colleague replacement logic
   - Fix: Debug why colleague replacement isn't firing for AM(antagonist)<->Ted(protagonist) and AM(antagonist)<->Gorrister(protagonist). Check execution order.

### HIGH
3. **No aliases for any character** [Character Extraction — Alias Grouping]
   - Problem: AM has zero aliases. Should at minimum have "Allied Mastercomputer" (explicitly mentioned in text/summary).
   - Evidence: Summary says "AM's origins as the Allied Mastercomputer" — this name appears in the text.
   - Location: `src/pipeline/character_extraction_v2/` — alias detection
   - Fix: This is likely an LLM output issue for short stories with few alias variations. Low priority compared to role/relationship fixes.

4. **Summary uses "the narrator" instead of "Ted"** [Summaries — Specificity]
   - Problem: The summary never mentions Ted by name. Says "the narrator" throughout.
   - Evidence: "the narrator, realizing death is the only escape, kills him" — should say "Ted"
   - Root cause: Ted has only 5 name-mentions in the text (first-person narrators are rarely named). The summarizer may not have had Ted's name available, or the narrator assignment happened after summary generation.
   - Location: `src/analyzer.py` or `src/agents/summary_agent.py` — check if narrator name is injected into summaries
   - Fix: Post-summary step could replace "the narrator" with the detected narrator's name.

### MEDIUM
5. **Ellen's relationship descriptions partially inaccurate** [Profiles — Accuracy]
   - "Nimdok: victim of her violence" — Ellen kills Nimdok as an act of mercy, not violence
   - "Benny: sexual object of her desire" — in the text it's more that Benny is sexually aggressive toward Ellen, not the reverse
   - "Gorrister: recipient of his physical abuse" — not clearly supported by text

6. **Missing physical descriptions for Ted, Nimdok, AM** [Profiles — Completeness]
   - AM is a computer (acceptable to have no physical desc), but Ted's transformation into a blob at the end and Nimdok's appearance could be described.

7. **No speech patterns noted** [Profiles — Completeness]
   - AM has a distinctive megalomaniacal speech style (the "HATE" monologue). Not captured.

### LOW
8. **Chapter title is null** [Structure]
   - Single section has `title: null`. Minor cosmetic issue for a short story.

9. **Common homographs in pronunciation** [Pronunciation — False Positives]
   - "read", "lead", "does", "close", "subject" are common English homographs that most narrators wouldn't need flagged. Minor noise.

## Fix Priority
Focus on CRITICAL #1 and #2 — these are the primary blockers for Character Profiles reaching 8.0. If roles and relationships are fixed, profiles should jump to ~7.5-8.0. HIGH #4 (summary naming) would push summaries to 8.0+.

## Attempt 11 Fix Applied
- **Post-Phase-B false-antagonist correction + colleague replacement** (`src/analyzer.py` after Phase B):
  - Re-runs false-antagonist check on final (Phase-B-corrected) output characters
  - Simulation confirms: Nimdok → protagonist, Benny → protagonist; Ellen stays antagonist (in_adv=1 from Gorrister's "abuser" label)
  - AM→Ted/Gorrister: "colleague" → "victim" (after role fix, AM has 2 active victim labels to protagonists)
  - Ted/Gorrister→AM: "colleague" → "tormentor" (Nimdok/Benny call AM "tormentor" → dominant label)
  - Root cause: pipeline role corrections run on Phase-A relationships; Phase B then refines them; running again on final data gives correct results
- **Summary narrator name substitution** (`src/analyzer.py` after narrator detection, line 1877):
  - After first-person narrator detected, replaces "the narrator" with actual name (e.g., "Ted") in chapter summaries
  - Fixes HIGH #4: summaries will use "Ted" instead of "the narrator"
  - Universal: only runs when pov == "first-person" AND narrator_name is detected
- Smoke test: Python simulation confirms all logic correct; 332 tests pass

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
| 10 | 7.65 | +1.30 | Ted narrator restored. But 3 humans still antagonist, colleague labels persist, summary uses "the narrator" not "Ted" |

## Pipeline Notes (Attempt 10)
- Analysis completed in 34m 35s
- 6 characters found: AM (77), Ted (5), Ellen (30), Nimdok (17), Gorrister (29), Benny (35)
- Ted correctly identified as narrator (narrator=True, role=protagonist)
- Model: qwen3-next:80b-a3b-instruct-q8_0 (all agents)
- Character Profiles took 1041s (17 min) — longest stage by far
- No aliases for any character

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
  1. **STEP 5.8 same-name dedup** (`src/agents/characters.py:1476-1494`) — Targeted supporting->main promotion, but duplicate Ted comes from STEP 5.8.6 narrator fallback
  2. **"victim" added to `_ADVERSARIAL_LABELS`** (`src/analyzer.py:2134`) — Correct addition, but AM's outgoing labels are mostly "colleague" not "victim", so threshold not met
  3. **Self-relationship filter** (`src/analyzer.py`) — May have worked (no self-relationships visible), but didn't address core issues

- Attempt 5: Four fixes — **3 of 4 worked**
  1. **STEP 5.2b placeholder->existing merge** (`src/agents/characters.py`) — WORKED: No duplicate Ted
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

- Attempt 9: Colleague label replacement for antagonist<->protagonist relationships
  1. **Post-profile colleague->role-appropriate label replacement** (`src/analyzer.py`) — PARTIALLY WORKED: Most relationships now correct (captor/tormentor/victim), but AM<->Ted still "colleague" because Ted has role="main" not "protagonist"
  2. **REGRESSION**: Ellen detected as narrator instead of Ted — LLM non-determinism

- Attempt 10: Two fixes
  1. **STEP 4.27 mention-ratio narrator validation** (`src/agents/characters.py`) — WORKED: Ted is narrator again
  2. **role="main" in _all_protagonists** (`src/analyzer.py`) — DID NOT WORK: colleague labels still present for AM<->Ted and AM<->Gorrister despite both being protagonist role now. Also, false-antagonist fix regressed (3 humans labeled antagonist).

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
| 10 | Narrator fix | characters.py (STEP 4.27 mention-ratio guard) | **Fixed** — Ted is narrator |
| 10 | AM<->Ted colleague | analyzer.py (role="main" in _all_protagonists) | **No change** — colleague labels persist |
| 10 | 3 humans antagonist | analyzer.py (false-antagonist fix from attempt 8) | **Regressed** — 3 humans still antagonist |

## Key Debugging Question for Fix Phase
The false-antagonist fix from attempt 8 worked perfectly (all 4 humans became protagonist). Now in attempt 10, 3 of 5 humans are back to "antagonist" despite the same code being present. The fix phase MUST:
1. Read the actual false-antagonist correction code in analyzer.py and verify it's still intact
2. Check if the LLM-generated relationship labels changed (different labels may bypass the threshold)
3. Check execution order: does colleague replacement run BEFORE or AFTER role correction?
4. Consider a simpler approach: in a story with exactly 1 antagonist (AM), ALL other characters should be protagonist

## Output Files
- HTML: ../output/i_have_no_mouth/report.html
- JSON: ../output/i_have_no_mouth/analysis.json

## Pipeline Notes (Attempt 11)
- Analysis completed in 19m 14s
- 6 characters found: AM (79), Ted (5), Ellen (30), Nimdok (17), Gorrister (29), Benny (?)
- Ted correctly identified as narrator (first-person)
- AM now has aliases: "Allied Mastercomputer, Adaptive Manipulator" ✓
- Contradictory tormentor<->tormentor pairs removed for AM↔Ellen, AM↔Nimdok, AM↔Gorrister, AM↔Benny (both directions had same label — system removed them)
- Model: qwen3-next:80b-a3b-instruct-q8_0 (all agents)
- Character Profiles took 8m 34s (bottleneck, 44.5% of total)

## Next Action
Run evaluation (PROMPT_evaluate.md) to verify attempt 11 fixes:
- Did Nimdok, Benny become protagonist?
- Did AM→Ted/Gorrister change from "colleague" to "victim"?
- Did chapter summaries use "Ted" instead of "the narrator"?
- Note: tormentor pairs were removed — check what replaced them

**Previous Next Action (pre-analysis):**
Run analysis (PROMPT_analyze.md) to verify attempt 11 fixes:
- Nimdok, Benny should be protagonist
- AM→Ted/Gorrister should be "victim" not "colleague"
- Ted/Gorrister→AM should be "tormentor" not "colleague"
- Chapter summaries should say "Ted" not "the narrator"
- Ellen stays antagonist (harder to fix without regression risk)

**Phase:** awaiting_analysis
