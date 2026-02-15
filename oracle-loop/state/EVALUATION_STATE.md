# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 28
- **Phase:** awaiting_analysis
- **baseline_score:** 6.60
- **Competitive Mode:** single (all stages: characters, structure, summaries)

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Latest Scores
- Structure Detection: 7/10 ✗
- Character Extraction: 4/10 ✗
  - Completeness: 5/10
  - Identity Resolution: 3/10
  - Alias Grouping: 5/10
- Character Profiles: 5/10 ✗
- Chapter Summaries: 7.5/10 ✗
- Pronunciation Guide: 5/10 ✗
- HTML Presentation: 6/10 ✗
- **Overall: 5.65/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (6 categories below threshold)

## Overall Score Calculation

```
Overall = (7 × 0.20) + (4 × 0.25) + (5 × 0.15) + (7.5 × 0.20) + (5 × 0.10) + (6 × 0.10)
        = 1.40 + 1.00 + 0.75 + 1.50 + 0.50 + 0.60
        = 5.75
```

**Overall: 5.75/10**

## Detailed Evaluation

### 2.1 Structure Detection: 7/10 ✗

**Unchanged from previous attempts.** "American, Sir" is a continuous short story with no chapter markers. The tool produces 2 sections, both with null titles and null start/end lines. Per the rubric, a continuous text should be identified as a single section (9-10); splitting into 2 sections is a structural error (6-7). Score 7 because the summaries for each section are coherent and usable despite the artificial split.

### 2.2 Character Extraction: 4/10 ✗ (DOWN from 5 in attempt 26)

**CRITICAL REGRESSION:** The main cast pipeline produced ZERO characters (`main_cast_count: 0` in `pipeline_metadata`). ALL 6 characters come from the supporting cast pipeline only (all have `supporting_*` IDs). In attempt 25/26, characters had `main_cast_*` IDs and the father/son split was working via `role_conflict` constraint edges. The identity graph's `constraint_edges` is now `null`.

**Characters present (6 total, DOWN from 7 in attempt 26):**
- `supporting_1`: Uncle Bill — 18 mentions, `is_narrator: true`, role: `protagonist` — CORRECT ✓
- `supporting_2`: John Donaldson — 28 mentions, `is_narrator: false`, role: `minor` — CONFLATED (father+son merged) ✗
- `supporting_4`: Joe Barron — 3 mentions — CORRECT ✓
- `supporting_5`: Red Cross — 4 mentions — WRONG (organization, not character) ✗
- `supporting_7`: Ted Frith — 5 mentions, alias: "Ted" — CORRECT ✓
- `supporting_9`: Johnny — 2 mentions — FRAGMENTED (should be alias of the son) ✗

**Missing characters:**
- Margaret Donaldson — was `main_cast_3` in attempt 26 with 2 mentions, now completely gone
- Second John Donaldson (the son) — the father/son split from attempt 25 is gone

**Sub-Dimension A: Completeness: 5/10** (DOWN from 7)
- Margaret Donaldson is completely absent (was present in attempt 26)
- The son has no distinct representation at all
- "Red Cross" is an organization, not a character
- Only 4 of the ~7 real characters are properly represented

**Sub-Dimension B: Identity Resolution: 3/10** (unchanged)
- Father/son John Donaldson still conflated into a single entry
- The identity graph has NO constraint edges — the `role_conflict` mechanism from attempt 25 is completely absent
- No main_cast characters means the disambiguation labels code had nothing to operate on
- "Johnny" still separate instead of being an alias of the son

**Sub-Dimension C: Alias Grouping: 5/10** (DOWN from 6)
- "John Donaldson's" (possessive) still appears as an alias ✗
- "Johnny" should be alias of the son character ✗
- "John" is an alias of the single John Donaldson — ambiguous ✗
- Ted → Ted Frith: correct ✓
- Bill → Uncle Bill: correct ✓

### 2.3 Character Profiles: 5/10 ✗ (DOWN from 7)

**REGRESSION: All `physical_description` fields are null (0/6).** In attempt 26, Uncle Bill had an excellent profile with physical description. Now ALL physical descriptions are missing.

**Uncle Bill profile:**
- personality summary is good — accurately describes his character ✓
- Relationships: `"John Donaldson (the son)": "mentor"` and `"John Donaldson (the father)": "family"` — the relationships reference disambiguated names but no such character entries exist ✗
- Evidence quotes are accurate ✓
- No physical description ✗

**John Donaldson profile:**
- personality accurately describes the FATHER — moral ambiguity, embezzlement, redemption ✓
- Evidence quotes are excellent and accurate ✓
- Relationships: references "John Donaldson (son)" — doesn't match any character entry ✗
- "Red Cross / American military" listed as relationship — Red Cross is an organization ✗
- No physical description ✗
- No representation of the son's character at all ✗

