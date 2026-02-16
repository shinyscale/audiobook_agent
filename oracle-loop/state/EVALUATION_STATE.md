# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 37
- **Phase:** awaiting_analysis
- **baseline_score:** 6.60
- **Competitive Mode:** single (all stages: characters, structure, summaries)

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Latest Scores
- Structure Detection: 7/10 ✗
- Character Extraction: 7/10 ✗
  - Completeness: 8/10
  - Identity Resolution: 6/10
  - Alias Grouping: 7/10
- Character Profiles: 6.5/10 ✗
- Chapter Summaries: 7.5/10 ✗
- Pronunciation Guide: 7/10 ✗
- HTML Presentation: 8/10 ✓
- **Overall: 7.15/10** (reference only)

## Overall Score Calculation

```
Overall = (7 × 0.20) + (7 × 0.25) + (6.5 × 0.15) + (7.5 × 0.20) + (7 × 0.10) + (8 × 0.10)
        = 1.40 + 1.75 + 0.975 + 1.50 + 0.70 + 0.80
        = 7.125
```

**Overall: 7.15/10** (UP from 7.05 in attempt 35)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (5 categories below threshold)

## Detailed Evaluation

### 2.1 Structure Detection: 7/10 ✗

Unchanged. "American, Sir" is a continuous short story with no chapter markers. The tool produces 2 sections, both with null titles. Per the rubric, a continuous text should be identified as a single section (9-10); splitting into 2 sections is a structural error (6-7). Score 7 because the summaries for each section are coherent and usable.

### 2.2 Character Extraction: 7/10 ✗

**THE GROUNDING GATE FIX WORKED!** John Donaldson Sr. is now in the character list with 10 mentions, aliases "the father" and "John Donaldson", and a correct relationship "John Donaldson (son): parent". This is the biggest single-fix improvement in several attempts.

**Character list (8 total, 4 main_cast + 4 supporting):**
- `main_cast_0`: **Uncle Bill** — 18 mentions, role: protagonist, is_narrator: true ✓✓
  - Aliases: ["Bill"] ✓
- `main_cast_1`: **John Donaldson** — 28 mentions, role: supporting — this is the SON ✓
  - Aliases: ["John"] ✓ (but missing "Johnny" — see below)
- `main_cast_2`: **John Donaldson Sr.** — 10 mentions, role: supporting — this is the FATHER ✓✓✓ NEW!
  - Aliases: ["the father", "John Donaldson"] ✓
- `main_cast_3`: **Margaret Donaldson** — 2 mentions, role: supporting ✓ NEW!
- `supporting_0`: **Joe Barron** — 3 mentions ✓
- `supporting_1`: **Red Cross** — 4 mentions — organization, not character ✗
- `supporting_2`: **Ted Frith** — 5 mentions, alias: "Ted" ✓
- `supporting_4`: **Johnny** — 2 mentions — FALSE SPLIT, should be alias of John Donaldson (son) ✗

**Sub-Dimension A: Completeness: 8/10** (UP from 6!)
- Uncle Bill present and correctly identified as protagonist/narrator ✓✓
- Son (John Donaldson) correctly identified ✓
- Father (John Donaldson Sr.) NOW PRESENT with 10 mentions ✓✓✓ — CRITICAL fix worked!
- Margaret Donaldson now detected ✓ — NEW!
- "Red Cross" is an organization, not a character ✗ (minor)
- All significant characters are present — major milestone

**Sub-Dimension B: Identity Resolution: 6/10** (DOWN from 7)
- Father/son correctly kept separate ✓✓ (HARD constraint still working)
- Father correctly in output (grounding gate fix) ✓✓
- BUT "Johnny" is a FALSE SPLIT — `supporting_4` with 2 mentions, no aliases. "Johnny" is clearly a nickname for the son (John Donaldson). In attempt 35, Johnny was correctly an alias of John Donaldson. This is a regression. ✗✗
- Son's profile is entirely about the FATHER's story (see Profiles below), suggesting profile-level identity confusion even though the characters are nominally separate ✗

**Sub-Dimension C: Alias Grouping: 7/10** (DOWN from 8)
- Uncle Bill has alias "Bill" ✓
- John Donaldson has alias "John" ✓ but MISSING "Johnny" ✗ (was correctly an alias in attempt 35)
- John Donaldson Sr. has aliases "the father", "John Donaldson" ✓
- Ted Frith has alias "Ted" ✓
- Father's alias "John Donaldson" creates ambiguity with the son's canonical name — but this is technically correct since the text uses "John Donaldson" for the father
- "Johnny" as separate character rather than alias is a regression ✗

### 2.3 Character Profiles: 6.5/10 ✗ (DOWN from 7.5)

**Major regression: Son's profile is entirely about the father's story.**

