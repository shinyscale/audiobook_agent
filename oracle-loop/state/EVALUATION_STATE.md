# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 37
- **Phase:** awaiting_fix
- **baseline_score:** 6.60
- **Competitive Mode:** single (all stages: characters, structure, summaries)

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Latest Scores
- Structure Detection: 7/10 ✗
- Character Extraction: 7/10 ✗
  - Completeness: 8/10
  - Identity Resolution: 6/10
  - Alias Grouping: 7/10
- Character Profiles: 5/10 ✗
- Chapter Summaries: 7.5/10 ✗
- Pronunciation Guide: 7/10 ✗
- HTML Presentation: 8/10 ✓
- **Overall: 6.83/10** (reference only)

## Overall Score Calculation

```
Overall = (7 × 0.20) + (7 × 0.25) + (5 × 0.15) + (7.5 × 0.20) + (7 × 0.10) + (8 × 0.10)
        = 1.40 + 1.75 + 0.75 + 1.50 + 0.70 + 0.80
        = 6.90
```

**Overall: 6.90/10** (DOWN from 7.15 in attempt 36)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (5 categories below threshold)

## Detailed Evaluation

### 2.1 Structure Detection: 7/10 ✗ (unchanged)

"American, Sir" is a continuous short story with no chapter markers. The tool produces 2 sections, both with null titles. Per the rubric, a continuous text should be identified as a single section (9-10); splitting into 2 sections is a structural error (6-7). Score 7 because the summaries for each section are coherent and usable.

### 2.2 Character Extraction: 7/10 ✗ (unchanged)

**Character list (8 total, 4 main_cast + 4 supporting):**
- `main_cast_1`: **Uncle Bill** — 18 mentions, role: protagonist, is_narrator: true ✓✓
  - Aliases: ["Bill"] ✓
- `main_cast_2`: **John Donaldson** — 9 mentions, role: supporting, is_narrator: true — this is the SON
  - Aliases: [] ✗ MISSING "Johnny" and "John"
  - is_narrator: true is WRONG — son narrates nested wartime story, but Uncle Bill is the first-person narrator
- `main_cast_3`: **John Donaldson** — 29 mentions, role: antagonist, is_narrator: false — this is the FATHER ✓
  - Aliases: ["John", "the father"] ✓
- `main_cast_4`: **Margaret Donaldson** — 2 mentions, role: supporting ✓
- `supporting_1`: **Joe Barron** — 3 mentions ✓
- `supporting_2`: **Red Cross** — 4 mentions — organization, not character ✗
- `supporting_3`: **Ted Frith** — 5 mentions, alias: "Ted" ✓
- `supporting_5`: **Johnny** — 2 mentions — FALSE SPLIT, should be alias of John Donaldson (son) ✗

**Sub-Dimension A: Completeness: 8/10** (stable)
- All significant characters present ✓
- "Red Cross" is an organization, not a character ✗ (minor)

**Sub-Dimension B: Identity Resolution: 6/10** (stable)
- Father/son correctly kept separate ✓✓
- "Johnny" is a FALSE SPLIT — should be alias of the son ✗✗
- Son incorrectly marked is_narrator: true ✗

**Sub-Dimension C: Alias Grouping: 7/10** (stable)
- Uncle Bill has alias "Bill" ✓
- Son has NO aliases ✗ (regression — had "John" in attempt 36, should also have "Johnny")
- Father has aliases "John", "the father" ✓
- Ted Frith has alias "Ted" ✓
- "Johnny" as separate character rather than alias of son ✗

### 2.3 Character Profiles: 5/10 ✗ (DOWN from 6.5 — MAJOR REGRESSION)

**The target character preference fix MADE THINGS WORSE.** Son and father now have IDENTICAL profiles — every field (appearance, personality, voice_guidance, relationships, evidence) is duplicated word-for-word between the two characters.

- **Uncle Bill**: Good profile ✓
  - Appearance: "elderly, small, grizzled" ✓
  - Personality: "self-sacrificing, loyal, reluctantly compassionate" ✓
  - Voice guidance: "low, restrained, gravelly baritone" ✓
  - Evidence quotes accurate ✓
  - Relationships: "John (father): family", "John Donaldson (son): family", "John Donaldson (father): mentor" — the last one is odd (Uncle Bill as mentor to the FATHER?). Should be mentor to the SON. ✗

