# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 10
- **Phase:** awaiting_fix
- **baseline_score:** 5.90

## Output Files
- HTML: ../output/gatsby/report.html
- JSON: ../output/gatsby/analysis.json

## Latest Scores
- Structure Detection: 10/10 ✓
- Character Extraction: 7/10 ✗
  - Completeness: 8/10
  - Identity Resolution: 6/10
  - Alias Grouping: 7.5/10
- Character Profiles: 6/10 ✗
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 8.5/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 8.05/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold: Character Extraction 7/10, Character Profiles 6/10)

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
| 9 | 8.30 | +2.40 | Green/Owl split ✓, Wolfsheim dedup ✓, F6 clutter ✓, 4/6 wrong spouses fixed. Gatz dup and Gatsby↔Jordan remain. |
| 10 | 8.05 | +2.15 | Gatz dedup ✓, Gatsby↔Jordan spousal ✓, alias cleanup ✓. BUT narrator REGRESSED, Wolfsheim dup REGRESSED, 11 fabricated family rels. |

## What Changed in Attempt 10

### Fix AA (Gatz dedup — STEP 3.95b Pattern C/D guard) — EFFECTIVE ✓
- Henry C. Gatz is now a single entry (main_cast_8, 13 mentions). No more "Henry C. Gatz (the father)" split.

### Fix BB (Spousal text-evidence check) — EFFECTIVE ✓
- Gatsby↔Jordan false spousal is GONE. Jordan→Gatsby is now "facilitator" (correct).
- However, Meyer Wolfsheim→Gatsby "husband" appeared (NEW fabrication, not spousal evidence issue).

### Fix CC (Alias dedup) — EFFECTIVE ✓
- Jordan Baker aliases are now ["Jordan", "Baker"] — no duplicates.

### Fix DD (Possessive-reference blocker Rule 0.5c) — EFFECTIVE ✓
- "the Buchanans' house" is gone from Tom's aliases.

### REGRESSIONS
- **Narrator detection REGRESSED**: Jay Gatsby is marked as narrator (was Nick in attempt 9). This is the 3rd time narrator has broken (attempts 4, 10). The narrator fix pipeline is fragile.
- **Wolfsheim dedup REGRESSED**: main_cast_7 "Meyer Wolfsheim" (6 mentions) AND supporting_2 "Wolfshiem" (32 mentions) both exist. Fix X from attempt 9 didn't persist or the merge logic varies between runs.
- **11 fabricated family relationships appeared**: Gatsby→Catherine "brother", Gatsby→Wilson "brother", Gatsby→Michaelis "brother", Gatsby→McKee "nephew", Gatsby→Wolfsheim "husband", Wilson→Gatsby "sister", Catherine→Gatsby "sister", Michaelis→Gatsby "brother", McKee→Gatsby "nephew", Wolfsheim→Gatsby "husband". These are complete fabrications — likely LLM variance in profiler output.

## Current Issues (Priority Order)

### CRITICAL

1. **Narrator REGRESSION: Gatsby tagged as narrator instead of Nick** [Profiles, Summaries]
   - Problem: main_cast_1 "Jay Gatsby" has `is_narrator: true`, main_cast_0 "Nick" has `is_narrator: false`. Nick Carraway is the first-person narrator.
   - Impact: Ch1 summary opens "The chapter opens with Jay Gatsby, Nick Carraway" — conflating the two. Profile generation uses wrong narrator context.
   - This has regressed 3 times (attempts 4, 10). The narrator detection pipeline is unreliable.
   - Location: `src/pipeline/character_extraction_v2/narrator.py`, `src/agents/characters.py` (STEP 6.6)
   - Fix: The narrator pipeline needs a harder constraint. For first-person narratives, the narrator should be the character whose mentions are predominantly in self-referential contexts ("I", "my"), NOT the most-mentioned character. Gatsby has 264 mentions (most in third person) vs Nick 34 mentions. A robust fix: if narrative is first-person and the highest-mention character is referred to in third person in the text (not "I"), they cannot be narrator.

