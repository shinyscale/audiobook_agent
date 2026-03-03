# Current Evaluation State

## Active Text
- **Name:** berenice
- **Attempt:** 4
- **Phase:** awaiting_analysis
- **baseline_score:** 8.68
- **Competitive Mode:** none

## Output Files
- HTML: ../output/berenice/report.html
- JSON: ../output/berenice/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 8/10 ✓
  - Completeness: 8/10
  - Identity Resolution: 9/10
  - Alias Grouping: 8.5/10
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
| 4       | 8.45  | -0.23               | Profiles fail: descriptions field now scanned correctly BUT reject_unfounded_familial_labels() overwrites "cousin" → "associated" |

## Current Issues (Priority Order)

### CRITICAL
(none)

### HIGH
1. **Egaeus↔Berenice relationship is "associated" instead of "cousin"** [Profiles]
   - **ROOT CAUSE CONFIRMED:** `reject_unfounded_familial_labels()` at line 2133-2147 in `post_corrections.py` unconditionally downgrades ALL non-sibling family terms to "associated" when characters don't share a surname.
   - **WHY ATTEMPT 4 FIX IS NECESSARY BUT INSUFFICIENT:** The attempt 4 fix (scanning `descriptions` field in `extract_relationships_from_evidence()`) IS correct — the description text "his cousin Berenice" DOES contain both the family term "cousin" AND the name "Berenice", so `extract_relationships_from_evidence()` correctly sets `rels["Berenice"] = "cousin"`. This is confirmed working.
   - **BUT THEN:** `reject_unfounded_familial_labels()` runs AFTER (line 772, after line 762) and checks:
     1. Shared surname? Egaeus has no surname, Berenice has no surname → NO shared surname
     2. Is it a sibling term? `sibling_terms = {"sister", "brother"}` — "cousin" is NOT in this set
     3. Since `not is_sibling` → line 2142: unconditionally downgrades to "associated" — **NO text evidence check at all**
   - The sibling path (lines 2149-2169) DOES check text co-mention evidence before downgrading. But "cousin" never reaches that path.
   - **FIX:** In `reject_unfounded_familial_labels()` at line 2133, expand `sibling_terms` to include extended family terms that commonly don't share surnames. Rename to `_EXTENDED_FAMILY_TERMS`:
     ```python
     # Extended family terms that commonly don't share surnames.
     # These get the text-evidence check rather than unconditional downgrade.
     _extended_family_terms = {"sister", "brother", "cousin", "aunt", "uncle", "nephew", "niece"}
     is_extended_family = any(t in rel_lower for t in _extended_family_terms)
     if not is_extended_family:
         # Unconditional downgrade for spouse/parent/child without shared surname
         char.relationships[other_key] = "associated"
         ...
         continue
     ```
   - **ALSO:** Even with this fix, the text-evidence check (lines 2149-2169) may fail for first-person narrators. "Egaeus" appears only ~1 time in the raw text (when the narrator names himself), and "Berenice" may not appear within the `tight_window = 100` chars. The text says "Berenice and I were cousins" but "Egaeus" appears much earlier ("my baptismal name is Egaeus").
   - **SECONDARY FIX IF NEEDED:** If the text-evidence check fails for narrators, add a narrator exemption: if either character `is_narrator`, skip the text-evidence check and keep the family label that was set by `extract_relationships_from_evidence()` (which already verified both name + family term in the same text).
   - Location: `src/pipeline/character_profiling/post_corrections.py` lines 2133-2147

