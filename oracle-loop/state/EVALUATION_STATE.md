# Current Evaluation State

## Active Text
- **Name:** i_have_no_mouth
- **Attempt:** 20
- **Phase:** awaiting_evaluation
- **baseline_score:** 6.35
- **Competitive Mode:** none

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 8.5/10 ✓
  - Completeness: 10/10
  - Identity Resolution: 10/10
  - Alias Grouping: 7/10
- Character Profiles: 6/10 ✗ (FAILING)
- Chapter Summaries: 6.5/10 ✗ (FAILING)
- Pronunciation Guide: 9/10 ✓
- HTML Presentation: 8/10 ✓
- **Overall: 7.78/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold)

## What Changed (Attempt 18 → 19)
- Step 6.9 added for narrator name substitution — but **did NOT fire** due to two bugs:
  1. `_nn_final = narrator_detected` but `narrator_detected = "the narrator"` → replaces "the narrator" with "the narrator" (no-op)
  2. Plot summary check `isinstance(_ps_obj, dict)` but `overview.get('plot_summary')` returns a **string**, not a dict → condition never true
- Net result: **no improvement** from attempt 18 on the failing categories

## Current Issues (Priority Order)

### CRITICAL
1. **Step 6.9 narrator substitution has two bugs — neither substitution fires** [Summaries + Profiles]
   - **Bug A:** Line 2533: `_nn_final = narrator_detected` but `narrator_detected = "the narrator"`. The code replaces "the narrator" with "the narrator" — a no-op. Should instead find the character with `is_narrator=True` and use their `canonical_name` ("Ted").
   - **Bug B:** Line 2551: `isinstance(_ps_obj, dict)` but `overview.get('plot_summary')` is a **string** (the plot summary text itself), not a nested dict. The condition is never true so plot summary is never substituted.
   - Location: `src/analyzer.py` lines 2532-2561
   - Fix Bug A: Replace `_nn_final = narrator_detected` with: scan `pipeline_char_map.characters` for `is_narrator=True`, use that character's `canonical_name` as `_nn_final`. If `_nn_final` equals "the narrator" or is empty, skip substitution.
   - Fix Bug B: Replace lines 2549-2552 with: `if overview and isinstance(overview.get('plot_summary'), str) and 'narrator' in overview['plot_summary'].lower(): overview['plot_summary'] = _nn_pat.sub(_nn_final, overview['plot_summary'])`

2. **narrator_character_id still None despite Ted having is_narrator=True** [Profiles + Summaries]
   - Problem: Top-level `narrator_character_id` in analysis.json is `null`. This cascades to: profiler doesn't apply first-person extraction for Ted, no narrator-aware summary generation.
   - Evidence: `jq '.narrator_character_id'` → `null`; Ted has `is_narrator: true`
   - Location: `src/analyzer.py` — where AnalysisResult is assembled (after Step 7). Search for `narrator_character_id` assignment.
   - Fix: After character extraction, scan characters for `is_narrator=True` and set `narrator_character_id` to that character's ID. This is a simple post-extraction fixup that should be added near where the AnalysisResult is constructed.

### HIGH
3. **Ted missing physical_description** [Profiles]
   - Problem: Ted has `physical_description: None`. The text describes Ted as "the handsome one" / "I was still the handsome one" — the only survivor AM didn't physically transform. This is narratively critical.
   - Root cause: With `narrator_character_id=None`, the profiler doesn't apply first-person self-description extraction. Ted rarely refers to himself by name (5 mentions), so the profiler has limited evidence.
   - Fix: Resolves with CRITICAL #2 — once narrator_character_id is set, profiler's first-person attribution activates for Ted.

4. **Plot summary treats "the narrator" and "Ted" as two separate people** [Summaries]
   - Problem: Plot summary says "the narrator recounts the harrowing journey of Ellen, Nimdok, Gorrister, Benny, and Ted" — lists 6 people but there are only 5 survivors. Then "the narrator observes..." and "the narrator, alive to tell this tale" while Ted is transformed. Factually contradictory.
   - Fix: Resolves with CRITICAL #1 Bug A+B — once "the narrator" is replaced with "Ted" in the plot summary, it reads correctly.

5. **Ted's personality summary and relationship evidence use "the narrator" not "Ted"** [Profiles]
   - Problem: HTML lines 1237, 1308, 1320, 1332, 1344 all say "The narrator..." instead of "Ted..."
   - Fix: Resolves with CRITICAL #1 Bug A — once `_nn_final` is "Ted", the personality substitution at lines 2554-2560 will fire correctly.

6. **Ted missing from chapter active_characters tags** [Presentation]
   - Problem: Chapter characters show Ellen, Nimdok, Gorrister, Benny, AM — but NOT Ted, despite being narrator and protagonist.
   - Root cause: `structure[0].active_characters` is `null`. The summarizer listed "the narrator" as active character, but either it was removed or never mapped to Ted.
   - Fix: Step 6.9 line 2542-2546 handles active_characters substitution, but Bug A prevents it. Additionally, if active_characters was null from the start, need to ensure the summarizer populates it OR Step 6.9 injects the narrator into active_characters when missing.

### MEDIUM
7. **AM missing "Allied Mastercomputer" alias** [Character Extraction - Alias Grouping]
   - AM has no aliases despite "Allied Mastercomputer" being mentioned in the text and even in the chapter summary.
   - Low priority — AM is clearly identified.

8. **"darkway" pronunciation IPA appears wrong** [Pronunciation]
   - Listed as /ˈdɑːrkteɪ/ — looks like it should be /ˈdɑːrkweɪ/ (dark-way, not dark-tay)
   - Minor issue.

## Fix Priority

**Two bugs in Step 6.9 are the immediate fix target.** They are simple code errors:
1. Bug A: Use `canonical_name` from `is_narrator=True` character instead of `narrator_detected`
2. Bug B: Check for string plot_summary, not dict

**Additionally**, set `narrator_character_id` on the AnalysisResult by scanning characters for `is_narrator=True`.

**Expected score improvements if fixed:**
- Summaries: 6.5 → 8.5+ (plot summary corrected, Ted in active_characters)
- Profiles: 6 → 8+ (Ted gets full profiling with narrator_character_id set, personality uses "Ted")
- Overall: 7.78 → ~8.5+

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

## Fix History (Attempt 19 → 20)
- **Step 6.9 narrator substitution bugs fixed:**
  - Bug A: Now scans `pipeline_char_map.characters` for `is_narrator=True`, uses `canonical_name` ("Ted") as `_nn_final`; only substitutes when name is not "the narrator"
  - Bug B: Changed `isinstance(_ps_obj, dict)` → `isinstance(_ps_obj, str)` for plot_summary type check
  - Added narrator injection into `active_characters` when narrator is absent from chapter cast
  - Modified: `src/analyzer.py` (Step 6.9 block)
- **narrator_character_id added to AnalysisResult:**
  - Added field to `src/models.py:AnalysisResult`
  - Set in `src/analyzer.py` by scanning converted characters for `is_narrator=True`

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
| 19 | Step 6.9 narrator substitution | analyzer.py (lines 2527-2561) | **Bug** (2 bugs: no-op substitution + wrong type check) |

## Output Files
- HTML: ../output/i_have_no_mouth/report.html
- JSON: ../output/i_have_no_mouth/analysis.json

## Next Action
Re-run analysis to verify Step 6.9 bug fixes and narrator_character_id population.
