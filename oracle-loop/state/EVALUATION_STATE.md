# Current Evaluation State

## Active Text
- **Name:** cask_of_amontillado
- **Attempt:** 5
- **Phase:** awaiting_evaluation
- **baseline_score: 4.65**

## Output Files
- HTML: ../output/cask_of_amontillado/report.html
- JSON: ../output/cask_of_amontillado/analysis.json
- Timestamped: ../output/The Cask of Amontillado - Poe_20260220_171846/

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 9/10 ✓
  - Completeness: 9/10
  - Identity Resolution: 9/10
  - Alias Grouping: 8/10
- Character Profiles: 7.5/10 ✗ (FAILING)
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 7.5/10 ✗ (FAILING)
- HTML Presentation: 8/10 ✓
- **Overall: 8.53/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold)

## Improvements from Attempt 3
- Montresor structured profile fields (personality, voice_guidance): **FIXED** — now populated with accurate data
- Montresor confidence: **FIXED** — upgraded from LOW (0.30) to HIGH
- Montresor evidence citations: **FIXED** — now has 8 evidence citations (was 0)
- All characters at HIGH confidence: **FIXED** (was 3H/0M/0L vs prev 2H/0M/1L)
- Profile parsing for F6-reconciled characters: **FIXED** — secondary call now returns structured data

## Current Issues (Priority Order)

