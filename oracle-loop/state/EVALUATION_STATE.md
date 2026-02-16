# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 46
- **Phase:** awaiting_analysis
- **baseline_score:** 6.60
- **Competitive Mode:** single (all stages: characters, structure, summaries)

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json
- Identity Graph: output/American Sir_20260216_060847/identity_graph.json

## Latest Scores
- Structure Detection: 7/10 ✗
- Character Extraction: 6/10 ✗
  - Completeness: 6/10
  - Identity Resolution: 5/10
  - Alias Grouping: 7/10
- Character Profiles: 6.5/10 ✗
- Chapter Summaries: 7.5/10 ✗
- Pronunciation Guide: 7/10 ✗
- HTML Presentation: 8/10 ✓
- **Overall: 6.78/10** (reference only)

## Overall Score Calculation

```
Overall = (7 × 0.20) + (6 × 0.25) + (6.5 × 0.15) + (7.5 × 0.20) + (7 × 0.10) + (8 × 0.10)
        = 1.40 + 1.50 + 0.975 + 1.50 + 0.70 + 0.80
        = 6.875
```

**Overall: 6.88/10** (UP from 6.45 in attempt 44 — revert recovered most of the regression)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (5 categories below threshold)

## Comparison with Attempt 43 (6.98)

The revert of attempt 44's alias filter partially restored the state, but with a **different failure mode**:

| Aspect | Attempt 43 | Attempt 45 |
|--------|-----------|-----------|
| Father present? | Yes (main_cast_1) | Yes (main_cast_0) ✓ |
| Son present? | Yes (main_cast_0) | **NO** ✗ — son MISSING |
| Father's profile | Contaminated with son's attributes | **Correct** — father's attributes properly assigned ✓ |
| Son's profile | Contaminated with father's attributes | N/A — son doesn't exist |
| Narrator | Uncle Bill ✓ | Uncle Bill ✓ (but metadata says "Narrator (the father)" ✗) |
| Father named | "John Donaldson (the father)" | "John Donaldson Sr." ✓ |

The LLM non-determinism produced a different main_cast composition this run. The main_cast pipeline produced "John Donaldson Sr." (the father) as main_cast_0, but the son ("John Donaldson (the son)") was rejected by F6 grounding with 0 text mentions. The `supporting_0` "John Donaldson" (9 mentions) was then merged into the father instead of becoming the son.

## Detailed Evaluation

### 2.1 Structure Detection: 7/10 ✗ (unchanged)

"American, Sir" is a continuous short story with no chapter markers. The tool produces 2 sections, both with null titles. Per the rubric, a continuous text should be identified as a single section (9-10); splitting into 2 sections is a structural error (6-7). Score 7 because the summaries are coherent and the split is not destructive.

### 2.2 Character Extraction: 6/10 ✗

**Sub-Dimension A: Completeness: 6/10**
- John Donaldson Sr. (the father) ✓ — 31 mentions, main_cast_0. Correctly named with "Sr." suffix.
- **John Donaldson (the son) MISSING** ✗ — The son is a MAJOR character. He enlists in WWI, drives ambulances on the Italian front, encounters his father in disguise, and tells the entire second half of the story to Uncle Bill. He should have ~30 mentions. The `supporting_0` "John Donaldson" (9 mentions) was merged into the father instead of being recognized as the son.
- Uncle Bill ✓ — 18 mentions, narrator ✓ (but listed as supporting_1, should be main cast) ✗
- Margaret Donaldson ✓ — 2 mentions
- Joe Barron ✓ — 3 mentions
- Ted Frith ✓ — 5 mentions
- "Red Cross" — organization, not a character ✗

Score 6 (not 5) because the father is present and correctly named, which was a regression in attempt 44. But the son being missing is critical.

