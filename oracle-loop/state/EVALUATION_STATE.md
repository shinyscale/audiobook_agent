# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 23
- **Phase:** awaiting_fix
- **baseline_score:** 6.60
- **Competitive Mode:** single (all stages: characters, structure, summaries)

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Pipeline Notes (Attempt 23)
- **CRITICAL CONTEXT:** All prior src/ fixes (attempts 1-22) were REVERTED via `f2a6ee5` ("Revert src/ to clean baseline"). This is a CLEAN BASELINE run with the new Phase 2 graph-based identity resolution pipeline.
- Analysis completed in 36m 40s using qwen3-next:80b-a3b-instruct-q8_0
- Found 7 characters total (3 main_cast, 4 supporting)
- Identity graph: 11 nodes, 9 merge edges, 2 constraint edges → 7 groups
- No merge decisions recorded (0 total merges)
- 31 pronunciation entries, 26 with IPA
- "Red Cross" extracted as character (organization, should be filtered)
- "Johnny" extracted as separate supporting character (should be alias of John Donaldson the son)
- "John Donaldson's" appears in aliases (possessive form, invalid alias)
- Father/son split is ABSENT — only one "John Donaldson" exists (the father)

## Latest Scores
- Structure Detection: 7/10 ✗
- Character Extraction: 5/10 ✗
  - Completeness: 6/10
  - Identity Resolution: 4/10
  - Alias Grouping: 5/10
- Character Profiles: 6/10 ✗
- Chapter Summaries: 7.5/10 ✗
- Pronunciation Guide: 5/10 ✗
- HTML Presentation: 7.5/10 ✗
- **Overall: 6.23/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (6 categories below threshold)

## Detailed Evaluation

### 2.1 Structure Detection: 7/10 ✗

"American, Sir" is a continuous short story with no explicit chapter markers. The tool produces 2 sections, both with null titles and null start/end lines. For a continuous text with no structural markers, 1 section would be more accurate (score 9-10 per rubric), but 2 is a structural error per the rubric's short story guidance ("Artificially splitting a continuous text into multiple sections is a structural error, score 6-7"). The 2-section output is somewhat functional since the summaries for each section are coherent, but the split is artificial.

**Issues:**
- 2 sections instead of 1 for a continuous short story
- Both sections have null titles (displayed as "Chapter 1" and "Chapter 2")
- Both sections have null start/end line positions

### 2.2 Character Extraction: 5/10 ✗ (MAJOR REGRESSION from attempt 22's 8/10)

**This regression is EXPECTED** — all prior fixes were reverted to clean baseline. The Phase 2 graph-based identity resolution pipeline is now in use, but it lacks the deterministic disambiguation guard that was critical for the father/son split.

**Sub-Dimension A: Completeness: 6/10**

Characters present:
- John Donaldson (the father): 29 mentions, `main_cast_2` — CORRECT but missing son disambiguation
- Uncle Bill: 18 mentions, `main_cast_3`, narrator=true, role=protagonist — CORRECT ✓
- Margaret Donaldson: 2 mentions, `main_cast_4` — CORRECT ✓
- Joe Barron: 3 mentions, `supporting_1` — CORRECT ✓
- Red Cross: 4 mentions, `supporting_2` — WRONG (organization, not character) ✗
- Ted Frith: 5 mentions, `supporting_4`, alias "Ted" — CORRECT ✓
- Johnny: 2 mentions, `supporting_6` — FRAGMENTED (should be alias of John Donaldson the son) ✗

**Missing:** John Donaldson (the son) — the MOST IMPORTANT character alongside the father. He is the story's emotional center: the boy who writes to Uncle Bill, grows up under his care, fights in WWI, and discovers his long-lost father on the battlefield. His absence is a critical extraction failure.

**Hallucinated/Invalid:** Red Cross is an organization, not a character.

**Sub-Dimension B: Identity Resolution: 4/10**

- **CRITICAL false merge:** Father and son John Donaldson conflated into one character. The identity graph shows `main_cast_1` ("John Donaldson", 9 mentions) and `main_cast_2` ("John Donaldson", 29 mentions) were merged via `name_containment` (weight 0.85) and `co-occurrence` (weight 0.5). These are TWO DIFFERENT PEOPLE — father and son sharing the same name. The father is a disgraced embezzler who faked his death; the son is a brave WWI volunteer. The graph-based resolution correctly detected same-name containment but had no way to BLOCK the merge for same-name disambiguation.
- "Johnny" is a separate supporting character but should be recognized as the son's nickname and merged with the son character (if the son existed as a separate entity).
- "John Donaldson's" (possessive) appears as an alias of the merged character — invalid.

