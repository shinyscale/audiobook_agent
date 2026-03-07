# Current Evaluation State

## Active Text
- **Name:** i_have_no_mouth
- **Attempt:** 22
- **Phase:** awaiting_evaluation
- **baseline_score:** 6.35
- **Competitive Mode:** none

## Output Files
- HTML: ../output/i_have_no_mouth/report.html
- JSON: ../output/i_have_no_mouth/analysis.json

## Pipeline Notes
- Analysis completed in 19m 21s
- 6 characters found (AM, Ted, Ellen, Nimdok, Gorrister + 1 more)
- 11 pronunciation flags
- BLOCKED alias: 'the narrator' meta-reference blocked for Ted (expected)
- BLOCKED alias: 'the machine' / 'a vengeful god' / etc. for AM (expected — Rule 0.5)
- Benny hallucinated aliases blocked (expected)
- Companion relationship contradictions removed (expected)

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 8.5/10 ✓
  - Completeness: 9/10
  - Identity Resolution: 10/10
  - Alias Grouping: 7/10
- Character Profiles: 7.5/10 ✗ (FAILING — from attempt 21)
- Chapter Summaries: 8/10 ✓
- Pronunciation Guide: 9/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 8.40/10** (attempt 21 — awaiting re-evaluation)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** Awaiting evaluation

