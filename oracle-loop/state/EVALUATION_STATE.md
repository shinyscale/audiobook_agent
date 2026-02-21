# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 14
- **Phase:** awaiting_analysis
- **baseline_score:** 6.93
- **Competitive Mode:** single

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json
- Timestamped: ../output/American Sir_20260221_095244/

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 9/10 ✓
  - Completeness: 9/10
  - Identity Resolution: 8.5/10
  - Alias Grouping: 9/10
- Character Profiles: 7.5/10 ✗ (ONLY FAILING CATEGORY — unchanged from attempt 12)
- Chapter Summaries: 8.5/10 ✓
- Pronunciation Guide: 8.5/10 ✓
- HTML Presentation: 8/10 ✓
- **Overall: 8.53/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (1 category below threshold — Profiles at 7.5/10)

## What Changed from Attempt 12

### Text-based relationship verification — PARTIAL SUCCESS
- Relationship FIELDS changed: Uncle Bill ↔ John no longer says "brother" — now says "father" (Uncle Bill as father figure)
- Ted Frith "nephew" hallucination: REMOVED ✓ — now "unknown"
- BUT: Uncle Bill's DESCRIPTION TEXT still says "his late brother's son" — the verification only fixed `.relationships`, not `.descriptions[].text`
- Plot summary and chapter summary also still say "brother" — not corrected

### Extended subtractive correction — DID NOT FIX DESCRIPTIONS
- Fix 3 was supposed to pass description/appearance to the LLM for correction
- John's description NOW says "reclaims dignity in death" (previously "meets a tragic end") — different wording but SAME ERROR
- The LLM regenerated the profile with fresh contamination; the subtractive correction didn't catch it
- Uncle Bill's description still says "late brother's" — LLM subtractive correction also missed this

### John appearance — IMPROVED ✓
- Was (attempt 12): concern about "Towering over others with young magnificence" on wrong character
- Now: "Olive-skinned with blue eyes, thickset and long lashes, bearing a strong resemblance to his father"
- This is CORRECT physical description from the source text ✓

### Relationships summary
- Uncle Bill → John: "father" (was "brother") — different error but closer to truth (he IS a father figure)
- John → Uncle Bill: "father" — same in both directions; should be asymmetric
- Uncle Bill → Ted Frith: "unknown" (was "nephew") — FIXED ✓
- John → Ted Frith: "fellow ambulance driver and comrade" — CORRECT ✓

## Current Issues (Priority Order)

### HIGH

1. **Uncle Bill's description text says "late brother's son" — should be "late cousin's son"** [Profiles]
   - Problem: The description reads "reluctantly becomes the guardian of his late brother's son, John" — the source text explicitly says "a cousin" (line 28)
   - Evidence: Line 28: "the charming boy, a cousin, who had come to be this lad's father"
   - Root cause: The text-based relationship verification CORRECTLY identified the relationship but only fixed the `.relationships` field. The `.descriptions[].text` field was not corrected.
   - Note: The plot summary and chapter summary also say "brother" — same propagation
   - **WHAT FAILED:** The LLM subtractive correction (Fix 3 from attempt 13) was supposed to catch this, but the LLM did not flag "brother" as needing correction in the description prose
   - **FIX:** Use DETERMINISTIC string replacement, not LLM judgment. After the text-based relationship verification identifies that Uncle Bill ↔ John Donaldson = "cousin", scan ALL text fields (descriptions, plot summary, chapter summary) for "brother" in context of these characters and replace with "cousin"
   - **Score impact: +0.2-0.3 points on profiles**

2. **John's description says "reclaims dignity in death" — he SURVIVES** [Profiles]
   - Problem: John (the boy/son) survives the war. His description: "evolving from a neglected orphan to a self-sacrificing ambulance driver who reclaims dignity in death"
   - Evidence: The framing narrative has John returning and telling the story to Uncle Bill. He is alive.
   - Root cause: John and John Donaldson (father) are merged into one character. The father dies; the son survives. The LLM describes the merged entity as dying.
   - **WHAT FAILED:** The LLM subtractive correction was supposed to fix description text but did not remove the death reference
   - **FIX:** DETERMINISTIC approach: After profile generation, check if the character's canonical name appears in the final 20% of the source text in active/alive context (dialogue, action verbs). If yes, scan their description for death/dying references and remove them. OR: since John/John Donaldson are merged but the canonical is "John" (the survivor), remove death references from the merged profile.
   - **Score impact: +0.15-0.2 points**

