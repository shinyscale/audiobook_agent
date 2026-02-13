# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 6
- **Phase:** awaiting_evaluation
- **baseline_score:** 6.60
- **Competitive Mode:** single (all stages: characters, structure, summaries)

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Pipeline Notes
- Completed in 37m 27s
- 4 characters extracted (John Donaldson: 30 mentions, Uncle Bill: 18 mentions, Joe Barron: 3 mentions, Ted Frith: 5 mentions)
- 2 chapters detected
- 25 pronunciation entries (11 unknown, 5 foreign, 5 homograph, 4 proper_noun)
- 73 LLM calls total, 109,481 tokens
- 1 JSON parse failure in pronunciation (model compatibility issue with batch enrichment)
- Competitive consensus ENABLED for characters, structure, and summaries (2/3 supermajority voting)
- Bottleneck: Character Profiles (25.9% of time, 9m 42s)

## Latest Scores
- Structure Detection: 7/10 ✗
- Character Extraction: 6.5/10 ✗
- Character Profiles: 7/10 ✗
- Chapter Summaries: 7.5/10 ✗
- Pronunciation Guide: 6.5/10 ✗
- HTML Presentation: 9/10 ✓
- **Overall: 7.08/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (5 categories below threshold)

## Detailed Evaluation

### 2.1 Structure Detection: 7/10 ✗

Unchanged from previous attempts. Two sections with null titles for a continuous short story. The text "American, Sir" by Ben Ames Williams has no explicit chapter divisions — it's a continuous short story. Splitting it into 2 sections is workable for a narrator, but 1 section would be more accurate. Both titles are null, which displays as "Chapter 1" and "Chapter 2" in HTML.

**What works:** The structure is usable. Two sections is reasonable for a story of this length (~5000 words).

**Issues:**
- Null titles (minor — the story has no chapter names)
- Arguably should be 1 section for a chaptered short story

Score: 7/10 — functional but not ideal for a text with no structural markers.

### 2.2 Character Extraction: 6.5/10 ✗ (IMPROVEMENT from 5)

**MAJOR IMPROVEMENT:** Main cast pipeline is restored (`main_cast_count: 2`, up from 0 in attempt 4). John Donaldson and Uncle Bill are back in `main_cast_*` IDs.

**What works:**
- John Donaldson has canonical full name (was just "John" in attempt 4) ✓
- Uncle Bill correctly identified as protagonist ✓
- Joe Barron and Ted Frith present with correct mention counts ✓
- No hallucinated characters ✓
- "John" alias correctly captured ✓
- Pipeline metadata correctly identifies Uncle Bill as narrator ✓

**Issues remaining:**

1. **Father/son John Donaldson still NOT split** — There's one "John Donaldson" entry (main_cast_1, 28 mentions) conflating the father (~55, embezzler who died as stretcher-bearer) and the son (~23, ambulance driver). The summaries correctly distinguish "John Donaldson (the son)" and "John Donaldson (the father)" in `characters_present`, but the character list doesn't reflect this.

2. **Margaret Donaldson still missing** — She is John Sr.'s widow who wrote Uncle Bill a letter. She was present in attempts 1-3 but has been absent since attempt 4.

3. **Narrator flag on wrong character** — `pipeline_metadata.narrator_name` correctly says "Uncle Bill", but in the character list, `John Donaldson` has `is_narrator: true` while Uncle Bill has `is_narrator: false`. The HTML renders John Donaldson as "Secondary narrator (nested narrative)" which is a creative interpretation, but the primary first-person narrator is Uncle Bill. The flags are inverted.

4. **Relationship "Uncle Bill (enemy)"** — John Donaldson lists Uncle Bill as "enemy". Uncle Bill was John Sr.'s beloved cousin and benefactor — the exact opposite. Should be "cousin" or "benefactor".

5. **"John Donaldson" listed as own alias** — The aliases list includes `["John Donaldson", "John"]`. The canonical name shouldn't be repeated as an alias.

Score 6.5/10 (up from 5) — main cast restored and canonical naming improved, but father/son split still missing, Margaret gone, narrator flag inverted, wrong relationship.

