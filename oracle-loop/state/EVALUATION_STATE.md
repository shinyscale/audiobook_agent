# Current Evaluation State

## Active Text
- **Name:** monkeys_paw
- **Attempt:** 1
- **Phase:** awaiting_fix
- **baseline_score:** 7.4

## Output Files
- HTML: ../output/monkeys_paw/report.html
- JSON: ../output/monkeys_paw/analysis.json

## Latest Scores
- Structure Detection: 8.5/10 ✓
- Character Extraction: 5/10 ✗
  - Completeness: 5/10
  - Identity Resolution: 4/10
  - Alias Grouping: 5/10
- Character Profiles: 6.5/10 ✗
- Chapter Summaries: 9.5/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 8/10 ✓
- **Overall: 7.4/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold: Character Extraction, Character Profiles)

## Current Issues (Priority Order)

### CRITICAL
1. **Sergeant-Major Morris missing from character output** [Completeness]
   - Problem: Morris was extracted (5 characters processed) but dropped from final output — only 4 remain. The profiling stage shows 1 low-confidence item (confidence 0.30). The analyze phase notes "Failed to parse JSON response for Sergeant-Major Morris (LLM JSON parse error)"
   - Evidence: Morris is a major character in Part I who brings the monkey's paw, tells of India and the wishes, and warns the family. He's listed in Chapter 1's character tags in the HTML. The summary correctly names him. He drives the entire plot.
   - Location: Profile confidence threshold in `src/analyzer.py` or profile generation. The JSON parse failure during profiling cascaded to low confidence → character dropped
   - Fix: Either (a) lower the confidence threshold for character inclusion, (b) retry profile generation on JSON parse failure, or (c) keep characters that appear in summaries regardless of profile confidence. The character extraction itself succeeded — the drop happened at the profiling stage.

2. **"the visitor" incorrectly aliased to "the monkey's paw"** [Identity Resolution]
   - Problem: The alias "the visitor" is assigned to the monkey's paw entry. In the actual text, "the visitor" refers to Sergeant-Major Morris in Part I and to the man from Maw and Meggins in Part II. The monkey's paw is an object, never a "visitor."
   - Evidence: Chapter 2's summary says "a well-dressed stranger from the firm 'Maw and Meggins' arrives" — "the visitor" is this person, not the paw. Chapter 1 characters list includes "Sergeant-Major Morris" who is also called "the visitor."
   - Location: Alias resolution in character extraction pipeline — Pass 2 or `verify_aliases` in `src/pipeline/character_extraction_v2/main_cast.py`
   - Fix: "the visitor" should not be assigned to a symbolic/object character. If Morris were present, "the visitor" would likely be resolved to him or remain unassigned (since it refers to two different people in different chapters).

### HIGH
3. **Mr. White has zero aliases** [Alias Grouping]
   - Problem: Mr. White has no aliases despite being referred to as "the old man" and "Father" throughout the text. Chapter 3's character list shows "the old man" as a separate unlinked reference.
   - Evidence: The profile itself says "he is referred to as an 'old man' and 'Father'" — the profiler KNOWS these are his aliases but they aren't in the alias list. Chapter 3 character tags show "the old man" unlinked to Mr. White.
   - Location: Pass 2 alias resolution failed for Mr. White. The analyze phase notes "Pass 2 failed for Mr. White (kept without aliases)." This is in `src/pipeline/character_extraction_v2/main_cast.py` or the alias consolidation step.
   - Fix: Debug why Pass 2 failed for Mr. White specifically. Possible LLM parse error or empty response. May need retry logic or fallback alias detection from profile text.