**Ted Frith profile:**
- personality is overly heroic for a minor character
- Evidence quote "'I'm American to-day, sir!'" is MISATTRIBUTED — this is the father's quote, NOT Ted Frith's ✗
- This is a significant factual error

**Why 5/10:** Zero physical descriptions (major regression), misattributed evidence for Ted Frith, relationship names reference non-existent disambiguated character entries, son has no profile at all.

### 2.4 Chapter Summaries: 7.5/10 ✗

**Chapter 1 (section 1):** EXCELLENT. Correctly describes the letter, Uncle Bill's memories, the cousin relationship, the scandal, Margaret Donaldson. Uses "cousin" correctly. `characters_present: ["the narrator"]` — acceptable but "Uncle Bill" would be better.

**Chapter 2 (section 2):** Good quality but contains the recurring "sister" hallucination:
- "his deceased sister's twelve-year-old son" — WRONG. Uncle Bill is the father's COUSIN, not his brother/sister. Ch1 correctly says "cousin." The plot_summary also correctly says "cousin."
- Otherwise excellent: covers Yale, fishing trip, WWI, Caporetto, reunion, deathbed revelation.
- `characters_present`: ["Uncle Bill", "John Donaldson (the son)", "John Donaldson (the father)"] — EXCELLENT, correctly disambiguates both John Donaldsons ✓

**Plot summary (nested in structure):** EXCELLENT — accurate full narrative arc across 3 well-structured paragraphs. Uses "cousin" correctly throughout. Captures the emotional arc of the story beautifully.

**Why 7.5/10:** One factual error ("sister" instead of "cousin" in Ch2) in otherwise excellent summaries. The plot summary is outstanding.

### 2.5 Pronunciation Guide: 5/10 ✗

**Unchanged from previous attempts.** 30 entries, 25 with IPA.

**Genuinely useful (8):** Caporetto, Piave, Solferino, Tagliamento, Bersagliari, Venetia, Guerre, Bordeaux — Italian/French geographic/military terms ✓

**Acceptable homographs (4):** live, minute, read, close — context-dependent pronunciation ✓ (moderate is also acceptable)

**False positives (18):**
- Standard names: Bill, Donaldson, Cross, Ted, Donaldson's, Joe, Barron, Frith, Johnny, Margaret ✗
- Common English words: whippersnapper, thriftless, thickset, manliness, dum-dums, orderlies, mayn't, was ✗
- "was" is particularly egregious ✗

**Why 5/10:** 18/30 entries (60%) are false positives.

### 2.6 HTML Presentation: 6/10 ✗ (DOWN from 7)

**Issues:**
1. No main cast section — all characters in supporting cast table only ✗
2. Only ONE "John Donaldson" entry — no distinction between father and son ✗
3. "Red Cross" listed as supporting character ✗
4. "Johnny" listed as separate supporting character ✗
5. "John Donaldson's" (possessive) shown as alias ✗
6. Relationships reference names ("John Donaldson Jr.", "John Donaldson (son)", "John Donaldson (the father)") that don't match any character entry ✗
7. Zero physical descriptions displayed ✗
8. Ch1 `characters_present` shows only "the narrator" instead of "Uncle Bill" ✗
9. No book overview at top level (plot_summary is null at root, only nested) ✗
10. Ted Frith has misattributed evidence quote ✗

**Why 6/10:** The regression from zero main_cast characters and zero physical descriptions significantly degrades the presentation. A narrator can't distinguish characters or prepare voices without physical descriptions or character separation.

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (user-configured, appropriate)
- Pipeline: V2 with Phase 2 graph-based identity resolution
- Identity graph: 6 groups, NO constraint edges (regression from attempt 25/26)
- main_cast_count: 0 (CRITICAL — was 4+ in attempt 25/26)
- supporting_cast_count: 6
- 0 LLM retries — good
- Character Extraction only 4 LLM calls (suggests main_cast extraction was skipped or failed silently)
- No config changes recommended — the issue is code, not config

## Current Issues (Priority Order)

### CRITICAL

1. **REGRESSION: Main cast pipeline produced ZERO characters** [Completeness, Identity Resolution]
   - Problem: `pipeline_metadata.main_cast_count: 0`. ALL characters have `supporting_*` IDs. In attempt 25/26, characters had `main_cast_*` IDs and the identity graph had `role_conflict` constraint edges enabling father/son separation.
   - Evidence: `jq '.pipeline_metadata.main_cast_count' analysis.json` → 0. `jq '.pipeline_metadata.identity_graph.graph.constraints' analysis.json` → null. Character Extraction used only 4 LLM calls (attempt 26 used more for main_cast extraction).
   - Root cause: The attempt 27 changes to `src/agents/characters.py` likely broke the main cast pipeline. The revert + re-implementation of disambiguation labels may have inadvertently damaged the code path that runs main_cast extraction, or the inline disambiguation code is running before main_cast extraction and interfering with it.
   - Fix approach: **Check the diff between attempt 25 and attempt 27 in `src/agents/characters.py`** to find what broke main_cast extraction. The attempt 25 code produced main_cast characters correctly. The fix should restore that behavior. The disambiguation labels can be re-attempted AFTER confirming main_cast extraction works again.
   - Files: `src/agents/characters.py`

