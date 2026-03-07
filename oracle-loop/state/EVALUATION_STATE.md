# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 1
- **Phase:** awaiting_analysis
- **baseline_score:** 5.90

## Output Files
- HTML: ../output/gatsby/report.html
- JSON: ../output/gatsby/analysis.json

## Latest Scores
- Structure Detection: 10/10 ✓
- Character Extraction: 4.5/10 ✗
  - Completeness: 7/10
  - Identity Resolution: 3/10
  - Alias Grouping: 4/10
- Character Profiles: 2/10 ✗
- Chapter Summaries: 8/10 ✓
- Pronunciation Guide: 7/10 ✗
- HTML Presentation: 8.5/10 ✓
- **Overall: 5.90/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 5.90 | - | Baseline. Profiles catastrophic, character identity broken |

## Current Issues (Priority Order)

### CRITICAL

1. **False narrator: Doctor T. J. Eckleburg tagged as narrator instead of Nick Carraway** [Identity Resolution]
   - Problem: `main_cast_12` "Doctor T. J. Eckleburg" has `is_narrator: true`. Nick Carraway (`main_cast_0`) has `is_narrator: false`.
   - Evidence: Nick Carraway is the first-person narrator of The Great Gatsby. Doctor T. J. Eckleburg is the name on a billboard advertisement (the eyes of Doctor T. J. Eckleburg), not even a person.
   - Impact: Narrator identification is completely wrong. Affects profiles and summaries downstream.
   - Location: V2 narrator detection logic — likely `src/pipeline/character_extraction_v2/` narrator assignment or `src/analyzer.py` narrator detection
   - Fix: The narrator detection heuristic is picking a symbolic entity instead of the actual first-person narrator. Nick Carraway has only 34 mentions (low for a narrator) because first-person narrators refer to themselves as "I" not by name. The pipeline needs to identify the first-person narrator from summary/text evidence, not just mention counts or heuristics.

