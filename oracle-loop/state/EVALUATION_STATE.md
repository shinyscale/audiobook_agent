# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 9
- **Phase:** awaiting_evaluation
- **baseline_score:** 6.55
- **Competitive Mode:** single

## Output Files
- HTML: ../output/gatsby/report.html
- JSON: ../output/gatsby/analysis.json

## Pipeline Notes (Attempt 9)
- Completed in 79m 33s, 239 LLM calls, 381,643 tokens
- 9 chapters detected, 20 characters extracted (+1 from attempt 8), 129 pronunciation entries
- No F3 error this time (Fix X — moral valence list guard resolved)
- Fix Y (evidence-to-relationship): impact TBD — awaiting evaluation
- Fix Z (best-context physical description): impact TBD — awaiting evaluation
- 20th character: likely a new minor character now crossing threshold

## Pipeline Notes (Attempt 8)
- Completed in 77m 47s, 227 LLM calls, 357,689 tokens
- 9 chapters detected, 19 characters extracted, 130 pronunciation entries
- New warning: `F3: Moral valence classification failed for Daisy Buchanan: 'list' object has no attribute 'get'` — may affect profile quality
- Fix U (alias-ambiguity filter for Daisy description): should now prevent wrong context from Tom Buchanan match
- Fix V (cross-character attribution detection): should remove Myrtle's "red bob" contamination
- Fix W (bidirectional relationship inference): should give Gatsby/Jordan relationships from bidirectional inference

## Pipeline Notes (Attempt 7)
- Completed in 87m 1s, 298 LLM calls, 449,366 tokens
- 9 chapters detected, 19 characters extracted, 130 pronunciation entries
- Jay Gatsby now canonical name (not James Gatz) ✓
- Nick Carraway narrator confirmed ✓ (first-person)
- Fix R SUCCESS: ALL hallucinated familial labels removed ✓
- Fix S PARTIAL: Myrtle still has Catherine's "red bob" contamination
- Fix T PARTIAL: Gatsby got a physical description ✓, but Daisy still null

## Latest Scores
- Structure Detection: 10/10 ✓
- Character Extraction: 8.5/10 ✓
  - Completeness: 8/10
  - Identity Resolution: 9/10
  - Alias Grouping: 8.5/10
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
| 8 | 8.80 | +2.25 | Fix U/V/W mixed results. Myrtle decontaminated ✓. Gatsby/Jordan gained minor rels ✓. BUT Gatsby desc REGRESSED to null. Core main-char rels still absent. Profiles STILL 7.5. |

## What Changed in Attempt 8

### Fix Results
- **Fix U (Alias-ambiguity filter):** UNCERTAIN — "Buchanan" alias correctly filtered from search, but Daisy still has `physical_description: null`. The F3 error ("list has no attribute 'get'") for Daisy may have blocked the pipeline from completing her profile. Cannot confirm if Fix U logic worked since the F3 bug may have interfered.
- **Fix V (Cross-character attribution):** SUCCESS ✓ — Myrtle's contaminated "red bob of hair (as described by her sister Catherine)" description is gone. `physical_description` is now null (cleared, not replaced). The contamination was removed but `propagate_physical_description()` didn't find a replacement.
- **Fix W (Bidirectional relationship inference):** PARTIAL — Gatsby gained 4 relationships (Eckleburg: acquaintance, Klipspringer: acquaintance, Lucille: acquaintance, George Wilson: enemy). Jordan gained 2 (Lucille: acquaintance, The butler: acquaintance). However, bidirectional inference can only create relationships when one side already has them. The core problem is that NEITHER side of main-character pairs (Gatsby↔Daisy, Gatsby↔Nick, Gatsby↔Tom, Nick↔Jordan, etc.) has relationships, so bidirectional inference cannot help.

