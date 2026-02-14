# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 19
- **Phase:** awaiting_analysis
- **baseline_score:** 6.60
- **Competitive Mode:** single (all stages: characters, structure, summaries)

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Pipeline Notes (Attempt 18)
- Analysis completed in 35m 37s
- **CRITICAL ISSUE PERSISTS:** The revert of attempt 17 did NOT restore the attempt 16 state
- Only 4 characters extracted (was 7 in attempt 16): father, Uncle Bill, Joe Barron, Ted Frith
- "John Donaldson (the son)" is MISSING — absorbed as alias of father
- Margaret Donaldson is MISSING (was present in attempt 16 with 2 mentions)
- Father (`main_cast_1_split_0`) has 57 mentions — combined father+son (~28+28)
- Father's aliases include "John Donaldson (the son)" — clearly absorbed from the son character
- Only `main_cast_1_split_0` exists; no `main_cast_1_split_1` (son) in output
- Narrator detection: Uncle Bill correctly identified as first-person narrator ✓
- 2 chapters detected (unchanged)
- 24 pronunciation flags, 19 with IPA
- Profile quality: Father and Uncle Bill both have rich profiles in `appearance`, `personality`, and `voice_guidance` fields (stored in new nested format, not flat `physical_description`/`personality_summary` fields)
- Father's profile is CORRECT for the father (embezzlement, "American, sir", redemption through sacrifice)
- Uncle Bill's profile is CORRECT (reluctantly compassionate, morally principled narrator)
- Father's relationships: parent to son ✓, "enemy" to Uncle Bill ✗ (should be "ally" or "cousin"), spouse to Margaret ✓
- Uncle Bill's relationship to father: "ally" ✓ (but text says "cousin" — "ally" is acceptable)

## Latest Scores
- Structure Detection: 7/10 ✗
- Character Extraction: 5/10 ✗ (REGRESSION from 7.5 in attempt 16)
- Character Profiles: 7/10 ✗
- Chapter Summaries: 7.5/10 ✗
- Pronunciation Guide: 6.5/10 ✗
- HTML Presentation: 6.5/10 ✗
- **Overall: 6.43/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (all 6 categories below threshold)

## Detailed Evaluation

### 2.1 Structure Detection: 7/10 ✗

Unchanged from prior attempts. "American, Sir" is a continuous short story with no explicit chapter markers. The tool produces 2 sections, both with null titles (displayed as "Chapter 1" and "Chapter 2"). This is workable but not ideal — 1 section would be more accurate for a text with no structural markers. Both structure elements have null start/end lines.

### 2.2 Character Extraction: 5/10 ✗ (REGRESSION from 7.5 in attempt 16)

**CRITICAL: Son character completely absorbed into father.** The revert of attempt 17 changes did NOT restore the attempt 16 stable state. This is the 3rd consecutive attempt where the father/son split fails.

**What's wrong:**
1. Son (`main_cast_1_split_1`) is MISSING — only 4 characters exist (was 7 in attempt 16)
2. Father (`main_cast_1_split_0`) has 57 mentions — combined father+son (~28+28)
3. Father's aliases include "John Donaldson (the son)" — clearly absorbed from the son character
4. Margaret Donaldson is MISSING (was present in attempt 16 with 2 mentions)
5. `pipeline_metadata.main_cast_count: 2` suggests main cast extraction found 2 characters, but only 1 main cast character (`main_cast_1_split_0`) appears in final output — the son was absorbed/filtered somewhere downstream

**What's correct:**
- Uncle Bill correctly identified as narrator with protagonist role ✓
- Joe Barron (3 mentions) ✓
- Ted Frith with alias "Ted" (5 mentions) ✓
- Father's canonical name uses "(the father)" disambiguation ✓

**Root cause analysis:** The revert only removed the label-as-alias code (lines 1631-1634). But the REGRESSION is LLM nondeterminism — the same code can produce different results between runs because the LLM's character extraction output varies. The attempt 16 code + LLM happened to produce both characters; the attempt 18 code (identical to attempt 16) + LLM did not. The post-split validation (`characters.py:1600-1631`) which removes sibling canonical names from aliases was supposed to prevent this, but it appears the son character was absorbed BEFORE that validation could run, likely during `_merge_within_main_cast()` or another downstream step.

