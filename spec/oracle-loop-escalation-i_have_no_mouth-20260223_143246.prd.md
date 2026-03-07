# Oracle Loop Escalation: i_have_no_mouth

## Status: Requires Human Investigation

**Generated:** 2026-02-23 14:32:46
**Text:** i_have_no_mouth
**Attempt:** 15
**Current Score:** 8.53
**Stuck Duration:** 4 consecutive attempts with score ±0.15

---

## Why This Escalation Was Triggered

The oracle loop has been stuck on the same score (±0.15) for 4 consecutive attempts. This indicates:

1. The fixes being attempted are not addressing the root cause
2. The root cause may be in a code layer the loop hasn't been examining
3. Human investigation is needed to identify blind spots

---

## Recent Score History

| Attempt | Score |
|---------|-------|
| 12 | 8.53 |
| 13 | 8.45 |
| 14 | 8.53 |
| 15 | 8.53 |

---

## Current Issues (from EVALUATION_STATE.md)

## Current Issues (Priority Order)

### CRITICAL
1. **AM personality is STILL a plot summary narrative — 6th failed fix attempt** [Profiles]
   - Problem: AM's personality reads: `"As time and space warp under AM's control, their fragile camaraderie fractures; AM weaponizes their memories, fears, and relationships, turning trust into paranoia and love into resentment. The story…"` — this describes story events, not AM's personality. It's coherent (not garbled) but fundamentally the wrong type of content. Truncated ("The story…"). Does not capture AM's key traits: sadistic, omnipotent, hateful, creative in cruelty, imprisoned by its own existence.
   - Root cause: Every heuristic approach to extract personality from LLM-generated plot_summary text has failed because the plot_summary is narrative prose — regex/pattern approaches can't distinguish "personality-relevant prose" from "plot-relevant prose" since they're interleaved in the same sentences.
   - **6 FAILED APPROACHES SO FAR:**
     1. Attempt 10: Direct dump of plot_summary → too long, mentions everyone
     2. Attempt 11: Sentence extraction → unchanged (code didn't take effect)
     3. Attempt 12: Subject-sentence selection → unchanged (code didn't take effect)
     4. Attempt 13: Post-correction cleanup → correct code but ran before AM existed
     5. Attempt 14: Execution ordering fix → garbled source-text fragments
     6. Attempt 15: Intro-phrase extraction + quality filter → coherent plot narrative (pronouns bypass name-check)
   - **RECOMMENDED APPROACH — Set personality to `None` for safety-net characters:**
     - After 6 failed heuristic extraction attempts, the simplest reliable fix is to NOT set personality at all for safety-net characters. A null personality is strictly better than a misleading plot summary for narrator preparation.
     - The narrator still gets: role="antagonist", 74 mentions, 5 adversary relationships — this is functionally useful.
     - Null personality is honest (says "I don't have detailed personality info") vs. plot narrative (misleads the narrator with story events presented as personality).
     - Implementation: In `_plot_summary_safety_net()`, simply don't set `personality` (or set it to `None`). Remove the personality extraction logic that has failed 6 times.
   - **ALTERNATIVE — Minimal hardcoded personality from role:**
     - For safety-net characters with role="antagonist", set personality to: `{"summary": "Primary antagonist.", "traits": [], "temperament": null, "emotional_range": null}`
     - This is one step above null — tells the narrator "this is the antagonist" without any risk of plot summary contamination.
   - Location: `analyzer.py` (`_plot_summary_safety_net` personality generation logic)
   - Expected impact: AM gets clean minimal profile → removes the only source of deduction on Profiles score from code-fixable issues. Combined with favorable stochastic outcomes on other profiles → Profiles reaches 8.0.

### MEDIUM
2. **Nimdok physical_description cross-contamination** [Profiles — stochastic]
   - Problem: Nimdok described as "resembling a chimpanzee in posture and movement" — this is Benny's ape-like description from the text, not Nimdok's. Nimdok has minimal physical description in the source text.
   - This is a stochastic LLM profiling error — was correct in attempt 14, wrong again in attempt 15. Not code-fixable.

3. **Remaining pronunciation false positives** [Pronunciation]
   - "palette", "piteously", "eternities", "shoal" are standard English words.
   - Not a threshold blocker (Pronunciation at 8.0).

4. **"choir" IPA wrong** [Pronunciation]
   - Listed as /kwɑːr/, correct is /kwaɪər/.
   - Not a threshold blocker.

### LOW
5. **Ted's personality too flat** [Profiles]
   - Misses paranoid, cynical, unreliable narrator traits.
   - LLM profiling quality issue, not code-fixable.

6. **AM relationships too generic** [Profiles]
   - All say "adversary". More specific descriptions would help narrators.
   - Low priority — relationships are functional.

7. **Gorrister personality partially inaccurate** [Profiles — stochastic]
   - Described as "cruel and domineering" but in the text Gorrister is more passive/nihilistic.
   - LLM profiling quality issue, not code-fixable.

## Fix Priority for Attempt 16

**CRITICAL #1 is the ONLY remaining blocker and the ONLY code-fixable issue.**

After 6 failed heuristic attempts, the fix must be SIMPLE and RELIABLE:

### Recommended Fix: Null out safety-net personality
In `_plot_summary_safety_net()` in `analyzer.py`, remove ALL personality extraction/generation logic for safety-net characters. Set personality to `None` or omit it entirely. The current heuristic approaches have failed 6 consecutive times because they cannot distinguish personality-relevant text from plot-relevant text in LLM-generated summaries.

**Why this will work:** It eliminates the entire class of bugs. There's nothing to extract incorrectly, nothing to filter, nothing for post-correction to catch. The AM profile will show: role=antagonist, 74 mentions, 5 adversary relationships, no personality text. This is honest and functional.

**Why null is acceptable:** The post-correction docstring itself says: "Clearing (None) is always preferable to retaining a misleading plot dump." Every version of personality we've generated for AM has been misleading — garbled fragments, plot narrative, truncated text. Null is the first option that is NOT misleading.

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

---

## Fix History (Recent Attempts)

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

### Attempt 15 Fixes Applied
- **Fix 1 (Part A)**: Intro-phrase extraction in `_plot_summary_safety_net()` → **DID NOT WORK** — produced coherent plot narrative instead of adjective-based personality traits. Pronouns bypass post-correction name check.
- **Fix 2 (Part B)**: Quality filter in `clean_plot_summary_personality()` → **DID NOT TRIGGER** — personality text is coherent prose, passes length/quality heuristics despite being wrong content type.

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

---

## Code Analysis

### Files Modified During Fix Attempts (last 7 days)

```

```

### Files NOT Modified (Potential Blind Spots)

These key pipeline files have NOT been touched during fix attempts. The bug may be here:

```
src/ingestion/base.py
src/ingestion/refine.py
src/pipeline/chapter_detection/profiler.py
src/pipeline/chapter_detection/proposers/regex.py
src/pipeline/chapter_detection/proposers/llm.py
src/pipeline/chapter_detection/validator.py
src/pipeline/chapter_detection/consensus.py
src/pipeline/chapter_detection/pipeline.py
src/agents/structure.py
src/analyzer.py
```

**IMPORTANT:** When fixes in one layer don't work, the bug is often in an upstream layer:
- If `consensus.py` fixes don't work → check `profiler.py`, `proposers/`, or `ingestion/`
- If `character_extraction` fixes don't work → check `ingestion/` text normalization
- If structure detection fails → check if ingestion is destroying formatting

---

## Recommended Investigation Steps

1. **Check data flow from ingestion to detection:**
   ```bash
   # Verify source text has expected patterns
   grep -n "^[[:space:]]*V[[:space:]]*$" Test_Texts/i_have_no_mouth.txt

   # Check what ingestion does to the text
   LOG_LEVEL=DEBUG python -c "
   from src.ingestion import ingest_document
   text = ingest_document('Test_Texts/i_have_no_mouth.txt')
   # Check if patterns survive
   import re
   centered = re.findall(r'^\s{10,}[IVXLC]+\s*$', text, re.MULTILINE)
   print(f'Centered roman numerals after ingestion: {len(centered)}')
   print(centered[:5])
   "
   ```

2. **Run isolated pipeline tests:**
   ```bash
   # Test structure detection in isolation
   python -c "
   from src.pipeline.chapter_detection.pipeline import ChapterDetectionPipeline
   from src.pipeline.llm import LLMClient, LLMConfig

   with open('Test_Texts/i_have_no_mouth.txt', 'r') as f:
       text = f.read()

   config = LLMConfig.ollama(model='qwen3:4b-instruct')
   pipeline = ChapterDetectionPipeline(llm_client=LLMClient(config))
   result = pipeline.run(text)

   for ch in result.chapters:
       print(f'{ch.index}: {ch.title}, {ch.word_count} words')
   "
   ```

3. **Compare isolated test vs full CLI:**
   - If isolated test passes but CLI fails, bug is in ingestion or agent layer
   - If both fail, bug is in the pipeline itself

4. **Add diagnostic logging to blind spot files:**
   - Add logging to ingestion showing text patterns before/after normalization
   - Add logging to profiler showing TOC detection and front_matter_end

---

## State Files for Reference

- `oracle-loop/state/EVALUATION_STATE.md` - Full evaluation state
- `oracle-loop/state/manifest.json` - Test manifest
- `oracle-loop/state/checkpoints.json` - Checkpoint history
- `oracle-loop/logs/` - Recent iteration logs

---

## Resolution

Once the root cause is identified and fixed:

1. Update this PRD with the resolution
2. Restart the oracle loop: `cd oracle-loop && ./oracle-loop.sh`
3. The loop will continue from where it left off