### Issue Resolution from Attempt 7
- Myrtle contaminated description: **FIXED** ✓ (Fix V — contamination cleared, now null)
- Gatsby zero relationships: **IMPROVED** (Fix W — gained 4 minor relationships, was 0)
- Jordan zero relationships: **IMPROVED** (Fix W — gained 2 minor relationships, was 0)
- Duplicate "Daisy" in alias list: **FIXED** ✓ (no longer duplicated)
- Gatsby physical description: **REGRESSED** ✗ (was "elegant young roughneck; wears a pink suit" in attempt 7, now null — LLM variance in `propagate_physical_description()`)
- Daisy physical description null: **UNCHANGED** — Fix U + F3 error may have blocked
- Core main-character relationships: **UNCHANGED** — bidirectional inference can't help when neither side has the relationship
- Owl Eyes missing: **UNCHANGED**

### Key Regression
**Gatsby physical_description regressed from populated → null.** In attempt 7, `propagate_physical_description()` found "elegant young roughneck; wears a pink suit". In attempt 8, it found nothing. Same code, same text — this is LLM variance (temperature 0.7). The function needs to be made more deterministic.

## Current Issues (Priority Order)

### CRITICAL

1. **F3 code bug: "list object has no attribute 'get'" in moral valence classification** [Profiles — Code Bug]
   - Problem: `F3: Moral valence classification failed for Daisy Buchanan: 'list' object has no attribute 'get'` — this is a Python TypeError in the profiling pipeline
   - Impact: May be preventing Daisy's profile from being fully populated. Could explain why Fix U didn't produce a description.
   - Location: Search for `moral_valence` or `moral` in `src/pipeline/character_profiling/` or `src/analyzer.py` — the code expects a dict but receives a list
   - Fix: Find the `.get()` call on what's actually a list, add type-checking or fix the upstream data structure. This is a deterministic code bug, not LLM variance.
   - Impact: Fixing this may unblock Daisy's physical description and other profile fields.

2. **Core main-character relationships entirely absent** [Profiles — Relationships]
   - Problem: The 5 most important characters (Nick, Gatsby, Daisy, Tom, Jordan) have almost NO relationships with each other:
     - Nick → {Wolfsheim, Myrtle, McKee, Klipspringer, Butler, Eckleburg, Catherine} — NONE with Gatsby, Daisy, Tom, Jordan
     - Gatsby → {Eckleburg, Klipspringer, Lucille, George Wilson} — NONE with Daisy, Nick, Tom, Wolfsheim, Dan Cody
     - Daisy → {Tom: wife, Klipspringer} — NONE with Gatsby, Nick, Jordan
     - Tom → {Daisy: husband, Eckleburg} — NONE with Gatsby, Myrtle, Nick
     - Jordan → {Lucille, Butler} — NONE with Nick, Daisy, Gatsby
   - Evidence: The `evidence` field for each character KNOWS about these relationships:
     - Daisy's evidence: "romantic history with Jay Gatsby", "Nick Carraway's cousin", "close social connection to Jordan Baker"
     - But these don't transfer to the `relationships` dict
   - Root cause: The LLM profiling prompt generates sparse relationships, and bidirectional inference (Fix W) can't help when neither side has the relationship. The relationship data exists in `evidence` but isn't being extracted.
   - Location: `src/pipeline/character_profiling/post_corrections.py`
   - Fix: Add `extract_relationships_from_evidence()` post-correction that scans each character's evidence statements for mentions of other cast members. When a statement like "has a romantic history with Jay Gatsby" is found, extract a relationship label. Alternatively, for any pair of characters with >50 mentions each and zero cross-references in relationships, create a minimal "associated" link.
   - Impact: +0.3 to Profiles — this is the single highest-impact fix remaining

### HIGH

