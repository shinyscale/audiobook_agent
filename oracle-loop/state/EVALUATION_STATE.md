# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 2
- **Phase:** awaiting_evaluation
- **baseline_score:** 6.60
- **Competitive Mode:** single

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Pipeline Notes (Attempt 2)
- Analysis completed successfully in 35m 23s
- Narrator correctly detected: "Uncle Bill (first-person)"
- 6 characters extracted (need to verify if father/son John Donaldson are now split)
- 30 pronunciation flags (same as attempt 1 - may still have false positives)
- Warnings: F19 ungrounded evidence quotes for Uncle Bill (3) and John Donaldson (6)
- Competitive consensus enabled for characters, structure, and summaries (2/3 supermajority)

## Latest Scores
- Structure Detection: 7/10 ✗
- Character Extraction: 5/10 ✗
- Character Profiles: 7/10 ✗
- Chapter Summaries: 7.5/10 ✗
- Pronunciation Guide: 6/10 ✗
- HTML Presentation: 9/10 ✓
- **Overall: 6.60/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (5 categories below threshold)

## Current Issues (Priority Order)

### CRITICAL

1. **False character split: Ted Frith / Ted / Teddy / Johnny**
   - Problem: "Ted Frith" (supporting_5, 2 mentions) and "Ted" (supporting_6, 5 mentions) are listed as separate characters. They are the same person: Ted Frith, who is also called "Ted", "Teddy", and even "Ted Firth" (variant spelling in text line 323). Additionally, "Johnny" (supporting_7, 2 mentions) is NOT a separate character — it is Ted's nickname for John Donaldson the son (lines 326, 349: "'That you, Johnny?' he shouted").
   - Evidence: Text lines 274, 281, 284, 288, 323, 345, 422 all refer to the same person Ted Frith. Lines 326 and 349 show Ted calling the son "Johnny".
   - ID patterns: `supporting_5` (Ted Frith), `supporting_6` (Ted), `supporting_7` (Johnny) → Fix in supporting cast pipeline
   - Location: `src/pipeline/character_extraction_v2/supporting.py` - alias/merge logic for supporting cast
   - Fix: Ted Frith should be a single entry with aliases ["Ted", "Teddy", "Ted Firth"]. "Johnny" should be an alias of John Donaldson (the son), not a separate character.

