# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 35
- **Phase:** awaiting_evaluation
- **baseline_score:** 6.60
- **Competitive Mode:** single (all stages: characters, structure, summaries)

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Pipeline Notes
- Analysis completed in 38m 36s
- 55 LLM calls, 93,344 tokens
- Found 5 characters, 2 chapters, 20 pronunciation flags
- F6 filter rejected "John Donaldson Sr. (the father)" as having 0 text mentions
- Warnings: 3 characters have potentially ungrounded evidence quotes (John Donaldson: 2, Uncle Bill: 3, Ted Frith: 2)
- 1 JSON parse failure (Pronunciation Guide batch enrichment)
- Uncle Bill correctly identified as protagonist with is_narrator: true
- "John Donaldson" is now ONLY the son (aliases: John, the boy, Johnny)
- Father is MISSING entirely from character list (filtered by F6 as hallucination)

## Latest Scores
- Structure Detection: 7/10 ✗
- Character Extraction: 6/10 ✗
  - Completeness: 7/10
  - Identity Resolution: 4/10
  - Alias Grouping: 7/10
- Character Profiles: 6/10 ✗
- Chapter Summaries: 7.5/10 ✗
- Pronunciation Guide: 7/10 ✗
- HTML Presentation: 8/10 ✓
- **Overall: 6.60/10** (reference only)

## Overall Score Calculation

```
Overall = (7 × 0.20) + (6 × 0.25) + (6 × 0.15) + (7.5 × 0.20) + (7 × 0.10) + (8 × 0.10)
        = 1.40 + 1.50 + 0.90 + 1.50 + 0.70 + 0.80
        = 6.80
```

**Overall: 6.80/10** (UP from 6.65 in attempt 33 — modest improvement)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (5 categories below threshold)

## Detailed Evaluation

### 2.1 Structure Detection: 7/10 ✗

Unchanged from previous attempts. "American, Sir" is a continuous short story with no chapter markers. The tool produces 2 sections, both with null titles and null start/end lines. Per the rubric, a continuous text should be identified as a single section (9-10); splitting into 2 sections is a structural error (6-7). Score 7 because the summaries for each section are coherent and usable despite the artificial split.

### 2.2 Character Extraction: 6/10 ✗ (stable from attempt 33 despite significant shifts)

**The adaptive promotion thresholds WORKED — Uncle Bill is back as main_cast_1!**
- `main_cast_1`: **Uncle Bill** — 18 mentions, `is_narrator: true`, `role: protagonist` ✓✓✓
- This was the primary goal of attempt 34 and it succeeded.
- `supporting_0: "Bill"` correctly merged into Uncle Bill with alias "Bill" ✓

**However, father/son FALSELY MERGED — critical regression:**
The identity graph had 3 main_cast nodes: Uncle Bill, John Donaldson (son), and John Donaldson Sr. (father). The merge_groups show `main_cast_2` and `main_cast_3` were merged into a single "John Donaldson" with aliases including "John Donaldson Sr.", "his father", "the father". This is a FALSE MERGE — the father and son are DIFFERENT PEOPLE. The son is the boy who goes to war; the father is the embezzler who faked his death 20 years earlier.

**Character list (6 total, 2 main_cast + 4 supporting):**
- `main_cast_1`: **Uncle Bill** — 18 mentions, `is_narrator: true`, role: `protagonist` ✓✓✓
  - Aliases: ["Bill"] ✓
- `main_cast_2`: **John Donaldson** — 32 mentions, role: `supporting` ✗✗
  - This is father+son merged into one entity — FALSE MERGE
  - Aliases: ["John", "John Donaldson Sr.", "his father", "the father"] — these mix son's and father's references
  - The son should be a separate character from the father
- `supporting_1`: **Joe Barron** — 3 mentions ✓
- `supporting_2`: **Red Cross** — 4 mentions — organization, not character ✗
- `supporting_3`: **Ted Frith** — 5 mentions, alias: "Ted" ✓
- `supporting_5`: **Johnny** — 2 mentions — should be alias of the son ✗

**Sub-Dimension A: Completeness: 7/10** (stable)
- Uncle Bill present and correctly identified as protagonist ✓✓
- Father present but merged with son — effectively one character is "missing" ✗
- "Red Cross" is an organization, not a character ✗
- "Johnny" should be alias, not separate entry ✗
- Margaret Donaldson MISSING from final output — was in identity graph as `main_cast_3` in attempt 33 but now the father took that slot ✗

