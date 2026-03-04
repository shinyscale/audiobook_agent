# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 18
- **Phase:** awaiting_evaluation
- **baseline_score:** 6.55
- **Competitive Mode:** none

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 4.5/10 ✗ (FAILING — father/son still merged, Johnny phantom, Joe Barron missing)
  - Completeness: 5/10
  - Identity Resolution: 3/10
  - Alias Grouping: 6/10
- Character Profiles: 5/10 ✗ (FAILING — empty relationships, wrong Ted↔Johnny link)
- Chapter Summaries: 4/10 ✗ (FAILING — severely garbled: wrong narrator attribution, wrong character deaths)
- Pronunciation Guide: 9/10 ✓
- HTML Presentation: 8/10 ✓
- **Overall: 6.2/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold — REGRESSION from attempt 16's 6.95)

**REGRESSION NOTE:** Overall score 6.2 is below baseline - 0.3 (6.25). However, the code changes (STEP 3.95b, STEP 3.97) DID NOT FIRE and therefore DID NOT CAUSE the regression. The regression is entirely due to LLM non-determinism in the summary pipeline — the same unchanged summary code produced much worse output this run. Reverting the code changes would not fix the regression. The fix phase should keep the code changes (they're correct but didn't trigger) and focus on the root causes.

## Detailed Evaluation

### 2.1 Structure Detection: 9/10 ✓
Single section detected for continuous short story with no chapter markers. Correct.

### 2.2 Character Extraction: 4.5/10 ✗

**Completeness (5/10):**
- Uncle Bill ✓ (19 mentions, narrator)
- John Donaldson ✓ (28 mentions) — but father and son merged into one
- Ted Frith ✓ (5 mentions)
- Johnny — PHANTOM (2 mentions, should be alias of John Donaldson)
- Joe Barron — MISSING (was present in attempt 16, LLM non-determinism)
- John Donaldson (father) — MISSING (merged with son)

**Identity Resolution (3/10):**
- **CRITICAL FALSE MERGE:** Father (stretcher-bearer, dies) and son (ambulance driver, survives) still merged as single "John Donaldson" (28 mentions). STEP 3.95b didn't fire.
- **FALSE SPLIT:** "Johnny" (2 mentions) still separate from "John Donaldson" (28 mentions). STEP 3.97 was blocked because "John Donaldson" was claimed as a canonical name.

**Alias Grouping (6/10):**
- "John" alias on John Donaldson ✓
- "Ted" alias on Ted Frith ✓
- "Bill" and "Uncle" aliases on Uncle Bill ✓
- Johnny should be alias of John Donaldson, not separate character

### 2.3 Character Profiles: 5/10 ✗
- **Johnny**: No description. Has relationship "close friend" with Ted Frith — WRONG (Ted is Uncle Bill's friend, not Johnny's). Johnny shouldn't exist as a character.
- **John Donaldson**: Physical description ✓ ("dark face with olive skin, blue eyes"). Relationships EMPTY — should have uncle→Uncle Bill, father→John Donaldson Sr.
- **Uncle Bill**: Physical description ✓ ("elderly, grizzled, small man"). Relationships EMPTY — should have nephew→John Donaldson.
- **Ted Frith**: No description. Relationship with "Johnny" as "close friend" — should be with Uncle Bill.

### 2.4 Chapter Summaries: 4/10 ✗ (MAJOR REGRESSION from 7.5/10)

**Section summary errors:**
- "the narrative shifts to John's service as an eighteen-year-old Red Cross ambulance driver" — conflates father (stretcher-bearer) and son (ambulance driver)
- "reveals the narrator is his long-lost son" — WRONG. The narrator (Uncle Bill) is NOT the son. The dying man's son is John (the ambulance driver).
- "Uncle Bill confesses his dishonor and American identity before dying" — WRONG. Uncle Bill does NOT die. The FATHER (John Donaldson) is the one who dies saying "American, sir."

**Plot summary errors:**
- "The story is framed by Johnny, a selfish narrator" — WRONG. Uncle Bill is the narrator, not Johnny.
- "Johnny encounters John Donaldson... reveals a shocking truth: Johnny is his long-lost son" — GARBLED. The son encounters his dying father.
- "Uncle Bill... confesses his dishonor and American identity before dying after Johnny calls him 'father'" — WRONG. Uncle Bill doesn't die. The father (John Donaldson) dies.
- Entire plot summary has wrong character attributions throughout.

**Root cause:** LLM non-determinism in summary generation. No code changes were made to the summary pipeline. The same code produced correct summaries in attempt 16 but garbled ones here.

