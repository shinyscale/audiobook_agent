# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 14
- **Phase:** awaiting_analysis
- **baseline_score:** 6.55
- **Competitive Mode:** none

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Pipeline Notes (Attempt 14)
- Father/son SPLIT fired ✓ — Two separate "John Donaldson" characters created
- Uncle Bill: 18 mentions, John Donaldson (father): 31 mentions, John Donaldson (the son): 28 mentions
- "Shabby American civilian" still exists as separate character (8 mentions) — FALSE SPLIT from father
- STEP 3.97 nickname phantom merge: no separate "Johnny" phantom this run ✓
- **No narrator detected** — all 5 characters have is_narrator=false. Uncle Bill should be frame narrator.
- Margaret Donaldson NOT in final output (F6 may have been skipped or she was filtered)
- 5 characters with profiles; Uncle Bill has null physical_description and {} relationships
- "ambulance driver" alias on John Donaldson (father) — should be on son
- Plot summary quality is GOOD — accurately captures the multi-layered narrative arc
- Runtime: 14m 25s

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 6.5/10 ✗ (FAILING — Shabby American civilian false split, no narrator, alias misattribution)
  - Completeness: 7/10
  - Identity Resolution: 6/10
  - Alias Grouping: 6.5/10
- Character Profiles: 6/10 ✗ (FAILING — Uncle Bill empty profile, no narrator attribution)
- Chapter Summaries: 8/10 ✓
- Pronunciation Guide: 9/10 ✓
- HTML Presentation: 8/10 ✓
- **Overall: 7.6/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold)

## Detailed Evaluation

### 2.1 Structure Detection: 9/10 ✓
Single section for a continuous short story — correct. No artificial splitting.

### 2.2 Character Extraction: 6.5/10 ✗

