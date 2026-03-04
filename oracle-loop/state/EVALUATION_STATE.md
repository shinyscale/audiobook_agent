# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 2
- **Phase:** awaiting_fix
- **baseline_score:** 6.55
- **Competitive Mode:** none

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 5/10 ✗ (FAILING)
  - Completeness: 5/10
  - Identity Resolution: 4/10 ← primary blocker (Johnny false-merged into father)
  - Alias Grouping: 6/10
- Character Profiles: 5.5/10 ✗ (FAILING)
- Chapter Summaries: 5/10 ✗ (FAILING)
- Pronunciation Guide: 8.5/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 6.6/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.55 | 0 | Baseline. Narrator misidentification cascades into profiles + summaries |
| 2 | 6.6 | +0.05 | Narrator fix worked (Bill=narrator ✓, Bill profile correct ✓). But Johnny still missing, summary still wrong. |

## What Improved in Attempt 2
- **Narrator identification FIXED**: Bill is now correctly tagged as `is_narrator=true` (was Johnny in attempt 1)
- **Bill's profile FIXED**: Now shows correct description ("elderly, grizzled, small man") instead of Johnny's description
- **"the boy" alias no longer misassigned to father** — it's no longer on any character (improvement, though incomplete)

## What Did NOT Improve
- Johnny (the son) is still completely missing from the character list
- Summary still contains major factual errors (Bill dying, grandfather vs father)
- Relationships still all generic ("associated", "colleague")

## Current Issues (Priority Order)

### CRITICAL

1. **Johnny (the son) is MISSING from the character list — false-merged into father** [Identity Resolution / Completeness]
   - Problem: The story's central inner-narrative character — Johnny, the son who goes to war, finds his dying father, carries him to a church — does not exist in the output. The pipeline extracted "John" (the son) but merged him into "John Donaldson" (the father) as an alias.
   - Evidence: `characters_present` in the structure lists both "John" AND "John Donaldson (the father)" as **separate** entries, proving the summarizer recognized them as distinct. But the final character list has only "John Donaldson" with alias "John."
   - Pipeline log: "Pass 2 failed for John, keeping without aliases" — a standalone "John" character existed but was later absorbed.
   - Root cause: `_merge_summary_name_fragments()` (Step 5.4.5 in characters.py) treats single-word "John" as a fragment of multi-word "John Donaldson" and merges them. But in this story, "John" = the SON and "John Donaldson" = the FATHER — they are different characters who share a name.
   - Location: `src/agents/characters.py` — `_merge_summary_name_fragments()` (Step 5.4.5) and/or `_merge_formal_name_aliases()` (Step 5.5a) and/or `_merge_lastname_aliases()` (Step 5.5)
   - Fix approach: **Guard against merging when both names appear as separate entries in the same summary's `characters_present` list.** If the summarizer listed "John" AND "John Donaldson (the father)" as separate characters in the same section, they should NOT be merged. The summary's character list is ground truth for co-occurrence — separate listing means separate characters.
   - Impact: CASCADING — without Johnny as a character, profiles, relationships, and role assignments are all wrong. This is the #1 blocker.

2. **Summary factual errors persist: "Bill dying" and "grandfather" vs "father"** [Summaries]
   - Problem: The summary says "Bill, now imprisoned and dying, confesses his American identity before passing away with a contented sigh." Bill does NOT die — he is at home in New York the entire time. The dying man is John Donaldson (the father). Also says "John asks if God has forgiven his grandfather's dishonor" — John Donaldson is Johnny's FATHER, not grandfather.
   - Evidence: In the text, Bill narrates from his home. The dying scene involves John Donaldson (father) in an Italian dressing station. Johnny says "The man I was helping to die was my father."
   - Root cause: The summary is generated BEFORE character extraction (Structure → Summary → Characters → Profiles). The LLM is confused by the frame/nested narrative structure and same-name characters. The narrator fix did NOT cascade to fix the summary because summaries don't re-run.
   - Location: Summary generation stage — `src/pipeline/summarizer/`
   - Fix approach: This is a hard problem because summaries are generated before character resolution. Options:
     1. Add post-summary correction step that revises summaries using resolved character list
     2. Improve summary prompt to better handle nested narratives with same-name characters
     3. Re-generate the plot_summary (overview) after character extraction is complete
   - Note: The chapter-level summary IS what drives character extraction, so it can't easily be regenerated. But the `plot_summary` in the overview COULD be regenerated post-character-extraction as a separate step.

### HIGH

