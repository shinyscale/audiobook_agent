# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 7
- **Phase:** awaiting_evaluation
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
- Character Profiles: 6.5/10 ✗ (ONLY FAILING CATEGORY)
  - Bidirectional relationship fix WORKED (John→John Donaldson now "son") — +0.5 from attempt 5
  - But personality contamination unchanged — John still has father's traits
- Chapter Summaries: 8.5/10 ✓ (IMPROVED from 7.5 — "brother's grandson" error FIXED)
- Pronunciation Guide: 8.5/10 ✓ (IMPROVED from 8.0 — categories now populated)
- HTML Presentation: 8/10 ✓
- **Overall: 8.25/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (1 category below threshold — Profiles only)

## What Improved from Attempt 5
- **Summary "brother's grandson" error FIXED:** Now correctly says John Donaldson is John's "long-lost father" ✓. No more "brother" or "grandson" errors.
- **Pronunciation categories now populated:** Was all null, now has homograph, unknown, proper_noun, foreign ✓. Score 8.0→8.5.
- **John→John Donaldson bidirectional relationship:** Now correctly says "son" instead of "unknown" ✓. The bidirectional relationship post-processing worked.
- **Uncle Bill verbal tics slightly improved:** No longer reversed ("addressing John as 'Uncle Bill'"). Now says "used the phrase 'Uncle Bill' when addressed by John" — better but still slightly odd.
- **Summaries now PASS threshold:** 7.5→8.5 (+1.0). Major improvement.
- **Score improved:** 7.93 → 8.25 (+0.32)

## What Didn't Improve
- **John (son) personality STILL has father's traits:** "Impulsive, self-centered, and evasive; capable of charm but avoids consequences" — these are the FATHER's traits. The son is brave, earnest, patriotic.
- **John example quotes are father's quotes:** "More money was needed always" and "John always thought that the world owed him a living" — clearly about the FATHER's financial irresponsibility, not the son.
- **John verbal tics:** "thought that the world owed him a living" — FATHER's trait, not son's.
- **John age: "middle-aged"** — wrong for the son (early 20s in WWI). This comes from father evidence contamination.
- **Uncle Bill appearance STILL "unknown":** Despite text saying "I... am... an elderly, grizzled, small man, grim and unexhilarating." The fix attempt didn't fire — warning persists: "No definitive narrator identified from plot summary" and "Narrator 'the elderly, crabbed man' identified but NOT found in main_cast."
- **Uncle Bill→John Donaldson relationship: "father-in-law"** — should be "cousin." The LLM invented a family connection through John's mother.

## Current Issues (Priority Order)

### CRITICAL