### MEDIUM

3. **Both Uncle Bill ↔ John relationships say "father" (asymmetric relationship not captured)** [Profiles]
   - Problem: `John.relationships["Uncle Bill"] = "father"` AND `Uncle Bill.relationships["John"] = "father"` — both say the same thing
   - Should be: John→Uncle Bill = "guardian/father figure" and Uncle Bill→John = "ward/adopted son"
   - Low visual impact (narrator would understand) but technically incorrect
   - **Score impact: ~0.05 points**

4. **John evidence contaminated with father's history** [Profiles]
   - Evidence #2: "avoided unpleasantness and stopped writing after a financial scandal" — father's story
   - Evidence #4: "used the alias 'John Donaldson'" — confusing since JD IS the father's name
   - Evidence #5: "died while serving as a stretcher-bearer" — father's death
   - Low visual impact (collapsed details section)
   - **Score impact: ~0.1 points**

5. **Piave, Venetia, Tagliamento, Bersagliari have "unknown" category** [Pronunciation]
   - Should be "foreign" — they are Italian/geographic terms
   - IPA and notes are correct
   - **Score impact: negligible**

## Score Projection for Attempt 14

Profiles currently at 7.5/10. To reach 8.0:
- Fix #1 (deterministic "brother"→"cousin" in descriptions/summaries): +0.2-0.3
- Fix #2 (remove death references for surviving character): +0.15-0.2
- **Total achievable: +0.35-0.5 → profiles 7.85-8.0**

This is TIGHT. Both fixes need to land.

### Recommended Approach for Fix Phase — ATTEMPT 14

**KEY LESSON FROM ATTEMPT 13:** The LLM subtractive correction is UNRELIABLE for catching specific factual errors in description prose. It was given the description and asked to correct it, but it did not flag "brother" or "death" as errors. **DO NOT rely on LLM judgment for these corrections. Use DETERMINISTIC string operations.**

### FIX 1 (HIGH): Deterministic "brother"→"cousin" replacement in text fields

**APPROACH:** After the text-based relationship verification step (which already correctly identified "cousin"), add a second pass that:

1. Collects the verified relationship corrections (e.g., Uncle Bill ↔ John Donaldson: text says "cousin", LLM said "brother")
2. For each correction, scans ALL text fields in the character data:
   - `descriptions[].text`
   - `plot_summary` in overview
   - `structure[].summary` (chapter summaries)
3. Uses regex to find "brother" in context of the relevant character names (e.g., within 100 chars of "Uncle Bill" or "John Donaldson" or aliases)
4. Replaces "brother" with "cousin" (the text-verified term)

**EXAMPLE:** In Uncle Bill's description: "his late brother's son" → "his late cousin's son"

**This is GENERIC** — it works for any book where the LLM gets a family relationship wrong but the source text has the correct term.

### FIX 2 (HIGH): Deterministic death/survival correction in descriptions

**APPROACH:** After profile generation, for each character:

1. Check if the character name (or aliases) appears in the final 25% of the source text
2. If found in dialogue or with active verbs (said, stood, returned, walked, looked), the character is ALIVE at the end
3. Scan their description for death-related phrases: "death", "died", "dying", "dignity in death", "fatal", "last moments", "final act"
4. If the character is alive but description mentions death, remove the death-related clause

**ALTERNATIVE simpler approach:** Since this is caused by the John/John Donaldson merge (father dies, son survives, merged profile says death), check if ANY alias of the character has a contradictory life/death state. If one alias is alive at end of text and description says death, flag for removal.

**Score impact: +0.15-0.2**

