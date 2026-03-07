# Oracle Loop Escalation: i_have_no_mouth

## Status: Requires Human Investigation

**Generated:** 2026-02-23 03:48:21
**Text:** i_have_no_mouth
**Attempt:** 7
**Current Score:** 6.80
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
| 4 | 6.80 |
| 5 | 6.80 |
| 6 | 6.80 |
| 7 | 6.80 |

---

## Current Issues (from EVALUATION_STATE.md)

## Current Issues (Priority Order)

### CRITICAL
1. **AM (the supercomputer) COMPLETELY MISSING — 7th consecutive failure** [Completeness]
   - Problem: AM is the primary antagonist — the sentient supercomputer whose hatred drives the entire story. The title itself derives from AM's punishment of Ted. The plot_summary mentions "AM" 7+ times. Yet AM is not in the character list.
   - Evidence: 0 main_cast characters. All 5 characters are from supporting pipeline (NER). The fallback LLM call at STEP 3.1 fired (Character Extraction: 5 LLM calls) but produced 0 characters for main_cast despite grounding bypass code being present.
   - Root cause: **UNKNOWN** — the grounding bypass code at line 228-236 is correct, yet AM doesn't appear. Either (a) the LLM fallback didn't return "AM", (b) `_parse_pass1_results` couldn't parse the response, or (c) `profiles_to_characters` filtered it. Without INFO-level logging at each step, we cannot diagnose.
   - Location: `src/agents/characters.py` lines 196-240 (STEP 3.1 fallback)
   - Fix: **ADD DIAGNOSTIC LOGGING FIRST** (see escalation strategy above). Do not guess at another fix.

2. **Ted STILL not flagged as narrator — 7th consecutive failure** [Completeness / Profiles]
   - Problem: Ted is the first-person narrator. `is_narrator: false`. He's in the "Supporting Characters" table with only 5 mentions.
   - Evidence: narrative_style = "first-person retrospective" exists in JSON output. But `_get_narrative_style()` apparently still returns None at runtime despite the type-check fix being present at line 3363.
   - Root cause: **UNKNOWN** — the `hasattr(ps, "narrative_style")` fix is in the code, yet the heuristic at STEP 5.8.6 apparently didn't fire. Either `_get_narrative_style()` returns None for a different reason (e.g., `context.get_result("summaries")` returns None or doesn't have `plot_summary` attribute), or the heuristic fires but fails to select Ted.
   - Location: `src/agents/characters.py` lines 3356-3365 (`_get_narrative_style()`) and lines 796-828 (STEP 5.8.6)
   - Fix: **ADD DIAGNOSTIC LOGGING FIRST** (see escalation strategy above).

### HIGH
3. **"Jesus: unknown" relationship pollution — partially fixed** [Profiles / Presentation]
   - Problem: Jesus was successfully removed from the character list (Fix 3 worked!), but "Jesus: unknown" still appears in the relationships of Benny, Ellen, and Nimdok. Relationships are generated during profiling and baked into the profile data. The post-profiling filter removes Jesus from the character list but doesn't clean up references to Jesus in other characters' relationships.
   - Evidence: `jq '.characters[] | {name: .canonical_name, relationships: .relationships}' analysis.json` shows "Jesus: unknown" in Benny's, Nimdok's relationships and "Jesus: not mentioned" in Ellen's.
   - Location: `src/analyzer.py` `_convert_characters()` — the evidence filter removes the character but doesn't scrub relationship references
   - Fix: After removing a character via the evidence filter, also iterate all remaining characters and remove the deleted character's name from their `relationships` dict.

4. **"Age: five years" / "Age: nine years" bug in appearance.age_indication** [Profiles]
   - Problem: Benny, Ellen, Gorrister show "Age: five years" and Ted shows "Age: nine years". These are adults trapped for 109 years by AM. The "five" comes from "five survivors" context confusion.
   - Evidence: Confirmed in JSON: `appearance.age_indication` values are wrong for all characters.
   - Location: Profile generation LLM — appearance extraction misinterprets number words as ages
   - Fix: Validate age_indication: reject pure number words ("five", "nine") without explicit age context ("years old", "aged X").

5. **0/5 characters have top-level physical_description** [Profiles]
   - Problem: `physical_description` is null for all characters. Nested `appearance.summary` has some data (Benny, Gorrister) but "Unknown"/"unknown" for Ellen, Nimdok, Ted.
   - Fix: Populate top-level `physical_description` from `appearance.summary` during conversion.

