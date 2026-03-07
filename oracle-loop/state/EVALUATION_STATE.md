# Current Evaluation State

## Active Text
- **Name:** i_have_no_mouth
- **Attempt:** 7
- **Phase:** awaiting_fix
- **baseline_score:** 6.35

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 5/10 ✗ (FAILING — REGRESSION)
  - Completeness: 4/10
  - Identity Resolution: 7/10
  - Alias Grouping: 5/10
- Character Profiles: 4/10 ✗ (FAILING — REGRESSION)
- Chapter Summaries: 7/10 ✗ (FAILING)
- Pronunciation Guide: 9/10 ✓
- HTML Presentation: 9/10 ✓
- **Overall: 6.65/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold — REGRESSION from attempt 6)

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

## Current Issues (Priority Order)

### CRITICAL
1. **Ted (narrator/protagonist) missing — replaced by "the ice caverns"** [Completeness, Identity Resolution]
   - Problem: The first-person narrator Ted is not in the character list at all. Instead, "the ice caverns" (a LOCATION in the story) is extracted as a character and marked as the narrator. It has aliases "ice caverns" and "the unnamed narrator".
   - Evidence: Other characters address Ted by name in dialogue: "Please, Ted, let's try it", "No, Ted, sit down". The summary itself mentions "Ted" 3 times. "The ice caverns" is the location where the climax occurs, not a character.
   - This is a REGRESSION from attempts 5-6 where Ted was correctly identified. The new model run (qwen3-next:80b) produced different extraction results.
   - Root cause: The summarizer used "the unnamed narrator" instead of "Ted", and Pass 1 character extraction picked up "the ice caverns" (a frequently mentioned location) and conflated it with the narrator role.
   - Impact: Cascades to profiles (narrator profile is for a location), summaries (uses "unnamed narrator" instead of Ted), and relationships (other chars reference "the unnamed narrator").
   - Location: Two-pronged fix needed:
     1. **Summary level**: The summarizer should use character names from dialogue when referring to the narrator, not "the unnamed narrator". The text has dialogue explicitly naming Ted.
     2. **Character extraction level**: "the ice caverns" is a location phrase, not a character. The extraction pipeline should filter location-like entities. However, the more robust fix is ensuring Ted is extracted from dialogue references.
   - Note: Previous attempts fixed Ted detection via vocative pattern + narrator fallback in characters.py (STEP 4.5b). That code path may not be firing with the new model output, or the model may be suppressing "Ted" from active_characters.

2. **Benny, Gorrister, Ellen, Nimdok all wrongly labeled "antagonist"** [Profiles — Role Assignment]
   - Problem: 4 of 5 human victims are labeled "antagonist". Only "the ice caverns" (the misidentified narrator) is "protagonist".
   - Root cause: The direction-aware fix from attempt 7 IS in the code (analyzer.py:2184-2223), but it doesn't fire because ALL four humans have at least one outgoing "victim" substring match:
     - Ellen → Nimdok: "victim of Ellen's final act" → "victim" matches _OUTGOING_AGGRESSOR_LABELS → _own_adv=1
     - Benny → Gorrister: "victim (of final violent act)" → _own_adv=1
     - Gorrister → Benny: "victim" → _own_adv=1
     - Nimdok → Ellen: "victim (killed by)" → _own_adv=1
   - These "victim" labels refer to the MERCY KILLINGS at the story's climax. The humans killed each other to escape AM's torture — this is an act of compassion, not antagonism.
   - The condition `_own_adv == 0 and _in_adv == 0` is too strict. A true antagonist like AM has _own_adv=5 (labels ALL humans as "victim"). A character with _own_adv=1 from a single mercy killing is not an antagonist.
   - **Fix: Raise the threshold or use a ratio.** Options:
     - (A) Require `_own_adv >= 2` to count as genuine aggressor evidence (single isolated "victim" label insufficient)
     - (B) Compare `_own_adv` to total relationship count: if aggressor labels are < 50% of relationships, likely not a true antagonist
     - (C) Compare to the maximum _own_adv among all characters: if this char's _own_adv is << max, they're not the antagonist
   - Option A is simplest and directly addresses this case. AM has _own_adv=5, so threshold of 2 preserves AM. All humans have _own_adv=1, so threshold of 2 corrects them.
   - Location: `src/analyzer.py:2218` — change `if _own_adv == 0 and _in_adv == 0:` to `if _own_adv <= 1 and _in_adv == 0:`

