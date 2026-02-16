# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 33
- **Phase:** awaiting_fix
- **baseline_score:** 6.60
- **Competitive Mode:** single (all stages: characters, structure, summaries)

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Pipeline Notes
- Analysis completed in 38m 7s
- 68 LLM calls, 108,910 tokens
- Found 8 characters, 2 chapters, 20 pronunciation flags
- 1 JSON parse failure (Pronunciation Guide batch enrichment)
- ALL character profiles are now empty (null personality, null traits, null evidence_quotes) — MASSIVE REGRESSION from attempt 32

## Latest Scores
- Structure Detection: 7/10 ✗
- Character Extraction: 6/10 ✗
  - Completeness: 7/10
  - Identity Resolution: 5/10
  - Alias Grouping: 6/10
- Character Profiles: 5/10 ✗
- Chapter Summaries: 7.5/10 ✗
- Pronunciation Guide: 7/10 ✗
- HTML Presentation: 8/10 ✓
- **Overall: 6.55/10** (reference only)

## Overall Score Calculation

```
Overall = (7 × 0.20) + (6 × 0.25) + (5 × 0.15) + (7.5 × 0.20) + (7 × 0.10) + (8 × 0.10)
        = 1.40 + 1.50 + 0.75 + 1.50 + 0.70 + 0.80
        = 6.65
```

**Overall: 6.65/10** (DOWN from 7.28 in attempt 32 — significant regression)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (5 categories below threshold)

## Detailed Evaluation

### 2.1 Structure Detection: 7/10 ✗

Unchanged from previous attempts. "American, Sir" is a continuous short story with no chapter markers. The tool produces 2 sections, both with null titles and null start/end lines. Per the rubric, a continuous text should be identified as a single section (9-10); splitting into 2 sections is a structural error (6-7). Score 7 because the summaries for each section are coherent and usable despite the artificial split.

### 2.2 Character Extraction: 6/10 ✗ (DOWN from 7 — regression)

**Uncle Bill has been DEMOTED from main_cast to supporting_cast.** He was `main_cast_3` ("Uncle Bill") in attempt 32. Now he's `supporting_1` ("Bill") with `role: minor`. This is a catastrophic regression — the protagonist and narrator of the story is classified as a minor supporting character.

**Character list (8 total, 3 main_cast + 5 supporting):**
- `main_cast_1`: **John Donaldson (the son)** — 28 mentions, `is_narrator: true`, role: `supporting`
  - `is_narrator: true` is correct for nested narration ✓
  - Aliases: ["John"] — improved from NONE in attempt 32 ✓, but still missing "Johnny" ✗
- `main_cast_2`: **John Donaldson (the father)** — 23 mentions, role: `supporting`
  - Aliases: ["father"] — possessive "John Donaldson's" is GONE ✓ (fix worked!)
  - But alias list is now too sparse — lost "the father", "the man", "John" from attempt 32 ✗
- `main_cast_3`: **Margaret Donaldson** — 2 mentions ✓
- `supporting_1`: **Bill** — 18 mentions, `is_narrator: false`, role: `minor` ✗✗✗
  - Should be "Uncle Bill", `is_narrator: true`, `role: protagonist`
  - Lost canonical name "Uncle Bill" → now just "Bill"
  - Lost ALL aliases (had ["Bill", "Uncle"] when he was main_cast_3)
  - Demoted from main_cast to supporting — WRONG
- `supporting_2`: **Joe Barron** — 3 mentions ✓
- `supporting_3`: **Red Cross** — 4 mentions — organization, not character ✗
- `supporting_4`: **Ted Frith** — 5 mentions, alias: "Ted" ✓
- `supporting_6`: **Johnny** — 2 mentions — should be alias of the son ✗

**Sub-Dimension A: Completeness: 7/10** (DOWN from 8)
- Uncle Bill is present but misnamed and demoted — effectively the protagonist is mischaracterized ✗
- "Red Cross" is an organization, not a character ✗
- "Johnny" should be alias, not separate entry ✗