### 2.3 Character Profiles: 7/10 ✗ (IMPROVEMENT from 6.5)

**JSON `profile` field is null for ALL 4 characters** — but this appears to be a systemic issue (was also null in attempt 4 with supporting-only characters). The HTML report renders rich profiles from internal data.

**John Donaldson's profile (in HTML — conflated father+son):**
- Appearance: "middle-aged man with dark features and strikingly familiar eyes" — accurate for the FATHER, but this profile conflates both characters
- Personality: "morally ambiguous man who committed financial betrayal" — accurate for father
- Voice: "American, sir" quote, fragmented speech — accurate father quotes
- Dialect: "American English with faint foreign inflection from long residence in Italy" — accurate for father
- Relationships: `Uncle Bill (enemy)` — WRONG. `Margaret Donaldson (spouse)` — correct. `John Donaldson (son) (parent)` — good, recognizes father-son distinction

**Uncle Bill's profile (in HTML):**
- Appearance: "elderly man with reserved, unassuming presence" — reasonable
- Personality: "reluctantly generous, loyal and protective" — accurate and well-described
- Voice: "low, measured, slightly gravelly voice" — excellent narrator guidance
- Example quotes: The letter quote and self-description quote are correctly attributed ✓
- But: "American, sir" appears as Uncle Bill's quote — this is actually John Sr.'s famous line, spoken on his deathbed. Uncle Bill quotes it when retelling the story, but it's not *his* quote.
- Relationships: only `John Donaldson (mentor)` — should also mention "cousin" to John Sr.

**Joe Barron and Ted Frith:** No profiles (expected for minor characters with few mentions).

Score 7/10 (up from 6.5) — profiles are back in HTML with good detail, but JSON profiles still null, "enemy" relationship persists, "American, sir" misattributed to Uncle Bill, father/son conflation affects John's profile accuracy.

### 2.4 Chapter Summaries: 7.5/10 ✗

**Section 1 summary:** Mostly accurate. Captures the backstory well — the letter, Uncle Bill's reluctance, memories of John Sr., the scandal, the widow's letter. Issue: `characters_present` only lists "Narrator" — should include Uncle Bill, John Donaldson, Margaret Donaldson.

**Section 2 summary:** Comprehensive and well-structured. Captures the fishing trip, WWI enlistment, the reunion at the pier, and the deathbed reveal. **Persistent factual error:** "his deceased sister's twelve-year-old son" — John Sr. was Uncle Bill's COUSIN, not his sister's son. The text explicitly says "a cousin, who had come to be this lad's father." This hallucination has persisted across all 5 attempts.

**Section 2 `characters_present`:** Correctly lists "Uncle Bill", "John Donaldson (the son)", "John Donaldson (the father)" — this is excellent and shows the summaries can distinguish father from son even though the character list doesn't.

Score: 7.5/10 — detailed and mostly accurate summaries useful for narrator prep, but the "sister" hallucination and incomplete Ch.1 characters_present prevent a higher score.

### 2.5 Pronunciation Guide: 6.5/10 ✗

24 entries (down from 26 in attempt 4). The CMU dictionary filter continues to work for short common names.

**Genuinely useful entries (~10):** Caporetto, Piave, Solferino, Tagliamento, Bersagliari, Venetia, Guerre, Bordeaux, Frith, mayn't

**Homographs (acceptable — 5):** live, minute, read, close, moderate

**Remaining false positives (~9):** Donaldson, Barron, whippersnapper, thriftless, thickset, manliness, dum-dums, orderlies, was

**IPA issues:**
- "Barron" now `/ˈbærən/` — FIXED from attempt 4's `/bəˈrɒn/` ✓
- "orderlies" `/ˈɔːr.dər.laɪz/` — the vowel in the last syllable should be /ɪ/ not /aɪ/ (orderlies = /ˈɔːr.dər.lɪz/)
- "was" `/wɒz/` — common word, shouldn't be flagged at all

