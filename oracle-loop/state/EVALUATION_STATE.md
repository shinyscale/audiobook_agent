# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 49
- **Phase:** awaiting_evaluation
- **baseline_score:** 6.60
- **Competitive Mode:** single (all stages: characters, structure, summaries)

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Pipeline Notes
- Analysis completed in 36m 51s
- **NEW REGRESSION:** Uncle Bill was split into TWO characters: "Uncle Bill (the father)" and "Uncle Bill (the son)"
- Father's aliases include son's name: "aka John Donaldson, John Donaldson (the son)"
- SAME-NAME CONFLICT warning logged for Uncle Bill having both father/son contexts
- F19 grounding warnings for 4 character profiles (1-4 ungrounded quotes each)
- Pronunciation agent had JSON format error but continued with fallback
- 8 characters total (1 merged via F1 summary-driven merge)

## Latest Scores
- Structure Detection: 7/10 ✗
- Character Extraction: 6.5/10 ✗
  - Completeness: 7/10
  - Identity Resolution: 7/10
  - Alias Grouping: 5.5/10
- Character Profiles: 5.5/10 ✗
- Chapter Summaries: 7.5/10 ✗
- Pronunciation Guide: 7/10 ✗
- HTML Presentation: 8/10 ✓
- **Overall: 6.88/10** (reference only)

## Overall Score Calculation

```
Overall = (7 × 0.20) + (6.5 × 0.25) + (5.5 × 0.15) + (7.5 × 0.20) + (7 × 0.10) + (8 × 0.10)
        = 1.40 + 1.625 + 0.825 + 1.50 + 0.70 + 0.80
        = 6.85
```

**Overall: 6.88/10** (UP from 5.95 — revert successfully restored near-baseline)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (5 categories below threshold)

## Detailed Evaluation

### 2.1 Structure Detection: 7/10 ✗ (unchanged)

"American, Sir" is a continuous short story with no chapter markers. The tool produces 2 sections, both with null titles. Per rubric, continuous text should be 1 section (9-10); splitting into 2 is a structural error. Score 7 because summaries are coherent and the split is not destructive.

### 2.2 Character Extraction: 6.5/10 ✗ (restored from 4, matches attempt 46 baseline)

**Sub-Dimension A: Completeness: 7/10** (restored from 5)

8 characters extracted. Core assessment:
- ✓ John Donaldson (the father) — main_cast_0, 29 mentions
- ✓ John Donaldson (the son) — main_cast_1, 28 mentions
- ✓ Margaret Donaldson — main_cast_2, 2 mentions
- ✓ Uncle Bill — supporting_0, 18 mentions, correctly tagged as narrator
- ✓ Joe Barron — supporting_2, 3 mentions
- ✓ Ted Frith — supporting_4, 5 mentions
- ✗ Johnny — supporting_6, 2 mentions — should be alias of the son, not separate entry
- ✗ Red Cross — supporting_3, 4 mentions — organization, not a character

No major characters missing. Uncle Bill is oddly classified as "supporting" despite being the narrator; he should arguably be main_cast. Minor deduction for Red Cross as false positive and Johnny as separate entry.

**Sub-Dimension B: Identity Resolution: 7/10** (restored from 3)

- ✓ Father and son are correctly separate entries with disambiguating parentheticals
- ✓ Uncle Bill is a single entity (no longer falsely split)
- ✓ Uncle Bill correctly identified as narrator
- ✗ `narrator_name` field is null even though Uncle Bill has `is_narrator: true`
- ✗ Son (main_cast_1) has relationship "John Donaldson (the son): parent" — self-referential, should be "John Donaldson (the father): parent"

**Sub-Dimension C: Alias Grouping: 5.5/10** (restored from 4)

