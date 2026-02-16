# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 32
- **Phase:** awaiting_analysis
- **baseline_score:** 6.60
- **Competitive Mode:** single (all stages: characters, structure, summaries)

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Pipeline Notes
- Analysis completed in 98m 35s (completed at 18:29)
- Competitive consensus ENABLED for characters, structure, summaries stages
- 60 LLM calls, 95,986 tokens
- Found 8 characters (4 main_cast + 4 supporting), 2 chapters, 21 pronunciation flags
- 0 LLM retries, 1 JSON parse failure (Pronunciation Guide)
- **Deterministic same-name constraint fix VERIFIED WORKING**

## Latest Scores
- Structure Detection: 7/10 ✗
- Character Extraction: 7.5/10 ✗
  - Completeness: 8/10
  - Identity Resolution: 8/10
  - Alias Grouping: 6.5/10
- Character Profiles: 7/10 ✗
- Chapter Summaries: 7.5/10 ✗
- Pronunciation Guide: 7/10 ✗
- HTML Presentation: 8/10 ✓
- **Overall: 7.33/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (5 categories below threshold)

## Overall Score Calculation

```
Overall = (7 × 0.20) + (7.5 × 0.25) + (7 × 0.15) + (7.5 × 0.20) + (7 × 0.10) + (8 × 0.10)
        = 1.40 + 1.875 + 1.05 + 1.50 + 0.70 + 0.80
        = 7.325
```

**Overall: 7.33/10** (UP from 6.78 in attempt 30 — significant improvement, highest since attempt 22)

## Detailed Evaluation

### 2.1 Structure Detection: 7/10 ✗

Unchanged from previous attempts. "American, Sir" is a continuous short story with no chapter markers. The tool produces 2 sections, both with null titles and null start/end lines. Per the rubric, a continuous text should be identified as a single section (9-10); splitting into 2 sections is a structural error (6-7). Score 7 because the summaries for each section are coherent and usable despite the artificial split.

### 2.2 Character Extraction: 7.5/10 ✗ (UP from 5.5 — MAJOR RECOVERY)

**The deterministic same-name constraint fix WORKED.** Father and son are now separate entries with correct disambiguation labels.

**Character list (8 total, 4 main_cast + 4 supporting):**
- `main_cast_1`: **Uncle Bill** — 18 mentions, `is_narrator: true`, role: `protagonist` ✓✓ (promoted from supporting!)
- `main_cast_2`: **John Donaldson (the son)** — 9 mentions, `is_narrator: true`, role: `supporting` ✓ (split restored!)
- `main_cast_3`: **John Donaldson (the father)** — 29 mentions, role: `supporting` ✓ (split restored!)
- `main_cast_4`: **Margaret Donaldson** — 2 mentions, role: `supporting` ✓
- `supporting_2`: **Joe Barron** — 3 mentions ✓
- `supporting_3`: **Red Cross** — 4 mentions — organization, not character ✗
- `supporting_5`: **Ted Frith** — 5 mentions, alias: "Ted" ✓
- `supporting_7`: **Johnny** — 2 mentions — should be alias of the son ✗

**What improved from attempt 30:**
1. Father/son SPLIT RESTORED with disambiguation labels "(the son)" and "(the father)" ✓✓
2. Uncle Bill PROMOTED to `main_cast_1` with role `protagonist` and `is_narrator: true` ✓✓
3. Both John Donaldsons now in main_cast (not supporting) ✓

