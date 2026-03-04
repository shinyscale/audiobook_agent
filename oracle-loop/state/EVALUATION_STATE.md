# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 11
- **Phase:** awaiting_evaluation
- **baseline_score:** 6.55
- **Competitive Mode:** none

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 5.5/10 ✗ (FAILING — REGRESSION)
  - Completeness: 6/10
  - Identity Resolution: 4/10 ← father/son FALSE MERGE (was split in attempts 8-9)
  - Alias Grouping: 6/10
- Character Profiles: 5/10 ✗ (FAILING — REGRESSION)
- Chapter Summaries: 7/10 ✗ (FAILING)
- Pronunciation Guide: 8.5/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 7.0/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold — regression from attempt 9)

## What Attempt 10 Changed vs Attempt 9

**REGRESSIONS:**
- **Father/son MERGED BACK into single character** — Only 3 characters: "John Donaldson" (55 mentions), "Uncle Bill" (18), "Ted Frith" (5). In attempts 8-9 these were separate: son (~27) + father (~28). The merged profile confusingly mixes father traits ("embezzled money", "dying stretcher-bearer", "seeks redemption") with son traits ("the boy", "ambulance driver").
- **Ted Frith lost relationships** — Had "companion" in attempt 9, now has empty relationships {}
- **Narrator detection STILL failing** — narrator_info is None, Uncle Bill not flagged as narrator
- **Relationships still "associated"** — The post-filter fix for "associated" labels did NOT work. All relationships remain "associated".
- **Step 5.4.6b rename did NOT fire** — Canonical name is "John Donaldson" (not "John Donaldson (the son)") because there is no parent character to trigger against.

**Root cause analysis:**
The attempt 10 code changes (post-filter for associated + Step 5.4.6b rename) did not CAUSE the regression — they simply had no effect because the underlying father/son split was lost. The split is LLM-non-deterministic: qwen3.5 sometimes separates the two John Donaldsons and sometimes merges them. The code changes from attempts 8-9 that enabled the split (summary prompt guidance for nested narration, role assignment) are still present, but the LLM chose differently this run.

**The fundamental problem:** The father/son split is not ENFORCED programmatically — it depends entirely on the LLM's Pass 1 extraction outputting two separate "John Donaldson" characters. When the LLM merges them, no downstream code can fix it because the evidence is lost.

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.55 | 0 | Baseline. Narrator misidentification cascades into profiles + summaries |
| 2 | 6.6 | +0.05 | Narrator fix worked (Bill=narrator ✓, Bill profile correct ✓). But Johnny still missing, summary still wrong. |
| 3 | 6.0 | -0.55 | **REGRESSION.** "American, sir" false character stole narrator from Uncle Bill. Johnny still missing. |
| 4 | 6.4 | -0.15 | Co-present guard fixed "American, sir" ✓, but narrator REGRESSED (Johnny instead of Bill). Johnny/John's Son false split. |
| 5 | 6.7 | +0.15 | Plot summary improved (correctly names Uncle Bill). But narrator metadata STILL wrong. Step 5.4.6 merged "the boy" into father. |
| 6 | 7.0 | +0.45 | Uncle Bill narrator ✓, merge direction fixed ✓. But John Donaldson false secondary narrator → profile catastrophe. |
| 7 | 6.9 | +0.35 | Narrator guard worked ✓ (John Donaldson not narrator). But boy disappeared (false merge), plot summary fabricates false twist. |
| 8 | 7.85 | +1.30 | Father/son split ✓, plot summary fixed ✓, summaries fixed ✓, profiles much improved ✓. Remaining: cross-character aliases, generic relationships. |
| 9 | 8.0 | +1.45 | Cross-character alias contamination fixed ✓. Relationship fix only hit secondary prompt. Father still has 0 descriptive aliases. |
| 10 | 7.0 | +0.45 | **REGRESSION.** Father/son merge recurred (LLM non-determinism). Both attempt 10 fixes had no effect. |

