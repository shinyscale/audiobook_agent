# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 16
- **Phase:** awaiting_evaluation
- **baseline_score:** 6.55
- **Competitive Mode:** none

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 5/10 ✗ (FAILING — father/son re-merged, aliases cross-contaminated)
  - Completeness: 6/10
  - Identity Resolution: 4/10
  - Alias Grouping: 5/10
- Character Profiles: 6/10 ✗ (FAILING — merged character has confused profile, Uncle Bill missing John relationship)
- Chapter Summaries: 6/10 ✗ (FAILING — major factual error: claims Uncle Bill dies)
- Pronunciation Guide: 9/10 ✓
- HTML Presentation: 8/10 ✓
- **Overall: 6.85/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold)

## Detailed Evaluation

### 2.1 Structure Detection: 9/10 ✓
Single section for continuous short story — correct. No artificial splitting.

### 2.2 Character Extraction: 5/10 ✗

**What Attempt 15 Fixes Got RIGHT:**
- STEP 5.4.6c fired ✓ — "Shabby American civilian" merged into John Donaldson
- Step 6.6 fired ✓ — Uncle Bill correctly identified as narrator (is_narrator=true)
- Joe Barron appeared as minor character (3 mentions)

**What FAILED (LLM non-determinism):**

**Completeness (6/10):**
- Uncle Bill ✓, Ted Frith ✓, Joe Barron ✓
- John Donaldson (the son) MISSING — merged into father character
- Only 4 characters total; should be 5 (father + son as separate)

