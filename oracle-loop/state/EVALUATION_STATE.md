# Current Evaluation State

## Active Text
- **Name:** frankenstein
- **Attempt:** 21
- **Phase:** awaiting_analysis
- **baseline_score:** 7.35

## Score History
| Attempt | Score | Notes |
|---------|-------|-------|
| 1 | 7.35 | Baseline |
| 20 | ~7.35 | No improvement: creature fragmentation, Elizabeth gender/rels, wrong Alphonse rel |
| 21 | 7.15 | Creature unified ✓, but duplicates (Walton, De Lacey), poor canonicals, empty profiles |

## Latest Scores
- Structure Detection: 8/10 ✓
  - 28 chapters correct (4 letters + 24 chapters)
  - Letter 1 title=null (minor)
- Character Extraction: 6.5/10 ✗
  - Completeness: 8/10 — all expected characters present, two duplicates inflate list
  - Identity Resolution: 6/10 — two false splits (Walton duplicate, De Lacey duplicate)
  - Alias Grouping: 6/10 — poor canonicals ("my father", "the fiend", "the old man"), parenthetical aliases
- Character Profiles: 5.5/10 ✗
  - Elizabeth (92 mentions): EMPTY relationships — should have Victor as fiancé/wife
  - Victor: missing Elizabeth, father, William relationships; no physical description
  - De Lacey self-referential relationships (De Lacey→the old man: "son" — same person)
  - Safie→De Lacey: "lover" WRONG (should be Safie→Felix)
- Chapter Summaries: 7.5/10 ✗
  - Ch11 summary says "Victor Frankenstein's journey of discovery" — this is the CREATURE's chapter (11-16 are creature narration)
  - Other creature chapters (12-16) use "The narrator" correctly
  - Ch17+ correctly attribute to Victor
- Pronunciation Guide: 8/10 ✓
  - 232/235 have IPA; dæmon, Chamounix, Arveiron, Clerval all present
  - 3 missing IPA are homographs with notes (acceptable)
- HTML Presentation: 8/10 ✓
- **Overall: 7.15/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (4 categories below threshold: Characters 6.5, Profiles 5.5, Summaries 7.5)

## Current Issues (Priority Order)

### CRITICAL

1. **False split: Robert Walton duplicate** [Identity Resolution]
   - Problem: main_cast_0 "R. Walton (Robert Walton)" AND cc30daa57250 "Robert Walton" (F6 reconciliation) exist as separate entries
   - Evidence: F6 added "Robert Walton" because "R. Walton (Robert Walton)" didn't match in `_is_likely_alias_of_existing`
   - Location: `src/analyzer.py` — F6 reconciliation; `_is_likely_alias_of_existing` fails to match "Robert Walton" against "R. Walton (Robert Walton)" canonical or aliases ["Walton", "R. Walton"]
   - Fix: In `_is_likely_alias_of_existing`, expand matching to handle abbreviated first names — "R. Walton" should match "Robert Walton" (initial matches first letter of full name + same last name)

2. **False split: De Lacey duplicate** [Identity Resolution]
   - Problem: main_cast_11 "the old man" (aliases: ["De Lacey (Old man)"]) AND fe2e94dd87de "De Lacey" exist separately
   - Evidence: F6 added "De Lacey" because alias "De Lacey (Old man)" has parenthetical — string matching fails
   - Location: `src/analyzer.py` — F6 `_is_likely_alias_of_existing` doesn't strip parentheticals when comparing
   - Fix: Strip parenthetical suffixes from aliases before comparison in `_is_likely_alias_of_existing`

3. **Elizabeth empty relationships** [Profiles]
   - Problem: Elizabeth (92 mentions) has `relationships: {}` — should have Victor as fiancé/wife, William as adoptive brother, Alphonse as adoptive father
   - Evidence: Elizabeth is Victor's love interest and eventual wife; central to the plot
   - Location: `src/analyzer.py` — `_generate_character_profile()` and/or Fix HH (supplementary F9) not producing results for Elizabeth
   - Fix: Debug why F9 supplementary relationship extraction fails for Elizabeth; check if "my father" canonical prevents relationship matching

### HIGH

4. **Poor canonical: "my father" instead of "Alphonse Frankenstein"** [Alias Grouping]
   - Problem: Canonical is "my father" with alias "Alphonse Frankenstein (Father)". Fix EE was supposed to promote proper-name aliases to canonical.
   - Evidence: "Alphonse Frankenstein" is the correct canonical name. The parenthetical "(Father)" may prevent Fix EE from selecting this alias.
   - Location: `src/pipeline/character_extraction_v2/characters.py` — Fix EE canonical promotion
   - Fix: Fix EE should strip parentheticals when evaluating alias quality, or prefer aliases containing proper names even if parenthetical

5. **Poor canonical: "the fiend" for the creature** [Alias Grouping]
   - Problem: Canonical is "the fiend" (89 mentions). Standard reference is "the creature" which is more recognizable for narrator prep.
   - Evidence: "the creature" is in aliases; while "the fiend" may be more frequent in text, "the creature" is the standard literary reference
   - Location: `src/pipeline/character_extraction_v2/characters.py` or `main_cast.py` — canonical selection
   - Fix: Consider preferring "the creature" over other creature_terms when multiple exist; or treat this as acceptable since aliases cover all variants. (MEDIUM priority if aliases are complete)

