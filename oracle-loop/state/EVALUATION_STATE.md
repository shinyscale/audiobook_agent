# Current Evaluation State

## Active Text
- **Name:** cask_of_amontillado
- **Attempt:** 1
- **Phase:** awaiting_analysis
- **baseline_score:** 6.10
- **Competitive Mode:** none

## Output Files
- HTML: ../output/cask_of_amontillado/report.html
- JSON: ../output/cask_of_amontillado/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 3/10 ✗ (FAILING)
  - Completeness: 2/10
  - Identity Resolution: 3/10
  - Alias Grouping: 6/10
- Character Profiles: 2/10 ✗ (FAILING)
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 7/10 ✗ (FAILING)
- HTML Presentation: 8.5/10 ✓
- **Overall: 6.10/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold: Characters, Profiles, Pronunciation)

## Current Issues (Priority Order)

### CRITICAL

1. **Protagonist Montresor completely missing from character list** [Completeness]
   - Problem: The narrator/protagonist Montresor does not appear as a character entry at all. Only Fortunato (14 mentions) is extracted.
   - Evidence: "Montresor" appears 3 times in the source text: "the catacombs of the Montresors" (line 54), "The Montresors" (line 94), and "For the love of God, Montresor!" (line 170). As the first-person narrator, he uses "I" throughout and is rarely named.
   - Root cause: The V2 character extraction pipeline likely has a mention threshold that Montresor doesn't meet (only ~3 name occurrences). First-person narrators who rarely name themselves fall through the cracks.
   - Location: `src/pipeline/character_extraction_v2/` — likely the main_cast extraction pass or the narrator detection logic
   - Fix approach: The pipeline needs to better handle first-person narrators: (a) detect first-person narrative voice, (b) search for any name associated with "I" (e.g., when other characters address the narrator by name), (c) ensure the narrator appears in the character list. Alternatively, lower the mention threshold to capture characters with ≥3 mentions in short texts.

2. **Fortunato incorrectly flagged as first-person narrator** [Identity Resolution]
   - Problem: Fortunato's entry has `is_narrator: true` and the HTML displays "📖 First-Person Narrator" badge on Fortunato. Montresor is the narrator, not Fortunato.
   - Evidence: The story is told from Montresor's perspective ("I had borne...I vowed revenge...I said"). Fortunato is the victim, not the narrator.
   - Root cause: With Montresor absent from the character list, the narrator detection likely fell back to the only available character (Fortunato) and incorrectly assigned narrator status.
   - Location: Narrator detection logic in the V2 pipeline or `src/analyzer.py`
   - Fix approach: Fix #1 (extract Montresor) should resolve this. The narrator flag should go on Montresor, not Fortunato.

3. **Fortunato's profile contains Montresor's personality traits (character conflation)** [Profiles]
   - Problem: Fortunato's profile describes him as "manipulative and vengeful individual who conceals malicious intent behind a facade of friendship" with traits "vengeful, manipulative, deceptive, calculating, sadistic" and voice "calm, deceptive, and increasingly mocking". These ALL describe Montresor (the narrator), not Fortunato.
   - Evidence: Fortunato is actually a proud wine connoisseur, boisterous when drunk, wearing a jester costume with jingling bells. He becomes bewildered and desperate when chained. His voice should be described as drunk/boisterous initially, then terrified/pleading.
   - Root cause: The profile LLM generated traits from the first-person narrative voice and attributed them to the only extracted character (Fortunato) instead of the narrator.
   - Location: Profile generation in `src/analyzer.py` (`_generate_character_profile`)
   - Fix approach: Fixing #1 (extract Montresor separately) should naturally fix the profile attribution. The LLM profile generation should correctly assign manipulative traits to Montresor and victim traits to Fortunato once both exist.

### HIGH

4. **Luchresi missing as a character** [Completeness]
   - Problem: Luchresi is mentioned 6 times in the source text (all in dialogue) but does not appear in the character list.
   - Evidence: Luchresi is a named character used by Montresor as a ploy to manipulate Fortunato's pride. He's mentioned in lines 30, 32, 42, 48, 74, 144.
   - Root cause: Luchresi never physically appears — he's only referenced in dialogue. The extraction pipeline may not capture characters who are only mentioned/discussed. Or 6 mentions may be below the threshold.
   - Location: V2 main_cast or supporting_cast extraction in `src/pipeline/character_extraction_v2/`
   - Fix approach: Characters mentioned ≥3 times by name should be extracted even if they don't physically appear. A short-text mode or lower threshold for stories with few characters would help.

5. **Missing key pronunciation entries** [Pronunciation]
   - Problem: Several important foreign terms are missing from the pronunciation guide:
     - "Nemo me impune lacessit" (Latin family motto, line 102) — critical for narrator
     - "Medoc" (French wine, lines 78, 106, 110) — 3 occurrences
     - "palazzo" (Italian, lines 50, 162, 166) — 3 occurrences
     - "De Grave" (French wine name, line 112) — 1 occurrence
   - Evidence: These are foreign-language terms that a narrator would need pronunciation guidance for.
   - Location: `src/pipeline/pronunciation/` — the flagging logic may not catch multi-word foreign phrases or common-seeming foreign words
   - Fix approach: Improve foreign phrase detection; ensure Italian and French terms (palazzo, Medoc) are flagged; detect Latin phrases in quotes.

