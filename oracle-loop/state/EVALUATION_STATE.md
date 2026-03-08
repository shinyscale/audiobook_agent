# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 14
- **Phase:** awaiting_fix
- **baseline_score:** 5.90

## Output Files
- HTML: ../output/gatsby/report.html
- JSON: ../output/gatsby/analysis.json
- Timestamped: output/gatsby_20260308_174827/

## Latest Scores
- Structure Detection: 10/10 ✓
- Character Extraction: 8/10 ✓
  - Completeness: 7.5/10 (George Wilson missing)
  - Identity Resolution: 9/10
  - Alias Grouping: 8.5/10
- Character Profiles: 7/10 ✗ (FAILING)
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 8.5/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 8.40/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (1 category below threshold: Character Profiles 7/10)

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
| 11 | 7.93 | +2.03 | Narrator guard overshot (Gatsby→Gatz instead of Nick). Wolfsheim dedup STILL broken. Fabricated rels reduced but not eliminated. |
| 12 | 7.68 | +1.78 | Narrator FIXED ✓ (Nick). But "Tom" F6 dup (191 mentions) newly identified. Wolfsheim STILL duplicated (5th failure). Fabricated rels persist (Gatsby↔Jordan spouse). |
| 13 | 8.40 | +2.50 | **BREAKTHROUGH**: Tom F6 dup FIXED ✓, Wolfsheim dedup FINALLY FIXED ✓. Character Extraction passes 8.0. Only Profiles (7/10) remains below threshold. |
| 14 | 8.40 | +2.50 | Fix MM (gender word-boundary) worked: Myrtle/Catherine gender correct. But "close friend" instead of "sister" (LLM variance). NEW fabrication: Gatsby↔Cody "romantic interest". Net: same score. |

## What Changed in Attempt 14

### Fix MM (`" man "` word-boundary in MALE_INDICATORS) — PARTIALLY EFFECTIVE
- Gender inference now works: Myrtle `gender: "female"` ✓, Catherine `gender: "female"` ✓, Tom `gender: null` (should be male but less critical)
- The "brother" label didn't appear this run — LLM generated "close friend" instead, so `enforce_gender_consistency` had nothing to correct
- Net: gender-wrong "brother" is gone (improvement), but "close friend" is still wrong (should be "sister")

### Previous fixes holding stable
- Narrator: Nick Carraway ✓ (4th consecutive stable attempt)
- Gatsby: main_cast protagonist with aliases James Gatz, Jay Gatsby ✓
- Daisy: aliases include Daisy Fay, Daisy Buchanan ✓
- Tom: alias "Tom" ✓, no F6 dup ✓
- Wolfsheim: single entry with alias "Meyer Wolfshiem" ✓

### NEW issues this run
- Gatsby→Dan Cody "romantic interest" — FABRICATED. Cody was Gatsby's mentor/employer, not romantic interest
- Dan Cody→Gatsby "romantic interest" — same fabrication, reciprocal
- Tom→Jordan Baker "romantic interest" — wrong (no romantic relationship)
- Tom→Catherine "romantic interest" — fabricated
- Tom→The Green Light "associated" — nonsensical relationship with a symbol

## Current Issues (Priority Order)

### HIGH

1. **Fabricated relationships: Gatsby↔Dan Cody "romantic interest"** [Profiles]
   - Problem: Gatsby and Dan Cody have a reciprocal "romantic interest" label. Cody was an elderly millionaire who employed young Gatsby as a personal assistant on his yacht. This is a mentor/employer relationship.
   - Evidence: The text says "James Gatz—that was really, or at least legally, his name... he was employed in a vague personal capacity" and Cody left him $25,000 in his will
   - Location: `src/analyzer.py` — `_generate_character_profile()` LLM hallucination
   - Fix: Post-processing relationship validation. A "romantic interest" label should require textual evidence (love/romance/attraction keywords near both names). Or: prune relationships where the characters never co-appear in the same chapter's active_characters.

