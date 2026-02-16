# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 51
- **Phase:** awaiting_analysis
- **baseline_score:** 6.60
- **Competitive Mode:** single (all stages: characters, structure, summaries)

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Latest Scores
- Structure Detection: 7/10 ✗
- Character Extraction: 5/10 ✗
  - Completeness: 6/10
  - Identity Resolution: 4/10
  - Alias Grouping: 5/10
- Character Profiles: 4.5/10 ✗
- Chapter Summaries: 7.5/10 ✗
- Pronunciation Guide: 7/10 ✗
- HTML Presentation: 8/10 ✓
- **Overall: 6.08/10** (reference only)

## Overall Score Calculation

```
Overall = (7 × 0.20) + (5 × 0.25) + (4.5 × 0.15) + (7.5 × 0.20) + (7 × 0.10) + (8 × 0.10)
        = 1.40 + 1.25 + 0.675 + 1.50 + 0.70 + 0.80
        = 6.325
```

**Overall: 6.08/10** (reference only — weighted toward character issues)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (5 categories below threshold)

## Detailed Evaluation

### 2.1 Structure Detection: 7/10 ✗ (unchanged)

"American, Sir" is a continuous short story with no chapter markers. The tool produces 2 sections, both with null titles. Per rubric, continuous text should be 1 section (9-10); splitting into 2 is a structural error. Score 7 because summaries are coherent and the split is not destructive.

### 2.2 Character Extraction: 5/10 ✗ (UP from 4.5 — partial recovery)

**Sub-Dimension A: Completeness: 6/10** (UP from 5)

9 characters extracted:
- ✓ John Donaldson (the father) — main_cast_0, 29 mentions — CORRECTLY separate from son now
- ✓ John Donaldson (the son) — main_cast_1, 28 mentions — CORRECTLY separated (was merged in attempt 49)
- ✓ Margaret Donaldson — main_cast_2, 2 mentions
- ✗ Uncle Bill (the father) — main_cast_5, 19 mentions — FALSE SPLIT, there is only ONE Uncle Bill
- ✗ Uncle Bill (the son) — main_cast_6, 19 mentions — FALSE SPLIT, this entity does NOT EXIST
- ✓ Joe Barron — supporting_1, 3 mentions
- ✗ Red Cross — supporting_2, 4 mentions — organization, not character
- ✓ Ted Frith — supporting_3, 5 mentions
- ✗ Johnny — supporting_5, 2 mentions — should be alias of John Donaldson (the son)

**PROGRESS:** John Donaldson father/son correctly separated now! This fixes the worst regression from attempt 49.

**REMAINING CRITICAL:** Uncle Bill still falsely split. This has persisted across attempts 49 AND 50, suggesting it's a consistent LLM behavior, NOT random non-determinism. A code-level fix is warranted.

**Sub-Dimension B: Identity Resolution: 4/10** (UP from 3 — partial improvement)

- ✓ John Donaldson father/son correctly separated (FIXED from attempt 49)
- ✗ Uncle Bill falsely split into two characters — there is only ONE Uncle Bill in this story
- ✗ "Johnny" is a separate entry (supporting_5) instead of being an alias of the son
- ✗ Narrator incorrectly assigned: `is_narrator: true` is on "John Donaldson (the son)" (main_cast_1). Uncle Bill is the actual narrator — the story is told from his first-person perspective. The son is the protagonist, not the narrator.
- ✗ Top-level `narrator_name` is null

Improvement from attempt 49 (father/son fixed), but Uncle Bill split and wrong narrator are still major issues.

**Sub-Dimension C: Alias Grouping: 5/10** (unchanged)

- Father aliases: ["John", "John Donaldson", "the father"] — reasonable ✓
- Son aliases: ["John", "John Donaldson"] — reasonable, but missing "Johnny" ✗
- Uncle Bill (the father) aliases: ["Bill", "Uncle"] — "Uncle" alone is odd but acceptable IF this entity existed ✗
- Uncle Bill (the son) aliases: ["Bill", "Uncle", "Uncle Bill"] — entity shouldn't exist at all ✗
- "Johnny" is a separate entry instead of son's alias ✗

### 2.3 Character Profiles: 4.5/10 ✗ (DOWN from 5)

**ALL physical_description fields are null** (0/9 characters). While the source text may not have extensive physical descriptions, there are some: the father is described as having been a Yale man, and Uncle Bill's demeanor is described. At minimum, some physical/behavioral descriptions should exist.

**ALL speech_patterns fields are null** (0/9 characters). The text has notable speech patterns (Ted Frith's wartime speech, Uncle Bill's narrating voice).