## Current Issues (Priority Order)

### CRITICAL

1. **Father/son characters FALSE MERGED — LLM non-deterministic split** [Identity Resolution]
   - Problem: "John Donaldson" has 55 mentions (sum of father ~28 + son ~27). The profile mixes: father's traits ("embezzled money", "dying stretcher-bearer", "seeks redemption", "shabby shoulders") with son's traits ("the boy", "ambulance driver", age 18). Evidence says "He physically resembles his son" but HE IS the son in this merged output.
   - Root cause: The father/son split depends entirely on the LLM producing two separate "John Donaldson" entries in Pass 1 character extraction. Attempts 8-9 happened to get this right; attempt 10 did not. The summarizer prompt improvements from attempt 8 (nested narration guidance) are still present but insufficient to guarantee the split.
   - Location: `src/pipeline/summarization/summarizer.py` (summaries must clearly distinguish father vs son) AND `src/pipeline/character_extraction_v2/main_cast.py` (Pass 1 must extract both)
   - Fix strategy: **This needs a programmatic post-extraction split, not more prompt engineering.** When the summary clearly describes two different people with the same name (one is a dying father, one is a young ambulance driver), and the LLM merges them, a post-extraction step in `src/agents/characters.py` should detect the conflicting descriptors and force a split. Alternatively, enhance the summary active_characters to explicitly list "John Donaldson (the father)" and "John Donaldson (the son)" as separate entries, giving the character extractor a stronger signal.
   - Impact: This single issue causes cascading failures in profiles (mixed identity), relationships (orphan references), and alias grouping.

### HIGH

2. **Relationships still all "associated" despite attempt 10 fix** [Profiles]
   - Problem: The post-filter for "associated" labels was supposed to trigger a secondary call for specific labels. But all relationships remain "associated": Uncle Bill → John Donaldson = "associated", John Donaldson → Uncle Bill = "associated".
   - Evidence: The fix from attempt 10 (post-filter + secondary call trigger) either did not fire or the secondary call also returned "associated".
   - Location: `src/analyzer.py` — `_generate_character_profile()` — the post-filter logic added in attempt 10
   - Fix: Debug why the post-filter/secondary-call mechanism failed. The secondary prompt works (proved by Ted Frith getting "companion" in attempt 9). The primary prompt post-filter may not be executing, or the secondary call may not be triggered correctly.
   - Impact: Profiles 5 → 7+ if relationships become specific (guardian, uncle, friend, son, etc.)

3. **Narrator detection failed — Uncle Bill not identified** [Profiles, Summaries]
   - Problem: `narrator_info` is None. Uncle Bill is the frame narrator of this story but `is_narrator=False` for all characters.
   - Evidence: Previous attempts (6, 8, 9) had Uncle Bill correctly as narrator. This is a regression.
   - Location: `src/pipeline/character_extraction_v2/narrator.py`
   - Root cause: Likely the LLM's narrator detection prompt returned an unparseable result. Pipeline notes say "Narrator detection failed or returned non-dict: None".
   - Fix: Add fallback/retry logic in narrator.py when detection returns None. Or strengthen the narrator prompt to be more robust.

4. **Ted Frith lost relationships — regression** [Profiles]
   - Problem: Ted Frith had "companion" relationship in attempt 9 (secondary prompt fix confirmed working). Now has empty relationships {}.
   - Location: `src/analyzer.py` — profile generation for supporting characters
   - Root cause: Possibly related to the same post-filter issue as HIGH #2, or the secondary prompt was not invoked for Ted Frith this run.

### MEDIUM

5. **"Age: two years old" hallucinated on John Donaldson AND Ted Frith** [Profiles]
   - Problem: Both characters show `appearance.age_indication: "two years old"`. John Donaldson (merged) should be ~18 (son) or elderly (father). Ted Frith's age is unspecified. "Two years old" is fabricated, likely from a time-duration phrase in the text.
   - Location: `src/analyzer.py` — profile generation, `age_indication` field
   - Fix: Add validation rejecting ages < 5 for non-infant characters, or cross-check against physical_description.

