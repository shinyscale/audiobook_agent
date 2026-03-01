# Current Evaluation State

## Active Text
- **Name:** frankenstein
- **Attempt:** 4
- **Phase:** awaiting_fix
- **baseline_score:** 6.20
- **Competitive Mode:** single

## Output Files
- HTML: ../output/frankenstein/report.html
- JSON: ../output/frankenstein/analysis.json
- Dated dir: ../output/Frankenstein_ebook_20260228_220746/

## What Improved from Attempt 3
- **Alphonse Frankenstein is NOW PRESENT** (main_cast_5, 10 mentions, alias "his father") — Fix 2 (summarizer prompt) WORKED! Summaries now use proper names, enabling F6 reconciliation to find Alphonse. This is a 3-attempt escalation that finally succeeded via upstream fix.
- **The Turk is a SEPARATE character again** (0a5ef5ac589f, 9 mentions) — Fix 1 (cross-character conflict rule + absent-alias blocking) WORKED for the Turk variants. "the Turk" and "the Turk (Safie's father)" are no longer false Creature aliases.
- **21 characters total** (up from 19 in attempt 3)
- Alphonse has CORRECT relationships: parent→William ✓, parent→Ernest ✓, employee→Justine ✓, close friend→Beaufort ✓

## What Still Fails
- **Creature STILL has 3 false aliases**: "the blind father (De Lacey)", "De Lacey", "shepherd" — Fix 1 blocked the Turk variants but these three enter through different paths
- **Fabricated relationships remain** for many characters — this is the lowest-scoring category (5/10)
- **Structure titles all null** for chapters (only Letters 2-4 detected)
- **Caroline Beaufort/Frankenstein** still missing

## Latest Scores
- Structure Detection: 7.5/10 ✗
- Character Extraction: 7/10 ✗
  - Completeness: 8/10
  - Identity Resolution: 7/10
  - Alias Grouping: 6/10
- Character Profiles: 5/10 ✗
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 7.5/10 ✗
- HTML Presentation: 7/10 ✗
- **Overall: 7.15/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (5 categories below threshold)

## Current Issues (Priority Order)

### CRITICAL

