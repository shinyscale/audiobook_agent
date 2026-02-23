# Current Evaluation State

## Active Text
- **Name:** i_have_no_mouth
- **Attempt:** 6
- **Phase:** awaiting_fix
- **baseline_score:** 7.35
- **Competitive Mode:** single

## Output Files
- HTML: ../output/i_have_no_mouth/report.html
- JSON: ../output/i_have_no_mouth/analysis.json
- Timestamped: ../output/I_Have_No_Mouth_And_I_Must_Scream_20260223_030910/

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 5/10 ✗ (FAILING)
  - Completeness: 4/10
  - Identity Resolution: 9/10
  - Alias Grouping: 7/10
- Character Profiles: 5/10 ✗ (FAILING)
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 6/10 ✗ (FAILING)
- HTML Presentation: 7/10 ✗ (FAILING)
- **Overall: 6.80/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (4 categories below threshold)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 7.35 | 0.00 | Baseline. AM missing, false positives, pronunciation artifacts |
| 2 | 7.40 | +0.05 | bush removed, roles improved, but AM still missing, narrator still undetected |
| 3 | CRASH | - | Pipeline crash: KeyError in MAIN_CAST_PROMPT format() due to unescaped JSON braces |
| 4 | 6.80 | -0.55 | Artifacts fixed but AM STILL missing, narrator STILL undetected, profiles empty, "Age: five years" bug |
| 5 | 6.80 | -0.55 | No change from attempt 4. [DIAG] logging not visible (needs DEBUG level). plot_summary fix worked but didn't propagate to narrator detection. |
| 6 | 6.80 | -0.55 | Fallback fired (5 LLM calls) but AM still missing — likely grounding failure. Heuristic narrator didn't fire — `_get_narrative_style()` returns None. |

## Root Cause Analysis for Attempt 6 Fix Failures

### Why Fix 1 (AM Fallback) Failed
The fallback at STEP 3.1 **did fire** (Character Extraction: 5 LLM calls, up from 4). But AM did NOT appear in the output. Two likely causes:
1. **Grounding Gate rejects "AM"**: The fallback runs results through `GroundingGate(min_mentions=3)`. The mention searcher must find at least 3 text occurrences of "AM" to pass. But "AM" is a 2-letter all-caps word — case-sensitive search may find 0 matches (if the searcher lowercases), or case-insensitive search would match thousands of "am" ("I am"), making it unreliable. Either way, grounding likely rejects AM.
2. **LLM may not have returned AM**: Without visible logging, we can't confirm the LLM actually returned AM in its response. But the plot_summary clearly mentions "AM" 7+ times, so it should.

**Fix approach**: Characters from the plot_summary fallback are already "grounded" by virtue of appearing in the LLM-generated plot summary. **Skip the grounding gate for the fallback**, or set `min_mentions=0` for fallback characters.

### Why Fix 2 (Heuristic Narrator) Failed
The condition at line 805-809 requires `_get_narrative_style()` to return a string containing "first-person". This method (line 3358-3365) does:
```python
ps = summaries_result.plot_summary
if isinstance(ps, dict):
    return ps.get("narrative_style")
```
The `isinstance(ps, dict)` check likely **fails** because `plot_summary` is a Pydantic model object (or similar), not a plain dict. The JSON output shows `narrative_style: "first-person retrospective"` — the data exists but the type check blocks access.

**Fix approach**: Change `isinstance(ps, dict)` to also handle attribute access on objects: `getattr(ps, 'narrative_style', None)` or convert with `ps.model_dump()` if Pydantic.

## Current Issues (Priority Order)

### CRITICAL
1. **AM (the supercomputer) COMPLETELY MISSING — 6th consecutive failure** [Completeness]
   - Problem: AM is the primary antagonist — a sentient supercomputer. The story's title derives from AM's punishment of Ted. The plot_summary mentions "AM" 7+ times. Yet AM is not in the character list.
   - Evidence: 0 main_cast characters. All 6 characters are from supporting pipeline (NER). The fallback LLM call at STEP 3.1 fired but produced 0 additional characters — likely because the GroundingGate rejects "AM" (2-letter word, case sensitivity issue with mention search).
   - Root cause: **GroundingGate with min_mentions=3 cannot handle "AM"** — case-sensitive search finds 0, case-insensitive matches thousands of "am" (common word). The fallback characters are already confirmed by plot_summary and should NOT need grounding.
   - Location: `src/agents/characters.py` lines 228-234 (STEP 3.1 fallback grounding)
   - Fix: **Skip grounding for plot_summary fallback characters** — set `min_mentions=0` for the fallback GroundingGate, or bypass it entirely. Characters extracted from the LLM-generated plot summary are inherently grounded (they drove the plot). Alternatively, add these characters directly to `main_cast` without a grounding gate.

