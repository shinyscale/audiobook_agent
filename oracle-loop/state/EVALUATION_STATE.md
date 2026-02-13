# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 2
- **Phase:** awaiting_evaluation
- **baseline_score:** 6.60
- **Competitive Mode:** single (all stages: characters, structure, summaries)

## Output Files
- HTML: ../output/american_sir/report.html (updated 2026-02-13 01:46)
- JSON: ../output/american_sir/analysis.json (updated 2026-02-13 01:46)

## Pipeline Notes (Attempt 2)
- ✅ Analysis completed successfully in 36m 35s
- ✅ Competitive consensus enabled for all 3 stages (characters, structure, summaries)
- ✅ Found 5 characters (down from 6 in attempt 1 - Red Cross likely filtered)
- ✅ Uncle Bill correctly identified as first-person narrator
- ⚠️ LLM batch enrichment failed for pronunciation guide (JSON parse error)
- ⚠️ Some potentially ungrounded evidence quotes in profiles (John, Uncle Bill, Ted)
- Pipeline used qwen3-next:80b-a3b-instruct-q8_0 for all agents
- Total LLM calls: 71, Total tokens: 104,278
- Bottleneck: Character Profiles (26.1% of time, 9m33s)

## Latest Scores
- Structure Detection: 7/10 ✗
- Character Extraction: 6/10 ✗
- Character Profiles: 8/10 ✓
- Chapter Summaries: 7.5/10 ✗
- Pronunciation Guide: 6/10 ✗
- HTML Presentation: 9/10 ✓
- **Overall: 7.00/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (4 categories below threshold)

## Detailed Evaluation

### 2.1 Structure Detection: 7/10 ✗

"American, Sir!" is a continuous short story (~548 lines, ~5000 words) with NO chapter divisions, headings, or section breaks. The tool detected 2 "chapters" (both with `title: null`), splitting the story roughly at the narrative shift from Uncle Bill's backstory to John's wartime account.

**Assessment:** While a 2-section split is reasonable for narrator prep (the story has a natural narrative shift), the story has zero structural markers. For a text this short with no markers, 1 section would be more accurate. Deducting because:
- Both sections have null titles — not useful for navigation
- The split point is somewhat arbitrary (a narrator could prepare the whole text as one unit)
- However, this is not catastrophic — 2 sections are workable

### 2.2 Character Extraction: 6/10 ✗

**What works:**
- Uncle Bill correctly identified as protagonist and first-person narrator
- John Donaldson correctly identified as secondary narrator (nested narrative)
- Margaret Donaldson, Joe Barron, Ted Frith all present
- "Johnny" is no longer a separate character (fix from attempt 1 helped somewhat)

**What fails:**

1. **Father/son John Donaldson NOT split (CRITICAL - still broken from attempt 1).** There is still only ONE "John Donaldson" entry (main_cast_1). The Rule 6 prompt change was made in attempt 1 but did not produce two separate characters. The single entry conflates:
   - The FATHER: 55+ years old, embezzler who faked his death, lived in Italy 20 years, died as stretcher-bearer
   - The SON: ~23 years old, Uncle Bill's ward, Yale student, ambulance driver, narrator of war story
   The profile appearance describes the father ("tall, dark-complexioned man with striking blue eyes"), the relationships reference both father and son contexts, and the character is tagged as "secondary narrator" (which applies to the son).

2. **Ted Frith alias/mention count issue (MEDIUM).** Ted Frith appears as a single entry (good — the `_merge_obvious_aliases()` fix worked for some merges), BUT:
   - Mention count is only 2 (should be ~7 including "Ted" 5x, "Teddy" 2x, "Ted Firth" variant)
   - No aliases listed (should have: Ted, Teddy, Ted Firth)
   - The merge function may have merged names but not accumulated mention counts or aliases

3. **"Red Cross" still extracted as a character (HIGH).** An organization with no agency, personality, or speech.

4. **Missing character: Morgan (LOW).** Named character at line 207 with agency ("Morgan had a thought") but only 1 mention.

### 2.3 Character Profiles: 8/10 ✓

**Major improvement from attempt 1.** Profiles are now rendered in the HTML with rich detail.