1. **Fabricated relationships throughout profiles — PRIMARY BLOCKER (score 5/10)** [Profiles]
   - Problem: Many relationships are fabricated from co-occurrence rather than explicit textual markers. This is the single biggest score drag.
   - Specific fabrications:
     - Victor → William: "father" (WRONG — Victor is William's BROTHER, Alphonse is their father)
     - Victor → Safie: "acquaintance" (WRONG — they never meet)
     - Victor → Mr. Kirwin: "protégé" (WRONG direction — Kirwin is the magistrate who handles Victor's case)
     - Creature → Elizabeth: "brother" (WRONG — no familial relationship)
     - Felix → Agatha: "father" (WRONG — Felix is Agatha's BROTHER, old man De Lacey is their father)
     - Safie → Victor: "acquaintance" (WRONG — never meet)
     - Safie → Creature: "associated" (WRONG)
     - Safie → Robert Walton: "associated" (WRONG)
     - Robert Walton → Safie: "associated" (WRONG)
     - Mr. Kirwin → Victor: "mentor" (WRONG — Kirwin is a magistrate)
     - Cornelius Agrippa → M. Krempe: "rival" (WRONG — centuries apart)
     - Cornelius Agrippa → M. Waldman: "rival" (WRONG — centuries apart)
     - William → Victor: "father" (WRONG — brother relationship)
   - Missing crucial relationships:
     - Creature → Victor Frankenstein: "creation" / "creator" (THE central relationship of the book)
     - Victor → Elizabeth: "fiancée" / "wife"
     - Victor → Henry Clerval: "best friend"
     - Victor → Robert Walton: "friend" / "confidant"
   - Root cause: The relationship extraction uses chapter-level co-occurrence rather than explicit textual relationship markers. Characters appearing in the same chapter are treated as "related." Direction/type is guessed incorrectly.
   - Location: `src/pipeline/character_extraction_v2/` — profile extraction stage. The relationship extraction prompt needs to require EXPLICIT textual evidence (words like "father", "brother", "creator", "friend", "wife") rather than inferring from proximity.
   - Fix approach: Modify the relationship extraction prompt to:
     (a) ONLY assign relationships when explicit relationship words appear in the text connecting the two characters
     (b) Use directional relationship terminology (if A is B's father, then B is A's child — not the reverse)
     (c) Never assign "acquaintance"/"associated" unless characters directly interact

### HIGH

2. **Creature still has 3 false aliases: "the blind father (De Lacey)", "De Lacey", "shepherd"** [Identity Resolution, Alias Grouping]
   - Problem: main_cast_2 ("the creature") still has these false aliases despite Fix 1 blocking the Turk variants. These enter through different paths than the Turk aliases.
   - Analysis of why Fix 1 didn't catch them:
     - **"De Lacey"**: Felix De Lacey (main_cast_8) has "De Lacey" as an alias, so Rule 3 (cross-character conflict) SHOULD block it. But the creature is main_cast_2 and Felix is main_cast_8 — if `verify_aliases` processes characters sequentially, Felix's aliases may not be available when the Creature is processed. The fix needs to check BIDIRECTIONALLY against ALL cast members, not just those processed so far.
     - **"the blind father (De Lacey)"**: Not claimed by another character, so Rule 3 doesn't apply. Not a verbatim match in summaries, so Rule 2a should block it — but the parenthetical "(De Lacey)" may be stripped or the check may do partial matching. Need to verify the alias-found logic handles parenthetical variants.
     - **"shepherd"**: A shepherd appears briefly in Ch 11 when the Creature enters his hut. The word "shepherd" co-occurs with the Creature in summaries. This is a false alias because the shepherd is a separate (unnamed) person.
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` — `verify_aliases()`
   - Fix approach:
     - For "De Lacey": Make Rule 3 check against ALL cast members' canonical names AND aliases (not just those already processed). Pre-compute the full cast alias set before verification begins.
     - For "the blind father (De Lacey)": Verify Rule 2a is checking the exact alias string including parentheticals. If it's doing substring matching, it might match "De Lacey" in summaries and pass.
     - For "shepherd": Rule 2a should block this if "shepherd" isn't used as a name/alias in summaries. Verify the alias-found logic.

3. **Physical descriptions missing for 14/21 characters (67%)** [Profiles]
   - Problem: Only 7/21 characters have physical descriptions. Missing for all major protagonists: Victor, Robert Walton, Henry Clerval, Alphonse.
   - Characters WITH descriptions (correct): the creature ✓, the old man ✓, Elizabeth Lavenza (minimal: "Fair-haired; beautiful") ✓, Justine ✓, William ✓, M. Waldman ✓, M. Krempe ✓
   - Evidence from text:
     - Victor is described as haggard, emaciated, feverish after his creation work
     - Henry Clerval has an expressive face full of benevolence
     - Robert Walton's appearance is less explicitly described but some traits are mentioned
   - Location: `src/pipeline/character_extraction_v2/` — profile extraction stage
   - Fix: Profile extraction prompt may need to search harder for physical descriptions of first-person narrators and characters described through others' observations.

4. **Caroline Beaufort/Frankenstein (Victor's mother) still missing** [Completeness]
   - Problem: Victor's mother appears in Chapters 1-3 and is mentioned in the summary: "The narrator's mother, Caroline Beaufort, endured extreme hardship caring for her dying father..." She saves Elizabeth, raises the children, and dies of scarlet fever.
   - Despite the summary now mentioning "Caroline Beaufort" by name (Fix 2 worked for summaries), F6 reconciliation still didn't pick her up.
   - Root cause: F6 may require a minimum number of summary mentions, and Caroline may appear in only 1-2 chapter summaries. Or F6 may not be matching "Caroline Beaufort" because it's referred to as "the narrator's mother" in most contexts.
   - Location: `src/analyzer.py` (F6 reconciliation logic, ~line 1220-1240)
   - Fix: Check F6 thresholds for summary-extracted characters. Caroline appears by name in at least 1 summary.

### MEDIUM

5. **Structure: Chapter titles null for all 24 chapters** [Structure]
   - Problem: Frankenstein's chapters are headed "Chapter I", "Chapter II" etc. These are not detected as titles. Only Letters 2, 3, 4 have titles. Letter 1 also has null title.
   - Evidence: 24/28 structure elements have `title: null`
   - Location: `src/pipeline/chapter_detection/` — title extraction logic
   - Fix: The title detector should recognize "Chapter I", "Chapter II" etc. as chapter titles. Also detect "Letter 1" as the first element's title.

6. **Pronunciation false positives** [Pronunciation]
   - Problem: Common English words flagged: "than", "hero" have zero pronunciation ambiguity. "sympathised", "sympathise", "sympathising", "unsympathised" are standard British English spellings. "slothful" is straightforward.
   - Evidence: ~8 unnecessary entries out of 206
   - Location: `src/pipeline/pronunciation/` — word filtering logic
   - Fix: Add common words to exclusion list. Filter standard -ise/-ised variants.

7. **All 206 pronunciation entries have null type and context** [Pronunciation]
   - Problem: Type (proper_noun, foreign, homograph) and context fields are all null, losing categorization information for the narrator.
   - Location: `src/pipeline/pronunciation/` — field population
   - Note: The `category` field IS populated and duplicates what `type` should contain. This may be a field mapping issue.

8. **Book title displayed as "Contents"** [Presentation]
   - Problem: HTML header says "Contents" instead of "Frankenstein". Title extracted from table-of-contents page.
   - Location: `src/ingestion/` or title extraction logic

9. **Letter 1 missing from Prologue Materials** [Presentation]
   - Problem: HTML shows "Prologue 1: Letter 2" as first prologue item. Letter 1 (null title) is excluded.
   - Location: HTML template — prologue section filters out elements with null titles

### LOW

10. **Creature missing key aliases: "the fiend", "the wretch", "the daemon"** [Alias Grouping]
    - Problem: These are frequently used descriptors for the Creature in the text. The Creature currently only has "the being" and "the monster" as valid descriptors (plus 3 false aliases and "the murderer").
    - Root cause: Rule 2a (absent-alias blocking) may be over-blocking. If cached summaries don't contain "the fiend" verbatim, valid aliases get blocked.
    - Fix: If summaries were regenerated with the new prompt, these terms should appear. May need to verify whether the summaries were actually regenerated or cached.

11. **Supporting characters lack full canonical names** [Alias Grouping]
    - Problem: "William" should be "William Frankenstein", "Ernest" should be "Ernest Frankenstein", "Margaret" should be "Margaret Saville"
    - Location: `src/pipeline/character_extraction_v2/supporting.py`

12. **"the old man" canonical name is vague** [Identity Resolution]
    - Problem: split_the_old_man (29 mentions) is the blind father De Lacey, but the canonical name "the old man" could refer to anyone. Should ideally be "De Lacey (father)" or "Old De Lacey".
    - Also: alias "the old man (shepherd)" conflates two different "old man" references — the De Lacey father and the shepherd in Ch 11.

13. **Cornelius Agrippa and Werter as character entries** [Completeness]
    - Low priority — historical/literary references, not characters in the narrative. Minor noise.

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.20 | - | Baseline. Creature/Turkish merchant merge is primary blocker. |
| 2 | 6.40 | +0.20 | Creature/Turk split FIXED. Victor/Frankenstein protagonist split now exposed as primary blocker. |
| 3 | 6.83 | +0.63 | Victor unified ✓. BUT Turk REGRESSED into Creature aliases. Alphonse still missing (3rd attempt). |
| 4 | 7.15 | +0.95 | Alphonse found ✓. Turk re-separated ✓. Profiles (5/10) now primary blocker. |

## Fix History
- Attempt 2 (Fix 1): Expanded competitive alias verification context from first-5-chapters (3000 chars) to ALL chapters (10000 chars)
  - Modified: `src/pipeline/character_extraction_v2/main_cast.py`

- Attempt 2 (Fix 2): Added occupation titles (merchant, magistrate, officer, soldier) to `human_descriptors` in `_split_semantic_conflicts`
  - Modified: `src/agents/characters.py`

- Attempt 3 (Fix A): Changed `consensus_merge_threshold` from 0.67 to `2/3` to allow 2/3 supermajority votes to pass
  - Modified: `src/agents/config.py`, `src/cli.py`

- Attempt 3 (Fix B): Narrator placeholder preservation — `_filter_narrator_variants` now keeps main_cast narrators with proper-name aliases
  - Modified: `src/agents/characters.py`

- Attempt 3 (Fix C): Narrator placeholder canonical name upgrade — "The narrator" with alias "Victor Frankenstein" gets canonical name upgraded
  - Modified: `src/agents/characters.py`

- Attempt 3 (Fix D): Lowered `min_grounding_mentions` from 3 to 1 — DID NOT SOLVE Alphonse issue
  - Modified: `src/agents/characters.py`

- Attempt 3 (Fix E): `_merge_surname_into_family_descriptive` — mark surname consumed when "the X" already has it as alias — DID NOT FULLY WORK for De Lacey
  - Modified: `src/agents/characters.py`

- Attempt 4 (Fix 1): Three algorithmic fixes to `verify_aliases()` in `main_cast.py`:
  - **Fix A (shared_parts stop-words)**: Filter stop words from `shared_parts` calculation
  - **Fix B (cross-character conflict)**: New Rule 3 — block alias if already name/alias of DIFFERENT character
  - **Fix C (alias absent from summaries)**: New Rule 2a — block alias if not found in any summary verbatim
  - Modified: `src/pipeline/character_extraction_v2/main_cast.py`
  - Result: Blocked Turk variants ✓. Did NOT block "De Lacey", "the blind father (De Lacey)", "shepherd" — these enter through different paths.

- Attempt 4 (Fix 2): Upstream summarizer fix for Alphonse — changed prompt from "use relationship terms only" to "use proper names when stated in text"
  - Modified: `src/pipeline/chapter_summary/summarizer.py`
  - Result: Alphonse now appears in summaries by name → F6 picked him up ✓

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 2 | Creature/Turkish merchant merge | `main_cast.py`, `characters.py` | Fixed ✓ |
| 3 | Victor/Frankenstein split | `config.py`, `cli.py`, `characters.py` | Fixed ✓ |
| 3 | Alphonse missing | `characters.py` (grounding threshold) | No change — grounding wasn't root cause |
| 3 | Creature De Lacey alias | `characters.py` (_merge_surname) | No change — aliases enter via different path |
| 3 | (Side effect) Turk regression | Unknown | Regression |
| 4 | Creature Turk aliases | `main_cast.py` (verify_aliases rules) | Fixed ✓ — Turk variants blocked |
| 4 | Creature De Lacey/shepherd aliases | `main_cast.py` (verify_aliases rules) | Partial — "De Lacey" still present (Rule 3 timing issue) |
| 4 | Alphonse missing | `summarizer.py` (upstream prompt fix) | Fixed ✓ — escalation to upstream succeeded |

**Pattern detected:** `main_cast.py` verify_aliases has been modified 2 times for Creature alias issues. Rule 3 (cross-character conflict) has a timing issue — it checks against cast members processed so far, not all cast members. Fix needs to pre-compute full cast alias set.

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (same for all agents)
- Temperature: 0.7 across all agents (reasonable)
- Context length: 32768 (sufficient)
- 0 retries across all stages ✓
- Profiling stage names are null (minor logging issue)
- Summaries stage shows 0 LLM calls — may still be cached from prior run

## Priority Fix Guidance for Attempt 5

### Fix Priority 1: Profile Relationships (CRITICAL #1 — score 5/10, needs 8/10)

This is the single biggest blocker. The relationship extraction is producing fabricated relationships based on co-occurrence rather than explicit textual evidence. Over 40% of relationships are wrong.

**Investigation steps:**
1. Find the profile/relationship extraction prompt in `src/pipeline/character_extraction_v2/`
2. Examine how relationships are inferred — is it purely co-occurrence, or does it look for explicit relationship words?
3. Modify the prompt to REQUIRE explicit textual evidence for each relationship
4. Key relationship types to handle correctly:
   - Family: "father", "mother", "brother", "sister", "son", "daughter", "cousin", "wife", "husband"
   - Professional: "mentor", "professor", "student", "employer", "servant"
   - Social: "friend", "companion", "creator", "creature"
5. Direction must be correct: if text says "A is B's father", then A→B is "child" and B→A is "parent"

**This fix alone could raise the overall score by ~0.45 points.**

### Fix Priority 2: Creature False Aliases (HIGH #2)

"De Lacey" should be blocked by Rule 3 (cross-character conflict with Felix De Lacey) but isn't due to processing order. Fix the timing issue in `verify_aliases()`:
- Pre-compute ALL cast members' aliases before running verification
- Pass the full alias map to the verification function
- Check bidirectionally against all cast aliases, not just those processed so far

"the blind father (De Lacey)" and "shepherd" should be blocked by Rule 2a (not in summaries). Verify the alias-found matching logic handles parenthetical variants correctly.

### Fix Priority 3: Structure Titles (MEDIUM #5)

Detect "Chapter I", "Chapter II" etc. as chapter titles. This is likely a simple pattern matching fix in `src/pipeline/chapter_detection/`.

### Do NOT attempt to fix: Chapter Summaries (8.5/10) — already passing.

## Next Action
Run PROMPT_fix.md to address profile relationships (Critical #1) and creature false aliases (High #2).