**Completeness (7/10):**
- Uncle Bill ✓, John Donaldson (father) ✓, John Donaldson (the son) ✓, Ted Frith ✓
- Margaret Donaldson missing (mentioned as the boy's mother but very minor — acceptable)
- Shabby American civilian extracted but is a false split (see Identity Resolution)

**Identity Resolution (6/10):**
- Father/son same-name split WORKS ✓ — huge improvement from attempt 13
- FALSE SPLIT: "Shabby American civilian" (8 mentions) IS John Donaldson the father — the story reveals the shabby civilian is the father. These should be ONE character with "shabby American civilian" as an alias.
- "ambulance driver" alias on father (main_cast_2) — the son was the ambulance driver, the father was the stretcher-bearer
- No narrator flag on any character — Uncle Bill should be is_narrator=true

**Alias Grouping (6.5/10):**
- "his father" as alias of Shabby American civilian is a relational descriptor, not a name alias
- "stretcher-bearer" on father is correct ✓
- "ambulance driver" on father is WRONG — belongs on son
- Ted Frith aliases ["Ted"] ✓

### 2.3 Character Profiles: 6/10 ✗

- **Uncle Bill**: physical_description=null, relationships={} — MAJOR GAP. He's the protagonist/frame narrator. The character summary text ("reflective, middle-aged man who initially displays selfishness") provides some useful info but structured profile is completely empty.
- **John Donaldson (father)**: "powerful old boy, middle-aged American civilian" — reasonable ✓. Has father→son relationship ✓
- **Shabby American civilian**: "middle-aged man with dark complexion, brown skin" — describes the same person as John Donaldson (father), wasting a profile slot on a duplicate
- **John Donaldson (the son)**: "tall boy, olive complexion, dark face, blue eyes" — good ✓. Has son→father relationship ✓
- **Ted Frith**: no description (appropriate for minor), has comrade relationship ✓
- Uncle Bill having ZERO relationships is wrong — he's guardian/uncle figure to the boy

### 2.4 Chapter Summaries: 8/10 ✓

The single chapter summary is comprehensive and captures the full arc: frame narrative → war story → reveal → redemption → return to frame. Plot summary also excellent — correctly identifies themes and narrative layers.

Minor issues:
- "Uncle Bill speaking to his son John by the fire" — John is NOT Bill's biological son; he's the ward/nephew of Bill. "His son" is misleading.
- Otherwise, factually accurate and useful for narrator preparation.

### 2.5 Pronunciation Guide: 9/10 ✓

Strong coverage of Italian place names (Piave, Caporetto, Venetia, Tagliamento, Solferino, Bersagliari) and homographs (live, minute, read, close, moderate). All 13 entries have IPA. No egregious false positives.

### 2.6 HTML Presentation: 8/10 ✓

Functional navigation, logical organization. No broken elements reported.

## Current Issues (Priority Order)

### CRITICAL
1. **"Shabby American civilian" is a false split from John Donaldson (father)** [Identity Resolution]
   - Problem: "Shabby American civilian" (main_cast_3, 8 mentions) and "John Donaldson" (main_cast_2, 31 mentions) are the SAME person — the father. The story reveals the mystery civilian IS John Donaldson Sr.
   - Evidence: Aliases of Shabby American civilian include "his father" — confirming the identity. The plot summary correctly states "this civilian is revealed to be John Donaldson, the boy's long-lost father."
   - Location: This is an identity-reveal pattern (like Masked Figure → Red Death in Masque). Post-extraction merge needed.
   - Fix: Add identity-reveal merge logic in `src/agents/characters.py` — after extraction, if a character has "his father"/"his mother"/etc. as alias AND another character has the same family role in relationships, merge them. OR: use `merge_reveal_characters()` pattern from `twostage_experiment.py`.
   - Alternative: Since "Shabby American civilian" has alias "his father" and "John Donaldson" has relationship "father" to the son, these can be programmatically detected as the same person.

### HIGH
2. **No narrator detected — Uncle Bill should be frame narrator** [Characters, Profiles]
   - Problem: All 5 characters have is_narrator=false. Uncle Bill (18 mentions, protagonist) is the frame narrator.
   - Evidence: Story opens with Uncle Bill's perspective. Overview says narrative_style="first-person retrospective". But narrator detection failed.
   - Location: `src/pipeline/narrator/narrator.py` or `src/agents/characters.py` narrator detection steps
   - Note: This has been fixed and regressed multiple times. Attempt 11 added V2 pipeline_metadata narrator extraction. Attempt 14 added post-5.8.5 narrator guard. Something is still not working.
   - Fix: Investigate why the narrator pipeline returned no result this run. The V2 pipeline_metadata should have identified Uncle Bill.

3. **Uncle Bill has empty structured profile** [Profiles]
   - Problem: physical_description=null, relationships={} despite being the protagonist
   - Evidence: His character summary text IS populated ("reflective, middle-aged man...") but structured fields are empty
   - Location: `src/pipeline/character_profiling/` or `src/analyzer.py` profile generation
   - Fix: Likely related to narrator status — if narrator detection fails, the profiler may not prioritize Uncle Bill correctly. Fixing issue #2 may resolve this.

### MEDIUM
4. **"ambulance driver" alias on wrong character** [Alias Grouping]
   - Problem: "ambulance driver" is an alias of John Donaldson (father, main_cast_2) but the father was a stretcher-bearer, not an ambulance driver. The SON was the ambulance driver.
   - Evidence: The son's profile says "wears an ambulance driver's uniform." Father's aliases include both "stretcher-bearer" AND "ambulance driver" — the latter is wrong.
   - Location: Character extraction Pass 1 or alias resolution
   - Fix: This is an LLM extraction error — difficult to fix generically without novel-specific rules. Low priority compared to critical/high issues.

5. **"his father" as alias is a descriptor, not a name** [Alias Grouping]
   - Problem: "his father" in Shabby American civilian's alias list is a relational descriptor, not a proper alias
   - Evidence: No one calls the character "his father" as a name — it's a relationship descriptor
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` — verify_aliases should filter relational descriptors
   - Fix: Low priority — will be resolved by fixing issue #1 (merging the characters)

### LOW
6. **"his son" in chapter/plot summary** [Summaries]
   - Problem: "Uncle Bill speaking to his son John" — John is NOT Bill's biological son, he's a ward/nephew
   - Evidence: The boy calls him "Uncle Bill" not "Dad/Father"
   - Fix: LLM summary generation — hard to fix without novel-specific correction

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
| 14 | 7.6 | +1.05 | Father/son split ✓, Johnny phantom gone ✓, summaries much improved ✓. But: no narrator, Shabby civilian false split, Uncle Bill empty profile. |

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
     - Result: **NEVER FIRED** — no parenthetical character existed (STEP 3.95 didn't split)
  2. `narrator_instruction` in `generator.py:_generate_plot_summary()`
     - Modified: `src/pipeline/overview/generator.py`
     - Result: **FIRED but with wrong narrator** — applied to "Johnny" instead of Uncle Bill, making plot summary worse
- Attempt 14:
  1. STEP 3.97: nickname phantom merge
     - Modified: `src/agents/characters.py`
     - Result: **FIXED** ✓ — no "Johnny" phantom character this run
  2. Post-5.8.5 narrator guard
     - Modified: `src/agents/characters.py`
     - Result: **UNCLEAR** — narrator still not detected. Guard may not have fired, or narrator pipeline returned nothing.
- Attempt 15:
  1. STEP 5.4.6c: Kinship alias merge for identity-reveal pattern
     - Modified: `src/agents/characters.py` — new step after STEP 5.4.6b
     - Root cause: "Shabby American civilian" (with alias "his father") was extracted separately from "John Donaldson" (proper-name parent). STEP 5.4.6c detects kinship alias + (the son) pattern → merges descriptor into proper-name parent.
     - Smoke test: PASS — "Shabby American civilian" correctly merged into "John Donaldson" (39 total mentions); "American, Sir" alias transferred; kinship alias "his father" dropped.
  2. Step 6.6: Narrator fallback using overview narrative_style
     - Modified: `src/analyzer.py` — new Step 6.6 after Step 6.5
     - Root cause: All narrator detection stages failed because chapter summaries are written in 3rd person → LLM returns "third-person" pov. The overview generator already correctly identified "first-person retrospective". Step 6.6 trusts this signal and applies the least-mentioned heuristic.
     - Smoke test: PASS — Uncle Bill (18 mentions) correctly identified as narrator when overview.narrative_style = "first-person retrospective".

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
| 14 | STEP 3.97: nickname phantom merge | `characters.py` | **FIXED** ✓ — no Johnny phantom |
| 14 | Post-5.8.5 narrator guard | `characters.py` | **UNCLEAR** — narrator still not detected |

**Pattern:** Narrator detection has been fixed and regressed 4+ times. The issue keeps returning because different LLM extraction outputs trigger different code paths. Step 6.6 uses the overview's narrative_style as a reliable authoritative signal — this bypasses all LLM narrator detection failures since the overview generator is the most accurate at identifying POV.

**Pattern:** "Shabby American civilian" false split (identity-reveal pattern) is handled by STEP 5.4.6c which uses kinship alias + "(the son)" name pattern to merge descriptor characters into proper-name parents. This is universal for stories with parent-child name splits.

## Configuration Notes
- Model config appropriate: qwen3.5:122b-a10b for characters/summaries/profiles, qwen3.5:35b-a3b for structure/pronunciation
- Zero LLM retries across all stages
- All 13 pronunciations have IPA
- Issue is NOT configuration — it's extraction and post-processing logic

## Next Action
Re-run analysis (attempt 15) to verify:
1. "Shabby American civilian" is merged into "John Donaldson" (father) via STEP 5.4.6c
2. Uncle Bill is flagged as narrator via Step 6.6 fallback
3. Uncle Bill's profile is populated (should improve once narrator is correctly assigned)
