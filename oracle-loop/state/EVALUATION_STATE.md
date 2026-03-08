# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 6
- **Phase:** awaiting_analysis
- **baseline_score:** 5.90

## Output Files
- HTML: ../output/gatsby/report.html
- JSON: ../output/gatsby/analysis.json

## Latest Scores
- Structure Detection: 10/10 ✓
- Character Extraction: 6/10 ✗
  - Completeness: 7/10
  - Identity Resolution: 5/10
  - Alias Grouping: 6/10
- Character Profiles: 3.5/10 ✗
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 7.15/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold: Character Extraction, Character Profiles)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 5.90 | - | Baseline. Profiles catastrophic, character identity broken |
| 2 | 6.73 | +0.83 | Relationships partially improved for main cast. Core narrator/Gatsby issues UNFIXED |
| 3 | 7.20 | +1.30 | Narrator FIXED (Nick ✓). Gatsby still supporting. "colleague" spam persists |
| 4 | 6.93 | +1.03 | REGRESSION: Gatsby promoted but narrator BROKE AGAIN. Colleague filter FAILED |
| 5 | 7.08 | +1.18 | Narrator FIXED ✓ (Fix I/J). Colleague filter STILL FAILED (192 remain). No speech patterns. |
| 6 | 7.15 | +1.25 | Colleague injection FIXED (192→30). But 47 wrong spousal labels EXPOSED underneath. Green light/Eckleburg separated ✓ |

## What Improved in Attempt 6
- **Fix L WORKED**: Disabling `add_text_window_cooccurrence_relationships()` eliminated the bulk of "colleague" spam (192→30). The 30 remaining come from the LLM profiler itself.
- **Fix M WORKED**: "Tom and Daisy" no longer appears as alias for Tom Buchanan.
- **Green light / Eckleburg SEPARATED**: Now distinct entries — "The Green Light" (alias: "the Light") and "Doctor T. J. Eckleburg" (alias: "the eyes of Doctor T. J. Eckleburg"). Major improvement.
- **Wolfsheim partial merge**: main_cast_7 "Meyer Wolfsheim" (6 mentions) now has alias "Meyer Wolfshiem" — so the main cast entry knows about the alternate spelling. However, supporting_2 "Meyer Wolfshiem" (32 mentions) still exists as a SEPARATE character with 5x more mentions.

