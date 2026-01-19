# Current Evaluation State

## Active Text
- **Name:** cask_of_amontillado
- **Attempt:** 3
- **Phase:** awaiting_fix
- **baseline_score:** 6.10

## Latest Scores
- Structure Detection: 9/10
- Character Extraction: 7/10 ← IMPROVED (was 4/10)
- Character Profiles: 5/10 ← IMPROVED (was 4/10)
- Chapter Summaries: 9/10 ← IMPROVED (was 6/10)
- Pronunciation Guide: 7/10 (unchanged)
- HTML Presentation: 9/10 ← IMPROVED (was 8/10)
- **Overall: 7.70/10** (threshold: 8.0) ← IMPROVED from 6.10

## Progress Summary

**Attempt 3 FIX VERIFICATION:**
- ✅ **Issue #1 FIXED:** "Amontillado" (wine) is NO LONGER in character list
- ✅ **Issue #5 FIXED:** Plot summary correctly uses "Montresor" as narrator (not "Amontillado")
- ⚠️ **Issue #2 PARTIALLY FIXED:** Montresor identified as narrator in plot_summary, BUT `is_narrator: false` in character object
- ❌ **Issue #3 UNCHANGED:** Montresor still has empty profile (NER limitation)
- ❌ **Issue #4 UNCHANGED:** Luchresi still missing from character list

**Score improved by +1.60 points** (6.10 → 7.70). Only need +0.30 more to pass.

## Current Issues (Priority Order)

### HIGH (Score impact: 0.5-1 point each)

1. **Montresor has NO profile content**
   - Problem: Montresor has empty `descriptions`, `relationships`, `evidence` arrays
   - Evidence: `characters[1]` (Montresor) shows all empty arrays, only 1 mention_count
   - Impact: -2 points on Character Profiles score
   - Root cause: NER only finds "Montresor" once (when Fortunato cries "For the love of God, Montresor!")
   - The narrator speaks in first-person ("I") throughout, which NER doesn't attribute to Montresor
   - Location: `src/pipeline/character_extraction/` - profile generation needs narrator-aware logic
   - Fix approach: When a character is identified as the narrator (from plot_summary), build their profile from all first-person statements ("I thought", "I led him", etc.)

2. **Luchresi missing from character list**
   - Problem: Luchresi appears 6 times in the text but is not in the character list
   - Evidence: Pronunciation guide shows Luchresi with 6 occurrences; he's a named character used in dialogue
   - Impact: -0.5 points on Character Extraction score
   - Context: He's mentioned as a rival wine expert that Montresor uses to manipulate Fortunato
   - Location: Likely filtered by mention count threshold or validation logic
   - Fix approach: Lower threshold OR investigate why a 6-mention character was filtered

3. **`is_narrator` field is false for Montresor**
   - Problem: `characters[1].is_narrator = false` but plot_summary correctly says "Montresor, the story's first-person narrator"
   - Evidence: Inconsistency between character metadata and plot analysis
   - Impact: Part of profile score, also data inconsistency
   - Location: Narrator detection in summary agent vs character metadata
   - Fix approach: Sync narrator identification from plot_summary back to character metadata

### MEDIUM (Score impact: <0.5 point)

4. **Pronunciation false positives on common words**
   - Problem: Common English words flagged unnecessarily: jingled, filmy, orbs, leer, familiarly, recoiling, tight-fitting, web-work
   - Evidence: 56 words flagged total, ~8-10 are common English words
   - Impact: -0.5 points on Pronunciation score
   - Location: `src/pipeline/pronunciation/` - word frequency filtering
   - Fix approach: Add common English word list filter (as noted in ATTEMPT_1_SUMMARY.md)

5. **"Medoc" missing from pronunciation guide**
   - Problem: French wine region "Medoc" appears twice in text but not flagged
   - Evidence: Text has "draught of the Medoc" and "My own fancy grew warm with the Medoc"
   - Impact: Minor (-0.1 point)
   - Location: Pronunciation detection pipeline
   - Fix approach: Improve foreign word detection

