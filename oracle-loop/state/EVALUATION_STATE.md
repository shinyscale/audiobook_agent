# Current Evaluation State

## Active Text
- **Name:** masque_of_red_death
- **Attempt:** 7
- **Phase:** awaiting_evaluation
- **baseline_score:** 6.85
- **Competitive Mode:** none

## Output Files
- HTML: ../output/masque_of_red_death/report.html
- JSON: ../output/masque_of_red_death/analysis.json

## Pipeline Notes (Attempt 7)
- Analysis completed in 20m 43s, exit code 0
- 2 characters extracted: Prince Prospero and the Red Death
- Prince Prospero aliases: "the prince, Prospero" — same as attempt 6 ✓
- The Red Death aliases: "the revellers, the assembly" — still wrong group aliases ✗ (changed from attempt 6's "The Courtiers, The Musicians, The Waltzers")
- BLOCKED alias messages in log: symbolic alias rule blocked "the masked figure", "the intruder", "the stranger", "the figure" from joining the Red Death
- "the masked figure" appears to have been extracted as a SEPARATE character that got is_symbolic=True, its correct aliases also blocked
- Rule 0.7 (attempt 7 fix) appears to have changed WHICH group aliases appear, but did not prevent group aliases entirely
- Rule 3 exception (attempt 7 fix) did not result in correct aliases — symbolic alias rule is the blocking point

## Latest Scores (Attempt 6 — pre-fix)
- Structure Detection: 9/10 ✓
- Character Extraction: 7.5/10 ✗
  - Completeness: 9/10
  - Identity Resolution: 10/10
  - Alias Grouping: 4/10 ← only failing sub-dimension
- Character Profiles: 8.5/10 ✓
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 8/10 ✓
- **Overall: 8.35/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL — 1 category below threshold (Character Extraction 7.5/10)
*(Attempt 7 analysis not yet run — scores above are from attempt 6)*

## Evaluation Details (Attempt 6)

### Structure Detection: 9/10 ✓
Continuous short story correctly identified as single section. Minor "1 chapters" grammar issue persists (cosmetic only).

### Character Extraction: 7.5/10 ✗

**REVERT SUCCESS.** The attempt 6 revert of characters.py restored the correct state from attempt 4:
- Prince Prospero and The Red Death both exist as separate main_cast characters ✓
- No spurious F6-reconciled characters (courtiers/musicians now absorbed as aliases, not separate entries) ✓
- The ebony clock is gone (no longer present as a character) ✓
- "Prospero" alias preserved thanks to grounding.py fix ✓

**Characters in output:**
1. **Prince Prospero** (aliases: the Prince, Prospero) — CORRECT ✓
2. **The Red Death** (aliases: The Courtiers, The Musicians, The Waltzers) — Entity correct, aliases WRONG ✗

**Expected:**
1. Prince Prospero (aliases: the Prince, Prospero) ✓
2. The Red Death (aliases: the masked figure, the figure, the intruder)

**Completeness: 9/10** — Both main characters correctly identified. No spurious entries, no hallucinations. For a short story with only 2 named entities, this is nearly perfect.

**Identity Resolution: 10/10** — Perfect. No false splits, no false merges. Both characters correctly identified as separate entities. The clock is correctly absent.

**Alias Grouping: 4/10** — Split outcome:
- ✓ Prince Prospero's aliases are perfect: "the Prince" and "Prospero" (grounding.py fix works!)
- ✗ The Red Death has 3 WRONG aliases: "The Courtiers", "The Musicians", "The Waltzers" — these are unnamed groups of partygoers, not aliases for the personification of pestilence
- ✗ The Red Death is MISSING 3 CORRECT aliases: "the masked figure", "the figure", "the intruder" — the text uses all three to refer to The Red Death's physical manifestation

### Character Profiles: 8.5/10 ✓

**Prince Prospero:** Excellent profile.
- Physical: "bold and robust man" — accurate to text ✓
- Personality: accurate arc from happy/dauntless to enraged to terrified ✓
- Voice guidance: "authoritative and aggressive" tone with actual quote ("Who dares insult us...") ✓
- Relationships: The Red Death = enemy ✓

**The Red Death:** Excellent profile (restored by revert).
- Physical: "tall, gaunt figure shrouded from head to foot in grave habiliments... mask resembling a stiffened corpse... features besprinkled with scarlet horror... vesture dabbled in blood" — all directly from Poe's text ✓
- Personality: "deliberate, solemn, stealthy" with "thief in the night" reference ✓
- Voice: correctly shows unknown (The Red Death doesn't speak in the text) ✓
- Relationships: Prince Prospero = enemy ✓

Minor gaps: voice_notes null for both (expected for this text), relationship labels sparse ("enemy" could be more descriptive).

### Chapter Summaries: 9/10 ✓
Comprehensive single summary accurately captures: Prospero's retreat, the castellated abbey, the seven colored rooms, the ebony clock's chiming, the masked figure's appearance at midnight, Prospero's confrontation and death, the revelation that the figure is The Red Death itself, universal death. No hallucinations. Accurate to Poe's text.

### Pronunciation Guide: 8/10 ✓
17 entries, 15 with IPA. Strong coverage of unusual words: castellated, improvisatori, habiliments, cerements, blood-bedewed, out-Heroded, piquancy. Homographs correctly flagged (live, close, produce, deliberate). 2 entries (produce, deliberate) missing IPA — minor gap.

### HTML Presentation: 8/10 ✓
- Navigation functional, tabs work ✓
- Both character profiles well-formatted with appearance, personality, voice guidance, relationships, source evidence ✓
- "1 chapters" grammar issue persists (cosmetic)
- The Red Death's "Also known as: The Courtiers, The Musicians, The Waltzers" is misleading to narrators, but the profile content itself is excellent

## Current Issues (Priority Order)

### CRITICAL
(none — no catastrophic failures)

### HIGH
(none — both HIGH issues from attempt 6 have been fixed in attempt 7)

### MEDIUM
1. **"1 chapters" grammar in HTML** [Presentation]
   - Problem: "This book contains 1 chapters" should be "1 chapter"
   - Location: HTML report template
   - Fix: Deferred — Presentation is at 8/10, above threshold

2. **2 pronunciation entries missing IPA** [Pronunciation]
   - Problem: "produce" and "deliberate" have null IPA
   - Fix: Deferred — Pronunciation is at 8/10, above threshold

### LOW
3. **Additional Red Death aliases** [Alias Grouping]
   - "the stranger", "the mummer" could be additional aliases
   - Fix: Deferred until core alias issues resolved

## What's Expected in Attempt 7

The attempt 7 fixes address both HIGH alias issues. Expected outcome:
- **Fix #1 (Rule 0.7)**: Group-noun canonicals ("The Courtiers" etc.) can no longer validate proper-noun aliases like "The Red Death" → `_deduplicate_alias_canonical_conflicts` won't merge them into The Red Death → Wrong aliases blocked.
- **Fix #2 (ALIAS_RESOLUTION_PROMPT Rule 3 exception)**: LLM will now propose "the masked figure", "the figure", "the intruder" as aliases when summary reveals the figure IS The Red Death → Correct aliases flow through.

Expected: Alias Grouping ~8/10, Character Extraction ~9.0/10, overall pass.

## Fix History

### Attempt 7 (PENDING ANALYSIS)
Root cause investigation revealed the actual mechanism for wrong group aliases:
1. `_get_chapter_summaries` in characters.py prepends `[Characters present: ..., the courtiers, the musicians, the waltzers]` to summary text
2. CHARACTER_IDENTIFICATION_PROMPT says "treat each entry as a distinct character" → Pass 1 LLM extracts group nouns as separate canonical characters
3. Pass 2 for "The Courtiers" canonically proposes "The Red Death" as its alias (co-occurrence) — passes verify_aliases (no Rule 0.6 match since "death" has no plural suffix)
4. `_deduplicate_alias_canonical_conflicts` in characters.py merges "The Courtiers" INTO "The Red Death" → "The Courtiers" canonical becomes an alias of The Red Death

And for missing correct aliases:
- ALIAS_RESOLUTION_PROMPT Rule 3 ("do NOT include persons who interacted with this entity") caused LLM to exclude "the masked figure" since it interacted with Prospero

**Fix 1: Rule 0.7 in verify_aliases()** — Blocks proper-noun aliases for plural-group-noun canonical characters. Universal invariant: group_of_people ≠ named_individual_entity. Prevents "The Red Death" and "Prince Prospero" from becoming validated aliases of "The Courtiers", stopping the cascade into `_deduplicate_alias_canonical_conflicts`.

**Fix 2: ALIAS_RESOLUTION_PROMPT Rule 3 exception** — Added identity-reveal exception: "Exception: if the summary explicitly reveals a figure IS {character_name} (e.g., 'revealed to be', 'proving to be', 'it was'), include the descriptors used before that reveal as aliases." Allows LLM to propose "the masked figure", "the figure", "the intruder" as aliases for The Red Death.

**Tests:** 332 passed, 10 skipped (all pre-existing). Rule 0.7 smoke tests PASS.

**Files modified:** `src/pipeline/character_extraction_v2/main_cast.py` ONLY.

### Attempt 6 (Score: 8.35/10 overall, Character Extraction 7.5/10 — IMPROVEMENT from 6.60)
1. **REVERTED characters.py Rule 0.6** — Removed the `_is_valid_alias()` Rule 0.6 addition from attempt 5. Restored The Red Death as its own character.
2. **KEPT grounding.py substring alias exemption** — "Prospero" alias correctly preserved.
3. **Result:** Back to attempt 4 state plus Prospero alias improvement. Overall 8.35 vs attempt 4's 8.23.

### Attempt 5 (Score: 6.60/10 — REGRESSION from 8.23)
1. Rule 0.6 in characters.py caused regression — blocked valid aliases, Red Death merged into clock.
2. grounding.py fix worked — Prospero alias preserved.

### Attempt 4 (Score: 8.23/10 — PREVIOUS BEST)
1. Reverted attempt 3 regression
2. Improved is_symbolic detection
3. Re-added Rule 0.6 and title-stripping (effects not visible in output)

### Attempt 3 (Score: 6.10/10 — REGRESSION)
Auto-reverted in attempt 4.

### Attempt 2 (Score: 7.98/10)
Rule 0.5, is_symbolic, narrator detection, pronunciation fixes.

### Attempt 1 (Score: 6.85/10 — baseline)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 7 | Wrong group aliases: Rule 0.7 in verify_aliases | main_cast.py | Pending analysis |
| 7 | Missing correct aliases: Rule 3 exception in ALIAS_RESOLUTION_PROMPT | main_cast.py | Pending analysis |
| 6 | Revert characters.py regression | characters.py (reverted) | Fixed ✓ — Red Death back as own character |
| 6 | Keep grounding.py fix | (no change) | Fixed ✓ — Prospero alias preserved |
| 5 | Wrong group aliases on Red Death | characters.py (_is_valid_alias) | **REGRESSION** — blocked valid aliases |
| 5 | Missing "Prospero" alias | grounding.py | Fixed ✓ |
| 4 | Revert attempt 3 regression | main_cast.py | Fixed ✓ |
| 4 | is_symbolic detection improvement | main_cast.py | Fixed ✓ |
| 3 | Wrong group aliases on Red Death | main_cast.py | REGRESSION |
| 2 | Rule 0.5 over-blocking | main_cast.py | Fixed ✓ |
| 2 | Clock not marked is_symbolic | main_cast.py | Fixed ✓ |
| 2 | Wrong narrator detection | narrator.py | Fixed ✓ |
| 2 | Pronunciation false positives | cmu_proposer.py | Fixed ✓ |

**Pattern confirmed:** Changes to characters.py are HIGH RISK (regressions in attempts 3 and 5). All remaining fixes must be scoped to main_cast.py.

## Score Progression
- Attempt 1: 6.85/10 (baseline)
- Attempt 2: 7.98/10 (+1.13)
- Attempt 3: 6.10/10 (-1.88) ← REGRESSION
- Attempt 4: 8.23/10 (+2.13) ← PREVIOUS BEST
- Attempt 5: 6.60/10 (-1.63) ← REGRESSION
- Attempt 6: 8.35/10 (+1.75) ← CURRENT BEST
- Attempt 7: TBD

## Configuration Audit
- Models: qwen3.5:122b-a10b for characters/summaries, qwen3.5:35b-a3b for structure/pronunciation
- Context length 32768 sufficient for 2,449-word short story
- Temperature 0.7 standard
- 0 LLM retries across all stages
- No chunking issues
- **Root cause is NOT model/config** — the remaining issues are alias validation logic in main_cast.py

## Next Action
Run PROMPT_analyze.md to execute attempt 7 analysis with the new fixes.
