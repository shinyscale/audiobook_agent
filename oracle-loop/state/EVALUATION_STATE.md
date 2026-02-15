# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 29
- **Phase:** awaiting_analysis
- **baseline_score:** 6.60
- **Competitive Mode:** single (all stages: characters, structure, summaries)

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Latest Scores
- Structure Detection: 7/10 ✗
- Character Extraction: 7.5/10 ✗
  - Completeness: 8/10
  - Identity Resolution: 7.5/10
  - Alias Grouping: 7/10
- Character Profiles: 7/10 ✗
- Chapter Summaries: 7.5/10 ✗
- Pronunciation Guide: 5/10 ✗
- HTML Presentation: 8/10 ✓
- **Overall: 7.05/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (5 categories below threshold)

## Overall Score Calculation

```
Overall = (7 × 0.20) + (7.5 × 0.25) + (7 × 0.15) + (7.5 × 0.20) + (5 × 0.10) + (8 × 0.10)
        = 1.40 + 1.875 + 1.05 + 1.50 + 0.50 + 0.80
        = 7.125
```

**Overall: 7.13/10** (UP from 6.65 in attempt 28)

## Detailed Evaluation

### 2.1 Structure Detection: 7/10 ✗

Unchanged from previous attempts. "American, Sir" is a continuous short story with no chapter markers. The tool produces 2 sections, both with null titles and null start/end lines. Per the rubric, a continuous text should be identified as a single section (9-10); splitting into 2 sections is a structural error (6-7). Score 7 because the summaries for each section are coherent and usable despite the artificial split.

### 2.2 Character Extraction: 7.5/10 ✗ (UP from 6 in attempt 28)

**MAJOR IMPROVEMENT: Disambiguation labels now applied!** The post-processing fix from attempt 29 successfully adds "(the son)" and "(the father)" labels to the two John Donaldson entries. This is the breakthrough that attempts 26-27 failed to achieve.

**Character list (8 total, 4 main_cast + 4 supporting):**
- `main_cast_1`: **John Donaldson (the son)** — 9 mentions, `is_narrator: true`, role: `supporting` — NOW DISAMBIGUATED ✓
- `main_cast_2`: **John Donaldson (the father)** — 28 mentions, aliases: ["John", "John Donaldson's"], role: `supporting` — NOW DISAMBIGUATED ✓
- `main_cast_3`: **Margaret Donaldson** — 2 mentions, role: `supporting` — NEW ✓ (was absent in previous attempts)
- `main_cast_4`: **Uncle Bill** — 18 mentions, `is_narrator: true`, role: `protagonist` — CORRECT ✓
- `supporting_1`: **Joe Barron** — 3 mentions — CORRECT ✓
- `supporting_2`: **Red Cross** — 4 mentions — WRONG (organization, not character) ✗
- `supporting_4`: **Ted Frith** — 5 mentions, alias: "Ted" — CORRECT ✓
- `supporting_6`: **Johnny** — 2 mentions — FRAGMENTED (should be alias of the son) ✗

**Sub-Dimension A: Completeness: 8/10** (stable)
- All 5 real characters present: Uncle Bill, father, son, Joe Barron, Ted Frith ✓
- Margaret Donaldson now appears as a main_cast entry ✓ (improvement)
- "Red Cross" is an organization, not a character ✗
- "Johnny" separate entry instead of alias ✗ (minor — only 2 mentions)

**Sub-Dimension B: Identity Resolution: 7.5/10** (UP from 5)
- Father/son structural split exists ✓
- **Disambiguation labels applied!** "John Donaldson (the son)" and "John Donaldson (the father)" clearly distinguishable ✓✓ (the core CRITICAL from attempt 28 is FIXED)
- Constraint edges (role_conflict) still present and working ✓
- "Johnny" remains separate instead of being merged as alias of the son ✗
- `main_cast_1` (son) has `role: "supporting"` while `main_cast_4` (Uncle Bill) has `role: "protagonist"` — the son's role could arguably be "protagonist" since it's his story, but "supporting" is acceptable given Uncle Bill narrates

**Sub-Dimension C: Alias Grouping: 7/10** (UP from 6)
- "John Donaldson's" (possessive) appears as alias of main_cast_2 ✗
- "Johnny" should be alias of main_cast_1 (the son) ✗
- "the father" NOT in aliases (was in attempt 28) — mildly worse but the canonical name now says "(the father)" so less needed
- "John" assigned to father — acceptable since father has more mentions with "John"
- "Ted" → Ted Frith: correct ✓
- "Bill" → Uncle Bill: correct ✓

### 2.3 Character Profiles: 7/10 ✗ (stable from attempt 28)

