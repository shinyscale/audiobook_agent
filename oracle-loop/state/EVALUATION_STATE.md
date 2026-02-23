# Current Evaluation State

## Active Text
- **Name:** john_g
- **Attempt:** 1
- **Phase:** awaiting_analysis
- **baseline_score:** 7.55
- **Competitive Mode:** single

## Output Files
- HTML: ../output/john_g/report.html
- JSON: ../output/john_g/analysis.json
- Timestamped: ../output/John G - Katherine Mayo_20260222_215614/

## Pipeline Notes
- Completed in 13m 8s, 30 LLM calls, 38,017 tokens
- 2,228 words extracted (short text)
- 1 chapter detected (single chapter story)
- 6 characters total (3 from extraction + 3 reconciled from summaries)
- 5 profiles generated with HIGH confidence
- 20 pronunciation flags (7 homograph, 6 proper_noun, 6 unknown, 1 foreign)
- Warnings: "LLM marker proposer returned non-list" → fell back to single chapter
- Warnings: "No passages provided for John / Two Troopers / First Sergeant Price" → UNCERTAIN
- Character contamination: 'John' profile corrected for same-name contamination with 'John G.'
- No narrator identified

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 6/10 ✗ (FAILING)
  - Completeness: 7/10
  - Identity Resolution: 5/10 ← false split is primary blocker
  - Alias Grouping: 5/10
- Character Profiles: 7/10 ✗ (FAILING)
- Chapter Summaries: 8/10 ✓
- Pronunciation Guide: 7/10 ✗ (FAILING)
- HTML Presentation: 9/10 ✓
- **Overall: 7.55/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold: Characters 6, Profiles 7, Pronunciation 7)

## Current Issues (Priority Order)

### CRITICAL
1. **False character split: "John" vs "John G."** [Identity Resolution]
   - Problem: "John G." (15 mentions, id: supporting_0) and "John" (4 mentions, id: supporting_1) are listed as separate characters. They are the SAME entity — John G. is a horse, and "John" is used as a short form of address on lines 126, 131, 133, 159 of the source text (e.g., "Come along, John, it's all right, old man!")
   - Evidence: Both profiles describe horse-like behavior; the "John" profile says "exhibits calmness, caution, and quiet resilience under stress" with traits like "cautious, reliable, resilient" — clearly describing the same horse
   - IDs: supporting_0 (John G.) and supporting_1 (John) — both from supporting cast pipeline
   - Location: `src/pipeline/character_extraction_v2/supporting.py` — alias resolution should recognize "John" as a short form of "John G."
   - Fix: The supporting cast or alias resolution logic needs to recognize that when a character named "X Y" exists and a separate entry "X" appears with far fewer mentions, "X" is very likely a short form. Especially when one entity is central to the narrative.

### HIGH
2. **Alias "John\nG." contains literal newline** [Alias Grouping]
   - Problem: The alias list for "John G." contains `"John\nG."` with a literal newline between "John" and "G." — this displays as a line break in the HTML report
   - Evidence: `jq` output shows `"John\nG."` in alias array
   - Location: Likely in text extraction/parsing or alias generation in `src/pipeline/character_extraction_v2/`
   - Fix: Strip or normalize whitespace (including newlines) in alias strings before storing

3. **Missing aliases for John G.** [Alias Grouping]
   - Problem: "John" should be listed as an alias (not a separate character). Additional terms of address "Johnny boy" (line 161) and "old man" (lines 126, 159, used as direct address) are also missing
   - Evidence: Text uses "Come along, John, old man" and "Make a pace, Johnny boy!" as direct addresses for the horse
   - Location: `src/pipeline/character_extraction_v2/` — alias detection
   - Fix: After merging "John" into "John G.", ensure "John", "Johnny boy" are captured as aliases

4. **Greensburg pronunciation uses German IPA instead of American English** [Pronunciation]
   - Problem: IPA is `/ˈɡʁɛnˌzʊʁk/` with phonetic "GREHN-zoork" — this is German pronunciation. Greensburg, Pennsylvania is an American city pronounced `/ˈɡriːnzbɜːrɡ/` (GREENZ-burg)
   - Evidence: The story is set in Pennsylvania ("hill-town of Greensburg", "Pennsylvania State Police")
   - Location: `src/pipeline/pronunciation.py` or pronunciation agent — the LLM is providing German pronunciation for an American place name
   - Fix: Context should help the LLM understand this is an American English text; place names should be pronounced in the language of the narrative

5. **"sharp-fanged" IPA is wrong** [Pronunciation]
   - Problem: IPA shows `/feɪnd/` for "fanged" (rhymes with "frayed"), but correct pronunciation is `/fæŋd/` (rhymes with "banged"). Note says "the 'g' is silent" which is incorrect — "fanged" has a hard /ŋ/ sound
   - Location: Pronunciation agent LLM generation
   - Fix: This is an LLM accuracy issue; may need better verification or dictionary lookup

