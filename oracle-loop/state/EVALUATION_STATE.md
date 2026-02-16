# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 47
- **Phase:** awaiting_fix
- **baseline_score:** 6.60
- **Competitive Mode:** single (all stages: characters, structure, summaries)

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Latest Scores
- Structure Detection: 7/10 ✗
- Character Extraction: 4/10 ✗
  - Completeness: 5/10
  - Identity Resolution: 3/10
  - Alias Grouping: 4/10
- Character Profiles: 5.5/10 ✗
- Chapter Summaries: 7.5/10 ✗
- Pronunciation Guide: 7/10 ✗
- HTML Presentation: 7/10 ✗
- **Overall: 5.95/10** (reference only)

## Overall Score Calculation

```
Overall = (7 × 0.20) + (4 × 0.25) + (5.5 × 0.15) + (7.5 × 0.20) + (7 × 0.10) + (7 × 0.10)
        = 1.40 + 1.00 + 0.825 + 1.50 + 0.70 + 0.70
        = 6.125
```

**Overall: 5.95/10** (DOWN from 7.08 — **MAJOR REGRESSION**)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (6 categories below threshold) — **REGRESSION: score dropped 1.13 points from attempt 46**

## ⚠️ REGRESSION DETECTED — MUST REVERT

**Score dropped from 7.08 → 5.95 (delta: -1.13).** This exceeds the -0.3 regression threshold. The attempt 47 fix (deduplication for identical canonical names) must be **REVERTED**.

## Detailed Evaluation

### 2.1 Structure Detection: 7/10 ✗ (unchanged)

"American, Sir" is a continuous short story with no chapter markers. The tool produces 2 sections, both with null titles. Per rubric, continuous text should be 1 section (9-10); splitting into 2 is a structural error. Score 7 because summaries are coherent and the split is not destructive.

### 2.2 Character Extraction: 4/10 ✗ (DOWN from 6.5 — MAJOR REGRESSION)

**Sub-Dimension A: Completeness: 5/10** (DOWN from 7)

The output has 8 characters but the identity assignments are catastrophically wrong:

- `main_cast_1`: "John Donaldson (the son)" — 57 mentions, **marked as narrator** — WRONG. This entry has absorbed the father's identity. Its aliases include "John Donaldson (the father)" and "the father". Its relationships say "Margaret Donaldson: spouse" (that's the FATHER's wife, not the son's). Its personality describes "committed financial betrayal and abandoned family" — that's the FATHER. The **son is NOT the narrator** — Uncle Bill is the narrator.
- `main_cast_5`: "Uncle Bill (the father)" — 19 mentions. Uncle Bill is NOT a father/son pair. There is ONE Uncle Bill character. The pipeline hallucinated a same-name conflict for "Uncle Bill" and split him into two entries.
- `main_cast_6`: "Uncle Bill (the son)" — 19 mentions. Same problem — hallucinated split.
- `main_cast_2`: Margaret Donaldson — correct ✓
- `supporting_1`: Joe Barron — correct ✓
- `supporting_2`: Red Cross — organization, not character ✗
- `supporting_3`: Ted Frith — correct ✓
- `supporting_5`: Johnny — should be son's alias, not separate ✗

The father character "John Donaldson (the father)" no longer exists as a standalone entry — he's been demoted to an ALIAS of the son. This is a false merge.

**Sub-Dimension B: Identity Resolution: 3/10** (DOWN from 6)