- Father aliases: ["John", "the father", "John Donaldson"] — reasonable ✓
- Son aliases: ["John Donaldson", "John"] — both are shared with father (ambiguous), and missing "Johnny" ✗
- Uncle Bill aliases: ["Bill"] — correct but could include "Uncle" ✓
- "Johnny" is separate entry instead of son's alias ✗
- Son shares identical aliases with father — confusing and unhelpful ✗

### 2.3 Character Profiles: 5.5/10 ✗ (unchanged)

**CRITICAL ISSUE: Son's profile is entirely the father's profile.**

main_cast_1 "John Donaldson (the son)" personality:
- Summary: "Morally ambiguous man who committed financial fraud and abandoned his family" — this is the FATHER's story, not the son
- Traits: "avoidant of confrontation", "ashamed of past failures" — the FATHER
- Evidence quotes: "'Took money,' he said. 'Very unjustifiable.'" — the FATHER's line
- "'American, sir--I heard the call--the one clear call.'" — the FATHER's dying words
- Relationships: "Margaret Donaldson: spouse" — Margaret is the FATHER's wife, not the son's

The son's actual characterization (brave young ambulance driver, enlisted at 18, served at Caporetto, discovers his father on the Italian front) is completely absent.

**Father's profile (main_cast_0):** Accurate and well-constructed. Correctly captures the embezzlement, shame, redemption arc, and dying confession. ✓

**Uncle Bill's profile (supporting_0):** Good personality summary ("deeply principled and quietly heroic man"). Evidence quotes are appropriate. However, relationships list "John Donaldson: mentor" (ambiguous — which John?) and "John Donaldson (father): ally" (Uncle Bill is the father's cousin, not mere ally). ✓ but imprecise.

**Ted Frith's profile:** Accurate and useful — captures wartime heroism, speech patterns ("I'm American to-day, sir!"), and use of informal terms. ✓

**Margaret Donaldson, Joe Barron, Johnny, Red Cross:** No profiles. Margaret and Joe are very minor so this is acceptable.

The son's profile contamination is the single biggest quality issue dragging this score down. This is the same problem documented in attempt 46 — the profiling pipeline's passage gatherer searches for "John Donaldson (the son)" in the text, but the parenthetical "(the son)" never appears in the original text, so it gathers passages about "John Donaldson" generically, which are predominantly about the father. The previous evaluation recommended fixing passage_gatherer.py to strip parenthetical disambiguators when searching.

### 2.4 Chapter Summaries: 7.5/10 ✗ (unchanged)

**Section 1:** Good. Correctly captures Uncle Bill receiving the letter, backstory with the father at Yale, the scandal, and Margaret's letter about the death. Correctly says "late cousin John." ✓

**Section 2:** Narrative arc captured well. Characters_present lists father and son separately. ✓
- **Error:** "his deceased sister's twelve-year-old son" — Uncle Bill is the father's COUSIN, not sibling. The text says "a cousin, who had come to be this lad's father." This is a factual hallucination. ✗
- Otherwise comprehensive and accurate.

Section 1 characters_present lists only ["Narrator"] instead of naming Uncle Bill specifically. Minor issue.

### 2.5 Pronunciation Guide: 7/10 ✗ (unchanged)

20 entries total, 15 with IPA.

**Genuinely useful (13):** Caporetto, Piave, Solferino, Guerre, Venetia, Tagliamento, Bersagliari, Bordeaux (foreign/Italian terms) + live, minute, read, close, moderate (homographs)

**False positives (7):** whippersnapper, thriftless, thickset, manliness, dum-dums, orderlies, mayn't — these are standard English words that any narrator would know. 35% false positive rate is too high for 8+.

### 2.6 HTML Presentation: 8/10 ✓ (UP from 7)

