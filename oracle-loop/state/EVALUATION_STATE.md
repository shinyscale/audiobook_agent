# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 16
- **Phase:** awaiting_fix
- **baseline_score:** 5.90

## Output Files
- HTML: ../output/gatsby/report.html
- JSON: ../output/gatsby/analysis.json
- Timestamped: output/gatsby_20260308_210438/

## Latest Scores
- Structure Detection: 10/10 ✓
- Character Extraction: 8/10 ✓
  - Completeness: 7.5/10 (George Wilson still missing)
  - Identity Resolution: 9/10
  - Alias Grouping: 7.5/10 (Tom has "the Buchanans' house" alias; Gatsby missing "James Gatz")
- Character Profiles: 7.5/10 ✗ (FAILING)
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 8.5/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 8.53/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (1 category below threshold: Character Profiles 7.5/10)

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
| 15 | 8.53 | +2.63 | Fix NN/OO/PP effective: Cody↔Gatsby "mentor/protégé" ✓, Catherine→Myrtle "sister" ✓, Tom→Catherine romantic GONE ✓. But NEW: Gatsby↔Tom "husband" fabricated. Profiles 7→7.5. |
| 16 | 8.53 | +2.63 | Fix QQ effective (same-gender guard): Gatsby↔Tom "husband" GONE ✓. But spousal label SHIFTED to Gatsby↔Daisy "husband"/"wife" — wrong pair. Net: no change. |

## What Changed in Attempt 16

### Fix QQ (same-gender spousal guard) — EFFECTIVE ✓
- Gatsby↔Tom "husband" → "associated" (blocked: both gender=male)
- Same-gender spousal guard works correctly

### Fix RR (_propagate_missing_reverses overwrites generics) — PARTIALLY EFFECTIVE
- Catherine→Myrtle "sister" persists ✓
- BUT Myrtle→Catherine still "associated" — propagation didn't fire for this pair
- Unclear why: possibly the reverse relationship already existed as "associated" and RR didn't overwrite