2. **Fabricated relationships: Daisy↔Dan Cody "friend"** [Profiles]
   - Problem: Daisy and Dan Cody never interact. Cody dies years before Gatsby meets Daisy.
   - Same root cause as #1 — LLM invents relationships between characters in the same novel
   - Fix: Co-occurrence filter. If character A and B never appear in the same chapter's active_characters, remove the relationship (with exception for family relationships like Henry C. Gatz→Gatsby).

3. **Myrtle↔Catherine "close friend" should be "sister"** [Profiles]
   - Problem: Catherine is explicitly Myrtle's sister in the text. "close friend" is wrong.
   - Root cause: LLM generated "close friend" instead of "brother" this run. Gender fix (Fix MM) was correct but didn't get exercised because the wrong label was different.
   - Location: `src/pipeline/character_profiling/post_corrections.py`
   - Fix: Add a post-correction step: if the text explicitly calls character B "X's sister/brother/mother/father", override whatever label the LLM generated with the correct family label.

4. **Tom Buchanan fabricated romantic relationships** [Profiles]
   - Problem: Tom→Jordan Baker "romantic interest", Tom→Catherine "romantic interest" — neither is accurate
   - Evidence: Tom's only romantic relationships are with Daisy (wife) and Myrtle (affair)
   - Location: Same LLM hallucination pattern as #1
   - Fix: Same co-occurrence/evidence-based pruning approach

5. **Gatsby physical_description: null** [Profiles]
   - Problem: The text describes Gatsby: "an elegant young rough-neck, a year or two over thirty," "tanned skin," "one of those rare smiles with a quality of eternal reassurance"
   - Location: `src/analyzer.py` — `_generate_character_profile()`
   - Fix: LLM variance. The profiler should be extracting this. May need multiple LLM calls or a fallback search for descriptions near the character name.

### MEDIUM

6. **Myrtle's physical description confuses her with Catherine** [Profiles]
   - Problem: Profile states the text describes her with a "solid, sticky bob of red hair" and "complexion powdered milky white" but then notes these details actually refer to Catherine. The profiler recognized the error but didn't provide Myrtle's actual description ("faintly stout... carried her surplus flesh sensuously").
   - Location: `src/analyzer.py` profiler prompt

7. **Tom→The Green Light "associated"** [Profiles]
   - Problem: Tom has no meaningful connection to the green light symbol. This is Gatsby's symbol.
   - Low-impact but shows LLM is generating spurious cross-character relationships with symbolic entities.

