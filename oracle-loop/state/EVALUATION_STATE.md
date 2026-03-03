# Current Evaluation State

## Active Text
- **Name:** masque_of_red_death
- **Attempt:** 2
- **Phase:** awaiting_analysis
- **baseline_score:** 6.85
- **Competitive Mode:** none

## Output Files
- HTML: ../output/masque_of_red_death/report.html
- JSON: ../output/masque_of_red_death/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 6/10 ✗ (FAILING)
  - Completeness: 9/10
  - Identity Resolution: 7/10
  - Alias Grouping: 3/10 ← primary blocker
- Character Profiles: 8.5/10 ✓
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 8/10 ✓
- **Overall: 7.98/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (1 category below threshold)

## Evaluation Details

### Structure Detection: 9/10 ✓
"The Masque of the Red Death" is a continuous short story with no chapter divisions. The pipeline correctly identifies it as a single section. No false splits. Null title is acceptable for a continuous text.

### Character Extraction: 6/10 ✗

**Completeness: 9/10** — The story has exactly two named characters: Prince Prospero and The Red Death. Both are present. No hallucinated characters. The courtiers, musicians, and waltzers are unnamed groups, not named characters, so their absence as separate entries is correct.

**Identity Resolution: 7/10** — No false splits (good). However, the three wrong aliases on The Red Death effectively create false merges: any mention of "The Courtiers" in the text would be attributed to The Red Death, which is incorrect. These are distinct groups of party guests.

**Alias Grouping: 3/10** — Three WRONG aliases on The Red Death:
- "The Courtiers" — these are Prospero's party guests, not the Red Death
- "The Musicians" — the musicians at the masquerade, not the Red Death
- "The Waltzers" — the dancing guests, not the Red Death

Missing valid aliases:
- "the masked figure" / "the stranger" — the Red Death's physical manifestation at the masquerade ball. The HTML summary shows "the masked figure" in active characters, confirming it's in the text.
- "Prospero" should be an alias of "Prince Prospero" (used interchangeably in the text)

### Character Profiles: 8.5/10 ✓
Both profiles are accurate:
- Prospero: "bold and robust", "happy, dauntless, sagacious" — all from text. Personality evolution (happiness → terror → rage → despair) well captured. Speech patterns noted.
- The Red Death: Physical description ("habiliments of the grave", "blood-dabbled vestments", "stiffened corpse" mask) closely matches Poe's text. "Silent, relentless, solemn" is accurate.
- Relationships ("enemy") are reasonable for both.

### Chapter Summaries: 9/10 ✓
Excellent summary capturing all key events: Prospero's retreat, the castellated abbey, seven color-coded rooms, the masked figure's appearance, Prospero's confrontation and death, the empty costume reveal, and "Darkness, Decay, and the Red Death" in dominion. Accurate and useful for narrator preparation.

### Pronunciation Guide: 8/10 ✓
Improved from attempt 1:
- False positives removed (giddiest, gaieties, convulsed, unutterable — Fix 4 worked)
- Good coverage: improvisatori, castellated, habiliments, cerements, out-Heroded, piquancy
- 15/17 entries have IPA
- 2 homograph entries (produce, deliberate) still have null IPA — minor issue since narrators know these words
- Missing "arabesque" — minor

### HTML Presentation: 8/10 ✓
Navigation functional, information organized. Minor grammar ("1 chapters"). Character section shows wrong aliases prominently ("Also known as: The Courtiers, The Musicians, The Waltzers") which is misleading for narrator preparation.

## Current Issues (Priority Order)

