# Current Evaluation State

## Active Text
- **Name:** i_have_no_mouth
- **Attempt:** 1
- **Phase:** awaiting_analysis
- **baseline_score:** 6.35

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 5/10 ✗ (FAILING)
  - Completeness: 7/10
  - Identity Resolution: 4/10
  - Alias Grouping: 8/10
- Character Profiles: 4/10 ✗ (FAILING)
- Chapter Summaries: 6/10 ✗ (FAILING)
- Pronunciation Guide: 7/10 ✗ (FAILING)
- HTML Presentation: 8/10 ✓
- **Overall: 6.35/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (4 categories below threshold)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.35 | 0 | Baseline - duplicate Benny, wrong narrator, profile errors |

## Current Issues (Priority Order)

### CRITICAL
1. **Duplicate "Benny" character (false split)** [Identity Resolution]
   - Problem: main_cast_1 and main_cast_5 are BOTH "Benny" with 35 mentions each. One is incorrectly marked as narrator.
   - Evidence: There is only ONE Benny in the story. The V2 pipeline created two identical entries.
   - Location: `src/pipeline/character_extraction_v2/` — deduplication logic failing to merge same-name characters
   - Fix: The pipeline should detect and merge characters with identical canonical names

2. **Wrong narrator identification — Benny marked as narrator instead of Ted** [Identity Resolution]
   - Problem: Benny (main_cast_1) is marked `is_narrator: True`. The actual narrator is Ted, who tells the story in first person.
   - Evidence: The story opens "Limp, the body of Gorrister hung from the pink palette..." narrated by Ted in first person. Ted says "I" throughout.
   - Location: Narrator detection logic — likely `src/agents/characters.py` (STEP 5.8.6 heuristic narrator fallback) or `src/pipeline/character_extraction_v2/`
   - Fix: Ted should be identified as narrator. The narrator detection may be assigning the wrong character because Ted has low explicit mention count (5) since he uses "I".

3. **Ted demoted to supporting cast** [Completeness]
   - Problem: Ted (the first-person narrator and protagonist) has only 5 mentions and is in supporting_cast. He should be the most important character.
   - Evidence: Ted narrates the entire story. His low mention count is because he uses "I" instead of his name. He's the one who kills the others at the climax and is transformed by AM.
   - Location: `src/pipeline/character_extraction_v2/` — first-person narrators with low self-mention counts get misclassified
   - Fix: Narrator characters should be promoted to main_cast regardless of mention count. This connects to issue #2.

### HIGH
4. **AM labeled as "protagonist" — should be antagonist** [Profiles]
   - Problem: AM's role is "protagonist" but AM is the malevolent supercomputer antagonist
   - Evidence: AM tortures the five survivors, destroys humanity, and transforms Ted into a blob as punishment
   - Location: Profile generation in `src/analyzer.py` (`_generate_character_profile()`)
   - Fix: Role assignment logic should detect antagonist patterns (torture, punishment, opposition to narrator)

