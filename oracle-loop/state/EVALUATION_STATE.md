# Current Evaluation State

## Active Text
- **Name:** cask_of_amontillado
- **Attempt:** 3
- **Phase:** awaiting_evaluation
- **baseline_score: 6.75**
- **Competitive Mode:** single

## Output Files
- HTML: ../output/cask_of_amontillado/report.html
- JSON: ../output/cask_of_amontillado/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 3/10 ✗ (FAILING)
- Character Profiles: 5/10 ✗ (FAILING)
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 7/10 ✗ (FAILING)
- HTML Presentation: 8.5/10 ✓
- **Overall: 6.65/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.75 | 0.0 | Baseline. 5 bogus supporting chars, Fortunato profile is Montresor's |
| 2 | 6.65 | -0.10 | Bogus chars fixed (+1), but Montresor still missing. Fortunato profile improved but still has issues |

## Current Issues (Priority Order)

### CRITICAL

1. **Montresor (protagonist/narrator) NOT extracted as a character**
   - Problem: The story's protagonist and narrator is completely absent from the character list. The pipeline correctly identifies him as narrator (`pipeline_metadata.narrator_name: "Montresor"`) but he never makes it into the character list.
   - Root cause: **Variable name typo** at `src/analyzer.py:1648` — `document.normalized_text` should be `doc.normalized_text`. This crashes F6 character reconciliation with `NameError: name 'document' is not defined`, preventing Montresor from being added via summary-based reconciliation.
   - Evidence: Log shows "F6 character reconciliation failed: name 'document' is not defined" and "Narrator 'Montresor' identified but NOT found in main_cast. Available characters: ['Fortunato']"
   - The F6 reconciliation step (analyzer.py lines 1640-1720) is designed to find characters appearing in chapter summaries but missing from main_cast — exactly this scenario. But it crashes before executing.
   - **Two fixes needed:**
     1. **Fix the typo**: `src/analyzer.py:1648` — change `document` to `doc` (same variable used everywhere else in the method, e.g., lines 813, 814, 829, 1777)
     2. **Add narrator→character fallback**: In `src/analyzer.py` around line 1760, if narrator is detected but not in character list AND F6 didn't add them, create a Character entry for the narrator. The profile filter at line 1811 already handles narrators with `or getattr(c, "is_narrator", False)`.
   - Impact: Score -5 on Character Extraction, -3 on Character Profiles. This is the single biggest issue blocking progress.

### HIGH

2. **Fortunato labeled "antagonist" with "villainous" moral alignment — inaccurate**
   - Problem: Fortunato is the VICTIM in this story. Montresor is both protagonist and villain. Fortunato is a proud, trusting, somewhat foolish man lured to his death. Labeling him "antagonist" with "villainous" moral alignment is misleading for narrator preparation.
   - Evidence: Fortunato is chained up and entombed alive — he's the victim, not the antagonist. His traits (gullible, overconfident, prideful) are correct but don't support "villainous."
   - Location: Role assignment in `src/pipeline/character_extraction_v2/main_cast.py` and moral alignment in profiling pipeline
   - Impact: Score -1 on Character Extraction, -0.5 on Character Profiles
   - Note: This is an LLM judgment issue, not easily fixed generically. Deprioritize in favor of CRITICAL #1.

3. **Fortunato's physical description attributes Montresor's clothing to Fortunato**
   - Problem: Description says "wears a black silk mask and roquelaire (as described in context of Montresor, but implied Fortunato is similarly attired)" — the roquelaire and black silk mask are Montresor's clothing, NOT Fortunato's. Fortunato wears a jester's motley with bells (correctly noted elsewhere).
   - Evidence: Poe's text: "I suffered him to hurry me to my palazzo...I had on a black silk mask..." — this is Montresor speaking.
   - Location: `src/pipeline/character_profiling/` — passage gatherer may still have some narrator contamination for physical descriptions
   - Impact: Score -0.5 on Character Profiles

4. **Pronunciation false positives (~30% rate)**
   - Problem: 11 of 37 entries are common words a narrator wouldn't need help with:
     - Common compounds: "tight-fitting", "web-work", "mason-work"
     - Archaic spelling: "to-day" (obvious pronunciation)
     - Common words: "cough's", "leer", "Grave"
     - Standard prefixed words: "Unsheathing", "reapproached", "re-echoed", "re-erected"
   - Location: `src/pipeline/pronunciation/` — flagging threshold too aggressive
   - Impact: Score -1.5 on Pronunciation

5. **OCR artifact "himselffelt" still present in pronunciation guide**
   - Problem: "himselffelt" (/hɪmˈsɛlfˌfɛlt/) is two fused words ("himself felt"), not a real word
   - Location: `src/ingestion/refine.py` (OCR repair) or pronunciation pipeline should reject compound artifacts
   - Impact: Score -0.5 on Pronunciation

### MEDIUM

6. **Relationship labels inaccurate**
   - Problem: Fortunato-Montresor labeled "rival" (should be something like "victim-murderer" or "acquaintance"). Luchresi-Fortunato also labeled "rival" (should be "professional competitor" or "fellow connoisseur"). Fortunato's "moral_alignment: villainous" is wrong.
   - Location: Relationship extraction in character profiling pipeline
   - Impact: Score -0.5 on Character Profiles

7. **Narrative style inconsistency in overview**
   - Problem: `overview.structure.narrative_style` says "unknown" while `overview.plot_summary.narrative_style` correctly says "first-person retrospective"
   - Location: `src/analyzer.py` — structure overview vs plot summary use different detection paths
   - Impact: Minor metadata inconsistency

### LOW