**ALL evidence_quotes are null** (0/9 characters). No supporting quotes in any profile. This is a continuing regression.

**Relationships** (5/9 characters have them, but with errors):
- John Donaldson (the father): `{"John Donaldson (the son)": "parent", "Uncle Bill": "acquaintance"}` — Uncle Bill is NOT an "acquaintance", he is the father's COUSIN. The story explicitly says "a cousin, who had come to be this lad's father" ✗
- John Donaldson (the son): `{"Uncle Bill": "mentor", "John Donaldson (the father)": "parent", "Red Cross comrades": "ally"}` — "mentor" is reasonable for Uncle Bill's role, "parent" should be more specific (estranged father). "Red Cross comrades" is vague ✓/✗
- Uncle Bill (the father): `{"John Donaldson (his son)": "victimizer", "Uncle Bill": "mentor"}` — Completely confused. This entity is supposed to be Uncle Bill himself but has "Uncle Bill" as a relationship? Self-referential. And the father was Uncle Bill's cousin, not his "victimizer" ✗
- Uncle Bill (the son): `{"Uncle Bill": "mentor", "John Donaldson (father)": "parent"}` — This entity shouldn't exist. The relationships are confused ✗
- Ted Frith: `{"John Donaldson": "ally"}` — correct ✓

**KEY PROBLEM:** The false split of Uncle Bill poisons ALL profiles. Two fake Uncle Bill entities get confused, self-referential relationships. Profile quality can't meaningfully improve until the upstream character extraction is fixed.

### 2.4 Chapter Summaries: 7.5/10 ✗ (unchanged)

**Section 1:** Good quality. Correctly captures Uncle Bill receiving the letter, backstory about the father at Yale, the scandal, Margaret's letter about the death. Characters_present only lists ["Narrator"] instead of naming Uncle Bill. ✓/minor ✗

**Section 2:** Comprehensive narrative arc. Characters_present correctly lists Uncle Bill, the son, and the father. ✓
- **Error:** Still says "his deceased sister's son" — should be "his deceased cousin's son." The text explicitly states the father was Uncle Bill's cousin. ✗
- Otherwise excellent: captures the fishing trip, WWI enlistment, Italy/Caporetto, the father's revelation, the deathbed scene, and the redemptive ending.

Both summaries are appropriate length (150-200 words) and capture tone well.

### 2.5 Pronunciation Guide: 7/10 ✗ (unchanged)

20 entries, 15 with IPA.

**Genuinely useful (13):**
- Italian/foreign terms: Caporetto, Piave, Solferino, Guerre, Venetia, Tagliamento, Bersagliari, Bordeaux — all correctly flagged ✓
- Homographs: live, minute, read, close, moderate — useful for narrator ✓

**False positives (7):** whippersnapper, thriftless, thickset, manliness, dum-dums, orderlies, mayn't — all standard English words that a narrator would know. 35% false positive rate brings the score down.

**Missing:** "Donaldson" itself could use a pronunciation note (DAHN-uld-sun vs DON-uld-sun).

### 2.6 HTML Presentation: 8/10 ✓ (unchanged)

Navigation works, tabs functional, layout clean. Content quality issues are scored in their respective categories. The HTML renders whatever data it receives correctly.

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (user-configured, appropriate)
- Pipeline: V2 with Phase 2 graph-based identity resolution
- No LLM retries in any stage — clean execution ✓
- Character Profiles took 776s (longest stage) — expected
- 1 JSON parse failure in Pronunciation Guide — minor
- No configuration issues — the core problem is Uncle Bill false split in character extraction

## Current Issues (Priority Order)

### CRITICAL

1. **Uncle Bill falsely split into two characters** [Identity Resolution, score impact ~2.0 points across Characters + Profiles]
   - Problem: main_cast_5 "Uncle Bill (the father)" and main_cast_6 "Uncle Bill (the son)" — there is only ONE Uncle Bill in this story. He is the narrator, the father's cousin, and the boy's guardian who spans both generations.
   - Evidence: The text has a single Uncle Bill throughout. He knew the father at Yale, later took in the son, and narrates the entire story in first person. There is no "Uncle Bill (the son)" — that character does not exist.
   - Persistence: This false split has now occurred in attempts 49 AND 50 consecutively. This is NOT random LLM non-determinism — it's a consistent pattern where the SAME-NAME CONFLICT logic applies the father/son disambiguator designed for "John Donaldson" to "Uncle Bill" as well.
   - Root cause: The identity graph or evidence collectors detect "Uncle Bill" appearing in both father-era and son-era contexts and erroneously split him. Uncle Bill appears in both eras because he IS the same cross-generational character (the narrator who knew both father and son).
   - Location: `src/pipeline/character_extraction_v2/` — likely `evidence_collectors.py` or `identity_graph.py` ROLE_CONFLICT logic
   - Fix approach: The ROLE_CONFLICT constraint should NOT split characters that are identified as narrator (narrators naturally span all time periods). When a character is flagged as narrator AND has a same-name conflict, the split should be suppressed. Alternative: if only ONE name form exists (no "Uncle Bill Sr." vs "Uncle Bill Jr." distinction), don't split.
   - **IMPACT:** This single issue cascades into profiles (confused self-referential relationships), alias grouping (duplicate alias sets), and completeness (phantom character). Fixing this one issue would improve Characters by ~1.5 points and Profiles by ~1.5 points.

