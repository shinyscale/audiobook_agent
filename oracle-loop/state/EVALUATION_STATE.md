# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 6
- **Phase:** awaiting_analysis
- **baseline_score:** 6.93
- **Competitive Mode:** single

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json
- Timestamped: ../output/American Sir_20260220_212706/

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 8.5/10 ✓
  - Completeness: 9/10
  - Identity Resolution: 8.5/10
  - Alias Grouping: 9/10
- Character Profiles: 6/10 ✗
- Chapter Summaries: 7.5/10 ✗
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 8/10 ✓
- **Overall: 7.93/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold)

## What Improved from Attempt 4
- **Ted/Ted Frith MERGED:** Ted Frith now has 5 mentions with "Ted" as alias ✓. Root cause was NER count mismatch; removing the `char.mention_count > other_char.mention_count` condition fixed it.
- **Red Cross REMOVED:** Organization filter (PERSON-only NER for supporting cast) worked ✓. Character count 6→5.
- **"Cross" pronunciation false positive gone:** Removed naturally when Red Cross was excluded. 19→18 entries.
- **John→John Donaldson relationship: no longer "same person":** Now shows "unknown" — still wrong but far less damaging than "same person." Improvement.
- **John Donaldson→John: "father":** CORRECT ✓. The father-to-son relationship is now accurately labeled.
- **John Donaldson personality improved:** "Introspective, burdened by guilt, seeks redemption through service" — accurate for the father ✓.
- **Character Extraction now passes 8.0:** Up from 7/10 to 8.5/10 thanks to Ted merge + Red Cross removal.
- **Score improved:** 7.48 → 7.93 (+0.45)

## What Didn't Improve
- **John (son) personality STILL has father's traits:** "impulsive, charming, avoidant of unpleasantness, thriftless" — 5 of 7 evidence citations are about the FATHER (financial irresponsibility, desire to live in Italy, faked death, avoided correspondence). Only evidence items #6 (ambulance driver) and #7 (light demeanor while wounded) are about the son. The ±500 char dedup filter didn't remove enough father evidence from John's collection.
- **Uncle Bill appearance STILL "unknown":** The synthetic early mention fix for narrators didn't produce results. The pipeline warning "No definitive narrator identified from plot summary" suggests narrator detection failed, preventing the fix from firing.
- **Uncle Bill verbal tics still backwards:** "addressing John as 'Uncle Bill'" — John addresses HIM as Uncle Bill, not the other way around.
- **Uncle Bill→John Donaldson relationship: "brother-in-law and estranged brother"** — wrong (should be "cousin").
- **Chapter summary STILL says "deceased brother's grandson":** "brother" should be "cousin," "grandson" should be "son." The plot summary has the same two errors. The plot summary correctly says "John's father" later, creating an internal contradiction.
- **All physical_description fields null** — the `appearance` object has data for John Donaldson but `physical_description` remains null across all characters.
- **Pronunciation categories still all null** — serialization bug persists.

## Current Issues (Priority Order)

### CRITICAL