### MEDIUM

6. **Fortunato has no physical description** [Profiles]
   - Problem: `physical_description: null` despite the text providing a distinctive appearance: "The man wore motley. He had on a tight-fitting parti-striped dress, and his head was surmounted by the conical cap and bells."
   - Evidence: This costume description appears early in the story and is an iconic element.
   - Root cause: Profile generation failed to extract physical description, possibly due to the character conflation issue (#3).
   - Fix approach: Should resolve when #1-3 are fixed and profiles are regenerated.

7. **False positive pronunciation entries** [Pronunciation]
   - Problem: Common English words flagged unnecessarily:
     - "leer" — standard English word
     - "gesticulation" — standard English word
     - "flagon" — reasonably common English word
   - Evidence: A professional audiobook narrator would know these words without guidance.
   - Location: `src/pipeline/pronunciation/` — false positive filtering
   - Fix approach: Improve the common-word filter to exclude standard English vocabulary.

8. **Pronunciation note for "rheum" is self-contradictory** [Pronunciation]
   - Problem: Note says "rhymes with 'room' or 'seam'" — but "room" (/ruːm/) and "seam" (/siːm/) don't rhyme with each other. The IPA /ruːm/ is correct, so "rhymes with room" is right but "seam" is wrong.
   - Location: Pronunciation note generation
   - Fix approach: Minor LLM hallucination in notes; low priority.

### LOW

9. **Structure metadata incomplete**
   - Problem: Chapter title is null, start_line and end_line are null
   - Evidence: A single-section short story could still have a title and line range
   - This is cosmetic and doesn't affect narrator utility

10. **Fortunato's role listed as "protagonist"**
    - Problem: Fortunato is the victim/antagonist target, not the protagonist. Montresor is the protagonist.
    - Will resolve when Montresor is properly extracted as the protagonist.

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.10 | — (baseline) | Missing Montresor, narrator misattribution, profile conflation |

## Fix History

### Attempt 1 Fix — Vocative Narrator Name Resolution
- **Issue addressed:** Issues #1-3 (Montresor missing, narrator misattribution, profile conflation)
- **Root cause:** The summarizer generates summaries that say "the narrator" instead of "Montresor" (Montresor's name only appears once as a direct address by Fortunato). The character extraction pipeline extracted "the narrator" as a placeholder, but `_merge_narrator_placeholder` incorrectly merged it into Fortunato (highest mention count = 14) rather than finding Montresor's actual name.
- **Fix:** Added three new pipeline stages to `src/agents/characters.py`:
  1. `_find_narrator_name_from_vocative(text)`: searches raw text for direct address patterns (e.g., `, Montresor!`) to identify narrator's actual name. Prefers names with fewer total text mentions (narrator says "I", other characters say their name rarely).
  2. **Step 4.5**: After narrator detection, if narrator is a placeholder with no proper-name aliases, call `_find_narrator_name_from_vocative()` and add the found name as alias. Step 5.2b then upgrades "the narrator" → "Montresor".
  3. **Step 5.2c**: Re-search mentions for narrator-placeholder-upgraded characters (mention count was 0 from placeholder; now correctly counts actual text occurrences).
- **Universal invariant:** Works for ANY first-person narrative where the narrator is addressed by name in dialogue. Gate: `narrator_info.pov == "first-person"` + narrator is placeholder + no existing proper-name alias.
- **Files modified:**
  - `src/agents/characters.py` — Added Step 4.5, Step 5.2c, `_find_narrator_name_from_vocative` method
  - `tests/test_character_extraction_v2.py` — Updated line count limit to 9400
- **Smoke test:** PASS — `_find_narrator_name_from_vocative("The Cask of Amontillado - Poe.txt")` correctly returns "Montresor"; `_find_narrator_name_from_vocative("Monkey's Paw.txt")` returns "Morris" but Step 4.5 guards against third-person narratives (`narrator_info.pov == "first-person"` check). All 332 tests pass.
- **Cascade effects expected:** Fixing Montresor extraction → correct narrator attribution (Fortunato loses is_narrator flag) → profiles regenerated separately for each character (Montresor gets manipulative/vengeful traits, Fortunato gets victim/drunkard traits).

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | Issues #1-3 (Montresor missing, narrator misattrib, profile conflation) | `src/agents/characters.py`, `tests/test_character_extraction_v2.py` | awaiting_analysis |

## Configuration Notes
- Model: qwen3.5:122b-a10b for characters and summaries (good)
- Model: qwen3.5:35b-a3b for structure and pronunciation
- `character_llm_chunk_chars: 5000` — adequate for this short text
- No obvious config issues; the problem is pipeline logic, not model/config

## Next Action
Re-run analysis to verify fix. Expected improvements:
- Issue #1 (Montresor missing): FIXED — vocative name search finds "Montresor" and adds as narrator alias
- Issue #2 (Fortunato as narrator): FIXED — narrator flag should transfer to Montresor
- Issue #3 (profile conflation): FIXED — separate characters get separate profiles
- Issue #4 (Luchresi missing): may improve if NER finds Luchresi ≥2 times in text (6 mentions in dialogue)
- Issue #5 (missing pronunciation): NOT addressed yet — needs separate iteration
