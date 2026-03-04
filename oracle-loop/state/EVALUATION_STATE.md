# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 13
- **Phase:** awaiting_analysis
- **baseline_score:** 6.55
- **Competitive Mode:** none

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 4.5/10 ✗ (FAILING — father/son merge REGRESSED, "Johnny" phantom split)
  - Completeness: 5/10
  - Identity Resolution: 3/10
  - Alias Grouping: 5/10
- Character Profiles: 3/10 ✗ (FAILING — all profiles wrong, narrator misidentified, descriptions swapped)
- Chapter Summaries: 4/10 ✗ (FAILING — plot summary completely garbled, confuses all character identities)
- Pronunciation Guide: 8.5/10 ✓
- HTML Presentation: 8/10 ✓
- **Overall: 5.8/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold) — **REGRESSION from attempt 12 (7.7)**

**⚠️ REGRESSION ALERT: 5.8 < baseline 6.55 - 0.3 = 6.25. Auto-revert of attempt 13 code changes should trigger.**

## What Attempt 13 Changed vs Attempt 12

**THE CODE CHANGES WERE LIKELY CORRECT but LLM non-determinism produced a catastrophically different extraction:**

Attempt 13 code fixes:
1. `force_parenthetical_relationship_labels()` in `post_corrections.py` — NEVER FIRED because STEP 3.95 didn't produce a "(his father)" character this run
2. Frame narrator instruction in `generator.py` plot summary — FIRED but narrator was wrong ("Johnny" instead of Uncle Bill), so it attributed embedded events to "Johnny" instead of Uncle Bill

**Root cause: LLM extraction non-determinism.** The qwen3.5:122b-a10b model produced different character extraction results:
- Attempt 12: STEP 3.95 alias contradiction fired → father/son split ✓ → Uncle Bill narrator ✓
- Attempt 13: STEP 3.95 did NOT fire → father/son merged → "Johnny" extracted as separate phantom → narrator assigned to "Johnny" → everything cascaded wrong

**Key differences in extraction:**
| Feature | Attempt 12 | Attempt 13 |
|---------|------------|------------|
| Characters | 5 (with father split) | 5 (with Johnny phantom) |
| Father/son | Split ✓ | Merged ✗ |
| Narrator | Uncle Bill ✓ | Johnny ✗ |
| "Johnny" | Not extracted | Extracted as separate char (2 mentions) |

## Detailed Issues

### CATASTROPHIC REGRESSIONS

