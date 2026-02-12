# Current Evaluation State

## Active Text
- **Name:** cask_of_amontillado
- **Attempt:** 5
- **Phase:** awaiting_fix
- **baseline_score: 6.75**
- **Competitive Mode:** single

## Output Files
- HTML: ../output/cask_of_amontillado/report.html
- JSON: ../output/cask_of_amontillado/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 6.5/10 ✗ (FAILING)
- Character Profiles: 4/10 ✗ (FAILING)
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 6/10 ✗ (FAILING)
- HTML Presentation: 8.5/10 ✓
- **Overall: 7.18/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.75 | 0.0 | Baseline. 5 bogus supporting chars, Fortunato profile is Montresor's |
| 2 | 6.65 | -0.10 | Bogus chars fixed (+1), but Montresor still missing. Fortunato profile improved but still has issues |
| 3 | 7.58 | +0.83 | Montresor now in character list (fallback worked), but profile generation failed. F6 still broken. |
| 4 | 7.40 | +0.65 | Attempt 4 fix introduced NEW error (Character constructor missing `supporting_strategies`). Same symptoms as attempt 3. Pronunciation false positive rate increased. |
| 5 | 7.18 | +0.43 | `supporting_strategies` fix applied but F6 now fails with NEW error (`MentionResult.total_count`). Narrator fallback fails with `CharacterMention.chapter_idx`. Montresor STILL missing. Regression from attempt 3. |

## Current Issues (Priority Order)

### CRITICAL

1. **Montresor missing from character list — F6 and narrator fallback BOTH crash with different errors (5th consecutive attempt)**
   - Problem: Montresor, the protagonist and first-person narrator, is not in the character list. Only 2 characters extracted (Fortunato and Luchresi).
   - Evidence: `pipeline_metadata.narrator_name = "Montresor"` and `characters_present = ["Montresor", "Fortunato"]` in chapter summary, but Montresor is not in the `characters` array.
   - **F6 error**: `'MentionResult' object has no attribute 'total_count'` (per EVALUATION_STATE notes from analyze phase)
   - **Narrator fallback error**: `'CharacterMention' object has no attribute 'chapter_idx'` (per EVALUATION_STATE notes from analyze phase)
   - **ROOT CAUSE ANALYSIS**: The attempt 4 fix added `MentionSearcher` usage to populate narrator fallback data, but the objects returned by `MentionSearcher` (`MentionResult`, `CharacterMention`) don't have the attributes the code expects. This has been a recurring pattern — the code keeps guessing at class APIs without reading their definitions.
   - **FIX APPROACH — THE FIX PHASE MUST:**
     1. **Read the actual class definitions** for `MentionResult` and `CharacterMention` (likely in `src/pipeline/character_extraction_v2/` or `src/models.py`) to see their actual attributes
     2. **Read the `MentionSearcher` class** to understand what it returns and what attributes are available
     3. **Find working examples** of how `MentionResult`/`CharacterMention` are used elsewhere in the codebase (grep for attribute access patterns)
     4. Fix the attribute access in both F6 reconciliation AND narrator fallback to use correct attribute names
     5. **If MentionSearcher is too complex to integrate correctly**, consider a SIMPLER fallback: just create a minimal Character object with the narrator name, basic role, and let the profiling pipeline fill in the rest. The attempt 3 approach (before MentionSearcher was added) at least got Montresor into the character list with `mention_count: 1`.
   - Impact: -3.5 on Character Profiles (protagonist has no profile), -1.5 on Character Extraction (protagonist missing entirely)
   - Location: `src/analyzer.py` — F6 reconciliation block (~line 1640-1720) and narrator fallback block (~line 1769-1807)
   - **ESCALATION NOTE**: This is the SAME core issue for the **5th consecutive attempt**. `src/analyzer.py` has been modified in attempts 3, 4, and 5 without successfully getting Montresor into the character list with a working profile. Each fix introduces a NEW AttributeError because the code doesn't read the class definitions before using them. **The fix phase MUST read the source code of `MentionSearcher`, `MentionResult`, and `CharacterMention` before writing any code.**

### HIGH

