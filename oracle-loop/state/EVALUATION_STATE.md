# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 22
- **Phase:** awaiting_analysis
- **baseline_score:** 6.55
- **Competitive Mode:** none

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 4.5/10 ✗ (FAILING — father/son merged, "American, sir" regression, Johnny fragment)
  - Completeness: 5/10
  - Identity Resolution: 3/10
  - Alias Grouping: 5/10
- Character Profiles: 4.5/10 ✗ (FAILING — description cross-contamination, null summaries, wrong relationships)
- Chapter Summaries: 5/10 ✗ (FAILING — Uncle Bill conflated with dying father at end)
- Pronunciation Guide: 9/10 ✓
- HTML Presentation: 8.5/10 ✓ (BOM fixed, title fixed)
- **Overall: 6.35/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold)

## Comparison to Attempt 21

| Category | Attempt 21 | Attempt 22 | Delta |
|----------|-----------|-----------|-------|
| Structure | 9 | 9 | 0 |
| Characters | 5 | 4.5 | -0.5 REGRESSION |
| Profiles | 5.5 | 4.5 | -1.0 REGRESSION |
| Summaries | 5 | 5 | 0 |
| Pronunciation | 9 | 9 | 0 |
| Presentation | 7.5 | 8.5 | +1.0 IMPROVEMENT |
| Overall | 6.5 | 6.35 | -0.15 |

**Regressions:** "American, sir" is a SEPARATE character again (was absorbed as alias in attempt 21). Narrator assigned to "American, sir" instead of Uncle Bill. These cascade into worse profiles and relationships.

**Improvement:** HTML title now shows "American, Sir!" instead of author name. BOM removed.

## Current Issues (Priority Order)

### CRITICAL
1. **Father/son merge: John Donaldson father + John son = one character** [Identity Resolution]
   - Problem: The father ("John Donaldson", shabby American civilian, dies on battlefield) and son ("John", beautiful youngster, ambulance driver, Uncle Bill's nephew) are merged into "John (Uncle Bill's son)" with 38 mentions.
   - Evidence: 22 attempts. STEP 3.95/3.95b fires ~50% due to LLM non-determinism. STEP 3.95c (attempt 22 fix) did NOT fire — need to investigate why.
   - Location: `src/agents/characters.py` STEP 3.95/3.95b/3.95c
   - Fix approach: Debug why STEP 3.95c didn't fire. It was supposed to be deterministic (matching "Johnny" via STANDARD_DIMINUTIVES to "John Donaldson" first word). Either the code path wasn't reached, or the matching conditions weren't met.

2. **"American, sir" as separate character — REGRESSION** [Identity Resolution]
   - Problem: "American, sir" (12 mentions, id=main_cast_4) is extracted as a SEPARATE character with narrator=True. In attempt 21, it was correctly absorbed as an alias of John Donaldson.
   - Evidence: This is a dialogue phrase ("American, sir!") that the dying father says. It should be an alias of John Donaldson, not a standalone character.
   - Location: V2 character extraction — Pass 1 extracts it as a character, Pass 2 should merge it but doesn't.
   - Note: This regression may be LLM non-determinism in Pass 1/2 extraction. The code changes from attempt 22 (STEP 3.95c) shouldn't have affected alias absorption.

3. **Wrong narrator: "American, sir" instead of Uncle Bill** [Identity Resolution]
   - Problem: narrator=True on "American, sir" (12 mentions). Uncle Bill (18 mentions) is the actual frame narrator.
   - Evidence: Uncle Bill tells the entire story. "American, sir" is a phrase, not a person narrating.
   - Cascading from issue #2 — if "American, sir" weren't a separate character, it couldn't be assigned as narrator.

### HIGH
4. **Summary hallucination: Uncle Bill dying on battlefield** [Summaries]
   - Problem: Plot summary says "Uncle Bill himself lies dying in a battlefield aid station, confesses his past deception" — FABRICATED. Uncle Bill never goes to any battlefield. The dying man is John Donaldson (the father).
   - Evidence: The summary correctly identifies Donaldson as the father earlier, then conflates Uncle Bill with Donaldson at the end.
   - Location: Summarizer prompt / nested narration confusion
   - Note: This hallucination has persisted across most attempts. It cascades from the character merge — when father/son are merged, the LLM can't keep the narrative layers straight.