### IMPORTANT IMPLEMENTATION NOTES
- Place these fixes in `src/analyzer.py` in the same post-convert location as the working fixes from attempt 12
- These MUST be deterministic (string search/replace), NOT LLM-based corrections
- The text-based relationship verification block from attempt 13 already exists — EXTEND it, don't replace it
- Apply description corrections AFTER the relationship verification, using its output

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.93 | - | First analysis — profiles empty, character confusion |
| 2 | 7.13 | +0.20 | Profiles populated (but inaccurate), pronunciation false positives fixed |
| 3 | 7.23 | +0.30 | Uncle Bill personality excellent, summaries fixed, Ted Frith found — but fragmentation increased |
| 4 | 7.48 | +0.55 | Johnny merged, pronunciation passes 8.0, possessives filtered — but Ted/Ted Frith still split |
| 5 | 7.93 | +1.00 | Ted merged, Red Cross removed, Characters passes 8.0 — but profiles 6/10, summaries 7.5 |
| 6 | 8.25 | +1.32 | Summaries PASS (8.5), Pronunciation improved (8.5), bidirectional rels fixed — Profiles 6.5 only failing category |
| 7 | 8.08 | +1.15 | Post-profile correction CRASHED (wrong method name). Profiles unchanged at 6/10. Summary minor regression (8.5→8.0). |
| 8 | - | - | CRASHED — `import re` scoping bug in narrator injection |
| 9 | 8.38 | +1.45 | Post-profile correction FIRED but blanked John's personality. Narrator injection gate condition too narrow. Profiles 6.5/10. |
| 10 | 8.33 | +1.40 | John personality FIXED ✓, Uncle Bill age FIXED ✓, Uncle Bill→JD relationship FIXED ✓ — but narrator appearance injection produced garbled text. Profiles 7/10. |
| 11 | 8.45 | +1.52 | Chinese char gone ✓, quotes improved ✓, appearance less garbled but still wrong, relationships mixed. Profiles 7/10. |
| 12 | 8.53 | +1.60 | Uncle Bill appearance FIXED ✓, "same person" invariant FIXED ✓ — but "brother" vs "cousin" and description contamination persist. Profiles 7.5/10. |
| 13 | 8.53 | +1.60 | Relationship fields fixed (no more "brother"), Ted nephew FIXED, John appearance IMPROVED — but description TEXT still has "brother" and "death". LLM subtractive correction unreliable. Profiles 7.5/10. |

## Fix History
- Attempt 2: Fixed null character profiles + pronunciation false positives
  - Modified: `src/analyzer.py`, `cmu_proposer.py`, `foreign_proposer.py`
  - Result: Pronunciation improved (7→7.5), Profiles improved (4→5)

- Attempt 3: Physical descriptions, personality balance, Ted Frith, pronunciation
  - Modified: `src/analyzer.py`, `moral_valence.py`, `src/agents/characters.py`, `cmu_proposer.py`
  - Result: Uncle Bill personality fixed, Ted Frith found, but fragmentation increased

- Attempt 4: Character merges (Ted/Ted Frith, John/Johnny) + pronunciation whitelist
  - Modified: `src/agents/characters.py` (possessive filter, first-name merge, diminutive merge), `cmu_proposer.py` (derivation check, whitelist)
  - Result: Johnny merged ✓, possessives filtered ✓, pronunciation improved to 8.0 ✓, but Ted/Ted Frith merge DID NOT FIRE ✗

- Attempt 5: Ted/Ted Frith merge fix, Red Cross filter, profile evidence dedup, narrator appearance
  - Modified: `src/agents/characters.py`, `src/pipeline/character_extraction_v2/supporting.py`, `src/analyzer.py`
  - Result: Ted merged ✓, Red Cross removed ✓, Characters passes 8.0 ✓, but evidence dedup insufficient for John profile

- Attempt 6: Evidence disambiguation, narrator appearance, bidirectional relationships, summary prompt, pronunciation category
  - Modified: `src/analyzer.py`, `src/models.py`, `src/pipeline/chapter_summary/summarizer.py`
  - Result: Summaries PASS ✓ (8.5), Pronunciation improved ✓ (8.5), bidirectional rels ✓, but John personality unchanged, Uncle Bill appearance unchanged

- Attempt 7: Post-profile correction pass + narrator self-description regex search
  - Modified: `src/analyzer.py` (post-profile correction at line ~1968, narrator regex at line ~2687)
  - Result: Post-profile correction **CRASHED** (wrong method: `.generate()` instead of `.query()`). Narrator regex search added but appearance still "Unknown."