3. **Gatsby/Daisy/Myrtle physical descriptions all null** [Profiles — Descriptions]
   - Problem: 3 of the top 5 characters lack physical descriptions:
     - Jay Gatsby (268 mentions): null — REGRESSION from attempt 7 ("elegant young roughneck; wears a pink suit")
     - Daisy Buchanan (208 mentions): null — unchanged across attempts 6-8
     - Myrtle Wilson (94 mentions): null — cleared of contamination but not replaced
   - Expected descriptions:
     - Gatsby: "an elegant young roughneck, a year or two over thirty" + pink suit, white flannel suit
     - Daisy: "face was sad and lovely with bright things in it, bright eyes and a bright passionate mouth" (Ch 1)
     - Myrtle: "thickish figure," "middle thirties, faintly stout," "carried her surplus flesh sensuously"
   - Root cause: `propagate_physical_description()` uses a physical-term vocabulary that doesn't reliably match how these characters are described. It found Gatsby in attempt 7 but not attempt 8 (LLM variance at temperature 0.7). It has never found Daisy's face-based description.
   - Location: `src/pipeline/character_profiling/post_corrections.py` — `propagate_physical_description()`
   - Fix: Two improvements needed:
     a. **Expand physical-term vocabulary** to include: face, eyes, mouth, lips, hair, complexion, build, figure, stout, slender, tall, short, skin, dress, suit, wore, wearing, flushed, pale
     b. **Search by all aliases**, not just canonical name — search for "Gatsby", "Daisy", "Myrtle" in addition to full names
     c. **Lower temperature or use deterministic extraction** — the current approach is too sensitive to LLM variance. Consider using a regex/keyword approach first, and only fall back to LLM if that fails.
   - Impact: +0.2 to Profiles

### MEDIUM

4. **Eckleburg has 6 inappropriate "acquaintance" relationships** [Profiles]
   - Problem: Doctor T. J. Eckleburg (a billboard/symbol, `is_symbolic: false`) has relationships with George Wilson, Jay Gatsby, Michaelis, Myrtle Wilson, Nick Carraway, Tom Buchanan
   - A billboard can't be acquainted with people
   - LOW priority — doesn't significantly impact narrator prep

5. **67/130 pronunciations still "unknown" category** [Pronunciation]
   - Many are classifiable proper nouns, musical terms, dialect spellings, literary words
   - Quality of entries is good (all have IPA, notes, context), just miscategorized
   - 51% unknown category rate

### LOW

6. **Owl Eyes still missing from character list** [Completeness]
   - The owl-eyed man from Gatsby's library (Ch 3) who appears at the funeral (Ch 9)
   - Narratively significant but minor character filtered by mention count

7. **Jordan's physical description is thin** [Profiles]
   - "Pleasing contemptuous expression; golden shoulder" — missing athletic build, tan, chin-raised posture
   - Not a blocker — has some description, just incomplete

## Configuration Audit

### Model Configuration
- Model: qwen3-next:80b-a3b-instruct-q8_0 (Ollama) — same model for all agents
- Context length: 32768 — adequate for Gatsby
- Temperature: 0.7 — a contributing factor to physical description variance between attempts
- think_mode: false

### Processing Issues
- 227 LLM calls, 0 retries — mechanically stable
- Personality/voice data: excellent quality (17/19 traits, 19/19 voice guidance)
- F3 error for Daisy Buchanan — code bug in moral valence classification
- Physical description extraction remains unreliable across runs
- Relationship extraction for main characters remains the biggest gap

### Recommendation
- **CRITICAL**: Fix F3 code bug (may unblock Daisy profile)
- **CRITICAL**: Add evidence-to-relationship extraction for main character pairs
- **HIGH**: Make physical description fallback more deterministic (broader terms, all aliases, lower LLM dependence)

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

### gatsby — Attempt 8 Fixes
**Fix U: Alias-ambiguity filter** [CRITICAL] — UNCERTAIN (src/pipeline/character_profiling/post_corrections.py — F3 error may have blocked)
**Fix V: Cross-character attribution detection** [HIGH] — SUCCESS ✓ (src/pipeline/character_profiling/post_corrections.py — Myrtle decontaminated)
**Fix W: Bidirectional relationship inference** [HIGH] — PARTIAL (src/pipeline/character_profiling/post_corrections.py — Gatsby +4, Jordan +2, but all minor; core relationships still absent)

