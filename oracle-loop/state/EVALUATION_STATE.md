# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 3
- **Phase:** awaiting_evaluation
- **baseline_score:** 6.93
- **Competitive Mode:** single

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json
- Timestamped: ../output/American Sir_20260220_200722/

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 6.5/10 ✗
  - Completeness: 7/10
  - Identity Resolution: 6/10
  - Alias Grouping: 7/10
- Character Profiles: 5/10 ✗
- Chapter Summaries: 7/10 ✗
- Pronunciation Guide: 7.5/10 ✗
- HTML Presentation: 8/10 ✓
- **Overall: 7.13/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (4 categories below threshold)

## What Improved from Attempt 1
- **Pronunciation false positives FIXED:** "Bill", "Joe", "was" no longer flagged (cmu_proposer.py, foreign_proposer.py changes worked)
- **Profiles partially populated:** personality summaries, traits, temperament, and voice guidance now exist for John and Uncle Bill (were all null in attempt 1). The `analyzer.py` secondary LLM call fix worked — profiles are generated.
- **Score improved:** 6.93 → 7.13 (+0.20)

## What Did NOT Improve
- Physical descriptions still "unknown" for ALL characters (0/4)
- Father/son evidence confusion on "John" entry persists — ALL 10 evidence items describe the father
- Cousin/brother relationship error persists ("brother-in-law" in attempt 2 vs "brother" in attempt 1 — still wrong)
- Ted Frith still missing
- Uncle Bill's example quotes still from other characters
- Pronunciation categories still all null; homographs still lack IPA

## Current Issues (Priority Order)

### CRITICAL

1. **"John" entry (supporting_0) has ENTIRELY the father's profile data** [Identity Resolution / Profiles]
   - Problem: The "John" entry (16 mentions) is intended to represent the SON, but every piece of profile data describes the FATHER:
     - Personality: "Impulsive, emotionally expressive, dependent on others for financial support, dream of living in Italy" — the FATHER
     - Traits: "impulsive, charismatic, thriftless, idealistic" — the FATHER
     - Description: "a charismatic but financially irresponsible young man who squanders his inheritance" — the FATHER
     - All 10 evidence items describe the father (graduated Yale, lived in Florida, died in accident, had a two-year-old son)
   - Impact: A narrator using this guide would voice the SON with the FATHER's characteristics. The SON is brave, earnest, patriotic (ambulance driver in WWI), but none of that appears.
   - Root cause: The text uses "John" for both father and son. The profiling pipeline gathered evidence for "John" without positional context to distinguish which John was being discussed. The father's backstory dominates the earlier part of the text (lines 28-63), so the LLM defaulted to those passages.
   - Location: V2 character profiling — evidence gathering stage. The evidence gatherer needs positional/contextual disambiguation.
   - Fix approach: This is fundamentally hard. Options:
     a) Add position-aware context: "When gathering evidence for 'John', note that the first half of the text discusses John Donaldson Sr. (the father) and the second half discusses his son, also named John"
     b) During evidence assignment, cross-reference with the existing "John Donaldson" entry to detect overlap
     c) Post-processing step: if two characters share a name and one entry's evidence completely overlaps the other, flag it for re-attribution
   - **This is the single biggest blocker** — it affects both Characters (6.5→8) and Profiles (5→8)

2. **All physical descriptions missing despite clear text evidence** [Profiles]
   - Problem: All 4 characters have `appearance.summary: "unknown"` despite the text providing vivid descriptions:
     - Uncle Bill: "an elderly, grizzled, small man, grim and unexhilarating" (line ~128)
     - John (boy): "a tall boy... Very olive he was... blue eyes shone out of the dark face from under the same thickset and long lashes" (lines ~91-93)
     - John Donaldson (father): "a big, athletic, grizzled chap, maybe fifty-five or over, shabby as to clothes, yet with an air like a duke" (line ~218)
   - Evidence: `jq '[.characters[] | select(.appearance.summary != "unknown")] | length'` returns 1 (John Donaldson has a confused appearance), but NONE have the text's actual physical descriptions
   - Root cause: The appearance extraction step in the profiling pipeline isn't capturing description-bearing passages. The profiling stage ran for 184s with 5 LLM calls and HIGH confidence, so the LLM was invoked but didn't extract physical details. Likely a prompt issue — the appearance extraction prompt may not emphasize looking for physical description phrases.
   - Location: V2 character profiling — appearance extraction. Check `src/pipeline/character_extraction_v2/` for the appearance/physical description extraction prompt.
   - Fix approach: This is MORE TRACTABLE than issue #1. The text has clear, extractable descriptions. The prompt needs to explicitly instruct: "Look for physical descriptions including height, build, coloring, age, facial features, clothing, and general bearing."

