# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 7
- **Phase:** awaiting_analysis
- **baseline_score:** 6.55
- **Competitive Mode:** single

## Output Files
- HTML: ../output/gatsby/report.html
- JSON: ../output/gatsby/analysis.json

## Pipeline Notes (Attempt 7)
- Completed in 87m 1s, 298 LLM calls, 449,366 tokens
- 9 chapters detected, 19 characters extracted, 130 pronunciation entries
- Jay Gatsby now canonical name (not James Gatz) ✓
- Nick Carraway narrator confirmed ✓ (first-person)
- Fix R SUCCESS: ALL hallucinated familial labels removed ✓
- Fix S PARTIAL: Myrtle still has Catherine's "red bob" contamination — `clean_unknown_appearance()` didn't catch it because the description doesn't contain "not directly described" phrasing
- Fix T PARTIAL: Gatsby got a physical description ✓, but Daisy still null — fallback didn't find her descriptions

## Latest Scores
- Structure Detection: 10/10 ✓
- Character Extraction: 8.5/10 ✓
  - Completeness: 8/10
  - Identity Resolution: 9/10
  - Alias Grouping: 8/10
- Character Profiles: 7.5/10 ✗ (FAILING) ← sole remaining blocker
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 8.5/10 ✓
- HTML Presentation: 9/10 ✓
- **Overall: 8.80/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (1 category below threshold: Profiles 7.5)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.55 | — | Baseline. main_cast pipeline failed; massive false splits; profiles catastrophically wrong |
| 2 | 7.15 | +0.60 | Fix A partially worked (Gatsby aliases resolved); main_cast STILL fails; IPA corruption fixed |
| 3 | 7.93 | +1.38 | Main cast pipeline FIXED (Fix C). 5 false splits resolved. Profiles still wrong. |
| 4 | 7.98 | +1.43 | Fixes G/H/I/J: Eckleburg deduped ✓, "like" removed ✓, Nick rels→unknown (marginal), profiles STILL primary blocker |
| 5 | 7.83 | +1.28 | Fixes K/L/M all SUCCESS ✓. LLM variance regressions: Ella Kaye narrator, Gatz name. Core blockers unchanged. |
| 6 | 8.43 | +1.88 | Fix N ✓ (Nick merged+narrator), Fix P ✓ (traits/speech populated), Fix Q ✓ (homograph IPA). Fix O partial (familial labels persist). Profiles sole remaining blocker. |
| 7 | 8.80 | +2.25 | Fix R ✓ (ALL wrong familial labels removed!). Fix S partial (Myrtle still contaminated). Fix T partial (Gatsby desc ✓, Daisy still null). Profiles STILL sole blocker at 7.5. |

## What Changed in Attempt 7

### Fix Results
- **Fix R (Familial labels Option B):** SUCCESS ✓ — `reject_unfounded_familial_labels()` now correctly removes all familial labels between non-surname-sharing pairs. ALL 11 wrong familial labels from attempt 6 are gone. Correct labels survive: Tom↔Daisy husband/wife ✓, Myrtle→George wife ✓, Catherine↔Myrtle sister ✓, Henry C. Gatz→Jay Gatsby parent ✓, Rosy→Wolfsheim close friend ✓.
- **Fix S (Self-negating appearance):** PARTIAL — `clean_unknown_appearance()` targets "not directly described" phrasing, but Myrtle's contaminated description doesn't contain that phrase. The description says "has a red bob of hair (as described by her sister Catherine)" — it's not self-negating, it's cross-contaminated with Catherine's features while acknowledging the source.
- **Fix T (Physical description fallback):** PARTIAL — `propagate_physical_description()` successfully found Gatsby's description ("elegant young roughneck; wears a pink suit") but failed to find Daisy's. Daisy's text descriptions use different patterns: "face was sad and lovely with bright things in it" — the word "face" + adjectives may not match the physical-term detection patterns.

