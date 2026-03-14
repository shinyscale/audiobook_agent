# Current Evaluation State

## Active Text
- **Name:** frankenstein
- **Attempt:** 29
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
| 28 | 6.30 | Summaries FIXED ✓ (Victor chapters correct). BUT: Creature/De Lacey FALSE MERGE (catastrophic). Profiles regressed. |

## Latest Scores
- Structure Detection: 8/10 ✓
  - 28 chapters correct (4 letters + 24 chapters)
  - Letter 1 title=null (minor)
- Character Extraction: 4/10 ✗ (CRITICAL REGRESSION)
  - Completeness: 5/10 — The Creature is MISSING as a separate character (merged into "the old man"/De Lacey). "Father" (134 mentions) is an unmerged F6 fragment of Alphonse.
  - Identity Resolution: 3/10 — FALSE MERGE: "the old man" (De Lacey) has the Creature's aliases ("the monster", "the fiend", "the being", "the dæmon"). Two completely different characters merged. "Father" fragment unmerged.
  - Alias Grouping: 4/10 — Creature's aliases are on wrong character entirely.
- Character Profiles: 4/10 ✗ (REGRESSION)
  - Victor→Alphonse: "brother" — WRONG (was "son" in attempt 27, regressed!)
  - Alphonse→Victor: "brother" — WRONG (was "father" in attempt 27, regressed!)
  - Alphonse→Robert Walton: "father" — WRONG (Walton is not Alphonse's son)
  - Robert Walton→Caroline: "son", →Alphonse: "son" — WRONG (Walton has no family connection to Frankensteins)
  - Caroline→Robert Walton: "parent" — WRONG
  - Elizabeth: 0 relationships — still empty
  - "the old man"→Clerval: "close friend" — actually Creature's relationship, on wrong character
  - Justine→"the old man": "victim" — should be victim of Creature
  - Only 6/20 with physical descriptions; Victor (protagonist) has none
- Chapter Summaries: 7.5/10 ✗
  - **FIX III WORKED**: Victor's chapters (2, 4, 5, 6, 8, 9, 19, 20, 24) now correctly say "Victor Frankenstein" ✓
  - Ch14 (idx 18): STILL "Felix The narrator" and "the The narrator family" — compound substitution bug persists
  - Letter 3 (idx 3): "R.W narrator" — odd phrasing
  - Creature chapters (11-16) correctly use "The narrator" ✓
- Pronunciation Guide: 8/10 ✓
  - 232/235 have IPA; good coverage
- HTML Presentation: 8/10 ✓
- **Overall: 6.30/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (4 categories below threshold: Characters 4.0, Profiles 4.0, Summaries 7.5)

## Current Issues (Priority Order)

### CRITICAL
1. **FALSE MERGE: Creature merged into "the old man" (De Lacey)** [Identity Resolution]
   - Problem: "the old man" (main_cast_2, 103 mentions) has aliases: "the monster", "the fiend", "the being", "the dæmon", "De Lacey", "the old man (De Lacey)". The Creature does NOT exist as a separate character.
   - Evidence: "the old man" is De Lacey (the blind father in the cottage). "the monster/fiend/being/dæmon" is the Creature (Victor's creation). These are completely different characters. The physical description ("silver hair and benevolent countenance") is De Lacey's, but the relationships ("Clerval: close friend", "Walton: enemy") are the Creature's.
   - Root cause: The extraction pipeline is merging two unrelated descriptor-only characters. Both "the old man" and "the monster/creature" are descriptor canonicals. The merge logic (Step 3.6b `_merge_descriptor_into_proper_name` or Step 3.4 pre-merge) may be treating them as aliases of the same entity because they co-occur frequently or share some mention context.
   - Location: `src/pipeline/character_extraction_v2/characters.py` — likely Step 3.4 pre-merge or Step 3.6b descriptor merge
   - Fix: The Creature and De Lacey must remain separate. They have different core nouns ("old man" vs "monster/fiend/creature"). Rule 0.5 (core noun check) should block this, but may not be firing for descriptor-to-descriptor merges. Verify that `verify_aliases` runs for descriptor-descriptor merges and that Rule 0.5 blocks "the monster" as alias of "the old man".

2. **"Father" F6 fragment unmerged with Alphonse** [Completeness]
   - Problem: "Father" (a30ca91be97a, 134 mentions) exists as separate character from "Alphonse Frankenstein" (main_cast_5, 10 mentions). Its only relationship is "Caroline Beaufort: husband" which is correct for Alphonse.
   - Evidence: "Father" in Frankenstein refers to Alphonse Frankenstein (Victor's father). 134 mentions is the highest of any character.
   - Location: F6 reconciliation in `src/analyzer.py` or post-extraction merge in `characters.py`
   - Fix: "Father" should be detected as a kinship term for an existing character. `_merge_descriptor_into_proper_name()` should merge "Father" into "Alphonse Frankenstein" since it's a common-noun descriptor for a proper-name character.

### HIGH
3. **Victor→Alphonse "brother" REGRESSED from attempt 27** [Profiles]
   - Problem: Victor→Alphonse: "brother" and Alphonse→Victor: "brother". In attempt 27, these were correctly "son" and "father" respectively (Fix FFF).
   - Evidence: Alphonse is Victor's father, not brother.
   - Root cause: Fix FFF's kinship bootstrapping may not have fired in this run, or Fix OOO/NNN changes affected relationship inference. Check if Fix FFF code still runs and whether the kinship alias "his father" on Alphonse is being processed.
   - Location: `post_corrections.py` — kinship bootstrapping or `_propagate_missing_reverses`

4. **Walton has wrong familial relationships** [Profiles]
   - Problem: Robert Walton→Caroline Beaufort: "son", →Alphonse: "son". Walton is NOT their son; Victor is.
   - Evidence: Walton is an Arctic explorer with no family connection to the Frankensteins.
   - Root cause: The profiler may be attributing Victor's family relationships to Walton because Walton is the frame narrator and Victor's story is told through Walton's letters. The narrator-character confusion in profiling.
   - Location: `analyzer.py` F9 profiling — narrator_name may still cause cross-attribution

5. **Elizabeth still has 0 relationships** [Profiles]
   - Problem: Elizabeth (92 mentions, 2nd highest) has NO relationships at all.
   - Evidence: Elizabeth is Victor's fiancée/wife, William's adoptive sister, Alphonse's ward.
   - Location: `analyzer.py` F9 or `post_corrections.py` — persistent issue across many attempts

6. **Ch14 (idx 18) compound substitution persists** [Summaries]
   - Problem: "the The narrator family" and "Felix The narrator" — nonsensical.
   - Evidence: Should be "the De Lacey family" and "Felix De Lacey". The regex replaces "the narrator" even inside compound constructs.
   - Location: `src/pipeline/summarizer/summarizer.py` or `analyzer.py` Step 6.9
   - Fix: When the narrator is the Creature, do NOT substitute "the narrator" with a name in Creature chapters (Creature has no proper name). Or: don't substitute when preceded by a proper name or "the".

### MEDIUM
7. **Multiple characters with 0 relationships** [Profiles]
   - Agatha (22 mentions): 0 relationships. Should have Felix (brother), the old man (father), Safie (friend).
   - Safie (25 mentions): 0 relationships. Should have Felix (love interest).
   - Felix: has only 0 explicit relationships listed.
   - Root cause: Supporting characters get sparse profiling from F9.

8. **Victor has NO physical description** [Profiles]
   - First-person narrator rarely describes themselves. Minor but notable for protagonist.

9. **Cornelius Agrippa and Werter as characters** [Characters]
   - Historical/literary references, minor noise. Agrippa has "referenced authority" relationships which are unusual but not harmful.

### LOW
10. **Letter 3 "R.W narrator" odd phrasing** [Summaries]

## Attempt 28 Fixes (Results)

### Fix III (analyzer.py): Step 6.9 blocked-narrator replacement guard — **WORKED ✓**
- Victor's chapters now correctly say "Victor Frankenstein" instead of "Robert Walton"
- Ch5 correctly says "Victor Frankenstein succeeds in animating a creature" ✓
- 9 previously wrong chapters now correct

### Fix HHH (analyzer.py): Early inner narrator for profiling — **UNCLEAR**
- narrator_detected set to "Victor Frankenstein" before profiling
- But profiles still show wrong relationships (Victor→Alphonse "brother"), so profiling improvement is limited

### Fix NNN/JJJ: protagonist-only possessive aliases + uninformative label cleanup — **MIXED**
- "not mentioned" labels cleaned up ✓
- But possessive alias changes may have contributed to Creature/De Lacey merge

### Fix OOO/PPP: creator/creation relationship detection — **DID NOT HELP**
- Creature is merged with De Lacey, so creator/creation relationships can't be correctly assigned
- "the old man"→Clerval: "close friend" and →Walton: "enemy" are the Creature's relationships misattributed

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
- Attempt 28: Fix III (narrator substitution fixed ✓), Fix HHH (early narrator for profiling — unclear), Fix NNN/JJJ (possessive aliases — may have caused Creature/De Lacey merge), Fix OOO/PPP (creator detection — blocked by merge)

## Root Cause Analysis

### The THREE remaining blockers are Characters (4.0), Profiles (4.0), and Summaries (7.5).

**Creature/De Lacey false merge (CRITICAL):** This is the worst regression since attempt 23. The Creature (103 mentions combined with De Lacey) has been merged with "the old man" De Lacey. Both are descriptor-canonical characters ("the old man", "the creature/monster/fiend"). The merge likely happened in Step 3.4 or 3.6b — descriptor characters with overlapping chapter appearances were combined. Fix NNN/JJJ changes to possessive alias handling may have inadvertently enabled this merge. The core issue: Rule 0.5 (core noun mismatch) should block "the monster" from being aliased to "the old man" — "monster" ≠ "man". Check if Rule 0.5 is being bypassed.

**"Father" fragment:** F6 reconciliation is creating "Father" as a separate character (134 mentions!) instead of recognizing it as a kinship reference to Alphonse. `_merge_descriptor_into_proper_name()` should handle this but may not be matching because "Father" is capitalized (looks proper) or because it lacks the 2x mention asymmetry condition (134 >> 10).

**Profile regression:** Victor→Alphonse "brother" was fixed in attempt 27 by Fix FFF (kinship bootstrapping). Either Fix FFF code was overwritten, or the Creature/De Lacey merge disrupted the processing order. The Walton familial relationships (Caroline: "son", Alphonse: "son") are the profiler confusing narrator with character.

**Priority for next fix:**
1. **Investigate and fix Creature/De Lacey merge** — find which step merges them and add a guard. Check if Fix NNN/JJJ introduced the regression.
2. **Fix "Father" fragment** — merge into Alphonse
3. **Verify Fix FFF still runs** — check if kinship bootstrapping code is intact
4. **Ch14 compound substitution** — add guard for Creature chapters

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 28 | Step 6.9 blocked-narrator guard (nested detection) | analyzer.py (Fix III) | **FIXED ✓** |
| 28 | Early inner narrator for profiling narrator_name | analyzer.py (Fix HHH) | Unclear |
| 28 | Protagonist-only possessive aliases | characters.py (Fix NNN/JJJ) | **MAY HAVE CAUSED CREATURE/DE LACEY MERGE** |
| 28 | Creator/creation relationship detection | post_corrections.py (Fix OOO/PPP) | Blocked by merge |
| 28 | "not mentioned" uninformative label cleanup | post_corrections.py | WORKED ✓ |
| 27 | Victor fragmentation (Step 3.95 guard) | characters.py (Fix EEE) | **PARTIAL** — Victor unified ✓, but caused Step 6.9 regression |
| 27 | Multi-narrator kinship bootstrapping | post_corrections.py (Fix FFF) | **PARTIAL** — Alphonse rels fixed ✓, Elizabeth still empty |
| 27 | Secondary narrator role floor | narrator.py (Fix GGG) | **WORKED ✓** |
| 26 | Ch16 narrator (narrator_detected fallback) | summarizer.py (Fix BBB) | **FIXED ✓** |
| 26 | "none" relationship cleanup | post_corrections.py (Fix CCC) | **FIXED ✓** |
| 26 | Geographic setting examples in prompt | main_cast.py (Fix DDD) | FAILED |
| 25 | Ch16 creature narrator misattribution | summarizer.py (Fix ZZ) | FAILED |
| 25 | Elizabeth/Clerval empty relationships | analyzer.py (Fix AAA) | PARTIAL |
| 24 | narrator.py outputs outer narrator | narrator.py (Fix XX) | MOSTLY FIXED ✓ |
| 24 | Felix/De Lacey false merge | analyzer.py (Fix YY) | Fixed ✓ |

## Next Action
Run PROMPT_fix.md — PRIORITY: investigate Fix NNN/JJJ as cause of Creature/De Lacey merge, then fix "Father" fragment and profile regressions.