1. **Father/son merge recurred (STEP 3.95 didn't fire)** [Identity Resolution]
   - Problem: "John Donaldson" (43 mentions) is a single merged character. No "John Donaldson (his father)" exists.
   - Evidence: Attempt 12 had the split working. This run, the alias contradiction detection didn't trigger.
   - Root cause: LLM non-determinism in character extraction — different alias sets produced, so contradiction detection conditions not met.
   - Location: `src/agents/characters.py` — STEP 3.95
   - Fix needed: Make STEP 3.95 more robust — don't rely solely on alias contradictions. Add secondary detection: if same-name characters appear in different narrative timeframes (war flashback vs pier scene), force split.

2. **Narrator wrong: "Johnny" (2 mentions) instead of Uncle Bill (18 mentions)** [Profiles, Summaries]
   - Problem: "Johnny" and "John Donaldson" are both `is_narrator=True`. Uncle Bill is `is_narrator=False`.
   - Evidence: Uncle Bill is the frame narrator. He has 18 mentions. "Johnny" with 2 mentions is just a nickname for John Donaldson the son.
   - Location: `src/agents/characters.py` — narrator detection, or `src/pipeline/narrator/narrator.py`
   - Fix: The mention-count guard (narrator must have significant mentions) should have blocked "Johnny" (2 mentions). Investigate why it didn't.

3. **"Johnny" is a phantom character** [Identity Resolution]
   - Problem: "Johnny" (2 mentions, id=main_cast_0) exists as separate character from "John Donaldson" (43 mentions). "Johnny" is a nickname for the son — should be an alias of John Donaldson, not a separate entry.
   - Evidence: Text uses "Johnny" as informal name for the young John Donaldson.
   - Location: Character extraction Pass 1 or alias resolution Pass 2.

4. **All physical descriptions are SWAPPED** [Profiles]
   - "Johnny" (phantom) has: "elderly, grizzled, small man, grim and unexhilarating" — that's Uncle Bill's description
   - "John Donaldson" has: same "elderly, grizzled, small man" — also Uncle Bill's description + "two years old" hallucination
   - "Uncle Bill" has: "tall, dark-skinned man with shabby appearance, brown skin" — that's the FATHER's description
   - Everything is wrong. The profiler is assigning descriptions to wrong characters.

5. **Plot summary completely garbled** [Summaries]
   - Says "an older narrator, Johnny, initially rejects a letter from his twelve-year-old son, John" — WRONG. Uncle Bill (not Johnny) receives the letter about the boy.
   - Says "Uncle Bill, who is revealed to be Johnny's father, dies" — COMPLETELY WRONG. Uncle Bill is the frame narrator, not anyone's father. The father is the elder John Donaldson who dies in Italy.
   - The entire plot summary has characters scrambled beyond usefulness.

6. **Relationships nonsensical** [Profiles]
   - Johnny → John Donaldson: "close friend" (should not exist as separate character)
   - John Donaldson → John: "father" (John is his OWN alias!)
   - Uncle Bill: zero relationships (should be guardian/friend of the Donaldsons)

### PERSISTENT
7. **"two years old" age hallucination** — Now on BOTH John Donaldson AND Ted Frith
8. **Uncle Bill zero relationships** — Persists across multiple attempts

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
| 8 | 7.85 | +1.30 | Father/son split ✓, plot summary fixed ✓, summaries fixed ✓, profiles much improved ✓. Remaining: cross-character aliases, generic relationships. |
| 9 | 8.0 | +1.45 | Cross-character alias contamination fixed ✓. Relationship fix only hit secondary prompt. Father still has 0 descriptive aliases. |
| 10 | 7.0 | +0.45 | **REGRESSION.** Father/son merge recurred (LLM non-determinism). Both attempt 10 fixes had no effect. |
| 11 | 7.2 | +0.65 | Narrator fix ✓, relationship cleanup ✓. But STEP 3.95 didn't fire (empty active_characters). Father/son still merged. |
| 12 | 7.7 | +1.15 | **Father/son split via alias contradiction ✓!** Characters now pass. But profiles (wrong relationships) and summaries (plot summary error) still fail. |
| 13 | 5.8 | -0.75 | **SEVERE REGRESSION.** STEP 3.95 didn't fire, narrator wrong (Johnny), all profiles/summaries garbled. Code changes correct but LLM non-determinism. |

## Fix History
- Attempt 11:
  1. STEP 3.95 — Programmatic same-name split from characters_present lists
     - Modified: `src/agents/characters.py` — new STEP 3.95 after STEP 3.9 (before narrator detection)
     - Result: **DID NOT FIRE** — active_characters is empty, no characters_present to parse
  2. clean_unknown_relationships() — extended to also remove "associated" labels
     - Modified: `src/pipeline/character_profiling/post_corrections.py`
     - Result: **FIXED** ✓ — Uncle Bill ↔ Ted Frith now "close friend"
  3. Narrator extracted from V2 pipeline_metadata in analyzer.py
     - Modified: `src/analyzer.py` — after line 1107 (V2 extraction result)
     - Result: **FIXED** ✓ — Uncle Bill is narrator
- Attempt 12:
  1. STEP 3.95 rewritten: alias contradiction detection (parent-tier vs child-tier aliases)
     - Modified: `src/agents/characters.py`
     - Result: **FIXED** ✓ — Father/son split works! Two separate John Donaldson characters created.
- Attempt 13:
  1. `force_parenthetical_relationship_labels()` in `post_corrections.py`
     - Modified: `src/pipeline/character_profiling/post_corrections.py`
     - Logic: detects canonical names with parenthetical like "(his father)" and forces correct relationship labels
     - Result: **NEVER FIRED** — no parenthetical character existed (STEP 3.95 didn't split)
  2. `narrator_instruction` in `generator.py:_generate_plot_summary()`
     - Modified: `src/pipeline/overview/generator.py`
     - Logic: clarifies that named narrator is FRAME narrator; embedded story events belong to the embedded character
     - Result: **FIRED but with wrong narrator** — applied to "Johnny" instead of Uncle Bill, making plot summary worse

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
| 8 | Role assignment: John Donaldson (28 mentions) was "supporting" | `characters.py` — Step 5.9.5 | Fixed ✓ |
| 8 | Chapter summary nested narration | `summarizer.py` — prompts | Fixed ✓ — summaries now correct |
| 8 | Father/son split | (side effect of summary fix) | Fixed ✓ in attempts 8-9, REGRESSED in attempt 10 |
| 9 | Cross-character alias contamination | `main_cast.py` — RULE 3d/3e | Fixed ✓ — contamination blocked |
| 9 | Generic relationship labels (secondary prompt) | `analyzer.py` — secondary prompt | **PARTIAL** — secondary works, primary NOT modified |
| 10 | Primary profiler "associated" labels | `analyzer.py` — post-filter + secondary call trigger | **NO EFFECT** — still "associated" |
| 10 | "John's son" confusing canonical name | `characters.py` — new Step 5.4.6b | **DID NOT FIRE** — no parent character (merged) |
| 11 | STEP 3.95 programmatic split from characters_present | `characters.py` | **DID NOT FIRE** — active_characters empty |
| 11 | "associated" relationship cleanup | `post_corrections.py` | Fixed ✓ |
| 11 | Narrator from V2 pipeline_metadata | `analyzer.py` | Fixed ✓ |
| 12 | STEP 3.95 alias contradiction detection | `characters.py` | **FIXED** ✓ — father/son split works |
| 13 | force_parenthetical_relationship_labels | `post_corrections.py` | Never fired (no split char) |
| 13 | Frame narrator plot summary instruction | `generator.py` | Fired on wrong narrator → made worse |
| 14 | STEP 3.97: nickname phantom merge | `characters.py` | Pending — merges "Johnny" (2 mentions) into "John Donaldson" (43 mentions) via STANDARD_DIMINUTIVES |
| 14 | Post-5.8.5 narrator guard | `characters.py` | Pending — re-applies STEP 4.26 low-mention invariant after STEP 5.8.5 re-run |

**Pattern:** LLM non-determinism is the #1 blocker. STEP 3.95 has fired in 1/2 attempts (attempt 12 yes, 13 no). The father/son same-name problem needs a MORE ROBUST detection mechanism that doesn't depend on specific LLM alias outputs.

## Configuration Notes
- Model config appropriate: qwen3.5:122b-a10b for characters/summaries/profiles, qwen3.5:35b-a3b for structure/pronunciation
- Zero LLM retries across all stages
- All 14 pronunciations have IPA
- Issue is NOT configuration — it's extraction non-determinism

## Next Action
Re-run analysis (attempt 14).
