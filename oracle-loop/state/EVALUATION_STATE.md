# Current Evaluation State

## Active Text
- **Name:** i_have_no_mouth
- **Attempt:** 2
- **Phase:** awaiting_analysis
- **baseline_score:** 6.35

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 6/10 ✗ (FAILING)
  - Completeness: 8/10
  - Identity Resolution: 5/10
  - Alias Grouping: 7/10
- Character Profiles: 6/10 ✗ (FAILING)
- Chapter Summaries: 8/10 ✓
- Pronunciation Guide: 7/10 ✗ (FAILING)
- HTML Presentation: 8/10 ✓
- **Overall: 7.3/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.35 | 0 | Baseline - duplicate Benny, wrong narrator, profile errors |
| 2 | 7.3 | +0.95 | Benny dedup fixed, narrator=Ted, but duplicate Ted appeared, profiles improved |

## Current Issues (Priority Order)

### CRITICAL
1. **Duplicate "Ted" character (false split)** [Identity Resolution]
   - Problem: main_cast_1 (Ted, narrator=True, role=protagonist) and main_cast_6 (Ted, narrator=False, role=minor) are both present. The exact-name dedup (Pass -1) fixed Benny but a second Ted was created, likely by the vocative narrator promotion logic (STEP 5.8.5b) which promoted Ted from supporting_cast while a Ted already existed in main_cast from the extraction pipeline.
   - Evidence: 7 characters total, two named "Ted" with identical 5 mentions each
   - Location: `src/agents/characters.py` — the vocative narrator promotion (STEP 5.8.5b) likely creates a new main_cast entry without checking if the name already exists in main_cast. Alternatively, Pass -1 dedup runs before the promotion step and doesn't get a second chance.
   - Fix: Either (a) the narrator promotion step should check if a character with the same name already exists in main_cast and merge into it rather than creating a new entry, or (b) run exact-name dedup AGAIN after narrator promotion (after STEP 5.8.6). Option (a) is cleaner.

### HIGH
2. **AM labeled as "protagonist" — should be antagonist** [Profiles]
   - Problem: AM's role is "protagonist" but AM is the malevolent supercomputer antagonist who destroyed humanity and tortures the survivors
   - Evidence: AM's own relationships correctly say "tormentor" for the humans — the profiler knows AM torments them but still labels role as "protagonist"
   - Location: `src/analyzer.py` (`_generate_character_profile()`) — role assignment
   - Fix: The role assignment logic should detect antagonist patterns. When a character's relationships are predominantly "tormentor"/"captor" toward other characters, role should be "antagonist" not "protagonist". This is a generic rule, not novel-specific.

3. **"creator" relationship label used for AM by humans** [Profiles]
   - Problem: Gorrister, Nimdok, and Ted all list AM as their "creator". AM did not create them — it captured/imprisoned them. AM created their torment, not the humans themselves.
   - Evidence: AM is a supercomputer that gained sentience and wiped out humanity, keeping 5 survivors as prisoners to torture forever
   - Location: `src/analyzer.py` relationship generation — the LLM is confusing AM's godlike power over them with literal creation
   - Fix: This is an LLM interpretation issue. The relationship vocabulary may not include "captor" or "prisoner". Check if the allowed relationship labels include appropriate adversarial terms. If not, add them.

4. **Ted has self-relationship "Ted: colleague"** [Profiles]
   - Problem: main_cast_1 Ted lists "Ted: colleague" — a character referencing itself
   - Evidence: This is an artifact of the duplicate Ted — the profiler sees two Teds and creates a relationship between them
   - Location: Self-relationships should be filtered in profile generation or post-processing
   - Fix: Fixing duplicate Ted (#1) should resolve this. As a safety net, add a generic filter that removes self-relationships (where relationship key == canonical_name).

### MEDIUM
5. **Pronunciation false positives for common English words** [Pronunciation]
   - Problem: "sentience", "sentient", "loonie", "piteously", "gibbered", "despond", "sonorities" are standard English words that don't need pronunciation guidance for a professional narrator
   - Evidence: These are all in standard dictionaries and commonly encountered
   - Location: `src/pipeline/pronunciation/cmu_proposer.py` — COMMON_WORDS_WHITELIST
   - Fix: Add these words (and their inflected forms) to COMMON_WORDS_WHITELIST

6. **Most characters lack physical descriptions** [Profiles]
   - Problem: Only 3/7 characters have physical_description (Ellen, Gorrister, Benny). AM, Ted, and Nimdok have null.
   - Evidence: Ted describes himself as paranoid and the others describe physical changes AM made. AM manifests as pillars of light, computer banks, etc. Nimdok is less described but the text mentions AM altered all of them.
   - Severity: Medium — the text is sparse on physical descriptions for some characters; null is acceptable when text doesn't provide details
   - Location: `src/analyzer.py` profile generation
   - Fix: Minor — the profiler should extract what's available but null is acceptable for genuinely undescribed characters

7. **Ellen's relationship "Gorrister: recipient of his abuse" is incorrect** [Profiles]
   - Problem: Gorrister does not abuse Ellen in the text. This appears to be a hallucinated relationship.
   - Evidence: In the story, Gorrister is a passive, depressive character. There's no textual basis for him abusing Ellen.
   - Location: Profile generation LLM hallucination
   - Fix: LLM temperature or prompt refinement — but this is a single-instance error, not systemic

### LOW
8. **Chapter title is null** [Structure]
   - Problem: Single section has `title: null` — could display the story title
   - Not blocking — single-section detection is correct

## What Improved from Attempt 1
- Benny duplicate FIXED (was main_cast_1 + main_cast_5, now single main_cast_5) ✓
- Ted identified as narrator ✓ (was Benny in attempt 1)
- Gorrister's physical description now correct (was Benny's blinding description in attempt 1) ✓
- AM's relationships improved — "tormentor" labels now correct (was "victim"/"colleague" in attempt 1) ✓
- Summary now attributes narrator actions to "the narrator" not "Benny" ✓
- cogito IPA fixed ✓
- Several pronunciation false positives removed ✓