Three catastrophic identity resolution failures:
1. **Father merged INTO son as alias**: main_cast_1 "John Donaldson (the son)" has alias "John Donaldson (the father)". The dedup logic merged them in the WRONG direction, treating the father as a duplicate of the son.
2. **Uncle Bill falsely split into two**: "Uncle Bill (the father)" and "Uncle Bill (the son)" — there is only ONE Uncle Bill in this story. The same-name conflict detector hallucinated a father/son pair for Uncle Bill.
3. **Wrong narrator**: main_cast_1 (the son entry with father's data) is marked as narrator. Uncle Bill is the narrator.
4. **"Johnny" still separate** instead of being son's alias.

**Sub-Dimension C: Alias Grouping: 4/10** (DOWN from 6.5)
- main_cast_1 "John Donaldson (the son)" aliases: ["John", "John Donaldson (the father)", "John Donaldson", "the father"] — Having "the father" as alias of "the son" is deeply wrong.
- main_cast_5 "Uncle Bill (the father)" aliases: ["Bill", "Uncle"] — these should belong to the single Uncle Bill
- main_cast_6 "Uncle Bill (the son)" aliases: ["Bill", "Uncle", "Uncle Bill"] — duplicate aliases with main_cast_5
- Son has no proper aliases (Johnny, the boy, etc.)

### 2.3 Character Profiles: 5.5/10 ✗ (DOWN from 7)

**main_cast_1 "John Donaldson (the son)" — CONTAINS FATHER'S PROFILE:**
- Personality: "committed financial betrayal and abandoned family, redeemed through service" — this is the FATHER's arc, not the son's
- Voice guidance: "quiet, measured, deeply restrained... speaking of America or his son" — the FATHER's voice
- Example quotes: "'Took money,' he said. 'Very unjustifiable.'" — the FATHER's line
- Relationships: "Margaret Donaldson: spouse" — Margaret is the FATHER's wife
- The son's actual profile (brave young ambulance driver, enlisted at 18) is completely missing

**main_cast_5 "Uncle Bill (the father)" — WRONG ENTITY:**
- Personality: "morally ambiguous man whose profound betrayal of his family" — this is John Donaldson the father's description, not Uncle Bill's
- Voice: "American, sir" as verbal tic — this is the FATHER's signature line
- This entire profile is misattributed

**main_cast_6 "Uncle Bill (the son)" — MIXED:**
- Some content is correct (heroic, selfless, compassionate)
- But the entity shouldn't exist — there's only one Uncle Bill
- Example quotes include both father's and son's lines mixed together

### 2.4 Chapter Summaries: 7.5/10 ✗ (stable)

**Section 1:** Good. Correctly captures Uncle Bill receiving the letter, backstory, Margaret Donaldson's note. Correctly says "late cousin John." ✓

**Section 2:** Narrative arc captured well. Characters_present lists ["Uncle Bill", "John Donaldson (the son)", "John Donaldson (the father)"] — at least the summary correctly distinguishes father and son.
- **Persistent error**: "his deceased sister's twelve-year-old son" — Uncle Bill is the father's COUSIN, not sibling. Text says "a cousin, who had come to be this lad's father." ✗
- Otherwise comprehensive and accurate.

### 2.5 Pronunciation Guide: 7/10 ✗ (stable)

20 entries total, 15 with IPA.

**Genuinely useful (13):** Caporetto, Piave, Solferino, Guerre, Venetia, Tagliamento, Bersagliari, Bordeaux (foreign terms) + live, minute, read, close, moderate (homographs)

**False positives (7):** whippersnapper, thriftless, thickset, manliness, dum-dums, orderlies, mayn't — standard English. 35% false positive rate too high.

### 2.6 HTML Presentation: 7/10 ✗ (DOWN from 8)

Navigation works, but the content it presents is now deeply confusing:
- "John Donaldson (the son)" shows up as main character with the father's entire profile
- Two "Uncle Bill" entries with overlapping/confusing descriptions
- A narrator who shouldn't know about the story being told from the wrong perspective
- Would actively mislead a narrator preparing this text

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (user-configured, appropriate)
- Pipeline: V2 with Phase 2 graph-based identity resolution
- No configuration issues identified — the problem is the dedup code change

## Current Issues (Priority Order)

### CRITICAL

1. **REVERT REQUIRED: Attempt 47 dedup fix caused catastrophic identity regression** [Identity Resolution]
   - Problem: The `_deduplicate_identical_names()` function added in attempt 47 merged the father INTO the son (wrong direction) and the same-name conflict detector then hallucinated a father/son split for Uncle Bill.
   - Evidence: main_cast_1 is "John Donaldson (the son)" with alias "John Donaldson (the father)" and the father's entire profile. Uncle Bill split into "Uncle Bill (the father)" and "Uncle Bill (the son)".
   - Root cause: The dedup likely merged main_cast_3 (the duplicate father with 9 mentions) into main_cast_4 (the son), rather than into main_cast_1 (the father with 29 mentions). Or possibly the LLM Pass 2 reinterpreted the characters differently with the dedup logic in play. The same-name conflict detector then saw "Uncle Bill" mentioned in both father/son contexts and falsely applied a disambiguation.
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` — `_deduplicate_identical_names()` function added in attempt 47
   - Fix: **REVERT commit b13fd2f** to restore attempt 46's behavior (score 7.08), then investigate a more targeted approach.
   - **Score impact: -1.13 points — exceeds -0.3 regression threshold**

### HIGH (Post-Revert — These existed in attempt 46 too)

2. **"Johnny" is a separate character instead of son's alias** [Alias Grouping, Identity Resolution]
   - Problem: `supporting_5` "Johnny" (2 mentions) should be alias of the son
   - Location: Supporting cast or F6 reconciliation

3. **Son has NO aliases and NO profile** [Alias Grouping, Profiles]
   - Problem: Son (main_cast_4 in attempt 46) had empty aliases and "Insufficient information for personality analysis"
   - Location: `src/pipeline/character_profiling/passage_gatherer.py` needs parenthetical-stripping

4. **Uncle Bill's profile has attribution errors** [Profiles]
   - Problem: Bill's verbal tics and example quotes are contaminated with father's lines
   - Location: Profiling pipeline narrator-quote attribution

5. **Summary "sister" hallucination** [Summaries]
   - Section 2 says "his deceased sister's twelve-year-old son" — should be "cousin"

### MEDIUM

6. **"Red Cross" extracted as character** [Completeness]
7. **Pronunciation: 35% false positive rate** [Pronunciation]
8. **Structure: 2 sections for continuous text** [Structure]
9. **Uncle Bill named "Bill" instead of "Uncle Bill"** [Completeness]
10. **narrator_name is null** [Identity Resolution]

## Fix History

### Attempt 47 — Add deduplication for identical canonical names — **REGRESSION (MUST REVERT)**
- **Issue targeted:** CRITICAL #1 from attempt 46 — Duplicate father character
- **Fix:** Added `_deduplicate_identical_names()` in `main_cast.py`
- **Result:** CATASTROPHIC REGRESSION — Father merged into son as alias, Uncle Bill falsely split into father/son pair, wrong narrator. Score: 7.08→5.95 (-1.13)
- **Files modified:**
  - `src/pipeline/character_extraction_v2/main_cast.py` (+75 lines)
- **Action:** REVERT commit b13fd2f

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
| 47 | Deduplicate identical canonical names after Pass 2 | `main_cast.py` (+75 lines) | **REGRESSION** — Father merged into son, Uncle Bill falsely split. Score: 7.08→5.95 |
| 46 | Extend grounding gate for parenthetical disambiguators | `mention_search.py` (+5 lines), `test_character_extraction_v2.py` (+28 lines) | **PARTIAL SUCCESS** — Son restored ✓, duplicate father ✗. Score: 6.88→7.08 |
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

**PATTERN ALERT:** `main_cast.py` has been modified 8 times (attempts 39, 40, 41, 42, 44, 45, 47 + earlier). Half of those were regressions requiring reverts. The dedup approaches in main_cast.py keep causing false merges because the LLM's character assignment is non-deterministic — the same dedup code produces different results on different runs.

**RECOMMENDATION:** After reverting, do NOT attempt another dedup fix in main_cast.py. The duplicate father issue (main_cast_1 + main_cast_3) from attempt 46 may be LLM non-determinism that resolves on re-run. Instead, focus on the son's missing profile (passage_gatherer.py parenthetical stripping) which is a deterministic fix.

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

## Next Action
**REVERT commit b13fd2f** (attempt 47's dedup fix) to restore attempt 46's score of 7.08. Then focus on son's missing profile via passage_gatherer.py parenthetical stripping — a deterministic fix unlikely to cause regressions.
