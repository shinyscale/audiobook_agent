# Current Evaluation State

## Active Text
- **Name:** i_have_no_mouth
- **Attempt:** 12
- **Phase:** awaiting_fix
- **baseline_score:** 6.35
- **Competitive Mode:** none

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 7.5/10 ✗
  - Completeness: 8/10
  - Identity Resolution: 10/10
  - Alias Grouping: 6/10
- Character Profiles: 7.5/10 ✗
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 9/10 ✓
- **Overall: 8.20/10**

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold: Character Extraction, Character Profiles)

## Improvement Summary (Attempt 11 → 12)
- Nimdok: antagonist → protagonist ✓ (was CRITICAL #1, FIXED by "fellow victim" guard)
- AM→Nimdok: "colleague" → "victim" ✓ (CRITICAL #2 auto-fixed)
- Nimdok→AM: "tormentor" ✓

Regressions (LLM non-determinism):
- AM aliases GONE (attempt 11 had "Allied Mastercomputer", "Adaptive Manipulator", "I am" — now empty)
- "AM's ice caverns" extracted as a 7th character (spurious location-as-character)
- Ted role changed from "protagonist" to "minor" (only 5 mentions)

## Current Issues (Priority Order)

### CRITICAL
1. **Ted role="minor" — narrator should never be "minor"** [Profiles — Roles]
   - Problem: Ted is the first-person narrator (is_narrator=True) but has role="minor" because he only has 5 mentions. The narrator/protagonist should never be classified as "minor".
   - Evidence: Ted narrates the entire story. He is one of the 5 humans tormented by AM. role="minor" is factually wrong.
   - Root cause: Role assignment likely uses mention count. Ted's low count (5) puts him in "minor" tier. The narrator role should override mention-based classification.
   - Location: `src/analyzer.py` or `src/agents/characters.py` — wherever roles are assigned post-extraction
   - Fix: If a character has `is_narrator=True`, their role should be at minimum "protagonist" (or "main"), never "minor" or "supporting". This is a universal invariant: narrators are always significant characters.

### HIGH
2. **"AM's ice caverns" extracted as a character** [Extraction — False Positive]
   - Problem: "AM's ice caverns" (5 mentions) is a location/setting, not a character. It has a profile, relationships to all other characters (all "colleague"), and adds noise throughout the report.
   - Evidence: Ice caverns are a place the characters travel to. They don't act, speak, or have agency.
   - Root cause: LLM non-determinism — attempt 11 had 6 characters (correct), attempt 12 added this spurious entry. The pipeline lacks a post-extraction filter for obvious locations.
   - Location: `src/agents/characters.py` — post-extraction filtering, or `src/analyzer.py` post-profile
   - Fix: Consider a generic filter: if a character's canonical_name contains location indicators ("cavern", "cave", "room", "house", "castle", "forest", "city", "town", etc.) AND the character has low mentions AND has no dialogue, filter it out. BUT be careful not to filter legitimate named characters who happen to share names with places. A safer approach: if the character's profile relationships are ALL "colleague" (no meaningful relationship types), and name contains possessive of another character ("AM's"), it's likely a sub-entity/location, not a character.

3. **AM aliases completely missing** [Extraction — Alias Regression]
   - Problem: AM has zero aliases. In attempt 11, AM had ["Allied Mastercomputer", "Adaptive Manipulator", "I am"]. These are textually stated expansions of the acronym.
   - Evidence: The text explicitly says AM stands for "Allied Mastercomputer" then "Adaptive Manipulator" then "Aggressive Menace" then "I think, therefore I AM."
   - Root cause: LLM non-determinism in Pass 2 alias extraction. Code didn't change alias logic.
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` — Pass 2 alias extraction
   - Fix: This is hard to fix deterministically since it's LLM variation. A programmatic approach: scan summary text for "stands for" / "stood for" / "short for" patterns near character names and inject found expansions as aliases. This would be a new post-extraction step.

### MEDIUM
4. **Relationship noise from spurious "AM's ice caverns" character** [Profiles]
   - Problem: Multiple characters have relationships to "AM's ice caverns" labeled "colleague", "place of suffering", "fellow victim" — adding noise to profile sections.
   - Fix: Auto-resolves if HIGH #2 is fixed (ice caverns removed from character list).

5. **Common homographs in pronunciation** [Pronunciation — False Positives]
   - "read", "lead", "does", "close", "subject" — 5 common English homographs that most narrators wouldn't need flagged. 11 of 16 entries are genuinely useful.
   - Persistent issue from multiple attempts. LOW priority.

### LOW
6. **Chapter title is null** [Structure]
   - Single section with `title: null`. Cosmetic for a short story with no heading.

7. **No speech patterns noted** [Profiles — Completeness]
   - AM's megalomaniacal monologue ("HATE. LET ME TELL YOU HOW MUCH I'VE COME TO HATE YOU...") and Ted's cynical narration are not captured. Nice-to-have but not blocking.

## Fix Priority
**CRITICAL #1 is the primary blocker.** If Ted's role is fixed from "minor" to "protagonist":
- Character Profiles score improves: the narrator having correct role is a major quality signal
- Profiles should move from 7.5 → 8.0+

**HIGH #2 is secondary.** Removing "AM's ice caverns" as a character:
- Character Extraction completeness improves (no false positive)
- Removes relationship noise from all other character profiles
- Extraction should move from 7.5 → 8.0+

**HIGH #3 (AM aliases) is desirable but risky** — programmatic alias injection for acronym expansions could help but adds complexity. Consider deferring if #1 and #2 are sufficient to pass.

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

## Pipeline Notes (Attempt 12)
- Analysis completed in 22m 23s
- 7 characters found: AM (77), Ellen (30), Nimdok (17), Gorrister (29), Benny (35), Ted (5), AM's ice caverns (5)
- Ted correctly identified as narrator (first-person, is_narrator=True)
- Ted role="minor" despite being narrator — role assignment bug
- AM has NO aliases (regression from attempt 11)
- "AM's ice caverns" is a spurious location-as-character
- Model: qwen3-next:80b-a3b-instruct-q8_0 (all agents)
- Character Profiles took 10m 37s (bottleneck, 47.5% of total)

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

## Key Debugging Notes for Fix Phase
1. **CRITICAL #1 (Ted role):** Find where roles are assigned. If `is_narrator=True`, role must be >= "protagonist". This is a universal invariant — narrators are never minor characters. Search for role assignment logic in `src/agents/characters.py` or `src/analyzer.py`.
2. **HIGH #2 (ice caverns):** The spurious character has possessive form ("AM's ice caverns") and all relationships are "colleague". A post-extraction filter could check: if canonical_name contains possessive of another character AND all relationships are generic, remove it.
3. **HIGH #3 (AM aliases):** LLM variation. A programmatic fix could scan summary text for acronym expansion patterns near "AM" and inject as aliases. But this is risky — defer unless #1 and #2 aren't enough to pass.

## Output Files
- HTML: ../output/i_have_no_mouth/report.html
- JSON: ../output/i_have_no_mouth/analysis.json

## Next Action
Run PROMPT_fix.md to address Ted role="minor" (CRITICAL #1) and ice caverns spurious character (HIGH #2)
