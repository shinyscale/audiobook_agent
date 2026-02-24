# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 6
- **Phase:** awaiting_analysis
- **baseline_score:** 6.55
- **Competitive Mode:** single

## Output Files
- HTML: ../output/gatsby/report.html
- JSON: ../output/gatsby/analysis.json

## Pipeline Notes (Attempt 5)
- Completed in 85m 30s, 295 LLM calls, 464,786 tokens
- 9 chapters detected, 21 characters extracted, 21 profiles generated
- Fix K (butler case dedup): SUCCESS — only 1 "The butler" entry now (431ff1f64d63)
- Fix L (unknown relationships): SUCCESS — Nick's 4 "unknown" entries removed; relationships dict cleaner
- Fix M (narrator prose filter): SUCCESS — Nick's physical_description is now null (not narrative prose)
- REGRESSION: Ella Kaye (main_cast_12) incorrectly marked as narrator (was not in attempt 4)
- REGRESSION: "Henry C. Gatz" regressed to just "Gatz" (supporting_12) — was full name in attempt 4
- PERSISTENT: Nick Carraway still split into "Nick" (supporting_3) + "Carraway" (supporting_7), not in main_cast
- PERSISTENT: Personality traits and speech patterns ALL null (0/21)
- PERSISTENT: Hallucinated familial relationship labels unchanged

## Latest Scores
- Structure Detection: 10/10 ✓
- Character Extraction: 7/10 ✗ (FAILING)
  - Completeness: 7.5/10
  - Identity Resolution: 6.5/10 ← Nick/Carraway split + Ella Kaye narrator bug
  - Alias Grouping: 7/10 ← Buchanan shared
- Character Profiles: 5/10 ✗ (FAILING) ← primary blocker
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 7.5/10 ✗ (FAILING)
- HTML Presentation: 9/10 ✓
- **Overall: 7.83/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold: Characters 7, Profiles 5, Pronunciation 7.5)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.55 | — | Baseline. main_cast pipeline failed; massive false splits; profiles catastrophically wrong |
| 2 | 7.15 | +0.60 | Fix A partially worked (Gatsby aliases resolved); main_cast STILL fails; IPA corruption fixed |
| 3 | 7.93 | +1.38 | Main cast pipeline FIXED (Fix C). 5 false splits resolved. Profiles still wrong. |
| 4 | 7.98 | +1.43 | Fixes G/H/I/J: Eckleburg deduped ✓, "like" removed ✓, Nick rels→unknown (marginal), profiles STILL primary blocker |
| 5 | 7.83 | +1.28 | Fixes K/L/M all SUCCESS ✓ (butler dedup, unknown rels, narrator prose). BUT LLM variance regressions: Ella Kaye narrator, Gatz name. Core blockers unchanged: traits/speech null, relationships wrong. |

## What Changed in Attempt 5

### Fix Results
- **Fix K (butler F6 case dedup):** SUCCESS ✓ — Only 1 "The butler" entry now (was 2 in attempt 4). f6_seen_normalized dedup works.
- **Fix L (unknown relationships):** SUCCESS ✓ — Nick's relationships now empty (was 4 "unknown" entries). Cleaner output, less noise.
- **Fix M (narrator prose filter):** SUCCESS ✓ — Nick's physical_description is now `null` (was narrative prose "a young man at the office suggested..."). Null is better than actively misleading.

