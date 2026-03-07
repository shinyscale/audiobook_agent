# Current Evaluation State

## Active Text
- **Name:** i_have_no_mouth
- **Attempt:** 15
- **Phase:** awaiting_fix
- **baseline_score:** 6.35
- **Competitive Mode:** none

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 5/10 ✗
  - Completeness: 6/10
  - Identity Resolution: 7/10
  - Alias Grouping: 4/10
- Character Profiles: 5.5/10 ✗
- Chapter Summaries: 6/10 ✗
- Pronunciation Guide: 8.5/10 ✓
- HTML Presentation: 8/10 ✓
- **Overall: 6.73/10**

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold: Character Extraction, Character Profiles, Chapter Summaries)

## What Changed (Attempt 14 → 15)
- **Pronunciation improved** — Common homograph exclusion WORKED. Down from 16 to 10 entries, no false positives. Pronunciation now passes.
- **REGRESSION: Ted lost narrator status** — Attempt 14 had Ted as `is_narrator=True` via self-identification scan. Attempt 15 has Ellen AND Gorrister as narrators, Ted is `is_narrator=False, role=minor, mentions=5`.
- **REGRESSION: "the ice caverns" is back** — Spurious location-as-character returned (was gone in attempt 14).
- **Acronym injection FAILED** — Created a standalone "Allied Mastercomputer" character instead of adding alias to AM. The standalone char was apparently merged or removed, but AM still has zero aliases.
- **Narrator role invariant (STEP 5.9.6) never fired** — Because Ted isn't identified as narrator, the invariant has nothing to elevate.

## Current Issues (Priority Order)

### CRITICAL
1. **Ted is NOT the narrator — Ellen and Gorrister are falsely marked** [Identity Resolution + Profiles + Summaries]
   - Problem: `Ellen.is_narrator=True`, `Gorrister.is_narrator=True`, `Ted.is_narrator=False`. Ted is the ONLY narrator of this story. He narrates in first person throughout. The last line "I have no mouth, and I must scream" is Ted's.
   - Evidence: Ted has only 5 mentions (should be much higher as first-person narrator). Ellen has 30, Gorrister has 29. The V2 pipeline selected Ellen as narrator.
   - Root cause: The self-identification scan (STEP 4.24 "I am Ted") worked in attempt 14 but NOT in attempt 15. LLM non-determinism in the V2 pipeline picks different narrators each run. The scan depends on finding "I am {name}" in text — if the LLM summary doesn't preserve that phrase, the scan fails.
   - Impact: CASCADING — wrong narrator breaks profiles (Ted has no full profile, just a brief description), summaries (uses "the narrator" instead of "Ted"), and relationships (Ted-AM is "colleague" instead of "tormentor").
   - Location: `src/agents/characters.py` (STEP 4.24 self-identification scan), `src/pipeline/character_extraction_v2/` (narrator detection)
   - Fix approach: **Make narrator detection deterministic.** Scan the RAW TEXT (not summaries) for "I am {character_name}" patterns. This story literally contains "I am Ted" or similar self-identification. A raw-text scan is immune to LLM non-determinism. If STEP 4.24 already does this, debug why it didn't fire — perhaps it's scanning summaries instead of raw text, or the text preprocessing strips the phrase.

2. **Ted has role=minor with only 5 mentions** [Completeness]
   - Problem: The first-person narrator/protagonist has `role=minor` and only 5 detected mentions. As the narrator of a first-person story, Ted should have hundreds of implicit mentions (every "I", "me", "my").
   - Evidence: Ted performs the climactic mercy killings, is the sole survivor transformed into a mouthless blob, and narrates the entire story.
   - Root cause: Mention counting only counts explicit name references. In first-person narration, the narrator's name appears rarely since they use "I" instead.
   - Fix: This will auto-resolve if Ted is correctly identified as narrator. The narrator role invariant (STEP 5.9.6) should then elevate role to protagonist.

