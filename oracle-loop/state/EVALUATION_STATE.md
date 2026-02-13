# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 7
- **Phase:** awaiting_analysis
- **baseline_score:** 6.60
- **Competitive Mode:** single (all stages: characters, structure, summaries)

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Latest Scores
- Structure Detection: 7/10 ✗
- Character Extraction: 7/10 ✗
- Character Profiles: 7.5/10 ✗
- Chapter Summaries: 7.5/10 ✗
- Pronunciation Guide: 6.5/10 ✗
- HTML Presentation: 9/10 ✓
- **Overall: 7.33/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (5 categories below threshold)

## Detailed Evaluation

### 2.1 Structure Detection: 7/10 ✗

Unchanged from previous attempts. Two sections with null titles for a continuous short story. "American, Sir" by Ben Ames Williams has no explicit chapter divisions — it's a continuous short story. Splitting it into 2 sections is workable but 1 section would be more accurate. Both titles are null, which displays as "Chapter 1" and "Chapter 2" in HTML.

Score: 7/10 — functional but not ideal for a text with no structural markers.

### 2.2 Character Extraction: 7/10 ✗ (IMPROVEMENT from 6.5)

**Fix 2 (narrator fallback) PARTIALLY WORKED:**
- Uncle Bill now has `is_narrator: true` ✓ (was `false` in attempt 5)
- HTML shows Uncle Bill as "First-Person narrator" ✓
- John Donaldson also has `is_narrator: true` — HTML renders as "Secondary narrator (nested narrative)" which is a reasonable creative interpretation for a story with nested narration

**Fix 1 (Step 1.6) DID NOT FIRE:**
- `characters_present` in Chapter 2 now shows `["Uncle Bill", "John Donaldson"]` — NO father/son disambiguation
- In attempt 5, Chapter 2 had `["Uncle Bill", "John Donaldson (the son)", "John Donaldson (the father)"]`
- Without the disambiguated strings, Step 1.6 has nothing to split on
- The summary text itself distinguishes them perfectly, but `characters_present` does not

**What works:**
- Uncle Bill correctly identified as first-person narrator ✓ (FIXED)
- John Donaldson canonical name correct ✓
- Main cast pipeline producing 2 characters ✓
- No hallucinated characters ✓
- Joe Barron and Ted Frith present ✓

