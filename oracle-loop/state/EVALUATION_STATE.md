# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 6
- **Phase:** awaiting_evaluation
- **baseline_score:** 5.90

## Output Files
- HTML: ../output/gatsby/report.html
- JSON: ../output/gatsby/analysis.json

## Latest Scores
- Structure Detection: 10/10 ✓
- Character Extraction: 5.5/10 ✗
  - Completeness: 7/10
  - Identity Resolution: 4.5/10
  - Alias Grouping: 5/10
- Character Profiles: 4/10 ✗
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 7.08/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 5.90 | - | Baseline. Profiles catastrophic, character identity broken |
| 2 | 6.73 | +0.83 | Relationships partially improved for main cast. Core narrator/Gatsby issues UNFIXED |
| 3 | 7.20 | +1.30 | Narrator FIXED (Nick ✓). Gatsby still supporting. "colleague" spam persists |
| 4 | 6.93 | +1.03 | REGRESSION: Gatsby promoted but narrator BROKE AGAIN. Colleague filter FAILED |
| 5 | 7.08 | +1.18 | Narrator FIXED ✓ (Fix I/J). Colleague filter STILL FAILED (192 remain). No speech patterns. |

## What Improved in Attempt 5
- **Fix I WORKED**: Nick Carraway is correctly identified as narrator with `is_narrator: true, role: "protagonist"`. Henry C. Gatz now has `is_narrator: false, role: "supporting"`. The relative mention guard (8% threshold) successfully blocked Henry (13/269 = 4.8%).
- **Role inflation FIXED**: Henry C. Gatz demoted to "supporting". The green light demoted to "supporting". No more spurious "protagonist" labels.
- **George Wilson name fixed**: Now "George Wilson" (88 mentions) — the fabricated "B." middle initial is gone.
- **Jay Gatsby correctly positioned**: main_cast_1, role "protagonist", 269 mentions, aliases [Gatsby, James Gatz, the poor son-of-a-bitch].

## What Did NOT Improve
- **"colleague" spam STILL pervasive**: 192/236 relationship entries are "colleague" (was 198 in attempt 4). Fix K (substring filter) was essentially ineffective — only removed 6 entries.
- **Speech patterns still all null**: 0/33 characters have speech_pattern. Fix was not attempted.
- **Jay Gatsby has NO physical description**: The protagonist has `physical_description: null`. Only 10/33 characters have descriptions.
- **F6 generic descriptor clutter persists**: butler (20), chauffeur (10), gardener (5), Reporter (2), Detective (1), Lutheran minister (1), The West Egg postman (1) — all generic roles, not named characters.
- **Owl Eyes still duplicated**: "Owl Eyes" (f6, 1 mention) and "The man with owl-eyed glasses" (f6, 1 mention) — same character.
- **Wolfsheim TRIPLICATED**: main_cast (missing?), supporting_9 "Meyer Wolfshiem" (32 mentions), f6 "Meyer Wolfsheim" (2 mentions). The canonical Wolfshiem/Wolfsheim is split three ways.
- **Green light merged with Eckleburg eyes**: main_cast_13 "The green light" has alias "The eyes of Doctor T. J. Eckleburg" — these are completely different symbols. The green light = Gatsby's longing for Daisy. Eckleburg's eyes = moral/divine judgment over the valley of ashes.
- **"Tom and Daisy" as alias of Tom Buchanan**: This is a pair reference, not an alias for Tom alone.
- **"Wilson's body" as alias of George Wilson**: Inappropriate — refers to his corpse, not a name variant.
- **"the poor son-of-a-bitch" as alias of Gatsby**: This is a quote from Owl Eyes, not an alias.

## Current Issues (Priority Order)

### CRITICAL

1. **"colleague" relationship spam — 192/236 entries (81%)** [Profiles]
   - Problem: Fix K changed `startswith` to substring `in` check, but 192 "colleague" entries remain — virtually unchanged from 198 in attempt 4
   - Evidence: Nick→Tom is "colleague" (should be "cousin's husband" or "acquaintance"). Gatsby→Henry C. Gatz is "colleague" (should be "father"). Gatsby→Jordan is "colleague" (should be "social acquaintance").
   - **Root cause hypothesis**: The filter code exists but relationships are being SET after the filter runs. The LLM is generating "colleague" as a default label for any character pair it can't classify, and the post-processing filter isn't the last step.
   - **Fix approach**: The filter must be the ABSOLUTE LAST step before JSON serialization. Add a final cleanup in the `analyze()` method's return path that iterates ALL characters and removes any relationship with "colleague" in the value. This must happen AFTER all profiling, post-corrections, and enrichment.
   - Location: `src/analyzer.py` — find where `analysis_result` is constructed/returned and add cleanup there
   - **Pattern alert**: This is the 3rd attempt to fix "colleague" (prompt: attempt 3, startswith: attempt 4, substring: attempt 5). All failed. The filter code may not be in the execution path at all, or relationships are rebuilt after it runs.

