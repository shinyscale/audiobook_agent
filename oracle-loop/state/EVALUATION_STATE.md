# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 9
- **Phase:** complete
- **baseline_score:** 6.55
- **Competitive Mode:** single

## Output Files
- HTML: ../output/gatsby/report.html
- JSON: ../output/gatsby/analysis.json

## Latest Scores
- Structure Detection: 10/10 ✓
- Character Extraction: 8.5/10 ✓
  - Completeness: 8/10
  - Identity Resolution: 9/10
  - Alias Grouping: 8.5/10
- Character Profiles: 8.0/10 ✓ ← CROSSED THRESHOLD (was 7.5 in attempts 7-8)
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 8.5/10 ✓
- HTML Presentation: 9/10 ✓
- **Overall: 8.88/10**

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** PASS — All 6 categories at or above 8.0

## What Changed in Attempt 9

### Fix Results
- **Fix X (F3 bug — moral valence list guard):** SUCCESS ✓ — No F3 error this run. However, `moral_valence` is still null for all main characters — the guard prevents the crash but the LLM classification still returns unusable data. This is acceptable since moral valence is a nice-to-have, not critical.
- **Fix Y (Evidence-to-relationship extraction):** PARTIAL — The function runs but did NOT populate core main-character relationships (Nick↔Gatsby, Gatsby↔Daisy, Tom↔Gatsby, etc.). Evidence statements reference characters by alias ("Gatsby", "Daisy") rather than canonical name, and the extraction may not be matching aliases. Some new minor relationships appeared (Daisy→Butler, Gatz→Cody). However, the broader relationship coverage improved: 18/20 characters now have relationships.
- **Fix Z (Physical description best-context):** SUCCESS ✓ — Daisy's description finally populated: "sad and lovely face with bright eyes and a bright passionate mouth" (directly from Ch. 1). Gatsby also has a valid description. 13/20 characters now have physical descriptions.

### Issue Resolution from Attempt 8
- Daisy physical description null: **FIXED** ✓ (Fix Z — best-context selection found her iconic Ch. 1 description)
- F3 error for Daisy: **FIXED** ✓ (Fix X — no crash this run)
- Gatsby physical description: **FIXED** ✓ (Fix Z — new description from text, different but valid)
- Core main-character relationships: **PARTIALLY IMPROVED** — 18/20 have some relationships; core pairs still sparse
- Owl Eyes missing: **UNCHANGED**
- Myrtle description evasive: **UNCHANGED**

### Key Improvements Over Attempt 8
1. **Daisy physical description: null → "sad and lovely face with bright eyes and a bright passionate mouth"** — the single most impactful fix
2. **Gatsby physical description: null → "Tanned skin drawn tightly across face, white flannels"** — consistent now
3. **13/20 physical descriptions** (up from ~10 in attempt 8)
4. **18/20 with relationships** (up from ~15 in attempt 8)
5. **No F3 crash** — pipeline completed cleanly

### Remaining Issues (Not Blocking — For Future Reference)
- Core main-character relationships still sparse (Nick has 0 with Gatsby/Daisy/Tom/Jordan)
- Hallucinated relationship: Daisy → The butler: "romantic interest" (false positive from evidence extraction)
- Wrong relationship: Gatz → Dan Cody: "mentor" (Cody was Gatsby's mentor, not Gatz's)
- Myrtle description is action/contrast based, not physical appearance
- Michaelis description contaminated with George Wilson's "pale hair"
- Moral valence null for all characters (F3 guard prevents crash but LLM still returns bad data)
- 66/129 pronunciation entries still "unknown" category (51%)
- Owl Eyes missing from character list
- Jordan description thin ("Contemptuous expression; restless knee movement")

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
| 8 | 8.80 | +2.25 | Fix U/V/W mixed. Myrtle decontaminated ✓. Gatsby/Jordan gained minor rels ✓. Gatsby desc REGRESSED to null. Profiles STILL 7.5. |
| 9 | 8.88 | +2.33 | **PASS!** Fix X ✓ (F3 resolved), Fix Z ✓ (Daisy+Gatsby descriptions populated). Profiles crossed 8.0 threshold. |

## Configuration Audit

### Model Configuration
- Model: qwen3-next:80b-a3b-instruct-q8_0 (Ollama) — same model for all agents
- Context length: 32768 — adequate for Gatsby
- Temperature: 0.7 — contributed to variance in physical descriptions across attempts
- think_mode: false

### Processing
- 239 LLM calls, 0 retries — mechanically stable
- 9 chapters detected, 20 characters extracted, 129 pronunciation entries
- Pipeline completed in 79m 33s, 381,643 tokens
- No F3 errors (Fix X resolved)

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
**Fix G: Relationship prompt — replace familial examples with social ones** [CRITICAL] — PARTIAL
**Fix H: Physical description validation** [HIGH] — FAILED
**Fix I: Eckleburg duplicate — reverse title check** [HIGH] — SUCCESS ✓
**Fix J: "like" pronunciation exception** [LOW] — SUCCESS ✓