6. **Summary confuses characters in final section** [Summaries]
   - Problem: Summary says "the narrator comforts a dying man named Uncle Bill, who fears dishonor until the narrator affirms his American identity, leading to Uncle Bill's peaceful death". Uncle Bill is the FRAME narrator, not a dying war casualty. The dying man in the war scene is the FATHER (John Donaldson Sr.). The summary conflates these two characters.
   - Location: `src/pipeline/summarization/summarizer.py`
   - Root cause: With the father/son merge, the LLM has no clear label for the dying father and substitutes "Uncle Bill".

7. **active_characters and key_events empty** [Summaries]
   - Problem: Both fields are empty lists `[]` in the structure output.
   - Impact: Minor — the summary text compensates, but these fields enable F6 reconciliation.

### LOW

8. **Missing nicknames: "Johnny" and "Teddy"** [Alias Grouping]
   - Still not captured. Low priority compared to critical issues.

9. **Margaret Donaldson absent from character list** [Completeness]
   - Minor character, filtered by mention count.

## Fix Strategy for Attempt 11

**The father/son merge is the root cause of most regressions. This must be solved programmatically, not via prompt engineering.**

Priority 1: **Force father/son split when summary evidence supports it.** Options:
- (A) In `characters.py`, add a post-extraction step that checks for conflicting age/role descriptors in a single character (e.g., "the boy" alias + "embezzled money 20 years ago" evidence = two different people). Split the character.
- (B) In `summarizer.py`, when the summary describes both a parent and child with the same name, output them as separate active_characters with disambiguating labels: "John Donaldson (father)" and "John Donaldson (son)".
- (C) Both — (B) gives extraction a signal, (A) catches cases where the LLM still merges.

Priority 2: **Debug the relationship post-filter** from attempt 10. Why didn't it fire? Check if the logic path is actually reached.

Priority 3: **Narrator detection robustness** — add retry/fallback when narrator detection returns None.

**Do NOT touch** (working correctly when split works):
- main_cast.py RULE 3d/3e (alias contamination fix)
- characters.py Step 5.4.5 (co-present guard)
- summarizer.py nested narration guidance (works when LLM cooperates)

## Fix History
- Attempt 11:
  1. STEP 3.95 — Programmatic same-name split from characters_present lists
     - Modified: `src/agents/characters.py` — new STEP 3.95 after STEP 3.9 (before narrator detection)
     - Root cause: LLM non-deterministically merges same-name characters; characters_present already lists them as distinct but LLM ignores the NOTE
     - Fix: After all merges (3.9), parse [Characters present: ...] from summaries; for each group with 2+ entries sharing the same base name, find the merged main_cast character and split it into N characters
     - Smoke test: PASS — parsing logic correctly identifies 'john donaldson' group with 2 CP entries; triggers split of "John Donaldson" into "John Donaldson (the narrator in the flashback)" + "John Donaldson (the father/volunteer)"
  2. clean_unknown_relationships() — extended to also remove "associated" labels
     - Modified: `src/pipeline/character_profiling/post_corrections.py`
     - Root cause: add_cooccurrence_relationships() adds "associated" for co-occurring chars; verify_relationships_from_text() fails to upgrade it; result is "associated" labels in output
     - Fix: Remove "associated"/"associate"/"acquaintance" along with "unknown" in final cleanup
  3. Narrator extracted from V2 pipeline_metadata in analyzer.py
     - Modified: `src/analyzer.py` — after line 1107 (V2 extraction result)
     - Root cause: characters.py Step 4/5.8 already ran narrator detection with the fully-resolved main_cast, but analyzer.py ignored this result and ran a duplicate LLM call (Step 4.5) that sometimes fails
     - Fix: Extract narrator_name/pov from pipeline_char_map.pipeline_metadata immediately after V2 extraction; set narrator_detected directly