Score 6.5/10 — good coverage of Italian WWI terms, but ~9 false positives including common English words (was, whippersnapper, manliness, thriftless, thickset, orderlies, dum-dums). The Barron IPA fix is an improvement.

### 2.6 HTML Presentation: 9/10 ✓

Well-organized HTML report with functional navigation, character profiles rendered with appearance/personality/voice/relationships sections. Both section titles show "Chapter 1" and "Chapter 2" (no null display). Minor: sections lack meaningful titles since text has no chapter divisions. John Donaldson correctly tagged as "Secondary narrator (nested narrative)" in HTML (even if the is_narrator JSON flag is misapplied).

Score unchanged: 9/10.

## Overall Score Calculation

```
Overall = (7 × 0.20) + (6.5 × 0.25) + (7 × 0.15) + (7.5 × 0.20) + (6.5 × 0.10) + (9 × 0.10)
        = 1.40 + 1.625 + 1.05 + 1.50 + 0.65 + 0.90
        = 7.125 ≈ 7.13
```

**Overall: 7.13/10**

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (user-configured, appropriate)
- No LLM retries across any stage (good)
- 1 JSON parse failure in pronunciation (minor, same as before)
- Temperature 0.7 across all agents — could be lower for character extraction (0.3-0.5)
- `main_cast_count: 2` — **RESTORED** from 0 in attempt 4 ✓
- Character Profiles was the bottleneck at 694s (largest stage)
- 3 characters profiled (John Donaldson, Uncle Bill, Ted Frith) — Joe Barron likely skipped due to low mentions

## Current Issues (Priority Order)

### CRITICAL

