# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 5
- **Phase:** awaiting_fix
- **baseline_score:** 6.55
- **Competitive Mode:** none

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 4.5/10 ✗ (FAILING)
  - Completeness: 6/10
  - Identity Resolution: 3/10 ← narrator regression + Johnny/John's Son false split
  - Alias Grouping: 5/10
- Character Profiles: 4.5/10 ✗ (FAILING)
- Chapter Summaries: 5.5/10 ✗ (FAILING)
- Pronunciation Guide: 8.5/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 6.4/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.55 | 0 | Baseline. Narrator misidentification cascades into profiles + summaries |
| 2 | 6.6 | +0.05 | Narrator fix worked (Bill=narrator ✓, Bill profile correct ✓). But Johnny still missing, summary still wrong. |
| 3 | 6.0 | -0.55 | **REGRESSION.** "American, sir" false character stole narrator from Uncle Bill. Johnny still missing. |
| 4 | 6.4 | -0.15 | Co-present guard fixed "American, sir" ✓, but narrator REGRESSED (Johnny instead of Bill). Johnny/John's Son false split. |

## What Attempt 4 Fixed vs Broke

**Fixed (relative to attempt 3):**
- "American, sir" no longer in character list ✓ (revert of attempt 3 + co-present guard)
- "John" no longer fully merged as a character into "John Donaldson" (now just an alias)
- Chapter summaries improved: no "Bill dying" error, no "grandfather vs father" confusion

**Broke / Still broken:**
- NARRATOR REGRESSED: Uncle Bill was narrator in attempt 2, now "Johnny" (2 mentions) is narrator AND "John Donaldson" is also marked narrator=True
- FALSE SPLIT: "Johnny" (main_cast_0, 2 mentions) and "John's Son" (main_cast_6, 14 mentions, alias "the boy") are the SAME character — John Donaldson's son
- Profile cross-contamination: Bill's self-descriptions ("crabbed, prejudiced, critical, selfish") attributed to BOTH Johnny AND John Donaldson
- Johnny's physical description is WRONG: "elderly, grizzled, small man" = the FATHER, not the son
- Roles wrong: Ted Frith (5 mentions) = "main", John Donaldson (28 mentions) = "supporting"
- Plot summary attributes all narrator actions to "Johnny" instead of Uncle Bill
- Margaret Donaldson not in final output (despite pipeline notes claiming F6b added her)

## Current Issues (Priority Order)

### CRITICAL

1. **NARRATOR REGRESSION: Uncle Bill must be narrator, not Johnny** [Identity Resolution]
   - Problem: Uncle Bill (18 mentions, first-person narrator of the entire story) has `is_narrator=false`. Instead, "Johnny" (2 mentions) is tagged as first-person narrator AND "John Donaldson" (28 mentions) is tagged as secondary narrator. Uncle Bill IS the "I" of the frame narrative.
   - Evidence: Chapter 1 summary says "the narrator, an unnamed man, receiving a letter from John's son" — this is Bill receiving the letter, reflecting on John. Chapter 2: "Uncle Bill drives miles to a freezing pier." Bill narrates the entire story in first person.
   - Root cause: The narrator detection fix from attempt 2 (commit 52770c3) is still in the code, but the LLM generated different summary text this time. The narrator heuristic (`_get_narrative_style()` + narrator detection) picked up "Johnny" instead of "Uncle Bill." Since the analysis was re-run from scratch, LLM non-determinism changed the narrator signals.
   - Impact: This one bug cascades into profiles (wrong self-descriptions), plot summary (wrong attribution), and roles. Fixing this alone would improve Characters, Profiles, and Summaries by ~1-2 points each.
   - Location: `src/pipeline/character_extraction_v2/narrator.py` and `src/agents/characters.py` (narrator assignment logic)
   - Fix approach: The attempt 2 prompt fix should have been sufficient. Investigate why the narrator heuristic picked "Johnny" over "Uncle Bill" — likely the summary text changed. Options:
     1. Make narrator detection more robust: prefer characters with higher mention counts when multiple candidates exist
     2. Cross-check narrator candidate against characters_present lists (Uncle Bill appears in ch2 characters_present; Johnny does not)
     3. Add a post-hoc narrator validation: if the detected narrator has <5 mentions and another character has 10x more, flag as suspect

