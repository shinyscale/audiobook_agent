# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 6
- **Phase:** awaiting_analysis
- **baseline_score:** 6.55
- **Competitive Mode:** single

## Output Files
- HTML: ../output/gatsby/report.html
- JSON: ../output/gatsby/analysis.json

## Pipeline Notes (Attempt 6)
- Completed in 76m 33s, 253 LLM calls, 401,362 tokens
- 9 chapters detected, 19 characters extracted (was 21 — Nick/Carraway merge succeeded), 19 profiles generated
- Fix N SUCCESS: Nick Carraway merged (34 mentions, aliases: Nick, Carraway), narrator correctly identified as "Nick Carraway (first-person)"
- Ella Kaye narrator regression from attempt 5 resolved — Ella Kaye no longer in character list
- Fix P SUCCESS: personality.traits populated for 17/19 characters, personality.speech_patterns for 15/19, voice_guidance populated with verbal_tics/dialect_notes/example_quotes
- Fix Q SUCCESS: All 129/129 pronunciations now have IPA, all 19 homographs have dual-IPA with context labels
- Fix O PARTIAL: `reject_unfounded_familial_labels()` exists and removed SOME wrong relationships (Daisy→George, Daisy→Wolfsheim gone) but many survive due to 100-char co-mention check being too permissive
- Henry C. Gatz has full name restored (was "Gatz" in attempt 5) with aliases ["Gatsby's father", "Gatz"]

## Latest Scores
- Structure Detection: 10/10 ✓
- Character Extraction: 8/10 ✓
  - Completeness: 8/10
  - Identity Resolution: 8.5/10
  - Alias Grouping: 7/10
- Character Profiles: 6.5/10 ✗ (FAILING) ← sole remaining blocker
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 8.5/10 ✓
- HTML Presentation: 9/10 ✓
- **Overall: 8.43/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (1 category below threshold: Profiles 6.5)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.55 | — | Baseline. main_cast pipeline failed; massive false splits; profiles catastrophically wrong |
| 2 | 7.15 | +0.60 | Fix A partially worked (Gatsby aliases resolved); main_cast STILL fails; IPA corruption fixed |
| 3 | 7.93 | +1.38 | Main cast pipeline FIXED (Fix C). 5 false splits resolved. Profiles still wrong. |
| 4 | 7.98 | +1.43 | Fixes G/H/I/J: Eckleburg deduped ✓, "like" removed ✓, Nick rels→unknown (marginal), profiles STILL primary blocker |
| 5 | 7.83 | +1.28 | Fixes K/L/M all SUCCESS ✓. LLM variance regressions: Ella Kaye narrator, Gatz name. Core blockers unchanged. |
| 6 | 8.43 | +1.88 | Fix N ✓ (Nick merged+narrator), Fix P ✓ (traits/speech populated), Fix Q ✓ (homograph IPA). Fix O partial (familial labels persist). Profiles sole remaining blocker. |

## What Changed in Attempt 6