2. **Ted STILL not flagged as narrator — 6th consecutive failure** [Completeness / Profiles]
   - Problem: Ted is the first-person narrator. `is_narrator: false`. He's in the "Supporting Characters" table in HTML with minimal profile data.
   - Evidence: narrative_style = "first-person retrospective" in JSON output (correct). But `_get_narrative_style()` returns None because it checks `isinstance(ps, dict)` and the plot_summary is likely a Pydantic model, not a dict.
   - Root cause: **Type mismatch in `_get_narrative_style()`** — the `isinstance(ps, dict)` check at line 3363 rejects Pydantic model objects. The data exists but the accessor fails.
   - Location: `src/agents/characters.py` lines 3358-3365 (`_get_narrative_style()`)
   - Fix: Replace `isinstance(ps, dict)` with a duck-typing approach:
     ```python
     if isinstance(ps, dict):
         return ps.get("narrative_style")
     elif hasattr(ps, "narrative_style"):
         return getattr(ps, "narrative_style", None)
     ```
     This handles both dict and Pydantic model objects.

### HIGH
3. **False positive character: "Jesus" — still present after 6 attempts** [Completeness]
   - Problem: "Jesus" (4 mentions) is extracted as supporting character. Only appears as exclamation ("Jesus God", "Christ"), not as a character. Has 0 evidence entries, null personality, null voice_guidance.
   - Evidence: `evidence: []` (0 citations), `personality: null`, `voice_guidance: null`. Every real character has 5-8 citations. Every real character's relationships include `"Jesus": "unknown"`, polluting all profiles.
   - Location: `src/pipeline/character_extraction_v2/supporting.py` — NER catches "Jesus" as PERSON entity
   - Fix: Add a post-profiling validation: any character with 0 evidence entries after profiling should be discarded. This is robust and generic — a character with zero textual evidence is a false positive.

4. **"Age: five years" / "Age: nine years" bug in appearance.age_indication** [Profiles]
   - Problem: `appearance.age_indication` is "five years" for Benny, Ellen, Gorrister and "nine years" for Ted. These are adults trapped for 109 years. The "five" comes from "five survivors" context confusion.
   - Evidence: `jq '.characters[] | {name: .canonical_name, appearance_age: .appearance.age_indication}'` confirms wrong ages.
   - Location: Profile generation pipeline — appearance extraction LLM misinterprets number words
   - Fix: Validate age_indication values: reject pure number words ("five", "nine") without explicit age context ("years old", "aged").

5. **0/6 characters have top-level physical_description — profiles partially empty** [Profiles]
   - Problem: Top-level `physical_description` is null for all characters. Nested `appearance.summary` has data for Benny and Gorrister but "Unknown"/"unknown" for Ellen, Nimdok, and Ted.
   - Root cause: Supporting cast pipeline doesn't populate top-level summary fields from nested objects.
   - Impact: Moderate — secondary to AM and narrator issues.

6. **Ted's profile far too thin for the narrator** [Profiles]
   - Problem: Ted described as "passive, emotionally detached, compliant" — but he's actually paranoid, self-aware, cynical, and unreliable. He suspects others hate him, he kills them in an act of mercy, he's the most psychologically complex character.
   - Evidence: The text has Ted constantly analyzing others' motives, expressing paranoia, and making sardonic observations. The profile misses all of this.
   - Fix: Resolves when #2 (narrator detection) is fixed — a detected narrator gets protagonist-level profiling.

### MEDIUM
7. **"hermiene" pronunciation artifact from PDF URL** [Pronunciation]
   - Problem: "hermiene" comes from `hermiene.net` URL in the PDF. Not a word in the story.
   - Fix: Filter tokens matching URL patterns (`.net`, `.com`, `.org`, etc.)

8. **~12 common English words flagged for pronunciation** [Pronunciation]
   - Problem: palette, tinfoil, firelight, snowdrifts, loonie, piteously, spastically, sentience, sentient, eternities, puckerings, stalactites — standard English
   - Fix: Improve compound word and suffix detection

9. **Self-evident compound words in pronunciation** [Pronunciation]
   - Problem: "darkway", "deckplates", "floorplates" — phonetically transparent
   - Fix: Same as #8

10. **Incorrect IPA for "choir" and "cogito"** [Pronunciation]
    - "choir": listed as /kwɑːr/, correct is /kwaɪər/
    - "cogito": listed as /kəˈdʒiː.toʊ/, correct is /ˈkɒɡɪtoʊ/ (Latin, hard 'g')

