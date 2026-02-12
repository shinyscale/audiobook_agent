# Current Evaluation State

## Active Text
- **Name:** berenice
- **Attempt:** 2
- **Phase:** awaiting_evaluation
- **baseline_score:** 8.15
- **Competitive Mode:** single

## Output Files
- HTML: ../output/berenice/report.html
- JSON: ../output/berenice/analysis.json

## Pipeline Notes (Attempt 2)
- Analysis completed in 31m 21s
- Competitive consensus enabled on all 3 stages (characters, structure, summaries)
- Found 2 characters: Berenice (14 mentions), Egaeus (1 mention)
- 54 pronunciation flags (46 unknown, 6 foreign, 2 proper_noun)
- OCR repair: fixed 1 broken ligature
- Warnings: F6 hallucination detected (servant maiden), F19 ungrounded evidence quotes

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 7/10 ✗ (FAILING)
- Character Profiles: 8/10 ✓
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 7/10 ✗ (FAILING)
- HTML Presentation: 9/10 ✓
- **Overall: 8.15/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold)

## Current Issues (Priority Order)

### CRITICAL
(none)

### HIGH
1. **False character extraction: "amicae visitarem" is a Latin phrase, not a character**
   - Problem: "amicae visitarem" is extracted as a supporting character (ID: `supporting_0`, 2 mentions). It's a Latin phrase from the story's epigraph meaning "if I should visit [the grave of] my beloved" — not a person or entity with agency.
   - Evidence: The profiling itself acknowledges "not a character but a Latin phrase referring to 'a friend's tomb'" — yet it's still listed.
   - Location: `src/pipeline/character_extraction_v2/` — the extraction pipeline or supporting cast filter should exclude non-entity Latin phrases.
   - Fix: The CHARACTER_IDENTIFICATION_PROMPT or supporting cast pipeline should better distinguish Latin/foreign-language phrases from actual character names. This is a prompt-level issue — the LLM needs to understand that Latin epigraph fragments are not characters. Alternatively, post-extraction filtering could check for multi-word entries that the profiling LLM itself identifies as "not a character."

2. **Pronunciation false positives: 8 common English words flagged unnecessarily**
   - Problem: These common English words are flagged as pronunciation items: "sentiments", "refracted", "sentient", "conformation", "tarried", "emaciation", "multiform", "aslant". Any English-speaking narrator would know these.
   - Evidence: These are standard vocabulary words found in any English dictionary; they are not foreign, archaic, or unusual.
   - Location: `src/pipeline/pronunciation/` — the pronunciation flagging pipeline is too aggressive.
   - Fix: The pronunciation agent's filtering needs better common-word exclusion. Previous fix (commit a105688) added common English words to exception lists — these 8 words may have been missed.

### MEDIUM
3. **Relationship labels are inverted for Berenice**
   - Problem: Berenice lists Egaeus as "victimizer" and Egaeus lists Berenice as "victimizer". In reality, Egaeus victimizes Berenice (correct for Berenice's entry), but Berenice does NOT victimize Egaeus — she is his **cousin** and **victim/betrothed**.
   - Evidence: In the story, Egaeus extracts Berenice's teeth while she is buried alive. She is a passive victim, not a victimizer of Egaeus.
   - Location: `src/pipeline/character_profiling/` — relationship extraction LLM call is generating symmetric labels incorrectly.
   - Fix: The relationship extraction should use directional labels (e.g., Berenice→Egaeus: "victim of" or "cousin"; Egaeus→Berenice: "victimizer" or "cousin"). This is a prompt-level issue in the profiling pipeline.

4. **Borderline pronunciation entries could be trimmed**
   - Problem: 11 archaic-but-common English words are flagged: "shrubberies", "monomania", "light-heartedness", etc. While some are reasonable (e.g., "pertinaciously"), others like "shrubberies" are well-known to English speakers.
   - Evidence: "shrubberies" and "monomania" are standard English words, not unusual enough to warrant pronunciation guidance.
   - Location: Same as issue #2 — `src/pipeline/pronunciation/` exception lists.
   - Fix: Add the most obviously common words ("shrubberies", "light-heartedness") to the exception list. Keep truly unusual ones like "pertinaciously."

### LOW
5. **Structure title is null**
   - Problem: The single structural element has `title: null` rather than "Berenice" or a meaningful label.
   - Evidence: `jq '.structure[0].title'` returns `null`.
   - Location: `src/pipeline/chapter_detection/` — single-chapter detection doesn't assign a title.
   - Fix: When a text has only one structural unit, use the work's title as the chapter title.

## Fix History
- Attempt 2: Fixed Latin phrase false extraction (HIGH #1)
  - Root cause: `supporting.py::_is_valid_name()` didn't filter multi-word foreign language phrases
  - Smoke test: PASS - "amicae visitarem" now filtered, English names allowed
  - Modified: `src/pipeline/character_extraction_v2/supporting.py`
  - Approach: Added `_is_likely_foreign_phrase()` using universal grammatical patterns (Latin/Greek verb endings), not vocabulary lists
  - Impact: Should filter Latin/Greek/foreign epigraph fragments in any book

- Attempt 2: Added 8 common words to pronunciation exceptions (HIGH #2)
  - Root cause: CMU and Foreign proposers lacking these common English words in exception lists
  - Smoke test: PASS - All 8 words ("sentiments", "refracted", "sentient", "conformation", "tarried", "emaciation", "multiform", "aslant") now in both lists
  - Modified: `src/pipeline/pronunciation_guide/proposers/cmu_proposer.py`, `foreign_proposer.py`
  - Note: Added TODO to replace deny-list approach with frequency-based filtering (wordfreq library)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 2 | HIGH #1: Latin phrase false extraction | supporting.py | awaiting_analysis |
| 2 | HIGH #2: Pronunciation false positives | cmu_proposer.py, foreign_proposer.py | awaiting_analysis |

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (correct per user settings)
- No JSON parse failures in character extraction or summaries
- 3 JSON parse failures in pronunciation (minor)
- character_llm_chunk_chars: 5000 (appropriate for short story)
- No retries needed across pipeline
- Bottleneck: Character Profiles (26% of total time) — acceptable

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 8.15 | - | Baseline. Characters 7/10, Pronunciation 7/10 |

## Next Action
Re-run analysis to verify fixes for HIGH #1 and HIGH #2.
Expected improvements:
- Characters: 7/10 → 8+/10 (remove false "amicae visitarem" extraction)
- Pronunciation: 7/10 → 8+/10 (reduce false positives by 8 words)
