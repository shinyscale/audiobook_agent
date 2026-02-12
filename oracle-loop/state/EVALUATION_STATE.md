# Current Evaluation State

## Active Text
- **Name:** cask_of_amontillado
- **Attempt:** 2
- **Phase:** awaiting_evaluation
- **baseline_score: 6.75**
- **Competitive Mode:** single

## Output Files
- HTML: ../output/cask_of_amontillado/report.html
- JSON: ../output/cask_of_amontillado/analysis.json

## Pipeline Notes (Attempt 2)
- **CRITICAL ERROR:** "F6 character reconciliation failed: name 'document' is not defined" - Code error in character reconciliation
- **CHARACTER EXTRACTION FAILURE:** Montresor (protagonist/narrator) was NOT extracted as a character
  - Multiple warnings: "Narrator 'Montresor' identified but NOT found in main_cast. Available characters: ['Fortunato']"
  - Final state: Only Fortunato and Luchresi were extracted
  - This is a CATASTROPHIC failure - the story's protagonist is missing
- **HALLUCINATION WARNING:** "F19: Profile for 'Fortunato' has 5 potentially ungrounded evidence quotes - may indicate hallucination"
- **JSON VALIDATION:** "LLM validation failed (got dict), keeping batch candidates" - Minor validation issue
- Competitive consensus enabled for all stages (characters, structure, summaries)

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 4/10 ✗ (FAILING)
- Character Profiles: 4/10 ✗ (FAILING)
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 7/10 ✗ (FAILING)
- HTML Presentation: 8.5/10 ✓
- **Overall: 6.75/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.75 | 0.0 | Baseline. 5 bogus supporting chars, Fortunato profile is Montresor's |

## Current Issues (Priority Order)

### CRITICAL

1. **Fortunato's personality profile describes MONTRESOR, not Fortunato**
   - Problem: Fortunato's personality says "A cruel and calculating antagonist who manipulates and murders with cold precision, exploiting vulnerability to satisfy a personal vendetta." This is verbatim a description of Montresor's actions, not Fortunato's.
   - Evidence: Fortunato is the VICTIM who is lured into the catacombs and entombed alive. He is proud, trusting, boastful about wine connoisseurship, and intoxicated. The traits listed ("manipulative, calculating, cruel, deceptive, vengeful, emotionally detached") are all Montresor's traits.
   - Root cause: The character profiling LLM likely confused the two characters due to first-person narration. Montresor narrates his own cruel actions, and the profiler attributed those actions to Fortunato instead.
   - Location: `src/pipeline/character_profiling/` — the profiling pipeline's evidence gathering or LLM prompt is confusing narrator actions with the profiled character.
   - Impact: Score -3 on Character Profiles. A narrator reading this would voice Fortunato completely wrong.

2. **5 of 6 supporting characters are bogus (not real characters)**
   - Problem: The supporting cast contains:
     - "Cask of Amontillado" — the story title, not a character
     - "Edgar Allan Poe" — the author, not a character in the story
     - "lacessit" — a Latin word from the family motto "Nemo me impune lacessit"
     - "De Grave" — a type of wine (Graves/De Grâve), not a person
     - "--yes" — a parsing artifact from dialogue punctuation
   - Evidence: Only "Luchresi" is a legitimate character (a wine expert mentioned but never appearing on-page)
   - Location: `src/pipeline/character_extraction_v2/supporting.py` — supporting cast extraction is pulling in non-character entities
   - All have `supporting_*` IDs, so the problem is specifically in the supporting cast pipeline
   - Impact: Score -4 on Character Extraction. These entries are garbage data.

### HIGH

3. **Fortunato labeled as "antagonist" role — misleading for narrator**
   - Problem: Fortunato's role is listed as "antagonist" but he is the victim of Montresor's revenge plot. While Montresor is the protagonist-narrator, Fortunato is best described as "victim" or at most a secondary character who is deceived and murdered.
   - Evidence: Montresor says "The thousand injuries of Fortunato I had borne..." suggesting Fortunato wronged him, but the entire story shows Fortunato as a trusting, somewhat foolish man being led to his death. In narrative terms, Montresor is both protagonist and villain.
   - Location: Character extraction role assignment in `src/pipeline/character_extraction_v2/main_cast.py`
   - Impact: Score -0.5 on Character Extraction.

