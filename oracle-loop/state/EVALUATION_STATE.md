# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 4
- **Phase:** awaiting_analysis
- **baseline_score:** 6.93
- **Competitive Mode:** single

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json
- Timestamped: ../output/American Sir_20260220_204834/

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 7/10 ✗
  - Completeness: 7.5/10
  - Identity Resolution: 6/10
  - Alias Grouping: 7/10
- Character Profiles: 5.5/10 ✗
- Chapter Summaries: 7.5/10 ✗
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 8/10 ✓
- **Overall: 7.48/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold)

## What Improved from Attempt 3
- **Johnny→John merge WORKS:** "Johnny" now appears as alias of "John" ✓. The diminutive merge fix worked perfectly.
- **Possessive forms filtered:** "John Donaldson's" no longer appears as alias ✓. The possessive check in `_is_valid_name()` worked.
- **Pronunciation reduced from 25→19:** thriftless (derivation check), thickset, greenhorns, whippersnapper, johnny removed ✓. Whitelist expansion worked.
- **John Donaldson personality improved:** Now "burdened by past shame, seeking redemption" — correct for the father. Was previously misattributed.
- **Pronunciation now passes 8.0:** Good coverage of Italian/French words, proper nouns, homographs. Only 1 false positive (Cross).
- **Score improved:** 7.23 → 7.48 (+0.25)

## What Regressed or Didn't Improve
- **Ted/Ted Frith STILL SPLIT:** The first-name merge fix was implemented but did NOT fire. Ted Frith has 2 mentions (≤3 threshold ✓) and Ted has 5 mentions (>2 ✓), so the condition SHOULD have triggered. Investigate why it didn't — possible ordering issue or ID mismatch.
- **Red Cross STILL extracted:** Organization filter was not implemented in attempt 3's fix scope.
- **Chapter summary regressed: "deceased brother's grandson"** — attempt 3 had fixed this to correctly say "cousin." Now the "brother" error is back. LLM stochasticity.
- **Plot summary says "cousin's grandson"** — "cousin" is correct but should be "cousin's son," not grandson. John is John Donaldson's son.
- **John (son) personality STILL has father's traits:** "impulsive, reckless with money, avoids discomfort" describes the FATHER. The son should be: brave, earnest, patriotic, compassionate. All 10 evidence citations for "John" describe the FATHER's life story.
- **John→John Donaldson relationship: "same person"** — CRITICALLY WRONG. They are father and son, not the same person. A narrator reading this will be confused about the entire plot.
- **Uncle Bill appearance still "unknown"** — first-person self-description not captured.
- **Pronunciation categories still all null** — serialization bug persists.

## Current Issues (Priority Order)

### CRITICAL

1. **John (son) personality has FATHER's traits — evidence collection broken for same-name characters** [Profiles / Identity Resolution]
   - Problem: "John" entry (the son, 30 mentions) has personality: "Charismatic and impulsive, avoids discomfort and responsibility, reckless with money" — these ALL describe the FATHER, not the son
   - Evidence: All 10 evidence citations for "John" describe the father's life: "pampered in youth," "inherited debts," "avoided responsibility," "death was likely suicide," "is the father of the narrator's adopted son"
   - The son's actual traits: brave, patriotic, earnest, compassionate (enlists in WWI, serves as ambulance driver, discovers his father in a war zone)
   - Root cause: The name "John" is used for BOTH characters throughout the text. The evidence gatherer collects all "John" passages without distinguishing which John is discussed. The father's backstory dominates the early sections.
   - Impact: Profiles 5.5→8.0 requires fixing this. A narrator voicing "John" would prepare the wrong characterization.
   - **This has persisted through ALL 4 attempts.** The same pipeline layer (profiling evidence gathering) keeps collecting father's passages for the son's entry.
   - Location: V2 character profiling — evidence gathering in `src/analyzer.py` or `src/pipeline/character_profiling/`
   - Fix approaches (escalating):
     a) **Position-aware evidence deduplication:** If evidence for "John" overlaps with evidence already collected for "John Donaldson," exclude it from "John" and use the remaining evidence (which should be about the son)
     b) **Cross-reference with known relationships:** If "John" and "John Donaldson" are known to be father/son, partition evidence by which character is the subject
     c) **Disambiguation prompt:** When evidence is ambiguous for same-name characters, ask the LLM to classify each passage as referring to Character A or Character B