### Issue Resolution from Attempt 6
- Hallucinated familial labels: **FIXED** ✓ (Fix R — 0 wrong labels now, was 11)
- Gatsby physical description null: **FIXED** ✓ (Fix T — now has description)
- Gatsby canonical name "James Gatz": **FIXED** ✓ (now "Jay Gatsby" with "James Gatz" as alias)
- Wolfsheim "old sport": **FIXED** ✓ (no longer in speech patterns)
- Gatsby misattributed quote: **FIXED** ✓ (example quotes all correct)
- Daisy physical description null: **UNCHANGED** — Fix T fallback didn't match
- Myrtle physical description contaminated: **UNCHANGED** — Fix S didn't catch non-self-negating contamination
- Owl Eyes missing: **UNCHANGED** — still not in character list (mentioned in Ch 9 summary though)

## Current Issues (Priority Order)

### CRITICAL

1. **Daisy Buchanan has null physical description** [Profiles]
   - Problem: Daisy (main_cast_2, 208 mentions, central female character) has `physical_description: null`
   - Expected: "face was sad and lovely with bright things in it, bright eyes and a bright passionate mouth" (Ch 1), white dress imagery, voice described extensively
   - Why Fix T missed it: `propagate_physical_description()` scans for physical-term sentences near character mentions, but Daisy's descriptions use "face" + adjectives, "eyes", "mouth" which may not be in the physical-term set, or the pattern matching missed the "sad and lovely" phrasing
   - Location: `src/pipeline/character_profiling/post_corrections.py` — `propagate_physical_description()`
   - Fix: Expand the physical-term vocabulary in `propagate_physical_description()` to include face-related terms (face, eyes, mouth, lips, hair, smile, voice, complexion, skin) and adjective-rich descriptive patterns. Also check if "Daisy" name matching is failing — the function may only check `canonical_name` but text uses "Daisy" not "Daisy Buchanan"
   - Impact: +0.3 to Profiles (from 7.5 to ~7.8)

### HIGH

2. **Myrtle's physical description contaminated with Catherine's features** [Profiles]
   - Problem: Myrtle's `physical_description` says "has a red bob of hair (as described by her sister Catherine)" — the red bob is CATHERINE's, not Myrtle's
   - Myrtle's actual description: "thickish figure," "middle thirties, faintly stout," "she carried her surplus flesh sensuously," "immediately perceptible vitality"
   - Why Fix S missed it: `clean_unknown_appearance()` looks for "not directly described" phrases. This description doesn't negate itself — it positively attributes Catherine's features to Myrtle.
   - Location: `src/pipeline/character_profiling/post_corrections.py`
   - Fix: Add cross-contamination detection — if a character's `physical_description` mentions another character's canonical_name or aliases by name, clear it and let `propagate_physical_description()` rescan. Regex check: if description contains any other character's name (case-insensitive), mark it as contaminated.
   - Impact: +0.1 to Profiles (from ~7.8 to ~7.9)

3. **Jay Gatsby (protagonist) has ZERO relationships** [Profiles]
   - Problem: Jay Gatsby (main_cast_1, 271 mentions) has `relationships: {}` — completely empty
   - Expected at minimum: Daisy Buchanan (obsession/former lover), Nick Carraway (friend/neighbor), Tom Buchanan (rival), Wolfsheim (associate/mentor), Dan Cody (former employer/mentor)
   - Why: Fix R correctly removed wrong familial labels, but the LLM didn't generate non-familial labels for Gatsby either. The aggressive cleanup left him with nothing.
   - Location: `src/pipeline/character_profiling/post_corrections.py`
   - Fix: After `reject_unfounded_familial_labels()` runs, add a safety check: for characters with >100 mentions who end up with ZERO relationships, generate minimal "associated" relationships from co-occurrence data. Any character pair where both have >50 mentions and appear in >3 common chapters should get an "associated" or "connected" relationship label.
   - Impact: +0.15 to Profiles (from ~7.9 to ~8.05)

### MEDIUM

