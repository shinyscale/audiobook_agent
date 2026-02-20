# Current Evaluation State

## Active Text
- **Name:** cask_of_amontillado
- **Attempt:** 3
- **Phase:** awaiting_analysis
- **baseline_score: 4.65**

## Output Files
- HTML: ../output/cask_of_amontillado/report.html
- JSON: ../output/cask_of_amontillado/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 7/10 ✗
  - Completeness: 9/10
  - Identity Resolution: 8/10
  - Alias Grouping: 5/10
- Character Profiles: 5/10 ✗
- Chapter Summaries: 7/10 ✗
- Pronunciation Guide: 7/10 ✗
- HTML Presentation: 8/10 ✓
- **Overall: 7.10/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (4 categories below threshold)

## Current Issues (Priority Order)

### CRITICAL
1. **Montresor profile parsing failure — structured data dumped as raw string in description** [Profiles]
   - Problem: Montresor's `appearance`, `personality`, and `voice_guidance` fields are all `null`. Instead, the LLM's structured profile response was concatenated into the `descriptions[0].text` field as a raw string containing JSON-like key-value pairs (e.g., `"appearance": "summary": "unknown"`, `"voice_guidance": "suggested_tone": "authoritative"`).
   - Evidence: `jq '.characters[2].appearance' analysis.json` → `null`. But `descriptions[0].text` contains: `"Montresor is the narrator who lures Fortunato... He recounts the event fifty years later...", "appearance": "summary": "unknown"...`
   - The data IS there — it was just not parsed into the proper structured fields. Fortunato's profile parsed correctly (appearance, personality, voice_guidance all populated), so this is an intermittent parsing issue.
   - Montresor has ID `e3bdcd5e8982` (F6 reconciliation hash), not `supporting_*` — the profile pipeline may handle F6-reconciled characters differently.
   - Location: `src/pipeline/character_extraction_v2/` — profile parsing logic. The LLM returned valid data but the parser failed to extract it into the structured fields for this character. Check how profiles are applied to F6-reconciled characters vs supporting_cast characters.
   - Fix approach: Investigate why Fortunato (supporting_0) got parsed correctly but Montresor (e3bdcd5e8982) did not. The parser likely expects a specific JSON format and Montresor's response was slightly malformed or in a different format.

2. **Plot summary contains Chinese characters (LLM hallucination)** [Summaries]
   - Problem: The plot summary contains "Fortunato's起初的笑声 and escalating pleas" — Chinese characters meaning "initial laughter" were injected mid-sentence.
   - Evidence: `jq '.overview.plot_summary.plot_summary' analysis.json` shows "起初的笑声" in paragraph 3.
   - This is a known issue with the qwen3 model family occasionally producing Chinese text mid-output.
   - Location: `src/pipeline/` — summary generation. Should have post-processing to strip non-Latin/non-IPA characters from English summaries, or the summary agent should validate output language.
   - Fix approach: Add a post-processing sanitization step that detects and removes/replaces non-Latin script characters in summary text (excluding IPA and expected Unicode). Alternatively, add a validation check that rejects and retries summaries containing unexpected script characters.

### HIGH
3. **Fortunato incorrectly labeled as "minor" role — should be a main character** [Character Extraction]
   - Problem: Fortunato has `role: "minor"` and is tagged as a "minor" character in the HTML, but he is one of the two central characters. He has 14 mentions and is the primary antagonist/victim.
   - Evidence: HTML shows `<span class="tag">minor</span>` next to Fortunato. In the JSON, `role: "minor"`. Fortunato is listed under "Main Characters" in the HTML (2 main characters) but tagged "minor".
   - In a ~2,354 word short story, 14 mentions is very significant. The role classification may be calibrated for novel-length works.
   - Location: Character role classification logic — likely in `src/pipeline/character_extraction_v2/supporting.py` since Fortunato's ID is `supporting_0`.
   - Fix: The role determination needs to account for text length. In a short story, a character with 14 mentions across 2,354 words is a major character (equivalent to ~600+ mentions in a 100K word novel).