2. **FALSE SPLIT: "Johnny" and "John's Son" are the same character** [Identity Resolution]
   - Problem: "Johnny" (main_cast_0, 2 mentions, narrator=True) and "John's Son" (main_cast_6, 14 mentions, alias "the boy") are both John Donaldson's son. Combined mentions: 16. They should be ONE character.
   - Evidence: "Johnny" is the boy's name. "John's Son" is a descriptor. The text context for "the boy" quotes include "Uncle Bill" which Johnny also says. John's Son's profile says "The man I was helping to die was my father" — this IS Johnny.
   - Root cause: Pass 1 extracted both "Johnny" and "John's Son" as separate characters. No merge step connects a name ("Johnny") to a possessive descriptor ("John's Son") because they share no textual overlap.
   - Location: `src/agents/characters.py` — merge steps (5.4.5, 5.5, 5.5a) don't handle name↔possessive-descriptor relationships
   - Fix approach:
     1. Add a merge step that recognizes "X's Son/Daughter" descriptors and checks if any character named with a diminutive of "X" exists (Johnny → John → "John's Son")
     2. OR: check if both characters share the same relationships (both related to John Donaldson, both related to Uncle Bill) and have compatible gender/role
     3. Simpler: check if a character's canonical_name is a possessive descriptor ("X's Son/Daughter/Wife/Husband") and another character has a proper name that is a known diminutive of X