8. **George Wilson missing from character list** [Completeness]
   - Problem: George Wilson (Myrtle's husband, runs the garage in the Valley of Ashes, kills Gatsby) is not extracted
   - He appears significantly in chapters 2, 7, 8, and 9
   - Note: This may be LLM variance between runs. Character extraction code did not change.
   - Location: Character extraction pipeline (V2)

9. **Tom Buchanan gender: null** [Profiles]
   - Problem: Tom is clearly male but gender wasn't inferred. Fix MM fixed word-boundary but Tom's text chunks may not contain "man" with spaces.
   - Low priority since Tom's relationships don't depend on gender correction.

### LOW

10. **Ch1 summary name duplication** [Summaries]
    - "The chapter opens with Nick Carraway, Nick Carraway, reflecting..." — canonical and alias both inserted.
    - Cosmetic issue.

11. **Dan Cody→Daisy "friend"** [Profiles]
    - Reciprocal of issue #2. Same fix applies.

12. **Doctor T. J. Eckleburg and The Green Light roles** [Characters]
    - Both listed as "protagonist" role — they're symbolic elements, not protagonists
    - Minor categorization issue, acceptable for narrator prep

## Fix Guidance for Attempt 15

**Focus ONLY on getting Character Profiles from 7/10 to 8/10.** All other categories pass.

The highest-impact fix is a **post-correction co-occurrence filter** for relationships:

**Approach: Prune fabricated relationships in `post_corrections.py`**
1. For each character's relationships, check if the related character appears in any of the same chapter's `active_characters` or `mentioned_characters` lists
2. If two characters NEVER co-appear in any chapter, remove the relationship UNLESS:
   - It's a family relationship (parent/child/sibling) — family bonds exist even without co-occurrence
   - The relationship was established by explicit textual evidence (names within N characters)
3. This would eliminate: Daisy↔Cody, and potentially Tom↔Green Light
4. For Gatsby↔Cody "romantic interest": they DO co-occur (Ch 6 Gatsby backstory), so co-occurrence alone won't fix this. Need to also validate "romantic interest" labels against textual evidence (love/romance/attraction keywords).

**Secondary fix: Sibling relationship detection**
- Scan text for "{Name}'s sister/brother" patterns
- Override LLM-generated labels with explicit sibling labels when found
- This fixes Myrtle↔Catherine regardless of what the LLM generates

**Tertiary: Gatsby physical description**
- The profiler already has the text. This is LLM variance. Consider a targeted re-prompt for characters with null physical_description.

Fixing issues 1-3 (fabricated relationships pruned + sibling detection) should push profiles to 8/10.

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

### Attempt 11 fixes
- **Fix EE: Max-mention narrator guard** — **OVERSHOT** (blocked Gatsby ✓ but fallback picked Gatz instead of Nick)
- **Fix FF: STEP 5.6.9 fuzzy Wolfsheim dedup** — **COMPLETELY INEFFECTIVE** (both entries still exist)

### Attempt 12 fixes
- **Fix GG: Chapter-spread narrator guard** — **EFFECTIVE ✓** (Gatz blocked, Nick correctly selected)
- **Fix HH: Heuristic narrator max-mention guard** — **EFFECTIVE ✓** (Nick selected over Gatsby)
- **Fix II: STEP 5.12 cross-cast alias dedup** — **COMPLETELY INEFFECTIVE** (Wolfsheim still duplicated)
- **Fix JJ: Shared single-word alias dedup** — **EFFECTIVE ✓** (Buchanan removed from both Tom and Daisy)

### Attempt 13 fixes
- **Fix KK: F6 single-word name component check** — **EFFECTIVE ✓** (Tom F6 dup eliminated)
- **Fix LL: Step 4.5.9 post-extraction word-subset dedup** — **EFFECTIVE ✓** (Wolfsheim FINALLY deduped after 7 attempts)

### Attempt 14 fixes
- **Fix MM: `" man "` word-boundary in MALE_INDICATORS** — **PARTIALLY EFFECTIVE** (gender inference correct, but LLM generated "close friend" instead of "brother" so gender-correction path not exercised)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 2 | False narrator (Eckleburg) | `src/agents/characters.py` (STEP 4.26 threshold) | No change — wrong layer |
| 2 | Gatsby wrong cast tier | `src/agents/characters.py` (STEP 5.11 new) | No change — code not firing |
| 2 | Relationship labels all "husband" | `src/pipeline/character_profiling/post_corrections.py` | Partial fix — main cast improved |
| 3 | False narrator | `src/pipeline/character_extraction_v2/narrator.py`, `src/agents/characters.py` | **FIXED** ✓ |
| 3 | "colleague" spam | `src/analyzer.py` (profiler prompt) | No change — LLM ignores forbidden list |
| 3 | Gatsby promotion diagnostic | `src/agents/characters.py` (STEP 5.11 logging) | No change — promotion still doesn't fire |
| 4 | Gatsby promotion safety net | `src/analyzer.py` (before Step 4.6) | Partially effective — Gatsby promoted but narrator regressed |
| 4 | "colleague" post-processing filter | `src/analyzer.py` (two locations) | **FAILED** — 198 "colleague" entries remain |
| 5 | Narrator mention guard | `src/pipeline/character_extraction_v2/narrator.py` | **FIXED** ✓ |
| 5 | Narrator fallback minimum | `src/agents/characters.py` (STEP 6.6) | **FIXED** ✓ |
| 5 | Colleague substring filter | `src/analyzer.py` (two locations) | **FAILED** — 192 "colleague" remain |
| 6 | Disable cooccurrence colleague injection | `src/pipeline/character_profiling/post_corrections.py` | **FIXED** ✓ (192→30) |
| 6 | Block " and " pair-reference aliases | `src/pipeline/character_extraction_v2/main_cast.py` | **FIXED** ✓ |
| 7 | NameError `_VAGUE_REL_LABELS` | `src/analyzer.py` | **FIXED** ✓ |
| 7 | Spouse evidence window | `src/pipeline/character_profiling/post_corrections.py` | Partial (47→23 spouse errors) |
| 7 | Speech patterns prompt | `src/analyzer.py` | **FAILED** — evaluator error |
| 7 | Wolfsheim alias absorption | `src/agents/characters.py` (STEP 5.6.9) | **FAILED** — still duplicated |
| 8 | Gatsby canonical rename | `src/analyzer.py` | **FIXED** ✓ |
| 8 | One-spouse invariant | `src/pipeline/character_profiling/post_corrections.py` | Partial (23→10, but 6 still wrong) |
| 8 | Colleague → associated | `src/pipeline/character_profiling/post_corrections.py` | **FIXED** ✓ |
| 8 | Second-pass alias absorption | `src/agents/characters.py` (STEP 5.9.9) | Partial (main entry fixed, 2 extras remain) |
| 9 | Green light / Owl Eyes split | `src/pipeline/character_extraction_v2/main_cast.py` | **FIXED** ✓ |
| 9 | Reciprocal spouse validation | `src/pipeline/character_profiling/post_corrections.py` | Partial (10→6 labels) |
| 9 | Fuzzy Wolfsheim dedup | `src/agents/characters.py` (STEP 5.9.9) | **FIXED** ✓ but REGRESSED |
| 9 | F6 proper-noun filter | `src/analyzer.py` | **FIXED** ✓ |
| 9 | Daisy Fay maiden-name match | `src/analyzer.py` | **FIXED** ✓ |
| 10 | Henry C. Gatz dedup | `src/agents/characters.py` | **FIXED** ✓ |
| 10 | Gatsby↔Jordan false spousal | `src/pipeline/character_profiling/post_corrections.py` | **FIXED** ✓ |
| 10 | Jordan duplicate alias | `src/agents/characters.py` | **FIXED** ✓ |
| 10 | Buchanans' house possessive alias | `src/pipeline/character_extraction_v2/main_cast.py` | **FIXED** ✓ |
| 11 | Narrator max-mention guard | `src/pipeline/character_extraction_v2/narrator.py` | **OVERSHOT** |
| 11 | Fuzzy Wolfsheim dedup STEP 5.6.9 | `src/agents/characters.py` | **COMPLETELY INEFFECTIVE** |
| 12 | Narrator chapter-spread guard | `src/agents/characters.py` | **FIXED** ✓ |
| 12 | Heuristic narrator max-mention guard | `src/agents/characters.py` | **FIXED** ✓ |
| 12 | STEP 5.12 cross-cast alias dedup | `src/agents/characters.py` | **COMPLETELY INEFFECTIVE** |
| 12 | Shared single-word alias dedup | `src/agents/characters.py` | **FIXED** ✓ |
| 13 | Tom F6 duplicate | `src/analyzer.py` | **FIXED** ✓ |
| 13 | Wolfsheim post-extraction dedup | `src/analyzer.py` | **FIXED** ✓ |
| 14 | Gender word-boundary (" man ") | `src/pipeline/character_profiling/post_corrections.py` | **PARTIALLY EFFECTIVE** — gender correct but LLM didn't generate "brother" this run |

## Configuration Audit
- Model: `qwen3-next:80b-a3b-instruct-q8_0` for all agents (think_mode: false)
- Context length: 32768 — adequate for Gatsby's chapter sizes
- Temperature: 0.7 — reasonable
- Zero LLM retries — no prompt/schema failures
- Mr. McKee still LOW CONFIDENCE (0.30) — JSON parse failure during profiling

## Next Action
Run PROMPT_fix.md to address fabricated relationships (co-occurrence pruning) and sibling detection in post_corrections.py
