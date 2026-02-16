# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 31
- **Phase:** awaiting_evaluation
- **baseline_score:** 6.60
- **Competitive Mode:** single (all stages: characters, structure, summaries)

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json
- Timestamped: ../output/American Sir_20260215_182917/

## Pipeline Notes
- Analysis completed in 98m 35s (completed at 18:29)
- Competitive consensus ENABLED for characters, structure, summaries stages
- 60 LLM calls, 95,986 tokens
- Found 8 characters (4 main_cast + 4 supporting), 2 chapters, 21 pronunciation flags
- Profiling: Chapter Detection (23.5% of time, bottleneck)
- Narrator detection: Uncle Bill (first-person)

## Latest Scores
- Structure Detection: 7/10 ✗
- Character Extraction: 5.5/10 ✗
  - Completeness: 7/10
  - Identity Resolution: 4/10
  - Alias Grouping: 6/10
- Character Profiles: 7/10 ✗
- Chapter Summaries: 7.5/10 ✗
- Pronunciation Guide: 7/10 ✗
- HTML Presentation: 7.5/10 ✗
- **Overall: 6.58/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (6 categories below threshold) — REGRESSION from attempt 29

## Overall Score Calculation

```
Overall = (7 × 0.20) + (5.5 × 0.25) + (7 × 0.15) + (7.5 × 0.20) + (7 × 0.10) + (7.5 × 0.10)
        = 1.40 + 1.375 + 1.05 + 1.50 + 0.70 + 0.75
        = 6.775
```

**Overall: 6.78/10** (DOWN from 7.13 in attempt 29 — REGRESSION)

## Detailed Evaluation

### 2.1 Structure Detection: 7/10 ✗

Unchanged from previous attempts. "American, Sir" is a continuous short story with no chapter markers. The tool produces 2 sections, both with null titles and null start/end lines. Per the rubric, a continuous text should be identified as a single section (9-10); splitting into 2 sections is a structural error (6-7). Score 7 because the summaries for each section are coherent and usable despite the artificial split.

### 2.2 Character Extraction: 5.5/10 ✗ (DOWN from 7.5 — MAJOR REGRESSION)

**CRITICAL REGRESSION: Father/Son Merge.** Attempt 29 had two separate John Donaldsons with disambiguation labels "(the son)" and "(the father)". This run merged them into a single "John Donaldson" entry. The core CRITICAL fix from attempt 29 has been UNDONE by this re-analysis.

**Character list (7 total, 2 main_cast + 5 supporting):**
- `main_cast_1`: **John Donaldson** — 28 mentions, `is_narrator: true`, role: `supporting` — MERGED father+son ✗✗
- `main_cast_3`: **Margaret Donaldson** — 2 mentions, role: `supporting` ✓
- `supporting_1`: **Uncle Bill** — 18 mentions, role: `minor` — should be protagonist ✗
- `supporting_3`: **Joe Barron** — 3 mentions ✓
- `supporting_4`: **Red Cross** — 4 mentions — organization, not character ✗
- `supporting_6`: **Ted Frith** — 5 mentions, alias: "Ted" ✓
- `supporting_8`: **Johnny** — 2 mentions — should be alias of the son ✗

**Root cause of regression:** The identity graph shows main_cast_1 and main_cast_2 as separate nodes, but the `role_conflict` constraint edge that existed in attempt 29 is MISSING. Without it, the co-occurrence score of 1.00 between them caused the merge. The constraint edges only show `different_first_names` (for Margaret) and `ambiguous_surname` (for "John" → both Donaldsons). The `role_conflict` edge that protected the father/son split is gone.

**Sub-Dimension A: Completeness: 7/10** (DOWN from 8)
- Uncle Bill present but demoted to `minor` role instead of protagonist ✗
- Margaret Donaldson present ✓
- "Red Cross" is an organization, not a character ✗
- Father/son merge means the son effectively disappears as a distinct character ✗
- Joe Barron, Ted Frith present ✓

