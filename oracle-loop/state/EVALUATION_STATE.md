# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 8
- **Phase:** awaiting_evaluation
- **baseline_score:** 6.55
- **Competitive Mode:** none

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 6/10 ✗ (FAILING)
  - Completeness: 7/10
  - Identity Resolution: 5/10 ← father/son false merge is primary blocker
  - Alias Grouping: 6/10
- Character Profiles: 6/10 ✗ (FAILING)
- Chapter Summaries: 5/10 ✗ (FAILING)
- Pronunciation Guide: 8.5/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 6.9/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold)

## What Attempt 7 Changed vs Attempt 6

**Improved:**
- John Donaldson is_narrator=False ✓ (mention-count guard blocked false secondary narrator)
- John Donaldson's profile now describes BOTH father and son correctly ✓ (no longer has Bill's traits)
- Uncle Bill's profile has correct physical description ✓ ("elderly, grizzled, small man")
- Profiles improved from 4.5 → 6 due to narrator fix cascade

**Still broken / new issues:**
- **NEW:** The boy (Johnny/young John) completely ABSENT as a separate character — merged into "John Donaldson" (father+son combined, 28 mentions). In attempt 6, "John's Son" existed with 14 mentions as a distinct entry.
- **WORSE:** Plot summary FABRICATES a false twist: claims "the narrator is not John's uncle but his biological father, having taken the name 'Uncle Bill' to protect the boy" — THIS IS COMPLETELY INVENTED. The real twist is that the Dark-Skinned Volunteer is John Donaldson (the boy's father), not that Bill is the father.
- Uncle Bill's personality STILL contaminated by the boy's first-person war narration: "caring for his dying father" and "crying like a child with a feeling I'd never known before when embracing his father" — these are the BOY's experiences, not Bill's. Bill isn't present at the deathbed.
- Chapter summary says "the narrator's long-lost father" — should be "the boy's father" / "John's father"
- Roles still wrong: Ted Frith (5 mentions) = "main", John Donaldson (28 mentions) = "supporting"
- Relationships still all generic ("associated")

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.55 | 0 | Baseline. Narrator misidentification cascades into profiles + summaries |
| 2 | 6.6 | +0.05 | Narrator fix worked (Bill=narrator ✓, Bill profile correct ✓). But Johnny still missing, summary still wrong. |
| 3 | 6.0 | -0.55 | **REGRESSION.** "American, sir" false character stole narrator from Uncle Bill. Johnny still missing. |
| 4 | 6.4 | -0.15 | Co-present guard fixed "American, sir" ✓, but narrator REGRESSED (Johnny instead of Bill). Johnny/John's Son false split. |
| 5 | 6.7 | +0.15 | Plot summary improved (correctly names Uncle Bill). But narrator metadata STILL wrong. Step 5.4.6 merged "the boy" into father. |
| 6 | 7.0 | +0.45 | Uncle Bill narrator ✓, merge direction fixed ✓. But John Donaldson false secondary narrator → profile catastrophe. |
| 7 | 6.9 | +0.35 | Narrator guard worked ✓ (John Donaldson not narrator). But boy disappeared (false merge), plot summary fabricates false twist. |

## Current Issues (Priority Order)

### CRITICAL

1. **Plot summary FABRICATES a false central twist** [Summaries]
   - Problem: The HTML plot summary (lines 643-647 of report.html) claims: "the narrator is not John's uncle but his biological father, having taken the name 'Uncle Bill' to protect the boy." This is COMPLETELY INVENTED. In the actual story, the twist is that the Dark-Skinned Volunteer is revealed to be John Donaldson (the boy's father who ran away years ago). Bill IS the boy's guardian/"uncle" — he is NOT the biological father.
   - Impact: A narrator reading this would fundamentally misunderstand the story's central revelation and perform the entire piece with the wrong subtext.
   - Root cause: The LLM generating the plot summary hallucinated an inverted twist. The `plot_summary` field is null in analysis.json, so this is generated in the HTML export step. The LLM may be confusing the nested narrative layers (Bill narrates → boy narrates his war experience → boy discovers his dying father).
   - Location: HTML export step that generates plot summaries — likely `src/export/` or the HTML template generation code. Also possibly fed by the chapter summary's own errors (which say "the narrator's long-lost father" — misidentifying WHO the father is father OF).
   - Fix approach: The plot summary generation prompt needs stronger grounding. Consider: (a) validate the plot summary against character relationships in the analysis, (b) lower temperature for plot summary generation, (c) include character relationship data in the plot summary prompt so the LLM knows "Uncle Bill" and "John Donaldson" are friends/classmates, not parent/child.

2. **Chapter summary attributes father relationship to wrong character** [Summaries]
   - Problem: Chapter summary says "This volunteer is revealed to be the narrator's long-lost father" — the volunteer is NOT the narrator's (Bill's) father. He is JOHN's (the boy's) father. Also says "suspicious death of John's father" — John Donaldson didn't die suspiciously; he ran away after theft. Also garbled ending: "revealed to be his father's son rather than his uncle."
   - Evidence: 3 factual errors in the chapter summary, all related to confused family relationships across narrative layers.
   - Location: Summary generation pipeline — `src/pipeline/summarization/` or `src/agents/summary_agent.py`
   - Fix approach: The summary prompt may need to be more explicit about distinguishing "the narrator" from characters narrating embedded stories. When a character WITHIN the story tells their own tale in first person, the summary should attribute that nested narration to the character, not to the frame narrator.