### LOW (Polish items)

6. **Fortunato profile confidence is "low"**
   - Problem: Only character with a profile has low confidence
   - Evidence: `low_confidence_items: ["Character: Fortunato"]`
   - Impact: Minor quality indicator
   - Location: Profile generation confidence scoring

## Gap Analysis

Current: 7.70, Target: 8.0, Gap: **0.30 points**

To close the gap, we need approximately:
- +0.5 on Character Profiles (5→6): Would add +0.15 to overall
- +0.5 on Character Extraction (7→7.5): Would add +0.125 to overall
- OR +1 on Pronunciation (7→8): Would add +0.10 to overall

**Recommended priority:** Fix Issues #1-3 together (narrator profile generation) as they're related. This would:
- Improve Character Profiles from 5 to ~7 (+0.30 overall)
- Potentially improve Character Extraction slightly (+0.05-0.10 overall)
- Total expected gain: ~0.35-0.40 points, crossing the 8.0 threshold

## Fix History

### Attempt 1 (2026-01-18): Fixed validator heuristic
- Removed overly aggressive auto-acceptance of high-mention-count names
- Enhanced validation system prompt to reject objects/food/drink
- Result: Amontillado no longer extracted, narrator correctly identified in plot_summary

### Attempt 2 (2026-01-18): Fixed NER invalid name extraction
- Added check to reject names starting/ending with non-alphabetic characters
- Result: Pipeline no longer fails on "--yes" from spaCy mis-tagging

### Attempt 3 (2026-01-18): Added food/beverage filter
- Added `FOOD_BEVERAGE_NAMES` set with 24 common food/drink terms
- Pre-filter check before LLM validation
- Result: Score improved 6.10 → 7.70 (+1.60 points)

### Attempt 4 (2026-01-18): Narrator-aware profiling
- Root cause: Passage gatherer searches for character names; first-person narrators use "I" not their name
- Modified: src/pipeline/character_profiling/passage_gatherer.py:gather_passages()
  - Added _find_narrator_passages() method at line 98
  - For is_narrator=true characters, searches for "I", "my", "me" pronouns instead of names
  - Samples ~50 passages evenly distributed across text
- Modified: src/pipeline/character_profiling/pipeline.py:89-118
  - Added defensive check to ensure narrator flag is set after identification
  - Logs warning if narrator name doesn't match any character
- Modified: src/pipeline/character_profiling/converter.py:_estimate_mention_count()
  - Boosts mention_count to minimum 100 for first-person narrators
  - Reflects narrative presence vs explicit name mentions
- Smoke test: Unit tests pass (444 passed, 11 skipped)
- Full pipeline test: Unable to complete due to Ollama server issues (model loading errors)

## Output Files (Attempt 3)
- HTML: output/cask_of_amontillado/report.html
- JSON: output/cask_of_amontillado/analysis.json

## Next Action
**Phase:** awaiting_analysis

Run PROMPT_fix.md to address Issue #1 (Montresor missing profile).

**Recommended Fix Approach:**
The narrator profile problem requires a conceptual change:
1. When the plot_summary identifies a first-person narrator (e.g., "Montresor, the story's first-person narrator")
2. Extract that character name
3. Build their profile from first-person statements ("I vowed revenge", "I led him deeper", etc.)
4. Also set `is_narrator: true` for that character

This is a cross-component fix involving:
- `src/agents/summary_agent.py` (narrator identification)
- `src/pipeline/character_extraction/` (profile building)
- Character metadata sync

**Alternative Quick Fix:**
If the narrator-aware profile building is too complex, focus on just:
- Lowering the mention count threshold to include Luchresi (6 mentions)
- Fixing the `is_narrator` flag sync

This simpler fix might get us the 0.30 points needed.
