# Current Evaluation State

## Active Text
- **Name:** berenice
- **Attempt:** 4
- **Phase:** awaiting_evaluation
- **baseline_score:** 8.68
- **Competitive Mode:** none

## Output Files
- HTML: ../output/berenice/report.html
- JSON: ../output/berenice/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 8/10 ✓
  - Completeness: 8.5/10
  - Identity Resolution: 7.5/10
  - Alias Grouping: 8/10
- Character Profiles: 7/10 ✗ (FAILING)
- Chapter Summaries: 9.5/10 ✓
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 9/10 ✓
- **Overall: 8.45/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (1 category below threshold: Character Profiles)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1       | 8.68  | —                   | Profiles fail: "cousin" relationship becomes "associated" in output |
| 2       | 8.43  | -0.25               | Profiles fail: narrator co-mention guard applied; relationship STILL "associated" |
| 3       | 8.45  | -0.23               | Profiles fail: extract_relationships_from_evidence() upgraded but fix misses because evidence statement with "cousin" doesn't name Berenice |

## Current Issues (Priority Order)

### CRITICAL
(none)

### HIGH
1. **Egaeus↔Berenice relationship is "associated" instead of "cousin"** [Profiles]
   - **WHY ATTEMPT 3 FIX FAILED:** `extract_relationships_from_evidence()` scans each `evidence` statement for co-mentions of other characters + relationship keywords. But the evidence statement containing "cousin" is:
     > "Egaeus describes himself as reclusive and meditative, contrasting with **his cousin**."
     This does NOT name "Berenice" — it just says "his cousin." So the regex `\bBerenice\b` never matches this statement.
   - The evidence statements that DO mention "Berenice" are:
     > "Egaeus becomes obsessed with Berenice's teeth..." → no family term → "associated"
     > "Egaeus is informed of Berenice's death by a servant." → no family term → "associated"
   - **WHERE THE DATA ACTUALLY IS:** The `descriptions` field for Egaeus contains:
     > "He contrasts his gloomy, meditative existence with the vibrant life of **his cousin Berenice**"
     This has BOTH "cousin" AND "Berenice" in the same text. But `extract_relationships_from_evidence()` only scans `char.evidence`, NOT `char.descriptions`.
   - **FIX:** Extend `extract_relationships_from_evidence()` to ALSO scan the `descriptions` field. Each description is a dict with a `text` key. Process them the same way as evidence statements — check for other character names and infer relationship type.
   - Location: `src/pipeline/character_profiling/post_corrections.py:extract_relationships_from_evidence()` line ~836
   - The description scanning loop should be added after the evidence scanning loop (lines 845-874), processing `getattr(char, 'descriptions', None) or []` and using `desc.get('text', '')` as the statement text.

### MEDIUM
2. **"The Disfigured Body" falsely merged as alias of "The Teeth"** [Characters — Identity Resolution]
   - Problem: "The Disfigured Body" and "a disfigured body" are listed as aliases of "The Teeth". In the story, the disfigured body is Berenice herself (found alive in the violated grave), NOT the teeth. The teeth are the 32 white objects found in the box.
   - Evidence: Summary says "a violated grave containing a disfigured body that is still breathing and alive" — this is Berenice, not the teeth.
   - Location: `src/pipeline/character_extraction_v2/` — alias grouping during extraction
   - Fix: Low priority — doesn't block the 8.0 threshold on profiles.

3. **Some common English words flagged as pronunciations** [Pronunciation]
   - Problem: "light-heartedness", "shrubberies", "refracted", "sentient", "emaciation", "unloveliness" are standard English vocabulary — false positives.
   - Location: `src/pipeline/pronunciation/cmu_proposer.py` — COMMON_WORDS_WHITELIST
   - Fix: Add these words to the whitelist. Low priority — score is 8/10 already.

### LOW
4. **Ebn Zaiat has "associated" relationship with The Teeth** [Profiles]
   - Problem: Ebn Zaiat is a poet quoted in the epigraph. He has no in-story connection to The Teeth.
   - Not blocking.

5. **Null chapter titles for single-section text** [Structure]
   - Problem: Both structure elements have `title: null`. Labeling them would be more informative.
   - Not blocking — score is 9/10.

