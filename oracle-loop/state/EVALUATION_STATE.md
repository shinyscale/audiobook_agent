# Current Evaluation State

## Active Text
- **Name:** i_have_no_mouth
- **Attempt:** 14
- **Phase:** awaiting_evaluation
- **baseline_score:** 6.35
- **Competitive Mode:** none

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 6/10 ✗
  - Completeness: 6/10
  - Identity Resolution: 7/10
  - Alias Grouping: 5/10
- Character Profiles: 5.5/10 ✗
- Chapter Summaries: 7.5/10 ✗
- Pronunciation Guide: 7.5/10 ✗
- HTML Presentation: 8.5/10 ✓
- **Overall: 7.23/10**

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (4 categories below threshold: Character Extraction, Character Profiles, Chapter Summaries, Pronunciation Guide)

## Regression Analysis (Attempt 12 → 13)
The attempt 13 fixes (narrator role elevation, possessive sub-entity filter) **did NOT fire** due to LLM non-determinism:
- **Narrator role elevation:** Ted was NOT flagged as narrator this run. Instead, "the ice caverns" got `is_narrator=True`. The fix code is correct but didn't trigger because the wrong character was assigned narrator.
- **Possessive filter (STEP 5.9.2):** LLM used "the ice caverns" (no possessive "AM's"), bypassing the `{char}'s ` pattern match. The filter needs to be broader.

New regressions from LLM variation:
- "the ice caverns" is now NARRATOR (was just a spurious character before)
- "Huergelmir" (mythological bird) extracted as a character (4 mentions, role=protagonist)
- Gorrister role=antagonist (was protagonist in attempt 12)
- Summary uses "the narrator" instead of "Ted" (attempt 11 fixed this, regressed)

## Current Issues (Priority Order)

### CRITICAL
1. **"the ice caverns" is marked as narrator** [Extraction — False Narrator]
   - Problem: `the ice caverns` has `is_narrator=True, role=protagonist`. This is a location/setting, not a character, and definitely not the narrator. Ted (the actual first-person narrator) has `is_narrator=False, role=main`.
   - Evidence: The ice caverns are a place the characters travel to. Ted narrates the entire story in first person. "The ice caverns" has relationships like "comrade" to all humans — nonsense for a location.
   - Root cause: The narrator detection pipeline assigned narrator to the wrong entity. Ted only has 5 mentions (characters refer to themselves rarely in first-person), making him a weak candidate. The pipeline needs a guard: locations/settings should NEVER be assigned narrator status.
   - Location: `src/pipeline/character_extraction_v2/narrator.py` — narrator assignment logic
   - Fix approach (two-pronged):
     1. **Narrator exclusion filter:** Characters whose canonical_name starts with "the " followed by a common location/setting noun (caverns, caves, mountains, forest, room, house, etc.) should be excluded from narrator candidacy. More broadly: if a character has NO dialogue and name is a common noun phrase (starts with "the "), skip it.
     2. **Strengthen Ted detection:** The narrator in this story says "I" throughout. The pipeline should detect first-person narration and match the narrator to a named character who appears in self-referential contexts, not just by mention count.

2. **Ted is not narrator and has wrong role** [Extraction — Narrator Detection]
   - Problem: Ted has `is_narrator=False, role=main`. He should be `is_narrator=True, role=protagonist`.
   - Evidence: Ted narrates the entire story. "I am Ted" is in the text. Every first-person passage is Ted.
   - Root cause: Same as CRITICAL #1 — narrator assignment went to wrong entity, so Ted's narrator elevation never triggered.
   - Location: Same as CRITICAL #1
   - Fix: Fixing #1 should cascade to fixing this — if "the ice caverns" is excluded from narrator candidacy, Ted should be the next best candidate.

### HIGH
3. **"the ice caverns" and "Huergelmir" are false positive characters** [Extraction — False Positives]
   - Problem: Two non-character entities extracted:
     - "the ice caverns" (5 mentions, id=main_cast_9) — a location
     - "Huergelmir" (4 mentions, id=main_cast_7, aliases=["the bird"]) — a mythological creature AM creates as a torture device, not a character with agency/dialogue
   - Evidence: Ice caverns are a setting. Huergelmir is a supernatural phenomenon AM creates — more like a weapon than a character. Neither has dialogue.
   - Root cause: LLM extracts any frequently mentioned noun phrase as a character. The pipeline lacks post-extraction filtering for non-character entities.
   - Location: `src/agents/characters.py` — post-extraction filtering
   - Fix: Broaden the STEP 5.9.2 possessive filter to also catch:
     - Common-noun entities starting with "the " that are location/setting words (caverns, caves, forest, room, house, castle, city, etc.)
     - Entities with very low mentions (< 5) that have no dialogue and ALL relationships are generic ("colleague", "comrade")
   - Note: The possessive filter from attempt 12 only catches `{char}'s X` patterns. This run the LLM dropped the possessive, so a broader filter is needed.

