# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 25
- **Phase:** awaiting_fix
- **baseline_score:** 6.60
- **Competitive Mode:** single (all stages: characters, structure, summaries)

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Latest Scores
- Structure Detection: 7/10 ✗
- Character Extraction: 6/10 ✗
  - Completeness: 7/10
  - Identity Resolution: 5/10
  - Alias Grouping: 6/10
- Character Profiles: 6/10 ✗
- Chapter Summaries: 7.5/10 ✗
- Pronunciation Guide: 5/10 ✗
- HTML Presentation: 7/10 ✗
- **Overall: 6.40/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (6 categories below threshold)

## Detailed Evaluation

### 2.1 Structure Detection: 7/10 ✗

"American, Sir" is a continuous short story with no chapter markers. The tool produces 2 sections, both with null titles and null start/end lines. Per the rubric, a continuous text should be identified as a single section (9-10); splitting into 2 sections is a structural error (6-7). Score 7 because the summaries for each section are coherent and usable despite the artificial split.

**Unchanged from attempt 24.**

### 2.2 Character Extraction: 6/10 ✗ (UP from 5 in attempt 24)

**The `role_conflict` constraint edge is now working!** The identity graph correctly shows a constraint edge between `main_cast_1` and `main_cast_2`: "Summary disambiguates 'John Donaldson': 2 distinct people with labels ['the son', 'the father']". This successfully prevented the father/son merge. **Major improvement.**

However, the split has significant quality problems that prevent a higher score.

**Sub-Dimension A: Completeness: 7/10** (UP from 6)

Characters present (8 total, up from 6):
- `main_cast_1`: John Donaldson — 9 mentions, `is_narrator: true`, role: `supporting` — intended as the FATHER
- `main_cast_2`: John Donaldson — 28 mentions, aliases: ["John", "John Donaldson's"], role: `antagonist` — unclear if father or son
- `main_cast_3`: Margaret Donaldson — 2 mentions — NEW, CORRECT ✓
- `supporting_1`: Uncle Bill — 18 mentions, alias: "Bill" — CORRECT ✓
- `supporting_3`: Joe Barron — 3 mentions — CORRECT ✓
- `supporting_4`: Red Cross — 4 mentions — WRONG (organization, not character) ✗
- `supporting_6`: Ted Frith — 5 mentions, alias: "Ted" — CORRECT ✓
- `supporting_8`: Johnny — 2 mentions — FRAGMENTED (should be alias of the son) ✗

**Improvements:** Margaret Donaldson now appears as a character (was missing). Two John Donaldson entries exist (father/son split working).

**Remaining issues:** Red Cross is an organization. Johnny should be an alias of the son, not separate.

**Sub-Dimension B: Identity Resolution: 5/10** (UP from 4)

The father/son split is working — the constraint edge successfully blocks the merge. This is a major improvement. However:

1. **Both entries are named identically "John Donaldson"** — a narrator seeing two entries with the same canonical name and no disambiguating labels would be confused. They need labels like "John Donaldson (the father)" and "John Donaldson (the son)".
2. **"John" (supporting_0) merged into `main_cast_2`** — but in the text, "John" predominantly refers to the SON, not the father. The identity graph merged "John" into `main_cast_2` (28 mentions, role: antagonist). It's unclear which John Donaldson this actually represents.
3. **`main_cast_1` (9 mentions) is labeled `is_narrator: true`** — WRONG. Uncle Bill is the story's narrator. The father never narrates.
4. **Roles are wrong:** `main_cast_1` is "supporting" and `main_cast_2` is "antagonist". The father is neither purely an antagonist nor merely supporting — he's the story's tragic hero. The son is the protagonist.
5. **"Johnny" still separate** — should be alias of the son.

**Sub-Dimension C: Alias Grouping: 6/10** (UP from 5)

- "John Donaldson's" (possessive) still appears as an alias of `main_cast_2` ✗
- "John" merged into `main_cast_2` — ambiguous, could be either father or son ✗
- "Johnny" should be alias of son character ✗
- Ted → Ted Frith: correct ✓
- Bill → Uncle Bill: correct ✓
- Margaret Donaldson: separate entity, correct ✓

### 2.3 Character Profiles: 6/10 ✗ (UP from 5)