1. **John (son) personality has FATHER's traits — 6th consecutive failure** [Profiles]
   - Problem: "John" (supporting_0, 30 mentions) personality: "Impulsive, self-centered, and evasive; capable of charm but avoids consequences"
   - Traits: "impulsive, thriftless, entitled, emotionally avoidant" — ALL are the father's traits
   - Example quotes are FATHER's: "More money was needed always" and "John always thought that the world owed him a living"
   - Verbal tic is FATHER's: "thought that the world owed him a living"
   - The son's actual traits: brave, earnest, patriotic, compassionate, forgiving, warm
   - The son's actual scenes: enlisting as ambulance driver, serving at Caporetto/Piave, reuniting with dying father, forgiving his father
   - **This has persisted through ALL 6 attempts.** Approaches tried:
     - Attempt 5: ±500 char proximity filter — removed all John Donaldson evidence but left father evidence in John's collection
     - Attempt 6: Disambiguation note with V2 character descriptions — insufficient, LLM still assigns father's traits to son
   - The warning "No passages provided for John Donaldson, returning UNCERTAIN" persists — meaning the dedup filter is too aggressive for John Donaldson (removing all his evidence) while not aggressive enough for John (leaving father's evidence)
   - **Root cause analysis:** The text uses just "John" when discussing the father's backstory. The proximity filter can't tell which "John" is being discussed because "John Donaldson" isn't always nearby when the father is discussed as "John." The disambiguation note approach also failed because it's just a hint — the LLM still generates the profile from the contaminated evidence passages.
   - **RECOMMENDED FIX — Post-profile personality correction:** After generating ALL profiles, add a second LLM pass specifically for same-name characters. Prompt: "Two characters share the name 'John': (A) John — the son, an ambulance driver in WWI who reunites with his father at the front. (B) John Donaldson — the father, who faked his death and lived in exile. Character A was assigned these traits: [impulsive, thriftless, entitled, emotionally avoidant]. Character B was assigned these traits: [honest, reflective, resigned, emotionally vulnerable]. Review: Are any of Character A's traits actually about Character B? If so, generate corrected traits for Character A based only on scenes where the SON appears (WWI service, reunion with father, return home)."
   - Location: `src/analyzer.py` — add post-profile correction pass after the main profile generation loop
   - This approach is fundamentally different from previous attempts (which tried to fix evidence BEFORE profiling). By fixing AFTER profiling, both profiles exist and can be compared.

### HIGH

2. **Uncle Bill appearance "unknown" despite first-person self-description** [Profiles]
   - Problem: Text says "I... am... an elderly, grizzled, small man, grim and unexhilarating" — but appearance shows "Unknown physical description"
   - Pipeline warnings: "Narrator 'the elderly, crabbed man' identified but NOT found in main_cast" — narrator detection partially works but can't match to Uncle Bill
   - Uncle Bill IS tagged `is_narrator: true` in character data
   - **6 attempts without resolution**
   - Previous approaches: synthetic early mention (attempt 5), strengthened narrator note (attempt 6) — both failed because narrator identification from plot summary fails
   - **RECOMMENDED FIX:** Don't rely on narrator detection from the plot summary at all. In `_generate_character_profile`, when `character.is_narrator == True`, directly search the FIRST 1000 characters of the raw text for first-person self-descriptions (patterns like "I am/was [adjective]", "I... am... [description]"). Extract any physical description found and PREPEND it to the appearance context. This bypasses the broken narrator detection pathway entirely.
   - Location: `src/analyzer.py` — `_generate_character_profile()` method, appearance extraction section

3. **Uncle Bill→John Donaldson relationship: "father-in-law"** [Profiles]
   - Problem: Should be "cousin" — John Donaldson is Uncle Bill's cousin, not father-in-law
   - The LLM invented "by marriage connection through John's mother, implied by context"
   - This persists from previous attempts (was "brother-in-law and estranged brother" in attempt 5)
   - May improve naturally if the post-profile correction pass (issue #1) also reviews relationships, or could be addressed by providing clearer character description context to the relationship extraction

### MEDIUM

4. **John age listed as "middle-aged"** [Profiles]
   - The son is in his early 20s during WWI, not middle-aged
   - Same root cause as issue #1 — father's age evidence contaminating son's profile
   - Will likely be fixed by the post-profile correction pass

5. **Some pronunciation entries have "unknown" category** [Pronunciation]
   - Piave, Venetia, Tagliamento, Bersagliari — these are Italian/foreign terms but categorized as "unknown"
   - Should be "foreign" category
   - Minor impact — the IPA and notes are correct
   - Location: Foreign term detection in pronunciation pipeline

### LOW

6. **Homographs lack IPA** [Pronunciation]
   - live, minute, read, close, moderate — flagged correctly with descriptive notes but no IPA for each pronunciation
   - Acceptable since both pronunciations are described textually

7. **"dum-dums" note says "colloquial term for beans"** [Pronunciation]
   - Dum-dum bullets are expanding bullets used in warfare — the note misidentifies this term
   - In the context of a WWI story, "dum-dums" almost certainly refers to the expanding bullets
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

## Configuration Notes
- Model: qwen3-next:80b-a3b-instruct-q8_0 (ollama) for all agents
- character_llm_chunk_chars: 5000 (appropriate for 5,048 word text)
- All characters from `supporting_*` IDs — main_cast pipeline did not fire
- Temperature: 0.7 for all agents
- Total time: 14m 21s, 32 LLM calls, 52,541 tokens
- 4 profiles generated with HIGH confidence
- 18 pronunciation flags; categories now populated (homograph, unknown, proper_noun, foreign)

## Priority Fix Guidance for Attempt 7

**ONE failing category remaining: Profiles at 6.5 → needs 8.0 (+1.5)**

### The John personality contamination has now persisted through ALL 6 attempts.

**Approaches that FAILED:**
1. ±500 char proximity filter (attempt 5) — too blunt, removed all John Donaldson evidence while leaving father evidence in John's collection
2. Disambiguation note with V2 descriptions (attempt 6) — insufficient, LLM still generates wrong personality from contaminated evidence

**All previous approaches tried to fix evidence BEFORE profiling. Attempt 7 must fix AFTER profiling.**

### REQUIRED: Post-profile personality correction pass

After generating all profiles in the main loop, add a SECOND LLM call specifically for characters that share a first name:

1. **Detect same-name pairs:** Iterate through characters. If character A's canonical name is a prefix/suffix/substring of character B's canonical name (e.g., "John" and "John Donaldson"), flag them for correction.

2. **LLM correction prompt:** Send BOTH profiles to the LLM:
   ```
   Two characters share the name "John":
   - Character A: "John" (the son) — ambulance driver in WWI, reunites with dying father
   - Character B: "John Donaldson" (the father) — faked death, lived in exile, died at Piave

   Character A was assigned: personality=[impulsive, thriftless, entitled], appearance=[middle-aged]
   Character B was assigned: personality=[honest, reflective, resigned]

   Are any of Character A's traits actually about Character B?
   Provide corrected personality traits, appearance, and verbal tics for Character A
   based ONLY on scenes where the SON appears.
   ```

3. **Apply corrections:** Replace the contaminated profile fields with the LLM's corrected output.

### Uncle Bill appearance: Direct text search for narrator

Don't rely on narrator detection from plot summary. When `character.is_narrator == True`:
- Search the FIRST 1000 chars of raw text for first-person physical self-description patterns
- Regex: `I\s+(?:am|was)\s+.*?(?:man|woman|person|old|young|tall|short|thin|fat|grizzled|small)`
- Apply any found description directly to the character's appearance

### WARNING: src/analyzer.py modified in 5 of 6 attempts
This file MUST be modified again (it's the right place for post-profile processing). But the approach MUST be fundamentally different — post-profile correction, not pre-profile evidence filtering.

## Pipeline Notes (Attempt 7)
- **CRITICAL:** Post-profile correction FAILED: `'LLMClient' object has no attribute 'generate'`
  - The correction pass ran but crashed — wrong method name used
  - John's personality contamination likely UNCHANGED
  - Fix attempt 8: Change `.generate()` to the correct LLMClient method name (probably `.complete()`)
- `No passages provided for John Donaldson, returning UNCERTAIN` — same as before
- `Narrator 'the narrator (unnamed)' identified but NOT found in main_cast` — Uncle Bill appearance still unknown
- `No definitive narrator identified from plot summary` — narrator detection still failing
- `LLM marker proposer returned non-list` — structure detection warnings (benign, 1 chapter correct)
- Run time: 13m 34s, 32 LLM calls, 51,891 tokens

## Next Action
Evaluate attempt 7 output (likely same as attempt 6 since post-profile correction failed)

## Attempt 7 Fix Applied
- **Issue #1 (CRITICAL)**: Post-profile personality correction pass
  - After ALL profiles are generated, find same-name character pairs (where name_a is a prefix of name_b)
  - For each pair, send both personality profiles + summary evidence to LLM
  - LLM detects whether shorter-name character's traits are contaminated by longer-name character
  - If contamination detected, corrected personality (and age_indication) is applied
  - Location: `src/analyzer.py` after bidirectional relationship post-processing
  - Fix type: algorithmic (post-profile LLM verification)

- **Issue #2 (HIGH)**: Narrator first-person self-description search
  - Instead of fixed position 100, regex-searches first 20% of text for "I am/was [physical descriptor]" patterns
  - Handles "I... am..." style (ellipsis between "I" and "am") via `[\s.…]{0,20}` in pattern
  - Falls back to position 100 if no self-description pattern found
  - Location: `src/analyzer.py` narrator synthetic mention block (~line 2687)
  - Fix type: algorithmic (pattern search)