4. **Jordan Baker has ZERO relationships** [Profiles]
   - Problem: Jordan (main_cast_4, 101 mentions) has `relationships: {}` — completely empty
   - Expected: Daisy (close friend), Nick (love interest), Tom/Gatsby (acquaintance)
   - Same root cause as issue #3 — LLM didn't generate, and no post-processing backfill
   - Would be addressed by the same co-occurrence fix as issue #3

5. **Eckleburg has 5 inappropriate "acquaintance" relationships** [Profiles]
   - Problem: Doctor T. J. Eckleburg (a billboard/symbol) has relationships with George Wilson, Michaelis, Myrtle, Tom, and Nick — all labeled "acquaintance"
   - A billboard can't be acquainted with people. Should have 0 or at most George Wilson (symbolic connection: "God sees everything")
   - Location: `src/pipeline/character_profiling/post_corrections.py`
   - Fix: LOW priority — doesn't significantly impact narrator prep. Could add a filter for symbolic/inanimate entities, but not worth the complexity for 0.05 points.

6. **Butler→Jordan relationship labeled "employee" is wrong** [Profiles]
   - Problem: The butler's relationship to Jordan Baker is "employee" (meaning "Jordan is my employee"). The butler works for Gatsby, not Jordan.
   - Minor — doesn't significantly mislead narrator

7. **Duplicate "Daisy" in Daisy's alias list** [Alias Grouping]
   - Daisy Buchanan's aliases: `["Daisy", "Daisy", "Buchanan"]` — "Daisy" appears twice

8. **66/130 pronunciations still "unknown" category** [Pronunciation]
   - Many are classifiable: "contralto" (musical term), "gonnegtion" (dialect), "murmurous" (literary), "gaiety" (archaic). 51% unknown.
   - Quality of entries is good (all have IPA, notes, context), just miscategorized.

### LOW

9. **Owl Eyes still missing from character list** [Completeness]
   - The owl-eyed man from Gatsby's library (Ch 3, Ch 9 funeral) not extracted. Mentioned in Ch 9 summary as "the man with owl-eyed glasses."
   - Narratively significant but minor character. Pipeline filters by mention count.

10. **Gatsby's physical description includes speech description** [Profiles]
    - "Elaborate formality of speech; elegant young roughneck; wears a pink suit" — the first clause is about speech, not appearance.
    - Minor — still captures key visual details.

## Configuration Audit

### Model Configuration
- Model: qwen3-next:80b-a3b-instruct-q8_0 (Ollama) — same model for all agents
- Context length: 32768 — adequate for Gatsby
- Temperature: 0.7 — acceptable for most tasks
- think_mode: false

### Processing Issues
- 298 LLM calls, 0 retries — mechanically stable
- Profile generation producing rich personality/voice data (17/19 traits, 15/19 speech patterns)
- Relationship extraction remains the weak point — LLM generates sparse non-familial labels even when familial labels are correctly filtered
- Physical description fallback (Fix T) works for some characters but misses face/feature-based descriptions

### Recommendation
- HIGH: Expand physical-term vocabulary in `propagate_physical_description()` for Daisy
- HIGH: Add cross-contamination detection for physical descriptions
- MEDIUM: Add co-occurrence-based relationship backfill for major characters with zero relationships

## Fix History

### gatsby — Attempt 2 Fixes
**Fix A: Include `characters_present` in summaries for main_cast LLM extraction** [CRITICAL] — PARTIAL
**Fix B: IPA validation to reject corrupt entries** [MEDIUM] — SUCCESS ✓

### gatsby — Attempt 3 Fixes
**Fix C: Main cast prompts changed to dict wrapper format** [CRITICAL] — SUCCESS ✓
**Fix D: Secondary relationship call no longer overwrites primary** [CRITICAL] — PARTIAL
**Fix E: Pronunciation false positive exclusions** [MEDIUM] — SUCCESS ✓
**Fix F: UNKNOWN → PROPER_NOUN reclassification** [MEDIUM] — PARTIAL

