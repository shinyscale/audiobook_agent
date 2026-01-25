# Current Evaluation State

## Active Text
- **Name:** masque_of_red_death
- **Attempt:** 2
- **Phase:** complete
- **baseline_score:** 7.25
- **Competitive Mode:** multi

## Latest Scores
- Structure Detection: 9/10
- Character Extraction: 9/10 (improved from 5/10)
- Character Profiles: 7/10
- Chapter Summaries: 9/10
- Pronunciation Guide: 6/10
- HTML Presentation: 9/10
- **Overall: 8.40/10** (threshold: 8.0) **PASS**

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 7.25 | - | Character fragmentation, pronunciation false positives |
| 2 | 8.40 | +1.15 | Character fixes successful, PASS threshold |

## Evaluation Summary

### What Was Fixed (Attempt 2)
1. **Character fragmentation resolved** - "masked figure" and "the masked figure" no longer appear as separate entries
2. **Red Death / masked figure merge working** - The system correctly identifies these as the same entity (the masked figure has "Red Death" as an alias and they are merged)
3. **Pronunciation word-splitting for descriptive handles** - "Red" and "Death" and "figure" etc. are no longer individually flagged

### Remaining Issues (not blocking, for future improvement)

#### MEDIUM
1. **Pronunciation false positives still present**
   - Common words like "Death", "chiming", "dauntless", "light-hearted", "magnificence" still flagged
   - 69 entries for ~2,500 word story (2.8%) is higher than ideal
   - Genuinely unusual words (improvisatori, castellated, cerements) ARE correctly captured

2. **Profile structured fields empty**
   - `physical_description` and `relationships` are null for all characters
   - However, profile prose IS rendered in HTML (descriptions derived from summaries)
   - This is a data mapping issue, not a content issue

#### LOW
3. **Structure title field null**
   - The single structure element has `title: null`
   - Could capture "The Masque of the Red Death" from document

## Output Files
- HTML: ../output/masque_of_red_death/report.html
- JSON: ../output/masque_of_red_death/analysis.json

## Fix History

### Attempt 2 Fixes (All Successful)

1. **Character fragmentation (Critical #1)** - Fixed article normalization in F6 reconciliation
   - Root cause: `analyzer.py:1236-1266` - `_normalize_name_for_matching()` stripped titles but not articles
   - Smoke test: PASS
   - Result: **FIXED** - No more "masked figure" / "the masked figure" split

2. **Character merge logic (Critical #2)** - Added alias-based deduplication
   - Root cause: `main_cast.py:1041-1162` - `merge_descriptive_entities()` only used semantic clusters
   - Fix: If Profile A has alias "X" and Profile B has canonical "X", they now merge
   - Smoke test: PASS
   - Result: **FIXED** - Red Death and masked figure properly unified

3. **Pronunciation false positives (High #3)** - Skip word-splitting for descriptive handles
   - Root cause: `character_proposer.py:54-102` - split all character names into words
   - Fix: Detect descriptive handles and skip word-splitting
   - Smoke test: PASS
   - Result: **PARTIALLY FIXED** - Character-derived false positives removed, but other common words still flagged

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 2 | Critical #1: Article normalization | analyzer.py | Fixed |
| 2 | Critical #2: Alias-based merge | main_cast.py | Fixed |
| 2 | High #3: Descriptive handle filtering | character_proposer.py | Partially fixed |

## Next Action
**PASS** - masque_of_red_death meets quality threshold (8.40 >= 8.0).

Ready to advance to next text: **berenice**
