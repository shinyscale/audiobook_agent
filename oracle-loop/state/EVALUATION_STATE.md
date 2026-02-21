# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 3
- **Phase:** awaiting_fix
- **baseline_score:** 6.93
- **Competitive Mode:** single

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json
- Timestamped: ../output/American Sir_20260220_200722/

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 6/10 ✗
  - Completeness: 7/10
  - Identity Resolution: 5/10
  - Alias Grouping: 5/10
- Character Profiles: 5.5/10 ✗
- Chapter Summaries: 8/10 ✓
- Pronunciation Guide: 7/10 ✗
- HTML Presentation: 8/10 ✓
- **Overall: 7.23/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold)

## What Improved from Attempt 2
- **Uncle Bill's personality NOW EXCELLENT:** "reserved, crabbed, selfish, emotionally guarded but moved by vulnerability" — balanced and accurate. No longer "manipulative" or "inflicts harm." The moral_valence fix worked.
- **John (son) appearance NOW CORRECT:** "Tall boy with olive complexion, blue eyes, thickset features" — matches text. Context window expansion worked.
- **Chapter summary no longer says "brother":** The per-chapter summary avoids the cousin/brother error entirely. Major improvement.
- **Ted Frith now extracted:** The adaptive threshold fix (min_mentions=2 for short texts) worked — Ted Frith appears.
- **Voice guidance excellent for Ted:** Dialect notes capture "'I 'lowed', 'dum-dums', 'ring-tailed snorter'" — genuinely useful for narrator.
- **Score improved:** 7.13 → 7.23 (+0.10)

## What Regressed or Didn't Improve
- **Character fragmentation increased:** 4 characters → 8 characters. Ted and Ted Frith are separate. Johnny is separate from John. Red Cross extracted as a character. The lower threshold helped find Ted Frith but also introduced noise.
- **John/John Donaldson personality swap persists:** John's personality traits ("impulsive, thriftless, emotionally avoidant") describe the FATHER. John Donaldson's traits ("resilient, empathetic, reflective") describe the SON. Profiles are populated but assigned to the wrong person.
- **Uncle Bill appearance still "unknown":** Despite context window expansion, the self-description ("an elderly, grizzled, small man") wasn't captured. The description is first-person ("I... am crabbed") — narrator self-descriptions may need special handling.
- **Pronunciation categories ALL null:** Pipeline notes claimed categories were populated but the output JSON shows null for all 25 entries. Data export bug.
- **Plot summary still says "brother-in-law":** The overview.plot_summary retains the error even though the chapter summary fixed it.

## Current Issues (Priority Order)

### CRITICAL

1. **Ted Frith / Ted false split** [Identity Resolution]
   - Problem: "Ted Frith" (supporting_7, 2 mentions) and "Ted" (supporting_8, 5 mentions) are the same person
   - Evidence: Ted Frith is introduced by full name; subsequent references use just "Ted." The voice/dialect data is all on the "Ted" entry while "Ted Frith" is empty.
   - Impact: A narrator looking up "Ted Frith" gets an empty profile, while the useful dialect notes are under "Ted" — requires manual cross-referencing.
   - Location: V2 character extraction — alias resolution. The pipeline should recognize "Ted" as first-name-only for "Ted Frith" and merge them.
   - Fix approach: In alias resolution, when a single first name matches the first name of a full-name entry, merge them. This is a common pattern ("Ted" → "Ted Frith", like "Nick" → "Nick Carraway"). Check `src/pipeline/character_extraction_v2/` for alias merging logic.

2. **John / Johnny false split** [Identity Resolution / Alias Grouping]
   - Problem: "Johnny" (supporting_9, 2 mentions) is a nickname for "John" (supporting_0, 16 mentions) but listed separately.
   - Evidence: Ted calls John "Johnny" in dialogue. "Johnny" is a standard diminutive of "John."
   - Location: V2 character extraction — alias resolution. Need diminutive name recognition.
   - Fix approach: Add common diminutive mappings (Johnny→John, Billy→Bill/William, Bobby→Robert, etc.) to alias resolution, OR improve the LLM alias prompt to recognize standard English diminutives.

3. **John entry has FATHER's personality, John Donaldson entry has SON's personality** [Identity Resolution / Profiles]
   - Problem: The pipeline swapped personality profiles between father and son:
     - "John" (the son): personality says "impulsive, thriftless, emotionally avoidant" — these are the FATHER's traits from the backstory
     - "John Donaldson" (the father): personality says "resilient, empathetic, reflective" — these are the SON's traits from the war narrative
   - Evidence: The text describes the father as "thriftless" who "always thought the world owed him a living." The son is brave, patriotic, speaks of God's forgiveness.
   - Root cause: The name "John" appears throughout for both characters. The evidence gatherer collects passages containing "John" without distinguishing which John is meant. The father's backstory (lines ~28-63) dominates the early text.
   - Location: V2 profiling — evidence gathering and personality extraction
   - Fix approach: This is the hardest issue. Options:
     a) Position-aware evidence: if "John" evidence overlaps heavily with "John Donaldson" evidence positions, flag for disambiguation
     b) Cross-reference descriptions: if evidence[i] for "John" closely matches content attributed to "John Donaldson" entry, reassign it
     c) Accept this may not be fully fixable for same-name father/son pairs in a single pipeline pass
   - **Note:** This has persisted through all 3 attempts. If the same approach fails again, consider a fundamentally different strategy.