4. **Gorrister role=antagonist** [Profiles — Wrong Role]
   - Problem: Gorrister has role=antagonist. He is one of the 5 human victims of AM — a fellow sufferer, not an antagonist.
   - Evidence: Gorrister is tormented by AM alongside the others. He has no antagonistic agency.
   - Root cause: The post-Phase-B role correction (attempts 8-12) should fix this, but may not be firing correctly this run. Gorrister's outgoing relationships include "victim" (to Benny) which may be triggering the false-antagonist heuristic.
   - Location: `src/analyzer.py` — post-Phase-B false-antagonist correction
   - Fix: Check why the false-antagonist correction didn't catch Gorrister. His profile has outgoing "victim" to Benny — but Gorrister IS the victim of Benny (Benny attacks Gorrister). The label direction may be confusing the heuristic.

5. **AM aliases completely missing** [Extraction — Alias Regression]
   - Problem: AM has zero aliases. The text explicitly states AM stands for "Allied Mastercomputer", "Adaptive Manipulator", "Aggressive Menace", and references "I think, therefore I AM."
   - Evidence: These are textually stated acronym expansions. Attempt 11 had them; attempts 12-13 lost them.
   - Root cause: LLM non-determinism in Pass 2 alias extraction.
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` — Pass 2
   - Fix: Programmatic acronym expansion detection: scan summary text for patterns like "stood for" / "stands for" / "short for" near character names and inject as aliases. This would be deterministic.

### MEDIUM
6. **Summary uses "the narrator" instead of "Ted"** [Summaries — Narrator Attribution]
   - Problem: Summary text says "the narrator recounts..." and "the narrator realizes..." instead of using Ted's name.
   - Evidence: Attempt 11 fixed this with narrator name substitution, but the fix depends on Ted being identified as narrator. Since Ted isn't narrator this run, the substitution doesn't fire.
   - Fix: Auto-resolves when CRITICAL #1-2 are fixed.

7. **Common homographs in pronunciation** [Pronunciation — False Positives]
   - "read", "lead", "does", "close", "subject" — 5 common English homographs most narrators wouldn't need flagged. 11 of 16 entries are genuinely useful.
   - Persistent issue across multiple attempts. LOW priority.

### LOW
8. **Chapter title is null** [Structure]
   - Single section with `title: null`. Cosmetic for a short story with no heading.

9. **No speech patterns noted** [Profiles — Completeness]
   - AM's megalomaniacal monologue and Ted's cynical narration not captured in profiles.

## Fix Priority
**CRITICAL #1 and #2 are the primary blockers.** They are the same root cause: narrator assigned to "the ice caverns" instead of Ted. Fixing narrator detection to exclude non-character entities would:
- Remove "the ice caverns" as narrator → Ted becomes narrator → role elevated to protagonist
- Summary narrator substitution fires → "Ted" instead of "the narrator"
- Character Profiles improve (correct narrator, correct role)
- Character Extraction improves (one fewer false positive)

**HIGH #3 is secondary.** A broader post-extraction filter for non-character entities (locations, mythological props) would remove both "the ice caverns" and "Huergelmir", cleaning up the character list and relationship noise.

**HIGH #4 (Gorrister role)** should auto-fix if the post-Phase-B correction runs correctly. May need investigation.

**HIGH #5 (AM aliases)** is LLM non-determinism. A programmatic acronym-expansion detector would help but adds complexity. Consider deferring if #1-3 are sufficient to pass.

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
| 11 | 8.30 | +1.95 | Major progress: Ellen/Benny protagonist, AM relationships fixed, aliases added, summary uses "Ted". Only Nimdok antagonist remains. |
| 12 | 8.20 | +1.85 | Nimdok FIXED to protagonist. But LLM regression: AM aliases lost, ice caverns spurious character, Ted role="minor" |
| 13 | 7.23 | +0.88 | REGRESSION: "the ice caverns" is narrator, Ted not narrator, Huergelmir false positive, Gorrister antagonist |

## Pipeline Notes (Attempt 13)
- Analysis completed in 20m 15s
- 8 characters found: AM (77), Ellen (30), Nimdok (17), Gorrister (29), Benny (35), Ted (5), Huergelmir (4), the ice caverns (5)
- "the ice caverns" incorrectly identified as narrator (is_narrator=True)
- Ted has is_narrator=False, role=main — narrator elevation fix didn't trigger
- Gorrister role=antagonist (wrong, should be protagonist)
- Huergelmir is a mythological bird reference, not a story character
- AM has NO aliases (regression persists from attempt 12)
- STEP 5.9.2 possessive filter didn't fire — LLM used "the ice caverns" not "AM's ice caverns"
- Model: qwen3-next:80b-a3b-instruct-q8_0 (all agents)
- Character Profiles bottleneck: 9m 48s (48.4% of total)

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

- Attempt 11: Two fixes — **MOSTLY WORKED**
  1. **Post-Phase-B role correction + colleague replacement** (`src/analyzer.py`) — WORKED for Ellen/Benny (protagonist) and AM->Ted/Gorrister (tormentor). Did NOT fix Nimdok (still antagonist, still "colleague" with AM).
  2. **Summary narrator name substitution** (`src/analyzer.py`) — WORKED: Summary uses "Ted" instead of "the narrator".

- Attempt 12: One fix — **WORKED but LLM regression on other fronts**
  1. **"fellow victim" guard in post-Phase-B false-antagonist check** (`src/analyzer.py`) — WORKED: Nimdok now protagonist, AM->Nimdok corrected. But LLM non-determinism caused: AM aliases lost, ice caverns character appeared, Ted role="minor".

- Attempt 13: Two fixes — **Neither took effect due to LLM variation**
  1. **Narrator role elevation** (`narrator.py:update_characters_with_narrator()`) — Code correct but didn't fire: Ted wasn't flagged as narrator (ice caverns was).
  2. **Possessive sub-entity filter (STEP 5.9.2)** (`characters.py`) — Code correct but didn't fire: LLM used "the ice caverns" not "AM's ice caverns".

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
| 11 | Roles + colleagues | analyzer.py (post-Phase-B re-run) | **Partial** — Ellen/Benny fixed, Nimdok still antagonist |
| 11 | Summary narrator | analyzer.py (name substitution) | **Fixed** — "Ted" in summary |
| 12 | Nimdok antagonist | analyzer.py ("fellow victim" guard) | **Fixed** — Nimdok now protagonist |
| 12 | LLM regression | N/A | AM aliases lost, ice caverns character, Ted role="minor" |
| 13 | Narrator elevation | narrator.py (role elevation for is_narrator) | **No change** — Ted wasn't flagged as narrator |
| 13 | Possessive filter | characters.py (STEP 5.9.2) | **No change** — LLM used non-possessive form |
| 13 | LLM regression | N/A | ice caverns=narrator, Huergelmir false positive, Gorrister antagonist |

## Key Debugging Notes for Fix Phase

**The core recurring problem is LLM non-determinism in narrator detection.** Ted has been narrator in attempts 2-8, 10-12, but lost it in 9 (Ellen) and 13 (ice caverns). The narrator detection needs to be MORE ROBUST against LLM variation:

1. **CRITICAL: Exclude non-character entities from narrator candidacy.** A character whose name is a common-noun phrase (starts with "the " + location/object noun) should never be narrator. This is a structural invariant.

2. **CRITICAL: Strengthen "I am {Name}" detection.** The text contains "I am Ted" — if the pipeline detects "I am {CharName}" in the source text, that character should be strongly preferred as narrator. This is more robust than LLM-based detection.

3. **HIGH: Broaden false-positive character filter.** The possessive filter (STEP 5.9.2) is too narrow. Need a broader filter that catches:
   - Common-noun phrases ("the ice caverns", "the bird") with low mentions and no dialogue
   - Mythological/creature references that aren't story characters (Huergelmir)

4. **HIGH: Gorrister role=antagonist** — investigate why post-Phase-B correction didn't fix this. May be a regression in the correction logic.

## Output Files
- HTML: ../output/i_have_no_mouth/report.html
- JSON: ../output/i_have_no_mouth/analysis.json

## Fix History (Attempt 14)
- **Fix 1: STEP 4.24 self-identification scan** (`src/agents/characters.py`)
  - Root cause: LLM narrator detection assigned "the ice caverns" as narrator; no deterministic override existed
  - Fix: After STEP 4, scan raw text for "I am {Name}" / "I'm {Name}" / "my name is {Name}" patterns. If matched character is in main_cast, override narrator assignment. This is deterministic and universal.
  - Expected effect: "I am Ted" found in text → Ted assigned narrator; "the ice caverns" cleared of narrator flag
  - Smoke test: Module imports cleanly, 332 tests pass

- **Fix 2: Post-Phase-B threshold `_fc_own <= 2`** (`src/analyzer.py:2613`)
  - Root cause: Gorrister had 2 outgoing "victim" labels (Benny + Huergelmir), both likely mislabeled (Gorrister IS the victim). Old threshold `<= 1` didn't catch 2 artifacts.
  - Fix: Changed `_fc_own <= 1` to `_fc_own <= 2` — a character with ≤2 outgoing victim-type labels AND zero incoming aggressor labels is not a true antagonist
  - Guard: AM has 5+ outgoing victim labels AND incoming "tormentor" from Ted → stays antagonist
  - Smoke test: Module imports cleanly, 332 tests pass

## Pipeline Notes (Attempt 14)
- Analysis completed in 22m 20s
- 7 characters found, 6 profiles generated
- **Narrator detected: Gorrister** (first-person) — WRONG, Ted should be narrator
- Fix 1 (self-identification "I am Ted" scan) did NOT override Gorrister detection
- "the narrator" alias blocked for Ted (good)
- Contradictory relationship removals: AM↔Gorrister, AM↔Nimdok, AM↔Benny (tormentor both ways), Gorrister↔Benny (companion both ways)
- Model: qwen3-next:80b-a3b-instruct-q8_0 (all agents)

## Next Action
**Phase:** awaiting_evaluation