**Major improvement:** Both John Donaldson entries now have rich profiles in the HTML report:
- Appearance: "An elderly, grizzled American man in shabby clothing" — describes the FATHER accurately ✓
- Personality: "committed serious financial crimes and fled justice but redeemed himself" — FATHER ✓
- Voice guidance: "calm, weathered voice with deep emotional restraint" — FATHER ✓
- Dialect: "American English with a faint foreign inflection from long residence in Italy" — FATHER ✓
- Example quotes: "'American, sir,' he said proudly" — FATHER ✓

**However, both entries have IDENTICAL profiles.** `main_cast_1` and `main_cast_2` show the exact same appearance, personality, voice guidance, and quotes. This means:
1. The SON has no distinct profile — he should be young, idealistic, a soldier
2. The father's profile is duplicated to an entry that may represent the son
3. `physical_description` is null in analysis.json for ALL characters (the rich profiles appear only in the HTML via the profiling pipeline, not in the JSON field)

**Relationships:**
- Both John Donaldsons: `Uncle Bill: "family (child)"` and `John Donaldson (father): "family (parent)"` — this is the SON's relationships applied to both entries ✗
- Uncle Bill → John Donaldson: "mentor" — CORRECT ✓ (Uncle Bill mentors the son)
- Ted Frith → John Donaldson: "ally" — reasonable ✓

**Why 6/10:** Profiles now exist with good quality for the father, but they're duplicated across both entries and the son gets no distinct profile. The "victimizer" relationship from attempt 24 is gone (replaced with "mentor"), which is an improvement.

### 2.4 Chapter Summaries: 7.5/10 ✗

**Chapter 1 (section 1):** EXCELLENT. Correctly describes the letter, Uncle Bill's memories, the cousin relationship, the scandal, Margaret Donaldson. `characters_present: ["Narrator"]` — acceptable but "Uncle Bill" would be better.

**Chapter 2 (section 2):** Good quality but contains the recurring "sister" hallucination:
- "his deceased sister's twelve-year-old son" — WRONG. Uncle Bill is the father's COUSIN, not John's uncle through a sister. Ch1 correctly says "cousin." The book overview correctly says "cousin." Only Ch2 has this error.
- Otherwise excellent: covers Yale, fishing trip, WWI, Caporetto, Santa Angela pier reunion, deathbed revelation.
- `characters_present`: ["Uncle Bill", "John Donaldson (the son)", "John Donaldson (the father)"] — CORRECT and shows the disambiguation labels working ✓

**Book overview (plot_summary):** EXCELLENT — accurate full narrative arc with correct family relationships ("beloved cousin"). Well-structured three-paragraph overview.

**Why 7.5/10:** One factual error ("sister" instead of "cousin" in Ch2) in otherwise excellent summaries.

### 2.5 Pronunciation Guide: 5/10 ✗

31 entries, 26 with IPA. Same severe false positive problem as all prior attempts.

**Genuinely useful (8):** Caporetto, Piave, Solferino, Tagliamento, Bersagliari, Venetia, Guerre, Bordeaux — Italian/French geographic/military terms ✓

**Acceptable homographs (5):** live, minute, read, close, moderate — context-dependent pronunciation ✓

**False positives (18):**
- Standard names: Bill, Donaldson, Cross, Ted, Donaldson's, Joe, Barron, Frith, Margaret, Johnny — common English names ✗
- Common English words: whippersnapper, thriftless, thickset, manliness, dum-dums, orderlies, mayn't, was ✗
- "was" is particularly egregious — one of the most common English words

**Why 5/10:** 18/31 entries (58%) are false positives. The genuinely useful Italian/French terms are good, but noise overwhelms signal.

### 2.6 HTML Presentation: 7/10 ✗ (DOWN from 7.5)

**Good elements:**
- Navigation tabs functional ✓
- Book overview prominent, accurate, well-formatted ✓
- Chapter summaries well-formatted with character tags ✓
- Ch2 correctly tags "John Donaldson (the son)" and "John Donaldson (the father)" ✓
- Profile sections organized with evidence quotes ✓

**Issues:**
1. TWO "John Donaldson" entries with NO distinguishing labels — a narrator would have no idea which is which ✗
2. Both entries have IDENTICAL profiles (same appearance, personality, quotes) — confusing and unhelpful ✗
3. `main_cast_1` labeled "supporting" + narrator badge; `main_cast_2` labeled "antagonist" — wrong roles ✗
4. "Red Cross" listed as supporting character ✗
5. "Johnny" listed as separate supporting character ✗
6. "John Donaldson's" (possessive) shown as alias ✗
7. `main_cast_1` narrator badge says "Secondary narrator (nested narrative)" — the father does speak in first person briefly at the end, but is NOT a narrator of the story ✗
8. Ch1 `characters_present` shows only "Narrator" instead of "Uncle Bill" ✗

