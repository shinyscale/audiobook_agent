# Current Evaluation State

## Active Text
- **Name:** frankenstein
- **Attempt:** 27
- **Phase:** awaiting_analysis
- **baseline_score:** 7.35

## Output Files
- HTML: ../output/frankenstein/report.html
- JSON: ../output/frankenstein/analysis.json

## Score History
| Attempt | Score | Notes |
|---------|-------|-------|
| 1 | 7.35 | Baseline |
| 20 | ~7.35 | No improvement: creature fragmentation, Elizabeth gender/rels, wrong Alphonse rel |
| 21 | 7.15 | Creature unified ✓, but duplicates (Walton, De Lacey), poor canonicals, empty profiles |
| 22 | (killed) | Had Fix OO/PP/QQ but missing Fix RR/SS/TT/UU/WW — killed to avoid wasting 2.5h |
| 23 | 6.45 | Canonicals fixed ✓, duplicates fixed ✓, but systematic narrator substitution errors in summaries; Felix/De Lacey false merge |
| 24 | 7.50 | Narrator substitution MOSTLY FIXED ✓, De Lacey now separate ✓, Victor→Alphonse fixed ✓ |
| 25 | 7.25 | Fix ZZ/AAA failed: Ch16 still wrong, Elizabeth still empty. New: Arctic ice as character |
| 26 | 7.30 | Fix BBB WORKED (Ch16 fixed ✓). Fix CCC worked (none cleanup ✓). Fix DDD failed (Arctic Ice persists). Profiles still broken. |
| 27 | 7.50 | Characters MUCH improved ✓ (Victor unified, De Lacey present, Arctic Ice gone). Summaries REGRESSED (9 chapters say "Robert Walton" instead of Victor). |

## Latest Scores
- Structure Detection: 8/10 ✓
  - 28 chapters correct (4 letters + 24 chapters)
  - Letter 1 title=null (minor)