**Sub-Dimension B: Identity Resolution: 5/10**
- Son completely missing — `supporting_0` "John Donaldson" (9 mentions) merged INTO father as an alias instead of being kept separate as the son. This is a **false merge**.
- The ROLE_CONFLICT constraint from attempt 43 IS working (same-name conflict detected), but F6 grounding gate rejected "John Donaldson (the son)" because the text never uses that exact string. The parenthetical disambiguator fails the literal text search.
- `narrator_name: "Narrator (the father)"` in metadata is completely wrong — Uncle Bill is the narrator. However, the character-level `is_narrator` flag is correct on Uncle Bill.
- Father's relationship to "John Donaldson Jr." refers to a non-existent character in the list.

**Sub-Dimension C: Alias Grouping: 7/10**
- Father's aliases: ["the father", "John", "John Donaldson", "Johnny"] — good set ✓
- Uncle Bill: ["Bill"] ✓
- Ted Frith: ["Ted"] ✓
- "John Donaldson" is listed as father's alias, which is correct for the father but prevents the son from being separately identified. This is more of an identity resolution issue than alias grouping.

### 2.3 Character Profiles: 6.5/10 ✗ (UP from 4.5 — significant improvement)

**Father's profile (John Donaldson Sr.) — GOOD:**
- Voice guidance: "weary and rough from years of hiding, brightens with quiet dignity" — accurate ✓
- Dialect: "American English with faint foreign twist from Italy" — accurate ✓
- Verbal tics: "American, sir", "I'm American to-day, sir" — correct, these ARE the father's lines ✓
- Appearance: "tall, olive skin, dark face, thickset and long lashes, grizzled" — this mixes father and son physical descriptions. The text describes the SON as "tall... very olive... blue eyes... dark face... thickset and long lashes." The father is described as "big, athletic, grizzled... with an air like a duke." ✗ Contamination persists here.
- Personality: "committed financial betrayal and abandoned family, found redemption through service" — accurate ✓
- Relationships: "John Donaldson Jr.: parent" (correct but Jr. isn't in character list), "Uncle Bill: victimizer" (wrong — the father didn't victimize Uncle Bill), "Margaret Donaldson: spouse" ✓

**Uncle Bill's profile — MIXED:**
- Voice guidance: "measured, gravelly baritone with restrained emotion" — reasonable ✓
- Personality summary: "embracing his lost son" — confused. Uncle Bill doesn't have a son; he's the cousin/uncle figure. This is narrative contamination from the father-son storyline. ✗
- Evidence quote #4: "'I want you to know that I'll be prouder all my life than words can say that I've had you for a father'" — this is the SON speaking to the dying father, NOT Uncle Bill's quote. ✗
- Relationships: "John Donaldson Sr.: enemy" — wrong. They were cousins/friends, not enemies. ✗

**Ted Frith's profile — MIXED:**
- Correctly identified as a separate character from the father ✓
- Appearance: "eyes that looked natural" — accurate quote from text ✓
- BUT example_quotes includes "'This is my good day. I'm American to-day, sir!'" — this is the FATHER's dying line, not Ted's ✗
- Personality traits are reasonable for a wartime comrade ✓

**Margaret Donaldson, Joe Barron, Red Cross — no profiles** (minor/supporting characters, acceptable)

Score improves from 4.5 to 6.5 because the father's profile is now mostly correct (was entirely missing in attempt 44), and the voice guidance is properly attributed. Main deductions: (1) appearance contamination on father, (2) Uncle Bill's profile confuses him with the father, (3) wrong relationship labels.

### 2.4 Chapter Summaries: 7.5/10 ✗ (stable)

**Section 1:** Good. Correctly captures Uncle Bill receiving the letter, backstory of his relationship with the father, and Margaret Donaldson's letter. Correctly says "late cousin John." ✓

**Section 2:** Good narrative arc captured but persistent factual error: "his deceased sister's twelve-year-old son" — Uncle Bill is the father's COUSIN, not sibling. The text says "a cousin, who had come to be this lad's father." Section 1 correctly says "cousin." ✗

Both sections are well-written and useful for narrator preparation. The plot summary in the overview is excellent and comprehensive. Characters_present in Section 2 references "John Donaldson (the son)" who doesn't exist in the character list — inconsistency.