2. **John→John Donaldson relationship says "same person"** [Identity Resolution / Profiles]
   - Problem: The relationship field states "same person (full name used in context)" — displayed prominently in the HTML
   - Evidence: They are CLEARLY father and son. The text says "I saw the charming boy, a cousin, who had come to be this lad's father"
   - Impact: A narrator reading this will be deeply confused about the plot
   - Location: Relationship extraction in profiling pipeline
   - Fix approach: Same root cause as issue #1 — the profiler can't distinguish the two Johns

### HIGH

3. **Ted/Ted Frith false split persists despite merge fix** [Identity Resolution]
   - Problem: Ted Frith (supporting_6, 2 mentions) and Ted (supporting_7, 5 mentions) remain separate entries
   - Evidence: Ted Frith is introduced by full name; "Ted" is used for all subsequent references. Even the profiler acknowledges in Ted's relationships: "same person... full name used interchangeably with first name only"
   - The fix from attempt 3 (first-name merge in `_merge_within_supporting_cast`) should have fired: Ted Frith has 2 mentions (≤3) and Ted has 5 mentions (>2). **Why didn't it work?**
   - Possible causes: (a) order of iteration — Ted Frith processed before Ted?, (b) the full-name character's first word comparison failed, (c) the merge condition uses wrong mention count field
   - Location: `src/agents/characters.py` — `_merge_within_supporting_cast()` Pass 2 (first-name check)
   - Fix: Debug the first-name merge condition. Add logging or verify with unit test. The condition should be: `if single_word_name == full_name.split()[0] and full_name_mentions <= 3 and single_word_mentions > full_name_mentions`

4. **Red Cross still extracted as character** [Completeness]
   - Problem: "Red Cross" (supporting_5, 4 mentions) is an organization, not a character or symbolic force
   - Unlike "the monkey's paw" (antagonistic force), the Red Cross is just a background institution
   - This was noted in attempts 2 and 3 but never fixed
   - Location: V2 character extraction — needs entity type filtering
   - Fix approach: Add known organization names (Red Cross, Army, Navy, United Nations, etc.) to an exclusion list in supporting cast extraction, OR filter entities with `is_symbolic: false` and no personality/voice data

5. **Chapter summary regression: "deceased brother's grandson"** [Summaries]
   - Problem: The chapter summary says "deceased brother's grandson, John" — TWO errors:
     - "brother" should be "cousin" (John Donaldson is Uncle Bill's cousin)
     - "grandson" should be "son" (John is John Donaldson's son, not grandson)
   - This was fixed in attempt 3 but regressed due to LLM stochasticity on re-run
   - The plot_summary correctly says "cousin" but also says "grandson" (should be "son")
   - Location: Summary generation — LLM-generated content
   - Fix approach: This is hard to fix generically. Options:
     a) Post-processing: cross-reference character relationships with summary text
     b) Stronger prompting: include extracted relationships in summary prompt context
     c) Accept LLM variability — score will fluctuate between runs

6. **Uncle Bill appearance still "unknown"** [Profiles]
   - Problem: Text says "I... am... an elderly, grizzled, small man, grim and unexhilarating" — but appearance is "unknown"
   - Root cause: Narrator describes himself in first person; appearance extraction searches for third-person descriptions
   - Was noted in attempts 2, 3, and 4 but not fixed
   - Location: V2 appearance extraction — needs first-person narrator self-description handling
   - Fix: When `is_narrator: true`, search for "I am/was [physical description]" patterns in addition to third-person descriptions

### MEDIUM

7. **Uncle Bill relationship errors** [Profiles]
   - "uncle by marriage (deceased brother's son)" for John Donaldson — should be "cousin"
   - "guardian figure / reluctant surrogate father" for John — acceptable but "son-in-law" prefix is wrong
   - Uncle Bill verbal tics include "addressing the boy as 'Uncle Bill'" — this is how the boy addresses HIM, not his own speech pattern
   - These are all consequences of the same profiling confusion