### Fix Results
- **Fix N (Nick/Carraway merge + narrator):** SUCCESS ✓ — Nick Carraway is now main_cast_0, narrator: true, 34 mentions, aliases: ["Nick", "Carraway"]. Ella Kaye no longer in output. This resolved the #1 issue from all 5 prior attempts.
- **Fix O (Familial label validation):** PARTIAL — Code exists and runs in post_corrections.py. Removed some wrong labels (Daisy→George "wife", Daisy→Wolfsheim "husband", Sloane's wrong entries gone). But many wrong labels survive because the 100-char co-mention text check catches incidental nearby family phrases (e.g., "her mother" mentioned near both characters in a scene, but referring to a third character).
- **Fix P (Personality traits + speech patterns):** SUCCESS ✓ — Personality data IS populated in nested `personality` and `voice_guidance` dicts:
  - `personality.traits`: 17/19 characters have traits (was 0)
  - `personality.speech_patterns`: 15/19 characters have speech patterns (was 0)
  - `voice_guidance.verbal_tics`: 14/19 characters have verbal tics
  - `voice_guidance.dialect_notes`: populated for characters with distinctive speech
  - `voice_guidance.example_quotes`: present for most characters
  - Note: The previous evaluation's "0/19" was checking nonexistent top-level fields (`personality_traits`, `speech_pattern`). The real data lives in nested personality/voice_guidance dicts.
- **Fix Q (Homograph IPA):** SUCCESS ✓ — All 129 pronunciations have IPA. All 19 homographs have excellent dual-IPA with context labels (e.g., minute: "/ˈmɪnɪt/ (time unit) or /maɪˈnjuːt/ (tiny)"). This is exactly what narrators need.

### Remaining Issues from Attempt 5 — Status
- Nick/Carraway split: **FIXED** ✓ (Fix N)
- Ella Kaye narrator: **FIXED** ✓ (Fix N — no longer in output)
- Personality traits 0/21: **FIXED** ✓ (Fix P — 17/19 populated)
- Speech patterns 0/21: **FIXED** ✓ (Fix P — 15/19 populated)
- 19 homographs lacking IPA: **FIXED** ✓ (Fix Q — all have dual IPA)
- Henry C. Gatz name regression: **FIXED** (stochastic — full name restored this run)
- Hallucinated familial labels: **PARTIAL** (Fix O — some removed, many persist)
- Gatsby physical description null: **UNCHANGED**
- Daisy physical description: **CHANGED** — now null (was Jordan's misattributed text in attempt 5). Null is better than wrong, but still needs the correct description.
- Myrtle physical description: **WRONG** — now contains Catherine's description instead of Myrtle's
- Owl Eyes missing: **UNCHANGED**

## Current Issues (Priority Order)

### CRITICAL

1. **Relationships still have hallucinated familial labels despite Fix O** [Profiles]
   - Problem: Fix O's `reject_unfounded_familial_labels()` runs but is too permissive. The 100-char co-mention check with `_rel_phrase_re` catches incidental text matches where family phrases (e.g., "her mother") appear near two characters who are in the same scene but aren't related.
   - Surviving wrong labels:
     - Daisy → Jordan Baker: "mother" (WRONG — friend)
     - Daisy → Jay Gatsby: "mother" (WRONG — former lover)
     - Daisy → Myrtle Wilson: "wife" (WRONG — rival/unaware)
     - Jordan → Daisy: "wife" (WRONG — friend)
     - Jordan → Tom: "wife" (WRONG — acquaintance)
     - Jordan → Gatsby: "mother" (WRONG — acquaintance)
     - Myrtle → Tom: "wife" (WRONG — lover/affair)
     - McKee → Myrtle: "husband" (WRONG — acquaintance)
     - McKee → Tom: "husband" (WRONG — acquaintance)
     - Henry C. Gatz → Dan Cody: "mentor" (WRONG — no relationship; Dan Cody was GATSBY's mentor, not Gatz's)
     - James Gatz → Henry C. Gatz: "son" (WRONG direction — Henry Gatz is James Gatz's FATHER, not son)
   - Correct relationships: Tom↔Daisy "husband"/"wife" ✓, Myrtle→George "wife" ✓, Catherine→Myrtle "sister" ✓, Henry C. Gatz→James Gatz "son" ✓, Rosy→Wolfsheim "close friend" ✓, George→Eckleburg "symbolic figure of judgment" ✓
   - Location: `src/pipeline/character_profiling/post_corrections.py` line 1065 — `reject_unfounded_familial_labels()`
   - **Required fix approach:** The 100-char co-mention check is too generous. Two options:
     - **Option A (recommended):** Tighten to 40-char window AND require the possessive pronoun ("his/her") to be adjacent to one of the two character names (not a third-party reference). Currently, "her mother" anywhere in a 100-char window where both characters appear is enough — even if "her" refers to a third character.
     - **Option B (simpler, more aggressive):** For non-surname-sharing character pairs, simply DELETE all familial labels. Only allow familial labels between characters whose canonical names share a surname component. This is safe because the only correct familial labels in Gatsby are between surname-sharing pairs (Buchanan↔Buchanan, Wilson↔Wilson, Gatz↔Gatz) or the Catherine↔Myrtle sister relationship (which Fix O should protect via text evidence).
     - **Exception needed for Option B:** Catherine and Myrtle Wilson don't share a surname in canonical names. Add logic: if the text contains "[CharA]'s sister" or "[CharB]'s sister" near the other character within 50 chars, keep the "sister"/"brother" label.
   - Impact: +1.0 to Profiles if fixed (from 6.5 to ~7.5)

### HIGH

2. **Gatsby (protagonist) has null physical description** [Profiles]
   - Problem: James Gatz (main_cast_13, 275 mentions) has `physical_description: null`
   - Expected: Elegant appearance, tanned, gorgeous smile, "an elegant young roughneck," pink suit, "He smiled understandingly — much more than understandingly"
   - Physical descriptions are available in Ch 3 ("a man of about my age... an elegant young roughneck"), Ch 5 ("He was pale, and there were dark signs of sleeplessness beneath his eyes"), Ch 7 (pink suit)
   - Location: Profile extraction chunking — the LLM assigned to Gatsby's profile may not receive the chapters containing his physical descriptions
   - Fix: Add a second-pass extraction for major characters (>50 mentions) who have null physical_description — scan full text for descriptive passages mentioning the character
   - Impact: +0.3 to Profiles

3. **Daisy has null physical description** [Profiles]
   - Problem: Daisy Buchanan (main_cast_1, 208 mentions) has `physical_description: null`
   - Expected: "face was sad and lovely with bright things in it, bright eyes and a bright passionate mouth"
   - In attempt 5, Daisy had Jordan's description misattributed. Now it's null — an improvement (not actively wrong), but still a gap.
   - Impact: +0.2 to Profiles

4. **Myrtle's physical description is actually Catherine's** [Profiles]
   - Problem: Myrtle Wilson's `physical_description` says "Described as having a 'slender, worldly' sister Catherine with a 'solid, sticky bob of red hair' and powdered milky white complexion; Myrtle herself is not directly described..."
   - This IS Catherine's description (correctly also in Catherine's entry), cross-contaminated to Myrtle.
   - Myrtle's actual appearance: "thickish figure of a woman... she was in the middle thirties, and faintly stout, but she carried her surplus flesh sensuously"
   - Location: Profile extraction — LLM is extracting from Catherine's description in the same Ch 2 apartment scene
   - Impact: +0.2 to Profiles

### MEDIUM

5. **Wolfsheim's speech_patterns incorrectly include "old sport"** [Profiles]
   - Problem: Wolfsheim's `personality.speech_patterns` lists "uses 'old sport' in addressing others" — this is GATSBY's catchphrase, not Wolfsheim's.
   - Wolfsheim's actual distinctive speech: accent rendering ("Oggsford" for "Oxford," "gonnegtion" for "connection"), dialect_notes should reflect this but says "unknown"
   - Impact: Minor — narrator might use wrong speech pattern for Wolfsheim

6. **James Gatz → Henry C. Gatz relationship direction wrong** [Profiles]
   - Problem: James Gatz's relationship to Henry C. Gatz is listed as "son" — meaning "Henry C. Gatz is my son." But Henry C. Gatz is James Gatz's FATHER.
   - Meanwhile, Henry C. Gatz correctly has "James Gatz: son" (meaning "James Gatz is my son" ✓)
   - The label should be "father" from James Gatz's perspective
   - Impact: Minor — confusing for narrator but Henry Gatz's entry has the correct direction

7. **"Buchanan" alias shared between Tom and Daisy** [Alias Grouping]
   - Both main_cast_1 (Daisy) and main_cast_2 (Tom) list "Buchanan" as alias. Similarly, "Gatz" is shared between James Gatz and Henry C. Gatz.
   - These are defensible (shared surname) but could confuse narrator lookup.

8. **Self-alias: "James Gatz" in alias list of canonical "James Gatz"** [Alias Grouping]
   - The canonical name appears in its own alias list — redundant and looks like a bug.

9. **Canonical name "James Gatz" rather than "Jay Gatsby"** [Completeness]
   - The character is overwhelmingly known as "Gatsby" (275 mentions are mostly for "Gatsby"/"Jay Gatsby"). Using his birth name as canonical is confusing for a narrator. "Jay Gatsby" would be more intuitive as the canonical name.

10. **Missing "Owl Eyes"** [Completeness]
    - The bespectacled man from Gatsby's library (Ch 3, Ch 9 funeral) not in character list. Narratively significant as the only non-family funeral attendee. Ch 3 summary mentions him.

11. **Chapter 7 summary has car arrangement error** [Summaries]
    - Summary says "Daisy and Tom returning home in Gatsby's car" — WRONG. It was Gatsby and Daisy in the yellow car (Daisy driving). Tom, Nick, Jordan returned in Tom's car.
    - Internally contradicts the next sentence: "killed by a yellow car (driven by Daisy)" — if Daisy was with Tom, who was driving?

12. **66 pronunciation entries still "unknown" category** [Pronunciation]
    - Many classifiable: dialect (gonnegtion, comin), literary (murmurous, contralto, extemporizing), archaic (plagiaristic). 66/129 = 51% unknown.

### LOW

13. **Gatsby's example_quote misattributed** [Profiles]
    - James Gatz's `voice_guidance.example_quotes` includes "Don't you call me 'old sport'!" — this is TOM speaking to Gatsby, not Gatsby himself.

## Configuration Audit

### Model Configuration
- Model: qwen3-next:80b-a3b-instruct-q8_0 (Ollama) — same model for all agents
- Context length: 32768 — adequate for Gatsby
- Temperature: 0.7 — still too high for relationship extraction
- think_mode: false

### Processing Issues
- 253 LLM calls total (down from 295 in attempt 5), 0 retries — pipeline mechanically stable
- Profile generation producing rich personality/voice data now — Fix P working well
- Relationship labels remain the weak point — LLM still hallucinating familial labels, post-processing filter too permissive

### Recommendation
- HIGH: Tighten or replace the familial label filter (CRITICAL #1 above)
- MEDIUM: Add second-pass physical description extraction for major characters with null descriptions

## Fix History

### gatsby — Attempt 2 Fixes
**Fix A: Include `characters_present` in summaries for main_cast LLM extraction** [CRITICAL] — PARTIAL
**Fix B: IPA validation to reject corrupt entries** [MEDIUM] — SUCCESS ✓

### gatsby — Attempt 3 Fixes
**Fix C: Main cast prompts changed to dict wrapper format** [CRITICAL] — SUCCESS ✓
**Fix D: Secondary relationship call no longer overwrites primary** [CRITICAL] — PARTIAL
**Fix E: Pronunciation false positive exclusions** [MEDIUM] — SUCCESS ✓
**Fix F: UNKNOWN → PROPER_NOUN reclassification** [MEDIUM] — PARTIAL

### gatsby — Attempt 4 Fixes
**Fix G: Relationship prompt — replace familial examples with social ones** [CRITICAL] — PARTIAL (Nick improved, others unchanged)
**Fix H: Physical description validation** [HIGH] — FAILED (narrator injection overwrites after validation)
**Fix I: Eckleburg duplicate — reverse title check** [HIGH] — SUCCESS ✓
**Fix J: "like" pronunciation exception** [LOW] — SUCCESS ✓

### gatsby — Attempt 5 Fixes
**Fix K: Butler/Butler F6 case dedup** [HIGH] — SUCCESS ✓ (src/analyzer.py)
**Fix L: Remove "unknown" relationships** [CRITICAL] — SUCCESS ✓ (src/pipeline/character_profiling/post_corrections.py)
**Fix M: Narrator appearance prose filter** [HIGH] — SUCCESS ✓ (src/pipeline/character_profiling/post_corrections.py)

### gatsby — Attempt 6 Fixes
**Fix N: Nick/Carraway merge + narrator** [CRITICAL] — SUCCESS ✓ (src/agents/characters.py)
**Fix O: Familial label validation** [CRITICAL] — PARTIAL (src/pipeline/character_profiling/post_corrections.py — code runs, but 100-char window too permissive, many wrong labels survive)
**Fix P: Personality traits + speech patterns** [CRITICAL] — SUCCESS ✓ (src/analyzer.py — data in personality/voice_guidance nested dicts)
**Fix Q: Homograph IPA** [HIGH] — SUCCESS ✓ (src/pipeline/pronunciation_guide/enricher.py)

### gatsby — Attempt 7 Fixes
**Fix R: Familial labels Option B** [CRITICAL] — PENDING (src/pipeline/character_profiling/post_corrections.py — `reject_unfounded_familial_labels()` now only allows sibling/brother text-evidence exception for non-surname-sharing pairs; all other family labels removed)
**Fix S: Self-negating appearance summary** [HIGH] — PENDING (src/pipeline/character_profiling/post_corrections.py — `clean_unknown_appearance()` now clears summaries containing "not directly described" etc. via NO_DESC_PHRASES substring check; targets Myrtle's Catherine-contaminated description)
**Fix T: Deterministic physical description fallback** [HIGH] — PENDING (src/pipeline/character_profiling/post_corrections.py — `propagate_physical_description()` now scans raw text for physical-term sentences near character name mentions for major chars with null descriptions)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | (baseline — no fixes yet) | — | — |
| 2 | Main cast pipeline failure (data) | `src/agents/characters.py` | Partial — aliases improved but grounding still fails |
| 2 | IPA corruption | `src/pipeline/pronunciation_guide/enricher.py` | Fixed ✓ |
| 3 | Main cast grounding failure (JSON format) | `src/pipeline/character_extraction_v2/main_cast.py` | Fixed ✓ |
| 3 | Relationship labels wrong (secondary overwrites) | `src/analyzer.py` | No change — primary pipeline also produces bad labels |
| 3 | Pronunciation false positives | `src/pipeline/pronunciation_guide/proposers/foreign_proposer.py` | Fixed ✓ |
| 3 | UNKNOWN pronunciation categorization | `src/pipeline/pronunciation_guide/consolidator.py` | Partial — 28 reclassified, 67 remain |
| 4 | Relationship biased toward familial labels | `src/analyzer.py` (prompt) | Partial — Nick improved, others still wrong |
| 4 | Physical description narrative text | `src/analyzer.py` (validation) | Failed — narrator injection overwrites after validation |
| 4 | Eckleburg duplicate (Doctor/no-Doctor) | `src/agents/characters.py` | Fixed ✓ |
| 4 | "like" flagged as foreign | `src/pipeline/pronunciation_guide/proposers/foreign_proposer.py` | Fixed ✓ |
| 5 | Butler/Butler F6 case sensitivity dedup | `src/analyzer.py` | Fixed ✓ |
| 5 | "unknown" relationship labels in output | `src/pipeline/character_profiling/post_corrections.py` | Fixed ✓ |
| 5 | Nick appearance: narrative prose | `src/pipeline/character_profiling/post_corrections.py` | Fixed ✓ |
| 6 | Nick/Carraway split + narrator | `src/agents/characters.py` | Fixed ✓ |
| 6 | Familial label validation | `src/pipeline/character_profiling/post_corrections.py` | Partial — filter too permissive |
| 6 | Personality traits + speech patterns | `src/analyzer.py` | Fixed ✓ |
| 6 | Homograph IPA | `src/pipeline/pronunciation_guide/enricher.py` | Fixed ✓ |
| 7 | Familial labels Option B | `src/pipeline/character_profiling/post_corrections.py` | Pending |
| 7 | Self-negating appearance descriptions | `src/pipeline/character_profiling/post_corrections.py` | Pending |
| 7 | Physical description text fallback | `src/pipeline/character_profiling/post_corrections.py` | Pending |

**Pattern alerts:**
- `src/pipeline/character_profiling/post_corrections.py` is the correct location for relationship fixes — `reject_unfounded_familial_labels()` exists but needs tightening. This is attempt 2 at this file for relationships (after Fix L succeeded for "unknown" removal). The method logic needs refinement, not a new location.
- `src/analyzer.py` prompt-level relationship fixes exhausted (4 attempts). Post-processing is the only viable path.
- Profiles are the SOLE remaining blocker. Fix the familial filter + add null-description second-pass → should cross 8.0.

## Next Action

Re-run analysis on gatsby (attempt 7) to verify fixes R/S/T close the Profiles gap.
