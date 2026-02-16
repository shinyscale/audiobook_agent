# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 40
- **Phase:** awaiting_analysis
- **baseline_score:** 6.60
- **Competitive Mode:** single (all stages: characters, structure, summaries)

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Latest Scores
- Structure Detection: 7/10 ✗
- Character Extraction: 7/10 ✗
  - Completeness: 7/10
  - Identity Resolution: 7/10
  - Alias Grouping: 7/10
- Character Profiles: 6.5/10 ✗
- Chapter Summaries: 7.5/10 ✗
- Pronunciation Guide: 7/10 ✗
- HTML Presentation: 8/10 ✓
- **Overall: 7.10/10** (reference only)

## Overall Score Calculation

```
Overall = (7 × 0.20) + (7 × 0.25) + (6.5 × 0.15) + (7.5 × 0.20) + (7 × 0.10) + (8 × 0.10)
        = 1.40 + 1.75 + 0.975 + 1.50 + 0.70 + 0.80
        = 7.125 ≈ 7.10
```

**Overall: 7.10/10** (UP from 6.80 in attempt 38)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (5 categories below threshold)

## Detailed Evaluation

### 2.1 Structure Detection: 7/10 ✗ (unchanged)

"American, Sir" is a continuous short story with no chapter markers. The tool produces 2 sections, both with null titles. Per the rubric, a continuous text should be identified as a single section (9-10); splitting into 2 sections is a structural error (6-7). Score 7 because the summaries for each section are coherent and usable.

### 2.2 Character Extraction: 7/10 ✗ (UP from 6 — IMPROVEMENT)

**MAJOR IMPROVEMENT: The disambiguator fix WORKED.** Two separate John Donaldson characters now exist:
- `main_cast_1`: **John Donaldson** — 28 mentions, role: supporting, is_narrator: true
- `main_cast_3`: **John (the father)** — 29 mentions, role: supporting, is_narrator: false

This resolves the CRITICAL false merge from attempt 38. However, identity assignments have issues.

**Character list (8 total, 4 main_cast + 4 supporting):**
- `main_cast_1`: **John Donaldson** — 28 mentions, narrator: true
  - Aliases: ["John"]
  - **Issue:** Profile quotes ("American, Sir!", "Took money. Very unjustifiable.") are the FATHER's dialogue. This suggests the profile is contaminated — this entry may represent the father despite being titled generically.
  - **Issue:** Marked as narrator, but Uncle Bill is the true narrator ✗
- `main_cast_2`: **Uncle Bill** — 18 mentions, role: protagonist, narrator: false ✓ (role correct, but should be narrator)
  - Aliases: ["Bill"] ✓
- `main_cast_3`: **John (the father)** — 29 mentions, role: supporting, narrator: false
  - Aliases: ["the father", "John"] — "the father" as alias is unusual but not wrong ✓
  - Profile quotes include "He gave his name as John Donaldson" — this is the SON narrating about the father ✗ (profile contamination)
- `main_cast_4`: **Margaret Donaldson** — 2 mentions ✓
- `supporting_1`: **Joe Barron** — 3 mentions ✓
- `supporting_2`: **Red Cross** — 4 mentions — organization, not character ✗
- `supporting_3`: **Ted Frith** — 5 mentions, alias: "Ted" ✓
- `supporting_5`: **Johnny** — 2 mentions — FALSE SPLIT, should be alias of son ✗

