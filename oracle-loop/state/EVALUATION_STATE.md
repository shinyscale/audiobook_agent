# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 16
- **Phase:** awaiting_analysis
- **baseline_score:** 6.55
- **Competitive Mode:** none

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Latest Scores
- Structure Detection: 8/10 ✓
- Character Extraction: 5/10 ✗ (FAILING — father/son still merged, Johnny phantom)
  - Completeness: 6/10
  - Identity Resolution: 4/10
  - Alias Grouping: 6/10
- Character Profiles: 6/10 ✗ (FAILING — Uncle Bill's relationship with John wrong, father missing)
- Chapter Summaries: 7.5/10 ✗ (FAILING — plot summary says "twelve-year-old" returned from war)
- Pronunciation Guide: 9/10 ✓
- HTML Presentation: 8/10 ✓
- **Overall: 6.95/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold)

## Detailed Evaluation

### 2.1 Structure Detection: 8/10 ✓
2 sections detected for continuous short story. Previous attempts produced 1 section (scored 9/10). The 2-section split corresponds to a natural narrative break (backstory → present-day reunion) but the story has no explicit chapter markers. Not a code regression — LLM non-determinism in structure detection. Section summaries within each section are accurate.

### 2.2 Character Extraction: 5/10 ✗

**What Attempt 16 Fixes Got RIGHT:**
- STEP 3.95 canonical-name parenthetical detection code is correct
- It simply didn't fire because this time the LLM produced "John Donaldson" WITHOUT a parenthetical

**What FAILED (LLM non-determinism — different output format):**

**Completeness (6/10):**
- Uncle Bill ✓, Ted Frith ✓, Joe Barron ✓
- John Donaldson (son) — exists as "John Donaldson" (29 mentions) with alias "ambulance driver" ✓
- John Donaldson (father) — MISSING. Father and son are merged into a single "John Donaldson" with 29 combined mentions
- "Johnny" (main_cast_0, 2 mentions) — PHANTOM character. This is a nickname for John Donaldson (the son) and should be an alias, not separate

**Identity Resolution (4/10):**
- **CRITICAL FALSE MERGE (STILL):** Only 1 "John Donaldson" exists with 29 mentions. The father (stretcher-bearer who dies) and son (ambulance driver who survives) are merged. The PLOT SUMMARY correctly distinguishes them ("John identifies the dying man as his father"), proving the summaries know they're separate — but the character extraction doesn't.
- **FALSE SPLIT:** "Johnny" (2 mentions) exists as separate character from "John Donaldson" (29 mentions). Johnny is a diminutive of John and should be an alias. STEP 3.97 (nickname phantom merge) should have caught this but apparently didn't fire.

**Alias Grouping (6/10):**
- "ambulance driver" on John Donaldson ✓
- "Bill" on Uncle Bill ✓
- "Ted" on Ted Frith ✓
- Johnny should be an alias of John Donaldson, not a separate character

### 2.3 Character Profiles: 6/10 ✗

- **Uncle Bill**: physical_description ✓ ("elderly, grizzled, small man"). But relationship with John Donaldson is WRONG: says `"father of John (biological father of the nephew, not Uncle Bill's father)"` — Uncle Bill is the UNCLE/guardian, NOT the father. This garbled text seems to be the profiler trying to describe someone else's relationship to John.
- **John Donaldson**: physical_description ✓ ("beautiful youngster", "rainbow prince", "dark face with olive color" — these correctly describe the son). Relationships empty — should at minimum have uncle→Uncle Bill and father→John Donaldson Sr.
- **Ted Frith**: relationship with Uncle Bill as "comrade" ✓
- **Joe Barron**: no description (appropriate for 3 mentions)
- **Johnny**: no profile (phantom character shouldn't exist)

### 2.4 Chapter Summaries: 7.5/10 ✗

**Major improvement from attempt 15:** Uncle Bill is no longer described as dying. The father's death is correctly attributed to the father.

**Section summaries (accurate):**
- Section 1: Correctly captures backstory — Uncle Bill's history with the Donaldson family, father's decline, hunting trip death, Margaret's letter ✓
- Section 2: Correctly describes John's return from WWI, discovery of dying father at the front, father's redemption and death, final fireside scene ✓

**Plot summary issues:**
- "his now twelve-year-old nephew, John, home from the Italian front" — FACTUAL ERROR. John was 12 when adopted; he's ~22 when returning from WWI. A 12-year-old cannot serve as an ambulance driver. The section summary correctly says "ten years after agreeing to take in his orphaned twelve-year-old nephew" (implying he's now ~22), but the plot summary compressed this incorrectly.
- Otherwise the plot summary is substantially improved — correctly distinguishes father and son, correctly attributes death to father, correct themes.

### 2.5 Pronunciation Guide: 9/10 ✓
14 entries, all with IPA. Good coverage of Italian/French terms and homographs.

### 2.6 HTML Presentation: 8/10 ✓
Functional navigation, logical organization.

## Current Issues (Priority Order)

### CRITICAL
1. **Father/son John Donaldson STILL merged — 16th attempt** [Identity Resolution]
   - Problem: Only 1 "John Donaldson" (29 mentions) exists. Father (stretcher-bearer, dies) and son (ambulance driver, survives) are merged.
   - Evidence: Plot summary correctly says "John identifies the dying man as his father" — the summaries distinguish them but character extraction doesn't.
   - Root cause: This time the LLM produced "John Donaldson" WITHOUT parenthetical annotation, so the attempt 16 fix (parenthetical tier detection in STEP 3.95) had nothing to detect.
   - **Pattern alert:** This is the 4th regression (attempts 10, 13, 15, 16). Previous fixes targeted SPECIFIC LLM output formats (parenthetical names, alias contradictions). Each fix works for ONE format but not others.
   - **Required approach:** The fix must use SUMMARY TEXT as ground truth, not LLM character output format. The section summaries explicitly describe a father dying and a son surviving with the same name. A summary-aware split would be robust against LLM non-determinism.
   - Location: `src/agents/characters.py` — needs a new approach, not another STEP 3.95 variant
   - Fix strategy: After character extraction, scan summary text for patterns like "his father [Name]" or "[Name]'s father" where [Name] matches a character. If found, and the character doesn't already have a parent/child split, create two characters: one for the father references and one for the son references.

