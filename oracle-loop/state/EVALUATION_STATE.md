# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 52
- **Phase:** awaiting_fix
- **baseline_score:** 6.60
- **Competitive Mode:** single (all stages: characters, structure, summaries)

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Latest Scores
- Structure Detection: 7/10 ✗
- Character Extraction: 5.5/10 ✗
  - Completeness: 7/10
  - Identity Resolution: 5/10
  - Alias Grouping: 5/10
- Character Profiles: 4/10 ✗
- Chapter Summaries: 7.5/10 ✗
- Pronunciation Guide: 7/10 ✗
- HTML Presentation: 8/10 ✓
- **Overall: 6.33/10** (reference only)

## Overall Score Calculation

```
Overall = (7 × 0.20) + (5.5 × 0.25) + (4 × 0.15) + (7.5 × 0.20) + (7 × 0.10) + (8 × 0.10)
        = 1.40 + 1.375 + 0.60 + 1.50 + 0.70 + 0.80
        = 6.375
```

**Overall: 6.33/10** (reference only — narrator misidentification + profiles remain the key blockers)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (5 categories below threshold)

## Detailed Evaluation

### 2.1 Structure Detection: 7/10 ✗ (unchanged)

"American, Sir" is a continuous short story with no chapter markers. The tool produces 2 sections, both with null titles. Per rubric, continuous text should be 1 section (9-10); splitting into 2 is a structural error. Score 7 because summaries are coherent and the split is not destructive.

### 2.2 Character Extraction: 5.5/10 ✗ (UP from 4.5 — dedup fix worked)

**Sub-Dimension A: Completeness: 7/10** (UP from 6)

7 characters extracted. The dedup fix successfully merged the two duplicate "John Donaldson (the father)" entries from attempt 51, AND the "John (the cousin)" entry is gone — absorbed into the father. This is a significant improvement:
- ✓ main_cast_1: John Donaldson (the son) — 28 mentions
- ✓ main_cast_2: John Donaldson (the father) — 10 mentions (was TRIPLED, now SINGLE ✓✓)
- ✓ main_cast_3: Uncle Bill — 18 mentions
- ✓ supporting_0: Joe Barron — 3 mentions
- ✗ supporting_1: Red Cross — 4 mentions — organization, not a character
- ✓ supporting_2: Ted Frith — 5 mentions
- ✗ supporting_4: Johnny — 2 mentions — should be alias of the son

**MISSING:** Margaret Donaldson (the father's wife who writes Uncle Bill a letter). Still absent since attempt 51.

**Real characters:** Uncle Bill, John Donaldson (father), John Donaldson (son), Margaret Donaldson, Joe Barron, Ted Frith = 6 characters. Tool has 5 unique real characters (missing Margaret, has Red Cross org + separate Johnny).

**Sub-Dimension B: Identity Resolution: 5/10** (UP from 3 — father dedup SUCCESS)

- ✓ Father is now a SINGLE entry (was tripled in attempt 51) — MAJOR FIX ✓✓
- ✓ Uncle Bill is a single entity ✓
- ✓ Father and son correctly separated ✓
- ✗ **NARRATOR REGRESSION:** John Donaldson (the son) is tagged `is_narrator: true` — this is WRONG. Uncle Bill is the narrator. The story is told in first person by Uncle Bill. The overview even says "first-person retrospective". This was CORRECT in attempt 51 (Uncle Bill = narrator) and has REGRESSED.
- ✗ "Johnny" (supporting_4) should be alias of the son, not separate character
- ✗ `overview.narrator_name` is still null

**Sub-Dimension C: Alias Grouping: 5/10** (unchanged)

- Uncle Bill aliases: ["Bill"] — minimal but acceptable ✓
- John Donaldson (the father) aliases: ["John Donaldson", "the father"] — good, improved from attempt 51 ✓
- John Donaldson (the son) aliases: ["John", "John Donaldson"] — missing "Johnny" ✗
- "Johnny" is separate character instead of son's alias ✗

### 2.3 Character Profiles: 4/10 ✗ (unchanged)

**ALL physical_description fields are null** (0/7 characters).
**ALL speech_patterns fields are null** (0/7 characters).
**ALL evidence_quotes are null** (0/7 characters).

**Relationships** (4/7 have them):
- John Donaldson (the son): `{"Uncle Bill": "mentor", "John Donaldson (the father)": "parent"}` — "mentor" is reasonable, "parent" is correct ✓
- John Donaldson (the father): `{"John Donaldson (the son)": "parent"}` — minimal but correct ✓, missing relationship to Uncle Bill (cousin) ✗
- Uncle Bill: `{"John Donaldson (nephew)": "mentor", "John Donaldson Sr. (son)": "victimizer"}` — reference names don't match character entries ✗, "victimizer" is bizarre and incorrect ✗ (Uncle Bill covered up the father's scandal — the opposite of victimization). The father was Uncle Bill's cousin, not a victimizer.
- Ted Frith: `{"John Donaldson": "unknown", "Ted Frith": "ally"}` — self-referential (Ted Frith → Ted Frith as "ally") ✗