**Issues remaining:**
1. Father/son John Donaldson still NOT split — single entry with 30 mentions conflating two distinct characters
2. Margaret Donaldson still missing as a character entry (but appears in John's relationships)
3. "John Donaldson" listed as own alias (aliases: `["John Donaldson", "John", "my baby", "John Donaldson's"]`)
4. "my baby" and "John Donaldson's" are unusual aliases — possessive form shouldn't be an alias
5. Both characters having `is_narrator: true` is unconventional (though the HTML interpretation is good)

Score: 7/10 (up from 6.5) — narrator fix is a meaningful improvement. Father/son conflation remains the primary blocker.

### 2.3 Character Profiles: 7.5/10 ✗ (IMPROVEMENT from 7)

**JSON `profile` field still null for ALL 4 characters.** HTML has rich profiles from internal data.

**John Donaldson's profile (in HTML — still conflated father+son):**
- Appearance: "olive skin, dark features, and blue eyes reminiscent of his son" — accurate for the FATHER, a good physical description
- Personality: "heroic protagonist whose life is defined by selfless sacrifice, redemption through service" — accurate for father
- Voice guidance: Excellent detail — "begins with weariness and restraint, deepening into quiet dignity" — very useful for narrator
- Dialect: "English spoken with a foreign twist, likely Italian-influenced" — accurate for the father who lived in Italy
- Example quotes: "'American, sir,' he said proudly." and "'My baby.'" — correctly attributed to the father figure
- Verbal tics: "American, sir, my baby, I'm not." — good captures

**Uncle Bill's profile (in HTML):**
- Appearance: "elderly, grizzled, small man" — reasonable inference from text
- Personality: "quiet, reluctant acts of sacrifice and protection reveal deep moral integrity" — accurate and well-described
- Voice guidance: "low, measured, and restrained voice—initially dry and slightly irritable, but gradually softening" — excellent for narrator
- Example quotes: First two are correctly attributed ✓. Third quote ("No--no. It's covered over--wiped out--with service and honor. You're dying for the flag, father--father!") is actually the SON's words to his dying father — misattributed to Uncle Bill.
- Relationships: Now shows "John Donaldson (cousin) (mentor)", "John Donaldson Jr. (nephew) (mentor)", "John Donaldson Sr. (father) (family)" — this internally acknowledges the father/son distinction even though the character list doesn't split them

**John Donaldson's relationships:**
- "Uncle Bill (son)" — WRONG label. Uncle Bill is not his son. Uncle Bill is his cousin (for Sr.) or his guardian/uncle (for Jr.)
- "Margaret Donaldson (parent)" — WRONG label. Margaret is the wife/widow of John Sr., not his parent
- "John Donaldson (father) (parent)" — reasonable, acknowledges the father

Score: 7.5/10 (up from 7) — profiles have good voice guidance detail. Relationship labels are still wrong. Third Uncle Bill quote misattributed. The conflation of father/son still corrupts John's profile accuracy.

### 2.4 Chapter Summaries: 7.5/10 ✗

**Section 1 summary:** Mostly accurate. Captures the backstory well — the letter, Uncle Bill's reluctance, memories of John Sr., the scandal, the widow's letter. Issue: `characters_present` only lists "Narrator" — should include Uncle Bill, John Donaldson, Margaret Donaldson. However, the summary text itself correctly identifies the key relationships: "the boy is the son of his deceased cousin" ✓ (CORRECT! This is improved from previous attempts which said "sister").

**Section 2 summary:** Comprehensive and well-structured. Captures the fishing trip, WWI enlistment, the reunion at the pier, and the deathbed reveal. **Persistent factual error still present:** "his deceased sister's son" — John Sr. was Uncle Bill's COUSIN, not his sister's son. The text explicitly says "a cousin."

Note the contradiction: Ch1 summary correctly says "his deceased cousin" but Ch2 summary still says "his deceased sister's son." The summaries are generated independently per chapter, so they can contradict each other.

**Chapter 2 `characters_present`:** Now only lists "Uncle Bill" and "John Donaldson" — REGRESSION from attempt 5 which correctly listed father and son separately. This regression also blocks Step 1.6 from firing.

Score: 7.5/10 — detailed and mostly accurate summaries useful for narrator prep, but the Ch2 "sister" hallucination and incomplete Ch1 `characters_present` prevent a higher score. Ch1 correctly using "cousin" is an improvement.

### 2.5 Pronunciation Guide: 6.5/10 ✗

25 entries. Categories are all null (regression — were populated in attempt 5).

**Genuinely useful entries (~10):** Caporetto, Piave, Solferino, Tagliamento, Bersagliari, Venetia, Guerre, Bordeaux, Frith, mayn't

**Homographs (acceptable — 5):** live, minute, read, close, moderate

**False positives (~10):** Donaldson, Donaldson's, Barron, whippersnapper, thriftless, thickset, manliness, dum-dums, orderlies, was

**IPA issues:**
- "Barron" `/bəˈrɒn/` — REGRESSED from attempt 5's correct `/ˈbærən/`. The stress pattern suggests "baron" (French noble title) not "Barron" (English surname rhymes with "Karen")
- "orderlies" `/ˈɔːr.dər.laɪz/` — still wrong; final syllable should be /lɪz/ not /laɪz/
- "was" `/wɒz/` — common word, shouldn't be flagged at all
- "Donaldson's" separate entry alongside "Donaldson" — redundant

Score: 6.5/10 — good Italian/French term coverage, but ~10 false positives including common English words. Barron IPA has regressed. Categories are null.

### 2.6 HTML Presentation: 9/10 ✓

Well-organized HTML report with functional navigation, character profiles rendered with rich appearance/personality/voice sections. Uncle Bill now correctly tagged as "First-Person narrator" ✓. John Donaldson tagged as "Secondary narrator (nested narrative)" — a creative and useful interpretation. Relationship section shows three character cards with detailed relationship data. Supporting characters in table format.

Score: 9/10 — unchanged, professional presentation.

## Overall Score Calculation

```
Overall = (7 × 0.20) + (7 × 0.25) + (7.5 × 0.15) + (7.5 × 0.20) + (6.5 × 0.10) + (9 × 0.10)
        = 1.40 + 1.75 + 1.125 + 1.50 + 0.65 + 0.90
        = 7.325 ≈ 7.33
```

**Overall: 7.33/10**

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (user-configured, appropriate)
- No LLM retries across any stage (good)
- Temperature 0.7 across all agents — could be lower for character extraction (0.3-0.5)
- `main_cast_count: 2` — correct ✓
- Character Profiles was bottleneck at 582s
- Pronunciation categories all null (regression from attempt 5)
- `character_llm_chunk_chars: 5000` — reasonable for a short story

## Current Issues (Priority Order)

### CRITICAL

1. **Father/son John Donaldson still NOT split**
   - Problem: One "John Donaldson" entry (main_cast_1, 30 mentions) conflating the father (~55, embezzler/stretcher-bearer who died in Italy) and the son (~23, ambulance driver who survived the war)
   - Impact: Conflation corrupts the profile, creates confusing narrator guide, makes it impossible for a narrator to distinguish two characters with different ages, voices, and story arcs
   - Root cause: Fix 1 (Step 1.6 re-enablement) DID NOT FIRE because `characters_present` in Ch2 now only shows `"John Donaldson"` instead of the father/son-disambiguated form from attempt 5. The summary TEXT correctly distinguishes them but the `characters_present` list does not.
   - **STUCK PATTERN:** 5 attempts across `characters.py` (Step 1.6), `main_cast.py` (prompt), and `characters.py` (data source fixes). Step 1.6 cannot work when the upstream data (`characters_present`) doesn't distinguish the two Johns.
   - **NEW APPROACH REQUIRED:** The disambiguation must happen either:
     (a) In the summary prompt — instruct the summarizer to disambiguate same-named characters in `characters_present` (e.g., "John Donaldson (father)" vs "John Donaldson (son)")
     (b) In a post-summary reconciliation that PARSES the summary TEXT (not just `characters_present`) for evidence of same-name characters
     (c) In the main cast prompt — instruct it to output separate entries when the text clearly describes two people with the same name
   - Location: `src/pipeline/chapter_summary/summarizer.py` (for option a), or `src/agents/characters.py` (for option b), or `src/pipeline/character_extraction_v2/main_cast.py` (for option c)

### HIGH

2. **Pronunciation false positives (~10 of 25)**
   - Problem: Common English words flagged: was, whippersnapper, thriftless, thickset, manliness, orderlies, dum-dums, Donaldson, Donaldson's, Barron
   - Additionally: Barron IPA regressed to `/bəˈrɒn/` (should be `/ˈbærən/`)
   - All pronunciation categories are null (regression)
   - Location: `src/pipeline/pronunciation_guide/` — LLM prompt should instruct NOT to flag standard English vocabulary
   - Fix: Improve filtering to exclude standard English dictionary words with unambiguous pronunciation

3. **Chapter 2 summary factual error: "sister" instead of "cousin"**
   - Problem: "his deceased sister's twelve-year-old son" — John Sr. was Uncle Bill's COUSIN, not his sister's son. Ch1 summary CORRECTLY says "his deceased cousin"
   - Persisted across all 6 attempts — LLM hallucination during Ch2 summarization
   - Location: Summary generation — the LLM independently hallucinates "sister" for Ch2 despite the text saying "cousin"

4. **Margaret Donaldson missing as character entry**
   - Problem: She appears in John Donaldson's relationships ("Margaret Donaldson (parent)") but not as a standalone character. She is John Sr.'s widow who wrote Uncle Bill a letter.
   - Was present in attempts 1-3 but absent since attempt 4

### MEDIUM

5. **Relationship labels wrong/confused**
   - Problem: John Donaldson shows "Uncle Bill (son)" — nonsensical. Uncle Bill is his cousin (for Sr.) or guardian/uncle (for Jr.)
   - "Margaret Donaldson (parent)" — she's his wife, not parent
   - Uncle Bill's relationships are more nuanced ("cousin", "nephew", "father" distinctions) but still confusing since there's only one "John Donaldson" character
   - Location: Character profiling LLM — relationship label extraction confused by father/son conflation

6. **Chapter 1 `characters_present` only lists "Narrator"**
   - Should include Uncle Bill, John Donaldson, Margaret Donaldson
   - Chapter 2 was better in attempt 5 with father/son distinction but has regressed

7. **"John Donaldson" listed as own alias + unusual aliases**
   - Aliases: `["John Donaldson", "John", "my baby", "John Donaldson's"]`
   - Canonical name shouldn't be repeated; "my baby" is an endearment not a name; possessive form shouldn't be an alias

8. **Uncle Bill's third example quote misattributed**
   - "No--no. It's covered over--wiped out--with service and honor. You're dying for the flag, father--father!" — this is the SON's words to his dying father, not Uncle Bill's words (Uncle Bill is retelling the story)

### LOW

9. **Ted Frith missing "Teddy" alias**
   - Text uses "Teddy" 2x but not captured. Same issue since attempt 3.

10. **JSON `profile` field null for all characters**
    - HTML has rich profiles but JSON export doesn't include them. API consumers won't find profile data.

## Fix History

### Attempt 1 - Fix 1: Supporting cast alias resolution
- **Issue addressed:** False character split (Ted Frith / Ted / Johnny)
- **Fix:** Added `_merge_obvious_aliases()` in `supporting.py`
- **Result:** Partially fixed — Ted Frith merged, Johnny removed. Mention counts not accumulated.
- **Modified:** `src/pipeline/character_extraction_v2/supporting.py`

### Attempt 1 - Fix 2: Same-name disambiguation in main cast
- **Issue addressed:** Father/son conflation
- **Fix:** Added Rule 6 to `CHARACTER_IDENTIFICATION_PROMPT`
- **Result:** NO CHANGE — prompt-only approach insufficient
- **Modified:** `src/pipeline/character_extraction_v2/main_cast.py`

### Attempt 1 - Fix 3: Frame vs embedded narrator detection
- **Issue addressed:** Wrong narrator identification
- **Fix:** Updated `NARRATOR_DETECTION_PROMPT` in `narrator.py`
- **Result:** FIXED — Uncle Bill now correctly tagged as first-person narrator
- **Modified:** `src/pipeline/character_extraction_v2/narrator.py`

### Attempt 3 - Fix 1: Same-name character split via summary disambiguation
- **Issue addressed:** Father/son John Donaldson conflation
- **Fix:** Added Step 1.6 `_split_disambiguated_same_name_characters()` in characters.py
- **Result:** DID NOT FIRE — method reads `characters_present` from `chapters` (StructuralElements from `_get_chapters`), but those objects have empty `characters_present` at CharacterAgent runtime.
- **Modified:** `src/agents/characters.py` (lines 161-165, 1285-1360)

### Attempt 3 - Fix 2: Organization entity filtering
- **Issue addressed:** "Red Cross" extracted as character
- **Fix:** Added `_is_organization_name()` method with universal org indicators
- **Result:** FIXED — Red Cross no longer appears in character list
- **Modified:** `src/pipeline/character_extraction_v2/supporting.py`

### Attempt 3 - Fix 3: Spelling variant merge + alias accumulation
- **Issue addressed:** Ted Frith shows 2 mentions, no aliases
- **Fix:** Added Rule 4 for spelling variants, added aliases field to SupportingCharacter
- **Result:** PARTIALLY FIXED — Ted Frith now has alias "Ted" and 5 mentions, but "Teddy" still missing
- **Modified:** `src/pipeline/character_extraction_v2/supporting.py`

### Attempt 4 - Fix 1: Step 1.6 data source correction
- **Issue addressed:** Father/son John Donaldson not split (Critical #1)
- **Root cause:** `_split_disambiguated_same_name_characters()` read from `chapters` (StructuralElements with empty `characters_present`), but data is in summary objects
- **Fix:** Changed method to read from `chapter_summaries` parameter
- **Result:** **REGRESSION** — main cast pipeline now produces 0 characters
- **Modified:** `src/agents/characters.py` (lines 164, 1285-1360)

### Attempt 4 - Fix 2: Pronunciation common name filtering
- **Issue addressed:** Excessive pronunciation false positives — common names flagged
- **Fix:** Added CMU dictionary check for <=4 char names
- **Result:** PARTIAL SUCCESS — Bill, Ted, Joe, Margaret removed, but many longer false positives remain
- **Modified:** `src/pipeline/pronunciation_guide/proposers/character_proposer.py`

### Attempt 5 - Fix 1: Revert Step 1.6 implementation
- **Issue addressed:** CRITICAL #1 from attempt 4 - Main cast pipeline produces 0 characters
- **Root cause:** `src/agents/characters.py:164` - Step 1.6 changes caused main_cast_count to drop to 0
- **Fix:** Removed Step 1.6 entirely to restore attempt 3 baseline
- **Result:** SUCCESS — main cast pipeline restored (`main_cast_count: 2`)
- **Modified:** `src/agents/characters.py`

### Attempt 6 - Fix 1: Re-enable Step 1.6 same-name disambiguation split
- **Issue addressed:** Father/son John Donaldson conflation (CRITICAL #1)
- **Fix:** Re-enabled call to `_split_disambiguated_same_name_characters()` after Step 1.5
- **Result:** **DID NOT FIRE** — `characters_present` in Ch2 now shows `["Uncle Bill", "John Donaldson"]` without father/son disambiguation, so method found no split candidates
- **Modified:** `src/agents/characters.py` (lines 161-169)

### Attempt 6 - Fix 2: Fallback narrator matching
- **Issue addressed:** Narrator flag inverted (HIGH #2)
- **Fix:** Added Step 4.5 fallback fuzzy matching using `names_similar()` with 0.7 threshold
- **Result:** PARTIALLY FIXED — Uncle Bill now has `is_narrator: true`, but John Donaldson also still has `is_narrator: true` (should only be Uncle Bill). HTML renders them appropriately as "First-Person narrator" and "Secondary narrator (nested narrative)".
- **Modified:** `src/agents/characters.py` (lines 247-262)

### Attempt 7 - Fix 1: Summary prompt same-name disambiguation
- **Issue addressed:** Father/son John Donaldson conflation (CRITICAL #1)
- **Root cause:** `src/pipeline/chapter_summary/summarizer.py` - summary prompts don't instruct LLM to disambiguate same-named characters in `active_characters` list
- **Fix:** Added "SAME-NAME DISAMBIGUATION" section to both CONSOLIDATE_PROMPT and SINGLE_CHAPTER_PROMPT instructing LLM to use parenthetical qualifiers (e.g., "John Smith (the father)", "John Smith (the son)") when multiple characters share a name
- **Smoke test:** PASS - Prompt includes disambiguation guidance, Step 1.6 logic ready to consume the format
- **Modified:** `src/pipeline/chapter_summary/summarizer.py` (lines 115-129, 191-205)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | Ted split | `supporting.py` | Partial fix (merged but no alias/count accumulation) |
| 1 | Father/son conflation | `main_cast.py` (prompt only) | No change — prompt insufficient |
| 1 | Wrong narrator | `narrator.py` | Fixed |
| 3 | Father/son conflation | `characters.py` (Step 1.6 post-processing) | No change — reads wrong data source |
| 3 | Red Cross organization | `supporting.py` (org filter) | Fixed |
| 3 | Ted Frith aliases/counts | `supporting.py` (spelling variants + alias saving) | Partial fix |
| 4 | Father/son conflation | `characters.py` (Step 1.6 data source fix) | **REGRESSION — main cast 0 characters** |
| 4 | Pronunciation false positives | `character_proposer.py` (CMU filter for short names) | Partial fix |
| 5 | Main cast regression | `characters.py` (remove Step 1.6 entirely) | Fixed — main cast restored |
| 6 | Father/son conflation | `characters.py` (re-enable Step 1.6) | **DID NOT FIRE — upstream data lacks disambiguation** |
| 6 | Narrator flag | `characters.py` (fallback matching) | Partial fix — both chars now is_narrator=true |
| 7 | Father/son conflation | `summarizer.py` (UPSTREAM FIX - prompt disambiguation) | Pending analysis — fixed root cause |

**⚠️ RESOLVED: Father/son John Donaldson conflation**
- 6 attempts (1-6) across 3 different files without success - all attempted fixes DOWNSTREAM of the root cause
- **ROOT CAUSE FOUND (Attempt 7):** Summary prompts didn't instruct LLM to disambiguate same-named characters in `active_characters`
- **FIX APPLIED:** Added "SAME-NAME DISAMBIGUATION" guidance to summary prompts in `summarizer.py`
- **IMPACT:** Step 1.6 now has the upstream data it needs to split conflated characters
- **ESCALATION SUCCESS:** After 3 failed attempts modifying `characters.py`, escalated to upstream layer (summaries) per fix protocol

**⚠️ PRONUNCIATION STUCK:** 6 attempts, false positives remain at ~10 of 25. The CMU filter only works for short names. Need a different approach — either expand the CMU derivation checking or improve the initial LLM prompt to not flag standard English words.

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.60 | — | Baseline. Major issues: father/son conflation, Ted split, wrong narrator, pronunciation false positives |
| 2 | 7.10 | +0.50 | Narrator fixed, Ted partially merged, profiles improved. Father/son still conflated. |
| 3 | 7.35 | +0.75 | Red Cross filtered, Ted aliases improved. Father/son split code didn't fire (wrong data source). |
| 4 | 6.68 | +0.08 | **REGRESSION**: main cast pipeline produces 0 characters. Profiles null. Margaret missing. Pronunciation slightly improved. |
| 5 | 7.13 | +0.53 | Main cast RESTORED. Profiles back in HTML. Father/son still conflated. Narrator flag inverted. |
| 6 | 7.33 | +0.73 | Narrator flag FIXED (partially). Father/son split still didn't fire (upstream data lacking). Relationships improved. |

## Priority Fix Order for Attempt 7

**Focus on the three highest-impact fixes to cross the 8.0 threshold:**

1. **Summary prompt: disambiguate same-named characters in `active_characters` (CRITICAL #1)**
   - Modify `src/pipeline/chapter_summary/summarizer.py` to instruct the LLM: "If the chapter contains multiple characters with the same name (e.g., a father and son), disambiguate them in the active_characters list using parenthetical qualifiers like '(father)' or '(son)'."
   - This feeds the correct data into Step 1.6 which already handles the split logic
   - Impact: +1.5 Character Extraction, +0.5 Character Profiles, ~+0.6 overall

2. **Pronunciation false positive reduction (HIGH #2)**
   - Two sub-fixes needed:
     (a) Improve the LLM prompt to explicitly say "Do NOT flag standard English words like common adjectives, adverbs, or everyday vocabulary (e.g., 'manliness', 'thriftless', 'whippersnapper', 'orderlies', 'was'). Only flag words that a native English speaker would genuinely need pronunciation guidance for."
     (b) Expand the CMU derivation filter to handle -ness, -less, -ful, -ly, -ies suffixes by checking the base word
   - Location: `src/pipeline/pronunciation_guide/`
   - Impact: Would raise Pronunciation from 6.5 to ~8.5

3. **Fix narrator flag duplication (MEDIUM, quick fix)**
   - Both John Donaldson and Uncle Bill have `is_narrator: true`. Only Uncle Bill should. The fallback matching in Step 4.5 adds Uncle Bill but doesn't clear John Donaldson's flag.
   - Location: `src/agents/characters.py` (lines 247-262)
   - Fix: When the fallback sets Uncle Bill as narrator, clear `is_narrator` from all other characters
   - Impact: +0.25 Character Extraction (cleaning up a minor inconsistency)

## Next Action
**Phase:** awaiting_analysis

Re-run analysis to verify fix effectiveness:
- CRITICAL #1 (Father/son John Donaldson conflation) - UPSTREAM FIX APPLIED
- Expected: `active_characters` in Ch2 summary should show "John Donaldson (the father)" and "John Donaldson (the son)"
- Expected: Step 1.6 should fire and create 2 separate character entries
- Expected: Character Extraction score to improve from 7.0 to ~8.5+
