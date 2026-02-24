# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 3
- **Phase:** awaiting_analysis
- **baseline_score:** 6.55
- **Competitive Mode:** single

## Output Files
- HTML: ../output/gatsby/report.html
- JSON: ../output/gatsby/analysis.json

## Latest Scores
- Structure Detection: 10/10 ✓
- Character Extraction: 5/10 ✗ (FAILING)
  - Completeness: 7/10
  - Identity Resolution: 3/10 ← primary blocker (5 major false splits, unchanged)
  - Alias Grouping: 5.5/10 (Gatsby aliases improved)
- Character Profiles: 3/10 ✗ (FAILING)
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 7.5/10 ✗ (FAILING)
- HTML Presentation: 9/10 ✓
- **Overall: 7.15/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold: Characters 5, Profiles 3, Pronunciation 7.5)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.55 | — | Baseline. main_cast pipeline failed; massive false splits; profiles catastrophically wrong |
| 2 | 7.15 | +0.60 | Fix A partially worked (Gatsby aliases resolved); main_cast STILL fails; IPA corruption fixed |

## Pipeline Notes (Attempt 2)
- Analysis completed in 78m 34s
- 9 chapters detected (correct)
- 23 characters total: 21 from supporting_cast + 2 from F6 reconciliation (both are "the butler" duplicates)
- **Main cast pipeline STILL produced 0 characters** — "V2 Step 3.1 FALLBACK: main_cast empty after grounding"
- 133 pronunciation flags, 114 with IPA (85%), 0 corrupt IPA entries (Fix B worked ✓)
- Improvements from Fix A:
  - Jay Gatsby: aliases correctly resolved (Gatsby, James Gatz, Gatz) ✓
  - Dan Cody: aliases [Cody] ✓
  - Meyer Wolfshiem: aliases [Wolfshiem] ✓
  - George Wilson / Myrtle Wilson: aliases [George] / [Myrtle] ✓
- Persistent failures:
  - main_cast pipeline still produces 0 characters after grounding (2nd failure on same path)
  - Tom/Tom Buchanan still split; Jordan/Jordan Baker still split; Nick/Carraway still split
  - "Jordan" (supporting_4) still incorrectly marked as narrator
  - Relationships still catastrophically wrong (same labels: wife, mother, husband)
  - "the butler" / "The butler" duplicated from F6 reconciliation (case difference)
  - Owl Eyes and Henry C. Gatz NOT in character list despite being in Ch 9 characters_present

## Current Issues (Priority Order)

### CRITICAL