1. **John (son) personality has FATHER's traits — evidence dedup insufficient** [Profiles]
   - Problem: "John" (supporting_0, 30 mentions) personality: "impulsive, charming, avoidant of unpleasantness, thriftless, courageous, casual" — 4 of 6 traits describe the FATHER
   - Evidence contamination: 5 of 7 evidence citations are about the father:
     - [1] "received financial support... lived extravagantly on inherited wealth" → FATHER
     - [2] "had a lifelong desire to live in Italy" → FATHER
     - [3] "frequently requested money and avoided correspondence" → FATHER
     - [4] "death was likely a suicide" → FATHER
     - [5] "nephew of the narrator and son of his deceased brother" → AMBIGUOUS
     - [6] "served as an ambulance driver in WWI" → SON ✓
     - [7] "maintained a light, affectionate demeanor even while severely wounded" → SON ✓
   - The son's actual traits: brave, earnest, patriotic, compassionate, forgiving
   - Root cause: The ±500 char proximity filter didn't work because many passages discussing "John" (the father) DON'T mention "John Donaldson" within 500 chars — they just use "John" throughout the early flashback sections
   - The pipeline warning "No passages provided for John Donaldson, returning UNCERTAIN" suggests the filter was too aggressive for John Donaldson (removing all his passages) while not aggressive enough for John (leaving father's passages in)
   - **This has persisted through ALL 5 attempts.** Approaches tried: position-aware dedup (attempt 5). The fundamental issue is the text uses "John" for BOTH characters and the father's backstory dominates the early narrative.
   - Location: `src/analyzer.py` — evidence dedup logic
   - Fix approach: **The proximity filter approach is flawed** because:
     - Passages about the father use just "John" without "John Donaldson" nearby
     - All "John Donaldson" passages DO have "John" nearby (trivially, as a substring)
     - Better approach: **Temporal/positional partitioning** — Use the text structure: passages in the first half (flashback about the father) that mention "John" in past tense or in context of financial irresponsibility/disappearance should be attributed to John Donaldson. Passages in the second half (WWI, reunion) with "John" in active/present context should be attributed to the son.
     - Alternative: **LLM disambiguation** — When two characters share a first name, prompt the LLM with each evidence passage and ask "Does this passage describe [John the son/young man] or [John Donaldson the father]?"

### HIGH

2. **Uncle Bill appearance "unknown" despite first-person self-description** [Profiles]
   - Problem: Text says "I... am... an elderly, grizzled, small man, grim and unexhilarating" — but appearance shows "unknown"
   - The attempt 5 fix (synthetic early mention for narrators) didn't fire because "No definitive narrator identified from plot summary" — narrator detection failed
   - Uncle Bill IS correctly tagged as `is_narrator: true` in the character data, but the appearance extraction didn't use this
   - **This has been noted in attempts 2, 3, 4, and 5 without resolution**
   - Location: `src/analyzer.py` or `src/pipeline/character_profiling/` — appearance extraction
   - Fix: The narrator detection check needs to use the `is_narrator` flag from character data, not rely on plot summary narrator identification. When a character has `is_narrator: true`, search for first-person self-descriptions ("I am/was [physical]") in addition to third-person descriptions.

3. **Summary says "deceased brother's grandson" — two factual errors** [Summaries]
   - Problem: Both chapter summary and plot summary open with "deceased brother's grandson, John"
   - Error 1: "brother" should be "cousin" (John Donaldson is Uncle Bill's cousin, not brother)
   - Error 2: "grandson" should be "son" (John is John Donaldson's son, not grandson)
   - The plot summary correctly identifies "John's father, the charismatic but reckless John Donaldson" later — contradicting itself
   - This error has appeared in attempts 1, 2, 4, and 5 (was correct in attempt 3 only)
   - Location: Summary generation LLM prompts
   - Fix approach: Include extracted character relationships in the summary prompt context so the LLM has explicit family relationship data. When John Donaldson→John is tagged "father," the summary prompt should say "John Donaldson is John's father; Uncle Bill is John's guardian (cousin of John Donaldson)."

### MEDIUM

4. **John→John Donaldson relationship: "unknown"** [Profiles]
   - Problem: Should be "son" or "father and son" — John Donaldson→John correctly says "father" but the reverse shows "unknown"
   - A narrator reading this sees the relationship only one way
   - Location: Relationship extraction — bidirectional relationship inference
   - Fix: When Character A→B has relationship "father," automatically set B→A to "son" if currently unknown

5. **Uncle Bill→John Donaldson relationship: "brother-in-law and estranged brother"** [Profiles]
   - Problem: Should be "cousin" — John Donaldson is Uncle Bill's cousin, not brother or brother-in-law
   - The summary correctly identifies a family connection but mischaracterizes it
   - Same root cause as the summary "brother" error — the LLM confuses the relationship

6. **Uncle Bill verbal tics reversed** [Profiles]
   - Problem: Lists "addressing John as 'Uncle Bill'" — but John addresses HIM as Uncle Bill, not the other way around
   - Also: "use of 'Uncle Bill' in narration" — this is his name/title used by others
   - A narrator reading this would misunderstand the speech patterns

7. **Pronunciation categories all null** [Pronunciation]
   - All 18 entries have `category: null` despite being classifiable (proper_noun, foreign_term, homograph, etc.)
   - Serialization bug — data is computed but not written to output model
   - Location: Pronunciation pipeline output serialization
   - Impact: Minor for narrator utility but reduces data quality

### LOW

8. **John age listed as "young (early 20s) to middle-aged (near 40)"** [Profiles]
   - Confusing range — the son is young. The wide range comes from conflating father and son evidence.
   - Same root cause as issue #1.

9. **Homographs lack IPA** [Pronunciation]
   - live, minute, read, close, moderate — flagged correctly with descriptive notes but no IPA
   - Acceptable since both pronunciations are described, but IPA for each pronunciation would be ideal

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.93 | - | First analysis — profiles empty, character confusion |
| 2 | 7.13 | +0.20 | Profiles populated (but inaccurate), pronunciation false positives fixed |
| 3 | 7.23 | +0.30 | Uncle Bill personality excellent, summaries fixed, Ted Frith found — but fragmentation increased, pronunciation categories null |
| 4 | 7.48 | +0.55 | Johnny merged, pronunciation passes 8.0, possessives filtered — but Ted/Ted Frith still split, summary regression, profiles unchanged |
| 5 | 7.93 | +1.00 | Ted/Ted Frith merged, Red Cross removed, Characters now passes 8.0 — but profiles still 6/10 (father/son evidence contamination persists), summaries still 7.5 |

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

- Attempt 5: Ted/Ted Frith merge fix, Red Cross filter, profile evidence dedup, narrator appearance
  - Modified: `src/agents/characters.py`, `src/pipeline/character_extraction_v2/supporting.py`, `src/analyzer.py`
  - Result: Ted merged ✓, Red Cross removed ✓, Characters passes 8.0 ✓, but evidence dedup insufficient for John profile, narrator appearance fix didn't fire

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
| 4 | Characters: Ted→Ted Frith merge | src/agents/characters.py (first-name) | **NO CHANGE** — condition didn't fire (NER count mismatch) |
| 4 | Pronunciation: whitelist | cmu_proposer.py | Fixed — thriftless/thickset/greenhorns/whippersnapper removed |
| 5 | Characters: Ted/Ted Frith merge | src/agents/characters.py (removed count condition) | **Fixed** ✓ |
| 5 | Characters: Red Cross filter | src/pipeline/character_extraction_v2/supporting.py | **Fixed** ✓ |
| 5 | Profiles: evidence dedup | src/analyzer.py (±500 char filter) | **Insufficient** — filter too blunt; removed all John Donaldson evidence but left father evidence in John's collection |
| 5 | Profiles: narrator appearance | src/analyzer.py (synthetic early mention) | **NO CHANGE** — narrator detection from plot summary failed, fix didn't fire |

## Configuration Notes
- Model: qwen3-next:80b-a3b-instruct-q8_0 (ollama) for all agents
- character_llm_chunk_chars: 5000 (appropriate for 5,048 word text)
- All characters from `supporting_*` IDs — main_cast pipeline did not fire
- Temperature: 0.7 for all agents
- Total time: 14m 3s, 32 LLM calls, 52,730 tokens
- 4 profiles generated with HIGH confidence (John Donaldson personality now accurate)
- 18 pronunciation flags; all categories null

## Priority Fix Guidance for Attempt 6

**Two failing categories and what's needed to reach 8.0:**

### Profiles: 6 → 8.0 (needs +2.0) — PRIMARY BLOCKER

**The father/son evidence contamination has persisted through ALL 5 attempts.** Previous approach (±500 char proximity filter) was insufficient. The fix must change strategy:

1. **LLM-based evidence disambiguation (RECOMMENDED):** When two characters share a first name (e.g., "John" and "John Donaldson"), send each collected evidence passage to the LLM with a prompt: "Character A is [John, the son, young ambulance driver]. Character B is [John Donaldson, the father, who faked his death]. Which character does this passage describe?" Reassign evidence accordingly before generating personality/traits.
   - This is the most robust generic approach — works for any same-name disambiguation
   - Location: `src/analyzer.py` or `src/pipeline/character_profiling/`

2. **Uncle Bill appearance: Use `is_narrator` flag directly** — Don't rely on plot summary narrator detection. Check the character's `is_narrator` field from extraction, and if true, search for first-person self-descriptions in the text.

3. **Bidirectional relationships:** When John Donaldson→John is "father," automatically infer John→John Donaldson is "son."

### Summaries: 7.5 → 8.0 (needs +0.5)

**Include character relationships in summary prompt context.** Pass the extracted relationship data (John Donaldson is John's father, Uncle Bill is John's guardian/cousin of John Donaldson) into the summary generation prompt. This gives the LLM explicit facts to work with instead of relying on inference.

### WARNING: Same files modified repeatedly
- `src/analyzer.py` — modified in attempts 2, 3, and 5 for profiles. The ±500 char filter approach FAILED. Attempt 6 must use a fundamentally different approach (LLM disambiguation) rather than refining the proximity filter.
- If the same approach is tried again, it will likely produce the same insufficient result.

## Fix History (continued)
- Attempt 6: Evidence disambiguation, narrator appearance, bidirectional relationships, summary prompt
  - Root causes:
    - John contamination: `src/analyzer.py:_generate_character_profile()` disambiguation note didn't include other character's V2-extracted description
    - Uncle Bill appearance: narrator note didn't explicitly say first-person "I" references describe the narrator; early text guarantee only fired for late first-mentions
    - Bidirectional: no reverse relationship inference after profile generation loop
    - Summary "brother's grandson": summarizer prompts allowed inferring family relationship types
    - Pronunciation categories null: `src/models.py:PronunciationEntry` missing `category` field
  - Fixes:
    - Added `character_descriptions` parameter to `_generate_character_profile`; disambiguation note now includes other character's description from V2 extraction
    - Changed narrator early-mention condition from `position > 1500` to ALWAYS add early context; strengthened narrator note to explicitly say first-person ("I am...") descriptions refer to this character
    - Added bidirectional relationship post-processing after profile loop (father↔son, uncle↔nephew, etc.)
    - Added "use only exact relationship terms from text" guideline to all three summarizer prompts
    - Added `category: Optional[str]` field with `model_validator` to `PronunciationEntry` to mirror `flag_reason.value`
  - Smoke test: imports OK, category field works, no new test failures
  - Modified: `src/analyzer.py`, `src/models.py`, `src/pipeline/chapter_summary/summarizer.py`

## Phase
awaiting_analysis

## Next Action
Re-run analysis on american_sir to verify fixes
