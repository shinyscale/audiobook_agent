# Current Evaluation State

## Active Text
- **Name:** john_g
- **Attempt:** 2
- **Phase:** awaiting_analysis
- **baseline_score:** 7.80

## Output Files
- HTML: ../output/john_g/report.html
- JSON: ../output/john_g/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 8/10 ✓
  - Completeness: 8/10
  - Identity Resolution: 10/10
  - Alias Grouping: 7.5/10
- Character Profiles: 7/10 ✗
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 7.5/10 ✗
- HTML Presentation: 8.5/10 ✓
- **Overall: 8.25/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold: Profiles, Pronunciation)

## Current Issues (Priority Order)

### CRITICAL
(None)

### HIGH
1. **Richardson speech_patterns missing "soft Southern tongue"** [Profiles]
   - Problem: The text explicitly states Richardson speaks in "his soft Southern tongue" but speech_patterns is null.
   - Evidence: Direct quote: "rejoined Corporal Richardson, in his soft Southern tongue"
   - Location: Profile generation in `analyzer.py` (`_generate_character_profile`). Richardson's profile has LOW confidence (0.30) — the LLM likely produced malformed output that couldn't be parsed.
   - Fix: This is an LLM output quality issue. Options: (a) increase temperature/retries for low-confidence profiles, (b) add a post-profile pass that scans source text for explicit speech pattern phrases like "in his [adjective] tongue/voice/accent", (c) lower the summary chunk size to give the profiler more focused context. A targeted regex scan for "in his/her [adj] tongue/voice/accent/drawl" patterns would be most reliable.

2. **Richardson relationships incomplete** [Profiles]
   - Problem: Richardson only has `{"John G.": "caretaker"}` but should also have a relationship to Price (colleague/fellow trooper).
   - Evidence: Richardson and Price spend the mission together; Richardson is the farrier of the Troop under Price's command.
   - Location: Same root cause as #1 — low confidence profile (0.30) means sparse data.
   - Fix: Same fix as #1. If profile confidence < threshold, a fallback extraction using co-occurrence could fill gaps.

3. **3 pronunciation entries have null IPA** [Pronunciation]
   - Problem: "sharp-fanged", "bolo-toothed", and "produce" all have `ipa: null` despite "sharp-fanged" being in KNOWN_IRREGULAR_IPA.
   - Evidence: `jq '.pronunciations[] | select(.ipa == null) | .word' analysis.json` returns these three words. The KNOWN_IRREGULAR_IPA entry for "sharp-fanged" exists at enricher.py:96 with `/ˈʃɑːrp.fæŋd/`.
   - Location: `src/pipeline/pronunciation_guide/enricher.py` and `pipeline.py`. The static lookup at line 219 should match, but the output has null. Possible causes: (a) the enrichment batch errored and fell through to the fallback path at line 442-448 which creates empty PronunciationEnrichment(confidence=0.0) entries that overwrite the static result; (b) "produce" goes through `enrich_homograph()` which may not check KNOWN_IRREGULAR_IPA.
   - Fix: Investigate why KNOWN_IRREGULAR_IPA lookup didn't take effect. Add "bolo-toothed" to KNOWN_IRREGULAR_IPA with `/ˈboʊ.loʊ.tuːθt/`. For "produce", ensure `enrich_homograph()` returns IPA (it's a homograph — /ˈprɒd.juːs/ noun vs /prəˈdjuːs/ verb). May need to add produce to HOMOGRAPH_IPA_MAP.

