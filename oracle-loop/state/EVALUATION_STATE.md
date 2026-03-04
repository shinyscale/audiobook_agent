# Current Evaluation State

## Active Text
- **Name:** cask_of_amontillado
- **Attempt:** 1
- **Phase:** awaiting_analysis
- **baseline_score:** 5.95
- **Competitive Mode:** none

## Output Files
- HTML: ../output/cask_of_amontillado/report.html
- JSON: ../output/cask_of_amontillado/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 4/10 ✗ (FAILING)
  - Completeness: 7/10
  - Identity Resolution: 3/10 ← narrator/protagonist swap is catastrophic
  - Alias Grouping: 5/10
- Character Profiles: 3/10 ✗ (FAILING)
- Chapter Summaries: 8/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 8/10 ✓
- **Overall: 5.95/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold: Character Extraction, Character Profiles)

## Current Issues (Priority Order)

### CRITICAL

1. **Narrator misattribution: Fortunato marked as narrator instead of Montresor** [Identity Resolution]
   - Problem: `Fortunato` has `is_narrator: true` (ID: `main_cast_1`). Montresor is the actual first-person narrator.
   - Evidence: The story opens "THE thousand injuries of Fortunato I had borne" — the "I" is Montresor. Fortunato never narrates.
   - Root cause: Montresor only has 3 mentions by name (first-person narrator refers to himself as "I" not "Montresor"). The pipeline assigned narrator to the highest-mention character instead of recognizing the actual narrator.
   - Location: Narrator detection in `src/pipeline/character_extraction_v2/` — likely the narrator heuristic that falls back to highest-mention character. Also `src/agents/characters.py` STEP 5.8.6 heuristic.
   - Fix: The narrator detection must recognize that in first-person narration, the narrator's name appears rarely (others address them). Montresor IS named in the text — "For the love of God, Montresor!" — and the summary correctly identifies "the narrator" as the revenge-seeker. The F6 reconciliation added Montresor but didn't flag it as narrator.

2. **Montresor demoted to supporting cast with only 3 mentions** [Identity Resolution]
   - Problem: Montresor (ID: `e3bdcd5e8982` — F6 hash) has only 3 mentions and is in supporting cast. As the narrator/protagonist of a first-person story, he should be the primary character.
   - Evidence: Montresor narrates the entire story. His name appears rarely because he uses "I" — but he IS the story.
   - Location: F6 reconciliation in `src/agents/characters.py` added him but with raw NER mention count (3). First-person narrators in short stories may only be named 1-3 times by other characters.
   - Fix: When narrator is identified, ensure they are promoted to main_cast regardless of mention count. The narrator of a first-person story should have elevated status even if named rarely.