**KEY PROBLEM:** While fragmentation is fixed, the profiles remain empty (no descriptions, quotes, or speech patterns) and relationships contain errors and name mismatches with character entries.

### 2.4 Chapter Summaries: 7.5/10 ✗ (unchanged)

**Section 1:** Good quality. Captures Uncle Bill receiving the letter, backstory about the father at Yale, the scandal, and the death. Characters_present only lists ["Narrator"] instead of naming Uncle Bill. ✓/minor ✗

**Section 2:** Comprehensive narrative arc. Characters_present correctly lists Uncle Bill and John Donaldson (son and father). ✓
- **Error (PERSISTENT):** Still says "his deceased sister's son" — should be "his deceased cousin's son." The text explicitly states the father was Uncle Bill's cousin. This has persisted across multiple attempts. ✗
- Otherwise captures the fishing trip, WWI, Italy, the father's reveal, and the deathbed scene well.

Both summaries are appropriate length and capture tone well.

### 2.5 Pronunciation Guide: 7/10 ✗ (unchanged)

20 entries, 15 with IPA.

**Genuinely useful (13):**
- Italian/foreign terms: Caporetto, Piave, Solferino, Guerre, Venetia, Tagliamento, Bersagliari, Bordeaux — all correctly flagged ✓
- Homographs: live, minute, read, close, moderate — useful for narrator ✓

**False positives (7):** whippersnapper, thriftless, thickset, manliness, dum-dums, orderlies, mayn't — all standard English words that a narrator would know. 35% false positive rate brings the score down.

### 2.6 HTML Presentation: 8/10 ✓ (unchanged)

Navigation works, tabs functional, layout clean. Content quality issues are scored in their respective categories.

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (user-configured, appropriate)
- Pipeline: V2 with Phase 2 graph-based identity resolution
- No retries, no JSON parse failures — clean pipeline execution
- Character Profiles: 4 items profiled out of 7 characters — only main_cast gets full profiling
- No configuration issues — the remaining problems are in narrator detection, profile population, and summary accuracy

## Current Issues (Priority Order)

### CRITICAL

1. **Narrator regression: Son tagged as narrator instead of Uncle Bill** [Identity Resolution, score impact ~1.0 across Characters + Summaries]
   - Problem: `main_cast_1` "John Donaldson (the son)" has `is_narrator: true`, but Uncle Bill is the narrator. The story is told in first person by Uncle Bill. Overview says "first-person retrospective" and plot_summary is clearly from Uncle Bill's perspective.
   - Evidence: Attempt 51 correctly had Uncle Bill as narrator. This REGRESSED in attempt 52 despite no changes to narrator detection logic.
   - Root cause: The dedup fix re-ordered characters (Uncle Bill was main_cast_1 in attempt 51, now main_cast_3). Narrator assignment may depend on character ordering/ID, or the LLM made a different narrator call this time.
   - Location: `src/analyzer.py` or `src/pipeline/character_extraction_v2/main_cast.py` — narrator detection/assignment logic
   - Fix approach: Investigate whether narrator assignment is order-dependent. The narrator detection should be robust to character reordering after dedup. This may be LLM non-determinism rather than a code bug.
   - **IMPACT:** Affects Characters (Identity Resolution), Profiles (narrator-perspective filtering), and potentially Summaries.

### HIGH