**Why 7/10:** Two identically-named entries with identical profiles is more confusing than the previous single entry. The structural layout is good but data quality issues propagate badly.

## Overall Score Calculation

```
Overall = (7 × 0.20) + (6 × 0.25) + (6 × 0.15) + (7.5 × 0.20) + (5 × 0.10) + (7 × 0.10)
        = 1.40 + 1.50 + 0.90 + 1.50 + 0.50 + 0.70
        = 6.50
```

**Overall: 6.50/10**

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (user-configured, appropriate)
- Pipeline: V2 with Phase 2 graph-based identity resolution
- Identity graph: 12 nodes, 15 merge edges, 5 constraint edges → 8 groups
- **NEW constraint edge working:** `role_conflict` between `main_cast_1` and `main_cast_2` with strength 1.0 — "Summary disambiguates 'John Donaldson': 2 distinct people with labels ['the son', 'the father']"
- `main_cast_2` group absorbed `supporting_0` ("John") and `supporting_5` ("John Donaldson's") — 1 constraint override
- 65 LLM calls, 102K tokens, 0 retries
- No config changes recommended

## Current Issues (Priority Order)

### CRITICAL

1. **Two identical "John Donaldson" entries with no disambiguation labels** [Identity Resolution]
   - Problem: Both `main_cast_1` and `main_cast_2` have canonical_name "John Donaldson" with no way for a narrator to tell them apart. The character split worked at the graph level, but the output doesn't communicate WHICH entry is the father vs. the son.
   - Evidence: Both entries show identical profiles (same appearance, personality, voice guidance, relationships). The summaries DO have disambiguation labels ("the son", "the father") in `characters_present`, but the character entries themselves don't use these labels.
   - Location: The disambiguation labels exist in the summary data. The issue is that the character entries don't incorporate these labels into their `canonical_name` or provide any other distinguishing information.
   - Fix approach: When two characters share the exact same canonical name and were kept separate by a `role_conflict` constraint edge, append the disambiguation labels from the summary data. For example: "John Donaldson (the father)" and "John Donaldson (the son)". The labels are already available — they were extracted from `characters_present` in the summaries. This likely needs to happen in the character agent after graph resolution, when finalizing the character list.
   - Files to investigate: `src/agents/characters.py` — after merge groups are finalized, check for duplicate canonical names and apply disambiguation labels from the constraint edge reason field (which contains "labels ['the son', 'the father']").

2. **Both entries have identical profiles — son has no distinct profile** [Profiles]
   - Problem: The profiling pipeline assigned the FATHER's profile to BOTH entries. The son should have a distinct profile: young, idealistic, enlisted as ambulance driver, went to Yale.
   - Root cause: Since both entries have the same canonical name, the profiling pipeline likely gathered the same evidence passages for both and generated identical profiles.
   - Dependency: This will likely resolve itself once issue #1 is fixed (distinct names → distinct passage gathering → distinct profiles).

### HIGH

3. **Wrong narrator assignment — `main_cast_1` marked as narrator instead of Uncle Bill** [Identity Resolution]
   - Problem: `main_cast_1` (John Donaldson, 9 mentions) has `is_narrator: true`. Uncle Bill narrates the story in first person. The father speaks briefly at the end but is NOT the narrator.
   - Evidence: Uncle Bill has `is_narrator: false` and role: "minor". The story begins "I did not know that I had an Uncle Bill..." from Uncle Bill's perspective.
   - Location: Narrator detection logic — may be confused because the father speaks in first person during the battlefield scene.
   - This was wrong in attempt 24 too (Uncle Bill had `is_narrator: true` there). Now it's moved to the wrong John Donaldson.

4. **"Red Cross" extracted as character (organization)** [Completeness]
   - Problem: Red Cross is an organization, not a character. `supporting_4` with 4 mentions.
   - Location: `src/pipeline/character_extraction_v2/supporting.py` — organization filtering
   - Fix: Add organization detection that filters out well-known organizations (Red Cross, United Nations, etc.) via prompt guidance or a simple check.

