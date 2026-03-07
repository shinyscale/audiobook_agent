# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 24
- **Phase:** awaiting_analysis
- **baseline_score:** 6.55
- **Competitive Mode:** none

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Pipeline Notes (Attempt 24)
- "American, sir" comma-filter: WORKED — not in character list (was Fix 1 from attempt 24)
- Narrator low-mention guard: PARTIALLY worked — blocked Johnny(2) but "the boy"(13) selected instead of Uncle Bill(18)
- Father/son: STILL MERGED — "John" has 30 mentions combining both
- Joe Barron: still missing
- Profile cross-contamination: still present ("the boy" has Uncle Bill's physical description)
- Summary: still confuses Uncle Bill with a dying soldier

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 5/10 ✗ (FAILING)
  - Completeness: 6/10
  - Identity Resolution: 3/10
  - Alias Grouping: 5.5/10
- Character Profiles: 4/10 ✗ (FAILING)
- Chapter Summaries: 5/10 ✗ (FAILING)
- Pronunciation Guide: 9/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 6.4/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold)

## Current Issues (Priority Order)

### CRITICAL
1. **Father/son "John Donaldson" merged into one entity** [Identity Resolution]
   - Problem: "John" (main_cast_1, 30 mentions) combines father AND son. The story has TWO distinct John Donaldsons: the father (embezzler who faked death, ~55, lives in Italy, dies as stretcher-bearer) and the son (the boy, ~22, ambulance driver).
   - Evidence: 30 mentions = both characters combined. "the boy" (main_cast_2, 13 mentions) IS the son but listed separately without the name "John Donaldson".
   - After 24 attempts, the pipeline cannot reliably separate same-name characters. The split heuristics fire ~40% of runs stochastically.
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` (STEP 3.95b/3.95c)
   - **THIS IS INTRACTABLE with current architecture.** Same-name disambiguation requires semantic understanding the post-extraction heuristics cannot provide.

2. **Wrong narrator: "the boy" instead of Uncle Bill** [Identity Resolution]
   - Problem: "the boy" (main_cast_2, 13 mentions) is marked narrator. Uncle Bill (18 mentions) is the actual first-person narrator — every "I" outside quotation marks is Uncle Bill.
   - Evidence: "I threw the letter in the scrap-basket", "I sat down to my orderly desk" — all Uncle Bill. "the boy" narrates his war story IN DIALOGUE within Uncle Bill's frame.
   - The low-mention guard (Fix 2) blocked Johnny(2) but the heuristic still picked "the boy"(13) over Uncle Bill(18). The heuristic needs to prefer the highest-mention character, or use first-person pronoun density outside quotes.
   - Location: `src/agents/characters.py` — `_heuristic_narrator_from_mention_count`

### HIGH
3. **Profile cross-contamination** [Character Profiles]
   - "the boy" shows "an elderly, grizzled, small man, grim and unexhilarating" — this is Uncle Bill's self-description
   - "John" has mixed father+son description ("dark-skinned, olive coloring, blue eyes")
   - Uncle Bill has NO physical description despite self-describing in text
   - Root cause: narrator misidentification causes Uncle Bill's "I" descriptions to be attributed to "the boy"

4. **Summary confuses Uncle Bill with dying soldier** [Chapter Summaries]
   - Summary says: "Uncle Bill, a gravely injured soldier, confesses in a field hospital that he had once been jailed but now seeks to die with honor; he revives briefly to declare 'American, sir' before dying"
   - This is WRONG. Uncle Bill is the narrator sitting in his den. The person who dies saying "American, sir" is John Donaldson the father. The summary also says "his late brother John's" — John is his COUSIN's son, not brother's.
   - Root cause: character extraction errors cascade into summary confusion

5. **Johnny is a fragment, not a real character** [Identity Resolution]
   - "Johnny" (main_cast_2_parent, 2 mentions) has alias "the narrator (the father)" — nonsensical. Johnny is just Ted Frith's nickname for the boy (one occurrence at line 326).
   - Should be an alias of the son, not a separate character.

### MEDIUM
6. **Joe Barron missing** [Completeness]
   - Named character appearing at lines 352, 382, 512. Minor but real.

7. **All character summaries are null** [Character Profiles]
   - Every character has `"summary": null`. Profile generation not producing summaries.

8. **Relationship errors** [Character Profiles]
   - "the boy" lists Johnny and Ted Frith as "close friend" — Johnny IS the boy (nickname)
   - Missing key relationships: Uncle Bill → the boy (guardian), the boy → John (son)

### LOW
9. **"Bersagliari" spelling** [Pronunciation]
   - Source text uses "Bersagliari" vs standard "Bersaglieri". IPA is reasonable. Minor.

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
| 21 | 6.5 | -0.05 | Narrator ✓, alias ✓, split ✗ |
| 22 | 6.35 | -0.20 | "American, sir" regression. HTML fixed. |
| 23 | 6.3 | -0.25 | STEP 3.95b fixes had no effect. Same issues. |
| 24 | 6.4 | -0.15 | "American, sir" FIXED. Narrator/split still broken. |

## Fix History
- Attempt 22: STEP 3.95c added (kinship-fragment split). HTML BOM/title fix. 3.95c didn't fire.
- Attempt 23: STEP 3.95b: removed `"(" in canonical_name` guard → sibling-ID check; alias iteration; Pattern E. STEP 3.95c/3.97: replaced `"(" not in canonical_name` guard with `not c.id.endswith("_parent")`.
- Attempt 24 (Fix 1): `main_cast.py:_parse_pass1_results` + `_parse_profiles` — reject canonical names with commas. WORKED — "American, sir" gone.
- Attempt 24 (Fix 2): `characters.py:_heuristic_narrator_from_mention_count` — exclude ≤2-mention candidates. PARTIALLY worked — blocked Johnny but "the boy" selected over Uncle Bill.
- Attempt 25: `characters.py:_heuristic_narrator_from_mention_count` — switched from `min` to `max` mention count. Rationale: narrator is frequently addressed by name in dialogue → highest-mention candidate. Fixes Uncle Bill(18) over "the boy"(13).

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
| 24 | Narrator low-mention guard | characters.py (heuristic narrator) | Partial — blocked Johnny, not "the boy" |
| 25 | Narrator heuristic min→max | characters.py (heuristic narrator) | Pending |

**ESCALATION NOTICE:** After 24 attempts, the score has oscillated between 5.8-8.0 with a median around 6.5. The two blocking issues are:
1. **Father/son same-name merge** — stochastic, depends on LLM output variance, heuristics fire ~40% of the time
2. **Narrator misidentification** — Uncle Bill (18 mentions, actual narrator) consistently not selected

The father/son issue is architecturally intractable with post-extraction heuristics. The narrator issue may be fixable with a better heuristic (prefer highest-mention candidate, or use first-person pronoun analysis).

## Configuration Notes
- Model: qwen3-next:80b-a3b-instruct-q8_0 (all agents)
- Config: max_tokens=8192, context_length=32768, think_mode=false

## Next Action
**ESCALATION REQUIRED.** After 24 attempts with scores ranging 5.8-8.0 (median ~6.5):

The remaining fixable issue is **narrator detection** (Issue #2). The heuristic should prefer the highest-mention first-person speaker. If Uncle Bill is correctly identified as narrator, profiles and summaries would improve (fixing Issues #3, #4, partially #8), potentially raising the score by 1-2 points.

The father/son merge (Issue #1) is **intractable** with the current architecture — same-name disambiguation requires either:
- A fundamentally different extraction approach (scene-level extraction, not chapter-level)
- Or accepting this as a known limitation for adversarial same-name texts

**Recommended path:** One more attempt focused ONLY on narrator detection (make heuristic prefer highest-mention candidate). If that raises the score to ~7.5+, try one more. If not, escalate to user for skip decision.