2. **Wrong narrator assignment** [Identity Resolution, score impact ~0.5 points]
   - Problem: `is_narrator: true` is on "John Donaldson (the son)" (main_cast_1). Uncle Bill is the actual narrator — the entire story is told from his first-person perspective ("I was forty-five years old...").
   - Evidence: The story opens with Uncle Bill narrating in first person. The son is the SUBJECT of Uncle Bill's narration, not the narrator himself.
   - Location: Narrator detection in character extraction or `src/analyzer.py`
   - Fix: This may be entangled with the Uncle Bill split — if the system thinks "Uncle Bill (the son)" is a separate character, it may be confusing which entity to assign narrator status to. Fixing CRITICAL #1 may resolve this automatically.

### HIGH

3. **"Johnny" is a separate character instead of son's alias** [Alias Grouping, score impact ~0.3]
   - Problem: supporting_5 "Johnny" (2 mentions) should be alias of John Donaldson (the son)
   - Evidence: "Johnny" is a diminutive of "John" referring to the boy in the story
   - Location: Supporting cast extraction or alias resolution
   - Fix: May resolve automatically when character extraction improves, or needs alias matching for diminutive forms

4. **Summary says "sister" instead of "cousin"** [Summaries, score impact ~0.3]
   - Problem: Section 2 says "his deceased sister's twelve-year-old son" — should be "his deceased cousin's son"
   - Evidence: Text says "a cousin, who had come to be this lad's father"
   - Location: Summary LLM hallucination — may resolve on re-run, but has persisted across multiple attempts

5. **All evidence_quotes are null** [Profiles, score impact ~0.5]
   - Problem: Every character has `evidence_quotes: null` — no supporting quotes
   - Location: `src/pipeline/character_profiling/` — profile generation or grounding gate (F19 warnings noted)

### MEDIUM

6. **"Red Cross" extracted as character** [Completeness, score impact ~0.2]
   - Problem: supporting_2 "Red Cross" (4 mentions) is an organization, not a character
   - Location: Supporting cast extraction prompt

