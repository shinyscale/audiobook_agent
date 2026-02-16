# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 33
- **Phase:** awaiting_analysis
- **baseline_score:** 6.60
- **Competitive Mode:** single (all stages: characters, structure, summaries)

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Pipeline Notes
- Analysis completed in 36m 6s
- 62 LLM calls, 97,754 tokens
- Found 8 characters, 2 chapters, 20 pronunciation flags
- 0 LLM retries, 1 JSON parse failure (Pronunciation Guide)
- Profiling shows Character Profiles as bottleneck (550s / 25% of total time)

## Latest Scores
- Structure Detection: 7/10 ✗
- Character Extraction: 7/10 ✗
  - Completeness: 8/10
  - Identity Resolution: 7/10
  - Alias Grouping: 6/10
- Character Profiles: 7.5/10 ✗
- Chapter Summaries: 7.5/10 ✗
- Pronunciation Guide: 7/10 ✗
- HTML Presentation: 8/10 ✓
- **Overall: 7.23/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (5 categories below threshold)

## Overall Score Calculation

```
Overall = (7 × 0.20) + (7 × 0.25) + (7.5 × 0.15) + (7.5 × 0.20) + (7 × 0.10) + (8 × 0.10)
        = 1.40 + 1.75 + 1.125 + 1.50 + 0.70 + 0.80
        = 7.275
```

**Overall: 7.28/10** (DOWN from 7.33 in attempt 31 — minor regression)

## Detailed Evaluation

### 2.1 Structure Detection: 7/10 ✗

Unchanged from previous attempts. "American, Sir" is a continuous short story with no chapter markers. The tool produces 2 sections, both with null titles and null start/end lines. Per the rubric, a continuous text should be identified as a single section (9-10); splitting into 2 sections is a structural error (6-7). Score 7 because the summaries for each section are coherent and usable despite the artificial split.

### 2.2 Character Extraction: 7/10 ✗ (DOWN from 7.5 — regression)

**The alias cleanup fix DID NOT WORK.** "Johnny" is still a separate supporting character (supporting_6), and "John Donaldson's" (possessive) is still an alias of the father.

**Additionally, Uncle Bill LOST `is_narrator: true` and `role: protagonist`** — both were correct in attempt 31 and have regressed. Uncle Bill is unambiguously the narrator (the story is told from his first-person perspective throughout) and the protagonist.

**Character list (8 total, 4 main_cast + 4 supporting):**
- `main_cast_1`: **John Donaldson (the son)** — 9 mentions, `is_narrator: true`, role: `supporting`
  - `is_narrator: true` is correct (he narrates the wartime section) ✓
  - Aliases: NONE — should have "Johnny", "John" ✗
- `main_cast_2`: **John Donaldson (the father)** — 32 mentions, role: `supporting`
  - Aliases: ["the father", "the man", "John", "John Donaldson's"] — possessive still present ✗
- `main_cast_3`: **Uncle Bill** — 19 mentions, `is_narrator: false`, role: `supporting`
  - Should be `is_narrator: true` and `role: protagonist` ✗✗ (REGRESSION from attempt 31)
  - Aliases: ["Bill", "Uncle"] ✓
- `main_cast_4`: **Margaret Donaldson** — 2 mentions ✓
- `supporting_1`: **Joe Barron** — 3 mentions ✓
- `supporting_2`: **Red Cross** — 4 mentions — organization, not character ✗
- `supporting_4`: **Ted Frith** — 5 mentions, alias: "Ted" ✓
- `supporting_6`: **Johnny** — 2 mentions — should be alias of the son ✗

**Sub-Dimension A: Completeness: 8/10** (stable)
- All expected characters present ✓
- "Red Cross" is an organization, not a character ✗ (minor)
- "Johnny" should be alias, not separate entry ✗

**Sub-Dimension B: Identity Resolution: 7/10** (DOWN from 8)
- Father/son correctly split with disambiguation labels ✓
- Uncle Bill lost narrator status — he IS the primary narrator ✗ (REGRESSION)
- Uncle Bill lost protagonist role ✗ (REGRESSION)
- "Johnny" remains separate instead of being alias of the son ✗

**Sub-Dimension C: Alias Grouping: 6/10** (DOWN from 6.5)
- "John Donaldson's" (possessive) still an alias of the father ✗ — fix didn't work
- "Johnny" separate instead of alias of the son ✗ — fix didn't work
- The son has ZERO aliases — should have "Johnny", "John" ✗
- "the man" as alias of the father — unusual but not wrong
- "Ted" → Ted Frith: correct ✓
- "Bill", "Uncle" → Uncle Bill: correct ✓