**Identity Resolution (4/10):**
- **CRITICAL FALSE MERGE:** Only 1 "John Donaldson (the father)" exists with 42 mentions. This combines BOTH the father (stretcher-bearer who dies on battlefield) and the son (ambulance driver, Uncle Bill's nephew). The story has TWO distinct John Donaldsons.
- The character labeled "(the father)" has aliases "the boy" and "John Donaldson (the boy/narrator)" — these belong to the SON, not the father. This is internal contradictiont hat STEP 3.95 should have caught.
- STEP 3.95 (alias contradiction detection) apparently did not fire — despite canonical name containing "father" and alias containing "boy", which is an obvious parent/child contradiction.

**Alias Grouping (5/10):**
- "the boy" alias on a character named "(the father)" — clearly wrong
- "John Donaldson (the boy/narrator)" alias — this is the son's descriptor on the father's character
- Aliases from the merged "Shabby American civilian" were absorbed correctly by STEP 5.4.6c

### 2.3 Character Profiles: 6/10 ✗

- **Uncle Bill**: physical_description="elderly, grizzled, small man" ✓, relationship with Ted Frith="colleague" ✓. But MISSING relationship with John Donaldson (nephew/ward). Character_summary=null.
- **John Donaldson (the father)**: physical_description describes the father correctly ("alluring, sidewise smile", "eyes like his son's"). But relationships={} empty — should have father→son. This is partly because the son doesn't exist as a separate character.
- **Joe Barron**: no description (appropriate for 3 mentions)
- **Ted Frith**: no description, has relationship with Uncle Bill ✓

### 2.4 Chapter Summaries: 6/10 ✗

**MAJOR FACTUAL ERROR** in both chapter summary and plot summary:
- "Uncle Bill, who dies confessing his fear of dishonor before revealing his true American identity" — Uncle Bill does NOT die. The FATHER (John Donaldson Sr.) is the one who dies on the battlefield. Uncle Bill is the frame narrator who survives to tell the story.
- "John embraces the dying narrator" — the narrator (Uncle Bill) is NOT dying; the narrator is alive telling the story in retrospect.
- The plot summary confuses Uncle Bill with John Donaldson the father in the final paragraph, attributing the father's death scene to Uncle Bill.

**What's correct:**
- Frame narrative setup (Uncle Bill + John by the fire) ✓
- War story details (Caporetto, stretcher-bearer, Croix de Guerre) ✓
- Father's identity reveal ✓
- Themes correctly identified ✓
- Narrative style "first-person retrospective" ✓

### 2.5 Pronunciation Guide: 9/10 ✓
14 entries, all with IPA. Strong coverage of Italian place names and homographs. No false positives.

### 2.6 HTML Presentation: 8/10 ✓
Functional navigation, logical organization.

## Current Issues (Priority Order)

### CRITICAL
1. **Father/son John Donaldson re-merged into single character** [Identity Resolution]
   - Problem: Only 1 "John Donaldson (the father)" with 42 mentions exists. The son (ambulance driver, Uncle Bill's nephew) is MISSING as a separate character. Aliases "the boy" and "John Donaldson (the boy/narrator)" from the son are on the father's character.
   - Evidence: Character has canonical name containing "father" but alias "the boy" — internal contradiction. 42 mentions combines both characters.
   - Root cause: LLM non-determinism — V2 extraction sometimes produces 2 John Donaldsons (attempts 8, 9, 12, 14) and sometimes 1 (attempts 10, 13, 15). STEP 3.95 (alias contradiction detection) should have caught the "father"/"boy" contradiction but did NOT fire.
   - Location: `src/agents/characters.py` — STEP 3.95
   - Fix: STEP 3.95 needs to detect when a character's CANONICAL NAME contains a parent-tier word (father, mother) AND has aliases containing child-tier words (boy, son, daughter, girl, child). This is a stronger signal than just alias-vs-alias contradiction. When detected, split the character.
   - **Pattern alert:** This is the SAME issue as attempts 10, 13. The father/son split has been fixed and regressed 3 times due to LLM non-determinism. The fix must be robust enough to handle BOTH cases: (a) when LLM produces 2 John Donaldsons (already works), and (b) when LLM produces 1 merged John Donaldson (STEP 3.95 must catch).

2. **Plot summary major factual error: Uncle Bill incorrectly described as dying** [Summaries]
   - Problem: Both chapter summary and plot summary claim "Uncle Bill dies confessing his fear of dishonor" and "John embraces the dying narrator." Uncle Bill is the SURVIVING frame narrator. The FATHER dies on the battlefield.
   - Evidence: Uncle Bill is marked is_narrator=true with narrative_style="first-person retrospective" — a dead narrator cannot narrate in retrospect. The overview correctly says he's the frame narrator.
   - Location: `src/pipeline/overview/generator.py` or summary generation
   - Root cause: Likely caused by the father/son merge — since there's only 1 John Donaldson, the LLM confuses which character dies. The merged character's death scene gets attributed to Uncle Bill in the summary. Fixing issue #1 (father/son split) may resolve this.
   - Fix: May self-resolve when father/son split works. If not, add narrator-death validation: if a character is_narrator=true and narrative_style is retrospective, the summary should not claim the narrator dies (logical impossibility).

### HIGH
3. **Uncle Bill missing relationship with John Donaldson** [Profiles]
   - Problem: Uncle Bill has relationship with Ted Frith only. He should have uncle/guardian relationship with John Donaldson (the son).
   - Evidence: Story opens with Uncle Bill greeting "his nephew John" — the relationship is explicit.
   - Location: `src/pipeline/character_profiling/` or `src/analyzer.py`
   - Fix: Likely a cascading effect of the father/son merge. When the son exists as a separate character, the profiler should correctly assign the uncle→nephew relationship. Fix issue #1 first.

### MEDIUM
4. **John Donaldson (the father) has empty relationships** [Profiles]
   - Problem: relationships={} despite being father to the son
   - Fix: Cascading effect of father/son merge. Will resolve with issue #1.

### LOW
5. **character_summary=null for all characters** [Profiles]
   - Problem: No character summaries generated for any character
   - Minor impact — physical descriptions and relationships are more important for narrators

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
| 15 | 6.85 | +0.30 | STEP 5.4.6c ✓ (shabby civilian merged), Step 6.6 ✓ (narrator). BUT father/son re-merged (STEP 3.95 didn't fire). Plot summary claims Uncle Bill dies (factual error). |

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
     - Result: **FIXED** ✓ — "Shabby American civilian" correctly merged into John Donaldson
  2. Step 6.6: Narrator fallback using overview narrative_style
     - Modified: `src/analyzer.py` — new Step 6.6 after Step 6.5
     - Result: **FIXED** ✓ — Uncle Bill correctly identified as narrator

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
| 15 | STEP 5.4.6c: identity-reveal kinship merge | `characters.py` | **FIXED** ✓ — shabby civilian merged |
| 15 | Step 6.6: narrator fallback | `analyzer.py` | **FIXED** ✓ — Uncle Bill is narrator |

**Pattern:** Father/son split has been fixed 3 times (attempts 8, 12, 14) and regressed 3 times (attempts 10, 13, 15). The fix works when the LLM happens to extract 2 John Donaldsons, but fails when the LLM merges them into 1 character. STEP 3.95 must be enhanced to detect the canonical-name-vs-alias contradiction (canonical has "father", alias has "boy") — this is a STRONGER signal than alias-vs-alias and should trigger a split even when there's only 1 John Donaldson character.

**Key insight for fix phase:** The character "John Donaldson (the father)" has canonical name containing "father" AND aliases containing "the boy" and "the boy/narrator". These are contradictory descriptors — a father is not a boy. STEP 3.95 currently checks alias-vs-alias contradictions but apparently does NOT check canonical-name-vs-alias contradictions. Extending STEP 3.95 to check this would make the split robust against LLM non-determinism.

## Configuration Notes
- Model config appropriate: qwen3.5:122b-a10b for characters/summaries/profiles, qwen3.5:35b-a3b for structure/pronunciation
- Zero LLM retries across all stages
- All 14 pronunciations have IPA
- Issue is NOT configuration — it's extraction and post-processing logic

## Next Action
Evaluate attempt 16 output.

## Fix History (Attempt 16)
- **STEP 3.95 extended: canonical-name parenthetical tier detection**
  - Root cause: STEP 3.95 only checked aliases for parent/child tier words. The canonical name "John Donaldson (the father)" has "the father" in the parenthetical, not in aliases. So `_parent_als` was empty → split never triggered.
  - Fix: Before the alias check, extract the canonical name's parenthetical and check its tier. If canonical is parent-tier and no parent-tier aliases exist, synthesize `_parent_als` from the parenthetical content. Also extract base name (strip parenthetical) before constructing split character canonical names. If the canonical was parent-tier, rename the child character's canonical to "BaseName (child-label)".
  - Modified: `src/agents/characters.py` — STEP 3.95 (lines 437-502)
  - Smoke test: 332 tests pass, 0 failures
  - Universality: universal invariant — parenthetical role-descriptor in canonical name is a generic pattern, not book-specific
