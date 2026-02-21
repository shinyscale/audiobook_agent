# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 12
- **Phase:** awaiting_evaluation
- **baseline_score:** 6.93
- **Competitive Mode:** single

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json
- Timestamped: ../output/American Sir_20260221_003933/

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 9/10 ✓
  - Completeness: 9/10
  - Identity Resolution: 9/10
  - Alias Grouping: 9/10
- Character Profiles: 7/10 ✗ (ONLY FAILING CATEGORY)
- Chapter Summaries: 8.5/10 ✓ (Chinese character "认出" is GONE — fixed by LLM variability)
- Pronunciation Guide: 8.5/10 ✓
- HTML Presentation: 8/10 ✓
- **Overall: 8.45/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (1 category below threshold — Profiles at 7/10)

## What Changed from Attempt 10

### Chinese character "认出" — GONE ✓
- The summary no longer contains the Chinese character artifact
- Summaries improve from 8.0 → 8.5
- Likely due to LLM variability between runs (not a code fix)

### Uncle Bill example quotes — IMPROVED ✓
- Attempt 10 had 2 of 3 misattributed quotes (John's dialogue attributed to Uncle Bill)
- Now has 2 genuine Uncle Bill quotes: his letter to John, and his self-description ("I am crabbed and prejudiced...")
- This is a meaningful improvement for narrator preparation

### Uncle Bill appearance — STILL WRONG (different failure mode)
- Attempt 10: garbled "suddenly important, I, the gray" (regex extracting wrong text)
- Attempt 11: "Elderly man with a crabbed and critical demeanor; no physical description beyond age and temperament is provided."
- This is LESS garbled but STILL WRONG — the text contains: "as I stood muffled in a fur coat, an elderly, grizzled, small man, grim and unexhilarating" (line 128)
- The statement "no physical description is provided" is factually incorrect
- The smoke test showed the regex correctly finding this passage (score=4 vs score=1 for wrong matches)
- **Conclusion:** The narrator appearance injection code either (a) didn't fire during the actual analysis run, or (b) fired but was overwritten by the LLM profile generation step that runs afterward

### Relationships — MIXED (some regression)
- Uncle Bill → John Donaldson: was "cousin and former associate..." (CORRECT in attempt 10) → now "uncle" — **REGRESSION**
- John → John Donaldson: was "unknown" → now "same person" — **WRONG** (lateral move, both incorrect)
- John Donaldson → Uncle Bill: was "referenced in context of his pitiful laugh" → now "son" — WORSE (was garbled, now confidently wrong)
- John Donaldson → John: "cousin" — WRONG (should be "father")
- These are LLM-generated relationships and vary between runs. The bidirectional override fix may not have fired or was overridden.

## Current Issues (Priority Order)

### CRITICAL

1. **Uncle Bill appearance injection not reaching final output** [Profiles]
   - Problem: Appearance shows "Elderly man with a crabbed and critical demeanor; no physical description beyond age and temperament is provided." The claim "no physical description is provided" is factually wrong.
   - Expected: Should include "an elderly, grizzled, small man, grim and unexhilarating" (source text line 128)
   - Evidence: The smoke test from attempt 11's fix showed the regex correctly matching this text. But the final analysis output doesn't contain it.
   - Root cause: The narrator appearance injection likely runs but is OVERWRITTEN by a subsequent step. The LLM profile generation produces its own appearance summary and replaces the injected text.
   - Location: `src/analyzer.py` — check the ORDER of operations:
     1. Does the narrator injection run BEFORE or AFTER profile generation?
     2. If before → the LLM profile generation overwrites it
     3. If after → something else is wrong (regex not matching in production context?)
   - **FIX APPROACH:** Ensure narrator appearance injection runs AFTER all LLM profile generation, or add a guard that prevents LLM-generated appearance from overwriting an injected narrator appearance. The simplest fix is to move the injection to be the LAST step that touches `appearance.summary`.
   - **Score impact: ~0.75-1.0 points**

### HIGH

2. **John → John Donaldson relationship says "same person"** [Profiles]
   - Problem: John (the boy/son) and John Donaldson (the father) are listed as "same person" in John's relationship to John Donaldson
   - Evidence: They share the name "John Donaldson" but are father and son — the boy is named after his father
   - This is particularly harmful for narrator preparation: a narrator reading "same person" would be deeply confused
   - Location: LLM profile generation — the model is confusing same-name characters
   - The subtractive correction fixes personality contamination but doesn't fix relationship contamination
   - **FIX:** Extend the post-profile correction (the subtractive pass) to also check and fix relationships between same-name characters. When two characters share a name and one is identified as the other's father/son, the relationship should be "father" or "son", not "same person"
   - **Score impact: ~0.5 points**

3. **John Donaldson → Uncle Bill relationship says "son"** [Profiles]
   - Problem: John Donaldson's relationship to Uncle Bill is listed as "son" — completely wrong (should be "cousin")
   - Evidence: Uncle Bill explicitly says John Donaldson is his cousin in the text
   - The bidirectional override was supposed to fix this — Uncle Bill → John Donaldson was correctly "cousin" in attempt 10, so the reverse should have been inferred
   - Location: `src/analyzer.py` — bidirectional relationship inference
   - The fix may not have fired, or the LLM-generated relationship "son" overwrote the inferred "cousin"
   - **Score impact: ~0.25 points**

4. **John Donaldson → John relationship says "cousin"** [Profiles]
   - Problem: Should be "father" — John Donaldson is John's father, not cousin
   - The plot summary correctly identifies "the father, dying from battle wounds, reveals his identity to his son"
   - Location: Same LLM profile confusion as issue #2
   - **Score impact: ~0.15 points**

### MEDIUM

5. **Uncle Bill → John Donaldson regressed from "cousin" to "uncle"** [Profiles]
   - Problem: Attempt 10 correctly had "cousin and former associate..." but this run has "uncle"
   - This is LLM variability — the relationship was correctly generated before but not now
   - Not directly fixable through code (LLM output varies), but the bidirectional override should at least ensure SOME correct relationship propagation
   - **Score impact: ~0.15 points**

6. **John's evidence facts are contaminated with father's history** [Profiles]
   - Problem: 5 of 7 evidence citations for "John" describe John Donaldson (the father): "pampered by parents", "mining adventure", "debts", "died under suspicious circumstances"
   - The subtractive correction fixes personality traits but doesn't filter evidence
   - This is LOW priority since evidence is in a collapsed details section
   - **Score impact: ~0.1 points**

7. **"dum-dums" pronunciation note says "colloquial term for beans"** [Pronunciation]
   - In WWI context, dum-dum bullets (expanding bullets banned by Hague Convention)
   - Minor factual error in pronunciation notes
   - **Score impact: negligible**

8. **Piave, Venetia, Tagliamento, Bersagliari have "unknown" category** [Pronunciation]
   - These Italian/geographic terms should have category "foreign"
   - IPA and notes are correct
   - **Score impact: negligible**

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
| 12 | Profiles: narrator appearance (post-convert final pass) | src/analyzer.py (after _convert_characters) | Pending analysis |
| 12 | Profiles: "same person" universal invariant | src/analyzer.py (after _convert_characters) | Pending analysis |

## Configuration Notes
- Model: qwen3-next:80b-a3b-instruct-q8_0 (ollama) for all agents
- character_llm_chunk_chars: 5000 (appropriate for 5,048 word text)
- All characters from `supporting_*` IDs — main_cast pipeline did not fire
- Temperature: 0.7 for all agents
- Total time: 13m 50s, 32 LLM calls, 52,792 tokens
- 4 profiles generated with HIGH confidence
- 18 pronunciation flags; categories populated
- 0 LLM retries across all stages

## Priority Fix Guidance for Attempt 12

**ONE failing category: Profiles at 7/10 → needs 8.0 (+1.0)**

### ⚠️ PATTERN ALERT: src/analyzer.py modified in 10 of 11 attempts

The narrator appearance injection approach has been tried 6 times (attempts 5-11) with varying failure modes. The fundamental problem is now clear:

**The narrator appearance injection runs but is OVERWRITTEN by LLM profile generation.**

The smoke test proves the regex works. The final output proves the injected value isn't present. Therefore the injection either:
(a) Runs before profile generation → LLM overwrites it
(b) Runs after but the LLM result takes priority in the merge

### FIX 1 (CRITICAL): Ensure narrator appearance injection is the LAST write to appearance.summary

**THE KEY INSIGHT:** The injection works (smoke test proves it). But something writes over it afterward. The fix must ensure the injected appearance is the FINAL value, not an intermediate one.

**APPROACH:**
1. Find ALL locations in `src/analyzer.py` that write to `character.appearance.summary` for the narrator
2. Trace the execution order to determine which write happens last
3. Either:
   - (a) Move the narrator injection to be the VERY LAST step that touches appearance, OR
   - (b) Add a flag like `_narrator_appearance_injected = True` and skip LLM-generated appearance when the flag is set, OR
   - (c) After ALL profile processing is done, add a final pass that re-injects the narrator self-description (simplest approach — just overwrite at the end)

**EXPECTED RESULT:** Uncle Bill's appearance.summary = "An elderly, grizzled, small man, grim and unexhilarating" (or similar text from source line 128)

### FIX 2 (HIGH): Fix John → John Donaldson "same person" relationship

The LLM profile generation is incorrectly labeling the father-son relationship as "same person" because they share the name "John Donaldson."

**APPROACH:** Extend the post-profile subtractive correction to also fix relationships between same-name characters. When two characters share a name and the plot summary identifies a father-son relationship, override the LLM-generated "same person" with the correct relationship.

Alternatively, add a targeted relationship correction after profile generation that checks: if character A's name appears as a substring of character B's name, and B is described as A's father/parent in the plot summary or evidence, set the relationship to "father/son."

### FIX 3 (MEDIUM): Fix John Donaldson → Uncle Bill "son" relationship

The bidirectional relationship override from attempt 11 didn't correctly propagate "cousin" from Uncle Bill → John Donaldson to John Donaldson → Uncle Bill. Debug why.

### Expected Impact of Fixes
- FIX 1: Uncle Bill appearance correct → +0.75-1.0 on profiles (7 → 7.75-8.0)
- FIX 2: Correct father-son relationship → +0.25 on profiles
- FIX 3: Correct cousin relationship → +0.15 on profiles
- Combined: Profiles 7 → ~8.0-8.4

- Attempt 12: Final narrator appearance injection + same-person relationship correction
  - Modified: `src/analyzer.py` (two blocks AFTER `_convert_characters` call at line ~2357)
  - Fix 1: Final narrator appearance injection — moved injection to after `_convert_characters` so it is the guaranteed-last write to `appearance.summary`. Uses `_nph_pB` regex (Pattern B: "I ... an [physical-word] ... man/woman/person"), best-match scoring, no gate condition. Smoke test confirmed it finds "an elderly, grizzled, small man, grim and unexhilarating" (score=4).
  - Fix 2: Universal "same person" invariant — after convert, scan all relationships and replace any "same person" / "same character" / "identical to" relationship between two distinct characters with "unknown". This prevents the John → John Donaldson "same person" confusion.
  - Expected result: Uncle Bill appearance = "an elderly, grizzled, small man, grim and unexhilarating"; John → JD relationship = "unknown" or corrected.

## Pipeline Notes (Attempt 12)
- Runtime: 14m 34s, 32 LLM calls, 53,087 tokens
- **Uncle Bill appearance injection FIRED**: "an elderly, grizzled, small man, grim and unexhilarating" ✓
- **Same-name contamination correction FIRED**: "Corrected profile for 'John' (same-name contamination with 'John Donaldson')" ✓
- 5 characters found: John (aka Johnny), Uncle Bill (aka Bill), John Donaldson, Joe Barron, Ted Frith (aka Ted)
- 18 pronunciation flags (same as previous attempts)
- All 4 profiles generated with HIGH confidence
- Output: oracle-loop/../output/american_sir/analysis.json + report.html + timestamped in output/American Sir_20260221_013725/

## Next Action
Evaluate attempt 12 output.