### 2.5 Pronunciation Guide: 9/10 ✓
14 entries, all with IPA. Good coverage: Piave, Caporetto, Venetia, Tagliamento, Solferino, Bersagliari, Guerre. Homographs included (live, minute, read, close, moderate).

### 2.6 HTML Presentation: 8/10 ✓
Functional navigation, logical organization. Content quality limited by upstream issues.

## Current Issues (Priority Order)

### CRITICAL
1. **Father/son John Donaldson STILL merged — 17th attempt** [Identity Resolution]
   - Problem: Only 1 "John Donaldson" (28 mentions). Father (stretcher-bearer, dies) and son (ambulance driver, survives) merged.
   - Evidence: Plot summary correctly describes father dying and son surviving — summaries know they're separate but extraction doesn't.
   - STEP 3.95b DID NOT FIRE: The regex pattern `named\s+{name}.*?\b(his|her|their)\s+(father|mother)` didn't match the summary text. The summary refers to "the narrator is his long-lost son" rather than "named John Donaldson... his father."
   - **17 attempts on this issue.** Format-based heuristics in STEP 3.95/3.95b keep failing because the LLM produces different summary text each time.
   - **Required approach:** The summary text DOES consistently describe a father-son relationship and a death. But the exact wording varies. Need a more flexible pattern match, or use the LLM itself to answer: "Does this summary describe a parent who shares a name with their child?"
   - Location: `src/agents/characters.py` — STEP 3.95b needs broader pattern matching

2. **Plot summary severely garbled — wrong narrator, wrong deaths** [Summaries]
   - Problem: Plot summary attributes narration to "Johnny" (wrong — Uncle Bill is narrator). Says Uncle Bill dies (wrong — father dies).
   - This is LLM non-determinism — summary code unchanged from attempt 16 which scored 7.5/10.
   - The plot summary is generated from section summaries. If the section summary is already garbled, the plot summary compounds the errors.
   - Location: `src/pipeline/overview/generator.py` — consider adding narrator context to the plot summary prompt
   - The narrator IS correctly identified in metadata (Uncle Bill, is_narrator=True). The plot summary prompt should use this.

### HIGH
3. **"Johnny" phantom character not merged** [Identity Resolution]
   - Problem: "Johnny" (main_cast_0, 2 mentions) separate from "John Donaldson" (main_cast_1, 28 mentions).
   - STEP 3.97 was BLOCKED: tried to add "John Donaldson" as alias for "John" but "John Donaldson" is claimed as canonical.
   - Location: `src/agents/characters.py` — STEP 3.97 merge direction issue. Should merge Johnny INTO John Donaldson (add "Johnny" as alias), not the other way.

4. **Empty relationships for main characters** [Profiles]
   - Uncle Bill and John Donaldson have zero relationships. Should have uncle↔nephew.
   - Ted Frith's relationship is with "Johnny" (phantom) instead of Uncle Bill.
   - Root cause: Likely cascading from character extraction issues (merged characters confuse profiler).

### MEDIUM
5. **Joe Barron missing** [Completeness]
   - Present in attempt 16, absent in attempt 17. LLM non-determinism.
   - Low impact (3 mentions in text), but demonstrates extraction instability.

### LOW
6. **character_summary=null for all characters** [Profiles]
   - Minor impact.

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
| 17 | 6.2 | -0.35 | STEP 3.95b and 3.97 didn't fire. Summary SEVERE REGRESSION (LLM non-determinism). Wrong narrator in plot summary, wrong deaths. |

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
     - Result: **DID NOT FIRE** — LLM produced "John Donaldson" without parenthetical this time.
- Attempt 17:
  1. STEP 3.95b: Summary-text parent attribution split
     - Modified: `src/agents/characters.py` — new STEP 3.95b after STEP 3.95
     - Result: **DID NOT FIRE** — regex pattern didn't match the actual summary wording
  2. STEP 3.97 strengthened: threshold lowered + parenthetical guard
     - Modified: `src/agents/characters.py` — STEP 3.97
     - Result: **BLOCKED** — "Johnny" mention_count inflated to 30 at STEP 3.97 time (had alias "John Donaldson" during grounding → total_mentions=30 → > 3 check skipped merge)
