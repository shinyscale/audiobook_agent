# Current Evaluation State

## Active Text
- **Name:** i_have_no_mouth
- **Attempt:** 1
- **Phase:** awaiting_fix
- **baseline_score:** 7.35
- **Competitive Mode:** single

## Output Files
- HTML: ../output/i_have_no_mouth/report.html
- JSON: ../output/i_have_no_mouth/analysis.json
- Timestamped: ../output/I_Have_No_Mouth_And_I_Must_Scream_20260222_234032/

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 6/10 ✗ (FAILING)
  - Completeness: 5/10 ← AM missing is critical
  - Identity Resolution: 9/10
  - Alias Grouping: 8/10
- Character Profiles: 6/10 ✗ (FAILING)
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 6/10 ✗ (FAILING)
- HTML Presentation: 8.5/10 ✓
- **Overall: 7.35/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 7.35 | 0.00 | Baseline. AM missing, false positives, pronunciation artifacts |

## Current Issues (Priority Order)

### CRITICAL
1. **AM (the supercomputer) is completely missing from character list** [Completeness]
   - Problem: AM is the primary antagonist of the entire story — a sentient supercomputer that has imprisoned the 5 survivors for 109 years. It speaks directly (including a famous hate monologue), acts, tortures, and transforms characters. AM is referenced ~39 times in the report itself (in summaries, evidence, relationships) yet never extracted as a character entity.
   - Evidence: "AM" appears throughout the text as a named entity. It has aliases: "Allied Mastercomputer", "Adaptive Manipulator", "Aggressive Menace". The story's entire plot revolves around AM's actions.
   - Location: Character extraction pipeline (`src/pipeline/character_extraction_v2/`). AM may be getting filtered because it's a 2-letter acronym, or because NER doesn't recognize it as a name. All 7 extracted characters come from `supporting_*` IDs — the main cast pipeline produced 0 characters, suggesting it failed entirely for this text.
   - Fix: The main cast pipeline needs to handle short-name/acronym entities better, or AM needs to be caught by the supporting cast pipeline. Since AM is referenced more than any individual character in the text, it should not be filtered by mention count.

2. **Ted is not flagged as narrator** [Completeness / Profiles]
   - Problem: Ted is the first-person narrator of the story. `is_narrator: false`. The story is told entirely from Ted's perspective using "I". His mention count (5) is artificially low because as narrator he uses first-person pronouns, not his name.
   - Evidence: The story opens with Ted's narration and ends with his famous line "I have no mouth, and I must scream." The plot summary correctly identifies Ted as the one who kills the others, but doesn't flag him as narrator.
   - Location: Narrator detection in summary/profile pipeline. The `narrative_style: "unknown"` in the overview confirms the pipeline failed to detect first-person narration.
   - Fix: The narrator detection logic should recognize first-person narration patterns ("I said", "I thought", etc.) and link them to named characters who appear in the same passages.

### HIGH
3. **False positive character: "Jesus"** [Completeness]
   - Problem: "Jesus" (4 mentions) is extracted as a supporting character. In this text, "Jesus" appears only as an exclamation ("Jesus God", "Christ") not as an actual character in the story.
   - Evidence: The character has no aliases, no appearance, no personality, no relationships, no evidence entries — completely empty. This is clearly an exclamation being treated as a character name.
   - Location: Supporting cast pipeline filtering (`src/pipeline/character_extraction_v2/supporting.py`). Exclamatory religious names should be filtered.
   - Fix: Add filtering for exclamatory name usage — if a name only appears in exclamation contexts (followed by "!", preceded by "Oh", etc.) and has zero profile data, it should be excluded.

4. **False positive character: "bush"** [Completeness]
   - Problem: "bush" (2 mentions, lowercase) is extracted as a minor character. This is a common noun, not a character name. The pipeline itself flagged it as low confidence.
   - Evidence: Lowercase, no profile data, no relationships, no evidence. Listed in `low_confidence_items`.
   - Location: Supporting cast pipeline. A common-noun filter or minimum confidence threshold should exclude this.
   - Fix: Characters flagged as low confidence with zero profile data should be automatically excluded.

5. **Systematic wrong age extraction for all characters** [Profiles]
   - Problem: Benny, Ellen, and Gorrister all show "Age: five years". Ted shows "Age: nine years". These are nonsensical — the characters have been trapped for 109 years and are adults. The "five" likely comes from "five survivors" being misinterpreted as an age, and "nine" may come from a similar contextual misread.
   - Evidence: Benny age "five years", Ellen age "five years", Gorrister age "five years", Ted age "nine years".
   - Location: Age extraction in character profiles pipeline (`src/pipeline/character_extraction_v2/` or profile generation).
   - Fix: This was addressed for john_g with "universal deterministic age extraction" (commit 592c0b2). Verify that fix applies here — these ages are clearly wrong and should not pass validation.