**Sub-Dimension B: Identity Resolution: 4/10** (DOWN from 5)
- Father/son FALSE MERGE is back — the deterministic same-name constraint from attempt 31 may not be firing, or the identity graph is overriding it ✗✗✗
- Uncle Bill correctly resolved: `main_cast_1` with `supporting_0: "Bill"` merged in ✓
- "Johnny" remains separate instead of being alias of the son ✗
- This is the SAME regression we saw in attempt 30 — the identity graph merges same-name characters despite constraints

**Sub-Dimension C: Alias Grouping: 7/10** (UP from 6)
- Uncle Bill has alias "Bill" ✓ (was ZERO in attempt 33)
- Father's aliases include "John Donaldson Sr.", "his father", "the father" — these are rich and useful ✓
- "John" correctly listed as alias ✓
- BUT these aliases belong to the merged father+son entity, so they're misleading ✗
- "Johnny" still separate instead of alias ✗

### 2.3 Character Profiles: 6/10 ✗ (UP from 5)

**Mixed results — some profiles excellent, some empty:**

- **Uncle Bill**: Profile completely empty — personality summary: "Insufficient information for personality analysis.", no traits, no evidence, no voice guidance. This is the protagonist and narrator; there should be abundant material. The pipeline note says "Profile generation failed for Uncle Bill: None" — this is a pipeline failure, not lack of material.
- **John Donaldson (merged father+son)**: Excellent profile — personality summary captures moral ambiguity and redemption arc, traits are insightful ("cowardly in the face of accountability", "deeply remorseful"), evidence quotes are accurate and well-chosen. Voice guidance is outstanding with "American, sir" verbal tic, dialect notes, emotional range. BUT this profile is entirely about the FATHER, ignoring the son entirely — which makes sense since they're falsely merged.
- **Ted Frith**: Has a profile with personality and voice guidance. However:
  - Evidence quote `"'This is my good day. I'm American to-day, sir!'"` is the FATHER's line, not Ted's ✗
  - Other evidence looks plausible: `"That you, Johnny?' he shouted"` could be Ted's
  - Personality description is somewhat generic ("heroic", "selfless") but not inaccurate
- **Joe Barron, Red Cross, Johnny**: All null profiles — expected for minor/invalid characters

**Why 6/10:** The father's profile is excellent (would score 9/10 alone), but Uncle Bill's complete profile failure drags this down significantly. The protagonist/narrator having "Insufficient information" is a major gap. Ted's contaminated quote is a recurring issue. UP from 5 because the father's profile data is present (attempt 33 falsely reported all profiles empty — it was a field path mismatch).

### 2.4 Chapter Summaries: 7.5/10 ✗ (stable)

**Section 1:** EXCELLENT. Correctly describes the cousin relationship, the narrator's background, Margaret Donaldson, the scandal and death. `characters_present`: not checked but section 1 quality is strong.

**Section 2:** Good quality but the recurring hallucination persists:
- "his deceased sister's son" — WRONG. Uncle Bill is the father's COUSIN, not sibling. Section 1 correctly says "cousin."
- Otherwise excellent: covers Yale, fishing trip, WWI, Caporetto, reunion, deathbed revelation.
- Excellent detail on the wartime narrative and the father's identity revelation.

**Why 7.5/10:** The "sister" factual error in section 2 prevents a higher score. Otherwise both summaries are comprehensive, well-written, and useful for narrators.

### 2.5 Pronunciation Guide: 7/10 ✗ (stable)

20 entries, 15 with IPA.

**Genuinely useful foreign terms (8):** Caporetto, Piave, Solferino, Guerre, Venetia, Tagliamento, Bersagliari, Bordeaux — excellent ✓

**Acceptable homographs (5):** live, minute, read, close, moderate — context-dependent, genuinely useful ✓

**False positives (7):**
- Common English words: whippersnapper, thriftless, thickset, manliness — uncommon but not pronunciation challenges ✗
- Military/medical terms: dum-dums, orderlies — standard pronunciation ✗
- Archaic contraction: mayn't — borderline ✗

**Why 7/10:** 7/20 entries (35%) are false positives. The core foreign terms and homographs are excellent, but the false positives drag the score down.

### 2.6 HTML Presentation: 8/10 ✓

Navigation works, character profiles render well. Uncle Bill correctly displayed as protagonist and narrator. Voice guidance sections display for characters that have them. Minor: "Red Cross" and "Johnny" in Supporting Characters. Father/son merged into one entry — this reflects the upstream character extraction issue.

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (user-configured, appropriate)
- Pipeline: V2 with Phase 2 graph-based identity resolution
- 0 LLM retries — good
- 1 JSON parse failure (Pronunciation Guide and Character Profiles stages)
- Character Profiles: 8 LLM calls, 28396 tokens, 549s — but Uncle Bill profile failed
- Identity graph has 2 constraint edges but father/son still merged — constraint not strong enough

