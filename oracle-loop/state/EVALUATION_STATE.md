# Current Evaluation State

## Active Text
- **Name:** i_have_no_mouth
- **Attempt:** 7
- **Phase:** awaiting_fix
- **baseline_score:** 7.35
- **Competitive Mode:** single

## Output Files
- HTML: ../output/i_have_no_mouth/report.html
- JSON: ../output/i_have_no_mouth/analysis.json
- Timestamped: ../output/I_Have_No_Mouth_And_I_Must_Scream_20260223_034103/

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 5/10 ✗ (FAILING)
  - Completeness: 5/10
  - Identity Resolution: 9/10
  - Alias Grouping: 6/10
- Character Profiles: 5/10 ✗ (FAILING)
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 6/10 ✗ (FAILING)
- HTML Presentation: 7/10 ✗ (FAILING)
- **Overall: 6.80/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (4 categories below threshold) — **STUCK: 4 consecutive attempts at 6.80**

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

## ESCALATION REQUIRED

**The oracle loop is STUCK.** The same two critical bugs (AM missing, narrator undetected) have persisted across attempts 4-7 with a stable score of 6.80. Targeted fixes keep "looking correct" in the code but producing no change in output. This indicates a fundamental misunderstanding of the runtime data flow.

**Evidence of being stuck:**
- `characters.py` modified 6 times for AM extraction — main_cast LLM consistently returns 0, fallback consistently fails to surface AM
- `characters.py` modified 6 times for narrator detection — LLM narrator detection fails, heuristic narrator fails
- Fix 1 (grounding bypass) code is present and correct at line 228-236, yet AM still absent
- Fix 2 (type check) code is present and correct at line 3363, yet narrator still undetected
- Only Fix 3 (evidence filter for Jesus) actually worked

**Root cause hypothesis:** The fixes target the right logic but something upstream prevents the code paths from executing as expected. Without runtime diagnostic output visible at INFO level, we cannot determine WHY.

**ESCALATION STRATEGY FOR ATTEMPT 8:**

The fix phase MUST do the following BEFORE making any code changes:

1. **Add INFO-level logging (NOT DEBUG) at every critical decision point:**
   - In STEP 3.1 fallback: log `fallback_result` type and content (first 500 chars)
   - In STEP 3.1: log `fallback_profiles` count and names
   - In STEP 3.1: log `fallback_chars` count and names
   - In `_get_narrative_style()`: log `summaries_result` type, whether it has `plot_summary`, what type `ps` is, and whether `narrative_style` attribute exists
   - In STEP 5.8.6: log each condition (`narrative_style`, `narrator_info.narrator_character_id`, `main_cast` length)

2. **Run the analysis with logging visible** (`--log-level INFO` or similar)

3. **Read the logs to identify the ACTUAL failure point** — where does the data diverge from expectations?

4. **Only THEN apply targeted fixes** based on observed runtime behavior, not inferred behavior.

**Alternative approach if diagnostic logging is impractical:**
- **Direct plot_summary NER**: Instead of relying on the main_cast LLM, parse the plot_summary text with spaCy NER + regex for "AM" specifically. Characters found in the plot_summary that don't exist in main_cast or supporting_cast should be added directly. This bypasses the entire LLM extraction chain for plot-summary-confirmed characters.

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