### gatsby — Attempt 4 Fixes
**Fix G: Relationship prompt — replace familial examples with social ones** [CRITICAL] — PARTIAL (Nick improved, others unchanged)
**Fix H: Physical description validation** [HIGH] — FAILED (narrator injection overwrites after validation)
**Fix I: Eckleburg duplicate — reverse title check** [HIGH] — SUCCESS ✓
**Fix J: "like" pronunciation exception** [LOW] — SUCCESS ✓

### gatsby — Attempt 5 Fixes
**Fix K: Butler/Butler F6 case dedup** [HIGH] — SUCCESS ✓ (src/analyzer.py)
**Fix L: Remove "unknown" relationships** [CRITICAL] — SUCCESS ✓ (src/pipeline/character_profiling/post_corrections.py)
**Fix M: Narrator appearance prose filter** [HIGH] — SUCCESS ✓ (src/pipeline/character_profiling/post_corrections.py)

### gatsby — Attempt 6 Fixes
**Fix N: Nick/Carraway merge + narrator** [CRITICAL] — SUCCESS ✓ (src/agents/characters.py)
**Fix O: Familial label validation** [CRITICAL] — PARTIAL (src/pipeline/character_profiling/post_corrections.py — code runs, but 100-char window too permissive, many wrong labels survive)
**Fix P: Personality traits + speech patterns** [CRITICAL] — SUCCESS ✓ (src/analyzer.py — data in personality/voice_guidance nested dicts)
**Fix Q: Homograph IPA** [HIGH] — SUCCESS ✓ (src/pipeline/pronunciation_guide/enricher.py)

### gatsby — Attempt 7 Fixes
**Fix R: Familial labels Option B** [CRITICAL] — SUCCESS ✓ (src/pipeline/character_profiling/post_corrections.py — all wrong familial labels removed)
**Fix S: Self-negating appearance summary** [HIGH] — PARTIAL (src/pipeline/character_profiling/post_corrections.py — catches "not directly described" but not cross-character contamination)
**Fix T: Deterministic physical description fallback** [HIGH] — PARTIAL (src/pipeline/character_profiling/post_corrections.py — found Gatsby's description, missed Daisy's)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | (baseline — no fixes yet) | — | — |
| 2 | Main cast pipeline failure (data) | `src/agents/characters.py` | Partial — aliases improved but grounding still fails |
| 2 | IPA corruption | `src/pipeline/pronunciation_guide/enricher.py` | Fixed ✓ |
| 3 | Main cast grounding failure (JSON format) | `src/pipeline/character_extraction_v2/main_cast.py` | Fixed ✓ |
| 3 | Relationship labels wrong (secondary overwrites) | `src/analyzer.py` | No change — primary pipeline also produces bad labels |
| 3 | Pronunciation false positives | `src/pipeline/pronunciation_guide/proposers/foreign_proposer.py` | Fixed ✓ |
| 3 | UNKNOWN pronunciation categorization | `src/pipeline/pronunciation_guide/consolidator.py` | Partial — 28 reclassified, 67 remain |
| 4 | Relationship biased toward familial labels | `src/analyzer.py` (prompt) | Partial — Nick improved, others still wrong |
| 4 | Physical description narrative text | `src/analyzer.py` (validation) | Failed — narrator injection overwrites after validation |
| 4 | Eckleburg duplicate (Doctor/no-Doctor) | `src/agents/characters.py` | Fixed ✓ |
| 4 | "like" flagged as foreign | `src/pipeline/pronunciation_guide/proposers/foreign_proposer.py` | Fixed ✓ |
| 5 | Butler/Butler F6 case sensitivity dedup | `src/analyzer.py` | Fixed ✓ |
| 5 | "unknown" relationship labels in output | `src/pipeline/character_profiling/post_corrections.py` | Fixed ✓ |
| 5 | Nick appearance: narrative prose | `src/pipeline/character_profiling/post_corrections.py` | Fixed ✓ |
| 6 | Nick/Carraway split + narrator | `src/agents/characters.py` | Fixed ✓ |
| 6 | Familial label validation | `src/pipeline/character_profiling/post_corrections.py` | Partial — filter too permissive |
| 6 | Personality traits + speech patterns | `src/analyzer.py` | Fixed ✓ |
| 6 | Homograph IPA | `src/pipeline/pronunciation_guide/enricher.py` | Fixed ✓ |
| 7 | Familial labels Option B | `src/pipeline/character_profiling/post_corrections.py` | Fixed ✓ |
| 7 | Self-negating appearance descriptions | `src/pipeline/character_profiling/post_corrections.py` | Partial — didn't catch cross-contamination |
| 7 | Physical description text fallback | `src/pipeline/character_profiling/post_corrections.py` | Partial — Gatsby ✓, Daisy missed |

