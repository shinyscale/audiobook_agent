# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 7
- **Phase:** awaiting_analysis
- **baseline_score:** 5.90

## Output Files
- HTML: ../output/gatsby/report.html
- JSON: ../output/gatsby/analysis.json

## Latest Scores
- Structure Detection: 10/10 ✓
- Character Extraction: 6/10 ✗
  - Completeness: 7.5/10
  - Identity Resolution: 5/10
  - Alias Grouping: 5.5/10
- Character Profiles: 4/10 ✗
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 7.45/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold: Character Extraction 6/10, Character Profiles 4/10)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 5.90 | - | Baseline. Profiles catastrophic, character identity broken |
| 2 | 6.73 | +0.83 | Relationships partially improved for main cast. Core narrator/Gatsby issues UNFIXED |
| 3 | 7.20 | +1.30 | Narrator FIXED (Nick ✓). Gatsby still supporting. "colleague" spam persists |
| 4 | 6.93 | +1.03 | REGRESSION: Gatsby promoted but narrator BROKE AGAIN. Colleague filter FAILED |
| 5 | 7.08 | +1.18 | Narrator FIXED ✓ (Fix I/J). Colleague filter STILL FAILED (192 remain). No speech patterns. |
| 6 | 7.15 | +1.25 | Colleague injection FIXED (192→30). But 47 wrong spousal labels EXPOSED underneath. |
| 7 | 7.45 | +1.55 | Spouse errors halved (47→23). But speech patterns 0/33, Wolfsheim still dup, Gatsby still supporting. |

## What Changed in Attempt 7

### Fix N (NameError) — EFFECTIVE ✓
- `_VAGUE_REL_LABELS` NameError fixed. Jordan Baker's profile now generates without error.

### Fix O (Spouse evidence window) — PARTIALLY EFFECTIVE
- Wrong spousal labels dropped from 47 to 23 (51% reduction). Still 23 wrong husband/wife labels.
- Total wrong relationships: 51/123 (41%), down from 80/143 (56%). Meaningful improvement but still far from acceptable.

### Fix P (Speech patterns prompt) — COMPLETELY FAILED
- Speech patterns: 0/33. The prompt change had zero effect.
- Either the LLM ignores the instruction, or the parser discards the field, or the field is never written to JSON.

### Fix Q (Wolfsheim alias absorption STEP 5.6.9) — FAILED
- Wolfsheim still duplicated: main_cast_7 (6 mentions) + supporting_2 (32 mentions).
- The new STEP 5.6.9 either didn't fire or didn't match. Need to check if it runs or if there's a logic error.

## Current Issues (Priority Order)

### CRITICAL