### 2.5 Pronunciation Guide: 7/10 ✗ (stable)

20 entries total, 15 with IPA.

**Genuinely useful (13):** Caporetto, Piave, Solferino, Guerre, Venetia, Tagliamento, Bersagliari, Bordeaux (foreign terms) + live, minute, read, close, moderate (homographs)

**False positives (7):** whippersnapper, thriftless, thickset, manliness, dum-dums, orderlies, mayn't — standard English words. 35% false positive rate is too high.

### 2.6 HTML Presentation: 8/10 ✓ (stable)

Navigation works. Character profiles render correctly for those that have profiles. The missing son character is reflected in the HTML. The father's profile section is well-formatted with voice guidance, appearance, and personality. Minor issues: "Red Cross" in characters, and relationships reference non-existent "John Donaldson Jr."

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (user-configured, appropriate)
- Pipeline: V2 with Phase 2 graph-based identity resolution
- 0 LLM retries — good
- 0 JSON parse failures — good
- Profiling: 8 LLM calls, 3 items processed, all high confidence — pipeline working correctly
- No configuration issues identified

## Current Issues (Priority Order)

### CRITICAL

1. **John Donaldson (the son) is completely MISSING from output** [Completeness, Identity Resolution]
   - Problem: The son character was rejected by F6 grounding. The `supporting_0` "John Donaldson" (9 mentions) was merged into the father instead of being kept as the son. The identity graph shows `supporting_0` merged into `main_cast_0` (the father).
   - Evidence: Only 6 characters in output, none is the son. The son drives the entire second half of the story — he enlists, goes to war, encounters his father on the Italian front, and narrates the revelation to Uncle Bill.
   - Root cause: The main_cast pipeline detected same-name conflict and created "John Donaldson (the son)" but F6 grounding rejected it with 0 text mentions. The text never uses "John Donaldson (the son)" literally — it just says "John" or "John Donaldson." The parenthetical disambiguator in the canonical name makes the character invisible to literal text search.
   - Location: `src/pipeline/character_extraction_v2/mention_search.py` or `src/analyzer.py` (F6 grounding gate) — the grounding search needs to strip parenthetical disambiguators before searching the text
   - Fix approach: When searching for mentions of a character with a parenthetical disambiguator (e.g., "John Donaldson (the son)"), search for the BASE name ("John Donaldson") instead. The disambiguator is metadata for identity resolution, not a literal text string. This was partially addressed in attempt 36 (grounding gate Sr./Jr. suffix) but needs to be extended to handle parenthetical suffixes like "(the son)", "(the father)".
   - **This is the same class of issue as attempt 44 but in reverse**: attempt 44 dropped the father by removing "John Donaldson" from aliases; attempt 45 drops the son by failing to search for "John Donaldson" when the canonical name is "John Donaldson (the son)".

### HIGH

2. **Uncle Bill's profile confused with father** [Profiles]
   - Problem: Uncle Bill's personality summary says "embracing his lost son" — Uncle Bill doesn't have a son. Evidence quote "'I'll be prouder all my life...' that I've had you for a father" is the SON's line, not Uncle Bill's. Relationship to father listed as "enemy" (wrong — they were cousins).
   - Location: `src/pipeline/character_profiling/passage_gatherer.py` or `generator.py` — first-person narrative passage attribution
   - Fix: In first-person narratives, passages where "I" is the narrator should be attributed to the narrator, but when the narrator quotes another character's speech, the quote should go to the speaking character.

3. **Father's appearance contaminated with son's physical description** [Profiles]
   - Problem: Father's appearance includes "tall boy, very olive, blue eyes, dark face, thickset and long lashes" — the text describes the SON this way, not the father. Father is described as "big, athletic, grizzled chap, maybe fifty-five or over, shabby as to clothes, yet with an air like a duke."
   - Evidence: The passage "He was a tall boy, and he looked like his father. Very olive he was..." explicitly says "tall boy" referring to the son.
   - Location: `src/pipeline/character_profiling/passage_gatherer.py` — passages for "John Donaldson" are gathered without disambiguating which John Donaldson they describe
   - Fix: Same root cause as CRITICAL #1 — same-name characters need context-aware passage gathering