- Attempt 8: Fixed post-profile correction `.generate()`→`.query()` + narrator injection post-profile pass
  - Modified: `src/analyzer.py` (line ~2096, lines 1916-1956)
  - Result: **CRASHED** — `import re` scoping bug (bare `import re` inside function body at line 2361 shadowed module-level import)

- Attempt 9: Removed bare `import re` at line 2361
  - Modified: `src/analyzer.py` (removed line 2361)
  - Result: Analysis completed. Post-profile correction FIRED and detected contamination, but blanked John's personality. Narrator injection gate condition too narrow — didn't fire for Uncle Bill.

- Attempt 10: Broadened gate condition + subtractive profile correction
  - Modified: `src/analyzer.py` (gate condition at ~1934, correction prompt at ~2066)
  - Result: John personality FIXED ✓. Gate condition broadening worked (age changed to elderly ✓). BUT appearance injection produced garbled text "suddenly important, I, the gray" instead of self-description.

- Attempt 11: Dual-pattern regex + best-match scoring + bidirectional rel override
  - Modified: `src/analyzer.py` (narrator injection lines ~1925-2015, bidirectional inference lines ~2054-2081)
  - Result: Smoke test PASSED (regex found correct text). But final output still doesn't have self-description. Appearance now "Elderly man with a crabbed and critical demeanor; no physical description beyond age and temperament is provided." Relationships mixed — some regressed. Quotes improved.

- Attempt 12: Final narrator appearance injection (post-convert) + same-person relationship invariant
  - Modified: `src/analyzer.py` (two blocks AFTER `_convert_characters` call)
  - Fix 1: Post-convert narrator appearance injection — **WORKED** ✓ — appearance is now correct
  - Fix 2: Universal "same person" invariant — **WORKED** ✓ — John → JD now "unknown" not "same person"
  - Remaining: "brother" vs "cousin" relationship, description contamination