### MEDIUM
2. **"The Teeth" not extracted this run** [Characters — Completeness]
   - Problem: Previous runs extracted "The Teeth" as a symbolic force (title object, driver of Egaeus's monomania). This run did not — only 3 characters extracted vs 4 before.
   - Evidence: Only 3 mentions of "teeth/Teeth" in 3240-word text. LLM non-determinism.
   - Not a pipeline bug — can't fix without hardcoding. Score still 8/10 without it.

3. **Some common English words flagged as pronunciations** [Pronunciation]
   - Problem: "light-heartedness", "shrubberies", "refracted", "sentient", "emaciation", "unloveliness" are standard English vocabulary — false positives.
   - Location: `src/pipeline/pronunciation/cmu_proposer.py` — COMMON_WORDS_WHITELIST
   - Not blocking — score is 8/10 already.

### LOW
4. **Egaeus has no physical_description** [Profiles]
   - Problem: As first-person narrator, sparse self-description. Text does mention sickly and melancholic temperament.
   - Partially excusable for 1st-person narration. Not blocking on its own.

5. **Null chapter titles for single-section text** [Structure]
   - Problem: Both structure elements have `title: null`. Labeling them would be more informative.
   - Not blocking — score is 9/10.

6. **Ebn Zaiat has "associated" relationship with The Teeth** [Profiles]
   - Not applicable this run ("The Teeth" not extracted). Was LOW priority anyway.

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
  - Root cause: `post_corrections.py:extract_relationships_from_evidence():line 848` — skip condition prevented upgrade; `_infer_rel()` had no FAMILY_TERMS detection
  - Result: **DID NOT FIX** — the evidence statement containing "cousin" does NOT name "Berenice" (says "his cousin" without the name). The `descriptions` field has "his cousin Berenice" but isn't scanned.
  - Modified: src/pipeline/character_profiling/post_corrections.py
- Attempt 4: Extend `extract_relationships_from_evidence()` to ALSO scan `char.descriptions` field
  - Root cause: `post_corrections.py:extract_relationships_from_evidence():lines 845-877` — only scanned `char.evidence`, not `char.descriptions`
  - Result: **FIX WORKS CORRECTLY** at line 762 — sets "cousin". BUT `reject_unfounded_familial_labels()` at line 772 unconditionally overwrites it to "associated" because "cousin" is not in `sibling_terms` and characters don't share a surname.
  - Modified: src/pipeline/character_profiling/post_corrections.py
- Attempt 5: Expand `sibling_terms` → `extended_family_terms` + narrator exemption in `reject_unfounded_familial_labels()`
  - Root cause: `post_corrections.py:reject_unfounded_familial_labels():line 2133` — "cousin" not in `sibling_terms = {"sister", "brother"}` → unconditional downgrade to "associated"
  - Fix 1: Expanded set to `{"sister", "brother", "cousin", "aunt", "uncle", "nephew", "niece"}` — routes extended family through text-evidence check instead of unconditional downgrade
  - Fix 2: Narrator exemption before text-evidence loop — first-person narrators rarely appear by name in raw text, so tight co-mention check always fails for them; trust `extract_relationships_from_evidence()` instead
  - Smoke test: 332 tests pass (0 regressions)
  - Modified: src/pipeline/character_profiling/post_corrections.py

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | Profiles: cousin blocked by _SYMMETRIC_RELATIONSHIPS | post_corrections.py | Fixed but insufficient — different downgrade path active |
| 2 | Profiles: cousin downgraded to acquaintance by verify_relationships_from_text() | post_corrections.py | Changed "acquaintance" to "associated" — NOT fixed, different label but still wrong |
| 3 | Profiles: "associated" from LLM not upgraded by extract_relationships_from_evidence() | post_corrections.py | NOT fixed — evidence stmt with "cousin" lacks "Berenice"; descriptions field not scanned |
| 4 | Profiles: descriptions field not scanned by extract_relationships_from_evidence() | post_corrections.py | FIX WORKS at extraction — but reject_unfounded_familial_labels() overwrites "cousin" → "associated" |
| 5 | Profiles: reject_unfounded_familial_labels() unconditionally downgrades "cousin" (not in sibling_terms) | post_corrections.py | Expanded sibling_terms → extended_family_terms; added narrator exemption |

## Pipeline Notes (Attempt 4 — current output)
- Analysis completed in 15m 4s
- **3 characters found** (down from 4): Egaeus (1 mention), Berenice (14 mentions), Ebn Zaiat (2 mentions)
- **"The Teeth" NOT extracted this run** — LLM non-determinism; doesn't block 8.0 threshold
- 46 pronunciation flags (all with IPA)
- Narrator detection: Egaeus (first-person)
- Models: structure/pronunciation=qwen3.5:35b-a3b, characters/summaries/profiles=qwen3.5:122b-a10b
- `extract_relationships_from_evidence()` correctly sets "cousin" from descriptions field
- `reject_unfounded_familial_labels()` overwrites "cousin" → "associated" (the downstream overwrite)

## Configuration Audit
- Models: Appropriate (larger 122b for character/profile, smaller 35b for structure/pronunciation)
- Context lengths: 32768 — sufficient for short story
- Temperature: 0.7 across the board — reasonable
- No LLM retries or parse failures
- All confidence=high for characters and profiles

## Next Action
Re-run analysis to verify fix.
