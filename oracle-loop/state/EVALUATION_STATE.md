# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 4
- **Phase:** awaiting_evaluation
- **baseline_score:** 6.55
- **Competitive Mode:** single

## Output Files
- HTML: ../output/gatsby/report.html
- JSON: ../output/gatsby/analysis.json

## Pipeline Notes (Attempt 4)
- Analysis completed in 76m 39s
- 9 chapters, 21 characters, 129 pronunciation flags
- **James Gatz alias**: BLOCKED by co-occurrence check during one proposer run, but final output shows "Jay Gatsby (aka Gatsby, James Gatz)" — alias IS present in final result
- **Nick appearance injection WARNING**: "Final narrator appearance injection for 'Nick Carraway'" still shows narrative text ("a young man at the office suggested that we take a house together..."). Fix H may not catch this — there appears to be a separate "narrator appearance injection" step that runs AFTER Fix H's validation check and overwrites the field.
- **"Buchanan" alias shared**: Both Daisy and Tom still list "Buchanan" as alias
- **"Wilson" alias**: Still assigned to Myrtle Wilson (not George)
- Pronunciation: 66 unknown (was 67), 29 proper_noun (was 28), 15 foreign, 19 homograph
- No LLM parse failures or pipeline crashes
- 1 low-confidence profile (McKee: 0.30)

## Latest Scores
- Structure Detection: 10/10 ✓
- Character Extraction: 7.5/10 ✗ (FAILING)
  - Completeness: 8/10
  - Identity Resolution: 8/10
  - Alias Grouping: 7/10 ← shared ambiguous aliases, Eckleburg duplicate
- Character Profiles: 4/10 ✗ (FAILING) ← primary blocker
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 7.5/10 ✗ (FAILING)
- HTML Presentation: 9/10 ✓
- **Overall: 7.93/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold: Characters 7.5, Profiles 4, Pronunciation 7.5)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.55 | — | Baseline. main_cast pipeline failed; massive false splits; profiles catastrophically wrong |
| 2 | 7.15 | +0.60 | Fix A partially worked (Gatsby aliases resolved); main_cast STILL fails; IPA corruption fixed |
| 3 | 7.93 | +1.38 | Main cast pipeline FIXED (Fix C). 5 false splits resolved. Profiles still wrong. |

## Key Improvements in Attempt 3
- **Main cast pipeline now works!** 9 characters from main_cast (was 0 in attempts 1-2)
- **All 5 major false splits from attempt 2 are FIXED**: Nick/Carraway → Nick Carraway, Tom/Tom Buchanan → Tom Buchanan, Jordan/Jordan Baker → Jordan Baker, Daisy now "Daisy Buchanan", Wilson disambiguation improved
- **Narrator correctly assigned** to Nick Carraway (was wrongly "Jordan" in attempt 2)
- **Foreign pronunciation false positives reduced** — kitchen, cigarette removed (Fix E)
- **UNKNOWN→PROPER_NOUN reclassification** — 28 proper nouns now categorized (was 3)

## Current Issues (Priority Order)

### CRITICAL

1. **Relationships still catastrophically wrong** [Profiles]
   - Problem: Fix D (preventing secondary overwrites + adding examples to template) did NOT fix the root cause. The LLM is producing nonsensical relationship labels:
     - Nick → Daisy: "daughter" (WRONG — second cousin once removed)
     - Nick → Tom: "daughter" (WRONG — college acquaintance)
     - Nick → Jordan: "mother" (WRONG — romantic interest)
     - Nick → Gatsby: "wife" (WRONG — friend/neighbor)
     - Gatsby → Wolfsheim: "husband" (WRONG — business associate)
     - Gatsby → Dan Cody: "son" (WRONG — protégé/employee)
     - McKee → Myrtle: "husband" (WRONG — party guest)
     - Catherine → Tom: "nephew" (WRONG — acquaintance)
     - Some CORRECT: Daisy ↔ Tom "wife"/"husband" ✓, Myrtle ↔ George "wife" ✓, Catherine ↔ Myrtle "sister" ✓
   - Evidence: ~30% correct, 30% "unknown", 40% wrong labels. The relationship type vocabulary is too limited — labels like "daughter", "wife", "husband", "mother", "son", "sister" are being forced onto non-familial relationships
   - Root cause: The relationship prompt/schema allows only familial labels plus "unknown" and freeform strings. The LLM defaults to familial labels when forced to classify non-familial relationships. Need to expand the allowed types to include: friend, romantic_interest, rival, employer, employee, business_associate, mentor, acquaintance, neighbor, etc.
   - Location: Must find and fix the relationship extraction prompt in `src/pipeline/character_extraction_v2/` or `src/analyzer.py` secondary structuring call
   - **IMPORTANT:** Fix D modified the secondary structuring call in `src/analyzer.py` but the primary relationship source may be the profile extraction pipeline. Need to trace which pipeline actually produces these labels.