- Character Extraction: 8.5/10 ✓
  - Completeness: 9/10 — All major characters present. Victor unified ✓, De Lacey father present ✓, Arctic Ice GONE ✓. 19 characters total. Cornelius Agrippa and Werter are historical/literary references (minor noise).
  - Identity Resolution: 9/10 — No false merges, no false splits. Victor unified with "the stranger", "Frankenstein", "Victor" aliases ✓. Creature unified ✓.
  - Alias Grouping: 8/10 — Felix has "De Lacey" alias (shared with the old man — "De Lacey" is primarily the father's name). Otherwise aliases are clean.
- Character Profiles: 6.5/10 ✗
  - Victor→Alphonse: "son" ✓ (FIXED from "brother"!) Alphonse→Victor: "father" ✓ (FIXED!)
  - Victor→Clerval: "close friend" ✓. Victor→Waldman: "protégé" ✓. Victor→creature: "enemy" — acceptable but missing "creator".
  - Elizabeth (92 mentions): only "the old man: source of compassion" — still nearly empty. Missing Victor (fiancée/wife), William (adoptive brother), etc.
  - Clerval→William: "brother" — WRONG (they're unrelated; Clerval is Victor's friend, not William's brother)
  - Creature→Victor: "enemy" — should also note "creator". Missing central relationship.
  - Felix: only "the creature: observer and admirer", "William: not mentioned" — sparse. Missing De Lacey (father), Agatha (sister), Safie.
  - Agatha: 0 relationships. The old man: 0 relationships. Safie: 0 relationships.
  - William: "the creature: murder victim", "Clerval: brother" — creature OK, Clerval WRONG.
  - Only 7/19 with physical descriptions. Victor (protagonist) has none.
- Chapter Summaries: 6/10 ✗ ← **REGRESSION from 7.5**
  - **9 chapters incorrectly say "Robert Walton" instead of Victor Frankenstein:**
    Ch2 (idx 6), Ch4 (idx 8), Ch5 (idx 9), Ch6 (idx 10), Ch8 (idx 12), Ch9 (idx 13), Ch19 (idx 23), Ch20 (idx 24), Ch24 (idx 28)
  - These are Victor's narrated chapters within Walton's frame. Step 6.9 narrator substitution is applying the FRAME narrator (Walton) to INNER narrator (Victor) chapters.
  - Ch5: "Robert Walton succeeds in animating a creature" — factually WRONG (Victor creates the creature)
  - Ch14 (idx 18): Still "Felix The narrator" — broken compound substitution persists.
  - Ch16 (idx 20): Still correctly says "The narrator" ✓ (Fix BBB holds).
  - Creature chapters (11-16) correctly use "The narrator" ✓.
  - Letter 3 (idx 3): "R.W narrator" — odd phrasing persists.
- Pronunciation Guide: 8/10 ✓
  - 232/235 have IPA; good coverage.
- HTML Presentation: 8/10 ✓
- **Overall: 7.50/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold: Profiles 6.5, Summaries 6.0)

## Current Issues (Priority Order)

### CRITICAL
1. **REGRESSION: 9 Victor chapters incorrectly say "Robert Walton"** [Summaries]
   - Problem: Step 6.9 narrator substitution replaces "the narrator" with "Robert Walton" in chapters that are Victor's narration within Walton's frame story. Ch5 says "Robert Walton succeeds in animating a creature" — factually WRONG.
   - Affected chapters: Ch2, Ch4, Ch5, Ch6, Ch8, Ch9, Ch19, Ch20, Ch24 (indices 6, 8, 9, 10, 12, 13, 23, 24, 28)
   - Evidence: In attempt 26, these chapters used "The narrator" (acceptable). Fix EEE/FFF/GGG changed narrator detection so Victor is now is_narrator=True, but Step 6.9 is choosing the WRONG narrator (Walton instead of Victor) for substitution in inner-narrative chapters.
   - Root cause: Step 6.9 likely picks the first/frame narrator (Walton) for all substitutions, or picks based on some heuristic that doesn't distinguish frame vs inner narration. With Victor now correctly detected as narrator, the logic needs to pick the RIGHT narrator per chapter.
   - Location: `src/pipeline/summarizer/summarizer.py` — Step 6.9 narrator substitution
   - Fix: Step 6.9 must check which narrator is active in each chapter. For Frankenstein: Letters 1-4 = Walton, Ch1-10 + Ch17-24 = Victor, Ch11-16 = Creature. The chapter's `narrator_detected` or `active_characters` should indicate which narrator is speaking. If multiple narrators exist, substitute with the narrator who appears in that chapter's active characters (or don't substitute at all — "The narrator" is safer than the wrong name).

2. **Elizabeth (92 mentions) has NO meaningful relationships** [Profiles]
   - Problem: Elizabeth's only relationship is "the old man: source of compassion" — irrelevant. Should have Victor (fiancée/wife), William (adoptive brother), Alphonse (adoptive father), Justine (friend).
   - Evidence: Elizabeth is the 2nd most-mentioned character. She grows up with Victor, they marry in Ch22.
   - Root cause: Fix FFF (kinship bootstrapping) was supposed to help — Elizabeth should have "his wife" or similar alias linking her to Victor. Either (a) Elizabeth doesn't have a possessive kinship alias, or (b) the kinship bootstrapping didn't fire properly.
   - Location: `post_corrections.py` — `_infer_relationships_from_possessive_aliases` or `src/analyzer.py` F9
   - Fix: (a) Check if Elizabeth has kinship alias; if so, kinship bootstrapping should link her to Victor. (b) Add reciprocal injection: if Victor→Elizabeth exists in Victor's profile, create Elizabeth→Victor automatically. (c) If neither, the F9 evidence for Elizabeth may be thin — try expanding F2 evidence window.

### HIGH
3. **Creature→Victor missing "creator" relationship** [Profiles]
   - Problem: Creature→Victor only shows "enemy". Should at minimum be "creator" — THE central relationship.
   - Evidence: Victor created the creature. The creature's narration repeatedly references "my creator".
   - Location: F9 profiling or post_corrections.py
   - Fix: If creature's aliases include "the monster"/"the creature" and Victor's profile says "enemy" toward creature, the reciprocal should include "creator" not just "enemy". Or: detect "creator"/"my creator" in creature's evidence text.

4. **Clerval→William: "brother" — WRONG** [Profiles]
   - Problem: Henry Clerval and William Frankenstein are listed as brothers. They are NOT related — Clerval is Victor's childhood friend; William is Victor's younger brother.
   - Evidence: The text never states Clerval and William are brothers.
   - Location: post_corrections.py or F9 prompt hallucination
   - Fix: The LLM may be confusing co-occurrence (both appear in Victor's narration) with kinship. `reject_unfounded_familial_labels` should catch this — check if it runs on "brother" labels between non-family characters.

5. **Ch14 (index 18) "Felix The narrator" broken compound** [Summaries]
   - Problem: "the The narrator family" and "Felix The narrator" — nonsensical compound substitution.
   - Evidence: Should be "the De Lacey family" and "Felix De Lacey".
   - Root cause: Step 6.9 replaces "the narrator" pattern even when it's part of a compound name/phrase. The regex is too greedy.
   - Location: summarizer.py Step 6.9
   - Fix: The substitution regex should not replace "the narrator" when preceded by a proper name or "the" (avoid "the The narrator" patterns). Better: skip substitution in creature chapters entirely (creature is not the one being substituted).

### MEDIUM
6. **Multiple characters with 0 relationships** [Profiles]
   - Agatha (22 mentions): 0 relationships. Should have Felix (brother), the old man (father), Safie (friend).
   - The old man (46 mentions): 0 relationships. Should have Felix (son), Agatha (daughter), creature (encountered).
   - Safie (25 mentions): 0 relationships. Should have Felix (love interest), the old man (host).
   - Root cause: Supporting characters get sparse profiling from F9.

7. **Victor has NO physical description** [Profiles]
   - Victor (71 mentions, protagonist, narrator): null physical_description.
   - First-person narrator rarely describes themselves. Elizabeth's letter (Ch6) describes Victor indirectly.

8. **Felix has "De Lacey" shared alias with the old man** [Characters - Alias Grouping]
   - "De Lacey" appears as alias for BOTH Felix and the old man. The old man is the patriarch — "De Lacey" primarily refers to him.
   - Fix: Remove bare "De Lacey" from Felix's aliases (keep "Felix De Lacey").

### LOW
9. **Letter 3 "R.W narrator" odd phrasing** [Summaries]
10. **Cornelius Agrippa and Werter as characters** [Characters] — historical/literary references, very minor noise

## Attempt 27 Fixes (Results)

### Fix EEE (characters.py): Step 3.95 parent-role conflict guard — **PARTIALLY WORKED**
- Victor Frankenstein is now unified as main_cast_1, protagonist, is_narrator=True ✓
- 71 mentions, proper aliases ("the stranger", "Frankenstein", "Victor") ✓
- BUT: This caused Step 6.9 to substitute "Robert Walton" into Victor's chapters (regression)

### Fix FFF (post_corrections.py): Multi-narrator kinship bootstrapping — **PARTIALLY WORKED**
- Victor→Alphonse: "son" ✓ and Alphonse→Victor: "father" ✓ — major improvement!
- But Elizabeth still has no Victor relationship — either she lacks kinship alias or bootstrapping didn't link her

### Fix GGG (narrator.py): Secondary narrator role floor — **WORKED ✓**
- Creature: role=protagonist ✓ (was "supporting" in attempt 26)
- Victor: role=protagonist ✓
- Arctic Ice: GONE (not extracted this run — LLM non-determinism or prompt from Fix DDD finally worked)

## Fix History
- Attempts 1-13: Various narrator detection fixes (Steps 4.5, 5.8.6, 6.9)
- Attempt 14: Step 6.9 picked Walton not Victor
- Attempt 15: Fix T (epistolary exclusion), Fix U (prominent narrator selection)
- Attempt 16: Fix V/W (narrator.py symbolic/mention guards)
- Attempt 17: Fix X/Y/AA (title patterns, Unicode tokenization, narrator ID selection) — REGRESSED
- Attempt 18: Fix BB (stop word filter in preamble) — REGRESSED
- Attempt 19: Guards CC2/CC3, Step 3.8 extended, Rule 0.5b extended
- Attempt 20: Fix DD/EE/FF/GG/HH — no improvement
- Attempt 21: Fix KK (creature fragment merge), Fix LL (kinship→relationship), Fix MM (gender), Fix NN — creature unified ✓
- Attempt 22: Fix OO/PP/QQ committed; killed
- Attempt 23: ALL fixes (OO/PP/QQ/RR/SS/TT/UU/WW) — canonicals fixed ✓
- Attempt 24: Fix XX (narrator.py inner narrator), Fix YY (alias guard) — narrator MOSTLY FIXED ✓
- Attempt 25: Fix ZZ (summarizer regex), Fix AAA (F2 evidence substitution) — ZZ failed, AAA partial (Clerval ✓, Elizabeth ✗)
- Attempt 26: Fix BBB (Ch16 narrator) ✓, Fix CCC (none cleanup) ✓, Fix DDD (Arctic Ice prompt) ✗
- Attempt 27: Fix EEE (Victor unified ✓, but caused Walton substitution regression), Fix FFF (Alphonse rels fixed ✓, Elizabeth still empty), Fix GGG (narrator roles ✓)

## Root Cause Analysis

The TWO remaining blockers are **Summaries (6.0)** and **Profiles (6.5)**.

**Summary regression root cause:** Fix EEE correctly made Victor a narrator (is_narrator=True). But Step 6.9 in summarizer.py now has MULTIPLE narrators (Walton, Victor, Creature) and is substituting the WRONG one (Walton) into Victor's chapters. The substitution logic needs to be chapter-aware: each chapter should only be substituted with its OWN narrator's name, not the frame narrator.

**Profile root cause (unchanged from attempt 26):** F9 relationship extraction is systematically failing for characters whose relationships are described through first-person narration pronouns. Elizabeth's relationships with Victor are described as "my love", "my dear cousin" — F2 evidence may not link her name directly to Victor.

**Priority for next fix:**
1. **Fix Step 6.9 narrator substitution** — must pick per-chapter narrator, not global frame narrator. When multiple narrators exist, either (a) use the narrator_detected field per chapter, or (b) don't substitute at all (safer than wrong name). → Summaries 6→8
2. **Reciprocal relationship injection** — if Victor→Elizabeth exists anywhere, create Elizabeth→Victor. → Profiles improvement
3. **reject_unfounded_familial_labels** for Clerval→William "brother" → Profiles improvement

## Attempt 28 Fixes

### Fix III (analyzer.py): Step 6.9 blocked-narrator replacement guard
- Root cause: Fix BBB's nested-narrator detection flags Victor's chapters as "nested" (they
  contain dialogue with FP pronouns after any quote in first 2000 chars). This prevented
  `_blocked_pat_69` ("Robert Walton" → "Victor Frankenstein") from running on Victor's chapters.
- Fix: Remove `not _is_nested_sum` guard from the blocked-narrator replacement condition.
  The blocked outer narrator's name shouldn't appear in creature chapters, so this is safe.
- Location: analyzer.py line ~3487
- Smoke test: 332 passed, 0 regressions

### Fix HHH (analyzer.py): Early inner narrator selection for profiling
- Root cause: narrator_detected = None at Step 4.6 (cleared when outer Walton was blocked).
  narrator_name = None passed to _generate_character_profile → Fix AAA (narrator→name subs)
  didn't run → F2 evidence kept "the narrator" placeholder → F9 found no relationships.
- Fix: Before Step 4.6, if narrator_detected is None and is_narrator chars exist (excluding
  blocked outer narrator), pick most prominent proper-name narrator → narrator_detected = "Victor Frankenstein"
- Location: analyzer.py ~line 2588 (before Step 4.6)

### Fix (post_corrections.py): "not mentioned" as uninformative relationship label
- Added "not mentioned" to _uninformative set (alongside "none", "unknown", "associated")
- Universal: any relationship valued "not mentioned" is meaningless and should be removed
- Removes spurious "Felix→William: not mentioned" type entries

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 28 | Step 6.9 blocked-narrator guard (nested detection) | analyzer.py (Fix III) | PENDING |
| 28 | Early inner narrator for profiling narrator_name | analyzer.py (Fix HHH) | PENDING |
| 28 | "not mentioned" uninformative label cleanup | post_corrections.py | PENDING |
| 27 | Victor fragmentation (Step 3.95 guard) | characters.py (Fix EEE) | **PARTIAL** — Victor unified ✓, but caused Step 6.9 regression |
| 27 | Multi-narrator kinship bootstrapping | post_corrections.py (Fix FFF) | **PARTIAL** — Alphonse rels fixed ✓, Elizabeth still empty |
| 27 | Secondary narrator role floor | narrator.py (Fix GGG) | **WORKED ✓** |
| 26 | Ch16 narrator (narrator_detected fallback) | summarizer.py (Fix BBB) | **FIXED ✓** |
| 26 | "none" relationship cleanup | post_corrections.py (Fix CCC) | **FIXED ✓** |
| 26 | Geographic setting examples in prompt | main_cast.py (Fix DDD) | FAILED — prompt guidance insufficient |
| 25 | Ch16 creature narrator misattribution | summarizer.py (Fix ZZ) | FAILED — Step 6.9 overwrites |
| 25 | Elizabeth/Clerval empty relationships | analyzer.py (Fix AAA) | PARTIAL — Clerval fixed ✓, Elizabeth still empty |
| 24 | narrator.py outputs outer narrator | narrator.py (Fix XX) | MOSTLY FIXED ✓ |
| 24 | Felix/De Lacey false merge | analyzer.py (Fix YY) | Fixed ✓ |
| 23 | Ch11 nested narrator error | summarizer.py (Fix RR) | Partial ✓ |
| 23 | F9 evidence uses pronouns | analyzer.py (Fix TT) | Partial — helped Clerval in attempt 25 |
| 23 | Canonical parentheticals | characters.py (Fix UU) | Fixed ✓ |
| 23 | "the fiend" canonical | characters.py (Fix WW) | Fixed ✓ |
| 22 | Walton/De Lacey F6 duplicates | analyzer.py (Fix OO) | Fixed ✓ |
| 22 | "my father" canonical | characters.py (Fix PP) | Fixed ✓ |

## Next Action
awaiting_analysis — run analysis to verify fixes
