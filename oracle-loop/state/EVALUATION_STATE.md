# Current Evaluation State

## Active Text
- **Name:** monkeys_paw
- **Attempt:** 15
- **Phase:** awaiting_analysis
- **baseline_score:** 6.275

## Latest Scores

- Structure Detection: 8/10 (unchanged)
- Character Extraction: 7/10 ← IMPROVED from 5/10
- Character Profiles: 7/10 (unchanged)
- Chapter Summaries: 9/10 ← IMPROVED from 8/10
- Pronunciation Guide: 5/10 ← IMPROVED from 4/10
- HTML Presentation: 9/10 (unchanged)
- **Overall: 7.60/10** (threshold: 8.0)

## Score Calculation

```
Overall = (8 × 0.20) + (7 × 0.25) + (7 × 0.15) + (9 × 0.20) + (5 × 0.10) + (9 × 0.10)
        = 1.60 + 1.75 + 1.05 + 1.80 + 0.50 + 0.90
        = 7.60/10
```

## Evaluation Details

### V2 Character Extraction - SIGNIFICANT IMPROVEMENT

**What V2 Fixed:**
1. ✅ **No more "White" orphan** - The 30-mention standalone "White" entry is GONE
2. ✅ **"Herbert" correctly aliased** - with "the son" as additional alias
3. ✅ **"the mother" correctly aliased to Mrs. White**
4. ✅ **"his wife" orphan is GONE**
5. ✅ **Gender conflict resolved** - "the old man" and "the old woman" are now SEPARATE entries (not merged)
6. ✅ **50% fewer tokens** (58K vs 113K) and **57% fewer LLM calls** (26 vs 60)

**Current Character List (7 characters):**
1. Mr. White (10 mentions) - Good
2. Mrs. White (11 mentions) with alias "the mother" - EXCELLENT
3. Herbert White (15 mentions) with aliases "Herbert", "the son" - EXCELLENT
4. Sergeant-Major Morris (6 mentions) with alias "Morris" - Good
5. The stranger from Maw and Meggins (1 mention) - OK
6. **the old man (1 mention)** - Should merge with Mr. White
7. **the old woman (1 mention)** - Should merge with Mrs. White

### Chapter Summaries: 9/10

All three part summaries are accurate and useful:
- Part I: Correctly describes the stormy night, Morris's visit, introduction of the monkey's paw, the first wish for £200
- Part II: Correctly describes the bright morning, Herbert leaving for work, the stranger from Maw and Meggins, Herbert's death, the £200 compensation
- Part III: Correctly describes the grief, the desperate second wish, the knocking at the door, the third wish

### Pronunciation Guide: 5/10

**Good entries with IPA (56 total):**
- "fakirs" /ˈfækɪəz/ - Indian holy men
- "rubicund" - red-complexioned
- "Laburnam" - the street name
- "condoling" - expressing sympathy
- "antimacassar" - chair cover
- "avaricious" - greedy
- Many compound words: "white-haired", "to-night", "unlooked-for"

**Still problematic:**
- Common words flagged: "old" (42x), "from" (38x), "man" (23x), "son" (15x)
- Gutenberg boilerplate: "GutenbergTM" (57x), "eBooks" (7x)

## Current Issues (Priority Order)

### HIGH

1. **"the old man" should merge with Mr. White**
   - Problem: In Part III, W.W. Jacobs switches to using "the old man" and "the old woman" for the Whites
   - Evidence: Only the Whites appear in Part III; "the old man" IS Mr. White grieving for Herbert
   - Location: V2 character extraction summary-driven approach doesn't cross-reference Part III characters with Parts I/II
   - Fix: In character extraction V2, when chapter summary mentions "the old man/woman" but previous chapters have established elderly couple, resolve the epithet
   - Impact: +1 point to Character Extraction (7→8)

2. **"the old woman" should merge with Mrs. White**
   - Same issue as above - Part III narrative shift
   - Fix: Same as above
   - Impact: Included in #1

3. **Common English words flagged in pronunciation**
   - Problem: "old", "from", "man", "son", "woman", "mother" flagged as proper nouns
   - Root cause: These words appear in character name phrases and get extracted
   - Location: `src/pipeline/pronunciation/` - needs stopword filtering
   - Fix: Add stopword list to filter common English words regardless of context
   - Impact: +1.5 points to Pronunciation (5→6.5→7 with Gutenberg fix)

