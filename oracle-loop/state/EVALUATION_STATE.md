# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 51
- **Phase:** awaiting_fix
- **baseline_score:** 6.60
- **Competitive Mode:** single (all stages: characters, structure, summaries)

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Pipeline Notes (Attempt 51)
- Analysis completed in 40m 53s
- 9 characters extracted
- Narrator detected: Uncle Bill (first-person) ✓ (FIXED from attempt 50)
- Uncle Bill is now a SINGLE entity ✓ (FIXED from attempt 50)
- NEW ISSUE: Father fragmented into 3 entries (main_cast_2, main_cast_3, main_cast_4)

## Latest Scores
- Structure Detection: 7/10 ✗
- Character Extraction: 4.5/10 ✗
  - Completeness: 6/10
  - Identity Resolution: 3/10
  - Alias Grouping: 5/10
- Character Profiles: 4/10 ✗
- Chapter Summaries: 7.5/10 ✗
- Pronunciation Guide: 7/10 ✗
- HTML Presentation: 8/10 ✓
- **Overall: 5.93/10** (reference only)

## Overall Score Calculation

```
Overall = (7 × 0.20) + (4.5 × 0.25) + (4 × 0.15) + (7.5 × 0.20) + (7 × 0.10) + (8 × 0.10)
        = 1.40 + 1.125 + 0.60 + 1.50 + 0.70 + 0.80
        = 6.125
```

**Overall: 5.93/10** (reference only — character fragmentation dominates)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (5 categories below threshold)

## Detailed Evaluation

### 2.1 Structure Detection: 7/10 ✗ (unchanged)

"American, Sir" is a continuous short story with no chapter markers. The tool produces 2 sections, both with null titles. Per rubric, continuous text should be 1 section (9-10); splitting into 2 is a structural error. Score 7 because summaries are coherent and the split is not destructive.

### 2.2 Character Extraction: 4.5/10 ✗ (DOWN from 5 — new fragmentation)

**Sub-Dimension A: Completeness: 6/10** (unchanged)

9 characters extracted, but only 5 represent unique real characters due to fragmentation:

