# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 1
- **Phase:** awaiting_fix
- **baseline_score:** 6.55
- **Competitive Mode:** none

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 5/10 ✗ (FAILING)
  - Completeness: 6/10
  - Identity Resolution: 4/10 ← primary blocker
  - Alias Grouping: 5/10
- Character Profiles: 4/10 ✗ (FAILING)
- Chapter Summaries: 6/10 ✗ (FAILING)
- Pronunciation Guide: 8.5/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 6.55/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.55 | 0 | Baseline. Narrator misidentification cascades into profiles + summaries |

## Current Issues (Priority Order)

### CRITICAL

1. **Wrong narrator: Uncle Bill is the first-person frame narrator, but Johnny is tagged as narrator** [Identity Resolution]
   - Problem: The story has a frame narrator (Uncle Bill, the "I" who opens with "I threw the letter...") and an inner narrator (Johnny, whose war story is quoted dialogue). The pipeline tagged Johnny (main_cast_0) as `is_narrator=true` and created Uncle Bill (main_cast_3) as a separate non-narrator character.
   - Evidence: The text opens "I threw the letter in the scrap-basket..." — this "I" is Uncle Bill. He describes himself: "an elderly, grizzled, small man, grim and unexhilarating" (line 128-129). Johnny's war account is all within quotes ("You know, Uncle Bill, we were blamed proud..."). Uncle Bill speaks at the very end ("John," I said, "we two know the splendor...")
   - Impact: CASCADING — causes wrong profile attribution (Uncle Bill's appearance → Johnny), wrong relationships, summary hallucinations
   - Location: Narrator detection in `src/pipeline/character_extraction_v2/` and/or `_get_narrative_style()` in `src/agents/characters.py`
   - Fix approach: The narrator detection needs to distinguish between the frame "I" narrator and quoted first-person speech. The frame narrator's "I" appears outside quotation marks; Johnny's "I" appears within extensive quoted dialogue. Uncle Bill should be recognized as the narrator since he is the unquoted first-person voice.

2. **False alias: "the boy" assigned to John Donaldson (Father) instead of son** [Alias Grouping / Identity Resolution]
   - Problem: "the boy" appears 10+ times in the text and ALWAYS refers to the son (Johnny), never the father. Yet it's listed as an alias of "John Donaldson (Father)" (main_cast_2).
   - Evidence: "the boy, standing before the blazing logs" (line 151), "The boy rose from his chair" (line 197), "the boy went on" (line 361) — all refer to Johnny/the son. The father is called "the man", "the old boy", "the shabby American volunteer", never "the boy."
   - Impact: Inflates father's mention count, deflates son's. Son (Johnny) shows only 2 mentions when he should have 20+.
   - Location: Alias resolution in V2 character extraction pipeline — likely Pass 2 or verify_aliases
   - Fix approach: The pipeline should check textual context when assigning descriptive aliases like "the boy." When two characters share a surname, age-descriptive aliases ("the boy" vs "the man"/"the old boy") should be assigned based on age evidence.

3. **Summary hallucination: "the narrator later comforts a dying Uncle Bill"** [Summaries]
   - Problem: The summary states "the narrator later comforts a dying Uncle Bill who fears dishonor until the narrator calls him 'father'". Uncle Bill does NOT die. The dying man is John Donaldson (the father). Johnny comforts his dying father, not Uncle Bill.
   - Evidence: Lines 351-526 — Johnny finds his wounded father, carries him to a church, holds his hand as he dies. Uncle Bill is at home the entire time, listening to Johnny tell the story.
   - Impact: Factual error makes the summary actively misleading for a narrator preparing to record
   - Location: Summary generation — likely downstream of narrator confusion (if the summarizer thinks Johnny is the narrator, it may conflate Uncle Bill with the dying father)
   - Fix approach: This likely resolves if narrator identification is fixed (Issue #1), since the summary LLM will correctly understand the frame structure

### HIGH

4. **Johnny's profile contains Uncle Bill's physical description and personality** [Profiles]
   - Problem: Johnny's profile says "an elderly, grizzled, small man, grim and unexhilarating" — this is Uncle Bill describing HIMSELF (line 128-129). Johnny is young, tall, olive-skinned with blue eyes and thick dark lashes (lines 91-93, 197-198).
   - Evidence: "He was a tall boy, and he looked like his father. Very olive he was--and is--and his blue eyes shone out of the dark face from under the same thickset and long lashes" (line 91-93)
   - Impact: Completely wrong physical description for the protagonist's son
   - Location: Profile generation in `src/analyzer.py` — `_generate_character_profile()`. Downstream of narrator confusion.
   - Fix approach: Resolves if narrator identification is fixed (Issue #1)

5. **All relationships are generic ("close friend", "associated") instead of family terms** [Profiles]
   - Problem: Johnny → John Donaldson (Father) is "close friend" (should be "son"). John Donaldson (Father) → Johnny is "close friend" (should be "father"). Uncle Bill → Johnny should be "guardian/uncle figure". Uncle Bill → John Donaldson should be "cousin."
   - Evidence: "The man I was helping to die was my father" (line 401). Uncle Bill describes being John's cousin who shared a room for a dozen years (lines 29-42). Uncle Bill becomes Johnny's guardian (lines 74-88).
   - Location: `post_corrections.py` → `verify_relationships_from_text`, and profile generation
   - Fix approach: The father-son relationship is explicitly stated in the text. The pipeline should detect "my father" / "his son" phrases in co-mention windows.

6. **Margaret Donaldson missing from character list** [Completeness]
   - Problem: Margaret Donaldson, John's wife and Johnny's mother, is mentioned by name (lines 59, 75) and her letter is quoted. She was noted in pipeline logs as "added from mentioned_characters" but doesn't appear in final output.
   - Evidence: "I had a note signed Margaret Donaldson, John's wife" (line 59-60). "Margaret Donaldson's boy was left with her poor and elderly parents" (line 75)
   - Impact: Minor — she's a background character but named and plot-relevant (her death triggers Johnny coming to Uncle Bill)
   - Location: May have been filtered by mention count threshold or dropped during merges
   - Fix approach: Not critical for passing. Can revisit if other issues are resolved.

### MEDIUM

7. **Summary factual error: "welcoming John's twelve-year-old son back from a fishing trip"** [Summaries]
   - Problem: Uncle Bill went to the boy's school commencement and THEN took him on a fishing trip to Canada. The summary implies the boy was returning from an existing fishing trip.
   - Evidence: Lines 86-97 — "I will come to your commencement and bring you back with me... I may take you on a fishing trip to Canada."
   - Fix approach: Will likely improve with better narrator identification

8. **Characters_present in structure lists fragmented identities** [Identity Resolution]
   - Problem: The chapter's `characters_present` lists "Uncle Bill", "John Donaldson", "The narrator", "The American volunteer", "The dying man" as 5 separate entities. "The narrator" = Uncle Bill. "The American volunteer" = "The dying man" = John Donaldson (Father).
   - Location: Summary stage character listing
   - Fix approach: Downstream of character extraction; will improve with better identity resolution

9. **Roles misassigned: Ted Frith (5 mentions) labeled "main", John Donaldson Father (43 mentions) labeled "supporting"** [Identity Resolution]
   - Problem: The father is the most-mentioned character (43) but has role "supporting". Ted Frith with only 5 mentions has role "main". Johnny with 2 mentions has role "protagonist".
   - Location: Role assignment logic in character extraction pipeline
   - Fix approach: Likely resolves with better mention attribution once aliases are corrected

### LOW

10. **Null chapter title for single-section text**
    - Problem: Structure `title` is null. Could show "American, Sir!" from the text header.
    - Impact: Very minor presentation issue

## Fix History
(First attempt — no previous fixes)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| (none yet) | - | - | - |

## Root Cause Analysis

The central problem is **frame narrator misidentification**. This story has a nested narrative structure:
- **Frame**: Uncle Bill narrates in first person (unquoted "I" text)
- **Inner**: Johnny tells his war story in quoted dialogue (quoted "I" text)

The pipeline picked Johnny as the narrator, likely because Johnny's extensive quoted speech uses first person. This cascades into:
1. Uncle Bill's self-descriptions attributed to Johnny (profiles)
2. "the boy" alias misattributed (the frame narrator calls the son "the boy")
3. Summary confuses who dies and who is being comforted
4. Relationships all wrong (narrator identity affects family detection)

**Fix priority**: Fixing narrator identification (#1) should cascade improvements to profiles (#4), summaries (#3), and relationships (#5). The "the boy" alias issue (#2) may need a separate fix in alias resolution.

## Configuration Notes
- Model config looks appropriate: qwen3.5:122b-a10b for characters/summaries, qwen3.5:35b-a3b for structure
- Zero LLM retries across all stages — no prompt/schema failures
- All 14 pronunciations have IPA — good coverage

## Next Action
Run PROMPT_fix.md to address narrator misidentification (Critical #1) and cascading issues
