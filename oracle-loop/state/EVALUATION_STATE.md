# Current Evaluation State

## Active Text
- **Name:** i_have_no_mouth
- **Attempt:** 14
- **Phase:** awaiting_fix
- **baseline_score:** 7.35
- **Competitive Mode:** single

## Output Files
- HTML: ../output/i_have_no_mouth/report.html
- JSON: ../output/i_have_no_mouth/analysis.json
- Timestamped: ../output/I_Have_No_Mouth_And_I_Must_Scream_20260223_132726/

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 9/10 ✓
  - Completeness: 9/10
  - Identity Resolution: 10/10
  - Alias Grouping: 9/10
- Character Profiles: 7.5/10 ✗ (FAILING — up from 7.0 in attempt 13; execution ordering fix WORKED but replacement quality poor)
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 8.53/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (1 category below threshold — Profiles at 7.5)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 7.35 | 0.00 | Baseline. AM missing, false positives, pronunciation artifacts |
| 2 | 7.40 | +0.05 | bush removed, roles improved, but AM still missing, narrator still undetected |
| 3 | CRASH | - | Pipeline crash: KeyError in MAIN_CAST_PROMPT format() due to unescaped JSON braces |
| 4 | 6.80 | -0.55 | Artifacts fixed but AM STILL missing, narrator STILL undetected, profiles empty, "Age: five years" bug |
| 5 | 6.80 | -0.55 | No change from attempt 4 |
| 6 | 6.80 | -0.55 | Fallback fired but AM not grounded. Heuristic narrator didn't fire (type mismatch). |
| 7 | 6.80 | -0.55 | Fix 3 worked (Jesus removed). Fixes 1+2 did NOT take effect despite correct code in codebase. |
| 8 | 7.43 | +0.08 | Narrator detection FIXED (Ted is_narrator: true). Orphaned relationships cleaned. AM still missing. Ages still wrong. |
| 9 | 7.98 | +0.63 | **AM ADDED via safety net!** Title/timing HTML fixes. hermiene removed. Ages null at top level but still in appearance. 4→2 failing categories. |
| 10 | 8.40 | +1.05 | Ages GONE. AM=antagonist with personality. Pronunciation 37→23. **1 failing category remaining (Profiles 7.5).** |
| 11 | 8.03 | +0.68 | **REGRESSION.** Nimdok DROPPED (6→5 chars). AM personality still plot_summary dump. 1→2 failing categories. |
| 12 | 8.53 | +1.18 | Nimdok RESTORED. 4/6 physical_desc (up from 1/6). AM personality STILL broken (3rd failed attempt). 2→1 failing category. |
| 13 | 8.45 | +1.10 | **MINOR REGRESSION.** AM personality post-correction DID NOT WORK (4th failure — root cause found: execution ordering). Ellen profile REGRESSED (stochastic LLM failure). 3/6 physical_desc (was 4/6). |
| 14 | 8.53 | +1.18 | Execution ordering fix WORKED — plot dump gone! But replacement is garbled sentence fragments. Ellen restored. Nimdok improved. AM personality still not useful. |

## What Happened in Attempt 14

### Fix Applied
1. **Execution ordering fix in `analyzer.py`**: Moved `_plot_summary_safety_net()` BEFORE `OutputCharacterCorrector().run_all()`. The post-correction now sees AM in the character list.

### Result: PARTIALLY WORKED — Ordering Fixed, Replacement Quality Poor

**The execution ordering fix succeeded:**
- `clean_plot_summary_personality()` now detects AM's personality mentions 3+ other characters ✓
- It replaces the full plot dump with source-text subject sentences ✓
- The plot dump is GONE — no more multi-paragraph narrative in personality ✓

**But the replacement is garbled:**
- AM personality is now: `"AM. AM had been as ruthless with its own life aswith ours. AM had blinded him."`
- Problems:
  1. First "sentence" is just `"AM."` — the character name with a period, not a personality descriptor
  2. `"aswith"` — text artifact from missing space in source PDF extraction
  3. These are narrative action sentences, not personality traits
  4. Doesn't capture any of AM's key personality: sadistic, omnipotent, hateful, creative in cruelty
  5. Less useful than null — a narrator reading this gets confused rather than informed

