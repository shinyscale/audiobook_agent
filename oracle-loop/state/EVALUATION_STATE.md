# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 9
- **Phase:** awaiting_fix
- **baseline_score:** 6.93
- **Competitive Mode:** single

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json
- Timestamped: ../output/American Sir_20260220_234210/

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 9/10 ✓
  - Completeness: 9/10
  - Identity Resolution: 9/10
  - Alias Grouping: 9/10
- Character Profiles: 6.5/10 ✗ (ONLY FAILING CATEGORY)
- Chapter Summaries: 8.5/10 ✓ (recovered from 8.0 regression — no "brother's grandson")
- Pronunciation Guide: 8.5/10 ✓
- HTML Presentation: 8/10 ✓
- **Overall: 8.38/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (1 category below threshold — Profiles at 6.5/10)

## What Changed from Attempt 7

### Post-profile correction (FIX 1) — FIRED but over-corrected:
- The method name fix (`.generate()` → `.query()`) worked — the correction ran
- It correctly detected personality contamination for John (father's traits on son)
- BUT the corrected personality is **BLANK**: "Insufficient story role evidence available to determine John's true personality" with empty traits list
- **Root cause:** The chapter evidence fed into the correction prompt was too sparse for a single-chapter short story. The LLM detected contamination but couldn't infer correct traits, so it blanked everything
- Net effect: John's personality went from "wrong" to "empty" — marginal improvement in correctness, but useless for narrator prep

### Narrator appearance injection (FIX 2) — DID NOT FIRE:
- The `import re` crash is fixed — the code now runs without error
- BUT the injection code has a **gate condition bug** at `src/analyzer.py:1935`:
  ```python
  if _current_app_summary not in ("", "unknown"):
      continue  # Already has appearance — nothing to inject
  ```
- Uncle Bill's appearance summary is: "The narrator does not provide a direct physical description of himself, but he is implied to be older than John..."
- This verbose non-answer is **neither "" nor "unknown"** — so the gate condition passes through as "already has appearance" and skips injection
- **ROOT CAUSE IDENTIFIED:** The LLM generates verbose "I don't know" answers instead of literal "unknown". The gate condition must be broadened.

### Summary improvement:
- "brother's grandson" error is gone — summary correctly uses "cousin" terminology
- Summary quality is good (8.5/10)

## Current Issues (Priority Order)

### CRITICAL

1. **Narrator appearance injection gate condition too narrow — Uncle Bill appearance still wrong (8th attempt)** [Profiles]
   - Problem: `src/analyzer.py:1935` checks `if _current_app_summary not in ("", "unknown")` but the LLM generates verbose non-answers like "The narrator does not provide a direct physical description..." which don't match either check value
   - Evidence: Uncle Bill's self-description is in the text: "I... am... an elderly, grizzled, small man, grim and unexhilarating" — but his appearance shows the LLM's verbose "I don't know"
   - Location: `src/analyzer.py:1935`
   - **FIX:** Broaden the gate condition to also catch verbose non-answers. Replace:
     ```python
     if _current_app_summary not in ("", "unknown"):
         continue
     ```
     With:
     ```python
     _no_desc_phrases = ("unknown", "does not provide", "no physical description",
                         "not described", "no direct physical", "no description",
                         "not provide a direct")
     _has_real_appearance = _current_app_summary and not any(
         phrase in _current_app_summary for phrase in _no_desc_phrases
     )
     if _has_real_appearance:
         continue
     ```
   - This is universal: any narrator whose LLM profile returns a verbose "I don't know" will now get the self-description injection
   - **ALSO fixes Uncle Bill's age:** The injection code already sets `age_indication` to "elderly" when the self-description contains "elderly" — so fixing the gate also fixes the age from "middle-aged" to "elderly"

2. **Post-profile correction blanks John's personality instead of correcting it** [Profiles]
   - Problem: The correction prompt asks the LLM to generate new traits from chapter evidence, but for a single-chapter story the evidence is too sparse
   - Evidence: John's personality is now: "Insufficient story role evidence available..." with `traits: []`, `temperament: "unknown"`
   - The original (contaminated) traits included some correct ones (e.g., "charming", "courageous in crisis") mixed with father's traits ("financially irresponsible", "emotionally avoidant")
   - Location: `src/analyzer.py:2060-2094` (correction prompt)
   - **FIX:** Modify the correction approach to be **subtractive rather than generative**. Instead of asking the LLM to generate new traits from scratch (which fails with sparse evidence), provide both characters' traits and ask which ones belong to which character:
     ```python
     correction_prompt = f"""Two characters share the first name "{_name_short}": "{_name_short}" and "{_name_long}".

     "{_name_short}"'s story role:
     {ev_short}

     "{_name_long}"'s story role:
     {ev_long}

     "{_name_short}" was assigned these personality traits: {traits_short}
     "{_name_long}" was assigned these personality traits: {traits_long}

     Some of "{_name_short}"'s traits may actually belong to "{_name_long}" (contamination from name overlap).

     For each trait in "{_name_short}"'s list, determine: does it genuinely describe "{_name_short}" based on their story role, or does it better fit "{_name_long}"?

     Return JSON only:
     {{
       "contamination_detected": true or false,
       "reason": "one sentence explanation",
       "corrected_personality": {{
         "summary": "corrected summary for {_name_short} keeping only their genuine traits",
         "traits": ["only traits that genuinely belong to {_name_short}"],
         "temperament": "based on retained traits",
         "emotional_range": "based on retained traits"
       }},
       "corrected_age_indication": "young/middle-aged/elderly/unknown"
     }}

     IMPORTANT: You MUST keep at least the traits that match "{_name_short}"'s story role. Do NOT return an empty traits list — if unsure about a trait, keep it.
     Only include "corrected_personality" and "corrected_age_indication" if contamination_detected is true."""
     ```
   - Key change: **"You MUST keep at least the traits that match"** prevents blanking. The subtractive approach (remove wrong traits) is more reliable than generative (invent new traits) with sparse evidence.

### HIGH

3. **Uncle Bill → John Donaldson relationship: "guardian and adoptive father figure"** [Profiles]
   - Problem: Uncle Bill is John Donaldson's COUSIN, not guardian. Uncle Bill raised John (the son), not John Donaldson (the father). The text says: "I saw the charming boy, a cousin, who had come to be this lad's father"
   - Evidence: Uncle Bill explicitly says he is a cousin of John Donaldson. He was John Donaldson's cousin who later raised John Donaldson's abandoned son.
   - This error has persisted across multiple attempts with various wrong answers
   - Location: Profile generation in `src/analyzer.py` — the relationship extraction prompt or the bidirectional relationship inference
   - Possible fix: The post-profile correction pass could also review relationships, or the relationship prompt needs better guidance about distinguishing who was raised by whom

4. **John's voice guidance completely empty** [Profiles]
   - Problem: Tone "unknown", Dialect "unknown", no verbal tics, no example quotes
   - This is a downstream effect of the blanked personality — when the LLM blanks personality, it also blanks voice guidance
   - Will likely be fixed when issue #2 (personality blanking) is resolved

### MEDIUM

5. **Uncle Bill age still "middle-aged"** [Profiles]
   - Will be fixed by issue #1 (gate condition fix) — the injection code already sets `age_indication` to "elderly" when the description contains "elderly"

6. **"dum-dums" pronunciation note says "colloquial term for beans"** [Pronunciation]
   - In WWI context, dum-dum bullets (expanding bullets banned by Hague Convention) — not beans
   - Minor factual error in pronunciation notes
   - Score impact: negligible

7. **Piave, Venetia, Tagliamento, Bersagliari have "unknown" category** [Pronunciation]
   - These Italian/geographic terms should have category "foreign"
   - Score impact: negligible — IPA and notes are correct

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
| 9 | 8.38 | +1.45 | Post-profile correction FIRED but blanked John's personality. Narrator injection gate condition too narrow. Profiles 6.5/10. Summary recovered to 8.5. |

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

## Configuration Notes
- Model: qwen3-next:80b-a3b-instruct-q8_0 (ollama) for all agents
- character_llm_chunk_chars: 5000 (appropriate for 5,048 word text)
- All characters from `supporting_*` IDs — main_cast pipeline did not fire
- Temperature: 0.7 for all agents
- Total time: 9m 45s, 29 LLM calls, 49,286 tokens
- 4 profiles generated with HIGH confidence
- 18 pronunciation flags; categories populated (homograph, unknown, proper_noun, foreign)

## Priority Fix Guidance for Attempt 10

**ONE failing category: Profiles at 6.5/10 → needs 8.0 (+1.5)**

**Both fixes are in `src/analyzer.py` — small, targeted changes to existing code.**

### FIX 1 (CRITICAL): Broaden narrator appearance injection gate condition

**ROOT CAUSE IDENTIFIED:** The gate condition at `src/analyzer.py:1935` only checks for literal `""` or `"unknown"`, but the LLM generates verbose non-answers. This is why the injection has failed for 8 consecutive attempts.

**At `src/analyzer.py:1934-1936`, replace:**
```python
_current_app_summary = (_nc.appearance.get("summary", "") or "").strip().lower()
if _current_app_summary not in ("", "unknown"):
    continue  # Already has appearance — nothing to inject
```

**With:**
```python
_current_app_summary = (_nc.appearance.get("summary", "") or "").strip().lower()
_no_desc_phrases = ("unknown", "does not provide", "no physical description",
                    "not described", "no direct physical", "no description",
                    "not provide a direct")
_has_real_appearance = _current_app_summary and not any(
    phrase in _current_app_summary for phrase in _no_desc_phrases
)
if _has_real_appearance:
    continue  # Already has a real appearance — nothing to inject
```

**This fixes:**
- Uncle Bill appearance (will inject "an elderly, grizzled, small man, grim and unexhilarating")
- Uncle Bill age (injection code already sets "elderly" when description contains the word)

### FIX 2 (CRITICAL): Make post-profile correction subtractive instead of generative

**At `src/analyzer.py:2060-2094`, modify the correction prompt** to use a subtractive approach. Key changes:
1. Ask the LLM to filter traits rather than generate new ones from scratch
2. Add explicit instruction: "You MUST keep at least the traits that match the character's story role. Do NOT return an empty traits list."
3. Frame it as "which of these traits belong to which character?" rather than "generate correct traits"

The current prompt at line 2079-2081:
```
Do "{_name_short}"'s assigned traits match their actual story role (from chapter summaries above)?
Or do they better match "{_name_long}"'s story role?
```

Should be changed to something like:
```
Review each trait in "{_name_short}"'s list. For each one, does it genuinely describe "{_name_short}" based on their story role above, or does it better fit "{_name_long}"?

Keep all traits that could plausibly describe "{_name_short}". Only remove traits that clearly belong to "{_name_long}" instead.

IMPORTANT: Do NOT return an empty traits list. If uncertain about a trait, keep it for "{_name_short}".
```

### FIX 3 (HIGH but OPTIONAL): Uncle Bill → John Donaldson relationship

This has persisted across all attempts. If there's room, the post-profile correction pass could also review relationships for same-name character pairs. But fixes #1 and #2 are sufficient to reach 8.0 on profiles if they work.

### WARNING: src/analyzer.py modified in 8 of 9 attempts
Both fixes are small, targeted changes to existing code (a gate condition and a prompt). No new functions or major refactors needed.

## Expected Impact of Fixes
- FIX 1: Uncle Bill appearance correct + age correct → +1.0 to profiles
- FIX 2: John personality restored (at least partially) + voice guidance → +0.5 to profiles
- Combined: Profiles 6.5 → ~8.0-8.5
- With relationship fix (#3): Profiles could reach 8.5-9.0

## Next Action
Run PROMPT_fix.md to apply gate condition fix and correction prompt fix.