3. **Plot summary wrong narrator attribution** [Summaries]
   - Problem: "The story is narrated by Johnny, who begins by reflecting on a letter from the son of his old friend John" — the narrator is Uncle Bill, not Johnny. All narrator actions (reading letter, reflecting on Yale, resolving scandal, driving to pier) are attributed to "Johnny."
   - Impact: Plot summary is the first thing a narrator reads; if it's wrong, their entire understanding of the story is wrong.
   - Root cause: Plot summary is generated AFTER character extraction and uses the (wrong) narrator identification.
   - Fix: Resolves automatically when narrator detection is fixed (Critical #1).

### HIGH

4. **Profile cross-contamination from wrong narrator** [Profiles]
   - Problem: "Johnny" profile has physical description "elderly, grizzled, small man" (the FATHER's description) and personality traits from Uncle Bill's self-description. John Donaldson's profile has Uncle Bill's "crabbed, prejudiced, critical, selfish" personality traits. Uncle Bill's profile is missing physical description and narrator status.
   - Fix: Mostly resolves when narrator detection is fixed. With correct narrator=Uncle Bill, the profiler will:
     - Assign Bill's first-person self-descriptions to Bill
     - Not inject narrator appearance into wrong characters
     - Generate accurate profiles for Johnny (the son) and John Donaldson (the father) without narrator contamination

5. **Roles wrong: Ted Frith = "main" (5 mentions) vs John Donaldson = "supporting" (28 mentions)** [Identity Resolution]
   - Problem: Role assignment doesn't match mention importance.
   - Fix: May partially resolve when narrator + Johnny/John's Son merge fixes change the character landscape and mention distribution.

6. **"John" alias ambiguity** [Alias Grouping]
   - Problem: "John" is alias of "John Donaldson" (the father). But in chapter 2, "John" refers to the SON (the nephew Uncle Bill meets at the pier). The name "John" is genuinely ambiguous in this text.
   - Impact: MEDIUM — affects mention count accuracy but doesn't create a visibly wrong character entry.
   - Fix: This may be acceptable. In a text where father and son share a first name, some ambiguity is inevitable. If Johnny/John's Son are merged, the son character will have sufficient mentions (16) regardless.

### MEDIUM

7. **Margaret Donaldson missing from final output** [Completeness]
   - Problem: John's wife, mentioned by name in chapter 1 summary and characters_present. Pipeline notes claimed F6b added her, but she's not in the 5 final characters.
   - Impact: Minor — she's a background character mentioned only "via letter."
   - Fix: Investigate why she was dropped. May have been filtered by minimum mention threshold.

8. **Chapter 2 summary age error: "twelve-year-old nephew"** [Summaries]
   - Problem: Summary says "Uncle Bill drives miles to a freezing pier at dawn to welcome his twelve-year-old nephew John home from the war." The boy was ~18-20 (text says "was eighteen" and fought in WWI with a Croix de Guerre). A 12-year-old cannot be an ambulance driver.
   - Impact: Factual error in chapter summary. However, this is LLM hallucination in the summarizer, not a code bug.
   - Fix: Difficult — would require the summarizer to cross-check stated ages against context. LOW priority relative to narrator/character issues.

### LOW

9. **All relationships "associated"** [Profiles]
   - Problem: Uncle Bill→John Donaldson = "associated" (should be "friend" or "cousin"), John Donaldson→John's Son = "associated" (should be "father"), etc.
   - Fix: Partially resolves with correct character landscape. The relationship extraction struggles with this text's complex nested narrative.

10. **Null chapter titles** [Structure]
    - Impact: Very minor. Text has no chapter headings, so null titles are expected.

## Fix Strategy for Attempt 5

**Priority 1: Fix narrator detection (Critical #1)**
- Investigate why the narrator heuristic picked "Johnny" over "Uncle Bill" in this run
- The attempt 2 narrator prompt fix (commit 52770c3) is still in the code but LLM non-determinism produced different results
- Consider adding a programmatic narrator validation: after LLM-based detection, cross-check against mention counts and characters_present lists
- If narrator candidate has <5 mentions and doesn't appear in any characters_present list, reject it

**Priority 2: Merge Johnny + John's Son (Critical #2)**
- Add a merge step for possessive-descriptor characters ("X's Son", "X's Daughter")
- Check if any existing character's name is a diminutive/variation of X
- If found and genders compatible, merge the possessive descriptor into the named character
- This should be a new step after the existing merge sequence

**Note on approach:** Since the narrator detection depends on LLM output and we've seen it flip between runs, a PROGRAMMATIC safeguard is needed rather than relying solely on prompt engineering. The safeguard should validate that the detected narrator makes sense (sufficient mentions, appears in characters_present, etc.).

## Fix History
- Attempt 2: Fixed narrator detection to trust explicit "narrator, known as [Name]" identification
  - Modified: `src/pipeline/character_extraction_v2/narrator.py:NARRATOR_DETECTION_PROMPT`
  - Result: Narrator fix WORKED — Bill correctly identified ✓
- Attempt 3: Added exact_firstname guard to `_merge_lastname_aliases`
  - Modified: `src/agents/characters.py` — `_merge_lastname_aliases()`
  - Result: **REGRESSION** — "American, sir" appeared as false character, stole narrator. Johnny NOT fixed. REVERTED.
- Attempt 4: Reverted attempt 3, then applied co-present guard to `_merge_summary_name_fragments()` (Step 5.4.5)
  - Modified: `src/agents/characters.py` — `_merge_summary_name_fragments()`
  - Result: "American, sir" gone ✓, but narrator REGRESSED (Johnny instead of Bill). Johnny/John's Son false split remains.

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 2 | Wrong narrator (Uncle Bill vs Johnny) | `src/pipeline/character_extraction_v2/narrator.py` | Fixed — Bill is now narrator ✓ |
| 2 | Johnny missing (false merge) | (not yet attempted) | Still broken |
| 3 | Johnny missing — `_merge_lastname_aliases` exact_firstname guard | `src/agents/characters.py` | **REGRESSION** — "American, sir" false character, narrator shifted. REVERTED. |
| 4 | Johnny false-merged — co_present guard in `_merge_summary_name_fragments()` Step 5.4.5 | `src/agents/characters.py` | "American, sir" gone ✓, narrator regressed ✗, Johnny/John's Son false split ✗ |

## Configuration Notes
- Model config appropriate: qwen3.5:122b-a10b for characters/summaries/profiles, qwen3.5:35b-a3b for structure/pronunciation
- Zero LLM retries across all stages
- All 14 pronunciations have IPA
- Runtime: 14m 3s (38 LLM calls)

## Next Action
Run PROMPT_fix.md to address:
1. Narrator detection robustness (programmatic safeguard, not just prompt)
2. Johnny/John's Son merge (possessive-descriptor recognition)