**Father's profile (main_cast_2): EXCELLENT ✓**
- Appearance: "big, athletic, grizzled chap, maybe fifty-five or over, shabby as to clothes, yet with an air like a duke" — accurate, with evidence quotes ✓
- Personality: "morally ambiguous man who committed grave betrayal by embezzling" — accurate ✓
- Voice guidance: "low, weary, controlled baritone" with dialect notes about foreign inflection — excellent for narrators ✓
- Evidence quotes include key lines: "Took money... Very unjustifiable" and "American, sir" ✓

**Uncle Bill's profile (main_cast_4): EXCELLENT ✓**
- Appearance: "elderly, grizzled, small man" — accurate ✓
- Personality: "quiet, reluctant acts of profound sacrifice" — excellent characterization ✓
- Voice guidance: detailed tone, formality, emotional range — very useful ✓
- Evidence quotes well-chosen ✓

**Son's profile (main_cast_1): EMPTY ✗**
- Appearance: "No physical description available in text" — this is WRONG. The text says he's tall, olive-skinned, dark-faced with thickset long lashes, looks like his father. The father's profile even quotes the evidence: "he looked like his father. Very olive he was--and is--and his blue eyes shone out of the dark face"
- Personality: "Insufficient information" — WRONG. He's a Yale-educated young man who volunteered as an ambulance driver in WWI, brave, emotional, capable of deep feeling
- Voice guidance: "No specific voice guidance available" — WRONG
- This is still the core profile issue: the profiler cannot gather passages for the son because his name "John Donaldson (the son)" includes the label. The profiler likely searches for exact name matches and finds nothing

