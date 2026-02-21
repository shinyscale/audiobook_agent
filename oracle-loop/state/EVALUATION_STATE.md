# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 7
- **Phase:** awaiting_analysis
- **baseline_score:** 6.93
- **Competitive Mode:** single

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json
- Timestamped: ../output/American Sir_20260220_223923/

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 8.5/10 ✓
  - Completeness: 9/10
  - Identity Resolution: 8.5/10
  - Alias Grouping: 9/10
- Character Profiles: 6/10 ✗ (ONLY FAILING CATEGORY)
  - Post-profile correction CRASHED (`profile_llm.generate()` → wrong method name)
  - John personality still contaminated with father's traits
  - Uncle Bill appearance still "Unknown" despite self-description in text
  - Two wrong relationships persist
- Chapter Summaries: 8/10 ✓ (REGRESSION from 8.5 — "brother's grandson" error returned)
- Pronunciation Guide: 8.5/10 ✓
- HTML Presentation: 8/10 ✓
- **Overall: 8.08/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (1 category below threshold — Profiles at 6/10)

## What Changed from Attempt 6

### Fix attempts that CRASHED:
- **Post-profile personality correction:** The approach was correct (detect same-name pairs, send both profiles to LLM, correct contamination) but CRASHED at runtime because `profile_llm.generate(correction_prompt)` used wrong method. The correct method is `profile_llm.query(correction_prompt)`. This is a **ONE-LINE FIX** at `src/analyzer.py:2054`.

### Fix attempts that were INEFFECTIVE:
- **Narrator self-description regex search:** The regex `r'\bI[\s.…]{0,20}(?:am|was)\b...'` was added at line 2687, but Uncle Bill's appearance is still "Unknown." Either:
  - The regex didn't match (text encoding issue with "I... am..." dots), or
  - The regex matched but the resulting synthetic mention didn't cause the LLM to extract the appearance
  - Need to verify by adding debug logging, or by directly setting appearance from the regex match itself

### Minor regression:
- **Summary "brother's grandson" returned:** Was fixed in attempt 6 (said "long-lost father") but LLM regenerated with old error. The code fix (summary prompt guidance) is still in place — this is LLM stochasticity.

### Unchanged:
- John personality traits: "charming, financially irresponsible, emotionally avoidant, courageous in crisis" — still has father's traits (financially irresponsible, emotionally avoidant)
- Uncle Bill→John Donaldson: "father-in-law" — still wrong (should be cousin)
- John→Uncle Bill: "brother" — still wrong (should be uncle/guardian/nephew)
- John age: "middle-aged" — still wrong (should be early 20s)

## Current Issues (Priority Order)

### CRITICAL

1. **Post-profile correction has wrong method name — ONE-LINE FIX** [Profiles]
   - Problem: `src/analyzer.py:2054` calls `profile_llm.generate(correction_prompt)` but `LLMClient` has no `generate()` method
   - Evidence: Pipeline log "Post-profile correction FAILED: 'LLMClient' object has no attribute 'generate'"
   - The correct method is `profile_llm.query(correction_prompt)` (see `src/llm/client.py:123`)
   - The `query()` method returns an `LLMResponse` object with a `.text` attribute for the response content
   - **FIX:** Change `profile_llm.generate(correction_prompt)` to `profile_llm.query(correction_prompt)` and access `.text` on the response
   - Verify: Check how `profile_llm.query()` is called elsewhere in `analyzer.py` to match the calling pattern (it returns `LLMResponse`, not a string)
   - Location: `src/analyzer.py:2054`
   - **This one fix should resolve John's personality contamination AND age error**

### HIGH