### gatsby — Attempt 9 Fixes
**Fix X: F3 bug — handle list response in moral_valence.py** [CRITICAL] — APPLIED
- Root cause: `query_json` returns `list` when LLM wraps result; `.get()` fails on list
- Fixed: Add `isinstance(result, list)` guard in `classify_character()`; extract first element or return UNCERTAIN
- File: `src/pipeline/character_profiling/moral_valence.py`
- Smoke test: PASS — tested mock list/empty-list/dict responses

**Fix Y: Evidence-to-relationship extraction** [CRITICAL] — APPLIED
- Root cause: Profiling LLM captures relationships in `evidence.statement` but doesn't populate `relationships` dict
- Fixed: Added `extract_relationships_from_evidence()` to `OutputCharacterCorrector`; scans evidence for cast co-mentions; infers type from universal indicators (romantic/rival/enemy/neighbor); applies symmetric bidirectional inference with "associated"→more-specific upgrade
- File: `src/pipeline/character_profiling/post_corrections.py`
- Smoke test: PASS — Nick→Gatsby:neighbor, Gatsby→Daisy:romantic interest, Tom→Gatsby:rival all correctly inferred; bidirectional upgrades confirmed

**Fix Z: Physical description — best-context occurrence** [HIGH] — APPLIED
- Root cause: `_llm_first_appearance_description()` used first name occurrence which may have no physical context
- Fixed: Score up to 5 occurrences per name by physical-word density; use the highest-scoring position (tie-broken by earliest); also expanded `PHYS_DESCRIPTOR_WORDS` with face/eyes/hair/etc.
- File: `src/pipeline/character_profiling/post_corrections.py`
- Smoke test: PASS — code runs, logic verified

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
| 8 | Alias-ambiguity filter for Daisy | `src/pipeline/character_profiling/post_corrections.py` | Uncertain — F3 bug may have blocked |
| 8 | Cross-character attribution | `src/pipeline/character_profiling/post_corrections.py` | Fixed ✓ (Myrtle decontaminated) |
| 8 | Bidirectional relationship inference | `src/pipeline/character_profiling/post_corrections.py` | Partial — added minor rels only |
| 9 | F3 bug: list response in moral valence | `src/pipeline/character_profiling/moral_valence.py` | Applied — deterministic code fix |
| 9 | Evidence-to-relationship extraction | `src/pipeline/character_profiling/post_corrections.py` | Applied — new method; smoke test PASS |
| 9 | Physical description best-context selection | `src/pipeline/character_profiling/post_corrections.py` | Applied — scores 5 occurrences per name |

**Pattern alerts:**
- `src/pipeline/character_profiling/post_corrections.py` modified in attempts 5, 6, 7, 8 (4 consecutive attempts). Physical descriptions partially improved but remain unreliable. Relationship fixes keep adding incremental post-processing but the ROOT issue is upstream: the LLM profiling prompt doesn't generate main-character relationships.
- The `evidence` field contains relationship data that the `relationships` field lacks. A new approach: mine the evidence field rather than keep trying to fix the LLM prompt.
- F3 code bug is a NEW issue (first appeared in attempt 8) — may be caused by Fix U/V/W changes or by LLM output variance. Must be investigated.

## Next Action

Run PROMPT_analyze.md to re-run the pipeline with attempt 9 fixes:
- Fix X: F3 bug resolved (moral_valence.py)
- Fix Y: Evidence-to-relationship extraction added (post_corrections.py)
- Fix Z: Physical description uses best-context window (post_corrections.py)

Expected improvements:
- Daisy's profile should now complete fully (F3 bug unblocked)
- Core main-character relationships (Nick↔Gatsby, Gatsby↔Daisy, Tom↔Gatsby, etc.) should now appear
- Physical descriptions for Gatsby/Daisy/Myrtle should be more consistently populated
