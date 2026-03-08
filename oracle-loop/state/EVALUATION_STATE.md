# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 4
- **Phase:** awaiting_evaluation
- **baseline_score:** 5.90

## Output Files
- HTML: ../output/gatsby/report.html
- JSON: ../output/gatsby/analysis.json

## Latest Scores
- Structure Detection: 10/10 ✓
- Character Extraction: 5/10 ✗
  - Completeness: 7/10
  - Identity Resolution: 4/10
  - Alias Grouping: 6/10
- Character Profiles: 4/10 ✗
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 7.20/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 5.90 | - | Baseline. Profiles catastrophic, character identity broken |
| 2 | 6.73 | +0.83 | Relationships partially improved for main cast. Core narrator/Gatsby issues UNFIXED |
| 3 | 7.20 | +1.30 | Narrator FIXED (Nick ✓). Gatsby still supporting. "colleague" spam persists |

## What Improved in Attempt 3
- **Fix D WORKED**: Nick Carraway correctly identified as narrator (is_narrator: true). Doctor T. J. Eckleburg is no longer narrator.
- **Chapter 1 doubled name fixed**: Summary no longer repeats "Nick Carraway, Nick Carraway"
- George Wilson canonical name is now "George Wilson" (not "George B. Wilson") — "George B. Wilson" moved to alias

## What Did NOT Improve
- **Fix E FAILED**: "colleague" still appears in ~75-90% of all relationship entries. The prompt forbidding "colleague" was ignored by the LLM.
- **STEP 5.11 still not promoting Gatsby**: James Gatz remains supporting_15 with role "minor" and 268 mentions. Diagnostic logging was added but the promotion didn't fire.
- **Speech patterns still all null**: Zero speech_pattern entries across all 41 characters.

## Current Issues (Priority Order)

### CRITICAL

1. **Protagonist in wrong cast tier: Gatsby is supporting_15 "James Gatz" with role "minor" (268 mentions)** [Identity Resolution]
   - Problem: Jay Gatsby — the TITLE CHARACTER with 268 mentions (most in the book) — is `supporting_15` with canonical name "James Gatz", role "minor", null physical_description, null speech_pattern, null personality_traits.
   - His aliases ARE correct: ["Jay Gatsby", "Gatsby"]. So the system knows who he is, but he's in the wrong tier.
   - STEP 5.11 (added in attempt 2) was supposed to promote high-mention supporting characters. It didn't fire despite 268 >> 200 threshold. Fix F added diagnostic logging but we can't see logs in the output — need to check what happened.
   - This is attempt 3 with same file modified (`src/agents/characters.py` STEP 5.11). **Pattern alert: same file modified 2x without success.** Need different approach.
   - Cascading impact: Without promotion, Gatsby gets no profile, no physical description, no speech patterns. This single issue tanks both Character Extraction AND Profiles scores.
   - **New fix approach:** Instead of trying to fix STEP 5.11 (which may have structural issues preventing execution), add a FINAL safety net in `src/analyzer.py` AFTER the character extraction pipeline returns. If any character has >100 mentions and role="minor", force-promote to main cast with role="protagonist". This bypasses whatever is blocking STEP 5.11 in characters.py.
   - Location: `src/analyzer.py` — add post-extraction promotion before profiling begins

2. **"colleague" relationship spam still pervasive (~80% of all relationships)** [Profiles]
   - Problem: Fix E added "colleague" to forbidden labels in the profiler prompt, but the LLM still defaults to "colleague" for any pair without a strong relationship. Examples:
     - Nick→Tom: "colleague" (should be "friend" or "cousin-in-law")
     - Nick→Myrtle: "colleague" (should be omitted — barely interacts)
     - Daisy→Catherine: "colleague" (no relationship)
     - James Gatz→Ferdie: "colleague" (no relationship)
   - Root cause: Simply listing "colleague" as forbidden doesn't work — the LLM needs a different instruction structure. Instead of "don't use colleague", the prompt should say "ONLY include characters who have a named, meaningful relationship. If no specific relationship exists, DO NOT list them."
   - Additional fix: Post-process to strip any relationship labeled "colleague" from the output.
   - Location: `src/analyzer.py` `_generate_character_profile()` prompt; also add post-processing filter

### HIGH

3. **Speech patterns null for ALL 41 characters** [Profiles]
   - Problem: Zero speech_pattern entries. Critical missing data for narrator prep.
   - Notable missing: Gatsby's "old sport" catchphrase, Wolfshiem's dialect ("Oggsford", "gonnegtion"), Tom's aggressive/domineering tone, Daisy's "low, thrilling voice"
   - Location: Profile generation in `src/analyzer.py` — the prompt may not explicitly request speech patterns, or the LLM response parser drops them
   - Fix: Ensure the profile prompt explicitly asks "What are this character's distinctive speech patterns, verbal tics, catchphrases, accent, or dialect?" and that the response parser captures the field