### Stochastic Improvements (not from code changes)
- **Ellen profile RESTORED**: 5H/0M/0L (was 4H/0M/1L in attempt 13). Ellen now has full personality, physical_description, and relationships ✓
- **Nimdok chimpanzee error GONE**: No longer says "resembling a chimpanzee AM intended him to resemble" (that was Benny's description). Now has accurate description ✓
- **AM relationships complete**: All 5 humans listed as "adversary" including Ellen (was missing in attempt 13) ✓
- **physical_description: 4/6** (up from 3/6 in attempt 13, same as attempt 12)

## Current Issues (Priority Order)

### CRITICAL
1. **AM personality is garbled sentence fragments — replacement quality too low** [Profiles]
   - Problem: AM's personality reads: `"AM. AM had been as ruthless with its own life aswith ours. AM had blinded him."` — extracted source-text sentences that are narrative actions, not personality traits. Contains text artifact ("aswith"). Worse than null for narrator preparation.
   - Root cause: `clean_plot_summary_personality()` extracts sentences from source text where "AM" is the grammatical subject. For Ellison's prose, those sentences describe AM's actions ("had blinded", "had been ruthless") not personality traits. The method correctly detects the plot dump and correctly extracts subject sentences, but the subject sentences are the wrong type of content.
   - **TWO-PART FIX needed:**
     - **Part A — Safety net personality** (`analyzer.py:3926-3947`): Instead of building personality from full plot-summary sentences (which mention other characters → trigger post-correction → get replaced with poor source sentences), extract ADJECTIVE PHRASES from the plot_summary context that describe the character. The plot summary already contains: "omnipotent and sadistic AI", "relentless cruelty", "Enraged by this ultimate defiance". Build personality like: `"Omnipotent and sadistic. Shows relentless cruelty and becomes enraged by defiance."` This personality won't mention 3+ other characters → post-correction won't flag it → clean personality survives.
     - **Part B — Fallback quality** (`post_corrections.py:949-967`): Add a quality filter to `clean_plot_summary_personality()`. If extracted subject sentences are < 50 chars total, or if ANY sentence is just the character name + period (e.g., "AM."), fall back to `None` instead of using garbled fragments. The method's docstring already says "Clearing (None) is always preferable to retaining a misleading plot dump."
   - Location: `analyzer.py` (`_plot_summary_safety_net`), `post_corrections.py` (`clean_plot_summary_personality`)
   - Expected impact: AM gets a usable personality description → Profiles reaches 8.0

### MEDIUM
2. **Remaining pronunciation false positives** [Pronunciation]
   - "palette", "piteously", "eternities", "shoal" are standard English words.
   - Not a threshold blocker (Pronunciation at 8.0).

3. **"choir" IPA wrong** [Pronunciation]
   - Listed as /kwɑːr/, correct is /kwaɪər/.
   - Not a threshold blocker.

### LOW
4. **Ted's personality too flat** [Profiles]
   - Misses paranoid, cynical, unreliable narrator traits.
   - LLM profiling quality issue, not code-fixable.

5. **AM relationships too generic** [Profiles]
   - All say "adversary". More specific descriptions would help narrators.
   - Low priority — relationships are functional.

## Fix Priority for Attempt 15

**CRITICAL #1 is the ONLY remaining blocker.**

The fix has two parts (both needed):

### Part A: Better safety net personality (analyzer.py)
In `_plot_summary_safety_net()` at lines 3926-3947, replace the sentence-extraction approach with adjective/descriptor extraction from the plot_summary context:
1. From the `contexts_original` list (already computed at line 3913-3914), extract adjective phrases that modify or describe the character
2. Look for patterns like `"{NAME}.*?(adjective|trait word)"` or `"(adjective) {common_noun_for_character}"`
3. Build a short personality summary from these descriptors: e.g., "Omnipotent and sadistic. Shows relentless cruelty."
4. This personality will NOT mention 3+ other character names → `clean_plot_summary_personality()` won't flag it

### Part B: Quality filter in post-correction (post_corrections.py)
In `clean_plot_summary_personality()` at lines 963-967, add quality checks before using extracted sentences:
1. Filter out sentences that are just the character name + punctuation (e.g., "AM.")
2. If remaining sentences total < 50 chars, fall back to `None` instead of using them
3. Check for text artifacts (consecutive words without spaces) — if found, fall back to `None`

Expected impact: AM personality either gets clean adjective-based description (Part A) or falls to null (Part B). Either is 8.0-worthy compared to current garbled fragments.

## Fix History

### Attempt 1 Fixes Applied
- **Fix 1**: Move supporting cast mention search to BEFORE promotion (STEP 5.7.5) → **WORKED**
- **Fix 2**: Add narrator re-detection after promotion (STEP 5.8.5) → **DID NOT WORK**
- **Fix 3**: Fix narrator prompt to account for 3rd-person summaries → **DID NOT WORK**
- **Fix 4**: Proper names must start with uppercase → **WORKED** ("bush" removed)
- **Bug fix**: Variable shadowing in STEP 5.10.5 → **Fixed**

### Attempt 3 Fixes Applied
- **Fix 1**: Robust LLM JSON parsing (accept "name" key, try wrapper keys) → **DID NOT WORK** (main_cast still 0)
- **Fix 2**: Two-pass → single-pass fallback in extract() → **Fires but still 0 characters**
- **Fix 3**: STEP 5.8.5 re-detection condition fix → **DID NOT WORK**
- **Fix 4**: Include plot_summary in narrator detection prompt → **DID NOT WORK**
- **Fix 5**: Pronunciation artifact detection improvements → **PARTIALLY WORKED**

### Attempt 4 Fix Applied
- **Fix**: Escape JSON example braces in MAIN_CAST_PROMPT → **Fixed crash**

### Attempt 5 Fixes Applied
- **Fix 1-3**: Added `[DIAG]` debug logging → **NOT VISIBLE** (DEBUG level)
- **Fix 4**: Fixed `_get_plot_summary()` — was always returning None → **WORKED**
- **Fix 5**: Improved NARRATOR_DETECTION_PROMPT rule #2 → **DID NOT WORK**

### Attempt 6 Fixes Applied
- **Fix 1**: Plot summary character fallback (STEP 3.1) → **FIRED but AM not grounded** — GroundingGate rejects "AM"
- **Fix 2**: Heuristic narrator fallback (STEP 5.8.6) → **DID NOT FIRE** — `_get_narrative_style()` returns None

### Attempt 7 Fixes Applied
- **Fix 1**: Skip GroundingGate for plot_summary fallback → **CODE PRESENT BUT NO EFFECT**
- **Fix 2**: Fix `_get_narrative_style()` type check (hasattr for Pydantic) → **CODE PRESENT BUT NO EFFECT**
- **Fix 3**: Post-profiling evidence filter (discard 0-evidence chars) → **WORKED** (Jesus removed)

### Attempt 8 Fixes Applied
- **Fix 1**: Fallback prompt includes "AI, non-human beings, sentient entities" → **FAILED** — 0 main_cast again
- **Fix 2**: `_get_narrative_style()` complete rewrite → **WORKED** — Ted is now narrator
- **Fix 3**: `clean_orphaned_relationships()` → **WORKED** — Jesus references cleaned from all characters
- **Fix 4**: Age validation in `extract_deterministic_age()` → **PARTIALLY WORKED** — top-level age null, but nested appearance.age_indication unchanged
- **Refactor**: PipelineCharacterCorrector + OutputCharacterCorrector with 49 tests → **WORKED**

### Attempt 9 Fixes Applied
- **Fix 1**: Plot_summary safety net in `analyzer.py` → **WORKED** — AM now present (74 mentions)
- **Fix 2**: HTML title underscores fix → **WORKED**
- **Fix 3**: HTML timing table empty rows fix → **WORKED**
- **Fix 4**: URL token filter in CMU pronunciation proposer → **WORKED** — "hermiene" removed

### Attempt 10 Fixes Applied
- **Fix 1**: `_age_extract_pat` — require "old" for written-number forms → **WORKED** — ages gone from HTML
- **Fix 2**: Safety net profile enrichment (role detection, context sentences, personality, relationships) → **PARTIALLY WORKED** — role=antagonist ✓, but personality=plot_summary dump, relationships="see plot summary"
- **Fix 3**: `clean_unknown_appearance()` → **WORKED** — placeholder values cleared
- **Fix 4**: `_is_closed_compound()` → **WORKED** — 37→23 pronunciation entries

### Attempt 11 Fixes Applied
- **Fix 1**: AM personality sentence extraction → **DID NOT WORK** — personality.summary still full plot_summary dump, unchanged from attempt 10
- **Fix 2**: AM relationships role-based defaults → **WORKED** — "adversary" replaces "see plot summary" for all 4 humans
- **Fix 3**: physical_description propagation from appearance.summary → **PARTIALLY WORKED** — Benny gets physical_description, but Ellen/Gorrister/Ted have null appearance.summary so nothing propagated

### Attempt 12 Fixes Applied
- **Fix 1**: Nimdok mention_count > 5 guard in evidence filter → **WORKED** — 6 characters restored (was 5)
- **Fix 2**: AM personality subject-sentence selection in _plot_summary_safety_net → **DID NOT WORK** (3rd failure) — personality.summary unchanged
- **Fix 3**: physical_description from distinguishing_features fallback → **WORKED** — 4/6 characters have physical_description (was 1/6)

### Attempt 13 Fix Applied
- **Fix 1**: `clean_plot_summary_personality()` post-correction in OutputCharacterCorrector → **DID NOT WORK** (4th failure) — ROOT CAUSE: OutputCharacterCorrector runs BEFORE safety net adds AM. Code is correct but never sees AM.

### Attempt 14 Fix Applied
- **Fix 1**: Reordered execution in `analyzer.py:2067-2079` — moved `_plot_summary_safety_net()` BEFORE `OutputCharacterCorrector().run_all()` → **PARTIALLY WORKED** — Plot dump replaced with source sentences, but extracted sentences are garbled fragments ("AM. AM had been as ruthless with its own life aswith ours. AM had blinded him."). Ordering is now correct; replacement quality is the issue.

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | Characters not promoted due to late mention search | characters.py (STEP 5.7.5) | Fixed |
| 1 | Narrator undetected due to empty main_cast | characters.py (STEP 5.8.5) | No change |
| 1 | Narrator prompt assumes first-person in summaries | narrator.py | No change |
| 1 | Lowercase false positive "bush" | supporting.py | Fixed |
| 1 | Variable shadowing bug | characters.py | Fixed |
| 3 | Main cast JSON parsing too strict | main_cast.py | No change — still 0 chars |
| 3 | No single-pass fallback | main_cast.py | Fallback fires but still 0 chars |
| 3 | STEP 5.8.5 condition too restrictive | characters.py | No change |
| 3 | Narrator prompt missing plot_summary | narrator.py | No change |
| 3 | Pronunciation concatenation artifacts | cmu_proposer.py | Partially fixed |
| 4 | MAIN_CAST_PROMPT crash (unescaped braces) | main_cast.py | Fixed crash |
| 5 | main_cast [DIAG] logging | main_cast.py | Not visible (DEBUG) |
| 5 | Narrator [DIAG] logging | narrator.py | Not visible (DEBUG) |
| 5 | _get_plot_summary() always returns None | characters.py | Fixed |
| 5 | Narrator prompt exact name rule | narrator.py | No change |
| 6 | Plot summary fallback (STEP 3.1) | characters.py | Fired but AM rejected by grounding |
| 6 | Heuristic narrator (STEP 5.8.6) | characters.py | Did not fire — type check bug |
| 7 | Grounding bypass for fallback | characters.py | Code correct, no effect |
| 7 | _get_narrative_style() type check | characters.py | Code correct, no effect |
| 7 | Evidence filter for false positives | analyzer.py | **WORKED** (Jesus removed) |
| 8 | Fallback prompt for sentient entities | characters.py | **FAILED** — 0 main_cast again |
| 8 | _get_narrative_style() complete rewrite | characters.py | **WORKED** — Ted is narrator |
| 8 | clean_orphaned_relationships() | post_corrections.py | **WORKED** — Jesus refs cleaned |
| 8 | Age validation in extract_deterministic_age() | post_corrections.py | **PARTIAL** — top-level only |
| 8 | Refactor post-corrections into classes | analyzer.py, post_corrections.py | **WORKED** |
| 9 | AM missing → plot_summary safety net | analyzer.py | **WORKED** — AM present |
| 9 | HTML title underscores | html_report.py | **WORKED** |
| 9 | HTML timing empty rows | html_report.py | **WORKED** |
| 9 | Pronunciation URL artifact (hermiene) | cmu_proposer.py | **WORKED** |
| 10 | Age pattern re-extraction | post_corrections.py | **WORKED** — ages gone |
| 10 | AM personality from plot_summary | analyzer.py (_plot_summary_safety_net) | **PARTIAL** — dumped full plot_summary instead of traits |
| 10 | Unknown appearance cleanup | post_corrections.py | **WORKED** |
| 10 | Compound word filter | cmu_proposer.py | **WORKED** — 37→23 entries |
| 11 | AM personality sentence extraction | analyzer.py (_plot_summary_safety_net) | **DID NOT WORK** — still plot_summary dump |
| 11 | AM relationships role defaults | analyzer.py | **WORKED** — "adversary" replaces placeholders |
| 11 | physical_description propagation | post_corrections.py, models.py | **PARTIAL** — Benny only |
| 12 | Nimdok evidence filter guard | analyzer.py (_convert_characters) | **WORKED** — 6 chars restored |
| 12 | AM personality subject-sentence | analyzer.py (_plot_summary_safety_net) | **DID NOT WORK** (3rd failure) |
| 12 | physical_description from features | post_corrections.py | **WORKED** — 4/6 chars have desc |
| 13 | AM personality post-correction | post_corrections.py (clean_plot_summary_personality) | **DID NOT WORK** — correct code but runs before AM exists |
| 14 | Execution ordering (safety net before post-corrections) | analyzer.py | **PARTIALLY WORKED** — ordering fixed, but replacement quality poor |

**⚠️ AM PERSONALITY — 5TH ATTEMPT**: The execution ordering is now correct. The problem is now PURELY about replacement quality: source-text subject sentences are narrative actions, not personality descriptors. Fix must target the personality content generation, not the detection/execution flow.

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (same for all stages)
- Context: 32768 tokens — sufficient for a short story (~5400 words)
- Temperature: 0.7 for all stages
- Character Extraction: 5 LLM calls (0 main_cast, 5 supporting, 1 safety net)
- Character Profiles: 15 LLM calls, 5 items processed, **5H/0M/0L** (ALL high confidence — Ellen restored)
- 0 LLM retries, 0 JSON parse failures
- Pronunciation: 23 entries (unchanged from attempt 10)
- Runtime: 17m 10s

## Pipeline Notes (Attempt 14)
- 6 characters found: Benny (35), Ellen (30), Gorrister (29), Nimdok (17), Ted (5), AM via safety net (74 mentions) ✓
- Character Profiles: **5H/0M/0L** — ALL profiles high confidence (Ellen no longer failing)
- AM safety net fired: role=antagonist, 74 mentions ✓
- Execution ordering fix applied: OutputCharacterCorrector now runs AFTER _plot_summary_safety_net ✓
- clean_plot_summary_personality() FIRED on AM: detected 3+ other character names, replaced with source-text subject sentences
- Replacement result: "AM. AM had been as ruthless with its own life aswith ours. AM had blinded him." (garbled)
- LLM marker proposer returned non-list (dict) × 3 during structure detection → fell back to "No valid proposals - returning single chapter" → found 1 chapter
- 23 pronunciation entries (unchanged)
- Runtime: 17m 10s

## Next Action
Run PROMPT_fix.md to improve AM personality quality (CRITICAL #1 — two-part fix in analyzer.py and post_corrections.py)