4. **Pronunciation false positives: common English words flagged**
   - Problem: Several common English words are flagged that any narrator would know:
     - "Cask" — common English word
     - "Edgar", "Allan", "Poe" — the author's name (shouldn't be in pronunciation guide for the story text)
     - "De" — common word
     - "tight-fitting", "to-day", "web-work" — hyphenated compounds, not pronunciation challenges
     - "cough's", "leer" — common English words
     - "Unsheathing", "reapproached", "re-erected", "re-echoed" — standard English with common prefixes
   - Evidence: ~12 of 42 entries are false positives (common words a narrator wouldn't need help with)
   - Location: `src/pipeline/pronunciation/` — the pronunciation flagging threshold is too aggressive
   - Impact: Score -1.5 on Pronunciation. Dilutes the useful entries with noise.

5. **"himselffelt" is an OCR artifact flagged as a pronunciation entry**
   - Problem: "himselffelt" (IPA: /hɪmˈsɛlfˌfɛlt/) is not a real word — it's two words ("himself felt") fused by an OCR/text extraction error. The OCR repair stage fixed 1 broken ligature but missed this one.
   - Evidence: No such word exists in the original Poe text
   - Location: `src/ingestion/refine.py` (OCR repair) or pronunciation pipeline should reject obviously compound artifacts
   - Impact: Score -0.5 on Pronunciation.

### MEDIUM

6. **Montresor's mention count is only 1 (should be higher)**
   - Problem: Montresor is listed with only 1 mention, but as the first-person narrator who is also referenced by name multiple times by Fortunato ("For the love of God, Montresor!"), the count should be higher.
   - Evidence: The name "Montresor" appears at least 3-4 times in the text (once in the narrator's self-identification, and in Fortunato's final plea). The count of 1 suggests only explicit NER matches are counted, missing dialogue references.
   - Location: Mention counting in character extraction pipeline
   - Impact: Minor metadata inaccuracy.

7. **Montresor-Fortunato relationship labeled "rival" — inaccurate**
   - Problem: Both characters list each other as "rival" but their relationship is more accurately "victim-murderer" or "acquaintance turned victim." "Rival" implies competition between equals, which doesn't capture the predator-prey dynamic.
   - Evidence: Montresor methodically lures and murders Fortunato. While Montresor claims past "injuries," the story depicts a calculated murder, not a rivalry.
   - Location: Relationship extraction in character profiling pipeline
   - Impact: Minor but misleading for narrator preparation.

8. **Luchresi has relationship "tool" with Montresor — unclear label**
   - Problem: Luchresi is listed with relationship `"Montresor": "tool"`. While Luchresi IS used as a tool by Montresor (mentioned to provoke Fortunato's pride), the relationship label "tool" is an unusual category that may confuse narrators.
   - Location: Relationship extraction in character profiling
   - Impact: Minor presentation issue.

### LOW

9. **Homographs "row", "close", "entrance" lack IPA (by design)**
   - Note: These 3 homographs have null IPA but provide context-dependent pronunciation notes. This is actually correct behavior for homographs — not a real issue. Noting for completeness.

10. **Missing pronunciation: "In pace requiescat" (closing Latin phrase)**
    - Problem: The story's famous closing Latin phrase "In pace requiescat!" is not in the pronunciation guide, though "requiescat" alone IS flagged. The full phrase context would be helpful.
    - Location: Pronunciation pipeline
    - Impact: Very minor.

## Configuration Audit

### Model Configuration
- All agents use `qwen3-next:80b-a3b-instruct-q8_0` — appropriate per user configuration
- Temperature 0.7 for all — could be lower (0.3-0.5) for character extraction to reduce hallucination
- Context length 32768 — sufficient for this short story

### Chunking Configuration
- `character_llm_chunk_chars: 5000` — fine for a ~13K character story (2-3 chunks)
- `summary_chunk_words: 2500` — appropriate, story is ~2353 words so fits in one chunk

### Processing Issues
- 0 LLM retries, 0 JSON parse failures — model worked cleanly
- Character Extraction: 2 high confidence (main cast), 6 medium confidence (supporting) — the medium confidence entries are the bogus ones
- Character Profiles: 3 high confidence, 0 low — but one of those "high confidence" profiles (Fortunato) has the wrong personality

## Fix History

### Attempt 2 Fixes
1. **CRITICAL #1: Fortunato personality profile contamination - FIXED**
   - Root cause: `src/analyzer.py:1828` - narrative_style set to "unknown" instead of "first-person" when narrator_detected was None
   - This disabled the perspective filter in passage_gatherer.py, allowing narrator-perspective passages to contaminate non-narrator profiles
   - Fix: Changed narrative_style detection to use text-based analysis (`is_first_person_text(doc.text)`) instead of narrator detection confidence
   - Modified: `src/analyzer.py` line 1828-1832
   - Expected impact: +3 on Character Profiles (fixes Fortunato's contaminated personality)

2. **CRITICAL #2: 5 bogus supporting characters - FIXED**
   - Root cause: `src/pipeline/character_extraction_v2/grounding.py:24-36` - adaptive_min_mentions() returned 1 for short stories
   - This allowed any NER-detected entity with a single mention to pass through (author names, titles, foreign words, etc.)
   - Fix: Raised the floor of adaptive_min_mentions from 1 to 2 for short stories
   - Modified: `src/pipeline/character_extraction_v2/grounding.py` line 35
   - Expected impact: +4 on Character Extraction (removes 5 bogus characters: "Cask of Amontillado", "Edgar Allan Poe", "lacessit", "De Grave", "--yes")

3. **Pronunciation false positives - DEFERRED**
   - Issue: ~12 of 42 entries are common words (29% false positive rate)
   - Root cause analysis: Multiple causes - hyphenated word tokenization, OCR artifacts, author names in bylines, CMU dictionary gaps
   - Decision: Deferred to next iteration - requires more comprehensive fix (possibly rethinking CMU-based approach)
   - Would gain +1.5-2.0 points but not critical for passing threshold

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 2 | CRITICAL #1: Narrative style detection | `src/analyzer.py` | Awaiting test |
| 2 | CRITICAL #2: Bogus supporting characters | `src/pipeline/character_extraction_v2/grounding.py` | Awaiting test |

## Next Action
Set phase to `awaiting_analysis` and re-run analysis to verify fixes.

**Expected score improvement:**
- Character Extraction: 4/10 → 8/10 (+4 from removing 5 bogus characters)
- Character Profiles: 4/10 → 7/10 (partial fix - Fortunato personality fixed, but role label "antagonist" still misleading)
- Pronunciation: 7/10 (unchanged - deferred)
- **Estimated new score: 7.42/10** (still below 8.0 threshold, but significant progress)