1. **Main cast pipeline grounding failure — 2nd consecutive failure** [Identity Resolution]
   - Problem: The main_cast pipeline produces 0 characters after the grounding step. Fix A (injecting `characters_present` into summaries) provided the LLM with correct character names, but the grounding step STILL rejects all candidates. This is the root cause of all identity resolution failures.
   - Evidence: `main_cast_ids: 0`, `supporting_ids: 21`, log warning "V2 Step 3.1 FALLBACK: main_cast empty after grounding"
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` — the grounding function
   - **ESCALATION NOTE:** This is the 2nd attempt modifying the character extraction path without fixing grounding. Fix A modified `src/agents/characters.py` (upstream data), but the grounding logic itself in `main_cast.py` was never examined. The fix phase MUST read and debug the grounding function directly — not just feed it better data.
   - Suggested approach: Add debug logging to the grounding step to see what candidates it receives and why it rejects them. The grounding criteria may be too strict, or the candidate format may not match what grounding expects.

2. **5 major false character splits** [Identity Resolution]
   - Problem: Same as attempt 1 — all unchanged:
     - "Tom" (191 mentions) + "Tom Buchanan" (22 mentions) — **same person**
     - "Jordan" (73 mentions) + "Jordan Baker" (40 mentions) — **same person**
     - "Nick" (24 mentions) + "Carraway" (10 mentions) — **same person** (Nick Carraway)
     - "Daisy" (186 mentions) — should be "Daisy Buchanan"
     - "Wilson" (77 mentions) — ambiguous between George Wilson and Myrtle Wilson
   - Evidence: All have `supporting_*` IDs with empty alias lists (no merge happened)
   - Root cause: Downstream of Issue #1 — supporting_cast pipeline doesn't perform first-name/full-name alias merging
   - Fix: Primary fix is Issue #1. If main_cast can't be fixed, add a post-processing merge step for obvious first-name/full-name pairs

3. **Wrong narrator assignment** [Identity Resolution]
   - Problem: "Jordan" (supporting_4) is marked `is_narrator: True`. The actual narrator is Nick Carraway.
   - Evidence: HTML report shows Jordan with "First-Person Narrator" badge. The profile text even says "The character 'Jordan' is not a distinct person... appears to be a misattribution of the narrator Nick Carraway"
   - Root cause: Pipeline correctly identifies "Nick Carraway" as narrator but can't match to any character because Nick/Carraway are split entries with no full-name match
   - Location: Narrator assignment fallback in `src/analyzer.py` or `src/pipeline/character_extraction_v2/`
   - Fix: If main_cast is fixed, Nick Carraway will exist as a single entry. If not, the narrator fallback should fuzzy-match "Nick Carraway" against "Nick" (first name match) rather than assigning to an arbitrary character.

4. **Relationships catastrophically wrong** [Profiles]
   - Problem: Relationship labels are nonsensical — the LLM is forced to pick from a restricted enum:
     - Jay Gatsby → Nick: "wife" (WRONG — friend/neighbor)
     - Jay Gatsby → Daisy: "wife" (WRONG — romantic interest, not married)
     - Jay Gatsby → Tom Buchanan: "wife" (WRONG — rival)
     - Jay Gatsby → Meyer Wolfshiem: "husband" (WRONG — business associate)
     - Jay Gatsby → Wilson: "sister" (WRONG)
     - Daisy → Jay Gatsby: "mother" (WRONG — romantic interest)
     - Tom Buchanan → Myrtle Wilson: "husband" (WRONG — affair partner)
     - Jordan Baker → Daisy: "wife" (WRONG — friends)
     - Myrtle Wilson → Catherine: "husband" (WRONG — sisters)
   - Evidence: `jq` extraction shows virtually every relationship has a wrong label
   - Location: `src/pipeline/character_extraction_v2/` — find the relationship extraction prompt and the allowed relationship types enum
   - Fix: The relationship type enum likely only includes family/marital labels (wife, husband, mother, father, sister, son). It MUST be expanded to include: friend, romantic_interest, rival, employer, employee, business_associate, mentor, neighbor, acquaintance, etc. This is a prompt/schema fix, not a pipeline logic fix.

### HIGH

5. **No personality traits or speech patterns** [Profiles]
   - Problem: All 23 characters have `personality_traits: null` and `speech_pattern: null`. Critical for narrators — Gatsby's "old sport" catchphrase, Wolfshiem's accent (Oggsford, gonnegtion), Tom's aggressive speaking style are all missing.
   - Evidence: All null in analysis.json
   - Location: Profile generation in `src/pipeline/character_extraction_v2/`
   - Fix: Check if the profile prompt requests personality traits and speech patterns. If the fields exist in the schema but aren't being populated, the prompt may not be extracting them.

6. **Duplicate "the butler" entries** [Completeness]
   - Problem: F6 reconciliation produced two entries: "the butler" (id: `a939b1174a88`) and "The butler" (id: `431ff1f64d63`), both with 13 mentions. These are identical except for capitalization.
   - Evidence: Two hash-ID entries in character list with same mention count
   - Location: F6 reconciliation in `src/analyzer.py` (~line 1220-1240) — case-insensitive dedup needed
   - Fix: Add case-insensitive matching when reconciling F6 characters to prevent duplicates

7. **Missing Owl Eyes and Henry C. Gatz** [Completeness]
   - Problem: Both appear in Ch 9 `characters_present` list ("The owl-eyed man", "Henry C. Gatz") but neither made it into the final character list. Both are narratively significant.
   - Evidence: Ch 9 characters_present includes them; final output does not
   - Location: F6 reconciliation should have caught these from characters_present data
   - Fix: Check why F6 reconciliation picked up "the butler" (twice!) but not "Henry C. Gatz" or "Owl Eyes". May be a mention-count threshold issue.

8. **Jordan's physical_description contains wrong narrative text** [Profiles]
   - Problem: "Jordan" (supporting_4, the falsely-split entry) has physical_description: "a young man at the office suggested that we take a house together in a commuting town..." — this is Nick's narrative about renting a house, not a physical description.
   - Evidence: Direct from analysis.json
   - Location: Profile extraction prompt — LLM returned arbitrary narrative text instead of physical description
   - Fix: The profile prompt needs stricter instructions. Also, if main_cast is fixed, "Jordan" as a separate entry won't exist.

9. **Gatsby falsely attributed with Wolfshiem's physical traits** [Profiles]
   - Problem: Jay Gatsby's physical_description mentions "tragic nose" — this is actually Meyer Wolfshiem's distinctive feature, not Gatsby's. Wolfshiem's profile correctly notes "Tragic nose" as well.
   - Evidence: Compare Gatsby and Wolfshiem entries in analysis.json
   - Fix: Profile extraction may be confusing co-occurring characters. Likely downstream of chunking — if Gatsby and Wolfshiem appear in the same text chunk, the LLM may misattribute physical features.

### MEDIUM

10. **Pronunciation false positives** [Pronunciation]
    - Problem: Common English words "kitchen" and "cigarette" flagged as category "foreign". Also "week" flagged as foreign.
    - Evidence: All three in pronunciation list with category "foreign"
    - Location: `src/pipeline/pronunciation_guide/` extraction or filtering logic
    - Fix: Add common-word exclusion list for everyday English words of foreign etymological origin

11. **92 "unknown" category pronunciations** [Pronunciation]
    - Problem: 92 of 133 pronunciations categorized as "unknown". Many are actually useful entries (dialect: Oggsford, gonnegtion, comin; proper nouns: Montauk, Tuolomee; archaic: plagiaristic, murmurous) but the category is unhelpful.
    - Evidence: Category distribution: unknown: 92, homograph: 19, foreign: 19, proper_noun: 3
    - Fix: Improve the categorization prompt. Most "unknown" entries are classifiable as dialect, proper_noun, or archaic/literary.

12. **Homographs lack IPA** [Pronunciation]
    - Problem: All 19 homograph entries (minute, live, close, wind, read, does, subject, row, excuse, elaborate...) have `ipa: null`. Providing both pronunciations for each homograph would be more useful for narrators.
    - Evidence: All homograph entries in analysis.json have null IPA
    - Fix: The pronunciation pipeline should provide both IPA variants for homographs (e.g., /rɛd/ vs /riːd/ for "read")

### LOW

13. **Daisy and Myrtle Wilson lack physical descriptions** [Profiles]
    - Problem: Daisy (white dresses, golden voice, blonde) and Myrtle (stout, thick-bodied, vitality) have no physical_description despite being richly described in the text.
    - Fix: Would be resolved if profile extraction prompt is improved (Issue #5/8/9 fixes)

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
- Character Extraction: Only 5 LLM calls, 54s total — very fast, suggesting minimal processing
- Character Profiles: 63 LLM calls, 2224s — bulk of time, but profiles are still bad
- All character confidence is MEDIUM (0 HIGH) — pipeline isn't confident
- Character Profiles: All HIGH confidence despite catastrophically wrong relationships — confidence scoring is broken for profiles
- No LLM retries or JSON parse failures across any stage

## Fix History

### flowers_for_algernon — Deferred (image-based PDF, no OCR available)
- **Issue:** Flowers_For_Algernon.pdf is a scanned/image-based PDF — 0 words extracted
- **Root cause:** Missing system dependency: tesseract-ocr (required by ocrmypdf / pytesseract)
- **Action:** Moved flowers_for_algernon to the END of manifest.texts so the loop continues with text-extractable books
- **Resolution:** When tesseract is installed, flowers_for_algernon will be re-attempted.

### gatsby — Attempt 2 Fixes

**Fix A: Include `characters_present` in summaries for main_cast LLM extraction** [CRITICAL - Issues #1, #2, #3]
- **Root cause:** `src/agents/characters.py:_get_chapter_summaries():1007-1012` returns only `s.summary`, discarding the structured `s.characters_present` field.
- **Fix:** Modified `_get_chapter_summaries()` to prefix each chapter summary with `[Characters present: ...]` when the field is populated.
- **Result:** PARTIAL SUCCESS — Jay Gatsby now has correct aliases (Gatsby, James Gatz, Gatz). But main_cast grounding STILL rejects all candidates. The fix improved data quality but didn't address the grounding logic itself.

**Fix B: IPA validation to reject corrupt entries** [MEDIUM - Issue #10]
- **Fix:** Added `_is_valid_ipa()` function that rejects IPA values containing non-IPA Unicode characters.
- **Result:** SUCCESS — 0 corrupt IPA entries in attempt 2 output (was 1 in attempt 1).

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | (baseline — no fixes yet) | — | — |
| 2 | Main cast pipeline failure (data) | `src/agents/characters.py` | Partial — aliases improved but grounding still fails |
| 2 | IPA corruption | `src/pipeline/pronunciation_guide/enricher.py` | Fixed ✓ |
| 3 | Main cast grounding failure (model JSON format) | `src/pipeline/character_extraction_v2/main_cast.py` | Changed both prompts from bare-array to `{"characters":[...]}` dict wrapper. qwen3-next returns error dicts for bare array requests; `_parse_pass1_results` already handles "characters" wrapper key. |
| 3 | Relationship labels wrong (secondary call overwrites) | `src/analyzer.py` | Secondary structuring call now only writes relationships if primary call produced none; added relationship examples to template. |
| 3 | Pronunciation false positives (kitchen, cigarette, week) | `src/pipeline/pronunciation_guide/proposers/foreign_proposer.py` | Added to ENGLISH_EXCEPTIONS: kitchen, chicken, thicken, quicken, stricken, sicken, cigarette, week, year, cent. |
| 3 | 92 UNKNOWN pronunciation entries | `src/pipeline/pronunciation_guide/consolidator.py` | Capitalized UNKNOWN words upgraded to PROPER_NOUN in `_build_entry()`. |

## Next Action
Run PROMPT_analyze.md for attempt 3.

### Attempt 3 Fixes Applied
1. **Fix C: main_cast prompts changed to dict wrapper format** — Both `CHARACTER_IDENTIFICATION_PROMPT` and `MAIN_CAST_PROMPT` now request `{"characters":[...]}` instead of bare JSON array. Root cause: qwen3-next returns error dicts when forced to produce bare arrays via json_mode.
2. **Fix D: Secondary relationship call no longer overwrites primary** — `analyzer.py` secondary structuring call only sets relationships when primary produced none. Template updated with proper relationship type examples.
3. **Fix E: Pronunciation false positive exclusions** — Added kitchen/cigarette/week/chicken etc. to ENGLISH_EXCEPTIONS.
4. **Fix F: UNKNOWN → PROPER_NOUN reclassification** — Capitalized UNKNOWN words upgraded to PROPER_NOUN in consolidator.
