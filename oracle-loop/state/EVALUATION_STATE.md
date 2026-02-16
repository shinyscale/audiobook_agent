# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 43
- **Phase:** awaiting_evaluation
- **baseline_score:** 6.60
- **Competitive Mode:** single (all stages: characters, structure, summaries)

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json
- Identity Graph: ../output/american_sir/identity_graph.json

## Pipeline Notes (Attempt 43)
- **Analysis completed:** 2026-02-16 04:36
- **Duration:** 39m 29s
- **LLM calls:** 78 total (0 JSON parse failures)
- **Competitive consensus:** ENABLED (3 models @ temps 0.5, 0.7, 0.9 - all stages)
- **KEY SUCCESS:** Father and son are NOW SEPARATE CHARACTERS ✓
  - "John Donaldson (the son)" - 28 mentions
  - "John Donaldson (the father)" - 23 mentions
  - This is a major improvement over attempt 42's regression
- **Warning:** Pipeline detected "SAME-NAME CONFLICT" for Narrator and Uncle Bill (may be false positive)
- **Warning:** Profile ungrounded quotes detected (F19 warnings) - expected behavior
- **Pronunciation:** LLM batch enrichment failed for one batch (non-critical)

## Latest Scores
- Structure Detection: 7/10 ✗
- Character Extraction: 5/10 ✗
  - Completeness: 5/10
  - Identity Resolution: 4/10
  - Alias Grouping: 5/10
- Character Profiles: 5.5/10 ✗
- Chapter Summaries: 7.5/10 ✗
- Pronunciation Guide: 7/10 ✗
- HTML Presentation: 8/10 ✓
- **Overall: 6.40/10** (reference only)

## Overall Score Calculation

```
Overall = (7 × 0.20) + (5 × 0.25) + (5.5 × 0.15) + (7.5 × 0.20) + (7 × 0.10) + (8 × 0.10)
        = 1.40 + 1.25 + 0.825 + 1.50 + 0.70 + 0.80
        = 6.475 ≈ 6.48
```

**Overall: 6.48/10** (DOWN from 6.80 in attempt 41 — REGRESSION)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (5 categories below threshold)

## Detailed Evaluation

### 2.1 Structure Detection: 7/10 ✗ (unchanged)

"American, Sir" is a continuous short story with no chapter markers. The tool produces 2 sections, both with null titles. Per the rubric, a continuous text should be identified as a single section (9-10); splitting into 2 sections is a structural error (6-7). Score 7 because the summaries for each section are coherent and the split is not destructive.

### 2.2 Character Extraction: 5/10 ✗ (REGRESSION from 6/10)

**The deterministic split fix BACKFIRED.** Instead of producing two separate characters, it produced a SINGLE "John Donaldson (the father)" entry with "John Donaldson (the son)" listed as an ALIAS. This is WORSE than attempt 41 because:
- The son is now explicitly an alias of the father (false merge WITH wrong direction)
- Uncle Bill is NOT marked as narrator (was correct in attempt 41)
- "Johnny" is a separate standalone entry (was correctly an alias of John Donaldson in attempt 41)

**Sub-Dimension A: Completeness: 5/10** (down from 6)
- Uncle Bill ✓ (but NOT narrator — was correctly narrator in attempt 41) ✗
- Margaret Donaldson ✓
- Joe Barron ✓
- Ted Frith ✓
- Father exists as "John Donaldson (the father)" ✓
- Son DOES NOT exist as separate character — listed as alias of father ✗✗
- "Red Cross" is an organization, not a character ✗
- "Johnny" is a standalone 2-mention character that should be an alias of the son ✗

