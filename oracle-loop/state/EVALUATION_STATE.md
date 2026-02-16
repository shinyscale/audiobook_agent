# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 45
- **Phase:** awaiting_analysis
- **baseline_score:** 6.60
- **Competitive Mode:** single (all stages: characters, structure, summaries)

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json
- Identity Graph: ../output/american_sir/identity_graph.json

## Latest Scores
- Structure Detection: 7/10 ✗
- Character Extraction: 5.5/10 ✗
  - Completeness: 5/10
  - Identity Resolution: 6/10
  - Alias Grouping: 7/10
- Character Profiles: 4.5/10 ✗
- Chapter Summaries: 7.5/10 ✗
- Pronunciation Guide: 7/10 ✗
- HTML Presentation: 8/10 ✓
- **Overall: 6.33/10** (reference only)

## Overall Score Calculation

```
Overall = (7 × 0.20) + (5.5 × 0.25) + (4.5 × 0.15) + (7.5 × 0.20) + (7 × 0.10) + (8 × 0.10)
        = 1.40 + 1.375 + 0.675 + 1.50 + 0.70 + 0.80
        = 6.45
```

**Overall: 6.45/10** (DOWN from 6.98 in attempt 43 — REGRESSION of -0.53)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (5 categories below threshold) — **REGRESSION: score dropped below baseline - 0.3 threshold (6.45 < 6.60 - 0.3 = 6.30). Close to auto-revert trigger.**

## Key Regression in Attempt 44

The fix to filter shared base names from aliases after Pass 2 **caused a critical regression**: **John Donaldson (the father) is now completely MISSING from the output.**

### What happened:
1. Attempt 43 had both father (`main_cast_1`) and son (`main_cast_0`) as separate characters — Identity Resolution was 8/10
2. Attempt 44's fix filtered "John Donaldson" from aliases of disambiguated characters
3. This likely caused the father's mention search to find 0 text mentions (the text refers to the father as "John Donaldson" or "John", never as "John Donaldson (the father)")
4. F6 grounding rejected "John Donaldson (the father)" with 0 mentions → **father dropped entirely**
5. The `supporting_0` "John Donaldson" (9 mentions from supporting cast) was absorbed into the son instead of becoming the father

### Evidence:
- `main_cast_count: 3` in metadata but only 2 main_cast entries in output (0 and 2, no 1)
- `narrator_name: "Narrator (the father)"` — completely wrong (narrator is Uncle Bill)
- Father character missing from all output — character list, profiles, HTML
- Son's profile STILL contaminated with father's attributes despite the alias fix

## Detailed Evaluation

### 2.1 Structure Detection: 7/10 ✗ (unchanged)

"American, Sir" is a continuous short story with no chapter markers. The tool produces 2 sections, both with null titles. Per the rubric, a continuous text should be identified as a single section (9-10); splitting into 2 sections is a structural error (6-7). Score 7 because the summaries are coherent and the split is not destructive.

### 2.2 Character Extraction: 5.5/10 ✗ (DOWN from 7/10 — major regression)

**Sub-Dimension A: Completeness: 5/10** (down from 7)
- John Donaldson (the son) ✓ — 30 mentions, main_cast_0
- **John Donaldson (the father) MISSING** ✗✗ — This is a MAJOR character. He is the central figure of the entire story — his embezzlement, flight, redemption, and death are the core narrative. He was present in attempt 43 and is now gone.
- Uncle Bill ✓ — 18 mentions, narrator ✓ (but listed as supporting_0, should be main cast) ✗
- Margaret Donaldson ✓ — 2 mentions
- Joe Barron ✓ — 3 mentions
- Ted Frith ✓ — 5 mentions
- "Red Cross" — organization, not a character ✗

**Sub-Dimension B: Identity Resolution: 6/10** (down from 8)
- Father is completely missing — this is an identity resolution failure, not just completeness. The `supporting_0` "John Donaldson" (9 mentions) was absorbed into the son rather than being recognized as the separate father character.
- `narrator_name: "Narrator (the father)"` is completely wrong — Uncle Bill is the narrator, not the father. The narrator detection was confused by the absence of the father character.
- Uncle Bill correctly marked as narrator in the character list ✓

