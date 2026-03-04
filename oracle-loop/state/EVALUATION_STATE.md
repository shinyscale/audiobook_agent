# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 6
- **Phase:** awaiting_analysis
- **baseline_score:** 6.55
- **Competitive Mode:** none

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 6/10 ✗ (FAILING)
  - Completeness: 7/10
  - Identity Resolution: 5/10 ← John Donaldson false secondary narrator, canonical name "John's Son" wrong
  - Alias Grouping: 7/10
- Character Profiles: 4.5/10 ✗ (FAILING)
- Chapter Summaries: 6.5/10 ✗ (FAILING)
- Pronunciation Guide: 8.5/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 7.0/10** (reference only)

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
| 6 | 7.0 | +0.45 | Uncle Bill narrator ✓, merge direction fixed ✓. But John Donaldson false secondary narrator → profile catastrophe. |

## What Attempt 6 Changed vs Attempt 5

**Improved:**
- Uncle Bill is correctly is_narrator=True ✓ (narrator.py crash fixed + min-mention guard)
- John's Son merge direction fixed ✓ — "the boy" (14 mentions) now on John's Son, not John Donaldson
- John Donaldson dropped from 42 to 28 mentions (lost "the boy" mentions correctly)
- No false splits ✓
- Uncle Bill's profile is now decent ✓ (correct self-descriptions attributed)

**Still broken / new issues:**
- **NEW:** John Donaldson is_narrator=True (tagged "Secondary narrator (nested narrative)") — WRONG. He never narrates. The BOY tells the war story, not the father.
- John Donaldson's ENTIRE profile is Uncle Bill's: appearance ("elderly, grizzled, small man"), personality ("crabbed, prejudiced, selfish"), quotes, evidence — ALL from Bill's first-person narration, attributed to John Donaldson because he's flagged as narrator
- John Donaldson age="two years old" — absurd (picked up "There was a child two years old" referring to when his SON was a toddler)
- Canonical name "John's Son" instead of "Johnny" — possessive descriptor survived as canonical when it should be the alias
- Plot summary has major factual errors: says Bill "also bears the name John Donaldson" (WRONG) and "Bill discovers that a dying American volunteer is actually his estranged father" (WRONG — the BOY discovers HIS father)
- Roles still wrong: Ted Frith (5 mentions) = "main", John's Son (14 mentions) = "supporting"
- All relationships generic ("associated")
- Margaret Donaldson missing from final output despite F6b adding her

## Current Issues (Priority Order)

### CRITICAL

1. **John Donaldson is false secondary narrator (is_narrator=True)** [Identity Resolution / Profiles]
   - Problem: John Donaldson (28 mentions) is tagged as "Secondary narrator (nested narrative)" with is_narrator=True. He NEVER narrates — he's the subject of both Uncle Bill's backstory and the boy's war account. The actual secondary narrator is the boy (John's Son), who tells the war story to Uncle Bill in first person.
   - Evidence: JSON shows `John Donaldson: is_narrator=true`. HTML shows "📖 Secondary narrator (nested narrative)". In the text, John Donaldson speaks as a character but never narrates. The boy says "I found him" and "I saw" — that's the boy narrating, not John Donaldson.
   - Impact: **CATASTROPHIC cascade** — John Donaldson's ENTIRE profile is actually Uncle Bill's:
     - Appearance: "elderly, grizzled, small man" = Bill's self-description (text line 128-129). John Donaldson should be "a big, athletic, grizzled chap, shabby, with an air like a duke" (text line 218-219).
     - Age: "two years old" = absurd
     - Personality: "crabbed, prejudiced, critical, selfish" = Bill's traits. John was "charming, irresistible, the rainbow prince"
     - Quotes: ALL are Bill's narration, not John's speech
     - Evidence: ALL 6 citations describe "the narrator" = Uncle Bill, wrongly attributed to John Donaldson
   - Root cause: The narrator detection assigns secondary narrator status. For this nested narrative, it picked John Donaldson (the father, whose name appears in first-person context) instead of the boy (who ACTUALLY narrates the embedded story). The system may be matching the name "John Donaldson" from the LLM's narrative analysis to the character with the most mentions who has that name.
   - Location: `src/pipeline/character_extraction_v2/narrator.py` — secondary narrator detection/assignment logic. Also possibly `src/agents/characters.py` in the narrator update pipeline.
   - Fix approach: **SIMPLEST FIX** — Add a guard that a secondary narrator must NOT have more mentions than the primary narrator. John Donaldson (28) > Uncle Bill (18), so the secondary narrator flag should be rejected. More robust: if the detected secondary narrator name matches multiple characters, prefer the one with FEWER mentions (the less-established character is more likely to be a nested narrator).
   - Expected impact: Fixing this ONE issue should cascade into:
     - Profiles +3 points (John Donaldson gets correct third-person descriptions)
     - Summaries +0.5 points (LLM less confused about narrative structure)