**Sub-Dimension C: Alias Grouping: 5/10**

- "the father" correctly appears as alias of John Donaldson — this is appropriate since the story explicitly calls him "the father"
- "John Donaldson's" (possessive form) is an invalid alias ✗
- "Johnny" should be an alias of the son, not a separate character ✗
- Ted Frith has "Ted" alias ✓, but "Teddy" is missing
- Uncle Bill has "Bill" alias ✓
- No aliases for Margaret Donaldson (acceptable given low mention count)

### 2.3 Character Profiles: 6/10 ✗

Only 3 characters have profiles: John Donaldson (father), Uncle Bill, and Ted Frith. The profiles are well-structured with appearance, personality, and voice guidance, but the CONTENT is problematic due to the father/son merge.

**John Donaldson (father) profile:**
- Appearance: "striking physical resemblance to his son—olive-skinned, with blue eyes and thick lashes" — this actually describes the SON's appearance. The text says the father is "big, athletic, grizzled chap, maybe fifty-five or over." Profile contamination from father/son merge.
- Personality: "morally ambiguous man who committed financial betrayal" — CORRECT for the father
- Voice: "worn by time and guilt—calm, deliberate" — reasonable for the father
- Relationships: Uncle Bill listed as "enemy" — WRONG. Uncle Bill is the father's cousin and friend (though disappointed in him). "John Donaldson Jr." as child — this is correct but confusing since the system only has one John Donaldson entity.

**Uncle Bill profile:**
- Appearance: "elderly, grizzled, small man with stern but dignified presence" — mostly accurate
- Personality: "profoundly principled and quietly heroic protagonist" — excellent ✓
- Voice: "low, measured, restrained baritone" — excellent ✓
- Relationships: INCORRECT — lists "John Donaldson (son)" as "family (parent)", "John Donaldson Jr. (grandson)" as "family (grandparent)", "John Donaldson Sr. (father-in-law)" as "ally". Uncle Bill is the COUSIN of John Donaldson the father, and acts as guardian/mentor to the son. He is NOT a parent, grandparent, or in-law.
- Narrative role: "First-Person narrator" — CORRECT ✓

**Ted Frith profile:**
- Appearance: "looks natural, especially in his eyes, wears American uniform with tin derby" — accurate ✓
- Personality: "heroic figure whose selfless actions under fire" — accurate ✓
- Voice: "warm, grounded, quietly determined" — reasonable ✓

**Why 6/10:** The father's profile is contaminated with the son's physical description. Uncle Bill's relationships are almost entirely wrong. The SON has no profile at all since he doesn't exist as a character. These are significant issues for narrator preparation.

### 2.4 Chapter Summaries: 7.5/10 ✗

**Chapter 1:** EXCELLENT quality. Correctly describes: the letter from young John, Uncle Bill's initial resistance, memories of "his late cousin John" (CORRECT family relationship), the financial scandal, the death, Margaret's letter, the emotional aftermath. `characters_present: ["Narrator"]` — acceptable but should use "Uncle Bill" rather than generic "Narrator".

**Chapter 2:** Good overall quality but contains the recurring "sister" hallucination:
- Opens with: "Ten years after receiving a letter asking him to take in his **deceased sister's son**"
- This is WRONG — Uncle Bill is the father's COUSIN, not his sister's son's guardian. Chapter 1 correctly says "his late cousin John." The book overview correctly says "his cousin John." Only Ch2 has this error.
- Otherwise excellent: covers Yale, fishing trip, WWI, Caporetto, Santa Angela pier reunion, the father's deathbed revelation. `characters_present` correctly lists "Uncle Bill", "John Donaldson (the son)", "John Donaldson (the father)" as disambiguated entities — ironically, the summary pipeline disambiguates them correctly even though the character extraction pipeline doesn't.

**Book overview:** EXCELLENT — accurately captures the full narrative arc with correct family relationships ("his cousin John").

**Why 7.5/10:** One factual error ("sister" instead of "cousin") in Ch2 in otherwise excellent summaries.

### 2.5 Pronunciation Guide: 5/10 ✗

31 entries, 26 with IPA. Severe false positive problem:

**Genuinely useful (8):** Caporetto, Piave, Solferino, Tagliamento, Bersagliari, Venetia, Guerre, Bordeaux — Italian/French geographic/military terms ✓