**Sub-Dimension B: Identity Resolution: 4/10** (DOWN from 7.5)
- **Father/son merged into single entry** ✗✗ — this is the most important identity resolution task for this text and it REGRESSED
- The merged character has the father's personality/voice but is marked `is_narrator: true` (which applies to the son's role as nested narrator)
- The profile conflates father and son attributes into one entry
- "Johnny" remains separate instead of being an alias of the son ✗

**Sub-Dimension C: Alias Grouping: 6/10** (DOWN from 7)
- "John Donaldson's" (possessive) still appears as alias ✗
- "Johnny" separate instead of alias ✗
- "Ted" → Ted Frith: correct ✓
- "Bill" → Uncle Bill: correct ✓
- With father/son merged, alias grouping is moot for the primary characters — the merge itself is wrong

### 2.3 Character Profiles: 7/10 ✗ (stable from attempt 29)

**John Donaldson (main_cast_1 — merged father+son): CONFUSED**
- The personality description is entirely about the FATHER ("morally ambiguous man who committed grave betrayals by stealing entrusted money and faking his death")
- But `is_narrator: true` — which is the SON's attribute
- The profile describes one coherent character (the father) but the metadata claims it's also the narrator (the son)
- Relationships: "John Donaldson (son): parent", "Uncle Bill: acquaintance", "Margaret Donaldson: spouse" — these are the FATHER's relationships, correctly attributed to the father, but the merged entry creates confusion
- Physical description: null ✗ (both father and son have textual descriptions)

**Uncle Bill (supporting_1): EXCELLENT ✓**
- Personality: "morally ambiguous man who abandoned his son" — WAIT, this is WRONG. Uncle Bill did NOT abandon his son. He has no son. He's describing the FATHER's behavior. The profile has contaminated Uncle Bill with the father's story.
- Actually reading more carefully: "A morally ambiguous man who abandoned his son through deceit and neglect, yet became a steadfast, protective guardian to his nephew" — This conflates uncle and father. Uncle Bill never abandoned anyone; the FATHER abandoned his son. Uncle Bill TOOK IN his cousin's orphaned son.
- Voice guidance: excellent quality ✓
- Relationships: "John Donaldson (nephew): mentor", "John Donaldson (father): victimizer" — "victimizer" is WRONG. Uncle Bill was not victimized by the father; if anything, the father was estranged from everyone.

**Margaret Donaldson: no profile data** (expected — minor character)

**Why 7/10:** Father's profile quality is individually good (voice guidance, evidence quotes) but it's contaminated by the merge with the son. Uncle Bill's profile has factual errors (claiming he "abandoned his son" when he has no son; labeling the father as "victimizer"). The merged character entry creates confusion about who is being described.

### 2.4 Chapter Summaries: 7.5/10 ✗ (stable)

**Section 1:** EXCELLENT. Correctly describes Uncle Bill's background, the letter from young John, the cousin relationship, the scandal, Margaret Donaldson. Uses "cousin" correctly. `characters_present`: ["Narrator"] — acceptable but could include named characters.

**Section 2:** Good quality but contains the recurring "sister" hallucination:
- "his deceased sister's twelve-year-old son" — WRONG. Uncle Bill is the father's COUSIN, not brother/sister. The section 1 summary correctly says "cousin."
- "his late brother" — WRONG. Same error — treats them as siblings instead of cousins.
- Otherwise excellent: covers Yale, fishing trip, WWI, Caporetto, reunion, deathbed revelation.
- `characters_present`: ["Uncle Bill", "John Donaldson"] — only one John Donaldson now (was disambiguated in attempt 29)

**Why 7.5/10:** Two factual errors ("sister" and "brother" instead of "cousin" in section 2) in otherwise excellent summaries. The loss of disambiguated names in `characters_present` is a minor regression from attempt 29.

### 2.5 Pronunciation Guide: 7/10 ✗ (UP from 5 — SIGNIFICANT IMPROVEMENT)

20 entries, 15 with IPA.

**Genuinely useful foreign terms (8):** Caporetto, Piave, Solferino, Guerre, Venetia, Tagliamento, Bersagliari, Bordeaux — excellent for narrators ✓

