# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 25
- **Phase:** awaiting_fix
- **baseline_score:** 6.55
- **Competitive Mode:** none

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 5/10 ✗ (FAILING)
  - Completeness: 6/10
  - Identity Resolution: 4/10
  - Alias Grouping: 5/10
- Character Profiles: 5.5/10 ✗ (FAILING)
- Chapter Summaries: 5/10 ✗ (FAILING)
- Pronunciation Guide: 9/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 6.6/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold)

## What Changed in Attempt 25

**Narrator fix WORKED:** Uncle Bill (19 mentions) is now correctly identified as narrator (was "the boy" before). This fixed:
- Uncle Bill now has his physical description ("elderly, grizzled, small man") — previously misattributed to "the boy"
- Profile cross-contamination partially resolved

**Still broken:** Father/son merge, summary errors, Johnny fragment, Joe Barron missing.

## Current Issues (Priority Order)

### CRITICAL
1. **Father/son "John Donaldson" merged into one entity** [Identity Resolution]
   - Problem: "John (the boy)" (main_cast_1, 103 mentions) combines father AND son. Two distinct John Donaldsons: the father (embezzler who faked death, stretcher-bearer who dies) and the son (ambulance driver, Uncle Bill's ward).
   - This has been intractable for 25 attempts. The split heuristics fire ~40% of runs stochastically.
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` (STEP 3.95b/3.95c)
   - **ARCHITECTURALLY INTRACTABLE** with current post-extraction heuristics.

2. **Summary has major factual errors** [Chapter Summaries]
   - "deceased brother John's" — John is the boy's FATHER (and Uncle Bill's cousin/nephew, not brother)
   - "the narrator finds his uncle Bill dying on a battlefield" — COMPLETELY WRONG. Uncle Bill is the frame narrator sitting at home in his den. He is NOT on the battlefield.
   - "Bill revives to declare 'American, sir' before dying" — WRONG. The father (John Donaldson Sr.) says "American, sir" before dying, not Uncle Bill.
   - Root cause: LLM conflates the frame narrative (Uncle Bill at home telling the story) with the embedded war narrative (the boy's experience). The character merge compounds this.

### HIGH
3. **Johnny is a fragment, not a separate character** [Identity Resolution]
   - "Johnny" (main_cast_0, 2 mentions) is Ted Frith's nickname for the boy. Should be an alias of "John (the boy)", not a separate character.
   - Has nonsensical relationship: "Ted Frith: close friend" (correct pairing but wrong entity)

4. **"American, sir" listed as alias of John (the boy)** [Alias Grouping]
   - This is a spoken phrase/exclamation, not a character name or alias.
   - "John (the brother)" alias also nonsensical — there is no brother relationship.

5. **All character summaries are null** [Character Profiles]
   - Every character has `"summary": null`. Profile generation not producing narrative summaries.

### MEDIUM
6. **Joe Barron missing** [Completeness]
   - Named character appearing multiple times. Minor but real.

7. **Incomplete relationships** [Character Profiles]
   - Uncle Bill only has "Ted Frith: colleague" — missing relationship with the boy (guardian/uncle)
   - "John (the boy)" has self-referential "John Donaldson: father" (father is merged into same entity)

### LOW
8. **"Bersagliari" spelling** [Pronunciation]
   - Source text variant vs standard "Bersaglieri". IPA is reasonable. Minor.

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.55 | 0 | Baseline |
| 2 | 6.6 | +0.05 | Narrator fix |
| 3 | 6.0 | -0.55 | REGRESSION |
| 4 | 6.4 | -0.15 | Partial fix |
| 5 | 6.7 | +0.15 | Plot summary improved |
| 6 | 7.0 | +0.45 | Uncle Bill narrator |
| 7 | 6.9 | +0.35 | Boy disappeared |
| 8 | 7.85 | +1.30 | Father/son split worked |
| 9 | 8.0 | +1.45 | Cross-character alias fix |
| 10 | 7.0 | +0.45 | REGRESSION — split didn't fire |
| 11 | 7.2 | +0.65 | Mixed |
| 12 | 7.7 | +1.15 | Split via alias contradiction |
| 13 | 5.8 | -0.75 | SEVERE REGRESSION |
| 14 | 7.6 | +1.05 | Split worked |
| 15 | 6.85 | +0.30 | Split didn't fire |
| 16 | 6.95 | +0.40 | No parenthetical |
| 17 | 6.2 | -0.35 | Summary regression |
| 18 | 6.8 | +0.25 | Father/son merged |
| 19 | 7.7 | +1.15 | Split worked (Pattern D) |
| 20 | 5.95 | -0.60 | SEVERE REGRESSION |
| 21 | 6.5 | -0.05 | Narrator OK, alias OK, split no |
| 22 | 6.35 | -0.20 | "American, sir" regression |
| 23 | 6.3 | -0.25 | STEP 3.95b fixes no effect |
| 24 | 6.4 | -0.15 | "American, sir" FIXED, narrator/split broken |
| 25 | 6.6 | +0.05 | Narrator FIXED (Uncle Bill). Split/summary still broken. |

## Fix History
- Attempt 22: STEP 3.95c added (kinship-fragment split). HTML BOM/title fix. 3.95c didn't fire.
- Attempt 23: STEP 3.95b: removed `"(" in canonical_name` guard; sibling-ID check; alias iteration; Pattern E.
- Attempt 24 (Fix 1): `main_cast.py:_parse_pass1_results` + `_parse_profiles` — reject canonical names with commas. WORKED.
- Attempt 24 (Fix 2): `characters.py:_heuristic_narrator_from_mention_count` — exclude <=2-mention candidates. Partial.
- Attempt 25: `characters.py:_heuristic_narrator_from_mention_count` — switched from `min` to `max` mention count. **WORKED** — Uncle Bill(19) correctly selected as narrator over "the boy"(13).

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 8 | Father/son split | main_cast.py (STEP 3.95) | Fixed (stochastic) |
| 9 | Cross-char alias | main_cast.py | Fixed |
| 10-16 | Father/son split reliability | main_cast.py (3.95, 3.95b, 3.95c) | Inconsistent — works ~40% of runs |
| 17 | Summary regression | analyzer.py | No change |
| 18-19 | Father/son split patterns | main_cast.py (Pattern D) | Inconsistent |
| 20-23 | Father/son split patterns | main_cast.py (3.95b, 3.95c, Pattern E) | No change |
| 24 | "American, sir" hallucination | main_cast.py (comma filter) | **Fixed** |
| 24 | Narrator low-mention guard | characters.py (heuristic narrator) | Partial |
| 25 | Narrator heuristic min->max | characters.py (heuristic narrator) | **Fixed** |

## ESCALATION REQUIRED

**After 25 attempts, the score has oscillated between 5.8-8.0 with a median around 6.5.**

The two fixable improvements achieved (comma filter, narrator heuristic) brought modest gains but the score remains at 6.6/10 — well below the 8.0 threshold on 3 categories.

**Remaining blockers are architecturally intractable:**

1. **Father/son same-name merge** (Issue #1) — Stochastic, depends on LLM output variance. Post-extraction heuristics cannot reliably separate two characters with the exact same name. This requires scene-level extraction or a fundamentally different approach.

2. **Summary factual errors** (Issue #2) — The LLM conflates the frame narrator (Uncle Bill at home) with the embedded war narrative. This is a compound error: the character merge makes it worse, and the nested narrative structure (story-within-a-story) is inherently hard for chapter-level summarization.

3. **Johnny fragment** (Issue #3) — Minor but persistent. 2-mention threshold should filter this but it doesn't because it was extracted as main_cast.

**Recommendation: SKIP this text.** "American, Sir" is an adversarial edge case with:
- Two characters sharing the exact same name (John Donaldson father/son)
- Nested frame narrative (Uncle Bill telling the boy's war story)
- A spoken phrase ("American, sir") that looks like a character name

These features stress-test architectural limits that cannot be resolved with incremental fixes. Move to the next test text.

## Configuration Notes
- Model: qwen3-next:80b-a3b-instruct-q8_0 (all agents)
- Config: max_tokens=8192, context_length=32768, think_mode=false

## Next Action
**ESCALATION TO USER.** After 25 attempts (median 6.5, best 8.0), this text should be skipped. The remaining issues require architectural changes beyond the scope of incremental fixes.