2. **Speech patterns null for ALL 33 characters** [Profiles]
   - Problem: Zero `speech_pattern` entries. This is critical data for narrator prep.
   - Missing examples: Gatsby's "old sport" catchphrase, Wolfshiem's dialect ("Oggsford", "gonnegtion"), Tom's aggressive/authoritative tone, Daisy's "low, thrilling voice"
   - Location: `src/analyzer.py` — `_generate_character_profile()` prompt likely doesn't request speech patterns, or response parser drops the field
   - Fix: Ensure profiler prompt explicitly requests speech patterns/verbal mannerisms and parser captures them

### HIGH

3. **Wolfsheim triplicated across pipelines** [Identity Resolution]
   - supporting_9 "Meyer Wolfshiem" (32 mentions) — main extraction with original Fitzgerald spelling
   - f6 "Meyer Wolfsheim" (2 mentions) — F6 reconciliation with "corrected" spelling
   - The character with most mentions (32) is in supporting cast, not main cast
   - Location: Cross-pipeline merge needed — supporting→main promotion + F6 dedup with fuzzy spelling match
   - Fix: Add Levenshtein/fuzzy matching in F6 reconciliation to catch near-identical names (Wolfshiem vs Wolfsheim)

4. **Green light falsely merged with Eckleburg eyes** [Identity Resolution]
   - main_cast_13 "The green light" has alias "The eyes of Doctor T. J. Eckleburg"
   - These are two completely different symbols with different meanings and locations
   - T. J. Eckleburg also exists as separate supporting_10 (5 mentions) — so the eyes are both an alias AND a separate character
   - Location: V2 alias resolution or post-extraction merge
   - Fix: These should be separate entities. Block merge when both entities are symbolic/non-human

5. **Jay Gatsby has no physical description** [Profiles]
   - The protagonist (269 mentions) has `physical_description: null`
   - Fitzgerald describes Gatsby: "an elegant young rough-neck, a year or two over thirty, whose elaborate formality of speech just missed being absurd"
   - Other main characters (Daisy, Tom, Jordan) have descriptions
   - Location: `src/analyzer.py` — profile generation for Gatsby specifically failing

6. **F6 generic descriptor clutter: 7+ non-character entries** [Completeness]
   - butler (20 mentions), chauffeur (10), gardener (5), Reporter (2), Detective (1), Lutheran minister (1), The West Egg postman (1)
   - These are roles/occupations, not named characters
   - Location: F6 reconciliation in `src/analyzer.py` — needs filter for generic role descriptors
   - Fix: Add blocklist of generic occupation words (butler, chauffeur, gardener, reporter, detective, minister, postman) in F6

7. **Owl Eyes duplicated** [Identity Resolution]
   - "Owl Eyes" (f6, 1 mention) and "The man with owl-eyed glasses" (f6, 1 mention) — same character
   - Both from F6 reconciliation (hash IDs)
   - Location: F6 merge logic needs fuzzy/substring matching

### MEDIUM

8. **Invalid aliases on main characters** [Alias Grouping]
   - Tom Buchanan has alias "Tom and Daisy" — pair reference, not alias
   - George Wilson has alias "Wilson's body" — corpse reference, not alias
   - Jay Gatsby has alias "the poor son-of-a-bitch" — quote, not alias
   - "Buchanan" shared between Tom and Daisy — ambiguous surname
   - Location: V2 alias validation in `src/pipeline/character_extraction_v2/main_cast.py`

9. **Henry C. Gatz still has fabricated middle initial** [Identity Resolution]
   - Fitzgerald never uses a middle initial for Gatsby's father — he's just "Henry C. Gatz" or "Mr. Gatz"
   - Wait — actually checking: Fitzgerald DOES use "Henry C. Gatz" in Chapter 9 when the father introduces himself. This is CORRECT. Withdrawing this issue.

10. **Catherine lacks context** [Completeness]
    - "Catherine" (supporting_4, 14 mentions) has no alias linking her to Myrtle Wilson as her sister
    - A narrator needs to know she's "Myrtle's sister Catherine"
    - Location: Profile generation or alias resolution

## Fix History

### Attempt 2 fixes
- **Fix A: STEP 4.26 narrator threshold** — INEFFECTIVE (wrong layer)
- **Fix B: STEP 5.11 promotion** — INEFFECTIVE (code not firing)
- **Fix C: Relationship label override guard** — PARTIALLY EFFECTIVE

### Attempt 3 fixes
- **Fix D: Narrator layered defense (narrator.py + characters.py)** — EFFECTIVE ✓ (but regressed in attempt 4)
- **Fix E: "colleague" forbidden in profiler prompt** — INEFFECTIVE (LLM ignores forbidden list)
- **Fix F: STEP 5.11 diagnostic logging** — ADDED but promotion still didn't fire

### Attempt 4 fixes
- **Fix G: Role safety net in analyzer.py** — PARTIALLY EFFECTIVE (Gatsby promoted ✓, but caused narrator regression and role inflation)
- **Fix H: "colleague" filter in post-processing** — COMPLETELY INEFFECTIVE (198 "colleague" entries remain)