- ✓ Uncle Bill — main_cast_1, 18 mentions, narrator=True — CORRECTLY SINGLE NOW ✓✓
- ✗ John (the cousin) — main_cast_2, 28 mentions — this IS the father (Uncle Bill's cousin). DUPLICATE of main_cast_3/4
- ✗ John Donaldson (the father) — main_cast_3, 10 mentions — one of TWO entries for the father with this exact name
- ✗ John Donaldson (the father) — main_cast_4, 28 mentions — DUPLICATE of main_cast_3
- ✓ John Donaldson (the son) — main_cast_5, 28 mentions
- ✓ Joe Barron — supporting_2, 3 mentions
- ✗ Red Cross — supporting_3, 4 mentions — organization, not character
- ✓ Ted Frith — supporting_4, 5 mentions
- ✗ Johnny — supporting_6, 2 mentions — should be alias of the son

**Real characters in the story:** Uncle Bill, John Donaldson (father), John Donaldson (son), Margaret Donaldson, Joe Barron, Ted Frith. That's 6 characters. The tool has 5 unique characters but TRIPLED the father and lost Margaret.

**CRITICAL NEW ISSUE:** The father is now split into THREE entries:
1. main_cast_2 "John (the cousin)" — the father, referred to from Uncle Bill's perspective as his cousin
2. main_cast_3 "John Donaldson (the father)" — another father entry
3. main_cast_4 "John Donaldson (the father)" — IDENTICAL canonical name to main_cast_3

The Uncle Bill fix prevented Uncle Bill from being falsely split, BUT it appears the LLM's same-name resolution now creates more fragmentation for "John" variants. Previously there were 2 Johns (father + son, correctly split). Now there are 4 John entries (3 father fragments + 1 son).

**MISSING:** Margaret Donaldson was present in attempt 50 but is now GONE.

**Sub-Dimension B: Identity Resolution: 3/10** (DOWN from 4 — worse fragmentation)

- ✓ Uncle Bill is now a single entity (FIXED!)
- ✓ Narrator correctly identified as Uncle Bill (FIXED!)
- ✗ Father is TRIPLED: "John (the cousin)" + two "John Donaldson (the father)" entries — should be ONE entry
- ✗ Two entries have IDENTICAL canonical names "John Donaldson (the father)" — main_cast_3 and main_cast_4
- ✗ "Johnny" (supporting_6) should be alias of son, not separate character
- ✗ Margaret Donaldson MISSING entirely

The Uncle Bill fix is a genuine improvement, but the father fragmentation is WORSE than before (was 1 entry, now 3).

**Sub-Dimension C: Alias Grouping: 5/10** (unchanged)

- Uncle Bill aliases: ["Bill"] — minimal but acceptable ✓
- John (the cousin) aliases: ["John"] — correct for this fragment ✓
- John Donaldson (the father) #3 aliases: ["the father"] — reasonable ✓
- John Donaldson (the father) #4 aliases: ["John", "John Donaldson"] — reasonable ✓
- John Donaldson (the son) aliases: ["John"] — missing "Johnny" ✗
- "Johnny" is separate instead of being son's alias ✗

### 2.3 Character Profiles: 4/10 ✗ (DOWN from 4.5)

**ALL physical_description fields are null** (0/9 characters).
**ALL speech_patterns fields are null** (0/9 characters).
**ALL evidence_quotes are null** (0/9 characters).

**Relationships** (6/9 have them):
- Uncle Bill: `{"John Donaldson (son)": "guardian", "John Donaldson (father)": "ally", "Margaret Donaldson": "acquaintance"}` — "guardian" is good ✓, "ally" for the father is wrong (should be "cousin") ✗, references Margaret even though she's not a character entry ✗
- John (the cousin): `{"Narrator (Uncle Bill)": "family", "Margaret Donaldson": "family (spouse)", "Young John (his son)": "family (parent)"}` — relationships are correct in substance ✓, but reference names that don't match character entries ✗
- John Donaldson (the father) #3: `{"John Donaldson (the son)": "parent"}` — minimal ✗
- John Donaldson (the father) #4: `{"John Donaldson (the son)": "parent"}` — duplicate of #3 ✗
- John Donaldson (the son): `{"John Donaldson (the son)": "parent", "Uncle Bill": "acquaintance"}` — self-referential ("son" has relationship to "son" as parent?) ✗, Uncle Bill should be "guardian" not "acquaintance" ✗

**KEY PROBLEM:** The 3-way father fragmentation creates confused, duplicated, and self-referential relationships. Profile quality score drops because fragmentation poisons the data.

### 2.4 Chapter Summaries: 7.5/10 ✗ (unchanged)

**Section 1:** Good quality. Captures Uncle Bill receiving the letter, backstory about the father at Yale, the scandal, and the death. Characters_present only lists ["Narrator"] instead of naming Uncle Bill. ✓/minor ✗

**Section 2:** Comprehensive narrative arc. Characters_present correctly lists Uncle Bill and John Donaldson. ✓
- **Error:** Still says "his deceased sister's twelve-year-old son" — should be "his deceased cousin's son." The text explicitly states the father was Uncle Bill's cousin. ✗
- Otherwise captures the fishing trip, WWI, Italy, the father's reveal, and the deathbed scene well.

Both summaries are appropriate length and capture tone well.

### 2.5 Pronunciation Guide: 7/10 ✗ (unchanged)

20 entries, 15 with IPA.

**Genuinely useful (13):**
- Italian/foreign terms: Caporetto, Piave, Solferino, Guerre, Venetia, Tagliamento, Bersagliari, Bordeaux — all correctly flagged ✓
- Homographs: live, minute, read, close, moderate — useful for narrator ✓

**False positives (7):** whippersnapper, thriftless, thickset, manliness, dum-dums, orderlies, mayn't — all standard English words that a narrator would know. 35% false positive rate brings the score down.

### 2.6 HTML Presentation: 8/10 ✓ (unchanged)

Navigation works, tabs functional, layout clean. Content quality issues are scored in their respective categories.

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (user-configured, appropriate)
- Pipeline: V2 with Phase 2 graph-based identity resolution
- No configuration issues — the core problem is character fragmentation in extraction

## Current Issues (Priority Order)

### CRITICAL

1. **Father character tripled into 3 entries** [Identity Resolution, score impact ~2.5 points across Characters + Profiles]
   - Problem: The father John Donaldson appears as THREE separate entries:
     - main_cast_2 "John (the cousin)" (28 mentions)
     - main_cast_3 "John Donaldson (the father)" (10 mentions)
     - main_cast_4 "John Donaldson (the father)" (28 mentions)
   - Evidence: There is only ONE father character. He is: Uncle Bill's cousin from Yale, John Donaldson, who later dies in Italy. The text refers to him as "John", "John Donaldson", "the father", and "my cousin" — all the same person.
   - Root cause: The same-name split fix in attempt 51 changed how father/son markers are matched. The stricter matching may have caused the LLM to produce fragmented results, OR the post-processing failed to merge these obvious duplicates.
   - Key observation: main_cast_3 and main_cast_4 have IDENTICAL canonical names "John Donaldson (the father)" — this should NEVER happen. The pipeline should have a dedup step for identical canonical names.
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` — same-name split logic, or missing dedup for identical canonical names
   - Fix approach: Add a simple post-processing step that merges characters with IDENTICAL canonical names (exact string match). This is safe — if two entries have the exact same name, they're the same character by definition. Then ensure "John (the cousin)" is recognized as an alias of "John Donaldson (the father)" since "the cousin" is a descriptor for the same person.
   - **IMPACT:** Fixing this cascades into profiles (no more duplicated/confused relationships), completeness (fewer ghost entries), and alias grouping.

### HIGH

2. **Margaret Donaldson missing** [Completeness, score impact ~0.3]
   - Problem: Margaret was present in attempt 50 (main_cast_2, 2 mentions) but is now completely absent from character list
   - Evidence: Margaret is the father's wife who writes Uncle Bill a letter. She's a minor but named character.
   - Location: May have been displaced by the "John (the cousin)" entry taking main_cast_2 slot
   - Fix: Should resolve naturally if fragmentation is fixed and character slots open up

3. **"Johnny" is a separate character instead of son's alias** [Alias Grouping, score impact ~0.3]
   - Problem: supporting_6 "Johnny" (2 mentions) should be alias of John Donaldson (the son)
   - Evidence: "Johnny" is a diminutive of "John" referring to the boy in the story
   - Location: Supporting cast extraction or alias resolution
   - Fix: May need diminutive name matching (Johnny → John)

4. **Summary says "sister" instead of "cousin"** [Summaries, score impact ~0.3]
   - Problem: Section 2 says "his deceased sister's twelve-year-old son" — should be "his deceased cousin's son"
   - Evidence: Text says "a cousin, who had come to be this lad's father"
   - Location: Summary LLM hallucination — has persisted across multiple attempts

5. **All evidence_quotes are null** [Profiles, score impact ~0.5]
   - Problem: Every character has `evidence_quotes: null` — no supporting quotes from the text
   - Location: `src/pipeline/character_profiling/` — profile generation or grounding gate (F19 warnings noted in pipeline)

### MEDIUM

6. **"Red Cross" extracted as character** [Completeness, score impact ~0.2]
   - Problem: supporting_3 "Red Cross" (4 mentions) is an organization, not a character
   - Location: Supporting cast extraction prompt

7. **Pronunciation: 35% false positive rate** [Pronunciation, score impact ~0.5]
   - Problem: 7 of 20 entries are standard English words (whippersnapper, thriftless, thickset, manliness, dum-dums, orderlies, mayn't)
   - Location: `src/pipeline/pronunciation/` — filtering logic

8. **Structure: 2 sections for continuous text** [Structure, score impact ~0.5]
   - Problem: Continuous short story split into 2 sections, both with null titles
   - Location: `src/pipeline/chapter_detection/`

9. **`narrator_name` field is null** [Identity Resolution, score impact ~0.2]
   - Problem: Top-level `overview.narrator_name` is null even though Uncle Bill is tagged `is_narrator: true`
   - Location: `src/analyzer.py` — narrator_name population logic

10. **All physical_description and speech_patterns are null** [Profiles, score impact ~0.3]
    - Problem: No character has physical descriptions or speech pattern notes
    - Location: `src/pipeline/character_profiling/`

11. **Uncle Bill-father relationship listed as "ally"** [Profiles, score impact ~0.1]
    - Should be "cousin" — the text explicitly says they were cousins at Yale

### LOW

12. **Section 1 characters_present only lists "Narrator"** [Summaries]
    - Should name Uncle Bill specifically

13. **Son's self-referential relationship** [Profiles]
    - John Donaldson (the son) has `"John Donaldson (the son)": "parent"` — self-referencing instead of referencing the father

## Fix Priority Recommendation

**CRITICAL #1 (Father tripled) is THE blocker.** The attempt 51 fix successfully resolved the Uncle Bill split, but introduced (or failed to prevent) a new 3-way fragmentation of the father character.

**TWO-PART FIX NEEDED:**

1. **Dedup identical canonical names:** main_cast_3 and main_cast_4 both have the exact same canonical name "John Donaldson (the father)". A simple exact-match dedup after Pass 2 would merge these. This is safe — identical names = same character by definition.

2. **Merge "John (the cousin)" into "John Donaldson (the father)":** The LLM produced "John (the cousin)" as a separate entry, but this is the same person as the father. The alias resolution should recognize that "John" with a family-descriptor disambiguator "(the cousin)" maps to "John Donaldson" who IS the cousin.

**CAUTION:** Attempt 47 tried a dedup approach and caused a MAJOR REGRESSION (7.08→5.95). That dedup was over-aggressive — it merged characters that happened to share first names. The new dedup MUST be limited to EXACT canonical name matches only, not fuzzy matching. `"John Donaldson (the father)" == "John Donaldson (the father)"` is safe; `"John" ≈ "John Donaldson"` is NOT.

**DO NOT:**
- Modify the same-name split pattern matching (just fixed in attempt 51, working correctly for Uncle Bill)
- Revert the attempt 51 fix (Uncle Bill single entity is correct)
- Change model configuration (user-set)
- Attempt fuzzy name merging (regression risk)

## Fix History

### Attempt 51 — Fix same-name split false positives — **PARTIAL SUCCESS**
- **Issue targeted:** CRITICAL #1 from attempt 50 — Uncle Bill falsely split
- **Fix:** Modified `_enforce_same_name_splits()` pattern matching to verify father/son markers modify the character's name directly
- **Uncle Bill result:** ✓ FIXED — now a single entity, correctly identified as narrator
- **New regression:** Father character tripled (was 1 entry in attempt 50, now 3 entries)
- **Root cause:** The same-name split fix changed contextual matching, and the LLM now produces more John variants that don't get merged
- **Files modified:** `src/pipeline/character_extraction_v2/main_cast.py`

### Attempt 50 — Re-run to test LLM non-determinism — **PARTIAL RECOVERY**
- Score: 6.08. Father/son fixed, Uncle Bill still split.

### Attempt 49 — Strip parenthetical disambiguators in passage gatherer — **MIXED**
- Score: 6.15. Profiles improved but upstream character extraction regressed.

### Attempt 48 — REVERT attempt 47 deduplication + re-analyze — **BASELINE RECOVERY**
- Score: 6.88.

### Attempt 47 — Deduplicate identical canonical names after Pass 2 — **REGRESSION (REVERTED)**
- Score: 5.95. Over-aggressive dedup caused false merges.

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 51 | Fix same-name split false positives | `main_cast.py` (lines 910-972) | **PARTIAL** — Uncle Bill fixed ✓, Father tripled ✗. Score: ~5.93 |
| 50 | Re-run for LLM non-determinism | None | **PARTIAL** — Father/son fixed, Uncle Bill still split. Score: 6.08 |
| 49 | Strip parenthetical disambiguators | `passage_gatherer.py` | **MIXED** — Score: 6.15 |
| 48 | REVERT attempt 47 dedup | `main_cast.py` | **BASELINE RECOVERY** — Score: 6.88 |
| 47 | Dedup identical canonical names | `main_cast.py` (+75 lines) | **REGRESSION (REVERTED)** — Score: 5.95 |
| 46 | Extend grounding gate | `mention_search.py`, tests | **PARTIAL SUCCESS** — Score: 7.08 |
| 45 | REVERT attempt 44 alias filter | `main_cast.py`, tests | **PARTIAL RECOVERY** — Score: 6.88 |
| 44 | Filter shared base name aliases | `main_cast.py`, tests | **REGRESSION** — Score: 6.45 |
| 43 | Disambiguator ROLE_CONFLICT | `evidence_collectors.py` | **SUCCESS** — Score: 6.98 |

**PATTERN ALERT:** `main_cast.py` has been modified 9 times (attempts 39-51). Over half were regressions. A NARROW, SAFE dedup (exact canonical name match only) is needed — NOT another broad merge attempt.

**KEY INSIGHT:** The attempt 47 dedup that regressed was doing FUZZY matching. A dedup that ONLY merges characters with IDENTICAL canonical names (exact string `==`) is fundamentally different and safe. Two entries both named "John Donaldson (the father)" must be the same character.

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.60 | — | Original baseline |
| 22 | 7.55 | +0.95 | Best score (all fixes active) |
| 23 | 6.30 | -0.30 | Clean baseline + Phase 2 pipeline |
| 31 | 7.33 | +0.73 | Deterministic same-name fix SUCCESS |
| 34 | 6.80 | +0.20 | Uncle Bill restored |
| 35 | 7.05 | +0.45 | HARD constraint works |
| 36 | 7.15 | +0.55 | Father grounded ✓ |
| 37 | 6.90 | +0.30 | REGRESSION |
| 38 | 6.80 | +0.20 | REGRESSION |
| 39 | 7.10 | +0.50 | Father/son SPLIT ✓ |
| 40 | 6.45 | -0.15 | REGRESSION |
| 41 | 6.80 | +0.20 | PARTIAL RECOVERY |
| 42 | 6.48 | -0.12 | REGRESSION |
| 43 | 6.98 | +0.38 | SUCCESS |
| 44 | 6.45 | -0.15 | **REGRESSION** |
| 45 | 6.88 | +0.28 | PARTIAL RECOVERY |
| 46 | 7.08 | +0.48 | PARTIAL SUCCESS — best recent score |
| 47 | 5.95 | -0.65 | **MAJOR REGRESSION** — dedup caused false merges |
| 48 | 6.88 | +0.28 | BASELINE RECOVERY — revert confirmed |
| 49 | 6.15 | -0.45 | **REGRESSION** — LLM non-determinism |
| 50 | 6.08 | -0.52 | Father/son fixed, Uncle Bill still split |
| 51 | 5.93 | -0.67 | Uncle Bill fixed ✓, Father TRIPLED ✗ |

## Next Action
Run PROMPT_fix.md to address father character triplication (CRITICAL #1). The fix must be NARROW: exact canonical name dedup only, plus recognition that "John (the cousin)" = "John Donaldson (the father)".