### HIGH
3. **Summary uses "the unnamed narrator" instead of "Ted"** [Summaries — Accuracy]
   - Problem: The chapter summary refers to the narrator as "the unnamed narrator" throughout, despite other characters calling him "Ted" in dialogue within the text.
   - Evidence: Summary text includes "prompting the unnamed narrator to kill him" and "the unnamed narrator kills Ellen with an ice spear". Meanwhile, dialogue quotes in the HTML show "Please, Ted, let's try it" and "No, Ted, sit down".
   - Impact: Cascades to character extraction (no "Ted" entity extracted from summaries).
   - This is an LLM generation issue — the model chose to use "the unnamed narrator" instead of the name used in dialogue.
   - Location: This is a model behavior issue, not easily fixed with code. The character extraction pipeline should compensate by checking dialogue for character names not in summaries (which the vocative pattern in STEP 4.5b was designed to do).

### MEDIUM
4. **Hallucinated relationship details** [Profiles — Evidence]
   - Gorrister → Ellen: "authority figure who enforces discipline" — not supported by text
   - Ellen → Nimdok: "victim of Ellen's final act" — technically Ellen kills Nimdok at the end, but the phrasing is oddly vague
   - Gorrister → Benny: "victim" — unclear direction; in the text, Benny attacks Gorrister (eats his face), making Gorrister the victim of Benny, not the other way

5. **Ted and AM have no physical description** [Profiles — Descriptions]
   - Ted: first-person narrator rarely describes himself — expected limitation
   - AM: a computer/AI — the text describes AM's internal environment, not AM's physical form
   - Severity: Medium — not fixable without hallucinating content

### LOW
6. **Chapter title is null** [Structure]
   - Single section has `title: null` — could display the story title
   - Not blocking — single-section detection is correct

7. **Summary minor inaccuracy: "Benny is blinded and deafened"** [Summaries]
   - In the text, Benny is blinded by AM as punishment, but the "deafened" part is less clear
   - Minor detail, not blocking

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

## Next Action
Run PROMPT_fix.md to address:
1. CRITICAL #1: Ted missing — ensure character extraction finds Ted from dialogue references even when summarizer uses "unnamed narrator"
2. CRITICAL #2: Raise false-antagonist threshold from `_own_adv == 0` to `_own_adv <= 1` so single mercy-kill labels don't block correction

## Output Files
- HTML: ../output/i_have_no_mouth/report.html
- JSON: ../output/i_have_no_mouth/analysis.json

## Pipeline Notes
- Attempt 7 analysis completed successfully in 21m 3s
- Model: qwen3-next:80b-a3b-instruct-q8_0 (all agents)
- 6 characters total: AM, Ellen, Nimdok, Gorrister, Benny, "the ice caverns" (should be Ted)
- 16 pronunciation flags
- WARNING: "Failed to parse JSON response for Ted: Could not parse JSON: line 1 column 1 (char 0)" → Low confidence profile for Ted: 0.30
- Relationship data in analysis.json is exported as strings (target names only), not dicts — relationship types are only visible in HTML
- REGRESSION NOTE: The profiler DID try to generate a profile for "Ted" (see JSON parse warning) but failed. This suggests Ted WAS known to the profiler but the character extraction produced "the ice caverns" instead, and the profiler couldn't match "Ted" to any extracted character.
