# Current Evaluation State

## Active Text
- **Name:** cask_of_amontillado
- **Attempt:** 4
- **Phase:** awaiting_evaluation
- **baseline_score: 4.65**

## Output Files
- HTML: ../output/cask_of_amontillado/report.html
- JSON: ../output/cask_of_amontillado/analysis.json
- Timestamped: ../output/The Cask of Amontillado - Poe_20260220_144354/

## Pipeline Notes (Attempt 4)
- Analysis completed in 12m 46s with competitive consensus enabled (all stages)
- Competitive consensus: ENABLED (3 LLMs, 2/3 supermajority) for characters, structure, summaries
- 46 LLM calls, 38,058 tokens
- Profiling: Pronunciation Guide (24.7% of time, bottleneck)
- Narrator detection: Montresor (first-person) - confirmed
- Warnings observed:
  - LLM marker proposer returned dict instead of list (handled, returned single chapter)
  - Narrator 'Montresor' not found in main_cast during initial extraction (but added via F6 reconciliation)
  - No passages provided for character profile generation (returned UNCERTAIN) for all 3 characters
  - Ollama json_mode validation errors in pronunciation stage
- Pipeline completed successfully despite warnings
- 3 characters extracted (Fortunato, Luchresi, Montresor)
- 1 chapter detected
- 36 pronunciation flags generated
- **Character Profiles: 3H/0M/0L confidence** (all high confidence - improvement from attempt 3's 1 low confidence)

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 8.5/10 ✓
  - Completeness: 9/10
  - Identity Resolution: 9/10
  - Alias Grouping: 8/10
- Character Profiles: 5.5/10 ✗ (FAILING)
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 7.5/10 ✗ (FAILING)
- HTML Presentation: 8/10 ✓
- **Overall: 8.10/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold)

## Improvements from Attempt 2
- Chinese character hallucination in plot summary: **FIXED** (no non-Latin characters found)
- Fortunato role classification: **FIXED** (now "protagonist" instead of "minor")
- Montresor mention count: **IMPROVED** (1 → 3, still low but acceptable for F6-reconciled narrator)
- Character Extraction overall: **IMPROVED** (7/10 → 8.5/10)
- Chapter Summaries: **IMPROVED** (7/10 → 9/10)

## Current Issues (Priority Order)

### CRITICAL
1. **Montresor profile parsing failure — structured data dumped as raw string in description** [Profiles]
   - Problem: Montresor's `appearance`, `personality`, and `voice_guidance` fields are ALL `null`. The LLM's structured profile response was concatenated into `descriptions[0].text` as a raw string containing JSON-like key-value pairs.
   - Evidence: `jq '.characters[2].appearance' analysis.json` → `null`. But `descriptions[0].text` contains: personality ("calculating, manipulative, patient, deceptive"), voice guidance ("authoritative", verbal tics), AND relationships ("Fortunato: target of revenge", "Luchresi: rival connoisseur used as manipulative tool").
   - The data IS there — it was just not parsed into the structured fields. Fortunato (supporting_0, high confidence) parsed correctly. Montresor (e3bdcd5e8982, low confidence) did not.
   - **Root cause:** Montresor's ID is an F6 reconciliation hash, not `supporting_*`. The profile pipeline may handle F6-reconciled characters differently, or the LLM returned a slightly malformed JSON response for Montresor that the parser couldn't extract but preserved as raw text.
   - Location: `src/analyzer.py` — `_generate_character_profile()` method. The LLM response parsing around line 2920 fails to extract structured fields for Montresor but succeeds for Fortunato.
   - Fix approach: Add robust parsing that can extract structured profile data even when the LLM response format is slightly different. Check if the profile generation code path differs for F6-reconciled characters vs supporting cast. The pipeline notes show "JSON parse failure for Montresor profile (low confidence 0.30)" — this confirms the parser recognized the failure but didn't recover.

2. **No relationships detected for ANY character** [Profiles]
   - Problem: All three characters have `relationships: {}`. The F9 focused relationship extraction added in attempt 2→3 DID NOT WORK — relationships are still empty.
   - Evidence: HTML shows "No explicit relationships detected." Montresor's raw description string contains relationship data ("Fortunato: target of revenge", "Luchresi: rival connoisseur") but it wasn't parsed into the structured field.
   - **The F9 fix either didn't trigger or failed silently.** Since Montresor's profile parse failed entirely (low confidence 0.30), the F9 code path may not have been reached for him. For Fortunato, the main profile parsed but returned empty relationships, and F9 should have triggered — but didn't produce results.
   - Location: `src/analyzer.py` — `_extract_relationships_from_evidence()` method (lines 3135-3235). Verify: (1) Is this method actually being called? (2) Is the evidence being passed correctly? (3) Is the LLM response being parsed correctly?
   - Fix: Add logging/debug output to verify F9 is triggering. If it triggers but LLM returns empty, the prompt may need adjustment. If it doesn't trigger, the conditional at lines 3080-3094 may have a bug.