### HIGH

4. **Uncle Bill's appearance still "unknown"** [Profiles]
   - Problem: The text says "I... am crabbed and prejudiced... an elderly, grizzled, small man, grim and unexhilarating" — but appearance.summary is "unknown"
   - Evidence: The narrator describes himself in first person. The appearance extraction likely searches for "[character name] + physical description" patterns, but Uncle Bill never says "Uncle Bill is a grizzled man" — it's all first-person.
   - Location: V2 appearance extraction — needs to handle narrator self-descriptions
   - Fix approach: When `is_narrator: true`, also search for first-person appearance descriptions ("I am...", "I was...", "I... am") near self-referential passages. The narrator's self-description at position ~128 ("an elderly, grizzled, small man") and ~4948 ("am crabbed and prejudiced and critical") should be captured.

5. **Red Cross extracted as a character** [Completeness]
   - Problem: "Red Cross" (supporting_5, 4 mentions) is an organization, not a character or narrative element.
   - Unlike symbolic forces (e.g., "the monkey's paw"), the Red Cross is just a background organization that characters serve in.
   - Location: V2 character extraction — entity type filtering
   - Fix approach: Filter known organizations (Red Cross, Army, Navy, etc.) from character extraction. OR add a post-processing step that removes entries with `is_symbolic: false` and no personality/voice data that match known organization names.

6. **Plot summary still says "brother-in-law"** [Summaries]
   - Problem: `overview.plot_summary` contains "the possibility of his brother-in-law's survival" — factually wrong. They are cousins.
   - Evidence: "Thirty years rolled back, and I saw the charming boy, a cousin, who had come to be this lad's father"
   - Note: The per-chapter summary is correct and no longer makes this error. The plot summary is generated separately (likely in summary agent or analyzer overview step).
   - Location: Plot summary generation — separate from chapter summaries
   - Fix approach: This may self-correct on re-run since it's LLM-generated. If not, it's the same comprehension issue as attempt 2's chapter summary.

### MEDIUM

7. **Pronunciation false positives: Cross, Johnny, thriftless, thickset, greenhorns, whippersnapper** [Pronunciation]
   - Problem: 6/25 entries (24%) are common English words that no narrator needs help with
   - "Cross" is just a common word (part of "Red Cross")
   - "Johnny" is a standard English name
   - "thriftless", "thickset", "greenhorns", "whippersnapper" are common vocabulary
   - Location: Pronunciation pipeline — common word whitelist in `cmu_proposer.py`
   - Fix: Add these to COMMON_WORDS_WHITELIST. Also consider: "Donaldson's" (possessive duplicate of "Donaldson") should be filtered.

8. **All pronunciation categories null** [Pronunciation]
   - Problem: All 25 entries have `category: null` despite being clearly classifiable (Caporetto=foreign, Donaldson=proper_noun, live=homograph)
   - Evidence: `jq '[.pronunciations[] | select(.category != null)] | length'` returns 0
   - The pipeline notes for attempt 3 claimed "categories now populated: proper_noun (6), homograph (5), foreign (4), unknown (10)" — this was incorrect or the data was lost during export
   - Location: Pronunciation data serialization — categories may be computed internally but not written to the output model
   - Fix: Check the pronunciation pipeline's output serialization to ensure `category` is written to the final JSON

9. **"John Donaldson's" as alias (possessive form)** [Alias Grouping]
   - Problem: John Donaldson has alias `["John Donaldson's"]` — a possessive form, not a valid alias
   - Location: V2 alias cleanup — possessive forms should be stripped
   - Fix: Add possessive stripping (`'s` removal) to alias cleanup logic

10. **John Donaldson's appearance describes the SON, not the father** [Profiles]
    - Problem: "Towering over others in young magnificence" describes the young John, not the 55-year-old father
    - The father: "a big, athletic, grizzled chap, maybe fifty-five or over, shabby as to clothes, yet with an air like a duke"
    - Same root cause as issue #3 (father/son profile swap)

### LOW

11. **Uncle Bill's verbal tics include "Uncle Bill"** [Profiles]
    - "Uncle Bill" is how others ADDRESS him, not his own speech pattern
    - Persists from attempt 2

12. **Homographs lack IPA** [Pronunciation]
    - live, minute, read, close, moderate — correctly flagged but no IPA
    - Only descriptive notes provided ("REED vs RED")
    - Acceptable but could be improved with context-specific IPA

13. **Uncle Bill → John Donaldson listed as "former associate"** [Profiles]
    - Should be "cousin" — the text explicitly says so
    - Better than attempt 2's "brother-in-law" but still wrong
    - May improve on re-run with better evidence gathering

