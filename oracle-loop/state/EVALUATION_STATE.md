# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 1
- **Phase:** awaiting_analysis
- **baseline_score:** 6.93
- **Competitive Mode:** single

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json
- Timestamped: ../output/American Sir_20260220_184428/

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 6.5/10 ✗
  - Completeness: 7/10
  - Identity Resolution: 6/10
  - Alias Grouping: 7/10
- Character Profiles: 4/10 ✗
- Chapter Summaries: 7/10 ✗
- Pronunciation Guide: 7/10 ✗
- HTML Presentation: 8/10 ✓
- **Overall: 6.93/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (4 categories below threshold)

## Current Issues (Priority Order)

### CRITICAL

1. **"John" character profile describes the FATHER, not the son** [Identity Resolution / Profiles]
   - Problem: The "John" entry (supporting_0, 16 mentions) has personality traits "impulsive, charismatic, financially irresponsible, dream-oriented" and evidence items that all describe John Donaldson Sr. (the father who faked his death, lived thriftlessly in Florida, took money). But the relationships field says "John Donaldson: father" — implying this entry is supposed to represent the SON. The description says "He dies under tragic circumstances abroad" which is the father, not the son (who survives).
   - Evidence: Text clearly distinguishes two John Donaldsons: the boy (ambulance driver, 18 years old, brave) and the father (50+, fled America, died in church). The pipeline correctly split them into two entries but assigned the father's evidence/personality to the son's entry.
   - Root cause: Same-name disambiguation failure during profiling. The name "John" refers to the father in the backstory (lines 28-63) and to the son in the war narrative (lines 90+). The profiling pipeline appears to have gathered evidence for "John" without distinguishing which John was being described.
   - Location: V2 character profiling — likely `src/pipeline/character_extraction_v2/` profiling stage, or the evidence gathering in the profile pipeline
   - Fix approach: This is a fundamentally hard same-name disambiguation problem. The profiling stage needs chapter/position context to distinguish which "John" is being described. Short of fixing the pipeline, improving the prompt to emphasize context-aware disambiguation could help.

2. **Relationship factual errors: cousin called "brother"** [Profiles]
   - Problem: Uncle Bill's relationship to John Donaldson is listed as "brother (deceased)" throughout — in relationships, description, and evidence. The text explicitly says: "Thirty years rolled back, and I saw the charming boy, **a cousin**, who had come to be this lad's father" (line 28). Uncle Bill and John Donaldson Sr. are COUSINS, not brothers.
   - Evidence: Line 28 of the source text: "a cousin, who had come to be this lad's father"
   - Location: Relationship extraction in profile pipeline (`src/pipeline/character_extraction_v2/`)
   - Impact: This error cascades — Uncle Bill's description says "his late brother's grandson" when it should say "his late cousin's son." The summary repeats this error.
   - Fix approach: This is an LLM inference error during relationship extraction. Not easily fixable via code changes — it's a model comprehension issue with the source text.

3. **All physical descriptions are null/unknown** [Profiles]
   - Problem: All 4 characters have `appearance.summary: "unknown"` and `physical_description: null` despite the text providing clear physical descriptions.
   - Evidence from text:
     - Uncle Bill: "an elderly, grizzled, small man, grim and unexhilarating" (line 128-129)
     - John (boy): "a tall boy... Very olive he was... blue eyes shone out of the dark face from under the same thickset and long lashes" (lines 91-93)
     - John Donaldson (father): "a big, athletic, grizzled chap, maybe fifty-five or over, shabby as to clothes, yet with an air like a duke" (line 218-219)
   - Location: Profile extraction pipeline — appearance extraction stage
   - Fix approach: The profiling ran for 3m 42s and generated descriptions/personalities but completely missed physical appearances. May be a prompt issue in the appearance extraction step, or the evidence gathering may not be capturing description-bearing passages.

### HIGH