6. **Excessive false positive proper nouns in pronunciation** [Pronunciation]
   - Problem: 6 out of 20 pronunciation entries are common English words that any professional narrator knows: "Sergeant", "Corporal", "Price", "Adams", "Richardson", "Troopers"
   - Evidence: These are standard English words/surnames; a narrator preparation guide should flag unusual or tricky words, not common ones
   - Location: Pronunciation flagging logic in `src/pipeline/pronunciation.py`
   - Fix: Add filtering for common English military ranks and common English surnames

### MEDIUM
7. **Corporal Richardson's relationship to Price described as "tense"** [Profiles]
   - Problem: Listed as "subordinate-to-superior (tense professional relationship)" but the text shows a warm, bantering dynamic — the Sergeant jokes about grooming a horse with "teeth and toes" and Richardson responds with gentle philosophy
   - Evidence: Lines 238-264 show mutual respect and humor, not tension
   - Location: Character profile generation in `src/pipeline/character_extraction_v2/` or profile agent
   - Fix: LLM accuracy issue in relationship characterization

8. **Plot summary hallucination: "John G. collapses"** [Profiles/Summaries]
   - Problem: The plot summary says "John G., the stalwart horse who carried them through the trestle, collapses from physical depletion" — the text never says John G. collapses. He has a "smoking back" (steaming from exertion) and Richardson brings medicine, but the horse doesn't collapse. In fact, after 3 hours of care "not a wet hair was left on him" and next morning he "walked out of his stall as fresh and as fit as if he had come from pasture"
   - Evidence: Source text lines 221-268
   - Location: Summary/overview generation
   - Fix: LLM hallucination — the summary agent embellished the horse's condition

9. **Missing pronunciation entries for notable terms** [Pronunciation]
   - Problem: Missing entries for "Allegheny" (river name, common mispronunciation), "Tien Tsin" (only "Tsin" flagged, not full place name), "I. W. W." (acronym — Industrial Workers of the World)
   - Location: Pronunciation flagging
   - Fix: These are genuinely useful entries for a narrator

10. **Chapter characters list missing John G.** [Presentation]
    - Problem: The chapter's "Characters Present" list shows First Sergeant Price, Captain Adams, Corporal Richardson, Two Troopers — but NOT John G., who is the title character and central to the entire story
    - Evidence: HTML report chapter card, line 948-961
    - Location: Chapter summary character extraction or structure agent
    - Fix: John G. should appear in characters_present for the chapter

### LOW
11. **"Two Troopers" as a character entry** [Completeness]
    - Problem: "Two Troopers" is a collective reference, not a named individual. While acceptable for narrator prep, it's unusual as a character entry
    - This is not blocking — just notable

12. **No narrator identified for third-person narrative** [Profiles]
    - Problem: The narrative is third-person limited (following Price). No narrator is flagged. For an audiobook narrator, knowing the POV style would be useful
    - Evidence: The overview correctly identifies "third-person limited" narrative style
    - This is not blocking — the overview captures it

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 7.55 | — (baseline) | 3 categories failing: Characters 6, Profiles 7, Pronunciation 7 |

## Fix History
- Attempt 2: Three fixes applied:
  1. **Newline normalization in NER entity names** — `supporting.py:extract():116`: changed `ent.text.strip()` to `re.sub(r"\s+", " ", ent.text).strip()`. Prevents "John\nG." artifact when text has line breaks inside names. Universal fix for any book with line-wrapped proper nouns.
  2. **First-name+initial merge in supporting cast** — `characters.py:_merge_within_supporting_cast():~2681`: Added "firstname of initial name" pattern: when a single-word name matches the first part of a "FirstName LastInitial." name (e.g., "John" + "John G."), they're merged unconditionally (regardless of mention count). Ambiguity guard: only merges when exactly ONE candidate matches. Universal fix for any book using initial-style names (military fiction, period fiction).
  3. **Greensburg German IPA fix** — `foreign_proposer.py:_validate_with_llm():264`: Updated LLM validation prompt to explicitly note that capitalized proper nouns (place names, personal names) with foreign-origin spellings are English words, not foreign. Prevents Greensburg and similar American place names from receiving German IPA.
  - Root causes: (1) no internal whitespace normalization at NER extraction; (2) first-name match threshold (≤3 mentions) too conservative for initial-style names; (3) LLM validation prompt insufficient guidance on proper noun vs foreign word distinction
  - Smoke tests: PASS — verified merging works for "John G."+"John" case and ambiguous case is correctly skipped

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 2 | CRITICAL: false split + newline alias + Greensburg IPA | supporting.py, characters.py, foreign_proposer.py | awaiting analysis |

## Next Action
Run PROMPT_analyze.md to re-analyze with fixes applied.