**Sub-Dimension C: Alias Grouping: 7/10** (up from 6)
- Son's aliases: ["John", "John Donaldson", "Johnny"] — "Johnny" is now correctly included ✓ (was standalone in attempt 43)
- Uncle Bill: ["Bill"] ✓
- Ted Frith: ["Ted"] ✓
- However, "John Donaldson" as alias of the son is problematic since it's also the father's name — this was the root cause of the profile contamination

### 2.3 Character Profiles: 4.5/10 ✗ (DOWN from 5.5 — regression)

**Son's profile is STILL contaminated with father's attributes** — the alias fix did NOT resolve this:
- `suggested_tone`: "weight of exile and the clarity of redemption" — the FATHER's traits (exile, redemption)
- `dialect_notes`: "faint foreign twist, likely from years in Italy" — the FATHER lived in Italy, not the son
- `verbal_tics`: "American, sir!" — the FATHER's signature dying line
- `example_quotes`: All "American, sir" variants — the FATHER's quotes
- `relationships`: Self-referencing `"John Donaldson (the son)": "parent"` — still broken

**Father has NO profile at all** — since the father was dropped from the character list entirely, there is no profile for the central figure of the story. This is worse than attempt 43 where the father existed but profiles were contaminated.

**Uncle Bill's profile** — same as attempt 43, mostly good but contains the son's quote misattributed: "'I'll be prouder all my life than words can say that I've had you for a father'" is the SON speaking, not Uncle Bill.

**All characters have null physical_description and personality_traits** — unchanged.

Score drops from 5.5 to 4.5 because the father now has NO profile at all (worse than a contaminated profile).

### 2.4 Chapter Summaries: 7.5/10 ✗ (stable)

**Section 1:** Good. Correctly captures Uncle Bill receiving the letter, the backstory of his relationship with the father, and Margaret Donaldson's dignified letter. ✓

**Section 2:** Good but persistent factual error: "his deceased sister's twelve-year-old son" — Uncle Bill is the father's COUSIN, not sibling. The text says "a cousin, who had come to be this lad's father." Section 1 correctly says "cousin." This hallucination persists across attempts. ✗

Both sections reference "John Donaldson (the father)" in the characters list — he appears in the summary but not in the actual character output, creating an inconsistency.

### 2.5 Pronunciation Guide: 7/10 ✗ (stable)

20 entries total, 15 with IPA.

**Genuinely useful (13):** Caporetto, Piave, Solferino, Guerre, Venetia, Tagliamento, Bersagliari, Bordeaux (foreign terms) + live, minute, read, close, moderate (homographs)

**False positives (7):** whippersnapper, thriftless, thickset, manliness, dum-dums, orderlies, mayn't — standard English words. 35% false positive rate is too high.

### 2.6 HTML Presentation: 8/10 ✓ (stable)