**Sub-Dimension B: Identity Resolution: 5/10** (DOWN from 7)
- Uncle Bill completely misidentified: wrong name ("Bill" not "Uncle Bill"), wrong role ("minor" not "protagonist"), not narrator ✗✗✗
- Father/son correctly split with disambiguation labels ✓
- "Johnny" remains separate instead of being alias of the son ✗
- Bill's relationships include "John Donaldson: father" — WRONG. Bill is not John Donaldson's father; he's the son's guardian/cousin ✗

**Sub-Dimension C: Alias Grouping: 6/10** (stable)
- Possessive "John Donaldson's" is gone — fix worked ✓
- Father's aliases reduced from ["the father", "the man", "John", "John Donaldson's"] to just ["father"] — over-stripped ✗
- Son now has ["John"] — improved from zero ✓, but missing "Johnny" ✗
- "Johnny" separate instead of alias of the son ✗
- Bill has zero aliases — lost "Uncle" ✗

### 2.3 Character Profiles: 5/10 ✗ (DOWN from 7.5 — MASSIVE regression)

**ALL character profiles are now completely empty.** Every character has:
- `personality_summary: null`
- `personality_traits: null`
- `evidence_quotes: null` (or empty)
- `physical_description: null`

In attempt 32, Uncle Bill and the father had excellent personality summaries, traits, and evidence quotes. All of that is gone.