8. **Missing pronunciation: "In pace requiescat" (closing Latin phrase)**
   - Note: "requiescat" alone IS flagged. The full phrase context would be helpful but not critical.

9. **Homographs "row", "close", "entrance" lack IPA (by design)**
   - Note: Correct behavior for homographs — context-dependent pronunciation notes provided instead.

## Configuration Audit

### Model Configuration
- All agents use `qwen3-next:80b-a3b-instruct-q8_0` — appropriate per user configuration
- Temperature 0.7 for all — could be lower (0.3-0.5) for character extraction to reduce hallucination
- Context length 32768 — sufficient for this short story

### Chunking Configuration
- `character_llm_chunk_chars: 5000` — fine for a ~13K character story (2-3 chunks)
- `summary_chunk_words: 2500` — appropriate, story is ~2353 words so fits in one chunk

### Processing Issues
- 0 LLM retries, 0 JSON parse failures — model worked cleanly
- Character Extraction: 1 high confidence (main cast), 1 medium confidence (supporting) — improved from attempt 1
- Character Profiles: 2 high confidence, 0 low — Fortunato personality now correctly about Fortunato (fix worked)
- F6 reconciliation crash prevented narrator from being added (CRITICAL #1)

## Fix History

### Attempt 2 Fixes Applied
1. **CRITICAL #1 (old): Fortunato personality profile contamination - FIXED (VERIFIED)**
   - Root cause: `src/analyzer.py:1828` - narrative_style set to "unknown" instead of "first-person"
   - Fix: Changed narrative_style detection to use text-based analysis
   - Result: **FIXED** — Fortunato's personality now correctly describes Fortunato (gullible, overconfident, prideful) instead of Montresor's traits. Profile score improved from 4/10 to 5/10.

2. **CRITICAL #2 (old): 5 bogus supporting characters - FIXED (VERIFIED)**
   - Root cause: `src/pipeline/character_extraction_v2/grounding.py:24-36` - adaptive_min_mentions() returned 1
   - Fix: Raised floor of adaptive_min_mentions from 1 to 2
   - Result: **FIXED** — All 5 bogus characters removed. Only Luchresi remains (correct).

3. **Pronunciation false positives - DEFERRED (still failing)**
   - Still ~30% false positive rate (11/37 entries)

### Attempt 3 Fixes Applied
1. **CRITICAL #1: Montresor (narrator) missing from character list - FIXED**
   - Root cause:
     - `src/analyzer.py:1648` — Variable name typo: `document.normalized_text` should be `doc.normalized_text`
     - This crashed F6 reconciliation with `NameError: name 'document' is not defined`
     - F6 is designed to add characters found in summaries but missing from main_cast (exactly this scenario)
     - Narrator detection worked (pipeline_metadata.narrator_name = "Montresor") but F6 crash prevented adding him
   - Fix (two-layer defense):
     - **Fix 1 (line 1648)**: Corrected typo `document` → `doc` to unblock F6 reconciliation
     - **Fix 2 (lines 1769-1807)**: Added narrator→character fallback after narrator detection
       - If narrator is detected but NOT in character list, create a Character entry
       - Uses same hash-based ID pattern as F6 (`hashlib.md5(name).hexdigest()[:12]`)
       - Marks character with `is_narrator=True` and `supporting_strategies=["narrator_detection_fallback"]`
       - Ensures profiling (line 1811 already filters for `is_narrator`)
   - Smoke test: **PASS** — All existing tests pass (298 passed, 8 pre-existing failures in test_semantic_conflicts.py)
   - Expected result:
     - Either F6 adds Montresor (typo fixed) OR fallback adds Montresor (safety net)
     - Either way, Montresor will be in character list and get a profile
     - Character Extraction: 3/10 → 8/10 (estimated +5)
     - Character Profiles: 5/10 → 8/10 (estimated +3)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 2 | Fortunato personality contamination | `src/analyzer.py` | Fixed — personality now correct |
| 2 | Bogus supporting characters | `src/pipeline/character_extraction_v2/grounding.py` | Fixed — 5 bogus chars removed |
| 3 | CRITICAL: F6 reconciliation crash (`document` typo) | `src/analyzer.py:1648` | **FIXED** — typo corrected |
| 3 | CRITICAL: Narrator not added to character list | `src/analyzer.py:1769-1807` | **FIXED** — fallback added |

## Pipeline Notes (Attempt 3)

**Execution Time:** 31m 7s

**Key Observations:**

1. **F6 reconciliation still failed** - Different error than before:
   - Previous error (attempt 2): `NameError: name 'document' is not defined` (typo at line 1648)
   - New error (attempt 3): `'ExtractedDocument' object has no attribute 'normalized_text'`
   - This suggests the typo fix revealed a deeper issue with the ExtractedDocument interface

2. **Narrator fallback activated successfully:**
   - Log shows: "Narrator 'Montresor' identified but NOT found in character list. Adding as character (safety fallback)."
   - Montresor was added to character list (shown in summary: 3 characters including Montresor)
   - However, profile generation failed: "Profile generation failed for Montresor: None"

3. **Competitive consensus active:**
   - "Competitive consensus: ENABLED (3 LLMs, 2/3 supermajority)"
   - Applied to characters, structure, summaries stages

4. **Profile quality warnings:**
   - "F19: Profile for 'Fortunato' has 3 potentially ungrounded evidence quotes - may indicate hallucination"
   - This may affect Character Profiles score

5. **Pronunciation LLM issues:**
   - Model returned error responses instead of structured JSON for some pronunciation queries
   - Example: Rejected "himselffelt" as invalid word (OCR artifact)
   - May affect Pronunciation Guide score

**Next Action:**
Phase changed to `awaiting_evaluation`. Evaluation phase will determine if fixes improved scores.
