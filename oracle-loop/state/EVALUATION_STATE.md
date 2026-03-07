# Current Evaluation State

## Active Text
- **Name:** i_have_no_mouth
- **Attempt:** 16
- **Phase:** awaiting_analysis
- **baseline_score:** 6.35
- **Competitive Mode:** none

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 4.5/10 ✗
  - Completeness: 6/10
  - Identity Resolution: 4/10
  - Alias Grouping: 4/10
- Character Profiles: 5/10 ✗
- Chapter Summaries: 6.5/10 ✗
- Pronunciation Guide: 8.5/10 ✓
- HTML Presentation: 7.5/10 ✗
- **Overall: 6.58/10**

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (4 categories below threshold: Character Extraction, Character Profiles, Chapter Summaries, HTML Presentation)

## What Changed (Attempt 15 → 16)
- **REGRESSION: "the ice caverns" is now the NARRATOR** — Attempt 15 had Ellen+Gorrister as narrators (wrong but human). Now a LOCATION is the narrator. Strictly worse.
- **STEP 5.8.4 fix didn't help** — narrator_name was "the narrator" (generic), not "Ted", so the name-to-ID resolver never matched.
- **STEP 4.24 self-identification scan still not firing** — Same failure as attempt 15. The "I am Ted" pattern is not being found.
- **AM aliases still zero** — Rule 0.5 blocks "Allied Mastercomputer" because core noun 'mastercomputer' != 'am'. Acronym expansions need Rule 0.5 exemption.
- **"the ice caverns" still present** — No location filtering was implemented in attempt 15→16 fixes.

## Current Issues (Priority Order)