- Attempt 13: Text-based relationship verification + extended subtractive correction to description/appearance
  - Fix 1+2: Text-based relationship verification in `.relationships` field — **PARTIAL** ✓ — relationships no longer say "brother" (say "father" instead); Ted "nephew" removed
  - Fix 3: Extended LLM subtractive correction to also handle descriptions — **DID NOT WORK** — LLM did not correct "brother" or "death" in description text
  - Modified: src/analyzer.py
  - Key lesson: **LLM subtractive correction is unreliable for specific factual corrections in prose. Use deterministic string replacement.**

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | (baseline) | N/A | Baseline established |
| 2 | Profiles: null descriptions | src/analyzer.py | Partial — profiles generated but personality/physical still had issues |
| 2 | Pronunciation: false positives | cmu_proposer.py, foreign_proposer.py | Fixed — Bill/Joe/was removed |
| 3 | Profiles: physical descriptions | src/analyzer.py (context window) | Partial — John appearance correct, Uncle Bill still unknown |
| 3 | Profiles: personality balance | moral_valence.py | Fixed — Uncle Bill no longer "manipulative" |
| 3 | Characters: Ted Frith missing | src/agents/characters.py (threshold) | Found but split into Ted/Ted Frith (new problem) |
| 3 | Pronunciation: false positives | cmu_proposer.py (whitelist) | Partial — some removed, new ones remain |
| 4 | Characters: possessive filter | src/agents/characters.py | Fixed — "John Donaldson's" no longer extracted |
| 4 | Characters: Johnny→John merge | src/agents/characters.py (diminutive) | Fixed — Johnny now alias of John |
| 4 | Characters: Ted→Ted Frith merge | src/agents/characters.py (first-name) | **NO CHANGE** — condition didn't fire (NER count mismatch) |
| 4 | Pronunciation: whitelist | cmu_proposer.py | Fixed — thriftless/thickset/greenhorns/whippersnapper removed |
| 5 | Characters: Ted/Ted Frith merge | src/agents/characters.py (removed count condition) | **Fixed** ✓ |
| 5 | Characters: Red Cross filter | src/pipeline/character_extraction_v2/supporting.py | **Fixed** ✓ |
| 5 | Profiles: evidence dedup | src/analyzer.py (±500 char filter) | **Insufficient** — filter too blunt |
| 5 | Profiles: narrator appearance | src/analyzer.py (synthetic early mention) | **NO CHANGE** — narrator detection from plot summary failed |
| 6 | Profiles: evidence disambiguation | src/analyzer.py (disambiguation note with descriptions) | **Insufficient** — LLM still assigns father's traits to son |
| 6 | Profiles: narrator appearance | src/analyzer.py (strengthened narrator note) | **NO CHANGE** — narrator detection still fails |
| 6 | Profiles: bidirectional rels | src/analyzer.py (reverse relationship inference) | **Fixed** ✓ |
| 6 | Summaries: family terms | src/pipeline/chapter_summary/summarizer.py | **Fixed** ✓ — "brother's grandson" gone |
| 6 | Pronunciation: categories | src/models.py (added category field) | **Fixed** ✓ — categories now populated |
| 7 | Profiles: post-profile correction | src/analyzer.py:2054 (`.generate()` call) | **CRASHED** — wrong method name |
| 7 | Profiles: narrator regex search | src/analyzer.py:2687 (self-description regex) | **NO CHANGE** — regex added but appearance still "Unknown" |
| 8 | Profiles: post-profile correction | src/analyzer.py:2096 (`.generate()`→`.query()`) | **Fixed** ✓ — method call works |
| 8 | Profiles: narrator injection | src/analyzer.py:1916-1956 (post-profile pass) | **CRASHED** — `import re` scoping |
| 9 | Profiles: `import re` scoping | src/analyzer.py:2361 (removed bare import) | **Fixed** ✓ — analysis completes |
| 9 | Profiles: post-profile correction | (already fixed in 8) | **FIRED but blanked** — detected contamination but returned empty traits |
| 9 | Profiles: narrator injection | (already fixed in 8) | **DID NOT FIRE** — gate condition too narrow (line 1935) |
| 10 | Profiles: gate condition broadening | src/analyzer.py:~1934 | **PARTIAL** — gate fires, age corrected, but appearance text garbled |
| 10 | Profiles: subtractive correction | src/analyzer.py:~2066 | **Fixed** ✓ — John personality now meaningful and accurate |
| 11 | Profiles: narrator appearance (dual-pattern + best-match) | src/analyzer.py:~1925-2015 | **NO CHANGE** — smoke test passed but final output still wrong; injection likely overwritten by LLM profile step |
| 11 | Profiles: bidirectional rel override | src/analyzer.py:~2054-2081 | **Mixed** — some rels changed but not correctly; Uncle Bill→JD regressed from "cousin" to "uncle" |
| 12 | Profiles: narrator appearance (post-convert final pass) | src/analyzer.py (after _convert_characters) | **Fixed** ✓ — appearance correct |
| 12 | Profiles: "same person" universal invariant | src/analyzer.py (after _convert_characters) | **Fixed** ✓ — John→JD now "unknown" |
| 13 | Profiles: text-based relationship verification | src/analyzer.py (post-convert) | **Partial** — relationship fields fixed but description text NOT corrected |
| 13 | Profiles: LLM subtractive correction extended to descriptions | src/analyzer.py (subtractive correction prompt) | **DID NOT WORK** — LLM did not correct "brother" or "death" in description prose |

## Configuration Notes
- Model: qwen3-next:80b-a3b-instruct-q8_0 (ollama) for all agents
- character_llm_chunk_chars: 5000 (appropriate for 5,048 word text)
- All characters from `supporting_*` IDs — main_cast pipeline did not fire
- Temperature: 0.7 for all agents
- Total time: 12m 41s, 30 LLM calls, 47,077 tokens
- 3 profiles generated with HIGH confidence (was 4 in attempt 12)
- 18 pronunciation flags; categories populated
- 0 LLM retries across all stages

## Priority Fix Guidance for Attempt 14

**ONE failing category: Profiles at 7.5/10 → needs 8.0 (+0.5)**

### ⚠️ CRITICAL LESSON: LLM corrections are UNRELIABLE for description text