8. **Pronunciation: "Cross" false positive** [Pronunciation]
   - Common English word flagged because "Red Cross" was extracted as a character
   - Fix: Add "Cross" to whitelist, OR removing Red Cross as a character would eliminate this naturally

9. **Pronunciation categories all null** [Pronunciation]
   - All 19 entries have `category: null` despite being clearly classifiable
   - Terminal output during analysis showed category counts — data is computed but not serialized
   - Location: Pronunciation pipeline output serialization
   - Fix: Check where `category` is set in the pronunciation pipeline and ensure it's written to the output model

### LOW

10. **John appearance confusion** [Profiles]
    - John's appearance: "Olive-skinned with blue eyes, thickset... physically resembles his son" — says "resembles his son" but John IS supposed to be the son. Age listed as "middle-aged" but the son is young.
    - Same root cause as issue #1

11. **Homographs lack IPA** [Pronunciation]
    - live, minute, read, close, moderate — flagged correctly but only have descriptive notes, no IPA
    - Acceptable since both pronunciations are given in notes, but IPA would be ideal

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.93 | - | First analysis — profiles empty, character confusion |
| 2 | 7.13 | +0.20 | Profiles populated (but inaccurate), pronunciation false positives fixed |
| 3 | 7.23 | +0.30 | Uncle Bill personality excellent, summaries fixed, Ted Frith found — but fragmentation increased, pronunciation categories null |
| 4 | 7.48 | +0.55 | Johnny merged, pronunciation passes 8.0, possessives filtered — but Ted/Ted Frith still split, summary regression, profiles unchanged |

## Fix History
- Attempt 2: Fixed null character profiles + pronunciation false positives
  - Modified: `src/analyzer.py`, `cmu_proposer.py`, `foreign_proposer.py`
  - Result: Pronunciation improved (7→7.5), Profiles improved (4→5)

- Attempt 3: Physical descriptions, personality balance, Ted Frith, pronunciation
  - Modified: `src/analyzer.py`, `moral_valence.py`, `src/agents/characters.py`, `cmu_proposer.py`
  - Result: Uncle Bill personality fixed, Ted Frith found, but fragmentation increased

- Attempt 4: Character merges (Ted/Ted Frith, John/Johnny) + pronunciation whitelist
  - Modified: `src/agents/characters.py` (possessive filter, first-name merge, diminutive merge), `cmu_proposer.py` (derivation check, whitelist)
  - Result: Johnny merged ✓, possessives filtered ✓, pronunciation improved to 8.0 ✓, but Ted/Ted Frith merge DID NOT FIRE ✗

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | (baseline) | N/A | Baseline established |
| 2 | Profiles: null descriptions | src/analyzer.py | Partial — profiles generated but personality/physical still had issues |
| 2 | Pronunciation: false positives | cmu_proposer.py, foreign_proposer.py | Fixed — Bill/Joe/was removed |
| 3 | Profiles: physical descriptions | src/analyzer.py (context window) | Partial — John appearance correct, Uncle Bill still unknown |
| 3 | Profiles: personality balance | moral_valence.py | Fixed — Uncle Bill no longer "manipulative" |
| 3 | Characters: Ted Frith missing | src/agents/characters.py (threshold) | Found but split into Ted/Ted Frith (new problem) |
| 3 | Pronunciation: false positives | cmu_proposer.py (whitelist) | Partial — some removed, new ones remain |
| 4 | Characters: possessive filter | src/agents/characters.py | Fixed — "John Donaldson's" no longer extracted |
| 4 | Characters: Johnny→John merge | src/agents/characters.py (diminutive) | Fixed — Johnny now alias of John |
| 4 | Characters: Ted→Ted Frith merge | src/agents/characters.py (first-name) | **NO CHANGE** — condition didn't fire despite being implemented |
| 4 | Pronunciation: whitelist | cmu_proposer.py | Fixed — thriftless/thickset/greenhorns/whippersnapper removed |