## What Changed (Attempt 21 → 22)
- **Step 6.9 evidence/descriptions plain string fix:** Changed to handle strings directly with index-based replacement; dict case retained as fallback — should fix all 5 evidence entries and descriptions still saying "The narrator"
- **Step 6.9 regex broadened:** Changed `\bthe (?:first-person )?narrator\b` → `\bthe (?:\S+ )?narrator\b` to catch any single-word modifier (unnamed, first-person, story's, etc.)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.35 | 0 | Baseline |
| 2 | 7.3 | +0.95 | Benny dedup, narrator=Ted, but dup Ted |
| 3 | 7.8 | +1.45 | Relationship vocab, pronunciation fixed |
| 4 | 7.6 | +1.25 | Fixes didn't take effect |
| 5 | 8.1 | +1.75 | Dup Ted fixed, AM antagonist, self-alias fixed |
| 6 | 8.4 | +2.05 | Semantic direction bug |
| 7 | 6.65 | +0.30 | REGRESSION: Ted missing |
| 8 | 8.50 | +2.15 | Ted restored, all roles correct |
| 9 | 7.25 | +0.90 | REGRESSION: Ellen narrator |
| 10 | 7.65 | +1.30 | Ted narrator restored |
| 11 | 8.30 | +1.95 | Major progress |
| 12 | 8.20 | +1.85 | Nimdok fixed but LLM regression |
| 13 | 7.23 | +0.88 | REGRESSION: ice caverns narrator |
| 14 | 7.20 | +0.85 | Ted narrator restored, summary wrong |
| 15 | 6.73 | +0.38 | REGRESSION: Ted lost narrator again |
| 16 | 6.58 | +0.23 | REGRESSION: ice caverns is narrator now |
| 17 | 7.53 | +1.18 | Ice caverns gone, AM aliases fixed, Ted=narrator but role/summary wrong |
| 18 | 7.93 | +1.58 | Ted=protagonist, Gorrister fixed, chapter summary correct, narrator_character_id still None |
| 19 | 7.78 | +1.43 | Step 6.9 added but has 2 bugs — no improvement over 18 |
| 20 | 8.30 | +1.95 | narrator_character_id fixed, personality uses Ted, but plot summary/evidence still broken |
| 21 | 8.40 | +2.05 | plot_summary fixed, darkway IPA fixed, but evidence/descriptions still broken (wrong type) |
| 22 | TBD | TBD | Evidence/descriptions plain-string fix + regex broadened |

## Fix History (Previous)
- Attempt 2: Benny dedup, vocative narrator, pronunciation fixes
- Attempt 3: Same-name guard, adversarial role correction, relationship vocab, pronunciation whitelist
- Attempt 4: STEP 5.8 dedup, victim label, self-relationship filter (none worked)
- Attempt 5: Placeholder merge, incoming adversarial, false antagonist, self-alias filter (3/4 worked)
- Attempt 6: ACTIVE/PASSIVE labels, colleague consistency (neither worked)
- Attempt 7: Direction-aware aggressor labels (didn't fix)
- Attempt 8: Narrator vocative expansion, false-antagonist threshold (BOTH worked)
- Attempt 9: Colleague replacement (partial), Ellen narrator regression
- Attempt 10: Mention-ratio narrator validation (worked)
- Attempt 11: Post-Phase-B role correction, summary narrator substitution (mostly worked)
- Attempt 12: "fellow victim" guard (worked but LLM regression)
- Attempt 13: Narrator elevation, possessive filter (neither fired)
- Attempt 14: Self-identification scan STEP 4.24 (worked for narrator, not role), antagonist threshold (worked)
- Attempt 15: Summary prompt, narrator invariant STEP 5.9.6, acronym injection STEP 1.2, homograph exclusion (only homograph exclusion worked)
- Attempt 16: STEP 5.8.4 narrator name resolver, STEP 1.2 standalone char removal (neither worked)
- Attempt 17: Generic narrator name STEP 4.5b (Fixed), supporting→main narrator STEP 5.8.4b (Partial), Rule 0.5 acronym exemption (Fixed)
- Attempt 18: Ted role=protagonist (Fixed), Gorrister role=antagonist (Fixed), narrator_detected preservation (Fixed), pipeline crashes (Fixed)
- Attempt 19: Step 6.9 narrator substitution — 2 bugs (no-op name, wrong type check)
- Attempt 20: Step 6.9 Bug A fixed (name), Bug B partial (nested dict), narrator_character_id added
- Attempt 21: Step 6.9 plot_summary nested dict (Fixed), regex broadened partial, evidence/descriptions no-op (wrong type)
- Attempt 22: Step 6.9 evidence/descriptions plain-string fix + regex catch-all modifier

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 2 | Dup Benny | characters.py (Pass -1 dedup) | Fixed |
| 2 | Wrong narrator | characters.py (vocative + STEP 4.5b) | Fixed but introduced dup Ted |
| 2 | Pronunciation FPs | cmu_proposer.py, enricher.py | Partially fixed |
| 3 | Dup Ted | characters.py (STEP 5.8.5b) | No change |
| 3 | AM wrong role | analyzer.py | No change |
| 3 | Relationship vocab | analyzer.py | Fixed |
| 3 | Pronunciation FPs | cmu_proposer.py | Fixed |
| 4 | Dup Ted | characters.py (STEP 5.8) | No change |
| 4 | AM wrong role | analyzer.py | No change |
| 5 | Dup Ted | characters.py (STEP 5.2b) | **Fixed** |
| 5 | AM wrong role | analyzer.py | **Fixed** |
| 5 | False antagonist | analyzer.py | **Partial** |
| 5 | AM self-alias | characters.py | **Fixed** |
| 6 | Wrong roles | analyzer.py | No change |
| 7 | Wrong roles | analyzer.py | No change |
| 8 | Ted missing | characters.py (STEP 4.25b) | **Fixed** |
| 8 | Wrong roles | analyzer.py | **Fixed** |
| 9 | Colleague labels | analyzer.py | **Partial** |
| 10 | Narrator fix | characters.py (STEP 4.27) | **Fixed** |
| 11 | Roles + colleagues | analyzer.py | **Partial** |
| 11 | Summary narrator | analyzer.py | **Fixed** |
| 12 | Nimdok antagonist | analyzer.py | **Fixed** |
| 13 | Narrator elevation | narrator.py | No change |
| 13 | Possessive filter | characters.py | No change |
| 14 | Self-identification | characters.py (STEP 4.24) | **Fixed** (narrator only) |
| 14 | Antagonist threshold | analyzer.py | **Fixed** |
| 15 | Summary prompt | summarizer.py | No change |
| 15 | Narrator invariant | characters.py (STEP 5.9.6) | No change |
| 15 | Acronym injection | characters.py (STEP 1.2) | **Bug** |
| 15 | Homograph exclusion | homograph_proposer.py | **Fixed** |
| 16 | Narrator name resolver | characters.py (STEP 5.8.4) | No change |
| 16 | Acronym dedup | characters.py (STEP 1.2) | No change |
| 17 | Generic narrator name | characters.py (STEP 4.5b) | **Fixed** |
| 17 | Supporting→main narrator | characters.py (STEP 5.8.4b) | **Partial** |
| 17 | Rule 0.5 acronym | main_cast.py (Rule 0.5) | **Fixed** |
| 18 | Ted role=protagonist | narrator.py, characters.py (STEP 5.9.6) | **Fixed** |
| 18 | Gorrister role=antagonist | analyzer.py | **Fixed** |
| 18 | narrator_detected preservation | analyzer.py | **Fixed** |
| 18 | Pipeline crashes | analyzer.py, models.py | **Fixed** |
| 19 | Step 6.9 narrator substitution | analyzer.py (lines 2527-2561) | **Bug** (2 bugs) |
| 20 | Step 6.9 Bug A (name) | analyzer.py | **Fixed** |
| 20 | Step 6.9 Bug B (dict) | analyzer.py | **Partial** (nested dict not handled) |
| 20 | narrator_character_id | analyzer.py, models.py | **Fixed** |
| 21 | Step 6.9 plot_summary nested dict | analyzer.py | **Fixed** |
| 21 | Step 6.9 regex broadened | analyzer.py | **Partial** ("unnamed" not covered) |
| 21 | Step 6.9 evidence/descriptions | analyzer.py | **No change** (expected dicts, got strings) |
| 22 | Step 6.9 evidence/descriptions (strings) | analyzer.py | TBD |
| 22 | Step 6.9 regex catch-all modifier | analyzer.py | TBD |