### CRITICAL
1. **Wrong aliases on The Red Death: "The Courtiers", "The Musicians", "The Waltzers"** [Alias Grouping]
   - Problem: These are groups of people at the masquerade party — Prospero's guests. They are NOT aliases for The Red Death (the personified plague). The LLM in Pass 2 proposed these group nouns as aliases and verify_aliases let them through.
   - Evidence: In the story, "the courtiers" refers to the thousand friends Prospero invites to his abbey. "The musicians" and "the waltzers" are entertainers at the party. The Red Death kills them all at the end — they are victims, not alternate names.
   - Root cause: `verify_aliases()` in `src/pipeline/character_extraction_v2/main_cast.py` has no rule blocking **plural group nouns** from being assigned as aliases of a singular entity. "The Courtiers" (a group of people) should not be an alias for "The Red Death" (a single personified force).
   - Fix approach: Add a verification rule that detects when a proposed alias is a **plural noun describing a group** (courtiers, musicians, waltzers, soldiers, servants, etc.) and the canonical name refers to a singular entity. Plural group nouns should be blocked as aliases unless the canonical name is itself a group/collective. This is a generic rule — group names are never aliases for individuals.
   - **Pipeline origin:** main_cast (IDs: main_cast_0, main_cast_2)

### HIGH
2. **Missing alias: "the masked figure" / "the stranger" for The Red Death** [Alias Grouping]
   - Problem: In the story, the Red Death appears at the masquerade as "a masked figure" / "the stranger" / "the mummer figure". These are the same entity — the Red Death's physical manifestation. The HTML summary shows "the masked figure" as an active character in the chapter, but it's not linked to The Red Death as an alias.
   - Evidence: Poe reveals that the masked figure IS the Red Death: "And now was acknowledged the presence of the Red Death."
   - Root cause investigation needed: Rule 0.5 (symbolic coherence) only applies to is_symbolic=True entities, and The Red Death has is_symbolic=False, so Rule 0.5 is NOT the blocker. Two possibilities: (a) the LLM in Pass 2 never proposed "the masked figure" as an alias — fix the CONSOLIDATED_ALIAS_PROMPT or Pass 2 prompt, or (b) another rule (Rule 2a absent-from-summaries, or Rule 2 co-occurrence) is blocking it. The fix phase should add DEBUG logging to trace which aliases Pass 2 proposes and which rules reject them.
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` — Pass 2 alias proposal + verify_aliases()
   - Fix approach: First diagnose whether the LLM proposes these or not (check Pass 2 output). If proposed but blocked, fix the blocking rule. If not proposed, consider whether the Pass 2 prompt needs adjustment for personified concepts that manifest physically.

3. **Missing alias: "Prospero" for Prince Prospero** [Alias Grouping]
   - Problem: Poe uses both "Prince Prospero" and "Prospero" throughout the text. "Prospero" should be listed as an alias of "Prince Prospero".
   - Evidence: The text alternates between "Prince Prospero" and "Prospero" — e.g., "Prospero rushed hurriedly through the six chambers"
   - Root cause: Pass 2 may not propose surname-only/name-only aliases when the canonical name includes a title. Or verify_aliases may be blocking it.
   - Location: `src/pipeline/character_extraction_v2/main_cast.py`
   - Fix approach: Likely a Pass 2 LLM issue — the LLM should recognize that "Prospero" (without "Prince") is a valid alias.

### MEDIUM
4. **Two pronunciation entries missing IPA** [Pronunciation]
   - Problem: "produce" and "deliberate" have `null` IPA values
   - Evidence: These are homograph entries that should have IPA for both pronunciations (like "live" and "close" which do have IPA)
   - Location: Pronunciation pipeline IPA generation
   - Fix: Ensure homograph entries always get IPA populated

## Priority Fix Order
1. Fix Critical #1 — add plural-group-noun blocking rule to verify_aliases
2. Fix High #2 — diagnose why masked figure aliases are missing (trace Pass 2)
3. Fix High #3 — "Prospero" as alias for "Prince Prospero"
4. Medium #4 — IPA for homographs (defer if needed)

## Fix History
### Attempt 3 Fix (this attempt)
1. **RULE 0.6: Block plural group noun aliases** — Added to `verify_aliases()` in `main_cast.py` (after Rule 0.5, before Rule 1). Plural agent/role nouns (courtiers, musicians, waltzers, servants, soldiers, etc.) ending in suffix patterns (-ers, -ors, -ians, -ists, -ants, -ents, -iers, -ees, -smen, -ies) are blocked as aliases for non-group canonical characters. Smoke test: "The Courtiers", "The Musicians", "The Waltzers" all blocked for "The Red Death". ✓
   - Root cause: `verify_aliases()` had no check for plural group descriptors; co-occurrence check passed all aliases in single-chapter stories
   - Modified: `src/pipeline/character_extraction_v2/main_cast.py`
2. **Auto-add title-stripped aliases** — Added `_add_title_stripped_aliases()` method (called before verify_aliases). Noble/royal title prefixes (Prince, King, Queen, Duke, etc.) are stripped to produce shortened name forms. "Prince Prospero" → auto-adds "Prospero" as alias. Smoke test: "Prospero" added and survives verify_aliases (Rule 2 substring check). ✓
   - Root cause: LLM never sees "Prospero" alone in summaries (always "Prince Prospero"), so Pass 2 doesn't propose it; summary-based alias detection was the bottleneck
   - Modified: `src/pipeline/character_extraction_v2/main_cast.py`
3. **Pass 2 ALIAS_RESOLUTION_PROMPT Rule 2 clarified** — Added "shortened name forms (e.g., 'Prospero' for 'Prince Prospero')" with example, changed "descriptive references" to "singular descriptive references for the same individual", added note about characters appearing under different descriptions. Rule 3 updated to mention "groups, or organizations". ✓
   - Modified: `src/pipeline/character_extraction_v2/main_cast.py`

### Attempt 2 Fix
1. **Rule 0.5 scoped to is_symbolic=True only** → Fixed: The Red Death no longer blocked by personified concept check. Clock aliases now correctly blocked. **Result: Partial fix** — Rule 0.5 no longer over-blocks, but wrong aliases (group nouns) still pass through and valid aliases (masked figure) still missing.
2. **Programmatic is_symbolic for multi-word descriptors** → Fixed: Ebony clock correctly marked is_symbolic=True and removed from character list.
3. **Narrator detection prompt** → Fixed: Third-person narration correctly identified (narrator=None).
4. **Pronunciation whitelist** → Fixed: giddiest, gaieties, convulsed, unutterable no longer false positives.

### Attempt 1 (Baseline)
- Character Extraction: 3/10 (catastrophic — clock as character, Red Death missing aliases, wrong narrator)
- Profiles: 5/10
- Pronunciation: 7.5/10
- Overall: 6.85/10

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 3 | Wrong group aliases on Red Death | main_cast.py | Fixed — Rule 0.6 blocks plural group nouns |
| 3 | Missing "Prospero" alias for Prince Prospero | main_cast.py | Fixed — title-stripping adds it programmatically |
| 3 | Pass 2 prompt: improve alias proposals | main_cast.py | Fixed — Rule 2 clarified for shortened forms + singular |
| 2 | Rule 0.5 over-blocking personified concepts | main_cast.py | Fixed — clock blocked, Red Death no longer over-blocked |
| 2 | Clock not marked is_symbolic | main_cast.py | Fixed — clock removed as character |
| 2 | Wrong narrator detection | narrator.py | Fixed — third-person correctly identified |
| 2 | Pronunciation false positives | cmu_proposer.py | Fixed — 4 common words whitelisted |

## Score Progression
- Attempt 1: 6.85/10 (baseline)
- Attempt 2: 7.98/10 (+1.13) — 4 of 6 issues fixed, 1 category still failing
- Attempt 3: TBD (awaiting analysis)

## Configuration Audit
- Models appropriate (qwen3.5:122b-a10b for characters, qwen3.5:35b-a3b for structure/pronunciation)
- Context length 32768 is plenty for 2,449-word short story
- Temperature 0.7 standard
- No chunking issues (story fits in single chunk)
- 0 LLM retries, high confidence on both characters
- The LLM confidently produced wrong alias assignments — this is a verification gap, not a model issue

## Next Action
Re-run analysis to verify fixes