**Relationships:**
- Father → son: "father" — correct ✓
- Father → Uncle Bill: "enemy" — WRONG ✗ (they're cousins; the text shows complex feelings but not enmity)
- Uncle Bill → "John (the father)": "ally" — acceptable but should be "family/cousin" ✗
- Uncle Bill → "John Donaldson (the son)": "mentor" — good ✓
- Uncle Bill → "John Donaldson (the father) - dying in Italy": "ally" — this is a duplicate relationship with a bizarre qualifier ✗

**Why 7/10:** Father's and Uncle Bill's profiles are excellent (9/10 quality). But the son's profile is completely empty despite having textual evidence available. The relationship labels are inconsistent ("enemy" instead of "cousin/family"). Profile quality is bottlenecked by the son's empty profile.

### 2.4 Chapter Summaries: 7.5/10 ✗ (stable)

**Chapter 1 (section 1):** EXCELLENT. Correctly describes the letter, Uncle Bill's memories, the cousin relationship, the scandal, the widow Margaret Donaldson. Uses "cousin" correctly. Well-written and comprehensive.

**Chapter 2 (section 2):** Good quality but contains the recurring "sister" hallucination:
- "his deceased sister's twelve-year-old son" — WRONG. Uncle Bill is the father's COUSIN, not brother/sister. The Ch1 summary correctly says "cousin."
- "his late brother" — WRONG. Same error — treats them as siblings instead of cousins.
- Otherwise excellent: covers Yale, fishing trip, WWI, Caporetto, reunion, deathbed revelation.
- `characters_present`: ["Uncle Bill", "John Donaldson (the son)", "John Donaldson (the father)"] — EXCELLENT, now uses disambiguated names ✓

**Plot summary (in structure):** Excellent — accurate full narrative arc, captures emotional arc beautifully.

**Why 7.5/10:** Two factual errors ("sister" and "brother" instead of "cousin" in Ch2) in otherwise excellent summaries. The plot summary is outstanding. The `characters_present` now uses disambiguated names — improvement from attempt 28.

### 2.5 Pronunciation Guide: 5/10 ✗ (stable)

31 entries, 25 with IPA.

**Genuinely useful (9):** Caporetto, Piave, Solferino, Tagliamento, Bersagliari, Venetia, Guerre, Bordeaux, Margaret — Italian/French geographic/military terms ✓

**Acceptable homographs (5):** live, minute, read, close, moderate — context-dependent pronunciation ✓

**False positives (17):**
- Standard names: Bill, Donaldson, Cross, Ted, Donaldson's, Joe, Barron, Frith, Johnny ✗
- Common English words: whippersnapper, thriftless, thickset, manliness, dum-dums, orderlies, mayn't, was ✗
- "was" is particularly egregious ✗

**Why 5/10:** 17/31 entries (~55%) are false positives. The useful entries (Italian/French terms) are genuinely valuable for a narrator, but they're buried in noise.

### 2.6 HTML Presentation: 8/10 ✓ (UP from 7)

**Why upgraded to 8/10:**
1. **Disambiguation labels visible!** The HTML now shows "John Donaldson (the son)" and "John Donaldson (the father)" as distinct, clearly labeled entries ✓✓ — this was the PRIMARY presentation blocker in attempt 28
2. Main Characters section has 4 entries with rich profile data ✓
3. Voice guidance section with tone, dialect, verbal tics, example quotes — very useful for narrators ✓
4. Relationship grid functional ✓
5. `characters_present` in Ch2 uses disambiguated names ✓
6. Margaret Donaldson appears as a character entry ✓

**Remaining minor issues:**
- "Red Cross" listed as supporting character ✗
- "Johnny" listed as separate supporting character ✗
- "John Donaldson's" (possessive) shown as alias ✗
- Uncle Bill's relationships has duplicate father entries ("John (the father)" and "John Donaldson (the father) - dying in Italy") ✗
- Son's profile sections all say "No information available" — looks empty ✗
- Ch1 `characters_present` not visible (section 1 has no characters_present tags in HTML)

**Why 8/10:** The disambiguation labels fix transformed the HTML from confusing (two identical entries) to clear (two distinct, labeled entries). Profile rendering for father and Uncle Bill is excellent. The remaining issues are data-driven (upstream), not presentation bugs. The HTML correctly renders what the pipeline gives it.

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (user-configured, appropriate)
- Pipeline: V2 with Phase 2 graph-based identity resolution
- Identity graph: constraint edges present (role_conflict between main_cast_1 and main_cast_2) ✓
- main_cast_count: 4 (UP from 3 — Margaret Donaldson added) ✓
- supporting_cast_count: 4
- 0 LLM retries — good
- No config changes recommended
- Profiling: 5 stages, all successful, no JSON parse failures

## Current Issues (Priority Order)

### CRITICAL

None! The previous CRITICAL issue (disambiguation labels) is FIXED.

### HIGH

1. **Son's profile is completely empty despite textual evidence** [Profiles]
   - Problem: `main_cast_1` (John Donaldson (the son)) has "No physical description available", "Insufficient information for personality analysis", and no voice guidance. The text describes him as tall, olive-skinned, dark-faced, brave ambulance driver.
   - Evidence: Father's profile even quotes "he looked like his father. Very olive he was" — this describes the SON, yet it appears in the father's evidence
   - Root cause: The profiler searches for character names in the text. "John Donaldson (the son)" with the disambiguation label won't match any text passages. The profiler needs to search using the BASE name "John Donaldson" and then use disambiguation context to separate father vs son passages.
   - Location: `src/pipeline/character_profiling/` — passage gatherer likely does exact name matching
   - Fix: When searching for passages, strip the disambiguation label "(the son)" from the name before searching. Then use the identity graph's constraint edge information to filter passages to the correct character.

2. **"Red Cross" extracted as character** [Completeness]
   - Problem: Organization, not a character (`supporting_2`, 4 mentions). Same as all prior attempts.
   - Location: `src/pipeline/character_extraction_v2/supporting.py`
   - Fix: Add prompt guidance to exclude organizations/institutions, or add post-processing filter for known organization patterns

3. **Pronunciation: 17/31 entries are false positives (~55%)** [Pronunciation]
   - Same as all prior attempts. Common names (Bill, Ted, Joe, Johnny) and words (was, whippersnapper, thickset) flagged unnecessarily.
   - Location: `src/pipeline/pronunciation_guide/proposers/`
   - Fix: Improve filtering to exclude standard English names and common words

4. **Chapter 2 "sister"/"brother" hallucination** [Summaries]
   - Problem: Ch2 says "his deceased sister's son" and "his late brother" — Uncle Bill is the father's COUSIN, not sibling.
   - This is the LLM hallucinating. Ch1 summary correctly says "cousin."
   - Location: `src/pipeline/chapter_summary/summarizer.py`

### MEDIUM

5. **"Johnny" separate instead of alias of the son** [Alias Grouping]
   - Problem: "Johnny" (`supporting_6`, 2 mentions) should be an alias of "John Donaldson (the son)".
   - The disambiguation labels are now in place, so the merge logic should be able to connect "Johnny" to the younger character.

6. **"John Donaldson's" (possessive) is an invalid alias** [Alias Grouping]
   - Same as all prior attempts. Possessive forms should be stripped.

7. **Father → Uncle Bill relationship says "enemy"** [Profiles]
   - Problem: Should be "family" or "cousin" — they are cousins. The relationship is complex (Bill resents John's betrayal) but "enemy" is inaccurate.
   - Uncle Bill's own data says "John (the father): ally" — inconsistent with father's "enemy" label.

8. **Uncle Bill has duplicate father relationship entries** [Profiles]
   - Problem: "John (the father): ally" AND "John Donaldson (the father) - dying in Italy: ally" — same person referenced twice with different name forms.

### LOW

9. **Structure: 2 sections for continuous short story** [Structure]
   - Same as all prior attempts. Not worth a targeted fix for this text alone.

10. **Son's `is_narrator: true` may be debatable** [Identity Resolution]
    - The son tells his wartime story as reported speech through Uncle Bill. Calling him a "secondary narrator (nested narrative)" is borderline acceptable.

11. **Ch1 `characters_present` empty in HTML** — section 1 has no character tags displayed

## Fix Priority

The biggest remaining score blockers are:
1. **Pronunciation false positives** (5/10 → needs 8/10, 3-point gap)
2. **Son's empty profile** (drags Profiles from potential 8.5 to 7/10)
3. **Summary "sister" hallucination** (drags Summaries from 9 to 7.5)
4. **Structure 2-section split** (7 → needs 8, but hard to fix generically)

**Recommended fix order:** Pronunciation (#3) has the largest gap and is the most self-contained fix. Then son's profile (#1) and "Red Cross" filtering (#2).

## Fix History

### Attempt 29 — Disambiguation labels via post-processing (SUCCESS!)
- **Issue targeted:** CRITICAL #1 — Both John Donaldson entries have identical names with no disambiguation labels
- **Changes made:** Added `_apply_disambiguation_labels_from_constraints()` as Step 5.11 in `run()` method
- **Result:** SUCCESS — Labels applied correctly: "John Donaldson (the son)" and "John Donaldson (the father)"
- **Score:** 7.13 (UP from 6.65)
- **File modified:** `src/agents/characters.py`
- **Why this succeeded where attempts 26-27 failed:** POST-PROCESSING ONLY — runs after ALL character extraction/merging is complete, only modifies `canonical_name` field

### Attempt 28 — Revert to attempt 25 state (REVERT SUCCESSFUL)
- **Issue targeted:** CRITICAL #1 from attempt 27 — main_cast pipeline produced ZERO characters
- **Changes made:** Reverted `src/agents/characters.py` to attempt 25 state
- **Result:** SUCCESS — main_cast pipeline restored. 3 main_cast characters extracted.
- **Score:** 6.65
- **File modified:** `src/agents/characters.py`

### Attempt 27 — Revert + re-implement disambiguation labels (MAJOR REGRESSION)
- **Issue targeted:** CRITICAL #1 from attempt 26
- **Result:** WORSE REGRESSION — main_cast_count: 0
- **Score:** 5.75
- **File modified:** `src/agents/characters.py`

### Attempt 26 — Apply disambiguation labels (REGRESSION)
- **Issue targeted:** Two identical "John Donaldson" entries
- **Result:** REGRESSION — main_cast_2 dropped
- **Score:** 6.40
- **File modified:** `src/agents/characters.py`

### Previous attempts — see earlier evaluation states

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
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

## Next Action

Run PROMPT_fix.md to address HIGH issues, starting with pronunciation false positives (largest score gap: 5→8 needed), then son's empty profile, then "Red Cross" filtering.

### Attempt 30 — Pronunciation false positive reduction (CHARACTER PROPOSER FIX)
- **Issue targeted:** HIGH #3 — Pronunciation: 17/31 entries are false positives (~55%)
- **Root cause:** CharacterProposer flagged ALL character name words without checking CMU dictionary. Common English names like "Bill", "Ted", "Joe" were flagged even though they're in the authoritative English pronunciation dictionary.
- **Changes made:** 
  - Added CMU dictionary loading to CharacterProposer
  - Added check to skip words that are in CMU dictionary (universal invariant: if it's in the authoritative English dictionary, it doesn't need pronunciation guidance)
  - **NOT a keyword filter** — uses universal signal (CMU dictionary presence) instead of book-specific word lists
- **Files modified:**
  - `src/pipeline/pronunciation_guide/proposers/character_proposer.py` — added `_load_cmu_dict()` method and CMU check in `propose()`
  - `tests/test_word_index.py` — updated test to match new behavior (Gatsby also in CMU, correctly skipped)
- **Smoke test:** PASS — verified Bill, Ted, Joe, Johnny, John are in CMU and will be skipped. Italian names (Caporetto, Piave, etc.) NOT in CMU and will still be flagged.
- **Test suite:** PASS — 336 passed, 10 skipped
- **Expected impact:** Reduce false positives from ~55% to <30%. Italian/foreign terms will still be flagged correctly.