- Attempt 10:
  1. Post-filter "associated"/"acquaintance"/"unknown" relationship labels from primary profiler
     - Modified: `src/analyzer.py` — `_generate_character_profile()` after parsing relationships
     - Result: **NO EFFECT** — relationships still "associated". Post-filter may not be executing.
  2. Renamed "John's son" → "John Donaldson (the son)" via new Step 5.4.6b
     - Modified: `src/agents/characters.py` — new Step 5.4.6b after Step 5.4.6
     - Result: **DID NOT FIRE** — no parent character exists (father/son merged)
- Attempt 2: Fixed narrator detection to trust explicit "narrator, known as [Name]" identification
  - Modified: `src/pipeline/character_extraction_v2/narrator.py`
  - Result: Fixed — Bill is now narrator ✓
- Attempt 3: Added exact_firstname guard to `_merge_lastname_aliases`
  - Modified: `src/agents/characters.py` — `_merge_lastname_aliases()`
  - Result: **REGRESSION** — "American, sir" false character, narrator shifted. REVERTED.
- Attempt 4: Reverted attempt 3, then applied co-present guard to `_merge_summary_name_fragments()` (Step 5.4.5)
  - Modified: `src/agents/characters.py` — `_merge_summary_name_fragments()`
  - Result: "American, sir" gone ✓, narrator regressed ✗, Johnny/John's Son false split ✗
- Attempt 5:
  1. Improved narrator prompt: added frame-narrative clarification
     - Modified: `src/pipeline/character_extraction_v2/narrator.py`
  2. Added Step 4.26 low-mention narrator guard (CRASHED: `'list' object has no attribute 'get'`)
     - Modified: `src/agents/characters.py` — new Step 4.26 block
  3. Added Step 5.4.6 possessive-descriptor merge (WRONG DIRECTION: merged into father not son)
     - Modified: `src/agents/characters.py` — new Step 5.4.6 block
  - Result: Plot summary improved ✓. Narrator still wrong ✗. "the boy" on father instead of son ✗.
- Attempt 6:
  1. Fixed `narrator.py detect()` crash (list vs dict unwrapping)
     - Modified: `src/pipeline/character_extraction_v2/narrator.py`
  2. Raised min-mention narrator guard from ≤1 to ≤2
     - Modified: `src/pipeline/character_extraction_v2/narrator.py`
  3. Fixed Step 5.4.6 merge direction (descriptor→proper name)
     - Modified: `src/agents/characters.py`
  - Result: Uncle Bill narrator ✓. Merge direction fixed ✓. But John Donaldson false secondary narrator → profile catastrophe.
- Attempt 7:
  1. Added mention-count guard for secondary narrators in `update_characters_with_narrator()`
     - Modified: `src/pipeline/character_extraction_v2/narrator.py`
     - Result: John Donaldson no longer false secondary narrator ✓. Profiles improved (4.5→6) ✓.
     - New: Boy (Johnny) disappeared — merged into father. Plot summary fabricated false twist.
- Attempt 8:
  1. Added Step 5.9.5 role assignment fix — mention-count-based role upgrades for main_cast
     - Modified: `src/agents/characters.py`
     - Result: John Donaldson (son) now "protagonist" ✓
  2. Added nested narration guidance to summarizer CHUNK+CONSOLIDATE prompts
     - Modified: `src/pipeline/summarization/summarizer.py`
     - Result: Chapter summaries correctly attribute embedded narrative to the boy ✓, plot summary no longer fabricated ✓
