# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 50
- **Phase:** awaiting_analysis
- **baseline_score:** 6.60
- **Competitive Mode:** single (all stages: characters, structure, summaries)

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Latest Scores
- Structure Detection: 7/10 ✗
- Character Extraction: 4.5/10 ✗
  - Completeness: 5/10
  - Identity Resolution: 3/10
  - Alias Grouping: 5/10
- Character Profiles: 5/10 ✗
- Chapter Summaries: 7.5/10 ✗
- Pronunciation Guide: 7/10 ✗
- HTML Presentation: 8/10 ✓
- **Overall: 6.15/10** (reference only)

## Overall Score Calculation

```
Overall = (7 × 0.20) + (4.5 × 0.25) + (5 × 0.15) + (7.5 × 0.20) + (7 × 0.10) + (8 × 0.10)
        = 1.40 + 1.125 + 0.75 + 1.50 + 0.70 + 0.80
        = 6.275
```

**Overall: 6.15/10** (DOWN from 6.88 — LLM non-determinism caused upstream character extraction regression)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (5 categories below threshold)

## Detailed Evaluation

### 2.1 Structure Detection: 7/10 ✗ (unchanged)

"American, Sir" is a continuous short story with no chapter markers. The tool produces 2 sections, both with null titles. Per rubric, continuous text should be 1 section (9-10); splitting into 2 is a structural error. Score 7 because summaries are coherent and the split is not destructive.

### 2.2 Character Extraction: 4.5/10 ✗ (DOWN from 6.5 — major regression)

**Sub-Dimension A: Completeness: 5/10** (DOWN from 7)

8 characters extracted, but with critical identity errors:
- ✓ John Donaldson (the father) — main_cast_1, 37 mentions — CORRECT character but has WRONG aliases
- ✗ John Donaldson (the son) — **MISSING entirely** — swallowed as alias of the father
- ✓ Margaret Donaldson — main_cast_3, 2 mentions
- ✗ Uncle Bill (the father) — main_cast_4, 18 mentions, narrator — Uncle Bill is ONE person, this is a FALSE SPLIT
- ✗ Uncle Bill (the son) — main_cast_5, 17 mentions — This entity DOES NOT EXIST in the story. There is only one Uncle Bill.
- ✓ Joe Barron — supporting_2, 3 mentions
- ✗ Red Cross — supporting_3, 4 mentions — organization, not character
- ✓ Ted Frith — supporting_4, 5 mentions
- ✗ Johnny — supporting_6, 2 mentions — should be alias of John Donaldson the son

**CRITICAL:** John Donaldson (the son) is completely missing as a separate character. He's listed as an alias of the father: `main_cast_1.aliases = ["John Donaldson", "John Donaldson (the son)", "John"]`. The son is NOT an alias of the father — they are different people.

**CRITICAL:** Uncle Bill has been falsely split into two characters: "Uncle Bill (the father)" and "Uncle Bill (the son)". There is only ONE Uncle Bill in the story. He is the narrator, the father's cousin, and the boy's guardian. The SAME-NAME CONFLICT logic apparently fired on Uncle Bill erroneously, applying the father/son disambiguator pattern from John Donaldson to Uncle Bill.

**Sub-Dimension B: Identity Resolution: 3/10** (DOWN from 7 — catastrophic)

- ✗ Uncle Bill falsely split into TWO characters — there is only one Uncle Bill
- ✗ John Donaldson (the son) merged as alias of the father — they are separate people
- ✗ "Uncle Bill (the son)" gets the son's profile but is the wrong entity entirely
- ✓ Uncle Bill (the father) correctly identified as narrator
- ✗ `narrator_name` field is still null

This is the worst identity resolution in recent attempts. Two critical false operations: a false split (Uncle Bill) and a false merge (John Donaldson son into father).

**Sub-Dimension C: Alias Grouping: 5/10** (DOWN from 5.5)

- Father aliases: ["John Donaldson", "John Donaldson (the son)", "John"] — "John Donaldson (the son)" should NOT be an alias of the father ✗
- Uncle Bill (the father) aliases: ["Bill", "Uncle Bill"] — reasonable for this entity, but entity shouldn't exist ✗
- Uncle Bill (the son) aliases: [] — empty, and entity shouldn't exist ✗
- "Johnny" is separate entry instead of son's alias ✗