6. **Ted's profile far too thin for the narrator** [Profiles]
   - Problem: Ted described as "passive, emotionally detached, compliant" — actually paranoid, self-aware, cynical, unreliable. He suspects others hate him, kills them in mercy, is psychologically complex.
   - Fix: Resolves when #2 (narrator detection) is fixed — detected narrator gets protagonist-level profiling.

### MEDIUM
7. **"hermiene" pronunciation artifact from PDF URL** [Pronunciation]
   - Problem: "hermiene" comes from `hermiene.net` URL in the PDF. Not a word in the story.
   - Fix: Filter tokens matching URL patterns (`.net`, `.com`, `.org`).

8. **Wrong IPA for "choir" and "cogito"** [Pronunciation]
   - "choir": listed as /kwɑːr/, correct is /kwaɪər/
   - "cogito": listed as /kəˈdʒiː.toʊ/, correct is /ˈkɒɡɪtoʊ/ (Latin, hard 'g')

9. **~12 common English words flagged for pronunciation** [Pronunciation]
   - palette, tinfoil, firelight, snowdrifts, loonie, piteously, spastically, sentience, sentient, eternities, puckerings, stalactites — standard English words that most narrators know.
   - Fix: Improve common-word detection or raise frequency threshold.

10. **Homographs without context-specific IPA** [Pronunciation]
    - "wind", "read", "lead", "does", "close", "subject" — all null IPA. Without context-specific pronunciation guidance, these entries are useless to a narrator.

11. **Themes are poor: "identity, ambition, loss"** [Summaries]
    - Better: hatred, dehumanization, suffering, mercy, technology/AI, imprisonment
    - "Ambition" is particularly wrong for this story about captive torture victims.

12. **Title displays as "I_Have_No_Mouth_And_I_Must_Scream" with underscores** [Presentation]
    - Should display as "I Have No Mouth, and I Must Scream"

13. **Performance timing table renders "started_at"/"ended_at" as empty rows** [Presentation]
    - The timing dict's `started_at` and `ended_at` entries get rendered as table rows with empty duration values.

### LOW
14. **Benny's voice guidance includes AM's origin story quote**
    - The "There was the Chinese AM and the Russian AM..." quote is Ted narrating about AM, not Benny's dialogue.

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
- **Fix 1**: Skip GroundingGate for plot_summary fallback → **CODE PRESENT BUT NO EFFECT** — AM still absent. Grounding bypass at line 228-236 should work but either LLM didn't return AM or parser rejected it.
- **Fix 2**: Fix `_get_narrative_style()` type check (hasattr for Pydantic) → **CODE PRESENT BUT NO EFFECT** — Either still returns None for different reason, or heuristic doesn't select Ted.
- **Fix 3**: Post-profiling evidence filter (discard 0-evidence chars) → **WORKED** — Jesus removed (5 chars vs 6). But relationship references to Jesus remain in other characters' profiles.

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
| 7 | Grounding bypass for fallback | characters.py | **Code correct, no effect** |
| 7 | _get_narrative_style() type check | characters.py | **Code correct, no effect** |
| 7 | Evidence filter for false positives | analyzer.py | **WORKED** (Jesus removed) |

**STUCK PATTERN — ESCALATION REQUIRED:**
- `characters.py` modified **7 times** for AM extraction — main_cast consistently empty
- `characters.py` modified **7 times** for narrator detection — consistently fails
- Fixes 1 and 2 in attempt 7 had **correct code** that produced **no visible change** in output
- This indicates the code paths are not executing as expected at runtime
- **The fix phase MUST add INFO-level diagnostic logging and trace actual execution before attempting more code changes**

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (same for all stages)
- Context: 32768 tokens — sufficient for a short story (~5400 words)
- Temperature: 0.7 for all stages
- Character Extraction: 5 LLM calls (same as attempt 6 = fallback fired)
- 0 low-confidence items, 0 LLM retries
- Chapter Summaries: 0 LLM calls (cached)
- Runtime: 17m 27s total

## Next Action
Run PROMPT_fix.md — **ESCALATION MODE**: Add diagnostic logging first, trace execution, then fix based on observed runtime behavior.

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

