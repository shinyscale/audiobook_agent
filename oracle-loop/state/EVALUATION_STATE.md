# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 8
- **Phase:** awaiting_fix
- **baseline_score:** 5.90

## Output Files
- HTML: ../output/gatsby/report.html
- JSON: ../output/gatsby/analysis.json

## Latest Scores
- Structure Detection: 10/10 ✓
- Character Extraction: 6.5/10 ✗
  - Completeness: 7/10
  - Identity Resolution: 5.5/10
  - Alias Grouping: 6/10
- Character Profiles: 6.5/10 ✗
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 7.75/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold: Character Extraction 6.5/10, Character Profiles 6.5/10)

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
| 8 | 7.75 | +1.85 | Gatsby promoted ✓, colleagues eliminated ✓. Green light+Owl Eyes merge, 6 wrong spouse labels remain. |

## What Changed in Attempt 8

### Fix R (Canonical rename) — EFFECTIVE ✓
- Gatsby is now main_cast_1, role "protagonist", 290 mentions. No longer "James Gatz" in supporting.
- "James Gatz" and "Jay Gatsby" are listed as aliases.

### Fix S (One-spouse invariant) — PARTIALLY EFFECTIVE
- Spousal relationships reduced from 23 to 10. However, 6 of those 10 are STILL WRONG.
- Wrong: Nick→Tom "husband", Gatsby→Jordan "husband", Jordan→Gatsby "wife", The green light→Tom "husband", McKee→Wilson "husband", Sloane→Tom "wife"
- Correct: Daisy→Tom ✓, Tom→Daisy ✓, Myrtle→Wilson ✓, Wilson→Myrtle ✓

### Fix T (Colleague → associated) — EFFECTIVE ✓
- Colleague count: 0. All colleague labels eliminated.

### Fix U (Second-pass alias absorption) — PARTIALLY EFFECTIVE
- main_cast_7 "Wolfshiem" (32 mentions) now has aliases "Wolfsheim" and "Meyer Wolfsheim"
- BUT: supporting_10 "Meyer Wolfshiem" (6 mentions) and F6 "Meyer Wolfsiem" (1 mention) still exist as separate entries
- Wolfsheim is TRIPLICATED instead of duplicated (worse fragmentation, though main entry now has correct mentions)

### Voice Guidance — DISCOVERED
- Previous evaluations checked for `speech_pattern` field — the actual field is `voice_guidance` with sub-fields: suggested_tone, dialect_notes, verbal_tics, formality_level
- This data IS populated for main characters. Gatsby has "old sport" ✓, Wolfsheim has "gonnegtion" ✓, Myrtle has working-class speech notes ✓
- **Profiles score revised upward from 4/10 to 6.5/10** — voice guidance was likely present in previous attempts too but missed by evaluator

## Current Issues (Priority Order)

### CRITICAL