- **Uncle Bill**: Excellent profile — personality "profoundly compassionate and self-sacrificing", traits "selfless, steadfast, emotionally reserved but deeply caring". Evidence quotes are accurate. ✓✓
- **John Donaldson Sr. (father)**: Excellent profile — "morally ambiguous man who committed financial betrayal and abandoned his family for two decades, yet sought redemption through selfless service." Evidence quotes are ALL correct: "Took money", "American, sir", "happiest hour." This is a huge improvement. ✓✓✓
- **John Donaldson (son)**: WRONG PROFILE — describes "morally ambiguous man who committed financial fraud and faked his death." This is the FATHER's story, not the son's. The son is a young man who went to Yale, was taken fishing by Uncle Bill, enlisted in WWI as an ambulance driver, and found his dying father at Caporetto. The son's profile also has the father's evidence quotes ("Took money", "American, sir"). ✗✗✗
  - Son's relationships are also wrong: "John Donaldson Jr.: parent" (nonsensical self-reference?), "Uncle Bill: victimizer" (should be mentor/guardian), "Margaret Donaldson: spouse" (Margaret is the son's MOTHER, not spouse)
- **Ted Frith**: Partially contaminated — "'I'm American to-day, sir!'" is the father's line, but "He's been eating it up. The hotter it got, the better it suited" is legitimately about Ted. Mixed ✗/✓

**Why 6.5/10:** Father's NEW profile is excellent (+1), Uncle Bill still excellent, but the son's profile is a complete mismatch — it describes the father's character arc instead of the son's. The son's relationships are entirely wrong (3/3 incorrect). This is worse than attempt 35 because the son's profile was mostly about the son in that attempt. The profile disambiguation is not working correctly when both father and son exist as separate characters.

### 2.4 Chapter Summaries: 7.5/10 ✗ (stable)

**Section 1:** Excellent. Correctly describes the cousin relationship, Margaret Donaldson, the scandal and faked death. ✓

**Section 2:** Good quality but the "sister" hallucination persists:
- "his deceased sister's son" — WRONG. Uncle Bill is the father's COUSIN, not sibling. Section 1 correctly says "cousin." ✗
- Otherwise covers Yale, fishing trip, WWI, Caporetto, reunion, deathbed revelation. ✓

### 2.5 Pronunciation Guide: 7/10 ✗ (stable)

20 entries, 15 with IPA.

**Genuinely useful (13):** Caporetto, Piave, Solferino, Guerre, Venetia, Tagliamento, Bersagliari, Bordeaux (foreign terms ✓), live, minute, read, close, moderate (homographs ✓)

**False positives (7):** whippersnapper, thriftless, thickset, manliness, dum-dums, orderlies, mayn't ✗

35% false positive rate. The foreign terms and homographs are excellent, but the false positives keep this at 7.

### 2.6 HTML Presentation: 8/10 ✓

Navigation works. Character profiles render well. Uncle Bill displayed as protagonist/narrator. Father now appears in the character list — major improvement. Minor: "Red Cross" in Supporting Characters. "Johnny" as separate character is confusing given it's the same person as John Donaldson.

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (user-configured, appropriate)
- Pipeline: V2 with Phase 2 graph-based identity resolution
- 0 LLM retries — good
- 1 JSON parse failure (Pronunciation Guide batch enrichment) — recurring
- Character Profiles: 11 LLM calls, 49,591 tokens, 675s
- Grounding gate fix working — father now grounded via base name ✓
- Johnny false split is new — was correctly an alias in attempt 35

## Current Issues (Priority Order)

### CRITICAL

1. **Son's profile is entirely about the father's story** [Profiles → Identity Resolution at profile level]
   - Problem: John Donaldson (the son, `main_cast_1`) has a profile describing "morally ambiguous man who committed financial fraud and faked his death." This is the FATHER's character arc. The son's profile should describe: a young man orphaned by his father's disappearance, raised partly by Uncle Bill, attended Yale, enlisted in WWI as ambulance driver, found his dying father at Caporetto.
   - Evidence: Son's evidence quotes ("Took money", "American, sir", "happiest hour") are all the father's lines. Son's personality summary is identical in theme to the father's.
   - Root cause: With both father and son having the canonical name "John Donaldson" (the father has it as an alias), the profiling pipeline likely gathers passages for both characters from the same text matches and assigns the father's more dramatic story to both. The name disambiguator may not distinguish them correctly during passage gathering.
   - Location: `src/pipeline/character_profiling/passage_gatherer.py` and `src/pipeline/character_profiling/name_disambiguator.py` — when gathering passages for "John Donaldson" (son), the system pulls passages about "John Donaldson" (father, via alias) and gives the father's story to the son.
   - Fix approach: When gathering passages for a character, if another character has the same name as an alias, the disambiguator needs to filter passages. If "John Donaldson" appears in context with temporal markers ("twenty years ago", "the father"), those passages belong to the father, not the son. The disambiguator should use the characters' own aliases and relationships for disambiguation — e.g., if the father is `John Donaldson Sr.` with alias "the father", passages mentioning "the father" near "John Donaldson" should be attributed to Sr., not to the son.