### 2.3 Character Profiles: 7.5/10 ✗ (UP from 7 — improvement)

**Major improvement:** Uncle Bill and the father now have rich personality summaries, traits, and evidence quotes. This was all null in attempt 31.

**Uncle Bill:** GOOD profile
- Personality summary: "morally ambiguous: initially cold and self-centered, he undergoes quiet transformation" ✓
- Traits: ["Self-centered", "Reluctantly compassionate", "Emotionally repressed", "Capable of profound moral reflection", "Prideful yet redeemable"] ✓✓
- Evidence quotes: 4 excellent, accurate quotes from text ✓✓
- Relationships: {"John Donaldson": "mentor", "John Donaldson (father)": "ally"} — imprecise (should be guardian/cousin) ✗
- Physical: null ✗
- Voice guidance: EXCELLENT ✓

**John Donaldson (the father):** EXCELLENT profile
- Personality: "morally ambiguous man who committed grave betrayals... yet redeemed himself" ✓✓
- Traits and evidence quotes accurate ✓✓
- Relationships: {"John Donaldson (the son)": "parent", "Uncle Bill": "acquaintance"} — "parent" is correct, "acquaintance" should be "cousin" ✗
- Voice guidance with "American, sir" verbal tic ✓✓

**John Donaldson (the son):** EMPTY — NO profile data at all ✗
- Personality: "Insufficient information" — but there IS information in the text about him
- Relationships: empty ✗ — should at minimum have Uncle Bill and his father
- Voice guidance: generic placeholder ✗

**Ted Frith:** CONTAMINATED profile ✗
- Evidence quotes attributed to Ted are actually the FATHER's quotes: "'this is my good day. I'm American to-day, sir!'" is John Donaldson (the father), not Ted Frith
- This is a cross-contamination error in the profiling pipeline
- Relationships list "Uncle Bill (narrator)" — but Uncle Bill isn't marked as narrator in this attempt

**Why 7.5/10:** The personality and voice guidance improvements for Uncle Bill and the father are genuinely excellent and useful for narrators. But the son has NO profile data, Ted Frith's profile is contaminated with the father's quotes, and physical descriptions remain null for all characters.

### 2.4 Chapter Summaries: 7.5/10 ✗ (stable)

**Section 1:** EXCELLENT. Correctly describes the cousin relationship, the narrator's background, Margaret Donaldson. `characters_present`: ["Narrator"] — acceptable but could include named characters.

**Section 2:** Good quality but the recurring hallucination persists:
- "his deceased sister's son" — WRONG. Uncle Bill is the father's COUSIN, not sibling. Section 1 correctly says "cousin."
- Otherwise excellent: covers Yale, fishing trip, WWI, Caporetto, reunion, deathbed revelation.
- `characters_present`: ["Uncle Bill", "John Donaldson (the son)", "John Donaldson (the father)"] — EXCELLENT, disambiguated names ✓✓

**Why 7.5/10:** The "sister" factual error in section 2 prevents a higher score. Otherwise both summaries are comprehensive, well-written, and useful for narrators.

### 2.5 Pronunciation Guide: 7/10 ✗ (stable)

20 entries, 15 with IPA.

**Genuinely useful foreign terms (8):** Caporetto, Piave, Solferino, Guerre, Venetia, Tagliamento, Bersagliari, Bordeaux — excellent ✓

**Acceptable homographs (5):** live, minute, read, close, moderate — context-dependent, genuinely useful ✓

**False positives (7):**
- Common English words: whippersnapper, thriftless, thickset, manliness — uncommon but not pronunciation challenges ✗
- Military/medical terms: dum-dums, orderlies — standard pronunciation ✗
- Archaic contraction: mayn't — borderline ✗

**"was" no longer present** — that false positive was removed ✓

**Why 7/10:** 7/20 entries (35%) are false positives. The core foreign terms and homographs are excellent, but the false positives drag the score down.

### 2.6 HTML Presentation: 8/10 ✓

Navigation works, character profiles render well, voice guidance sections are properly formatted. Disambiguation labels display correctly. Minor issues: possessive alias displayed, "Red Cross" and "Johnny" in Supporting Characters.

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (user-configured, appropriate)
- Pipeline: V2 with Phase 2 graph-based identity resolution
- 0 LLM retries — good
- 1 JSON parse failure in Pronunciation Guide stage
- Character Profiles bottleneck (550s) — not actionable
- No config changes recommended

## Current Issues (Priority Order)

### CRITICAL
(None)

### HIGH

