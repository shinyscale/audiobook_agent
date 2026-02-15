# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 24
- **Phase:** awaiting_fix
- **baseline_score:** 6.60
- **Competitive Mode:** single (all stages: characters, structure, summaries)

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Pipeline Notes (Attempt 24)
- Analysis completed in 39m 3s using qwen3-next:80b-a3b-instruct-q8_0
- Competitive consensus ENABLED: characters, structure, summaries (all stages)
- Found 6 characters total (UNCHANGED from attempt 23 — fix had no effect)
- Identity graph: output/American Sir_20260215_113215/identity_graph.json
- 81 LLM calls, 112,858 tokens (0 retries)
- 30 pronunciation entries
- Warnings during analysis:
  - OCR repair: fixed 1 broken ligature
  - F19: Profile quotes for John Donaldson (2), Uncle Bill (4), Ted Frith (3) potentially ungrounded
  - LLM validation failed (got dict), keeping batch candidates (pronunciation stage)
  - Model returned error-like response during pronunciation enrichment
- **CRITICAL: Attempt 24 fix had NO EFFECT** — the summary-based disambiguation constraint edge was NOT added because `_get_chapters()` returns StructuralElements with EMPTY `characters_present` lists. The characters_present field is only populated during the final assembly in `analyzer.py:_convert_structure()`, not during character extraction.

## Latest Scores
- Structure Detection: 7/10 ✗
- Character Extraction: 5/10 ✗
  - Completeness: 6/10
  - Identity Resolution: 4/10
  - Alias Grouping: 5/10
- Character Profiles: 5/10 ✗
- Chapter Summaries: 7.5/10 ✗
- Pronunciation Guide: 5/10 ✗
- HTML Presentation: 7.5/10 ✗
- **Overall: 6.05/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (6 categories below threshold)

## Detailed Evaluation

### 2.1 Structure Detection: 7/10 ✗

"American, Sir" is a continuous short story with no explicit chapter markers. The tool produces 2 sections, both with null titles and null start/end lines. Per the rubric, a continuous text with no structural markers should be identified as a single section (score 9-10); artificially splitting into 2 sections is a structural error (score 6-7). Giving 7 because the summaries for each section are coherent and usable, just artificially split.

**Issues:**
- 2 sections instead of 1 for a continuous short story
- Both sections have null titles (displayed as "Chapter 1" and "Chapter 2")
- Both sections have null start/end line positions

### 2.2 Character Extraction: 5/10 ✗

**Unchanged from attempt 23.** The attempt 24 disambiguation fix had no effect (see root cause analysis below).

**Sub-Dimension A: Completeness: 6/10**

Characters present:
- John Donaldson (the father): 29 mentions, `main_cast_2` — CORRECT but conflated with son
- Uncle Bill: 18 mentions, `main_cast_3`, narrator=true, role=protagonist — CORRECT ✓
- Joe Barron: 3 mentions, `supporting_2` — CORRECT ✓
- Red Cross: 4 mentions, `supporting_3` — WRONG (organization, not character) ✗
- Ted Frith: 5 mentions, `supporting_5`, alias "Ted" — CORRECT ✓
- Johnny: 2 mentions, `supporting_7` — FRAGMENTED (should be alias of the son) ✗

**Missing:** John Donaldson (the son) — the story's emotional center. The boy who writes to Uncle Bill, grows up under his care, fights in WWI, and discovers his long-lost father on the battlefield. His absence is a critical extraction failure.

**Hallucinated/Invalid:** Red Cross is an organization, not a character.

**Sub-Dimension B: Identity Resolution: 4/10**

- **CRITICAL false merge:** Father and son John Donaldson conflated into one character. Identity graph shows `main_cast_1` and `main_cast_2` (both "John Donaldson") merged via `name_containment` (0.85) + `spelling_variant` (0.65) + `cooccurrence` (0.83). NO constraint edge blocked this because the attempt 24 fix received empty `characters_present` lists.
- "Johnny" is a separate supporting character but should be recognized as the son's nickname.
- "John Donaldson's" (possessive) appears as an alias of the merged character — invalid.

**Sub-Dimension C: Alias Grouping: 5/10**

- "the father" correctly appears as alias of John Donaldson ✓
- "John Donaldson's" (possessive form) is an invalid alias ✗
- "Johnny" should be an alias of the son, not a separate character ✗
- Ted Frith has "Ted" alias ✓
- Uncle Bill has "Bill" alias ✓

### 2.3 Character Profiles: 5/10 ✗