### NEW issues this run
- **Gatsby→Daisy "husband"** — FABRICATED. Gatsby is NOT Daisy's husband; Tom is. Gatsby is Daisy's lover/romantic interest. The spousal label shifted from the Gatsby↔Tom pair (blocked by Fix QQ) to the Gatsby↔Daisy pair (not blocked because they're different genders).
- **Daisy→Gatsby "wife"** — same fabrication, reciprocal
- **Tom↔Daisy "associated"** — WRONG. They ARE married. The actual husband-wife pair gets "associated" while the wrong pair gets "husband"/"wife".
- **Dan Cody→Daisy "friend"** — FABRICATED. Dan Cody died before Gatsby met Daisy.
- **Wolfshiem→{Tom, Jordan, Daisy, Nick} "friend"** — FABRICATED. Wolfshiem interacts only with Gatsby (and briefly Nick at the funeral).
- **Tom→green light "associated"** — Nonsensical.

### Root Cause Analysis: Spousal Label Whack-a-Mole

The same "husband"/"wife" fabrication has now appeared on THREE different character pairs across attempts:
- Attempt 8-12: Various characters labeled "husband"/"wife" (47→23→10→6)
- Attempt 15: Gatsby↔Tom "husband" (fixed by QQ in attempt 16)
- Attempt 16: Gatsby↔Daisy "husband"/"wife" (NEW)

The pattern: the LLM profiler or `_infer_rel`/`verify_relationships_from_text` detects "husband" in text windows containing Gatsby+Daisy. But "husband" in those windows refers to TOM ("her husband"), not Gatsby. Blocking the label on one pair just shifts it to another.

**The fix must address the ROOT CAUSE:** text-window spousal detection doesn't distinguish WHO the spousal term refers to when a third character is the actual referent.

## Current Issues (Priority Order)

### HIGH

1. **Gatsby→Daisy "husband" / Daisy→Gatsby "wife" — WRONG** [Profiles]
   - Problem: Gatsby is labeled as Daisy's husband. In the novel, TOM is Daisy's husband. Gatsby is her former lover and current romantic interest.
   - Root cause: Text windows with Gatsby+Daisy mentions contain "her husband" (referring to Tom). `_infer_rel` or the LLM profiler attributes the "husband" label to Gatsby instead of Tom.
   - Location: `src/pipeline/character_profiling/post_corrections.py` — `verify_relationships_from_text` and/or `_infer_rel`
   - Fix approach: **Third-party spousal attribution check.** When "husband"/"wife" is found in a text window between characters A and B, check if a THIRD character's name also appears in the same window near the spousal term. If "her husband" is followed by/preceded by "Tom" (or any other character name), attribute the spousal relationship to Tom↔Daisy instead of Gatsby↔Daisy. This is universal: "her husband [NAME]" should attribute to [NAME], not the other character in the window.

2. **Tom↔Daisy "associated" — should be "husband"/"wife"** [Profiles]
   - Problem: The novel's central married couple gets a vague "associated" label
   - Evidence: "her husband" appears dozens of times near Tom+Daisy co-mentions
   - Location: Same as above — if fix #1 correctly attributes "husband" to Tom↔Daisy instead of Gatsby↔Daisy, this resolves automatically
   - Fix: Ensure `verify_relationships_from_text` checks Tom↔Daisy windows and finds strong "husband"/"wife" evidence

3. **Myrtle→Catherine still "associated" (should be "sister")** [Profiles]
   - Problem: Fix RR was supposed to propagate Catherine→Myrtle "sister" to the reverse, but didn't
   - Evidence: Catherine→Myrtle correctly shows "sister", but Myrtle→Catherine shows "associated"
   - Location: `src/pipeline/character_profiling/post_corrections.py` — `_propagate_missing_reverses`
   - Fix: Debug why propagation didn't fire. Likely the reverse relationship already existed as "associated" and the function doesn't overwrite existing labels. Must overwrite generic labels ("associated") with specific ones ("sister").

### MEDIUM

4. **Fabricated Wolfshiem friendships** [Profiles]
   - Problem: Wolfshiem→Tom "friend", Wolfshiem→Jordan "friend", Wolfshiem→Daisy "friend", Wolfshiem→Nick "friend" — none of these interactions exist in the text (except brief Nick encounter)
   - Location: LLM profiler generates these; `verify_relationships_from_text` should catch and remove unsupported labels
   - Low individual impact but contributes to overall profile noise

5. **Dan Cody→Daisy "friend"** [Profiles]
   - Problem: Dan Cody died years before Gatsby met Daisy. They cannot be friends.
   - Location: LLM profiler fabrication
   - Low individual impact

6. **Nick and Gatsby physical_description: null** [Profiles]
   - Problem: Two protagonists lack physical descriptions. Gatsby is described in the text.
   - Location: LLM variance in `_generate_character_profile()`

7. **Tom alias "the Buchanans' house"** [Alias Grouping]
   - Problem: Possessive building reference incorrectly grouped as Tom's alias
   - Note: Fix DD was supposed to block this; likely LLM variance re-introduced it

### LOW

8. **Gatsby missing "James Gatz" alias** [Alias Grouping]
   - LLM variance (was present in attempt 14, absent in 15-16)

9. **George Wilson missing from character list** [Completeness]
   - LLM variance in extraction — mentioned in summaries but not extracted as character

## Fix Guidance for Attempt 17

**Focus ONLY on getting Character Profiles from 7.5/10 to 8/10.** All other categories pass.

**The spousal label has now shifted across 3 different pairs over multiple attempts. Targeted blocks (same-gender guard, one-spouse invariant) just move the problem. The fix must address the ROOT CAUSE.**

**Fix 1 (CRITICAL): Third-party spousal attribution in `verify_relationships_from_text`**
When checking a text window between characters A and B and finding a spousal keyword ("husband", "wife", "spouse"):
1. Check if ANY other character's name appears in the same window within ~30 chars of the spousal keyword
2. If yes (e.g., "her husband Tom" in a Gatsby+Daisy window), attribute the spousal relationship to that third character + the relevant party, NOT to A↔B
3. If no third character, proceed with normal attribution to A↔B
4. This is universal: disambiguates possessive spousal references across all texts

**Fix 2 (HIGH): Debug and fix `_propagate_missing_reverses` for Myrtle→Catherine**
- Catherine→Myrtle = "sister" but Myrtle→Catherine = "associated"
- The propagation function should overwrite "associated" with "sister" (specific > generic)
- Check if the function skips when a reverse relationship already exists, even if it's a vague label
- Fix: only skip propagation if the existing reverse label is SPECIFIC (not "associated"/"unknown"/"acquaintance")

**Fix 3 (MEDIUM): If Fix 1 correctly attributes "husband" to Tom↔Daisy, verify the one-spouse invariant doesn't then REMOVE it**
- The one-spouse invariant from Fix S (attempt 8) may conflict if Gatsby↔Daisy still has "husband" from LLM
- Ensure ordering: verify_relationships_from_text runs FIRST (corrects attribution), THEN one-spouse invariant cleans up any remaining duplicates

Fixing #1 and #2 removes 2 fabricated labels (Gatsby↔Daisy "husband"/"wife"), adds 2 correct labels (Tom↔Daisy "husband"/"wife"), and adds 1 correct label (Myrtle→Catherine "sister"). That's a net improvement of +5 correct relationship entries, which should push profiles to 8/10.

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

### Attempt 15 fixes
- **Fix NN: Word-boundary matching in `_infer_rel`** — **EFFECTIVE ✓** (Gatsby↔Cody "romantic interest" → "mentor"/"protégé")
- **Fix OO: Tighter romantic keyword window** — **EFFECTIVE ✓** (Tom→Jordan/Catherine "romantic interest" eliminated)
- **Fix PP: Strong family evidence override** — **EFFECTIVE ✓** (Catherine→Myrtle "sister" ✓, but reciprocal missing)

### Attempt 16 fixes
- **Fix QQ: Same-gender spousal guard in `_enforce_one_spouse_invariant`** — **EFFECTIVE ✓** (Gatsby↔Tom "husband" blocked)
- **Fix RR: `_propagate_missing_reverses` overwrites generic labels** — **PARTIALLY EFFECTIVE** (Myrtle→Catherine still "associated")

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
| 14 | Gender word-boundary (" man ") | `src/pipeline/character_profiling/post_corrections.py` | **PARTIALLY EFFECTIVE** |
| 15 | Word-boundary in _infer_rel | `src/pipeline/character_profiling/post_corrections.py` | **EFFECTIVE** ✓ (Cody↔Gatsby romantic → mentor) |
| 15 | Tighter romantic keyword window | `src/pipeline/character_profiling/post_corrections.py` | **EFFECTIVE** ✓ (Tom romantic false positives removed) |
| 15 | Strong family evidence override | `src/pipeline/character_profiling/post_corrections.py` | **EFFECTIVE** ✓ (Catherine→Myrtle "sister", but no reciprocal) |
| 16 | Same-gender spousal guard | `src/pipeline/character_profiling/post_corrections.py` | **EFFECTIVE** ✓ (Gatsby↔Tom "husband" blocked) |
| 16 | _propagate_missing_reverses overwrites generics | `src/pipeline/character_profiling/post_corrections.py` | **PARTIALLY EFFECTIVE** (reciprocal still missing for Myrtle→Catherine) |

## Configuration Audit
- Model: `qwen3-next:80b-a3b-instruct-q8_0` for all agents (think_mode: false)
- Context length: 32768 — adequate for Gatsby's chapter sizes
- Temperature: 0.7 — reasonable
- Zero LLM retries — no prompt/schema failures
- Mr. McKee still LOW CONFIDENCE (0.30) — JSON parse failure during profiling

## Next Action
Run PROMPT_fix.md to address spousal attribution root cause (Fix 1: third-party spousal attribution) and reciprocal propagation (Fix 2).