**Sub-Dimension A: Completeness: 7/10** (UP from 6)
- Both father AND son exist as separate entries ✓ (was the #1 blocker, now resolved!)
- "Red Cross" is an organization, not a character ✗ (minor)
- "Johnny" exists as a separate character when it should be an alias of the son ✗
- All other significant characters present ✓

**Sub-Dimension B: Identity Resolution: 7/10** (UP from 5)
- Father and son are NOW separate characters ✓✓ (MAJOR improvement)
- Both entries share the alias "John" — this is ambiguous. "John" should only be alias of one ✗
- "Johnny" false split — should be alias of son ✗
- Narrator assignment wrong: `main_cast_1` (John Donaldson) is marked as narrator, but Uncle Bill is the true first-person narrator ✗

**Sub-Dimension C: Alias Grouping: 7/10** (stable)
- Uncle Bill has alias "Bill" ✓
- Ted Frith has alias "Ted" ✓
- Both John Donaldsons have "John" as alias — ambiguous overlap ✗
- "Johnny" as separate character rather than alias of son ✗
- "the father" as alias of John (the father) — technically works for narrator prep ✓

### 2.3 Character Profiles: 6.5/10 ✗ (UP from 6)

**Improvement:** Two separate profiles exist for father and son (was completely missing in attempt 38). But profiles are CROSS-CONTAMINATED — quotes and voice guidance are mixed between father and son.

- **Uncle Bill** (`main_cast_2`):
  - Tone: "calm, measured, gravelly baritone with restrained emotion" ✓
  - Quotes: "I will come to your commencement and bring you back..." ✓ (correct, this is Uncle Bill's letter)
  - Quotes: "I want you to know that I'll be prouder all my life..." ✓ (this IS Uncle Bill speaking to the dying father)
  - Quotes: "Do you suppose a great God is more narrow-minded than we?" ✓ (Uncle Bill to the son)
  - Relationships: "John Donaldson: mentor", "John Donaldson (father): ally" — mentor to son is correct ✓, "ally" for the father is odd (they're cousins/family) ✗
  - physical_description: null, personality_traits: null ✗
  - **Narrator flag missing** — Uncle Bill should be is_narrator: true ✗
  - Score: 7/10

- **John Donaldson** (`main_cast_1`, appears to be the son based on canonical name without disambiguator):
  - Tone: "calm, resonant baritone with restrained emotion — quiet authority and underlying sorrow" — sounds more like the FATHER ✗
  - Quotes: "American, Sir!" — this is the FATHER's catchphrase ✗✗
  - Quotes: "Took money. Very unjustifiable." — this is the FATHER confessing ✗✗
  - Quotes: "This is the happiest hour I've had for twenty years." — also the FATHER dying ✗✗
  - Relationships: "Uncle Bill: victimizer" — WRONG. Uncle Bill is the son's mentor/uncle figure. "Victimizer" applies to father→Uncle Bill (the father defrauded Bill's family) ✗
  - Relationships: "John Donaldson (son): parent" — This entry calls ITSELF a parent to the son, confirming the profile is actually describing the FATHER despite the generic canonical name ✗
  - **This entire profile is the FATHER's profile misattributed to the undisambiguated name** ✗✗
  - Score: 3/10

- **John (the father)** (`main_cast_3`):
  - Tone: "polished charm and aristocratic ease, then cracks under guilt" ✓ (fits father's arc)
  - Quotes: "American, Sir!" ✓ (correct for father)
  - Quotes: "He gave his name as John Donaldson." — this is the SON narrating, not the father speaking ✗
  - Relationships: "Narrator (Uncle Bill): victimizer" — incorrect label, but the CONCEPT is right (the father victimized Uncle Bill's family). The relationship direction is wrong though (should be "father victimized Bill" not "Bill is victimizer") ✗
  - Relationships: "John Donaldson (his son): father" ✓, "Margaret Donaldson: spouse" ✓
  - Score: 6/10

- **Ted Frith** (`supporting_3`):
  - Good profile with accurate quotes ✓
  - Score: 8/10

- **ALL characters have null physical_description and null personality_traits** ✗

**Why 6.5/10:** Two separate profiles exist (improvement from 6), and Uncle Bill and Ted Frith have good profiles. But `main_cast_1` has a completely wrong profile (father's content under the son's name), and `main_cast_3` has some contamination. The cross-contamination between the two same-name characters remains problematic.

### 2.4 Chapter Summaries: 7.5/10 ✗ (stable)

**Section 1:** Excellent. Correctly describes the cousin relationship, Margaret Donaldson, the scandal and faked death. Mentions Yale, the financial split of inheritance. ✓

**Section 2:** Good quality but the "sister" hallucination persists:
- "his deceased sister's twelve-year-old son" — WRONG. Uncle Bill is the father's COUSIN, not sibling. Section 1 correctly says "cousin." ✗
- Otherwise covers Yale enrollment, fishing trip to Canada, WWI enlistment, Red Cross ambulance work, Caporetto disaster, deathbed reunion and revelation. ✓

### 2.5 Pronunciation Guide: 7/10 ✗ (stable)

20 entries, 15 with IPA.

**Genuinely useful (13):** Caporetto, Piave, Solferino, Guerre, Venetia, Tagliamento, Bersagliari, Bordeaux (foreign terms ✓), live, minute, read, close, moderate (homographs ✓)

**False positives (7):** whippersnapper, thriftless, thickset, manliness, dum-dums, orderlies, mayn't ✗

35% false positive rate. The foreign terms and homographs are excellent, but the false positives keep this at 7.

### 2.6 HTML Presentation: 8/10 ✓ (stable)

Navigation works. Character profiles render well. Uncle Bill displayed as protagonist. Two John Donaldson entries now visible with distinct profiles. Minor issues: "Red Cross" in characters, "Johnny" as separate character.

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (user-configured, appropriate)
- Pipeline: V2 with Phase 2 graph-based identity resolution
- 0 LLM retries — good
- Stage 3 (profiling): 13 LLM calls, 748s — reasonable
- Stage 2 (character extraction): 28 LLM calls, 239s — reasonable
- No JSON parse failures ✓

## Current Issues (Priority Order)

### CRITICAL

1. **Profile cross-contamination: `main_cast_1` "John Donaldson" has the FATHER's profile** [Profiles / Identity Resolution]
   - Problem: `main_cast_1` is the undisambiguated "John Donaldson" (presumably the son) but its entire profile — tone, quotes, relationships — describes the FATHER. Quotes: "American, Sir!", "Took money. Very unjustifiable.", "This is the happiest hour I've had for twenty years." are ALL the father's dialogue. The relationship "John Donaldson (son): parent" confirms the profile THINKS it's the father.
   - Meanwhile, `main_cast_3` "John (the father)" has a separate father profile that's mostly correct.
   - Result: **The son has NO usable profile.** `main_cast_1` was supposed to be the son but got the father's profile. `main_cast_3` is explicitly the father.
   - Root cause: The passage disambiguation/profile extraction stage can't distinguish which "John Donaldson" a passage belongs to when the canonical name is identical or ambiguous. The `main_cast_1` entry has canonical name "John Donaldson" (no disambiguator), so the profiler attributes father's passages to it.
   - Location: `src/pipeline/character_profiling/` — the passage gatherer/disambiguator collects evidence passages, and without clear disambiguators, father's dialogue gets assigned to the generic "John Donaldson" entry.
   - Fix approach: The son's canonical name should also have a disambiguator — e.g., "John Donaldson (the son)" — so the profiler can distinguish them. Currently only the father has "(the father)" in his canonical name. The son needs "(the son)" too.

### HIGH

2. **Narrator assignment wrong: Uncle Bill should be narrator, not John Donaldson** [Identity Resolution]
   - Problem: `main_cast_1` "John Donaldson" is marked `is_narrator: true`, but Uncle Bill is the first-person narrator of the story. The son narrates a war story within the frame but is not the primary narrator.
   - `main_cast_2` "Uncle Bill" has `is_narrator: false` despite being the actual "I" of the story.
   - This is a non-deterministic LLM issue — narrator detection varies across attempts.

3. **"Johnny" false split — should be alias of son** [Identity Resolution / Alias Grouping]
   - Problem: `supporting_5` "Johnny" with 2 mentions exists as a separate character. "Johnny" is a childhood nickname for the son.
   - If `main_cast_1` is the son, "Johnny" should be merged as alias.

4. **Summary "sister" hallucination** [Summaries]
   - Problem: Section 2 says "his deceased sister's twelve-year-old son" — Uncle Bill is the father's COUSIN, not sibling.
   - Evidence: Section 1 correctly says "cousin."
   - Non-deterministic LLM issue.

5. **All characters have null physical_description and null personality_traits** [Profiles]
   - Problem: Every character has `physical_description: null` and `personality_traits: null`. Only `voice_guidance` is populated.
   - These are separate fields in the character schema and should be populated.

### MEDIUM

6. **Both John Donaldsons share "John" as alias — ambiguous** [Alias Grouping]
   - `main_cast_1` aliases: ["John"], `main_cast_3` aliases: ["the father", "John"]
   - "John" should only be alias of one character (likely the son, since "the father" wouldn't be called just "John" in context).

7. **"Red Cross" extracted as character** [Completeness]
   - Organization, not a character (`supporting_2`, 4 mentions).

8. **Pronunciation: 7/20 false positives (35%)** [Pronunciation]
   - Remaining false positives: whippersnapper, thriftless, thickset, manliness, dum-dums, orderlies, mayn't.

9. **Structure: 2 sections for continuous short story** [Structure]
   - Same as all prior attempts.

10. **Relationship labels confused** [Profiles]
    - Uncle Bill → "John Donaldson: mentor" (should be: "uncle/mentor to son")
    - John Donaldson → "Uncle Bill: victimizer" (direction wrong — the father victimized Bill's family, Uncle Bill is not the victimizer)

### LOW

11. **Father listed as "supporting" role** — Could be "antagonist" given the scandal/deception arc, but "supporting" is acceptable.

## Fix Priority

**The disambiguator fix (attempt 39) was a SUCCESS for character extraction** — father and son are now separate entities. Score improved from 6.80 to 7.10. However, the profile cross-contamination (CRITICAL #1) is the new blocker.

**Recommended fix for attempt 40:**

The root cause of CRITICAL #1 is that `main_cast_1` "John Donaldson" (the son) has NO disambiguator in his canonical name, while `main_cast_3` "John (the father)" does. This means the profiler can't tell which "John Donaldson" a passage belongs to and defaults to attributing father-related passages to the generic name.

**Fix:** Ensure BOTH same-name characters get disambiguators in their canonical names. The `_clean_canonical_name()` fix in attempt 39 preserved disambiguators that the LLM output, but if the LLM only outputs a disambiguator for one of the two same-name characters, the other gets the bare name. The fix should:
1. In `_process_consolidated_pass2()` (or downstream), detect when two characters have the same bare name (after stripping disambiguators) and ensure BOTH have disambiguators
2. If only one has a disambiguator, infer a complementary one for the other (e.g., if one is "John Donaldson (the father)", the other should be "John Donaldson (the son)")
3. This makes both distinguishable by name throughout the entire pipeline

## Fix History

### Attempt 40 — Ensure both same-name characters get disambiguators — TARGETING CRITICAL #1
- **Issue targeted:** CRITICAL #1 — Profile cross-contamination (son has father's profile content)
- **Root cause:** `_process_consolidated_pass2()` line 726 builds `char_by_name` dict. If two characters have the same bare name (e.g., "John Donaldson") but only ONE has a disambiguator ("John (the father)"), the dict key collision overwrites the first character. The profiler then can't distinguish which passages belong to which "John Donaldson."
- **Changes made:**
  1. Added `_ensure_same_name_disambiguation()` method that detects when multiple characters share the same bare name (after stripping disambiguators)
  2. If only some have disambiguators, infers complementary disambiguators for the others (e.g., "father" → "the son", "Sr." → "Jr.")
  3. Calls this method at the start of `_process_consolidated_pass2()` to ensure ALL same-name characters have unique canonical names BEFORE building the char_by_name dict
- **Expected result:** Both father and son should have distinct canonical names with disambiguators, allowing the profiler to correctly attribute passages to each. This should resolve profile cross-contamination.
- **Files modified:**
  - `src/pipeline/character_extraction_v2/main_cast.py` (added `_ensure_same_name_disambiguation()` and `_infer_complementary_disambiguator()` methods, modified `_process_consolidated_pass2()` to call the new method)
  - `tests/test_character_extraction_v2.py` (updated line count limit from 7150 to 7300 to accommodate new code)
- **Smoke test:** TBD - needs re-analysis

### Attempt 39 — Preserve disambiguators in canonical names — PARTIAL SUCCESS
- **Issue targeted:** CRITICAL #1 — Father/son FALSE MERGE (son completely missing)
- **Changes made:** Modified `_clean_canonical_name()` to preserve relationship/role disambiguators like "(the son)", "(father)", "(elder)", "(Sr.)"
- **Result:** Two separate John Donaldson characters now exist ✓. Score: 6.80→7.10 (+0.30). Character Extraction 6→7. Identity Resolution 5→7.
- **Remaining issue:** Only the father got a disambiguator ("John (the father)"). The son is still just "John Donaldson" without one. This causes profile cross-contamination — the profiler can't distinguish which passages belong to the son vs the father when one has a bare name.
- **Files modified:**
  - `src/pipeline/character_extraction_v2/main_cast.py` (lines 855-895, modified `_clean_canonical_name()` method)

### Attempt 38 — REVERT target character preference signal — REGRESSION
- Score: 6.90→6.80

### Attempt 37 — Target character preference in passage disambiguation — REGRESSION
- Score: 7.15→6.90

### Attempt 36 — Generational suffix handling in mention search — PARTIAL SUCCESS
- Score: 7.05→7.15

### Attempt 35 — Make ROLE_CONFLICT constraint HARD — PARTIAL SUCCESS
- Score: 6.80→7.05

### Attempt 34 — Adaptive promotion thresholds — PARTIAL SUCCESS
- Score: 6.65→6.80

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 40 | Ensure both same-name characters get disambiguators | `main_cast.py`, `test_character_extraction_v2.py` | TBD - awaiting analysis |
| 39 | Preserve disambiguators in canonical names | `main_cast.py` | PARTIAL SUCCESS — two characters ✓, profile contamination ✗. Characters 6→7. Score: 6.80→7.10 |
| 38 | REVERT target preference signal | `name_disambiguator.py` | REGRESSION — son false-merged. Score: 6.90→6.80 |
| 37 | Profile passage disambiguation | `name_disambiguator.py` | REGRESSION — duplicate profiles. Score: 7.15→6.90 |
| 36 | Grounding gate Sr./Jr. suffix | `mention_search.py`, `test_character_extraction_v2.py` | PARTIAL SUCCESS. Score: 7.05→7.15 |
| 35 | ROLE_CONFLICT hard constraint | `identity_graph.py` | PARTIAL SUCCESS. Score: 6.80→7.05 |
| 34 | Adaptive promotion thresholds | `characters.py` | PARTIAL SUCCESS. Score: 6.65→6.80 |
| 33 | Possessive stripping + narrator detection | `supporting.py`, `narrator.py` | MIXED. Score: 6.65 |
| 32 | Alias cleanup | `evidence_collectors.py`, `main_cast.py` | NO EFFECT |
| 31 | Deterministic same-name constraint | `evidence_collectors.py` | SUCCESS. Score: 6.78→7.33 |
| 30 | Pronunciation false positives | `character_proposer.py`, `foreign_proposer.py` | Pronunciation improved, character regression |
| 29 | Disambiguation labels post-processing | `characters.py` | SUCCESS. Score: 7.13 |

**PATTERN:** The disambiguator approach (attempts 29, 39) is the most promising strategy. Attempt 39 achieved the split but only one character got a disambiguator. The next step is to ensure BOTH same-name characters get disambiguators.

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.60 | — | Original baseline |
| 22 | 7.55 | +0.95 | Best score (all fixes active) |
| 23 | 6.30 | -0.30 | Clean baseline + Phase 2 pipeline |
| 31 | 7.33 | +0.73 | Deterministic same-name fix SUCCESS |
| 34 | 6.80 | +0.20 | Uncle Bill restored |
| 35 | 7.05 | +0.45 | HARD constraint works, father filtered |
| 36 | 7.15 | +0.55 | Father grounded ✓, profiles contaminated ✗ |
| 37 | 6.90 | +0.30 | REGRESSION — identical duplicate profiles |
| 38 | 6.80 | +0.20 | REGRESSION — son false-merged into father |
| 39 | 7.10 | +0.50 | Father/son SPLIT ✓, profile contamination ✗ |

## Next Action
Run PROMPT_fix.md to address profile cross-contamination (CRITICAL #1) — ensure both same-name characters get disambiguators in canonical names.