4. **Incorrect relationship labels persist** [Profiles]
   - Tom→George Wilson: "husband" (completely wrong — Tom sold George a car, Tom is Myrtle's lover)
   - Myrtle→Catherine: "husband" (should be "sister" — Catherine is Myrtle's sister)
   - George→Myrtle: "husband" (correct relationship but wrong gender label — should be "wife" or "spouse")
   - Tom→Daisy: "husband" (correct meaning but inconsistent — Daisy→Tom uses "spouse")
   - Location: `src/pipeline/character_profiling/post_corrections.py` — co-mention window still picking up wrong labels

5. **Wolfsheim/Wolfshiem duplicate** [Identity Resolution]
   - `supporting_10` "Meyer Wolfshiem" (32 mentions) and `5a81392a280e` "Meyer Wolfsheim" (2 mentions) — same character, different spellings
   - Fitzgerald uses "Wolfshiem" in the text but F6 reconciliation created a second entry with the standard spelling "Wolfsheim"
   - Location: F6 reconciliation in `src/analyzer.py` — needs fuzzy string matching for near-identical names

6. **Owl-eyed man duplicated** [Identity Resolution]
   - `f2d0505f9af9` "The man with owl-eyed spectacles" (1 mention) and `f189a657a225` "The man with owl-eyed glasses" (1 mention)
   - Same character with slightly different descriptions
   - Location: F6 reconciliation — needs substring/overlap dedup

7. **Montenegro listed as character** [Completeness]
   - `4e92f9d2cdf0` "Montenegro" (7 mentions) — this is a country, not a character. Gatsby claims a medal from Montenegro but it's a place name.
   - Location: F6 reconciliation — needs to filter geographic entities (cross-reference with NER labels)

8. **F6 generic descriptor clutter** [Completeness]
   - Butler (20 mentions), Chauffeur (10), Gardener (5), reporter (2), "The war veteran" (1), "The postman" (1), "The passenger in the coupé" (1), "The man in the duster" (1), "The woman in yellow" (1), "The red-haired chorus girl" (1)
   - These are generic descriptors, not named characters. Inflates character count from ~15 real characters to 41.
   - Location: F6 reconciliation in `src/analyzer.py` — needs filtering for generic descriptors and single-mention ephemeral references

### MEDIUM

9. **"Buchanan" alias shared between Tom and Daisy** [Alias Grouping]
   - Both main_cast_2 (Daisy) and main_cast_3 (Tom) have "Buchanan" as alias
   - Fix: Remove shared surname alias when multiple characters claim it

10. **Nick Carraway has no physical_description** [Profiles]
    - As first-person narrator, physical details are sparse in text, but Nick does mention being "thirty" and describes himself briefly
    - The profiler should note narrator self-description limitations

11. **Relationship references use inconsistent names** [Profiles]
    - Some relationships reference "Gatsby", others "Jay Gatsby", others "James Gatz" — all the same person but the profiler doesn't normalize
    - Jordan→"Gatsby": "intermediary"; Wolfshiem→"Gatsby": "close friend"; Daisy→"Jay Gatsby": "romantic interest"; Daisy→"James Gatz": "romantic interest" (duplicate!)
    - This creates phantom relationship entries for the same person

12. **"George B. Wilson" — fabricated middle initial still in aliases** [Identity Resolution]
    - Canonical is now "George Wilson" (improvement) but "George B. Wilson" remains as alias
    - Fitzgerald never uses a middle initial for George Wilson
    - Location: V2 Pass 1 extraction hallucinated it; post-extraction validation should strip initials not in source text

## Fix History

### Attempt 2 fixes
- **Fix A: STEP 4.26 narrator threshold** — INEFFECTIVE (wrong layer)
- **Fix B: STEP 5.11 promotion** — INEFFECTIVE (code not firing)
- **Fix C: Relationship label override guard** — PARTIALLY EFFECTIVE

### Attempt 3 fixes
- **Fix D: Narrator layered defense (narrator.py + characters.py)** — EFFECTIVE ✓
- **Fix E: "colleague" forbidden in profiler prompt** — INEFFECTIVE (LLM ignores forbidden list)
- **Fix F: STEP 5.11 diagnostic logging** — ADDED but promotion still didn't fire

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 2 | False narrator (Eckleburg) | `src/agents/characters.py` (STEP 4.26 threshold) | No change — wrong layer |
| 2 | Gatsby wrong cast tier | `src/agents/characters.py` (STEP 5.11 new) | No change — code not firing |
| 2 | Relationship labels all "husband" | `src/pipeline/character_profiling/post_corrections.py` | Partial fix — main cast improved |
| 3 | False narrator | `src/pipeline/character_extraction_v2/narrator.py`, `src/agents/characters.py` | **FIXED** ✓ |
| 3 | "colleague" spam | `src/analyzer.py` (profiler prompt) | No change — LLM ignores forbidden list |
| 3 | Gatsby promotion diagnostic | `src/agents/characters.py` (STEP 5.11 logging) | No change — promotion still doesn't fire |

**Pattern detected:** `src/agents/characters.py` STEP 5.11 has been modified 2x without success for Gatsby promotion. Fix phase MUST use a different approach — either fix the root cause in characters.py by debugging why STEP 5.11 doesn't execute, or add a safety-net promotion in `src/analyzer.py` post-extraction.

**Pattern detected:** Prompt-level forbidden labels (Fix E) are ineffective for "colleague". Fix phase MUST use a structural approach — either rewrite the relationship prompt to only request meaningful relationships (not list all characters), or add post-processing to strip "colleague" entries.

## Configuration Audit
- Model: `qwen3-next:80b-a3b-instruct-q8_0` for all agents (think_mode: false)
- Context length: 32768 — adequate for Gatsby's chapter sizes
- Temperature: 0.7 — reasonable
- Zero LLM retries — no prompt/schema failures
- No chunking issues apparent

## Priority Fix Order for Attempt 4
1. **Gatsby promotion** (Critical #1) — fixes Character Extraction AND Profiles scores. Use analyzer.py safety net, not characters.py STEP 5.11.
2. **"colleague" spam** (Critical #2) — rewrite relationship prompt structure + add post-processing filter. Fixes Profiles score.
3. **Speech patterns** (High #3) — ensure prompt requests and parser captures speech_pattern field. Fixes Profiles score.
4. **Wrong relationship labels** (High #4) — Tom→George "husband", Myrtle→Catherine "husband"

Items 1-3 together should bring Character Extraction to ~7-8 and Profiles to ~7-8, potentially crossing the 8.0 threshold.

## Attempt 4 Fixes Applied

### Fix G: Role safety net in analyzer.py (CRITICAL #1 — Gatsby promotion)
- **Root cause:** James Gatz (supporting_15, 268 mentions, role "minor") wasn't being promoted by STEP 5.11 in characters.py for unclear reasons. The characters.py pipeline likely promotes "Jay Gatsby" (supporting NER entry with alias "Gatsby") to main_cast by STEP 5.8, but "James Gatz" (3-5 raw NER mentions, separate entry) stays in supporting_cast. Aliases ["Jay Gatsby", "Gatsby"] are added to "James Gatz" only AFTER promotion logic runs, so the alias-aware 268-mention count arrives too late.
- **Fix:** Added a safety net BEFORE profiling in `src/analyzer.py` that upgrades any character with role "minor"/"supporting" and ≥200 mentions to "protagonist", ≥100 mentions to "main". Runs on `pipeline_char_map.characters` before Step 4.6.
- **Files modified:** `src/analyzer.py` (before Step 4.6)
- **Classification:** Algorithmic / universal invariant enforcement
- **Universality:** Yes — any character with 200+ mentions in a 50K+ word novel is a protagonist

### Fix H: "colleague" filter in relationship post-processing (CRITICAL #2)
- **Root cause:** `_VAGUE_REL_LABELS` set in `_generate_character_profile()` at line ~3774 filtered "associated"/"acquaintance"/"unknown" but NOT "colleague". LLM uses "colleague" as default fallback for 213/256 relationships.
- **Fix 1:** Added "colleague" to `_VAGUE_REL_LABELS` and added `startswith("colleague")` check to catch variants like "colleague in observation". Location: `src/analyzer.py:_generate_character_profile()`.
- **Fix 2:** Added same filtering at relationship assignment point (~line 2131) to catch any "colleague" labels that bypass the primary filter.
- **Files modified:** `src/analyzer.py` (two locations)
- **Classification:** Post-processing filter (deterministic cleanup)
- **Universality:** Yes — "colleague" is always a vague non-relationship in any novel
- **Tests:** 332 passed, 10 skipped

## Attempt 4 Analysis Notes

### Pipeline Observations
- Analysis completed in 87m 7s (301 LLM calls, 643K tokens)
- 36 characters found (was 41 in attempt 3)
- Jay Gatsby now appears in main character summary with 268 mentions — Fix G may have worked
- **CRITICAL REGRESSION:** Narrator identified as "Henry C. Gatz" (Gatsby's father, appears only at end) instead of Nick Carraway
  - Pipeline output: "Narrator (from V2 pipeline): Henry C. Gatz" and "Confirmed narrator: Henry C. Gatz (first-person)"
  - Fix D (attempt 3) fixed this — but something in attempt 4 fixes caused it to regress
  - Henry C. Gatz has very few text mentions; Nick Carraway (34 shown) is the actual first-person narrator
- Nick Carraway shows only 34 mentions in summary (suspicious — he narrates the entire book)

### Output Files
- HTML: ../output/gatsby/report.html ✓
- JSON: ../output/gatsby/analysis.json ✓

## Next Action
Run PROMPT_evaluate.md to evaluate attempt 4 output.