2. **11 fabricated family relationships on Gatsby** [Profiles]
   - Problem: Gatsby is labeled "brother" to Catherine, Wilson, Michaelis; "nephew" to McKee; "husband" to Meyer Wolfsheim. All fabricated.
   - Reciprocal fabrications exist: Wilson→Gatsby "sister", Catherine→Gatsby "sister", etc.
   - Root cause: LLM hallucination during profiling. The one-spouse invariant (Fix S) doesn't catch "brother"/"sister"/"nephew" labels.
   - Location: `src/pipeline/character_profiling/post_corrections.py` or `src/analyzer.py`
   - Fix: Add a **kinship plausibility filter** in post-corrections: for "brother"/"sister"/"nephew"/"uncle" labels, verify that both characters share at least one chapter where they are explicitly described in family terms. Alternatively, block family labels between characters that are not in each other's "mentioned_characters" in family context. Simpler: build a whitelist of VERIFIED family pairs from the text (e.g., Catherine↔Myrtle "sister" appears in text) and reject all other family labels.

### HIGH

3. **Wolfsheim STILL duplicated** [Identity Resolution]
   - Problem: main_cast_7 "Meyer Wolfsheim" (6 mentions) AND supporting_2 "Wolfshiem" (32 mentions). Same person, spelling variant.
   - Fix X from attempt 9 was supposedly effective but didn't persist. The fuzzy dedup may be order-dependent or has a race condition.
   - Location: `src/agents/characters.py` (STEP 5.9.9 or wherever fuzzy dedup runs)
   - Fix: The dedup should normalize "Wolfsheim"/"Wolfshiem" variants. Add edit-distance or phonetic matching that catches single-letter transpositions (ie→ei). The main_cast entry has 6 mentions and supporting has 32 — they must be merged with the 32-mention entry absorbing the 6-mention one.

4. **James Gatz not merged with Jay Gatsby** [Identity Resolution]
   - Problem: F6 entry cbff004f6102 "James Gatz" (4 mentions) exists separately from main_cast_1 "Jay Gatsby". James Gatz is Gatsby's birth name (revealed in Ch6/9).
   - Gatsby already has relationship "James Gatz: previous identity" which confirms they're the same person.
   - Location: `src/analyzer.py` (F6 reconciliation) or post-extraction merge
   - Fix: When F6 adds a character whose name appears in an existing character's relationships with a label like "previous identity", "birth name", "alias", or "alter ego" — merge instead of adding separately. Alternatively, "James Gatz" should match via surname "Gatz" to Henry C. Gatz's alias entry — but actually "Gatz" is Gatsby's original surname, not Henry's exclusive.

