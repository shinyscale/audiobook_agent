# Current Evaluation State

## Active Text
- **Name:** i_have_no_mouth
- **Attempt:** 4
- **Phase:** awaiting_fix
- **baseline_score:** 6.35

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 6/10 ✗ (FAILING)
  - Completeness: 9/10
  - Identity Resolution: 4/10
  - Alias Grouping: 7/10
- Character Profiles: 6.5/10 ✗ (FAILING)
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 8.5/10 ✓
- HTML Presentation: 8/10 ✓
- **Overall: 7.6/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.35 | 0 | Baseline - duplicate Benny, wrong narrator, profile errors |
| 2 | 7.3 | +0.95 | Benny dedup fixed, narrator=Ted, but duplicate Ted appeared, profiles improved |
| 3 | 7.8 | +1.45 | Relationship vocab improved, pronunciation fixed, but duplicate Ted and AM role fixes didn't work |
| 4 | 7.6 | +1.25 | Fixes did NOT take effect — duplicate Ted persists, AM still "protagonist" |

## Current Issues (Priority Order)

### CRITICAL
1. **Duplicate "Ted" — STEP 5.8 dedup fix targeted WRONG mechanism (again)** [Identity Resolution]
   - Problem: Two Ted entries exist: main_cast_5 (role=main, narrator=False, mentions=5) and main_cast_7 (role=protagonist, narrator=True, mentions=5)
   - Root cause analysis: Both have `main_cast_*` IDs. main_cast_5 is from normal extraction. main_cast_7 is created by the **narrator heuristic fallback** (STEP 5.8.6), which creates a NEW main_cast entry when it detects first-person narration but `narrator_character_id is None`. The attempt 4 fix guarded STEP 5.8 *supporting cast promotion*, but the duplicate comes from STEP 5.8.6 *narrator creation*.
   - **The fix must target STEP 5.8.6**: Before creating a new narrator entry, check if a character with that name already exists in main_cast. If so, set `is_narrator=True` and `role="protagonist"` on the existing entry instead of creating a new one.
   - Location: `src/agents/characters.py` — search for STEP 5.8.6 or the narrator fallback heuristic
   - Evidence: main_cast_5 has `narrator=False, role=main`; main_cast_7 has `narrator=True, role=protagonist` — classic pattern of narrator fallback creating a duplicate

2. **AM still labeled "protagonist" — adversarial role correction cannot fire** [Profiles]
   - Problem: AM's relationships are: Ted→captor, Ellen→colleague, Nimdok→colleague, Gorrister→colleague, Benny→colleague. Only 1/5 labels is adversarial ("captor"); the other 4 are "colleague".
   - Root cause: The adversarial role correction in `src/analyzer.py` checks outgoing relationship labels. With 4/5 labels being "colleague" (not in `_ADVERSARIAL_LABELS`), the threshold for antagonist relabeling is not met.
   - **The real problem is upstream**: The LLM is generating "colleague" as a default for AM's relationships with the humans. AM is their **captor/tormentor**, not colleague. The relationship generation prompt needs to better distinguish captor-prisoner dynamics from peer relationships.
   - Two-part fix needed:
     a. In the adversarial role correction, also check if a character's INCOMING labels from others include adversarial terms (Ted→AM: "tormentor", implying AM is an antagonist)
     b. Consider adding "colleague" blocklist logic: if a character has ANY adversarial outgoing label (captor), "colleague" labels to the same group of characters are suspicious

### HIGH
3. **Nimdok incorrectly labeled "antagonist"** [Profiles]
   - Problem: Nimdok is one of the five human victims, not an antagonist. He should be "protagonist" like the other humans.
   - Evidence: Nimdok's relationships are all "fellow victim" and "colleague" — nothing antagonistic
   - Location: Role assignment logic in character extraction or profiling
   - Likely cause: LLM misclassification, possibly because Nimdok's name sounds sinister or because the text hints at his Nazi past

4. **Pervasive "colleague" relationship label is incorrect** [Profiles]
   - Problem: "colleague" appears in 12 of ~25 relationship entries. AM-to-humans as "colleague" is wrong (should be captor/victim/tormentor). Human-to-AM as "colleague" is wrong. Even human-to-human would be better as "fellow prisoner" or "companion".
   - Evidence: AM→Ellen: colleague, AM→Nimdok: colleague, AM→Gorrister: colleague, AM→Benny: colleague, Ellen→AM: colleague, Nimdok→AM: colleague, etc.
   - Location: Profile generation in `src/analyzer.py` — `_generate_character_profile()` relationship vocabulary
   - Fix: The relationship vocab expansion from attempt 3 added captor/tormentor/victim terms but the LLM is still defaulting to "colleague". May need to exclude "colleague" from valid labels or add negative guidance: "Do not use 'colleague' for captor-prisoner or torturer-victim relationships"

### MEDIUM
5. **AM has self-alias "AM"** [Alias Grouping]
   - Problem: AM's alias list is `["AM"]` — the canonical name appears as its own alias
   - Location: Alias extraction or post-processing
   - Fix: Filter self-aliases where alias == canonical_name

6. **Ellen's relationship "Gorrister: abuser" is incorrect** [Profiles]
   - Problem: Gorrister does not abuse Ellen in the text. This is hallucinated.
   - Severity: Medium — single incorrect relationship label