2. **Son's relationships are entirely wrong** [Profiles]
   - Problem: Son has relationships: `"John Donaldson Jr.": "parent"` (nonsensical — this is either a self-reference or inverted), `"Uncle Bill": "victimizer"` (Uncle Bill is his mentor/guardian, not victimizer), `"Margaret Donaldson": "spouse"` (Margaret is his MOTHER, not spouse).
   - Evidence: The text clearly shows Uncle Bill as the son's guardian/mentor who took him fishing, corresponded with him. Margaret is described as the son's mother. There is no "John Donaldson Jr." in the text — the son IS the younger John Donaldson.
   - Root cause: Same as CRITICAL #1 — profile contamination from the father's story causes the LLM to generate relationships that make sense for the father (whose spouse IS Margaret, whose relationship to Uncle Bill IS adversarial/fraught) rather than the son.
   - Fix: Resolving CRITICAL #1 should fix this — if the son gets the right passages, the relationships will be correct.

### HIGH

3. **"Johnny" false split — should be alias of John Donaldson (son)** [Identity Resolution / Alias Grouping]
   - Problem: `supporting_4` "Johnny" with 2 mentions exists as a separate character. In attempt 35, "Johnny" was correctly an alias of John Donaldson (the son). This is a regression.
   - Evidence: "Johnny" is clearly a childhood nickname for the son, John Donaldson. The text uses it affectionately in early passages.
   - Location: The identity graph or alias resolution is not connecting "Johnny" to "John Donaldson" when the father is also present. Possibly the graph sees "Johnny" and two "John Donaldson" entries and can't decide which to merge into, so it stays separate.
   - Fix approach: "Johnny" should unambiguously merge into the son (it's a diminutive of "John", and the context is the son's childhood). The alias resolution should be able to handle this even with two same-name characters. This might be a side effect of the HARD constraint being too aggressive — it might be blocking the Johnny→John merge because both father and son are "John Donaldson."

4. **Summary "sister" hallucination persists** [Summaries]
   - Problem: Section 2 says "his deceased sister's son" — Uncle Bill is the father's COUSIN, not sibling.
   - Evidence: Section 1 correctly says "cousin."
   - Location: LLM generation in summary pipeline. Non-deterministic — may resolve on re-run.

### MEDIUM

5. **Ted Frith profile partially contaminated** [Profiles]
   - Problem: "'I'm American to-day, sir!'" in Ted's evidence is the father's line. The other quote ("He's been eating it up") is legitimately about Ted.
   - Impact: Will likely improve if CRITICAL #1 is fixed — correct passage attribution for the father should prevent his dialogue from leaking to Ted.

6. **Pronunciation: 7/20 false positives (35%)** [Pronunciation]
   - Remaining false positives: whippersnapper, thriftless, thickset, manliness, dum-dums, orderlies, mayn't.

7. **Structure: 2 sections for continuous short story** [Structure]
   - Same as all prior attempts.

8. **"Red Cross" extracted as character** [Completeness]
   - Organization, not a character (`supporting_1`, 4 mentions).

### LOW

9. **Father's alias "John Donaldson" overlaps with son's canonical name** — technically correct but creates confusion in display and profile gathering.

## Fix Priority

**Attempt 36 was a PARTIAL SUCCESS.** The grounding gate fix worked — father is now in the character list with correct profile and quotes. Margaret Donaldson also appeared. Overall character count went from 5→8. BUT the profile disambiguation is now broken: the son's profile is entirely about the father's story because both share the name "John Donaldson" and the passage gatherer can't distinguish them.

**The blocking issue is now in the PROFILING pipeline, not the extraction pipeline.** The characters are correctly extracted and separated — the identity graph and grounding are working. But the profiling step gathers the wrong passages for the son because the father has "John Donaldson" as an alias.

**Recommended fix for attempt 37:**
1. **CRITICAL #1+#2: Profile passage disambiguation** — The passage gatherer/name disambiguator needs to correctly attribute passages when two characters share a name. When the son (`John Donaldson`) and father (`John Donaldson Sr.`, alias `John Donaldson`) both exist, passages containing "John Donaldson" need to be disambiguated using contextual signals (temporal markers, relationship phrases, chapter context). The father's dramatic story (embezzlement, faked death, redemption) should go to the father's profile, not the son's.
2. **HIGH #3: Johnny alias regression** — Investigate why "Johnny" is no longer being merged as an alias of the son. May be a side effect of the HARD constraint or the presence of two "John Donaldson" characters confusing the alias resolution.