### HIGH

3. **Relationship factual error: cousin called "brother-in-law"** [Profiles / Summaries]
   - Problem: Uncle Bill's relationship to John Donaldson is listed as "brother-in-law (deceased), embezzler, and source of deep shame." The text explicitly says: "Thirty years rolled back, and I saw the charming boy, **a cousin**, who had come to be this lad's father" (line ~28). They are COUSINS, not brothers-in-law.
   - Impact: This error propagates to the summary ("his deceased brother's son") and relationships throughout
   - Root cause: LLM misreads "a cousin, who had come to be this lad's father" — this sentence means the cousin eventually became a father (i.e., had a child), not that the cousin is a brother. The phrase is archaic/literary and trips up models.
   - Location: Relationship extraction in V2 profiling pipeline
   - Fix approach: This is an LLM comprehension error. May improve with a re-run, but is not reliably fixable via code. Could add a post-processing heuristic: if the source text contains "cousin" near a character name, prefer "cousin" over "brother."

4. **Missing character: Ted Frith/Firth** [Completeness]
   - Problem: Ted Frith (also spelled "Firth" once) is a named speaking character who appears in 4+ scenes, delivers key plot information (reporting on the elder Donaldson's heroism), and has dialogue.
   - Evidence: "Ted Frith" appears on multiple lines with dialogue
   - Location: Character extraction — likely filtered by mention count threshold. All 4 characters came from `supporting_*` IDs, suggesting main_cast pipeline didn't fire for this short text.
   - Fix approach: Lower the mention count threshold for short texts, or ensure the main_cast pipeline handles single-chapter texts.

5. **Uncle Bill's example quotes are from OTHER characters** [Profiles]
   - Problem: 3 of 4 example quotes for Uncle Bill are actually spoken BY other characters:
     - "Dear Uncle Bill: Where am I going to in vacation?" — the BOY's letter
     - "You know, Uncle Bill, we were blamed proud to be Red Cross..." — the BOY speaking
     - "Sincerely, Uncle Bill." — a letter sign-off (could be from either)
   - Only "Heaven only knows. I was not his uncle..." is actually Uncle Bill's speech
   - Root cause: Quote extraction is finding quotes that CONTAIN "Uncle Bill" rather than quotes SPOKEN BY Uncle Bill
   - Location: V2 profiling — quote/voice extraction stage
   - Fix: Quote attribution needs speaker identification, not just character name matching

6. **Uncle Bill's personality is unfairly negative** [Profiles]
   - Problem: Uncle Bill is described as "manipulative," "emotionally withholding," and his description says he "inflicts harm" and demonstrates "moral failure." While Uncle Bill IS gruff and conflicted, the text actually portrays him as a caring guardian who takes in his cousin's son, finances his education, and waits at the dock in freezing cold to welcome him home from war.
   - Impact: A narrator would voice Uncle Bill as a villain when he's actually a complex, ultimately caring figure
   - Root cause: The LLM generated an adversarial literary analysis rather than a neutral character profile
   - Location: V2 profiling — personality extraction prompt
   - Fix: The profiling prompt should instruct: "Provide a balanced, neutral character description based on textual evidence. Avoid critical literary analysis or moral judgments."

### MEDIUM

7. **Pronunciation false positives: "magnificence", "manliness", "orderlies"** [Pronunciation]
   - Problem: Common English words flagged for pronunciation guidance. No narrator needs help with these.
   - Location: Pronunciation pipeline — common word filtering
   - Fix: Add these to COMMON_WORDS_WHITELIST or add a check for word length + frequency

8. **Homographs lack IPA and context** [Pronunciation]
   - Problem: "live", "minute", "read", "close", "moderate" are flagged as homographs (correct!) but have no IPA and no context about which pronunciation applies in the text
   - Location: Pronunciation pipeline — IPA generation for homographs
   - Fix: Homographs need text-context analysis to determine which pronunciation applies, then provide that IPA

9. **All pronunciation categories are null** [Pronunciation]
   - Problem: All 24 entries have `category: null` despite clearly being "foreign" (Caporetto), "proper_noun" (Donaldson), or "homograph" (live/read)
   - Location: Pronunciation pipeline — category assignment
   - Fix: Ensure category field is populated during extraction

10. **Summary says "brother" instead of "cousin"** [Summaries]
    - Problem: Summary says "reluctantly responding to a letter from his deceased brother's son" — should be "his late cousin's son"
    - Root cause: Same as issue #3 — LLM misreads the familial relationship
    - Note: The summary is otherwise excellent — comprehensive, well-structured, captures the dual timeline and emotional arc

### LOW

11. **John → John Donaldson relationship listed as "not related (distinct character)"** [Identity Resolution]
    - Problem: John IS John Donaldson's son. The relationship should be "son"
    - Location: Relationship extraction

12. **John Donaldson → Uncle Bill relationship listed as "father"** [Identity Resolution]
    - Problem: John Donaldson is NOT Uncle Bill's father — he's Uncle Bill's cousin
    - Same root cause as issue #3

13. **Uncle Bill's verbal tics include "'Uncle Bill'"** [Profiles]
    - Problem: "Uncle Bill" is how others ADDRESS the narrator, not a verbal tic of his own speech
    - Location: Voice guidance extraction

14. **Evidence for Uncle Bill cites summary text, not source text** [Profiles]
    - Problem: Evidence item 2 quotes: "After wrestling with memories of his own past relationship with John's father—a charming but irresponsible man who vanished after embezzling money and faked his death—the narrator agrees to meet the boy." This is from the GENERATED SUMMARY, not the source text. This is a circular reference.
    - Location: Evidence gathering in V2 profiling — may be pulling from summary output instead of source text

## Pipeline Notes (Attempt 2)
- Model: qwen3-next:80b-a3b-instruct-q8_0 (ollama) for all agents
- 4 characters extracted: John (16), Uncle Bill (18), John Donaldson (7), Joe Barron (3)
- 3 profiles generated with HIGH confidence (vs null profiles in attempt 1)
- 24 pronunciation flags: 19 with IPA, 5 homographs without IPA
- Profiling: 184.56s, 5 LLM calls, 3 items processed (all HIGH confidence)
- All characters from `supporting_*` IDs — main_cast pipeline didn't fire
- Total time: ~12m 8s

## Pipeline Notes (Attempt 3)
- Model: qwen3-next:80b-a3b-instruct-q8_0 (ollama) for all agents
- Competitive consensus: ENABLED (stages: characters, structure, summaries) via --competitive-all
- 8 characters extracted (up from 4): John (16), Uncle Bill/Bill (18), John Donaldson (9), Joe Barron (3), Red Cross (4), + 3 more
- 4 profiles generated with HIGH confidence
- 25 pronunciation flags; categories now populated: proper_noun (6), homograph (5), foreign (4), unknown (10)
- Warning: "Narrator 'John Donaldson' identified but NOT found in main_cast. Available characters: []"
- Warning: "No passages provided for John, returning UNCERTAIN"
- Profiling: 5m 20s, 10 LLM calls, 4 items processed (all HIGH confidence)
- Total time: 14m 39s, 39 LLM calls, 56,216 tokens

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.93 | - | First analysis — profiles empty, character confusion |
| 2 | 7.13 | +0.20 | Profiles populated (but inaccurate), pronunciation false positives fixed |

## Fix History
- Attempt 2: Fixed null character profiles + pronunciation false positives
  - **Profile fix:** Secondary LLM call now triggers when profile is empty — profiles generated for 3/4 characters
  - **Pronunciation fix:** Added common nicknames to COMMON_WORDS_WHITELIST; ForeignProposer checks whitelist
  - Modified: `src/analyzer.py`, `src/pipeline/pronunciation_guide/proposers/cmu_proposer.py`, `src/pipeline/pronunciation_guide/proposers/foreign_proposer.py`
  - Result: Pronunciation improved (7→7.5), Profiles improved (4→5), but core accuracy issues remain

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | (baseline) | N/A | Baseline established |
| 2 | Profiles: null descriptions | src/analyzer.py | Partial — profiles generated but personality/description/physical still have issues |
| 2 | Pronunciation: false positives | cmu_proposer.py, foreign_proposer.py | Fixed — Bill/Joe/was removed |

## Configuration Notes
- Model: qwen3-next:80b-a3b-instruct-q8_0 (ollama) for all agents
- character_llm_chunk_chars: 5000 (appropriate for 5,048 word text)
- All characters came from `supporting_*` IDs — main_cast pipeline may not have fired
- Temperature: 0.7 for all agents (consider lower for character extraction to reduce hallucination)
- No LLM retries recorded

## Priority Fix Guidance for Attempt 3

**Focus areas ranked by score impact:**

1. **Profiles (5→8, +0.45 overall):** The biggest gain. Two sub-fixes:
   a. **Physical descriptions (CRITICAL #2):** Most tractable. The text has crystal-clear physical descriptions. The appearance extraction prompt needs to be more explicit about looking for physical details (height, build, coloring, facial features, clothing). This alone could improve profiles by 1-1.5 points.
   b. **Personality balance (HIGH #6):** The prompts should request neutral, narrator-useful descriptions rather than adversarial literary analysis.

2. **Characters (6.5→8, +0.375 overall):** Add Ted Frith by adjusting mention threshold for short texts. The father/son evidence confusion (CRITICAL #1) is harder — may need position-aware evidence attribution.

3. **Summaries (7→8, +0.20 overall):** The summary is otherwise excellent. The cousin/brother error (MEDIUM #10) may self-correct on re-run, or could be addressed by improving relationship extraction (HIGH #3).

4. **Pronunciation (7.5→8, +0.05 overall):** Quick wins: add "magnificence", "manliness", "orderlies" to common word list. Populate categories. Add IPA for homographs.

**Strategy recommendation:** Focus on issues #2 (physical descriptions) and #7/#8/#9 (pronunciation fixes) as they are code-fixable and together could push profiles to ~6.5 and pronunciation to ~8.0. Issues #1 and #3 (father/son confusion, cousin/brother error) are LLM comprehension issues that are harder to fix systematically but may improve with prompt refinement or a re-run.

## Fix History (Attempt 3)

### Changes Made
1. **Profile context window expanded** (Character Profiles — CRITICAL #2)
   - Root cause: Text snippets around character name mentions (200 char radius) too narrow to capture physical description passages that appear further from the name.
   - Fix: `src/analyzer.py:_generate_character_profile` — context window 200→400 chars each direction.
   - Also improved appearance prompt: "Search the text snippets carefully for physical descriptions (height, build, coloring, hair, eyes, age, clothing, bearing)."
   - Also updated requirement #5 to: "Write from a narrator's practical perspective — balanced, actionable descriptions without literary criticism or moral judgments."
   - Universality: Any book benefits from wider context; not book-specific.

2. **Moral valence ANTAGONIST constraint softened** (Character Profiles — HIGH #6)
   - Root cause: ANTAGONIST constraint said "Profile MUST acknowledge their harmful actions" which forced the LLM to describe Uncle Bill as manipulative/harmful when the text shows him as caring.
   - Fix: `src/pipeline/character_profiling/moral_valence.py` — removed mandatory negative attribution, replaced with "Acknowledge clearly evidenced harmful behaviors, but remain balanced and avoid attributing negative motives without direct textual support."
   - Universality: Any character whose moral valence is misclassified was previously forced into unfair negative portrayal.

3. **Grounding threshold adaptive for short texts** (Character Extraction — HIGH #4)
   - Root cause: min_mentions=3 for supporting cast may filter Ted Frith if he has only 2 text mentions despite appearing in 4+ scenes (scenes can reference characters without restating their name).
   - Fix: `src/agents/characters.py:run()` — adaptive threshold: 2 for texts < 10,000 words, 3 for longer texts.
   - Universality: Short stories (<10K words) have fewer name repetitions per character; lower threshold is appropriate without introducing noise for longer books.

4. **Pronunciation common word whitelist expanded** (Pronunciation — MEDIUM #7)
   - Root cause: "magnificence", "manliness", "orderlies" and related common English words were missing from COMMON_WORDS_WHITELIST.
   - Fix: `src/pipeline/pronunciation_guide/proposers/cmu_proposer.py` — added 18 common English words to whitelist.
   - Universality: These are standard English vocabulary words that no narrator needs pronunciation guidance for.

### Fix Classification
- **Fix types:** threshold adjustment (context window, grounding), prompt clarification (appearance, personality), keyword filter (whitelist — allowed as per guidelines: universal, small, for recognition not rejection)
- **Universality:** All fixes would help a book with a totally different setting (wider context helps any book; lower short-text threshold correct for any short story; softer constraint prevents over-attribution of harm for any character)
- **Smoke test:** Syntax checks passed; pre-existing test failures unchanged (15 failures same as before changes)

## Next Action
Set phase to awaiting_analysis — re-run pipeline to verify fixes.