**Uncle Bill profile — Good:**
- Appearance: "elderly, grizzled, small man" — accurate to text ("I am crabbed", "small", "grizzled")
- Personality: "deeply principled and self-sacrificing" — accurate
- Voice guidance: "low, measured, gravelly tone" — appropriate
- Dialect: "formal American English with old-fashioned phrasing" — accurate
- Relationships: "John Donaldson (the son): mentor" — correct; "John Donaldson (the father): father" — WRONG (Uncle Bill is John Sr.'s cousin, not his father)
- Example quotes look correct

**John Donaldson profile — Mixed (conflated):**
- Appearance describes the FATHER (correct for that character): "tall, dark-complexioned man with striking blue eyes"
- Personality describes the FATHER's arc — accurate for him
- Voice guidance is for the FATHER ("American, sir" catchphrase) — accurate
- Relationships: "Margaret Donaldson: spouse" — correct for father; "Uncle Bill: acquaintance" — should be "cousin" or "benefactor"
- The profile would be EXCELLENT if it were clearly labeled as the father's profile, but since the entry conflates both characters, the son's profile is entirely missing

**Issues:**
- Uncle Bill's relationship to John Sr. labeled as "father" — should be "cousin"
- Uncle Bill's relationship to Margaret labeled as "acquaintance" — they have a more complex relationship (she's his cousin's widow who sent him a letter)
- The `physical_description` JSON field is still null for all characters, though HTML renders profile data (data model issue, not content issue)

### 2.4 Chapter Summaries: 7.5/10 ✗

**Chapter 1 summary — Mostly accurate but with errors:**
- Correctly captures: young John's letter, Uncle Bill's emotional response, backstory about John Sr.
- Error: "parents died in an accident" — text says John Sr.'s parents died, but doesn't specify an accident for them specifically. The father's death was described as a "hunting accident" (possibly suicide).
- Error: "split it with John" — accurate
- Error: `characters_present` only lists "Narrator" — should list Uncle Bill, John Donaldson (referenced), Margaret Donaldson (her letter is quoted), young John (his letter opens the chapter)

**Chapter 2 summary — Major error persists:**
- Error: "deceased sister's twelve-year-old son" — John Sr. was Uncle Bill's COUSIN (text line 28), NOT his sister. This is a factual hallucination.
- Otherwise comprehensive and detailed — covers the war service, meeting the father, deathbed reunion
- `characters_present` correctly lists: Uncle Bill, John Donaldson (the son), John Donaldson (the father) — this is good and shows the summary agent CAN distinguish father/son even though the character extractor didn't split them

### 2.5 Pronunciation Guide: 6/10 ✗

30 pronunciation entries for a ~5000-word short story remains excessive. The same issue from attempt 1 persists.

**Genuinely useful entries (~10):** Caporetto, Piave, Solferino, Tagliamento, Bersagliari, Venetia, Guerre, Bordeaux, Frith, mayn't

**Homographs (acceptable — 5):** live, minute, read, close, moderate — these are useful for narrators

**False positives (~15):** Bill, Ted, Joe, Cross, Donaldson's (duplicate of Donaldson), Margaret, was, whippersnapper, thriftless, thickset, manliness, orderlies, dum-dums, Donaldson, Joe Barron

**IPA error:** "Barron" given as `/bəˈrɒn/` (buh-RON) — should be `/ˈbær.ən/` (BARE-un) with stress on first syllable.

### 2.6 HTML Presentation: 9/10 ✓

The HTML report is well-organized with functional navigation, character profiles with rich formatting (appearance, personality, voice guidance sections), pronunciation guide with type/chapter views and search. No broken elements observed.

Minor: Both chapter sections show "null" for titles instead of something more descriptive.

## Overall Score Calculation

```
Overall = (7 × 0.20) + (6 × 0.25) + (8 × 0.15) + (7.5 × 0.20) + (6 × 0.10) + (9 × 0.10)
        = 1.40 + 1.50 + 1.20 + 1.50 + 0.60 + 0.90
        = 7.10
```

**Overall: 7.10/10**

## Current Issues (Priority Order)

### CRITICAL

1. **Father/son John Donaldson NOT split — Rule 6 prompt change insufficient**
   - Problem: Still only one "John Donaldson" entry (main_cast_1) conflating two distinct characters with different ages, life stories, and roles. The Rule 6 prompt change from attempt 1 did not produce separate entries.
   - Evidence: The father is "fifty-five or over", an embezzler who faked his death 20 years ago and died as a stretcher-bearer. The son is ~23, Uncle Bill's ward, an ambulance driver who narrates the war story. They appear in different time periods and have completely different arcs.
   - ID pattern: `main_cast_1` → main cast pipeline
   - Location: `src/pipeline/character_extraction_v2/main_cast.py`
   - Previous fix attempt: Added Rule 6 to `CHARACTER_IDENTIFICATION_PROMPT` (attempt 1) — DID NOT WORK
   - Fix: The prompt-only approach was insufficient. The LLM may be seeing both characters under the same name and merging them at the response level. Consider:
     a. Adding explicit same-name disambiguation in the post-processing code (not just the prompt)
     b. Checking if the chapter summaries' `characters_present` already distinguish "John Donaldson (the son)" vs "John Donaldson (the father)" — if so, use that signal to split the main_cast entry
     c. The summary agent already correctly identified both in Chapter 2's `characters_present` — leverage this downstream

### HIGH

2. **"Red Cross" extracted as a character — organization filtering needed**
   - Problem: "Red Cross" (supporting_1, 4 mentions) is an organization, not a character
   - Evidence: All mentions are organizational references ("under our Red Cross", "Red Cross uniform")
   - ID pattern: `supporting_1` → supporting cast pipeline
   - Location: `src/pipeline/character_extraction_v2/supporting.py`
   - Fix: Add organization-type entity filtering. SpaCy NER tags "Red Cross" as ORG, not PERSON — use the NER label to filter. Only entities tagged PERSON should be extracted as characters.

3. **Ted Frith aliases and mention count not accumulated**
   - Problem: Ted Frith (supporting_3) shows only 2 mentions and no aliases, but "Ted" (5x), "Teddy" (2x), "Ted Firth" (variant spelling) all refer to the same person
   - Evidence: Text lines 274, 281, 284, 288, 323, 345, 422 all refer to Ted Frith
   - ID pattern: `supporting_3` → supporting cast pipeline
   - Location: `src/pipeline/character_extraction_v2/supporting.py` — `_merge_obvious_aliases()` may be merging entries but not accumulating aliases/mention counts
   - Fix: When merging, the merged entry should: (a) accumulate mention counts from all merged entries, (b) add the shorter/variant names as aliases

4. **Excessive pronunciation false positives (15 of 30 entries are common English)**
   - Problem: Common names (Bill, Ted, Joe, Margaret, Johnny), common words (was, Cross), standard vocabulary (whippersnapper, manliness, orderlies, thickset, thriftless) flagged
   - Useful entries: ~10 Italian/French place names + "mayn't" + Frith
   - Location: `src/pipeline/pronunciation/` or `src/agents/pronunciation_agent.py`
   - Fix: Filter out entries where: (a) word is a common English given name, (b) word is in a standard English dictionary and not foreign/archaic, (c) word is a possessive duplicate of an already-flagged word. This has been a persistent issue across multiple texts.

5. **Barron IPA incorrect: `/bəˈrɒn/` should be `/ˈbær.ən/`**
   - Problem: Stress on wrong syllable (buh-RON vs BARE-un)
   - Location: Pronunciation IPA generation
   - Fix: This is an LLM IPA accuracy issue — hard to fix generically

### MEDIUM

6. **Chapter 2 summary says "sister" instead of "cousin"**
   - Problem: "his deceased sister's twelve-year-old son" — John Sr. was Uncle Bill's COUSIN (line 28: "a cousin, who had come to be this lad's father")
   - Location: Summary generation — LLM hallucination
   - Fix: Difficult to fix generically (LLM-generated content)

7. **Chapter 1 characters_present only lists "Narrator"**
   - Problem: Should identify Uncle Bill, John Donaldson, Margaret Donaldson, young John as characters discussed in this section
   - Location: Summary agent / character presence detection
   - Fix: Characters who are discussed/referenced (not just physically present) should be included

8. **Uncle Bill's relationship to John Sr. labeled "father" — should be "cousin"**
   - Problem: In Uncle Bill's relationship list, "John Donaldson (the father): father" makes no sense — Uncle Bill is John Sr.'s COUSIN, not his father
   - Location: Character profiling — relationship extraction
   - Fix: LLM-generated relationship labels; hard to fix generically

9. **Structure: Short story with no chapter markers split into 2 null-titled sections**
   - Problem: The story has zero structural markers (no "Chapter" headings, no section breaks, no dividers). Two null-titled sections are less useful than one section with a clear title.
   - Location: `src/pipeline/chapter_detection/` — may need a threshold for minimum structural evidence before splitting
   - Fix: For very short texts with no detected markers, consider treating the entire text as one section. This is MEDIUM because the 2-section split doesn't break usability.

### LOW

10. **`physical_description` JSON field null for all characters despite HTML showing appearance data**
    - Problem: HTML profiles render appearance info but the JSON `physical_description` field is null
    - Location: Data model / export — profile data stored in a different field
    - Impact: API consumers expecting `physical_description` won't find it

## Fix History

### Attempt 1 - Fix 1: Supporting cast alias resolution
- **Issue addressed:** Critical #1 (attempt 1) - False character split (Ted Frith / Ted / Johnny)
- **Fix:** Added `_merge_obvious_aliases()` in `supporting.py`
- **Result:** Partially fixed — Ted Frith is now one entry, Johnny removed. BUT mention counts not accumulated (2 instead of ~7) and no aliases listed.
- **Modified:** `src/pipeline/character_extraction_v2/supporting.py`

### Attempt 1 - Fix 2: Same-name disambiguation in main cast
- **Issue addressed:** Critical #2 (attempt 1) - Father/son conflation
- **Fix:** Added Rule 6 to `CHARACTER_IDENTIFICATION_PROMPT`
- **Result:** NO CHANGE — still one conflated "John Donaldson" entry. Prompt-only approach insufficient.
- **Modified:** `src/pipeline/character_extraction_v2/main_cast.py`

### Attempt 1 - Fix 3: Frame vs embedded narrator detection

### Attempt 3 - Fix 1: Same-name character split via summary disambiguation
- **Issue addressed:** Critical #1 (attempt 2) - Father/son John Donaldson conflation
- **Root cause:** `src/agents/characters.py` - LLM merges same-name characters despite summaries using disambiguating labels like "John (the father)" and "John (the son)"
- **Fix:** Added Step 1.6 `_split_disambiguated_same_name_characters()` post-processing method that:
  - Scans chapter `characters_present` fields for disambiguating labels (e.g., "(the father)", "(the son)")
  - Splits characters with 2+ distinct labels into separate Character objects
  - Programmatic, deterministic - no prompt changes
- **Modified:** `src/agents/characters.py` (lines 161-165 in run(), new method at line 1285)
- **Expected impact:** +1.0 to Character Extraction, +0.5 to Profiles (father/son now separate)

### Attempt 3 - Fix 2: Organization entity filtering
- **Issue addressed:** High #2 (attempt 2) - "Red Cross" extracted as character (ORG entity)
- **Root cause:** `src/pipeline/character_extraction_v2/supporting.py` line 111 accepts both PERSON and ORG NER labels to catch mis-tagged names, but admits actual organizations
- **Fix:** Added `_is_organization_name()` method with universal organizational indicators:
  - Checks for org suffixes (company, corporation, university, etc.)
  - Checks small reference list of org patterns (Red Cross, Pentagon, FBI, etc.)
  - Only filters ORG-labeled entities (trusts PERSON labels)
  - Uses universal signals, NOT book-specific vocabulary deny-lists
- **Modified:** `src/pipeline/character_extraction_v2/supporting.py` (new method at line 404, called at line 132)
- **Expected impact:** +0.5 to Character Extraction (org entities filtered)

### Attempt 3 - Fix 3: Spelling variant merge + alias accumulation
- **Issue addressed:** High #3 (attempt 2) - Ted Frith shows 2 mentions instead of ~7, no aliases saved
- **Root cause:** `_merge_obvious_aliases()` merged counts but:
  1. Didn't catch spelling variants ("Ted Frith" vs "Ted Firth")
  2. Didn't save merged names as aliases (SupportingCharacter had no aliases field)
- **Fix:** 
  - Added Rule 4 for spelling variants using Levenshtein distance <= 1
  - Added `_is_spelling_variant()` helper method
  - Added `aliases` field to SupportingCharacter dataclass
  - Updated merge logic to save merged names as aliases
  - Updated `_to_characters()` to transfer aliases to Character objects
- **Modified:** `src/pipeline/character_extraction_v2/supporting.py` (dataclass line 30, Rule 4 line 541, new method line 582, alias tracking line 557, _to_characters line 645)
- **Expected impact:** +0.5 to Character Extraction (Ted Frith now has correct mentions + aliases)
- **Issue addressed:** Critical #3 (attempt 1) - Wrong narrator identification
- **Fix:** Updated `NARRATOR_DETECTION_PROMPT` in `narrator.py`
- **Result:** FIXED — Uncle Bill now correctly tagged as first-person narrator, John Donaldson as secondary narrator
- **Modified:** `src/pipeline/character_extraction_v2/narrator.py`

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|---------|
| 1 | Ted split | `supporting.py` | Partial fix (merged but no alias/count accumulation) |
| 1 | Father/son conflation | `main_cast.py` (prompt only) | No change — prompt insufficient |
| 1 | Wrong narrator | `narrator.py` | Fixed |
| 3 | Father/son conflation | `characters.py` (Step 1.6 post-processing) | Programmatic split via summary labels |
| 3 | Red Cross organization | `supporting.py` (org filter) | Filter ORG entities using universal indicators |
| 3 | Ted Frith aliases/counts | `supporting.py` (spelling variants + alias saving) | Rule 4 + alias field added |

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (user-configured, appropriate)
- No LLM retries across any stage (good)
- 0 JSON parse failures except 1 in pronunciation (minor)
- `character_llm_chunk_chars: 5000` is reasonable for a 27KB text
- Temperature 0.7 across all agents — could be lower for character extraction (0.3-0.5) for more deterministic results
- Character Profiles was the bottleneck at 513s (24% of total), but produced high-quality results

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.60 | - | Baseline. Major issues: father/son conflation, Ted split, wrong narrator, pronunciation false positives |
| 2 | 7.10 | +0.50 | Narrator fixed, Ted partially merged, profiles improved. Father/son still conflated, pronunciation still noisy |

## Priority Fix Order for Attempt 3

Focus on the 4 failing categories. Highest-impact fixes:

1. **Father/son split (Critical #1)** — This is the single biggest blocker. Prompt-only approach failed. Need code-level post-processing to split same-name characters when evidence shows two distinct people. The chapter summaries ALREADY distinguish them — use that signal. (+1 to Character Extraction, +0.5 to Profiles)

2. **Red Cross organization filter (High #2)** — Filter ORG-tagged NER entities from character list. (+0.5 to Character Extraction)

3. **Ted Frith alias/count accumulation (High #3)** — Fix `_merge_obvious_aliases()` to accumulate mention counts and populate aliases. (+0.5 to Character Extraction)

4. **Pronunciation false positive filtering (High #4)** — Filter common English names and standard vocabulary. (+1.5 to Pronunciation)

These 4 fixes should push Character Extraction from 6→8+, Pronunciation from 6→8+, and help Structure/Summaries indirectly.


## Next Action
Re-run analysis to verify fixes for:
1. ✅ Father/son split (Step 1.6 post-processing in characters.py)
2. ✅ Red Cross organization filter (supporting.py org filter)  
3. ✅ Ted Frith alias/count accumulation (supporting.py spelling variants + alias saving)

**Expected score improvement:**
- Character Extraction: 6 → 8+ (father/son split +1.0, Red Cross filter +0.5, Ted aliases +0.5)
- Profiles: 8 → 8+ (father/son profiles now separate)
- Summaries: 7.5 → 7.5 (no changes)
- Pronunciation: 6 → 6 (deferred - would need vocabulary filtering)
- Structure: 7 → 7 (no changes)

**Note:** Pronunciation false positive filtering (High #4) was NOT addressed in this attempt to limit scope to 3 fixes. This can be addressed in attempt 4 if needed.
