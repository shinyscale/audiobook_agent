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
- Character Extraction: 4/10 ✗ (FAILING)
  - Completeness: 6/10
  - Identity Resolution: 3/10 ← narrator STILL wrong + Step 5.4.6 merged "the boy" into father not son
  - Alias Grouping: 4/10
- Character Profiles: 4.5/10 ✗ (FAILING)
- Chapter Summaries: 7.5/10 ✗ (FAILING)
- Pronunciation Guide: 8.5/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 6.7/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.55 | 0 | Baseline. Narrator misidentification cascades into profiles + summaries |
| 2 | 6.6 | +0.05 | Narrator fix worked (Bill=narrator ✓, Bill profile correct ✓). But Johnny still missing, summary still wrong. |
| 3 | 6.0 | -0.55 | **REGRESSION.** "American, sir" false character stole narrator from Uncle Bill. Johnny still missing. |
| 4 | 6.4 | -0.15 | Co-present guard fixed "American, sir" ✓, but narrator REGRESSED (Johnny instead of Bill). Johnny/John's Son false split. |
| 5 | 6.7 | +0.15 | Plot summary improved (correctly names Uncle Bill). But narrator metadata STILL wrong. Step 5.4.6 merged "the boy" into father. |

## What Attempt 5 Changed vs Attempt 4

**Improved:**
- Plot summary in HTML now correctly identifies "the narrator, known as 'Uncle Bill'" ✓
- Chapter summary comprehensive and mostly accurate ✓
- Step 5.4.6 merged "John's Son" (eliminating false split from attempt 4) ✓
- Step 4.26 narrator guard was added (but crashed — see below)

**Still broken / new issues:**
- NARRATOR METADATA WRONG: Johnny (2 mentions, is_narrator=True) vs Uncle Bill (18 mentions, is_narrator=False)
- Step 4.26 crashed with `'list' object has no attribute 'get'` — guard didn't execute, narrator detection fell through to Step 5.8.5 fallback which picked Johnny again
- Step 5.4.6 merged "the boy" alias into John Donaldson (father, 42 mentions) instead of Johnny (son, 2 mentions) — WRONG MERGE DIRECTION
- Johnny's profile has father's appearance ("elderly, grizzled, small man") and Uncle Bill's personality ("solitary, thoroughly selfish")
- John Donaldson profile says "estranged son of the narrator (Uncle Bill)" — WRONG: he was Bill's college friend, not his son
- All relationships still generic ("associated", "close friend") instead of specific (father/son/uncle)
- Roles: Ted Frith (5 mentions) = "main", John Donaldson (42 mentions) = "supporting"

## Current Issues (Priority Order)

### CRITICAL

1. **NARRATOR STILL WRONG: Johnny (2 mentions) = narrator instead of Uncle Bill (18 mentions)** [Identity Resolution]
   - Problem: Despite narrator detection prompt correctly identifying Uncle Bill during analysis, the final output has Johnny as is_narrator=True. The Step 4.26 low-mention guard crashed with `'list' object has no attribute 'get'`, so the programmatic safeguard never fired.
   - Evidence: JSON shows `Johnny: is_narrator=true, mentions=2`. `Uncle Bill: is_narrator=false, mentions=18`. Uncle Bill IS the first-person narrator of the entire story.
   - Root cause: Step 4.26 bug — the code passes a list where a dict was expected. When this guard crashes, the narrator falls through to Step 5.8.5 which re-runs detection and picks the wrong character.
   - Location: `src/agents/characters.py` — Step 4.26 block (new code from attempt 5)
   - Fix approach:
     1. **Fix the Step 4.26 bug**: The `'list' object has no attribute 'get'` error means the code is calling `.get()` on a list instead of a dict. Find and fix the type mismatch.
     2. **Strengthen the guard**: After fixing the type error, ensure the guard actually works: if detected narrator has ≤ 2 mentions and another character has ≥ 5x more mentions, reject the low-mention narrator.
     3. **Add final narrator validation**: As a last resort, add a post-pipeline check that verifies the narrator character has reasonable mentions (≥ 5) and appears in characters_present lists.
   - Impact: This ONE fix cascades into Profiles (+2 pts) and Summaries (+0.5 pts) because the profiler attributes first-person descriptions to the narrator character.

2. **Step 5.4.6 merged "the boy" into FATHER instead of SON** [Identity Resolution / Alias Grouping]
   - Problem: The possessive-descriptor merge ("John's Son") correctly identified "Johnny" as a diminutive of "John" but then merged "John's Son" (and its alias "the boy") into John Donaldson (the father, who also has "John" in his name). The result: the father has 42 mentions with "the boy" as an alias, while Johnny (the actual boy) has only 2 mentions.
   - Evidence: `John Donaldson: aliases=["John", "the boy"], mentions=42`. `Johnny: aliases=[], mentions=2`. "The boy" in the text refers to the SON, not the father.
   - Root cause: Step 5.4.6 looks for a character matching the possessor name "John" and picks the one with the most mentions (John Donaldson, 42). It should prefer the character whose name is a DIMINUTIVE of "John" (Johnny).
   - Location: `src/agents/characters.py` — Step 5.4.6 block (new code from attempt 5)
   - Fix approach: When the possessor-name match returns multiple candidates:
     1. **Prefer the diminutive match**: If one candidate's name IS a diminutive of the possessor (Johnny = diminutive of John), prefer that over a candidate whose name merely CONTAINS the possessor (John Donaldson contains "John")
     2. **Use kinship context**: "John's Son" → the TARGET should be the SON, not the FATHER. The possessive descriptor itself indicates the relationship direction
     3. **Fallback**: If no diminutive match, use mention count ratio (prefer the LOWER-mention character, since the possessive descriptor is likely referencing the less-established character)

