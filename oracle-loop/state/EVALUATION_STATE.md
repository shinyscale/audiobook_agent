# Current Evaluation State

## Active Text
- **Name:** i_have_no_mouth
- **Attempt:** 4
- **Phase:** awaiting_fix
- **baseline_score:** 7.35
- **Competitive Mode:** single

## Output Files
- HTML: ../output/i_have_no_mouth/report.html
- JSON: ../output/i_have_no_mouth/analysis.json
- Timestamped: ../output/I_Have_No_Mouth_And_I_Must_Scream_20260223_014514/

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
**Status:** FAIL (4 categories below threshold)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 7.35 | 0.00 | Baseline. AM missing, false positives, pronunciation artifacts |
| 2 | 7.40 | +0.05 | bush removed, roles improved, but AM still missing, narrator still undetected |
| 3 | CRASH | - | Pipeline crash: KeyError in MAIN_CAST_PROMPT format() due to unescaped JSON braces |
| 4 | 6.80 | -0.55 | Artifacts fixed but AM STILL missing, narrator STILL undetected, profiles empty, "Age: five years" bug persists |

## Current Issues (Priority Order)

### CRITICAL
1. **AM (the supercomputer) is COMPLETELY MISSING — 3rd consecutive analysis with 0 main_cast characters** [Completeness]
   - Problem: AM is the primary antagonist — a sentient supercomputer that imprisoned the 5 survivors for 109 years. It speaks directly (famous hate monologue), acts, tortures, and transforms characters. The story's title derives from AM's punishment of Ted. The plot_summary mentions AM 7+ times. The pronunciation guide even includes "Mastercomputer". Yet AM is not in the character list.
   - Evidence: All 6 characters have `supporting_*` IDs — the main cast pipeline produced **zero** characters for the 3rd consecutive attempt. The two-pass→single-pass fallback (added in attempt 3) fired successfully but STILL produced 0 main_cast characters. The supporting cast pipeline uses NER which doesn't recognize "AM" as a character (it's a 2-letter uppercase acronym, not a PERSON entity).
   - Root cause analysis: **The main_cast LLM pipeline has failed 3 times.** The single-pass fallback fires but still produces nothing. This suggests either: (a) the LLM response format doesn't match what the parser expects (despite attempt 3 adding flexible key parsing), (b) the text/summary passed to main_cast is malformed, or (c) the model simply doesn't extract characters for short single-chapter texts. Meanwhile, the supporting cast NER cannot catch "AM" because it's an acronym, not a standard PERSON entity.
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` (LLM extraction) and `src/pipeline/character_extraction_v2/supporting.py` (NER fallback)
   - Fix approach: **This has failed 3 attempts. ESCALATE.** Two approaches needed simultaneously:
     1. **Debug main_cast**: Add logging to capture the actual LLM response text before parsing. Determine WHY 0 characters are extracted. Is the LLM returning valid JSON that the parser drops? Is it returning empty results? Log the raw response.
     2. **Supporting cast fallback**: If main_cast produces 0 characters, the supporting cast pipeline should do a supplementary LLM-based character search to catch non-NER entities (acronyms like AM, non-PERSON entities that function as characters). Alternatively, the plot_summary already names AM — use it as a signal to inject characters the NER missed.

2. **Ted is STILL not flagged as narrator — 4th consecutive failure** [Completeness / Profiles]
   - Problem: Ted is the first-person narrator. `is_narrator: false`. `narrative_style` is "unknown" in structure overview. Plot summary correctly identifies "first-person retrospective" — this signal exists but narrator detection ignores it.
   - Evidence: The story is told entirely from Ted's "I" perspective. Fixes in attempts 1 and 3 (STEP 5.8.5 condition fix, plot_summary inclusion in narrator prompt) did not work.
   - Root cause analysis: Ted has only 5 name-mentions (as narrator he uses "I" not his name). He's classified as "main" role but may not be considered as a narrator candidate because he's not "protagonist" role. ALSO, narrative_style in `overview.structure` is "unknown" while `overview.plot_summary.narrative_style` says "first-person retrospective" — these are different fields and narrator detection may read from the wrong one.
   - Location: `src/pipeline/character_extraction_v2/narrator.py`, `src/agents/characters.py` (STEP 5.8.5)
   - Fix approach: **ESCALATE — 4 failed attempts.** Add debug logging to narrator detection to capture: (a) which candidates it considers, (b) what the LLM responds, (c) why it concludes "no narrator". The narrative_style inconsistency (unknown vs first-person retrospective) is a concrete bug: if plot_summary says first-person, the structure overview should too, and narrator detection should use this.

### HIGH
3. **False positive character: "Jesus" — still present after 4 attempts** [Completeness]
   - Problem: "Jesus" (4 mentions) is extracted as supporting character. Only appears as exclamation ("Jesus God", "Christ"), not as an actual character. Has zero evidence entries, zero profile data.
   - Evidence: Empty profile. Every real character's relationship dict has `"Jesus": "unknown"`, polluting profiles.
   - Location: `src/pipeline/character_extraction_v2/supporting.py` — NER catches "Jesus" as PERSON
   - Fix approach: Add a post-extraction filter: if a character has 0 evidence entries AND 0 profile data (no description, no personality, no aliases), discard it. Alternatively, add a blocklist of exclamatory names ("Jesus", "Christ", "God", "Lord") that require actual character evidence (dialogue, actions, relationships) to be retained.

4. **"Age: five years" incorrectly displayed for Benny, Ellen, Gorrister in HTML** [Profiles]
   - Problem: Lines 1036, 1234, 1442 of report.html show "Age: five years". The characters are adults trapped for 109 years. The JSON `age_indication` is null (fixed previously), but the HTML rendering pipeline independently extracts "five years" from "five survivors" context.
   - Evidence: HTML profiles show wrong age. JSON has null age. The rendering pipeline is using a different data source than the JSON age_indication field.
   - Location: The HTML template rendering or the profile generation pipeline that feeds into HTML. Not the `age_indication` field itself (that's null).
   - Fix approach: Find where the HTML "Age:" field is sourced. It's NOT from `age_indication` (that's null). There must be a separate profile field or rendering logic extracting age from text. Apply the same "five" ≠ age validation.

5. **0/6 characters have physical_description — empty profiles** [Profiles]
   - Problem: All `physical_description` fields are null despite the source text providing vivid physical descriptions (Benny's ape-like transformation, Ted's self-description, Ellen's appearance).
   - Evidence: `Characters with physical_description: 0/6`
   - Root cause analysis: All characters are from the supporting cast pipeline. The supporting cast may not run the full profile pipeline (descriptions, appearance). Main cast characters would get full profiles, but main cast produced 0 characters.
   - Location: Profile generation pipeline — may only run on main_cast characters, not supporting_cast
   - Fix approach: This likely resolves when issue #1 (AM missing / main_cast failure) is fixed. If main_cast successfully extracts characters, they'll get full profiles. If not, the profile pipeline should also run on promoted supporting cast characters.

6. **Ted demoted to "Supporting Characters" table in HTML — narrator gets least detail** [Profiles / Presentation]
   - Problem: Ted is role="main" in JSON but rendered in the Supporting Characters table with truncated description and no full profile. The narrator/protagonist of the story gets the least detailed entry.
   - Evidence: HTML lines 1807-1817 show Ted in supporting table. No appearance, personality, voice guidance, or evidence sections rendered.
   - Fix approach: Resolves when issue #2 (narrator detection) is fixed — a detected narrator should get protagonist role and full profile rendering. Alternatively, any character with role="main" should render in the main characters section, not supporting.

### MEDIUM
7. **"hermiene" pronunciation artifact from PDF source URL** [Pronunciation]
   - Problem: "hermiene" comes from `hermiene.net` URL embedded in the PDF. Not a word in the story.
   - Location: `src/pipeline/pronunciation_guide/proposers/cmu_proposer.py` or input text filtering
   - Fix approach: Filter tokens that match URL patterns (contain `.net`, `.com`, `.org`, etc.) or add URL stripping during text ingestion.

8. **~12 common English words flagged as needing pronunciation** [Pronunciation]
   - Problem: palette, tinfoil, firelight, snowdrifts, loonie, piteously, spastically, sentience, sentient, eternities, puckerings, stalactites — all standard English words a narrator would know.
   - Location: `src/pipeline/pronunciation_guide/` common-word filtering
   - Fix approach: Improve common-word filtering. Compound words with common components (tin+foil, fire+light, snow+drifts) and words with standard suffixes (-ly, -ness, -ence/-ent, -tion, -ings) derived from common roots should be excluded.

9. **Self-evident compound words in pronunciation** [Pronunciation]
   - Problem: "darkway", "deckplates", "floorplates" — compound words that are phonetically transparent.
   - Fix approach: Same as #8 — compound word detection.

10. **Incorrect IPA for "choir"** [Pronunciation]
    - Problem: IPA listed as /kwɑːr/. Correct is /kwaɪər/.
    - Location: LLM IPA generation — no easy generic fix.

11. **Homographs listed without disambiguation** [Pronunciation]
    - Problem: "wind", "read", "lead", "does", "close", "subject" all appear with NO IPA. A narrator needs to know WHICH pronunciation to use in context. These entries are useless without context-specific guidance.
    - Location: Homograph handling in pronunciation pipeline
    - Fix approach: Low priority — homographs without context are a systemic issue, not specific to this text.

### LOW
12. **Relationships polluted with "Jesus": "unknown"**
    - Resolves when issue #3 (Jesus false positive) is fixed.

13. **Themes "identity, ambition, loss" — "ambition" is questionable**
    - Better themes: hatred, dehumanization, survival, mercy, suffering.
    - Low priority LLM quality issue.

## Fix History

### Attempt 1 Fixes Applied
- **Fix 1**: Move supporting cast mention search to BEFORE promotion (STEP 5.7.5) → **WORKED** (characters promoted)
- **Fix 2**: Add narrator re-detection after promotion (STEP 5.8.5) → **DID NOT WORK**
- **Fix 3**: Fix narrator prompt to account for 3rd-person summaries → **DID NOT WORK**
- **Fix 4**: Proper names must start with uppercase → **WORKED** ("bush" removed)
- **Bug fix**: Variable shadowing in STEP 5.10.5 → **Fixed**

### Attempt 3 Fixes Applied
- **Fix 1**: Robust LLM JSON parsing (accept "name" key, try wrapper keys) → Pending verification (main_cast still 0)
- **Fix 2**: Two-pass → single-pass fallback in extract() → Fallback fires but still 0 characters
- **Fix 3**: STEP 5.8.5 re-detection condition fix → Pending verification (narrator still undetected)
- **Fix 4**: Include plot_summary in narrator detection prompt → Pending verification (narrator still undetected)
- **Fix 5**: Pronunciation artifact detection improvements → **PARTIALLY WORKED** (6/7 artifacts removed, "hermiene" remains)

### Attempt 4 Fix Applied
- **Fix**: Escape JSON example braces in MAIN_CAST_PROMPT → **Fixed crash** (pipeline ran successfully)

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

**ESCALATION REQUIRED:**
- **main_cast.py** modified 3 times across 3 attempts → still produces 0 characters. The fix phase MUST add debug logging to capture the actual LLM response and diagnose the root cause rather than guessing at parser fixes.
- **narrator.py / characters.py (STEP 5.8.5)** modified 4 times across 3 attempts → narrator still undetected. The fix phase MUST add debug logging to see what candidates are evaluated and what the LLM responds.

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (same for all stages)
- Context: 32768 tokens — sufficient for a short story (~5400 words)
- Temperature: 0.7 for all stages — reasonable
- Two-pass→single-pass fallback fired successfully (crash fixed)
- Main cast pipeline produced 0 characters — pipeline failure, not config issue
- 0 low-confidence items reported
- 0 LLM retries

## Next Action
Run PROMPT_fix.md to address issues #1 and #2 (CRITICAL). **The fix phase MUST add debug logging** to main_cast extraction and narrator detection to capture actual LLM responses before making further code changes. Blind prompt/parser changes have failed 3 times.
