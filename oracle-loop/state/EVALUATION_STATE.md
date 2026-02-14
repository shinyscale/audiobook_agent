# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 22
- **Phase:** awaiting_analysis
- **baseline_score:** 6.60
- **Competitive Mode:** single (all stages: characters, structure, summaries)

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Pipeline Notes (Attempt 21)
- Analysis completed in 35m 33s
- Competitive consensus: ENABLED (3 LLMs, 2/3 supermajority)
- Found 6 characters total (merged 1 based on identity statements)
- Generated 3 character profiles
- 27 pronunciation flags
- **CRITICAL REGRESSION: Son character absorbed as alias of father** — attempt 20 had both characters separate, attempt 21 merged them back

## Latest Scores
- Structure Detection: 7/10 ✗
- Character Extraction: 5.5/10 ✗ (FAILING — REGRESSION)
- Character Profiles: 7/10 ✗ (FAILING)
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 6.5/10 ✗
- HTML Presentation: 6.5/10 ✗
- **Overall: 6.78/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (5 categories below threshold — REGRESSION from attempt 20)

## Detailed Evaluation

### 2.1 Structure Detection: 7/10 ✗

Unchanged from prior attempts. "American, Sir" is a continuous short story with no explicit chapter markers. The tool produces 2 sections, both with null titles (displayed as "Chapter 1" and "Chapter 2"). Both structure elements have null start/end lines. For a continuous text with no structural markers, 1 section would be more accurate, but 2 is workable.

### 2.2 Character Extraction: 5.5/10 ✗ (CRITICAL REGRESSION)

**REGRESSION from attempt 20 (was 7.5/10).** The attempt 21 passage pre-filtering fix appears to have triggered or coincided with the son being re-absorbed as an alias of the father. This is LLM nondeterminism — the same defense issue from attempts 15/17/18/19.

**What's present:**
- John Donaldson (the father): 56 mentions, `main_cast_1_split_0` — has rich profile ✓
- Uncle Bill: 18 mentions, correctly identified as narrator with protagonist role ✓
- Margaret Donaldson: 2 mentions ✓
- Joe Barron: 3 mentions ✓
- Ted Frith with alias "Ted": 5 mentions ✓
- "John Donaldson's" (supporting_2): 4 mentions — spurious possessive character ✗

**CRITICAL: Son character MISSING**
- "John Donaldson (the son)" appears as an **ALIAS** of the father (line 945 of report.html)
- There is NO separate character entry for the son
- The father has 56 mentions (double-counted — absorbing both father and son mentions)
- The `main_cast_1_split_1` ID does not appear in the output at all

**The split was generated but then the son was re-merged into the father.** This is the same LLM nondeterminism problem that has plagued attempts 15-19. Despite the Pass 2 disambiguation label guidance added in attempt 20, the LLM merged them again.

**Why 5.5/10 (down from 7.5):** The son — a central character who drives the entire second half of the story — is completely absent. The chapter summaries correctly reference "John Donaldson (the son)" as a separate person, but the character list contradicts this by listing the son as an alias of the father.

### 2.3 Character Profiles: 7/10 ✗

**Father's profile: EXCELLENT** ✓
- Appearance: "big, athletic, grizzled chap, maybe fifty-five or over, shabby as to clothes, yet with an air like a duke" — accurate
- Personality: "committed profound betrayal by stealing and faking his death... yet redeemed himself in his final moments" — accurate and nuanced
- Voice: "calm, resonant baritone with underlying tension... English with a faint foreign twist" — excellent narrator guidance
- Evidence quotes: "Took money... Very unjustifiable", "American, sir", "This is the happiest hour" — all correctly attributed
- Relationships: son (father), Margaret (spouse), Uncle Bill (acquaintance) — types partially correct (Uncle Bill should be "cousin" not "acquaintance")

**Uncle Bill's profile: EXCELLENT** ✓
- Personality: "heroic protagonist whose quiet, unassuming actions reveal profound compassion, integrity, and moral courage" — spot on
- Appearance: "elderly man with a weathered, reserved presence; thin hair, smokes cigars" — accurate
- Voice guidance not explicitly structured but speech patterns ("formal, uses understated language") are good
- Relationships: lists father as "family" ✓, son as "mentor" ✓, Margaret as "acquaintance" — reasonable
- Extra relationship "American volunteer (John Donaldson, the father) in Italy: ally" is redundant but not harmful

