# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 5
- **Phase:** awaiting_evaluation
- **baseline_score:** 6.55
- **Competitive Mode:** single

## Output Files
- HTML: ../output/gatsby/report.html
- JSON: ../output/gatsby/analysis.json

## Pipeline Notes (Attempt 5)
- Completed in 85m 30s, 295 LLM calls, 464,786 tokens
- 9 chapters detected, 21 characters extracted, 21 profiles generated
- "The butler" still appears (as single entry with UNCERTAIN passages — F6 case dedup may have worked)
- Nick Carraway still not in main_cast (same warning as previous attempts)
- Blocked: Owl Eyes / Eckleburg billboard aliases blocked correctly ✓
- Fix K (butler case dedup), Fix L (unknown relationships), Fix M (narrator prose filter) all applied

## Latest Scores
- Structure Detection: 10/10 ✓
- Character Extraction: 7.5/10 ✗ (FAILING)
  - Completeness: 8/10
  - Identity Resolution: 7.5/10 ← butler/Butler false split
  - Alias Grouping: 7/10 ← Buchanan shared, Wilson misassigned
- Character Profiles: 5/10 ✗ (FAILING) ← primary blocker
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 7.5/10 ✗ (FAILING)
- HTML Presentation: 9/10 ✓
- **Overall: 7.98/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold: Characters 7.5, Profiles 5, Pronunciation 7.5)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.55 | — | Baseline. main_cast pipeline failed; massive false splits; profiles catastrophically wrong |
| 2 | 7.15 | +0.60 | Fix A partially worked (Gatsby aliases resolved); main_cast STILL fails; IPA corruption fixed |
| 3 | 7.93 | +1.38 | Main cast pipeline FIXED (Fix C). 5 false splits resolved. Profiles still wrong. |
| 4 | 7.98 | +1.43 | Fixes G/H/I/J: Eckleburg deduped ✓, "like" removed ✓, Nick rels→unknown (marginal), profiles STILL primary blocker |

## What Changed in Attempt 4
- **Fix G (relationship prompt):** PARTIAL — Nick's relationships improved from wrong familial labels ("daughter", "wife") to "unknown". But many other characters still have wrong familial labels (Daisy→Gatsby "mother", Jordan→Nick "mother", Gatsby→Wolfsheim "husband"). ~25% correct, ~35% unknown, ~40% still wrong.
- **Fix H (physical description validation):** FAILED — Nick's physical_description is STILL narrative text ("a young man at the office suggested that we take a house together..."). The validation either doesn't run at the right point or has a bug.
- **Fix I (Eckleburg duplicate):** SUCCESS ✓ — "T. J. Eckleburg" now an alias of "Doctor T. J. Eckleburg" (main_cast_10)
- **Fix J ("like" exclusion):** SUCCESS ✓ — "like" removed from foreign pronunciation list
- **NEW issue:** "the butler" (a939b1174a88) and "The butler" (431ff1f64d63) are duplicates — F6 reconciliation case sensitivity bug
- **Henry C. Gatz** now has full canonical name with aliases ["Gatsby's father", "Gatz"] ✓

## Current Issues (Priority Order)

### CRITICAL

1. **Relationships still mostly wrong — Fix G insufficient** [Profiles]
   - Problem: Fix G changed the JSON schema example from familial-first to social-first, but the LLM STILL produces wrong familial labels for most non-familial relationships:
     - Daisy → Gatsby: "mother" (WRONG — former lover/romantic interest)
     - Daisy → Nick: "mother" (WRONG — second cousin once removed)
     - Daisy → Jordan: "mother" (WRONG — friend)
     - Jordan → Nick: "mother" (WRONG — romantic interest)
     - Jordan → Gatsby: "mother" (WRONG — acquaintance)
     - Jordan → Daisy: "wife" (WRONG — friend)
     - Jordan → Tom: "wife" (WRONG — acquaintance)
     - Gatsby → Wolfsheim: "husband" (WRONG — business associate)
     - Gatsby → Dan Cody: "son" (CORRECT for protégé reading, but "mentor" or "employer" more accurate)
     - Tom → George: "husband" (WRONG — customer)
     - George → Tom: "husband" (WRONG — business associate)
     - George → Michaelis: "wife" (WRONG — neighbor)
     - Catherine → Tom: "nephew" (WRONG — acquaintance)
     - Catherine → Gatsby: "sister" (WRONG — acquaintance)
     - Myrtle → Tom: "wife" (WRONG — lover/affair)
   - CORRECT: Daisy↔Tom wife/husband ✓, Myrtle↔George wife ✓, Catherine↔Myrtle sister ✓, George→Gatsby "enemy" ✓, Klipspringer→Gatsby "employer" ✓, Wolfsheim→Rosy "deceased associate" ✓, Henry C. Gatz→Gatsby "child" ✓
   - Root cause: The prompt change was too shallow. The LLM (qwen3-next:80b) is heavily biased toward familial labels regardless of example wording. Need either:
     (a) Post-processing validation that rejects familial labels unless both characters share a surname or text explicitly states family relationship, OR
     (b) A constrained enum approach where the LLM picks from a fixed list of NON-familial defaults and only uses familial when explicitly justified, OR
     (c) Lower temperature for relationship extraction (currently 0.7, try 0.3)
   - Location: `src/analyzer.py` — the secondary structuring call around line 2804-2835, or wherever the primary relationship labels are generated
   - **IMPORTANT:** Fix G modified the prompt but didn't add post-processing validation. Given that 3 prompt-level attempts haven't fixed this, the next fix MUST add code-level validation/correction as a post-processing step.