7. **AM evidence says "AM is the creator and tormentor of the five humans"** [Profiles]
   - Problem: AM did not create the humans — it captured/imprisoned them
   - Location: Evidence generation in profile pipeline

### LOW
8. **Chapter title is null** [Structure]
   - Problem: Single section has `title: null` — could display the story title
   - Not blocking — single-section detection is correct

9. **Themes listed as "identity, ambition, loss"** [Summaries]
   - Problem: While not entirely wrong, better themes would be: suffering, technology/AI, humanity, free will, cruelty
   - Severity: Low — themes are supplementary information

## Fix History
- Attempt 2: Three connected fixes for character extraction and pronunciation
  1. **Exact-name dedup in `_merge_within_main_cast`** (`src/agents/characters.py` Pass -1) — Fixed Benny duplicate
  2. **Vocative pattern + narrator fallback** (`src/agents/characters.py`) — Fixed narrator detection but introduced duplicate Ted
  3. **Pronunciation fixes** (`cmu_proposer.py`, `enricher.py`) — Partially fixed false positives

- Attempt 3: Four fixes (two didn't take effect)
  1. **STEP 5.8.5b same-name guard** (`src/agents/characters.py`) — Code is correct but targets wrong path; duplicate Ted comes from STEP 5.8 general promotion → WRONG, actually comes from STEP 5.8.6
  2. **Post-profile adversarial role correction** (`src/analyzer.py`) — Code is correct but `_ADVERSARIAL_LABELS` doesn't include "victim"
  3. **Relationship vocabulary expanded** (`src/analyzer.py`) — WORKED: but LLM still uses "colleague" as fallback
  4. **Pronunciation whitelist additions** (`cmu_proposer.py`) — WORKED

- Attempt 4: Three fixes — **NONE took effect on the actual problem**
  1. **STEP 5.8 same-name dedup** (`src/agents/characters.py:1476-1494`) — Targeted supporting→main promotion, but duplicate Ted comes from STEP 5.8.6 narrator fallback
  2. **"victim" added to `_ADVERSARIAL_LABELS`** (`src/analyzer.py:2134`) — Correct addition, but AM's outgoing labels are mostly "colleague" not "victim", so threshold not met
  3. **Self-relationship filter** (`src/analyzer.py`) — May have worked (no self-relationships visible), but didn't address core issues

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 2 | Dup Benny | characters.py (Pass -1 dedup) | Fixed |
| 2 | Wrong narrator | characters.py (vocative + STEP 4.5b) | Fixed but introduced dup Ted |
| 2 | Pronunciation FPs | cmu_proposer.py, enricher.py | Partially fixed |
| 3 | Dup Ted | characters.py (STEP 5.8.5b same-name guard) | No change — wrong code path |
| 3 | AM wrong role | analyzer.py (post-profile adversarial role correction) | No change — "victim" not in label set |
| 3 | Relationship vocab | analyzer.py (captor/prisoner/tormentor/victim labels) | Fixed vocab but LLM ignores it |
| 3 | Pronunciation FPs | cmu_proposer.py (7 more words whitelisted) | Fixed |
| 4 | Dup Ted | characters.py (STEP 5.8 promotion dedup) | No change — wrong code path AGAIN |
| 4 | AM wrong role | analyzer.py ("victim" in _ADVERSARIAL_LABELS) | No change — AM labels are "colleague" not "victim" |
| 4 | Self-relationship | analyzer.py (post-profile filter) | Likely worked (no self-rels visible) |

**ESCALATION WARNING:** Duplicate Ted has been attempted 3 times (attempts 2, 3, 4) without success. Each attempt targeted a different code path but missed the actual source (STEP 5.8.6 narrator fallback). The fix phase MUST:
1. Read STEP 5.8.6 code carefully to find the narrator creation logic
2. Add a same-name check BEFORE creating a new main_cast entry
3. Verify with grep that no other code path also creates narrator entries

**ESCALATION WARNING:** AM role has been attempted 2 times (attempts 3, 4). The adversarial label approach cannot work because the LLM generates "colleague" labels. The fix phase should consider:
1. A simpler heuristic: if OTHER characters label this character as "tormentor"/"captor", it's an antagonist (check incoming labels, not just outgoing)
2. OR: post-profile role override based on incoming relationship evidence

## Next Action
Run PROMPT_fix.md. Priority: (1) Fix duplicate Ted by targeting STEP 5.8.6 narrator fallback, (2) Fix AM role by checking incoming adversarial labels, (3) Fix Nimdok role.

## Output Files
- HTML: ../output/i_have_no_mouth/report.html
- JSON: ../output/i_have_no_mouth/analysis.json

## Pipeline Notes
- Attempt 4 analysis completed successfully in 20m 40s
- Model: qwen3-next:80b-a3b-instruct-q8_0 (all agents)
- Competitive mode: none (baseline behavior)
- Ted detected as narrator (first-person)
- 7 characters in JSON, 6 displayed in HTML (role="main" Ted excluded from display?)
- 16 pronunciation flags, all with IPA
- Self-relationship filter appears to have worked
- "colleague" relationship label is pervasive and masking the adversarial role correction
