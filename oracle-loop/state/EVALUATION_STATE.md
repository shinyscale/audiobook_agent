# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 20
- **Phase:** awaiting_fix
- **baseline_score:** 6.55
- **Competitive Mode:** none

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## IMPORTANT: External Changes Detected

Commit `90b62a5` ("Rationalize LLM tuning params for qwen3-next:80b model") was made OUTSIDE the oracle loop after the analysis commit. It changed:
- LLMConfig max_tokens: 4096 -> 8192
- AgentConfig max_tokens: 32768 -> 8192
- AgentConfig context_length: 65536 -> 32768
- Fixed config mutation bug where qwen3 auto-tuning permanently mutated self.config

**The analysis MUST be re-run before applying more code fixes** to verify whether these config changes affect the output. The current output may reflect stale config.

## IMPORTANT: Pipeline Notes vs Actual Output Mismatch

The previous pipeline notes (from the analysis phase) claimed father/son split fired, Joe Barron present, Margaret Donaldson present, Uncle Bill narrator confirmed. **None of these match the actual output.** The output shows:
- Single "John" character (no father/son split)
- No Joe Barron or Margaret Donaldson
- John marked as narrator (WRONG — Uncle Bill should be)
- "the American, sir" as a false character

The analysis phase likely wrote notes based on intermediate log output that didn't persist to the final analysis.json. Evaluate based on ACTUAL OUTPUT only.

## Latest Scores
- Structure Detection: 8/10 ✓
- Character Extraction: 4/10 ✗ (FAILING — no father/son split, false character, wrong narrator)
  - Completeness: 5/10
  - Identity Resolution: 3/10
  - Alias Grouping: 5/10
- Character Profiles: 3/10 ✗ (FAILING — profile contamination from narrator misassignment, wrong relationships)
- Chapter Summaries: 6.5/10 ✗ (FAILING — "Uncle Bill's father" error, Uncle Bill on battlefield)
- Pronunciation Guide: 9/10 ✓
- HTML Presentation: 7.5/10 ✗ (FAILING — BOM in title, author name as title instead of story name)
- **Overall: 5.95/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (4 categories below threshold) — SEVERE REGRESSION from attempt 19 (7.7)

## Detailed Evaluation

### 2.1 Structure Detection: 8/10 ✓
- 1 section for continuous short story — correct, no chapter markers in source text
- Title is null — minor issue but acceptable for continuous text
- Attempt 19 had 2 sections; 1 section is arguably more correct for this text

### 2.2 Character Extraction: 4/10 ✗

**Completeness (5/10):**
- John (44 mentions) ✓ — but this is son only, father not separated
- Uncle Bill (18 mentions) ✓
- Ted Frith (5 mentions) ✓
- "the American, sir" (5 mentions) — FALSE CHARACTER. This is a quote/phrase from the story, not a character name. The "shabby American civilian" is John Donaldson's father.
- MISSING: John Donaldson (the father) as a separate character
- MISSING: Joe Barron, Margaret Donaldson

**Identity Resolution (3/10):**
- Father/son NOT split — the central identity puzzle of this story is completely unresolved
- "the American, sir" is a false extraction that should be the father character
- Narrator misassigned: John=narrator (WRONG), Uncle Bill=not narrator (WRONG). Uncle Bill is the first-person frame narrator.

**Alias Grouping (5/10):**
- John aliases: ['the boy', 'John Donaldson', 'John', 'Johnny'] — reasonable for the son
- Uncle Bill aliases: ['Bill'] — OK
- "the American, sir" aliases: ['American, sir'] — entire entry is invalid
- Ted Frith aliases: ['Ted'] — OK

### 2.3 Character Profiles: 3/10 ✗

- **John** (marked narrator): Physical description is "elderly, grizzled, small man, grim and unexhilarating" — this is UNCLE BILL's description, not John's! John should be "beautiful youngster, towering". The narrator misassignment caused the profiler to attribute Uncle Bill's first-person self-descriptions ("I am crabbed and prejudiced") to John.
- **Uncle Bill** (marked non-narrator): Has no physical description of his own. Relationships empty except "the American, sir (uncle)" — meaningless since that character shouldn't exist.
- **"the American, sir"**: Has physical description "tall and broad-shouldered, dark skin, shabby clothing" — this is actually the father's description, but attached to a false character name. Relationships claim uncle↔John and nephew↔Uncle Bill — completely wrong.
- **Ted Frith**: colleague to John ✓ — only correct relationship in the output.
- character_summary null for all characters.

### 2.4 Chapter Summaries: 6.5/10 ✗

**Section summary (decent):**
- Covers story arc from Uncle Bill receiving letter → John's war service → deathbed scene
- Correctly mentions "American, sir" declaration
- Erroneously says "the narrator encounters John Donaldson" on the battlefield — Uncle Bill is NOT on the battlefield; John encounters his father there

