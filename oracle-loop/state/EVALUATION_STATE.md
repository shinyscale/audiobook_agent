# Current Evaluation State

## Active Text
- **Name:** frankenstein
- **Attempt:** 26
- **Phase:** awaiting_evaluation
- **baseline_score:** 7.35

## Output Files
- HTML: ../output/frankenstein/report.html
- JSON: ../output/frankenstein/analysis.json

## Pipeline Notes
- 28 chapters found (same as previous attempts)
- 25 characters extracted; "the Arctic Ice" still appears despite Fix DDD prompt additions
- Victor Frankenstein set as narrator via Step 6.9 fallback (Robert Walton had only 3 mentions, skipped)
- Fix BBB (narrator_detected fallback for Ch16) pending evaluation
- Fix CCC ("none" relationship cleanup) pending evaluation
- Fix DDD (geographic setting prompt) — "the Arctic Ice" still extracted (prompt guidance may not be sufficient)
- Pronunciation: 235 words flagged (same as attempt 25); multiple JSON validation retries but completed
- Runtime: 200m 33s

## Score History
| Attempt | Score | Notes |
|---------|-------|-------|
| 1 | 7.35 | Baseline |
| 20 | ~7.35 | No improvement: creature fragmentation, Elizabeth gender/rels, wrong Alphonse rel |
| 21 | 7.15 | Creature unified ✓, but duplicates (Walton, De Lacey), poor canonicals, empty profiles |
| 22 | (killed) | Had Fix OO/PP/QQ but missing Fix RR/SS/TT/UU/WW — killed to avoid wasting 2.5h |
| 23 | 6.45 | Canonicals fixed ✓, duplicates fixed ✓, but systematic narrator substitution errors in summaries; Felix/De Lacey false merge |
| 24 | 7.50 | Narrator substitution MOSTLY FIXED ✓, De Lacey now separate ✓, Victor→Alphonse fixed ✓ |
| 25 | 7.25 | Fix ZZ/AAA failed: Ch16 still wrong, Elizabeth still empty. New: Arctic ice as character, De Lacey father missing again |

## Latest Scores
- Structure Detection: 8/10 ✓
  - 28 chapters correct (4 letters + 24 chapters)
  - Letter 1 title=null (minor)
- Character Extraction: 7/10 ✗
  - Completeness: 7/10 — "the Arctic ice" (78 mentions) extracted as protagonist character — it's a SETTING not a character. De Lacey father (the old man) MISSING (was main_cast_9 in attempt 24).
  - Identity Resolution: 7.5/10 — Creature unified ✓, no false merges. But De Lacey father absorbed/missing.
  - Alias Grouping: 7/10 — "Father" as canonical instead of "Alphonse Frankenstein" (regression from attempt 24). "De Lacey" still alias of Felix only (should belong to the old man).
- Character Profiles: 6/10 ✗
  - Elizabeth (94 mentions): Fix AAA FAILED — only relationship is "the Arctic ice: setting of final demise" (nonsensical). Should have Victor as fiancé/husband.
  - Clerval: "Victor Frankenstein: close friend" ✓ (IMPROVEMENT from attempt 24). But also has filler "William: none", "Felix: none".
  - Victor→William: "son" — WRONG. William is Victor's BROTHER, not son. Victor's father is Alphonse.
  - the creature→Victor: "enemy" — misses the most important relationship: creator.
  - the creature role: "supporting" — REGRESSION from attempt 24 where it was "protagonist".
  - "the Arctic ice" has 5 nonsensical relationships ("Elizabeth: none", "Father: none", etc.) polluting profiles.
  - Felix: only "the creature: observer and learner" — missing De Lacey (father), Agatha (sister), Safie (love interest).
  - 5 characters with zero relationships (Justine, Agatha, Safie, Ernest, Werter).
  - 8/20 with physical descriptions. Victor (71 mentions, protagonist) has NO physical description.
- Chapter Summaries: 7/10 ✗
  - Ch16 (index 20): Fix ZZ FAILED — STILL says "Victor Frankenstein burns their hovel" and "Victor Frankenstein strangles the child". These are the CREATURE's actions. Critical error.
  - Ch14 (index 18): STILL says "The narrator family", "Felix The narrator" — broken substitution.
  - Ch15 (index 19): "The narrator" — correct for creature chapter.
  - Ch1 (index 5), Ch10 (index 14), Ch20 (index 24), Ch21 (index 25): "The narrator" instead of "Victor Frankenstein" — inconsistent but not wrong.
  - Letter 3 (index 3): "R.W narrator" — odd phrasing.
  - Ch8 (index 12): "Victor Frankenstein accompanies their family" — pronoun mismatch ("their" should be "his").
  - Most Victor chapters (2-9, 17-19, 22-28) correctly attributed ✓.
  - Letters 1-4 correctly attributed to Walton ✓.