### HIGH
3. **AM has zero aliases** [Alias Grouping]
   - Problem: AM should have aliases: "Allied Mastercomputer", "Adaptive Manipulator", "Aggressive Menace". The text explicitly states these are what AM stands for.
   - Evidence: Attempt 15 pipeline notes say "Acronym injection BLOCKED: 'Allied Mastercomputer' claimed by another character (injection created standalone char)".
   - Root cause: STEP 1.2 acronym injection created a SEPARATE character entry for "Allied Mastercomputer" instead of adding it as an alias to the existing AM character. Then Rule 3 blocked it because another character (the standalone entry) already claimed the name.
   - Location: `src/agents/characters.py` (STEP 1.2 acronym alias injection)
   - Fix: STEP 1.2 must inject aliases INTO the existing character's alias list, not create new character entries. The code should: (1) find the existing character with the all-caps name, (2) append the expansion to that character's aliases list. Do NOT create new MainCastProfile entries.

4. **"the ice caverns" is a spurious character** [Completeness]
   - Problem: "the ice caverns" is a location/setting, not a character. It has `role=main`, `mentions=5`, and nonsensical relationships ("destination of hope", "colleague" to Ted).
   - Evidence: The ice caverns are where the canned food is stored — a physical place, not a narrative entity. Unlike symbolic forces (e.g., "the monkey's paw" which acts as an antagonistic force), ice caverns are passive scenery.
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` or `src/agents/characters.py`
   - Fix: Location/setting nouns should be filtered. Add common geographical/architectural terms ("caverns", "caves", "mountains", "forest", "castle", "city", "village", "river") to a location-noun exclusion list that blocks extraction as characters. Alternatively, if "the ice caverns" comes from F6 reconciliation, filter there.

### MEDIUM
5. **AM→Ted relationship is "colleague"** [Profiles]
   - Problem: AM's relationship to Ted is listed as "colleague". Ted's relationship to AM is also "colleague". AM is Ted's tormentor/captor, not colleague.
   - Evidence: AM tortures all five humans. The correct label is "tormentor" or "captor" (as used for AM→Ellen, AM→Gorrister, etc.).
   - Root cause: Ted's low mention count (5) and minor role means the profiler doesn't generate a proper profile. AM-Ted relationship defaults to generic "colleague".
   - Fix: Will likely auto-resolve when Ted is correctly identified as narrator/protagonist and gets a full profile.

6. **Ted has no full profile** [Profiles]
   - Problem: Ted only has a brief supporting-character description ("passive participant in a group"). No personality traits, no voice guidance, no detailed relationships.
   - Evidence: HTML shows Ted in the "Supporting Characters" table, not in the "Character Profiles" section.
   - Fix: Will auto-resolve when Ted is correctly identified as narrator/protagonist.

7. **Summary uses "the narrator" instead of "Ted"** [Summaries]
   - Problem: Chapter summary says "the narrator kills him" and "preserves the narrator in a mutilated, mouthless form". Should say "Ted".
   - Root cause: Narrator name substitution can't work because Ted isn't identified as narrator.
   - Fix: Will auto-resolve when narrator detection is fixed.

### LOW
8. **Chapter title is null** [Structure]
   - Single section with `title: null`. Minor for a short story with no heading.

## Fix Priority

**Everything cascades from CRITICAL #1 (Ted not narrator).** If Ted is correctly and reliably identified as narrator:
- Role elevates to protagonist (STEP 5.9.6 invariant fires)
- Full profile gets generated
- Summary substitutes "Ted" for "the narrator"
- AM→Ted relationship becomes "tormentor" not "colleague"
- Profiles score jumps from 5.5 → ~8
- Summaries score jumps from 6 → ~8

**HIGH #3 (AM aliases)** is a code bug in STEP 1.2 — it creates standalone characters instead of injecting into existing ones.

**HIGH #4 (ice caverns)** needs location filtering.

## Root Cause Analysis: Why Does Narrator Detection Keep Failing?

Across 15 attempts, Ted has been correctly identified as narrator in attempts 2, 5, 8, 10, 11, 14 — and INCORRECTLY in attempts 7, 9, 12, 13, 15. The success rate is ~50%, which means the narrator detection is non-deterministic.

The fundamental problem: **narrator detection relies on LLM output** (which character the LLM names as narrator in summaries/extraction). For a first-person story where the narrator's name appears rarely, the LLM picks different characters each run.

**The fix must be deterministic.** Scan the raw text for explicit self-identification patterns:
- "I am {Name}" / "my name is {Name}" / "call me {Name}"
- These are authorial signals that definitively identify the narrator
- This scan should override any LLM-based narrator detection
- Must run on RAW TEXT, not LLM-generated summaries

If this scan already exists (STEP 4.24), it may be:
1. Running on summaries instead of raw text
2. Case-sensitive and missing the pattern
3. Running before the character is in the cast list
4. Being overridden by later steps

**The fix phase MUST debug why STEP 4.24 didn't fire in attempt 15 when it fired in attempt 14.**

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
| 15 | 6.73 | +0.38 | REGRESSION: Ted lost narrator again, pronunciation fixed |

## Pipeline Notes (Attempt 15)
- Analysis completed in 22m 14s
- 7 characters found (including spurious "the ice caverns")
- Ellen and Gorrister both marked as narrators (WRONG)
- Ted: is_narrator=False, role=minor, 5 mentions
- AM: role=antagonist, zero aliases (acronym injection created standalone char)
- Homograph exclusion WORKED — pronunciation down from 16 to 10 entries
- Model: qwen3-next:80b-a3b-instruct-q8_0 (all agents)

## Fix History
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
- Attempt 13: Narrator role elevation, possessive filter (neither fired)
- Attempt 14: Self-identification scan STEP 4.24 (worked for narrator, not role), antagonist threshold (worked)
- Attempt 15: Single-chapter prompt guideline, narrator role invariant STEP 5.9.6, acronym injection STEP 1.2, homograph exclusion (only homograph exclusion worked)

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

**PATTERN ALERT:** Narrator detection has been fixed and broken 6+ times across 15 attempts. The fix phase MUST implement a deterministic solution that does not depend on LLM output. Raw-text self-identification scanning is the only reliable approach.

## Key Debugging Notes for Fix Phase

1. **CRITICAL: Debug STEP 4.24 self-identification scan.** It worked in attempt 14 but not 15. Check:
   - Does it scan raw text or summaries?
   - Is the raw text available at that point in the pipeline?
   - Does it run before or after the V2 pipeline sets Ellen as narrator?
   - Is it being overridden by a later step?

2. **HIGH: Fix STEP 1.2 acronym injection.** It must add aliases to existing characters, not create new entries. The current code apparently calls something that creates a new MainCastProfile.

3. **HIGH: Filter location nouns.** "the ice caverns" should not be extracted as a character.

## Output Files
- HTML: ../output/i_have_no_mouth/report.html
- JSON: ../output/i_have_no_mouth/analysis.json

## Fix Applied (Attempt 15 → 16)

### Fix 1 (CRITICAL): STEP 5.8.4 — Narrator name-to-ID resolver before LLM re-detection
- **Root cause:** STEP 4.25b correctly identifies "Ted" via vocative pattern but sets `narrator_character_id=None`. STEP 5.8.5 then re-runs LLM detection (condition: narrator_character_id is None) which picks Ellen/Gorrister again.
- **Fix:** Added STEP 5.8.4 before STEP 5.8.5: when narrator_name is known but narrator_character_id is None, do a deterministic name lookup in main_cast. If Ted is in main_cast, resolve and skip LLM re-detection.
- **Smoke test:** PASS — "Ted" in main_cast resolves immediately; STEP 5.8.5 skipped.
- **Files:** `src/agents/characters.py` (STEP 5.8.4 inserted ~line 1755)

### Fix 2 (HIGH): STEP 1.2 — Remove standalone expansion characters after acronym alias injection
- **Root cause:** LLM extracted "Allied Mastercomputer" as standalone character AND as alias of AM. verify_aliases Rule 3 then blocked it (claimed by another character).
- **Fix:** After injecting aliases into AM, scan all other characters for canonical_name matching an alias, and remove them.
- **Files:** `src/agents/characters.py` (STEP 1.2 ~line 252)

**Phase:** awaiting_analysis

## Next Action
Re-run analysis to verify: (1) Ted is narrator, (2) AM has acronym aliases, (3) score improves.