**Sub-Dimension A: Completeness: 8/10** (UP from 7)
- Uncle Bill present as protagonist ✓
- Father and son both present as separate entries ✓
- Margaret Donaldson present ✓
- Joe Barron, Ted Frith present ✓
- "Red Cross" is an organization, not a character ✗ (minor — doesn't hurt)
- "Johnny" should be alias, not separate entry ✗

**Sub-Dimension B: Identity Resolution: 8/10** (UP from 4 — huge recovery)
- Father/son correctly split into two separate entries ✓✓
- Disambiguation labels correctly applied ✓
- The son is `is_narrator: true` — correct, he narrates the wartime section ✓
- Note: The son also having `is_narrator: true` alongside Uncle Bill is slightly unusual (there's a nested narrative structure), but acceptable ✓
- "Johnny" remains separate instead of being alias of the son ✗ (minor)

**Sub-Dimension C: Alias Grouping: 6.5/10** (DOWN from 7 — minor)
- "John Donaldson's" (possessive) appears as alias of the father ✗
- "the father" as alias of John Donaldson (the father) — redundant but not harmful
- "John" as alias of the father — correct ✓
- "Ted" → Ted Frith: correct ✓
- "Bill" → Uncle Bill: correct ✓
- "Johnny" separate instead of alias of the son ✗
- The son has NO aliases — should have "Johnny", "John" ✗

### 2.3 Character Profiles: 7/10 ✗

**Uncle Bill (main_cast_1): MIXED**
- Personality: null ✗ — should have rich personality data (the story is told from his perspective)
- Physical: null ✗
- Relationships: "John Donaldson (father): mentor", "John Donaldson (son): mentor", "Margaret Donaldson: acquaintance"
  - The "mentor" label for both is acceptable but imprecise — he's the son's guardian/uncle, not really the father's mentor
  - "Margaret Donaldson: acquaintance" — correct, they have minimal contact
- Voice guidance: EXCELLENT ✓ — tone, dialect, verbal tics, example quotes all present and accurate
- The voice guidance is the standout: "A low, measured, reserved tone—calm but heavy with unspoken emotion" perfectly captures Uncle Bill

**John Donaldson (the son) (main_cast_2): SPARSE**
- Personality: null ✗
- Physical: null ✗
- Relationships: empty ✗
- Voice guidance: generic "No specific voice guidance available" ✗
- This character has NO useful profile data — he needs at minimum relationships (Uncle Bill: guardian, John Donaldson (the father): father)

**John Donaldson (the father) (main_cast_3): GOOD**
- Personality: null ✗ — but the voice guidance compensates
- Physical: null ✗
- Relationships: "John Donaldson (the son): father", "Uncle Bill: acquaintance"
  - "father" is correct ✓
  - "acquaintance" for Uncle Bill is imprecise — they're cousins — but acceptable
- Voice guidance: EXCELLENT ✓ — "A voice worn by years of secrecy, but steady and proud" captures him well
- Verbal tics: "repeats 'American, sir' with solemn emphasis" — perfect ✓
- Example quotes include the pivotal "American, sir" line ✓

**Why 7/10:** Voice guidance is excellent for Uncle Bill and the father — genuinely useful for narrators. But all `personality` and `physical_description` fields are null. The son has NO profile data at all. Relationships exist for 3/8 characters but some labels are imprecise. The null personality/physical fields for main characters with rich textual descriptions drags the score down.

### 2.4 Chapter Summaries: 7.5/10 ✗ (stable)

**Section 1:** EXCELLENT. Correctly describes Uncle Bill's background, the letter from young John, the cousin relationship, the scandal, Margaret Donaldson. Uses "cousin" correctly. `characters_present`: ["Narrator"] — acceptable but could include named characters.

**Section 2:** Good quality but contains the recurring "sister" hallucination:
- "his deceased sister's twelve-year-old son" — WRONG. Uncle Bill is the father's COUSIN, not brother/sister. Section 1 correctly says "cousin."
- Otherwise excellent: covers Yale, fishing trip, WWI, Caporetto, reunion, deathbed revelation.
- `characters_present`: ["Uncle Bill", "John Donaldson (the son)", "John Donaldson (the father)"] — EXCELLENT, disambiguated names ✓✓ (this was missing in attempt 30!)

**Why 7.5/10:** The "sister" factual error in section 2 prevents a higher score. Otherwise both summaries are comprehensive, well-written, and useful for narrators. The disambiguated character names in `characters_present` for section 2 is a clear improvement.

### 2.5 Pronunciation Guide: 7/10 ✗ (stable)

21 entries, 16 with IPA.

**Genuinely useful foreign terms (8):** Caporetto, Piave, Solferino, Guerre, Venetia, Tagliamento, Bersagliari, Bordeaux — excellent ✓

**Acceptable homographs (5):** live, minute, read, close, moderate — context-dependent, genuinely useful ✓

**False positives (8):**
- Common English words: whippersnapper, thriftless, thickset, manliness — uncommon but not pronunciation challenges ✗
- Military/medical terms: dum-dums, orderlies — standard pronunciation ✗
- Archaic contraction: mayn't — borderline ✗
- **"was" reappeared** — this was removed in attempt 30 but came back ✗ (possible LLM non-determinism or the fix didn't persist through reanalysis)

**Why 7/10:** 8/21 entries (38%) are false positives. The "was" regression is minor but notable. The remaining false positives are uncommon-but-real English words that are harder to filter generically.

### 2.6 HTML Presentation: 8/10 ✓

**What improved:**
1. Disambiguation labels RESTORED: "John Donaldson (the son)" and "John Donaldson (the father)" displayed correctly ✓
2. Uncle Bill now in Main Characters section with protagonist role ✓
3. 3 Main Characters displayed (Uncle Bill, the son, the father) ✓
4. Section 2 `characters_present` shows disambiguated names ✓
5. Voice guidance sections render well for Uncle Bill and the father ✓
6. Navigation works ✓

**Minor issues:**
- "John Donaldson's" (possessive) shown as alias ✗
- "Red Cross" and "Johnny" still in Supporting Characters ✗
- Section 1 `characters_present` only shows "Narrator" — could be more specific

**Why 8/10:** The HTML correctly renders the improved upstream data. Disambiguation labels, proper main character placement, and functional navigation make this usable for a narrator. Minor alias and supporting character issues don't significantly impact usability.

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (user-configured, appropriate)
- Pipeline: V2 with Phase 2 graph-based identity resolution
- Identity graph: `role_conflict` constraint edge now generated DETERMINISTICALLY ✓
- main_cast_count: 4 (UP from 2 in attempt 30 — fixed!)
- supporting_cast_count: 4
- 0 LLM retries — good
- 1 JSON parse failure in Pronunciation Guide stage
- No config changes recommended
- Profiling: 5 stages, all successful

## Current Issues (Priority Order)

### CRITICAL
(None — the father/son regression is FIXED!)

### HIGH

1. **Alias grouping below threshold: 6.5/10** [Alias Grouping]
   - Problem: "Johnny" exists as separate `supporting_7` instead of alias of "John Donaldson (the son)". "John Donaldson's" (possessive) is an invalid alias. The son has ZERO aliases.
   - Evidence: "Johnny" is clearly a diminutive of "John" used for the son. The possessive form "John Donaldson's" should be stripped.
   - Location: `src/pipeline/character_extraction_v2/supporting.py` (Johnny extracted as separate supporting character), `src/pipeline/character_extraction_v2/main_cast.py` or `src/agents/characters.py` (possessive not stripped)
   - Fix approach: Two sub-fixes needed:
     a. Strip possessive forms ("'s" suffix) from aliases during post-processing
     b. Add logic to merge diminutive names (Johnny→John) with same-surname main_cast entries when they have low mention counts

2. **Character profiles missing personality/physical descriptions** [Profiles]
   - Problem: All 8 characters have `personality: null` and `physical_description: null`. The son has NO profile data at all (empty relationships, empty voice guidance).
   - Evidence: The text contains rich personality and physical descriptions — Uncle Bill is described as "crabbed and prejudiced and critical" and "thoroughly selfish"; the father is described with "physical beauty" and "charm."
   - Location: `src/pipeline/character_profiling/` — the profiling pipeline generates voice guidance but not personality/physical fields
   - Note: This is a persistent issue across all attempts. Voice guidance quality is excellent, suggesting the pipeline has access to the right text but isn't populating these specific fields.

3. **Summary "sister"/"brother" hallucination** [Summaries]
   - Problem: Section 2 says "his deceased sister's twelve-year-old son" — Uncle Bill is the father's COUSIN, not sibling.
   - Evidence: Section 1 correctly says "cousin"
   - Location: LLM generation in summary pipeline — this may be non-deterministic

### MEDIUM

4. **"Red Cross" extracted as character** [Completeness]
   - Problem: Organization, not a character (`supporting_3`, 4 mentions). Same as all prior attempts.
   - Location: `src/pipeline/character_extraction_v2/supporting.py`

5. **Pronunciation: 8/21 false positives (38%)** [Pronunciation]
   - Remaining false positives: whippersnapper, thriftless, thickset, manliness, dum-dums, orderlies, mayn't, was
   - "was" reappeared despite being removed in attempt 30
   - Location: `src/pipeline/pronunciation_guide/proposers/`

6. **Structure: 2 sections for continuous short story** [Structure]
   - Same as all prior attempts. Not worth a targeted fix for this text alone.

### LOW

7. **Section 1 `characters_present` only shows "Narrator"** — should list named characters
8. **Uncle Bill relationship to father labeled "mentor"** — imprecise, should be "cousin/guardian"

## Fix Priority

**Focus on crossing 8.0 in the most categories:**

The closest categories to threshold are:
- **Character Extraction: 7.5** — needs alias grouping improvement (+1.5 on that sub-dimension)
- **Character Profiles: 7** — needs personality/physical fields populated
- **Chapter Summaries: 7.5** — needs "sister"/"brother" hallucination fixed
- **Pronunciation: 7** — needs false positive reduction
- **Structure: 7** — hard to fix generically; continuous text detection needed

**Recommended fix order:**
1. **Alias cleanup** (HIGH #1) — strip possessives, merge "Johnny" with the son. This directly improves Character Extraction from 7.5 toward 8+.
2. **Profiles** (HIGH #2) — if personality/physical fields can be populated from existing evidence, this lifts Profiles from 7 toward 8+.
3. **Summary hallucination** and **pronunciation** are LLM-dependent and harder to fix deterministically.

## Fix History

### Attempt 32 — Alias cleanup (possessive stripping + nickname matching)
- **Issue targeted:** HIGH #1 — Alias grouping below threshold (6.5/10)
- **Root causes:**
  1. Possessive forms ("John Donaldson's") included as aliases without stripping
  2. "Johnny" (supporting cast) not merged with "John Donaldson (the son)" (main cast) - missing nickname mapping
- **Changes made:**
  1. Added `COMMON_NICKNAMES` entries: `"john": ["jonathan"]`, `"johnny": ["john", "jonathan"]` in `evidence_collectors.py`
  2. Added `_strip_possessive()` helper function to `main_cast.py` - removes trailing "'s" and "'" from aliases
  3. Applied `_strip_possessive()` to all alias assignment locations in `main_cast.py` (lines 690, 695, 757, 764, 953, 955)
- **Universality:** YES
  - "Johnny" → "John" is universal diminutive (like "Tommy" → "Tom" already in list)
  - Possessive stripping is universal English grammar pattern
- **Smoke test:** Unit tests verify possessive stripping and nickname matching logic
- **Test suite:** 336 passed, 8 failed (pre-existing test_semantic_conflicts failures), 10 skipped
- **Files modified:** `src/pipeline/character_extraction_v2/evidence_collectors.py`, `src/pipeline/character_extraction_v2/main_cast.py`
- **Expected impact:** Character Extraction: Alias Grouping 6.5→8+ (eliminates possessive aliases, merges Johnny→son)

### Attempt 31 — Deterministic same-name constraint (SUCCESS!)
- **Issue targeted:** CRITICAL #1 — Father/son merged (regression from attempt 29)
- **Changes made:** Added deterministic check in `evidence_collectors.py:collect_constraint_evidence()` — if two main_cast characters have identical `canonical_name`, automatically add `role_conflict` constraint edge
- **Result:** SUCCESS — Father/son split restored, disambiguation labels applied, Uncle Bill promoted to protagonist
- **Score impact:** 6.78 → 7.33 (+0.55)
- **File modified:** `src/pipeline/character_extraction_v2/evidence_collectors.py`

### Attempt 30 — Pronunciation false positive reduction (PARTIAL SUCCESS + REGRESSION)
- **Issue targeted:** HIGH #3 — Pronunciation: 17/31 entries are false positives (~55%)
- **Changes made:** CMU dictionary safety check, ENGLISH_EXCEPTIONS additions
- **Result:** Pronunciation improved (5→7), BUT character regression (father/son merged)
- **Score:** 6.78
- **Files modified:** `character_proposer.py`, `foreign_proposer.py`

### Attempt 29 — Disambiguation labels via post-processing (SUCCESS!)
- **Issue targeted:** Two identical "John Donaldson" entries need labels
- **Changes made:** Added `_apply_disambiguation_labels_from_constraints()` post-processing
- **Result:** SUCCESS — Labels applied correctly
- **Score:** 7.13
- **File modified:** `src/agents/characters.py`

### Attempt 28 — Revert to attempt 25 state
- **Result:** SUCCESS — main_cast restored
- **Score:** 6.65

### Previous attempts — see earlier evaluation states

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 32 | Alias cleanup (possessive + nicknames) | `evidence_collectors.py`, `main_cast.py` | PENDING — awaiting analysis |
| 31 | Deterministic same-name constraint | `evidence_collectors.py` | SUCCESS — father/son split restored, score 6.78→7.33 |
| 30 | Pronunciation false positives | `character_proposer.py`, `foreign_proposer.py` | Pronunciation improved (5→7), BUT character regression |
| 29 | Disambiguation labels post-processing | `characters.py` | SUCCESS — labels applied, score 7.13 |
| 28 | Revert to attempt 25 (undo regression) | `characters.py` | SUCCESS — main_cast restored |
| 27 | Revert + re-implement disambiguation labels | `characters.py` | WORSE REGRESSION — main_cast_count: 0 |
| 26 | Disambiguation labels for same-name characters | `characters.py` | REGRESSION — main_cast_2 dropped |
| 25 | Father/son disambiguation (data flow fix) | `characters.py` | SUCCESS — split works but identical names |
| 24 | Father/son disambiguation | `evidence_collectors.py`, `characters.py` | NO EFFECT |
| 23 (baseline) | Clean baseline + Phase 2 pipeline | N/A | Score: 6.30 |

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.60 | — | Original baseline |
| 22 | 7.55 | +0.95 | Best score (all fixes active) |
| 23 | 6.30 | -0.30 | Clean baseline + Phase 2 pipeline |
| 24 | 6.15 | -0.45 | Fix had no effect; profiles worse |
| 25 | 6.50 | -0.10 | Father/son split working but needs labels |
| 26 | 6.40 | -0.20 | REGRESSION — labels dropped main_cast_2 |
| 27 | 5.75 | -0.85 | WORSE REGRESSION — main_cast pipeline broken |
| 28 | 6.65 | +0.05 | Revert successful — main_cast restored |
| 29 | 7.13 | +0.53 | Disambiguation labels SUCCESS |
| 30 | 6.78 | +0.18 | Pronunciation improved but father/son merge regression |
| 31 | 7.33 | +0.73 | Deterministic same-name fix SUCCESS — highest since attempt 22 |

## Next Action

**Phase:** awaiting_analysis

Re-run analysis to verify:
1. "John Donaldson's" possessive removed from aliases
2. "Johnny" merged with "John Donaldson (the son)" via nickname matching
3. Character Extraction: Alias Grouping score improves from 6.5→8+

If successful, subsequent fixes may address:
- **Profile population** (personality/physical fields) — to push Profiles 7→8+
- **Summary hallucination** or **pronunciation** improvements