- Attempt 9:
  1. Added RULE 3d + RULE 3e to verify_aliases() in main_cast.py
     - Modified: `src/pipeline/character_extraction_v2/main_cast.py`
     - Result: Cross-character alias contamination fixed ✓. Son no longer has "the father" etc.
  2. Fixed secondary profiler prompt to forbid "associated"/"acquaintance"
     - Modified: `src/analyzer.py` — secondary prompt only (~line 3405)
     - Result: **PARTIAL** — Ted Frith got "companion" ✓, but main characters still all "associated" because PRIMARY prompt was not modified.

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 2 | Wrong narrator (Uncle Bill vs Johnny) | `narrator.py` | Fixed — Bill is now narrator ✓ |
| 3 | Johnny missing — exact_firstname guard | `characters.py` | **REGRESSION** — REVERTED |
| 4 | Johnny false-merged — co-present guard Step 5.4.5 | `characters.py` | "American, sir" gone ✓, narrator regressed ✗ |
| 5 | Narrator guard (Step 4.26) | `characters.py` | **BUG** — crashed, never fired |
| 5 | Possessive-descriptor merge (Step 5.4.6) | `characters.py` | **WRONG DIRECTION** |
| 5 | Narrator prompt (frame narrative) | `narrator.py` | Partial — prompt works but code guard fails |
| 6 | narrator.py detect() crash | `narrator.py` | Fixed ✓ |
| 6 | Min-mention narrator guard ≤2 | `narrator.py` | Fixed ✓ |
| 6 | Step 5.4.6 merge direction | `characters.py` | Fixed ✓ |
| 7 | John Donaldson false secondary narrator | `narrator.py` | Fixed ✓ — mention-count guard blocks correctly |
| 7 | Boy disappeared (false merge with father) | (not yet attempted) | **NEW ISSUE** |
| 7 | Plot summary fabrication | (not yet attempted) | **NEW ISSUE** |
| 8 | Role assignment: John Donaldson (28 mentions) was "supporting" | `characters.py` — Step 5.9.5 | Fixed ✓ |
| 8 | Chapter summary nested narration | `summarizer.py` — prompts | Fixed ✓ — summaries now correct |
| 8 | Father/son split | (side effect of summary fix) | Fixed ✓ in attempts 8-9, REGRESSED in attempt 10 |
| 9 | Cross-character alias contamination | `main_cast.py` — RULE 3d/3e | Fixed ✓ — contamination blocked |
| 9 | Generic relationship labels (secondary prompt) | `analyzer.py` — secondary prompt | **PARTIAL** — secondary works, primary NOT modified |
| 10 | Primary profiler "associated" labels | `analyzer.py` — post-filter + secondary call trigger | **NO EFFECT** — still "associated" |
| 10 | "John's son" confusing canonical name | `characters.py` — new Step 5.4.6b | **DID NOT FIRE** — no parent character (merged) |

**Pattern:** Father/son split is NON-DETERMINISTIC across LLM runs. Attempts 8-9 split correctly; attempt 10 merged. Programmatic enforcement needed — prompt-only approach is unreliable after 3 attempts.

## Configuration Notes
- Model config appropriate: qwen3.5:122b-a10b for characters/summaries/profiles, qwen3.5:35b-a3b for structure/pronunciation
- Zero LLM retries across all stages
- All 13 pronunciations have IPA
- Runtime: ~35 min (33 LLM calls)
- Narrator detection returned None — needs robustness fix

## Pipeline Notes (Attempt 11)
- Runtime: 9m 51s, 31 LLM calls, 70,489 tokens
- Characters found: Uncle Bill (18), John Donaldson (43 — still merged), Joe Barron (3), Ted Frith (5)
- Margaret Donaldson added by F6 reconciliation
- Narrator from V2 pipeline: "The Narrator (Uncle Bill)" ✓ — narrator fix appears to have worked
- STEP 3.95 did NOT split father/son — John Donaldson still has 43 mentions (combined), aliased as "the father"
- "associated" relationship cleanup: to be confirmed by evaluation

## Next Action
Evaluate output (PROMPT_evaluate.md)