## What Did NOT Improve / NEW Issues Exposed
- **47 wrong spousal labels**: With colleague injection disabled, the UNDERLYING relationship quality is exposed. The LLM profiler and/or post_corrections randomly assign "husband"/"wife" to unrelated character pairs. Examples:
  - Gatsby→Wolfsheim: "husband" (should be "business associate")
  - Gatsby→Sloane: "husband" (nonsensical)
  - Gatsby→Henry C. Gatz: "son" (reversed — should be "father" from Gatsby's POV)
  - Daisy→George Wilson: "wife" (WRONG — she's Tom's wife)
  - Daisy→Catherine: "wife" (nonsensical)
  - Daisy→Wolfshiem: "husband" (nonsensical)
  - Daisy→Mr. McKee: "wife" (nonsensical)
  - Jordan→Tom: "adulterer" (WRONG)
  - Jordan→George Wilson: "wife" (nonsensical)
  - Jordan→Myrtle: "husband" (nonsensical)
  - Nick→Mr. Sloane: "husband" (nonsensical)
  - Total: 47 wrong spousal + 30 colleague + 3 "none" = 80/143 relationships wrong (56%)
- **Speech patterns still 0/42**: Not attempted in this fix cycle.
- **Physical descriptions missing for protagonist**: Nick Carraway and Jay Gatsby both have `physical_description: null`.
- **F6 generic descriptor clutter**: Butler (20), Chauffeur (10), Gardener (5), Reporter (2), postman (1), Lutheran minister (1), war veteran (1), servants (1), chorus girl (1), rowdy little girl (1), man in duster (1) — 11 non-named-character entries.
- **Owl Eyes still duplicated**: "Owl Eyes" (f6, 1 mention) and "The man with owl-eyed glasses" (f6, 1 mention) — same character. Possibly also "The drunken man in the library" (f6, 1 mention).
- **Wolfsheim still duplicated**: main_cast_7 (6 mentions) vs supporting_2 (32 mentions) — the supporting entry has 5x the mentions but is in the lower tier.
- **`_VAGUE_REL_LABELS` NameError**: Warning logged: "Failed to structure profile for Jordan Baker: name '_VAGUE_REL_LABELS' is not defined" — Jordan's profile may be incomplete due to a code bug.
- **Duplicate aliases**: Daisy has "Daisy" twice, George has "Wilson" twice.
- **Invalid aliases persist**: "the poor son-of-a-bitch" (quote, not alias) still on Gatsby.

## Current Issues (Priority Order)

### CRITICAL

1. **47 wrong spousal/romantic relationship labels across all characters** [Profiles]
   - Problem: The LLM profiler assigns random "husband"/"wife"/"romantic interest" labels to unrelated characters. 47 out of 143 relationships are wrong spousal labels; only 44% of relationships are correct.
   - Evidence: Gatsby→Wolfsheim "husband", Daisy→George Wilson "wife", Jordan→Myrtle "husband", Nick→Sloane "husband" — all nonsensical.
   - Root cause: The profiler prompt likely presents all character pairs and asks for a relationship label. The LLM defaults to gendered spousal terms when it doesn't know the real relationship. The `enforce_gender_consistency` post-correction then "fixes" gender but can't fix wrong relationship TYPE.
   - Location: `src/analyzer.py` (`_generate_character_profile()`) — profiler prompt. Also `src/pipeline/character_profiling/post_corrections.py` — `enforce_gender_consistency` may be CAUSING some of these by flipping labels to "husband"/"wife".
   - Fix approach: (A) In the profiler prompt, instruct the LLM to OMIT relationships where it has no evidence — do NOT require an entry for every pair. (B) Add a post-processing step that removes any "husband"/"wife" relationship where both characters are not in the known married couples (from text evidence). (C) Check if `enforce_gender_consistency` is converting reasonable labels like "acquaintance" into "husband"/"wife" — if so, fix the conversion logic.

2. **Speech patterns null for ALL 42 characters** [Profiles]
   - Problem: 0/42 have speech_pattern. Critical for narrator prep.
   - Missing: Gatsby's "old sport", Wolfsheim's "Oggsford"/"gonnegtion", Tom's aggressive tone, Daisy's "low thrilling voice"
   - Location: `src/analyzer.py` — `_generate_character_profile()` prompt and response parser
   - Fix: Ensure profiler prompt explicitly requests speech_pattern and parser captures it

3. **`_VAGUE_REL_LABELS` NameError in profiler** [Profiles]
   - Problem: "Failed to structure profile for Jordan Baker: name '_VAGUE_REL_LABELS' is not defined" — code references an undefined variable
   - Impact: Jordan Baker's profile may have incomplete/broken relationships
   - Location: `src/analyzer.py` or `src/pipeline/character_profiling/post_corrections.py` — search for `_VAGUE_REL_LABELS`
   - Fix: Define the variable or fix the reference. This is likely a simple bug from a previous fix attempt.

### HIGH

4. **Wolfsheim duplicated: main_cast (6) vs supporting (32)** [Identity Resolution]
   - main_cast_7 "Meyer Wolfsheim" (6 mentions) has alias "Meyer Wolfshiem"
   - supporting_2 "Meyer Wolfshiem" (32 mentions) exists separately with 5x more mentions
   - The two were not merged despite the alias indicating they're the same person
   - Location: Post-extraction merge in `src/agents/characters.py` — the alias-to-existing-character merge should detect this
   - Fix: When a main_cast character has an alias matching a supporting character's canonical name, merge the supporting into main_cast (absorbing mentions)

5. **F6 generic descriptor clutter: 11 non-character entries** [Completeness]
   - Butler (20), Chauffeur (10), Gardener (5), Reporter (2), postman (1), Lutheran minister (1), war veteran (1), servants (1), chorus girl (1), rowdy little girl (1), man in duster (1)
   - These are roles/occupations, not named characters
   - Location: F6 reconciliation in `src/analyzer.py`
   - Fix: Add blocklist for generic role/occupation descriptors in F6 — filter entries that are purely descriptive (no proper nouns in name, common occupation words)

6. **Owl Eyes triplicated in F6** [Identity Resolution]
   - "Owl Eyes" (f6, 1 mention), "The man with owl-eyed glasses" (f6, 1 mention), "The drunken man in the library" (f6, 1 mention) — all the same character
   - Location: F6 reconciliation lacks substring/fuzzy matching for descriptive names
   - Fix: Add fuzzy/keyword matching in F6 to merge descriptive names sharing key terms ("owl")

7. **Nick Carraway and Jay Gatsby missing physical descriptions** [Profiles]
   - The narrator (34 mentions) and protagonist (269 mentions) have `physical_description: null`
   - Gatsby: "elegant young rough-neck, a year or two over thirty" (Ch.3). Nick describes himself less but has some physical context.
   - Location: `src/analyzer.py` — `_generate_character_profile()` failing for these specific characters
   - Fix: Debug why profiler returns null for these two. May be related to prompt length or character context.

### MEDIUM

8. **Invalid aliases persist** [Alias Grouping]
   - "the poor son-of-a-bitch" as Gatsby alias — this is a quote from Owl Eyes at the funeral, not a name variant
   - Duplicate aliases: Daisy has "Daisy" twice, George has "Wilson" twice
   - "Buchanan" shared between Tom and Daisy — ambiguous surname
   - Location: V2 alias validation in `src/pipeline/character_extraction_v2/main_cast.py`
   - Fix: Block aliases containing profanity/expletives. Deduplicate alias lists. Remove shared surname aliases when >1 character claims them.

9. **30 remaining "colleague" relationships from LLM profiler** [Profiles]
   - These come from the LLM itself (not the disabled co-occurrence injection)
   - Examples: Nick→Tom "colleague", Nick→George Wilson "colleague"
   - Fix: The profiler prompt should instruct omitting entries without textual evidence (same fix as Critical #1)

10. **Gatsby→Henry C. Gatz: "son" (reversed direction)** [Profiles]
    - From Gatsby's perspective, Henry C. Gatz is his FATHER, not his "son"
    - Location: `src/pipeline/character_profiling/post_corrections.py` or profiler prompt
    - Fix: Post-correction should detect directional inconsistency — if A→B is "son", B→A should be "father"

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
- **Fix H: "colleague" post-processing filter** — COMPLETELY INEFFECTIVE (198 "colleague" entries remain)

### Attempt 5 fixes
- **Fix I: Relative mention guard in narrator.py** — EFFECTIVE ✓
- **Fix J: Step 6.6 narrator fallback minimum raised to 20** — EFFECTIVE ✓
- **Fix K: Colleague substring filter** — INEFFECTIVE (192 remain, down from 198)

### Attempt 6 fixes
- **Fix L: Disabled `add_text_window_cooccurrence_relationships()` in post_corrections.py** — **EFFECTIVE ✓** (192→30 colleague entries)
- **Fix M: Block " and " pair-reference aliases in verify_aliases()** — **EFFECTIVE ✓** ("Tom and Daisy" removed)

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
| 6 | Disable cooccurrence colleague injection | `src/pipeline/character_profiling/post_corrections.py` | **FIXED** ✓ (192→30) |
| 6 | Block " and " pair-reference aliases | `src/pipeline/character_extraction_v2/main_cast.py` | **FIXED** ✓ |

**Pattern detected:** Relationship quality is now the PRIMARY blocker. With colleague injection disabled, the underlying LLM profiler output is exposed as poor — 47 wrong spousal labels, 30 remaining colleagues, only 44% of relationships correct. The fix must target the profiler prompt and post_corrections logic.

## Configuration Audit
- Model: `qwen3-next:80b-a3b-instruct-q8_0` for all agents (think_mode: false)
- Context length: 32768 — adequate for Gatsby's chapter sizes
- Temperature: 0.7 — reasonable
- Zero LLM retries — no prompt/schema failures
- `_VAGUE_REL_LABELS` NameError indicates a code bug introduced in a previous fix

## Priority Fix Order for Attempt 7

**The two blocking categories are Character Extraction (6/10) and Profiles (3.5/10).**

**Profiles are the bigger blocker (3.5/10, needs +4.5 to pass).** Focus order:

1. **Fix `_VAGUE_REL_LABELS` NameError** (Critical #3) — Simple bug fix. May fix Jordan's profile and prevent cascade errors. Quick win.

2. **Fix relationship quality** (Critical #1) — This is the single biggest issue. Two-part fix:
   - (A) Modify profiler prompt to instruct LLM to ONLY include relationships with explicit textual evidence, and to OMIT entries rather than guess.
   - (B) Add a post-processing cleanup that strips any "husband"/"wife" relationship that isn't reciprocal AND supported by evidence. If A→B is "husband" but B→A is not "wife", remove both.
   - (C) Check if `enforce_gender_consistency` is converting reasonable labels INTO "husband"/"wife".

3. **Add speech pattern extraction** (Critical #2) — Modify profiler prompt to request speech patterns; ensure parser captures them.

4. **Merge duplicate Wolfsheim** (High #4) — When main_cast has alias matching supporting's canonical, absorb supporting into main.

5. **Filter F6 generic descriptors** (High #5) — Blocklist for occupation words in F6.

6. **Fix missing physical descriptions for Nick/Gatsby** (High #7) — Debug profiler for these characters.

Items 1-3 target Profiles (3.5→8+). Items 4-6 target Character Extraction (6→8+).

## Fix History (Attempt 7)

### Attempt 7 fixes
- **Fix N: `_VAGUE_REL_LABELS` NameError** — Defined missing variable as local constant in secondary call block (line 3938 of analyzer.py). This unblocks Jordan Baker's profile generation.
  - Root cause: Line 3939 referenced `_VAGUE_REL_LABELS` which was never defined; `try/except` caught it silently
  - Modified: `src/analyzer.py`
  - Smoke test: Tests pass ✓

- **Fix O: Tighten spouse evidence window** — Changed `evidence_window` for spouse terms in `reject_unfounded_familial_labels()` from 500 chars to 150 chars. A 150-char window (~20-25 words) requires the family phrase to appear within the same short passage as both character names, preventing "his wife Daisy" in one sentence from validating a Gatsby→Wolfsheim "husband" label when they co-appear in a distant business passage.
  - Root cause: 500-char window is too loose; allows incidental family phrases (referring to third parties) to satisfy the evidence check
  - Modified: `src/pipeline/character_profiling/post_corrections.py`
  - Universality: Threshold change, not book-specific

- **Fix P: Speech patterns / verbal_tics prompt clarification** — Added explicit instruction to extract recurring phrases from dialogue for `verbal_tics` field. Changed from generic "otherwise use {}" to actionable guidance: "For verbal_tics, copy any recurring phrases or speech patterns from the character's dialogue."
  - Root cause: The fallback instruction allowed empty `verbal_tics: []` without requiring search of dialogue text
  - Modified: `src/analyzer.py` (CRITICAL INSTRUCTIONS section)

- **Fix Q: Wolfsheim alias-absorption step (STEP 5.6.9)** — Added new merge step to absorb supporting characters whose canonical name exactly matches an alias of a main cast character. This catches the case where "Meyer Wolfshiem" (32 mentions, supporting) is already an alias of "Meyer Wolfsheim" (main cast) but wasn't being merged because the alias was added after STEP 5.5 ran.
  - Root cause: STEP 5.5 checks supporting-vs-main-aliases, but some aliases are added to main cast characters AFTER 5.5 runs; the new STEP 5.6.9 runs after all alias-adding steps
  - Modified: `src/agents/characters.py`
  - Universality: Universal — if a character's name IS an alias, they're the same person

## Next Action
Run analysis to verify fixes.