5. **Gorrister's physical description is wrong — has Benny's description** [Profiles]
   - Problem: Gorrister's profile says "after being blinded by AM, his eyes become 'two soft, moist pools of pus-like jelly'" — this happened to BENNY, not Gorrister
   - Evidence: In the text, AM blinds Benny as punishment for trying to escape. Gorrister has a "lantern jaw" but is not blinded.
   - Location: Profile generation — LLM conflated characters, possibly due to duplicate Benny confusing context
   - Fix: Fixing duplicate Benny (#1) should reduce profile confusion. The profiler may also need stronger character isolation.

6. **Relationship labels wrong for AM** [Profiles]
   - Problem: AM's relationship to humans listed as "victim" (to Benny/Ellen/Nimdok/Gorrister) and "colleague" (to Ted). AM is their CAPTOR/TORTURER, not their victim or colleague.
   - Evidence: AM keeps them alive to torture them forever. "Colleague" is absurd for a god-machine vs. its prisoners.
   - Location: `src/analyzer.py` relationship generation, possibly `src/pipeline/post_corrections.py`
   - Fix: May be a label vocabulary issue — "captor", "torturer", "antagonist" may not be in allowed labels

7. **Plot summary attributes narrator actions to Benny** [Summaries]
   - Problem: The plot summary says "Benny realizes death is the only escape" and "Benny kills Gorrister, Ellen, and Nimdok" — this is TED, not Benny
   - Evidence: Ted is the narrator who kills the others and is transformed. This error cascades from the wrong narrator identification (#2).
   - Location: Summary generation uses narrator identity; fixing #2 should cascade to fix this
   - Fix: Depends on fixing narrator identification first

8. **Benny has self-relationship "Benny: colleague"** [Profiles]
   - Problem: Both Benny entries list a relationship to themselves
   - Evidence: A character cannot have a relationship with itself — artifact of the duplicate
   - Location: Deduplication/profile generation
   - Fix: Fixing duplicate Benny (#1) resolves this

### MEDIUM
9. **Pronunciation false positives for common English words** [Pronunciation]
   - Problem: "stalactites", "palette", "puckerings", "tinfoil", "eternities", "choir", "shoal" are all standard English words that don't need pronunciation guidance
   - Evidence: These are common enough that any narrator would know them
   - Location: `src/pipeline/pronunciation/cmu_proposer.py` — COMMON_WORDS_WHITELIST
   - Fix: Add these words to COMMON_WORDS_WHITELIST

10. **"cogito" IPA is wrong** [Pronunciation]
    - Problem: Listed as /kəˈdʒiːtoʊ/ (soft g, "ko-JEE-toh"). Should be /ˈkɒɡɪtoʊ/ (hard g, "KOG-ih-toh") — Latin word from "cogito ergo sum"
    - Evidence: Standard Latin pronunciation uses hard g
    - Location: LLM-generated IPA in `src/pipeline/pronunciation/enricher.py`
    - Fix: Add "cogito" to KNOWN_IRREGULAR_IPA with correct pronunciation

11. **Themes are weak** [Profiles]
    - Problem: Themes listed as "identity, ambition, loss" — doesn't capture the story's core
    - Evidence: Better themes: suffering, dehumanization, technology/AI tyranny, mercy killing, revenge
    - Severity: Minor — themes are supplementary information

### LOW
12. **Chapter title is null** [Structure]
    - Problem: Single section has `title: null` — could display the story title instead
    - Not blocking — single-section detection is correct

## Fix History
- Attempt 2: Three connected fixes for character extraction and pronunciation
  1. **Exact-name dedup in `_merge_within_main_cast`** (`src/agents/characters.py` Pass -1)
     - Root cause: `_merge_within_main_cast` Pass 1 skips single-word vs single-word comparisons; Pass 2 should catch it but apparently doesn't when both entries have equal mention counts and the `break` at the else branch prevents second character from being processed again. Added explicit Pass -1 that collapses any two characters with identical canonical names before all other merge passes.
     - Addresses: Critical #1 (duplicate Benny)
  2. **Vocative pattern + narrator fallback** (`src/agents/characters.py`)
     - Extended `_find_narrator_name_from_vocative` to also detect `, Name,` patterns (comma-delimited vocative address, e.g., "Please, Ted, let's try it"). Original pattern only matched `, Name!` / `, Name?`.
     - Added STEP 4.5b: when pov=first-person AND narrator_character_id is None AND narrator_name is None, run vocative detection to set narrator_name. This allows STEP 5.8.5b to find the narrator in supporting_cast and promote them.
     - Addresses: Critical #2 (wrong narrator), Critical #3 (Ted in supporting cast)
  3. **Pronunciation fixes** (`cmu_proposer.py`, `enricher.py`)
     - Added stalactite(s), palette, tinfoil, eternity/eternities, choir, shoal, puckering(s) to COMMON_WORDS_WHITELIST
     - Added "cogito" → /ˈkɒɡɪtoʊ/ (KOG-ih-toh) to KNOWN_IRREGULAR_IPA
     - Addresses: Medium #9 (false positives), Medium #10 (wrong cogito IPA)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 2 | Dup Benny + narrator + pronunciation | characters.py, cmu_proposer.py, enricher.py | Awaiting analysis |

## Next Action
Re-run analysis on i_have_no_mouth to verify fixes.

## Output Files
- HTML: ../output/i_have_no_mouth/report.html
- JSON: ../output/i_have_no_mouth/analysis.json

## Pipeline Notes
- Analysis completed successfully
- Model: qwen3-next:80b-a3b-instruct-q8_0 (all agents)
- Competitive mode: none (baseline behavior)