- **John Donaldson (son, `main_cast_2`)**: COMPLETELY WRONG — has father's profile ✗✗✗
  - Appearance describes "middle-aged, physically imposing man" — this is the FATHER. The son is a young man (12 when adopted, 18 when enlisted, early 20s during the story).
  - Personality describes "committed serious crimes but redeemed himself through selfless service" — this is the FATHER's arc entirely.
  - Evidence quotes: "'American, sir,' he said proudly" — the FATHER's iconic line.
  - Relationships: "John Donaldson (son): parent" and "Uncle Bill: acquaintance" — these are the FATHER's relationships copied verbatim.

- **John Donaldson (father, `main_cast_3`)**: Has the correct profile content BUT it's identical to the son's ✗
  - The father's profile IS correct for the father — it describes his redemption arc accurately.
  - But the son having an identical copy means the disambiguator failed: it gave both characters the same passages, producing identical LLM-generated profiles.

- **Ted Frith**: IMPROVED from attempt 36 ✓
  - Appearance mentions natural eyes, American uniform ✓
  - Personality: "heroic, courageous, selfless" ✓ (appropriate for Ted's battlefield role)
  - Evidence quotes mostly correct — though "'I'm American to-day, sir!'" is Ted quoting the father, it's borderline acceptable in context since Ted is the one speaking.
  - Score: 7/10 for this individual profile

**Why 5/10:** The critical regression is that son and father have IDENTICAL profiles (word-for-word duplication). In attempt 36, the son had the wrong profile but the father had a unique correct one. Now both have the same content, meaning the disambiguator fix actually removed all differentiation. The father's profile is correct in isolation, but duplicating it to the son is worse than having a contaminated-but-different profile. Uncle Bill's profile remains good. Ted improved slightly.

### 2.4 Chapter Summaries: 7.5/10 ✗ (stable)

**Section 1:** Excellent. Correctly describes the cousin relationship, Margaret Donaldson, the scandal and faked death. Mentions Yale, the financial split of inheritance. ✓

**Section 2:** Good quality but the "sister" hallucination persists:
- "his deceased sister's son" — WRONG. Uncle Bill is the father's COUSIN, not sibling. Section 1 correctly says "cousin." ✗
- Otherwise covers Yale enrollment, fishing trip to Canada, WWI enlistment, Red Cross ambulance work, Caporetto disaster, deathbed reunion and revelation. ✓

### 2.5 Pronunciation Guide: 7/10 ✗ (stable)

20 entries, 15 with IPA.

**Genuinely useful (13):** Caporetto, Piave, Solferino, Guerre, Venetia, Tagliamento, Bersagliari, Bordeaux (foreign terms ✓), live, minute, read, close, moderate (homographs ✓)

**False positives (7):** whippersnapper, thriftless, thickset, manliness, dum-dums, orderlies, mayn't ✗

35% false positive rate. The foreign terms and homographs are excellent, but the false positives keep this at 7.

### 2.6 HTML Presentation: 8/10 ✓ (stable)

Navigation works. Character profiles render well with appearance, personality, voice guidance sections. Uncle Bill displayed as protagonist/narrator. Both John Donaldsons visible with different roles (supporting vs antagonist). Minor issues: "Red Cross" in Supporting Characters, "Johnny" as separate character.

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (user-configured, appropriate)
- Pipeline: V2 with Phase 2 graph-based identity resolution
- 0 LLM retries — good
- 1 JSON parse failure (Pronunciation Guide batch enrichment) — recurring
- Character Profiles: 11 LLM calls, 678s — stage RAN successfully but produced duplicate content
- Grounding gate working — father grounded ✓
- Target preference fix: DID NOT WORK — profiles are now duplicated instead of disambiguated

## Current Issues (Priority Order)

### CRITICAL

1. **Son and father have IDENTICAL profiles (word-for-word duplication)** [Profiles]
   - Problem: `main_cast_2` (son) and `main_cast_3` (father) have exactly the same appearance, personality, voice_guidance, relationships, and evidence quotes. Both describe the father's character arc ("committed serious crimes", "American, sir", "middle-aged, physically imposing"). The son's profile should describe: a young man (early 20s), attended Yale, taken fishing by Uncle Bill, enlisted as WWI ambulance driver, found dying father at Caporetto.
   - Evidence: `jq` shows identical JSON for both characters' appearance, personality, voice_guidance, and relationships fields.
   - Root cause analysis: The attempt 37 fix added a "target character preference" signal (confidence 0.98) to the disambiguator. This signal is TOO STRONG — when gathering passages for the son, it prefers the son (target) for ambiguous mentions. But when gathering for the father, it prefers the father (target) for the same mentions. The result: BOTH characters claim ALL "John Donaldson" passages, producing identical profiles. The signal doesn't disambiguate — it just makes each character's profiling run grab everything.
   - The real problem is deeper: The passage gatherer finds the same passages for both characters because both match "John Donaldson". The disambiguator then assigns them to whichever is the "target" at that moment, so both end up with the same set. The LLM then generates the same profile from the same passages.
   - Location: `src/pipeline/character_profiling/name_disambiguator.py` — Signal 0 (target preference)
   - Fix approach: The target preference signal should be REMOVED or made much weaker. Instead, the fix needs to use CONTEXT-BASED signals that actually distinguish passages about the father vs the son:
     - Passages with "the father", "twenty years ago", "took money", "faked his death" → father
     - Passages with "Yale", "ambulance driver", "enlisted", "the boy", "twelve years old" → son
     - The disambiguator already HAS these context signals (relationship markers, temporal markers, chapter range). The target preference signal at 0.98 confidence is OVERRIDING them all.
   - **Recommended fix:** Remove Signal 0 entirely. The disambiguator's existing signals (relationship markers at 0.95, name-shape at 0.90, temporal markers at 0.80) should be sufficient IF they're actually running before a target preference short-circuits the decision.

### HIGH

2. **"Johnny" false split — should be alias of John Donaldson (son)** [Identity Resolution / Alias Grouping]
   - Problem: `supporting_5` "Johnny" with 2 mentions exists as a separate character. "Johnny" is a childhood nickname for the son.
   - Same as attempt 36. Not addressed in attempt 37.
   - Location: Identity graph / alias resolution — may be blocked by HARD constraint when two "John Donaldson" candidates exist.

3. **Son has no aliases** [Alias Grouping]
   - Problem: `main_cast_2` (son) has an empty alias list. Should have at least "John" and "Johnny".
   - In attempt 36 the son had alias "John". Now the son has NO aliases, while the father has "John". This suggests the alias "John" moved from son to father between attempts.

4. **Summary "sister" hallucination** [Summaries]
   - Problem: Section 2 says "his deceased sister's son" — Uncle Bill is the father's COUSIN, not sibling.
   - Evidence: Section 1 correctly says "cousin."
   - Non-deterministic LLM issue.

5. **Son incorrectly marked as narrator** [Identity Resolution]
   - Problem: `main_cast_2` (son) has `is_narrator: true`. The son narrates his wartime experience within the story (nested narration to Uncle Bill), but Uncle Bill is the actual first-person narrator of the short story. Only Uncle Bill should be `is_narrator: true`.

### MEDIUM

6. **Uncle Bill's relationship "John Donaldson (father): mentor" is inverted** [Profiles]
   - Problem: Uncle Bill is listed as MENTOR to the father. Uncle Bill is mentor/guardian to the SON, not the father. Uncle Bill and the father were cousins/contemporaries.

7. **Pronunciation: 7/20 false positives (35%)** [Pronunciation]
   - Remaining false positives: whippersnapper, thriftless, thickset, manliness, dum-dums, orderlies, mayn't.

8. **Structure: 2 sections for continuous short story** [Structure]
   - Same as all prior attempts.

9. **"Red Cross" extracted as character** [Completeness]
   - Organization, not a character (`supporting_2`, 4 mentions).

### LOW

10. **Father's alias "John Donaldson" overlaps with son's canonical name** — technically correct but creates confusion in display and profiling.

## Fix Priority

**Attempt 37 REGRESSED on profiles.** The target character preference signal at confidence 0.98 is too strong and overrides all contextual disambiguation signals. Both characters now get identical profiles because the signal always picks the "target" regardless of textual context.

**The fix made the disambiguator WORSE, not better.** Before the fix, the disambiguator at least occasionally assigned some passages correctly. Now it assigns ALL passages to both targets equally.

**Recommended fix for attempt 38:**
1. **CRITICAL #1: REVERT the target preference signal (Signal 0) from `name_disambiguator.py`** — This is the direct cause of the regression. Remove the 25 lines added in attempt 37. The existing signals (relationship markers, name-shape, temporal markers, chapter range) need to work without being overridden.
2. **Then investigate why the existing signals aren't disambiguating correctly.** The disambiguator has signals for relationship markers ("the father", "the boy"), temporal markers ("twenty years ago"), and chapter range. If these aren't working, the fix should improve THOSE signals rather than adding a new one that bypasses them.
3. **Do NOT add another new high-confidence signal.** The problem is that the existing disambiguation signals aren't firing, not that a new signal is needed.

**Alternative approach if revert+signal-fix doesn't work:** Instead of fixing the disambiguator, give the two characters distinguishable canonical names. If the son were "John Donaldson Jr." or "Young John Donaldson" and the father were "John Donaldson Sr.", the passage gatherer could match on distinct names. BUT this changes the identity graph output and may have side effects.

## Fix History

### Attempt 37 — Target character preference in passage disambiguation — REGRESSION
- **Issue targeted:** CRITICAL #1+#2 — Son's profile contaminated with father's story due to shared name
- **Changes made:**
  1. Added Signal 0 (target character preference, confidence 0.98) to `ContextDisambiguator.disambiguate()`
  2. When a candidate exactly matches `target_character_names[0]`, prefer it strongly
  3. Added `by_target_preference` stat tracking
- **Result:** REGRESSION — Both son and father now have IDENTICAL profiles (word-for-word duplication of the father's profile). The target preference signal overrides all contextual signals, so both characters get all passages. Profiles 6.5→5. Score: 7.15→6.90.
- **Files modified:**
  - `src/pipeline/character_profiling/name_disambiguator.py` (added 25 lines)

### Attempt 36 — Generational suffix handling in mention search — PARTIAL SUCCESS
- Father now in character list with 10 mentions ✓. Son's profile contaminated ✗. Johnny false split ✗.
- Score: 7.05→7.15

### Attempt 35 — Make ROLE_CONFLICT constraint HARD (strength 1.0) — PARTIAL SUCCESS
- Father/son no longer merged ✓. Father filtered by grounding gate ✗. Score: 6.80→7.05

### Attempt 34 — Adaptive promotion thresholds (length-scaled) — PARTIAL SUCCESS
- Uncle Bill restored ✓. Father/son merged ✗. Score: 6.65→6.80

### Previous attempts — see earlier evaluation states

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 37 | Profile passage disambiguation (target preference) | `name_disambiguator.py` | REGRESSION — identical profiles for son/father. Profiles 6.5→5. Score 7.15→6.90 |
| 36 | Grounding gate Sr./Jr. suffix | `mention_search.py`, `test_character_extraction_v2.py` | PARTIAL SUCCESS — father grounded ✓, profiles contaminated ✗. Score: 7.05→7.15 |
| 35 | ROLE_CONFLICT hard constraint | `identity_graph.py` | PARTIAL SUCCESS — no false merge ✓, father filtered ✗. Score: 6.80→7.05 |
| 34 | Adaptive promotion thresholds | `characters.py` | PARTIAL SUCCESS — Uncle Bill restored. Score: 6.65→6.80 |
| 33 | Possessive stripping + narrator detection | `supporting.py`, `narrator.py` | MIXED — possessive fixed, Uncle Bill demoted. Score: 6.65 |
| 32 | Alias cleanup (possessive + nicknames) | `evidence_collectors.py`, `main_cast.py` | NO EFFECT |
| 31 | Deterministic same-name constraint | `evidence_collectors.py` | SUCCESS — father/son split restored. Score: 6.78→7.33 |
| 30 | Pronunciation false positives | `character_proposer.py`, `foreign_proposer.py` | Pronunciation improved, character regression |
| 29 | Disambiguation labels post-processing | `characters.py` | SUCCESS — labels applied. Score: 7.13 |

**STUCK PATTERN ALERT:** `name_disambiguator.py` has now been modified in attempt 37 with NO improvement. The profiling pipeline's passage gathering remains the core blocker. The disambiguator has been modified 1 time. If the next attempt also modifies only `name_disambiguator.py` without success, escalate to passage_gatherer.py or consider changing the character canonical names upstream.

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.60 | — | Original baseline |
| 22 | 7.55 | +0.95 | Best score (all fixes active) |
| 23 | 6.30 | -0.30 | Clean baseline + Phase 2 pipeline |
| 31 | 7.33 | +0.73 | Deterministic same-name fix SUCCESS |
| 34 | 6.80 | +0.20 | Uncle Bill restored |
| 35 | 7.05 | +0.45 | HARD constraint works, father filtered |
| 36 | 7.15 | +0.55 | Father grounded ✓, profiles contaminated ✗ |
| 37 | 6.90 | +0.30 | REGRESSION — identical duplicate profiles |

## Next Action

Run PROMPT_fix.md to:
1. REVERT the target preference signal (Signal 0) from `name_disambiguator.py`
2. Investigate and fix why existing disambiguation signals (relationship markers, temporal markers) aren't correctly separating father vs son passages
3. The fix should make contextual signals STRONGER, not add a bypass signal