## Current Issues (Priority Order)

### CRITICAL

1. **Father/son FALSE MERGE — "John Donaldson" and "John Donaldson Sr." merged** [Identity Resolution]
   - Problem: The identity graph had `main_cast_2` (son, 28 mentions) and `main_cast_3` (father/Sr., 13 mentions) as separate nodes. The merge_groups show they were MERGED into a single "John Donaldson" entity. The father and son are completely different people — the son is the boy who grows up, goes to Yale, serves in WWI; the father is the embezzler who faked his death 20 years earlier and dies in Italy.
   - Evidence: `merge_groups[1]` shows `members: ["main_cast_2", "main_cast_3"]` with canonical name "John Donaldson". The identity graph stats show 2 constraint edges but they didn't prevent this merge.
   - Location: `src/pipeline/character_extraction_v2/evidence_collectors.py` — the deterministic same-name constraint added in attempt 31 may not be firing in Phase 2. Also check `src/pipeline/character_extraction_v2/identity_graph.py` (or wherever merge decisions are made).
   - Fix approach: The constraint from attempt 31 was in `evidence_collectors.py`. Verify it's still active. The identity graph has 2 constraint edges — check if they're blocking the right merge. The merge happened despite constraints, suggesting the merge evidence (3 pieces) outweighed the constraint. Need to make the same-name constraint HARD (absolute block) rather than weighted.
   - **IMPORTANT:** This same issue was fixed in attempt 31 and regressed in attempt 30. The fix was a deterministic check in `evidence_collectors.py`. It may have broken when the identity graph was introduced.

2. **Uncle Bill profile generation failed** [Profiles]
   - Problem: Uncle Bill's personality is "Insufficient information for personality analysis" with no traits, evidence, or voice guidance. He's the first-person narrator — there should be plenty of material.
   - Evidence: Pipeline warning: "Profile generation failed for Uncle Bill: None". The profiling stage ran (8 LLM calls) but failed for Uncle Bill specifically.
   - Location: `src/pipeline/character_profiling/` — likely the passage gatherer or profile generator fails for first-person narrators because the narrator refers to themselves as "I" rather than by name.
   - Fix approach: For first-person narrators, the profile pipeline needs to use first-person passages ("I felt...", "I drove...") rather than searching for the character name. Check if `is_narrator: true` is being used to adjust passage gathering.

### HIGH

3. **Ted Frith profile contaminated with father's quotes** [Profiles]
   - Problem: Ted's evidence includes `"'This is my good day. I'm American to-day, sir!'"` — this is John Donaldson (the father)'s iconic line, not Ted's.
   - Evidence: The "American, sir" verbal tic belongs exclusively to the father throughout the story.
   - Location: `src/pipeline/character_profiling/` — passage gathering or evidence extraction assigns nearby dialogue to wrong character.
   - Fix approach: Name disambiguation in the profiling pipeline needs to recognize that when "American, sir" is spoken, the speaker is always the father (John Donaldson), not whoever is nearby.

4. **Summary "sister" hallucination persists** [Summaries]
   - Problem: Section 2 says "his deceased sister's son" — Uncle Bill is the father's COUSIN, not sibling. Section 1 correctly says "cousin."
   - Evidence: LLM is hallucinating the family relationship despite the text clearly stating "cousin."
   - Location: LLM generation in summary pipeline. Non-deterministic — the model sometimes gets this wrong.

### MEDIUM

5. **"Johnny" still a separate character instead of alias of the son** [Alias Grouping]
   - Problem: Johnny (supporting_5, 2 mentions) should be an alias of John Donaldson (the son), not a separate character.
   - Location: Identity graph merge logic — nickname matching not connecting "Johnny" to "John Donaldson".

6. **Pronunciation: 7/20 false positives (35%)** [Pronunciation]
   - Remaining false positives: whippersnapper, thriftless, thickset, manliness, dum-dums, orderlies, mayn't.

7. **Structure: 2 sections for continuous short story** [Structure]
   - Same as all prior attempts. Not worth a targeted fix for this text alone.

8. **"Red Cross" extracted as character** [Completeness]
   - Organization, not a character (supporting_2, 4 mentions).

9. **Margaret Donaldson missing from final character list** [Completeness]
   - Was in the identity graph but may have been dropped during reconciliation. Only has 2 mentions so may be below threshold.

### LOW

10. **Section 1 `characters_present` only shows "Narrator"** — should list named characters