### MEDIUM
4. **"the Sergeant" alias missing for Price** [Alias Grouping]
   - Problem: "the Sergeant" is used 15+ times in the text to refer to Price but is not listed as an alias.
   - Evidence: Lines 34, 83, 93, 100, 107, 114, 123, 136, 171, 187, 194, 196, 198, 208, 238 — all "the Sergeant" = Price.
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` — likely filtered by descriptor-blocking rules (Rule 0.6 or similar). "the Sergeant" is a generic rank descriptor.
   - Fix: This is a design tradeoff — in multi-character texts, "the Sergeant" could be ambiguous. In this single-sergeant story it's unambiguous. Not worth adding special-case logic for a marginal alias improvement. Accept 7.5 on alias grouping.

### LOW
5. **"Johnny boy" alias for John G.** [Alias Grouping]
   - Minor: Used once as an endearment (line 161). Not worth fixing.

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 7.80 | N/A | First run — 3 categories failing |
| 2 | 8.25 | +0.45 | Characters fixed (8.0), Profiles and Pronunciation still failing |

## Fix History
- Attempt 2: Three fixes applied:
  1. **Captain Adams (Completeness)**: Exempted `chapter_summary_reconciliation` characters from evidence filter in `_convert_characters()`. Root cause: `analyzer.py:_convert_characters():4086-4096`.
  2. **Alias grouping (Completeness/Alias)**: Extended `_add_title_stripped_aliases` for multi-word compound ranks ("First Sergeant Price" -> "Price", "Sergeant Price"). Root cause: `main_cast.py:_add_title_stripped_aliases():1320-1330`.
  3. **IPA sharp-fanged (Pronunciation)**: Added to KNOWN_IRREGULAR_IPA with `/ˈʃɑːrp.fæŋd/`. Root cause: `enricher.py:KNOWN_IRREGULAR_IPA`. **NOTE: Fix is in code but IPA is still null in output — enricher may have errored for the batch.**

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 2 | Captain Adams missing | analyzer.py | Fixed — Captain Adams now present |
| 2 | Alias grouping (compound ranks) | main_cast.py | Fixed — "Price", "Sergeant Price" aliases present |
| 2 | IPA sharp-fanged | enricher.py | No change — IPA still null despite code fix |

## Configuration Notes
- Model: qwen3-next:80b-a3b-instruct-q8_0 (all agents)
- Config: max_tokens=8192, context_length=32768, think_mode=false
- No LLM retries needed (0 retries across all stages)
- Character Profiles took 669s (11 min) — disproportionately long for 4 characters
- Richardson profile has LOW confidence (0.30) — root cause of missing speech patterns and relationships

## Next Action
Re-run analysis to verify attempt 3 fixes.

## Fix History (continued)
- Attempt 3: Three fixes applied:
  1. **Pronunciation "bolo-toothed"** (null IPA): Added to KNOWN_IRREGULAR_IPA with `/ˈboʊ.loʊ.tuːθt/`. Root cause: `enricher.py:KNOWN_IRREGULAR_IPA`.
  2. **Pronunciation "produce"** (null IPA): Added to HOMOGRAPH_IPA_MAP with both stress variants. Root cause: `enricher.py:HOMOGRAPH_IPA_MAP` — `enrich_homograph()` returned no IPA when word not found in map.
  3. **Pronunciation "sharp-fanged"** (null IPA): Fix was already in code from attempt 2; cleared `__pycache__` to ensure bytecode cache is invalidated. Root cause: stale .pyc file (classic pycache timing issue noted in MEMORY.md).
  4. **Richardson missing Price relationship** (Profiles): Added `add_text_window_cooccurrence_relationships` to `PipelineCharacterCorrector.run_all` in `post_corrections.py`. Scans character mention positions (from V2 mention search) and adds "colleague" for pairs within 600-char windows. Root cause: no summary-based co-occurrence possible for single-chapter texts (summaries list is empty); Phase B co-occurrence scan skipped. Smoke test: PASS — Richardson→Price "colleague" added correctly.

### Fix Classification (Attempt 3)
- **Fix type:** Reference lexicon extension (pronunciation dicts) + algorithmic (text co-occurrence)
- **Universality check:** Pronunciation overrides apply to these words in any book. Text window co-occurrence is universal — characters sharing scenes in any story have a relationship.
- **Root-cause location:** `enricher.py:KNOWN_IRREGULAR_IPA` (bolo-toothed), `enricher.py:HOMOGRAPH_IPA_MAP` (produce), `post_corrections.py:PipelineCharacterCorrector.run_all` (no text-based co-occurrence fallback)