## Configuration Notes
- Model: qwen3-next:80b-a3b-instruct-q8_0 (ollama) for all agents
- character_llm_chunk_chars: 5000 (appropriate for 5,048 word text)
- All characters from `supporting_*` IDs — main_cast pipeline did not fire
- Temperature: 0.7 for all agents
- Total time: 13m 31s, 31 LLM calls, 51,634 tokens
- 4 profiles generated with HIGH confidence
- 19 pronunciation flags; all categories null

## Priority Fix Guidance for Attempt 5

**The three failing categories and what's needed to reach 8.0:**

### Characters: 7 → 8.0 (needs +1.0)
**Tractable fixes:**
1. **Debug Ted/Ted Frith merge** — The code was added in attempt 4 but didn't fire. This is a debugging task, not a design task. Check `_merge_within_supporting_cast()` with actual data. If fixed: Identity Resolution 6→7, Alias Grouping 7→8.
2. **Remove Red Cross** — Add organization exclusion list. If fixed: Completeness 7.5→8.5.
3. Together these push Characters to ~8.0.

### Summaries: 7.5 → 8.0 (needs +0.5)
**Harder — LLM stochasticity:**
- The "brother" error comes and goes between runs. Attempt 3 had it right, attempt 4 doesn't.
- Options: (a) Re-run and hope for better luck. (b) Add extracted character relationships to summary prompt context so the LLM knows Uncle Bill's cousin is John Donaldson. (c) Post-process summary to fix known relationship errors.
- Option (b) is the most robust generic approach.

### Profiles: 5.5 → 8.0 (needs +2.5) — HARDEST
**This is the critical blocker.** The father/son confusion has persisted through ALL 4 attempts.
- **Evidence deduplication** is the most promising approach: if "John" evidence overlaps with "John Donaldson" evidence positions, exclude the overlapping passages from "John" and use remaining evidence (about the son).
- **Uncle Bill appearance**: handle narrator first-person self-descriptions.
- **Relationship accuracy**: fixing evidence deduplication should cascade to fix relationships.
- Even with perfect execution, this may only get profiles to ~7. The pipeline fundamentally struggles with same-name father/son pairs.

**Strategy recommendation:** Focus on Characters (debug Ted merge + Red Cross filter) and Summaries (add relationships to prompt context) as the tractable wins. For Profiles, attempt position-aware evidence deduplication — but this is the highest-risk fix with the most code complexity. If profiles remain below 8.0, this text may need to be flagged as requiring more fundamental pipeline changes.

**WARNING: Same files modified repeatedly without success:**
- `src/agents/characters.py` — modified in attempts 3 and 4 for Ted/Ted Frith. If attempt 5 modifies it again for the same issue, the fix approach needs to change.
- `src/analyzer.py` — modified in attempts 2 and 3 for profiles. Profile evidence gathering is the root cause and has NOT been successfully addressed.

## Fix History (continued)
- Attempt 5: Debug Ted/Ted Frith merge, Red Cross filter, profile evidence deduplication, narrator appearance
  - Issue 1 (Ted/Ted Frith): Root cause found — NER counts Ted=1 mention, Ted Frith=3 mentions; old condition `char.mention_count > other_char.mention_count` evaluated as `1 > 3 = False`, blocking the merge. Removed that condition since `other_char.mention_count <= 3` already guards against false merges.
  - Issue 2 (Red Cross): Restricted supporting cast NER extraction to PERSON type only. Organizations like "Red Cross" are ORG-typed — the ORG inclusion was defensive but unnecessary since main cast catches important characters.
  - Issue 3 (John personality/evidence): Added same-name disambiguation filter in profile generation. When "John" and "John Donaldson" both exist, filters out "John" mention contexts where "John Donaldson" appears within ±500 chars. This prevents father's passages from contaminating the son's profile.
  - Issue 4 (Uncle Bill appearance): For narrator characters whose first named mention is >1500 chars from text start, adds a synthetic early mention at position 100 to capture first-person self-descriptions ("I am an elderly, grizzled, small man...").
  - Modified: src/agents/characters.py, src/pipeline/character_extraction_v2/supporting.py, src/analyzer.py
  - Smoke test: PASS — Ted/Ted Frith merge now fires (NER count mismatch was root cause); Red Cross excluded; no new test regressions

## Next Action
**Phase:** awaiting_analysis