1. **FALSE MERGE: "The green light" + Owl-Eyed Man** [Identity Resolution]
   - Problem: main_cast_10 "The green light" (18 mentions) has aliases: "the light", "The drunk man in the library", "the library", "The owl-eyed man", "The man with owl-eyed glasses"
   - Evidence: The green light is a SYMBOL (light at end of Daisy's dock). The owl-eyed man is a SPEAKING CHARACTER who appears at Gatsby's library party (Ch 3) and alone at his funeral (Ch 9). These are completely unrelated entities.
   - Root cause: Both are non-standard "characters" (symbolic/descriptor). The extraction pipeline likely merged all non-person entities together.
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` or `src/agents/characters.py` — descriptor merge logic is too aggressive
   - Fix: The owl-eyed man should be a separate character entry. Either prevent merging entities with different core nouns ("light" vs "man"), or add a post-extraction split for entities whose aliases have incompatible semantic categories (inanimate object vs person descriptor).

2. **6 wrong spousal relationships persist** [Profiles]
   - Problem: Despite one-spouse invariant, 6 false spousal labels remain:
     - Nick→Tom "husband" ✗
     - Gatsby→Jordan "husband" ✗
     - Jordan→Gatsby "wife" ✗
     - The green light→Tom "husband" ✗
     - McKee→Wilson "husband" ✗
     - Sloane→Tom "wife" ✗
   - Root cause: The LLM profiler generates wrong gendered labels. The one-spouse invariant only prunes MULTIPLE spouses per character, but these are all single (each character has only 1 spouse label, and it's wrong).
   - Location: `src/pipeline/character_profiling/post_corrections.py`
   - Fix: Add a KNOWN COUPLES validation: for each spousal label A→B "husband"/"wife", verify B→A also has the reciprocal label. If the relationship is not reciprocated (B doesn't list A as spouse), downgrade to "associated". True couples (Tom↔Daisy, George↔Myrtle) will survive because both directions confirm each other.

3. **Tom Buchanan has "old sport" as verbal tic — WRONG** [Profiles]
   - Problem: Tom's voice_guidance.verbal_tics includes "old sport", but this is Gatsby's signature phrase, not Tom's.
   - Tom's actual speech patterns: aggressive, commanding, racist rhetoric, forceful assertions
   - Root cause: LLM attributed the wrong character's catchphrase
   - Location: `src/analyzer.py` profiler — low priority since this requires LLM accuracy improvement
   - Fix: Post-processing: if the same verbal_tic appears on multiple characters, keep it only on the one with the highest mention of that phrase in dialogue. Or: flag "old sport" as exclusively Gatsby's since it appears in his dialogue far more.

### HIGH

4. **Wolfsheim TRIPLICATED** [Identity Resolution]
   - main_cast_7 "Wolfshiem" (32 mentions, aliases: "Wolfsheim", "Meyer Wolfsheim")
   - supporting_10 "Meyer Wolfshiem" (6 mentions)
   - F6 hash "Meyer Wolfsiem" (1 mention)
   - Location: `src/agents/characters.py` STEP 5.9.9 or F6 reconciliation in `src/analyzer.py`
   - Fix: The matching is likely exact-string. Need fuzzy/normalized matching: strip "Meyer ", normalize spelling variants (Wolfshiem/Wolfsheim/Wolfsiem). A Levenshtein distance ≤ 2 check would catch all three.

5. **F6 generic descriptor clutter: 6 non-character entries** [Completeness]
   - "gardener" (5 mentions), "butler" (20 mentions), "chauffeur" (10), "New York reporter" (1), "Lutheran minister" (1), "the war veteran" (1)
   - These are occupational roles, not named characters
   - Location: F6 reconciliation in `src/analyzer.py`
   - Fix: Add blocklist for common occupational/role descriptors that are all-lowercase or match patterns like "the [noun]", "[adjective] [occupation]". Block any F6 candidate that is entirely lowercase (no proper noun).

6. **"Daisy Fay" as separate F6 entry** [Identity Resolution]
   - F6 hash "Daisy Fay" (1 mention) — this is Daisy Buchanan's maiden name, should be her alias
   - Location: F6 reconciliation in `src/analyzer.py`
   - Fix: F6 should check if a new character's first name matches an existing character's canonical name or alias before creating a new entry. "Daisy Fay" shares "Daisy" with main_cast_2 "Daisy" → should become an alias, not a new character.

7. **Invalid aliases on Gatsby** [Alias Grouping]
   - "the man" — too generic
   - "the poor son-of-a-bitch" — a quote from the owl-eyed man at the funeral, not an alias
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` alias validation
   - Fix: Block aliases that are pure generic descriptors ("the man", "the woman") and aliases containing profanity/slang.

8. **"Buchanan" shared by both Tom and Daisy** [Alias Grouping]
   - Tom Buchanan has alias "Buchanan"; Daisy also has alias "Buchanan"
   - Ambiguous shared surname — a narrator looking up "Buchanan" gets two hits
   - Location: `src/pipeline/character_extraction_v2/main_cast.py`
   - Fix: If a surname-only alias is shared by 2+ characters, remove it from all (or keep only on the character who uses it most as a standalone reference — Tom is usually called "Tom" or "Tom Buchanan", while "Buchanan" standalone typically refers to the family generally).

### MEDIUM

9. **Nick Carraway, Gatsby, and Myrtle missing physical descriptions** [Profiles]
   - Nick: sparse self-description but has some context (narrator, first-person perspective)
   - Gatsby: "an elegant young rough-neck, a year or two over thirty" + tan, short hair, clean-cut
   - Myrtle: "middle thirties, faintly stout, carried her surplus flesh sensuously"
   - Location: `src/analyzer.py` profiler
   - Fix: May require longer context windows for the profiler or explicit prompting to look for appearance descriptions in other characters' observations.

10. **Chapter 1 summary has "Nick Carraway, Nick Carraway" repetition** [Summaries]
    - Minor cosmetic issue in first sentence.
    - Location: `src/agents/summary_agent.py` or post-processing

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
- **Fix P: Speech patterns prompt** — **COMPLETELY FAILED** (0/33 still) — Note: voice_guidance field was populated all along; evaluator checked wrong field name
- **Fix Q: STEP 5.6.9 alias absorption** — **FAILED** (Wolfsheim still duplicated)

### Attempt 8 fixes
- **Fix R: Canonical rename (James Gatz → Gatsby)** — **EFFECTIVE ✓** (Gatsby promoted to main_cast protagonist)
- **Fix S: One-spouse invariant** — **PARTIALLY EFFECTIVE** (23→10 spousal labels, but 6 still wrong)
- **Fix T: Colleague → associated** — **EFFECTIVE ✓** (colleague count: 0)
- **Fix U: Second-pass alias absorption (STEP 5.9.9)** — **PARTIALLY EFFECTIVE** (main Wolfshiem entry has 32 mentions, but 2 extra entries remain)

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
| 7 | Speech patterns prompt | `src/analyzer.py` | **FAILED** — evaluator error (voice_guidance was populated) |
| 7 | Wolfsheim alias absorption | `src/agents/characters.py` (STEP 5.6.9) | **FAILED** — still duplicated |
| 8 | Gatsby canonical rename | `src/analyzer.py` | **FIXED** ✓ |
| 8 | One-spouse invariant | `src/pipeline/character_profiling/post_corrections.py` | Partial (23→10, but 6 still wrong) |
| 8 | Colleague → associated | `src/pipeline/character_profiling/post_corrections.py` | **FIXED** ✓ |
| 8 | Second-pass alias absorption | `src/agents/characters.py` (STEP 5.9.9) | Partial (main entry fixed, 2 extras remain) |

**Patterns detected:**
- `src/pipeline/character_profiling/post_corrections.py` is the right place for relationship fixes — post-processing works better than prompt engineering
- Wolfsheim spelling variants (Wolfshiem/Wolfsheim/Wolfsiem) need fuzzy matching, not exact string matching
- Green light + Owl Eyes merge is a NEW issue (or newly noticed) — likely caused by descriptor merge logic treating all non-person entities as one

## Configuration Audit
- Model: `qwen3-next:80b-a3b-instruct-q8_0` for all agents (think_mode: false)
- Context length: 32768 — adequate for Gatsby's chapter sizes
- Temperature: 0.7 — reasonable
- Zero LLM retries — no prompt/schema failures

## Priority Fix Order for Attempt 9

**The two blocking categories are Character Extraction (6.5/10) and Profiles (6.5/10).**

### Character Extraction (6.5/10 → 8+)

1. **Split green light from Owl Eyes** — CRITICAL. Either prevent the merge in descriptor merge logic (different core nouns: "light" vs "man") or add a post-merge split for inanimate+person merged entities. This is worth ~1 point to Identity Resolution.

2. **Fuzzy Wolfsheim dedup** — Normalize spelling variants before dedup. Levenshtein distance ≤ 2 or normalize by stripping title words and comparing. Worth ~0.5 points.

3. **F6 generic descriptor filter** — Block all-lowercase F6 candidates or those matching occupation patterns. Remove 6 clutter entries. Worth ~0.5 points.

4. **Merge "Daisy Fay" into Daisy** — F6 should check first-name overlap with existing characters. Worth ~0.25 points.

5. **Remove invalid aliases** — Block "the man", "the poor son-of-a-bitch", shared "Buchanan". Worth ~0.5 points.

### Profiles (6.5/10 → 8+)

6. **Reciprocal spouse validation** — For each spousal label A→B, require B→A to also be spousal. Non-reciprocated → downgrade to "associated". This eliminates 6 wrong labels while preserving 4 correct ones (Tom↔Daisy and George↔Myrtle are reciprocal). Worth ~1 point.

7. **Missing physical descriptions** — Gatsby and Myrtle have clear textual descriptions that the profiler missed. Nick as narrator has less, but still has some. Worth ~0.5 points if fixed.

## Next Action
Run PROMPT_fix.md to address green light/owl eyes split (Critical #1) and reciprocal spouse validation (Critical #2) as top priorities.