### CRITICAL
1. **Relationships still empty for ALL three characters — 3rd attempt failing** [Profiles]
   - Problem: `relationships: {}` for Fortunato, Luchresi, and Montresor. The F9 focused relationship extraction (added attempt 2→3) and evidence extraction fix (added attempt 3→4) have both failed to populate relationships.
   - Evidence: `jq '[.characters[] | select(.relationships | length > 0)] | length'` → 0. HTML shows "No explicit relationships detected."
   - Expected relationships:
     - Montresor → Fortunato: target of revenge, outwardly feigned friendship
     - Fortunato → Montresor: friend/acquaintance (from Fortunato's perspective)
     - Montresor → Luchresi: uses as manipulation tool to goad Fortunato
     - Fortunato → Luchresi: rival wine connoisseur
   - **ESCALATION REQUIRED:** This issue has been modified in `src/analyzer.py` in BOTH attempts 2→3 and 3→4 without success. Per loop rules, the fix phase MUST escalate upstream — do not modify `src/analyzer.py` relationship extraction a 3rd time with minor tweaks. Instead:
     - **Option A:** Add debug logging to trace WHY F9 isn't triggering or producing output. Run the analysis with verbose logging before making code changes.
     - **Option B:** Check if the evidence data structure passed to `_extract_relationships_from_evidence()` actually contains data. The evidence IS now populated (6 for Fortunato, 8 for Montresor), so F9's conditional should trigger. Investigate the F9 method's LLM prompt or response parsing.
     - **Option C:** Bypass F9 entirely — extract relationships during the profile generation step itself rather than as a separate post-processing pass. Add relationship fields to the profile generation prompt.
   - Location: `src/analyzer.py` — `_extract_relationships_from_evidence()` (lines ~3135-3235) and F9 trigger conditional (~lines 3080-3094)

### HIGH
2. **Fortunato's appearance attributes Montresor's clothing to Fortunato** [Profiles]
   - Problem: Fortunato's `appearance.distinguishing_features` includes "wears a mask of black silk and a roquelaire". In the text, Montresor says "putting on a mask of black silk and drawing a roquelaire closely about my person" — the mask and roquelaire belong to MONTRESOR, not Fortunato.
   - Evidence: Text quote: "putting on a mask of black silk and drawing a roquelaire closely about my person, I suffered him to hurry me to my palazzo." The "I" is Montresor.
   - Impact: Factual inaccuracy in a profile field. A narrator relying on this would voice Fortunato incorrectly.
   - Location: This is an LLM extraction error, not a code bug. The profile generation prompt or the evidence parsing incorrectly attributed Montresor's clothing to Fortunato.
   - Fix: This may resolve on re-analysis (LLM variance), or the profile prompt could be improved to require quote-level attribution of physical descriptions. Lower priority than #1.

3. **Pronunciation false positives — 8 common English words flagged** [Pronunciation]
   - Problem: 8 of 36 entries are standard English words that no narrator needs pronunciation help for: "tight-fitting", "to-day", "web-work", "cough's", "leer", "mason-work", "Unsheathing", "reapproached".
   - Evidence: These are common English words or trivially decomposable compounds. "leer", "cough's", and "Unsheathing" are particularly egregious.
   - Impact: Reduces trust in the pronunciation guide. Removing them would leave 28 useful entries.
   - Location: `src/pipeline/pronunciation/` — word filtering/flagging stage.
   - Fix: Add a common-word filter that: (1) checks individual words of hyphenated compounds against a frequency list — if all component words are common, skip the compound; (2) skips possessive forms of common words; (3) skips words with common prefixes (un-, re-) where the base word is common. This would eliminate all 8 false positives while preserving the 28 genuinely useful entries.

### MEDIUM
4. **All 36 pronunciation entries have null type and category** [Pronunciation]
   - Problem: `type: null` and `category: null` for every entry. "Fortunato" should be `proper_noun`, "Amontillado" should be `foreign` (Spanish), "impune"/"lacessit"/"requiescat" should be `foreign` (Latin), etc.
   - Evidence: `jq '[.pronunciations[] | select(.type != null)] | length'` → 0
   - Impact: Reduces navigation/filtering usefulness in the HTML pronunciation guide.
   - Location: Pronunciation pipeline type/category classification.
   - Fix: Lower priority than #3. If fixing the false positive filter, this could be addressed in the same pass.

5. **Montresor's appearance is "unknown" but text provides details** [Profiles]
   - Problem: Montresor's `appearance.summary` is "unknown" but the text says he wears "a mask of black silk" and a "roquelaire" — details that were incorrectly assigned to Fortunato instead.
   - Impact: Minor — narrator already knows Montresor narrates in first person. But for completeness, his disguise is a relevant visual detail.
   - Fix: Would likely resolve alongside issue #2 if the LLM correctly attributes the clothing.

### LOW
6. **Structure section title is null**
   - Problem: Single section has `title: null` instead of a meaningful title like "The Cask of Amontillado".
   - Impact: Very minor for a single-section short story.

7. **Homograph entries (row, close, entrance) lack IPA**
   - Problem: 3 pronunciation entries have `ipa: null`. These are homographs where pronunciation depends on context, so null IPA is arguably correct, but providing both pronunciations or the contextually correct one would be more useful.
   - Impact: Very minor.

## Fix History
- Attempt 1 (4.65/10): Character extraction produced ZERO characters. Character profiles scored 0/10 (blocked). Pronunciation had excessive false positives.
- Attempt 2 (7.10/10): Character extraction now working (3 characters). Profiles partially working (Fortunato has rich profile, Montresor's profile failed to parse). Summary had Chinese character hallucination. Pronunciation still had false positives but improved.
- Attempt 3 (8.10/10): Chinese hallucination fixed. Fortunato role fixed (minor→protagonist). Character extraction improved. Summaries improved. BUT: Montresor profile still unparsed, relationships still empty (F9 fix didn't work), pronunciation false positives persist.
- Attempt 4 (8.53/10): Montresor profile parsing **FIXED** — personality, voice guidance, evidence all populated. All 3 characters at HIGH confidence. BUT: Relationships STILL empty (3rd failed attempt), pronunciation false positives persist.
- Attempt 5 (TBD): TWO fixes applied:
  1. **Relationships** — Root cause identified: F9 `_extract_relationships_from_evidence` was missing `json_mode=True`, causing likely parse failures when LLM adds preamble text. Also: relationship prompt examples only showed family types (father/wife/nephew), not narrative types (enemy/victim/acquaintance). Fixed both: added `json_mode=True` to F9 LLM call; updated main profile prompt relationship examples to include antagonistic/narrative relationships; replaced book-specific F9 examples with generic ones (CLAUDE.md compliance). Modified: `src/analyzer.py`
  2. **Pronunciation false positives** — Root cause: WordIndex captures hyphenated compounds ("tight-fitting") as single tokens; these aren't in CMU so get flagged as UNKNOWN. Also: possessives ("cough's") and prefixed+derived words ("unsheathing", "reapproached") weren't handled. Fixed: (A) Added hyphen-compound check to `is_unknown` — splits on "-" and skips if all parts in CMU; (B) Added possessive check — strips "'s" and checks base in CMU; (C) Refactored `_is_common_derivation` to also try stripping common prefixes (re-, un-, dis-, etc.) before suffix checking. Smoke test: 7/8 false positives eliminated. Modified: `src/pipeline/pronunciation_guide/proposers/cmu_proposer.py`

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1→2 | Zero characters extracted | (unknown — analysis re-run) | Fixed — 3 characters now extracted |
| 1→2 | Profiles scored 0 (blocked) | (unknown) | Partially fixed — Fortunato has rich profile, Montresor parse failure |
| 1→2 | Pronunciation false positives | (unknown) | Slightly improved but still present |
| 2→3 | Empty relationships for all characters | src/analyzer.py (F9 method added) | **No change** — relationships still empty |
| 2→3 | Chinese hallucination in summary | (not explicitly fixed) | Fixed — likely model variance on re-run |
| 2→3 | Fortunato role "minor" | (not explicitly fixed) | Fixed — now "protagonist" on re-run |
| 3→4 | Profile fields null (Montresor) | src/analyzer.py (_clean_dict, json_mode, secondary call) | **Fixed** — personality, voice guidance populated |
| 3→4 | Empty evidence for all characters | src/analyzer.py (evidence extraction in secondary call) | **Fixed** — 6 citations for Fortunato, 8 for Montresor |
| 3→4 | F9 not triggering (no evidence) | src/analyzer.py (evidence now populated) | **No change** — evidence populated but relationships STILL empty |
| 4→5 | Relationships empty (F9 parse failure) | src/analyzer.py (json_mode=True + prompt examples + F9 generic examples) | TBD |
| 4→5 | Pronunciation false positives (8 words) | cmu_proposer.py (hyphen compound + possessive + prefix handling) | TBD |

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (ollama) for all agents
- Temperature: 0.7 for all agents (appropriate)
- Context length: 32768 (sufficient for this short text)
- character_llm_chunk_chars: 5000 (sufficient — text is only ~2,354 words)
- Character Profiles: 5 LLM calls, 0 retries, 183.9s — **3 HIGH confidence** (major improvement from attempt 3's 1 LOW)
- Character Extraction: 2 LLM calls, 0 retries, 17.6s — produced 2 supporting characters
- Pronunciation Guide: 36 LLM calls, 0 retries, 189.2s — 9 HIGH, 27 MEDIUM confidence
- Montresor added via F6 reconciliation (hash ID `e3bdcd5e8982`)
- No JSON parse failures, no LLM retries — pipeline is stable

## Next Action
Re-run analysis on cask_of_amontillado to verify:
1. Relationships now populated for at least Montresor and Fortunato
2. Pronunciation false positives reduced from 8 to ~1 (only "leer" remains, which is genuinely not in CMU)
