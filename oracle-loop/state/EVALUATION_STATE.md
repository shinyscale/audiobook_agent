# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 1
- **Phase:** awaiting_analysis
- **baseline_score:** 6.55
- **Competitive Mode:** single

## Output Files
- HTML: ../output/gatsby/report.html
- JSON: ../output/gatsby/analysis.json

## Latest Scores
- Structure Detection: 10/10 ✓
- Character Extraction: 4/10 ✗ (FAILING)
  - Completeness: 8/10
  - Identity Resolution: 3/10 ← primary blocker (5 major false splits)
  - Alias Grouping: 5/10
- Character Profiles: 2/10 ✗ (FAILING)
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 7.5/10 ✗ (FAILING)
- HTML Presentation: 9/10 ✓
- **Overall: 6.55/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.55 | — | Baseline. main_cast pipeline failed; massive false splits; profiles catastrophically wrong |

## Pipeline Notes
- Analysis completed in 100m 6s
- 9 chapters detected (correct)
- 22 characters extracted — **0 from main_cast, 21 from supporting_cast, 1 from F6 reconciliation**
- 134 pronunciation flags (115 with IPA)
- Warnings:
  - "V2 Step 3.1 FALLBACK: main_cast empty after grounding" — **ROOT CAUSE of character issues**
  - "Two-pass extraction returned 0 characters; retrying with single-pass" — character extraction fallback triggered
  - "Narrator 'Nick Carraway' identified but NOT found in main_cast" — narrator detection found correct narrator but couldn't link it
  - "LLM marker proposer returned non-list: dict" (20x) — structure agent response parsing issue (didn't affect structure quality)

## Current Issues (Priority Order)

### CRITICAL

1. **Main cast pipeline completely failed — 0 characters from main_cast** [Identity Resolution]
   - Problem: All 22 characters came through supporting_cast (IDs: `supporting_*`) or F6 reconciliation. The main_cast pipeline produced 0 characters after grounding. This means no proper alias merging or identity resolution was performed.
   - Evidence: `main_cast_ids: 0`, `supporting_ids: 21`, warning "V2 Step 3.1 FALLBACK: main_cast empty after grounding"
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` — the grounding step is rejecting all main cast candidates
   - Fix: Investigate why main_cast grounding fails for this text. The fallback produced supporting_cast entries with no alias resolution.

2. **5 major false character splits** [Identity Resolution]
   - Problem: The following characters are split into separate entries:
     - "Tom" (191 mentions) ≠ "Tom Buchanan" (22 mentions) — **same person**
     - "Jordan" (73 mentions) ≠ "Jordan Baker" (40 mentions) — **same person**
     - "Nick" (24 mentions) ≠ "Carraway" (10 mentions) — **same person** (Nick Carraway)
     - "Daisy" (186 mentions) — missing surname, should be "Daisy Buchanan"
     - "Wilson" (77 mentions) ≠ "George Wilson" (14) / "Myrtle Wilson" (23) — ambiguous, unresolved
   - Evidence: All `supporting_*` IDs, no alias lists on fragmented entries
   - Location: This is a downstream consequence of Issue #1. Supporting cast pipeline (`src/pipeline/character_extraction_v2/supporting.py`) doesn't perform the alias merging that main_cast does.
   - Fix: Fix main_cast pipeline (Issue #1) to resolve this. Alternatively, add post-hoc merge logic to supporting_cast for first-name/full-name matches.

3. **Wrong narrator identification** [Identity Resolution]
   - Problem: "Jordan" (supporting_4) is marked `is_narrator: True`. The actual narrator of The Great Gatsby is Nick Carraway.
   - Evidence: The pipeline warning says "Narrator 'Nick Carraway' identified but NOT found in main_cast" — it correctly detected Nick as narrator but couldn't match him because main_cast was empty, and "Nick" and "Carraway" are split entries.
   - Location: Narrator assignment logic in `src/analyzer.py` or `src/pipeline/character_extraction_v2/` — when the identified narrator doesn't match any character, it apparently falls back to an incorrect assignment.
   - Fix: Fix main_cast pipeline (Issue #1) so "Nick Carraway" exists as a character entry. Also fix the narrator fallback to not assign narrator to an arbitrary character.

4. **Character relationships are catastrophically wrong** [Profiles]
   - Problem: Relationship labels are nonsensical:
     - Daisy → Jay Gatsby: "mother" (WRONG — romantic interest)
     - Daisy → Tom Buchanan: "wife" (direction is backwards — Tom is Daisy's husband)
     - Tom → George Wilson: "husband" (WRONG)
     - Jay Gatsby → Dan Cody: "son" (WRONG — Cody was Gatsby's mentor)
     - Jay Gatsby → Meyer Wolfshiem: "husband" (WRONG — business associate)
     - Jordan → Nick: "mother" (WRONG — romantic interest)
   - Evidence: `jq '.characters[] | select(.mention_count > 30) | {name: .canonical_name, rels: .relationships}'` shows all major characters have wrong relationship labels
   - Location: `src/pipeline/character_extraction_v2/` profile generation, or the LLM relationship extraction prompt
   - Fix: The relationship extraction prompt likely uses an enum that doesn't include "romantic interest", "mentor/protégé", "business associate" etc., forcing the LLM to pick from wrong labels. Check the relationship schema and expand allowed values.

### HIGH

5. **Most character profiles lack physical descriptions** [Profiles]
   - Problem: Only 10/22 characters have physical_description populated. Major characters like Jay Gatsby (described as having a "rare smile"), Daisy (blonde, white dresses), Tom (hulking, physically imposing), and Nick have no physical descriptions.
   - Evidence: `with_desc: 10/22`, Gatsby/Tom/Daisy/Nick all have `physical_description: None`
   - Location: Profile extraction in character_extraction_v2 or the profile generation stage
   - Fix: The profile LLM calls may be timing out or the text chunks don't include relevant descriptive passages.

6. **Jordan Baker's physical_description contains wrong text** [Profiles]
   - Problem: Jordan's `physical_description` field contains a passage about Nick renting a house: "a young man at the office suggested that we take a house together in a commuting town..." This is not a physical description at all — it's narrative text from Chapter 1.
   - Evidence: Direct extraction from analysis.json
   - Location: Profile extraction prompt or text chunking — the LLM is returning arbitrary text instead of physical descriptions
   - Fix: Likely a prompt issue in profile generation. The LLM needs clearer instructions to extract only physical appearance details.

7. **No personality traits or speech patterns extracted** [Profiles]
   - Problem: All characters have `personality_traits: NONE` and `speech_pattern: NONE`. Gatsby's mannerisms ("old sport"), Wolfshiem's accent (dialect spellings), Tom's aggressive style are all missing.
   - Evidence: All personality_traits and speech_pattern fields are empty/NONE
   - Location: Profile extraction pipeline
   - Fix: These fields may not be populated by the current pipeline, or the LLM prompt doesn't request them.

8. **Missing minor characters: Owl Eyes, Henry C. Gatz** [Completeness]
   - Problem: "Owl Eyes" (the bespectacled man in Gatsby's library, Ch 3 and funeral in Ch 9) and Henry C. Gatz (Gatsby's father, Ch 9) are not in the character list. Both are narratively significant.
   - Evidence: Neither name appears in the 22-character output
   - Location: Character extraction — Owl Eyes may be missed because it's a nickname, Henry Gatz appears only in the final chapter
   - Fix: Lower mention threshold or improve detection for nicknamed characters. These may also be resolved if main_cast pipeline is fixed.

### MEDIUM

9. **Pronunciation false positives** [Pronunciation]
   - Problem: Common English words flagged as "foreign": "kitchen", "cigarette". These are not unusual to English speakers.
   - Evidence: Both in pronunciation list with category "foreign"
   - Location: `src/pipeline/` pronunciation extraction prompt or filtering logic
   - Fix: Add a common-word exclusion list or improve the LLM prompt to skip everyday English words of foreign origin.

10. **Corrupt IPA entry** [Pronunciation]
    - Problem: "flavoured" has IPA `/ˈflえvəd/` containing a Japanese hiragana character (え) instead of proper IPA
    - Evidence: Direct from analysis.json pronunciation entry
    - Location: LLM IPA generation — model output corruption
    - Fix: Add IPA validation to reject entries containing non-IPA Unicode characters

11. **92 "unknown" category pronunciations** [Pronunciation]
    - Problem: 92 of 134 pronunciations are categorized as "unknown" rather than proper_noun, foreign, or homograph. Many are legitimately useful (dialect spellings, invented names from Gatsby's party guest list) but the categorization is unhelpful for narrators.
    - Evidence: Category distribution: unknown: 92, homograph: 19, foreign: 19, proper_noun: 4
    - Fix: Improve category assignment. Most "unknown" entries are either proper_noun (guest names), dialect (Oggsford, gonnegtion), or archaic/literary words.

### LOW

12. **Character count includes very minor characters** [Completeness]
    - Problem: Characters like "Lucille" (6 mentions), "Rosy" (6 mentions), "Sloane" (10 mentions) are borderline inclusions. Not wrong, but adds noise.
    - Not actionable — minor characters are acceptable per rubric.

## Configuration Audit

### Model Configuration
- Model: qwen3-next:80b-a3b-instruct-q8_0 (Ollama) — same model for all agents
- Context length: 32768 — adequate for Gatsby (48K words)
- Temperature: 0.7 for all agents — may be too high for character extraction (structured task)
- think_mode: false — disables chain-of-thought, may hurt quality

### Chunking Configuration
- `character_llm_chunk_chars`: 5000 — **potentially too small** for proper character identification across chapter context
- `summary_chunk_words`: 2500 — adequate
- `character_mention_context_chars`: 250 — small, may miss relationship context

### Processing Issues
- Character Extraction: Only 5 LLM calls, 58s total — very fast, suggesting minimal processing
- Character Profiles: 58 LLM calls, 3334s — this is where most time was spent
- All character confidence is MEDIUM (0 HIGH) — the pipeline isn't confident in its results
- Character Profiles: All HIGH confidence despite catastrophically wrong relationships — confidence scoring is broken for profiles

## Fix History

### flowers_for_algernon — Deferred (image-based PDF, no OCR available)
- **Issue:** Flowers_For_Algernon.pdf is a scanned/image-based PDF — 0 words extracted
- **Root cause:** Missing system dependency: tesseract-ocr (required by ocrmypdf / pytesseract)
- **Action:** Moved flowers_for_algernon to the END of manifest.texts so the loop continues with text-extractable books
- **Resolution:** When tesseract is installed, flowers_for_algernon will be re-attempted.

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | (baseline — no fixes yet) | — | — |
| 2 | Main cast pipeline failure + IPA corruption | `src/agents/characters.py`, `src/pipeline/pronunciation_guide/enricher.py` | Awaiting analysis |

## Fix History

### gatsby — Attempt 2 Fixes

**Fix A: Include `characters_present` in summaries for main_cast LLM extraction** [CRITICAL - Issues #1, #2, #3]
- **Root cause:** `src/agents/characters.py:_get_chapter_summaries():1007-1012` returns only `s.summary`, discarding the structured `s.characters_present` field. The `CHARACTER_IDENTIFICATION_PROMPT` has a NOTE referencing `characters_present` lists but they were never actually included in the text — a disconnect between the prompt design and data flow.
- **Fix:** Modified `_get_chapter_summaries()` to prefix each chapter summary with `[Characters present: ...]` when the field is populated (from `s.characters_present` / `s.active_characters`). The LLM now receives e.g. `[Characters present: Nick Carraway, Tom Buchanan, Daisy Buchanan, Jordan Baker, Jay Gatsby]` before the chapter text.
- **Universality:** YES — `characters_present` is generated by the summarizer for ALL books. Falls back gracefully (no prefix added) when the field is empty.
- **Expected impact:** The LLM will now identify "Nick Carraway", "Jay Gatsby", "Daisy Buchanan" etc. as canonical names rather than descriptive handles. This should fix Issues #1 (main_cast populated), #2 (false splits resolved via alias merging), #3 (narrator found in main_cast), #8 (Owl Eyes/Henry Gatz visible in Ch 9 characters_present).
- **Smoke test:** Verified `characters_present` injection logic and confirmed no functional regressions (346 tests pass, 2 pre-existing failures in unrelated modules).

**Fix B: IPA validation to reject corrupt entries** [MEDIUM - Issue #10]
- **Root cause:** `src/pipeline/pronunciation_guide/enricher.py` accepts any string as IPA without validation. The LLM occasionally produces corrupted IPA containing non-Latin Unicode characters (e.g., hiragana 'え' U+3048 instead of IPA 'æ').
- **Fix:** Added `_is_valid_ipa()` function that rejects IPA values containing characters outside standard IPA Unicode ranges. Applied at all three points where IPA is assigned in `enrich_batch` and `enrich_single`.
- **Universality:** YES — corrupt IPA can occur with any model and any book.
- **Smoke test:** PASS — valid IPA strings pass, strings with hiragana/CJK are rejected.

## Next Action
Run PROMPT_analyze.md to re-analyze gatsby with the fixes applied.