**Acceptable homographs (5):** live, minute, read, close, moderate — context-dependent pronunciation, genuinely useful ✓

**False positives (7):**
- Common English words: whippersnapper, thriftless, thickset, manliness — these are uncommon but not pronunciation challenges ✗
- Military/medical terms: dum-dums, orderlies — standard pronunciation ✗
- Archaic contraction: mayn't — arguably useful, borderline ✗

**What improved:** Character names (Bill, Donaldson, Cross, Ted, Joe, Barron, Frith, Johnny) and "was" are ALL gone. The CMU dictionary check and ENGLISH_EXCEPTIONS fix worked. False positives dropped from 17/31 (55%) to 7/20 (35%).

**Why 7/10 (not 8):** 7/20 entries (35%) are still false positives. The threshold for 8/10 is "few false positives" — 35% is still noticeable. However, the remaining false positives are harder to fix generically (they're uncommon-but-real English words, not obvious common words like "was" or "Bill").

### 2.6 HTML Presentation: 7.5/10 ✗ (DOWN from 8)

**Why downgraded from 8:**
1. **Disambiguation labels GONE.** Attempt 29 showed "John Donaldson (the son)" and "John Donaldson (the father)" — this attempt shows just "John Donaldson" as a single merged entry. The HTML correctly renders the data, but the data is worse.
2. Uncle Bill demoted to "Supporting Characters" section instead of Main Characters
3. Only 2 entries in Main Characters (John Donaldson, Margaret Donaldson)
4. "Red Cross" and "Johnny" still listed as supporting characters
5. Section 1 `characters_present` shows only "Narrator" — not useful

**What still works:**
- Profile data renders well for available characters
- Voice guidance section functional
- Navigation works
- "John Donaldson's" (possessive) shown as alias ✗

**Why 7.5/10:** The regression of the father/son merge means the HTML shows a confusing single entry that conflates two characters. The HTML renderer isn't broken — the upstream data is wrong.

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (user-configured, appropriate)
- Pipeline: V2 with Phase 2 graph-based identity resolution
- Identity graph: constraint edges present but MISSING `role_conflict` between main_cast_1 and main_cast_2
- main_cast_count: 2 (DOWN from 4 in attempt 29 — regression)
- supporting_cast_count: 5
- 0 LLM retries — good
- 1 JSON parse failure in Pronunciation Guide stage
- No config changes recommended
- Profiling: 5 stages, all successful
- **KEY OBSERVATION:** The `role_conflict` constraint edge that protected the father/son split in attempt 29 was NOT generated this time. This is likely LLM non-determinism — the same code with the same text can produce different constraint edges depending on the model's output.

## Current Issues (Priority Order)

### CRITICAL

1. **Father/son merged into single "John Donaldson" entry — REGRESSION from attempt 29** [Identity Resolution]
   - Problem: Attempt 29 had two separate entries with disambiguation labels "(the son)" and "(the father)". This attempt merged them into one entry with 28 mentions, conflating father and son attributes.
   - Evidence: Identity graph still shows main_cast_1 and main_cast_2 as separate nodes, but the `role_conflict` constraint edge from attempt 29 is MISSING. Co-occurrence score of 1.00 caused the merge.
   - Root cause: The `role_conflict` constraint edge generation is non-deterministic — it depends on the LLM correctly identifying conflicting roles. When the LLM doesn't flag the conflict, the identical names + high co-occurrence = merge.
   - Location: `src/agents/characters.py` — the `_apply_disambiguation_labels_from_constraints()` post-processing from attempt 29 is still present, but it has nothing to work with because the upstream constraint edge wasn't generated.
   - Fix approach: The disambiguation labels post-processing (attempt 29's fix) worked perfectly WHEN the constraint edge existed. The fix should be to make the father/son detection more robust — either:
     a. Add a deterministic check: if two main_cast entries have IDENTICAL names, automatically add a `role_conflict` constraint edge (don't rely on LLM to flag it)
     b. In the post-processing step, check for identically-named main_cast entries even without constraint edges and force a split
   - **This is the SAME issue from attempts 25-29, manifesting differently each time. The core problem is that same-name detection relies on LLM non-deterministic output.**

### HIGH

2. **Uncle Bill demoted to supporting cast with role "minor"** [Completeness]
   - Problem: Uncle Bill is the first-person narrator and primary character. He should be `main_cast` with role `protagonist`. Instead he's `supporting_1` with role `minor`.
   - Evidence: The pipeline metadata shows `narrator_name: "Narrator (Uncle Bill)"` — it correctly identifies Uncle Bill as narrator but doesn't promote him to main_cast.
   - Location: `src/agents/characters.py` or `src/pipeline/character_extraction_v2/` — narrator identification doesn't feed back into cast classification
   - Note: This was also present in attempt 29 but scored less impactful because the father/son split was working

3. **"Red Cross" extracted as character** [Completeness]
   - Problem: Organization, not a character (`supporting_4`, 4 mentions). Same as all prior attempts.
   - Location: `src/pipeline/character_extraction_v2/supporting.py`

4. **Summary "sister"/"brother" hallucination in section 2** [Summaries]
   - Problem: Section 2 says "his deceased sister's twelve-year-old son" and "his late brother" — Uncle Bill is the father's COUSIN, not sibling.
   - Section 1 correctly says "cousin" — the LLM is hallucinating in section 2.
   - Location: LLM generation in summary pipeline

### MEDIUM

5. **Pronunciation: 7/20 false positives (35%)** [Pronunciation]
   - Remaining false positives: whippersnapper, thriftless, thickset, manliness, dum-dums, orderlies, mayn't
   - These are uncommon but pronounceable English words, harder to filter than common names/words
   - The CMU dictionary fix successfully removed character names and "was" — good progress
   - Location: `src/pipeline/pronunciation_guide/proposers/`

6. **"Johnny" separate instead of alias of the son** [Alias Grouping]
   - Problem: "Johnny" (`supporting_8`, 2 mentions) should be an alias of "John Donaldson" (the son specifically)
   - With the father/son merge, this is moot — but if/when the split is restored, Johnny should be grouped with the son

7. **"John Donaldson's" (possessive) is an invalid alias** [Alias Grouping]
   - Same as all prior attempts. Possessive forms should be stripped.

8. **Uncle Bill's profile says he "abandoned his son"** [Profiles]
   - Problem: Uncle Bill has no son. The profile conflates him with the FATHER (John Donaldson Sr.). Uncle Bill is the cousin who TOOK IN the orphaned son.
   - This may be caused by the father/son merge contaminating other profiles

9. **Uncle Bill's relationship to father labeled "victimizer"** [Profiles]
   - Problem: Should be "family/cousin" — they are cousins. The father didn't victimize Uncle Bill.

### LOW

10. **Structure: 2 sections for continuous short story** [Structure]
    - Same as all prior attempts. Not worth a targeted fix for this text alone.

11. **Section 1 `characters_present` only shows "Narrator"** — should list named characters appearing in that section

## Fix Priority

**CRITICAL REGRESSION requires immediate fix.** The pronunciation improvement (5→7) is real progress, but the father/son merge regression (7.5→4 on Identity Resolution) more than offsets it.

**Recommended fix:** Make same-name detection DETERMINISTIC rather than relying on LLM-generated constraint edges:
1. In `src/agents/characters.py`, add a deterministic check: if two main_cast entries have identical `canonical_name`, ALWAYS add a `role_conflict` constraint edge — don't wait for the LLM to flag it
2. This ensures the `_apply_disambiguation_labels_from_constraints()` post-processing from attempt 29 always has constraint edges to work with
3. This is a ~5-line fix in the identity graph construction code

**After that fix stabilizes the father/son split, THEN address:**
- Pronunciation remaining false positives (7→8 needed, small gap)
- Son's empty profile (same issue as attempt 29)
- Summary hallucination

## Fix History

### Attempt 31 — Deterministic same-name constraint (FIX FOR REGRESSION)
- **Issue targeted:** CRITICAL #1 — Father/son merged (regression from attempt 29)
- **Root cause:** `collect_constraint_evidence()` relied on LLM-populated `descriptions` field to detect role conflicts. When descriptions are empty (LLM non-determinism), no `role_conflict` edge is created, allowing high co-occurrence to merge same-name characters.
- **Changes made:** Added deterministic check in `evidence_collectors.py:collect_constraint_evidence()` (lines 1027-1036)
  - If two main_cast characters have **identical canonical_name** → automatically add `role_conflict` constraint edge
  - This makes same-name detection **universal and deterministic** (no dependency on LLM output)
  - Preserves existing description-based detection as fallback
- **Expected result:** Father/son split restored with disambiguation labels from attempt 29's post-processing
- **File modified:** `src/pipeline/character_extraction_v2/evidence_collectors.py`

### Attempt 30 — Pronunciation false positive reduction (PARTIAL SUCCESS + REGRESSION)
- **Issue targeted:** HIGH #3 — Pronunciation: 17/31 entries are false positives (~55%)
- **Changes made:**
  1. `character_proposer.py`: CMU dictionary safety check, better logging
  2. `foreign_proposer.py`: Added "was", "were", "been", "being" to ENGLISH_EXCEPTIONS
- **Pronunciation result:** SUCCESS — false positives reduced from 17/31 (55%) to 7/20 (35%), score 5→7
- **Character regression:** REGRESSION — father/son split lost due to missing `role_conflict` constraint edge (LLM non-determinism). Score 7.5→5.5 on Character Extraction.
- **Net result:** Overall score DOWN from 7.13 to 6.78 due to character regression
- **Files modified:** `character_proposer.py`, `foreign_proposer.py`

### Attempt 29 — Disambiguation labels via post-processing (SUCCESS!)
- **Issue targeted:** CRITICAL #1 — Both John Donaldson entries have identical names with no disambiguation labels
- **Changes made:** Added `_apply_disambiguation_labels_from_constraints()` as Step 5.11 in `run()` method
- **Result:** SUCCESS — Labels applied correctly: "John Donaldson (the son)" and "John Donaldson (the father)"
- **Score:** 7.13 (UP from 6.65)
- **File modified:** `src/agents/characters.py`
- **Why this succeeded where attempts 26-27 failed:** POST-PROCESSING ONLY — runs after ALL character extraction/merging is complete, only modifies `canonical_name` field

### Attempt 28 — Revert to attempt 25 state (REVERT SUCCESSFUL)
- **Issue targeted:** CRITICAL #1 from attempt 27 — main_cast pipeline produced ZERO characters
- **Changes made:** Reverted `src/agents/characters.py` to attempt 25 state
- **Result:** SUCCESS — main_cast pipeline restored. 3 main_cast characters extracted.
- **Score:** 6.65
- **File modified:** `src/agents/characters.py`

### Attempt 27 — Revert + re-implement disambiguation labels (MAJOR REGRESSION)
- **Issue targeted:** CRITICAL #1 from attempt 26
- **Result:** WORSE REGRESSION — main_cast_count: 0
- **Score:** 5.75
- **File modified:** `src/agents/characters.py`

### Attempt 26 — Apply disambiguation labels (REGRESSION)
- **Issue targeted:** Two identical "John Donaldson" entries
- **Result:** REGRESSION — main_cast_2 dropped
- **Score:** 6.40
- **File modified:** `src/agents/characters.py`

### Previous attempts — see earlier evaluation states

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 31 | Father/son merge regression (deterministic fix) | `evidence_collectors.py` | Awaiting analysis |
| 30 | Pronunciation false positives | `character_proposer.py`, `foreign_proposer.py` | Pronunciation improved (5→7), BUT character regression (father/son merged) |
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

## Next Action

Re-run analysis to verify the deterministic same-name constraint fix. Expected outcomes:
1. Identity graph should contain `role_conflict` edge between main_cast_1 and main_cast_2
2. Father/son should remain as 2 separate characters (not merged)
3. Disambiguation labels should be applied: "John Donaldson (the son)" and "John Donaldson (the father)"
4. Pronunciation improvements from attempt 30 should remain (7/10)