4. **Summary "sister" hallucination persists** [Summaries]
   - Problem: Section 2 says "his deceased sister's twelve-year-old son" — Uncle Bill is the father's COUSIN, not sibling.
   - Evidence: Text says "a cousin, who had come to be this lad's father." Section 1 correctly says "cousin."
   - Persistent across multiple attempts — LLM non-determinism.

5. **Wrong relationship labels** [Profiles]
   - Father → Uncle Bill: "victimizer" (wrong — should be "cousin" or "friend")
   - Uncle Bill → Father: "enemy" (wrong — should be "cousin")
   - Father → "John Donaldson Jr.": "parent" (correct label but refers to non-existent character)

### MEDIUM

6. **"Red Cross" extracted as character** [Completeness]
   - Organization, not a character (`supporting_4`, 4 mentions).

7. **Pronunciation: 7/20 false positives (35%)** [Pronunciation]
   - whippersnapper, thriftless, thickset, manliness, dum-dums, orderlies, mayn't — standard English.

8. **Structure: 2 sections for continuous short story** [Structure]
   - Persistent. Continuous text should be 1 section.

9. **Uncle Bill listed as supporting cast, not main cast** [Completeness]
   - Uncle Bill is narrator and has 18 mentions. Should be main cast.

10. **narrator_name in metadata says "Narrator (the father)"** [Identity Resolution]
    - Completely wrong. Uncle Bill is the narrator.

11. **Ted Frith's example quote "'This is my good day. I'm American to-day, sir!'"** [Profiles]
    - This is the father's dying line, not Ted's. Mild profile contamination affecting supporting character.

### LOW

12. **Father's relationship references non-existent "John Donaldson Jr."** [Profiles]
    - The son doesn't exist in the character list, so this relationship dangles.

## Fix Priority

**PRIMARY FIX: Make F6 grounding gate strip parenthetical disambiguators before text search**

The core issue across attempts 44 and 45 is that disambiguated characters (e.g., "John Donaldson (the father)", "John Donaldson (the son)") cannot be found in the literal text. The grounding gate (F6) needs to:
1. Detect parenthetical suffixes like "(the son)", "(the father)"
2. Strip them before searching
3. Search for the base name "John Donaldson" instead

This was partially addressed in attempt 36 for "Sr./Jr." suffixes but needs to be extended to general parenthetical disambiguators.

