# Current Evaluation State

## Active Text
- **Name:** masque_of_red_death
- **Attempt:** 6
- **Phase:** awaiting_fix
- **baseline_score:** 6.85
- **Competitive Mode:** none

## Output Files
- HTML: ../output/masque_of_red_death/report.html
- JSON: ../output/masque_of_red_death/analysis.json

## Latest Scores
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

## Evaluation Details

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
- Analysis logs confirm: correct aliases were proposed but BLOCKED by semantic mismatch check ("core noun 'figure' vs 'death'") due to is_symbolic processing

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
1. **Wrong group-noun aliases on The Red Death** [Alias Grouping]
   - Problem: "The Courtiers", "The Musicians", "The Waltzers" are aliases of The Red Death. These are unnamed groups of partygoers at Prospero's ball, NOT aliases for the personification of pestilence.
   - Evidence: In the text, courtiers are the noble guests, musicians play during the ball, and waltzers dance. They are The Red Death's VICTIMS, not its identities.
   - Source: These group nouns are proposed by the LLM in Pass 2 alias resolution and not filtered out.
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` — Pass 2 processing (`_process_consolidated_pass2`)
   - Fix approach: Add a post-Pass-2 filter in main_cast.py that strips plural group-noun aliases (definite article + plural noun like "The Courtiers") from non-group characters. This must be in main_cast.py ONLY, NOT in characters.py's global `_is_valid_alias()` (that caused the attempt 5 regression). Specifically:
     - After `_process_consolidated_pass2()` returns, filter aliases where: (a) alias starts with "The " (definite article), AND (b) alias ends with a plural suffix (-ers, -ors, -ians, -ists), AND (c) the canonical name is NOT itself a group noun.
     - Alternatively, use the existing Rule 0.6 logic but apply it ONLY at the point where Pass 2 aliases are added, not globally.

2. **Missing correct aliases for The Red Death** [Alias Grouping]
   - Problem: "the masked figure", "the figure", and "the intruder" are valid aliases for The Red Death (the text explicitly uses them to refer to it) but they were BLOCKED during alias validation.
   - Evidence: Analysis logs show semantic mismatch check rejected them ("core noun 'figure' vs 'death'"). The Red Death was treated as is_symbolic during processing, triggering a stricter alias validation path where the core nouns must semantically match.
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` — likely in `verify_aliases()` or `_is_valid_alias()` semantic mismatch check
   - Fix approach: The Red Death is a personified entity that physically manifests in the story — it's described as a "figure" and an "intruder". The semantic check comparing "figure" to "death" is too strict. Options:
     - (a) **Best:** Don't mark The Red Death as is_symbolic during alias validation. It's an entity that physically appears, acts, and is confronted — it's more character than symbol. The is_symbolic flag should be reserved for purely abstract/inanimate entities (like the ebony clock).
     - (b) **Alternative:** Relax the semantic mismatch check to allow human-form descriptors ("figure", "form", "shape", "intruder", "stranger") as aliases for any character, including symbolic ones.
     - (c) **Safest fallback:** Allow aliases where the proposed alias has a high co-occurrence count with the canonical name in the same passages.

### MEDIUM
3. **"1 chapters" grammar in HTML** [Presentation]
   - Problem: "This book contains 1 chapters" should be "1 chapter"
   - Location: HTML report template
   - Fix: Deferred — Presentation is at 8/10, above threshold

4. **2 pronunciation entries missing IPA** [Pronunciation]
   - Problem: "produce" and "deliberate" have null IPA
   - Fix: Deferred — Pronunciation is at 8/10, above threshold

### LOW
5. **Additional Red Death aliases** [Alias Grouping]
   - "the stranger", "the mummer" could be additional aliases
   - Fix: Deferred until core alias issues resolved

## What's Needed to Pass

Only Character Extraction (7.5/10) needs to reach 8.0. The two HIGH issues are both alias-related:

**Fix #1:** Remove wrong group-noun aliases (Courtiers, Musicians, Waltzers) from The Red Death → improves Alias Grouping from 4/10 toward 7/10

**Fix #2:** Allow correct aliases (masked figure, figure, intruder) through semantic check → improves Alias Grouping from 7/10 toward 9/10

Both fixes together should push Alias Grouping to ~8/10, bringing overall Character Extraction to ~9×0.33 + 10×0.33 + 8×0.33 ≈ 9.0, well above threshold.

**CRITICAL CONSTRAINT:** Do NOT modify `src/agents/characters.py` — attempt 5 proved that global changes there cascade unpredictably. Both fixes must be scoped to `src/pipeline/character_extraction_v2/main_cast.py`.

## Fix History

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
- Attempt 6: 8.35/10 (+1.75) ← NEW BEST

## Configuration Audit
- Models: qwen3.5:122b-a10b for characters/summaries, qwen3.5:35b-a3b for structure/pronunciation
- Context length 32768 sufficient for 2,449-word short story
- Temperature 0.7 standard
- 0 LLM retries across all stages
- No chunking issues
- **Root cause is NOT model/config** — the remaining issues are alias validation logic in main_cast.py

## Next Action
Run PROMPT_fix.md to address:
1. HIGH #1: Block group-noun aliases (Courtiers/Musicians/Waltzers) in main_cast.py Pass 2 output
2. HIGH #2: Allow personified-form aliases (masked figure/figure/intruder) through semantic check in main_cast.py
Both fixes must be in `src/pipeline/character_extraction_v2/main_cast.py` ONLY.