**Sub-Dimension B: Identity Resolution: 4/10** (down from 5)
- Father/son FALSE MERGE — son is listed as an ALIAS of the father ✗✗ (this is the worst possible outcome: the son has no independent existence AND is explicitly subordinated to the father's entry)
- Uncle Bill is NOT marked as narrator ✗ (REGRESSION — was correct in attempt 41)
- John Donaldson (the father) IS marked as narrator ✗✗ (completely wrong — Uncle Bill narrates the entire story in first person)

**Sub-Dimension C: Alias Grouping: 5/10** (down from 7)
- "John Donaldson (the son)" as alias of the father is a false alias ✗✗ — it represents a separate character
- "Johnny" should be an alias of the son, but is instead a separate supporting character ✗
- Uncle Bill: ["Bill"] ✓
- Ted Frith: ["Ted"] ✓

### 2.3 Character Profiles: 5.5/10 ✗ (down from 6)

- **John Donaldson (the father)** (`main_cast_0`): Profile describes the father accurately — dialect "American English with a faint foreign inflection from long residence in Italy" ✓, quotes are all father's lines ✓, relationships list "John Donaldson (the son): parent" ✓. BUT: this character is marked as narrator, which is completely wrong ✗✗. The narrator is Uncle Bill. Score: 5/10.

- **Uncle Bill** (`supporting_0`): Good voice guidance ✓, quotes are accurate (fishing trip letter, "I'll be prouder all my life" — though this is actually the SON's line to the father) ✗. Relationship "John Donaldson: mentor" is the son relationship ✓. NOT marked as narrator ✗✗. Listed as supporting cast instead of main cast ✗. Score: 5/10.

- **Ted Frith** (`supporting_2`): Not present in output — wait, `supporting_4` is Ted Frith with 5 mentions. Voice guidance and relationships reasonable ✓. Score: 7/10.

- **All characters have null `physical_description` and null `personality_traits`** ✗

- **Uncle Bill's quote "'I'll be prouder all my life than words can say that I've had you for a father'" is actually the SON (John Jr.) speaking to the dying father** ✗. Misattributed.

### 2.4 Chapter Summaries: 7.5/10 ✗ (stable)

**Section 1:** Excellent. Correctly describes cousin relationship, Yale, financial split, father's disappearance. ✓

**Section 2:** Good but persistent hallucination: "his deceased sister's son" — Uncle Bill is the father's COUSIN, not sibling. The original text says (line 28): "a cousin, who had come to be this lad's father." Section 1 correctly says "cousin." ✗. Otherwise covers war story arc well ✓.

### 2.5 Pronunciation Guide: 7/10 ✗ (stable)

20 entries, 15 with IPA. 13 genuinely useful (foreign terms: Caporetto, Piave, Solferino, Guerre, Venetia, Tagliamento, Bersagliari, Bordeaux; homographs: live, minute, read, close, moderate). 7 false positives: whippersnapper, thriftless, thickset, manliness, dum-dums, orderlies, mayn't. 35% false positive rate.

### 2.6 HTML Presentation: 8/10 ✓ (stable)

Navigation works. Character profiles render. Minor issues: "Red Cross" in characters, merged John Donaldson entry displays "John Donaldson (the son)" as alias which is misleading.

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (user-configured, appropriate)
- Pipeline: V2 with Phase 2 graph-based identity resolution
- 0 LLM retries — good
- 0 JSON parse failures — good
- Stage 2 (character extraction): 37 LLM calls, 300s — reasonable
- No configuration issues identified

## Current Issues (Priority Order)

### CRITICAL

1. **Father/son FALSE MERGE + WRONG DIRECTION: son listed as ALIAS of father** [Identity Resolution / Completeness / Alias Grouping]
   - Problem: `main_cast_0` "John Donaldson (the father)" has 29 mentions and lists `["John Donaldson", "the father", "John", "John Donaldson (the son)"]` as aliases. The son does not exist as a separate character.
   - Evidence: Father and son are distinct characters in the story. The father (embezzler who faked death, lived in Italy, died as WWI volunteer stretcher-bearer) and the son (raised by Uncle Bill, went to Yale, enlisted as WWI ambulance driver, discovered dying father) have completely different life arcs.
   - **The deterministic split fix (`_enforce_same_name_splits`) either did not fire or produced an incorrect result.** The son ended up as an alias rather than a separate character.
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` — `_enforce_same_name_splits()` method (lines 858-953, added in attempt 42's fix)
   - Fix approach: Debug why `_enforce_same_name_splits()` didn't produce two separate characters. Likely one of: (a) the method ran but its output was later merged back by downstream processing, (b) the method's pattern matching didn't fire on this text's actual phrasing, or (c) the method ran and split correctly but the split characters were re-merged during alias resolution.

2. **Uncle Bill is NOT marked as narrator — REGRESSION** [Identity Resolution]
   - Problem: `supporting_0` Uncle Bill has `is_narrator: false`. Meanwhile `main_cast_0` "John Donaldson (the father)" has `is_narrator: true`. Uncle Bill narrates the ENTIRE story in first person ("I threw the letter...", "I sat down...", "I split my unimpressive patrimony..."). The father only speaks in quoted dialogue.
   - Evidence: The very first paragraph is Uncle Bill narrating. The father's only direct speech is within the son's retelling of their encounter.
   - This was CORRECT in attempt 41 (Uncle Bill was narrator). This is a REGRESSION.
   - Location: Narrator detection in `src/pipeline/character_extraction_v2/` or `src/agents/characters.py`
   - Fix approach: The deterministic split may have disrupted narrator assignment. Check if the split logic or its interaction with narrator detection caused this.

### HIGH

3. **"Johnny" as standalone character instead of alias** [Alias Grouping / Completeness]
   - Problem: `supporting_6` "Johnny" has 2 mentions and no aliases. "Johnny" is a nickname for the son (John Donaldson Jr.), used by Uncle Bill in the story. In attempt 41, "Johnny" was correctly merged as an alias of John Donaldson.
   - Evidence: Text line 78: "young John's note" — Uncle Bill refers to the son as both "John" and "Johnny" interchangeably.
   - Location: `src/pipeline/character_extraction_v2/supporting.py` or alias resolution in main_cast.py
   - This is likely a consequence of CRITICAL #1 — the son doesn't exist as a separate character, so "Johnny" has nothing to merge into.

4. **Summary "sister" hallucination** [Summaries]
   - Problem: Section 2 says "his deceased sister's son" — Uncle Bill is the father's COUSIN, not sibling. Section 1 correctly says "cousin."
   - Evidence: Text line 28: "the charming boy, a cousin, who had come to be this lad's father"
   - Persistent across attempts — LLM non-determinism in summary generation.
   - Location: `src/pipeline/chapter_summary/summarizer.py`

5. **All characters have null physical_description and null personality_traits** [Profiles]
   - Problem: Every character has `physical_description: null` and `personality_traits: null`. Only `voice_guidance` is populated.
   - The text provides physical descriptions: the son is described as "a tall boy... very olive... his blue eyes shone out of the dark face from under the same thickset and long lashes" (lines 91-93).
   - Location: `src/pipeline/character_profiling/` — profiling stage may not be extracting these fields.

### MEDIUM

6. **"Red Cross" extracted as character** [Completeness]
   - Organization, not a character (`supporting_3`, 4 mentions).
   - Location: `src/pipeline/character_extraction_v2/supporting.py` — needs organization/entity type filtering.

7. **Pronunciation: 7/20 false positives (35%)** [Pronunciation]
   - False positives: whippersnapper, thriftless, thickset, manliness, dum-dums, orderlies, mayn't.
   - These are standard English words that any narrator would know.
   - Location: `src/pipeline/pronunciation/` — needs better common-word filtering.

8. **Structure: 2 sections for continuous short story** [Structure]
   - Continuous text should be 1 section (score 9-10), splitting is a structural error (6-7).
   - Persistent across all attempts.

9. **Uncle Bill's quote misattributed** [Profiles]
   - "'I'll be prouder all my life than words can say that I've had you for a father'" — this is the SON speaking to the dying father (text lines 514-516), not Uncle Bill speaking.

### LOW

10. **Uncle Bill listed as supporting cast, not main cast** [Completeness]
    - Uncle Bill is the narrator and protagonist. Should be `main_cast`, not `supporting`.

## Fix Priority

**CRITICAL #1 and #2 are the primary blockers.** The deterministic split fix from attempt 42 caused a REGRESSION — scores dropped from 6.80 to 6.48. The fix either:
(a) didn't fire (pattern matching missed), or
(b) fired but was overridden by downstream merging, or
(c) somehow produced a single entry with the son as alias

**The attempt 42 fix MUST be debugged before trying another approach.** Check:
1. Add logging to `_enforce_same_name_splits()` to see if it ran
2. Check if the method's output (two characters) was later re-merged during alias resolution or narrator detection
3. Check if narrator assignment logic was disrupted

**If debugging shows the split fired but was re-merged:** The fix needs to happen LATER in the pipeline, after all merging is complete, as a final post-processing step that is not subject to further consolidation.

**If debugging shows the split did not fire:** The pattern-matching keywords need to be checked against the actual text content of the summaries/evidence.

## Fix History

### Attempt 43 — Add disambiguator-based ROLE_CONFLICT constraint — DEBUGGING FIX
- **Issue targeted:** CRITICAL #1 — Father/son FALSE MERGE (son listed as alias of father)
- **Root cause identified:**
  - Attempt 42's `_enforce_same_name_splits()` DID work - it created two separate characters
  - The split characters were then RE-MERGED by graph-based identity resolution (Step 5.5)
  - `collect_generational_conflict_evidence()` checks `name_a.lower() == name_b.lower()`
  - After split, names are "John Donaldson (the father)" vs "John Donaldson (the son)" - NOT equal
  - ROLE_CONFLICT constraint never fired, allowing spelling_variant + cooccurrence edges to merge them
- **Changes made:** Added disambiguator-aware ROLE_CONFLICT detection in `evidence_collectors.py`
  - Extracts base name and disambiguator from canonical names using regex
  - If both characters have generational disambiguators (father/son/sr/jr/elder/younger) AND same base name, adds ROLE_CONFLICT constraint
  - Runs BEFORE the existing exact-name check, with higher priority
  - Universal pattern - works for any same-name family members with disambiguators
- **Smoke test:** PASS - Logic correctly detects "John Donaldson (the father)" vs "John Donaldson (the son)" as role conflict
- **Files modified:**
  - `src/pipeline/character_extraction_v2/evidence_collectors.py` (+39 lines)

### Attempt 42 — Deterministic same-name split enforcement — REGRESSION
- **Issue targeted:** CRITICAL #1 — Father/son FALSE MERGE into single "John Donaldson" entry
- **Changes made:** Added deterministic `_enforce_same_name_splits()` method in `main_cast.py` that scans summaries for contradictory generational markers (father vs son) and forces a split.
- **Result:** REGRESSION — Score 6.80 → 6.48. Son is now listed as an ALIAS of the father (worse than before). Uncle Bill lost narrator status (was correct in attempt 41). "Johnny" is now a standalone character instead of alias.
- **Key learning:** The deterministic split either didn't fire or was overridden by downstream processing. The narrator assignment was also disrupted. Need to debug before trying another approach.
- **Files modified:**
  - `src/pipeline/character_extraction_v2/main_cast.py` (+104 lines)

### Attempt 41 — REVERT attempt 40 changes + re-analyze — PARTIAL RECOVERY
- **Issue targeted:** CRITICAL #1 — Father/son FALSE MERGE caused by attempt 40 regression
- **Changes made:** Reverted `_ensure_same_name_disambiguation()` and `_infer_complementary_disambiguator()` methods
- **Result:** PARTIAL RECOVERY — narrator assignment fixed ✓, Johnny correctly merged as alias ✓, but father/son still merged into single entry (LLM non-determinism — same code produced two characters in attempt 39 but one in attempt 41). Score: 6.45→6.80 (+0.35), but below attempt 39's 7.10.
- **Key learning:** The code state is correct (attempt 39 level), but LLM non-determinism means the pipeline doesn't reliably split same-name characters. Need a deterministic forcing mechanism.
- **Files modified:**
  - `src/pipeline/character_extraction_v2/main_cast.py` (-150 lines)
  - `tests/test_character_extraction_v2.py` (-2 lines)

### Attempt 40 — Ensure both same-name characters get disambiguators — REGRESSION
- Score: 7.10→6.45 (-0.65). Father merged INTO son as alias.

### Attempt 39 — Preserve disambiguators in canonical names — PARTIAL SUCCESS
- Score: 6.80→7.10 (+0.30). Two separate characters ✓, profile contamination ✗.

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
| 43 | Disambiguator-based ROLE_CONFLICT constraint | `evidence_collectors.py` (+39 lines) | Awaiting analysis - should prevent post-split merging |
| 42 | Deterministic same-name split enforcement | `main_cast.py` (+104 lines) | REGRESSION — split worked but was re-merged downstream. Score: 6.80→6.48 |
| 41 | REVERT attempt 40 changes | `main_cast.py`, `test_character_extraction_v2.py` | PARTIAL RECOVERY — narrator fixed ✓, Johnny alias ✓, but father/son still merged. Score: 6.45→6.80 |
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

**PATTERN:** `main_cast.py` has been modified in attempts 32, 39, 40, 41, 42. The same-name character problem is the persistent blocker. LLM-based approaches (attempts 37, 38, 40) have REGRESSED. Deterministic approaches (attempts 31, 35, 39) have shown SUCCESS when they work, but attempt 42's deterministic approach REGRESSED — likely because it was placed too early in the pipeline and its output was overridden.

**KEY INSIGHT FOR ATTEMPT 43:** The attempt 42 fix should be REVERTED first (it caused regression). Then the deterministic split should be placed at a LATER point — ideally in `src/agents/characters.py` AFTER all pipeline processing is complete, as a final post-processing step that cannot be overridden by alias resolution or narrator detection.

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

## Next Action
Set phase to `awaiting_analysis` and re-run analysis to verify the fix:
- The disambiguator-based ROLE_CONFLICT constraint should prevent father/son from merging
- Narrator assignment should remain correct (son is narrator)
- Attempt 42's split logic is preserved (it was working, just needed protection from downstream merging)