2. **Personality traits and speech patterns ALL null** [Profiles]
   - Problem: All 21 characters have `personality_traits: null` and `speech_pattern: null`. This is critical for narrator preparation — Gatsby's "old sport" catchphrase, Wolfsheim's accent (Oggsford, gonnegtion), Tom's aggressive speech are all missing.
   - Evidence: `with_traits: 0/21`, `with_speech: 0/21`
   - Location: Profile generation in `src/pipeline/character_extraction_v2/` — the profile prompt may not request these fields, or the schema may not include them
   - Fix: Ensure the profile extraction prompt explicitly requests personality traits and speech patterns, and that the response schema includes these fields

### HIGH

3. **Main character physical descriptions missing or wrong** [Profiles]
   - Problem:
     - Nick Carraway: physical_description is WRONG — contains narrative text ("a young man at the office suggested that we take a house together...") instead of physical appearance
     - Jay Gatsby: NULL — should describe his elegant appearance, gorgeous smile, tanned, formal dress
     - Daisy Buchanan: NULL — should mention beautiful face, white dress, musical/thrilling voice
     - Myrtle Wilson: NULL — should mention stout, thick-bodied, sensuous vitality
   - Evidence: 4 of 5 main characters have missing or wrong physical descriptions
   - Location: Profile extraction prompt — LLM sometimes returns arbitrary text instead of physical description
   - Fix: Tighten the profile prompt to explicitly request ONLY physical appearance details (hair, build, clothing, distinguishing features). Add a validation step that rejects descriptions not containing physical terms.

4. **"T. J. Eckleburg" duplicate of "Doctor T. J. Eckleburg"** [Identity Resolution / Alias Grouping]
   - Problem: main_cast_12 "Doctor T. J. Eckleburg" and supporting_14 "T. J. Eckleburg" are the same entity listed twice
   - Evidence: Both have 5 mentions, both describe the same billboard eyes
   - Location: Post-extraction merge logic — supporting_cast entries aren't being deduplicated against main_cast when one is a substring of the other
   - Fix: Add fuzzy/substring matching when reconciling supporting_cast against main_cast. "T. J. Eckleburg" should match "Doctor T. J. Eckleburg".