5. **Johnny 2-mention fragment** [Completeness]
   - Problem: "Johnny" (id=main_cast_5, 2 mentions) is separate from "John (Uncle Bill's son)" (38 mentions). Johnny is the son's nickname.
   - Evidence: In the story, "Johnny" = the son = John Jr. Should be an alias, not separate.
   - Note: Resolves naturally if father/son split works — Johnny would merge into the son character.

6. **character_summary null for all characters** [Profiles]
   - Problem: All 5 characters have empty character_summary fields.
   - Location: Profile generation in `src/pipeline/character_profiling/` or `src/analyzer.py`
   - Persistent across attempts 21 and 22. May be model/config issue with qwen3-next.

### MEDIUM
7. **Physical description cross-contamination** [Profiles]
   - Problem: "American, sir" got Uncle Bill's physical description ("an elderly, grizzled, small man, grim and unexhilarating"). This is Uncle Bill's description, not the father's.
   - Evidence: The father (John Donaldson) is described as tall, dark-skinned, shabby. Uncle Bill is the elderly grizzled man.
   - Cascades from issue #2 — wrong character gets wrong description.

8. **Relationship confusion** [Profiles]
   - Problem: "American, sir" shows Uncle Bill as "nephew" and John as "uncle" — inverted/wrong relationships caused by the character being misidentified.
   - Cascades from issue #2.

9. **Missing minor characters: Margaret Donaldson, Joe Barron** [Completeness]
   - Both appear in evidence citations but not as extracted characters.
   - Margaret Donaldson is John Jr.'s mother (mentioned by name in text).
   - Joe Barron is John Jr.'s fellow ambulance driver (has direct quotes).
   - F6b should catch these from summary mentioned_characters but didn't in this run.

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.55 | 0 | Baseline |
| 2 | 6.6 | +0.05 | Narrator fix |
| 3 | 6.0 | -0.55 | REGRESSION |
| 4 | 6.4 | -0.15 | Partial fix |
| 5 | 6.7 | +0.15 | Plot summary improved |
| 6 | 7.0 | +0.45 | Uncle Bill narrator |
| 7 | 6.9 | +0.35 | Boy disappeared |
| 8 | 7.85 | +1.30 | Father/son split worked |
| 9 | 8.0 | +1.45 | Cross-character alias fix |
| 10 | 7.0 | +0.45 | REGRESSION — split didn't fire |
| 11 | 7.2 | +0.65 | Mixed |
| 12 | 7.7 | +1.15 | Split via alias contradiction |
| 13 | 5.8 | -0.75 | SEVERE REGRESSION |
| 14 | 7.6 | +1.05 | Split worked |
| 15 | 6.85 | +0.30 | Split didn't fire |
| 16 | 6.95 | +0.40 | No parenthetical |
| 17 | 6.2 | -0.35 | Summary regression |
| 18 | 6.8 | +0.25 | Father/son merged |
| 19 | 7.7 | +1.15 | Split worked (Pattern D) |
| 20 | 5.95 | -0.60 | SEVERE REGRESSION |
| 21 | 6.5 | -0.05 | Narrator ✓, alias ✓, split ✗ |
| 22 | 6.35 | -0.20 | "American, sir" regression. HTML fixed. |

## Fix History
- Attempt 11-20: See previous entries
- Attempt 21: Re-analysis with new config (90b62a5). Narrator and alias absorption improved. Father/son split still not firing.
- Attempt 22: STEP 3.95c added (deterministic sibling-name split). HTML BOM/title fix. STEP 3.95c DID NOT FIRE — father/son still merged. "American, sir" regressed to separate character.

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 2 | Wrong narrator | `narrator.py` | Fixed |
| 3 | Johnny exact_firstname guard | `characters.py` | REGRESSION — REVERTED |
| 4 | Co-present guard Step 5.4.5 | `characters.py` | Partial |
| 5 | Narrator guard / merge direction | `characters.py`, `narrator.py` | Bug/wrong direction |
| 6 | narrator.py detect() crash | `narrator.py` | Fixed |
| 7 | John Donaldson false narrator | `narrator.py` | Fixed |
| 8 | Role assignment / summaries | `characters.py`, `summarizer.py` | Fixed |
| 9 | Cross-character alias / relationships | `main_cast.py`, `analyzer.py` | Partial |
| 11 | STEP 3.95 / relationships / narrator | `characters.py`, `post_corrections.py`, `analyzer.py` | Mixed |
| 12 | STEP 3.95 alias contradiction | `characters.py` | Fixed |
| 13 | force_parenthetical / narrator_instruction | `post_corrections.py`, `generator.py` | Never fired |
| 14 | STEP 3.97 nickname phantom | `characters.py` | Fixed |
| 15 | STEP 5.4.6c / Step 6.6 narrator | `characters.py`, `analyzer.py` | Fixed |
| 16-18 | STEP 3.95/3.95b patterns | `characters.py` | Intermittent |
| 19 | STEP 3.95b Pattern D / narrator survival | `characters.py`, `generator.py` | Fixed |
| 20 | Cross-alias decontamination / parenthetical rel labels | `characters.py`, `post_corrections.py` | UNTESTABLE |
| 21 | Re-analysis with new config (90b62a5) | No code changes | Narrator ✓, alias ✓, split ✗ |
| 22 | STEP 3.95c: kinship-fragment split + HTML fix | `characters.py`, `txt.py`, `base.py` | 3.95c didn't fire. HTML fix ✓. "American, sir" regression. |