**Location:** Either `src/pipeline/character_extraction_v2/mention_search.py` (if that's where grounding search happens) or `src/analyzer.py` (F6 gate itself). Check which file handles the mention count search for grounding.

**Expected impact:** Restoring the son character would improve:
- Completeness: 6 → 7-8
- Identity Resolution: 5 → 7-8
- Profiles: Can't assess until son has a profile
- Overall Character Extraction: 6 → 7-8

**Secondary fixes** (after son is restored):
- Profile contamination for same-name characters remains the long-term blocker but is lower priority than having the son present at all

## Fix History

### Attempt 46 — Extend grounding gate to strip parenthetical disambiguators — FIX APPLIED
- **Issue targeted:** CRITICAL #1 from attempt 45 — John Donaldson (the son) completely MISSING from output
- **Root cause:** `mention_search.py:_extract_base_name()` only stripped Sr./Jr. suffixes, not parenthetical disambiguators like "(the son)", "(the father)". F6 grounding searched for "John Donaldson (the son)" literally, found 0 mentions, and rejected the character.
- **Changes made:** Extended `_extract_base_name()` to strip parenthetical disambiguators (e.g., "(the son)", "(the father)", "(narrator)") before searching text for mentions. These parentheticals are metadata for identity resolution, not literal text strings.
- **Smoke test:** PASS - Tested with 7 cases including "John Donaldson (the son)" → "John Donaldson", "Victor Frankenstein (narrator)" → "Victor Frankenstein". All base name extractions work correctly.
- **Expected impact:** Restoring the son character should improve:
  - Completeness: 6 → 7-8 (son now present)
  - Identity Resolution: 5 → 7-8 (no false merge of supporting_0 into father)
  - Overall Character Extraction: 6 → 7-8
- **Files modified:**
  - `src/pipeline/character_extraction_v2/mention_search.py` (+5 lines: regex to strip parenthetical suffixes)
  - `tests/test_character_extraction_v2.py` (+28 lines: 2 new tests for parenthetical and Sr./Jr. handling)
- **Test results:** 44/44 tests pass (added 2 new regression tests)

### Attempt 45 — REVERT attempt 44's alias filter — PARTIAL RECOVERY
- **Issue targeted:** CRITICAL #1 from attempt 44 — Father character completely DROPPED from output
- **Changes made:** Reverted the alias filter logic added in attempt 44
- **Result:** Father restored ✓, but **son now MISSING** due to F6 grounding rejecting "John Donaldson (the son)" with 0 text mentions. Different failure mode from attempt 44 (which dropped the father). Father's profile is now mostly correct — voice guidance, verbal tics, and personality are properly attributed. Score: 6.45 → 6.88 (partial recovery).
- **Files modified:**
  - `src/pipeline/character_extraction_v2/main_cast.py` (-16 lines: reverted import + filter block)
  - `tests/test_character_extraction_v2.py` (line count limit 7150→7350)

### Attempt 44 — Filter shared base name from aliases after Pass 2 — **REGRESSION (REVERTED)**
- **Issue targeted:** CRITICAL #1 from attempt 43 — Son's profile contaminated with father's attributes
- **Result:** REGRESSION — Father character DROPPED ENTIRELY from output. Score: 6.98→6.45 (-0.53).
- **Files modified:**
  - `src/pipeline/character_extraction_v2/main_cast.py` (+19 lines: import re, filter logic)
  - `tests/test_character_extraction_v2.py` (updated line count limit)

### Attempt 43 — Add disambiguator-based ROLE_CONFLICT constraint — SUCCESS
- **Issue targeted:** Father/son FALSE MERGE
- **Result:** SUCCESS — Father and son are NOW SEPARATE ✓, Uncle Bill is narrator ✓. Score: 6.48→6.98 (+0.50)
- **Files modified:** `src/pipeline/character_extraction_v2/evidence_collectors.py` (+39 lines)

### Attempt 42 — Deterministic same-name split enforcement — REGRESSION
- Score: 6.80→6.48. Split worked but was re-merged downstream.
- **Files modified:** `src/pipeline/character_extraction_v2/main_cast.py` (+104 lines)

### Attempt 41 — REVERT attempt 40 changes — PARTIAL RECOVERY
- Score: 6.45→6.80. Narrator fixed ✓, father/son still merged.

### Attempt 40 — Ensure both same-name characters get disambiguators — REGRESSION
- Score: 7.10→6.45. Father merged INTO son as alias.

### Attempt 39 — Preserve disambiguators in canonical names — PARTIAL SUCCESS
- Score: 6.80→7.10. Two characters ✓, profile contamination ✗.

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
| 45 | REVERT attempt 44's alias filter | `main_cast.py` (-16 lines), `test_character_extraction_v2.py` (limit 7150→7350) | **PARTIAL RECOVERY** — Father restored ✓, son MISSING ✗. Score: 6.45→6.88 |
| 44 | Filter shared base name from aliases after Pass 2 | `main_cast.py` (+19 lines), `test_character_extraction_v2.py` | **REGRESSION (REVERTED)** — Father character DROPPED. Score: 6.98→6.45 |
| 43 | Disambiguator-based ROLE_CONFLICT constraint | `evidence_collectors.py` (+39 lines) | SUCCESS — father/son separate ✓, narrator correct ✓, score 6.48→6.98 |
| 42 | Deterministic same-name split enforcement | `main_cast.py` (+104 lines) | REGRESSION — split worked but was re-merged downstream. Score: 6.80→6.48 |
| 41 | REVERT attempt 40 changes | `main_cast.py`, `test_character_extraction_v2.py` | PARTIAL RECOVERY — narrator fixed ✓, father/son still merged. Score: 6.45→6.80 |
| 40 | Ensure both same-name characters get disambiguators | `main_cast.py`, `test_character_extraction_v2.py` | REGRESSION — father merged into son. Score: 7.10→6.45 |
| 39 | Preserve disambiguators in canonical names | `main_cast.py` | PARTIAL SUCCESS — two characters ✓, profile contamination ✗. Score: 6.80→7.10 |
| 38 | REVERT target preference signal | `name_disambiguator.py` | REGRESSION — son false-merged. Score: 6.90→6.80 |
| 37 | Profile passage disambiguation | `name_disambiguator.py` | REGRESSION — duplicate profiles. Score: 7.15→6.90 |
| 36 | Grounding gate Sr./Jr. suffix | `mention_search.py`, `test_character_extraction_v2.py` | PARTIAL SUCCESS. Score: 7.05→7.15 |
| 35 | ROLE_CONFLICT hard constraint | `identity_graph.py` | PARTIAL SUCCESS. Score: 6.80→7.05 |
| 34 | Adaptive promotion thresholds | `characters.py` | PARTIAL SUCCESS. Score: 6.65→6.80 |
| 33 | Possessive stripping + narrator detection | `supporting.py`, `narrator.py` | MIXED. Score: 6.65 |
| 32 | Alias cleanup | `evidence_collectors.py`, `main_cast.py` | NO EFFECT |
| 31 | Deterministic same-name constraint | `evidence_collectors.py` | SUCCESS. Score: 6.78→7.33 |
| 30 | Pronunciation false positives | `character_proposer.py`, `foreign_proposer.py` | Pronunciation improved, character regression |
| 29 | Disambiguation labels post-processing | `characters.py` | SUCCESS. Score: 7.13 |

**PATTERN ALERT:** The F6 grounding gate is a recurring blocker for same-name characters. Attempts 36, 44, and 45 all stumble on grounding when characters have disambiguated names that don't appear literally in the text. The fix in attempt 36 handled "Sr./Jr." suffixes but didn't generalize to parenthetical disambiguators. `mention_search.py` has been modified once (attempt 36) — it needs a more general solution.

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.60 | — | Original baseline |
| 22 | 7.55 | +0.95 | Best score (all fixes active) |
| 23 | 6.30 | -0.30 | Clean baseline + Phase 2 pipeline |
| 31 | 7.33 | +0.73 | Deterministic same-name fix SUCCESS |
| 34 | 6.80 | +0.20 | Uncle Bill restored |
| 35 | 7.05 | +0.45 | HARD constraint works, father filtered |
| 36 | 7.15 | +0.55 | Father grounded ✓, profiles contaminated ✗ |
| 37 | 6.90 | +0.30 | REGRESSION — identical duplicate profiles |
| 38 | 6.80 | +0.20 | REGRESSION — son false-merged into father |
| 39 | 7.10 | +0.50 | Father/son SPLIT ✓, profile contamination ✗ |
| 40 | 6.45 | -0.15 | REGRESSION — father merged into son as alias |
| 41 | 6.80 | +0.20 | PARTIAL RECOVERY — narrator fixed, father/son still merged |
| 42 | 6.48 | -0.12 | REGRESSION — son as alias of father, narrator wrong |
| 43 | 6.98 | +0.38 | SUCCESS — father/son split ✓, narrator correct ✓, profiles contaminated |
| 44 | 6.45 | -0.15 | **REGRESSION** — father character DROPPED, profiles still contaminated |
| 45 | 6.88 | +0.28 | PARTIAL RECOVERY — father restored ✓, son dropped by F6 ✗, profiles improved |

## Next Action
Run PROMPT_fix.md to address F6 grounding gate for parenthetical disambiguators (CRITICAL #1). The fix should generalize the Sr./Jr. handling from attempt 36 to also strip "(the son)", "(the father)", and similar parenthetical suffixes before searching the text for mentions.