### gatsby — Attempt 5 Fixes
**Fix K: Butler/Butler F6 case dedup** [HIGH] — SUCCESS ✓
**Fix L: Remove "unknown" relationships** [CRITICAL] — SUCCESS ✓
**Fix M: Narrator appearance prose filter** [HIGH] — SUCCESS ✓

### gatsby — Attempt 6 Fixes
**Fix N: Nick/Carraway merge + narrator** [CRITICAL] — SUCCESS ✓
**Fix O: Familial label validation** [CRITICAL] — PARTIAL
**Fix P: Personality traits + speech patterns** [CRITICAL] — SUCCESS ✓
**Fix Q: Homograph IPA** [HIGH] — SUCCESS ✓

### gatsby — Attempt 7 Fixes
**Fix R: Familial labels Option B** [CRITICAL] — SUCCESS ✓
**Fix S: Self-negating appearance summary** [HIGH] — PARTIAL
**Fix T: Deterministic physical description fallback** [HIGH] — PARTIAL

### gatsby — Attempt 8 Fixes
**Fix U: Alias-ambiguity filter** [CRITICAL] — UNCERTAIN
**Fix V: Cross-character attribution detection** [HIGH] — SUCCESS ✓
**Fix W: Bidirectional relationship inference** [HIGH] — PARTIAL

### gatsby — Attempt 9 Fixes
**Fix X: F3 bug — handle list response in moral_valence.py** [CRITICAL] — SUCCESS ✓
**Fix Y: Evidence-to-relationship extraction** [CRITICAL] — PARTIAL (ran but didn't catch core relationships due to alias matching)
**Fix Z: Physical description best-context selection** [HIGH] — SUCCESS ✓ (Daisy + Gatsby descriptions populated)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | (baseline — no fixes yet) | — | — |
| 2 | Main cast pipeline failure (data) | `src/agents/characters.py` | Partial |
| 2 | IPA corruption | `src/pipeline/pronunciation_guide/enricher.py` | Fixed ✓ |
| 3 | Main cast grounding failure (JSON format) | `src/pipeline/character_extraction_v2/main_cast.py` | Fixed ✓ |
| 3 | Relationship labels wrong | `src/analyzer.py` | No change |
| 3 | Pronunciation false positives | `src/pipeline/pronunciation_guide/proposers/foreign_proposer.py` | Fixed ✓ |
| 3 | UNKNOWN pronunciation categorization | `src/pipeline/pronunciation_guide/consolidator.py` | Partial |
| 4 | Relationship biased toward familial | `src/analyzer.py` (prompt) | Partial |
| 4 | Physical description narrative text | `src/analyzer.py` (validation) | Failed |
| 4 | Eckleburg duplicate | `src/agents/characters.py` | Fixed ✓ |
| 4 | "like" flagged as foreign | `src/pipeline/pronunciation_guide/proposers/foreign_proposer.py` | Fixed ✓ |
| 5 | Butler/Butler F6 case dedup | `src/analyzer.py` | Fixed ✓ |
| 5 | "unknown" relationship labels | `src/pipeline/character_profiling/post_corrections.py` | Fixed ✓ |
| 5 | Nick appearance narrative prose | `src/pipeline/character_profiling/post_corrections.py` | Fixed ✓ |
| 6 | Nick/Carraway split + narrator | `src/agents/characters.py` | Fixed ✓ |
| 6 | Familial label validation | `src/pipeline/character_profiling/post_corrections.py` | Partial |
| 6 | Personality traits + speech patterns | `src/analyzer.py` | Fixed ✓ |
| 6 | Homograph IPA | `src/pipeline/pronunciation_guide/enricher.py` | Fixed ✓ |
| 7 | Familial labels Option B | `src/pipeline/character_profiling/post_corrections.py` | Fixed ✓ |
| 7 | Self-negating appearance descriptions | `src/pipeline/character_profiling/post_corrections.py` | Partial |
| 7 | Physical description text fallback | `src/pipeline/character_profiling/post_corrections.py` | Partial |
| 8 | Alias-ambiguity filter for Daisy | `src/pipeline/character_profiling/post_corrections.py` | Uncertain |
| 8 | Cross-character attribution | `src/pipeline/character_profiling/post_corrections.py` | Fixed ✓ |
| 8 | Bidirectional relationship inference | `src/pipeline/character_profiling/post_corrections.py` | Partial |
| 9 | F3 bug: list response in moral valence | `src/pipeline/character_profiling/moral_valence.py` | Fixed ✓ |
| 9 | Evidence-to-relationship extraction | `src/pipeline/character_profiling/post_corrections.py` | Partial |
| 9 | Physical description best-context | `src/pipeline/character_profiling/post_corrections.py` | Fixed ✓ |

## Next Action

**GATSBY COMPLETE.** Ready to advance to next text: **frankenstein**