11. **Homographs without disambiguation** [Pronunciation]
    - "wind", "read", "lead", "does", "close", "subject" — all null IPA, useless without context

12. **Themes are poor: "identity, ambition, loss"** [Summaries]
    - Better: hatred, dehumanization, suffering, mercy, technology/AI, imprisonment
    - "Ambition" is particularly wrong for this story

13. **Title displays as "I_Have_No_Mouth_And_I_Must_Scream" with underscores** [Presentation]
    - Should display as "I Have No Mouth, and I Must Scream"

### LOW
14. **Relationships polluted with "Jesus": "unknown"**
    - Resolves when #3 (Jesus false positive) is fixed

15. **Benny's voice guidance includes AM's origin story quote**
    - The AM origin monologue ("At first it meant Allied Mastercomputer...") is attributed as Benny's example_quote. This is actually Ted narrating/remembering. Ted tells this information about AM; it's not Benny's dialogue.

## Fix Strategy for Attempt 7

**CRITICAL FIXES ONLY — target 3 specific bugs:**

### Priority 1: Fix AM Grounding (CRITICAL #1)
**Strategy: Skip GroundingGate for plot_summary fallback characters**

In STEP 3.1 (characters.py lines 228-234), the fallback extracts characters from the plot_summary then runs them through GroundingGate. This kills AM because "AM" is a 2-letter word that can't be grounded by text search.

Fix: After `profiles_to_characters()` and `search_all()`, add fallback characters directly to `main_cast` WITHOUT the grounding gate. They are already "grounded" — the LLM identified them from the plot summary, which is itself a summary of the text. At minimum, set `min_mentions=0` for the fallback gate.

### Priority 2: Fix `_get_narrative_style()` type check (CRITICAL #2)
**Strategy: Support Pydantic model objects in addition to dicts**

In `_get_narrative_style()` (characters.py line 3363), change:
```python
if isinstance(ps, dict):
    return ps.get("narrative_style")
```
to:
```python
if isinstance(ps, dict):
    return ps.get("narrative_style")
elif hasattr(ps, "narrative_style"):
    return getattr(ps, "narrative_style", None)
```

This allows the heuristic narrator fallback (STEP 5.8.6) to actually fire, which should identify Ted (lowest mention count, 5, among candidates in the plot_summary).

### Priority 3: Remove Jesus false positive (HIGH #3)
**Strategy: Post-profiling evidence filter**

After profiling completes, discard any character whose `evidence` list is empty (length 0). Jesus has 0 evidence entries while every real character has 5-8. This is a robust generic filter.

### NOT fixing in this attempt:
- Age bug (#4) — won't block passing (profiles need AM and narrator first)
- Pronunciation issues (#7-11) — marginal impact
- Themes (#12) — low weight
- Title underscores (#13) — cosmetic

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
- **Fix 1**: Plot summary character fallback (STEP 3.1) → **FIRED but AM not grounded** — GroundingGate with min_mentions=3 rejects "AM" (2-letter word, case sensitivity issue)
- **Fix 2**: Heuristic narrator fallback (STEP 5.8.6) → **DID NOT FIRE** — `_get_narrative_style()` returns None because `isinstance(ps, dict)` fails on Pydantic model

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

**STUCK PATTERN DETECTED:**
- `main_cast.py` modified 4 times — main_cast LLM consistently returns 0 characters (abandoned, using fallback)
- `narrator.py` modified 4 times — LLM narrator detection consistently fails (abandoned, using heuristic)
- `characters.py` modified 6 times — fallback approaches keep failing on edge cases:
  - STEP 3.1 fallback fires but grounding kills AM
  - STEP 5.8.6 heuristic doesn't fire due to type mismatch
- **Both fixes in attempt 6 were architecturally correct but had implementation bugs**
- **Attempt 7 should fix these specific bugs (grounding bypass + type check) rather than try new approaches**

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (same for all stages)
- Context: 32768 tokens — sufficient for a short story (~5400 words)
- Temperature: 0.7 for all stages
- Character Extraction: 5 LLM calls (1 more than attempt 5 = fallback fired)
- 0 low-confidence items, 0 LLM retries
- Chapter Summaries: 0 LLM calls (cached)
- Runtime: 16m 45s, 61 LLM calls, 73,394 tokens

## Next Action
Run PROMPT_fix.md to fix the two implementation bugs (grounding bypass for AM, type check for narrator heuristic) and add post-profiling evidence filter for Jesus.