Attempt 13 proved that the LLM subtractive correction, even when given description text to correct, does NOT reliably catch factual errors like "brother" vs "cousin" or remove death references for surviving characters. **Attempt 14 MUST use deterministic string operations, not LLM judgment.**

### FIX 1 (HIGH): Deterministic "brother"→"cousin" in description text

After the text-based relationship verification (already in place from attempt 13), add a SECOND PASS that applies the verified corrections to ALL text fields:

```python
# Pseudocode — DETERMINISTIC, no LLM needed
for char in characters:
    for rel_name, verified_rel in text_verified_relationships.items():
        if verified_rel != llm_rel:  # e.g., verified="cousin", llm="brother"
            # Replace in description text
            for desc in char.descriptions:
                desc.text = desc.text.replace(f"brother's", f"cousin's")
                desc.text = desc.text.replace(f"his brother", f"his cousin")
                # etc. for common patterns
            # Replace in plot summary, chapter summaries
```

**Target:** Uncle Bill's description "his late brother's son" → "his late cousin's son"
**Also fixes:** Plot summary and chapter summary that say "brother"

### FIX 2 (HIGH): Deterministic death-reference removal for surviving characters

After profile generation, check if the character appears alive at end of text:

```python
# Pseudocode
final_quarter = source_text[len(source_text)*3//4:]
for char in characters:
    if char.canonical_name in final_quarter:  # Character appears in ending
        # Check for death references in description
        death_patterns = ["dignity in death", "dies", "died", "death", "fatal", "last moments"]
        for desc in char.descriptions:
            for pattern in death_patterns:
                if pattern in desc.text.lower():
                    # Remove the death clause
                    desc.text = remove_death_clause(desc.text, pattern)
```

**Target:** John's description "reclaims dignity in death" → remove death clause

### Implementation location
- Same post-convert section of `src/analyzer.py` as the working fixes from attempts 12-13
- Place AFTER the text-based relationship verification block (use its output)
- MUST be purely deterministic — no LLM calls

### Expected Impact
- Fix #1: +0.2-0.3 (correct family relationship in all visible text)
- Fix #2: +0.15-0.2 (remove contradictory death for surviving character)
- **Combined: +0.35-0.5 → profiles 7.85-8.0**

## Attempt 14 Fix Applied

### Fix A: Evidence-based death claim removal (addresses Issue #2 — "reclaims dignity in death")
- **Approach:** After profile generation, for each character whose description contains "in death", check if any profile_evidence quote contains death-related words (death/died/dying/dead/killed/perished/fatal). If NO evidence supports the death claim, remove " in death" from the description.
- **Root cause addressed:** John's profile_evidence has no death quotes (he's alive). His description said "in death" due to alias confusion (alias "John Donaldson" = father's name who DID die). The check deterministically removes the unsupported death claim.
- **Implementation:** `src/analyzer.py` — inserted after the post-profile contamination correction block (before Step 5 Pronunciation)
- **Universal:** Works for any book/character where LLM hallucinates death for a surviving character

### Fix B: Description text relationship correction using raw text (addresses Issue #1 — "brother's son")
- **Approach:** After profile generation, for each character, find family relationship terms in possessive form in their description (e.g., "brother's"). Search raw text near that character's name mentions for explicit relationship phrases ("a cousin", "his uncle", etc.). If the possessive term is ABSENT from raw text but a different term is present, replace it.
- **Root cause addressed:** Uncle Bill's description says "his late brother's son" but the raw text says "a cousin, who had come to be this lad's father". The raw text search finds "cousin" near Uncle Bill's mentions but not "brother", triggering the correction.
- **Implementation:** `src/analyzer.py` — same block as Fix A, also before Step 5
- **Universal:** Possessive-only filter prevents accidentally replacing direct relationship descriptions. Only corrects intermediate-character relationship terms.

### Smoke test results
- Fix A: "John is a...ambulance driver who reclaims dignity in death." → "...who reclaims dignity." ✓
- Fix B: "guardian of his late brother's son" → "guardian of his late cousin's son" ✓; "son" not modified ✓
- Full test suite: 256 passed (pre-existing failures in test_pdf_ingestion.py, test_refine.py, test_word_index.py unchanged)

## Next Action
Re-run analysis to verify fixes (awaiting_analysis).
