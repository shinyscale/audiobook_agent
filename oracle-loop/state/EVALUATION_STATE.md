# Current Evaluation State

## Active Text
- **Name:** cask_of_amontillado
- **Attempt:** 7
- **Phase:** complete
- **baseline_score: 6.75**
- **Competitive Mode:** single

## Output Files
- HTML: ../output/cask_of_amontillado/report.html
- JSON: ../output/cask_of_amontillado/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 8.5/10 ✓
- Character Profiles: 8/10 ✓
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 8.5/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 8.63/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** PASS — All categories at or above threshold

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.75 | 0.0 | Baseline. 5 bogus supporting chars, Fortunato profile is Montresor's |
| 2 | 6.65 | -0.10 | Bogus chars fixed (+1), but Montresor still missing. Fortunato profile improved but still has issues |
| 3 | 7.58 | +0.83 | Montresor now in character list (fallback worked), but profile generation failed. F6 still broken. |
| 4 | 7.40 | +0.65 | Attempt 4 fix introduced NEW error (Character constructor missing `supporting_strategies`). Same symptoms as attempt 3. Pronunciation false positive rate increased. |
| 5 | 7.18 | +0.43 | `supporting_strategies` fix applied but F6 now fails with NEW error (`MentionResult.total_count`). Narrator fallback fails with `CharacterMention.chapter_idx`. Montresor STILL missing. Regression from attempt 3. |
| 6 | 8.33 | +1.58 | **Major breakthrough!** Montresor now has full profile. MentionResult/CharacterMention attribute errors fixed. Pronunciation false positives reduced from 38% to 22%. 2 categories still failing (Profiles 7.5, Pronunciation 7.5). |
| 7 | 8.63 | +1.88 | **PASS!** Relationship labels fixed (rival→victim/victimizer/professional_competitor). Pronunciation false positives reduced from 22% to ~5%. All 6 categories now >= 8.0. |

## Current Issues (Priority Order)

No blocking issues. All categories pass threshold.

### Remaining Polish Items (LOW priority, not blocking)

1. **Montresor appearance still missing roquelaire and black silk mask**
   - Root cause: Montresor's `mention_count: 1` limits passage gatherer data
   - Impact: Minor — profile overall is good with personality, voice guidance, and relationships

2. **Narrative style inconsistency in overview**
   - `overview.structure.narrative_style` says "unknown" while `overview.plot_summary.narrative_style` correctly says "first-person retrospective"
   - Impact: Cosmetic

3. **Double-quoted example quotes in HTML**
   - Example quotes render as `""Amontillado!""` (double double-quotes)
   - Impact: Cosmetic formatting issue

4. **Fortunato's role labeled "antagonist" instead of "victim"**
   - Debatable — some literary analysis does call the opposing character "antagonist"
   - Impact: Minor

5. **hearken/hearkened redundancy in pronunciation guide**
   - Both base form and past tense flagged separately
   - Impact: Very minor

## What Passed (Attempt 7 Fixes That Worked)

### Relationship Labels — FIXED
- Fortunato→Montresor: "rival" → "victim" ✓
- Montresor→Fortunato: "rival" → "victimizer" ✓
- Luchresi→Fortunato: "rival" → "professional_competitor" ✓
- The prompt enhancement in `src/pipeline/character_profiling/generator.py` worked perfectly

### Pronunciation False Positives — FIXED
- False positive rate: 22% (6/27) → ~5% (1/22)
- Removed: Montresors, cough's, leer, inmost, Grave
- "unredressed" remains but is borderline acceptable (uncommon enough for narrators)
- Filters added: possessive filter, monosyllabic word filter, compound patterns, redundant variant filter

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
- F6 reconciliation works correctly
- All 3 character profiles generated successfully with HIGH confidence
- Analysis completed in 25m 48s

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
2. **Pronunciation false positives reduced from 38% to 22% - PARTIALLY FIXED**

### Attempt 7 Fixes Applied
1. **Pronunciation false positives - FIXED (VERIFIED)** — Rate reduced from 22% to ~5%
2. **Relationship labels all "rival" - FIXED (VERIFIED)** — Now victim/victimizer/professional_competitor

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
| 7 | Pronunciation false positives (6 remaining) | `src/pipeline/pronunciation_guide/proposers/cmu_proposer.py`, `foreign_proposer.py` | **Fixed** — reduced from 22% to ~5% |
| 7 | Relationship labels all "rival" | `src/pipeline/character_profiling/generator.py` | **Fixed** — accurate relationship types now generated |

## Next Action
**Phase:** complete

Text `cask_of_amontillado` has PASSED with all categories >= 8.0. Ready to advance to next text in manifest (`masque_of_red_death`).