## Fix Priority

**Attempt 34 was a PARTIAL SUCCESS.** The adaptive promotion thresholds worked perfectly — Uncle Bill is back as protagonist and narrator. But the father/son merge regressed, which is the same issue that was fixed in attempt 31.

**Root cause analysis:** The identity graph is merging `main_cast_2` (John Donaldson / son) and `main_cast_3` (John Donaldson Sr. / father) despite there being 2 constraint edges. The merge evidence (3 pieces) is outweighing the constraints. The deterministic same-name check from attempt 31 in `evidence_collectors.py` needs to produce a HARD constraint that cannot be overridden.

**Recommended fix order:**
1. **CRITICAL #1: Father/son false merge** — Make the same-name constraint HARD/absolute in the identity graph. Characters with the same base name but different generational markers (Sr./Jr., "the father"/"the son") MUST NOT be merged. This was working in attempts 31-32 but regressed.
2. **CRITICAL #2: Uncle Bill profile** — Investigate why profile generation fails for first-person narrators. The passage gatherer may need special handling for `is_narrator: true` characters.
3. HIGH #3 (Ted Frith contamination) and HIGH #4 (sister hallucination) are secondary.

## Fix History

### Attempt 35 — Make ROLE_CONFLICT constraint HARD (strength 1.0)
- **Issue targeted:** CRITICAL #1 — Father/son false merge (regression from attempt 31)
- **Root cause:** `ROLE_CONFLICT` constraint strength was 0.9, allowing merge evidence weight > 0.9 to override it
- **Changes made:**
  1. Changed `ROLE_CONFLICT` constraint strength from 0.9 to 1.0 in `identity_graph.py` line 83
  2. This makes it a HARD constraint that cannot be overridden by merge evidence
  3. The deterministic same-name check in `evidence_collectors.py` (lines 1033-1040) already creates this constraint
- **Result:** TBD - awaiting analysis
- **Files modified:**
  - `src/pipeline/character_extraction_v2/identity_graph.py` (line 83)
- **Test results:** All 38 identity graph unit tests pass, including `test_father_son_same_name_not_merged`


### Attempt 34 — Adaptive promotion thresholds (length-scaled) — PARTIAL SUCCESS
- **Issues targeted:**
  1. CRITICAL #1 — Uncle Bill demoted from main_cast to supporting
  2. CRITICAL #2 — Profile data loss (FALSE ALARM in attempt 33 — data existed at `personality.summary` not `personality_summary`)
- **Changes made:**
  1. Added `adaptive_promotion_thresholds(word_count)` function to `src/agents/characters.py`
  2. Updated Step 5.8 promotion logic to use adaptive thresholds instead of hardcoded values
  3. Thresholds scale with text length: ≤10K → 15/10/8; 10K-50K → 50/30/20; >50K → 200/100/50
- **Result:** PARTIAL SUCCESS — Uncle Bill restored to main_cast as protagonist/narrator ✓. BUT father/son falsely merged ✗. Uncle Bill profile still empty ✗. Score: 6.65 → 6.80 (+0.15)
- **Files modified:**
  - `src/agents/characters.py` (lines 47-75, 457-479)

### Attempt 33 — Possessive stripping in supporting cast + deterministic narrator detection
- **Issues targeted:**
  1. HIGH #1 — Uncle Bill narrator/protagonist regression
  2. HIGH #2 — Alias fix from attempt 32 didn't work (possessive + Johnny)
- **Changes made:**
  1. Added `_strip_possessive()` method to `supporting.py` (same logic as main_cast.py)
  2. Applied possessive stripping to NER entity names at extraction time
  3. Added deterministic fallback in `narrator.py`