**Acceptable homographs (5):** live, minute, read, close, moderate — context-dependent pronunciation ✓

**False positives (18):**
- Standard names: Bill, Donaldson, Cross, Ted, Donaldson's, Joe, Barron, Frith, Margaret, Johnny — these are common English names/words that any narrator would know ✗
- Common English words: whippersnapper, thriftless, thickset, manliness, dum-dums, orderlies, mayn't, was — standard vocabulary ✗
- "was" is particularly egregious

**Why 5/10:** More than half the entries (18/31 = 58%) are false positives. The genuinely useful Italian/French terms are good, but the noise overwhelms the signal. A narrator would have to wade through 18 false alarms to find 13 useful entries.

### 2.6 HTML Presentation: 7.5/10 ✗

**Good elements:**
- Navigation tabs functional ✓
- Book overview prominent, accurate, and well-formatted ✓
- Chapter summaries well-formatted with character tags ✓
- Ch2 correctly tags "John Donaldson (the son)" and "John Donaldson (the father)" in characters_present ✓
- Uncle Bill correctly shown with narrator badge and protagonist tag ✓
- Profile sections well-organized with appearance, personality, voice guidance, evidence ✓

**Issues:**
1. Only ONE John Donaldson character shown — no son profile exists ✗
2. John Donaldson's profile describes the FATHER but the appearance section describes the SON (contamination) ✗
3. "Red Cross" listed as supporting character ✗
4. "Johnny" listed as separate supporting character instead of being linked to the son ✗
5. Uncle Bill's relationships section shows INCORRECT family relationships (parent, grandparent, father-in-law) ✗
6. John Donaldson's relationships show Uncle Bill as "enemy" ✗
7. "John Donaldson's" (possessive) shown as an alias ✗
8. Ch1 `characters_present` shows only "Narrator" instead of "Uncle Bill" ✗

**Why 7.5/10:** The report is functional and well-structured, but the character data quality issues (from upstream extraction failures) propagate to the presentation layer. The profile contamination and wrong relationships would actively mislead a narrator.

## Overall Score Calculation

```
Overall = (7 × 0.20) + (5 × 0.25) + (6 × 0.15) + (7.5 × 0.20) + (5 × 0.10) + (7.5 × 0.10)
        = 1.40 + 1.25 + 0.90 + 1.50 + 0.50 + 0.75
        = 6.30
```

**Overall: 6.30/10** (DOWN from 7.55 in attempt 22 — this is expected since all fixes were reverted)

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (user-configured, appropriate)
- Pipeline: V2 with Phase 2 graph-based identity resolution (NEW — replaced 7 sequential merge passes)
- Identity graph produced 11 nodes, 9 merge edges, 2 constraint edges → 7 groups
- Constraint edges correctly identified John Donaldson vs Margaret Donaldson as different people (different first names)
- BUT no constraint edge blocked the father/son merge because both have the SAME name
- Total analysis time: ~37m
- 100 LLM calls, 133K tokens
- No LLM retries (good)
- 0 merge decisions recorded — the graph-based pipeline doesn't use the old merge decision framework
- No config changes recommended

## Current Issues (Priority Order)

### CRITICAL

