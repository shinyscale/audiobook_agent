# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 13
- **Phase:** awaiting_evaluation
- **baseline_score:** 6.55
- **Competitive Mode:** none

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 8/10 ✓
  - Completeness: 8/10
  - Identity Resolution: 8.5/10
  - Alias Grouping: 7.5/10
- Character Profiles: 5.5/10 ✗ (FAILING — wrong relationships, missing relationships, hallucinated age)
- Chapter Summaries: 7/10 ✗ (FAILING — plot summary misattributes flashback to Uncle Bill)
- Pronunciation Guide: 8.5/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 7.7/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold)

## What Attempt 12 Changed vs Attempt 11

**MAJOR IMPROVEMENT:**
- **Father/son SPLIT WORKED!** — STEP 3.95 alias contradiction detection fired correctly. Now two separate characters:
  - "John Donaldson" (id=main_cast_1, 32 mentions, aliases: ['son', 'John', 'young John']) — the son
  - "John Donaldson (his father)" (id=main_cast_1_parent, 12 mentions, aliases: ['his father', 'John Donaldson']) — the father
- **Uncle Bill still narrator** ✓
- **5 characters total** — Uncle Bill, John Donaldson (son), John Donaldson (his father), Joe Barron, Ted Frith

**PERSISTENT/NEW FAILURES:**
- **Relationships ALL WRONG** — Father↔Son labeled "brother" instead of "father"/"son". Uncle Bill has ZERO relationships. This is the primary blocker.
- **Plot summary factual error** — Says "a young Uncle Bill, driving a transport vehicle near the Piave River" and "the volunteer is actually Uncle Bill's long-lost father". WRONG: The boy (young John) was the ambulance driver who encountered HIS father in Italy, not Uncle Bill.
- **Ted Frith age "two years old"** hallucination persists
- **Father's physical description** has beauty traits ("physical beauty", "charm", "alluring, sidewise smile") that seem copied/shared with the son's — the father's appearance should be distinct

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

## Current Issues (Priority Order)

### CRITICAL

1. **Father↔Son relationship labeled "brother" instead of "father"/"son"** [Profiles]
   - Problem: `John Donaldson → John Donaldson (his father) = "brother"` and vice versa. Should be "son" and "father" respectively.
   - Evidence: The characters are explicitly father and son. The canonical names even contain "(his father)".
   - Root cause: The profiler LLM is confused by two characters with the same base name "John Donaldson". Despite the disambiguating "(his father)" suffix, it labels the relationship "brother" — likely because same-name = same generation in the LLM's heuristic.
   - Location: `src/analyzer.py` — `_generate_character_profile()` or `src/pipeline/character_profiling/post_corrections.py`
   - Fix approach: Post-correction in `post_corrections.py` — if a character's canonical name contains "(his/her/their father/mother/son/daughter)", force the relationship label to match. E.g., if character B is "X (his father)", then A→B should be "father" and B→A should be "son".

2. **Plot summary says "a young Uncle Bill" encountered the father — should be the boy** [Summaries]
   - Problem: Plot summary states "The narrative shifts into a flashback where a young Uncle Bill, driving a transport vehicle" and "the volunteer is actually Uncle Bill's long-lost father". WRONG — the boy (young John) was the ambulance driver in Italy who encountered HIS father.
   - Evidence: Uncle Bill is elderly, goes to the pier to meet the boy. The boy tells Uncle Bill about his wartime experience of finding his father.
   - Root cause: The plot summary consolidation LLM confuses the frame narrator (Uncle Bill) with the embedded narrator (the boy telling his story). The chapter summary uses "a young narrator" which is ambiguous — the consolidation LLM then attributes this to Uncle Bill.
   - Location: `src/pipeline/summarization/summarizer.py` — plot summary consolidation prompt
   - Fix approach: The chapter summary's "young narrator" phrasing is the root cause. If the chapter summary correctly said "young John" or "the boy" instead of "young narrator", the plot summary would not confuse the identity. Fix the chapter summary's nested-narration handling to name the embedded narrator properly.

### HIGH

3. **Uncle Bill has ZERO relationships** [Profiles]
   - Problem: Uncle Bill (narrator, main character) has `relationships: {}`. Should have: guardian/family friend of both John Donaldsons, close friend of Ted Frith.
   - Evidence: Uncle Bill is the frame narrator who knew the father, raised the boy, and has a close friend Ted Frith.
   - Location: `src/analyzer.py` — `_generate_character_profile()`
   - Fix: May partially resolve when CRITICAL #1 is fixed (once father/son relationships are correct, the profiler can better infer Uncle Bill's relationships). If not, the profiler prompt may need guidance about frame narrators having relationships with the characters they narrate about.