2. **Father/son John Donaldson conflation persists** [Identity Resolution]
   - Problem: Only one "John Donaldson" entry exists. The `role_conflict` constraint edge from attempt 25 is completely absent (identity graph has no constraint edges at all).
   - Evidence: Identity graph shows 6 groups, all from supporting cast. No constraint edges.
   - Dependency: Blocked by CRITICAL #1 — main_cast pipeline must work first to generate `main_cast_1` and `main_cast_2` entries that the role_conflict mechanism can separate.
   - Files: `src/agents/characters.py`

### HIGH

3. **Margaret Donaldson missing** [Completeness]
   - Problem: Was `main_cast_3` in attempt 26 with 2 mentions. Now absent entirely.
   - Dependency: Blocked by CRITICAL #1 — likely returns when main_cast pipeline is restored.

4. **Zero physical descriptions for all characters** [Profiles]
   - Problem: `physical_description` is null for all 6 characters. In attempt 26, Uncle Bill had "elderly, grizzled, small man."
   - Evidence: `jq '[.characters[] | select(.physical_description != null)] | length' analysis.json` → 0
   - Location: `src/pipeline/character_profiling/` — may be related to all characters being supporting cast (profiling may skip or reduce detail for supporting cast)
   - Dependency: May resolve when main_cast pipeline is restored (main_cast characters likely get fuller profiling).

5. **Ted Frith evidence quote misattribution** [Profiles]
   - Problem: "'I'm American to-day, sir!'" is attributed to Ted Frith. This is the FATHER's (John Donaldson's) quote — the central line of the story.
   - Evidence: The father says "American, sir" / "I heard the call—the one clear call. American." Ted Frith is a different character.
   - Location: `src/pipeline/character_profiling/passage_gatherer.py` or evidence collection
   - This is a factual error that a narrator would notice immediately.

6. **"Red Cross" extracted as character** [Completeness]
   - Problem: Organization, not character (`supporting_5`, 4 mentions). Same as all prior attempts.
   - Location: `src/pipeline/character_extraction_v2/supporting.py`

7. **"Johnny" separate instead of alias of the son** [Alias Grouping]
   - Problem: "Johnny" (`supporting_9`, 2 mentions) should be a diminutive alias of John/the son.
   - Dependency: Once father/son split is restored, "Johnny" should merge into the son's entry.

8. **Pronunciation: 18/30 entries are false positives (60%)** [Pronunciation]
   - Same as all prior attempts. Common names and words flagged unnecessarily.
   - Location: `src/pipeline/pronunciation_guide/proposers/`

9. **Chapter 2 "sister" hallucination** [Summaries]
   - Problem: Ch2 says "his deceased sister's twelve-year-old son" — Uncle Bill is the father's COUSIN, not brother/sister.
   - Location: `src/pipeline/chapter_summary/summarizer.py`

### MEDIUM

10. **"John Donaldson's" (possessive) is an invalid alias** [Alias Grouping]
    - Same as prior attempts.

11. **Relationships reference non-existent character names** [Profiles]
    - Problem: Relationships mention "John Donaldson (the son)", "John Donaldson (the father)", "John Donaldson (son)" — none match actual character entries.
    - Dependency: Will partially resolve when father/son split is properly restored with labeled names.

12. **Uncle Bill → John Donaldson relationship says "acquaintance"** [Profiles]
    - Problem: Uncle Bill's relationship to John Donaldson is merely "acquaintance" — should be "family" or "cousin"

13. **Structure: 2 sections for continuous short story** [Structure]
    - Same as all prior attempts. Not worth a targeted fix for this text alone.

### LOW

14. **Ch1 `characters_present` uses "the narrator" instead of "Uncle Bill"**
15. **plot_summary is null at root level** — only exists nested in structure
16. **Ted Frith personality is overly heroic for a minor character with 5 mentions**

## Fix History