2. **Uncle Bill appearance "Unknown" despite self-description — 7th consecutive failure** [Profiles]
   - Problem: Text says "I... am... an elderly, grizzled, small man, grim and unexhilarating" but appearance shows "Unknown"
   - The regex search (line 2687) was added but didn't resolve this
   - Uncle Bill IS tagged `is_narrator: true` in character data
   - **ROOT CAUSE HYPOTHESIS:** The regex search creates a synthetic mention at the self-description position, but the LLM still generates "Unknown" appearance because it doesn't interpret first-person "I am" as referring to the character being profiled, even with the narrator note
   - **RECOMMENDED FIX — Direct appearance injection:** Instead of relying on the LLM to extract appearance from the self-description, when the regex finds a match for a narrator character, DIRECTLY set `character.appearance["summary"]` to the matched text (cleaned up). This bypasses the LLM entirely for this specific case:
     ```python
     # After regex match for narrator self-description:
     if match and character.is_narrator:
         desc_text = match.group()  # e.g., "I... am... an elderly, grizzled, small man"
         # Clean up: remove "I am/was" prefix
         cleaned = re.sub(r'^I[\s.…]*(?:am|was)\s*', '', desc_text, flags=re.IGNORECASE).strip()
         if character.appearance:
             character.appearance["summary"] = cleaned
         # Also fix age from the description
         if "elderly" in desc_text.lower() or "old" in desc_text.lower():
             character.appearance["age_indication"] = "elderly"
     ```
   - Location: `src/analyzer.py` — near line 2687 (narrator self-description search block)
   - This is MORE reliable than depending on the LLM to correctly interpret first-person self-description

3. **Uncle Bill→John Donaldson relationship: "father-in-law"** [Profiles]
   - Problem: Should be "cousin" — the text evidence says "I saw the charming boy, a cousin, who had come to be this lad's father"
   - This relationship error has persisted through ALL attempts with different wrong answers (brother-in-law, estranged brother, father-in-law)
   - May require either: (a) the post-profile correction pass to also review relationships, or (b) providing the "cousin" evidence more explicitly in the relationship context

4. **John→Uncle Bill relationship: "brother"** [Profiles]
   - Problem: Uncle Bill is John's uncle/guardian (raised him after father's death), not his brother
   - Evidence from text: "I was not his uncle and almost never had I been addressed as 'Bill.'" — but Uncle Bill still functionally served as guardian
   - May be partially addressable through the post-profile correction pass

### MEDIUM