### MEDIUM

4. **Project Gutenberg boilerplate contamination**
   - Problem: "GutenbergTM" (57x), "eBooks", "PGLAF", "MERCHANTABILITY" in pronunciation
   - Location: `src/ingestion/` - back matter detection
   - Fix: Add patterns to detect and strip Project Gutenberg license text
   - Impact: +0.5 points to Pronunciation

5. **Chapter titles showing as "None"**
   - Problem: All three chapters have `title: null` instead of "Part I", "Part II", "Part III"
   - Location: `src/pipeline/chapter_detection/` - title extraction
   - Fix: Improve title regex for "Part X" format

## Fix History

| Attempt | Fix | Score | Delta |
|---------|-----|-------|-------|
| 5 | First successful run | 6.275 | baseline |
| 6 | Re-evaluated with consistent rubric | 7.05 | +0.775 |
| 10 | Case sensitivity fix | 7.05 | +0.775 |
| 11 | `is_ambiguous_lastname_only()` in heuristic path | 6.70 | Regression |
| 12 | Added ambiguity check to `_validate_merge()` in LLM path | 7.00 | +0.725 |
| 13 | Gender conflict detection in epithet resolution | 7.00 | Fix didn't execute |
| 14 | **V2 character extraction (summary-driven)** | **7.60** | **+1.325** |
| 15 | F6 epithet filtering + pronunciation stopwords | TBD | TBD |

**Attempt 15 Changes:**
1. **F6 Generic Epithet Filter** (src/analyzer.py:1113-1130)
   - Root cause: F6 Chapter Summary Reconciliation was creating separate character entries for generic epithets like "the old man", "the old woman" found in summaries
   - Fix: Added GENERIC_EPITHETS set to skip common descriptive phrases that are likely aliases of existing characters
   - Impact: Should eliminate the 2 orphan characters (the old man, the old woman)
   - Smoke test: PASS - "the old man" and "the old woman" correctly filtered out

2. **Pronunciation Stopword Expansion** (src/pipeline/pronunciation_guide/proposers/cmu_proposer.py:21-42)
   - Root cause: COMMON_WORDS_WHITELIST only had articles and titles, not common descriptive words that appear in character epithets
   - Fix: Expanded whitelist with common descriptive words: old, young, man, woman, boy, girl, father, mother, son, daughter, etc.
   - Impact: Should remove ~40+ false positive pronunciation entries for common English words
   - Smoke test: PASS - common words filtered, proper names still flagged

## Score History

| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 5 | 6.275* | baseline | First successful run |
| 6 | 7.05 | +0.775 | Re-evaluated |
| 10 | 7.05 | +0.775 | Case sensitivity fix |
| 11 | 6.70 | +0.425 | Regression |
| 12 | 7.00 | +0.725 | Partial fix |
| 13 | 7.00 | +0.725 | Cache issue |
| **14** | **7.60** | **+1.325** | **V2 working!** |

## Path to 8.0

**Current: 7.60**
**Needed: +0.40 points**

Easiest path:
1. Resolve "the old man/woman" → Mr./Mrs. White: Character Extraction 7→8 (+0.25 weighted)
2. Add pronunciation stopword filtering: Pronunciation 5→6 (+0.10 weighted)
3. Strip Gutenberg boilerplate: Pronunciation 6→7 (+0.10 weighted)

Total potential: +0.45 points → **8.05/10 PASS**

## Configuration Audit

- Model: qwen3-next:80b-a3b-instruct-q8_0 for character extraction
- Chunking: Not applicable for V2 (summary-driven)
- LLM calls: 26 total, 58,668 tokens (50% reduction from V1)
- Character Extraction: Only 31.2s (vs 449s in V1 - 93% faster!)
- High confidence on all 4 extracted characters

## Next Action

**Phase:** awaiting_evaluation

Analysis complete for attempt 15. Pipeline ran successfully:
- Total time: 11m 49s
- 26 LLM calls, 58,026 tokens
- 7 characters extracted (5 from V2 + 2 from summary reconciliation)
- 73 pronunciation flags

## Pipeline Notes
- Some low-confidence profile warnings (Mr. White: 0.30 confidence)
- LLM identity detection had server errors (500) but analysis completed
- Front matter detected (1 region)

## Output Files
- HTML: ../output/monkeys_paw/report.html (160KB)
- JSON: ../output/monkeys_paw/analysis.json (84KB)
