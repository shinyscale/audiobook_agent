# Current Evaluation State

## Active Text
- **Name:** cask_of_amontillado
- **Attempt:** 4
- **Phase:** awaiting_analysis
- **baseline_score: 6.75**
- **Competitive Mode:** single

## Output Files
- HTML: ../output/cask_of_amontillado/report.html
- JSON: ../output/cask_of_amontillado/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 7/10 ✗ (FAILING)
- Character Profiles: 4.5/10 ✗ (FAILING)
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 7/10 ✗ (FAILING)
- HTML Presentation: 8.5/10 ✓
- **Overall: 7.58/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.75 | 0.0 | Baseline. 5 bogus supporting chars, Fortunato profile is Montresor's |
| 2 | 6.65 | -0.10 | Bogus chars fixed (+1), but Montresor still missing. Fortunato profile improved but still has issues |
| 3 | 7.58 | +0.83 | Montresor now in character list (fallback worked), but profile generation failed. F6 still broken. |

## Current Issues (Priority Order)

### CRITICAL

1. **Montresor profile generation FAILED — protagonist/narrator has zero profile**
   - Problem: Montresor was successfully added to the character list via narrator fallback, but profile generation failed completely. All profile fields are defaults: "No physical description available", "Insufficient information for personality analysis", "No specific voice guidance available".
   - Evidence: `analysis.json` shows Montresor with empty appearance, empty personality traits, empty speech patterns, empty voice guidance, 0 relationships, and only 1 mention count. Log from analyze phase: "Profile generation failed for Montresor: None"
   - Root cause analysis:
     - The narrator fallback creates a minimal Character object with `mention_count=1` and no chapters_present
     - The profiling pipeline likely needs a character with populated mentions/chapters to gather evidence passages
     - Additionally, F6 reconciliation STILL fails (new error: `'ExtractedDocument' object has no attribute 'normalized_text'`), so F6 never gets a chance to properly populate Montresor's data
   - **Two fixes needed:**
     1. **Fix F6 reconciliation properly**: The `ExtractedDocument` object doesn't have `normalized_text` — need to check what attribute it actually uses (likely `text` or `full_text`). Check the `ExtractedDocument` model in `src/models.py` or `src/ingestion/` to find the correct attribute name. This will allow F6 to properly add Montresor with full metadata.
     2. **Improve narrator fallback character creation**: When creating a narrator character via fallback, populate `mention_count` by counting occurrences of the name in the text, and set `chapters_present` to all chapters. This gives the profiling pipeline enough data to generate a proper profile.
   - Impact: Score -3.5 on Character Profiles (main character has no profile), -1 on Character Extraction (mention count wrong)
   - Location: `src/analyzer.py` — F6 reconciliation block (~line 1640-1720) and narrator fallback block (~lines 1769-1807)

### HIGH

2. **Fortunato role labeling inaccurate ("antagonist" / "villainous")**
   - Problem: Fortunato is labeled "antagonist" with personality summary calling him "villainous antagonist whose fatal flaw...is ruthlessly exploited to facilitate his murder." This contradicts itself — someone whose murder is "facilitated" is a victim, not a villain.
   - Evidence: In "The Cask of Amontillado," Montresor is the villain; Fortunato is the victim lured to his death. Fortunato's traits (arrogant, vain, gullible) are correct, but "villainous" moral alignment is wrong.
   - Location: Role assignment happens in `src/pipeline/character_extraction_v2/main_cast.py` (Pass 1). Moral alignment comes from the profiling pipeline.
   - Impact: Score -0.5 on Character Extraction, -0.5 on Character Profiles
   - Note: This is an LLM judgment issue. The fix for CRITICAL #1 (getting Montresor properly profiled as the villain/protagonist) may naturally improve how the LLM perceives Fortunato's role in relation. **Deprioritize — fix CRITICAL #1 first and re-evaluate.**