- Pronunciation Guide: 8/10 ✓
  - 232/235 have IPA; good coverage of unusual names.
- HTML Presentation: 8/10 ✓
- **Overall: 7.25/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold: Characters 7, Profiles 6, Summaries 7)

## Current Issues (Priority Order)

### CRITICAL
1. **Ch16 narrator misattribution PERSISTS — Fix ZZ did not work** [Summaries]
   - Problem: Ch16 (index 20) still says "Victor Frankenstein burns their hovel" and "Victor Frankenstein strangles the child to death". These are the CREATURE's actions.
   - Evidence: Fix ZZ extended `_quoted_any_re` to catch chapters starting with a quote character. Either the regex didn't match Ch16's text, or the FP-count heuristic didn't trigger, or the fix was overridden by Step 6.9 substitution afterwards.
   - Location: `src/pipeline/chapter_summary/summarizer.py` (Fix ZZ regex) AND `src/analyzer.py` Step 6.9 (narrator substitution)
   - Root cause: Step 6.9 replaces "the narrator" → "Victor Frankenstein" globally for ALL chapters in Victor's frame. Even if the summarizer correctly outputs "the narrator" for creature chapters, Step 6.9 overwrites it. **The fix must be in Step 6.9**, not in summarizer.py.
   - Fix: Step 6.9 must check per-chapter narrator. Chapters 11-16 (creature's narration within Victor's narration) should NOT substitute Victor's name. Either: (a) use the creature's `is_narrator=True` + chapter range detection, or (b) check if the summary already mentions "the creature" performing actions and skip substitution for that chapter.

2. **Elizabeth still has no meaningful relationships — Fix AAA did not work** [Profiles]
   - Problem: Elizabeth (94 mentions) has only "the Arctic ice: setting of final demise" — no Victor relationship.
   - Evidence: Fix AAA was supposed to substitute narrator_name for "the narrator" in F2 evidence before F9 runs. Either the substitution didn't fire (pov check?), or F9 still failed to extract relationships from the evidence.
   - Location: `src/analyzer.py` — Fix TT/AAA block (~line 4861), then F9 relationship extraction
   - Fix: Debug whether Fix AAA actually ran. Check if F2 evidence for Elizabeth now contains "Victor Frankenstein" instead of "the narrator". If yes, F9 prompt quality is the issue. If no, the substitution condition didn't fire.