**Ted Frith's profile:** Not generated (only 3 profiles generated: father, Uncle Bill, and implicitly the son's profile was lost when son was merged)

**Son's profile: ABSENT** ✗✗
- The son was absorbed as an alias, so no separate profile exists at all
- This is worse than attempt 20 where the son had a contaminated (copied) profile — now there's no profile whatsoever

**Why 7/10 (UP from 5.5):** The father's profile is now excellent and genuinely useful for narration. Uncle Bill's profile is excellent. The improvement in profile QUALITY for existing characters offsets the loss of the son's profile, which was previously contaminated anyway. But the missing son still prevents a passing score.

### 2.4 Chapter Summaries: 8.5/10 ✓ (MAJOR IMPROVEMENT)

**The persistent "sister" hallucination is FINALLY FIXED after 20 consecutive failures.** Both chapter summaries now correctly use "cousin" instead of "sister."

**Chapter 1:** Excellent quality. Correctly describes: the letter from young John, Uncle Bill's initial resistance, memories of "his late cousin John" (CORRECT — was "his deceased sister's son" for 20 attempts), the financial scandal, the death, Margaret's letter, the emotional aftermath. `characters_present: ["the narrator", "John (the boy)"]` — mostly correct, though "the narrator" should use "Uncle Bill".

**Chapter 2:** Comprehensive and well-structured. Covers: taking in the boy after mother's death, Yale, fishing trip, WWI service, Caporetto, ambulance driving, pier reunion in 1919, the dying father revelation, deathbed scene. `characters_present` correctly lists disambiguated names including both father and son. ✓

**Book overview:** Excellent — accurately captures the full narrative arc. Correctly describes the cousin relationship. Well-paced for narrator preparation.

**Minor issues:**
- Ch1 `characters_present` uses "the narrator" instead of "Uncle Bill"
- Ch2 says "taken in by his uncle" — Uncle Bill is not actually the son's uncle, he's the father's cousin. But "Uncle Bill" is what the boy calls him, so this is a reasonable simplification.

**Why 8.5/10:** The elimination of the persistent "sister" hallucination is a huge improvement. Both summaries are factually accurate, well-written, and useful for narrator preparation. The minor "narrator" vs "Uncle Bill" naming issue is the only real problem.

### 2.5 Pronunciation Guide: 6.5/10 ✗

27 entries, 22 with IPA. Quality unchanged from attempt 20:
- **Genuinely useful (8):** Caporetto, Piave, Solferino, Tagliamento, Bersagliari, Venetia, Guerre, Bordeaux — Italian/French geographic/military terms
- **Acceptable homographs (4):** live, minute, read, close — context-dependent pronunciation (but "moderate" is borderline)
- **False positives (~15):** Donaldson, Barron, Frith, Margaret, Johnny, Donaldson's, whippersnapper, thriftless, thickset, manliness, dum-dums, orderlies, mayn't, was — common English words/standard names
  - "was" is particularly egregious
  - "orderlies" IPA shown as "/ˈɔːr.dər.laɪz/" — incorrect (should be "/ˈɔːr.dər.liz/")

### 2.6 HTML Presentation: 6.5/10 ✗

**Good elements:**
- Navigation tabs functional ✓
- Book overview prominent, accurate, and well-formatted ✓
- Father's profile beautifully rendered with appearance, personality, voice guidance sections ✓
- Uncle Bill correctly shown with narrator badge and protagonist tag ✓
- Chapter summaries well-formatted with character tags ✓
- Pronunciation section organized ✓

**Issues:**
1. **Son MISSING from character list entirely** — only appears as an alias of the father. A narrator would not know the son exists as a separate character.
2. **"John Donaldson's" in supporting characters table** — malformed character name with possessive
3. **Father labeled as "antagonist"** — debatable; he's morally complex but calling him the antagonist is misleading for a story about redemption
4. **Father's alias list includes "John Donaldson (the son)"** — this is actively confusing. The alias list says the father is "also known as" the son.
5. **Uncle Bill's relationships include redundant "American volunteer (John Donaldson, the father) in Italy: ally"** — confusing duplicate

