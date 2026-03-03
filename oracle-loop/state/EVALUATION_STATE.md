# Current Evaluation State

## Active Text
- **Name:** cask_of_amontillado
- **Attempt:** 3
- **Phase:** complete
- **baseline_score:** 6.10

## Output Files
- HTML: ../output/cask_of_amontillado/report.html
- JSON: ../output/cask_of_amontillado/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 9/10 ✓
  - Completeness: 9/10
  - Identity Resolution: 10/10
  - Alias Grouping: 9/10
- Character Profiles: 8.5/10 ✓
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 8.65/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** PASS — all categories at or above threshold

## Evaluation Details

### Structure Detection: 9/10
- Correctly identifies as single continuous text (no chapters) — 1 structure element
- Short story with no internal divisions — this is the right result
- Minor: title/start_line/end_line are null (cosmetic, doesn't affect narrator utility)

### Character Extraction: 9/10
- **Completeness: 9/10** — All 3 named characters present (Montresor, Fortunato, Luchresi) plus family reference ("the Montresors"). Luchresi extraction via F6b fix is WORKING (6 mentions, hash ID d7d5db997d33). For a 3-character story, 100% character capture.
- **Identity Resolution: 10/10** — No false splits, no false merges. Montresor correctly identified as narrator with only 1 name mention (correct — his name appears once in text when Fortunato calls out to him).
- **Alias Grouping: 9/10** — Clean alias state. No self-aliases or invalid entries.

### Character Profiles: 8.5/10
- **Montresor:** Rich profile. Physical description correctly attributed (mask, roquelaire, trowel). Personality accurate ("calculating, deceptive, manipulative"). Voice guidance excellent ("calm, ironic, and controlled" with verbal tics and example quotes).
- **Fortunato:** Good profile. Physical description correct in JSON (jester costume, parti-striped dress, cap and bells). Personality captures arc from "proud, trustful" to "desperate." Voice guidance captures tonal shift and verbal tics ("he! he! he!").
- **Misattribution fix VERIFIED:** Montresor's clothes (silk mask, roquelaire) are on Montresor. Fortunato's clothes (jester costume) are on Fortunato. The first-person narrator attribution fix is working.
- Minor: Fortunato's appearance.summary is null (while distinguishing_features is populated), causing HTML not to render an Appearance section for Fortunato despite data being in JSON.

### Chapter Summaries: 8.5/10
- Single comprehensive summary captures all key narrative beats: carnival setting, Amontillado ruse, catacomb descent, wine manipulation, chaining, walling up, 50-year coda.
- Accurate to text — no hallucinations detected.
- Good narrator utility — provides the narrative arc and emotional progression.
- Minor: Doesn't mention Luchresi by name (he's the manipulation ploy) or the family motto. Acceptable for summary length.

### Pronunciation Guide: 8/10
- 13 entries, all with IPA. No false positives (leer/flagon/gesticulation fix WORKING).
- Good entries: Luchresi, Montresor(s), Amontillado, nitre, roquelaire, rheum, impune, requiescat, hearkened
- Useful homograph entries: row, close, entrance — narrators need to know which pronunciation to use in context
- Minor gaps: "Medoc" (French wine), "palazzo" (Italian), "De Grave" (French wine) still missing. "Nemo me impune lacessit" not flagged as full phrase. These would be nice-to-have but the guide is functional.

### HTML Presentation: 8.5/10
- Navigation functional, tabbed layout works
- Rich profile rendering with source evidence citations (7 for Montresor, 8 for Fortunato)
- Voice guidance prominently displayed with example quotes
- Pronunciation guide with chapter view
- Minor: Fortunato's physical description not rendering in HTML (appearance.summary null) despite data being in JSON

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.10 | — (baseline) | Missing Montresor, narrator misattribution, profile conflation |
| 2 | 8.0 | +1.90 | Montresor extracted, narrator fixed, profiles improved; Luchresi still missing, pronunciation gaps |
| 3 | 8.65 | +2.55 | ALL PASS. Luchresi extracted, descriptions correct, false positives removed |

## Fix History

### Attempt 1 Fix — Vocative Narrator Name Resolution
- **Issues addressed:** #1-3 from attempt 1 (Montresor missing, narrator misattribution, profile conflation)
- **Result:** All three FIXED. Montresor now extracted as protagonist/narrator. Fortunato no longer flagged as narrator. Profiles have correct personality traits per character.
- **Files modified:** `src/agents/characters.py`, `tests/test_character_extraction_v2.py`

### Attempt 2 Fix — 3-part fix
**1. Luchresi extraction (Character Extraction Completeness)**
- **Fix:** Added F6b — scans `mentioned_characters` with adaptive text-mention threshold (2 for short texts, 3 for long).
- **Result:** FIXED. Luchresi present with 6 mentions via F6b.
- **File:** `src/analyzer.py`

**2. Physical description misattribution (Character Profiles)**
- **Fix:** Added `narrator_name` parameter to `_generate_character_profile()`. Non-narrator characters in 1st-person narrative get prompt: "All 'I' descriptions belong to {narrator_name}, NOT {character_name}."
- **Result:** FIXED. Montresor has his clothes; Fortunato has jester costume.
- **File:** `src/analyzer.py`

**3. Pronunciation false positives (Pronunciation Guide)**
- **Fix:** Added "leer", "flagon", "gesticulation" (+ inflected forms) to `COMMON_WORDS_WHITELIST`.
- **Result:** FIXED. All three removed from output.
- **File:** `src/pipeline/pronunciation_guide/proposers/cmu_proposer.py`

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | Montresor missing + narrator misattrib + profile conflation | `src/agents/characters.py`, `tests/test_character_extraction_v2.py` | Fixed |
| 2 | Luchresi missing | `src/analyzer.py` (F6b) | Fixed |
| 2 | Profile misattribution | `src/analyzer.py` (narrator_name) | Fixed |
| 2 | Pronunciation false positives | `src/pipeline/pronunciation_guide/proposers/cmu_proposer.py` | Fixed |

## Configuration Notes
- Model: qwen3.5:122b-a10b for characters and summaries (good)
- Model: qwen3.5:35b-a3b for structure and pronunciation
- `character_llm_chunk_chars: 5000` — adequate for this short text
- No config issues detected; 0 LLM retries across all stages

## Next Action
PASS — Ready to advance to next text (masque_of_red_death).
