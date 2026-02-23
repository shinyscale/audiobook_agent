# Current Evaluation State

## Active Text
- **Name:** i_have_no_mouth
- **Attempt:** 6
- **Phase:** awaiting_evaluation
- **baseline_score:** 7.35
- **Competitive Mode:** single

## Output Files
- HTML: ../output/i_have_no_mouth/report.html
- JSON: ../output/i_have_no_mouth/analysis.json
- Timestamped: ../output/I_Have_No_Mouth_And_I_Must_Scream_20260223_030910/

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 5/10 ✗ (FAILING)
  - Completeness: 5/10
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

## Current Issues (Priority Order)

### CRITICAL
1. **AM (the supercomputer) is COMPLETELY MISSING — 4th consecutive analysis with 0 main_cast characters** [Completeness]
   - Problem: AM is the primary antagonist — a sentient supercomputer that imprisoned the 5 survivors for 109 years. It speaks directly (famous hate monologue), acts, tortures, and transforms characters. The story's title derives from AM's punishment of Ted. The plot_summary mentions AM 7+ times. The pronunciation guide includes "Mastercomputer". Yet AM is not in the character list.
   - Evidence: All 6 characters have `supporting_*` IDs — the main_cast pipeline produced **zero** characters for the **4th** consecutive attempt. Two-pass and single-pass both return 0. The supporting cast NER cannot recognize "AM" (2-letter acronym, not a PERSON entity).
   - Root cause: **main_cast.py's LLM extraction pipeline has failed every single time.** 5 attempts of fixes (JSON parsing, fallback, prompt escaping, diagnostic logging) have not worked. The [DIAG] logging added in attempt 5 was not visible because it uses `logger.debug()` which requires DEBUG log level.
   - Location: `src/pipeline/character_extraction_v2/main_cast.py`
   - **ESCALATION REQUIRED — 5 failed attempts.** Fix approach must change strategy entirely:
     1. **Run a standalone test** of main_cast extraction with visible output (print statements, not logger.debug) to see the actual LLM response
     2. **OR** bypass the broken main_cast pipeline: add a "characters from summary" fallback that extracts character names from `overview.plot_summary` when main_cast returns 0 characters. The plot_summary already names all characters including AM.
     3. **OR** add AM as a character in the supporting cast pipeline via an LLM-based supplementary search when NER misses non-PERSON entities