### LLM Variance Regressions (not caused by code changes)
- **Ella Kaye (main_cast_12) marked as narrator:** WRONG — Ella Kaye is a minor character (journalist who inherits Cody's fortune). Nick Carraway is the narrator. This is a stochastic LLM error in main_cast extraction.
- **"Henry C. Gatz" → "Gatz" (supporting_12):** Name quality regression. In attempt 4, this was "Henry C. Gatz" with aliases ["Gatsby's father", "Gatz"]. Now it's just "Gatz" with no aliases for the full name.
- **Daisy's physical description misattributed:** Daisy is described as "wan, charming, discontented face with grey sun-strained eyes" — this is actually JORDAN's description from Chapter 1 ("Her grey sun-strained eyes looked back at me... out of a wan, charming, discontented face"). Jordan's entry also has this same text, creating duplicate descriptions.

### Persistent Issues (unchanged from attempt 4)
- Nick/Carraway split (supporting_3 + supporting_7) — across all 5 attempts
- Personality traits: 0/21
- Speech patterns: 0/21
- Hallucinated familial relationship labels (Daisy→Gatsby "mother", etc.)
- Gatsby and Myrtle missing physical descriptions
- Owl Eyes missing from character list
- 19 homographs lacking IPA
- 67 "unknown" pronunciation entries

## Current Issues (Priority Order)

### CRITICAL

1. **Nick Carraway split into 2 entries + not identified as narrator** [Identity Resolution, Completeness]
   - Problem: The narrator/protagonist "Nick Carraway" is fragmented across TWO supporting cast entries:
     - "Nick" (supporting_3, 24 mentions, narrator: false)
     - "Carraway" (supporting_7, 10 mentions, narrator: false)
     - Neither is in main_cast. Neither is marked as narrator.
   - Additionally: Ella Kaye (main_cast_12, 3 mentions) is incorrectly marked `is_narrator: true`
   - Evidence: The chapter summaries correctly identify "Nick Carraway" as narrator (see Ch 2-4 summaries). The text is first-person narration by Nick.
   - Root cause: Nick, as first-person narrator, is mostly the "I" voice. His name appears less frequently than characters he describes, so he falls below the main_cast mention threshold. The supporting cast pipeline then finds "Nick" and "Carraway" as separate first-name/last-name references without linking them.
   - Location: This requires a post-processing merge step in `src/analyzer.py` or `src/pipeline/character_profiling/post_corrections.py`
   - **Recommended generic fix:** After main_cast + supporting_cast extraction, check chapter summaries for narrator identification. If summaries consistently name the narrator (e.g., "Nick Carraway"), find supporting cast entries matching first/last name components, merge them, set `is_narrator: true`, and clear the flag from any wrongly-flagged character. This fix is generic — it works for any first-person narrator by using the summary-derived narrator name.
   - **This has persisted for ALL 5 attempts.** Previous fixes focused on other issues. This is now the #1 priority.
   - Impact: +1.0 to Identity Resolution, +0.5 to Completeness if fixed

2. **Personality traits and speech patterns ALL null** [Profiles]
   - Problem: All 21 characters have `personality_traits: null` and `speech_pattern: null`
   - Evidence: `with_traits: 0/21`, `with_speech: 0/21`
   - Missing examples:
     - Gatsby: "old sport" catchphrase, formal/measured speech
     - Wolfsheim: accent rendering ("Oggsford," "gonnegtion," "business gonnegtion")
     - Tom: aggressive, domineering, interrupting
     - Daisy: "low, thrilling voice," breathy/performative speech
     - George Wilson: flat, defeated, monosyllabic
   - Location: Investigate the profile extraction schema in `src/pipeline/character_extraction_v2/` — the profile prompt and Pydantic response model likely don't include `personality_traits` or `speech_pattern` fields, OR the fields exist but the LLM response parsing drops them
   - Fix: Ensure the profile extraction template explicitly requests these fields, and the response model captures them
   - **This has been null across ALL 5 attempts.** The fix phase must investigate why.
   - Impact: +2.0 to Profiles if both fields are populated for major characters

3. **Relationships still massively hallucinated — 4 prompt-level attempts failed** [Profiles]
   - Problem: ~70% of relationship labels are wrong familial labels applied randomly by the LLM:
     - Daisy → Gatsby: "mother" (WRONG — former lover)
     - Daisy → Jordan: "mother" (WRONG — friend)
     - Daisy → Myrtle: "husband" (WRONG — rival/unaware)
     - Daisy → George: "wife" (WRONG — barely interacts)
     - Daisy → Wolfsheim: "husband" (WRONG — never interacts)
     - Jordan → Daisy: "wife" (WRONG — friend)
     - Jordan → Tom: "wife" (WRONG — acquaintance)
     - Jordan → Gatsby: "mother" (WRONG — acquaintance)
     - Gatsby → Wolfsheim: "husband" (WRONG — business associate)
     - Myrtle → Tom: "husband" (WRONG — lover/affair)
     - Myrtle → Catherine: "husband" (WRONG — sister)
     - McKee → Myrtle: "husband" (WRONG — acquaintance)
     - McKee → Tom: "husband" (WRONG — acquaintance)
     - Sloane → everyone: "wife" (WRONG — all are acquaintances)
     - Gatz → Dan Cody: "mentor" (WRONG — Henry Gatz has no relationship to Cody)
   - CORRECT relationships (unchanged): Tom↔Daisy husband/wife ✓, Catherine→Myrtle sister ✓, Gatz→Gatsby child ✓, Klipspringer→Gatsby employer ✓, George→Eckleburg symbolic ✓
   - **ESCALATION REQUIRED:** Prompt-level fixes have been attempted 4 times (attempts 3, 4, 4, 5) across `src/analyzer.py` without resolving this. The LLM (qwen3-next:80b) has a strong familial-label bias that no prompt can override.
   - **Mandatory approach for attempt 6:** Post-processing validation in `src/pipeline/character_profiling/post_corrections.py`:
     1. Define familial labels: {"mother", "father", "son", "daughter", "wife", "husband", "sister", "brother", "nephew", "niece", "uncle", "aunt", "cousin", "child", "parent"}
     2. For each relationship where label ∈ familial_labels: check if both characters share a surname (or text explicitly establishes family). If NOT, replace with "associate" or remove.
     3. Exception: allow familial labels when canonical names share surname components (e.g., "Tom Buchanan" ↔ "Daisy Buchanan" → "wife/husband" is valid)
   - Impact: +1.5 to Profiles if fixed

### HIGH

4. **Gatsby and Myrtle physical descriptions NULL** [Profiles]
   - Problem: Two of the five most important characters have no physical description
   - Gatsby: Should describe elegant appearance, tanned, gorgeous smile, "an elegant young roughneck," pink suit
   - Myrtle: Should describe stout/thick-bodied, sensuous vitality, mid-thirties
   - Evidence: `physical_description: null` for both main_cast_1 and main_cast_4
   - Location: Profile extraction — LLM may not find descriptions in the assigned chunks
   - Fix: May require second-pass extraction for major characters with null descriptions, or increased chunk overlap
   - Impact: +0.5 to Profiles

5. **Daisy's physical description is actually Jordan's** [Profiles]
   - Problem: Daisy's `physical_description` is "wan, charming, discontented face with grey sun-strained eyes" — this is Jordan's description from Ch 1 ("Her grey sun-strained eyes looked back at me with polite reciprocal curiosity out of a wan, charming, discontented face")
   - Jordan's entry has the same text, creating duplicate descriptions
   - Daisy's actual appearance: "face was sad and lovely with bright things in it, bright eyes and a bright passionate mouth"
   - Location: Profile extraction prompt or chunking — the LLM is extracting from a scene where both women are present and misattributing
   - Impact: +0.3 to Profiles (minor — both characters still have SOME description)

6. **19 homograph entries lack IPA** [Pronunciation]
   - Problem: All homographs (minute, live, close, wind, read, does, subject, row, excuse, elaborate, intimate, content, bow, refuse, bass, entrance, polish, separate, moderate) have `ipa: null`
   - Evidence: These are exactly the words narrators most need guidance for — knowing WHICH pronunciation to use in context
   - Location: `src/pipeline/pronunciation_guide/enricher.py` — the IPA generation likely doesn't handle homographs differently
   - Fix: For known English homographs, provide BOTH IPA variants with context labels (e.g., minute: /ˈmɪnɪt/ "unit of time" vs /maɪˈnjuːt/ "tiny")
   - Impact: +0.5 to Pronunciation (enough to cross 8.0 threshold)

### MEDIUM

7. **67 pronunciation entries still "unknown" category** [Pronunciation]
   - Problem: Many classifiable words remain unknown: dialect (gonnegtion, comin, prac, bles-sed), literary (murmurous, contralto, extemporizing), archaic (plagiaristic, decencies), proper (gaiety, splendour, savours)
   - Evidence: 67/129 entries = 52% of entries are "unknown"
   - Location: `src/pipeline/pronunciation_guide/consolidator.py`
   - Fix: Expand reclassification heuristics (e.g., words ending in -tion/-ous/-ing are likely literary/archaic, not unknown)

8. **"Buchanan" alias shared between Tom and Daisy** [Alias Grouping]
   - Problem: Both main_cast_2 (Daisy) and main_cast_3 (Tom) list "Buchanan" as alias
   - Fix: When a surname alias would be shared, assign only to the character more commonly called by surname alone (Tom), or remove from both

9. **Chapter 7 summary has car arrangement error** [Summaries]
   - Problem: Summary says "Tom and Daisy return home in Gatsby's yellow car" — WRONG. It was Gatsby and Daisy in the yellow car (with Daisy driving). Tom, Nick, and Jordan returned in Tom's car.
   - Evidence: The summary then correctly states "which Daisy was driving" hitting Myrtle — contradicting Tom being in the same car
   - Impact: Minor — only one chapter affected, and the key event (Myrtle's death) is correctly attributed

10. **Missing "Owl Eyes"** [Completeness]
    - Problem: The bespectacled man from Gatsby's library (Ch 3, Ch 9 funeral) not in character list
    - Evidence: Ch 3 summary mentions "Owl Eyes" but he's not a character entry. Narratively significant as the only non-family funeral attendee.

### LOW

11. **"Gatz" should be "Henry C. Gatz"** [Completeness]
    - Regression from attempt 4 where this had the full name. Now just "Gatz" (supporting_12) with no aliases for "Henry C. Gatz" or "Gatsby's father"
    - Relationships correctly show Jay Gatsby: "child" ✓, but "Dan Cody: mentor" is WRONG (Henry Gatz had no relationship with Dan Cody)

12. **Eckleburg self-relationship resolved** [Profiles]
    - Previous self-reference "Doctor T. J. Eckleburg: unknown" was removed by Fix L ✓

## Configuration Audit

### Model Configuration
- Model: qwen3-next:80b-a3b-instruct-q8_0 (Ollama) — same model for all agents
- Context length: 32768 — adequate for Gatsby
- Temperature: 0.7 for all agents — **too high for relationship extraction** (see CRITICAL #3)
- think_mode: false

### Processing Issues
- 295 LLM calls total, 0 retries — pipeline mechanically stable
- Character Profiles: 57 LLM calls (high investment, poor output due to schema/prompt issues)
- Personality traits and speech patterns never requested or always dropped — likely schema issue

### Recommendation
- MEDIUM: Consider lowering temperature to 0.3 for relationship extraction specifically
- HIGH: Check if profile extraction Pydantic model includes personality_traits and speech_pattern fields

## Fix History

### gatsby — Attempt 2 Fixes
**Fix A: Include `characters_present` in summaries for main_cast LLM extraction** [CRITICAL] — PARTIAL
**Fix B: IPA validation to reject corrupt entries** [MEDIUM] — SUCCESS ✓

### gatsby — Attempt 3 Fixes
**Fix C: Main cast prompts changed to dict wrapper format** [CRITICAL] — SUCCESS ✓
**Fix D: Secondary relationship call no longer overwrites primary** [CRITICAL] — PARTIAL
**Fix E: Pronunciation false positive exclusions** [MEDIUM] — SUCCESS ✓
**Fix F: UNKNOWN → PROPER_NOUN reclassification** [MEDIUM] — PARTIAL

### gatsby — Attempt 4 Fixes
**Fix G: Relationship prompt — replace familial examples with social ones** [CRITICAL] — PARTIAL (Nick improved, others unchanged)
**Fix H: Physical description validation** [HIGH] — FAILED (narrator injection overwrites after validation)
**Fix I: Eckleburg duplicate — reverse title check** [HIGH] — SUCCESS ✓
**Fix J: "like" pronunciation exception** [LOW] — SUCCESS ✓

### gatsby — Attempt 5 Fixes
**Fix K: Butler/Butler F6 case dedup** [HIGH] — SUCCESS ✓ (src/analyzer.py)
**Fix L: Remove "unknown" relationships** [CRITICAL] — SUCCESS ✓ (src/pipeline/character_profiling/post_corrections.py)
**Fix M: Narrator appearance prose filter** [HIGH] — SUCCESS ✓ (src/pipeline/character_profiling/post_corrections.py)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | (baseline — no fixes yet) | — | — |
| 2 | Main cast pipeline failure (data) | `src/agents/characters.py` | Partial — aliases improved but grounding still fails |
| 2 | IPA corruption | `src/pipeline/pronunciation_guide/enricher.py` | Fixed ✓ |
| 3 | Main cast grounding failure (JSON format) | `src/pipeline/character_extraction_v2/main_cast.py` | Fixed ✓ |
| 3 | Relationship labels wrong (secondary overwrites) | `src/analyzer.py` | No change — primary pipeline also produces bad labels |
| 3 | Pronunciation false positives | `src/pipeline/pronunciation_guide/proposers/foreign_proposer.py` | Fixed ✓ |
| 3 | UNKNOWN pronunciation categorization | `src/pipeline/pronunciation_guide/consolidator.py` | Partial — 28 reclassified, 67 remain |
| 4 | Relationship biased toward familial labels | `src/analyzer.py` (prompt) | Partial — Nick improved, others still wrong |
| 4 | Physical description narrative text | `src/analyzer.py` (validation) | Failed — narrator injection overwrites after validation |
| 4 | Eckleburg duplicate (Doctor/no-Doctor) | `src/agents/characters.py` | Fixed ✓ |
| 4 | "like" flagged as foreign | `src/pipeline/pronunciation_guide/proposers/foreign_proposer.py` | Fixed ✓ |
| 5 | Butler/Butler F6 case sensitivity dedup | `src/analyzer.py` | Fixed ✓ (f6_seen_normalized set) |
| 5 | "unknown" relationship labels in output | `src/pipeline/character_profiling/post_corrections.py` | Fixed ✓ (clean_unknown_relationships) |
| 5 | Nick appearance: narrative prose from narrator injection | `src/pipeline/character_profiling/post_corrections.py` | Fixed ✓ (density check in _is_compact_physical_description) |

**Pattern alerts:**
- `src/analyzer.py` modified 4 times for relationship/profile issues (attempts 3, 4, 4, 5) — prompt-level fixes exhausted. **MUST use code-level post-processing validation for relationships.**
- `src/pipeline/character_profiling/post_corrections.py` is the correct location for output-level corrections. Fixes L and M both succeeded here. **Relationship validation should also go here.**
- Nick/Carraway split has never been attempted as a fix target. It should be the #1 priority for attempt 6.

## Attempt 6 Fixes Applied

### Fix N: Nick/Carraway merge + narrator fix [CRITICAL → Characters 7→8+]
- **Location:** `src/agents/characters.py`
- **Method added:** `_find_narrator_in_supporting()` — searches supporting_cast for contiguous word-fragments matching the narrator name (e.g., "Nick" + "Carraway" → "Nick Carraway"), merges them, and promotes to main_cast
- **New step added:** Step 5.8.5b — runs BEFORE the heuristic fallback (Step 5.8.6), prevents Ella Kaye from being selected as narrator when Nick Carraway is correctly identified by summaries but split in supporting cast
- **Test updated:** `test_character_extraction_v2.py` line count limit raised from 8600→8800 to accommodate new method (~80 lines)

### Fix O: Relationship familial label validation [CRITICAL → Profiles 5→6.5+]
- **Location:** `src/pipeline/character_profiling/post_corrections.py`
- **Method added:** `OutputCharacterCorrector.reject_unfounded_familial_labels()` — removes familial labels (husband, wife, mother, etc.) between characters who (1) share no surname component AND (2) have no tight text co-mention (100-char window) with a possessive family phrase
- **Runs:** After `verify_relationships_from_text()` (which can introduce false family labels from large 500-char windows) and before `enforce_gender_consistency()`

### Fix P: Personality traits + speech patterns [CRITICAL → Profiles 6.5→8+]
- **Location:** `src/analyzer.py` profile generation prompt (lines ~2825-2857)
- **Change:** Added `speech_patterns` field to the personality JSON schema in the profile prompt, and updated the fallback instruction to include `"speech_patterns": []`
- **Root cause:** The prompt's personality section never included `speech_patterns`, so LLMs never generated it

### Fix Q: Homograph IPA [HIGH → Pronunciation 7.5→8+]
- **Location:** `src/pipeline/pronunciation_guide/enricher.py`
- **Added:** `HOMOGRAPH_IPA_MAP` — static lookup table with IPA notation for 25 common English homographs (minute, live, close, wind, read, tear, bow, bass, etc.)
- **Updated:** `enrich_homograph()` to use the static lookup before falling back to text-only notes

## Next Action

Run PROMPT_analyze.md for attempt 6. Execute: `audiobook-prep analyze` on gatsby with the fixes applied.