3. **All relationships are generic ("associated", "colleague") — no family terms** [Profiles]
   - Problem: Bill → John Donaldson = "associated" (should be "cousin"). John Donaldson → Bill = "associated" (should be "cousin"). Ted Frith → Bill = "colleague" (Bill and Ted never interact; Ted is Johnny's fellow soldier). No father-son relationship exists because Johnny is missing.
   - Evidence: Text explicitly states: Bill and John "shared a room for a dozen years" at Yale (cousins). "The man I was helping to die was my father." Uncle Bill becomes Johnny's guardian.
   - Location: `src/analyzer.py` → `_generate_character_profile()` and `post_corrections.py` → `verify_relationships_from_text`
   - Fix approach: Will partially resolve if Johnny is restored as a character (Issue #1). The "cousin" relationship between Bill and John Donaldson needs the co-mention analysis to detect "my cousin" / "shared a room" phrasing.

4. **Role assignments wrong: Ted Frith (5 mentions) = "main", John Donaldson (30 mentions) = "supporting"** [Identity Resolution]
   - Problem: The most-mentioned non-narrator character (John Donaldson, 30 mentions) has role "supporting" while Ted Frith (5 mentions) has role "main."
   - Location: Role assignment in character extraction pipeline
   - Fix approach: Will likely resolve once Johnny is restored — the mention counts will be redistributed (many "John" mentions currently counted under John Donaldson should go to Johnny), and role assignment will be based on correct data.

### MEDIUM

5. **John Donaldson's profile mixes father and son physical attributes** [Profiles]
   - Problem: Profile says "'beautiful youngster' and 'rainbow prince' in youth; later, his son is described as having 'All John Donaldson's physical beauty'" — this confusingly references both father (in youth) and son (inheriting those traits). Without Johnny as a separate character, the profiler can't cleanly separate them.
   - Fix approach: Resolves if Johnny is restored as a character (Issue #1).

6. **God profile inverts textual meaning** [Profiles]
   - Problem: God is listed with trait "narrow-minded." In context, Bill says "Do you suppose a great God is more narrow-minded than I am?" — meaning God is LESS narrow-minded. The profile inverts this rhetorical question.
   - Impact: Minor — "God" is a borderline character extraction anyway.
   - Fix approach: Low priority. The profiler misreads rhetorical questions.

7. **Margaret Donaldson still missing from character list** [Completeness]
   - Problem: John's wife and Johnny's mother, mentioned by name (lines 59, 75), doesn't appear in output.
   - Impact: Minor — she's a background character.
   - Fix approach: Low priority, revisit after primary issues resolved.

### LOW

8. **Null chapter title for single-section text**
   - Impact: Very minor presentation issue.

## Fix History
- Attempt 2: Fixed narrator detection to trust explicit "narrator, known as [Name]" identification in summaries
  - Root cause: Chapter summary had self-contradiction: "narrator, known as Uncle Bill" (correct) AND "narrator later comforts a dying Uncle Bill" (hallucination). Narrator detection LLM was confused and picked Johnny instead.
  - Fix: Added universal rule to NARRATOR_DETECTION_PROMPT: explicit "narrator, known as [Name]" identification takes priority over contradictions. Also added frame/nested narrative guidance.
  - Modified: `src/pipeline/character_extraction_v2/narrator.py:NARRATOR_DETECTION_PROMPT`
  - Result: Narrator fix WORKED — Bill correctly identified. Profile attribution fixed. But did NOT cascade to fix summaries or restore Johnny.

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 2 | Wrong narrator (Uncle Bill vs Johnny) | `src/pipeline/character_extraction_v2/narrator.py` | Fixed — Bill is now narrator ✓ |
| 2 | Johnny missing (false merge) | (not yet attempted) | Still broken — Johnny merged into father |
| 2 | Summary errors (Bill dying) | (not yet attempted) | Still broken — summary not re-generated |

## Root Cause Analysis

**Primary blocker: Johnny false-merged into father (Issue #1)**

The pipeline's merge logic in `characters.py` sees "John" (single-word character = the son) as a name fragment of "John Donaldson" (multi-word character = the father) and merges them. This is a correct heuristic in MOST cases (e.g., "Jim" → "Jim Dillingham Young") but WRONG when father and son share the same first name.

The key signal that these are different characters is in `characters_present`: the summarizer listed BOTH "John" AND "John Donaldson (the father)" in the same section. If both appear as separate entries in the same summary, they must be separate characters. The merge logic should check this.

**Merge steps that could be responsible (check in order):**
1. `_merge_summary_name_fragments()` (Step 5.4.5) — most likely. Merges single-word fragments into multi-word canonical names from summary character lists.
2. `_merge_formal_name_aliases()` (Step 5.5a) — less likely but possible. Merges formal names into nicknames.
3. `_merge_lastname_aliases()` (Step 5.5) — possible. "John" could be treated as a component.

**Secondary blocker: Summary errors (Issue #2)**

Summaries are generated BEFORE character extraction (pipeline order: Structure → Summary → Characters). The summary LLM is confused by:
- Frame/nested narrative (Bill narrates, Johnny's war story is quoted dialogue)
- Same-name characters (father and son both "John Donaldson")
- The dying man's identity (father, not Bill)

The narrator fix improved character extraction but could NOT retroactively fix already-generated summaries. The `plot_summary` in the overview is derived from chapter summaries, so it inherits their errors.

## Configuration Notes
- Model config appropriate: qwen3.5:122b-a10b for characters/summaries/profiles, qwen3.5:35b-a3b for structure/pronunciation
- Zero LLM retries across all stages
- All 14 pronunciations have IPA
- Runtime: 30m 25s (36 LLM calls)

## Next Action
Run PROMPT_fix.md to address Issue #1 (Johnny false-merged into father). The fix should:
1. Add a guard in `_merge_summary_name_fragments()` (and related merge functions) to prevent merging characters that appear as **separate entries** in the same summary's `characters_present` list
2. This is the highest-impact fix — restoring Johnny as a character should cascade improvements to profiles, relationships, and role assignments
3. Summary errors (Issue #2) may need a separate approach since summaries are generated before character extraction
