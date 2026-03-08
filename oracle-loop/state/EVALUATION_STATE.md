# Current Evaluation State

## Active Text
- **Name:** gatsby
- **Attempt:** 2
- **Phase:** awaiting_fix
- **baseline_score:** 5.90

## Output Files
- HTML: ../output/gatsby/report.html
- JSON: ../output/gatsby/analysis.json

## Latest Scores
- Structure Detection: 10/10 ✓
- Character Extraction: 4.5/10 ✗
  - Completeness: 7/10
  - Identity Resolution: 3/10
  - Alias Grouping: 6/10
- Character Profiles: 3/10 ✗
- Chapter Summaries: 8/10 ✓
- Pronunciation Guide: 7/10 ✗
- HTML Presentation: 8.5/10 ✓
- **Overall: 6.73/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 5.90 | - | Baseline. Profiles catastrophic, character identity broken |
| 2 | 6.73 | +0.83 | Relationships partially improved for main cast. Core narrator/Gatsby issues UNFIXED |

## Current Issues (Priority Order)

### CRITICAL

1. **False narrator: Doctor T. J. Eckleburg still tagged as narrator — Fix A ineffective** [Identity Resolution]
   - Problem: `main_cast_11` "Doctor T. J. Eckleburg" has `is_narrator: true`. Nick Carraway (`main_cast_0`) has `is_narrator: false`.
   - Why Fix A failed: Pipeline notes confirm "Narrator already identified by V2 pipeline: Doctor T. J. Eckleburg (skipping re-detection)". The V2 pipeline (`src/pipeline/character_extraction_v2/`) sets the narrator BEFORE `characters.py` runs, and `characters.py` sees an already-set narrator and skips its own detection (STEP 4.26 threshold change never fires).
   - Fix approach: The fix must be in the V2 pipeline itself, not in characters.py. Find where V2 sets `is_narrator=True` and fix the heuristic there. A billboard/symbolic entity (5 mentions) should never be chosen as narrator over a first-person pronoun character like Nick. Alternatively, the "skip re-detection" guard in characters.py should be removed or weakened so its improved logic can override bad V2 narrator picks.
   - Location: Search `src/pipeline/character_extraction_v2/` for narrator assignment logic; also check `src/agents/characters.py` for the "Narrator already identified by V2 pipeline" skip guard

2. **Protagonist in wrong cast tier: Gatsby still `supporting_14` "James Gatz" with role "minor" — Fix B ineffective** [Identity Resolution]
   - Problem: Jay Gatsby (269 mentions — THE most mentioned character) remains in supporting cast as "James Gatz" with role "minor". He has zero profile data (null physical_description, null speech_pattern, null personality_traits) and ALL 23 relationships are "colleague".
   - Why Fix B failed: STEP 5.11 was supposed to re-check supporting characters after alias-aware mention counts. Either: (a) the code isn't being reached, (b) the mention count threshold isn't being met, or (c) the canonical name rename logic isn't firing. The pipeline notes say "BLOCKED alias" still fires in Pass 2, suggesting James Gatz and Jay Gatsby are still treated as potentially separate characters.
   - Fix approach: Debug why STEP 5.11 isn't promoting. Add logging. The 269 mentions >> 200 threshold should easily trigger promotion. If STEP 5.11 code exists but isn't executing, there may be an early return or the supporting character list isn't being iterated.
   - Location: `src/agents/characters.py` STEP 5.11

3. **Gatsby's profile is completely empty** [Profiles]
   - Problem: James Gatz (Gatsby) — the title character with 269 mentions — has: physical_description=null, speech_pattern=null, personality_traits=null, and ALL 23 relationships labeled "colleague".
   - Root cause: As a `supporting_14` "minor" role character, the profiler likely generates minimal/no profiles for supporting-minor characters. The profiler may also fail to match "James Gatz" to text passages about "Gatsby" or "Jay Gatsby".
   - Fix: This issue is downstream of Critical #2. Once Gatsby is correctly promoted to main cast with canonical name "Jay Gatsby", the profiler should generate a full profile.
   - Location: Downstream of `src/agents/characters.py` → `src/analyzer.py` profile generation

### HIGH