### HIGH

2. **Canonical name "John's Son" should be "Johnny"** [Identity Resolution / Alias Grouping]
   - Problem: The possessive-descriptor character survived as canonical "John's Son" (14 mentions). The proper name "Johnny" was apparently absorbed or lost. In the source text, Ted Frith calls him "Johnny" (line 326) and Uncle Bill calls him "John" (line 538).
   - Evidence: `John's Son: canonical_name="John's Son", aliases=["the boy"]`. No "Johnny" alias. The ID is main_cast_3.
   - Root cause: Step 5.4.6 merge may have kept the wrong character as canonical. The fix in attempt 6 was supposed to merge the descriptor INTO the proper name, making "Johnny" survive. But either: (a) the merge still went wrong, or (b) "Johnny" was never extracted as a separate character in this run.
   - Location: `src/agents/characters.py` — Step 5.4.6
   - Fix approach: Check if "Johnny" was extracted in Pass 1. If the descriptor "John's Son" has more mentions, the merge might be keeping the higher-mention character. The fix should ensure the PROPER NAME always becomes canonical, regardless of mention count. Add "Johnny" as an alias even if not separately extracted.

3. **Plot summary has major factual errors** [Summaries]
   - Problem: Plot summary paragraph 2 says:
     - "Bill reveals his own identity as a participant in these events, specifically as a narrator who also bears the name John Donaldson" — **WRONG.** Bill is NOT named John Donaldson. Bill is just Bill.
     - "Bill discovers that a dying American volunteer... is actually his estranged father" — **WRONG.** The BOY (John's Son) discovers the dying man is HIS father. Bill wasn't even present.
     - "Bill comforts his own son, John" — **WRONG.** John is not Bill's biological son; he's Bill's ward/godson.
   - Impact: A narrator reading this summary would fundamentally misunderstand the story's central revelation.
   - Root cause: LLM summarizer confused Uncle Bill with the boy, likely because: (a) John Donaldson is flagged as narrator, creating confusion about who is narrating what, (b) the nested narrative structure is genuinely complex.
   - Location: Summary generation in `src/agents/` or `src/pipeline/`
   - Fix: Should partially resolve when false narrator flag on John Donaldson is removed. The LLM won't be primed to think multiple people are narrating.

4. **Roles wrong** [Identity Resolution]
   - Problem: Ted Frith (5 mentions) = "main", John's Son (14 mentions) = "supporting"
   - Fix: Role assignment should correlate with mention count. John's Son (14) should be main or at least higher than Ted Frith (5).

### MEDIUM

5. **Relationships all generic ("associated")** [Profiles]
   - Problem: Every relationship is "associated" or "comrade" (Ted→Bill). Should be:
     - Uncle Bill → John Donaldson: "friend" / "former classmate"
     - Uncle Bill → John's Son: "guardian" / "uncle figure"
     - John's Son → John Donaldson: "son"
     - John Donaldson → John's Son: "father"
   - Impact: Narrators need specific relationship labels to understand character dynamics.
   - Fix: May improve when narrator flag is fixed and the profiler generates better relationship context. LOW priority for direct fix — generic pipeline can't easily infer complex nested-narrative relationships.

6. **Margaret Donaldson missing** [Completeness]
   - Problem: Mentioned by name in text ("a note signed Margaret Donaldson, John's wife"). Pipeline notes say F6b added her, but she's absent from 5 final characters.
   - Impact: Minor — she's barely mentioned and dies offscreen before the main narrative.
   - Fix: Check if she was filtered by minimum mention threshold or removed during dedup.

7. **Missing aliases: "Johnny" and "Teddy"** [Alias Grouping]
   - Problem: Ted Frith is called "Teddy" (text line 345, 422). The boy is called "Johnny" (text line 326). Neither alias appears in the output.
   - Impact: Minor — narrator won't know these are the same characters.

### LOW

8. **Null plot_summary in JSON** [Summaries]
   - Problem: `plot_summary: null` in analysis.json, though HTML has a plot summary.

9. **Null chapter title** [Structure]
   - Expected — text has no chapter headings.

## Fix Strategy for Attempt 7

**SINGLE ROOT CAUSE: Remove false secondary narrator from John Donaldson**

This is the highest-leverage fix. The false narrator flag on John Donaldson (is_narrator=True) cascades into:
- Profile catastrophe (all of Bill's traits attributed to John Donaldson) → Profiles score should jump from 4.5 to ~7-8
- Plot summary confusion (LLM confused about who narrates) → Summaries score should improve
- The profiler generating John Donaldson's profile from third-person descriptions will produce correct appearance, personality, and relationships

**Approach:**
1. In `narrator.py` or the narrator update logic, add a guard: if a secondary narrator has MORE mentions than the primary narrator, reject the secondary narrator flag. John Donaldson (28) > Uncle Bill (18) → secondary flag rejected.
2. Alternatively: validate that secondary narrator characters actually narrate (have first-person passages attributed to them), not just appear in first-person narration.
3. The secondary narrator should be the boy (John's Son), if anyone. But for this story, having only Uncle Bill as narrator is acceptable.

**Do NOT touch:**
- Step 5.4.6 (merge direction fix from attempt 6 is working — John's Son has correct mentions)
- narrator.py detect() function (crash fix from attempt 6 is working)
- characters.py Step 5.4.5 (co-present guard from attempt 4 is working)

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
     - Root cause: Lines 316-321 marked secondary narrators without any mention-count validation
     - Fix: Pre-compute primary narrator mention count; reject secondary narrator candidates whose mention count EXCEEDS the primary narrator's (John Donaldson: 28 > Uncle Bill: 18 → rejected)
     - Smoke test: All 332 unit tests pass ✓
     - Universality: Non-nested narratives unaffected (nested_narrators=[]); guard is a sound universal invariant (secondary narrators narrate a smaller portion of the book than the primary)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 2 | Wrong narrator (Uncle Bill vs Johnny) | `narrator.py` | Fixed — Bill is now narrator ✓ |
| 3 | Johnny missing — exact_firstname guard | `characters.py` | **REGRESSION** — REVERTED |
| 4 | Johnny false-merged — co-present guard Step 5.4.5 | `characters.py` | "American, sir" gone ✓, narrator regressed ✗ |
| 5 | Narrator guard (Step 4.26) | `characters.py` | **BUG** — crashed, never fired |
| 5 | Possessive-descriptor merge (Step 5.4.6) | `characters.py` | **WRONG DIRECTION** |
| 5 | Narrator prompt (frame narrative) | `narrator.py` | Partial — prompt works but code guard fails |
| 6 | narrator.py detect() crash | `narrator.py` | Fixed ✓ — Uncle Bill is now primary narrator |
| 6 | Min-mention narrator guard ≤2 | `narrator.py` | Fixed ✓ — Johnny no longer picked as narrator |
| 6 | Step 5.4.6 merge direction | `characters.py` | Fixed ✓ — "the boy" on John's Son, not father |
| 6 | John Donaldson false secondary narrator | (not yet attempted) | **NEW ISSUE** — needs fix |
| 7 | John Donaldson false secondary narrator | `narrator.py` | Mention-count guard added — John Donaldson (28) > Uncle Bill (18) → blocked |

**Pattern:** narrator.py has been key in attempts 2, 5, 6. The secondary narrator assignment is the remaining narrator-layer issue.

## Configuration Notes
- Model config appropriate: qwen3.5:122b-a10b for characters/summaries/profiles, qwen3.5:35b-a3b for structure/pronunciation
- Zero LLM retries across all stages
- All 14 pronunciations have IPA
- Runtime: 14m 19s (36 LLM calls)

## Next Action
Re-run analysis on american_sir (attempt 7). The false secondary narrator guard has been applied. Expected: John Donaldson drops is_narrator=False, profiles recover (John Donaldson gets correct third-person descriptions), plot summary confusion reduces.