**Plot summary (major errors):**
- Paragraph 1: "he is Uncle Bill's long-lost father" — WRONG. The dying man is JOHN's father, not Uncle Bill's. Uncle Bill is the frame narrator with no blood relation.
- Paragraph 2: "Uncle Bill himself encounters this same man" — WRONG. Uncle Bill is not on the Italian front. John encounters the dying man.
- Paragraph 3: Good — correctly notes Uncle Bill "alive and whole, carries this moment"
- The nested narration (Uncle Bill telling John's story) continues to confuse the LLM

### 2.5 Pronunciation Guide: 9/10 ✓
- 15 entries, all with IPA ✓
- Excellent foreign terms: Caporetto, Piave, Solferino, Guerre, Venetia, Tagliamento, Bersagliari, Bordeaux
- Homographs: live, minute, read, close, moderate — appropriate
- Minor: "dum-dums" and "mayn't" are valid flags

### 2.6 HTML Presentation: 7.5/10 ✗
- Title shows "Mary Raymond Shipman Andrews" (author) instead of story title "American, Sir"
- BOM character in title: `﻿Mary Raymond Shipman Andrews`
- Navigation functional ✓
- Character sections logically organized ✓
- 2 main + 2 supporting character layout ✓

## Current Issues (Priority Order)

### CRITICAL
1. **Father/son split did not fire — STEP 3.95/3.95b regression** [Identity Resolution]
   - Problem: Only one "John" character exists (44 mentions). The father is not a separate character.
   - Evidence: Attempt 19 successfully split using Pattern D (STEP 3.95b). This run, the split didn't occur.
   - Root cause: LLM non-determinism in summary text. Pattern D regex depends on specific wording in summaries. Different summary wording → different regex matches → split doesn't fire.
   - NOTE: Before adding more patterns, re-run analysis first — external config changes (commit 90b62a5) may affect model output.

2. **"the American, sir" extracted as false character** [Completeness/Identity]
   - Problem: "the American, sir" is a quote/phrase, not a character name. The actual character is John Donaldson's father (the "shabby American civilian").
   - Evidence: main_cast_3 with id "main_cast_3" has 5 mentions. The phrase appears in dialogue.
   - Location: V2 character extraction — LLM incorrectly extracts quoted phrases as character names
   - Fix: This may resolve naturally if the father/son split fires correctly (the father would absorb these mentions). Could also add a post-extraction filter for quoted phrases containing "sir".

3. **Narrator misassignment: John instead of Uncle Bill** [Identity Resolution]
   - Problem: John is narrator=True, Uncle Bill is narrator=False. Uncle Bill is the first-person frame narrator.
   - Evidence: Uncle Bill's quotes ("I am not soft-hearted. I am crabbed and prejudiced...") are attributed to John's profile.
   - Location: Narrator detection pipeline — Step 6.6 narrator fallback (analyzer.py) may not be firing.
   - Note: This worked in attempts 14-15, 19. Regression suggests LLM non-determinism or config change impact.

### HIGH
4. **Profile contamination from narrator misassignment** [Profiles]
   - Problem: John's profile contains Uncle Bill's physical description and personality traits. Uncle Bill's profile is empty.
   - Evidence: John shows "elderly, grizzled, small man" — this describes Uncle Bill. John should be "beautiful youngster, towering."
   - Root cause: Cascades from Issue #3. When narrator is fixed, profiles should improve.

5. **Plot summary says "Uncle Bill's father" and puts Uncle Bill on battlefield** [Summaries]
   - Problem: (a) "he is Uncle Bill's long-lost father" — should be JOHN's father. (b) "Uncle Bill himself encounters this same man" — Uncle Bill is not in Italy.
   - Evidence: The text establishes John Donaldson (the son) discovers his father on the Italian front. Uncle Bill is the frame narrator in New York/at home.
   - Location: `src/pipeline/overview/generator.py` — narrator_instruction needs stronger clarification about nested narration.

### MEDIUM
6. **HTML title shows author name instead of story title** [Presentation]
   - Problem: `<title>﻿Mary Raymond Shipman Andrews - Audiobook Prep Report</title>` — should be "American, Sir" or the actual story title.
   - BOM character `﻿` is also present.
   - Location: Title extraction in ingestion or HTML template generation.

7. **Missing minor characters: Joe Barron, Margaret Donaldson** [Completeness]
   - F6/F6b reconciliation non-deterministic. Low priority.

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.55 | 0 | Baseline. Narrator misidentification cascades into profiles + summaries |
| 2 | 6.6 | +0.05 | Narrator fix worked (Bill=narrator). Johnny still missing, summary wrong. |
| 3 | 6.0 | -0.55 | REGRESSION. "American, sir" false character stole narrator. |
| 4 | 6.4 | -0.15 | Co-present guard fixed "American, sir" but narrator regressed. |
| 5 | 6.7 | +0.15 | Plot summary improved. Narrator metadata still wrong. |
| 6 | 7.0 | +0.45 | Uncle Bill narrator. John Donaldson false secondary narrator. |
| 7 | 6.9 | +0.35 | Narrator guard worked. Boy disappeared (false merge). |
| 8 | 7.85 | +1.30 | Father/son split, plot summary fixed, profiles improved. |
| 9 | 8.0 | +1.45 | Cross-character alias contamination fixed. |
| 10 | 7.0 | +0.45 | REGRESSION. Father/son merge recurred (LLM non-determinism). |
| 11 | 7.2 | +0.65 | Narrator fix, relationship cleanup. STEP 3.95 didn't fire. |
| 12 | 7.7 | +1.15 | Father/son split via alias contradiction! |
| 13 | 5.8 | -0.75 | SEVERE REGRESSION. STEP 3.95 didn't fire, narrator wrong. |
| 14 | 7.6 | +1.05 | Father/son split, Johnny gone, summaries improved. |
| 15 | 6.85 | +0.30 | Shabby civilian merged, narrator fixed. Father/son re-merged. |
| 16 | 6.95 | +0.40 | LLM produced no parenthetical this time. Johnny phantom returned. |
| 17 | 6.2 | -0.35 | Summary severe regression. Wrong narrator in plot summary. |
| 18 | 6.8 | +0.25 | No Johnny phantom. Father/son still merged. |
| 19 | 7.7 | +1.15 | Father/son split (Pattern D)! "Dying Uncle Bill" gone. |
| 20 | 5.95 | -0.60 | **SEVERE REGRESSION.** Father/son split didn't fire. "American, sir" false char. Narrator wrong. External config change may be factor. |

## Fix History
- Attempt 11-19: See previous entries (preserved from prior evaluations)
- Attempt 20:
  1. Cross-alias contamination in STEP 3.95 — mutual alias decontamination after split
     - Modified: `src/agents/characters.py` — STEP 3.95
     - Result: **UNTESTABLE** — STEP 3.95 didn't fire, so decontamination code never ran
  2. force_parenthetical_relationship_labels() base-name lookup fallback
     - Modified: `src/pipeline/character_profiling/post_corrections.py`
     - Result: **UNTESTABLE** — no parenthetical characters exist, so function never fired

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 2 | Wrong narrator | `narrator.py` | Fixed |
| 3 | Johnny exact_firstname guard | `characters.py` | REGRESSION — REVERTED |
| 4 | Co-present guard Step 5.4.5 | `characters.py` | Partial |
| 5 | Narrator guard / merge direction | `characters.py`, `narrator.py` | Bug/wrong direction |
| 6 | narrator.py detect() crash | `narrator.py` | Fixed |
| 7 | John Donaldson false narrator | `narrator.py` | Fixed |
| 8 | Role assignment / summaries | `characters.py`, `summarizer.py` | Fixed |
| 9 | Cross-character alias / relationships | `main_cast.py`, `analyzer.py` | Partial |
| 11 | STEP 3.95 / relationships / narrator | `characters.py`, `post_corrections.py`, `analyzer.py` | Mixed |
| 12 | STEP 3.95 alias contradiction | `characters.py` | Fixed |
| 13 | force_parenthetical / narrator_instruction | `post_corrections.py`, `generator.py` | Never fired |
| 14 | STEP 3.97 nickname phantom | `characters.py` | Fixed |
| 15 | STEP 5.4.6c / Step 6.6 narrator | `characters.py`, `analyzer.py` | Fixed |
| 16-18 | STEP 3.95/3.95b patterns | `characters.py` | Intermittent |
| 19 | STEP 3.95b Pattern D / narrator survival | `characters.py`, `generator.py` | Fixed |
| 20 | Cross-alias decontamination / parenthetical rel labels | `characters.py`, `post_corrections.py` | UNTESTABLE (split didn't fire) |

**Pattern: STEP 3.95/3.95b fires ~50% of the time due to LLM non-determinism in summary wording. This is the core instability.**

## Configuration Notes
- External commit 90b62a5 changed LLM config: max_tokens 4096→8192, context_length 65536→32768, fixed config mutation bug
- These changes were NOT reflected in the current output (analysis ran before config commit)
- Model: qwen3.5:122b-a10b for chars/summaries/profiles, qwen3.5:35b-a3b for structure/pronunciation

## Next Action
**RE-ANALYZE FIRST.** External config changes (commit 90b62a5) must be tested before applying more code fixes. Run the analysis phase again with the new config to see if:
1. Father/son split fires with new config
2. "the American, sir" false character is eliminated
3. Narrator assignment improves

If the re-analysis still shows the same issues, THEN apply code fixes targeting the root instability: STEP 3.95b's dependence on specific LLM summary wording.