1. **Jay Gatsby (269 mentions) STILL in supporting cast** [Identity Resolution]
   - Problem: The PROTAGONIST with the most mentions in the entire book (269) is `supporting_13 "James Gatz"` instead of main cast. This has persisted across ALL 7 attempts.
   - Evidence: `jq '.characters[] | select(.id == "supporting_13")' analysis.json` → 269 mentions, supporting tier
   - Root cause: The V2 extraction pipeline assigned "James Gatz" to supporting. Previous fix attempts (G, STEP 5.11) failed to promote him. The role safety net in analyzer.py may not be firing, OR the character was never in main_cast to begin with (only in supporting_cast output).
   - Location: `src/agents/characters.py` — STEP 5.11 promotion logic. Also check if supporting_cast extraction is running and absorbing the character before main_cast can claim him.
   - Fix: This needs a DIFFERENT approach since 5 previous attempts failed. Add a post-extraction step that checks if ANY supporting character has >100 mentions AND more mentions than any main cast character → force-promote to main cast. This is a universal rule (highest-mention character can't be supporting).

2. **Speech patterns still 0/33 despite Fix P** [Profiles]
   - Problem: Zero speech patterns for any character. Critical for narrator prep.
   - Expected: Gatsby "old sport", Wolfsheim "Oggsford"/"gonnegtion", Daisy's "low thrilling voice", Tom's aggressive/commanding tone
   - Root cause: Fix P modified the profiler prompt but had NO effect. The issue is likely:
     - (A) The `speech_pattern` field is not in the Pydantic model or JSON schema, so LLM output is discarded
     - (B) The parser doesn't read it from the LLM response
     - (C) The field is populated but not written to final output
   - Location: Must trace the FULL pipeline: `src/models.py` (Character model fields) → `src/analyzer.py` (profiler prompt + response parser) → JSON serialization
   - Fix: Search for `speech_pattern` in models.py to verify the field exists. Search the profiler response parser to verify it captures the field. Add debug logging if needed.

3. **23 wrong spousal relationships remain** [Profiles]
   - Problem: Despite Fix O halving spouse errors, 23 wrong "husband"/"wife" labels persist. Examples from this run:
     - Nick→Tom "husband" ✗, Nick→Sloane "husband" ✗
     - Tom→George "husband" ✗, Tom→Nick "husband" ✗, Tom→McKee "husband" ✗, Tom→Sloane "husband" ✗
     - Jordan→Henry C. Gatz "mother" ✗, Jordan→James Gatz "wife" ✗
     - Myrtle→McKee "husband" ✗, Myrtle→Catherine "brother" ✗ (should be "sister")
     - George→McKee "husband" ✗
     - Sloane→James Gatz "wife" ✗, Sloane→Nick "wife" ✗, Sloane→Tom "wife" ✗, Sloane→Henry C. Gatz "mother" ✗
     - McKee→Daisy "husband" ✗, McKee→Tom "husband" ✗, McKee→Myrtle "husband" ✗, McKee→George "husband" ✗
     - Henry C. Gatz→Jordan "son" ✗, Henry C. Gatz→Sloane "son" ✗
   - Root cause: The LLM profiler is STILL assigning gendered familial labels to unrelated characters. The 150-char evidence window helped but isn't enough. The fundamental issue is the LLM guesses relationship types when it has no evidence.
   - Location: `src/analyzer.py` (profiler prompt) + `src/pipeline/character_profiling/post_corrections.py`
   - Fix: Two-pronged approach:
     - (A) Restrict valid relationship labels to a closed set: "spouse", "parent", "child", "sibling", "romantic interest", "friend", "employer/employee", "rival", "neighbor", "acquaintance", "associate". The LLM must pick from ONLY this list or output "none" (then drop the entry).
     - (B) Add a post-processing step: if a character appears as "husband"/"wife" to MORE than one other character, keep only the one with highest co-occurrence count and remove the rest (a person can have at most one spouse).

4. **28 "colleague" relationships remain** [Profiles]
   - Problem: "colleague" is not a meaningful label in 1920s Long Island social fiction. Characters like Nick→Myrtle, Daisy→George, Jordan→Wolfsheim have zero professional interaction.
   - Location: `src/analyzer.py` profiler prompt
   - Fix: Remove "colleague" from allowed relationship labels, or post-filter all "colleague" labels where neither character has an occupation/professional role.

### HIGH

5. **Wolfsheim still duplicated despite Fix Q** [Identity Resolution]
   - main_cast_7 "Meyer Wolfsheim" (6 mentions, alias "Meyer Wolfshiem") + supporting_2 "Meyer Wolfshiem" (32 mentions)
   - Fix Q (STEP 5.6.9) was supposed to absorb supporting chars whose canonical matches a main_cast alias — but it didn't work
   - Location: `src/agents/characters.py` — verify STEP 5.6.9 actually runs (add logging), check if string matching is case-sensitive or has whitespace issues
   - Fix: Debug why STEP 5.6.9 didn't fire. The alias "Meyer Wolfshiem" on main_cast_7 should match supporting_2's canonical "Meyer Wolfshiem" exactly.

6. **Phantom parent entries** [Identity Resolution]
   - "the man (the father)" (main_cast_3_parent, 2 mentions) and "Henry C. Gatz (the father)" (main_cast_8_parent, 2 mentions)
   - These are artifacts from semantic split logic creating `_parent` suffixed IDs
   - Location: `src/agents/characters.py` — semantic split or parent-child disambiguation
   - Fix: The parent-splitting logic is too aggressive. These should not be separate entries.

7. **F6 generic descriptor clutter: 6+ non-character entries** [Completeness]
   - Reporter, Lutheran minister, Butler (20 mentions!), war veteran, Chauffeur (10), Gardener (5)
   - These are occupational roles, not named characters
   - Location: F6 reconciliation in `src/analyzer.py`
   - Fix: Add blocklist for common occupational/role descriptors in F6 filter

8. **Invalid aliases** [Alias Grouping]
   - "Gatsby's mansion" — a building, not a person alias (on James Gatz)
   - "the poor son-of-a-bitch" — a quote, not an alias (on James Gatz)
   - "the man" — too generic (on Tom Buchanan)
   - Tom has "Tom" twice (duplicate)
   - "Buchanan" shared by both Tom and Daisy (ambiguous)
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` alias validation
   - Fix: Block possessive aliases, aliases containing profanity, duplicate aliases, overly generic single-word aliases like "the man"

### MEDIUM

9. **Nick Carraway and Myrtle Wilson missing physical descriptions** [Profiles]
   - Nick (narrator, 34 mentions) and Myrtle (23 mentions) have `physical_description: null`
   - Nick: sparse self-description but has context. Myrtle: "middle thirties, faintly stout, carried her surplus flesh sensuously"
   - Location: `src/analyzer.py` profiler

10. **Chapter 1 summary has "Nick Carraway, Nick Carraway" repetition** [Summaries]
    - Minor name duplication in first summary. Cosmetic issue.

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

### Attempt 7 fixes
- **Fix N: `_VAGUE_REL_LABELS` NameError** — **EFFECTIVE ✓** (Jordan profile generates)
- **Fix O: Spouse evidence window 500→150 chars** — **PARTIALLY EFFECTIVE** (47→23 wrong spouse labels)
- **Fix P: Speech patterns prompt** — **COMPLETELY FAILED** (0/33 still)
- **Fix Q: STEP 5.6.9 alias absorption** — **FAILED** (Wolfsheim still duplicated)

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
| 7 | NameError `_VAGUE_REL_LABELS` | `src/analyzer.py` | **FIXED** ✓ |
| 7 | Spouse evidence window | `src/pipeline/character_profiling/post_corrections.py` | Partial (47→23 spouse errors) |
| 7 | Speech patterns prompt | `src/analyzer.py` | **FAILED** — 0/33 |
| 7 | Wolfsheim alias absorption | `src/agents/characters.py` (STEP 5.6.9) | **FAILED** — still duplicated |

**Patterns detected:**
- `src/analyzer.py` modified in attempts 3, 4, 5, 7 for relationship/profile issues → Fix approach must change. Prompt-level fixes are unreliable with this LLM. Post-processing filters are more effective.
- `src/agents/characters.py` modified in attempts 2, 3, 5, 7 for Gatsby promotion → 5 failed attempts. Need a fundamentally different approach (hard rule, not heuristic).
- Speech patterns: prompt changes don't work. Must verify the data pipeline end-to-end (model field → parser → serializer).

## Configuration Audit
- Model: `qwen3-next:80b-a3b-instruct-q8_0` for all agents (think_mode: false)
- Context length: 32768 — adequate for Gatsby's chapter sizes
- Temperature: 0.7 — reasonable
- Zero LLM retries — no prompt/schema failures

## Priority Fix Order for Attempt 8

**The two blocking categories are Character Extraction (6/10) and Profiles (4/10).**

### Profiles (4/10 → 8+) — Primary blocker

1. **Debug speech_pattern pipeline end-to-end** — Trace from `src/models.py` → profiler prompt → response parser → JSON output. The field may not exist in the data model, or the parser may discard it. This is the MOST impactful single fix (0/33 → populated would add ~2 points to Profiles score alone).

2. **Post-process relationships aggressively** — Don't trust the LLM to get labels right. Add a post-processing pass that:
   - Removes any relationship where the label is "husband"/"wife" and neither character has a known marriage from text evidence
   - Removes all "colleague" labels (not applicable to this genre, and the LLM clearly can't use it correctly)
   - Limits each character to at most 1 "spouse" relationship (the highest-confidence one)
   - Falls back to "acquaintance" or drops entries entirely rather than keeping wrong labels

### Character Extraction (6/10 → 8+) — Secondary blocker

3. **Force-promote highest-mention supporting characters** — Add a hard rule: if a supporting character has >100 mentions AND more mentions than any main_cast character, promote to main_cast. This bypasses the broken STEP 5.11 logic with a simple, universal, unchallengeable rule.

4. **Debug STEP 5.6.9 (Wolfsheim merge)** — Add logging to verify the step runs and check why the match fails. The canonical "Meyer Wolfshiem" (supporting_2) should EXACTLY match alias "Meyer Wolfshiem" on main_cast_7.

5. **Filter F6 generic descriptors** — Block entries matching common occupation words.

6. **Remove phantom parent entries** — Suppress `_parent` suffixed character IDs or merge them back.

## Attempt 8 Fixes Applied

### Fix R (Canonical name normalization — Step 4.5.5 in analyzer.py)
- Added post-extraction canonical rename: if canonical appears < 10 times in text AND an alias appears 20+ times (3x more), rename canonical to the alias.
- Target: "James Gatz" (4 text uses) → "Jay Gatsby" (175+ uses).
- Universal: applies to any book where a character is known primarily by a pseudonym or nickname.
- Location: `src/analyzer.py` (after role safety net, before profiling)

### Fix S (One-spouse invariant — post_corrections.py)
- Added `_enforce_one_spouse_invariant()`: if a character has spousal (husband/wife/spouse) labels pointing to multiple other characters, keep only the pair with the most text co-mentions, downgrade the rest to "associated".
- Universal rule: each character has at most one spouse.
- Location: `src/pipeline/character_profiling/post_corrections.py`

### Fix T (Colleague → associated in add_cooccurrence_relationships)
- Changed `add_cooccurrence_relationships` to use "associated" instead of "colleague".
- "associated" gets cleaned by `clean_unknown_relationships`, removing spurious cooccurrence labels.
- Universal: cooccurrence-based fallback labels should be ephemeral (upgraded by text evidence or dropped).
- Location: `src/pipeline/character_profiling/post_corrections.py`

### Fix U (STEP 5.9.9 — second-pass alias absorption)
- Added a second-pass of STEP 5.6.9 that runs AFTER all alias-enrichment steps (before STEP 5.10).
- Catches cases where main cast aliases are added after the first STEP 5.6.9 pass.
- Handles Wolfsheim duplicate: supporting_2 "Meyer Wolfshiem" absorbed into main_cast_7 "Meyer Wolfsheim".
- Location: `src/agents/characters.py`

## Next Action
Re-run analysis to verify fixes.