### HIGH

3. **Profile cross-contamination from wrong narrator** [Profiles]
   - Problem: Johnny's profile has: (a) father's physical description "elderly, grizzled, small man", (b) Uncle Bill's personality "solitary, thoroughly selfish", (c) Uncle Bill's narration quotes "I was a solitary pilgrim ever"
   - John Donaldson's profile says "estranged son of the narrator (Uncle Bill)" — factually wrong (he was Bill's Yale classmate/friend)
   - Fix: Mostly resolves automatically when narrator detection is fixed (Critical #1). With correct narrator=Uncle Bill:
     - Bill's first-person self-descriptions go to Bill's profile
     - Johnny doesn't get narrator appearance injection
     - John Donaldson's relationship to Bill would be "friend" not "son"

4. **Roles wrong: mention counts don't match role assignments** [Identity Resolution]
   - Problem: Ted Frith (5 mentions) = "main", John Donaldson (42 mentions) = "supporting"
   - Fix: May partially resolve when narrator + merge fixes change mention distributions. If not, role assignment logic needs review.

5. **Relationships all generic** [Profiles]
   - Problem: All relationships are "associated" or "close friend" instead of specific labels:
     - Johnny → John Donaldson should be "son" (or "father" inverse)
     - Uncle Bill → Johnny should be "uncle" or "guardian"
     - Uncle Bill → John Donaldson should be "friend" or "former classmate"
   - Fix: The relationship extraction struggles with this text's complex nested narrative. Fixing narrator may help the profiler generate better relationships. Otherwise, LOW priority — this is hard to fix generically.

### MEDIUM

6. **Margaret Donaldson missing from final output** [Completeness]
   - Problem: John's wife/mother, mentioned by name in summaries. Pipeline notes say F6 added her but she's not in the 4 final characters.
   - Impact: Minor — she's barely mentioned.
   - Fix: Check if she was filtered by minimum mention threshold.

7. **Chapter summary frame-narrative ambiguity** [Summaries]
   - Problem: Summary says "the narrator then describes navigating a dressing station" — ambiguous whether Uncle Bill (frame narrator) or Johnny (embedded narrator recounting events) is the subject. In reality, Johnny experienced these events; Uncle Bill is relaying Johnny's account.
   - Impact: Minor — most of the summary is clear. The plot summary in HTML correctly handles this.

### LOW

8. **Null plot_summary in JSON** [Summaries]
   - Problem: `plot_summary: null` in analysis.json, though the HTML has a well-written plot summary
   - Impact: Minor — HTML output is what narrators actually use

9. **Null chapter title** [Structure]
   - Impact: Expected — text has no chapter headings

## Fix Strategy for Attempt 6

**Priority 1: Fix Step 4.26 bug (Critical #1)**
- The `'list' object has no attribute 'get'` error means Step 4.26 code is calling `.get()` on a list
- Find the exact line in characters.py Step 4.26 block and fix the type handling
- After fixing, verify the guard logic: if narrator has ≤ 2 mentions AND another main_cast character has ≥ 5x more mentions, reset narrator_character_id so Step 5.8.5 retries
- This should result in Uncle Bill being correctly assigned as narrator

**Priority 2: Fix Step 5.4.6 merge direction (Critical #2)**
- When "John's Son" is found as a possessive descriptor:
  1. Extract possessor name ("John")
  2. Find candidate targets: characters whose names are DIMINUTIVES of "John" → "Johnny"
  3. Do NOT pick the character whose canonical name contains "John" as a substring (John Donaldson)
  4. The merge should go: "John's Son" + its alias "the boy" → merged INTO "Johnny"
  5. Result: Johnny should have mentions = 2 + 14 = 16, aliases = ["the boy", "John's Son"]

**NOTE on approach:** These are both bugs in NEW code from attempt 5. The fixes are targeted:
1. Step 4.26: fix a type error (list vs dict)
2. Step 5.4.6: fix target selection to prefer diminutive matches over substring matches

Both fixes are in `src/agents/characters.py` only. No prompt changes needed.

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

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 2 | Wrong narrator (Uncle Bill vs Johnny) | `src/pipeline/character_extraction_v2/narrator.py` | Fixed — Bill is now narrator ✓ |
| 2 | Johnny missing (false merge) | (not yet attempted) | Still broken |
| 3 | Johnny missing — `_merge_lastname_aliases` exact_firstname guard | `src/agents/characters.py` | **REGRESSION** — "American, sir" false character. REVERTED. |
| 4 | Johnny false-merged — co_present guard in Step 5.4.5 | `src/agents/characters.py` | "American, sir" gone ✓, narrator regressed ✗ |
| 5 | Narrator guard (Step 4.26) | `src/agents/characters.py` | **BUG** — crashed with type error, never fired |
| 5 | Possessive-descriptor merge (Step 5.4.6) | `src/agents/characters.py` | **WRONG DIRECTION** — merged "the boy" into father |
| 5 | Narrator prompt (frame narrative) | `narrator.py` | Partial — prompt works but code guard fails |

**Pattern detected:** characters.py has been modified in attempts 3, 4, 5 with mixed results. Steps 4.26 and 5.4.6 are NEW code from attempt 5 with bugs — these are targeted fixes, not architectural changes.

## Configuration Notes
- Model config appropriate: qwen3.5:122b-a10b for characters/summaries/profiles, qwen3.5:35b-a3b for structure/pronunciation
- Zero LLM retries across all stages
- All 13 pronunciations have IPA
- Runtime: ~31 min (31 LLM calls)

## Next Action
Run PROMPT_fix.md to address:
1. Step 4.26 type error (list vs dict) → narrator guard fires correctly
2. Step 5.4.6 target selection → prefer diminutive match (Johnny) over substring match (John Donaldson)