4. **Montresor has only 1 mention count — far too low** [Character Extraction]
   - Problem: Montresor shows `mention_count: 1` despite being the narrator who refers to himself and is named multiple times.
   - Evidence: `jq '.characters[2].mention_count' analysis.json` → `1`. The name "Montresor" appears at least twice explicitly in the text ("For the love of God, Montresor!" and the family name "Montresors"), plus first-person "I" references throughout.
   - Montresor has an F6 reconciliation hash ID (`e3bdcd5e8982`), suggesting he was added during reconciliation rather than by the main extraction pipeline. The reconciliation may not properly count mentions.
   - Location: F6 reconciliation in `src/analyzer.py` (around line 1220-1240) — mention counting for reconciled characters.
   - Fix: Ensure F6-reconciled characters get proper mention counts, or ensure the narrator is detected during main extraction with accurate counts.

5. **No relationships detected for any character** [Profiles]
   - Problem: All three characters have `relationships: {}` despite the story being centered on the Montresor-Fortunato relationship, with Luchresi as a manipulative tool.
   - Evidence: HTML shows "No explicit relationships detected." in the Key Relationships section.
   - The profile pipeline ran (7 LLM calls, 247 seconds), so this isn't a skipped stage. The relationship extraction failed to populate the structured field.
   - For Montresor, the relationship data IS present in the raw description string: `"relationships": "Fortunato": "acquaintance whom he lures to his death"` — but it wasn't parsed into the structured `relationships` field.
   - Location: Profile/relationship extraction and parsing in `src/pipeline/character_extraction_v2/`.
   - Fix: Related to issue #1 — fixing Montresor's profile parsing should also fix his relationships. For Fortunato and Luchresi, relationships should at minimum be: Fortunato↔Montresor (victim/antagonist), Fortunato↔Luchresi (rival connoisseur), Montresor↔Luchresi (manipulative tool).

6. **Pronunciation false positives — common English words flagged** [Pronunciation]
   - Problem: ~8 of 36 entries are standard English words or simple hyphenated compounds: "tight-fitting", "to-day", "web-work", "cough's", "leer", "Unsheathing", "reapproached", "mason-work".
   - Evidence: These are common words any English narrator would know. "leer", "cough's", and "Unsheathing" are particularly egregious false positives.
   - Improved from attempt 1: "hearkened", "re-echoed", "re-erected", "Grave" are borderline but acceptable. "parti-striped" is period-specific and acceptable.
   - Location: `src/pipeline/pronunciation/` — word filtering/flagging threshold.
   - Fix: Filter common English words more aggressively. Words like "leer", "cough's", "tight-fitting", "web-work", "mason-work", "Unsheathing", "reapproached" should not be flagged.

### MEDIUM
7. **Amontillado classified as "unknown" type rather than "foreign" or "proper_noun"** [Pronunciation]
   - Problem: "Amontillado" is in the "Other" category with type "unknown", but it's a Spanish wine term that should be classified as "foreign" (Spanish).
   - Evidence: It appears 17 times and is the title object — it should be prominently categorized.
   - Location: Pronunciation type classification logic.
   - Fix: Classify wine/spirit terms from foreign languages appropriately.

8. **Latin phrases split into individual words** [Pronunciation]
   - Problem: "impune" and "lacessit" are listed separately rather than as the phrase "Nemo me impune lacessit". Similarly, "requiescat" should ideally be "In pace requiescat" (or "Requiescat in pace").
   - Evidence: The context shows they appear as part of complete Latin phrases.
   - Impact: Minor — a narrator can still piece them together, and individual word pronunciation is provided.
   - Location: Pronunciation flagging — phrase detection.

9. **Structure section title is null**
   - Problem: The single section has `"title": null` instead of a meaningful title like "Full Text" or the story title.
   - Evidence: `jq '.structure[0].title' analysis.json` → `null`
   - Impact: Very minor for a single-section text.