5. **"Johnny" is a separate character instead of alias of the son** [Alias Grouping]
   - Problem: "Johnny" (`supporting_8`, 2 mentions) should be recognized as a diminutive of "John" and merged with the son character.
   - Location: Identity graph alias detection — "Johnny" → "John" is a standard English diminutive not currently detected.
   - Dependency: Once issue #1 gives the son a distinct name, "Johnny" should merge into that entry. May need an explicit diminutive detection rule.

6. **Pronunciation: 18/31 entries are false positives (58%)** [Pronunciation]
   - Problem: Common names and words flagged unnecessarily. "was", "Bill", "Joe", "Ted", "Margaret" etc. are not pronunciation challenges.
   - Location: `src/pipeline/pronunciation_guide/proposers/`
   - Fix: Three universal invariants needed:
     1. Foreign proposer: merge COMMON_WORDS_WHITELIST into ENGLISH_EXCEPTIONS
     2. CMU proposer: add common English words to whitelist
     3. Character proposer: skip names found in CMU dictionary

7. **Chapter 2 "sister" hallucination** [Summaries]
   - Problem: Ch2 says "his deceased sister's twelve-year-old son" — Uncle Bill is the father's COUSIN, not brother. Ch1 and the book overview correctly say "cousin."
   - Location: `src/pipeline/chapter_summary/summarizer.py`
   - Fix: Consider cross-chapter consistency check or stronger prompt guidance.

### MEDIUM

8. **"John Donaldson's" (possessive) is an invalid alias** [Alias Grouping]
   - Problem: Possessive form appears as alias of `main_cast_2`.
   - Location: Supporting cast extraction or identity graph node creation
   - Fix: Strip possessive suffixes ('s) from candidate character names before adding as nodes.

9. **Roles incorrect for both John Donaldson entries** [Identity Resolution]
   - Problem: `main_cast_1` is "supporting", `main_cast_2` is "antagonist". Neither role is appropriate — the father is a tragic figure, the son is the protagonist.
   - Dependency: May resolve with disambiguation labels (issue #1).

10. **Uncle Bill role is "minor"** [Completeness]
    - Problem: Uncle Bill is the narrator and a central character, not "minor." He should be "protagonist" or at least "major."
    - Location: Role assignment logic

11. **Structure: 2 sections for continuous short story** [Structure]
    - Same as all prior attempts. Not worth a targeted fix for this text alone.

### LOW

12. **Ted Frith missing "Teddy" alias** — if present in text
13. **Ch1 `characters_present` uses "Narrator" instead of "Uncle Bill"**
14. **Margaret Donaldson has no relationships defined** — should be "wife of John Donaldson (the father)"

## Fix History

### Attempt 25 — Populate characters_present from summaries in _get_chapters() (DATA FLOW FIX)
- **Issue targeted:** CRITICAL #1 from attempt 24 — Father/son John Donaldson conflation
- **Changes made:** Modified `_get_chapters()` to fetch summary results and populate `characters_present` on StructuralElements
- **Result:** SUCCESS — `role_conflict` constraint edge now blocks the merge. 8 characters extracted (up from 6). Two separate "John Donaldson" entries exist.
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

## Next Action

**Phase:** awaiting_fix

**Priority fix for attempt 26:** CRITICAL #1 — Apply disambiguation labels to same-name characters.

When two characters share the exact same `canonical_name` and were kept separate by a `role_conflict` constraint edge, the pipeline should append the disambiguation labels from the summary data to their canonical names. The labels are already available in the constraint edge reason: `"labels ['the son', 'the father']"`.

**Recommended approach:**
1. In `src/agents/characters.py`, after merge groups are finalized and before character objects are built:
   - Scan for groups with identical `canonical_name`
   - If they were separated by a `role_conflict` constraint edge, extract the disambiguation labels
   - Append labels to canonical names: "John Donaldson (the father)", "John Donaldson (the son)"
2. This should cascade: distinct names → distinct profiles → distinct relationships
3. "Johnny" may then naturally merge into "John Donaldson (the son)" if diminutive detection is added

**Secondary fixes (if time permits):**
- #4: Organization filtering for Red Cross
- #6: Pronunciation false positive filtering
- #8: Possessive stripping from aliases

**If attempt 26 succeeds on #1:** The profile duplication (#2), narrator assignment (#3), and role issues (#9) may self-resolve once the profiling pipeline can distinguish the two characters.