**Pattern: STEP 3.95/3.95b fires ~50% of the time. STEP 3.95c (attempt 22, supposedly deterministic) also didn't fire. 22 attempts and the father/son split has succeeded in only 5 (attempts 8, 9, 12, 14, 19).**

**ROOT CAUSE ANALYSIS: After 22 attempts, the father/son split problem has two aspects:**
1. **LLM extraction non-determinism** — Pass 1 sometimes extracts father/son as one character, sometimes as two. No code fix can reliably control this.
2. **Post-extraction split** — STEP 3.95/3.95b/3.95c try to split after extraction, but depend on specific signals (parenthetical text, alias patterns, diminutive matches) that may or may not be present depending on what the LLM produced.

**The fundamental issue is that this is a VERY HARD identity resolution problem — same name (John/John Donaldson), same family, nested narration — and the current approach of post-extraction regex splitting is inherently fragile. A more robust approach would need to either:**
- **Force the LLM** to consider father/son distinctions in Pass 1 (but CLAUDE.md forbids novel-specific prompts)
- **Use physical description contradictions** as a deterministic split signal (elderly/shabby vs young/beautiful for the same character → must be two people)
- **Use narrative role contradictions** (character who both "dies on battlefield" and "tells the story years later" → must be two people)

## Configuration Notes
- Model: qwen3-next:80b-a3b-instruct-q8_0 (all agents)
- Config: max_tokens=8192, context_length=32768, think_mode=false
- No config issues identified — the problems are in character extraction logic, not model configuration.

## Next Action
Re-run analysis to verify fixes.

## Attempt 23 Fix Summary
### Why STEP 3.95c didn't fire (attempt 22)
- "Johnny" (main_cast_5) had NO aliases — the child-tier alias check `if not _child_als_395c: continue` exited early
- STEP 3.95c requires the fragment to have a child-tier alias like "his son" — LLM didn't assign any to "Johnny"

### Why STEP 3.95b didn't fire (attempt 22)
Two issues:
1. Guard `"(" in _char_395b.canonical_name` skipped "John (Uncle Bill's son)" — the "(" was a natural LLM-generated parenthetical, not a split annotation
2. Pattern search used canonical name "John (Uncle Bill's son)" in regex, but summary contains "John Donaldson" (an alias). No pattern matched.

### Fixes applied (attempt 23)
**STEP 3.95b** (`src/agents/characters.py`):
- Removed `"(" in canonical_name` guard → replaced with sibling-ID check `any(c.id == f"{_char_395b.id}_parent" for c in main_cast)`
- Added "revealed to be" to Pattern A introducer list
- Search now iterates over canonical name AND multi-word neutral aliases — covers cases where the parent's formal name is stored as an alias
- Added Pattern E: `NAME...reveals/confesses...he/she is X's...father` with period-permissive character class for titles like "Jr." — handles "John Donaldson...reveals...he is John Jr.'s long-lost father"

**STEP 3.95c + STEP 3.97** (`src/agents/characters.py`):
- Replaced `"(" not in c.canonical_name` guard with `not c.id.endswith("_parent")` in both steps — allows processing characters with natural LLM parentheticals

### Expected behavior in attempt 23
- STEP 3.95b fires: "John (Uncle Bill's son)" has alias "John Donaldson" → Pattern E matches in summary → creates "John Donaldson (the father)"
- STEP 3.97 fires: "Johnny" (2 mentions, nickname for "john") → merges as alias of "John (Uncle Bill's son)"
- Narrator detection: with proper split, Uncle Bill should be correctly identified as narrator