### HIGH
3. **"the Arctic ice" extracted as protagonist character** [Characters - Completeness]
   - Problem: "the Arctic ice" (main_cast_2, 78 mentions) is extracted as a character with role "protagonist" and relationships to other characters. It's a geographic SETTING, not a character or symbolic entity.
   - Evidence: Unlike symbolic forces (Red Death, the monkey's paw), "the Arctic ice" doesn't act as an agent in the narrative. Its relationships are all "none" or "setting of X" — even the LLM knows it's a setting.
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` — extraction phase. Or post-extraction filtering.
   - Fix: Add a filter to reject candidates whose relationships are ALL "none"/"setting of" — these are settings not characters. Or add "ice", "ocean", "forest", "mountain" etc. to an exclusion list for non-agent nouns. However, this must be generic (per CLAUDE.md rules).

4. **"Father" as canonical name instead of "Alphonse Frankenstein"** [Characters - Alias Grouping]
   - Problem: Alphonse Frankenstein's canonical name is "Father" (a kinship term) with "Alphonse Frankenstein" as an alias. Attempt 24 had "Alphonse Frankenstein" as canonical.
   - Evidence: This is LLM variability between runs. The pipeline should prefer proper names over kinship terms as canonical.
   - Location: `src/pipeline/character_extraction_v2/characters.py` — canonical name selection logic
   - Fix: Existing Fix PP should handle this (prefer proper names over kinship). If it ran but the LLM's initial extraction used "Father" with higher mention count, the mention-based canonical selection may override proper-name preference. Verify Fix PP still applies.

5. **De Lacey father (the old man) MISSING** [Characters - Completeness]
   - Problem: The old man (De Lacey father, blind man who plays the guitar) was main_cast_9 in attempt 24 but is completely absent in attempt 25. Only Felix, Agatha, and Safie represent the De Lacey family.
   - Evidence: The old man is a significant character in chapters 11-16 (creature's narration). His encounter with the creature in Ch15 is a pivotal scene.
   - Location: LLM variability in extraction. The pipeline correctly extracted him in attempt 24; this run he wasn't proposed.
   - Fix: This is non-deterministic. The old man may or may not appear depending on the LLM run. If the pipeline has F6 reconciliation for summary-mentioned characters, verify "the old man" appears in chapter summaries for Ch11-15.

6. **Victor→William: "son" is WRONG** [Profiles]
   - Problem: Victor lists William as "son" but William is Victor's younger BROTHER, not son. Victor's father is Alphonse.
   - Evidence: William Frankenstein is the youngest brother, murdered by the creature in Ch7-8.
   - Location: `src/analyzer.py` F9 or `post_corrections.py`
   - Fix: LLM hallucination. The text says "my youngest brother" explicitly. This may be a consequence of the narrator substitution — if summaries say "Victor Frankenstein's son William" due to misattribution, F9 picks it up. Check Ch7-8 summaries for this error.

7. **the creature role = "supporting" (regression from "protagonist" in attempt 24)** [Characters]
   - Problem: The creature (83 mentions, is_narrator) has role "supporting". In attempt 24 it was correctly "protagonist".
   - Evidence: The creature is one of the two central characters. LLM variability.
   - Location: Role assignment in character extraction
   - Fix: Non-deterministic. May need a rule: characters with `is_narrator=True` should be at least "main" role.

### MEDIUM
8. **"none" filler relationships polluting profiles** [Profiles]
   - Problem: Multiple characters have relationships like "William: none", "Felix: none", "Elizabeth: none". These provide no useful information.
   - Location: `post_corrections.py` — `clean_unknown_relationships` or F9
   - Fix: Filter out relationships with label "none" during post-processing.

9. **Ch14 broken "The narrator family" substitution** [Summaries]
   - Problem: Ch14 (index 18) says "The narrator family" and "Felix The narrator" instead of "the De Lacey family".
   - Evidence: The summarizer used "the narrator" as a noun phrase modifier, and substitution couldn't handle it.
   - Location: Summarizer prompt or Step 6.9 substitution
   - Fix: This is a summarizer prompt issue — the LLM should use proper names for the observed family (De Lacey), not "the narrator" as a possessive.

10. **Inconsistent narrator substitution across Victor chapters** [Summaries]
    - Ch1, Ch10, Ch20, Ch21 still say "The narrator" while other Victor chapters say "Victor Frankenstein".
    - Minor inconsistency, not factually wrong.

11. **Felix missing family relationships** [Profiles]
    - Felix only has "the creature: observer and learner". Missing: De Lacey (father), Agatha (sister), Safie (love interest).
    - Part of broader profile quality issue.

### LOW
12. **Letter 3 "R.W narrator" odd phrasing** [Summaries]
13. **Ch8 "their family" pronoun mismatch** [Summaries]

## Attempt 26 Fixes (Applied, Awaiting Analysis)

### Fix BBB (summarizer.py): Ch16 narrator misattribution — narrator_detected fallback in Fix 6
- Root cause: Fix 6's name detection found "De Lacey" (first multi-word capitalized name in first sentence of summary "After being rejected from the **De Lacey** cottage, Victor Frankenstein burns..."). "De Lacey" appears only once in the summary → count guard sets wrong_name3=None → fix doesn't apply.
- Fix: After existing detection fails, check if narrator_detected appears ≥2 times in summary. If so, use narrator_detected as wrong_name3. Universal: only fires for inner-narrator chapters (Fix 6 condition: quoted opening + FP density) when the primary narrator's name was substituted by Step 6.9.
- Location: `summarizer.py:_fix_narrator_attribution():~line 1492`

### Fix CCC (post_corrections.py): Add "none" to uninformative relationship labels
- Added "none" to `clean_unknown_relationships._uninformative` set
- Removes "William: none", "Felix: none", "Elizabeth: none" etc. from character profiles
- Location: `post_corrections.py:clean_unknown_relationships():~line 3322`

### Fix DDD (main_cast.py): CHARACTER_IDENTIFICATION_PROMPT geographic setting examples
- Expanded Rule 1 examples to include outdoor geographic features (ship, arctic landscape, mountain, sea)
- Prevents LLM from extracting environmental settings as characters in future runs
- Location: `main_cast.py:CHARACTER_IDENTIFICATION_PROMPT:~line 86`

## Attempt 25 Fixes (Results)

### Fix ZZ (summarizer.py): Ch16 narrator misattribution — FAILED
- Extended `_quoted_any_re` to match chapters starting with quote character without "Chapter N" heading
- Result: Ch16 STILL says "Victor Frankenstein" — the fix either didn't match or Step 6.9 overwrites it afterward
- **Root cause confirmed**: The problem is in Step 6.9, not summarizer.py. Step 6.9 globally replaces "the narrator" → "Victor Frankenstein" for all chapters, including creature chapters.

### Fix AAA (analyzer.py): Elizabeth/Clerval empty relationships — PARTIAL
- Substituted narrator_name for "the narrator" in F2 evidence statements
- Result: Clerval now has "Victor Frankenstein: close friend" ✓ (was empty). Elizabeth STILL has no meaningful relationships (only "Arctic ice" nonsense). Fix worked for Clerval but not Elizabeth.
- **Possible cause**: Elizabeth's F2 evidence may not contain "the narrator" in the right context, or F9 extraction failed for her specifically.

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

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 26 | Ch16 narrator (narrator_detected fallback) | summarizer.py (Fix BBB) | Pending |
| 26 | "none" relationship cleanup | post_corrections.py (Fix CCC) | Pending |
| 26 | Geographic setting examples in prompt | main_cast.py (Fix DDD) | Pending |
| 25 | Ch16 creature narrator misattribution | summarizer.py (Fix ZZ) | FAILED — Step 6.9 overwrites, fix was in wrong layer |
| 25 | Elizabeth/Clerval empty relationships | analyzer.py (Fix AAA) | PARTIAL — Clerval fixed ✓, Elizabeth still empty |
| 24 | narrator.py outputs outer narrator | narrator.py (Fix XX) | MOSTLY FIXED ✓ |
| 24 | Felix/De Lacey false merge | analyzer.py (Fix YY) | Fixed ✓ |
| 23 | Ch11 nested narrator error | summarizer.py (Fix RR) | Partial ✓ |
| 23 | F9 evidence uses pronouns | analyzer.py (Fix TT) | Partial — helped Clerval in attempt 25 |
| 23 | Canonical parentheticals | characters.py (Fix UU) | Fixed ✓ |
| 23 | "the fiend" canonical | characters.py (Fix WW) | Fixed ✓ |
| 22 | Walton/De Lacey F6 duplicates | analyzer.py (Fix OO) | Fixed ✓ |
| 22 | "my father" canonical | characters.py (Fix PP) | Fixed ✓ (but regressed in attempt 25) |

## Root Cause Analysis

The THREE remaining blockers require focused fixes:

1. **Ch16 narrator (Summaries → 7/10)**: Fix ZZ targeted summarizer.py but the REAL problem is Step 6.9 in analyzer.py. Step 6.9 globally substitutes "the narrator" → "Victor Frankenstein" for all chapters. It must SKIP creature chapters (11-16). The creature has `is_narrator=True` — Step 6.9 should check if a chapter's content refers to creature actions and leave "the narrator" untouched for those chapters. **Next fix must target analyzer.py Step 6.9, NOT summarizer.py.**

2. **Elizabeth empty profiles (Profiles → 6/10)**: Fix AAA partially worked (Clerval now has relationships), but Elizabeth still has none. The F9 extraction may need explicit reciprocal relationship injection — if Victor→Elizabeth is found, Elizabeth→Victor should be created automatically. Or Elizabeth's F2 evidence may lack the right context. Debug F2 evidence content for Elizabeth.

3. **"the Arctic ice" as character (Characters → 7/10)**: A setting extracted as protagonist. Need a post-extraction filter to remove entries whose relationships are all "none"/"setting of" or whose name matches common geographic/environmental terms. This must be generic per CLAUDE.md.

## Next Action
Run PROMPT_fix.md to address:
1. Step 6.9 narrator substitution: skip creature chapters (CRITICAL)
2. Elizabeth relationship extraction or reciprocal injection (HIGH)
3. "the Arctic ice" filtering (HIGH)