4. **Mrs. White's relationship to Herbert labeled "father" instead of "mother"** [Profiles]
   - Problem: Mrs. White's relationship entry for Herbert White says "father". She is Herbert's mother.
   - Evidence: Mrs. White is explicitly "his wife" (Mr. White's wife) and Herbert's mother. The text refers to her as the mother figure throughout.
   - Location: Profile generation in `src/analyzer.py` (`_generate_character_profile()`) or relationship label assignment. The `enforce_gender_consistency` step should have caught this — "father" is a MALE_ONLY_REL and Mrs. White is female.
   - Fix: Check why `enforce_gender_consistency` didn't correct "father" → "mother" for Mrs. White. Either gender wasn't detected for Mrs. White, or the enforcement step didn't run on this relationship.

### MEDIUM
5. **Chapter titles show Arabic numerals instead of Roman** [Structure]
   - Problem: Part I has null title, Parts II and III show as "2" and "3" instead of the original Roman numerals "II" and "III". HTML displays "Chapter 2: 2" (redundant).
   - Evidence: The Monkey's Paw uses Roman numeral section headers (I, II, III). The `_clean_title()` function in `src/pipeline/chapter_detection/consensus.py` may be converting Roman to Arabic or stripping Part I's heading.
   - Location: `src/pipeline/chapter_detection/consensus.py` — `_clean_title()`
   - Fix: Preserve original Roman numeral formatting. The null title for Part I suggests the heading wasn't detected at all for the first section.

6. **Chapter 3 characters show descriptors not mapped to characters** [Presentation]
   - Problem: Chapter 3's character tags show "the old man" and "the old woman" instead of "Mr. White" and "Mrs. White". These descriptors aren't linked to their character entries.
   - Evidence: In Part III, the text primarily uses descriptors ("the old man", "the old woman") rather than names. The summary mentions "old couple" and refers to "the wife" and "the husband". Since "the old man" isn't an alias of Mr. White, it appears as a separate unlinked tag.
   - Location: This is downstream of Issue #3 — if Mr. White had "the old man" as an alias, the summary character reconciliation would map it correctly.
   - Fix: Resolves with Issue #3 (alias grouping fix).

7. **Pronunciation false positives** [Pronunciation]
   - Problem: "bedclothes", "instalment", and "betokened" are relatively common English words flagged as needing pronunciation guidance. A narrator wouldn't struggle with these.
   - Evidence: These are standard English vocabulary — "bedclothes" is a compound of two common words, "instalment" is just British spelling of installment, "betokened" is a simple past tense.
   - Location: CMU proposer in `src/pipeline/pronunciation/cmu_proposer.py` — these words may not be in CMU dictionary. Could add to `COMMON_WORDS_WHITELIST`.
   - Fix: Add "bedclothes", "instalment", "betokened" to COMMON_WORDS_WHITELIST in cmu_proposer.py.

### LOW
8. **monkey's paw not marked as is_symbolic** [Character Metadata]
   - Problem: "the monkey's paw" has `is_symbolic: false` but it is a supernatural object/force, not a person. Should be `is_symbolic: true`.
   - Evidence: It's an inanimate cursed talisman. The profile correctly describes it as "an inanimate cursed object."
   - Location: Character extraction — symbolic detection heuristic may not trigger for objects with possessive nouns.
   - Fix: Low priority — doesn't affect narrator usability significantly.

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 7.4 | - | Baseline — Morris dropped, visitor alias wrong, Mr. White no aliases |

## Fix History
(none yet)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| (none yet) | | | |

## Configuration Audit
- Models: qwen3.5:35b-a3b (structure, pronunciation), qwen3.5:122b-a10b (chars, summaries, profiles) — appropriate
- Context length: 32768 — sufficient for this short story (3,954 words)
- Temperature: 0.7 — reasonable
- think_mode: false — correct for qwen3.5
- Character extraction had 1 JSON parse failure — this directly caused Morris to get a low-confidence profile and be dropped
- No retry issues (llm_retries: 0 across all stages)

## Next Action
Run PROMPT_fix.md to address:
1. Morris dropped due to profile parse failure (CRITICAL #1) — this is the primary blocker
2. "the visitor" alias on monkey's paw (CRITICAL #2)
3. Mr. White missing aliases (HIGH #3)
4. Mrs. White gender-inconsistent relationship label (HIGH #4)

Focus on Issues #1 and #3 as the highest-impact fixes. If Morris is restored and Mr. White gets aliases, Characters should jump from 5→7+ and Profiles from 6.5→8+.