### CRITICAL
1. **Ted is NOT the narrator — "the ice caverns" is falsely marked as narrator** [Identity Resolution + Profiles + Summaries]
   - Problem: `the ice caverns.is_narrator=True`, `Ted.is_narrator=False, role=main, id=supporting_0, mentions=5`. Ted is the ONLY narrator — he narrates in first person throughout.
   - Evidence: The story literally contains "I am Ted" or "My name is Ted" — a definitive self-identification.
   - Root cause chain: (1) STEP 4.24 self-identification scan does NOT fire → (2) narrator_name stays generic "the narrator" → (3) STEP 5.8.4 name resolver can't match generic name → (4) STEP 5.8.5 LLM re-detection runs and picks wrong entity → (5) "the ice caverns" gets narrator=True
   - **The fundamental fix: STEP 4.24 must be debugged.** Check:
     - Does it scan RAW TEXT or summaries? It MUST scan raw text.
     - Is the raw text (`full_text` or `raw_text`) available at that point?
     - What exact regex pattern does it use? Does it match "I'm Ted" or "I am Ted"?
     - Is there a case sensitivity issue?
     - Does it run BEFORE or AFTER the character list is populated? (If Ted isn't in the cast yet, name matching fails)
   - Location: `src/agents/characters.py` (STEP 4.24)
   - Fix approach: **Print/log the raw text snippet and pattern match results in STEP 4.24.** Then fix whatever is broken. If raw text isn't available, thread it through. If the pattern is wrong, fix it. This has been broken for 6+ attempts — it needs actual debugging, not more workarounds.

2. **"the ice caverns" is a spurious character AND the narrator** [Completeness + Identity Resolution]
   - Problem: A physical location extracted as a character with `role=protagonist, mentions=5, is_narrator=True`. Has relationships like "comrade" to humans — nonsensical.
   - Evidence: Ice caverns are where canned food is stored — passive scenery, not a narrative entity.
   - Location: Likely extracted by main_cast pipeline (`id=main_cast_11`). Needs location-noun filtering.
   - Fix: Add location/geographical terms to an exclusion list in main_cast extraction. Terms: "caverns", "caves", "mountains", "forest", "castle", "city", "village", "river", "cavern", "tunnel", "chamber". Block any character whose canonical name consists entirely of articles + location nouns.

### HIGH
3. **AM has zero aliases** [Alias Grouping]
   - Problem: AM should have aliases: "Allied Mastercomputer", "Adaptive Manipulator", "Aggressive Menace".
   - Root cause: Rule 0.5 (symbolic object semantic guard) blocks "Allied Mastercomputer" because core noun 'mastercomputer' != 'am'. This rule is designed for objects like "the Ebony Clock" but incorrectly fires on acronym expansions.
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` (Rule 0.5 in verify_aliases)
   - Fix: **Acronym expansions must be exempt from Rule 0.5.** Detection: if the canonical name is ALL-CAPS and ≤4 chars, and the alias initials spell the canonical name, it's an acronym expansion → skip Rule 0.5. Example: canonical="AM", alias="Allied Mastercomputer" → initials "A.M." match → exempt.

4. **Ted has role=main but is in supporting cast** [Completeness]
   - Problem: Ted has `id=supporting_0` with only 5 mentions. As first-person narrator, Ted should be protagonist.
   - Root cause: Mention counting only counts explicit name references. In first-person narration, "I"/"me"/"my" are all Ted but not counted.
   - Fix: Will auto-resolve when Ted is correctly identified as narrator. STEP 5.9.6 narrator role invariant should elevate to protagonist.

### MEDIUM
5. **Ted has no profile** [Profiles]
   - Problem: No physical description, no personality traits, no speech patterns. Only relationships.
   - Fix: Will auto-resolve when Ted is narrator/protagonist and gets full profiling.

6. **Summary uses "the narrator" instead of "Ted"** [Summaries]
   - Problem: Summary says "the narrator kills him" instead of "Ted kills him".
   - Fix: Will auto-resolve when narrator detection is fixed and narrator name substitution works.

7. **HTML shows "the ice caverns" as narrator** [Presentation]
   - Problem: Misleading narrator attribution visible in the report.
   - Fix: Will auto-resolve when ice caverns is filtered and Ted is narrator.

### LOW
8. **Chapter title is null** [Structure]
   - Single section with `title: null`. Minor for a short story with no heading.

## Fix Priority

**Everything cascades from CRITICAL #1 (Ted not narrator) and CRITICAL #2 (ice caverns as character).**

The fix phase MUST:
1. **Actually debug STEP 4.24** — read the code, add logging if needed, run a targeted test. Stop applying workarounds without understanding WHY the scan doesn't fire. This is attempt 16 and the same issue keeps recurring.
2. **Add location-noun filtering** to block "the ice caverns" from extraction.
3. **Exempt acronym expansions from Rule 0.5** so AM gets its aliases.

If Ted is correctly identified as narrator:
- Role elevates to protagonist (STEP 5.9.6)
- Full profile gets generated
- Summary substitutes "Ted" for "the narrator"
- Profiles score: 5 → ~8
- Summaries score: 6.5 → ~8
- Character Extraction score: 4.5 → ~8
- HTML Presentation score: 7.5 → ~8.5

## Root Cause Analysis: Why Does STEP 4.24 Keep Failing?

**This is the #1 question the fix phase must answer.** Across attempts 14-16:
- Attempt 14: STEP 4.24 fired, Ted identified as narrator ✓
- Attempt 15: STEP 4.24 did NOT fire ✗
- Attempt 16: STEP 4.24 did NOT fire ✗

Possible causes:
1. **Raw text not available** — STEP 4.24 may reference a variable that's None or empty
2. **Pattern too strict** — Maybe the text says "I'm Ted" not "I am Ted", or there's punctuation between words
3. **Character list not populated yet** — If Ted isn't in the cast when STEP 4.24 runs, name matching fails
4. **Code path not reached** — Maybe an earlier condition short-circuits past STEP 4.24
5. **LLM non-determinism in text content** — If STEP 4.24 scans summaries (not raw text), different LLM runs produce different text

**The fix phase MUST read the STEP 4.24 code, understand its inputs, and test it directly.** No more blind fixes.

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.35 | 0 | Baseline |
| 2 | 7.3 | +0.95 | Benny dedup, narrator=Ted, but dup Ted |
| 3 | 7.8 | +1.45 | Relationship vocab, pronunciation fixed |
| 4 | 7.6 | +1.25 | Fixes didn't take effect |
| 5 | 8.1 | +1.75 | Dup Ted fixed, AM antagonist, self-alias fixed |
| 6 | 8.4 | +2.05 | Semantic direction bug |
| 7 | 6.65 | +0.30 | REGRESSION: Ted missing |
| 8 | 8.50 | +2.15 | Ted restored, all roles correct |
| 9 | 7.25 | +0.90 | REGRESSION: Ellen narrator |
| 10 | 7.65 | +1.30 | Ted narrator restored |
| 11 | 8.30 | +1.95 | Major progress |
| 12 | 8.20 | +1.85 | Nimdok fixed but LLM regression |
| 13 | 7.23 | +0.88 | REGRESSION: ice caverns narrator |
| 14 | 7.20 | +0.85 | Ted narrator restored, summary wrong |
| 15 | 6.73 | +0.38 | REGRESSION: Ted lost narrator again |
| 16 | 6.58 | +0.23 | REGRESSION: ice caverns is narrator now |

## Pipeline Notes (Attempt 16)
- Analysis completed in 22m 8s
- 7 characters found (including spurious "the ice caverns")
- "the ice caverns" marked as narrator (WORST result yet)
- Ted: is_narrator=False, role=main, id=supporting_0, mentions=5
- STEP 5.8.4 fix: narrator_name="the narrator" (generic) — name resolver couldn't match
- STEP 4.24: did NOT fire (same as attempt 15)
- AM: zero aliases (Rule 0.5 blocks acronym expansions)
- Pronunciation: 10 entries, all correct
- Model: qwen3-next:80b-a3b-instruct-q8_0 (all agents)

## Fix History (Attempt 17)
- **Ted narrator fix (CRITICAL):**
  - Root cause: LLM returns narrator_name="the narrator" (generic) not "Ted"; STEP 4.5b only fires when narrator_name is None, missing generic placeholders; STEP 5.8.5 then re-runs LLM with wrong main_cast
  - Fix A: Extended STEP 4.5b condition to also fire when narrator_name is a generic placeholder ("the narrator", "narrator", "protagonist", etc.) — vocative search then returns "Ted"
  - Fix B: Extended STEP 5.8.4b to search supporting_cast for narrator_name (after self-id scan) — finds Ted in supporting_0, promotes to main_cast, sets narrator_character_id before STEP 5.8.5 can run
  - Fix C: Added STEP 4.24 else branch update — saves self-id name (belt-and-suspenders)
  - Smoke test: `_find_narrator_name_from_vocative` confirmed returns "Ted" (vocative=3, total=5) from actual text
- **AM aliases fix (HIGH):**
  - Root cause: Rule 0.5 in verify_aliases blocks "Allied Mastercomputer" because core noun "mastercomputer" ≠ "am"
  - Fix: Added acronym expansion exemption to Rule 0.5 — if canonical is ALL-CAPS (2-5 chars) and alias initials match canonical, skip semantic check
  - Universal: acronym expansions are a well-defined linguistic pattern (AM = Allied Mastercomputer)
- Modified: src/agents/characters.py (STEP 4.5b, STEP 4.24 else, STEP 5.8.4b), src/pipeline/character_extraction_v2/main_cast.py (Rule 0.5)

## Fix History (Previous)
- Attempt 2: Benny dedup, vocative narrator, pronunciation fixes
- Attempt 3: Same-name guard, adversarial role correction, relationship vocab, pronunciation whitelist
- Attempt 4: STEP 5.8 dedup, victim label, self-relationship filter (none worked)
- Attempt 5: Placeholder merge, incoming adversarial, false antagonist, self-alias filter (3/4 worked)
- Attempt 6: ACTIVE/PASSIVE labels, colleague consistency (neither worked)
- Attempt 7: Direction-aware aggressor labels (didn't fix)
- Attempt 8: Narrator vocative expansion, false-antagonist threshold (BOTH worked)
- Attempt 9: Colleague replacement (partial), Ellen narrator regression
- Attempt 10: Mention-ratio narrator validation (worked)
- Attempt 11: Post-Phase-B role correction, summary narrator substitution (mostly worked)
- Attempt 12: "fellow victim" guard (worked but LLM regression)
- Attempt 13: Narrator elevation, possessive filter (neither fired)
- Attempt 14: Self-identification scan STEP 4.24 (worked for narrator, not role), antagonist threshold (worked)
- Attempt 15: Summary prompt, narrator invariant STEP 5.9.6, acronym injection STEP 1.2, homograph exclusion (only homograph exclusion worked)
- Attempt 16: STEP 5.8.4 narrator name resolver, STEP 1.2 standalone char removal (neither worked — name was generic, Rule 0.5 blocked aliases)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 2 | Dup Benny | characters.py (Pass -1 dedup) | Fixed |
| 2 | Wrong narrator | characters.py (vocative + STEP 4.5b) | Fixed but introduced dup Ted |
| 2 | Pronunciation FPs | cmu_proposer.py, enricher.py | Partially fixed |
| 3 | Dup Ted | characters.py (STEP 5.8.5b) | No change |
| 3 | AM wrong role | analyzer.py | No change |
| 3 | Relationship vocab | analyzer.py | Fixed |
| 3 | Pronunciation FPs | cmu_proposer.py | Fixed |
| 4 | Dup Ted | characters.py (STEP 5.8) | No change |
| 4 | AM wrong role | analyzer.py | No change |
| 5 | Dup Ted | characters.py (STEP 5.2b) | **Fixed** |
| 5 | AM wrong role | analyzer.py | **Fixed** |
| 5 | False antagonist | analyzer.py | **Partial** |
| 5 | AM self-alias | characters.py | **Fixed** |
| 6 | Wrong roles | analyzer.py | No change |
| 7 | Wrong roles | analyzer.py | No change |
| 8 | Ted missing | characters.py (STEP 4.25b) | **Fixed** |
| 8 | Wrong roles | analyzer.py | **Fixed** |
| 9 | Colleague labels | analyzer.py | **Partial** |
| 10 | Narrator fix | characters.py (STEP 4.27) | **Fixed** |
| 11 | Roles + colleagues | analyzer.py | **Partial** |
| 11 | Summary narrator | analyzer.py | **Fixed** |
| 12 | Nimdok antagonist | analyzer.py | **Fixed** |
| 13 | Narrator elevation | narrator.py | No change |
| 13 | Possessive filter | characters.py | No change |
| 14 | Self-identification | characters.py (STEP 4.24) | **Fixed** (narrator only) |
| 14 | Antagonist threshold | analyzer.py | **Fixed** |
| 15 | Summary prompt | summarizer.py | No change (LLM still chose Ellen) |
| 15 | Narrator invariant | characters.py (STEP 5.9.6) | No change (Ted not narrator) |
| 15 | Acronym injection | characters.py (STEP 1.2) | **Bug** (created standalone char) |
| 15 | Homograph exclusion | homograph_proposer.py | **Fixed** |
| 16 | Narrator name resolver | characters.py (STEP 5.8.4) | No change (name was generic) |
| 16 | Acronym dedup | characters.py (STEP 1.2) | No change (Rule 0.5 blocked first) |

**PATTERN ALERT:** Narrator detection has been fixed and broken 7+ times across 16 attempts. The fix phase MUST:
1. READ the STEP 4.24 code and understand exactly what it does
2. TEST it in isolation with the actual raw text
3. Fix the root cause, not add another workaround layer

## Key Debugging Notes for Fix Phase

1. **CRITICAL: Debug STEP 4.24.** Read `src/agents/characters.py` around STEP 4.24. Determine:
   - What text does it scan? (raw text variable name, where it comes from)
   - What pattern does it match? (exact regex)
   - Is the text actually populated at runtime?
   - Does the character "Ted" exist in the cast when the scan runs?
   - Add a print/log statement to see the scan input and results

2. **HIGH: Exempt acronym expansions from Rule 0.5.** In `main_cast.py`, Rule 0.5 checks core noun similarity. Add: if canonical is all-caps ≤4 chars and alias initials match canonical, skip Rule 0.5.

3. **HIGH: Filter location nouns.** Add exclusion for geographical/architectural terms in character extraction. "caverns", "caves", "mountains", etc. should not be character names.

## Output Files
- HTML: ../output/i_have_no_mouth/report.html
- JSON: ../output/i_have_no_mouth/analysis.json