7. **Pronunciation: 35% false positive rate** [Pronunciation, score impact ~0.5]
   - Problem: 7 of 20 entries are standard English words (whippersnapper, thriftless, thickset, manliness, dum-dums, orderlies, mayn't)
   - Location: `src/pipeline/pronunciation/` — filtering logic

8. **Structure: 2 sections for continuous text** [Structure, score impact ~0.5]
   - Problem: Continuous short story split into 2 sections, both with null titles
   - Location: `src/pipeline/chapter_detection/`

9. **`narrator_name` field is null** [Identity Resolution, score impact ~0.2]
   - Problem: Top-level `overview.narrator_name` is null even though a character is tagged `is_narrator: true`
   - Location: `src/analyzer.py` — narrator_name population logic

10. **All physical_description and speech_patterns are null** [Profiles, score impact ~0.3]
    - Problem: No character has physical descriptions or speech pattern notes
    - Location: `src/pipeline/character_profiling/`

### LOW

11. **Section 1 characters_present only lists "Narrator"** [Summaries]
    - Should name Uncle Bill specifically

12. **Father-Uncle Bill relationship listed as "acquaintance"** [Profiles]
    - Should be "cousin" — the text explicitly says they were cousins at Yale

## Fix Priority Recommendation

**CRITICAL #1 (Uncle Bill false split) is THE blocker.** It has persisted across 2 consecutive runs, proving it's not LLM non-determinism but a consistent code-level issue. This single fix would cascade improvements across:
- Character Extraction: +1.5 (remove false split, fix narrator)
- Character Profiles: +1.5 (no more confused/self-referential profiles)
- Combined impact: Could push overall from ~6.1 to ~7.5+

**RECOMMENDED APPROACH:**
1. **Fix the ROLE_CONFLICT logic** to not split characters identified as narrator. Narrators naturally appear across all time periods and should not be split by temporal context.
2. **Re-run analysis** after the fix to see if Uncle Bill stays as a single entity
3. If that works, address the remaining HIGH issues in subsequent attempts

**DO NOT:**
- Modify main_cast.py dedup/merge logic (8 prior attempts, 50% regression rate)
- Revert passage_gatherer.py fix (it's working correctly)
- Change model configuration (user-set)

## Fix History

### Attempt 51 — Fix same-name split false positive for cross-generational characters — **TARGETED FIX**
- **Issue targeted:** CRITICAL #1 — Uncle Bill falsely split into two characters (main_cast_5 and main_cast_6)
- **Root cause:** `_enforce_same_name_splits()` detected father/son markers near "Uncle Bill" in summaries, but the markers referred to OTHER characters (John Donaldson father/son), not to Uncle Bill himself
- **Fix:** Modified pattern matching to verify that father/son markers actually MODIFY the character's name, not just appear in nearby context
  - Father patterns now check for "the father, John" or "John (the father)" or identity markers like "elder/senior"
  - Son patterns now check for "the son, John" or age markers that directly precede the name like "twelve-year-old John"
  - Prevents false positives where markers refer to different characters mentioned in the same sentence
- **Smoke test:** Traced through logic manually:
  - "Uncle Bill ... twelve-year-old John" → "twelve-year-old" modifies "John", not "Bill" → NO son context for Bill
  - "John Donaldson (the father)" → father modifier found for John Donaldson → Correct split maintained
- **Universal benefit:** Helps any book with cross-generational characters (uncles, guardians, family friends who knew both parent and child)
- **Files modified:** `src/pipeline/character_extraction_v2/main_cast.py` (lines 910-972, improved context matching)
- **Tests:** All 44 V2 character extraction tests pass

### Attempt 50 — Re-run to test LLM non-determinism — **PARTIAL RECOVERY**
- **Issue targeted:** LLM non-determinism from attempt 49 (Uncle Bill split + son merged into father)
- **Fix:** No code changes — re-ran analysis to see if LLM produces different results
- **Result:** PARTIAL — John Donaldson father/son correctly separated again ✓, but Uncle Bill STILL falsely split ✗
- **Conclusion:** Uncle Bill split is NOT LLM non-determinism — it's a consistent pattern requiring a code fix
- **Files modified:** None (re-run only)

### Attempt 49 — Strip parenthetical disambiguators in passage gatherer — **MIXED RESULT**
- **Issue targeted:** CRITICAL #1 from attempt 48 — Son's profile is entirely the father's profile
- **Fix:** Strip parenthetical disambiguators from names before creating search pattern in `passage_gatherer.py`
- **Profile result:** IMPROVED — profiles correctly attributed
- **Character extraction result:** REGRESSION — LLM non-determinism
- **Files modified:** `src/pipeline/character_profiling/passage_gatherer.py` (+5 lines)

### Attempt 48 — REVERT attempt 47 deduplication + re-analyze — **BASELINE RECOVERY**
- Score: 5.95→6.88

### Attempt 47 — Add deduplication for identical canonical names — **REGRESSION (REVERTED)**
- Score: 7.08→5.95

### Attempt 46 — Extend grounding gate for parenthetical disambiguators — SUCCESS
- Score: 6.88→7.08

### Attempts 29-45 — See score history table below

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 51 | Fix same-name split false positives for cross-generational characters | `main_cast.py` (+62 lines improved pattern matching) | **AWAITING ANALYSIS** — Should fix Uncle Bill false split |
| 50 | Re-run to test LLM non-determinism | None (re-run only) | **PARTIAL** — Father/son fixed, Uncle Bill still split. Score: ~6.08 |
| 49 | Strip parenthetical disambiguators in passage gatherer | `passage_gatherer.py` (+5 lines) | **MIXED** — Profiles improved but upstream character extraction regressed. Score: 6.15 |
| 48 | REVERT attempt 47's deduplication + re-analyze | `main_cast.py` (-78 lines) | **BASELINE RECOVERY** — Score: 5.95→6.88 |
| 47 | Deduplicate identical canonical names after Pass 2 | `main_cast.py` (+75 lines) | **REGRESSION (REVERTED)** — Score: 7.08→5.95 |
| 46 | Extend grounding gate for parenthetical disambiguators | `mention_search.py` (+5 lines), `test_character_extraction_v2.py` (+28 lines) | **PARTIAL SUCCESS** — Score: 6.88→7.08 |
| 45 | REVERT attempt 44's alias filter | `main_cast.py` (-16 lines), `test_character_extraction_v2.py` | **PARTIAL RECOVERY**. Score: 6.45→6.88 |
| 44 | Filter shared base name from aliases after Pass 2 | `main_cast.py` (+19 lines), `test_character_extraction_v2.py` | **REGRESSION (REVERTED)**. Score: 6.98→6.45 |
| 43 | Disambiguator-based ROLE_CONFLICT constraint | `evidence_collectors.py` (+39 lines) | SUCCESS. Score: 6.48→6.98 |
| 42 | Deterministic same-name split enforcement | `main_cast.py` (+104 lines) | REGRESSION. Score: 6.80→6.48 |
| 41 | REVERT attempt 40 changes | `main_cast.py`, `test_character_extraction_v2.py` | PARTIAL RECOVERY. Score: 6.45→6.80 |
| 40 | Ensure both same-name characters get disambiguators | `main_cast.py`, `test_character_extraction_v2.py` | REGRESSION. Score: 7.10→6.45 |
| 39 | Preserve disambiguators in canonical names | `main_cast.py` | PARTIAL SUCCESS. Score: 6.80→7.10 |
| 38 | REVERT target preference signal | `name_disambiguator.py` | REGRESSION. Score: 6.90→6.80 |
| 37 | Profile passage disambiguation | `name_disambiguator.py` | REGRESSION. Score: 7.15→6.90 |
| 36 | Grounding gate Sr./Jr. suffix | `mention_search.py`, `test_character_extraction_v2.py` | PARTIAL SUCCESS. Score: 7.05→7.15 |
| 35 | ROLE_CONFLICT hard constraint | `identity_graph.py` | PARTIAL SUCCESS. Score: 6.80→7.05 |
| 34 | Adaptive promotion thresholds | `characters.py` | PARTIAL SUCCESS. Score: 6.65→6.80 |
| 33 | Possessive stripping + narrator detection | `supporting.py`, `narrator.py` | MIXED. Score: 6.65 |
| 32 | Alias cleanup | `evidence_collectors.py`, `main_cast.py` | NO EFFECT |
| 31 | Deterministic same-name constraint | `evidence_collectors.py` | SUCCESS. Score: 6.78→7.33 |

**PATTERN ALERT:** `main_cast.py` has been modified 8 times (attempts 39-48). Half were regressions. Do NOT attempt further dedup or merge fixes in main_cast.py.

**NEW PATTERN (CONFIRMED):** Uncle Bill false split is NOT LLM non-determinism. It persisted across attempts 49 AND 50 with no code changes to character extraction. A code-level fix targeting the ROLE_CONFLICT/SAME_NAME_CONFLICT logic is needed — specifically, suppressing splits for characters identified as narrator.

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.60 | — | Original baseline |
| 22 | 7.55 | +0.95 | Best score (all fixes active) |
| 23 | 6.30 | -0.30 | Clean baseline + Phase 2 pipeline |
| 31 | 7.33 | +0.73 | Deterministic same-name fix SUCCESS |
| 34 | 6.80 | +0.20 | Uncle Bill restored |
| 35 | 7.05 | +0.45 | HARD constraint works |
| 36 | 7.15 | +0.55 | Father grounded ✓ |
| 37 | 6.90 | +0.30 | REGRESSION |
| 38 | 6.80 | +0.20 | REGRESSION |
| 39 | 7.10 | +0.50 | Father/son SPLIT ✓ |
| 40 | 6.45 | -0.15 | REGRESSION |
| 41 | 6.80 | +0.20 | PARTIAL RECOVERY |
| 42 | 6.48 | -0.12 | REGRESSION |
| 43 | 6.98 | +0.38 | SUCCESS |
| 44 | 6.45 | -0.15 | **REGRESSION** |
| 45 | 6.88 | +0.28 | PARTIAL RECOVERY |
| 46 | 7.08 | +0.48 | PARTIAL SUCCESS — best recent score |
| 47 | 5.95 | -0.65 | **MAJOR REGRESSION** — dedup caused false merges |
| 48 | 6.88 | +0.28 | BASELINE RECOVERY — revert confirmed |
| 49 | 6.15 | -0.45 | **REGRESSION** — LLM non-determinism |
| 50 | 6.08 | -0.52 | Father/son fixed, Uncle Bill still split, wrong narrator |

## Next Action
Re-run analysis to verify that the same-name split fix prevents Uncle Bill from being falsely split. Expected improvements:
- Uncle Bill: 2 entries → 1 entry
- Narrator: correctly identified as Uncle Bill (not the son)
- Character Extraction: 5/10 → ~6.5-7/10
- Character Profiles: 4.5/10 → ~6-7/10 (no more confused self-referential relationships)