### LOW
10. **"Grave" classified as foreign word when used as wine term**
    - The pronunciation note correctly explains it's a French wine (Graves), but the classification and handling are reasonable. The note itself is thorough and helpful for a narrator. No fix needed.

## Fix History
- Attempt 1 (4.65/10): Character extraction produced ZERO characters. Character profiles scored 0/10 (blocked). Pronunciation had excessive false positives.
- Attempt 2 (7.10/10): Character extraction now working (3 characters). Profiles partially working (Fortunato has rich profile, Montresor's profile failed to parse). Summary has Chinese character hallucination. Pronunciation still has false positives but improved.
- Attempt 3: Added focused relationship extraction (F9) — second LLM call to extract relationships from already-collected evidence when main profile generation returns empty relationships dict

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1→2 | Zero characters extracted | (unknown — analysis re-run) | Fixed — 3 characters now extracted |
| 1→2 | Profiles scored 0 (blocked) | (unknown) | Partially fixed — Fortunato has rich profile, Montresor parse failure |
| 1→2 | Pronunciation false positives | (unknown) | Slightly improved but still present |
| 2→3 | Empty relationships for all characters | src/analyzer.py | Added `_extract_relationships_from_evidence()` method + focused LLM call (F9) |

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (ollama) for all agents
- Temperature: 0.7 for all agents (appropriate)
- Context length: 32768 (sufficient for this short text)
- character_llm_chunk_chars: 5000 (sufficient — text is only ~2,354 words)
- Character Profiles: 7 LLM calls, 0 retries, 247s — high time suggests complex processing
- Character Extraction: 2 LLM calls, 0 retries, 23.7s — produced 2 items (supporting characters)
- Montresor added via F6 reconciliation (hash ID), not main extraction pipeline — this may explain profile parsing issues

## Next Action
Re-run analysis to verify fix

## Fix Applied (Attempt 3)

### Root Cause Analysis
**Issue:** All characters had empty `relationships: {}` despite evidence containing relationship information

**Data Investigation:**
- Verified actual data in `cask.json` (evaluation claims were outdated or based on different run)
- Montresor's profile IS properly structured (appearance, personality, voice_guidance all populated)
- Evidence DOES mention relationships (e.g., "Montresor seeks revenge against Fortunato")
- The LLM was including relationship info in prose profile but returning `{}` for the structured relationships dict

**Root Cause:** `src/analyzer.py:_generate_character_profile()` lines 2640-2659
The main profile generation prompt requests a `relationships` dict, but the LLM consistently returns empty `{}` even when evidence contains relationship information. The LLM includes relationships in the prose profile and evidence statements, but not in the structured field.

**Data Flow:**
1. Profile generation prompt (line 2640-2643) requests relationships dict
2. LLM response at line 2920: `relationships = result.get("relationships")` → returns `{}`
3. Empty dict preserved and assigned to Character.relationships
4. Result: All characters have `relationships: {}`

### Fix Implementation
**Approach:** Focused second LLM call (per USER_NOTES.md guidance)

Added `_extract_relationships_from_evidence()` method that:
1. Triggers when main profile generation returns empty relationships dict
2. Uses already-collected evidence (no duplicate text extraction)
3. Makes focused LLM call with simplified prompt
4. Uses lower temperature (0.3) and shorter max_tokens (512) for precision
5. Validates character names against `all_character_names` list

**Files Modified:** `src/analyzer.py`
- Lines 3080-3094: Added conditional call to focused relationship extraction
- Lines 3135-3235: New `_extract_relationships_from_evidence()` method

**Smoke Test:** PASSED
- Method imports correctly
- Signature validated: `(llm, character_name, evidence, all_character_names) -> Optional[dict[str, str]]`
- No syntax errors or crashes

### Expected Impact
- Profiles: 5/10 → 8+/10 (relationships is a major scoring factor)
- Characters: May improve slightly if relationships help clarify character roles
- Overall: Should close the 3-point gap in Profiles category
