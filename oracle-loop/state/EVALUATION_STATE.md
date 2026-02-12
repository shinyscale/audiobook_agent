# Current Evaluation State

## Active Text
- **Name:** cask_of_amontillado
- **Attempt:** 6
- **Phase:** awaiting_fix
- **baseline_score: 6.75**
- **Competitive Mode:** single

## Output Files
- HTML: ../output/cask_of_amontillado/report.html
- JSON: ../output/cask_of_amontillado/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 8/10 ✓
- Character Profiles: 7.5/10 ✗ (FAILING)
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 7.5/10 ✗ (FAILING)
- HTML Presentation: 8.5/10 ✓
- **Overall: 8.33/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.75 | 0.0 | Baseline. 5 bogus supporting chars, Fortunato profile is Montresor's |
| 2 | 6.65 | -0.10 | Bogus chars fixed (+1), but Montresor still missing. Fortunato profile improved but still has issues |
| 3 | 7.58 | +0.83 | Montresor now in character list (fallback worked), but profile generation failed. F6 still broken. |
| 4 | 7.40 | +0.65 | Attempt 4 fix introduced NEW error (Character constructor missing `supporting_strategies`). Same symptoms as attempt 3. Pronunciation false positive rate increased. |
| 5 | 7.18 | +0.43 | `supporting_strategies` fix applied but F6 now fails with NEW error (`MentionResult.total_count`). Narrator fallback fails with `CharacterMention.chapter_idx`. Montresor STILL missing. Regression from attempt 3. |
| 6 | 8.33 | +1.58 | **Major breakthrough!** Montresor now has full profile. MentionResult/CharacterMention attribute errors fixed. Pronunciation false positives reduced from 38% to 22%. 2 categories still failing (Profiles 7.5, Pronunciation 7.5). |

## Current Issues (Priority Order)

### HIGH

1. **Relationship labels oversimplified — all "rival" (impacts Character Profiles)**
   - Problem: All three characters have relationships labeled "rival":
     - Fortunato→Montresor: "rival" — should be "friend/acquaintance" (Fortunato doesn't know about Montresor's intentions)
     - Montresor→Fortunato: "rival" — should be "victim" or "target of revenge"
     - Luchresi→Fortunato: "rival" — should be "professional competitor" (in wine connoisseurship)
   - Evidence: The text shows Fortunato trusts Montresor, calling him "my friend." Montresor feigns concern and friendship. They are not rivals.
   - Location: Relationship extraction in character profiling pipeline (`src/pipeline/character_profiling/`)
   - Impact: -0.5 on Character Profiles
   - **Note:** This is an LLM judgment issue. The profiling pipeline's relationship extraction prompt may need to provide better relationship type options beyond "rival."

2. **Montresor appearance missing roquelaire and black silk mask**
   - Problem: Montresor's appearance only mentions "conceals a trowel beneath his cloak." The text explicitly describes him wearing a roquelaire (short cloak) and a black silk mask.
   - Evidence: From the text: "I had on a silk mask" and "drawing a roquelaire closely about my person"
   - Location: Passage gathering for Montresor in character profiling. Since Montresor entered via F6 reconciliation with only 1 mention, the passage gatherer may not have found enough direct text references.
   - Impact: -0.5 on Character Profiles
   - **Root cause analysis:** Montresor's `mention_count: 1` and empty `mentions: []` means the passage gatherer has minimal data to work with. The F6 reconciliation creates a Character object but doesn't populate full mention data. The profiling pipeline then has to work with limited context.

3. **Pronunciation: ~22% false positive rate (6 of 27 entries are common/redundant words)**
   - Problem: These entries shouldn't be flagged:
     - "Montresors" — plural of already-listed "Montresor" (redundant)
     - "cough's" — very common word
     - "leer" — common English word
     - "inmost" — common English word
     - "Grave" — common English word (could be homograph, but context is clear)
     - "unredressed" — standard English word with common prefix
   - "gesticulation" is borderline — keep it, it's uncommon enough.
   - Location: `src/pipeline/pronunciation_guide/proposers/cmu_proposer.py` — the pattern-based exclusions from attempt 6 caught many false positives but missed these
   - Impact: -0.5 on Pronunciation
   - **Fix approach:**
     - Add exclusion for plurals/possessives of names already in the pronunciation list (Montresors when Montresor exists)
     - The `_is_obvious_compound()` filter already handles re-/un- prefixed words but missed "unredressed" — check if it's actually being called for this word
     - Common monosyllabic English words like "leer", "Grave" should be filtered by a more aggressive common-word check. The CMU proposer may need to check if the word (lowercased) is in the CMU dictionary as a common English word (not a name). If it IS in CMU with an obvious pronunciation, don't flag it.
     - "cough's" — possessives of common words should be filtered
     - "inmost" — a standard English compound (in + most) should be caught by compound detection