### HIGH

3. **Father-son false merge: John Donaldson** [Identity Resolution]
   - Problem: John Donaldson (the father, ~14 mentions) and the boy/Johnny/young John (the son, ~14 mentions) are merged into a SINGLE character entry with 28 combined mentions. They are distinct people: the father is a charming wastrel who ran away and died in WWI; the son is a brave young ambulance driver who discovers his dying father.
   - Evidence: `John Donaldson: aliases=["John", "young John"], mentions=28`. The profile acknowledges both people ("The father is portrayed as..." / "The son is depicted as...") but they share one entry. In attempt 6, "John's Son" existed as a separate character with 14 mentions.
   - Root cause: Both characters share the name "John Donaldson." The pass-1 extraction groups all mentions of "John" and "John Donaldson" together. The alias "young John" is treated as a variant of "John" rather than a DIFFERENT person.
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` (pass 1 extraction) or `src/agents/characters.py` (merge pipeline)
   - Fix approach: This is a genuinely hard same-name disambiguation problem. Possible approaches:
     - (a) If a character profile references BOTH "the father" and "the son" as separate people, flag for potential false merge
     - (b) Age-modifier aliases ("young X", "old X", "little X") should trigger split consideration when the character has high mentions
     - (c) Post-extraction validation: if the profiler describes TWO distinct people in one entry, split them
     - NOTE: Any fix must be GENERIC (no novel-specific logic). This pattern (parent and child with same name) occurs in many novels.

4. **Uncle Bill's profile contaminated by nested first-person narration** [Profiles]
   - Problem: Uncle Bill's personality says "displays immense compassion and courage while caring for his dying father" and his quotes include "I whispered with my arms around him and crying like a child" — these are the BOY's first-person narration of the war story, not Bill's own experience. Bill isn't present at the deathbed scene.
   - Evidence: Personality summary attributes the deathbed vigil to Bill. The text has the boy telling this story in first person ("I found him", "I saw").
   - Root cause: The profiler sees all first-person "I" statements and attributes them to the primary narrator (Bill). In a nested narrative, the inner narrator's "I" belongs to a different character.
   - Location: `src/pipeline/profiling/` or `_generate_character_profile()` in `src/analyzer.py`
   - Fix approach: When `narrative_style` indicates first-person AND character profiles reveal embedded narration, the profiler should recognize that not all "I" statements belong to the frame narrator. This is the same class of problem as issue #2 (nested narration confusion).

5. **Role assignment wrong** [Identity Resolution]
   - Problem: Ted Frith (5 mentions) = "main", while John Donaldson (28 mentions) = "supporting". Characters with higher mention counts should not be outranked by characters with much lower counts.
   - Location: `src/agents/characters.py` — role assignment logic
   - Fix approach: Role assignment should factor in mention count. A character with 28 mentions should never be "supporting" when a character with 5 mentions is "main." This should be a simple threshold-based fix.

### MEDIUM

6. **Relationships all generic ("associated")** [Profiles]
   - Problem: Every relationship is "associated" or "companion". Should be: Bill→John Donaldson: "friend/classmate", Bill→the boy: "guardian/uncle figure", the boy→John Donaldson: "son", Dark-Skinned Volunteer→John Donaldson: "same person" or "disguise".
   - Fix: May improve with better profiler prompts but is low priority compared to CRITICAL issues.

7. **Missing aliases: "Johnny" and "Teddy"** [Alias Grouping]
   - Problem: The boy is called "Johnny" in the text (line ~326), Ted Frith is called "Teddy" (lines ~345, ~422). Neither alias appears.
   - Fix: `NICKNAME_TO_FORMAL` dict could help if "Johnny"→"John" mapping exists. "Teddy"→"Ted"/"Edward" may need to be added.

8. **Margaret Donaldson still missing** [Completeness]
   - Problem: Mentioned by name in text. F6b should have caught her but she's absent from the 6 final characters.
   - Impact: Very minor — she's barely mentioned and dies before the main narrative.

### LOW

9. **Null plot_summary in JSON** [Summaries]
   - Problem: `plot_summary: null` in analysis.json, though the HTML has a generated plot summary.
   - The HTML export must generate it separately. Should be populated in the JSON too for consistency.

## Fix Strategy for Attempt 8

**ROOT CAUSE ANALYSIS:** The 3 failing categories share a common root cause — **nested first-person narration confusion**. The text has three narrative layers:
1. Frame: Uncle Bill narrates (first person)
2. Embedded: The boy tells his war story to Uncle Bill (first person within Bill's narration)
3. Dialogue: John Donaldson speaks within the boy's story

The pipeline conflates layers 1 and 2, attributing the boy's "I" to Bill, and merging the boy with his identically-named father.

**RECOMMENDED APPROACH — Fix summaries first (highest leverage):**

The summary is upstream of profiles and the plot summary. If the chapter summary correctly identifies the nested narrative structure and WHO the relationships are between, the downstream profile generation and plot summary will improve automatically.

1. **Fix the summary prompt** to handle nested first-person narratives: when a frame narrator (Bill) recounts another character's first-person story, the summary should clearly attribute the embedded narrative to the inner narrator (the boy), not the frame narrator.

2. **Fix the plot summary generation** (likely in HTML export) to be grounded in character relationship data rather than re-interpreting the story from scratch. Pass character relationships into the prompt so the LLM knows Bill and John Donaldson are friends/classmates, not parent/child.

3. **Fix role assignment** as a simple mention-count-based correction. Quick win.

**Do NOT touch:**
- narrator.py (attempt 7 guard working correctly)
- characters.py Step 5.4.5 (co-present guard working)
- characters.py Step 5.4.6 (merge direction fix working)

## Fix History
- Attempt 2: Fixed narrator detection to trust explicit "narrator, known as [Name]" identification
  - Modified: `src/pipeline/character_extraction_v2/narrator.py`
  - Result: Fixed — Bill is now narrator ✓
- Attempt 3: Added exact_firstname guard to `_merge_lastname_aliases`
  - Modified: `src/agents/characters.py` — `_merge_lastname_aliases()`
  - Result: **REGRESSION** — "American, sir" false character, narrator shifted. REVERTED.
- Attempt 4: Reverted attempt 3, then applied co-present guard to `_merge_summary_name_fragments()` (Step 5.4.5)
  - Modified: `src/agents/characters.py` — `_merge_summary_name_fragments()`
  - Result: "American, sir" gone ✓, narrator regressed ✗, Johnny/John's Son false split ✗
- Attempt 5:
  1. Improved narrator prompt: added frame-narrative clarification
     - Modified: `src/pipeline/character_extraction_v2/narrator.py`
  2. Added Step 4.26 low-mention narrator guard (CRASHED: `'list' object has no attribute 'get'`)
     - Modified: `src/agents/characters.py` — new Step 4.26 block
  3. Added Step 5.4.6 possessive-descriptor merge (WRONG DIRECTION: merged into father not son)
     - Modified: `src/agents/characters.py` — new Step 5.4.6 block
  - Result: Plot summary improved ✓. Narrator still wrong ✗. "the boy" on father instead of son ✗.
- Attempt 6:
  1. Fixed `narrator.py detect()` crash (list vs dict unwrapping)
     - Modified: `src/pipeline/character_extraction_v2/narrator.py`
  2. Raised min-mention narrator guard from ≤1 to ≤2
     - Modified: `src/pipeline/character_extraction_v2/narrator.py`
  3. Fixed Step 5.4.6 merge direction (descriptor→proper name)
     - Modified: `src/agents/characters.py`
  - Result: Uncle Bill narrator ✓. Merge direction fixed ✓. But John Donaldson false secondary narrator → profile catastrophe.
- Attempt 7:
  1. Added mention-count guard for secondary narrators in `update_characters_with_narrator()`
     - Modified: `src/pipeline/character_extraction_v2/narrator.py`
     - Result: John Donaldson no longer false secondary narrator ✓. Profiles improved (4.5→6) ✓.
     - New: Boy (Johnny) disappeared — merged into father. Plot summary fabricated false twist.

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 2 | Wrong narrator (Uncle Bill vs Johnny) | `narrator.py` | Fixed — Bill is now narrator ✓ |
| 3 | Johnny missing — exact_firstname guard | `characters.py` | **REGRESSION** — REVERTED |
| 4 | Johnny false-merged — co-present guard Step 5.4.5 | `characters.py` | "American, sir" gone ✓, narrator regressed ✗ |
| 5 | Narrator guard (Step 4.26) | `characters.py` | **BUG** — crashed, never fired |
| 5 | Possessive-descriptor merge (Step 5.4.6) | `characters.py` | **WRONG DIRECTION** |
| 5 | Narrator prompt (frame narrative) | `narrator.py` | Partial — prompt works but code guard fails |
| 6 | narrator.py detect() crash | `narrator.py` | Fixed ✓ |
| 6 | Min-mention narrator guard ≤2 | `narrator.py` | Fixed ✓ |
| 6 | Step 5.4.6 merge direction | `characters.py` | Fixed ✓ |
| 7 | John Donaldson false secondary narrator | `narrator.py` | Fixed ✓ — mention-count guard blocks correctly |
| 7 | Boy disappeared (false merge with father) | (not yet attempted) | **NEW ISSUE** |
| 7 | Plot summary fabrication | (not yet attempted) | **NEW ISSUE** |
| 8 | Role assignment: John Donaldson (28 mentions) was "supporting" | `characters.py` — new Step 5.9.5 | Applies mention-count thresholds to ALL main_cast (upgrade only) |
| 8 | Chapter summary nested narration: "narrator's father" vs "John's father" | `summarizer.py` — CHUNK+CONSOLIDATE prompts | Added embedded narration attribution guidance to FIRST-PERSON NARRATORS bullet |

**Pattern:** narrator.py issues are now resolved. Remaining issues are in summary generation (nested narration confusion) and character extraction (same-name father/son merge). Summary fixes have NOT been attempted yet — new territory.

## Configuration Notes
- Model config appropriate: qwen3.5:122b-a10b for characters/summaries/profiles, qwen3.5:35b-a3b for structure/pronunciation
- Zero LLM retries across all stages
- All 14 pronunciations have IPA
- Runtime: ~14 min (38 LLM calls)

## Pipeline Notes (Attempt 8)
- Runtime: 12m 10s, 36 LLM calls
- Father/son split working: `John Donaldson (the son)` (76 mentions) and `John Donaldson` (father, 9 mentions) are separate ✓
- Narrator correct: Uncle Bill (first-person) ✓
- Secondary narrator guard blocked `John Donaldson (the son)` correctly ✓
- Margaret Donaldson added via F6b ✓
- Profile correction: "Corrected profile for 'John Donaldson' (same-name contamination with 'John Donaldson (the son)')" ✓
- Plot summary: awaiting evaluation (this was a critical issue in attempt 7)

## Next Action
Evaluate attempt 8 output.
