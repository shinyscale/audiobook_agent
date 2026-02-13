# Current Evaluation State

## Active Text
- **Name:** a_camping_trip
- **Attempt:** 2
- **Phase:** awaiting_evaluation
- **baseline_score:** 8.08
- **Competitive Mode:** single

## Latest Scores
- Structure Detection: 10/10 ✓
- Character Extraction: 6.5/10 ✗ (FAILING)
- Character Profiles: 7/10 ✗ (FAILING)
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 8.5/10 ✓
- HTML Presentation: 9/10 ✓
- **Overall: 8.08/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold)

## Fix History

### Attempt 2 Fixes
**CRITICAL #1: Fixed "Milt" / "Milton Jennings" split**
- Root cause: src/agents/characters.py:_merge_lastname_aliases():line 2227-2256 - common_nicknames dictionary was missing "milt" → "milton" mapping
- Fix: Added "milt": ["milton"] to the common_nicknames reference lexicon
- Smoke test: PASS - verified mapping exists in source code, all character agent tests pass
- Modified: src/agents/characters.py
- Expected impact: Character Extraction 6.5/10 → ~9.0/10 (eliminates false split)

**HIGH #3: Fixed ambiguous bare surname aliases**
- Root cause: src/pipeline/character_extraction_v2/main_cast.py:verify_aliases() - no filtering for bare surnames shared by multiple characters
- Fix: Added RULE 3 at end of verify_aliases() to detect when multiple characters share a surname (e.g., "Milton Jennings", "Mr. Jennings", "Mrs. Jennings" all have surname "Jennings") and remove the bare surname from individual character aliases
- Smoke test: PASS - verified filtering logic exists in source code, all tests pass
- Modified: src/pipeline/character_extraction_v2/main_cast.py
- Expected impact: Character Extraction 6.5/10 → ~8.5/10 (eliminates ambiguous aliases)

**Combined Expected Impact:** Character Extraction 6.5/10 → ~9.0/10

## Current Issues (Priority Order)

### HIGH
2. **Bert's profile has misattributed physical description** (DEFERRED - awaiting Character Extraction fix verification)
   - Problem: Bert's appearance says "brown as a leather glove" but this description is about Lincoln in the narration
   - Location: `src/pipeline/character_profiling/` — passage gathering or evidence attribution
   - Will address if Character Extraction still fails after current fixes

### MEDIUM
4. **Bert's full name "Bert Jenks" not captured** (DEFERRED - lower priority)
   - Problem: The text says "Bert Jenks will lend us his boat" but canonical name is just "Bert"
   - Location: `src/pipeline/character_extraction_v2/main_cast.py` — full name resolution

5. **"kitchen" flagged as pronunciation entry — false positive** (DEFERRED - minor)
   - Problem: Common English word flagged for pronunciation guidance
   - Location: `src/pipeline/pronunciation/` — false positive filtering

6. **All character profiles have null physical_description in JSON** (DEFERRED - not critical)
   - Problem: JSON fields are null but HTML shows profile content (data model mismatch)

### LOW
7. **Narrative style inconsistency** (DEFERRED - cosmetic)
   - Problem: structure overview says "unknown" but plot summary says "first-person retrospective" (actually third-person)

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 2 | CRITICAL #1: Milt/Milton split | src/agents/characters.py | Added nickname mapping |
| 2 | HIGH #3: Ambiguous surnames | src/pipeline/character_extraction_v2/main_cast.py | Added RULE 3 filtering |

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (user-configured, DO NOT CHANGE)
- No LLM retries or JSON parse failures in character extraction
- 1 JSON parse failure in pronunciation enrichment (non-critical)
- Profiling was the bottleneck (16m 24s, 43% of total time)
- All confidence scores are high for characters — the pipeline is confident but had cross-pipeline split issue

## Output Files
- HTML: ../output/a_camping_trip/report.html
- JSON: ../output/a_camping_trip/analysis.json

## Pipeline Notes (Attempt 2)
- Duration: 41m 55s
- Structure: 1 chapter detected (single-chapter short story)
- Characters: 9 characters extracted
- Character extraction used competitive consensus (single mode, 3 temperatures)
- Defensive steps activated:
  - BLOCKED titled people aliases (Lincoln's father, Milton's father/mother)
  - REMOVED ambiguous bare surname aliases (Stewart, Jennings)
  - LOW CONFIDENCE MERGE flagged: 'Stewart' → 'Lincoln Stewart' (score: 0.182)
- Hallucination filters activated:
  - F6: Rejected 'young man with oars' (0 text mentions)
  - F19: Multiple characters flagged for ungrounded evidence quotes
- Pronunciation enrichment: 1 JSON parse failure (non-critical)
- Bottleneck: Character Profiles (40.4% of time, 16m 57s)

## Next Action
Proceed to evaluation phase to score results
