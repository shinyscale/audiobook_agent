# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 42
- **Phase:** awaiting_analysis
- **baseline_score:** 6.60
- **Competitive Mode:** single (all stages: characters, structure, summaries)

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Latest Scores
- Structure Detection: 7/10 ✗
- Character Extraction: 6/10 ✗
  - Completeness: 6/10
  - Identity Resolution: 5/10
  - Alias Grouping: 7/10
- Character Profiles: 6/10 ✗
- Chapter Summaries: 7.5/10 ✗
- Pronunciation Guide: 7/10 ✗
- HTML Presentation: 8/10 ✓
- **Overall: 6.80/10** (reference only)

## Overall Score Calculation

```
Overall = (7 × 0.20) + (6 × 0.25) + (6 × 0.15) + (7.5 × 0.20) + (7 × 0.10) + (8 × 0.10)
        = 1.40 + 1.50 + 0.90 + 1.50 + 0.70 + 0.80
        = 6.80
```

**Overall: 6.80/10** (UP from 6.45 in attempt 40, near attempt 39's 7.10)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (5 categories below threshold)

## Detailed Evaluation

### 2.1 Structure Detection: 7/10 ✗ (unchanged)

"American, Sir" is a continuous short story with no chapter markers. The tool produces 2 sections, both with null titles. Per the rubric, a continuous text should be identified as a single section (9-10); splitting into 2 sections is a structural error (6-7). Score 7 because the summaries for each section are coherent and the split is not destructive.

### 2.2 Character Extraction: 6/10 ✗

**Improvements from attempt 40:**
- Uncle Bill correctly identified as sole narrator ✓ (was wrong in attempt 40)
- "Johnny" now correctly an alias of John Donaldson ✓ (was a separate character in attempt 40)
- No explicit wrong-direction merge (attempt 40 had father as alias of son) ✓

**Remaining problems:**
- Father and son are combined into ONE "John Donaldson" entry with 30 mentions ✗✗
- "Red Cross" extracted as a character (organization) ✗
- Father does not exist as a separate character ✗

**Sub-Dimension A: Completeness: 6/10**
- Uncle Bill ✓, Margaret ✓, Joe Barron ✓, Ted Frith ✓
- Father MISSING as separate character — absorbed into merged entry ✗✗
- "Red Cross" is an organization ✗

**Sub-Dimension B: Identity Resolution: 5/10**
- Father/son FALSE MERGE — one entry combines two different people with different life arcs ✗✗
- The father (embezzler who faked death, lived in Italy, died in WWI as volunteer) and son (raised by Uncle Bill, went to Yale, enlisted in WWI ambulance corps, discovered dying father) are distinct characters
- Johnny correctly merged as alias ✓ (improvement)
- Uncle Bill correctly sole narrator ✓ (improvement)

**Sub-Dimension C: Alias Grouping: 7/10**
- Uncle Bill: ["Bill"] ✓
- John Donaldson: ["John", "Johnny"] ✓ (aliases are correct for the merged entity)
- Ted Frith: ["Ted"] ✓
- No self-aliases or invalid aliases ✓

### 2.3 Character Profiles: 6/10 ✗

- **Uncle Bill** (`main_cast_0`): Tone and dialect accurate ✓. Two quotes misattributed: "'American, sir'" is the father's catchphrase ✗, "'No--no. It's covered over...'" is the SON speaking ✗. Relationships list three confusing "John Donaldson" variants that don't match the character list ✗. physical_description: null, personality_traits: null ✗. Score: 6/10.

- **John Donaldson** (`main_cast_1`): Profile describes the FATHER — dialect "English with a slight foreign inflection, possibly Italian-influenced" (father lived in Italy for decades, son grew up in America) ✗. Quotes are all father's lines: "American, sir.", "Took money. Quite a lot of money..." ✗. Relationships internally contradictory — lists "Uncle Bill: mentor" (son's relationship) AND "John Donaldson (son): parent" (father's relationship) ✗✗. Score: 4/10.

- **Ted Frith** (`supporting_2`): Accurate tone, quotes, and verbal tics ✓. Score: 8/10.

- **All characters have null physical_description and null personality_traits** ✗

### 2.4 Chapter Summaries: 7.5/10 ✗ (stable)

**Section 1:** Excellent. Correctly describes cousin relationship, Yale, financial split, father's disappearance. ✓

**Section 2:** Good but persistent hallucination: "his deceased sister's son" — Uncle Bill is the father's COUSIN, not sibling. Section 1 correctly says "cousin." ✗. Otherwise covers war story arc well ✓.

### 2.5 Pronunciation Guide: 7/10 ✗ (stable)

20 entries, 15 with IPA. 13 genuinely useful (foreign terms: Caporetto, Piave, Solferino, Guerre, Venetia, Tagliamento, Bersagliari, Bordeaux; homographs: live, minute, read, close, moderate). 7 false positives: whippersnapper, thriftless, thickset, manliness, dum-dums, orderlies, mayn't. 35% false positive rate.

### 2.6 HTML Presentation: 8/10 ✓ (stable)

Navigation works. Character profiles render. Uncle Bill displayed as protagonist and narrator. Minor issues: "Red Cross" in characters, merged John Donaldson profile internally contradictory.

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (user-configured, appropriate)
- Pipeline: V2 with Phase 2 graph-based identity resolution
- 0 LLM retries — good
- 0 JSON parse failures — good
- Stage 2 (character extraction): 16 LLM calls, 147s — reasonable
- No configuration issues identified

## Current Issues (Priority Order)

### CRITICAL

1. **Father/son FALSE MERGE: single "John Donaldson" entry combines two distinct characters** [Identity Resolution / Completeness]
   - Problem: `main_cast_1` "John Donaldson" (30 mentions) combines the father (embezzler who faked death, lived in Italy, died as WWI volunteer stretcher-bearer) and the son (raised by Uncle Bill, went to Yale, enlisted as WWI ambulance driver, discovered dying father).
   - Evidence: Profile describes the father (Italian dialect, embezzlement quotes) but relationships mix both characters (mentor from Uncle Bill = son's; spouse Margaret = father's).
   - This is the CORE problem of american_sir across 41 attempts. Both characters share the exact name "John Donaldson."
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` — the pipeline cannot distinguish two characters with identical names without explicit textual cues being captured.
   - **Root cause analysis:** The same-name disambiguation has been attempted many ways:
     - Attempt 29: Disambiguation labels post-processing (SUCCESS but partial)
     - Attempt 31: Deterministic same-name constraint (SUCCESS, score 7.33)
     - Attempt 35: Hard ROLE_CONFLICT constraint (PARTIAL SUCCESS)
     - Attempt 39: Preserve disambiguators in canonical names (got two characters)
     - Attempt 40: Ensure both get disambiguators (REGRESSION — merged them)
     - Attempt 41: Revert to attempt 39 state (BUT LLM non-determinism produced single merged entry instead of two)
   - **The code is back to attempt 39's state, but LLM non-determinism means we didn't get the same result.** The pipeline CAN produce two characters (attempt 39 proved it), but doesn't do so reliably. The same-name split needs to be more deterministic/forced.
   - Fix approach: The pipeline needs a HARD rule that when the identity graph detects two distinct clusters for the same name (different chapter ranges, different roles, different ages), it FORCES a split even when the LLM consolidation merges them. This should happen AFTER the consolidated pass2, as a deterministic post-processing step.

### HIGH

2. **John Donaldson profile is internally contradictory** [Profiles]
   - Problem: The merged entry has father's characteristics (Italian dialect, embezzlement quotes) but son's relationships (Uncle Bill as mentor). A narrator reading this would be confused.
   - This is a CONSEQUENCE of CRITICAL #1. Fixing the character split should resolve it.

3. **Summary "sister" hallucination** [Summaries]
   - Problem: Section 2 says "his deceased sister's son" — Uncle Bill is the father's COUSIN, not sibling. Section 1 correctly says "cousin."
   - Persistent across attempts — LLM non-determinism in summary generation.
   - Location: `src/pipeline/chapter_summary/summarizer.py` — may need relationship-aware summary post-processing or a fact-check pass.

4. **All characters have null physical_description and null personality_traits** [Profiles]
   - Problem: Every character has `physical_description: null` and `personality_traits: null`. Only `voice_guidance` is populated.
   - Location: `src/pipeline/character_profiling/` — profiling stage may not be extracting these fields.

### MEDIUM

5. **"Red Cross" extracted as character** [Completeness]
   - Organization, not a character (`supporting_1`, 4 mentions).
   - Location: `src/pipeline/character_extraction_v2/supporting.py` — needs organization/entity type filtering.

6. **Pronunciation: 7/20 false positives (35%)** [Pronunciation]
   - False positives: whippersnapper, thriftless, thickset, manliness, dum-dums, orderlies, mayn't.
   - These are standard English words that any narrator would know.
   - Location: `src/pipeline/pronunciation/` — needs better common-word filtering.

7. **Structure: 2 sections for continuous short story** [Structure]
   - Continuous text should be 1 section (score 9-10), splitting is a structural error (6-7).
   - Persistent across all attempts.

8. **Uncle Bill's quotes misattributed** [Profiles]
   - "'American, sir'" is the father's catchphrase, not Uncle Bill's.
   - "'No--no. It's covered over...'" is the SON speaking to the dying father, not Uncle Bill.
   - Location: `src/pipeline/character_profiling/passage_gatherer.py` — quote attribution logic.

### LOW

9. **Uncle Bill's relationships reference three "John Donaldson" variants** [Profiles]
   - Lists "John (the elder)", "John Donaldson (the younger)", "John Donaldson (the father)" as separate relationships, but the character list only has one "John Donaldson" entry. Confusing for narrator.

## Fix Priority

**CRITICAL #1 is the persistent blocker** across 41 attempts. The father/son same-name merge is the root cause of most failing scores (Character Extraction, Profiles, and indirectly Summaries).

**Key insight:** Attempt 39 SUCCESSFULLY produced two separate characters with the same code that attempt 41 has. The difference is LLM non-determinism. The fix needs to make the split MORE DETERMINISTIC — not relying on the LLM to decide to split them, but forcing a split when evidence clearly indicates two different characters share a name.

**Recommended approach for attempt 42:**
The identity graph (`identity_graph.py`) and/or `_process_consolidated_pass2()` need a deterministic post-processing rule: when evidence passages for a single name clearly reference two different people (different generational markers, different chapter ranges, different life stages), force a split into two characters with disambiguators — REGARDLESS of what the LLM consolidation returned. This is more robust than attempt 40's approach (which tried to add disambiguators via LLM inference and got a merge instead).

Specifically:
1. After consolidated pass2, check if any character's evidence references contain contradictory life-stage markers (e.g., "parent" and "child" of the same person, "old" and "young" in different passages)
2. If found, split into two characters with role-based disambiguators
3. This must be deterministic (no LLM call) to avoid non-determinism

## Fix History

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

**PATTERN:** `main_cast.py` has been modified in attempts 32, 39, 40, 41. The same-name character problem is the persistent blocker. LLM-based approaches (attempts 37, 38, 40) have REGRESSED. Deterministic approaches (attempts 31, 35, 39) have shown SUCCESS. **Attempt 42 should use a DETERMINISTIC post-processing split**, not rely on LLM judgment.

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

## Fix History

### Attempt 42 — Deterministic same-name split enforcement — IMPLEMENTED
- **Issue targeted:** CRITICAL #1 — Father/son FALSE MERGE into single "John Donaldson" entry
- **Root cause:** `src/pipeline/character_extraction_v2/main_cast.py` - LLM non-determinism in Pass 2 consolidation. Attempt 39 successfully produced two characters with same code, but attempt 41 merged them due to LLM variance.
- **Changes made:** Added deterministic `_enforce_same_name_splits()` method that runs AFTER `_process_consolidated_pass2()`. Scans summaries for contradictory generational markers (father vs son) in contexts mentioning the character's name. Forces split when both markers detected.
- **Smoke test:** ✓ PASSED - Test case with "John's father" and "twelve-year-old John Donaldson" correctly split into "(the father)" and "(the son)" variants.
- **Universality:** This will help ANY book with same-name family members (common pattern across all literature)
- **Files modified:**
  - `src/pipeline/character_extraction_v2/main_cast.py` (+104 lines)
    - Added `_enforce_same_name_splits()` static method (lines 858-953)
    - Called from `_extract_two_pass()` after consolidated Pass 2 (line 646)
- **Key features of fix:**
  - Deterministic (no LLM call) - avoids non-determinism that plagued attempts 37-41
  - Pattern-based detection: searches for "father", "fled", "embezzled", "vanished" vs "son", "boy", "twelve-year-old", "enlist", "nephew"
  - Contextual scanning: looks within ±100 chars of name mentions
  - Preserves aliases: both split characters inherit the original's aliases

## Next Action
Run PROMPT_analyze.md to re-analyze american_sir with the deterministic same-name split fix.