## What Regressed from Attempt 1
- New duplicate Ted appeared (main_cast_1 + main_cast_6) — likely from vocative narrator promotion creating a new entry

## Fix History
- Attempt 2: Three connected fixes for character extraction and pronunciation
  1. **Exact-name dedup in `_merge_within_main_cast`** (`src/agents/characters.py` Pass -1)
     - Root cause: `_merge_within_main_cast` Pass 1 skips single-word vs single-word comparisons; Pass 2 should catch it but apparently doesn't when both entries have equal mention counts and the `break` at the else branch prevents second character from being processed again. Added explicit Pass -1 that collapses any two characters with identical canonical names before all other merge passes.
     - Addresses: Critical #1 (duplicate Benny) — FIXED
  2. **Vocative pattern + narrator fallback** (`src/agents/characters.py`)
     - Extended `_find_narrator_name_from_vocative` to also detect `, Name,` patterns (comma-delimited vocative address, e.g., "Please, Ted, let's try it"). Original pattern only matched `, Name!` / `, Name?`.
     - Added STEP 4.5b: when pov=first-person AND narrator_character_id is None AND narrator_name is None, run vocative detection to set narrator_name. This allows STEP 5.8.5b to find the narrator in supporting_cast and promote them.
     - Addresses: Critical #2 (wrong narrator) — FIXED, but introduced duplicate Ted regression
  3. **Pronunciation fixes** (`cmu_proposer.py`, `enricher.py`)
     - Added stalactite(s), palette, tinfoil, eternity/eternities, choir, shoal, puckering(s) to COMMON_WORDS_WHITELIST
     - Added "cogito" to KNOWN_IRREGULAR_IPA
     - Addresses: Medium #9 (false positives) — PARTIALLY FIXED (more remain), Medium #10 (cogito IPA) — FIXED

## Fix History (Attempt 3)
1. **Duplicate Ted — STEP 5.8.5b now checks for existing main_cast entry** (`src/agents/characters.py`)
   - Root cause: STEP 5.8.5b appended `merged_narrator` to main_cast without checking if a character with the same name was already there (the LLM had extracted Ted in Pass 1; supporting cast also had a Ted fragment; promotion created a second entry after Pass -1 dedup already ran).
   - Fix: Before appending, search main_cast for a character with matching canonical_name. If found, update is_narrator/narrative_role/mention_count on the existing entry; skip append.
   - Universal invariant: "no two main_cast characters with the same name" applied at promotion time.

2. **AM role protagonist→antagonist via post-profile correction** (`src/analyzer.py`)
   - Root cause: Pass 1 LLM labeled AM "protagonist" (highest mentions, narrative driver). Post-profile relationships correctly showed "tormentor" labels but role was never corrected.
   - Fix: After `corrector.run_all()`, added a universal post-processing pass: non-narrator "protagonist" characters whose outgoing relationships are ≥50% adversarial labels → role="antagonist". Small reference set of unambiguously adversarial labels (tormentor, captor, oppressor, etc.).

3. **Relationship vocabulary expanded** (`src/analyzer.py`)
   - Added "captor", "prisoner", "tormentor", "victim" to the example label list in profile generation prompt.
   - Gives LLM better vocabulary so it uses "captor" instead of "creator" for power/confinement relationships.

4. **Pronunciation whitelist additions** (`cmu_proposer.py`)
   - Added: sentience, sentient, loonie/loonies, piteously, gibbered/gibbering, despond/despondency, sonority/sonorities

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 2 | Dup Benny | characters.py (Pass -1 dedup) | Fixed |
| 2 | Wrong narrator | characters.py (vocative + STEP 4.5b) | Fixed but introduced dup Ted |
| 2 | Pronunciation FPs | cmu_proposer.py, enricher.py | Partially fixed |
| 3 | Dup Ted | characters.py (STEP 5.8.5b same-name guard) | Pending |
| 3 | AM wrong role | analyzer.py (post-profile adversarial role correction) | Pending |
| 3 | Relationship vocab | analyzer.py (captor/prisoner/tormentor/victim labels) | Pending |
| 3 | Pronunciation FPs | cmu_proposer.py (7 more words whitelisted) | Pending |

## Next Action (Attempt 3)
Re-run analysis to verify:
1. Duplicate Ted resolved (expect 6 characters, one Ted as narrator)
2. AM labeled "antagonist" (via post-profile adversarial-relationship detection)
3. Fewer pronunciation false positives

**Phase:** awaiting_analysis

## Output Files
- HTML: ../output/i_have_no_mouth/report.html
- JSON: ../output/i_have_no_mouth/analysis.json

## Pipeline Notes
- Attempt 2 analysis completed successfully in 22m 21s
- Model: qwen3-next:80b-a3b-instruct-q8_0 (all agents)
- Competitive mode: none (baseline behavior)
- Ted detected as narrator (first-person) — vocative fix worked
- 7 characters extracted (was 9 in attempt 1, 8 after Benny dedup but now +1 from Ted duplicate)
- AM: 77 mentions, Benny: 35, Ellen: 30, Gorrister: 29, Nimdok: 17, Ted: 5+5