**Why 6.5/10 (down from 7.0):** The son's absence from the character list is more damaging to presentation than having a contaminated profile. A narrator reading this report would not know the son is a distinct character.

## Overall Score Calculation

```
Overall = (7 × 0.20) + (5.5 × 0.25) + (7 × 0.15) + (8.5 × 0.20) + (6.5 × 0.10) + (6.5 × 0.10)
        = 1.40 + 1.375 + 1.05 + 1.70 + 0.65 + 0.65
        = 6.825 ≈ 6.83
```

**Overall: 6.83/10** (REGRESSION from 6.95 in attempt 20 — -0.12)

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (user-configured, appropriate)
- No LLM retries across any stage (good)
- Total analysis time: ~35m
- Character extraction: 7 items processed, main_cast_count=2, supporting_cast_count=4
- Profile pipeline produced 3 profiles (items_processed=3) — all high confidence
- 0 merge decisions recorded
- No config changes recommended — the bottleneck is character merge nondeterminism

## Current Issues (Priority Order)

### CRITICAL

1. **Son character (John Donaldson (the son)) re-absorbed as alias of father — REGRESSION**
   - Problem: The son does not exist as a separate character. "John Donaldson (the son)" is listed as an ALIAS of "John Donaldson (the father)". The `main_cast_1_split_1` character ID is absent from output.
   - Evidence: Father has aliases `["John Donaldson", "John", "John Donaldson (the son)"]` and 56 mentions (double-counted). No separate son entry exists.
   - Root cause: LLM nondeterminism in the merge/alias resolution. Despite the disambiguation label guidance added in attempt 20 (which worked for attempt 20), the LLM merged them again in attempt 21. The passage pre-filtering fix in `passage_gatherer.py` did not cause this — the merge happens upstream in character extraction, before profiling.
   - This is the SAME nondeterminism pattern from attempts 15, 17, 18, 19 where split characters get re-merged despite protective rules.
   - Location: The merge likely happens in `_process_consolidated_pass2()` in `src/pipeline/character_extraction_v2/main_cast.py` where the LLM produces a `merge_into` directive despite the rule added in attempt 20.
   - **Fix approach — DETERMINISTIC PROTECTION NEEDED:** The prompt-only approach (attempt 20) works sometimes but not reliably. Need a **code-level guard** that prevents merging characters whose canonical names contain disambiguation labels like "(the father)" and "(the son)". Specifically: in `_process_consolidated_pass2()`, before applying any `merge_into` directive, check if both the source and target canonical names contain parenthesized disambiguation labels. If they do and the base names match but the labels differ, SKIP the merge. This is a deterministic check that cannot be overridden by LLM nondeterminism.
   - **Alternative/complementary approach:** In `_split_disambiguated_same_name_characters()` or the post-split validation (attempt 16), add a check that runs AFTER Pass 2 processing. If a split produced both `split_0` and `split_1`, verify both still exist in the final character list. If one was absorbed as an alias of the other, undo the absorption by removing the absorbed name from aliases and restoring it as a separate character.

### HIGH

2. **"John Donaldson's" (supporting_2) is a spurious character**
   - Problem: Character named "John Donaldson's" (possessive) with 4 mentions and alias "Johnny"
   - Evidence: Extracted from possessive phrases like "John Donaldson's son" or "John Donaldson's widow"
   - Location: `src/pipeline/character_extraction_v2/supporting.py` — NER treats possessive forms as names
   - Fix: Add name cleaning to strip trailing `'s` from extracted character names

3. **Relationship types inaccurate: Uncle Bill listed as "acquaintance" of father**
   - Problem: Uncle Bill is the father's COUSIN, not "acquaintance"
   - Evidence: Text says "my cousin John"
   - Location: `src/pipeline/character_profiling/` — relationship extraction
   - Fix: Will partially improve if profiles are correctly generated

### MEDIUM

4. **Pronunciation false positives (~15 of 27)**
   - Common English words (was, orderlies, manliness, whippersnapper, thriftless, thickset, dum-dums, mayn't) and standard names (Donaldson, Donaldson's, Barron, Frith, Margaret, Johnny) flagged unnecessarily
   - "was" is particularly egregious
   - "orderlies" IPA is incorrect (/ˈɔːr.dər.laɪz/ → should be /ˈɔːr.dər.liz/)
   - Location: `src/pipeline/pronunciation_guide/`