2. **Personality traits and speech patterns ALL null** [Profiles]
   - Problem: All 21 characters have `personality_traits: null` and `speech_pattern: null`. Critical for narrator preparation.
   - Evidence: `with_traits: 0/21`, `with_speech: 0/21`
   - Missing examples: Gatsby's "old sport" catchphrase, Wolfsheim's accent (Oggsford, gonnegtion), Tom's aggressive/domineering speech, Daisy's "low, thrilling voice"
   - Location: Profile extraction schema in `src/pipeline/character_extraction_v2/` — the profile prompt and/or response schema likely don't include these fields
   - Fix: Ensure the profile extraction template explicitly requests personality_traits and speech_pattern, and that the Pydantic model includes them

### HIGH

3. **Nick Carraway physical_description is narrative text — Fix H didn't work** [Profiles]
   - Problem: Nick's physical_description is STILL: "a young man at the office suggested that we take a house together in a commuting town..."
   - Evidence: This is clearly narrative text, not a physical description
   - Root cause of Fix H failure: The validation was added at line ~1862-1883 of analyzer.py but either:
     (a) It runs BEFORE the narrator appearance injection step overwrites the field (the pipeline notes from analyze phase warned about this), OR
     (b) The validation regex/logic doesn't match this specific string
   - Location: Need to trace the exact order of operations: profile extraction → Fix H validation → narrator appearance injection. If narrator injection runs AFTER validation, the validation is useless.
   - Fix: Either move the validation AFTER the narrator appearance injection step, or fix the narrator appearance injection to not overwrite validated fields with narrative text