5. **"Buchanan" shared alias on both Tom and Daisy** [Alias Grouping]
   - Problem: Both main_cast_2 (Daisy) and main_cast_3 (Tom Buchanan) have "Buchanan" as alias.
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` or `src/agents/characters.py`
   - Fix: If a surname-only alias appears on 2+ characters, remove it from all of them. "Buchanan" alone is ambiguous in Gatsby.

### MEDIUM

6. **Fabricated relationships on Daisy** [Profiles]
   - Daisy→Dan Cody "friend" — FABRICATED (they never meet; Cody dies years before Gatsby meets Daisy)
   - Daisy→Myrtle "romantic interest" — WRONG (no romantic connection)
   - Daisy→Wolfshiem "friend" — FABRICATED (they never interact)
   - Location: `src/analyzer.py` profiler or `src/pipeline/character_profiling/post_corrections.py`

7. **Missing physical descriptions for Nick and Myrtle** [Profiles]
   - Nick: described as "a young man from Minnesota" with various contextual details
   - Myrtle: "middle thirties, faintly stout, carried her surplus flesh sensuously" — explicit description in text but not captured
   - Location: `src/analyzer.py` profiler context or prompting

8. **Doctor Eckleburg and Green Light labeled "protagonist"/"supporting"** [Character Extraction]
   - These are symbolic entities. Minor impact — doesn't affect narrator preparation significantly.

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

### Attempt 9 fixes
- **Fix V: Rule 0.5b person/non-person mismatch** — **EFFECTIVE ✓** (green light and Owl Eyes separated)
- **Fix W: Reciprocal spouse validation** — **PARTIALLY EFFECTIVE** (10→6 spousal labels; 4 removed, but Gatsby↔Jordan and Myrtle gender wrong persist)
- **Fix X: Fuzzy Wolfsheim dedup** — **EFFECTIVE ✓** (3 entries → 1) — BUT REGRESSED in attempt 10
- **Fix Y: F6 proper-noun filter** — **EFFECTIVE ✓** (6 clutter entries removed)
- **Fix Z: Daisy Fay maiden-name match** — **EFFECTIVE ✓** (Daisy Fay → alias of Daisy)

### Attempt 10 fixes
- **Fix AA: STEP 3.95b Pattern C/D guard** — **EFFECTIVE ✓** (Henry C. Gatz dedup)
- **Fix BB: Spousal text-evidence check** — **EFFECTIVE ✓** (Gatsby↔Jordan spousal removed)
- **Fix CC: Alias dedup** — **EFFECTIVE ✓** (Jordan duplicate alias removed)
- **Fix DD: Possessive-reference blocker Rule 0.5c** — **EFFECTIVE ✓** (Buchanans' house removed)

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
| 9 | Green light / Owl Eyes split | `src/pipeline/character_extraction_v2/main_cast.py` | **FIXED** ✓ |
| 9 | Reciprocal spouse validation | `src/pipeline/character_profiling/post_corrections.py` | Partial (10→6 labels; 4 removed) |
| 9 | Fuzzy Wolfsheim dedup | `src/agents/characters.py` (STEP 5.9.9) | **FIXED** ✓ but REGRESSED in attempt 10 |
| 9 | F6 proper-noun filter | `src/analyzer.py` | **FIXED** ✓ |
| 9 | Daisy Fay maiden-name match | `src/analyzer.py` | **FIXED** ✓ |
| 10 | Henry C. Gatz dedup | `src/agents/characters.py` | **FIXED** ✓ |
| 10 | Gatsby↔Jordan false spousal | `src/pipeline/character_profiling/post_corrections.py` | **FIXED** ✓ |
| 10 | Jordan duplicate alias | `src/agents/characters.py` | **FIXED** ✓ |
| 10 | Buchanans' house possessive alias | `src/pipeline/character_extraction_v2/main_cast.py` | **FIXED** ✓ |

## Configuration Audit
- Model: `qwen3-next:80b-a3b-instruct-q8_0` for all agents (think_mode: false)
- Context length: 32768 — adequate for Gatsby's chapter sizes
- Temperature: 0.7 — reasonable
- Zero LLM retries — no prompt/schema failures

## Priority Fix Order for Attempt 11

**The two blocking categories are Character Extraction (7/10) and Profiles (6/10).**

### Profiles (6 → 8+) — HIGHEST PRIORITY

1. **Fix narrator regression** — The narrator keeps breaking. Need a ROBUST fix that survives LLM variance. The current narrator detection assigns narrator to high-mention characters. For Gatsby, the highest-mention character IS Gatsby (264 mentions) but he's referred to in third person. Nick (34 mentions) is the actual first-person narrator. Fix approach: in narrator.py, add a hard check — if narrative is first-person and the candidate narrator is referenced overwhelmingly in third person in the text, reject them. Only accept a narrator whose text references include first-person pronouns near their name.

2. **Fix fabricated family relationships** — 11 fabricated "brother"/"sister"/"nephew"/"husband" labels. Add a post-correction kinship filter: for any family label (brother, sister, nephew, uncle, cousin, husband, wife, parent, child, son, daughter), verify the label appears in source text near both character names. If no textual evidence, downgrade to "associated".

### Character Extraction (7 → 8+)

3. **Fix Wolfsheim duplication** — This needs a more robust approach. The spelling variants "Wolfsheim"/"Wolfshiem" (ei↔ie transposition) should be caught by edit-distance matching. Ensure the dedup runs on BOTH main_cast and supporting_cast entries, not just within one tier.

4. **Merge James Gatz into Jay Gatsby** — F6 should check existing character relationships for "previous identity"/"birth name" labels before creating new entries. Or add "James Gatz" as a known alias of Gatsby when the relationship exists.

5. **Remove shared "Buchanan" alias** — When a surname-only alias appears on 2+ characters, remove from all.

## Next Action
Run PROMPT_fix.md to address narrator regression (Critical #1) and fabricated relationships (Critical #2) as top priorities.