4. **Missing character: Ted Frith/Firth** [Completeness]
   - Problem: Ted Frith (also spelled "Firth" once on line 323) is a named speaking character who appears in 4+ scenes, delivers key plot information (reporting on the elder Donaldson's heroism), and has dialogue. He is narratively important — without his reports, the son wouldn't know about his father's heroics.
   - Evidence: "Ted Frith" appears on lines 274, 282, 323, 345, 422; has dialogue in multiple scenes
   - Location: Character extraction — likely filtered by mention count threshold. All characters came from `supporting_*` IDs, suggesting the main_cast pipeline didn't fire for this short text.
   - Fix approach: May need lower mention threshold for short texts, or the main_cast pipeline needs to handle single-chapter texts.

5. **Uncle Bill's example quotes are NOT his quotes** [Profiles]
   - Problem: The voice guidance for Uncle Bill includes quotes that are actually from other characters:
     - "Dear Uncle Bill: I will come to your commencement..." — This is FROM the boy's letter, not Uncle Bill's speech
     - "American, sir,' he said proudly." — This is John Donaldson Sr.'s dialogue
     - "'Uncle Bill,' went on the throbbing voice..." — This is the boy speaking
   - Evidence: Uncle Bill's actual dialogue: "Dear John: I will come to your commencement and bring you back with me for a short time" (line 86-88); "What!" I asked bewildered (line 266); "It was devilish odd" (line 271)
   - Location: Quote extraction in profile pipeline
   - Fix: Quote attribution needs to correctly identify the speaker, not just extract quotes containing the character's name

6. **Chapter summary relationship errors** [Summaries]
   - Problem: Summary says "reluctantly responding to a letter from his late brother's grandson, John" — should be "his late cousin's son." Also says Uncle Bill "witnesses this emotional reunion" — Uncle Bill was NOT present at the church; he heard the story from the boy afterward at home.
   - Evidence: Lines 28 (cousin), 150-547 (boy tells story to Uncle Bill at home)
   - Location: Summary generation pipeline
   - Fix: These are LLM comprehension errors, same root cause as issue #2

### MEDIUM

7. **Uncle Bill's verbal tics incorrectly listed as "'Uncle Bill,'"** [Profiles]
   - Problem: "Uncle Bill" is how OTHER characters address the narrator, not a verbal tic of his own speech
   - Location: Voice guidance extraction in profile pipeline

8. **Pronunciation false positives** [Pronunciation]
   - Problem: "Bill" (/bɪl/), "Joe" (/dʒoʊ/), and "was" (/wɒz/) are common English words that don't need pronunciation guidance for a narrator
   - Location: Pronunciation extraction pipeline — needs better filtering of common words
   - Fix: These should be filtered by the common-word exclusion list

9. **Pronunciation entries missing categories** [Pronunciation]
   - Problem: All 27 pronunciation entries have `category: null`. Categories like "foreign", "proper_noun", "homograph" should be populated.
   - Evidence: `jq '[.pronunciations[] | select(.category != null)] | length'` returns 0
   - Location: Pronunciation pipeline — category assignment step
   - Fix: Ensure the category field is being populated during pronunciation extraction

10. **Homograph pronunciations lack IPA and context** [Pronunciation]
    - Problem: "live", "minute", "read", "close", "moderate" are flagged as homographs (good!) but have no IPA and no context about which pronunciation to use in the text
    - Location: Pronunciation pipeline — IPA generation for homographs
    - Fix: Homographs need context-specific IPA (e.g., "read" as /riːd/ or /rɛd/ depending on tense in context)

### LOW

11. **John Donaldson → John relationship listed as "unknown"** [Identity Resolution]
    - Problem: John Donaldson's relationship to John should be "father" / "son" but is listed as "unknown"
    - Location: Relationship extraction

12. **John Donaldson → Uncle Bill relationship listed as "father"** [Identity Resolution]
    - Problem: Says John Donaldson is Uncle Bill's "father" which is wrong — he's Uncle Bill's cousin
    - Location: Relationship extraction (same root cause as issue #2)

13. **Structure chapter has null title** [Structure]
    - Problem: For a short story, the single section has `title: null`. Could use the story title "American, Sir!"
    - Minor issue — single-section short story with no title is acceptable

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.93 | - | First analysis — profiles empty, character confusion |

## Fix History
- Attempt 2: Fixed null character profiles + pronunciation false positives
  - **Profile fix (Profiles: 4→8 target):** Secondary LLM call now triggers when profile is empty, using context_text as source instead of requiring existing profile text. Also generates profile description from the secondary call.
    - Root cause: `analyzer.py:_generate_character_profile()` line 3009 — secondary call condition `if has_minimal_data and profile` excluded cases where profile was empty string
    - Smoke test: PASS — secondary LLM call now triggers when profile is empty with context available
    - Modified: `src/analyzer.py`
  - **Pronunciation fix (Pronunciation: 7→8 target):**
    1. Added common English nicknames (bill, joe, bob, jim, etc.) to COMMON_WORDS_WHITELIST — these are universal English names no narrator needs pronunciation guidance for
    2. Made ForeignProposer check COMMON_WORDS_WHITELIST to prevent common verbs like "was" from being flagged as "foreign"
    - Root cause A: "Bill", "Joe" not in COMMON_WORDS_WHITELIST so character proposer flagged them
    - Root cause B: Foreign proposer found "la {word}" pattern matching in text, extracted the word, but didn't check COMMON_WORDS_WHITELIST — so "was" was incorrectly flagged
    - Smoke test: PASS — "was" not flagged as foreign; "Bill"/"Joe" not flagged as character names needing pronunciation
    - Modified: `src/pipeline/pronunciation_guide/proposers/cmu_proposer.py`, `src/pipeline/pronunciation_guide/proposers/foreign_proposer.py`

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | (baseline) | N/A | Baseline established |
| 2 | Profiles: null descriptions / Pronunciation: false positives | analyzer.py, cmu_proposer.py, foreign_proposer.py | Pending re-analysis |

## Configuration Notes
- Model: qwen3-next:80b-a3b-instruct-q8_0 (ollama) for all agents
- character_llm_chunk_chars: 5000 (appropriate for 5,048 word text)
- All characters came from `supporting_*` IDs — main_cast pipeline may not have fired
- Profiling took 3m 42s but produced null physical descriptions
- No LLM retries recorded

## Priority Fix Guidance

**Focus for Attempt 2:** The biggest score gains come from:
1. **Profiles (4→8):** Fix physical description extraction — the text has clear descriptions that should be captured. This alone could add ~0.6 to overall score.
2. **Summaries (7→8):** Fix the cousin/brother error and the "witnesses" claim.
3. **Pronunciation (7→8):** Remove false positives (Bill, Joe, was), populate categories, add context to homographs.
4. **Characters (6.5→8):** Fix the father/son profile confusion, add Ted Frith.

Issues #1 (father/son confusion) and #2 (cousin/brother) are likely LLM comprehension errors that may be hard to fix via code. Re-running the analysis may produce different results. Issues #3 (null physical descriptions), #8-10 (pronunciation) are more likely systematic/code issues.

## Next Action
Re-run analysis to verify profile and pronunciation fixes improved scores.