### Attempt 28 — Revert to attempt 25 (UNDOING REGRESSION)
- **Issue targeted:** CRITICAL #1 from attempt 27 — main_cast pipeline produced ZERO characters
- **Root cause analysis:** The attempt 27 inline disambiguation code (lines 349-452) somehow prevented main_cast extraction from running or returning results. The grounding_report shows 0 grounded AND 0 ungrounded characters, meaning no profiles were extracted at all in Step 1. Character Extraction used only 4 LLM calls (far too few). The exact cause is unclear, but the fix broke the pipeline.
- **Changes made:** Reverted `src/agents/characters.py` to attempt 25 state (removed 106 lines of disambiguation code added in attempt 27)
- **Rationale:** Attempt 25 had main_cast working correctly with father/son split via role_conflict edges. The disambiguation labels feature is LOWER PRIORITY than having the main_cast pipeline functional. Restore working state first.
- **Expected result:** main_cast extraction should work again, 4+ main_cast characters should be extracted, father/son split should work (two "John Donaldson" entries with same names). Score should return to ~6.50 range.
- **File modified:** `src/agents/characters.py` (reverted to commit f3fb56a)

### Attempt 27 — Revert + re-implement disambiguation labels (MAJOR REGRESSION)
- **Issue targeted:** CRITICAL #1 from attempt 26 — `main_cast_2` disappeared after `_apply_disambiguation_labels()`
- **Changes made:**
  1. Reverted `src/agents/characters.py` to attempt 25 state
  2. Re-implemented disambiguation labels with inline code
- **Result:** WORSE REGRESSION — main_cast pipeline now produces ZERO characters (was 4+ in attempt 25/26). All characters come from supporting cast only. Identity graph has no constraint edges. Father/son split completely lost. Margaret Donaldson missing. All physical descriptions gone.
- **Score:** 5.75 (DOWN from 6.40 in attempt 26)
- **File modified:** `src/agents/characters.py`

### Attempt 26 — Apply disambiguation labels to same-name characters (REGRESSION)
- **Issue targeted:** CRITICAL #1 from attempt 25 — Two identical "John Donaldson" entries with no disambiguation labels
- **Changes made:** Added `_apply_disambiguation_labels()` method to `CharacterAgent` (src/agents/characters.py, lines 887-1012)
- **Result:** REGRESSION — The method caused `main_cast_2` to be dropped from the final output. Score dropped from 6.50 to 6.40.
- **Files modified:** `src/agents/characters.py` (lines 348-351, 887-1012)

### Attempt 25 — Populate characters_present from summaries in _get_chapters() (DATA FLOW FIX)
- **Issue targeted:** CRITICAL #1 from attempt 24 — Father/son John Donaldson conflation
- **Changes made:** Modified `_get_chapters()` to fetch summary results and populate `characters_present` on StructuralElements
- **Result:** SUCCESS — `role_conflict` constraint edge now blocks the merge. 8 characters extracted (up from 6). Two separate "John Donaldson" entries exist. main_cast_count: 4+.
- **New issues:** Both entries have identical names and profiles. Need disambiguation labels.
- **File modified:** `src/agents/characters.py` (lines 707-756)

### Attempt 24 — Summary-based disambiguation constraint (NO EFFECT)
- **Issue targeted:** Father/son conflation
- **Changes made:** Added `collect_summary_disambiguation_evidence()` to `evidence_collectors.py`
- **Result:** NO CHANGE — empty `characters_present` lists
- **Files modified:** `evidence_collectors.py`, `characters.py`

### Attempt 23 — CLEAN BASELINE (all prior fixes reverted)
- Score: 6.30

### Previous attempts (1-22) — ALL REVERTED
- Key learnings: Attempt 22 best score (7.55). Organization filtering (attempt 3) and pronunciation invariants worked.

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 28 | Revert to attempt 25 (undo regression) | `characters.py` | (awaiting analysis) |
| 27 | Revert + re-implement disambiguation labels | `characters.py` | WORSE REGRESSION — main_cast_count: 0, all characters from supporting only |
| 26 | Disambiguation labels for same-name characters | `characters.py` | REGRESSION — main_cast_2 dropped from output |
| 25 | Father/son disambiguation (data flow fix) | `characters.py` | PARTIAL SUCCESS — split works but entries have identical names/profiles |
| 24 | Father/son disambiguation | `evidence_collectors.py`, `characters.py` | NO EFFECT |
| 23 (baseline) | Clean baseline + Phase 2 pipeline | N/A | Score: 6.30 |

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.60 | — | Original baseline |
| 22 | 7.55 | +0.95 | Best score (all fixes active) |
| 23 | 6.30 | -0.30 | Clean baseline + Phase 2 pipeline |
| 24 | 6.15 | -0.45 | Fix had no effect; profiles worse |
| 25 | 6.50 | -0.10 | Father/son split working but needs disambiguation labels |
| 26 | 6.40 | -0.20 | REGRESSION — disambiguation labels fix dropped main_cast_2 |
| 27 | 5.75 | -0.85 | WORSE REGRESSION — main_cast pipeline broken, 0 main_cast chars |
| 28 | (pending) | | Revert to attempt 25 state |

## Next Action

**Attempt 28 changes applied:** Reverted to attempt 25 state to restore main_cast pipeline functionality.

Re-run analysis to verify the revert restores main_cast extraction and father/son split.