1. **Father/son John Donaldson conflation — graph-based pipeline lacks same-name disambiguation** [Identity Resolution]
   - Problem: `main_cast_1` ("John Donaldson", 9 mentions) and `main_cast_2` ("John Donaldson", 29 mentions) were merged via `name_containment` (weight 0.85). These are TWO DIFFERENT PEOPLE — father and son.
   - Evidence: Ch2 summary correctly disambiguates "John Donaldson (the son)" and "John Donaldson (the father)". The book overview describes both as separate people. The identity graph has no mechanism to BLOCK a merge when two nodes have identical names but are different people.
   - Root cause: The Phase 2 graph-based identity resolution merges nodes based on name similarity, spelling variants, and co-occurrence — but has NO constraint edge type for "same name, different person." The old pipeline had a deterministic guard (attempt 22's fix) but it was reverted with the clean baseline.
   - Location: The graph-based identity resolution pipeline (likely in `src/pipeline/character_extraction_v2/` or wherever the Phase 2 code lives)
   - Fix approach: Add a **same-name disambiguation constraint** to the identity graph. When chapter summaries identify two instances of the same name with different disambiguation labels (e.g., "John Donaldson (the son)" vs "John Donaldson (the father)"), add a `different_person` constraint edge that BLOCKS the merge. This uses the summary data as an upstream signal — the summaries already correctly disambiguate.
   - **Alternative approach:** Re-apply the deterministic disambiguation label guard from attempt 22 to the Phase 2 pipeline's merge resolution step: if two nodes have parenthesized disambiguation labels with different label text, block the merge.

### HIGH

2. **"Red Cross" extracted as character (organization)** [Completeness]
   - Problem: Red Cross is an organization, not a character. It has 4 mentions and `supporting_2` ID.
   - Evidence: Red Cross is a humanitarian aid organization, not a person.
   - Location: `src/pipeline/character_extraction_v2/supporting.py` — organization filtering
   - Fix: The `_is_organization_name()` filter (added in attempt 3 but reverted) needs to be re-applied. It used universal org indicators (e.g., words like "Cross", "Society", "Association" combined with capitalization patterns).

3. **"Johnny" is a separate character instead of alias** [Alias Grouping]
   - Problem: "Johnny" (supporting_6, 2 mentions) is a separate character but should be recognized as a nickname of the son.
   - Evidence: In the story, "Johnny" is used as an affectionate name for young John Donaldson.
   - Location: Supporting cast alias merging or identity graph alias detection
   - Fix: The identity graph should detect that "Johnny" is a diminutive of "John" and merge it into the John Donaldson character (or, once the son is split out, into the son's character).

4. **Pronunciation: 18/31 entries are false positives (58%)** [Pronunciation]
   - Problem: Common names (Bill, Ted, Joe, Margaret, Donaldson, Barron, Frith, Johnny, Cross, Donaldson's) and common words (whippersnapper, thriftless, thickset, manliness, dum-dums, orderlies, mayn't, was) flagged unnecessarily.
   - Evidence: "was" is a word every English speaker knows. "Bill" is one of the most common English names. These are not pronunciation challenges.
   - Location: `src/pipeline/pronunciation_guide/proposers/` — character_proposer.py (names), cmu_proposer.py (common words), foreign_proposer.py ("was" flagged as foreign)
   - Fix: The attempt 23 fix (3 universal invariants) was reverted with the clean baseline. Re-apply:
     1. Foreign proposer: merge COMMON_WORDS_WHITELIST into ENGLISH_EXCEPTIONS
     2. CMU proposer: add common English words to whitelist
     3. Character proposer: skip ANY name found in CMU dictionary (not just <=4 chars)

5. **Chapter 2 "sister" hallucination** [Summaries]
   - Problem: Ch2 says "his deceased sister's son" — Uncle Bill is the father's COUSIN, not the boy's uncle by blood through a sister.
   - Evidence: Ch1 correctly says "his late cousin John". The overview correctly says "his cousin John". Only Ch2 has this error.
   - Location: `src/pipeline/chapter_summary/summarizer.py`
   - Fix: Need a deterministic post-generation check or stronger prompt guidance to ensure family relationship consistency across chapters.

### MEDIUM

6. **Uncle Bill's relationships are wrong** [Profiles]
   - Problem: Listed as parent of "John Donaldson (son)", grandparent of "John Donaldson Jr. (grandson)", ally of "John Donaldson Sr. (father-in-law)". Uncle Bill is the COUSIN of the father, and guardian/mentor to the son.
   - Location: Profile generation / relationship extraction
   - Fix: This is partially downstream of the father/son conflation — fixing #1 should improve this.

7. **John Donaldson's profile has contaminated appearance** [Profiles]
   - Problem: Appearance says "olive-skinned, with blue eyes and thick lashes" — this describes the SON. The father is "big, athletic, grizzled chap, maybe fifty-five or over."
   - Location: Profile generation, downstream of father/son conflation
   - Fix: Fixing #1 (father/son split) would naturally fix this by giving each character their own passages.

8. **"John Donaldson's" (possessive) is an invalid alias** [Alias Grouping]
   - Problem: Possessive form "John Donaldson's" appears as alias and in supporting cast pre-merge
   - Location: Supporting cast extraction or identity graph node creation
   - Fix: Strip possessive suffixes ('s) from candidate character names before adding to graph.

9. **Structure: 2 sections for continuous short story** [Structure]
   - Same as all prior attempts. Not worth fixing specifically for this text.

10. **Uncle Bill → John Donaldson relationship listed as "enemy"** [Profiles]
    - Problem: Uncle Bill is labeled as John Donaldson's "enemy". He's actually his cousin and close friend (though deeply disappointed).
    - Location: Relationship extraction
    - Fix: Downstream of father/son conflation + LLM relationship inference quality.

### LOW

11. **Ted Frith missing "Teddy" alias**
12. **Margaret Donaldson promoted to main_cast** — 2 mentions should be supporting
13. **Ch1 characters_present uses "Narrator" instead of "Uncle Bill"**
14. **Johnny has 0 context — no profile, no description, low confidence**

## Fix History

### Attempt 24 — Summary-based disambiguation constraint
- **Issue fixed:** CRITICAL #1 — Father/son John Donaldson conflation
- **Root cause:** Phase 2 identity graph lacked constraint edges for same-name disambiguation
- **Data flow:** Chapter summaries correctly distinguish "John Donaldson (the son)" vs "John Donaldson (the father)" in `characters_present`, but this signal wasn't being used to block merges
- **Fix location:** `src/pipeline/character_extraction_v2/evidence_collectors.py`
- **Changes:**
  1. Added `collect_summary_disambiguation_evidence()` — new constraint collector that:
     - Parses disambiguation labels from `characters_present` (e.g., "(the son)", "(the father)")
     - When two graph nodes have same base name but different labels, adds ROLE_CONFLICT constraint edge (strength=1.0)
  2. Updated `collect_all_evidence()` to accept and use `chapter_summaries` parameter
  3. Updated `src/agents/characters.py` to pass chapter StructuralElements to evidence collectors
- **Smoke test:** PASS — Correctly added constraint edge between two "John Donaldson" nodes when summaries have different labels
- **Full test suite:** PASS — 336 passed, 10 skipped
- **Expected impact:** +1.5 on Characters (resolves false merge), +0.5 on Profiles (uncontaminates father's profile), +0.5 on HTML (shows both characters correctly)

### Attempt 23 — CLEAN BASELINE (all prior fixes reverted)
- Commit `f2a6ee5`: "Revert src/ to clean baseline (87d268d) - remove 23 attempts of american_sir fixes"
- Commit `48be828`: "Phase 2: Replace 7 sequential merge passes with graph-based identity resolution"
- This is a fresh run on the NEW Phase 2 graph-based identity resolution pipeline
- All fixes from attempts 1-22 are gone
- Score: 6.30 (down from 7.55 in attempt 22, but expected)

### Previous attempts (1-22) — ALL REVERTED
- See git history for details. Key learnings:
  - Attempt 22: Deterministic disambiguation guard in Pass 2 was the ONLY reliable fix for father/son split
  - Attempt 3: Organization filtering (`_is_organization_name()`) successfully filtered Red Cross
  - Attempt 23 pre-revert: Pronunciation false positive filtering with 3 universal invariants worked
  - Prompt-only approaches for father/son split failed consistently (LLM nondeterminism)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 24 | Father/son disambiguation | `evidence_collectors.py`, `characters.py` | Awaiting analysis — added constraint edge for summary-disambiguated same-name characters |
| 23 (baseline) | Clean baseline + Phase 2 pipeline | N/A (all reverted) | Score: 6.30 — father/son merged, Red Cross back, pronunciation FPs back |

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.60 | — | Original baseline |
| 22 | 7.55 | +0.95 | Best score (all fixes active) |
| 23 | 6.30 | -0.30 | Clean baseline + Phase 2 pipeline |

## Next Action

**Phase:** awaiting_analysis

**PRIORITY FIX ORDER:**

The fix phase should re-apply proven fixes from the previous attempts adapted to the new Phase 2 graph-based pipeline:

1. **Father/son disambiguation** (CRITICAL #1) — Adapt the attempt 22 deterministic guard to the Phase 2 graph pipeline. Add a `different_person` constraint edge when chapter summaries disambiguate same-name characters with different labels. This is the highest-impact fix (+1.5 expected across Characters, Profiles, Presentation).

2. **Pronunciation false positive filtering** (HIGH #4) — Re-apply the 3 universal invariants from attempt 23's fix to the pronunciation proposers. This was proven to work before the revert. Expected impact: +2.0 on Pronunciation.

3. **Organization filtering** (HIGH #2) — Re-apply `_is_organization_name()` to filter Red Cross and similar entities. Expected impact: +0.5 on Characters.

4. **Summary "sister" hallucination** (HIGH #5) — This has been persistent across many attempts. Consider a deterministic post-generation relationship consistency check.

**Target:** Fix #1 and #2 alone should bring Characters to ~7-8 and Pronunciation to ~8, which would significantly close the gap to passing.