### Attempt 5 fixes
- **Fix I: Relative mention guard in narrator.py** — EFFECTIVE ✓ (Henry C. Gatz blocked as narrator)
- **Fix J: Step 6.6 narrator fallback minimum raised to 20** — EFFECTIVE ✓ (backstop for low-mention candidates)
- **Fix K: Colleague substring filter** — INEFFECTIVE (192 remain, down from 198 — negligible improvement)

### Attempt 6 fixes
- **Fix L: Disabled `add_text_window_cooccurrence_relationships()` call in `post_corrections.py:run_all()`** — Root cause of 192 "colleague" entries: this function runs AFTER profile generation filter and adds "colleague" to all co-occurring character pairs. Disabled by removing call from run_all(). All 3 previous attempts filtered LLM output; the real source was this post-profile function. Expect ~192 fewer "colleague" entries.
- **Fix M: Block " and " pair-reference aliases in `verify_aliases()`** — "Tom and Daisy" (and similar) blocked by new invariant check before Rule 0.4. Universal: "X and Y" is never a valid alias for a single character in any book.

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 2 | False narrator (Eckleburg) | `src/agents/characters.py` (STEP 4.26 threshold) | No change — wrong layer |
| 2 | Gatsby wrong cast tier | `src/agents/characters.py` (STEP 5.11 new) | No change — code not firing |
| 2 | Relationship labels all "husband" | `src/pipeline/character_profiling/post_corrections.py` | Partial fix — main cast improved |
| 3 | False narrator | `src/pipeline/character_extraction_v2/narrator.py`, `src/agents/characters.py` | **FIXED** ✓ |
| 3 | "colleague" spam | `src/analyzer.py` (profiler prompt) | No change — LLM ignores forbidden list |
| 3 | Gatsby promotion diagnostic | `src/agents/characters.py` (STEP 5.11 logging) | No change — promotion still doesn't fire |
| 4 | Gatsby promotion safety net | `src/analyzer.py` (before Step 4.6) | **Partially effective** — Gatsby promoted but narrator regressed |
| 4 | "colleague" post-processing filter | `src/analyzer.py` (two locations) | **FAILED** — 198 "colleague" entries remain |
| 5 | Narrator mention guard | `src/pipeline/character_extraction_v2/narrator.py` | **FIXED** ✓ |
| 5 | Narrator fallback minimum | `src/agents/characters.py` (STEP 6.6) | **FIXED** ✓ |
| 5 | Colleague substring filter | `src/analyzer.py` (two locations) | **FAILED** — 192 "colleague" remain |
| 6 | Disable cooccurrence colleague injection | `src/pipeline/character_profiling/post_corrections.py` | Expected: eliminate 192 "colleague" entries |
| 6 | Block " and " pair-reference aliases | `src/pipeline/character_extraction_v2/main_cast.py` | Expected: remove "Tom and Daisy" alias for Tom |

**Pattern detected:** "colleague" filtering has FAILED 3 times across 3 attempts (prompt: attempt 3, startswith: attempt 4, substring: attempt 5). The filter code is either not in the execution path, or relationships are set AFTER the filter runs. The fix phase MUST trace the actual execution to find where relationships are finalized and place the filter there.

## Configuration Audit
- Model: `qwen3-next:80b-a3b-instruct-q8_0` for all agents (think_mode: false)
- Context length: 32768 — adequate for Gatsby's chapter sizes
- Temperature: 0.7 — reasonable
- Zero LLM retries — no prompt/schema failures
- No chunking issues apparent

## Priority Fix Order for Attempt 6

**The two blocking categories are Character Extraction (5.5/10) and Profiles (4/10).**

1. **TRACE and fix the "colleague" filter** (Critical #1) — Read the ACTUAL code paths in analyzer.py to find where relationships are assigned. Verify Fix K's code exists and is reachable. Then add a FINAL cleanup as the very last step before returning the AnalysisResult. This single fix could raise Profiles from 4→6+.

2. **Add speech pattern extraction** (Critical #2) — Modify the profiler prompt and parser to capture speech patterns. This alone could add 1-2 points to Profiles.

3. **Fix Wolfsheim triplication** (High #3) — Add fuzzy name matching in F6 reconciliation and cross-pipeline merge.

4. **Fix green light / Eckleburg false merge** (High #4) — Block symbolic entity merges when entities have different thematic meanings.

5. **Filter F6 generic descriptors** (High #6) — Add occupation/role blocklist to F6 reconciliation.

6. **Fix Gatsby missing physical description** (High #5) — Debug why profiler fails for the protagonist.

Items 1-2 are essential to cross 8.0 on Profiles. Items 3-5 are needed to cross 8.0 on Character Extraction.

## Pipeline Notes (Attempt 6)
- Analysis completed in 91m 31s
- 42 characters extracted (up from 33 in attempt 5)
- Fix M confirmed: "Tom and Daisy" blocked as pair alias ✓
- Fix L: colleague injection disabled — result unknown until evaluation
- Warning: `Failed to structure profile for Jordan Baker: name '_VAGUE_REL_LABELS' is not defined` — Jordan profile may be incomplete
- Gatsby→Henry C. Gatz contradictory parent labels detected and removed
- Output: output/gatsby/analysis.json, output/gatsby/report.html

## Next Action
Evaluate output (PROMPT_evaluate.md).