6. **Poor canonical: "the old man" for De Lacey** [Alias Grouping]
   - Problem: Canonical is "the old man" with alias "De Lacey (Old man)". Should be "De Lacey".
   - Location: Same Fix EE issue as #4 — parenthetical blocks proper-name promotion
   - Fix: Same as #4

7. **Ch11 narrator substitution error** [Summaries]
   - Problem: Ch11 summary says "Victor Frankenstein's journey" but Ch11 is narrated by the creature (chapters 11-16 are the creature's story)
   - Evidence: Ch11 describes the creature's first experiences after creation — discovering fire, shelter, the De Lacey cottage
   - Location: `src/analyzer.py` — Step 6.9 narrator substitution; may have incorrectly substituted "Victor Frankenstein" for "the narrator" in Ch11
   - Fix: Check if Ch11 narrator attribution is correct; the creature chapters should use "The narrator" or "the creature"

8. **Safie→De Lacey: "lover" is WRONG** [Profiles]
   - Problem: Safie's relationship to De Lacey (fe2e94dd87de) says "lover" — Safie is Felix's lover, not De Lacey's
   - Evidence: Safie is the Turkish woman who comes to the De Lacey cottage to be with Felix
   - Location: Profiler LLM hallucination; the duplicate De Lacey entry confuses the profiler
   - Fix: Fixing the De Lacey duplicate (#2) should resolve this — profiler won't have two De Lacey targets

9. **Victor missing key relationships** [Profiles]
   - Problem: Victor has no relationship to Elizabeth (fiancée/wife), "my father" (father), or William (brother)
   - Evidence: These are Victor's most important relationships in the novel
   - Location: `src/analyzer.py` — profile generation or F9 relationship extraction
   - Fix: Related to #3; the "my father" canonical may confuse relationship extraction. Check if profiler uses canonical names that don't match typical relationship phrasing.

10. **De Lacey self-referential relationships** [Profiles]
    - Problem: "the old man" has relationship "De Lacey: son" and "De Lacey" (duplicate) has "the old man: son" — both say "son" which is nonsensical (they're the same person)
    - Fix: Resolving duplicate #2 eliminates this

### MEDIUM

11. **"R. Walton (Robert Walton)" canonical format** [Alias Grouping]
    - Problem: Canonical includes initial abbreviation. Should be "Robert Walton" with "R. Walton" as alias
    - Location: Canonical name selection in main_cast pipeline
    - Fix: Prefer full proper names over abbreviated forms for canonical

12. **Victor and Elizabeth missing physical descriptions** [Profiles]
    - Problem: Two major characters have no physical_description
    - Evidence: Victor is described in the text; Elizabeth is described as beautiful with fair features
    - Location: Profile generation LLM not extracting descriptions
    - Fix: Lower priority — may improve with better relationship extraction

13. **Parenthetical aliases throughout** [Alias Grouping]
    - Problem: Aliases like "Alphonse Frankenstein (Father)", "William Frankenstein (Younger brother)", "De Lacey (Old man)" have parenthetical annotations
    - Location: Pass 2 alias extraction in main_cast.py
    - Fix: Strip parenthetical annotations from aliases during alias processing

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
- Attempt 22: Fix OO (canonical/alias parenthetical matching in F6), Fix PP (strip parenthetical from canonical in Fix EE), Fix QQ (strip parenthetical from aliases in Pass 2)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 22 | Walton/De Lacey F6 duplicates | analyzer.py (Fix OO) | Pending — canonical/alias parenthetical matching in _is_likely_alias_of_existing |
| 22 | "my father" / "the old man" canonical | characters.py (Fix PP) | Pending — strip parenthetical from best_alias before setting canonical |
| 22 | Parenthetical aliases | main_cast.py (Fix QQ) | Pending — strip parenthetical from aliases in Pass 2 (also fixes Fix EE by providing clean aliases) |
| 21 | Creature fragmentation | characters.py (Fix KK) | Fixed ✓ — creature unified as "the fiend" |
| 21 | Kinship alias relationships | characters.py (Fix LL) | Partially — Alphonse→Caroline "husband" correct |
| 21 | Gender from kinship | characters.py (Fix MM) | Fixed ✓ — Elizabeth gender=female |
| 21 | Fix EE surname guard | main_cast.py (Fix NN) | Unknown — "my father" still canonical |
| 20 | Elizabeth relationships | analyzer.py (Fix HH) | No change — still empty |
| 20 | Canonical promotion | characters.py (Fix EE) | Partial — "my father" not promoted |

## Next Action

The fix phase should focus on these high-impact issues in order:

1. **Fix `_is_likely_alias_of_existing` to catch Walton and De Lacey duplicates** (CRITICAL #1, #2) — strip parentheticals from aliases, handle initial abbreviations ("R." matching "Robert")
2. **Fix canonical promotion (Fix EE) to strip parentheticals** (HIGH #4, #6) — "Alphonse Frankenstein (Father)" should promote to "Alphonse Frankenstein"
3. **Debug Elizabeth empty relationships** (CRITICAL #3) — trace why F9/profiler produces nothing for 92-mention character
4. **Ch11 narrator attribution** (HIGH #7) — verify creature chapters use correct narrator

Fixing #1+#2 should cascade to fix #8 and #10 (De Lacey relationship confusion). Fixing #4 may cascade to fix #9 (Victor's relationships using "my father" key).