## Pipeline Notes (Attempt 3)
- Model: qwen3-next:80b-a3b-instruct-q8_0 (ollama) for all agents
- Competitive consensus: ENABLED (stages: characters, structure, summaries) via --competitive-all
- 8 characters extracted (up from 4): John (16), Uncle Bill/Bill (18), John Donaldson (9), Joe Barron (3), Red Cross (4), Ted Frith (2), Ted (5), Johnny (2)
- 4 profiles generated with HIGH confidence
- 25 pronunciation flags; categories all null in output despite pipeline claims
- Warning: "Narrator 'John Donaldson' identified but NOT found in main_cast. Available characters: []"
- Warning: "No passages provided for John, returning UNCERTAIN"
- Profiling: 5m 20s, 10 LLM calls, 4 items processed (all HIGH confidence)
- Total time: 14m 39s, 39 LLM calls, 56,216 tokens
- All characters from `supporting_*` IDs — main_cast pipeline didn't fire

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.93 | - | First analysis — profiles empty, character confusion |
| 2 | 7.13 | +0.20 | Profiles populated (but inaccurate), pronunciation false positives fixed |
| 3 | 7.23 | +0.30 | Uncle Bill personality excellent, summaries fixed, Ted Frith found — but fragmentation increased, pronunciation categories null |

## Fix History
- Attempt 2: Fixed null character profiles + pronunciation false positives
  - **Profile fix:** Secondary LLM call now triggers when profile is empty — profiles generated for 3/4 characters
  - **Pronunciation fix:** Added common nicknames to COMMON_WORDS_WHITELIST; ForeignProposer checks whitelist
  - Modified: `src/analyzer.py`, `src/pipeline/pronunciation_guide/proposers/cmu_proposer.py`, `src/pipeline/pronunciation_guide/proposers/foreign_proposer.py`
  - Result: Pronunciation improved (7→7.5), Profiles improved (4→5), but core accuracy issues remain

- Attempt 3: Physical descriptions, personality balance, Ted Frith, pronunciation
  - **Context window expanded:** 200→400 chars for character profiling
  - **Moral valence softened:** Removed mandatory negative attribution for ANTAGONIST classification
  - **Adaptive grounding threshold:** min_mentions=2 for texts <10,000 words
  - **Pronunciation whitelist expanded:** Added 18 common English words
  - Modified: `src/analyzer.py`, `src/pipeline/character_profiling/moral_valence.py`, `src/agents/characters.py`, `src/pipeline/pronunciation_guide/proposers/cmu_proposer.py`
  - Result: Uncle Bill personality much better (+), John appearance correct (+), Ted Frith found (+), but character fragmentation increased (-), pronunciation categories null (-)

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

## Configuration Notes
- Model: qwen3-next:80b-a3b-instruct-q8_0 (ollama) for all agents
- character_llm_chunk_chars: 5000 (appropriate for 5,048 word text)
- All characters from `supporting_*` IDs — main_cast pipeline may not have fired
- Temperature: 0.7 for all agents
- No LLM retries recorded

## Priority Fix Guidance for Attempt 4

**Focus areas ranked by tractability and score impact:**

1. **Character merging: Ted+Ted Frith, John+Johnny (Characters 6→7.5-8, +0.50-0.50 overall)**
   - Most tractable fix. Two clear false splits that should be merged.
   - Ted/Ted Frith: first-name matches full-name's first component → merge
   - John/Johnny: standard diminutive → merge as alias
   - This alone could push Identity Resolution from 5→7 and Alias Grouping from 5→7
   - Also remove Red Cross (organization, not character) → Completeness 7→8

2. **Pronunciation cleanup (Pronunciation 7→8, +0.10 overall)**
   - Quick win: add Cross, Johnny, thriftless, thickset, greenhorns, whippersnapper, Donaldson's to whitelist
   - Fix category null bug: check pronunciation serialization for category field
   - Together these push pronunciation to ~8.0

3. **Uncle Bill appearance (Profiles 5.5→6.5, +0.15 overall)**
   - Handle first-person narrator self-descriptions in appearance extraction
   - The text has a clear description: "an elderly, grizzled, small man, grim and unexhilarating"

4. **Father/son personality swap (Profiles 6.5→8, would need significant work)**
   - This is the hardest remaining issue
   - Has persisted through all 3 attempts
   - May require position-aware evidence gathering or cross-reference checks
   - Consider: if Characters and Pronunciation hit 8.0, only Profiles remains below threshold. Attempt 5 could focus entirely on this.

**Strategy recommendation:** Focus attempt 4 on issues #1 (character merges) and #2 (pronunciation) which are code-fixable and can push two of three failing categories to 8.0. Issue #3 (Uncle Bill appearance) is also tractable. Issue #4 (father/son swap) may need to wait for attempt 5 if it can't be solved concurrently.

## Next Action
Run PROMPT_fix.md to address character fragmentation (Ted/Ted Frith + John/Johnny merges), pronunciation false positives, and pronunciation category null bug.