4. **Fortunato's role labeled "antagonist" instead of "victim"**
   - Problem: Fortunato is not the antagonist — he's the victim. Montresor is the villain-protagonist. In literary terms, the "antagonist" opposes the protagonist, but Fortunato doesn't oppose Montresor — he's oblivious to Montresor's plan.
   - Location: Role assignment in character extraction pipeline
   - Impact: -0.5 on Character Extraction (but scored 8.0, so this is a buffer issue — fixing helps but isn't strictly needed to pass)
   - **Deprioritize** — Character Extraction already passes at 8.0. Fix if easy, skip if complex.

### MEDIUM

5. **Montresor's evidence quotes are from the summary, not direct text**
   - Problem: The `evidence` array in Montresor's appearance section contains a quote from the chapter summary ("begins sealing him alive behind a stone wall using a trowel concealed beneath his cloak") rather than direct text from the story.
   - Evidence: F19 warnings during analysis noted "ungrounded evidence quotes" for all 3 profiles
   - Location: Character profiling pipeline — evidence gathering
   - Impact: -0.5 on Character Profiles
   - **Root cause:** Same as issue #2 — Montresor's low mention count limits what the passage gatherer can find, so it falls back to summary text.

6. **Narrative style inconsistency in overview**
   - Problem: `overview.structure.narrative_style` says "unknown" while `overview.plot_summary.narrative_style` correctly says "first-person retrospective"
   - Location: `src/analyzer.py` — structure overview generation
   - Impact: Minor (-0.5 on Structure Detection, but already passes at 9.0)

### LOW

7. **Double-quoted example quotes in HTML**
   - Problem: Example quotes render as `""Amontillado!""` (double double-quotes) in the HTML
   - Location: HTML template rendering — likely the evidence/quotes are stored with quotes already, and the template adds more
   - Impact: Minor formatting issue (-0.5 on Presentation, but already passes at 8.5)

## What Needs to Happen to Pass

Only 2 categories need fixing, and both are close to threshold:

### Character Profiles (7.5 → 8.0): Need +0.5 points
Fix **ANY TWO** of these:
- **Relationships** (issue #1): Improve from "rival" to more accurate labels → +0.5
- **Montresor appearance** (issue #2): Add roquelaire/mask details → +0.5
- **Evidence grounding** (issue #5): Use direct text instead of summary → +0.5

### Pronunciation Guide (7.5 → 8.0): Need +0.5 points
- **Reduce false positives** (issue #3): Remove 3-4 of the 6 identified false positives → +0.5

**Priority order for fix phase:**
1. Pronunciation false positives (issue #3) — independent, quick win, pattern-based
2. Relationship labels (issue #1) — high impact on Profiles score
3. Montresor appearance detail (issue #2) — nice to have but harder to fix (root cause is low mention count)

## Configuration Audit

### Model Configuration
- All agents use `qwen3-next:80b-a3b-instruct-q8_0` — appropriate per user configuration
- Temperature 0.7 for all — acceptable
- Context length 32768 — sufficient for this short story

### Chunking Configuration
- `character_llm_chunk_chars: 5000` — fine for ~13K character story
- `summary_chunk_words: 2500` — appropriate

### Processing Issues
- 0 LLM retries, 0 JSON parse failures for most stages — clean execution
- 1 JSON parse failure in Pronunciation (batch enrichment)
- F6 reconciliation now works (attribute errors fixed in attempt 6)
- All 3 character profiles generated successfully with HIGH confidence
- Montresor successfully reconciled via F6 with correct role and narrator status

## Fix History

### Attempt 2 Fixes Applied
1. **Fortunato personality contamination - FIXED (VERIFIED)**
2. **5 bogus supporting characters - FIXED (VERIFIED)**

### Attempt 3 Fixes Applied
1. **Montresor missing - PARTIALLY FIXED** (narrator fallback works, but profile fails)

### Attempt 4 Fixes Applied
1. **F6 reconciliation and narrator fallback - FAILED** (introduced Character constructor error)

### Attempt 5 Fixes Applied
1. **Character constructor missing supporting_strategies - FIXED** (but new MentionSearcher attribute errors)

### Attempt 6 Fixes Applied
1. **MentionResult/CharacterMention attribute errors - FIXED (VERIFIED)**
   - All attribute names corrected after reading actual class definitions
   - **Result:** Montresor now in character list with full profile — the 5-attempt saga is RESOLVED
2. **Pronunciation false positives reduced from 38% to 22% - PARTIALLY FIXED**
   - Pattern-based exclusions catch obvious compounds, OCR artifacts, standard prefixes
   - Still ~6 false positives remaining (cough's, leer, inmost, Grave, Montresors, unredressed)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 2 | Fortunato personality contamination | `src/analyzer.py` | Fixed — personality now correct |
| 2 | Bogus supporting characters | `src/pipeline/character_extraction_v2/grounding.py` | Fixed — 5 bogus chars removed |
| 3 | F6 reconciliation crash (`document` typo) | `src/analyzer.py:1648` | Partially fixed — new error revealed |
| 3 | Narrator not added to character list | `src/analyzer.py:1769-1807` | Fixed — fallback works, but profile fails |
| 4 | F6 reconciliation AttributeError | `src/analyzer.py:1648` | Fixed attribute name — but new constructor error |
| 4 | Narrator fallback missing mention data | `src/analyzer.py:1784-1807` | MentionSearcher added — but Character constructor error + wrong attribute access |
| 5 | Character constructor missing `supporting_strategies` | `src/analyzer.py:1662, 1802` | Fixed constructor — but MentionSearcher attribute errors now visible |
| 6 | MentionResult/CharacterMention attribute errors | `src/analyzer.py:1668, 1670, 1809, 1818` | Fixed — read class definitions, corrected all attribute names |
| 6 | Pronunciation false positives | `src/pipeline/pronunciation_guide/proposers/cmu_proposer.py` | Partial — reduced from 38% to 22%, need <15% |
| 7 | Pronunciation false positives (6 remaining) | `src/pipeline/pronunciation_guide/proposers/cmu_proposer.py`, `foreign_proposer.py` | Enhanced filtering — added possessive filter, monosyllabic word filter, compound patterns, redundant variant filter, and "grave" to ENGLISH_EXCEPTIONS |
| 7 | Relationship labels all "rival" | `src/pipeline/character_profiling/generator.py` | Enhanced prompt — added relationship guidance section with power dynamics, specific type categories, and deception handling |

## Next Action
**Phase:** awaiting_analysis

Fixes applied for attempt 7:
1. **Pronunciation false positives** (issue #3):
   - Root cause: Missing filters for possessives, monosyllabic words, non-hyphenated compounds, and redundant variants
   - Files modified:
     - `src/pipeline/pronunciation_guide/proposers/cmu_proposer.py`:
       - Added `_is_possessive_of_known_word()` — filters "cough's" when "cough" is in CMU
       - Added `_is_common_monosyllabic_word()` — filters "leer" and similar obvious words
       - Enhanced `_is_obvious_compound()` — now catches "inmost", "outermost", etc.
       - Added `_filter_redundant_variants()` — filters "Montresors" when "Montresor" already flagged
       - Applied all filters in both `propose()` and `_propose_from_index()` paths
     - `src/pipeline/pronunciation_guide/proposers/foreign_proposer.py`:
       - Added "grave" to ENGLISH_EXCEPTIONS (common English word, even in wine names)
   - Expected impact: Reduce false positive rate from 22% (6/27) to ~7% (2/27) or better

2. **Relationship labels** (issue #1):
   - Root cause: Prompt lacked specific relationship type guidance, LLM defaulted to generic "rival"
   - Files modified:
     - `src/pipeline/character_profiling/generator.py`:
       - Added "RELATIONSHIP GUIDANCE" section to prompt with power dynamics framework
       - Distinguished asymmetric (victim/victimizer), competitive (rival/competitor), and friendly relationships
       - Added explicit deception handling ("pretends friendship to harm" = victimizer, not friend)
       - Expanded relationship type options with specific categories
   - Expected impact: Relationships should now be more accurate (Fortunato→Montresor: "friend/acquaintance", Montresor→Fortunato: "victim", Luchresi→Fortunato: "professional_competitor")

Re-run analysis to verify fixes.