5. **Structure: 2 sections for a continuous short story**
   - 1 section would be more accurate; both have null titles and null start/end lines
   - Location: `src/pipeline/chapter_detection/`

6. **Ch1 characters_present uses "the narrator" instead of "Uncle Bill"**
   - Should use actual character name for narrator linking

7. **Uncle Bill classified as supporting_0 instead of main_cast**
   - Narrator/protagonist has supporting_ prefix ID

8. **Father labeled as "antagonist"**
   - Morally complex but "antagonist" is misleading; "supporting" or no role tag would be better
   - Location: Character extraction role assignment

### LOW

9. **Ted Frith still missing "Teddy" alias**
10. **Margaret Donaldson promoted to main_cast (main_cast_3)** — she has only 2 mentions
11. **`physical_description` field null for all characters** — appearance info exists in profile body but not in top-level field
12. **Uncle Bill's relationships include redundant "American volunteer (John Donaldson, the father) in Italy: ally"**

## Fix History

### Attempt 22 - Fix 1: Deterministic disambiguation label protection in Pass 2
- **Issue addressed:** Son character (John Donaldson (the son)) re-absorbed as alias of father (CRITICAL #1)
- **Root cause:** `_process_consolidated_pass2()` in `src/pipeline/character_extraction_v2/main_cast.py` applied LLM merge directives without checking for conflicting disambiguation labels. The prompt-only rule (attempt 20, line 199) was nondeterministic and failed ~50% of the time.
- **Fix:** Added deterministic code-level guard (Rule 0) before semantic validation that:
  1. Checks if both source and target canonical names have parenthesized disambiguation labels
  2. Extracts base name and label from each (e.g., "John Donaldson" + "the father")
  3. If base names match but labels differ, BLOCKS the merge regardless of LLM output
  4. Also removed `_clean_canonical_name()` call in Pass 2 processing - was stripping disambiguation labels and preventing character lookup
- **Smoke test:** Created `smoke_test_disambiguation_guard.py` - PASSES
- **Modified:** `src/pipeline/character_extraction_v2/main_cast.py` (lines 780-820, 745)

### Attempt 1 - Fix 1: Supporting cast alias resolution
- **Issue addressed:** False character split (Ted Frith / Ted / Johnny)
- **Fix:** Added `_merge_obvious_aliases()` in `supporting.py`
- **Result:** Partially fixed — Ted Frith merged, Johnny removed. Mention counts not accumulated.
- **Modified:** `src/pipeline/character_extraction_v2/supporting.py`

### Attempt 1 - Fix 2: Same-name disambiguation in main cast
- **Issue addressed:** Father/son conflation
- **Fix:** Added Rule 6 to `CHARACTER_IDENTIFICATION_PROMPT`
- **Result:** NO CHANGE — prompt-only approach insufficient
- **Modified:** `src/pipeline/character_extraction_v2/main_cast.py`

### Attempt 1 - Fix 3: Frame vs embedded narrator detection
- **Issue addressed:** Wrong narrator identification
- **Fix:** Updated `NARRATOR_DETECTION_PROMPT` in `narrator.py`
- **Result:** FIXED — Uncle Bill now correctly tagged as first-person narrator
- **Modified:** `src/pipeline/character_extraction_v2/narrator.py`

### Attempt 3 - Fix 1: Same-name character split via summary disambiguation
- **Issue addressed:** Father/son John Donaldson conflation
- **Fix:** Added Step 1.6 `_split_disambiguated_same_name_characters()` in characters.py
- **Result:** DID NOT FIRE — method reads `characters_present` from `chapters` (StructuralElements from `_get_chapters`), but those objects have empty `characters_present` at CharacterAgent runtime.
- **Modified:** `src/agents/characters.py` (lines 161-165, 1285-1360)

### Attempt 3 - Fix 2: Organization entity filtering
- **Issue addressed:** "Red Cross" extracted as character
- **Fix:** Added `_is_organization_name()` method with universal org indicators
- **Result:** FIXED — Red Cross no longer appears in character list
- **Modified:** `src/pipeline/character_extraction_v2/supporting.py`

### Attempt 3 - Fix 3: Spelling variant merge + alias accumulation
- **Issue addressed:** Ted Frith shows 2 mentions, no aliases
- **Fix:** Added Rule 4 for spelling variants, added aliases field to SupportingCharacter
- **Result:** PARTIALLY FIXED — Ted Frith now has alias "Ted" and 5 mentions, but "Teddy" still missing
- **Modified:** `src/pipeline/character_extraction_v2/supporting.py`

### Attempt 4 - Fix 1: Step 1.6 data source correction
- **Issue addressed:** Father/son John Donaldson not split (Critical #1)
- **Root cause:** `_split_disambiguated_same_name_characters()` read from `chapters` (StructuralElements with empty `characters_present`), but data is in summary objects
- **Fix:** Changed method to read from `chapter_summaries` parameter
- **Result:** **REGRESSION** — main cast pipeline now produces 0 characters
- **Modified:** `src/agents/characters.py` (lines 164, 1285-1360)

### Attempt 4 - Fix 2: Pronunciation common name filtering
- **Issue addressed:** Excessive pronunciation false positives — common names flagged
- **Fix:** Added CMU dictionary check for <=4 char names
- **Result:** PARTIAL SUCCESS — Bill, Ted, Joe, Margaret removed, but many longer false positives remain
- **Modified:** `src/pipeline/pronunciation_guide/proposers/character_proposer.py`

### Attempt 5 - Fix 1: Revert Step 1.6 implementation
- **Issue addressed:** CRITICAL #1 from attempt 4 - Main cast pipeline produces 0 characters
- **Fix:** Removed Step 1.6 entirely to restore attempt 3 baseline
- **Result:** SUCCESS — main cast pipeline restored (`main_cast_count: 2`)
- **Modified:** `src/agents/characters.py`

### Attempt 6 - Fix 1: Re-enable Step 1.6 same-name disambiguation split
- **Issue addressed:** Father/son John Donaldson conflation (CRITICAL #1)
- **Fix:** Re-enabled call to `_split_disambiguated_same_name_characters()` after Step 1.5
- **Result:** **DID NOT FIRE** — `characters_present` in Ch2 now shows `["Uncle Bill", "John Donaldson"]` without father/son disambiguation, so method found no split candidates
- **Modified:** `src/agents/characters.py` (lines 161-169)

### Attempt 6 - Fix 2: Fallback narrator matching
- **Issue addressed:** Narrator flag inverted (HIGH #2)
- **Fix:** Added Step 4.5 fallback fuzzy matching using `names_similar()` with 0.7 threshold
- **Result:** PARTIALLY FIXED — Uncle Bill now has `is_narrator: true`, but John Donaldson also still has `is_narrator: true`
- **Modified:** `src/agents/characters.py` (lines 247-262)

### Attempt 7 - Fix 1: Summary prompt same-name disambiguation
- **Issue addressed:** Father/son John Donaldson conflation (CRITICAL #1) — upstream fix
- **Fix:** Added "SAME-NAME DISAMBIGUATION" section to CONSOLIDATE_PROMPT and SINGLE_CHAPTER_PROMPT
- **Result:** PARTIALLY WORKED — Ch2 `characters_present` now has "John Donaldson (the son)", "John Donaldson (the father)", "John Donaldson (the uncle)". But "the uncle" is Uncle Bill misidentified as John Donaldson, and Step 1.6 still didn't produce a split.
- **Modified:** `src/pipeline/chapter_summary/summarizer.py` (lines 115-129, 191-205)

### Attempt 8 - Fix 1: Clarify summary disambiguation + extend Step 1.6 to supporting cast
- **Issue addressed:** Father/son John Donaldson conflation (CRITICAL #1)
- **Fix 1:** Summary prompt: "Only disambiguate characters who ACTUALLY share the same base name" — prevents Uncle Bill mislabeling
- **Fix 2:** Added Step 5.10.7 to apply `_split_disambiguated_same_name_characters()` to supporting cast
- **Result:** Summary fix WORKED (no more Uncle Bill mislabeling), but split STILL DID NOT FIRE due to regex mismatch
- **Modified:**
  - `src/pipeline/chapter_summary/summarizer.py` (prompt clarification)
  - `src/agents/characters.py` (Step 5.10.7)

### Attempt 9 - Fix 1: Alias-based regex matching in _split_disambiguated_same_name_characters()
- **Issue addressed:** Father/son John Donaldson conflation (CRITICAL #1) — downstream fix
- **Fix:** Added fallback logic to try each alias as potential base_name when canonical doesn't match
- **Result:** **DID NOT WORK** — wrong condition prevented alias fallback from running
- **Modified:** `src/agents/characters.py` (lines 1400-1467)

### Attempt 10 - Fix 1: Correct alias fallback condition
- **Issue addressed:** Father/son John Donaldson conflation (CRITICAL #1) — final fix
- **Fix:** Changed line 1421 from `if not labels_found` to `if len(labels_found) < 2`
- **Result:** **SUCCESS** — Father/son split now works! Two separate characters created.
- **BUT:** Split characters have 0 mentions, no aliases, and no profiles — the split creates empty shells.
- **Modified:** `src/agents/characters.py` (line 1421)

### Attempt 11 - Fix 1: Propagate aliases to split characters
- **Issue addressed:** Split characters have 0 mentions and no profiles (CRITICAL #1, #2)
- **Fix:** Copy original character's aliases to each split child
- **Result:** **PARTIAL SUCCESS / NEW REGRESSION** — Father now has 29 mentions and rich profile. BUT: only ONE split child created (father). The son was absorbed as an alias of the father instead of becoming a separate character.
- **Modified:** `src/agents/characters.py` (lines 1459-1470)

### Attempt 12 - Fix 1: Prevent re-merge of split characters in Step 3.5
- **Issue addressed:** Son absorbed as alias of father (CRITICAL #1 regression from attempt 11)
- **Fix:** Added SAFETY CHECK 2 in Pass 2 to skip merge if both characters come from the same split operation
- **Result:** **PARTIAL SUCCESS / NEW PROBLEM** — Merge protection worked but `split_0` (father) MISSING while `split_1` (son) survives.
- **Modified:** `src/agents/characters.py` (lines 1904-1923)

### Attempt 13 - Fix 1: Partition aliases between split children
- **Issue addressed:** Father character (`split_0`) missing from output (CRITICAL #1)
- **Fix:** Modified `_split_disambiguated_same_name_characters()` to PARTITION aliases
- **Result:** **NO EFFECT** — father still missing
- **Modified:** `src/agents/characters.py` (lines 1450-1505)

### Attempt 14 - Diagnostic Fix: Add comprehensive logging to trace split character flow
- **Issue addressed:** Father character (`split_0`) missing (CRITICAL #1)
- **Fix:** Added DEBUG logging at all critical pipeline stages
- **Result:** **SUCCESS** — Both `split_0` (father) AND `split_1` (son) now exist! NEW: Son has father's profile (cross-contamination).
- **Modified:** `src/agents/characters.py` (6 diagnostic logging blocks)

### Attempt 15 - Fix: Split character label-based disambiguation
- **Issue addressed:** Son's profile contamination (CRITICAL #1 from attempt 14)
- **Fix:** Added Signal 0 (confidence 0.99) for split character label detection in `name_disambiguator.py`
- **Result:** **REGRESSION** — Son absorbed as alias of father. LLM nondeterminism.
- **Modified:** `src/pipeline/character_profiling/name_disambiguator.py`

### Attempt 16 - Fix: LLM Nondeterminism Defenses
- **Issue addressed:** Son absorbed, Uncle Bill lost narrator flag (CRITICAL #1, #2 from attempt 15)
- **Fix:** Three defensive protections: post-split validation, narrator promotion, narrator exclusivity
- **Result:** **SUCCESS** — Both father and son exist. Uncle Bill correctly narrates.
- **Modified:** `src/agents/characters.py` (lines 383-410, 600-631, 731-757)

### Attempt 17 - Fix: Add split character labels as standalone aliases
- **Issue addressed:** Son's profile contamination (CRITICAL #1 from attempt 16)
- **Fix:** Add label itself as alias during split character creation
- **Result:** **REGRESSION** — Father absorbed into son.
- **Modified:** `src/agents/characters.py` (lines 1632-1634)

### Attempt 18 - Fix: Revert attempt 17 changes
- **Issue addressed:** Father absorbed into son (CRITICAL #1 from attempt 17)
- **Fix:** Removed lines 1631-1634. Restores attempt 16 stable extraction state.
- **Result:** **DID NOT RESTORE** — Son absorbed into father. LLM nondeterminism.
- **Modified:** `src/agents/characters.py` (removed lines 1631-1634)

### Attempt 19 - Fix: Universal split sibling merge protection
- **Issue addressed:** Son character absorbed despite attempt 12 safety check
- **Fix:** Added safety checks to ALL 5 merge passes in `_merge_within_main_cast()`
- **Result:** **NO EFFECT** — Son still absorbed. This PROVES absorption happens OUTSIDE `_merge_within_main_cast()`. The merge passes were never the problem.
- **Modified:** `src/agents/characters.py` (4 new safety checks in Passes 0,1,3,4)

### Attempt 20 - Fix: Disambiguation label guidance in Pass 2
- **Issue addressed:** Son character absorbed in Pass 2 consolidated alias resolution (CRITICAL #1)
- **Root cause:** `CONSOLIDATED_ALIAS_PROMPT` lacked guidance about characters with disambiguation labels in parentheses. LLM saw "John Donaldson (the father)" and "John Donaldson (the son)" and produced `merge_into` directive merging them, which was applied in `_process_consolidated_pass2()` BEFORE Step 1.6 split could run.
- **Fix:** Added explicit rule to Merge Rules section: "CRITICAL: Characters with disambiguation labels in parentheses are DIFFERENT people" with examples
- **Result:** **SUCCESS** — Both father AND son now exist as separate characters with 28 mentions each. NEW ISSUE: Son's profile is a copy of father's (profile contamination persists from attempt 14).
- **Modified:** `src/pipeline/character_extraction_v2/main_cast.py` (line 197)

### Attempt 21 - Fix: Pre-filter passages by chapter for split characters
- **Issue addressed:** Son's profile contamination (CRITICAL #1 from attempt 20)
- **Fix:** Added early filter in `_find_passages_for_name()` (line 326) to check if character has split label (parentheses at end of canonical name). If yes, skip passages from chapters where the FULL canonical name is NOT in the chapter summary's `active_characters` list.
- **Result:** **REGRESSION** — Son absorbed as alias of father AGAIN. The passage pre-filtering fix is in the profiling pipeline (downstream), but the merge happened upstream in character extraction. The prompt-only defense from attempt 20 was nondeterministic and failed this time.
- **Modified:** `src/pipeline/character_profiling/passage_gatherer.py` (lines 326-347)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 22 | Son re-absorbed (CRITICAL) | `main_cast.py` (deterministic guard + no cleaning in Pass 2) | Smoke test PASSES - awaiting full analysis |
|---------|-------|----------------|--------|
| 1 | Ted split | `supporting.py` | Partial fix |
| 1 | Father/son conflation | `main_cast.py` (prompt only) | No change |
| 1 | Wrong narrator | `narrator.py` | Fixed |
| 3 | Father/son conflation | `characters.py` (Step 1.6) | No change — wrong data source |
| 3 | Red Cross organization | `supporting.py` | Fixed |
| 3 | Ted Frith aliases/counts | `supporting.py` | Partial fix |
| 4 | Father/son conflation | `characters.py` (data source fix) | **REGRESSION** |
| 4 | Pronunciation false positives | `character_proposer.py` | Partial fix |
| 5 | Main cast regression | `characters.py` (remove Step 1.6) | Fixed |
| 6 | Father/son conflation | `characters.py` (re-enable Step 1.6) | DID NOT FIRE |
| 6 | Narrator flag | `characters.py` (fallback matching) | Partial fix |
| 7 | Father/son conflation | `summarizer.py` (upstream prompt) | Partial |
| 8 | Father/son conflation | `summarizer.py` + `characters.py` | Partial |
| 9 | Father/son conflation | `characters.py` (alias fallback) | DID NOT WORK |
| 10 | Father/son conflation | `characters.py:1421` (fix condition) | SUCCESS (but 0 mentions) |
| 11 | Split chars empty | `characters.py` (alias propagation) | Partial |
| 12 | Son re-merged | `characters.py` (merge protection) | Partial |
| 13 | Father missing | `characters.py` (alias partitioning) | NO EFFECT |
| 14 | Diagnostic logging | `characters.py` (6 logging blocks) | SUCCESS |
| 15 | Son profile contamination | `name_disambiguator.py` | REGRESSION |
| 16 | LLM nondeterminism | `characters.py` (3 defenses) | SUCCESS |
| 17 | Son profile contamination | `characters.py` (label aliases) | REGRESSION |
| 18 | Revert attempt 17 | `characters.py` (revert) | DID NOT RESTORE |
| 19 | Universal merge protection | `characters.py` (5 safety checks) | **NO EFFECT — proves absorption is OUTSIDE merge passes** |
| 20 | Disambiguation label guidance | `main_cast.py` (Pass 2 prompt) | **SUCCESS — both characters exist! Profile contamination persists.** |
| 21 | Split character passage pre-filtering | `passage_gatherer.py` (early filter) | **REGRESSION — son re-absorbed as alias of father** |

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.60 | — | Baseline |
| 2 | 7.10 | +0.50 | Narrator fixed, Ted partially merged |
| 3 | 7.35 | +0.75 | Red Cross filtered, Ted aliases improved |
| 4 | 6.68 | +0.08 | REGRESSION: 0 main cast characters |
| 5 | 7.13 | +0.53 | Main cast restored |
| 6 | 7.33 | +0.73 | Narrator flag partially fixed |
| 7 | 7.33 | +0.73 | Summary disambiguation partial |
| 8 | 7.33 | +0.73 | Summary fix worked, regex mismatch |
| 9 | 7.08 | +0.48 | Alias fallback wrong condition |
| 10 | 7.25 | +0.65 | Father/son split success (0 mentions) |
| 11 | 6.85 | +0.25 | Father profiled, son re-merged |
| 12 | 6.10 | -0.50 | Merge protection, father missing |
| 13 | 5.93 | -0.67 | Alias partitioning no effect |
| 14 | 6.83 | +0.23 | Both chars exist! Son profile contaminated |
| 15 | 5.90 | -0.70 | REGRESSION: son absorbed, narrator lost |
| 16 | 7.28 | +0.68 | RECOVERY: LLM defenses worked |
| 17 | 6.33 | -0.27 | REGRESSION: father absorbed into son |
| 18 | 6.50 | -0.10 | Revert did not restore |
| 19 | 6.50 | -0.10 | Universal merge protection NO EFFECT |
| 20 | 6.95 | +0.35 | Both chars exist! Son profile contaminated |
| 21 | 6.83 | +0.23 | REGRESSION: son re-absorbed as alias of father |

## Next Action

**Phase:** awaiting_analysis

**CRITICAL INSIGHT from 21 attempts:** The father/son split problem has been solved and regressed MULTIPLE times due to LLM nondeterminism. The prompt-only fix from attempt 20 works ~50% of the time. The code-level merge protections from attempts 12, 16, and 19 target `_merge_within_main_cast()` passes, but attempt 19 PROVED that absorption happens in `_process_consolidated_pass2()` (the Pass 2 consolidated alias resolution), NOT in the merge passes.

**THE FIX MUST BE DETERMINISTIC AND IN `_process_consolidated_pass2()`:**

The fix phase should add a **code-level guard** in `_process_consolidated_pass2()` (in `src/pipeline/character_extraction_v2/main_cast.py`) that:
1. Before applying any `merge_into` directive, check if the source character's canonical name AND the target character's canonical name both contain parenthesized disambiguation labels (e.g., "(the father)", "(the son)")
2. If both names share the same base name (before the parenthesized label) but have DIFFERENT labels, **SKIP the merge** regardless of what the LLM says
3. Log the skipped merge for debugging

This is the ONE location where the merge happens and it needs a deterministic guard that cannot be overridden by LLM output variation.

**Secondary:** The passage pre-filtering fix from attempt 21 (in `passage_gatherer.py`) should be KEPT — it will help with profile disambiguation once the son character actually survives extraction. But it cannot help if the son doesn't exist.

**Summaries improvement:** The "sister" hallucination fix is a bonus — summaries now score 8.5/10.