### HIGH
2. **"Johnny" phantom character not merged** [Identity Resolution]
   - Problem: "Johnny" (main_cast_0, 2 mentions) is a separate character from "John Donaldson" (main_cast_3, 29 mentions). Johnny is a common diminutive of John.
   - Evidence: "Johnny" is clearly a nickname for John Donaldson. STEP 3.97 (nickname phantom merge) should have caught this.
   - Location: `src/agents/characters.py` — STEP 3.97
   - Fix: Check if STEP 3.97 covers "Johnny" → "John" mapping. If not, add it. Also check mention threshold — 2 mentions vs 29 should easily trigger a merge.

3. **Uncle Bill's relationship with John is wrong** [Profiles]
   - Problem: Uncle Bill's relationship says `"father of John (biological father of the nephew, not Uncle Bill's father)"` — Uncle Bill is the UNCLE, not father.
   - Root cause: Likely cascading from the father/son merge. Since there's only 1 John Donaldson, the profiler conflates the father-son relationship information.
   - Fix: Will likely resolve when father/son split works (issue #1).

### MEDIUM
4. **Plot summary incorrectly says John is twelve returning from war** [Summaries]
   - Problem: "his now twelve-year-old nephew, John, home from the Italian front" — he was 12 when adopted, ~22 when returning from WWI.
   - Evidence: Section 2 summary correctly says "ten years after agreeing to take in his orphaned twelve-year-old nephew" (implying now ~22).
   - Location: `src/pipeline/overview/generator.py` — plot summary generation
   - Fix: This is LLM compression error. Low priority — the section summaries are correct.

### LOW
5. **character_summary=null for all characters** [Profiles]
   - Minor impact — physical descriptions and relationships are more important.

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
| 16 | 6.95 | +0.40 | STEP 3.95 parenthetical fix correct but LLM produced no parenthetical this time. Summaries much improved (Uncle Bill no longer dies). Johnny phantom returned. |

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
- Attempt 16:
  1. STEP 3.95 extended: canonical-name parenthetical tier detection
     - Modified: `src/agents/characters.py` — STEP 3.95
     - Result: **DID NOT FIRE** — LLM produced "John Donaldson" without parenthetical this time. Code is correct but targets a specific LLM output format that didn't occur.
- Attempt 17:
  1. STEP 3.95b: Summary-text parent attribution split
     - Modified: `src/agents/characters.py` — new STEP 3.95b after STEP 3.95
     - Detects "named {Name}... his/her/their father/mother" pattern in chapter summaries
     - Only fires when: multi-word name, no existing paren annotation, ≥10 mentions, ≥1 neutral alias
     - Creates "[Name] (the father/mother)" supporting character with 2 estimated mentions
     - Root cause: STEP 3.95 only checked LLM-assigned aliases; this checks summary text directly
  2. STEP 3.97 strengthened: threshold lowered + parenthetical guard added
     - Modified: `src/agents/characters.py` — STEP 3.97 candidates filter
     - Asymmetry threshold lowered from 10x/min-10 to 5x/min-5 (catches lower-mention formal names)
     - Added `"(" not in c.canonical_name` guard: excludes STEP 3.95b-created parent characters from candidates, preventing the "two John-starting candidates" ambiguity that would block the merge

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
| 16 | STEP 3.95 parenthetical tier detection | `characters.py` | **DID NOT FIRE** — no parenthetical in canonical name |
| 17 | STEP 3.95b: summary-text parent attribution | `characters.py` | Pending |
| 17 | STEP 3.97: lower threshold + parenthetical guard | `characters.py` | Pending |

**ESCALATION PATTERN DETECTED:** The father/son split has been attempted in `characters.py` STEP 3.95 across 5 attempts (11, 12, 13, 15, 16). Each fix targets a specific LLM output format:
- Attempt 11: characters_present lists → empty lists, didn't fire
- Attempt 12: alias-vs-alias tier contradiction → works when LLM assigns contradictory aliases
- Attempt 15: same as 12, regressed when LLM didn't assign contradictory aliases
- Attempt 16: canonical-name parenthetical → works when LLM adds parenthetical, doesn't fire otherwise

**The fundamental problem:** All STEP 3.95 variants depend on the LLM's character OUTPUT format. The LLM sometimes produces 2 characters, sometimes 1; sometimes adds parentheticals, sometimes doesn't; sometimes assigns contradictory aliases, sometimes doesn't. No single format-based heuristic is robust.

**Required escalation:** Use SUMMARY TEXT as the ground truth signal. The section summaries ALWAYS correctly distinguish father and son (e.g., "John identifies the dying man as his father"). A summary-text-aware split would be robust because the summary text is deterministic — it consistently describes the father/son relationship regardless of how the character extractor formats its output.

## Configuration Notes
- Model config appropriate: qwen3.5:122b-a10b for characters/summaries/profiles, qwen3.5:35b-a3b for structure/pronunciation
- Zero LLM retries across all stages
- All 14 pronunciations have IPA
- Issue is NOT configuration — it's extraction and post-processing logic

## Next Action
Re-run analysis to verify fix. STEP 3.95b should split father/son. STEP 3.97 (with lowered threshold + parenthetical guard) should merge Johnny.