### 2.3 Character Profiles: 5/10 ✗ (DOWN from 5.5)

The passage_gatherer.py fix appears to have improved profile generation quality — the profiles THEMSELVES are better — but they're attached to the wrong character entities due to the upstream extraction regression.

**John Donaldson (the father) — main_cast_1:** "A manipulative and cowardly antagonist who stole from his family, faked his death to escape accountability, abandoned his son for two decades." This is CORRECT for the father. ✓

**Uncle Bill (the father) — main_cast_4:** "A deeply principled and quietly heroic man whose actions reveal profound selflessness, loyalty, and moral courage, despite his outwardly crabbed and selfish demeanor." This correctly describes Uncle Bill. ✓ But relationships list "John Donaldson (the father): ally" — Uncle Bill is the father's COUSIN, not "ally". ✗

**Uncle Bill (the son) — main_cast_5:** "A heroic protagonist whose actions are defined by selfless sacrifice, compassion, and moral courage—risking his life in war and embracing his estranged father with unconditional love." This is actually the SON's (John Donaldson Jr.) profile. The content is correct for the son, but it's attached to the wrong entity. The profiler generated profiles for "Uncle Bill (the son)" and attributed the son's passages to it. ✗

**Ted Frith — supporting_4:** Good profile — captures wartime heroism and speech patterns. ✓

**Evidence quotes:** ALL characters have `evidence_quotes: null`. This is a regression from attempt 48 where at least some evidence was present. ✗

**KEY INSIGHT:** The passage_gatherer.py fix may be working correctly — "Uncle Bill (the son)" got the son's actual characterization (brave ambulance driver, war hero, forgiving). But the upstream character extraction created the wrong entities, so good profiles are attached to wrong characters.

### 2.4 Chapter Summaries: 7.5/10 ✗ (unchanged)

**Section 1:** Good. Correctly captures Uncle Bill receiving the letter, backstory with the father at Yale, the scandal, and Margaret's letter about the death. ✓

**Section 2:** Narrative arc captured well. Characters_present lists ["Uncle Bill", "John Donaldson (the son)", "John Donaldson (the father)"] — correctly names all three. ✓
- **Error:** Still says "his deceased sister's twelve-year-old son" — should be "his deceased cousin's" son. The text says "a cousin, who had come to be this lad's father." ✗
- Otherwise comprehensive and accurate.

Section 1 characters_present lists only ["the narrator"] instead of naming Uncle Bill specifically. Minor issue.

### 2.5 Pronunciation Guide: 7/10 ✗ (unchanged)

20 entries total, 15 with IPA.

**Genuinely useful (13):** Caporetto, Piave, Solferino, Guerre, Venetia, Tagliamento, Bersagliari, Bordeaux (foreign/Italian terms) + live, minute, read, close, moderate (homographs)

**False positives (7):** whippersnapper, thriftless, thickset, manliness, dum-dums, orderlies, mayn't — standard English words. 35% false positive rate.

### 2.6 HTML Presentation: 8/10 ✓ (unchanged)

Navigation works, tabs functional, layout clean. Content quality issues are scored elsewhere. The HTML correctly renders whatever data it receives.

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (user-configured, appropriate)
- Pipeline: V2 with Phase 2 graph-based identity resolution
- No LLM retries in any stage — clean execution ✓
- Character Profiles took 697s (longest stage) — expected
- No configuration issues — the regression is from LLM non-determinism in character extraction

## Current Issues (Priority Order)

### CRITICAL