All 6 characters have `physical_description: null` — zero physical descriptions. Only 3 characters have relationships (John Donaldson, Uncle Bill, Ted Frith). The profile data is sparse compared to attempt 23.

**John Donaldson relationships:**
- "John Donaldson (son)" → "parent" — correct for the father entity
- "Uncle Bill" → "victimizer" — WRONG. Uncle Bill is the father's cousin and lifelong friend. The father victimized HIMSELF through embezzlement, not Uncle Bill. ✗
- "Margaret Donaldson" → "spouse" — CORRECT ✓

**Uncle Bill relationships:**
- "John Donaldson (cousin)" → "family" — CORRECT ✓
- "John Donaldson Jr. (nephew)" → "family" — CORRECT conceptually (guardian of the son) ✓
- "John Donaldson Sr. (father of nephew)" → "ally" — acceptable ✓

**Ted Frith relationships:**
- "John Donaldson" → "ally" — reasonable ✓
- "Uncle Bill" → "acquaintance" — reasonable ✓

**Why 5/10:** Zero physical descriptions despite the text having clear descriptions (father: "big, athletic, grizzled chap"; son: "olive-skinned, with blue eyes and thick lashes"). The father/son conflation makes the single John Donaldson entry's profile misleading. Uncle Bill → "victimizer" is actively wrong.

### 2.4 Chapter Summaries: 7.5/10 ✗

**Chapter 1:** EXCELLENT quality. Correctly describes the letter from young John, Uncle Bill's memories, the financial scandal, the cousin relationship (CORRECT — "his late cousin"). The emotional arc is well-captured. `characters_present: ["Narrator"]` — acceptable but should use "Uncle Bill."

**Chapter 2:** Good overall but contains the recurring "sister" hallucination:
- Opens with: "his deceased sister's son" — WRONG. Uncle Bill is the father's COUSIN, not sister. Ch1 correctly says "cousin," and the book overview correctly says "cousin." Only Ch2 has this error.
- Otherwise excellent: covers Yale, fishing trip, WWI, Caporetto, Santa Angela pier reunion, deathbed revelation. Correctly tags "John Donaldson (the son)" and "John Donaldson (the father)" in characters_present.

**Book overview:** Excellent — accurate full narrative arc with correct family relationships.

**Why 7.5/10:** One factual error ("sister" instead of "cousin") in otherwise excellent summaries.

### 2.5 Pronunciation Guide: 5/10 ✗

30 entries, 25 with IPA. Severe false positive problem unchanged from attempt 23.

**Genuinely useful (8):** Caporetto, Piave, Solferino, Tagliamento, Bersagliari, Venetia, Guerre, Bordeaux — Italian/French geographic/military terms ✓

**Acceptable homographs (5):** live, minute, read, close, moderate — context-dependent pronunciation ✓

**False positives (17):**
- Standard names: Bill, Donaldson, Cross, Ted, Donaldson's, Joe, Barron, Frith, Johnny — common English names/words ✗
- Common English words: whippersnapper, thriftless, thickset, manliness, dum-dums, orderlies, mayn't, was ✗
- "was" is particularly egregious

**Why 5/10:** More than half the entries (17/30 = 57%) are false positives. The genuinely useful Italian/French terms are good, but noise overwhelms signal.

### 2.6 HTML Presentation: 7.5/10 ✗

**Good elements:**
- Navigation tabs functional ✓
- Book overview prominent, accurate, well-formatted ✓
- Chapter summaries well-formatted with character tags ✓
- Ch2 correctly tags "John Donaldson (the son)" and "John Donaldson (the father)" ✓
- Uncle Bill shown with narrator badge ✓
- Profile sections organized with evidence quotes ✓

**Issues:**
1. Only ONE John Donaldson character shown — no son profile exists ✗
2. "Red Cross" listed as supporting character ✗
3. "Johnny" listed as separate supporting character ✗
4. "John Donaldson's" (possessive) shown as alias ✗
5. Uncle Bill → John Donaldson relationship listed as "victimizer" ✗
6. Ch1 characters_present shows only "Narrator" instead of "Uncle Bill" ✗
7. No physical descriptions visible for any character ✗

**Why 7.5/10:** Functional and well-structured, but character data quality issues propagate to presentation.

## Overall Score Calculation

```
Overall = (7 × 0.20) + (5 × 0.25) + (5 × 0.15) + (7.5 × 0.20) + (5 × 0.10) + (7.5 × 0.10)
        = 1.40 + 1.25 + 0.75 + 1.50 + 0.50 + 0.75
        = 6.15
```