4. **Relationship labels still broken for several pairs** [Profiles]
   - Problem: Fix C partially worked — main cast core relationships improved (Daisy→Tom "spouse", Tom→Gatsby "rival"). But several wrong labels remain:
     - Nick → Mr. Sloane: "wife" (nonsensical)
     - Tom → George Wilson: "husband" (should be none or "business contact")
     - Myrtle → Catherine: "husband" (should be "sister" — Catherine is Myrtle's sister)
     - Tom → Daisy: "husband" (correct meaning but should be "spouse" for consistency)
     - "colleague" used as default filler for ~80% of all relationships
   - Location: `src/pipeline/character_profiling/post_corrections.py` — the "husband" override still leaks through in some cases; also the LLM profile prompt produces "colleague" as catch-all
   - Fix: The "colleague" spam is an LLM prompt issue — the profiler prompt likely instructs listing all relationships, and the LLM defaults to "colleague" when no real relationship exists. Fix: instruct the LLM to OMIT characters with no meaningful relationship rather than listing them as "colleague". The remaining "husband"/"wife" mislabels suggest the co-mention window is still picking up spousal terms near unrelated character pairs.

5. **"George B. Wilson" — fabricated middle initial** [Identity Resolution]
   - Problem: `main_cast_6` canonical name is "George B. Wilson" but Fitzgerald never uses a middle initial. The text uses "George Wilson" and "Wilson".
   - Location: V2 Pass 1 extraction — the LLM hallucinated the middle initial
   - Fix: Post-extraction validation could check if middle initials appear in the source text

6. **Owl-eyed man duplicated as two F6 entries** [Identity Resolution]
   - Problem: `048c90e0dfda` "Owl-eyed man" and `3e931d5e0f1f` "the drunken guest with owl-eyed spectacles" — same character
   - Location: F6 reconciliation in `src/analyzer.py` — no dedup of descriptive entries
   - Fix: F6 should check substring/semantic overlap before creating new entries

7. **F6 generic descriptor clutter** [Completeness]
   - Problem: butler (20 mentions), chauffeur (10), gardener (5), reporter (2), war veteran (1) — generic occupational roles, not named characters
   - Location: F6 reconciliation in `src/analyzer.py`
   - Fix: Filter single-word lowercase occupational descriptors in F6

8. **Speech patterns null for ALL characters** [Profiles]
   - Problem: Zero speech_pattern entries across all 27 characters
   - Notable missing: Gatsby's "old sport" catchphrase, Wolfshiem's dialect ("Oggsford", "gonnegtion"), Tom's aggressive/domineering tone
   - Location: Profile generation prompt in `src/analyzer.py` — likely not requesting speech patterns or the LLM ignores that field
   - Fix: Ensure the profile prompt explicitly asks for speech patterns, verbal tics, and distinctive phrases

### MEDIUM

9. **"Buchanan" alias shared between Tom and Daisy** [Alias Grouping]
   - Problem: Both main_cast_2 (Daisy) and main_cast_3 (Tom) have "Buchanan" as alias
   - Fix: Remove shared surname alias when multiple characters claim it

10. **Chapter 1 summary has doubled name** [Summaries]
    - Problem: "Nick Carraway, Nick Carraway, reflecting on..." — name repeated
    - Location: Summary generation or post-processing concatenation

11. **Common English words in pronunciation guide** [Pronunciation]
    - Problem: "chauffeur", "scepticism", "silhouette" etc. are standard English, not unusual
    - Location: `src/pipeline/pronunciation/cmu_proposer.py` COMMON_WORDS_WHITELIST

### LOW

12. **"The green light" relationships nonsensical** [Profiles]
    - Daisy → green light: "colleague"; the green light shouldn't have relationship entries at all
    - Symbolic entities should have relationships stripped or flagged differently

## Fix History

### Attempt 2 fixes (applied, PARTIALLY effective)

**Fix A: False narrator threshold in characters.py** — INEFFECTIVE
- Changed STEP 4.26 threshold from <=2 to <=5
- Result: No change. V2 pipeline sets narrator before characters.py runs; characters.py skips re-detection entirely.
- Root cause: Fix was in the wrong layer. Must fix V2 narrator assignment directly.

**Fix B: STEP 5.11 final promotion pass** — INEFFECTIVE
- Added post-alias promotion logic for supporting characters with >= 200 mentions
- Result: James Gatz still supporting_14 with role "minor". STEP 5.11 either not reached or not firing.
- Root cause: Needs debugging — the threshold should easily be met with 269 mentions.

**Fix C: Relationship label override guard** — PARTIALLY EFFECTIVE
- Changed post_corrections.py to only override when both current and found are family labels
- Result: Core main-cast relationships improved (Daisy→Tom "spouse", Tom→Gatsby "rival"). But "husband"/"wife" mislabels remain for some pairs, and "colleague" spam is unchanged (LLM prompt issue, not post-correction).

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 2 | False narrator (Eckleburg) | `src/agents/characters.py` (STEP 4.26 threshold) | No change — wrong layer |
| 2 | Gatsby wrong cast tier | `src/agents/characters.py` (STEP 5.11 new) | No change — code not firing |
| 2 | Relationship labels all "husband" | `src/pipeline/character_profiling/post_corrections.py` | Partial fix — main cast improved, "colleague" spam unchanged |

**Pattern detected:** Fixes in `src/agents/characters.py` are not effective because V2 pipeline decisions override them. Critical narrator and cast-tier issues must be fixed in `src/pipeline/character_extraction_v2/` directly.

## Configuration Audit
- Model: `qwen3-next:80b-a3b-instruct-q8_0` for all agents (think_mode: false)
- Context length: 32768 — adequate for Gatsby's chapter sizes
- Temperature: 0.7 — reasonable
- Zero LLM retries — no prompt/schema failures
- No chunking issues apparent

## Next Action
Run PROMPT_fix.md to address:
1. **V2 narrator assignment** — fix in `src/pipeline/character_extraction_v2/` (not characters.py)
2. **Debug STEP 5.11** — why isn't 269-mention James Gatz being promoted?
3. **"colleague" relationship spam** — fix profiler prompt to omit non-relationships
4. **Speech patterns** — ensure profiler prompt requests them