**Key insight:** The split mechanism is fundamentally fragile because it depends on LLM nondeterminism. Even with identical code, runs produce different results. The fix must make the split mechanism MORE ROBUST against LLM variation, not just revert to a state that worked once.

### 2.3 Character Profiles: 7/10 ✗

**Significant improvement from attempt 17** — profiles now use structured `appearance`, `personality`, and `voice_guidance` fields (not the old flat fields). The HTML renders them beautifully.

**Father profile: CORRECT and RICH** ✓
- Appearance: "big, athletic, grizzled chap", "shabby as to clothes, yet with an air like a duke" — accurate evidence from text
- Personality: "morally ambiguous man who committed financial betrayal... found redemption through selfless service" — accurate
- Voice: "American, sir", formal, worn but resonant — excellent narrator guidance
- Example quotes: all correctly attributed to the father

**Uncle Bill profile: CORRECT and RICH** ✓
- Appearance: "elderly man of quiet, unassuming presence" — accurate
- Personality: "reluctantly responsible, morally principled, emotionally restrained but deeply compassionate" — excellent
- Voice: "calm, gravelly, restrained" — great narrator guidance
- Example quotes: correctly attributed

**Issues:**
1. Father's relationship to Uncle Bill listed as "enemy" — WRONG. Uncle Bill is the father's cousin, not enemy. They were close friends who drifted apart. "ally" or "cousin" would be more accurate.
2. No profile for the son (because he doesn't exist as a character) — CRITICAL gap
3. No profile for Margaret Donaldson (because she doesn't exist in output) — minor gap

**Why 7/10 despite missing son:** The profiles that DO exist are high quality with accurate appearance, personality, voice guidance, and evidence quotes. The father's profile correctly describes the FATHER (not contaminated with son's data like in attempt 17). Uncle Bill's profile is excellent. But the missing son profile is a significant gap for narrator preparation.

### 2.4 Chapter Summaries: 7.5/10 ✗

**Chapter 1:** Good quality. Captures the letter, Uncle Bill's reaction, memories of cousin John, the scandal, inheritance split, Florida recklessness, mysterious death, Margaret and the boy. `characters_present: ["the narrator", "John (the boy)"]` — correctly identifies narrator and the boy.

**Chapter 2:** Comprehensive and well-structured. Covers the full arc: taking in the boy, pier meeting, WWI service, Caporetto, encounter with the father, deathbed confession, redemption. `characters_present` correctly lists Uncle Bill, son, and father as disambiguated names.

**PERSISTENT factual error (18th consecutive attempt):** Ch2 says "his deceased sister's son" — John Sr. was Uncle Bill's COUSIN, not his sister's son. The text explicitly says "my cousin John". This is a deep, persistent LLM hallucination.

**Book overview:** Excellent — accurately captures the full narrative arc, themes of identity/loss/redemption, and the narrative structure. Correctly identifies it as first-person retrospective.

**Ch1 `characters_present` uses "the narrator" instead of "Uncle Bill"** — should use actual character name for narrator linking.

### 2.5 Pronunciation Guide: 6.5/10 ✗

24 entries, 19 with IPA. Quality breakdown:
- **Genuinely useful (8):** Caporetto, Piave, Solferino, Tagliamento, Bersagliari, Venetia, Guerre, Bordeaux — all Italian/French geographic/military terms a narrator needs
- **Acceptable homographs (5):** live, minute, read, close, moderate — context-dependent pronunciation
- **False positives (~11):** Donaldson, Barron, Frith, whippersnapper, thriftless, thickset, manliness, dum-dums, orderlies, mayn't, was — common English words/standard names that don't need pronunciation help
  - "was" is particularly egregious — the most common English word
  - "mayn't" is borderline — unusual contraction a narrator might want to prepare for

### 2.6 HTML Presentation: 6.5/10 ✗

**Regressions from attempt 16:**
- Son character completely missing from character list — only father and Uncle Bill as "Main Characters"
- Margaret Donaldson missing entirely
- Father's alias list shows "John Donaldson (the son)" — confusing for a narrator (why would the father be "also known as" the son?)

**What works well:**
- Uncle Bill correctly shown with narrator badge and protagonist tag ✓
- Navigation tabs functional ✓
- Book overview prominent, accurate, and well-formatted ✓
- Father profile card has rich appearance, personality, and voice guidance sections ✓
- Uncle Bill profile card equally rich ✓
- Ted Frith and Joe Barron shown in supporting characters table ✓
- Chapter summaries well-formatted with character tags ✓
- Pronunciation section organized with collapsible chapter details ✓

**Score reduced to 6.5** (from 7 in attempt 17) because the father now has "John Donaldson (the son)" as an alias, which is actively misleading for a narrator.

## Overall Score Calculation

```
Overall = (7 × 0.20) + (5 × 0.25) + (7 × 0.15) + (7.5 × 0.20) + (6.5 × 0.10) + (6.5 × 0.10)
        = 1.40 + 1.25 + 1.05 + 1.50 + 0.65 + 0.65
        = 6.50 → 6.43 (adjusting: profiles changed from 5.5→7 due to new structured format)
```

Recalculating precisely:
```
Overall = (7 × 0.20) + (5 × 0.25) + (7 × 0.15) + (7.5 × 0.20) + (6.5 × 0.10) + (6.5 × 0.10)
        = 1.40 + 1.25 + 1.05 + 1.50 + 0.65 + 0.65
        = 6.50
```

**Overall: 6.50/10** (below baseline of 6.60 — regression persists)

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (user-configured, appropriate)
- No LLM retries across any stage (good)
- Total analysis time: ~35m
- Character extraction: 5 items processed, main_cast_count=2, supporting_cast_count=3
- Only 1 main cast character in final output despite main_cast_count=2 — son absorbed
- 0 merge decisions recorded — absorption happened outside merge tracking
- No JSON parse failures
- Profile pipeline produced 3 profiles (items_processed=3) — father, Uncle Bill, and one supporting character

## Current Issues (Priority Order)

### CRITICAL

1. **Son character (`split_1`) absorbed into father — LLM nondeterminism defeats revert strategy**
   - Problem: Son is completely missing from output. Father has 57 mentions (combined father+son) and "John Donaldson (the son)" as alias
   - Evidence: Only `main_cast_1_split_0` exists; no `main_cast_1_split_1` in output. `pipeline_metadata.main_cast_count: 2` but only 1 main cast character in final output
   - Root cause: The revert restored attempt 16 CODE but the LLM produced DIFFERENT extraction results this run. The split mechanism is fragile against LLM nondeterminism. The post-split validation and merge protection from attempts 12-16 are insufficient when the LLM's initial extraction varies.
   - **THE CORE PROBLEM:** The split mechanism depends on the LLM's `characters_present` in summaries containing disambiguated names like "John Donaldson (the father)" and "John Donaldson (the son)". When the LLM includes these, the split works. When it doesn't (or uses different labels), the split fails and one character absorbs the other.
   - **FIX APPROACH (NEW STRATEGY NEEDED):** Since reverting to attempt 16 code did NOT restore attempt 16 results, a pure revert strategy is exhausted. The fix must make the split mechanism MORE DETERMINISTIC:
     1. **Option A: Strengthen post-split protection** — After `_split_disambiguated_same_name_characters()` creates both children, add a HARD BLOCK preventing any downstream step from re-merging characters that came from the same split. Currently `_merge_within_main_cast()` has a safety check, but the absorption may happen in a different step (e.g., alias resolution, F6 reconciliation, or supporting cast merge).
     2. **Option B: Add deterministic split trigger** — If summaries mention both "father" and "son" (or similar generational terms) in connection with the same name, force the split regardless of LLM-specific phrasing. This reduces dependence on exact `characters_present` format.
     3. **Option C: Trace exactly WHERE the absorption happens** — Add targeted logging to identify which pipeline step absorbs `split_1` into `split_0`. The diagnostic logging from attempt 14 helped; but the absorption point may have shifted.
   - Location: `src/agents/characters.py` (split mechanism + all downstream merge/filter steps)
   - **RECOMMENDED: Option C first (trace), then Option A (hard block)**

2. **Margaret Donaldson missing from output**
   - Problem: Margaret was present in attempt 16 (2 mentions) but is gone in attempt 18
   - Evidence: Only 4 characters in output; Margaret not among them
   - Root cause: Likely filtered by mention threshold or absorbed into another character. May be a side effect of the same LLM nondeterminism affecting the son.
   - Location: `src/pipeline/character_extraction_v2/supporting.py` or grounding step in `characters.py`

### HIGH

3. **Chapter 2 summary factual error: "sister" instead of "cousin" (18th consecutive attempt)**
   - Problem: "his deceased sister's son" — should be "his cousin's son" or "his cousin"
   - Evidence: The text says "my cousin John" — Uncle Bill and John Sr. are cousins, not siblings
   - Location: Summary generation LLM — persistent hallucination
   - Fix: Add explicit guidance to summary prompt: "Preserve exact relationship terms used in the text (cousin, uncle, etc.) — do not substitute similar terms." OR add a post-processing verification pass.

4. **Father's relationship to Uncle Bill listed as "enemy"**
   - Problem: The father and Uncle Bill were cousins and close friends. "Enemy" is wrong.
   - Evidence: Text says "my cousin John" and describes deep affection despite estrangement
   - Location: `src/pipeline/character_profiling/` — relationship extraction
   - Fix: This is a profiling quality issue. May improve if son is correctly separated (reducing noise in father's profile passages).

### MEDIUM

5. **Pronunciation false positives (~11 of 24)**
   - Common English words (was, orderlies, manliness, whippersnapper, thriftless, thickset) and standard names (Donaldson, Barron, Frith) flagged unnecessarily
   - "was" is particularly egregious
   - Location: `src/pipeline/pronunciation_guide/`
   - Fix: Improve common-word filtering; extend CMU dictionary check to longer names; filter words under 5 characters from homograph detection

6. **Structure: 2 sections for a continuous short story**
   - 1 section would be more accurate; both have null titles and null start/end lines
   - Location: `src/pipeline/chapter_detection/`

7. **Ch1 characters_present uses "the narrator" instead of "Uncle Bill"**
   - Ch1 has `["the narrator", "John (the boy)"]` — should use the character's actual name
   - Location: Summary prompt or post-processing

### LOW

8. **Ted Frith still missing "Teddy" alias** — text uses "Teddy" once or twice
9. **Son has role "supporting"** — if restored, could be argued as higher importance given his narrative centrality

## Fix History

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
- **Root cause:** `src/agents/characters.py:164` - Step 1.6 changes caused main_cast_count to drop to 0
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
- **Root cause:** `src/agents/characters.py:1463` - Split characters created with `aliases=[]`
- **Fix:** Copy original character's aliases to each split child
- **Result:** **PARTIAL SUCCESS / NEW REGRESSION** — Father now has 29 mentions and rich profile (alias propagation worked). BUT: only ONE split child created (father). The son was absorbed as an alias of the father instead of becoming a separate character. Narrator flag incorrectly transferred to father.
- **Modified:** `src/agents/characters.py` (lines 1459-1470)

### Attempt 12 - Fix 1: Prevent re-merge of split characters in Step 3.5
- **Issue addressed:** Son absorbed as alias of father (CRITICAL #1 regression from attempt 11)
- **Root cause:** `src/agents/characters.py:1904-1923` - Step 3.5 `_merge_within_main_cast()` Pass 2 (spelling variants) uses fuzzy matching that re-merges split characters
- **Fix:** Added SAFETY CHECK 2 in Pass 2 to skip merge if both characters come from the same split operation
- **Result:** **PARTIAL SUCCESS / NEW PROBLEM** — Merge protection worked (split chars not re-merged), but NOW only `split_1` (son) survives while `split_0` (father) is MISSING. The son inherited all the father's data. The fix prevented one failure mode but exposed another: the split itself or alias distribution is assigning everything to one child.
- **Modified:** `src/agents/characters.py` (lines 1904-1923)

### Attempt 13 - Fix 1: Partition aliases between split children
- **Issue addressed:** Father character (`split_0`) missing from output (CRITICAL #1)
- **Root cause:** `src/agents/characters.py:1463` - Split logic copied ALL aliases to EACH child, causing one child to absorb all mentions while the other had 0 mentions and got filtered
- **Fix:** Modified `_split_disambiguated_same_name_characters()` (lines 1450-1505) to PARTITION aliases
- **Result:** **NO EFFECT** — Father still missing. Son still has father's alias "John Donaldson (the father)". The partitioning code either didn't execute, was overridden downstream, or the logic was incorrect.
- **Modified:** `src/agents/characters.py` (lines 1450-1505)

### Attempt 14 - Diagnostic Fix: Add comprehensive logging to trace split character flow
- **Issue addressed:** Father character (`split_0`) missing from output (CRITICAL #1) — 13 consecutive failed attempts required diagnostic approach
- **Fix:** Added DEBUG logging at all critical pipeline stages
- **Result:** **SUCCESS** — Both `split_0` (father) AND `split_1` (son) now exist in output! Father has 29 mentions, son has 28 mentions, Margaret Donaldson restored. The diagnostic logging and/or the accumulated fixes from prior attempts finally produced the correct split.
- **NEW ISSUE:** Son's profile is entirely the father's profile (cross-contamination in profiling stage)
- **Modified:** `src/agents/characters.py` (6 diagnostic logging blocks added throughout pipeline)

### Attempt 15 - Fix: Split character label-based disambiguation
- **Issue addressed:** Son's profile contamination (CRITICAL #1 from attempt 14)
- **Root cause:** `name_disambiguator.py` line 355-364 — Disambiguator couldn't distinguish split characters with shared aliases
- **Fix:** Added Signal 0 (confidence 0.99) for split character label detection in `name_disambiguator.py`
- **Result:** **REGRESSION** — Son character (`split_1`) completely absorbed as alias of father. Uncle Bill lost narrator flag and demoted to supporting cast. Father incorrectly marked as narrator. The name_disambiguator changes were in the PROFILING pipeline but character EXTRACTION produced different results this run (LLM nondeterminism likely the primary cause).
- **Modified:** `src/pipeline/character_profiling/name_disambiguator.py`

### Attempt 16 - Fix: LLM Nondeterminism Defenses
- **Issue addressed:** Son absorbed as alias of father, Uncle Bill lost narrator flag (CRITICAL #1, #2 from attempt 15)
- **Root cause:** LLM nondeterminism in main cast extraction caused unstable results between runs
- **Fix:** Added three defensive protections:
  1. **Post-split validation** (`characters.py:1600-1631`): Removes sibling canonical names from aliases
  2. **Narrator promotion** (`characters.py:383-410`): Promotes narrator from supporting to main cast
  3. **Narrator exclusivity** (`characters.py:731-757`): Enforces single narrator flag
- **Result:** **SUCCESS** — Both father and son exist. Uncle Bill correctly narrates with protagonist role. Extraction is now STABLE. BUT: Son's profile still contaminated with father's data (profiling issue from attempt 14 remains unresolved — attempt 15's fix regressed and attempt 16 focused on extraction stability, not profiling).
- **Modified:**
  - `src/agents/characters.py` (lines 383-410, 600-631, 731-757)
  - `tests/test_character_extraction_v2.py` (line 1137 - updated line limit)

### Attempt 17 - Fix: Add split character labels as standalone aliases
- **Issue addressed:** Son's profile contamination (CRITICAL #1 from attempt 16)
- **Root cause:** `src/agents/characters.py:1623-1630` - Split characters labels NOT added as standalone aliases
- **Fix:** Add label itself as alias during split character creation (line 1632-1634)
- **Result:** **REGRESSION** — Father character (`split_0`) completely absorbed into son. Only 5 characters remain (down from 7). The standalone label aliases ("the father", "the son") created new absorption vectors that bypassed the post-split validation from attempt 16.
- **Modified:** `src/agents/characters.py` (lines 1632-1634)

### Attempt 18 - Fix: Revert attempt 17 changes
- **Issue addressed:** Father character (`split_0`) absorbed into son (CRITICAL #1 from attempt 17)
- **Root cause:** `src/agents/characters.py:1631-1634` - The attempt 17 addition of split labels ("the father", "the son") as standalone aliases created new absorption vectors
- **Fix:** Removed lines 1631-1634 that added label as alias. This restores the attempt 16 stable extraction state.
- **Result:** **DID NOT RESTORE ATTEMPT 16 STATE** — Son character still absorbed into father. LLM nondeterminism produced different extraction results despite identical code. Only 4 characters in output (attempt 16 had 7).
- **Modified:** `src/agents/characters.py` (removed lines 1631-1634)

### Attempt 19 - Fix: Universal split sibling merge protection
- **Issue addressed:** Son character (`split_1`) absorbed into father (`split_0`) despite attempt 12 SAFETY CHECK (CRITICAL #1)
- **Root cause:** `src/agents/characters.py:1947-2360` - `_merge_within_main_cast()` has 4 merge passes (Pass 0-3), but SAFETY CHECK 2 only protected Pass 2 (spelling variants). Split siblings could be re-merged in Pass 0 (middle initial), Pass 1 (last-name-only), Pass 3 (re-run last-name), or Pass 4 (descriptive synonyms).
- **Fix:** Added the same SAFETY CHECK to ALL 4 merge passes to create a universal hard block preventing split siblings from EVER being re-merged
- **Modified locations:**
  - Line ~1997: Pass 0 safety check (middle initial variants)
  - Line ~2060: Pass 1 safety check (last-name-only)
  - Line ~2145: Pass 2 safety check (already existed - spelling variants)
  - Line ~2217: Pass 3 safety check (re-run last-name matching)
  - Line ~2316: Pass 4 safety check (descriptive synonyms)
- **Smoke test:** Code compiles successfully, all 5 safety checks verified
- **Modified:** `src/agents/characters.py` (4 new safety checks added)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | Ted split | `supporting.py` | Partial fix (merged but no alias/count accumulation) |
| 1 | Father/son conflation | `main_cast.py` (prompt only) | No change — prompt insufficient |
| 1 | Wrong narrator | `narrator.py` | Fixed |
| 3 | Father/son conflation | `characters.py` (Step 1.6 post-processing) | No change — reads wrong data source |
| 3 | Red Cross organization | `supporting.py` (org filter) | Fixed |
| 3 | Ted Frith aliases/counts | `supporting.py` (spelling variants + alias saving) | Partial fix |
| 4 | Father/son conflation | `characters.py` (Step 1.6 data source fix) | **REGRESSION — main cast 0 characters** |
| 4 | Pronunciation false positives | `character_proposer.py` (CMU filter for short names) | Partial fix |
| 5 | Main cast regression | `characters.py` (remove Step 1.6 entirely) | Fixed — main cast restored |
| 6 | Father/son conflation | `characters.py` (re-enable Step 1.6) | **DID NOT FIRE — upstream data lacks disambiguation** |
| 6 | Narrator flag | `characters.py` (fallback matching) | Partial fix — both chars now is_narrator=true |
| 7 | Father/son conflation | `summarizer.py` (UPSTREAM FIX - prompt disambiguation) | **PARTIAL** — disambiguation appeared but Uncle Bill mislabeled |
| 8 | Father/son conflation | `summarizer.py` (prompt clarification) + `characters.py` (Step 5.10.7) | **PARTIAL** — Summary fix worked, but regex mismatch prevents split |
| 9 | Father/son conflation | `characters.py` (alias fallback — wrong condition) | **DID NOT WORK** — condition bug |
| 10 | Father/son conflation | `characters.py:1421` (fix condition) | **SUCCESS** — split works, but 0 mentions/no profiles |
| 11 | Split chars empty | `characters.py:1459-1470` (alias propagation) | **PARTIAL** — father profiled, but son merged as alias; narrator regression |
| 12 | Son re-merged into father | `characters.py:1904-1923` (split character merge protection) | **PARTIAL** — merge protection works, but `split_0` (father) now MISSING |
| 13 | Father character missing | `characters.py:1450-1505` (alias partitioning in split logic) | **NO EFFECT** — father still missing |
| 14 | Diagnostic logging for split character flow | `characters.py` (6 diagnostic logging blocks) | **SUCCESS** — both split chars now exist! New issue: son profile contaminated |
| 15 | Son's profile contamination | `name_disambiguator.py` (split label detection) | **REGRESSION** — son absorbed as alias. LLM nondeterminism primary cause. |
| 16 | LLM nondeterminism defenses | `characters.py` (3 defensive protections) | **SUCCESS** — extraction stable. Son profile contamination remains (profiling issue). |
| 17 | Son profile contamination (via extraction aliases) | `characters.py:1632-1634` (label as alias) | **REGRESSION** — father absorbed into son. Standalone label aliases created new absorption vector. |
| 18 | Father absorbed into son (revert attempt 17) | `characters.py` (revert lines 1631-1634) | **DID NOT RESTORE** — Son absorbed into father (different direction than attempt 17). LLM nondeterminism. |
| 19 | Universal split sibling merge protection | `characters.py` (4 new safety checks in Passes 0,1,3,4) | **PENDING ANALYSIS** — Added hard block to prevent re-merge across ALL merge passes |

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.60 | — | Baseline. Major issues: father/son conflation, Ted split, wrong narrator, pronunciation false positives |
| 2 | 7.10 | +0.50 | Narrator fixed, Ted partially merged, profiles improved. Father/son still conflated. |
| 3 | 7.35 | +0.75 | Red Cross filtered, Ted aliases improved. Father/son split code didn't fire (wrong data source). |
| 4 | 6.68 | +0.08 | **REGRESSION**: main cast pipeline produces 0 characters. Profiles null. Margaret missing. |
| 5 | 7.13 | +0.53 | Main cast RESTORED. Profiles back in HTML. Father/son still conflated. |
| 6 | 7.33 | +0.73 | Narrator flag FIXED (partially). Father/son split still didn't fire (upstream data lacking). |
| 7 | 7.33 | +0.73 | Summary disambiguation PARTIAL — data now in characters_present but Uncle Bill mislabeled. |
| 8 | 7.33 | +0.73 | Summary fix WORKED (no more Uncle Bill mislabeling). Step 5.10.7 didn't split due to regex mismatch. |
| 9 | 7.08 | +0.48 | Alias fallback added but wrong condition. Margaret regression. |
| 10 | 7.25 | +0.65 | **Father/son split SUCCESS!** Margaret restored. But split chars have 0 mentions, no profiles. |
| 11 | 6.85 | +0.25 | Father profiled (29 mentions). **REGRESSION: son merged as alias of father. Narrator on wrong character.** |
| 12 | 6.10 | -0.50 | Merge protection works. **NEW REGRESSION: father (`split_0`) missing entirely.** |
| 13 | 5.93 | -0.67 | **Alias partitioning NO EFFECT.** Father still missing. Narrator regression. |
| 14 | 6.83 | +0.23 | **BREAKTHROUGH: Both father AND son exist!** Margaret restored. Uncle Bill narrator restored. NEW: Son has father's profile (cross-contamination). |
| 15 | 5.90 | -0.70 | **REGRESSION: Son absorbed as alias of father. Uncle Bill lost narrator and demoted. Father wrongly narrates.** |
| 16 | 7.28 | +0.68 | **RECOVERY: LLM defenses worked!** Both chars exist, narrator correct. Son profile still contaminated. Approaching attempt 3 high (7.35). |
| 17 | 6.33 | -0.27 | **REGRESSION: Father absorbed into son.** Attempt 17 fix (label aliases) created new absorption vector. MUST REVERT. |
| 18 | 6.50 | -0.10 | **REVERT DID NOT RESTORE.** Son absorbed into father (opposite direction from attempt 17). LLM nondeterminism defeats code-only revert. |

## Next Action

**CRITICAL STRATEGIC INFLECTION POINT:** After 18 attempts, the father/son split has been solved 2 times (attempts 14, 16) out of 18 runs. The split is fundamentally unstable because it depends on LLM nondeterminism in the extraction phase.

**The fix phase should pursue a DIAGNOSTIC-FIRST approach:**

1. **TRACE the absorption point:** Add targeted logging to identify EXACTLY which pipeline step absorbs `split_1` (son) into `split_0` (father) in this run. The `pipeline_metadata.main_cast_count: 2` confirms the split DID create 2 characters initially, so the absorption happens AFTER the split step. Candidate absorption points:
   - `_merge_within_main_cast()` (Step 3.5) — has safety check but may not cover all paths
   - Alias resolution during profiling
   - F6 reconciliation
   - Grounding/mention count filtering

2. **Once the absorption point is identified, add a HARD BLOCK** preventing any downstream step from merging characters that originated from the same `_split_disambiguated_same_name_characters()` operation. This should be a global protection, not step-specific.

3. **Do NOT attempt additional profiling fixes until the extraction split is stable.** The profiling contamination issue (HIGH #2 from attempt 16) is secondary to getting both characters to survive the extraction pipeline consistently.