**Pattern alerts:**
- `src/pipeline/character_profiling/post_corrections.py` is attempt 3 for physical descriptions (Fix H failed in analyzer.py, Fix S/T in post_corrections partially worked). The functions exist and work for some characters — they need refinement, not a new approach.
- Profiles are the SOLE remaining blocker at 7.5/10. Need +0.5 across: Daisy description (+0.3), Myrtle decontamination (+0.1), Gatsby relationships (+0.15).

## Attempt 8 Fixes Applied

### Fix U: Alias-ambiguity filter in `_llm_first_appearance_description` [CRITICAL #1]
- **Root cause:** Alias "Buchanan" for Daisy matches Tom Buchanan's first appearance, sending wrong context to the LLM → LLM returns NONE for Daisy
- **Fix:** Before searching for first occurrence, filter out single-word aliases that are last-name tokens of other characters. "Buchanan" is filtered because it ends Tom Buchanan's name. Search now uses "Daisy Buchanan" and "Daisy" only.
- **File:** `src/pipeline/character_profiling/post_corrections.py` — `_llm_first_appearance_description()`
- **Universal:** Yes — any alias that is a bare last name shared by another cast member could produce wrong first-appearance context
- **Smoke test:** PASS — "Buchanan" correctly excluded from search, "Daisy" and "Daisy Buchanan" kept

### Fix V: Cross-character attribution detection in `clean_unknown_appearance` [HIGH #2]
- **Root cause:** Myrtle's summary "has a red bob of hair (as described by her sister Catherine)" wasn't caught by `NO_DESC_PHRASES` check since it doesn't self-negate — it positively attributes Catherine's feature to Myrtle
- **Fix:** Added `_strip_attribution_clauses()` helper + call in `clean_unknown_appearance`. Detects "(as described by X)" clauses where X is another cast member and removes those semicolon-delimited clauses from the summary
- **File:** `src/pipeline/character_profiling/post_corrections.py` — `clean_unknown_appearance()` + new `_strip_attribution_clauses()`
- **Universal:** Yes — cross-character attributions with explicit "(as described by [name])" language can appear in any book
- **Smoke test:** PASS — "has a red bob of hair (as described by her sister Catherine)" clause removed; other clauses preserved

### Fix W: Extended bidirectional relationship inference [HIGH #3]
- **Root cause:** `RELATIONSHIP_REVERSES` missing "parent"→"child", "employer"→"employee"; no handling for symmetric relationships like "acquaintance"/"rival"/"friend". Gatsby has zero relationships even though others list him as employer/parent-child target
- **Fix:** Added "parent"/"child", "employer"/"employee", "mentor"/"protégé" to `RELATIONSHIP_REVERSES`. Added `_SYMMETRIC_RELATIONSHIPS` frozenset ("acquaintance", "close friend", "rival", "enemy", "associate", etc.). Updated `infer_bidirectional_relationships` to check symmetric set and fall back to word-set match for compound labels
- **File:** `src/pipeline/character_profiling/post_corrections.py` — `RELATIONSHIP_REVERSES`, `_SYMMETRIC_RELATIONSHIPS`, `infer_bidirectional_relationships()`
- **Universal:** Yes — bidirectional inference for employment, parent-child, and symmetric social relationships applies to all books
- **Smoke test:** PASS — Gatsby now gets: Klipspringer→employee, Henry C. Gatz→child, Lucille→acquaintance from bidirectional inference

## Next Action

Re-run analysis to verify fixes (awaiting_analysis)
