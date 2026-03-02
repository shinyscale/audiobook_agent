# Current Evaluation State

## Active Text
- **Name:** cask_of_amontillado
- **Attempt:** 2
- **Phase:** awaiting_fix
- **baseline_score:** 6.10
- **Competitive Mode:** none

## Output Files
- HTML: ../output/cask_of_amontillado/report.html
- JSON: ../output/cask_of_amontillado/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 7.5/10 ✗ (FAILING)
  - Completeness: 7/10
  - Identity Resolution: 10/10
  - Alias Grouping: 9/10
- Character Profiles: 7/10 ✗ (FAILING)
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 7/10 ✗ (FAILING)
- HTML Presentation: 8.5/10 ✓
- **Overall: 8.0/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold: Characters 7.5, Profiles 7, Pronunciation 7)

## Current Issues (Priority Order)

### HIGH

1. **Luchresi missing from character list** [Completeness]
   - Problem: Luchresi is mentioned 6 times in the source text (all in dialogue) but does not appear as a character entry. For a story with only 3 named characters, missing one is 33% of the cast.
   - Evidence: Luchresi is referenced by Montresor as a manipulation ploy to goad Fortunato's pride ("Luchresi cannot tell Amontillado from Sherry"). Lines 30, 32, 42, 48, 74, 144 in source text. He never physically appears.
   - Root cause: V2 pipeline likely requires characters to appear in NER or have a physical presence. Characters only referenced in dialogue (never physically present) may fall through. 6 mentions may also be below extraction threshold for main_cast.
   - Location: `src/pipeline/character_extraction_v2/` — main_cast or supporting_cast extraction
   - Fix approach: Ensure characters with ≥3 name mentions (even in dialogue only) are extracted. For short texts with very few characters, lowering the threshold is especially important. Alternatively, add a post-extraction check that scans for named entities in dialogue that aren't in the character list.

2. **Physical description misattribution: Montresor's garments on Fortunato** [Profiles]
   - Problem: Fortunato's profile includes "wears a mask of black silk" and "roquelaire (cloak) drawn closely about his person" — but these are Montresor's garments. The text says "**I** put on a mask of black silk" and "Drawing the roquelaire closely about **my** person" (first-person = Montresor).
   - Evidence: Fortunato's actual costume is: "tight-fitting parti-striped dress, conical cap and bells." Montresor wears: "mask of black silk, roquelaire."
   - Root cause: The profile generation LLM reads first-person "I" descriptions and misattributes them to the character being profiled (Fortunato) instead of the narrator (Montresor). This is a generic issue with first-person narration profile extraction.
   - Location: `src/analyzer.py` — `_generate_character_profile()` prompt
   - Fix approach: Add guidance to the profile generation prompt that in first-person narration, "I" references describe the NARRATOR, not the character being profiled. When profiling a non-narrator character, only extract physical details explicitly attributed to that character (e.g., "He wore..." not "I put on...").

3. **Montresor has no physical description** [Profiles]
   - Problem: `physical_description: null` for Montresor despite text providing: "I put on a mask of black silk" and "Drawing the roquelaire closely about my person."
   - Root cause: Related to issue #2 — the LLM extracted these as Fortunato's description instead of Montresor's. If the profile prompt correctly attributes "I" to the narrator, Montresor should gain these descriptions.
   - Location: Same as #2 — `src/analyzer.py` profile generation
   - Fix approach: Will likely resolve when #2 is fixed.

### MEDIUM

4. **Missing foreign pronunciation entries** [Pronunciation]
   - Problem: Three important foreign terms are missing from the pronunciation guide:
     - "Medoc" (French wine, mentioned 3 times) — narrator needs to know it's /meɪˈdɒk/
     - "palazzo" (Italian for palace, mentioned 3 times) — /pəˈlæt.soʊ/
     - "De Grave" (French wine name, mentioned once) — /də ˈɡʁɑːv/
   - Evidence: These are non-English words a narrator would need guidance on.
   - Location: `src/pipeline/pronunciation/` — foreign word detection
   - Fix approach: Improve detection of Italian and French terms. "palazzo" and "Medoc" are common enough foreign words that should be flagged. Consider adding a short foreign-language word list or improving the LLM prompt to catch common Romance-language terms.

5. **False positive pronunciation entries** [Pronunciation]
   - Problem: Three common English words flagged unnecessarily:
     - "leer" — standard English word
     - "gesticulation" — standard English word
     - "flagon" — reasonably common English word
   - Evidence: A professional audiobook narrator would know these words.
   - Location: `src/pipeline/pronunciation/` — common-word filtering
   - Fix approach: Improve the common-word filter. These are not archaic or unusual enough to warrant pronunciation guidance.

6. **Montresor's voice guidance is thin** [Profiles]
   - Problem: Voice tone described as only "calm and deceptive" — could be richer. The narrator's voice should convey the contrast between outward cordiality and inner malice, with increasing intensity during the walling scene.
   - This is a polish item that would help push profiles from 7 to 8.

### LOW

7. **Structure metadata incomplete**
   - Problem: title, start_line, end_line are all null for the single section
   - Cosmetic issue, doesn't affect narrator utility

8. **"Nemo me impune lacessit" not flagged as full phrase** [Pronunciation]
   - Problem: Only "impune" is individually flagged from the Latin family motto. The full phrase "Nemo me impune lacessit" is what the narrator needs to pronounce.
   - Location: Pronunciation pipeline may not detect multi-word foreign phrases in quotes

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.10 | — (baseline) | Missing Montresor, narrator misattribution, profile conflation |
| 2 | 8.0 | +1.90 | Montresor extracted, narrator fixed, profiles improved; Luchresi still missing, pronunciation gaps |

## Fix History

### Attempt 1 Fix — Vocative Narrator Name Resolution
- **Issues addressed:** #1-3 from attempt 1 (Montresor missing, narrator misattribution, profile conflation)
- **Result:** All three FIXED. Montresor now extracted as protagonist/narrator. Fortunato no longer flagged as narrator. Profiles have correct personality traits per character.
- **Files modified:** `src/agents/characters.py`, `tests/test_character_extraction_v2.py`

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | Montresor missing + narrator misattrib + profile conflation | `src/agents/characters.py`, `tests/test_character_extraction_v2.py` | Fixed (all 3 resolved) |

## Configuration Notes
- Model: qwen3.5:122b-a10b for characters and summaries (good)
- Model: qwen3.5:35b-a3b for structure and pronunciation
- `character_llm_chunk_chars: 5000` — adequate for this short text
- No obvious config issues; remaining problems are pipeline logic and prompt quality

## Next Action
Run PROMPT_fix.md to address:
1. **Priority 1:** Luchresi extraction (Characters 7.5 → 8.0) — either lower mention threshold for short texts or improve dialogue-only character detection
2. **Priority 2:** Physical description attribution in profiles (Profiles 7 → 8.0) — fix first-person narrator physical description misattribution in profile generation prompt
3. **Priority 3:** Pronunciation gaps (Pronunciation 7 → 8.0) — add missing foreign terms, reduce false positives

All three categories need +1.0 point improvement. Issues #1-3 are the primary blockers.