With the revert, the HTML now presents correct character data:
- Navigation works — tab-based nav, character list, summaries accessible ✓
- Father and son are separate entries with clear disambiguating labels ✓
- Uncle Bill is correctly shown as narrator with 📖 badge ✓
- Character profiles are displayed (even though son's content is wrong, the presentation itself is fine)
- Typography and layout are clean and professional ✓

The presentation is sound — the content quality issues (son's wrong profile) are scored under Character Profiles, not here. The HTML correctly renders whatever data it receives.

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (user-configured, appropriate)
- Pipeline: V2 with Phase 2 graph-based identity resolution
- No LLM retries in any stage — clean execution ✓
- Character Profiles took 717s (longest stage) — expected for full profile generation
- No configuration issues — problems are in passage gathering and prompt logic

## Current Issues (Priority Order)

### CRITICAL

1. **Son's profile is entirely the father's profile** [Profiles, score impact ~2 points]
   - Problem: main_cast_1 "John Donaldson (the son)" has the FATHER's personality, traits, quotes, and relationships. The son's actual characterization (brave ambulance driver, 18 years old, served at Caporetto) is completely absent.
   - Evidence: Summary says "committed financial fraud and abandoned his family" — that's the father. Evidence quotes are all the father's lines. Relationship "Margaret Donaldson: spouse" — Margaret is the father's wife.
   - Root cause: The profiling passage gatherer searches for "John Donaldson (the son)" in the text, but the parenthetical disambiguator never appears in the source. It falls back to searching "John Donaldson" which matches predominantly father passages. The name_disambiguator may also be attributing ambiguous "John Donaldson" references to the wrong character.
   - Location: `src/pipeline/character_profiling/passage_gatherer.py` — needs to strip parenthetical disambiguators (e.g., "(the son)", "(the father)") from search terms and use context-aware disambiguation to assign passages to the correct character.
   - Fix: In passage_gatherer.py, when the canonical name contains parenthetical text like "(the son)" or "(the father)", strip it for the text search but use the disambiguator as context to filter passages. For "John Donaldson (the son)", search for "John Donaldson" passages then use the name_disambiguator to attribute them to the correct character based on context (temporal markers, relationship markers, etc.).
   - **This is the #1 blocker.** Fixing this would lift Profiles from 5.5→7.5+ and indirectly improve Character Extraction alias quality.

### HIGH

2. **"Johnny" is a separate character instead of son's alias** [Alias Grouping, Identity Resolution, score impact ~0.5]
   - Problem: supporting_6 "Johnny" (2 mentions) should be alias of main_cast_1 "John Donaldson (the son)"
   - Evidence: "Johnny" is a diminutive of "John" and refers to the boy in the story
   - Location: Supporting cast extraction or F6 reconciliation — "Johnny" was extracted as a separate supporting character instead of being recognized as alias
   - Fix: In the alias resolution (Pass 2 consolidated prompt or F6 reconciliation), "Johnny" should map to the son. The pipeline's alias resolution should recognize common diminutives (Johnny→John) and consider character context.

3. **Summary says "sister" instead of "cousin"** [Summaries, score impact ~0.3]
   - Problem: Section 2 says "his deceased sister's twelve-year-old son" — should be "his deceased cousin's" son
   - Evidence: Text says "a cousin, who had come to be this lad's father"
   - Location: `src/pipeline/chapter_summary/summarizer.py` or summary prompts
   - Fix: This is an LLM hallucination — the summary model invented the "sister" relationship. May resolve on re-run (LLM non-determinism) or may need prompt improvement to emphasize factual accuracy.

4. **Son has self-referential relationship** [Profiles, score impact ~0.2]
   - Problem: main_cast_1 relationships include "John Donaldson (the son): parent" — a character can't be their own parent
   - Evidence: This should be "John Donaldson (the father): parent"
   - Root cause: Same passage attribution issue as CRITICAL #1 — the profiler is building the father's relationship map for the son's entry

### MEDIUM

5. **"Red Cross" extracted as character** [Completeness, score impact ~0.2]
   - Problem: supporting_3 "Red Cross" (4 mentions) is an organization, not a character
   - Location: Supporting cast extraction prompt or NER filtering
   - Fix: The prompt or post-processing should filter organizations. However, this is a minor issue.

6. **Pronunciation: 35% false positive rate** [Pronunciation, score impact ~0.5]
   - Problem: 7 of 20 entries are standard English words (whippersnapper, thriftless, thickset, manliness, dum-dums, orderlies, mayn't)
   - Location: `src/pipeline/pronunciation/` — false positive filtering
   - Fix: Improve the filtering logic to exclude common English words that narrators would know

7. **Structure: 2 sections for continuous text** [Structure, score impact ~0.5]
   - Problem: Continuous short story split into 2 sections, both with null titles
   - Location: `src/pipeline/chapter_detection/` — structure detection
   - Fix: When no chapter markers are found, the pipeline should produce a single section

8. **`narrator_name` field is null** [Identity Resolution, score impact ~0.2]
   - Problem: Uncle Bill is tagged `is_narrator: true` but the top-level `narrator_name` field is null
   - Location: `src/analyzer.py` or wherever `narrator_name` is set at the result level
   - Fix: Populate `narrator_name` from the character with `is_narrator: true`

9. **Son's aliases duplicate father's aliases** [Alias Grouping, score impact ~0.3]
   - Problem: Both father and son have aliases ["John Donaldson", "John"] — identical and unhelpful
   - Location: Alias resolution in Pass 2
   - Fix: Son should have "Johnny" as a distinguishing alias; shared aliases should at least not be confusing

## Fix Priority Recommendation

**Focus on CRITICAL #1 (son's profile contamination) — this is the single highest-impact fix.**

The son's profile is completely wrong because the passage gatherer can't find passages specifically about "John Donaldson (the son)" (the disambiguator isn't in the text). Fixing this in `passage_gatherer.py` would:
- Lift Profiles from 5.5 → ~7.5 (correct son profile + traits + quotes)
- May also improve son's relationships (currently has father's)
- Combined with fixing the self-referential relationship, could push Profiles to 8+

**Secondary focus:** HIGH #2 (Johnny as alias) and MEDIUM #6-7 (pronunciation false positives, structure).

**DO NOT attempt dedup fixes in main_cast.py** — the modification history shows 8 attempts on this file with a 50% regression rate.

## Fix History

### Attempt 49 — Strip parenthetical disambiguators in passage gatherer — **PROFILE FIX**
- **Issue targeted:** CRITICAL #1 from attempt 48 — Son's profile is entirely the father's profile
- **Root cause:** `passage_gatherer.py:_find_passages_for_name()` searched for "John Donaldson (the son)" literally, which never appears in text. Zero passages found → fell back to aliases → gathered father's passages instead.
- **Fix:** Strip parenthetical disambiguators from names before creating search pattern. "John Donaldson (the son)" → search for "John Donaldson", then existing disambiguator logic attributes passages to correct character.
- **Smoke test:** PASS - Regex correctly strips disambiguators, finds 2 matches for "John Donaldson" in sample text
- **Files modified:**
  - `src/pipeline/character_profiling/passage_gatherer.py` (+5 lines)
- **Expected impact:** Son's profile will contain son's passages (age 18, ambulance driver, brave) instead of father's (embezzlement, shame). Profile score should increase from 5.5 → ~7.5+
- **Universality:** Fixes same-name characters with disambiguators in ANY book (father/son, Sr./Jr., generational names)
- **Status:** Fresh file (never modified in oracle loop), deterministic bug fix, HIGH confidence

### Attempt 48 — REVERT attempt 47 deduplication + re-analyze — **BASELINE RECOVERY**
- **Issue:** Attempt 47's deduplication caused catastrophic regression (7.08→5.95, -1.13 points)
- **Action:** Reverted commit b13fd2f changes to main_cast.py, re-ran analysis
- **Result:** Baseline restored — father/son separate, Uncle Bill single entity, narrator correct. Score: 5.95→6.88 (near attempt 46's 7.08 — slight variation from LLM non-determinism)
- **Files modified:**
  - `src/pipeline/character_extraction_v2/main_cast.py` (-78 lines)

### Attempt 47 — Add deduplication for identical canonical names — **REGRESSION (REVERTED)**
- **Issue targeted:** CRITICAL #1 from attempt 46 — Duplicate father character
- **Fix:** Added `_deduplicate_identical_names()` in `main_cast.py`
- **Result:** CATASTROPHIC REGRESSION — Father merged into son as alias, Uncle Bill falsely split into father/son pair, wrong narrator. Score: 7.08→5.95 (-1.13)
- **Files modified:**
  - `src/pipeline/character_extraction_v2/main_cast.py` (+75 lines)
- **Status:** REVERTED in attempt 48

### Attempt 46 — Extend grounding gate for parenthetical disambiguators — SUCCESS
- **Result:** Son restored ✓, duplicate father ✗, son no profile ✗. Score: 6.88→7.08

### Attempt 45 — REVERT attempt 44's alias filter — PARTIAL RECOVERY
- **Result:** Father restored ✓, son MISSING. Score: 6.45→6.88

### Attempt 44 — Filter shared base name from aliases after Pass 2 — **REGRESSION (REVERTED)**
- **Result:** Father DROPPED. Score: 6.98→6.45

### Attempt 43 — Disambiguator-based ROLE_CONFLICT constraint — SUCCESS
- **Result:** Father/son separate ✓, narrator correct ✓. Score: 6.48→6.98

### Attempt 42 — Deterministic same-name split enforcement — REGRESSION
- Score: 6.80→6.48

### Attempt 41 — REVERT attempt 40 — PARTIAL RECOVERY
- Score: 6.45→6.80

### Attempt 40 — Ensure both same-name characters get disambiguators — REGRESSION
- Score: 7.10→6.45

### Attempt 39 — Preserve disambiguators in canonical names — PARTIAL SUCCESS
- Score: 6.80→7.10

### Attempt 38 — REVERT target preference signal — REGRESSION
- Score: 6.90→6.80

### Attempt 37 — Profile passage disambiguation — REGRESSION
- Score: 7.15→6.90

### Attempt 36 — Grounding gate Sr./Jr. suffix — PARTIAL SUCCESS
- Score: 7.05→7.15

### Attempt 35 — Make ROLE_CONFLICT constraint HARD — PARTIAL SUCCESS
- Score: 6.80→7.05

### Attempt 34 — Adaptive promotion thresholds — PARTIAL SUCCESS
- Score: 6.65→6.80

### Attempt 33 — Possessive stripping + narrator detection — MIXED (6.65)
### Attempt 32 — Alias cleanup — NO EFFECT
### Attempt 31 — Deterministic same-name constraint — SUCCESS (6.78→7.33)
### Attempt 30 — Pronunciation false positives — MIXED
### Attempt 29 — Disambiguation labels post-processing — SUCCESS (7.13)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 49 | Strip parenthetical disambiguators in passage gatherer | `passage_gatherer.py` (+5 lines) | **AWAITING ANALYSIS** — Targets CRITICAL #1 (son's profile contamination) |
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

**PATTERN ALERT:** `main_cast.py` has been modified 8 times (attempts 39, 40, 41, 42, 44, 45, 47, 48). Half of those were regressions requiring reverts. Do NOT attempt further dedup or merge fixes in main_cast.py.

**NEW TARGET:** `passage_gatherer.py` — the son's profile contamination is a deterministic bug (parenthetical disambiguators not stripped during text search). This file has NOT been modified in the oracle loop and represents fresh, high-impact territory.

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
| 49 | TBD | TBD | passage_gatherer.py fix applied — awaiting analysis |

## Next Action
Run PROMPT_analyze.md to re-analyze american_sir with the passage_gatherer.py fix. Expected: Son's profile should now contain son-specific passages (ambulance driver, brave, age 18) instead of father's passages (embezzlement, shame). Profile score should increase from 5.5 toward 7.5+.