1. **Uncle Bill lost narrator status and protagonist role — REGRESSION** [Identity Resolution]
   - Problem: In attempt 31, Uncle Bill was `is_narrator: true` and `role: protagonist`. Now he's `is_narrator: false` and `role: supporting`. This is incorrect — Uncle Bill narrates the entire story in first person.
   - Evidence: The story opens with "I had not even seen him" and is entirely from Uncle Bill's perspective. He is unambiguously the narrator and protagonist.
   - Location: LLM non-determinism in `src/pipeline/character_extraction_v2/main_cast.py` — the main cast extraction sometimes assigns narrator/protagonist correctly and sometimes doesn't. This needs a deterministic fix.
   - Fix approach: The narrator detection should be strengthened. Since the son ALSO has `is_narrator: true` (correct for nested narration), the pipeline may be only assigning narrator to one character. Uncle Bill should always be detected as narrator given first-person POV.

2. **Alias fix did not take effect** [Alias Grouping]
   - Problem: "John Donaldson's" (possessive) is still an alias of the father. "Johnny" is still a separate supporting character (supporting_6) not merged with the son. The possessive stripping and nickname matching fixes from attempt 32 did not work.
   - Evidence: Father's aliases: ["the father", "the man", "John", "John Donaldson's"]. Johnny: separate character with 0 aliases.
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` (possessive stripping), `src/pipeline/character_extraction_v2/evidence_collectors.py` (nickname matching)
   - Fix approach: Debug why the fixes didn't take effect. The possessive stripping function was added but may not be called in the right code path. The nickname matching may need to happen at a different stage (post-extraction merge rather than during extraction).

3. **Ted Frith profile contaminated with father's quotes** [Profiles]
   - Problem: Ted Frith's evidence quotes include "'this is my good day. I'm American to-day, sir!'" — this is the FATHER's iconic line, not Ted's. Ted Frith is a minor character mentioned in the wartime section.
   - Evidence: The "American, sir" and "American to-day" lines are consistently attributed to John Donaldson (the father) throughout the text. Ted's actual role is more limited.
   - Location: `src/pipeline/character_profiling/` — passage gathering or evidence extraction is assigning passages from the father's scenes to Ted Frith, likely because they appear in the same scenes.
   - Fix approach: The name disambiguator or passage filter needs to correctly attribute these quotes to the father, not Ted.

4. **Summary "sister" hallucination persists** [Summaries]
   - Problem: Section 2 says "his deceased sister's son" — Uncle Bill is the father's COUSIN, not sibling.
   - Evidence: Section 1 correctly says "cousin"
   - Location: LLM generation non-determinism in summary pipeline

### MEDIUM

5. **Son has NO profile data** [Profiles]
   - Problem: John Donaldson (the son) has "Insufficient information for personality analysis", empty relationships, and generic voice guidance. But the text describes him — he enlists in WWI, drives ambulances, earns a Croix de Guerre, and has a pivotal reunion with his father.
   - Location: `src/pipeline/character_profiling/` — likely passage gathering fails for disambiguated names with "(the son)" suffix
   - Evidence: The EVALUATION_STATE.md from attempt 31 noted "No passages found for 'John Donaldson (the son)'" — the passage gatherer can't find text matching this disambiguated name format.

6. **Pronunciation: 7/20 false positives (35%)** [Pronunciation]
   - Remaining false positives: whippersnapper, thriftless, thickset, manliness, dum-dums, orderlies, mayn't
   - These are uncommon-but-real English words, harder to filter generically

7. **Structure: 2 sections for continuous short story** [Structure]
   - Same as all prior attempts. Not worth a targeted fix for this text alone.

8. **"Red Cross" extracted as character** [Completeness]
   - Organization, not a character (supporting_2, 4 mentions). Same as all prior attempts.

### LOW

9. **Section 1 `characters_present` only shows "Narrator"** — should list named characters
10. **Relationship labels imprecise** — Uncle Bill↔father should be "cousin" not "acquaintance"/"mentor"/"ally"
11. **All characters have null physical_description** — text contains some physical descriptions (father described with "physical beauty and charm")

## Fix Priority

**Focus on crossing 8.0 in the most categories:**

The closest categories to threshold:
- **Character Extraction: 7** — needs narrator regression fixed AND alias issues resolved
- **Character Profiles: 7.5** — needs son profile populated, Ted contamination fixed
- **Chapter Summaries: 7.5** — needs "sister" hallucination fixed (LLM-dependent)
- **Pronunciation: 7** — needs false positive reduction
- **Structure: 7** — continuous text detection (persistent, hard to fix generically)

**Recommended fix order:**
1. **Fix Uncle Bill narrator/protagonist regression** (HIGH #1) — this is the most impactful single fix. Must be deterministic, not LLM-dependent.
2. **Debug alias fix** (HIGH #2) — the possessive stripping and Johnny merge were coded but didn't take effect. Need to trace why.
3. **Profile contamination** (HIGH #3) and **son profile** (MEDIUM #5) — may be related to the same passage gathering issue with disambiguated names.

## Fix History

### Attempt 33 — Possessive stripping in supporting cast + deterministic narrator detection
- **Issues targeted:**
  1. HIGH #1 — Uncle Bill narrator/protagonist regression
  2. HIGH #2 — Alias fix from attempt 32 didn't work (possessive + Johnny)
- **Root cause analysis:**
  1. **Possessive:** NER extracts "John Donaldson's" → supporting_3 → gets merged into father's group → canonical name becomes alias. The `_strip_possessive()` in main_cast.py works but doesn't touch supporting cast names.
  2. **Narrator:** Detection is LLM-based. Summaries use "Narrator" (generic) instead of "Uncle Bill", causing non-deterministic matching failures.
- **Changes made:**
  1. Added `_strip_possessive()` method to `supporting.py` (same logic as main_cast.py)
  2. Applied possessive stripping to NER entity names at extraction time (line 117: `name = self._strip_possessive(ent.text.strip())`)
  3. Added deterministic fallback in `narrator.py`: when LLM returns generic "Narrator", `_identify_narrator_by_prominence()` selects based on:
     - Protagonist role (if present)
     - Chapter presence (narrator appears in most/all chapters)
     - Mention count (as tiebreaker)
     - Alias count (final tiebreaker)
- **Expected impact:**
  - Possessive "John Donaldson's" should be stripped before entering identity graph → won't become an alias
  - Uncle Bill should be identified as narrator consistently (appears in both sections, father only in section 2)
  - Johnny still separate (requires identity graph merge logic changes - deferred to future attempt)
- **Files modified:**
  - `src/pipeline/character_extraction_v2/supporting.py` — added `_strip_possessive()` method and applied to NER entity text
  - `src/pipeline/character_extraction_v2/narrator.py` — added `_identify_narrator_by_prominence()` deterministic fallback

### Attempt 32 — Alias cleanup (possessive stripping + nickname matching) — DID NOT WORK
- **Issue targeted:** HIGH #1 from attempt 31 — Alias grouping below threshold (6.5/10)
- **Changes made:**
  1. Added `COMMON_NICKNAMES` entries: `"john": ["jonathan"]`, `"johnny": ["john", "jonathan"]` in `evidence_collectors.py`
  2. Added `_strip_possessive()` helper function to `main_cast.py`
  3. Applied `_strip_possessive()` to all alias assignment locations in `main_cast.py`
- **Result:** NO EFFECT — possessive still present, Johnny still separate character
- **Additional regression:** Uncle Bill lost `is_narrator: true` and `role: protagonist`
- **Score impact:** 7.33 → 7.28 (-0.05) — minor regression overall

### Attempt 31 — Deterministic same-name constraint (SUCCESS!)
- **Issue targeted:** CRITICAL #1 — Father/son merged (regression from attempt 29)
- **Changes made:** Added deterministic check in `evidence_collectors.py`
- **Result:** SUCCESS — Father/son split restored, Uncle Bill promoted to protagonist
- **Score impact:** 6.78 → 7.33 (+0.55)
- **File modified:** `src/pipeline/character_extraction_v2/evidence_collectors.py`

### Attempt 30 — Pronunciation false positive reduction (PARTIAL SUCCESS + REGRESSION)
- Score: 6.78

### Attempt 29 — Disambiguation labels via post-processing (SUCCESS!)
- Score: 7.13

### Attempt 28 — Revert to attempt 25 state
- Score: 6.65

### Previous attempts — see earlier evaluation states

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 32 | Alias cleanup (possessive + nicknames) | `evidence_collectors.py`, `main_cast.py` | NO EFFECT — aliases unchanged, narrator regression |
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
| 32 | 7.28 | +0.68 | Alias fix NO EFFECT, Uncle Bill narrator regression, profiles improved |

## Next Action

**Phase:** awaiting_analysis

Re-run analysis with fixes from attempt 33:
1. Possessive stripping in supporting cast should eliminate "John Donaldson's" as a separate alias
2. Deterministic narrator detection should consistently identify Uncle Bill as narrator
3. Johnny will remain a separate character (identity graph merge logic not modified in this attempt)