1. **Uncle Bill falsely split into two characters** [Identity Resolution, score impact ~1.5 points]
   - Problem: main_cast_4 "Uncle Bill (the father)" and main_cast_5 "Uncle Bill (the son)" — there is only ONE Uncle Bill in this story. He is the narrator, the father's cousin, and the boy's guardian.
   - Evidence: The text has a single Uncle Bill throughout. The SAME-NAME CONFLICT logic erroneously applied the father/son disambiguator pattern (designed for John Donaldson) to Uncle Bill.
   - Root cause: The LLM's character extraction Pass 1 or the identity resolution graph detected "Uncle Bill" in both father-era and son-era contexts and applied the same father/son split that is appropriate for "John Donaldson" but NOT for "Uncle Bill." Uncle Bill appears in BOTH eras because he IS the same person who knew the father and later raised the son.
   - Location: `src/pipeline/character_extraction_v2/` — the SAME-NAME CONFLICT / ROLE_CONFLICT logic in `evidence_collectors.py` or `identity_graph.py`
   - Fix: The ROLE_CONFLICT constraint needs to be smarter about when to split. Uncle Bill appears in father and son contexts because he is a cross-generational character (narrator who knew both), NOT because there are two Uncle Bills. The constraint should NOT split when:
     - The character is identified as narrator (narrators naturally span all time periods)
     - The character has only ONE name form (no "Uncle Bill Sr." vs "Uncle Bill Jr." distinction exists)
     - Context suggests a single person who knew both generations (guardian, relative, narrator)