### MEDIUM
6. **PDF artifact words in pronunciation guide** [Pronunciation]
   - Problem: 6 entries are concatenated word artifacts from PDF extraction: "we'lldie", "Nimdokwith", "ifwe", "mefrom", "myright", "mysurface". These are not real words.
   - Evidence: These are clearly two words merged together during PDF text extraction. The ingestion pipeline rejoined 47 split words but these concatenations slipped through.
   - Location: Pronunciation validation or ingestion refinement (`src/ingestion/refine.py`, `src/pipeline/pronunciation/`).
   - Fix: Add validation to reject pronunciation entries that match common concatenation patterns (camelCase-like mid-word capitals, entries containing known word boundaries). Or improve PDF text extraction to catch these.

7. **Common word false positives in pronunciation** [Pronunciation]
   - Problem: Several common English words don't need pronunciation guidance: "palette", "tinfoil", "firelight", "snowdrifts", "loonie", "piteously", "spastically". These are standard English words any narrator would know.
   - Evidence: All are common English words with standard pronunciation. A narrator doesn't need help pronouncing "tinfoil" or "snowdrifts".
   - Location: Pronunciation filtering (`src/pipeline/pronunciation/`).
   - Fix: Improve the common-word filter or frequency threshold to exclude standard compound words and common English vocabulary.

8. **Possessive forms as separate pronunciation entries** [Pronunciation]
   - Problem: "Gorrister's" and "Nimdok's" appear as separate entries alongside "Gorrister" and "Nimdok". Possessive forms should not be separate pronunciation entries.
   - Evidence: "Gorrister" and "Gorrister's" are separate entries with nearly identical IPA.
   - Location: Pronunciation deduplication logic.
   - Fix: Strip possessive suffixes ('s, s') before deduplication.

9. **Incorrect IPA for "choir"** [Pronunciation]
   - Problem: IPA listed as /kwɑːr/ which is incorrect. The correct IPA is /kwaɪər/.
   - Evidence: "choir" is pronounced with a diphthong, not a monophthong.
   - Location: IPA generation in pronunciation pipeline.
   - Fix: This may be an LLM hallucination. No easy generic fix beyond improving the IPA validation step.

10. **Incorrect IPA for "cogito"** [Pronunciation]
    - Problem: IPA listed as /kəˈdʒiː.toʊ/ which treats the 'g' as /dʒ/. Standard pronunciation is /ˈkoʊɡɪtoʊ/ (English) or /ˈkɔɡɪtɔː/ (Latin).
    - Evidence: "cogito ergo sum" is a well-known Latin phrase with established pronunciation.
    - Location: IPA generation in pronunciation pipeline.
    - Fix: Same as above — LLM IPA generation quality issue.

### LOW
11. **Relationships reference "Jesus" and "bush" as "unknown"**
    - Problem: Multiple real characters (Benny, Ellen, Nimdok, Ted) list relationships to "Jesus" and "bush" as "unknown". These should not appear in relationship lists.
    - Evidence: Every character's relationship dict includes `"Jesus": "unknown"` and `"bush": "unknown"`.
    - Location: Relationship extraction in profiles pipeline.
    - Fix: Will be resolved automatically when false positive characters are removed.

12. **Nimdok's appearance incorrectly says "resembles a chimpanzee"**
    - Problem: It's Benny who AM altered to have a monkey-like appearance, not Nimdok. Nimdok's distinguishing features list says "resembles a chimpanzee as intended by AM" which is incorrect attribution.
    - Evidence: The text describes Benny as having been altered by AM to have simian features. Nimdok is not described this way.
    - Location: Profile generation - evidence was attributed to the wrong character.
    - Fix: LLM profile accuracy issue. No easy generic fix.

## Fix History
(No previous attempts)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| (none yet) | - | - | - |

## Next Action
Run PROMPT_fix.md to address:
1. CRITICAL: AM missing from character list (main cast pipeline failure)
2. CRITICAL: Ted not flagged as narrator
3. HIGH: False positive characters "Jesus" and "bush"
4. HIGH: Wrong age extraction
5. MEDIUM: Pronunciation artifacts and false positives

Focus on issues #1-4 first as they affect Character Extraction (6/10) and Profiles (6/10) — the two biggest failing categories. Pronunciation fixes (#6-8) can follow if needed.