2. **Protagonist in wrong cast tier with wrong canonical name** [Identity Resolution]
   - Problem: Jay Gatsby — the title character — exists only as `supporting_12` "James Gatz" (268 mentions) with aliases "Jay Gatsby" and "Gatsby". There is NO main_cast entry for Gatsby.
   - Evidence: The novel is called "The Great Gatsby." The character is referred to as "Gatsby" or "Jay Gatsby" throughout 8 of 9 chapters. "James Gatz" is his birth name revealed only in Chapter 6.
   - Impact: The most important character is in the supporting cast with the wrong canonical name.
   - Location: The EVALUATION_STATE notes show "BLOCKED alias: 'James Gatz' and 'Jay Gatsby' appear in summaries but NEVER co-occur in the same chapter and have no name overlap" — so Pass 1 extracted them as separate characters, Pass 2 tried to merge but the co-occurrence check blocked it. The main_cast "Jay Gatsby" entry was likely consumed/removed while "James Gatz" survived in supporting.
   - Fix: The co-occurrence requirement is too strict for identity-reveal patterns (where a character's real name is revealed in a single chapter). A name that appears as an alias of another in summaries AND shares the same role/description should be mergeable even without co-occurrence.

3. **Relationship labels are catastrophically wrong — almost all labeled "husband" or "colleague"** [Profiles]
   - Problem: Nearly every relationship for every character is labeled "husband" or "colleague". Examples:
     - Nick → James Gatz: "husband" (should be "friend/neighbor")
     - Nick → Tom Buchanan: "husband" (should be "cousin-in-law/friend")
     - Nick → Myrtle Wilson: "husband" (nonsensical)
     - Tom → George Wilson: "husband" (should be "acquaintance" or none)
     - James Gatz → George Wilson: "brother" (completely wrong)
     - James Gatz → Henry C. Gatz: "son" (correct but only one)
   - Evidence: The LLM is outputting garbage relationship labels. Only ~1 out of 50+ relationships is correct.
   - Impact: Profiles are completely unusable for narrator preparation. This alone drops Profile score to 2/10.
   - Location: `src/analyzer.py` `_generate_character_profile()` — the relationship extraction prompt or the relationship label vocabulary is broken
   - Fix: The profile generation prompt likely lacks proper relationship label guidance. Should use labels like: parent, child, sibling, spouse, friend, rival, employer, employee, lover, neighbor, acquaintance. The LLM may be defaulting to "husband" as a catch-all male relationship term.

4. **Meyer Wolfsheim / Meyer Wolfshiem duplicate** [Identity Resolution]
   - Problem: Two separate entries for the same character with a spelling variant:
     - `main_cast_7` "Meyer Wolfsheim" (6 mentions) with alias "Meyer Wolfshiem"
     - `supporting_2` "Meyer Wolfshiem" (32 mentions) with alias "Wolfshiem"
   - Evidence: Same character, Fitzgerald actually spelled it "Wolfshiem" in the text. The pipeline created both spellings as separate characters.
   - Location: Cross-tier merge logic in `src/pipeline/character_extraction_v2/` or `src/agents/characters.py` — fuzzy matching for spelling variants across main/supporting cast
   - Fix: Fuzzy string matching (edit distance) should catch single-letter spelling variants like Wolfsheim/Wolfshiem.

### HIGH

5. **Invalid aliases on multiple characters** [Alias Grouping]
   - Problem: Several characters have nonsensical aliases:
     - Tom Buchanan: "the Buchanans' house" (a building), "Tom and Daisy" (a couple)
     - George Wilson: "Wilson's body" (a corpse reference), "her husband" (generic pronoun)
     - Myrtle Wilson: "the woman" (generic descriptor)
     - Dan Cody: "the Tuolomee" (that's Cody's yacht, not Cody)
     - Tom Buchanan: "Tom" appears twice in aliases
   - Location: Alias extraction in V2 pipeline `src/pipeline/character_extraction_v2/main_cast.py` — possessive/compound phrases not filtered
   - Fix: Add validation rules to reject aliases containing possessives ('s), conjunctions ("and"), or that are clearly non-person nouns (house, body). Filter duplicates.

6. **"Buchanan" alias conflict between Tom and Daisy** [Alias Grouping]
   - Problem: "Buchanan" appears as alias for both `main_cast_2` (Daisy) and `main_cast_3` (Tom). A shared surname alias creates ambiguity.
   - Location: Alias deduplication in `src/pipeline/character_extraction_v2/`
   - Fix: When a surname alias is claimed by multiple characters, either remove it from all or assign it to the character who uses it most as a standalone reference.

7. **Owl-eyed man duplicated as two F6 entries** [Identity Resolution]
   - Problem: "The man with owl-eyed glasses" (`f189a657a225`, 1 mention) and "The owl-eyed man" (`3c8fa52c5db5`, 1 mention) are clearly the same character — commonly known as "Owl Eyes."
   - Location: F6 reconciliation in `src/analyzer.py` — no deduplication of descriptive F6 entries
   - Fix: F6 should check if a new entry is a substring/paraphrase of an existing entry before creating a duplicate.

8. **Excessive F6 generic descriptor characters** [Completeness]
   - Problem: 12 F6-reconciled characters, most are generic descriptors: "New York reporter", "Gardener", "Butler" (20 mentions!), "Chauffeur" (10 mentions), "The Lutheran minister", "The war veteran", "The detective", "The postman". These clutter the character list.
   - Location: F6 reconciliation in `src/analyzer.py`
   - Fix: F6 should filter out single-word generic occupational descriptors (butler, chauffeur, gardener, postman, detective) that aren't proper names. "Butler" with 20 mentions is a role, not a character name.

### MEDIUM

9. **No physical description for Nick Carraway** [Profiles]
   - Problem: `physical_description: null` for the narrator/protagonist
   - Evidence: Fitzgerald doesn't describe Nick extensively, but the text mentions he's about 30, from the Midwest. Some physical inference is possible.
   - Location: Profile generation in `src/analyzer.py`

10. **No speech patterns noted for any character** [Profiles]
    - Problem: `speech_pattern: null` for all characters
    - Evidence: Several characters have distinctive speech: Gatsby's "old sport", Wolfshiem's dialect spelling ("gonnegtion", "Oggsford"), Tom's aggressive/domineering tone
    - Location: Profile generation prompt in `src/analyzer.py`

11. **131 of 150 pronunciation entries have MEDIUM confidence** [Pronunciation]
    - Problem: High proportion of medium-confidence entries suggests the model is hedging or json_mode validation is flagging preamble text
    - Evidence: From pipeline notes: "Model refused to invent IPA for obscure proper nouns"
    - Location: Pronunciation pipeline confidence scoring

12. **Common English words flagged as pronunciation entries** [Pronunciation]
    - Problem: Words like "chauffeur", "silhouette", "bureau", "settee" are common English — not unusual enough to flag
    - Location: `src/pipeline/pronunciation/cmu_proposer.py` COMMON_WORDS_WHITELIST
    - Fix: Add these to the whitelist

13. **Chapter 1 summary has repeated name** [Summaries]
    - Problem: "Nick Carraway, Nick Carraway, reflecting on..." — name doubled
    - Location: Summary generation or post-processing

### LOW

14. **"The green light" as a character entry** [Completeness]
    - Per rubric, symbolic objects ARE acceptable extractions. The green light is narratively significant. No action needed, but its relationships are nonsensical (Daisy → green light: "wife").

15. **Vladmir Tostoff spelling** [Pronunciation]
    - Fitzgerald spelled it "Vladimir Tostoff" — the extraction dropped the 'i'. Very minor.

## Fix History

### Attempt 2 fixes

**Fix A: False narrator — STEP 4.26 threshold raised**
- Root cause: `characters.py:run():~1015` STEP 4.26 only reset narrator if `mention_count <= 2`. Doctor T. J. Eckleburg has 5 mentions — too many for the old guard, too few to be a real narrator.
- Fix: Changed threshold from `<= 2` to `<= 5` (with existing `* 5` ratio guard).
- After reset: STEP 4.5b finds vocative candidate "Nick" → STEP 5.8.4 assigns Nick Carraway as narrator.
- Smoke test: Logic trace confirms Eckleburg (5 mentions) now triggers reset; Montresor in Cask (3 mentions, Fortunato=14) does NOT (14 < 15=3*5).

**Fix B: Gatsby cast tier — STEP 5.11 final promotion pass added**
- Root cause: STEP 5.7.5 (pre-promotion mention search) ran before "Jay Gatsby"/"Gatsby" aliases were added to the "James Gatz" supporting character. At STEP 5.8 time, James Gatz had only 4 NER-based mentions (< 50 threshold) and was not promoted. Aliases were added afterward (by some later step), giving 268 total mentions at STEP 5.10.5, but too late for promotion.
- Fix: Added STEP 5.11 after STEP 5.10.5 — re-checks all supporting characters after alias-aware mention counts are updated. Any character with >= protagonist threshold (200 mentions) is promoted to main cast.
- Also: canonical name rename — if canonical has < 10 text mentions but a multi-word alias has 1.5x+ more mentions, use that alias as canonical (e.g., "James Gatz" → "Jay Gatsby" since "Jay Gatsby" has 8 mentions vs 4 for "James Gatz").
- Smoke test: 268 mentions >> 200 threshold; "Jay Gatsby" multi-word alias would be selected as canonical.

**Fix C: Relationship label catastrophe — verify_relationships_from_text guard added**
- Root cause: `post_corrections.py:verify_relationships_from_text():~1877` allowed co-mention window family terms (like "his wife", "her husband") to override ANY existing relationship label, including specific non-family ones like "friend" or "rival". In Gatsby, "husband" appears near almost every character co-mention (Tom = Daisy's husband, George = Myrtle's husband), causing all relationships to be overridden to "husband".
- Fix: Changed `if is_best_family or cur_lower in _generic_labels:` to `if cur_lower in _generic_labels or (is_best_family and is_family):` — only override when (a) current label is generic placeholder, OR (b) both current AND found terms are family (within-family correction like "brother" → "cousin").
- Smoke test: Test `test_text_overrides_llm_relationship` still passes (brother→cousin within-family); "friend" → "husband" would no longer override.

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 2 | False narrator (Eckleburg) | `src/agents/characters.py` (STEP 4.26 threshold) | Pending re-run |
| 2 | Gatsby wrong cast tier + canonical name | `src/agents/characters.py` (STEP 5.11 new) | Pending re-run |
| 2 | Relationship labels all "husband"/"colleague" | `src/pipeline/character_profiling/post_corrections.py` | Pending re-run |

## Configuration Audit
- Model: `qwen3-next:80b-a3b-instruct-q8_0` for all agents (think_mode: false)
- Context length: 32768 — adequate for Gatsby's chapter sizes
- Temperature: 0.7 for all agents — reasonable
- Zero LLM retries across all stages — no prompt/schema failures
- No chunking issues apparent from profiling data

## Next Action
Re-run analysis on gatsby (attempt 2). Fixes applied:
- CRITICAL #1: False narrator → STEP 4.26 threshold raised (≤2→≤5)
- CRITICAL #2: Gatsby cast tier + canonical name → STEP 5.11 added
- CRITICAL #3: Relationship label catastrophe → verify_relationships_from_text guard fixed
CRITICAL #4 (Wolfsheim duplicate) deferred to attempt 3 if needed.
