# Current Evaluation State

## Active Text
- **Name:** cask_of_amontillado
- **Attempt:** 2
- **Phase:** awaiting_fix
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

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 2 | Fortunato personality contamination | `src/analyzer.py` | Fixed — personality now correct |
| 2 | Bogus supporting characters | `src/pipeline/character_extraction_v2/grounding.py` | Fixed — 5 bogus chars removed |
| 3 | CRITICAL: F6 reconciliation crash (`document` typo) | `src/analyzer.py:1648` | Pending fix |
| 3 | CRITICAL: Narrator not added to character list | `src/analyzer.py:~1760` | Pending fix |

## Next Action
Run PROMPT_fix.md to address:
1. **CRITICAL #1**: Fix `document` → `doc` typo at `src/analyzer.py:1648` (unblocks F6 reconciliation, which should add Montresor)
2. **CRITICAL #1 (fallback)**: Add narrator→character creation fallback at `src/analyzer.py:~1760` (safety net if F6 still misses narrator)

**Expected score improvement after fix:**
- Character Extraction: 3/10 → 8/10 (+5 from adding Montresor as protagonist/narrator)
- Character Profiles: 5/10 → 8/10 (+3 from Montresor getting a profile, existing narrator filter at line 1811 ensures profiling)
- Pronunciation: 7/10 (unchanged — deferred)
- **Estimated new score: ~8.15/10**

**Note:** Pronunciation (7/10) will still be below threshold. If CRITICAL #1 is fixed and Characters+Profiles pass, the remaining blocker will be pronunciation false positives (HIGH #4 and #5).