2. **Pronunciation false positive rate ~38% (14 of 37 entries are common words)**
   - Problem: These entries are common English words a narrator doesn't need help pronouncing:
     - Common hyphenated compounds: "tight-fitting", "web-work", "mason-work"
     - Archaic spelling of obvious word: "to-day"
     - Common English words: "cough's", "leer", "Grave"
     - Standard prefixed words: "Unsheathing", "reapproached", "re-echoed", "re-erected"
     - Redundant: "Montresors" (plural of already-listed "Montresor")
     - OCR artifact: "himselffelt" (fused "himself felt")
     - Arguably common: "unredressed", "gesticulation"
   - Good entries (23 of 37): Character names, Amontillado, flambeaux, nitre, roquelaire, connoisseurship, gemmary, puncheons, requiescat, impune, lacessit, hearken/hearkened, parti-striped, rheum, imposture, flagon, homographs
   - Location: `src/pipeline/pronunciation/` — the flagging prompt needs exclusion guidance
   - Fix: Add to the pronunciation flagging prompt instructions to NOT flag:
     - Simple hyphenated compounds of common English words (tight-fitting, web-work, mason-work)
     - Common English words with obvious pronunciation (leer, cough's, Grave)
     - Words with standard English prefixes re-/un- where pronunciation is obvious
     - Archaic hyphenated spellings of common words (to-day = today)
     - Plurals/possessives of names already in the list
     - OCR artifacts (strings that appear to be fused/concatenated words)
   - Impact: Score -2 on Pronunciation
   - **NOTE**: This is a prompt improvement, not a keyword deny-list. Per USER_NOTES.md, keyword lists are forbidden.

3. **Fortunato's role labeled "antagonist" — he is the victim**
   - Problem: In "The Cask of Amontillado," Montresor is the villain-protagonist who murders Fortunato. Fortunato is the victim. Labeling Fortunato "antagonist" is misleading.
   - Evidence: Fortunato is lured into the catacombs and sealed alive. He commits no villainous acts.
   - Location: Role assignment in character extraction pipeline
   - Impact: Score -0.5 on Character Extraction
   - Note: This is an LLM judgment call that may improve when Montresor gets properly extracted as protagonist. **Deprioritize — fix CRITICAL #1 first.**

### MEDIUM

4. **Fortunato personality_summary, personality_traits, and temperament are null**
   - Problem: While Fortunato has appearance data and voice_guidance, personality fields are completely empty.
   - Evidence: `personality_summary: null`, `personality_traits: null`, `temperament: null` in analysis.json. The HTML report does show a "Personality" section but it appears to be auto-generated from other fields rather than the dedicated personality extraction.
   - Location: Character profiling pipeline — personality extraction stage
   - Impact: Score -0.5 on Character Profiles
   - Note: The personality_summary shown in the HTML ("Fortunato is a villainous antagonist whose arrogance and pride make him vulnerable...") appears to come from the `appearance.summary` or a generated fallback, not the dedicated personality fields.

5. **Relationship labels oversimplified — all "rival"**
   - Problem: Fortunato→Montresor: "rival", Luchresi→Fortunato: "rival". None are accurate:
     - Fortunato→Montresor: friend/acquaintance (Fortunato doesn't know Montresor plans murder)
     - Luchresi→Fortunato: professional competitor in wine connoisseurship
   - Location: Relationship extraction in character profiling pipeline
   - Impact: Score -0.5 on Character Profiles

6. **Narrative style inconsistency in overview**
   - Problem: `overview.structure.narrative_style` says "unknown" while `overview.plot_summary.narrative_style` correctly says "first-person retrospective"
   - Location: `src/analyzer.py` — structure overview generation
   - Impact: Minor (-0.5 on Structure Detection)

### LOW

7. **Missing pronunciation: "In pace requiescat" (full Latin phrase)**
   - Note: "requiescat" alone IS flagged with IPA. Full phrase context would be nice-to-have.

8. **Homographs "row", "close", "entrance" lack IPA (by design)**
   - Note: Correct behavior — context-dependent notes provided instead. No fix needed.

## What Needs to Happen to Pass

To cross 8.0 in all three failing categories:

1. **Character Profiles (4 → 8): THE BIGGEST GAP — fix CRITICAL #1**
   - Montresor MUST get a proper profile. He needs:
     - Appearance: black silk mask, roquelaire (short cloak)
     - Personality: cold, calculating, vindictive, patient, darkly ironic
     - Speech patterns: formal, ironic, manipulative, uses polite concern as weapon
     - Voice guidance: controlled, chilling narration that reveals calculation
     - Relationships: Fortunato (acquaintance/victim)
   - Fortunato also needs personality_summary populated (currently null)

2. **Character Extraction (6.5 → 8): Get Montresor into the character list**
   - Currently missing entirely — should be listed as protagonist/narrator
   - Will be fixed when F6/narrator fallback successfully creates a Character object
   - Fortunato's role should ideally switch from "antagonist" to "victim" or similar

3. **Pronunciation (6 → 8): reduce false positive rate from 38% to <15%**
   - Remove/don't flag ~10 common words
   - Remove OCR artifact "himselffelt"
   - Keep all the good entries (23 genuinely useful pronunciation aids)

**Priority:** CRITICAL #1 is the single most impactful fix. Getting Montresor into the character list with a proper profile would push Character Profiles from 4 to ~7-8 and Character Extraction from 6.5 to 8+. Pronunciation fix is independent and can be done in parallel.

**MANDATORY FOR FIX PHASE:** Before writing ANY code that touches `MentionSearcher`, `MentionResult`, or `CharacterMention`, the fix phase MUST:
1. `grep -rn "class MentionResult" src/` to find the definition
2. `grep -rn "class CharacterMention" src/` to find the definition
3. `grep -rn "class MentionSearcher" src/` to find the definition
4. Read those class definitions to understand the actual API
5. Find at least ONE working usage example in the codebase
6. Only THEN write the fix using correct attribute names

## Configuration Audit

### Model Configuration
- All agents use `qwen3-next:80b-a3b-instruct-q8_0` — appropriate per user configuration
- Temperature 0.7 for all — acceptable
- Context length 32768 — sufficient for this short story

### Chunking Configuration
- `character_llm_chunk_chars: 5000` — fine for a ~13K character story (2-3 chunks)
- `summary_chunk_words: 2500` — appropriate, story fits in one chunk

### Processing Issues
- 0 LLM retries, 0 JSON parse failures — model worked cleanly for all stages
- F6 reconciliation crashes with `'MentionResult' object has no attribute 'total_count'`
- Narrator fallback crashes with `'CharacterMention' object has no attribute 'chapter_idx'`
- Character profiling ran but produced null personality for Fortunato, no entry for Montresor
- 2 JSON parse failures in Pronunciation (for "himselffelt" and batch enrichment)

## Fix History

### Attempt 2 Fixes Applied
1. **CRITICAL #1 (old): Fortunato personality profile contamination - FIXED (VERIFIED)**
   - Root cause: `src/analyzer.py:1828` - narrative_style set to "unknown" instead of "first-person"
   - Fix: Changed narrative_style detection to use text-based analysis
   - Result: **FIXED** — Fortunato personality now correctly about Fortunato.

2. **CRITICAL #2 (old): 5 bogus supporting characters - FIXED (VERIFIED)**
   - Root cause: `src/pipeline/character_extraction_v2/grounding.py:24-36` - adaptive_min_mentions() returned 1
   - Fix: Raised floor from 1 to 2
   - Result: **FIXED** — All 5 bogus characters removed.

### Attempt 3 Fixes Applied
1. **CRITICAL: Montresor missing from character list - PARTIALLY FIXED**
   - Fix 1 (typo `document` → `doc`): Applied but F6 still fails with new error (`ExtractedDocument` has no `normalized_text`)
   - Fix 2 (narrator fallback): **WORKS** — Montresor added to character list successfully
   - BUT: Profile generation failed for Montresor (empty profile). The fallback creates a minimal Character object that the profiling pipeline can't work with.
   - Fortunato's clothing contamination (black silk mask/roquelaire) is FIXED — no longer appears in Fortunato's profile.

### Attempt 4 Fixes Applied
1. **CRITICAL #1 (F6 reconciliation and narrator fallback) - FAILED**
   - **Fix 1:** Changed `doc.normalized_text` → `doc.text` at line 1648
   - **Fix 2:** Modified narrator fallback to use `MentionSearcher` to populate real mention data
   - **Result:** Both fixes introduced NEW error: `Character.__init__() missing 1 required positional argument: 'supporting_strategies'`
   - The Character constructor signature was not checked before modifying the constructor calls
   - **Smoke test passed** (298 tests) but the error only manifests at runtime during analysis, not in unit tests

### Attempt 5 Fixes Applied
1. **CRITICAL #1 (Character constructor missing supporting_strategies) - FIXED but new errors revealed**
   - **Fix:** Added `supporting_strategies=[]` to both temp_char and temp_narrator Character constructors
   - **Result:** `supporting_strategies` error is gone, but TWO NEW attribute errors surfaced:
     - F6: `'MentionResult' object has no attribute 'total_count'`
     - Narrator fallback: `'CharacterMention' object has no attribute 'chapter_idx'`
   - These errors were hidden behind the `supporting_strategies` error before. They originate from the attempt 4 `MentionSearcher` integration which was never properly validated.

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 2 | Fortunato personality contamination | `src/analyzer.py` | Fixed — personality now correct |
| 2 | Bogus supporting characters | `src/pipeline/character_extraction_v2/grounding.py` | Fixed — 5 bogus chars removed |
| 3 | F6 reconciliation crash (`document` typo) | `src/analyzer.py:1648` | Partially fixed — new error revealed |
| 3 | Narrator not added to character list | `src/analyzer.py:1769-1807` | Fixed — fallback works, but profile fails |
| 4 | F6 reconciliation AttributeError | `src/analyzer.py:1648` | Fixed attribute name — but new constructor error |
| 4 | Narrator fallback missing mention data | `src/analyzer.py:1784-1807` | MentionSearcher added — but Character constructor error + wrong attribute access |
| 5 | Character constructor missing `supporting_strategies` | `src/analyzer.py:1662, 1802` | Fixed constructor — but MentionSearcher attribute errors now visible |

**Pattern detected:** `src/analyzer.py` has been modified 5 times for the same root issue. Each fix reveals another layer of AttributeErrors because the code is guessing at class APIs. The fix phase MUST read class definitions before writing code.

## Next Action
Run PROMPT_fix.md to address:
1. **CRITICAL #1**: Read `MentionSearcher`, `MentionResult`, `CharacterMention` class definitions, then fix attribute access in F6 reconciliation and narrator fallback. **OR** simplify by reverting to the attempt 3 approach (minimal Character object) which at least got Montresor into the list.
2. **HIGH #2**: Improve pronunciation flagging prompt to reduce false positives.