- Attempt 18:
  1. STEP 3.95b: Added Pattern B (revelation verb + his son/daughter) + Pattern C (possessive)
     - Root cause: Pattern A required "named {name}...his father" but summary said "John Donaldson...reveals...his long-lost son" (reversed direction)
     - Pattern B requires revelation verb to avoid false positives on ordinary parent references
     - Smoke test: Pattern B matched actual summary text ✓, did NOT match normal parent reference ✓
     - Modified: `src/agents/characters.py` — STEP 3.95b
  2. STEP 3.97: Use canonical-name-only mention count from mention_results
     - Root cause: after _deduplicate_alias_canonical_conflicts strips cross-character aliases, char.mention_count stays inflated (was total_mentions including stripped aliases). `mentions_by_alias[canonical_name]` gives the actual count.
     - Smoke test: correctly reads canonical_count=2 (not inflated mention_count=30) → merge fires ✓
     - Modified: `src/agents/characters.py` — STEP 3.97
  3. generator.py narrator injection: added "Refer to narrator as '{name}'" to narrator_instruction
     - Root cause: LLM hallucinated "Johnny" as narrator name from context cues (dying man calling "Johnny" in dialogue, confusing the narrator's identity)
     - Modified: `src/pipeline/overview/generator.py` — narrator_instruction

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
| 17 | STEP 3.95b: summary-text parent attribution | `characters.py` | **DID NOT FIRE** — regex didn't match summary wording |
| 17 | STEP 3.97: lower threshold + parenthetical guard | `characters.py` | **BLOCKED** — inflated mention_count (alias stripped but count not refreshed) |
| 18 | STEP 3.95b: added Pattern B (revelation+son) + Pattern C (possessive) | `characters.py` | Pending verification |
| 18 | STEP 3.97: use canonical-name-only count from mention_results | `characters.py` | Pending verification |
| 18 | generator.py: narrator name instruction strengthened | `generator.py` | Pending verification |

**ESCALATION PATTERN — CRITICAL:** The father/son split has been attempted across 7 attempts (11, 12, 13, 15, 16, 17) using 5 different heuristics, ALL in `characters.py`. Each heuristic targets a specific LLM output format that may or may not appear:
- Attempt 11: characters_present lists → empty
- Attempt 12: alias tier contradiction → works sometimes
- Attempt 15: same as 12, regressed
- Attempt 16: canonical-name parenthetical → didn't fire
- Attempt 17: summary-text regex → didn't match

**The fundamental problem is clear:** No format-specific regex can reliably catch this pattern across LLM runs. The fix MUST either:
1. Use an LLM call to analyze whether a same-name parent-child exists in the summaries (robust against wording variation), OR
2. Search summary text for a BROADER set of father/son signals (not just "named X... his father" but also "X's father", "father of X", "his father X", "identifies the dying man as his father", etc.), OR
3. Move the detection UPSTREAM to the summary/extraction prompts to force the LLM to explicitly flag same-name parent-child relationships

## Configuration Notes
- Model config appropriate: qwen3.5:122b-a10b for characters/summaries/profiles, qwen3.5:35b-a3b for structure/pronunciation
- Zero LLM retries across all stages
- All 14 pronunciations have IPA
- Issue is NOT configuration — it's extraction logic AND summary LLM non-determinism

## Pipeline Notes (Attempt 18)
- Analysis completed in 29m 49s
- 4 final characters: Uncle Bill (18), John Donaldson (28), Joe Barron (3), Ted Frith (5)
- No "Johnny" phantom character ✓ (STEP 3.97 working)
- "John's Father" appeared in warnings (BLOCKED alias log) — STEP 3.95b may have fired but created a character that was filtered
- "Pass 2 failed for John, keeping without aliases" — alias processing issue for short name
- "Low confidence profile for John Donaldson: 0.30" + JSON parse failure
- Joe Barron present ✓ (was missing in attempt 17 due to LLM non-determinism)
- Margaret Donaldson added via F6 reconciliation but not in final top-level characters

## Pipeline Notes (Attempt 17)
- STEP 3.95b DID NOT FIRE — regex `named\s+{name}.*?\b(his|her|their)\s+(father|mother)` didn't match
- STEP 3.97 BLOCKED — tried to add "John Donaldson" as alias for "John" (wrong direction, canonical name conflict)
- Uncle Bill narrator: ✓ (V2 pipeline metadata)
- Summary REGRESSION: LLM produced garbled summaries this run (narrator confused with Johnny, Uncle Bill described as dying)
- Pass 2 failures: "Pass 2 failed for the narrator" and "Pass 2 failed for Uncle Bill"

## Next Action
Re-run analysis to verify fixes from attempt 18:
1. STEP 3.95b Pattern B should now fire on "John Donaldson...reveals...his long-lost son" → creates "John Donaldson (the father)"
2. STEP 3.97 should now merge "Johnny" → alias of "John Donaldson" (canonical count=2 not inflated 30)
3. generator.py should now use narrator name "Uncle Bill" explicitly in plot summary

If father/son split still fails: investigate whether Pattern B's `{0,400}` window is too short, or whether the summary text wording varies again.