1. **Father/son John Donaldson still NOT split**
   - Problem: One "John Donaldson" entry (main_cast_1, 28 mentions) conflating the father (~55, embezzler/stretcher-bearer who died in Italy) and the son (~23, ambulance driver who survived the war). The summaries already distinguish them in `characters_present` ("John Donaldson (the father)" and "John Donaldson (the son)").
   - Impact: Conflation corrupts the profile (father's traits assigned to merged entry), creates wrong narrator flags, and makes the character guide confusing for a narrator who needs to voice two different Johns.
   - Root cause: Step 1.6 was reverted in attempt 5 Fix 1 to restore main cast pipeline. The father/son split has NEVER successfully fired across 5 attempts.
   - **STUCK PATTERN:** `characters.py` modified 4 times for this issue without success. The approach of post-processing in CharacterAgent is flawed — the data to disambiguate is available in summaries but the split code keeps failing.
   - **NEW APPROACH NEEDED:** Since the summaries already contain `"John Donaldson (the father)"` and `"John Donaldson (the son)"` in `characters_present`, a reliable approach would be to use this information during the final character reconciliation (F6 stage in `analyzer.py`) rather than in the CharacterAgent post-processing. Alternatively, enhance the main cast prompt to ask the LLM to distinguish same-named characters if the text context makes it clear they are different people.
   - Location: `src/agents/characters.py` (post-processing), or `src/analyzer.py` (reconciliation), or `src/pipeline/character_extraction_v2/main_cast.py` (prompt-level)

### HIGH

2. **Narrator flag inverted between Uncle Bill and John Donaldson**
   - Problem: `pipeline_metadata.narrator_name` = "Uncle Bill" (correct), but in the character list, `John Donaldson` has `is_narrator: true` while Uncle Bill has `is_narrator: false`. Uncle Bill is the first-person narrator who tells the entire story using "I".
   - Evidence: The HTML renders John Donaldson as "Secondary narrator (nested narrative)" — creative but the JSON `is_narrator` flag should be on Uncle Bill, not John.
   - Location: Likely in `src/agents/characters.py` where narrator flags are applied to character entries, or `src/pipeline/character_extraction_v2/narrator.py`
   - Fix: The narrator assignment logic should set `is_narrator=true` on the character matching `pipeline_metadata.narrator_name` (Uncle Bill), not on a secondary character.

3. **Margaret Donaldson missing**
   - Problem: Present in attempts 1-3 as a supporting character. She is John Sr.'s widow who wrote Uncle Bill a letter informing him of John's death and the existence of the son. She's a named character with narrative significance.
   - Root cause: Possibly related to changes in the main cast or supporting cast pipeline between attempts 3 and 4. With main cast restored, she should reappear if the issue was pipeline-specific.
   - Location: Check supporting cast extraction and any filtering changes

4. **Pronunciation false positives still excessive (~9 of 24)**
   - Problem: Common English words flagged: was, whippersnapper, thriftless, thickset, manliness, orderlies, dum-dums, Donaldson, Barron
   - The CMU filter works for short common names but doesn't catch longer common vocabulary
   - Location: `src/pipeline/pronunciation_guide/` — LLM prompt should instruct NOT to flag standard English vocabulary
   - Fix: The pronunciation prompt should exclude: (1) standard English dictionary words with unambiguous pronunciation (whippersnapper, thriftless, manliness, thickset, orderlies), (2) common monosyllabic words (was), (3) standard English surnames that follow normal phonetic rules (Donaldson, Barron)

5. **Chapter 2 summary factual error: "sister" instead of "cousin"**
   - Problem: "his deceased sister's twelve-year-old son" — John Sr. was Uncle Bill's COUSIN, not his sister's son. Text explicitly says "a cousin."
   - Persisted across all 5 attempts — LLM hallucination
   - Location: Summary generation — hard to fix generically without biasing prompts toward specific texts

### MEDIUM

6. **JSON `profile` field null for all characters**
   - Problem: HTML has rich profiles but JSON `profile`, `physical_description`, `speech_patterns` all null
   - Impact: API consumers expecting profile data won't find it
   - Location: Profile-to-JSON export path in `src/agents/characters.py` or `src/analyzer.py`

7. **Relationship labels wrong**
   - Problem: John Donaldson lists `Uncle Bill (enemy)` — should be "cousin" or "benefactor". Uncle Bill lists `John Donaldson (mentor)` — incomplete, should also include "cousin" relationship to John Sr.
   - Location: Character profiling LLM — relationship label extraction

8. **Chapter 1 `characters_present` only lists "Narrator"**
   - Problem: Should include Uncle Bill, John Donaldson, Margaret Donaldson — all discussed/referenced in Section 1
   - Chapter 2 `characters_present` is excellent (correctly lists Uncle Bill, son, father)

9. **"American, sir" quote given to Uncle Bill**
   - Problem: Uncle Bill's profile has "American, sir" as an example quote, but this is John Donaldson Sr.'s famous dying words. Uncle Bill quotes it when retelling, but it's the father's line.
   - Minor for narrator prep — the narrator does speak these words when narrating

### LOW

10. **"John Donaldson" listed as own alias**
    - Problem: Aliases `["John Donaldson", "John"]` — canonical name repeated in alias list. Should just be `["John"]`.

11. **Ted Frith missing "Teddy" alias**
    - Problem: Text uses "Teddy" 2x but not captured. Same issue since attempt 3.

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
- **Smoke test:** PASS — but full pipeline FAILED because main cast produced 0 characters
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

**⚠️ STUCK PATTERN:** The father/son John Donaldson conflation has been attempted 4 times via `characters.py` post-processing without success. **The fix phase MUST use a DIFFERENT approach.** Options:
1. **Reconciliation-level split in `analyzer.py`** — Use the already-correct `characters_present` from summaries (which distinguishes father/son) to split the character during F6 reconciliation
2. **Main cast prompt enhancement** — Add instructions to `main_cast.py` to output same-named characters as separate entries when context clearly differentiates them
3. **Supporting cast split** — Process the split in `supporting.py` where the summary data is more readily available

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.60 | — | Baseline. Major issues: father/son conflation, Ted split, wrong narrator, pronunciation false positives |
| 2 | 7.10 | +0.50 | Narrator fixed, Ted partially merged, profiles improved. Father/son still conflated. |
| 3 | 7.35 | +0.75 | Red Cross filtered, Ted aliases improved. Father/son split code didn't fire (wrong data source). |
| 4 | 6.68 | +0.08 | **REGRESSION**: main cast pipeline produces 0 characters. Profiles null. Margaret missing. Pronunciation slightly improved. |
| 5 | 7.13 | +0.53 | Main cast RESTORED. Profiles back in HTML. Father/son still conflated. Narrator flag inverted. |

## Priority Fix Order for Attempt 6

**Focus on the highest-impact issues that can cross the 8.0 threshold:**

1. **Father/son John Donaldson split (CRITICAL #1)** — Use a NEW approach (not `characters.py` Step 1.6). The summaries already contain the answer: `characters_present` has `"John Donaldson (the father)"` and `"John Donaldson (the son)"`. Use this data in the reconciliation phase (`analyzer.py`) or enhance the main cast prompt. This single fix would improve Character Extraction by +1.5, Character Profiles by +0.5, and overall by ~0.6.

2. **Narrator flag fix (HIGH #2)** — Set `is_narrator=true` on the character matching `pipeline_metadata.narrator_name`. Quick fix with +0.5 impact on Character Extraction.

3. **Pronunciation false positive reduction (HIGH #4)** — Improve the LLM prompt to exclude standard English vocabulary. Would raise Pronunciation from 6.5 to ~8.

4. **Margaret Donaldson recovery (HIGH #3)** — Investigate why she disappeared after attempt 3. May resolve naturally if the character pipeline changes for the split also improve coverage.

### Attempt 6 - Fix 1: Re-enable Step 1.6 same-name disambiguation split
- **Issue addressed:** Father/son John Donaldson conflation (CRITICAL #1)
- **Root cause:** Step 1.6 method exists (lines 1279-1372) and can parse formatted summaries correctly, but was NOT being called (removed in attempt 5 Fix 1)
- **Fix:** Re-enabled call to `_split_disambiguated_same_name_characters()` after Step 1.5 (title variant merge) and before Step 2 (mention search)
- **Data source:** The method correctly parses formatted summary strings like `[Characters: Uncle Bill, John Donaldson (the father), John Donaldson (the son)]` (lines 1317-1324)
- **Expected impact:** Split conflated John Donaldson entry into father and son characters (~+1.5 Character Extraction, +0.5 Character Profiles, +0.6 overall)
- **Smoke test:** PASS - code review verified method call is now in pipeline, all 298 tests pass
- **Modified:** `src/agents/characters.py` (lines 161-169)

### Attempt 6 - Fix 2: Fallback narrator matching
- **Issue addressed:** Narrator flag inverted (HIGH #2) - `pipeline_metadata.narrator_name = "Uncle Bill"` but `is_narrator: true` on wrong character
- **Root cause:** Narrator detector identifies correct name but `_match_to_character()` fails, leaving `narrator_character_id = null`
- **Fix:** Added Step 4.5 fallback fuzzy matching after Step 4 narrator detection, using `names_similar()` with 0.7 threshold
- **Expected impact:** Correctly assign `is_narrator` flag to Uncle Bill instead of John Donaldson (~+0.5 Character Extraction)
- **Smoke test:** PASS - code review verified fallback logic, all 298 tests pass
- **Modified:** `src/agents/characters.py` (lines 247-262)

### Attempt 6 - Issue #4 DEFERRED: Pronunciation false positives
- **Issue:** 9 false positives (was, whippersnapper, orderlies, manliness, thickset, thriftless, dum-dums, Donaldson, Barron)
- **Root cause:** Words NOT in CMU dictionary, not caught by derivation/compound filters
- **Why deferred:**
  - Fix requires expanding derivation logic or adding keyword lists (forbidden per fix philosophy)
  - Lower impact than CRITICAL/HIGH character issues
  - Current score 6.5/10 - fixing alone won't cross 8.0 threshold
  - Fixes #1 and #2 have much higher impact
- **Future approach:** Improve CMU derivation checking to handle -ness suffix variants ("manliness" from "manly")

## Next Action
**Phase:** awaiting_analysis

Run PROMPT_analyze.md to re-run analysis with Fixes #1 and #2 applied.