**Overall: 6.15/10**

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (user-configured, appropriate)
- Pipeline: V2 with Phase 2 graph-based identity resolution
- Identity graph: 11 nodes, 15 merge edges, 2 constraint edges → 6 groups
- Constraint edges only have `ambiguous_surname` type — NO `ROLE_CONFLICT` edge was created
- **Root cause confirmed:** `_get_chapters()` in `characters.py:707-726` returns StructuralElements with EMPTY `characters_present` lists. The disambiguated names ("John Donaldson (the son)", etc.) are populated only in `analyzer.py:_convert_structure()` AFTER character extraction completes.
- 81 LLM calls, 113K tokens, 0 retries
- No config changes recommended

## Current Issues (Priority Order)

### CRITICAL

1. **Father/son John Donaldson conflation — attempt 24 fix had no effect due to data flow bug** [Identity Resolution]
   - Problem: `main_cast_1` and `main_cast_2` (both "John Donaldson") merged. The attempt 24 fix added `collect_summary_disambiguation_evidence()` which correctly parses disambiguation labels from `characters_present`, but the StructuralElements passed to it have EMPTY `characters_present` lists.
   - Root cause: `_get_chapters()` in `src/agents/characters.py:707-726` creates StructuralElements from chapter_map without copying `characters_present`. The `characters_present` field is populated from summary data only during final assembly in `analyzer.py:_convert_structure()` (line 2608), which runs AFTER character extraction.
   - Evidence: Identity graph shows NO `ROLE_CONFLICT` constraint edges. Only `ambiguous_surname` constraints exist. Meanwhile, the final output's `characters_present` correctly has ["John Donaldson (the son)", "John Donaldson (the father)"].
   - Location: `src/agents/characters.py` — `_get_chapters()` method (line 707-726)
   - Fix: **`_get_chapters()` must populate `characters_present` on StructuralElements from the summary data.** The summary agent's output (available via `context.get_result("summaries")`) already has `characters_present` / `active_characters` on each summary object. The fix should:
     1. In `_get_chapters()`, also fetch the summary results
     2. Match chapters to summaries by index
     3. Copy `characters_present` from each summary onto the corresponding StructuralElement
     - This is the ONLY change needed — the existing `collect_summary_disambiguation_evidence()` will then work correctly since it already correctly parses the labels and adds ROLE_CONFLICT constraint edges.

### HIGH

2. **"Red Cross" extracted as character (organization)** [Completeness]
   - Problem: Red Cross is an organization, not a character. `supporting_3` with 4 mentions.
   - Location: `src/pipeline/character_extraction_v2/supporting.py` — organization filtering
   - Fix: Re-apply `_is_organization_name()` filter from attempt 3 (reverted with baseline).