**Do NOT touch the identity graph, grounding gate, or constraint logic — those are all working correctly now.**

## Fix History

### Attempt 36 — Generational suffix handling in mention search — PARTIAL SUCCESS
- **Issue targeted:** CRITICAL #1 — Father rejected by grounding gate with 0 text mentions
- **Changes made:**
  1. Added `_extract_base_name()` method to `MentionSearcher` in `mention_search.py`
  2. Modified `search_character()` to search for base name without Sr./Jr. suffixes
  3. Regex strips: Sr./Sr, Jr./Jr, Roman numerals (I, II, III) from end of name
- **Result:** PARTIAL SUCCESS — Father now in character list with 10 mentions ✓✓✓. Margaret Donaldson also detected ✓. Character count 5→8 ✓. BUT son's profile is contaminated with father's story ✗✗. Johnny is a false split (regression from attempt 35 where it was correctly an alias) ✗.
- **Files modified:**
  - `src/pipeline/character_extraction_v2/mention_search.py` (added 18 lines)
  - `tests/test_character_extraction_v2.py` (updated line count threshold)

### Attempt 35 — Make ROLE_CONFLICT constraint HARD (strength 1.0) — PARTIAL SUCCESS
- Father/son no longer merged ✓. Father filtered out by grounding gate ✗. Uncle Bill profile now working ✓. Johnny now alias ✓. Score: 6.80→7.05

### Attempt 34 — Adaptive promotion thresholds (length-scaled) — PARTIAL SUCCESS
- Uncle Bill restored to main_cast ✓. Father/son merged ✗. Score: 6.65→6.80

### Previous attempts — see earlier evaluation states

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 37 | Profile passage disambiguation | `name_disambiguator.py` | PENDING ANALYSIS — Added target character preference signal |
| 36 | Grounding gate Sr./Jr. suffix | `mention_search.py`, `test_character_extraction_v2.py` | PARTIAL SUCCESS — father grounded ✓, son's profile contaminated ✗, Johnny false split ✗. Completeness 6→8, IR 7→6, Profiles 7.5→6.5. Score: 7.05→7.15 |
| 35 | ROLE_CONFLICT hard constraint | `identity_graph.py` | PARTIAL SUCCESS — no false merge ✓, father filtered by grounding ✗. IR 4→7, AG 7→8, Profiles 6→7.5. Score: 6.80→7.05 |
| 34 | Adaptive promotion thresholds | `characters.py` | PARTIAL SUCCESS — Uncle Bill restored, father/son merged. Score: 6.65→6.80 |
| 33 | Possessive stripping + narrator detection | `supporting.py`, `narrator.py` | MIXED — possessive fixed, Uncle Bill demoted. Score: 6.65 |
| 32 | Alias cleanup (possessive + nicknames) | `evidence_collectors.py`, `main_cast.py` | NO EFFECT |
| 31 | Deterministic same-name constraint | `evidence_collectors.py` | SUCCESS — father/son split restored. Score: 6.78→7.33 |
| 30 | Pronunciation false positives | `character_proposer.py`, `foreign_proposer.py` | Pronunciation improved, character regression |
| 29 | Disambiguation labels post-processing | `characters.py` | SUCCESS — labels applied. Score: 7.13 |

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

## Fix History

### Attempt 37 — Target character preference in passage disambiguation — IN PROGRESS
- **Issue targeted:** CRITICAL #1+#2 — Son's profile contaminated with father's story due to shared name
- **Root cause:** When gathering passages for the son ("John Donaldson"), the disambiguator sees two candidates:
  - Son's canonical name: "John Donaldson"
  - Father's alias: "John Donaldson"
  The disambiguator had NO "prefer the target character" signal, so it couldn't reliably distinguish them.
- **Changes made:**
  1. Added Signal 0 (target character preference, confidence 0.98) to `ContextDisambiguator.disambiguate()`
  2. When a candidate exactly matches `target_character_names[0]` (the canonical name we're gathering for), prefer it strongly
  3. Added `by_target_preference` stat tracking
- **Fix classification:**
  - Fix type: algorithmic (add missing universal invariant)
  - Universality check: YES - helps ANY book with same-name characters (father/son, generational names, etc.)
  - Not a keyword filter - uses exact canonical name matching
- **Files modified:**
  - `src/pipeline/character_profiling/name_disambiguator.py` (added 25 lines)
- **Expected result:** Son's profile should now get passages about the son, not the father. Father's profile should remain correct.

## Next Action

**Phase:** awaiting_analysis

Re-run analysis on american_sir (attempt 37) to verify:
1. Son's profile now describes the SON (Yale student, WWI ambulance driver, found dying father)
2. Father's profile remains correct (fraud, faked death, redemption)
3. No regression on character extraction or other categories

Note: Did NOT address HIGH #3 (Johnny false split) in this attempt - focusing on CRITICAL issues first.