5. **John age "middle-aged" (father's age contamination)** [Profiles]
   - Son is in his early 20s during WWI, not middle-aged
   - **Will likely be fixed** by the post-profile correction (issue #1) since the correction prompt includes age
   - Same root cause as personality contamination

6. **Uncle Bill age "middle-aged" should be "elderly"** [Profiles]
   - Text says "an elderly, grizzled, small man"
   - Will be fixed by issue #2 (direct appearance injection) if age is also extracted

7. **Summary regression: "brother's grandson" returned** [Summaries]
   - Summary says "his deceased brother's grandson, John" — should be "his cousin's son"
   - The code fix from attempt 6 (summary prompt guidance) is still present
   - This is LLM stochasticity — the prompt guides away from wrong family terms but doesn't guarantee it
   - Score impact: 8.5→8.0 (still passing, not urgent)

### LOW

8. **Uncle Bill verbal tics confused** [Profiles]
   - "addressing John as 'Uncle Bill' despite not being his uncle" — this describes how others address HIM, not his verbal tic
   - Minor — Uncle Bill's example quotes are excellent

9. **Some pronunciation entries have "unknown" category** [Pronunciation]
   - Piave, Venetia, Tagliamento, Bersagliari — should be "foreign" category
   - Score impact minimal — IPA and notes are correct

10. **"dum-dums" note says "colloquial term for beans"** [Pronunciation]
    - In WWI context, dum-dum bullets (expanding bullets) — not beans
    - Minor factual error in pronunciation notes

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
  - Result: Post-profile correction **CRASHED** (wrong method: `.generate()` instead of `.query()`). Narrator regex search added but appearance still "Unknown." Net effect: no improvement over attempt 6, slight summary regression.

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
| 7 | Profiles: post-profile correction | src/analyzer.py:2054 (`.generate()` call) | **CRASHED** — wrong method name `.generate()` instead of `.query()` |
| 7 | Profiles: narrator regex search | src/analyzer.py:2687 (self-description regex) | **NO CHANGE** — regex added but appearance still "Unknown" |

## Configuration Notes
- Model: qwen3-next:80b-a3b-instruct-q8_0 (ollama) for all agents
- character_llm_chunk_chars: 5000 (appropriate for 5,048 word text)
- All characters from `supporting_*` IDs — main_cast pipeline did not fire
- Temperature: 0.7 for all agents
- Total time: 13m 34s, 32 LLM calls, 51,891 tokens
- 4 profiles generated with HIGH confidence
- 18 pronunciation flags; categories populated (homograph, unknown, proper_noun, foreign)

## Priority Fix Guidance for Attempt 8

**ONE failing category: Profiles at 6/10 → needs 8.0 (+2.0)**

### FIX 1 (CRITICAL — ONE-LINE FIX): Fix post-profile correction method name

The post-profile correction approach is **CORRECT** and already implemented. It just crashed due to a wrong method name.

**At `src/analyzer.py:2054`:**
```python
# CURRENT (broken):
_corr_response = profile_llm.generate(correction_prompt)

# FIX:
_corr_response = profile_llm.query(correction_prompt)
```

**IMPORTANT:** `query()` returns an `LLMResponse` object, not a string. Check how the response is used on subsequent lines — ensure it accesses `_corr_response.text` (or whatever attribute `LLMResponse` uses) to get the string content. Look at how `profile_llm.query()` is called elsewhere in analyzer.py for the correct pattern.

This fix should resolve:
- John personality contamination (CRITICAL)
- John age "middle-aged" → should become early 20s (MEDIUM)

### FIX 2 (HIGH): Direct narrator appearance injection

The narrator self-description regex is in place but the LLM still outputs "Unknown." Instead of relying on the LLM, directly inject the appearance when the regex matches:

**At `src/analyzer.py` near line 2694-2700 (after regex match is found):**
```python
# After finding the match, directly set appearance on the character
# instead of just creating a synthetic mention
if _m and is_narrator and hasattr(character, 'appearance') and character.appearance:
    desc_text = _m.group()
    # Strip "I am/was" prefix to get just the description
    cleaned = re.sub(r'^I[\s.…]*(?:am|was)\s*', '', desc_text, flags=re.IGNORECASE).strip()
    if cleaned and character.appearance.get("summary", "").lower() in ("unknown", ""):
        character.appearance["summary"] = cleaned
        logger.info(f"Narrator '{character.canonical_name}': directly set appearance from self-description: {cleaned}")
        # Also set age from description keywords
        if any(w in desc_text.lower() for w in ("elderly", "old", "aged")):
            character.appearance["age_indication"] = "elderly"
```

**NOTE:** This code must run AFTER the profile is generated (post-processing), not before. If the appearance dict is created during profiling, this injection should happen after the profile generation loop, similar to the post-profile correction pass.

### WARNING: src/analyzer.py modified in 6 of 7 attempts
This file is the correct location for both fixes. Fix 1 is a one-line change to existing code. Fix 2 is a small addition to existing regex match handling.

## Attempt 8 Fixes Applied

### FIX 1 (CRITICAL — DONE): Fixed post-profile correction method name
- Changed `profile_llm.generate(correction_prompt)` → `profile_llm.query(correction_prompt)`
- Added `_corr_response_text = _corr_response.content if _corr_response.success else ""`
- Updated all downstream uses of `_corr_response` to use `_corr_response_text`
- Location: `src/analyzer.py` (~line 2096)
- Smoke test: Pre-existing test suite passes (no new failures)

### FIX 2 (HIGH — DONE): Direct narrator appearance injection (post-profile pass)
- Added a new post-profile pass (after all profiles generated, before bidirectional rels)
- For each narrator with `appearance["summary"] == "Unknown"`, searches text for first-person self-description regex
- Directly injects the cleaned description and age indication
- Runs at `src/analyzer.py:1916-1956` (after profile generation loop)
- NOTE: Previous attempt added injection INSIDE `_generate_character_profile` where `character.appearance` is None — this was dead code. New injection correctly runs POST-profile where `char.appearance` is already set.
- Universality: Universal invariant — any first-person narrator who describes themselves physically gets that description injected if LLM returns "Unknown"

## Next Action
Re-run analysis to verify fixes.