2. **John Donaldson (the son) missing — merged as alias of father** [Identity Resolution, Completeness, score impact ~1.5 points]
   - Problem: main_cast_1 "John Donaldson (the father)" has aliases ["John Donaldson", "John Donaldson (the son)", "John"]. The son should be a SEPARATE character entry, not an alias of the father.
   - Evidence: Father and son are clearly different people — the father is the embezzler who faked his death; the son is the 18-year-old ambulance driver who enlists in WWI.
   - Root cause: The LLM's character extraction or identity resolution merged the son into the father. In attempt 48 they were correctly separate. LLM non-determinism caused this regression.
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` Pass 1 or Pass 2 alias resolution
   - Fix: This may be LLM non-determinism rather than a code bug. The same code produced correct results in attempt 48. However, the ROLE_CONFLICT constraint that was added (attempt 43) to PREVENT this exact merge may not be firing. Check if the constraint is still active and if it correctly prevents merging characters with different role contexts (father=embezzler vs son=soldier).

### HIGH

3. **"Johnny" is a separate character instead of son's alias** [Alias Grouping, score impact ~0.5]
   - Problem: supporting_6 "Johnny" (2 mentions) should be alias of the son (if son were correctly extracted)
   - Evidence: "Johnny" is a diminutive of "John" referring to the boy in the story
   - Location: Supporting cast extraction or F6 reconciliation
   - Fix: When the son is correctly extracted as a separate character, "Johnny" should map to him

4. **Summary says "sister" instead of "cousin"** [Summaries, score impact ~0.3]
   - Problem: Section 2 says "his deceased sister's twelve-year-old son" — should be "his deceased cousin's" son
   - Evidence: Text says "a cousin, who had come to be this lad's father"
   - Location: Summary LLM hallucination — may resolve on re-run

5. **All evidence_quotes are null** [Profiles, score impact ~0.5]
   - Problem: Every character has `evidence_quotes: null` — no supporting quotes in any profile
   - Evidence: In attempt 48, at least some characters had evidence quotes
   - Location: `src/pipeline/character_profiling/` — the profile generation pipeline
   - This could be related to the passage_gatherer.py change or F19 grounding warnings noted in pipeline logs

### MEDIUM

6. **"Red Cross" extracted as character** [Completeness, score impact ~0.2]
   - Problem: supporting_3 "Red Cross" (4 mentions) is an organization, not a character
   - Location: Supporting cast extraction prompt

7. **Pronunciation: 35% false positive rate** [Pronunciation, score impact ~0.5]
   - Problem: 7 of 20 entries are standard English words
   - Location: `src/pipeline/pronunciation/` — filtering logic

8. **Structure: 2 sections for continuous text** [Structure, score impact ~0.5]
   - Problem: Continuous short story split into 2 sections, both with null titles
   - Location: `src/pipeline/chapter_detection/`

9. **`narrator_name` field is null** [Identity Resolution, score impact ~0.2]
   - Problem: Uncle Bill (the father) is tagged `is_narrator: true` but top-level `narrator_name` is null
   - Location: `src/analyzer.py`

## Fix Priority Recommendation

**The passage_gatherer.py fix (attempt 49) should be KEPT** — the profile content quality improved (the son's actual characterization appears, just attached to wrong entity). The regression is UPSTREAM in character extraction, not in profiling.

**CRITICAL #1 and #2 are both caused by LLM non-determinism in character extraction.** The same code produced correct results in attempt 48 (Uncle Bill single, father/son separate). The LLM made different extraction decisions this run.

**RECOMMENDED APPROACH:** Since the passage_gatherer.py fix is deterministic and correct, and the character extraction regression is from LLM non-determinism, the best action is:
1. **KEEP the passage_gatherer.py fix** (it's working correctly for profiles)
2. **Re-run analysis** to see if the LLM produces better character extraction this time
3. If Uncle Bill split persists across multiple runs, then investigate adding a constraint that prevents splitting narrator characters

**DO NOT revert passage_gatherer.py** — the fix is correct and the regression is unrelated to it.

**DO NOT attempt dedup/merge fixes in main_cast.py** — the modification history shows 8 prior attempts with 50% regression rate.

## Fix History

### Attempt 49 — Strip parenthetical disambiguators in passage gatherer — **MIXED RESULT**
- **Issue targeted:** CRITICAL #1 from attempt 48 — Son's profile is entirely the father's profile
- **Fix:** Strip parenthetical disambiguators from names before creating search pattern in `passage_gatherer.py`
- **Profile result:** IMPROVED — "Uncle Bill (the son)" entity got the son's actual characterization (brave, heroic, wartime), proving the passage_gatherer fix works. But it's attached to the wrong entity due to upstream regression.
- **Character extraction result:** REGRESSION — LLM non-determinism caused Uncle Bill to be falsely split and John Donaldson son to be merged into father. The passage_gatherer.py change does NOT affect character extraction (it only affects profiling).
- **Files modified:**
  - `src/pipeline/character_profiling/passage_gatherer.py` (+5 lines)
- **Assessment:** The fix itself is correct and should be KEPT. The regression is upstream.

### Attempt 48 — REVERT attempt 47 deduplication + re-analyze — **BASELINE RECOVERY**
- **Issue:** Attempt 47's deduplication caused catastrophic regression (7.08→5.95, -1.13 points)
- **Action:** Reverted commit b13fd2f changes to main_cast.py, re-ran analysis
- **Result:** Baseline restored — father/son separate, Uncle Bill single entity, narrator correct. Score: 5.95→6.88
- **Files modified:**
  - `src/pipeline/character_extraction_v2/main_cast.py` (-78 lines)

### Attempt 47 — Add deduplication for identical canonical names — **REGRESSION (REVERTED)**
- Score: 7.08→5.95 (-1.13)

### Attempt 46 — Extend grounding gate for parenthetical disambiguators — SUCCESS
- Score: 6.88→7.08

### Attempt 45 — REVERT attempt 44's alias filter — PARTIAL RECOVERY
- Score: 6.45→6.88

### Attempt 44 — Filter shared base name from aliases after Pass 2 — **REGRESSION (REVERTED)**
- Score: 6.98→6.45

### Attempt 43 — Disambiguator-based ROLE_CONFLICT constraint — SUCCESS
- Score: 6.48→6.98

### Attempts 29-42 — See score history table below

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 49 | Strip parenthetical disambiguators in passage gatherer | `passage_gatherer.py` (+5 lines) | **MIXED** — Profiles improved but upstream character extraction regressed (LLM non-determinism). Score: 6.88→6.15 |
| 48 | REVERT attempt 47's deduplication + re-analyze | `main_cast.py` (-78 lines) | **BASELINE RECOVERY** — Score: 5.95→6.88 |
| 47 | Deduplicate identical canonical names after Pass 2 | `main_cast.py` (+75 lines) | **REGRESSION (REVERTED)** — Score: 7.08→5.95 |
| 46 | Extend grounding gate for parenthetical disambiguators | `mention_search.py` (+5 lines), `test_character_extraction_v2.py` (+28 lines) | **PARTIAL SUCCESS** — Score: 6.88→7.08 |
| 45 | REVERT attempt 44's alias filter | `main_cast.py` (-16 lines), `test_character_extraction_v2.py` | **PARTIAL RECOVERY**. Score: 6.45→6.88 |
| 44 | Filter shared base name from aliases after Pass 2 | `main_cast.py` (+19 lines), `test_character_extraction_v2.py` | **REGRESSION (REVERTED)**. Score: 6.98→6.45 |
| 43 | Disambiguator-based ROLE_CONFLICT constraint | `evidence_collectors.py` (+39 lines) | SUCCESS. Score: 6.48→6.98 |
| 42 | Deterministic same-name split enforcement | `main_cast.py` (+104 lines) | REGRESSION. Score: 6.80→6.48 |
| 41 | REVERT attempt 40 changes | `main_cast.py`, `test_character_extraction_v2.py` | PARTIAL RECOVERY. Score: 6.45→6.80 |
| 40 | Ensure both same-name characters get disambiguators | `main_cast.py`, `test_character_extraction_v2.py` | REGRESSION. Score: 7.10→6.45 |
| 39 | Preserve disambiguators in canonical names | `main_cast.py` | PARTIAL SUCCESS. Score: 6.80→7.10 |
| 38 | REVERT target preference signal | `name_disambiguator.py` | REGRESSION. Score: 6.90→6.80 |
| 37 | Profile passage disambiguation | `name_disambiguator.py` | REGRESSION. Score: 7.15→6.90 |
| 36 | Grounding gate Sr./Jr. suffix | `mention_search.py`, `test_character_extraction_v2.py` | PARTIAL SUCCESS. Score: 7.05→7.15 |
| 35 | ROLE_CONFLICT hard constraint | `identity_graph.py` | PARTIAL SUCCESS. Score: 6.80→7.05 |
| 34 | Adaptive promotion thresholds | `characters.py` | PARTIAL SUCCESS. Score: 6.65→6.80 |
| 33 | Possessive stripping + narrator detection | `supporting.py`, `narrator.py` | MIXED. Score: 6.65 |
| 32 | Alias cleanup | `evidence_collectors.py`, `main_cast.py` | NO EFFECT |
| 31 | Deterministic same-name constraint | `evidence_collectors.py` | SUCCESS. Score: 6.78→7.33 |
| 30 | Pronunciation false positives | `character_proposer.py`, `foreign_proposer.py` | Pronunciation improved, character regression |
| 29 | Disambiguation labels post-processing | `characters.py` | SUCCESS. Score: 7.13 |

**PATTERN ALERT:** `main_cast.py` has been modified 8 times (attempts 39-48). Half were regressions. Do NOT attempt further dedup or merge fixes in main_cast.py.

**NEW PATTERN:** LLM non-determinism is a major factor. The same code produced correct character extraction in attempt 48 (Uncle Bill single, father/son separate) and incorrect extraction in attempt 49 (Uncle Bill split, son merged into father). No code changed between these runs for character extraction.

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
| 49 | 6.15 | -0.45 | **REGRESSION** — LLM non-determinism, Uncle Bill split, son merged |

## Next Action
Phase set to `awaiting_analysis`. Re-run to test if LLM non-determinism resolves itself (no code changes).

### Attempt 50 — No code changes, re-run to test LLM non-determinism — **KEEPING PASSAGE_GATHERER FIX**
- **Decision:** Keep the passage_gatherer.py fix from attempt 49 (it's correct and profiles improved)
- **Rationale:**
  - The passage_gatherer.py fix successfully improved profile quality - "Uncle Bill (the son)" got the son's actual characterization
  - The character extraction regression (Uncle Bill split, son merged into father) is LLM non-determinism, NOT caused by passage_gatherer.py
  - passage_gatherer.py only affects profiling, not character extraction
  - The same code produced correct character extraction in attempt 48
  - Modification history shows main_cast.py has been modified 8 times with 50% regression rate - avoid further changes
- **Root Cause Analysis:**
  - Uncle Bill false split: Summaries' `characters_present` lists may have included "Uncle Bill (the father)" and "Uncle Bill (the son)" due to summarizer LLM non-determinism, which the character extraction LLM then treated as distinct per prompt instructions
  - John Donaldson son merged into father: LLM Pass 1 or Pass 2 incorrectly merged them, despite correct separation in attempt 48
- **Action:** Re-run analysis without code changes to test if LLM produces better character extraction
- **If issue persists:** Consider adding deterministic constraint in `_enforce_same_name_splits` to prevent splitting characters identified as narrators (narrators inherently span all time periods)