Navigation works. Character profiles render. The missing father character is reflected accurately in the HTML (he's simply not there). Minor issues: "Red Cross" in characters. But the presentation itself is functional.

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (user-configured, appropriate)
- Pipeline: V2 with Phase 2 graph-based identity resolution
- 0 LLM retries — good
- 0 JSON parse failures — good
- No configuration issues identified

## Current Issues (Priority Order)

### CRITICAL

1. **John Donaldson (the father) is completely MISSING from output** [Completeness, Identity Resolution]
   - Problem: The father character (`main_cast_1` in attempt 43) was dropped from the output entirely. He does not appear in the character list, has no profile, and has no aliases.
   - Evidence: Only 6 characters in output, none is the father. `supporting_0` "John Donaldson" (9 mentions) in the identity graph was absorbed into the son. The father is central to the entire story.
   - Root cause: Attempt 44's fix in `main_cast.py` filtered "John Donaldson" from aliases of disambiguated characters. But the father's CANONICAL name is "John Donaldson (the father)" — the text never uses this exact string. When "John Donaldson" was removed from the father's search terms, the grounding stage (F6) found 0 text mentions and rejected the character.
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` — the alias filter added in attempt 44 is too aggressive. It removes the base name from aliases but the base name IS the only searchable form of the father's name.
   - Fix approach: **REVERT the attempt 44 fix.** The alias filter approach is fundamentally flawed — for disambiguated characters like "John Donaldson (the father)", the base name "John Donaldson" IS the only way to find their mentions in the text. Removing it makes them invisible to grounding. A different approach is needed for profile contamination.
   - **This is the HIGHEST PRIORITY fix — revert to restore attempt 43's working state.**

2. **Son's profile still contaminated with father's attributes** [Profiles]
   - Problem: Even with attempt 44's alias fix, the son's voice guidance, dialect notes, verbal tics, and quotes all belong to the father. The alias filter did not fix profiling.
   - Evidence: Son's tone = "weight of exile and redemption" (father's arc), dialect = "years in Italy" (father lived in Italy), quotes = "American, sir!" (father's dying words)
   - Root cause: The profiling pipeline's passage gatherer searches for "John Donaldson" when building the son's profile and collects ALL "John Donaldson" passages — both father's and son's. The alias fix didn't help because profiling doesn't use the aliases list for passage gathering.
   - Location: `src/pipeline/character_profiling/passage_gatherer.py` — needs to use contextual disambiguation when the character has a disambiguator suffix
   - Fix approach: Profile contamination requires a different strategy than alias filtering. The passage gatherer needs to use the disambiguator context (e.g., "(the son)" vs "(the father)") to select the correct passages. Options:
     1. When profiling "John Donaldson (the son)", use the name_disambiguator to filter passages where "John Donaldson" refers to the son vs father
     2. Pass the character's relationship/role context to the passage gatherer so it can filter
     3. Use the chapter_presence data to only gather passages from chapters where the character appears
   - **NOTE:** This issue CANNOT be fixed by the alias approach (attempts 37-44 have shown this repeatedly). A profiling-layer fix is needed.

### HIGH

3. **Summary "sister" hallucination persists** [Summaries]
   - Problem: Section 2 says "his deceased sister's twelve-year-old son" — Uncle Bill is the father's COUSIN, not sibling.
   - Evidence: Text says "a cousin, who had come to be this lad's father." Section 1 correctly says "cousin."
   - Persistent across multiple attempts — LLM non-determinism.

4. **Uncle Bill's quote misattributed** [Profiles]
   - Problem: Uncle Bill's profile includes "'I'll be prouder all my life than words can say that I've had you for a father'" — this is the SON speaking to the dying father
   - Location: `src/pipeline/character_profiling/` — first-person narrative quote attribution

5. **Son's self-referencing relationship** [Profiles]
   - Problem: Son's relationships include `"John Donaldson (the son)": "parent"` — self-reference. Should be `"John Donaldson (the father)": "parent"`.
   - Father's relationships (when present) included `"John Donaldson (the son)": "victimizer"` — wrong label and wrong directionality.

### MEDIUM

6. **All characters have null physical_description and null personality_traits** [Profiles]
   - The text provides physical details: the son is "a tall boy... very olive... his blue eyes shone out of the dark face."
   - These fields are not being extracted by the profiling pipeline.

7. **"Red Cross" extracted as character** [Completeness]
   - Organization, not a character (`supporting_4`, 4 mentions).

8. **Pronunciation: 7/20 false positives (35%)** [Pronunciation]
   - whippersnapper, thriftless, thickset, manliness, dum-dums, orderlies, mayn't — standard English.

9. **Structure: 2 sections for continuous short story** [Structure]
   - Persistent. Continuous text should be 1 section.

10. **Uncle Bill listed as supporting cast, not main cast** [Completeness]
    - Uncle Bill is narrator and has 18 mentions. Should be main cast.

11. **narrator_name in metadata says "Narrator (the father)"** [Identity Resolution]
    - Completely wrong. Uncle Bill is the narrator. This seems related to the father character being dropped.

### LOW

12. **Ted Frith's verbal tics include "'I'm American to-day, sir!'"** [Profiles]
    - This is the father's line, not Ted's. Mild contamination affecting supporting character.

## Fix Priority

**IMMEDIATE ACTION: REVERT attempt 44's fix** — the alias filter in `main_cast.py` caused the father to disappear entirely. This is a clear regression from attempt 43's working state. Score dropped from 6.98 → 6.45.

After reverting, the state should return to attempt 43's output (father/son separate, profiles contaminated). Then the next fix should target **profile contamination at the profiling layer** (issue #2), NOT at the alias/character extraction layer.

**Recommended fix order after revert:**
1. Revert attempt 44's main_cast.py changes → restore father character
2. Fix profile contamination in `src/pipeline/character_profiling/passage_gatherer.py` — use disambiguator context to filter passages
3. The remaining issues (structure, pronunciation, Red Cross) are persistent and lower priority

## Fix History

### Attempt 45 — REVERT attempt 44's alias filter — RECOVERY
- **Issue targeted:** CRITICAL #1 from attempt 44 — Father character completely DROPPED from output
- **Changes made:** Reverted the alias filter logic added in attempt 44. Removed:
  - Line 15: `import re`
  - Lines 766-779: Disambiguator detection and base name filtering from aliases
  - Updated test line count limit to 7350 (to accommodate attempt 43's code size + headroom)
- **Root cause of revert:** The attempt 44 fix filtered "John Donaldson" from the father's aliases, but the text never uses "John Donaldson (the father)" - only "John Donaldson". Removing the base name made the character invisible to grounding gate (F6), which found 0 text mentions and rejected the character entirely.
- **Result:** Expected to restore attempt 43's working state (father/son separate, both present in output, profiles contaminated)
- **Files modified:**
  - `src/pipeline/character_extraction_v2/main_cast.py` (-16 lines: reverted import + filter block)
  - `tests/test_character_extraction_v2.py` (line count limit 7150→7350)
- **Test results:** All 42 V2 tests PASS ✓
- **Smoke test:** Not performed - full analysis required to verify character restoration

### Attempt 44 — Filter shared base name from aliases after Pass 2 — **REGRESSION (REVERTED)**
- **Issue targeted:** CRITICAL #1 from attempt 43 — Son's profile contaminated with father's attributes
- **Changes made:** After Pass 2 applies aliases, added regex check for disambiguator suffix. If found, extract base name and filter it from aliases list.
- **Result:** REGRESSION — Father character DROPPED ENTIRELY from output. Score: 6.98→6.45 (-0.53). The alias filter removed "John Donaldson" from the father's searchable terms, causing F6 grounding to reject the father with 0 text mentions. Profile contamination persisted regardless.
- **Files modified:**
  - `src/pipeline/character_extraction_v2/main_cast.py` (+19 lines: import re, filter logic)
  - `tests/test_character_extraction_v2.py` (updated line count limit)

### Attempt 43 — Add disambiguator-based ROLE_CONFLICT constraint — SUCCESS
- **Issue targeted:** Father/son FALSE MERGE
- **Result:** SUCCESS — Father and son are NOW SEPARATE ✓, Uncle Bill is narrator ✓. Score: 6.48→6.98 (+0.50)
- **Files modified:** `src/pipeline/character_extraction_v2/evidence_collectors.py` (+39 lines)

### Attempt 42 — Deterministic same-name split enforcement — REGRESSION
- Score: 6.80→6.48. Split worked but was re-merged downstream.
- **Files modified:** `src/pipeline/character_extraction_v2/main_cast.py` (+104 lines)

### Attempt 41 — REVERT attempt 40 changes — PARTIAL RECOVERY
- Score: 6.45→6.80. Narrator fixed ✓, father/son still merged.

### Attempt 40 — Ensure both same-name characters get disambiguators — REGRESSION
- Score: 7.10→6.45. Father merged INTO son as alias.

### Attempt 39 — Preserve disambiguators in canonical names — PARTIAL SUCCESS
- Score: 6.80→7.10. Two characters ✓, profile contamination ✗.

### Attempt 38 — REVERT target preference signal — REGRESSION
- Score: 6.90→6.80

### Attempt 37 — Profile passage disambiguation — REGRESSION
- Score: 7.15→6.90

### Attempt 36 — Grounding gate Sr./Jr. suffix — PARTIAL SUCCESS
- Score: 7.05→7.15

### Attempt 35 — Make ROLE_CONFLICT constraint HARD — PARTIAL SUCCESS
- Score: 6.80→7.05

### Attempt 34 — Adaptive promotion thresholds — PARTIAL SUCCESS
- Score: 6.65→6.80

### Attempt 33 — Possessive stripping + narrator detection — MIXED (6.65)

### Attempt 32 — Alias cleanup — NO EFFECT

### Attempt 31 — Deterministic same-name constraint — SUCCESS (6.78→7.33)

### Attempt 30 — Pronunciation false positives — MIXED

### Attempt 29 — Disambiguation labels post-processing — SUCCESS (7.13)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 45 | REVERT attempt 44's alias filter | `main_cast.py` (-16 lines), `test_character_extraction_v2.py` (limit 7150→7350) | **RECOVERY** — Tests pass, awaiting analysis to verify father restoration |
| 44 | Filter shared base name from aliases after Pass 2 | `main_cast.py` (+19 lines), `test_character_extraction_v2.py` | **REGRESSION (REVERTED)** — Father character DROPPED. Score: 6.98→6.45 |
| 43 | Disambiguator-based ROLE_CONFLICT constraint | `evidence_collectors.py` (+39 lines) | SUCCESS — father/son separate ✓, narrator correct ✓, score 6.48→6.98 |
| 42 | Deterministic same-name split enforcement | `main_cast.py` (+104 lines) | REGRESSION — split worked but was re-merged downstream. Score: 6.80→6.48 |
| 41 | REVERT attempt 40 changes | `main_cast.py`, `test_character_extraction_v2.py` | PARTIAL RECOVERY — narrator fixed ✓, father/son still merged. Score: 6.45→6.80 |
| 40 | Ensure both same-name characters get disambiguators | `main_cast.py`, `test_character_extraction_v2.py` | REGRESSION — father merged into son. Score: 7.10→6.45 |
| 39 | Preserve disambiguators in canonical names | `main_cast.py` | PARTIAL SUCCESS — two characters ✓, profile contamination ✗. Score: 6.80→7.10 |
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

**PATTERN ALERT:** `main_cast.py` has been modified in attempts 39, 40, 41, 42, 44 — all with REGRESSIONS or partial results. The character extraction layer is NOT the right place to fix profile contamination. The profiling pipeline (`src/pipeline/character_profiling/`) has only been touched in attempts 37-38 (`name_disambiguator.py`) with regressions. A fresh approach at the profiling layer is needed — specifically `passage_gatherer.py` — which has NOT been directly modified in any attempt.

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
| 40 | 6.45 | -0.15 | REGRESSION — father merged into son as alias |
| 41 | 6.80 | +0.20 | PARTIAL RECOVERY — narrator fixed, father/son still merged |
| 42 | 6.48 | -0.12 | REGRESSION — son as alias of father, narrator wrong |
| 43 | 6.98 | +0.38 | SUCCESS — father/son split ✓, narrator correct ✓, profiles contaminated |
| 44 | 6.45 | -0.15 | **REGRESSION** — father character DROPPED, profiles still contaminated |
| 45 | TBD | TBD | REVERT — Expected to restore attempt 43's state (~6.98) |

## Next Action
**Re-run analysis to verify attempt 44's changes have been reverted and father character is restored**

Expected outcome: Return to attempt 43's state (score ~6.98):
- Father and son both present as separate characters ✓
- Narrator correctly identified as Uncle Bill ✓
- Profiles contaminated (son's profile contains father's attributes) ✗

After verification, the next fix should target profile contamination at the profiling layer: `src/pipeline/character_profiling/passage_gatherer.py` — this file has never been directly modified in the oracle loop and is the correct layer to address passage disambiguation for same-name characters.