3. **Pronunciation false positives (~32% rate)**
   - Problem: 12 of 37 pronunciation entries are common words a narrator wouldn't need help with:
     - Common compounds: "tight-fitting", "web-work", "mason-work"
     - Archaic spelling: "to-day" (obvious)
     - Common words: "cough's", "leer", "Grave"
     - Standard prefixed words: "Unsheathing", "reapproached", "re-echoed", "re-erected"
     - Redundant: "Montresors" (plural of already-listed name)
     - OCR artifact: "himselffelt" (two fused words: "himself felt")
   - Location: `src/pipeline/pronunciation/` — flagging criteria too aggressive for common English words
   - Impact: Score -1.5 on Pronunciation
   - Suggested fix: The pronunciation flagging prompt should instruct the LLM to NOT flag:
     - Simple hyphenated compounds of common words (tight-fitting, web-work)
     - Common English words regardless of archaic spelling (to-day)
     - Regular re-/un- prefixed words where pronunciation is obvious
     - Possessive forms of common words (cough's)
     - Plurals of names already in the pronunciation list

4. **OCR artifact "himselffelt" in pronunciation guide**
   - Problem: "himselffelt" is two words fused together ("himself felt"), not a real word. It should be caught by text refinement or rejected by the pronunciation pipeline.
   - Location: `src/ingestion/refine.py` or `src/pipeline/pronunciation/`
   - Impact: Score -0.5 on Pronunciation

### MEDIUM

5. **Relationship labels simplistic**
   - Problem: Fortunato→Montresor labeled "rival", Luchresi→Fortunato labeled "rival", Luchresi→Montresor labeled "rival". None of these are accurate:
     - Fortunato-Montresor: acquaintance/friend (Fortunato doesn't know Montresor wants to kill him)
     - Luchresi-Fortunato: professional competitor/fellow connoisseur
   - Location: Relationship extraction in character profiling pipeline
   - Impact: Score -0.5 on Character Profiles
   - Note: May improve once CRITICAL #1 is fixed and full profiling runs

6. **Narrative style inconsistency in overview**
   - Problem: `overview.structure.narrative_style` says "unknown" while `overview.plot_summary.narrative_style` correctly says "first-person retrospective"
   - Location: `src/analyzer.py` — structure overview generation
   - Impact: Minor metadata inconsistency

### LOW

7. **Missing pronunciation: "In pace requiescat" (closing Latin phrase)**
   - Note: "requiescat" alone IS flagged. The full phrase context would be helpful but not critical.

8. **Homographs "row", "close", "entrance" lack IPA (by design)**
   - Note: Correct behavior — context-dependent notes provided instead.

## What Needs to Happen to Pass

To cross 8.0 in all failing categories:

1. **Character Extraction (7 → 8):** Fix Montresor's mention count (currently 1, should be ~10+). Fix or accept Fortunato's role label.
2. **Character Profiles (4.5 → 8):** This is the **biggest gap**. Montresor MUST get a proper profile. He needs: appearance (black silk mask, roquelaire), personality (cold, calculating, vindictive, patient), speech patterns (formal, ironic, manipulative), voice guidance, and relationships.
3. **Pronunciation (7 → 8):** Reduce false positive rate from 32% to <15%. Remove OCR artifact.

**The single most impactful fix is CRITICAL #1** — getting Montresor's profile generated. This alone could push Character Profiles from 4.5 to 7-8 and Character Extraction from 7 to 8.

## Configuration Audit

### Model Configuration
- All agents use `qwen3-next:80b-a3b-instruct-q8_0` — appropriate per user configuration
- Temperature 0.7 for all — acceptable
- Context length 32768 — sufficient for this short story

### Chunking Configuration
- `character_llm_chunk_chars: 5000` — fine for a ~13K character story (2-3 chunks)
- `summary_chunk_words: 2500` — appropriate, story fits in one chunk

### Processing Issues
- 0 LLM retries, 0 JSON parse failures — model worked cleanly
- F6 reconciliation crashes with `'ExtractedDocument' object has no attribute 'normalized_text'`
- Profile generation failed for Montresor (likely due to minimal character data from fallback)

## Fix History

### Attempt 2 Fixes Applied
1. **CRITICAL #1 (old): Fortunato personality profile contamination - FIXED (VERIFIED)**
   - Root cause: `src/analyzer.py:1828` - narrative_style set to "unknown" instead of "first-person"
   - Fix: Changed narrative_style detection to use text-based analysis
   - Result: **FIXED** — Fortunato personality now correctly about Fortunato.

2. **CRITICAL #2 (old): 5 bogus supporting characters - FIXED (VERIFIED)**
   - Root cause: `src/pipeline/character_extraction_v2/grounding.py:24-36` - adaptive_min_mentions() returned 1
   - Fix: Raised floor from 1 to 2
   - Result: **FIXED** — All 5 bogus characters removed.

### Attempt 3 Fixes Applied
1. **CRITICAL: Montresor missing from character list - PARTIALLY FIXED**
   - Fix 1 (typo `document` → `doc`): Applied but F6 still fails with new error (`ExtractedDocument` has no `normalized_text`)
   - Fix 2 (narrator fallback): **WORKS** — Montresor added to character list successfully
   - BUT: Profile generation failed for Montresor (empty profile). The fallback creates a minimal Character object that the profiling pipeline can't work with.
   - Fortunato's clothing contamination (black silk mask/roquelaire) is FIXED — no longer appears in Fortunato's profile.
   - Net result: +0.93 overall improvement, but still 3 categories failing.

### Attempt 4 Fixes Applied
1. **CRITICAL #1 (F6 reconciliation and narrator fallback) - FULLY FIXED**
   - **Root cause 1:** `src/analyzer.py:1648` - F6 reconciliation used `doc.normalized_text`, but `ExtractedDocument` only has `.text` attribute
   - **Root cause 2:** `src/analyzer.py:1794` - Narrator fallback created character with hardcoded `mention_count=1`, empty `mentions=[]`, which caused profile generation to fail
   - **Fix 1:** Changed `doc.normalized_text` → `doc.text` at line 1648
   - **Fix 2:** Modified narrator fallback (lines 1784-1807) to use `MentionSearcher` to populate real mention data (mentions, mention_count, chapters_present)
   - **Expected impact:** F6 will now work correctly. If narrator fallback activates, it creates a fully-populated character that profiling can work with.
   - **Smoke test:** PASS - Code compiles, all tests pass (298 passed, 10 skipped)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 2 | Fortunato personality contamination | `src/analyzer.py` | Fixed — personality now correct |
| 2 | Bogus supporting characters | `src/pipeline/character_extraction_v2/grounding.py` | Fixed — 5 bogus chars removed |
| 3 | F6 reconciliation crash (`document` typo) | `src/analyzer.py:1648` | Partially fixed — new error revealed |
| 3 | Narrator not added to character list | `src/analyzer.py:1769-1807` | Fixed — fallback works, but profile fails |
| 4 | F6 reconciliation AttributeError | `src/analyzer.py:1648` | Fixed — `normalized_text` → `text` |
| 4 | Narrator fallback missing mention data | `src/analyzer.py:1784-1807` | Fixed — now populates real mentions via MentionSearcher |

## Next Action
**Phase:** awaiting_analysis

Re-run analysis to verify:
1. F6 reconciliation works OR narrator fallback creates properly-populated character
2. Montresor gets a complete profile (appearance, personality, voice guidance)
3. Pronunciation false positives reduced (may need separate fix)