2. **Ted is STILL not flagged as narrator — 5th consecutive failure** [Completeness / Profiles]
   - Problem: Ted is the first-person narrator. `is_narrator: false`. He's in the "Supporting Characters" table in HTML with minimal profile data.
   - Evidence: plot_summary.narrative_style = "first-person retrospective" (correct, fix from attempt 5 worked). But narrator detection STILL fails. Ted has only 5 name-mentions (he uses "I" not his name). He's role="main" while Benny/Ellen/Gorrister/Nimdok are role="protagonist".
   - Root cause: The [DIAG] logging in narrator.py was not visible (DEBUG level). We cannot determine whether the LLM considers Ted or why it rejects him. The narrator prompt fix (rule #2 about exact names) hasn't been verified.
   - Location: `src/pipeline/character_extraction_v2/narrator.py`, `src/agents/characters.py`
   - **ESCALATION REQUIRED — 5 failed attempts.** Fix approach:
     1. Add **print()** statements (not logger.debug) to narrator.py to see the LLM response in the pipeline output
     2. **OR** add a heuristic fallback: if `narrative_style` contains "first-person" AND there's a character with low mention count who appears in the text more via pronouns (or is the least-mentioned named character but appears in every chapter), flag as narrator candidate
     3. **OR** use the plot_summary text directly: if narrative_style is first-person, search plot_summary for patterns like "{name} realizes", "{name} kills", "{name} becomes" — the subject of these summary verbs is likely the narrator

### HIGH
3. **False positive character: "Jesus" — still present after 5 attempts** [Completeness]
   - Problem: "Jesus" (4 mentions) is extracted as supporting character. Only appears as exclamation ("Jesus God", "Christ"), not as a character. Has 0 evidence entries, null profile data.
   - Evidence: `Jesus` has `evidence: []` (0 citations) while every real character has 5-8 citations. Every real character's relationships include `"Jesus": "unknown"/"no relationship mentioned"`, polluting all profiles.
   - Location: `src/pipeline/character_extraction_v2/supporting.py` — NER catches "Jesus" as PERSON entity
   - Fix: Add a post-extraction validation: any character with 0 evidence entries after profiling should be discarded. This is a robust generic filter — a character with zero textual evidence supporting their role as a character is a false positive.

4. **"Age: five years" / "Age: nine years" bug in appearance.age_indication** [Profiles]
   - Problem: `appearance.age_indication` is "five years" for Benny, Ellen, Gorrister and "nine years" for Ted. These are adults trapped for 109 years. The "five" comes from "five survivors" context confusion.
   - Evidence: `jq '.characters[] | {name: .canonical_name, appearance_age: .appearance.age_indication}'` shows wrong ages. The top-level `age_indication` field is null (was fixed previously), but `appearance.age_indication` in the nested object was never fixed. The HTML renders from this nested field.
   - Location: Profile generation pipeline — the appearance extraction LLM misinterprets "five" from "five survivors" as an age
   - Fix: Validate age_indication values: if the value is a number word ("five", "nine") without age-related context ("years old", "aged"), reject it. Or add a rule: if the same number appears in the text as a group count ("five survivors"), it's not an age.

5. **0/6 characters have top-level physical_description — profiles partially empty** [Profiles]
   - Problem: Top-level `physical_description` is null for all characters, though `appearance.summary` has data for 4 characters (Benny, Ellen, Gorrister, Nimdok). Ted has no appearance data at all.
   - Evidence: The nested `appearance` object has decent data: Benny's "monkey-like face with radiation scars", Ellen's "walks with a limp", etc. But the top-level `physical_description` field is null.
   - Root cause: All characters are from the supporting cast pipeline. The profile pipeline generates `appearance`, `personality`, `voice_guidance` nested objects but doesn't populate the top-level summary fields.
   - Impact: Moderate — the HTML renders from nested objects and looks reasonable for 4 characters. But Ted's profile is nearly empty.
   - Fix: This is a secondary concern. Primary fix is getting AM and Ted's narrator status correct (issues #1 and #2).

6. **Ted demoted to "Supporting Characters" table — narrator gets minimal detail** [Presentation / Profiles]
   - Problem: Ted (role="main") is rendered in the "Supporting Characters" table with a truncated 1-line description and no expanded profile. He has no appearance, personality, voice guidance, or evidence sections rendered.
   - Evidence: HTML lines 1804-1815: Ted appears alongside Jesus in the supporting table
   - Fix: Resolves when #2 (narrator detection) is fixed. A detected narrator would get protagonist role and full profile. Alternatively, any character with role="main" should render in the main characters section.

### MEDIUM
7. **"hermiene" pronunciation artifact from PDF URL** [Pronunciation]
   - Problem: "hermiene" comes from `hermiene.net` URL in the PDF. Not a word in the story.
   - Location: Text ingestion or pronunciation proposer
   - Fix: Filter tokens matching URL patterns (`.net`, `.com`, `.org`, etc.)

8. **~12 common English words flagged for pronunciation** [Pronunciation]
   - Problem: palette, tinfoil, firelight, snowdrifts, loonie, piteously, spastically, sentience, sentient, eternities, puckerings, stalactites — standard English words
   - Location: `src/pipeline/pronunciation_guide/` common-word filtering
   - Fix: Improve compound word and suffix detection

9. **Self-evident compound words in pronunciation** [Pronunciation]
   - Problem: "darkway", "deckplates", "floorplates" — phonetically transparent
   - Fix: Same as #8

10. **Incorrect IPA for "choir" and "cogito"** [Pronunciation]
    - "choir": listed as /kwɑːr/, correct is /kwaɪər/
    - "cogito": listed as /kəˈdʒiː.toʊ/, correct is /ˈkɒɡɪtoʊ/ (Latin, hard 'g')
    - Location: LLM IPA generation

11. **Homographs without disambiguation** [Pronunciation]
    - "wind", "read", "lead", "does", "close", "subject" — all with null IPA, useless without context
    - Low priority systemic issue

### LOW
12. **Relationships polluted with "Jesus": "unknown"**
    - Resolves when #3 (Jesus false positive) is fixed

13. **Themes "identity, ambition, loss" — poor thematic analysis**
    - Better themes: hatred, dehumanization, suffering, mercy, technology/AI
    - "Ambition" is particularly wrong for this story

14. **Title displays as "I_Have_No_Mouth_And_I_Must_Scream" with underscores**
    - Should display as "I Have No Mouth, and I Must Scream"

## Fix Strategy for Attempt 6

**The main_cast pipeline has failed 5 consecutive times.** Diagnostic logging added in attempt 5 was invisible because it used `logger.debug()`. The fix phase MUST take a fundamentally different approach:

### Priority 1: Get AM into the character list (CRITICAL #1)
**Strategy: Add a "characters from plot_summary" fallback in characters.py**

When `main_cast_characters` is empty after extraction, parse character names from `overview.plot_summary.plot_summary` text. The plot summary already mentions: "Ted, Ellen, Nimdok, Gorrister, and Benny" and "the malevolent AI known as AM". Extract these names and create main_cast entries for any that don't already exist in the character list. This bypasses the broken main_cast.py entirely.

### Priority 2: Flag Ted as narrator (CRITICAL #2)
**Strategy: Add a heuristic narrator fallback**

If narrator detection returns no narrator AND narrative_style contains "first-person", check which character is the grammatical subject of key plot_summary sentences (e.g., "Ted realizes", "Ted kills", "Ted becomes"). That character is the narrator. This doesn't require LLM — just text pattern matching on the plot_summary.

### Priority 3: Remove Jesus false positive (HIGH #3)
**Strategy: Post-profiling evidence filter**

After profiling, discard any character with 0 evidence entries. This is a robust generic filter.

### Priority 4: Fix age_indication bug (HIGH #4)
**Strategy: Validate in profile pipeline**

Reject age_indication values that are pure number words without "years old" or "aged" context.

## Fix History

### Attempt 1 Fixes Applied
- **Fix 1**: Move supporting cast mention search to BEFORE promotion (STEP 5.7.5) → **WORKED** (characters promoted)
- **Fix 2**: Add narrator re-detection after promotion (STEP 5.8.5) → **DID NOT WORK**
- **Fix 3**: Fix narrator prompt to account for 3rd-person summaries → **DID NOT WORK**
- **Fix 4**: Proper names must start with uppercase → **WORKED** ("bush" removed)
- **Bug fix**: Variable shadowing in STEP 5.10.5 → **Fixed**

### Attempt 3 Fixes Applied
- **Fix 1**: Robust LLM JSON parsing (accept "name" key, try wrapper keys) → **DID NOT WORK** (main_cast still 0)
- **Fix 2**: Two-pass → single-pass fallback in extract() → **Fires but still 0 characters**
- **Fix 3**: STEP 5.8.5 re-detection condition fix → **DID NOT WORK** (narrator still undetected)
- **Fix 4**: Include plot_summary in narrator detection prompt → **DID NOT WORK** (narrator still undetected)
- **Fix 5**: Pronunciation artifact detection improvements → **PARTIALLY WORKED** (6/7 artifacts removed)

### Attempt 4 Fix Applied
- **Fix**: Escape JSON example braces in MAIN_CAST_PROMPT → **Fixed crash** (pipeline ran without KeyError)

### Attempt 5 Fixes Applied (diagnostic + data flow)
- **Fix 1**: Added `[DIAG]` debug logging to main_cast.py → **NOT VISIBLE** (logger.debug needs DEBUG level)
- **Fix 2**: Added `[DIAG]` debug logging to narrator.py → **NOT VISIBLE** (logger.debug needs DEBUG level)
- **Fix 3**: Added `[DIAG]` debug logging to characters.py → **NOT VISIBLE** (logger.debug needs DEBUG level)
- **Fix 4**: Fixed `_get_plot_summary()` — was always returning None → **WORKED** (plot_summary.narrative_style now correct)
- **Fix 5**: Improved NARRATOR_DETECTION_PROMPT rule #2 → **DID NOT WORK** (Ted still not narrator)

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
| 3 | STEP 5.8.5 condition too restrictive | characters.py | No change — narrator still undetected |
| 3 | Narrator prompt missing plot_summary | narrator.py | No change — narrator still undetected |
| 3 | Pronunciation concatenation artifacts | cmu_proposer.py | Partially fixed (6/7 removed) |
| 4 | MAIN_CAST_PROMPT crash (unescaped braces) | main_cast.py | Fixed crash |
| 5 | main_cast LLM produces 0 chars — added [DIAG] logging | main_cast.py | Logging not visible (DEBUG level) |
| 5 | Narrator still undetected — added [DIAG] logging | narrator.py | Logging not visible (DEBUG level) |
| 5 | _get_plot_summary() always returns None | characters.py | Fixed — plot_summary now available |
| 5 | Narrator prompt doesn't specify exact name needed | narrator.py | No change — narrator still undetected |

**STUCK PATTERN DETECTED:**
- `main_cast.py` modified 4 times (attempts 3, 3, 4, 5) — still produces 0 characters
- `narrator.py` modified 4 times (attempts 1, 3, 5, 5) — still fails to detect narrator
- `characters.py` modified 4 times (attempts 1, 1, 3, 5) — fixes worked but didn't resolve root issues
- **Recommendation: ESCALATE upstream. Stop modifying main_cast.py parsing. Add fallback logic in characters.py to extract characters from plot_summary when main_cast returns empty.**

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (same for all stages)
- Context: 32768 tokens — sufficient for a short story (~5400 words)
- Temperature: 0.7 for all stages — reasonable
- Two-pass→single-pass fallback fires but still returns 0 characters
- 0 low-confidence items, 0 LLM retries
- Character Extraction: only 4 LLM calls, 3055 tokens — suspiciously low (suggests main_cast prompt may not be reaching the LLM or is getting empty responses)

## Pipeline Notes (Attempt 5)
- Runtime: 17m 16s, 60 LLM calls, 72,732 tokens
- "Two-pass extraction returned 0 characters; retrying with single-pass" — still 0
- plot_summary.narrative_style = "first-person retrospective" (correct)
- structure.narrative_style = null (inconsistency)
- Chapter Summaries: 0 LLM calls (cached or generated without LLM)
- "LLM marker proposer returned non-list: <class 'dict'>" × 3
- "LLM validation failed (got dict), keeping batch candidates" in supporting cast
- Character Extraction stage: 4 LLM calls for 6 characters = all from supporting cast validation, none from main_cast

## Attempt 6 Fixes Applied

### Fix 1: Plot Summary Character Fallback (CRITICAL #1 — AM missing)
- **Root cause:** main_cast LLM extraction has failed 5 consecutive times (unknown reason — LLM model may not parse complex prompts reliably)
- **Fix:** Added STEP 3.1 fallback in `characters.py:run()` — when `main_cast` is empty after grounding, makes a simple LLM call on just the `plot_summary` text with a minimal 4-line prompt
- **Universality:** Only fires when main_cast is empty (defensive safety net for any book). Does not affect books where main_cast extraction succeeds.
- **Modified:** `src/agents/characters.py` lines 196-242
- **Smoke test:** Import succeeds, all character extraction tests pass

### Fix 2: Heuristic Narrator Fallback (CRITICAL #2 — Ted not narrator)
- **Root cause:** LLM narrator detection keeps failing to set narrator_character_id, likely because main_cast was empty at STEP 4 and re-detection at STEP 5.8.5 also fails or matches wrong character
- **Fix:** Added STEP 5.8.6 heuristic fallback — when `narrative_style` contains "first-person" (from summaries metadata) AND narrator_character_id is still None, uses universal invariant: first-person narrator has lowest name-mention count (they use "I" not their name)
- **Helper methods added:** `_get_narrative_style()`, `_heuristic_narrator_from_mention_count()`
- **Universality:** Only fires when LLM-based detection fails. The "lowest mention count" invariant is universal across first-person fiction.
- **Modified:** `src/agents/characters.py` lines 798-830, 3358-3400

## Pipeline Notes (Attempt 6)
- Runtime: 17m 14s, 61 LLM calls, 73,394 tokens
- **Fix 1 (AM fallback) FIRED**: "V2 Step 3.1 FALLBACK: main_cast empty after grounding. Retrying with simpler prompt on plot_summary."
- Character Extraction: 5 LLM calls (was 4) — 1 extra from fallback
- 6 characters found (same count as before) — "1 more" beyond the 5 survivors could be AM
- **Narrator still undetected**: "No definitive narrator identified yet" and "No definitive narrator identified from plot summary"
- Fix 2 (heuristic narrator fallback from mention count) did not produce result — needs evaluation to verify
- "LLM marker proposer returned non-list: dict" × 3 — same as before
- Chapter Summaries: 0 LLM calls (cached)

## Next Action
Run PROMPT_evaluate.md to evaluate attempt 6 output.