3. **Fortunato's profile describes Montresor** [Profiles]
   - Problem: Fortunato's personality says "vengeful, calculating, duplicitous... plotting murder." His voice guidance says "Calm, authoritative, and deceptive." His traits are "vengeful, calculating, duplicitous, manipulative, proud."
   - Evidence: Fortunato is the VICTIM — a proud wine connoisseur in a jester costume who is lured to his death. The vengeful plotter is Montresor.
   - Root cause: Because Fortunato was misidentified as narrator, the profiler generated Montresor's profile under Fortunato's name (the profiler's first-person attribution logic assumed "I" references = this character).
   - Location: `src/agents/characters.py` or `src/analyzer.py` `_generate_character_profile()` — cascading from issue #1.
   - Fix: Fixing narrator attribution (#1) should cascade to fix this automatically.

4. **Self-relationship: Fortunato lists "Fortunato (enemy)"** [Alias Grouping / Profiles]
   - Problem: Fortunato's relationships include `"Fortunato": "enemy"` — a character related to itself.
   - Evidence: This is a data integrity error. No character should appear in its own relationship map.
   - Location: Profile generation in `src/analyzer.py` `_generate_character_profile()` or relationship verification in `src/pipeline/post_corrections.py`.
   - Fix: Filter self-references from relationship maps during profile generation or post-processing.

### HIGH

5. **"the Montresors" extracted as separate character** [Completeness]
   - Problem: "the Montresors" (ID: `7ee470116aa7`, 2 mentions) is listed as a separate supporting character. This is a family reference ("a great and numerous family"), not an individual.
   - Evidence: The text says "the Montresors... were a great and numerous family" — this is a collective noun/family reference.
   - Location: Plural group noun detection. Memory notes mention Rule 0.6 blocks plural agent/role suffixes, but "Montresors" is a proper-noun plural, not a descriptor.
   - Fix: Plural forms of character surnames should be merged into the singular character or filtered. "the Montresors" should become an alias of "Montresor" or be dropped entirely.

6. **Relationships inaccurate across all characters** [Profiles]
   - Problem: Montresor↔Fortunato labeled "rival" — they are not rivals. Montresor secretly murders Fortunato. Fortunato considers Montresor a friend. Luchresi↔Fortunato labeled "friend" — Luchresi is a professional rival/competitor in wine expertise, not a friend.
   - Evidence: Montresor says "You are happy, as once I was" — there's no rivalry. The relationship is deceiver/victim. Luchresi is mentioned as competition ("Luchresi cannot tell Amontillado from Sherry").
   - Location: `src/analyzer.py` `_generate_character_profile()` relationship generation.
   - Fix: Cascading from narrator fix should help. Relationship labels like "rival" are too simplistic — but within the system's vocabulary, "enemy" (one-directional: Montresor→Fortunato) and "acquaintance" or "associate" (Fortunato→Montresor, unaware) would be more accurate.

### MEDIUM

7. **No physical descriptions for any character** [Profiles]
   - Problem: All four characters have `physical_description: null`.
   - Evidence: The text describes Fortunato: "He had on a tight-fitting parti-striped dress, and his head was surmounted by the conical cap and bells." Montresor: "I put on a mask of black silk, and drawing a roquelaire closely about my person."
   - Location: `src/analyzer.py` `_generate_character_profile()`.
   - Fix: The profiler should extract these physical details from the text. May be related to the "No passages provided" warning in pipeline notes — if no text passages are sent to the profiler, it can't extract descriptions.

8. **Missing quote attribution — "For the love of God, Montresor!" assigned to Fortunato's profile as narrator** [Profiles]
   - Problem: The example quote "For the love of God, Montresor!" is listed under Fortunato (labeled as narrator). This is actually FORTUNATO's desperate plea to Montresor. When the narrator swap is fixed, this quote should still be associated with Fortunato as his dialogue, not Montresor.
   - Fix: Cascading from narrator fix.

### LOW

9. **Structure title is null**
   - Problem: The single section has `title: null`. Could display the story title "The Cask of Amontillado" or at minimum a section identifier.
   - Location: `src/pipeline/chapter_detection/consensus.py`
   - Fix: For single-section texts with no chapter markers, use the filename or detected title as the section title.

## Fix History

### Fix Attempt 1

**Issues addressed:** Critical #1+2 (narrator misattribution), Critical #4 (self-relationship), HIGH #3 cascade (profiles)

**Root cause:** V2 pipeline extracted only Fortunato as main_cast (14 mentions). When narrator detection ran with only Fortunato available, the LLM assigned Fortunato as narrator (forced choice). Montresor (3 mentions, narrator who uses "I") was not extracted by any stage — he was only added by F6 reconciliation after character extraction completed.

**Fix:** Two new algorithmic steps in `src/agents/characters.py`:
1. **STEP 4.25 (Vocative-based narrator correction):** After narrator detection, if pov=first-person and the assigned narrator has more mentions than ALL other main-cast characters (anomalous for a narrator), run vocative pattern search (`_find_narrator_name_from_vocative`). If a different name is found with fewer mentions, reset the narrator assignment and set narrator_name to the vocative name. This correctly identifies "Montresor" from "For the love of God, Montresor!" (1 occurrence, 1 total mention < Fortunato's 14).
2. **STEP 5.8.5c (Create narrator character):** If narrator_name is known (from STEP 4.25 or STEP 4) but narrator_character_id is None (not found in supporting_cast), verify the name exists in raw text (>=1 mention) and create a proper Character object. This ensures Montresor appears as a proper main_cast character (not an F6 hash added later).

**Self-relationship fix:** `src/analyzer.py` — filter self-references from relationship maps at both assignment sites (lines ~2051 and ~2282). A character cannot appear in its own relationship dict.

**Files modified:**
- `src/agents/characters.py` — STEP 4.25 + STEP 5.8.5c
- `src/analyzer.py` — self-relationship filter

**Smoke test:** PASS
- Vocative detection correctly finds "Montresor" from "For the love of God, Montresor!" (1 vocative occurrence)
- narrator_suspiciously_high fires: Fortunato (14) > Montresor (1) ✓
- STEP 5.8.5c creates Montresor with mention_count=1, is_narrator=True ✓
- Profile generation has special handling for is_narrator=True with total_mentions<3 (samples broadly) ✓
- Berenice regression check: Egaeus (1 mention) < Berenice (14 mentions) → narrator_suspiciously_high=False → no correction ✓
- Monkey's Paw: third-person → STEP 4.25 skipped (pov check) ✓
- All 332 tests pass ✓

**Expected cascade:** Fortunato → not narrator (clean profile), Montresor → narrator protagonist (proper profile), self-relationship Fortunato→Fortunato removed.

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | Narrator misattribution + self-relationship | `src/agents/characters.py`, `src/analyzer.py` | awaiting analysis |

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 5.95 | — | Narrator misattribution cascades to profiles |

## Configuration Audit
- Models: qwen3.5:35b-a3b (structure, pronunciation), qwen3.5:122b-a10b (characters, summaries) — appropriate
- think_mode: false — correct for qwen3.5
- 21 LLM calls, 42,713 tokens — reasonable for a short story
- "No passages provided" warnings for Montresor and the Montresors suggest the profiler passage retrieval failed for F6-reconciled characters

## Next Action
Re-run analysis to verify narrator fix cascade (Montresor → narrator, Fortunato → victim, profiles corrected).