6. **Egaeus has no physical_description** [Profiles]
   - Problem: As first-person narrator, sparse self-description. Text does mention he's sickly and melancholic.
   - Partially excusable for 1st-person narration. Not blocking on its own.

## Fix History
- Attempt 1: Added `"cousin"`, `"brother"`, `"sister"`, `"spouse"` to `_SYMMETRIC_RELATIONSHIPS` in post_corrections.py
  - Root cause: `post_corrections.py:_SYMMETRIC_RELATIONSHIPS:line 60` was missing "cousin"
  - Result: Correct fix but insufficient — the relationship was being downgraded BEFORE reaching remove_contradictory_relationships()
  - Modified: src/pipeline/character_profiling/post_corrections.py
- Attempt 2: In `verify_relationships_from_text()`, skip family-label downgrade when `is_narrator=True` for either character
  - Root cause: `post_corrections.py:verify_relationships_from_text():line 1698` — narrator names rarely appear in raw text
  - Result: Relationship changed from "acquaintance" to "associated" — suggests fix addressed one path but another path or LLM non-determinism still produces wrong label
  - Modified: src/pipeline/character_profiling/post_corrections.py
- Attempt 3: Fix `extract_relationships_from_evidence()` to process generic labels AND detect family terms
  - Root cause: `post_corrections.py:extract_relationships_from_evidence():line 848` — skip condition `if other_name in rels: continue` prevented upgrade from "associated" to "cousin"; `_infer_rel()` had no FAMILY_TERMS detection so returned "associated" even when evidence contained kinship words
  - Result: **DID NOT FIX** — the FAMILY_TERMS detection logic is correct, but the evidence statement containing "cousin" does NOT name "Berenice" (it says "his cousin" without the name). The statements that DO name Berenice don't contain "cousin". The `descriptions` field has "his cousin Berenice" but isn't scanned.
  - Modified: src/pipeline/character_profiling/post_corrections.py
- Attempt 4: Extend `extract_relationships_from_evidence()` to ALSO scan `char.descriptions` field
  - Root cause: `post_corrections.py:extract_relationships_from_evidence():lines 845-877` — only scanned `char.evidence`, not `char.descriptions`. Egaeus's description contains "his cousin Berenice" which has both the family term AND the name. The fix merges evidence + description texts into a single `text_sources` list and processes both.
  - Smoke test: Confirmed `descriptions[0].text` = "...his cousin Berenice..." in analysis.json; tests: 332 passed, 0 failures
  - Modified: src/pipeline/character_profiling/post_corrections.py

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | Profiles: cousin blocked by _SYMMETRIC_RELATIONSHIPS | post_corrections.py | Fixed but insufficient — different downgrade path active |
| 2 | Profiles: cousin downgraded to acquaintance by verify_relationships_from_text() | post_corrections.py | Changed "acquaintance" to "associated" — NOT fixed, different label but still wrong |
| 3 | Profiles: "associated" from LLM not upgraded by extract_relationships_from_evidence() | post_corrections.py | NOT fixed — evidence stmt with "cousin" lacks "Berenice"; descriptions field (which has both) not scanned |
| 4 | Profiles: descriptions field not scanned by extract_relationships_from_evidence() | post_corrections.py | Applied — now scans both evidence + descriptions; awaiting analysis |

## Pipeline Notes (Attempt 4 — current output)
- Analysis completed in 15m 4s
- **3 characters found** (down from 4): Egaeus (1 mention), Berenice (14 mentions), Ebn Zaiat (2 mentions)
- **"The Teeth" NOT extracted this run** — LLM non-determinism; may hurt character extraction score
- 46 pronunciation flags
- Narrator detection: Egaeus (first-person)
- Models: structure/pronunciation=qwen3.5:35b-a3b, characters/summaries/profiles=qwen3.5:122b-a10b
- `extract_relationships_from_evidence()` now scans both `evidence` AND `descriptions` fields — awaiting evaluation to confirm cousin fix worked

## Configuration Audit
- Models: Appropriate (larger 122b for character/profile, smaller 35b for structure/pronunciation)
- Context lengths: 32768 — sufficient for short story
- Temperature: 0.7 across the board — reasonable
- No LLM retries or parse failures
- All confidence=high for characters and profiles

## Next Action
Evaluate attempt 4 output — check if Egaeus↔Berenice relationship is now "cousin"; also check if missing "The Teeth" character hurts character extraction score.