5. **"Wilson" alias misassigned to Myrtle instead of George** [Alias Grouping]
   - Problem: Myrtle Wilson (main_cast_5) has aliases ["Myrtle", "Wilson"]. George Wilson (supporting_17) has aliases ["George"]. In the text, bare "Wilson" almost always refers to George Wilson, not Myrtle. The alias assignment is inverted for the surname.
   - Evidence: George Wilson is the character usually called "Wilson" in the narrative (garage scene, after Myrtle's death)
   - Location: Main cast alias resolution — surname aliases should be assigned based on text usage frequency
   - Fix: This is difficult to fix generically. The main_cast pipeline assigned "Wilson" to Myrtle because she's listed first. A post-processing step could check which character "Wilson" more often co-occurs with in context.

6. **"Buchanan" alias shared between Tom and Daisy** [Alias Grouping]
   - Problem: Both Daisy Buchanan and Tom Buchanan list "Buchanan" as an alias. This creates ambiguity — which character does bare "Buchanan" refer to?
   - Evidence: main_cast_2 and main_cast_3 both have "Buchanan" in aliases
   - Fix: When a surname alias would be shared between two characters, either assign it to the character more commonly referred to by surname alone, or remove it from both to avoid ambiguity.

### MEDIUM

7. **Missing "Owl Eyes" (the owl-eyed man)** [Completeness]
   - Problem: The bespectacled man from Gatsby's library (Ch 3) who appears at Gatsby's funeral (Ch 9) is not in the character list. He's narratively significant — one of only a few non-family attendees at the funeral.
   - Evidence: Ch 9 summary mentions "the man with owl-eyed glasses" but he's not a character entry
   - Location: May be filtered by mention count threshold or not detected by NER
   - Fix: Check if "Owl Eyes" or "owl-eyed" appears in NER candidates; may need lower threshold for nicknamed characters

8. **"Gatz" (supporting_13) should be "Henry C. Gatz"** [Completeness]
   - Problem: Supporting character "Gatz" with 11 mentions is Gatsby's father Henry C. Gatz. The canonical name should include his full name. "Gatz" alone is confusing because "James Gatz" is Jay Gatsby's real name.
   - Evidence: Ch 9 summary explicitly mentions "Gatsby's father, Henry C. Gatz, arrives from Minnesota"
   - Location: Supporting cast extraction or F6 reconciliation didn't use the full name
   - Fix: Minor — could be handled by better NER or by F6 reconciliation preferring full names from chapter summaries

9. **"like" flagged as foreign pronunciation** [Pronunciation]
   - Problem: The common English word "like" is categorized as "foreign" in the pronunciation guide
   - Evidence: `jq` shows "like" in foreign category list
   - Location: `src/pipeline/pronunciation_guide/proposers/foreign_proposer.py`
   - Fix: Add "like" to ENGLISH_EXCEPTIONS list

10. **67 pronunciation entries still categorized as "unknown"** [Pronunciation]
    - Problem: Many unknown entries are classifiable: dialect words (gonnegtion, comin, prac), literary terms (murmurous, contralto, extemporizing), archaic words (plagiaristic, decencies), etc.
    - Evidence: Only 28 upgraded to proper_noun by Fix F; 67 remain unknown
    - Fix: Expand the reclassification logic in consolidator.py beyond just capitalized words — add heuristics for dialect spellings, literary/archaic terms

11. **19 homograph entries lack IPA** [Pronunciation]
    - Problem: Homographs (minute, live, close, wind, read, does, subject, row, excuse, elaborate) all have `ipa: null`. These are exactly the words narrators need pronunciation guidance for.
    - Evidence: All 19 homograph entries have null IPA
    - Fix: The pronunciation enrichment pipeline should provide BOTH IPA variants for homographs (e.g., /rɛd/ vs /riːd/ for "read")

### LOW

12. **"aluminium" flagged as foreign** [Pronunciation]
    - Problem: "aluminium" is the standard British English spelling, not truly foreign
    - Evidence: Listed as foreign category
    - Fix: Could add to ENGLISH_EXCEPTIONS, though it's borderline — American narrators might need the note

## Configuration Audit

### Model Configuration
- Model: qwen3-next:80b-a3b-instruct-q8_0 (Ollama) — same model for all agents
- Context length: 32768 — adequate for Gatsby (48K words)
- Temperature: 0.7 for all agents — may be too high for structured extraction (character profiles, relationships)
- think_mode: false — disables chain-of-thought

### Processing Issues
- Character Extraction: 32 LLM calls, 315s — reasonable, main_cast pipeline now working
- Character Profiles: 53 LLM calls, 1855s — significant time but profiles still poor quality. The prompt/schema is the issue, not processing.
- Pronunciation Guide: 118 LLM calls, 639s — high call count suggests per-word enrichment
- No LLM retries or parse failures — pipeline is stable

## Fix History

### flowers_for_algernon — Deferred (image-based PDF, no OCR available)

### gatsby — Attempt 2 Fixes

**Fix A: Include `characters_present` in summaries for main_cast LLM extraction** [CRITICAL]
- Modified `src/agents/characters.py:_get_chapter_summaries()` to prefix summaries with character lists
- Result: PARTIAL — aliases improved but main_cast grounding still rejected all candidates

**Fix B: IPA validation to reject corrupt entries** [MEDIUM]
- Added `_is_valid_ipa()` in `src/pipeline/pronunciation_guide/enricher.py`
- Result: SUCCESS ✓

### gatsby — Attempt 3 Fixes

**Fix C: Main cast prompts changed to dict wrapper format** [CRITICAL]
- Changed both `CHARACTER_IDENTIFICATION_PROMPT` and `MAIN_CAST_PROMPT` in `main_cast.py` from bare JSON array to `{"characters":[...]}` dict wrapper
- Result: SUCCESS ✓ — main_cast pipeline now produces 9 characters

**Fix D: Secondary relationship call no longer overwrites primary** [CRITICAL]
- Modified `src/analyzer.py` secondary structuring call to only set relationships when primary produced none; added relationship examples to template
- Result: PARTIAL — relationships still catastrophically wrong. The primary pipeline itself produces bad labels. Secondary overwrite prevention doesn't help if primary output is bad.

**Fix E: Pronunciation false positive exclusions** [MEDIUM]
- Added kitchen/cigarette/week/chicken etc. to ENGLISH_EXCEPTIONS in `foreign_proposer.py`
- Result: SUCCESS ✓ — kitchen, cigarette, week removed

**Fix F: UNKNOWN → PROPER_NOUN reclassification** [MEDIUM]
- Capitalized UNKNOWN words upgraded to PROPER_NOUN in `consolidator.py`
- Result: PARTIAL — 28 now proper_noun (was 3), but 67 still unknown

### gatsby — Attempt 4 Fixes

**Fix G: Relationship prompt — replace biasing familial examples with diverse social/professional ones** [CRITICAL]
- Root cause: JSON schema example used `(e.g., 'father', 'friend', 'rival')` with "father" as first example, biasing LLM toward familial labels for non-familial relationships. LLM returned "daughter", "wife", "mother" for Nick→Daisy, Nick→Jordan, Nick→Gatsby etc.
- Changed JSON schema example to `(e.g., 'romantic interest', 'close friend', 'rival', 'mentor', 'acquaintance', 'employer', 'business partner')`
- Replaced RELATIONSHIPS EXTRACTION section examples with explicit rule: "Use familial labels ONLY when text EXPLICITLY states a family relationship. If unclear, use 'acquaintance' or 'unknown'."
- Smoke test: N/A (prompt change — verified correct examples in output)
- Modified: `src/analyzer.py` (line ~2804-2835)

**Fix H: Physical description validation** [HIGH]
- Root cause: LLM returned narrative text ("a young man at the office suggested that we take a house together...") as Nick's appearance.summary instead of physical descriptors. Any appearance summary >80 chars with no physical terms is likely wrong.
- Added post-processing check: if `appearance.summary` is >80 chars and contains no physical terms (hair, eyes, tall, slim, etc.), reset to "unknown"
- Universal invariant: physical descriptions must contain physical descriptor words
- Modified: `src/analyzer.py` (lines ~1862-1883)

**Fix I: Eckleburg duplicate — reverse title check** [HIGH]
- Root cause: `_merge_lastname_aliases` only handled SUPPORTING-has-title case (e.g., "Mr. X" → "X"). It didn't handle MAIN-has-title case (e.g., main_cast "Doctor T. J. Eckleburg" vs supporting_cast "T. J. Eckleburg").
- Added "Doctor", "Professor", "Reverend", "Rev.", "Prof." to `_strip_title` titles list
- Added reverse check in `_merge_lastname_aliases`: when main_cast name stripped of titles matches supporting_cast name, merge as alias
- Universal invariant: title-free and title-prefixed versions of the same name should merge
- Modified: `src/agents/characters.py` (lines ~1545, 2577-2600)

**Fix J: "like" pronunciation exception** [LOW]
- Added "like" to ENGLISH_EXCEPTIONS in `foreign_proposer.py`
- Modified: `src/pipeline/pronunciation_guide/proposers/foreign_proposer.py`

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | (baseline — no fixes yet) | — | — |
| 2 | Main cast pipeline failure (data) | `src/agents/characters.py` | Partial — aliases improved but grounding still fails |
| 2 | IPA corruption | `src/pipeline/pronunciation_guide/enricher.py` | Fixed ✓ |
| 3 | Main cast grounding failure (JSON format) | `src/pipeline/character_extraction_v2/main_cast.py` | Fixed ✓ — main_cast produces 9 characters |
| 3 | Relationship labels wrong (secondary overwrites) | `src/analyzer.py` | No change — primary pipeline also produces bad labels |
| 3 | Pronunciation false positives | `src/pipeline/pronunciation_guide/proposers/foreign_proposer.py` | Fixed ✓ |
| 3 | UNKNOWN pronunciation categorization | `src/pipeline/pronunciation_guide/consolidator.py` | Partial — 28 reclassified, 67 remain |
| 4 | Relationship biased toward familial labels | `src/analyzer.py` | Pending analysis |
| 4 | Physical description returns narrative text | `src/analyzer.py` | Pending analysis |
| 4 | Eckleburg duplicate (Doctor/no-Doctor) | `src/agents/characters.py` | Pending analysis |
| 4 | "like" flagged as foreign | `src/pipeline/pronunciation_guide/proposers/foreign_proposer.py` | Pending analysis |

## Next Action

Re-run analysis (gatsby attempt 4) to verify:
1. Relationships are now reasonable (not catastrophically wrong with familial labels)
2. Nick's appearance.summary is "unknown" instead of narrative text
3. "T. J. Eckleburg" supporting entry merged into "Doctor T. J. Eckleburg" main cast
4. "like" removed from pronunciation guide