4. **Ted Frith age "two years old" hallucination** [Profiles]
   - Problem: `appearance.age_indication: "two years old"` — completely fabricated. Ted Frith has no age indication in the text.
   - Evidence: Ted Frith is Uncle Bill's adult companion.
   - Location: `src/analyzer.py` — profile generation, age parsing
   - Fix: Add validation rejecting implausibly young ages (< 5) unless the character is explicitly an infant/toddler. Or improve the prompt to distinguish age from time durations mentioned near a character's name.

### MEDIUM

5. **Father's physical description duplicates son's traits** [Profiles]
   - Problem: Father has "physical beauty", "charm", "alluring, sidewise smile" — these are the SON's features as described in the text. The father is described differently (shabbily dressed, wounded).
   - Root cause: The split operation may have copied appearance data from the merged character to both split halves.
   - Location: STEP 3.95 in `src/agents/characters.py` — how it handles appearance data during split
   - Fix: Clear or reset appearance fields on the split-off parent character, let the profiler regenerate them.

6. **Missing Margaret Donaldson** [Completeness]
   - Problem: Margaret Donaldson (the boy's mother, mentioned in text) is not in the character list.
   - Impact: Minor — she's a referenced-only character.

7. **Missing "Johnny" nickname** [Alias Grouping]
   - Problem: The text uses "Johnny" as a nickname for the son, but it's not in aliases.
   - Impact: Minor polish.

## Fix Strategy for Attempt 13 — APPLIED

**Priority 1 DONE: Force father/son relationship labels via post-correction.**
- Added `force_parenthetical_relationship_labels()` to `OutputCharacterCorrector` in `post_corrections.py`
- Detects characters whose canonical_name matches `{base} (his/her/their/the {rel_term})`
- Forces: this_char → base_char = rel_term; base_char → this_char = RELATIONSHIP_REVERSES[rel_term]
- Runs after `verify_relationships_from_text`, before `fix_bidirectional_parent_labels`
- Universal: any book using parenthetical disambiguation benefits

**Priority 2 DONE: Fix the plot summary misattribution.**
- Changed `narrator_instruction` in `generator.py:_generate_plot_summary()` from:
  `"Refer to the narrator by their name ({name}) rather than 'the narrator'"`
  to:
  `"{name} is the FRAME narrator who tells the overall story. When chapter summaries describe an embedded flashback, oral account, or story-within-a-story told by a DIFFERENT character to {name}, attribute those embedded events to THAT other character — not to {name}."`
- Universal: applies to any nested narrative (frame narrator + embedded storyteller)

**Do NOT touch (working correctly):**
- STEP 3.95 alias contradiction detection (father/son split ✓)
- Narrator detection (Uncle Bill = narrator ✓)
- Relationship cleanup ("close friend" in Ted Frith ✓)
- Pronunciation pipeline
- Structure detection

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
  2. `narrator_instruction` in `generator.py:_generate_plot_summary()`
     - Modified: `src/pipeline/overview/generator.py`
     - Logic: clarifies that named narrator is FRAME narrator; embedded story events belong to the embedded character

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

**Pattern:** Characters pipeline is now stable. Remaining issues are in profiling (relationships) and summarization (plot summary). Focus fixes on `post_corrections.py` and `summarizer.py`/`generator.py`.

## Configuration Notes
- Model config appropriate: qwen3.5:122b-a10b for characters/summaries/profiles, qwen3.5:35b-a3b for structure/pronunciation
- Zero LLM retries across all stages
- All 14 pronunciations have IPA
- Narrator detection from V2 pipeline: working ✓

## Pipeline Notes (Attempt 13)
- Analysis completed in 13m 23s
- **WARNING: Possible regressions vs attempt 12:**
  - Narrator detected as "Johnny" (2 mentions) — should be "Uncle Bill"
  - No "John Donaldson (his father)" visible in output — father/son split may not have fired
  - "Final narrator appearance injection" applied Uncle Bill's appearance to both "Johnny" AND "John Donaldson"
- Characters found: Johnny (2), John Donaldson (43), Uncle Bill (18), Joe Barron (3), Ted Frith (5)
- Margaret Donaldson added via F6b ✓

## Next Action
Evaluate attempt 13 output — check for regressions on narrator and father/son split.