**What remains functional:**
- Relationships: 4/8 characters have some relationships (but several are wrong — Bill's says "John Donaldson: father" which is incorrect)
- Voice guidance: 4 characters have voice guidance sections, and quality is mixed:
  - **Father's voice guidance:** Excellent — includes "American, sir" verbal tic, accurate example quotes ✓✓
  - **Son's voice guidance:** Good — includes his letter and emotional quotes ✓
  - **Bill's voice guidance:** CONTAMINATED — example quotes include "'American, sir,' he said proudly" and "'Took money,' he said. 'Very unjustifiable.'" — these are the FATHER's lines, not Uncle Bill's ✗✗
  - **Ted Frith's voice guidance:** CONTAMINATED — "'This is my good day. I'm American to-day, sir!'" is the FATHER's iconic line, not Ted's ✗

**Why 5/10:** Having voice guidance saves this from being lower, but the complete loss of personality data, evidence quotes, and contaminated voice guidance for two characters is a severe regression.

### 2.4 Chapter Summaries: 7.5/10 ✗ (stable)

**Section 1:** EXCELLENT. Correctly describes the cousin relationship, the narrator's background, Margaret Donaldson. `characters_present`: ["Narrator"] — acceptable but could include named characters.

**Section 2:** Good quality but the recurring hallucination persists:
- "his deceased sister's son" — WRONG. Uncle Bill is the father's COUSIN, not sibling. Section 1 correctly says "cousin."
- Otherwise excellent: covers Yale, fishing trip, WWI, Caporetto, reunion, deathbed revelation.
- `characters_present`: ["Uncle Bill", "John Donaldson (the son)", "John Donaldson (the father)"] — EXCELLENT, disambiguated names ✓✓

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

Navigation works, character profiles render well (even if data is empty), voice guidance sections display. Disambiguation labels for the Donaldsons display correctly. Minor: "Red Cross" and "Johnny" in Supporting Characters, Bill misnamed.

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (user-configured, appropriate)
- Pipeline: V2 with Phase 2 graph-based identity resolution
- 0 LLM retries — good
- 1 JSON parse failure in Pronunciation Guide stage
- Character Profiles bottleneck (654s / largest stage) — not actionable
- All profiles null despite successful LLM calls (11 calls, 45427 tokens) — suggests profiling data isn't being saved to output
- No config changes recommended

## Current Issues (Priority Order)

### CRITICAL

1. **Uncle Bill demoted from main_cast to supporting, misnamed as "Bill"** [Identity Resolution]
   - Problem: Uncle Bill was `main_cast_3` ("Uncle Bill") in attempt 32, now `supporting_1` ("Bill") with `role: minor` and `is_narrator: false`. He's the story's protagonist and primary narrator.
   - Evidence: The story is told entirely from Uncle Bill's first-person perspective. He narrates both sections. He appears in all sections.
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` — main cast extraction is NOT identifying Uncle Bill as main cast. The supporting cast pipeline picks him up as just "Bill" instead.
   - Fix approach: The main cast extraction must be identifying Uncle Bill. The issue may be that "Uncle Bill" appears less frequently than "John Donaldson" variants, pushing him below the main cast threshold. The deterministic narrator detection from attempt 33 in `narrator.py` can't work if Uncle Bill isn't even in the main cast. Need to investigate why main_cast extraction dropped him — this is a regression from attempt 32.

2. **ALL character profiles empty — massive regression** [Profiles]
   - Problem: Every character has null personality_summary, null personality_traits, null evidence_quotes, null physical_description. In attempt 32, Uncle Bill and the father had excellent profiles.
   - Evidence: `jq '[.characters[] | select(.personality_summary != null)] | length'` returns 0. But profiling stage ran (11 LLM calls, 45427 tokens, 654 seconds).
   - Location: `src/pipeline/character_profiling/` or `src/agents/characters.py` (wherever profiling results are merged into the final character objects)
   - Fix approach: The profiling pipeline ran and consumed significant tokens, so it's generating data. The data is not making it into the final output. Check if the profiles are being matched to characters by name — since "Bill" ≠ "Uncle Bill", the profile for "Uncle Bill" may not match `supporting_1: "Bill"`. This may be a downstream effect of CRITICAL #1.

### HIGH

3. **Bill's voice guidance contaminated with father's quotes** [Profiles]
   - Problem: Bill's example_quotes include "'American, sir,' he said proudly" and "'Took money,' he said. 'Very unjustifiable.'" — these are the FATHER's iconic lines, not Uncle Bill's.
   - Evidence: Throughout the story, "American, sir" and "Took money" are spoken by John Donaldson (the father), not by Uncle Bill.
   - Location: `src/pipeline/character_profiling/` — passage gathering or evidence extraction is assigning the father's dialogue to Bill because they appear in the same scenes.
   - Fix approach: Same root cause as Ted Frith contamination from attempt 32 — the profiling pipeline has a name disambiguation problem where quotes from the father are attributed to nearby characters.

4. **Ted Frith's voice guidance still contaminated with father's quotes** [Profiles]
   - Problem: Ted's example_quotes include "'This is my good day. I'm American to-day, sir!'" — this is the FATHER's line.
   - Evidence: Same as attempt 32 — the "American, sir" lines belong to John Donaldson (the father).
   - Location: Same root cause as HIGH #3.

5. **Father's alias list over-stripped** [Alias Grouping]
   - Problem: Father's aliases went from ["the father", "the man", "John", "John Donaldson's"] to just ["father"]. While removing the possessive was correct, losing "the father", "the man", and "John" was not.
   - Evidence: "the father" and "the man" are valid aliases used in the text. "John" is shared with the son but contextually valid.
   - Location: The possessive stripping fix in `src/pipeline/character_extraction_v2/supporting.py` may have been too aggressive, or NER is extracting fewer aliases this run.
   - Fix approach: This is likely LLM non-determinism rather than a code bug. The possessive stripping only removes "'s" forms — it shouldn't affect "the father" or "the man".

6. **Summary "sister" hallucination persists** [Summaries]
   - Problem: Section 2 says "his deceased sister's son" — Uncle Bill is the father's COUSIN, not sibling.
   - Evidence: Section 1 correctly says "cousin."
   - Location: LLM generation non-determinism in summary pipeline.

### MEDIUM

7. **"Johnny" still a separate character** [Alias Grouping]
   - Problem: Johnny (supporting_6, 2 mentions) should be an alias of John Donaldson (the son), not a separate character.
   - Location: Identity graph merge logic in `src/pipeline/character_extraction_v2/` — nickname matching not connecting "Johnny" to "John Donaldson (the son)".

8. **Pronunciation: 7/20 false positives (35%)** [Pronunciation]
   - Remaining false positives: whippersnapper, thriftless, thickset, manliness, dum-dums, orderlies, mayn't.

9. **Structure: 2 sections for continuous short story** [Structure]
   - Same as all prior attempts. Not worth a targeted fix for this text alone.

10. **"Red Cross" extracted as character** [Completeness]
    - Organization, not a character (supporting_3, 4 mentions).

11. **Bill's relationship "John Donaldson: father" is wrong** [Profiles]
    - Bill is the son's guardian/cousin, not his father. This relationship label is incorrect.

### LOW

12. **Section 1 `characters_present` only shows "Narrator"** — should list named characters
13. **Son still missing "Johnny" alias**

## Fix Priority

**This attempt regressed significantly.** The overall score dropped from 7.28 to 6.65 (-0.63), which is BELOW the baseline of 6.60. The auto-revert threshold is baseline - 0.3 = 6.30, so it doesn't trigger, but this is close.

**Root cause analysis:** The main regression is Uncle Bill being demoted from main_cast to supporting. This likely cascaded into:
1. Profile matching failure (profiles generated for "Uncle Bill" can't match to "Bill")
2. Narrator detection failure (deterministic fallback in narrator.py looks at main_cast characters, Bill is in supporting)

**The possessive stripping fix DID work** — "John Donaldson's" is gone from the father's aliases. But the main_cast extraction became unstable, dropping Uncle Bill entirely.

**Recommended fix order:**
1. **CRITICAL #1: Stabilize Uncle Bill in main_cast** — This is the root cause of most regressions. Need to investigate why main_cast extraction dropped him and ensure he's reliably identified.
2. **CRITICAL #2: Profile data loss** — Likely resolves automatically if Uncle Bill returns to main_cast with correct name. But verify that profiles are actually being written to output.
3. HIGH #3-4 (voice contamination) — May require profile pipeline changes but lower priority than getting the basics right.

## Fix History

### Attempt 34 — Adaptive promotion thresholds (length-scaled)
- **Issues targeted:**
  1. CRITICAL #1 — Uncle Bill demoted from main_cast to supporting (root cause of most regressions)
  2. CRITICAL #2 — Profile data loss (FALSE ALARM - evaluator checked wrong field path)
- **Root cause analysis:**
  - Uncle Bill demotion: LLM non-determinism in main_cast extraction (no code changed but different results)
  - Hard-coded promotion threshold of 50 mentions works for novels but fails for short stories
  - american_sir (~5K words): Uncle Bill has 18 mentions, below threshold despite protagonist-level density
  - Profile data loss: FALSE ALARM - data exists in `personality.summary`, evaluator checked `personality_summary`
- **Changes made:**
  1. Added `adaptive_promotion_thresholds(word_count)` function to `src/agents/characters.py`
  2. Updated Step 5.8 promotion logic to use adaptive thresholds instead of hardcoded values
  3. Thresholds now scale with text length:
     - ≤10K words (short story): 15/10/8 mentions
     - 10K-50K words (novella): 50/30/20 mentions
     - >50K words (novel): 200/100/50 mentions
- **Expected impact:**
  - Uncle Bill (18 mentions in 5K words) → promoted to main_cast with role "protagonist"
  - Same narrative density as 180 mentions in 50K-word novel
  - Universal fix: works for any text length without book-specific tuning
  - Profiles should populate correctly once Uncle Bill is in main_cast with correct name
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
| 34 | Adaptive promotion thresholds | `characters.py` | TBD — awaiting analysis |
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

## Next Action

**Phase:** awaiting_analysis

Attempt 34 fix applied: adaptive promotion thresholds that scale with text length.

Root cause was hardcoded promotion threshold (50 mentions) calibrated for novels, not short stories.
For american_sir (~5K words), Uncle Bill's 18 mentions represent protagonist-level narrative density
but fell below the absolute threshold. The fix scales thresholds to maintain consistent narrative
density requirements across all text lengths.

Re-run analysis to verify:
1. Uncle Bill promoted to main_cast with role "protagonist"
2. Profiles populate correctly (they already exist but evaluator checked wrong field path)
3. No regressions on characters that were already working