2. **Margaret Donaldson still missing** [Completeness, score impact ~0.3]
   - Problem: Margaret (the father's wife/widow) is mentioned in the text — she writes Uncle Bill a letter. Present in attempt 50 but absent since attempt 51.
   - Evidence: She's a minor but named character with narrative significance (her letter haunts Uncle Bill).
   - Location: Supporting cast extraction or mention threshold filtering
   - Fix: May need lower mention threshold or improved detection of characters mentioned in summaries

3. **"Johnny" is a separate character instead of son's alias** [Alias Grouping, score impact ~0.3]
   - Problem: supporting_4 "Johnny" (2 mentions) should be alias of John Donaldson (the son)
   - Evidence: "Johnny" is a diminutive of "John" referring to the boy in the story
   - Location: Alias resolution / supporting cast extraction
   - Fix: Diminutive name matching (Johnny → John) in alias resolution

4. **Summary says "sister" instead of "cousin"** [Summaries, score impact ~0.3]
   - Problem: Section 2 says "his deceased sister's son" — should be "his deceased cousin's son"
   - Evidence: The text says "a cousin, who had come to be this lad's father." This error has persisted across 4+ attempts.
   - Location: Summary LLM hallucination — the LLM consistently gets this relationship wrong
   - Fix: This is an LLM accuracy issue, not a code bug. May need prompt engineering or fact-checking verification.

5. **All evidence_quotes are null** [Profiles, score impact ~0.5]
   - Problem: Every character has `evidence_quotes: null` — no supporting quotes from the text
   - Location: `src/pipeline/character_profiling/` — profile generation or F19 grounding gate
   - Pipeline notes mention "F19 warnings: 4 characters have potentially ungrounded evidence quotes" — the grounding gate may be rejecting ALL quotes

### MEDIUM

6. **All physical_description and speech_patterns are null** [Profiles, score impact ~0.3]
   - Problem: No character has physical descriptions or speech pattern notes despite the text containing some (e.g., "dark-complexioned" for the father)
   - Location: `src/pipeline/character_profiling/`

7. **Uncle Bill relationships: wrong names and bizarre "victimizer" label** [Profiles, score impact ~0.2]
   - Problem: Uncle Bill's relationships reference "John Donaldson (nephew)" and "John Donaldson Sr. (son)" — these names don't match any character entry. "victimizer" is incorrect — Uncle Bill HELPED the father by covering up his scandal.
   - Location: Profile LLM output — relationship extraction is referencing non-canonical names

8. **"Red Cross" extracted as character** [Completeness, score impact ~0.2]
   - Problem: supporting_1 "Red Cross" (4 mentions) is an organization, not a character
   - Location: Supporting cast extraction prompt or filtering

9. **Pronunciation: 35% false positive rate** [Pronunciation, score impact ~0.5]
   - Problem: 7 of 20 entries are standard English words (whippersnapper, thriftless, thickset, manliness, dum-dums, orderlies, mayn't)
   - Location: `src/pipeline/pronunciation/` — filtering logic

10. **Structure: 2 sections for continuous text** [Structure, score impact ~0.5]
    - Problem: Continuous short story split into 2 sections, both with null titles
    - Location: `src/pipeline/chapter_detection/`

11. **`narrator_name` field is null** [Identity Resolution, score impact ~0.2]
    - Problem: Top-level `overview.narrator_name` is null even though a character has `is_narrator: true`
    - Location: `src/analyzer.py` — narrator_name population logic

### LOW

12. **Section 1 characters_present only lists "Narrator"** [Summaries]
    - Should name Uncle Bill specifically

13. **Ted Frith self-referential relationship** [Profiles]
    - Ted Frith has `"Ted Frith": "ally"` — self-referencing relationship

## Fix Priority Recommendation

**CRITICAL #1 (narrator regression) is the most impactful single fix.** However, this may be LLM non-determinism rather than a code bug introduced by the dedup change. Before making code changes:

1. **Verify whether narrator assignment is order-dependent** — the dedup changed character ordering (Uncle Bill moved from main_cast_1 to main_cast_3). If narrator assignment depends on ID ordering, fixing that dependency would make it robust.

2. **If it's purely LLM non-determinism**, a re-run might naturally fix it. But given we're on attempt 52, adding deterministic narrator validation would be more reliable.

**HIGH #2-5 are recurring issues** that have persisted across multiple attempts. The evidence_quotes nullification (HIGH #5) and profile emptiness (MEDIUM #6) suggest the profiling pipeline is systematically failing to populate these fields, possibly due to the grounding gate being too aggressive.

**DO NOT:**
- Revert the dedup fix (it clearly worked — father went from 3 entries to 1)
- Change model configuration (user-set)
- Attempt broad changes to multiple subsystems at once

**SUGGESTED APPROACH:** Focus on CRITICAL #1 only. Check if narrator detection can be made order-independent, or if there's a deterministic signal (the word "I" in summaries, the plot_summary perspective) that can validate narrator assignment.

## Fix History

### Attempt 52 — Deduplicate exact canonical name matches — **PARTIAL SUCCESS**
- **Issue targeted:** Father character tripled into 3 entries
- **Fix:** Added `_deduplicate_exact_canonical_names()` in `main_cast.py`
- **Father result:** ✓ FIXED — now a single entry "John Donaldson (the father)" with merged aliases
- **New regression:** Narrator flipped from Uncle Bill to the son (was correct in attempt 51)
- **Character count:** 9 → 7 (cleaner)
- **Files modified:** `src/pipeline/character_extraction_v2/main_cast.py`, `tests/test_character_extraction_v2.py`

### Attempt 51 — Fix same-name split false positives — **PARTIAL SUCCESS**
- **Issue targeted:** Uncle Bill falsely split
- **Fix:** Modified `_enforce_same_name_splits()` pattern matching
- **Uncle Bill result:** ✓ FIXED — single entity, correctly narrator
- **New regression:** Father character tripled
- **Files modified:** `src/pipeline/character_extraction_v2/main_cast.py`

### Attempt 50 — Re-run to test LLM non-determinism — **PARTIAL RECOVERY**
- Score: 6.08. Father/son fixed, Uncle Bill still split.

### Attempt 49 — Strip parenthetical disambiguators in passage gatherer — **MIXED**
- Score: 6.15. Profiles improved but upstream character extraction regressed.

### Attempt 48 — REVERT attempt 47 deduplication + re-analyze — **BASELINE RECOVERY**
- Score: 6.88.

### Attempt 47 — Deduplicate identical canonical names after Pass 2 — **REGRESSION (REVERTED)**
- Score: 5.95. Over-aggressive dedup caused false merges.

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 52 | Deduplicate exact canonical name matches | `main_cast.py`, `test_character_extraction_v2.py` | **PARTIAL** — Father deduped ✓, Narrator regressed ✗. Score: ~6.33 |
| 51 | Fix same-name split false positives | `main_cast.py` (lines 910-972) | **PARTIAL** — Uncle Bill fixed ✓, Father tripled ✗. Score: ~5.93 |
| 50 | Re-run for LLM non-determinism | None | **PARTIAL** — Father/son fixed, Uncle Bill still split. Score: 6.08 |
| 49 | Strip parenthetical disambiguators | `passage_gatherer.py` | **MIXED** — Score: 6.15 |
| 48 | REVERT attempt 47 dedup | `main_cast.py` | **BASELINE RECOVERY** — Score: 6.88 |
| 47 | Dedup identical canonical names | `main_cast.py` (+75 lines) | **REGRESSION (REVERTED)** — Score: 5.95 |
| 46 | Extend grounding gate | `mention_search.py`, tests | **PARTIAL SUCCESS** — Score: 7.08 |
| 45 | REVERT attempt 44 alias filter | `main_cast.py`, tests | **PARTIAL RECOVERY** — Score: 6.88 |
| 44 | Filter shared base name aliases | `main_cast.py`, tests | **REGRESSION** — Score: 6.45 |
| 43 | Disambiguator ROLE_CONFLICT | `evidence_collectors.py` | **SUCCESS** — Score: 6.98 |

**PATTERN ALERT:** `main_cast.py` has been modified 10 times (attempts 39-52). The dedup fix in attempt 52 achieved its goal (father dedup), but the narrator detection is now wrong — likely LLM non-determinism since no narrator logic was changed. A deterministic narrator validation step would prevent this oscillation.

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
| 50 | 6.08 | -0.52 | Father/son fixed, Uncle Bill still split |
| 51 | 5.93 | -0.67 | Uncle Bill fixed ✓, Father TRIPLED ✗ |
| 52 | 6.33 | -0.27 | Father deduped ✓, Narrator regressed ✗ |

## Next Action
Run PROMPT_fix.md to address narrator misidentification (CRITICAL #1). The dedup fix worked — father is now correctly a single entity. The narrator regression is likely LLM non-determinism (no narrator code was changed). A deterministic narrator validation step would prevent this from oscillating between attempts.