3. **"Johnny" is a separate character instead of alias of the son** [Alias Grouping]
   - Problem: "Johnny" (`supporting_7`, 2 mentions) should be recognized as a diminutive of "John" and merged with the son character (once the son exists as a separate entity after fix #1).
   - Location: Identity graph alias detection — the graph should detect "Johnny" as a diminutive of "John/John Donaldson"
   - Fix: Once the father/son split is working, "Johnny" should merge into the son's character. May need an explicit diminutive detection rule (Johnny → John).

4. **Pronunciation: 17/30 entries are false positives (57%)** [Pronunciation]
   - Problem: Common names and words flagged unnecessarily. "was" is egregious.
   - Location: `src/pipeline/pronunciation_guide/proposers/`
   - Fix: Re-apply the 3 universal invariants from pre-revert fixes:
     1. Foreign proposer: merge COMMON_WORDS_WHITELIST into ENGLISH_EXCEPTIONS
     2. CMU proposer: add common English words to whitelist
     3. Character proposer: skip ANY name found in CMU dictionary

5. **Chapter 2 "sister" hallucination** [Summaries]
   - Problem: Ch2 says "his deceased sister's son" — Uncle Bill is the father's COUSIN, not the boy's uncle through a sister.
   - Evidence: Ch1 correctly says "his late cousin John". Overview correctly says "his cousin John". Only Ch2 has this error.
   - Location: `src/pipeline/chapter_summary/summarizer.py`
   - Fix: Consider cross-chapter consistency check or stronger prompt guidance.

### MEDIUM

6. **Zero physical descriptions for all characters** [Profiles]
   - Problem: All 6 characters have `physical_description: null` despite the text containing clear descriptions (father: "big, athletic, grizzled chap"; son: "olive-skinned, with blue eyes and thick lashes").
   - Evidence: `physical_description` is null for all 6 characters in analysis.json.
   - Location: `src/pipeline/character_profiling/` — profile extraction may be failing to populate this field
   - Fix: Check if physical_description extraction is working at all, or if it's a field mapping issue.

7. **Uncle Bill → John Donaldson relationship "victimizer"** [Profiles]
   - Problem: Uncle Bill is labeled as John Donaldson's "victimizer". He's actually his cousin and close friend.
   - Location: Relationship extraction — downstream of father/son conflation
   - Fix: Fixing #1 should partially fix this; the LLM may also need prompt improvement for relationship extraction.

8. **"John Donaldson's" (possessive) is an invalid alias** [Alias Grouping]
   - Problem: Possessive form appears as alias and in supporting cast.
   - Location: Supporting cast extraction or identity graph node creation
   - Fix: Strip possessive suffixes ('s) from candidate character names.

9. **Structure: 2 sections for continuous short story** [Structure]
   - Same as all prior attempts. Not worth fixing specifically for this text.

### LOW

10. **Ted Frith missing "Teddy" alias**
11. **Ch1 characters_present uses "Narrator" instead of "Uncle Bill"**
12. **Johnny has 0 context — no profile, no description**
13. **Margaret Donaldson missing from character list** — mentioned 2+ times as wife of John Donaldson father

## Fix History

### Attempt 24 — Summary-based disambiguation constraint (NO EFFECT)
- **Issue targeted:** CRITICAL #1 — Father/son John Donaldson conflation
- **Changes made:** Added `collect_summary_disambiguation_evidence()` to `evidence_collectors.py`; updated `collect_all_evidence()` to accept `chapter_summaries`; updated `characters.py` to pass chapters
- **Result:** NO CHANGE — The StructuralElements passed to the function had empty `characters_present` lists because they're populated later in the pipeline
- **Root cause:** Data flow ordering — `characters_present` is set in `analyzer.py:_convert_structure()` AFTER character extraction, not before
- **The function code itself is CORRECT** — it just receives empty input. The fix for attempt 25 is to populate `characters_present` on the StructuralElements from summary data in `_get_chapters()`.

### Attempt 23 — CLEAN BASELINE (all prior fixes reverted)
- Commit `f2a6ee5`: "Revert src/ to clean baseline (87d268d) - remove 23 attempts of american_sir fixes"
- Commit `48be828`: "Phase 2: Replace 7 sequential merge passes with graph-based identity resolution"
- Score: 6.30

### Previous attempts (1-22) — ALL REVERTED
- Key learnings:
  - Attempt 22: Deterministic disambiguation guard was reliable for father/son split
  - Attempt 3: Organization filtering successfully filtered Red Cross
  - Pronunciation false positive filtering with 3 universal invariants worked
  - Prompt-only approaches for father/son split failed consistently

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 24 | Father/son disambiguation | `evidence_collectors.py`, `characters.py` | NO EFFECT — StructuralElements had empty characters_present (data flow bug) |
| 23 (baseline) | Clean baseline + Phase 2 pipeline | N/A (all reverted) | Score: 6.30 |

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.60 | — | Original baseline |
| 22 | 7.55 | +0.95 | Best score (all fixes active) |
| 23 | 6.30 | -0.30 | Clean baseline + Phase 2 pipeline |
| 24 | 6.15 | -0.45 | Fix had no effect; profiles slightly worse (0 physical descriptions) |

## Next Action

**Phase:** awaiting_fix

**PRIORITY FIX ORDER:**

1. **Fix the data flow bug in `_get_chapters()`** (CRITICAL #1) — This is a SURGICAL fix:
   - In `_get_chapters()` (characters.py:707-726), also fetch summary data from context
   - Match summaries to chapters by index
   - Copy `characters_present` / `active_characters` from each summary onto the corresponding StructuralElement
   - The existing `collect_summary_disambiguation_evidence()` function will then work as designed
   - **Expected impact:** +1.5 on Characters (resolves false merge), +0.5 on Profiles, +0.5 on HTML

2. **Pronunciation false positive filtering** (HIGH #4) — Re-apply proven invariants. Expected: +2.0 on Pronunciation.

3. **Organization filtering** (HIGH #2) — Re-apply `_is_organization_name()`. Expected: +0.5 on Characters.

4. **Zero physical descriptions** (MEDIUM #6) — Investigate why all `physical_description` fields are null. This is a NEW regression not seen in attempt 23.

**Target:** Fix #1 alone should split the father/son, which cascades to improved profiles and presentation. Combined with #2 and #4, we should see significant movement toward passing scores.