- **Result:** MIXED — Possessive stripping worked (John Donaldson's gone), BUT Uncle Bill demoted from main_cast to supporting. ALL profiles now empty. Score: 7.28 → 6.65 (-0.63). **Net negative.**
- **Files modified:**
  - `src/pipeline/character_extraction_v2/supporting.py`
  - `src/pipeline/character_extraction_v2/narrator.py`

### Attempt 32 — Alias cleanup (possessive stripping + nickname matching) — DID NOT WORK
- **Issue targeted:** HIGH #1 from attempt 31 — Alias grouping below threshold (6.5/10)
- **Changes made:**
  1. Added `COMMON_NICKNAMES` entries in `evidence_collectors.py`
  2. Added `_strip_possessive()` helper function to `main_cast.py`
  3. Applied `_strip_possessive()` to all alias assignment locations in `main_cast.py`
- **Result:** NO EFFECT — possessive still present, Johnny still separate character
- **Additional regression:** Uncle Bill lost `is_narrator: true` and `role: protagonist`
- **Score impact:** 7.33 → 7.28 (-0.05)

### Attempt 31 — Deterministic same-name constraint (SUCCESS!)
- **Issue targeted:** CRITICAL #1 — Father/son merged (regression from attempt 29)
- **Changes made:** Added deterministic check in `evidence_collectors.py`
- **Result:** SUCCESS — Father/son split restored, Uncle Bill promoted to protagonist
- **Score impact:** 6.78 → 7.33 (+0.55)
- **File modified:** `src/pipeline/character_extraction_v2/evidence_collectors.py`

### Attempt 30 — Pronunciation false positive reduction (PARTIAL SUCCESS + REGRESSION)
- Score: 6.78

### Attempt 29 — Disambiguation labels via post-processing (SUCCESS!)
- Score: 7.13

### Previous attempts — see earlier evaluation states

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 35 | ROLE_CONFLICT hard constraint | `identity_graph.py` | TBD — awaiting analysis |
| 34 | Adaptive promotion thresholds | `characters.py` | PARTIAL SUCCESS — Uncle Bill restored to main_cast, but father/son merged. Score: 6.65→6.80 |
| 33 | Possessive stripping + narrator detection | `supporting.py`, `narrator.py` | MIXED — possessive fixed, Uncle Bill demoted to supporting, profiles empty. Score: 6.65 (-0.63) |
| 32 | Alias cleanup (possessive + nicknames) | `evidence_collectors.py`, `main_cast.py` | NO EFFECT — aliases unchanged, narrator regression |
| 31 | Deterministic same-name constraint | `evidence_collectors.py` | SUCCESS — father/son split restored, score 6.78→7.33 |
| 30 | Pronunciation false positives | `character_proposer.py`, `foreign_proposer.py` | Pronunciation improved (5→7), BUT character regression |
| 29 | Disambiguation labels post-processing | `characters.py` | SUCCESS — labels applied, score 7.13 |
| 28 | Revert to attempt 25 (undo regression) | `characters.py` | SUCCESS — main_cast restored |
| 27 | Revert + re-implement disambiguation labels | `characters.py` | WORSE REGRESSION — main_cast_count: 0 |
| 26 | Disambiguation labels for same-name characters | `characters.py` | REGRESSION — main_cast_2 dropped |
| 25 | Father/son disambiguation (data flow fix) | `characters.py` | SUCCESS — split works but identical names |
| 24 | Father/son disambiguation | `evidence_collectors.py`, `characters.py` | NO EFFECT |
| 23 (baseline) | Clean baseline + Phase 2 pipeline | N/A | Score: 6.30 |

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.60 | — | Original baseline |
| 22 | 7.55 | +0.95 | Best score (all fixes active) |
| 23 | 6.30 | -0.30 | Clean baseline + Phase 2 pipeline |
| 24 | 6.15 | -0.45 | Fix had no effect; profiles worse |
| 25 | 6.50 | -0.10 | Father/son split working but needs labels |
| 26 | 6.40 | -0.20 | REGRESSION — labels dropped main_cast_2 |
| 27 | 5.75 | -0.85 | WORSE REGRESSION — main_cast pipeline broken |
| 28 | 6.65 | +0.05 | Revert successful — main_cast restored |
| 29 | 7.13 | +0.53 | Disambiguation labels SUCCESS |
| 30 | 6.78 | +0.18 | Pronunciation improved but father/son merge regression |
| 31 | 7.33 | +0.73 | Deterministic same-name fix SUCCESS — highest since attempt 22 |
| 32 | 7.28 | +0.68 | Alias fix NO EFFECT, Uncle Bill narrator regression, profiles improved |
| 33 | 6.65 | +0.05 | Possessive fix worked, BUT Uncle Bill demoted, profiles empty |
| 34 | 6.80 | +0.20 | Uncle Bill restored ✓, father/son merged ✗, profile still empty |

## Next Action

**Phase:** awaiting_analysis

Re-run analysis to verify that father and son are now correctly split into separate characters.

**Expected outcome:**
- `main_cast_2`: John Donaldson (son) — should have aliases like "John", "Johnny" but NOT "John Donaldson Sr.", "the father"
- `main_cast_3`: John Donaldson Sr. (father) — should have aliases like "his father", "the father", "John Donaldson Sr."
- The ROLE_CONFLICT constraint (now strength 1.0) should prevent these from merging

**Secondary issue (CRITICAL #2):** Uncle Bill profile still empty. If father/son fix works, this becomes the next priority.