4. **Gatsby and Myrtle physical descriptions NULL** [Profiles]
   - Problem: Two of the five most important characters have no physical description
   - Gatsby: Should describe elegant appearance, tanned, gorgeous smile, formal dress, "an elegant young roughneck"
   - Myrtle: Should describe stout/thick-bodied, sensuous vitality, mid-thirties, faintly stout
   - Location: Profile extraction prompt — LLM may not find descriptions for these characters in their profile chunks
   - Fix: This may resolve if the profile prompt is improved for traits/speech (issue #2). If not, may need to increase chunk overlap or add a second-pass extraction for major characters with missing descriptions

5. **"the butler" / "The butler" false split** [Identity Resolution]
   - Problem: F6 reconciliation created two entries from case-variant mentions: a939b1174a88 "the butler" and 431ff1f64d63 "The butler", both with 13 mentions
   - Evidence: Both appear as separate character profiles in the HTML (lines 1204, 1253) with identical relationships
   - Location: F6 reconciliation in `src/analyzer.py` (~lines 1220-1240) — case-insensitive comparison not applied
   - Fix: Normalize to lowercase when comparing character names in F6 reconciliation. Merge entries that differ only in capitalization.

6. **"Wilson" alias misassigned to Myrtle instead of George** [Alias Grouping]
   - Problem: Myrtle Wilson has alias "Wilson" but in the text, bare "Wilson" almost always refers to George Wilson (garage scenes, after Myrtle's death)
   - Location: Main cast alias resolution assigns surname to first character encountered
   - Fix: Difficult to fix generically without text co-occurrence analysis. Lower priority than profiles.

7. **"Buchanan" alias shared between Tom and Daisy** [Alias Grouping]
   - Problem: Both main_cast_2 (Daisy) and main_cast_3 (Tom) list "Buchanan" as an alias, creating ambiguity
   - Fix: When a surname alias would be shared, either assign to the character more commonly called by surname alone (Tom, in this case), or remove from both

### MEDIUM

8. **Chapter 7 summary has factual error about car arrangement** [Summaries]
   - Problem: Summary says "Daisy and Tom returning home in Gatsby's car, leaving Gatsby behind" — but it was Daisy and GATSBY who took Gatsby's car home (with Daisy driving). Tom, Nick, and Jordan followed in Tom's car.
   - Evidence: The summary then correctly notes "Tom, unaware it was Daisy driving" — which contradicts placing Tom in the same car. Internal inconsistency.
   - Impact: Minor — doesn't affect overall summary quality score significantly but worth noting
   - Location: Summary generation temperature or prompt

9. **Missing "Owl Eyes"** [Completeness]
   - Problem: The bespectacled man from Gatsby's library (Ch 3, Ch 9 funeral) not in character list
   - Evidence: Ch 9 summary mentions "the owl-eyed man" but he's not a character entry
   - Impact: Minor character but narratively significant (only non-family funeral attendee)

10. **19 homograph entries lack IPA** [Pronunciation]
    - Problem: All homographs (minute, live, close, wind, read, does, subject, row, excuse, elaborate, intimate, content, bow, refuse, bass, entrance, polish, separate, moderate) have `ipa: null`
    - Evidence: These are exactly the words narrators most need guidance for
    - Fix: The pronunciation enrichment pipeline should provide both IPA variants for homographs

11. **66 pronunciation entries still "unknown"** [Pronunciation]
    - Problem: Many classifiable words remain unknown: dialect (gonnegtion, comin, prac), literary (murmurous, contralto, extemporizing), archaic (plagiaristic, decencies)
    - Fix: Expand reclassification heuristics beyond capitalization

### LOW

12. **"aluminium" flagged as foreign** [Pronunciation]
    - Borderline — standard British English spelling. American narrators might need the note.

13. **Doctor T. J. Eckleburg self-relationship** [Profiles]
    - Eckleburg has a relationship entry to itself: `"Doctor T. J. Eckleburg": "unknown"`. Harmless but odd.

## Configuration Audit

### Model Configuration
- Model: qwen3-next:80b-a3b-instruct-q8_0 (Ollama) — same model for all agents
- Context length: 32768 — adequate for Gatsby
- Temperature: 0.7 for all agents — **too high for relationship extraction** (see CRITICAL #1)
- think_mode: false

### Processing Issues
- Character Profiles: 53 LLM calls, 1855s — time invested but quality still poor due to prompt/schema issues
- No LLM retries or parse failures — pipeline is stable mechanically
- 1 low-confidence profile (McKee: 0.30) — expected for a very minor character

### Recommendation
- MEDIUM: Consider lowering temperature to 0.3 for relationship extraction specifically, to reduce hallucinated familial labels

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
**Fix K: Butler/Butler F6 case dedup** [HIGH] — Added `f6_seen_normalized` set to track normalized names within each F6 pass; prevents "the butler"/"The butler" from being added as separate characters when they appear with different capitalization in different chapter summaries. (src/analyzer.py)
**Fix L: Remove "unknown" relationships** [CRITICAL] — Added `clean_unknown_relationships()` to OutputCharacterCorrector.run_all(); strips relationship entries where the value is "unknown" since they provide no information. Smoke test: Nick's 4 "unknown" entries were removed, leaving only meaningful ones. (src/pipeline/character_profiling/post_corrections.py)
**Fix M: Narrator appearance prose filter** [HIGH] — Added `_is_compact_physical_description()` density check; narrator appearance injection now rejects extractions where len > 60 AND descriptor_score/len < 0.04 (narrative prose), preventing Nick's appearance from being set to "a young man at the office suggested..." (src/pipeline/character_profiling/post_corrections.py)

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

**Pattern alert:** `src/analyzer.py` has been modified 3 times for relationship/profile issues (attempts 3, 4, 4) without resolving the core problem. The fix phase should consider whether the issue is in the profile extraction pipeline (`src/pipeline/character_extraction_v2/`) rather than the secondary structuring call in analyzer.py.

## Next Action

Re-run analysis (Attempt 5) to verify fixes K/L/M. Expected improvements:
- Character Extraction: butler/Butler dedup removed → +0.5 Identity Resolution
- Character Profiles: "unknown" relationships removed → cleaner relationships dict; Nick appearance no longer narrative prose → +1 or more
- Remaining open issues: hallucinated familial relationship labels (Daisy→Gatsby "mother", etc.) if LLM still generates them before clean_unknown strips "unknown" but NOT wrong-non-unknown labels; Gatsby/Myrtle null appearance
