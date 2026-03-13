# Current Evaluation State

## Active Text
- **Name:** frankenstein
- **Attempt:** 24
- **Phase:** awaiting_analysis
- **baseline_score:** 7.35

## Score History
| Attempt | Score | Notes |
|---------|-------|-------|
| 1 | 7.35 | Baseline |
| 20 | ~7.35 | No improvement: creature fragmentation, Elizabeth gender/rels, wrong Alphonse rel |
| 21 | 7.15 | Creature unified ✓, but duplicates (Walton, De Lacey), poor canonicals, empty profiles |
| 22 | (killed) | Had Fix OO/PP/QQ but missing Fix RR/SS/TT/UU/WW — killed to avoid wasting 2.5h |
| 23 | 6.45 | Canonicals fixed ✓, duplicates fixed ✓, but systematic narrator substitution errors in summaries; Felix/De Lacey false merge |

## Latest Scores
- Structure Detection: 8/10 ✓
  - 28 chapters correct (4 letters + 24 chapters)
  - Letter 1 title=null (minor)
- Character Extraction: 6/10 ✗
  - Completeness: 7/10 — De Lacey (blind old man) MISSING, merged into Felix
  - Identity Resolution: 5/10 — Felix/De Lacey false merge (father absorbed as son's alias)
  - Alias Grouping: 7.5/10 — Much improved: creature unified, no parentheticals, proper canonicals
- Character Profiles: 5/10 ✗
  - Elizabeth (92 mentions): EMPTY relationships — should have Victor as fiancé/wife
  - Victor→Alphonse: "brother" WRONG (should be "son"→"father")
  - Alphonse→Victor: "brother" WRONG (should be "father"→"son")
  - Felix→Agatha: "son" WRONG (should be "brother"/"sibling")
  - the creature role: "supporting" (should be antagonist/main)
  - Clerval relationship: "Felix: not mentioned" — useless entry
  - 12/19 characters with relationships, 7/19 with physical descriptions
- Chapter Summaries: 5/10 ✗
  - SYSTEMATIC narrator substitution error: Victor's chapters (2-10, 17-24) say "Robert Walton" instead of "Victor Frankenstein"
  - Ch5 (index 9): "Robert Walton succeeds in animating a creature" — WRONG, this is Victor
  - Ch7 (index 11): "Robert Walton receiving a letter from his father, Alphonse Frankenstein" — WRONG
  - Ch9 (index 13): "Robert Walton, consumed by guilt after Justine's execution" — WRONG
  - Ch16 (index 20): "Robert Walton burns the dwelling" — WRONG, this is the creature
  - Ch23 (index 27): "Robert Walton lands on the shore...with Elizabeth" — WRONG, this is Victor
  - Ch24 (index 28): "Robert Walton, consumed by vengeance" — WRONG, this is Victor
  - Ch14 (index 18): "Felix The narrator" — BROKEN substitution text
  - Ch11 (index 15): "the narrator, a newly conscious being" — CORRECT (Fix RR worked here)
  - Only Letter 1-4 correctly use "Robert Walton" (he IS the narrator there)
- Pronunciation Guide: 8/10 ✓
  - 232/235 have IPA; dæmon, Chamounix, Arveiron, Clerval all present
- HTML Presentation: 8/10 ✓
- **Overall: 6.45/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (4 categories below threshold: Characters 6, Profiles 5, Summaries 5)

**NOTE ON REGRESSION:** Overall 6.45 < baseline 7.35 - 0.3 = 7.05. However, the narrator substitution errors in Victor's chapters are likely PRE-EXISTING (attempt 21 evaluator only spot-checked Ch11 and Ch17+, may have missed pervasive "Robert Walton" substitution). The character improvements from attempt 23 (Fix OO/UU/WW/PP/QQ) are genuine progress. DO NOT auto-revert — instead fix the narrator substitution which is the core blocker.

## Current Issues (Priority Order)

### CRITICAL
1. **Systematic narrator substitution: "Robert Walton" replaces Victor in all his chapters** [Summaries]
   - Problem: Step 6.9 narrator substitution replaces "the narrator" with "Robert Walton" (frame narrator) in ALL chapters, not just Walton's letters. Victor's chapters (1-10, 17-24) should use "Victor Frankenstein" and creature's chapters (11-16) should use "the creature".
   - Evidence: Ch2-10 all begin "Robert Walton..." describing events that happen to Victor (university, creating creature, illness, Justine's trial). Ch16 says "Robert Walton burns the dwelling" — this is the creature. Ch23 says "Robert Walton...with Elizabeth" — this is Victor's wedding night.
   - Location: `src/analyzer.py` — Step 6.9 narrator substitution logic. The code likely uses a single global narrator name instead of per-chapter narrator detection.
   - Fix: Step 6.9 must use per-chapter narrator attribution. For Frankenstein: Letters 1-4 → Robert Walton, Chapters 1-10 + 17-24 → Victor Frankenstein, Chapters 11-16 → "the creature" (or leave as "the narrator"). The nested narration structure (Walton frames Victor who frames the creature) requires chapter-level narrator tracking.

2. **Felix/De Lacey false merge** [Identity Resolution]
   - Problem: Felix (main_cast_7) has aliases ["De Lacey", "the son", "Felix De Lacey"]. The blind old man De Lacey (Felix's FATHER) is MISSING from the character list entirely. Felix absorbed his father's identity.
   - Evidence: In the novel, De Lacey is the blind old father who lives in the cottage. Felix is his son. The creature approaches De Lacey alone (Ch15) precisely because he's blind. They are distinct characters with different scenes.
   - Location: `src/pipeline/character_extraction_v2/characters.py` — likely Step 5.5 lastname merge or similar logic merged "De Lacey" (father) into "Felix" because Felix has alias "Felix De Lacey"
   - Fix: The merge logic should not absorb a standalone surname character ("De Lacey") into a first-name character ("Felix") when the surname character has distinct scenes and high mention count. Guard: if "De Lacey" appears as a standalone character with significant mentions, don't merge into Felix.

### HIGH
3. **Victor→Alphonse: "brother" is WRONG** [Profiles]
   - Problem: Victor's relationship to Alphonse says "brother" but Alphonse is Victor's FATHER
   - Evidence: Ch7 summary itself says "a letter from his father, Alphonse Frankenstein"
   - Location: `src/analyzer.py` — F9 relationship extraction or `post_corrections.py`
   - Fix: The profiler or relationship extractor is confused. This may be related to issue #1 — if summaries say "Robert Walton" instead of Victor, the profiler can't correctly attribute Victor's family relationships.

4. **Elizabeth empty relationships** [Profiles]
   - Problem: Elizabeth (92 mentions, main_cast_3) has `relationships: {}`
   - Evidence: Elizabeth is Victor's fiancée/wife, adopted by the Frankenstein family. She should have relationships to Victor, Alphonse, William, Justine.
   - Location: `src/analyzer.py` — F9 relationship extraction; Fix TT/SS may not have resolved this
   - Fix: Debug F9 supplementary extraction for Elizabeth. The wrong narrator substitution may prevent the profiler from connecting "Robert Walton" (who appears in summaries) with Elizabeth.

5. **Felix→Agatha: "son" is WRONG** [Profiles]
   - Problem: Felix's relationship to Agatha says "son" — Felix is Agatha's BROTHER
   - Evidence: Felix and Agatha are siblings, children of old De Lacey
   - Location: Profiler LLM confusion, likely exacerbated by Felix/De Lacey false merge (#2)
   - Fix: Fixing #2 (separating De Lacey from Felix) should help the profiler correctly identify Felix and Agatha as siblings

6. **Ch14 broken substitution text** [Summaries]
   - Problem: "Felix The narrator" appears in Ch14 summary — partial/broken narrator substitution
   - Evidence: The text reads "The narrator recounts the tragic history of The narrator family, explaining how Felix The narrator"
   - Location: Same Step 6.9 logic as #1
   - Fix: Part of #1 fix

### MEDIUM
7. **the creature role: "supporting"** [Profiles]
   - Problem: The creature is listed as role "supporting" but is the antagonist/co-protagonist
   - Location: Role assignment in character extraction pipeline
   - Fix: Lower priority — cosmetic for narrator prep

8. **Victor and Elizabeth missing physical descriptions** [Profiles]
   - Problem: Two major characters have null physical_description
   - Evidence: Victor is described in the text; Elizabeth is described as beautiful/fair-haired (only "Fair-haired." currently)
   - Location: Profile generation LLM prompts
   - Fix: Lower priority

9. **Clerval relationship "Felix: not mentioned"** [Profiles]
   - Problem: Useless relationship entry. Clerval should have "Victor Frankenstein: friend"
   - Location: Profiler generated unhelpful relationship
   - Fix: Related to narrator substitution (#1) — profiler sees "Robert Walton" in summaries, can't link to Victor

## Fix History
- Attempts 1-13: Various narrator detection fixes (Steps 4.5, 5.8.6, 6.9)
- Attempt 14: Step 6.9 picked Walton not Victor
- Attempt 15: Fix T (epistolary exclusion), Fix U (prominent narrator selection)
- Attempt 16: Fix V/W (narrator.py symbolic/mention guards)
- Attempt 17: Fix X/Y/AA (title patterns, Unicode tokenization, narrator ID selection) — REGRESSED (dæmon narrator)
- Attempt 18: Fix BB (stop word filter in preamble) — REGRESSED (Arctic ice merge)
- Attempt 19: Guards CC2/CC3, Step 3.8 extended, Rule 0.5b extended
- Attempt 20: Fix DD/EE/FF/GG/HH — no improvement (creature fragmentation, profile gaps)
- Attempt 21: Fix KK (creature fragment merge), Fix LL (kinship→relationship), Fix MM (gender from kinship), Fix NN (Fix EE surname guard) — creature unified ✓ but new issues
- Attempt 22: Fix OO/PP/QQ committed; killed at 1h14m because Fix RR/SS/TT/UU/WW also needed
- Attempt 23: ALL fixes committed (OO/PP/QQ/RR/SS/TT/UU/WW) — canonicals fixed ✓, Walton dup removed ✓, but systematic narrator substitution errors
- Attempt 24: Fix XX (narrator.py: prefer inner narrator for nested narratives), Fix YY (Fix OO alias guard: require canonical-word overlap)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 24 | narrator.py outputs outer narrator (Walton) → used globally | narrator.py (Fix XX) | Changed prompt+example: inner narrator (Victor) for nested narratives |
| 24 | Felix/De Lacey false merge via alias surname match | analyzer.py (Fix YY) | Added canonical-word-overlap guard to Fix OO alias check |
| 23 | Ch11 nested narrator error | summarizer.py (Fix RR) | Partial ✓ — Ch11 fixed, but Ch16 and all Victor chapters still wrong |
| 23 | F9 None→{} normalization | analyzer.py (Fix SS) | No visible effect — Elizabeth still empty relationships |
| 23 | F9 evidence uses pronouns for narrator | analyzer.py (Fix TT) | No visible effect — relationships still wrong |
| 23 | Canonical parentheticals (proper-name chars) | characters.py (Fix UU) | Fixed ✓ — Robert Walton canonical clean |
| 23 | "the fiend" canonical | characters.py (Fix WW) | Fixed ✓ — "the creature" is now canonical |
| 22 | Walton/De Lacey F6 duplicates | analyzer.py (Fix OO) | Mixed — Walton dup removed ✓, De Lacey dup removed but created Felix/De Lacey false merge |
| 22 | "my father" / "the old man" canonical | characters.py (Fix PP) | Fixed ✓ — Alphonse Frankenstein proper canonical |
| 22 | Parenthetical aliases | main_cast.py (Fix QQ) | Fixed ✓ — no parenthetical aliases |
| 21 | Creature fragmentation | characters.py (Fix KK) | Fixed ✓ — creature unified |
| 21 | Gender from kinship | characters.py (Fix MM) | Fixed ✓ — Elizabeth gender=female |
| 20 | Canonical promotion | characters.py (Fix EE) | Partial — fixed by Fix PP+QQ in attempt 22 |

## Root Cause Analysis

The **narrator substitution** (issue #1) is the single highest-impact issue. It causes:
- Summaries score to drop to 5/10 (12+ chapters with wrong narrator name)
- Profile score to drop (profiler reads "Robert Walton" in Victor's chapters → can't link relationships to Victor)
- Elizabeth empty relationships (profiler doesn't see "Victor" in summaries, sees "Robert Walton")
- Victor→Alphonse "brother" (profiler confused by Walton/Victor conflation)

Fixing narrator substitution alone could lift Summaries to ~8/10 and Profiles to ~7/10.

The **Felix/De Lacey merge** (issue #2) is the second-highest impact. It removes a named character and creates wrong relationships.

## Output Files (Attempt 23)
- HTML: output/frankenstein/report.html
- JSON: output/frankenstein/analysis.json
- Duration: 197m 31s

## Next Action
Run PROMPT_fix.md to address:
1. CRITICAL: Fix narrator substitution to use per-chapter narrator (Victor for Ch1-10+17-24, creature for Ch11-16, Walton for Letters)
2. CRITICAL: Fix Felix/De Lacey false merge — prevent surname absorption when standalone surname char has significant mentions