### HIGH
3. **Pronunciation false positives — 8 common English words flagged** [Pronunciation]
   - Problem: ~8 of 36 entries are standard English words: "tight-fitting", "to-day", "web-work", "cough's", "leer", "mason-work", "Unsheathing", "reapproached".
   - Evidence: These are common words any English narrator would know. "leer", "cough's", and "Unsheathing" are particularly egregious — narrators do not need pronunciation help for these.
   - Removing 8 false positives would leave 28 entries, all of which are genuinely useful.
   - Location: `src/pipeline/pronunciation/` — word filtering/flagging threshold.
   - Fix: The pronunciation pipeline needs more aggressive common-word filtering. This is a recurring issue across attempts. Consider: (1) checking against a frequency wordlist and skipping top-N common words, (2) filtering simple hyphenated compounds of common words, (3) skipping possessive forms of common words.

### MEDIUM
4. **Amontillado and other entries have null type/category fields** [Pronunciation]
   - Problem: ALL 36 pronunciation entries have `type: null` and `category: null`. "Amontillado" should be classified as "foreign" (Spanish), character names as "proper_noun", Latin phrases as "foreign", etc.
   - Evidence: `jq '[.pronunciations[] | select(.type != null)] | length' analysis.json` → 0
   - Impact: Reduces the usefulness of the pronunciation guide for navigation and filtering.
   - Location: Pronunciation type/category classification logic.
   - Fix: Lower priority than issues #1-3 since words are still flagged with IPA.

5. **Latin phrases split into individual words** [Pronunciation]
   - Problem: "impune" and "lacessit" listed separately rather than "Nemo me impune lacessit". "requiescat" listed alone rather than "In pace requiescat".
   - Impact: Minor — individual word pronunciation still useful for narrators.

### LOW
6. **Structure section title is null**
   - Problem: Single section has `title: null` instead of a meaningful title.
   - Impact: Very minor for a single-section short story.

## Fix History
- Attempt 1 (4.65/10): Character extraction produced ZERO characters. Character profiles scored 0/10 (blocked). Pronunciation had excessive false positives.
- Attempt 2 (7.10/10): Character extraction now working (3 characters). Profiles partially working (Fortunato has rich profile, Montresor's profile failed to parse). Summary had Chinese character hallucination. Pronunciation still had false positives but improved.
- Attempt 3 (8.10/10): Chinese hallucination fixed. Fortunato role fixed (minor→protagonist). Character extraction improved. Summaries improved. BUT: Montresor profile still unparsed, relationships still empty (F9 fix didn't work), pronunciation false positives persist.
- Attempt 3→4: **Fixed profile parsing and evidence extraction**
  - Root cause: Secondary LLM structuring call was returning empty dicts `{}` for missing fields, which `_clean_dict()` was converting to `None`
  - Root cause: Secondary call wasn't extracting evidence, and F9 requires evidence to trigger
  - Fix 1: Changed `_clean_dict()` to preserve empty dicts (empty dict means "looked but found nothing", different from None meaning "didn't look")
  - Fix 2: Added `json_mode=True` to secondary structuring call for reliability
  - Fix 3: Added evidence extraction to secondary call prompt and result processing
  - Modified: src/analyzer.py lines 2949, 3034, 3016-3028, 3054-3061
  - **Expected improvement:** Montresor profile fields should now populate from secondary call; evidence should populate; F9 should trigger and extract relationships

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1→2 | Zero characters extracted | (unknown — analysis re-run) | Fixed — 3 characters now extracted |
| 1→2 | Profiles scored 0 (blocked) | (unknown) | Partially fixed — Fortunato has rich profile, Montresor parse failure |
| 1→2 | Pronunciation false positives | (unknown) | Slightly improved but still present |
| 2→3 | Empty relationships for all characters | src/analyzer.py | **No change** — F9 method added but relationships still empty |
| 2→3 | Chinese hallucination in summary | (not explicitly fixed) | Fixed — likely model variance on re-run |
| 2→3 | Fortunato role "minor" | (not explicitly fixed) | Fixed — now "protagonist" on re-run |
| 3→4 | Profile fields null (Montresor) | src/analyzer.py | Fixed `_clean_dict()` to preserve empty dicts, added json_mode and evidence to secondary call |
| 3→4 | Empty evidence for all characters | src/analyzer.py | Added evidence extraction to secondary structuring call |
| 3→4 | F9 not triggering (no evidence) | src/analyzer.py | Should trigger after evidence is populated by secondary call |

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (ollama) for all agents
- Temperature: 0.7 for all agents (appropriate)
- Context length: 32768 (sufficient for this short text)
- character_llm_chunk_chars: 5000 (sufficient — text is only ~2,354 words)
- Character Profiles: 5 LLM calls, 0 retries, 158.7s — 1 low confidence item (Montresor)
- Character Extraction: 2 LLM calls, 0 retries, 16s — produced 2 items (supporting characters)
- Montresor added via F6 reconciliation (hash ID), not main extraction pipeline — this is the root cause of profile parsing issues

## Next Action
Re-run analysis (PROMPT_analyze.md) to verify fixes for:
1. ✓ Profile parsing (secondary call should now populate structured fields)
2. ✓ Evidence extraction (secondary call now extracts evidence from profile text)
3. ✓ F9 relationships (should trigger now that evidence will be populated)

If profiles pass 8.0, address pronunciation false positives (8 common words flagged).

**Note:** Did NOT fix pronunciation in this iteration — focused on CRITICAL profile issues first per priority order.