2. **Father/Son conflation: Single "John Donaldson" entry blends two distinct characters**
   - Problem: There is only one "John Donaldson" entry (main_cast_2) but the story has TWO distinct John Donaldsons: the father (who faked his death, lived in Italy 20 years, died as a stretcher-bearer in WWI) and the son (Uncle Bill's ward, ambulance driver, who tells the war story). The physical description on the entry ("middle-aged man with dark, olive skin and striking blue eyes") is the FATHER's appearance, yet the entry is tagged as narrator (which would be the son's role). The relationships are also mixed: "parent" of "John Donaldson (son)" is a father relationship, but "Uncle Bill: victimizer" makes no sense for either.
   - Evidence: The son is a young man (~23 in 1919) while the father is "fifty-five or over" and has been living in Italy for 20 years. They are distinct characters who share a name.
   - ID pattern: `main_cast_2` → Fix in main cast pipeline
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` - same-name character disambiguation
   - Fix: These should be two separate characters: "John Donaldson (the son)" and "John Donaldson (the father)" or similar disambiguation.

3. **Wrong narrator identification**
   - Problem: "John Donaldson" (main_cast_2) is marked as `is_narrator: true` with the badge "Secondary narrator (nested narrative)". The PRIMARY narrator of the entire story is Uncle Bill — it's told entirely in first person from his perspective ("I threw the letter in the scrap-basket", "I am crabbed and prejudiced"). Uncle Bill (main_cast_1) is marked `is_narrator: false`, which is wrong. The son John does narrate a nested story (the war account), but Uncle Bill is the frame narrator.
   - Evidence: The story opens with Uncle Bill narrating in first person and closes with him narrating. The son's war story is quoted speech within Uncle Bill's narration.
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` or `src/agents/characters.py` - narrator detection logic
   - Fix: Uncle Bill should be `is_narrator: true`. John Donaldson (the son) could be a secondary narrator.

### HIGH

4. **"Red Cross" extracted as a character**
   - Problem: "Red Cross" (supporting_3, 4 mentions) is an organization, not a character. It has no agency, personality, or speech in the text.
   - Evidence: All mentions are references to the organization (e.g., "under our Red Cross", "Red Cross uniform").
   - ID pattern: `supporting_3` → Fix in supporting cast pipeline
   - Location: `src/pipeline/character_extraction_v2/supporting.py` - organization filtering
   - Fix: Organizations without agency should be filtered out of character extraction.

5. **Incorrect relationship: Uncle Bill labeled as "victimizer" of John Donaldson**
   - Problem: The relationship "Uncle Bill: victimizer" on John Donaldson's profile is factually wrong. Uncle Bill was John Sr.'s benefactor — he split his inheritance with John, covered up John's financial scandal, and repaid stolen money. If anything, Uncle Bill was the victim of John's actions, not the victimizer.
   - Evidence: Text lines 44-57: "I split my unimpressive patrimony in two", "I pulled him out and hushed up the story and repaid the money"
   - Location: Character profiling pipeline - relationship extraction
   - Fix: Relationship should be "benefactor" or "guardian", not "victimizer".

6. **Missing character: Morgan**
   - Problem: Morgan is mentioned at line 207 as someone who has a significant idea ("Morgan had a thought") that drives the plot forward — his suggestion to recruit American civilians in Italy. While minor (1 mention), he's a named character with agency.
   - Severity: Minor but notable for completeness.
   - Location: Supporting cast extraction threshold may be too high.

7. **Excessive false positives in pronunciation guide**
   - Problem: 31 pronunciation entries is too many for a ~5000-word short story. Many entries are common English words that no narrator would need help with:
     - "Bill" (/bɪl/) — extremely common English name
     - "Ted" (/tɛd/) — extremely common English name
     - "Joe" (/dʒoʊ/) — extremely common English name
     - "Cross" (/krɒs/) — common English word
     - "was" (/wɒz/) — one of the most common English words
     - "manliness", "orderlies", "thickset", "whippersnapper" — standard English vocabulary
     - "Donaldson's" — duplicate of "Donaldson" (possessive form)
     - "Margaret" — common English name
     - "Johnny" — common English name
     - "dum-dums" — slang already explained in the text ("that's beans, Uncle Bill")
   - Evidence: Only about 8-10 entries are genuinely useful: Caporetto, Piave, Solferino, Tagliamento, Bersagliari, Venetia, Guerre, Bordeaux, Frith, Barron, mayn't
   - Location: `src/pipeline/pronunciation/` or `src/agents/pronunciation_agent.py` - false positive filtering
   - Fix: Filter out common English words, common given names, and standard vocabulary.

### MEDIUM

8. **Structure detection: Short story split into 2 "chapters" but has no chapter divisions**
   - Problem: "American, Sir!" is a continuous short story with no chapter breaks. The tool detected 2 chapters, splitting at approximately line 90 (after Uncle Bill agrees to take John in). Both chapters have `title: null`. While a reasonable narrative break point, the story is a continuous narrative with no structural markers.
   - Evidence: The source text has no "Chapter" headings, section breaks, or dividers. It flows continuously.
   - Location: `src/pipeline/chapter_detection/` - narrative break detection may be too aggressive for short stories
   - Fix: For very short texts (~5000 words) with no structural markers, treating the whole text as a single section may be more appropriate. However, the 2-section split is not terrible for narrator prep purposes, so this is medium severity.

9. **Chapter 2 summary error: "deceased sister's twelve-year-old son"**
   - Problem: The summary says "Ten years after receiving a letter asking him to take in his deceased sister's twelve-year-old son" — John Sr. was NOT Uncle Bill's sister. He was Uncle Bill's cousin ("I saw the charming boy, a cousin, who had come to be this lad's father", line 28).
   - Evidence: Text line 28 explicitly says "cousin".
   - Location: Summary generation - factual accuracy
   - Fix: This is an LLM hallucination in the summary. Hard to fix generically.

10. **Chapter 1 character list only shows "Narrator"**
    - Problem: Chapter 1's characters_present only lists "Narrator" as a generic label. It should identify Uncle Bill (the narrator), John Donaldson Sr. (discussed extensively in memory), Margaret Donaldson (her letter is quoted), and young John (his letter opens the chapter).
    - Evidence: Chapter 1 discusses John Sr., Margaret, and young John extensively even though they don't physically "appear" — for narrator prep, knowing which characters are discussed is important.
    - Location: Summary agent / character presence detection

11. **No physical descriptions populated in JSON** (0/8 characters have `physical_description`)
    - Problem: The JSON `physical_description` field is null for all characters, yet the HTML profile section shows appearance information. The profile data may be stored in a different field than `physical_description`.
    - Evidence: HTML shows "Uncle Bill is an elderly man with a reserved, unassuming physical presence" and John Donaldson has "very olive skin, blue eyes with thickset and long lashes" — these are present in the rendered profile but not in the `physical_description` JSON field.
    - This may be a data model issue rather than a content issue. The profiles ARE rendered.

12. **Barron pronunciation stress pattern incorrect**
    - Problem: "Barron" is given IPA `/bəˈrɒn/` (stress on second syllable: buh-RON). The standard English pronunciation of the surname Barron is `/ˈbær.ən/` (BARE-un), with stress on the FIRST syllable.
    - Location: Pronunciation enrichment IPA generation

### LOW

13. **"Ted" supporting character has a description that confuses Ted with the father**
    - Problem: The "Ted" character description says "A heroic figure whose selfless actions under fire—volunteering for frontline duty, distributing comfort, and repeatedly risking his life to carry the wounded" — this description actually fits John Donaldson the father more than Ted. Ted reported on the father's heroism but didn't personally do the stretcher-bearing.
    - This would be moot if Ted/Ted Frith are properly merged (Critical #1).

## Fix History

### Attempt 1 - Fix 1: Supporting cast alias resolution
- **Issue addressed:** Critical #1 - False character split (Ted Frith / Ted / Johnny)
- **Root cause:** Supporting cast extractor had NO alias resolution or merge logic - all NER-extracted names treated as separate characters
- **Fix:** Added deterministic merge logic (`_merge_obvious_aliases()`) in `supporting.py` after NER extraction
- **Approach:**
  - Substring matching: "Ted" merges into "Ted Frith" (shorter name is substring of longer)
  - Word overlap: Single-word names that appear in multi-word names (e.g., "Ted" in "Ted Frith")
  - Nickname patterns: Common -y/-ie diminutives (e.g., "Johnny" for "John", "Teddy" for "Ted")
  - Conservative: No LLM calls, deterministic rules only
- **Smoke test:** PASS - Correctly merged "Ted" (5 mentions) + "Ted Frith" (2 mentions) → "Ted Frith" (7 mentions)
- **Modified:** `src/pipeline/character_extraction_v2/supporting.py`
- **Universal applicability:** YES - Applies to all books with characters called by multiple names

### Attempt 1 - Fix 2: Same-name disambiguation in main cast
- **Issue addressed:** Critical #2 - Father/son conflation (both named "John Donaldson")
- **Root cause:** Prompt had rules for "similar names" (John vs John Donaldson) but not for EXACT name duplicates with different biographies
- **Fix:** Added Rule 6 to `CHARACTER_IDENTIFICATION_PROMPT` in `main_cast.py`:
  - "If summaries clearly describe TWO distinct people with the EXACT SAME name, you MUST create TWO separate character entries with disambiguation"
  - Examples: "John Donaldson (the father)" and "John Donaldson (the son)"
  - Look for biographical differences: different ages, time periods, relationships, one deceased while other is alive
- **Smoke test:** N/A (prompt change, requires full re-analysis to verify)
- **Modified:** `src/pipeline/character_extraction_v2/main_cast.py`
- **Universal applicability:** YES - Common in literature (Hamlet Sr./Jr., Russian novels with multiple "Ivan"s, etc.)

### Attempt 1 - Fix 3: Frame vs embedded narrator detection
- **Issue addressed:** Critical #3 - Wrong narrator identification (John marked as narrator instead of Uncle Bill)
- **Root cause:** Narrator detection prompt didn't distinguish frame narrator (outermost voice) from embedded narrators (characters who tell stories within the frame)
- **Fix:** Updated `NARRATOR_DETECTION_PROMPT` in `narrator.py`:
  - Emphasized "identify the PRIMARY/FRAME narrator as the narrator_name"
  - Added instruction: "The frame narrator is the one whose voice opens and closes the story"
  - Clarified distinction: narrator_name = frame narrator, nested_narrators = all narrators in order
- **Smoke test:** N/A (prompt change, requires full re-analysis to verify)
- **Modified:** `src/pipeline/character_extraction_v2/narrator.py`
- **Universal applicability:** YES - Standard narrative structure in Frankenstein, Wuthering Heights, Heart of Darkness, etc.

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | Critical #1 (Ted split) | `src/pipeline/character_extraction_v2/supporting.py` | Added `_merge_obvious_aliases()` method |
| 1 | Critical #2 (father/son) | `src/pipeline/character_extraction_v2/main_cast.py` | Added Rule 6 for exact name duplicates |
| 1 | Critical #3 (wrong narrator) | `src/pipeline/character_extraction_v2/narrator.py` | Emphasized frame narrator detection |

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (user-configured, appropriate)
- No LLM retries across any stage (good)
- `character_llm_chunk_chars: 5000` is reasonable for a 27KB text
- Temperature 0.7 across all agents — could be lower for character extraction (0.3-0.5) for more deterministic results
- No profiling anomalies

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.60 | - | Baseline. Major issues: father/son conflation, Ted split, wrong narrator, pronunciation false positives |

## Next Action
Re-run analysis with fixes applied to verify:
1. Ted Frith/Ted merge (supporting cast alias resolution)
2. Father/son John Donaldson split (same-name disambiguation)
3. Uncle Bill identified as primary narrator (frame narrator detection)

Run PROMPT_analyze.md for attempt 2.
