# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 35
- **Phase:** awaiting_fix
- **baseline_score:** 6.60
- **Competitive Mode:** single (all stages: characters, structure, summaries)

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Pipeline Notes
- Analysis completed in 38m 36s
- 55 LLM calls, 93,344 tokens
- Found 5 characters, 2 chapters, 20 pronunciation flags
- F6 filter rejected "John Donaldson Sr. (the father)" as having 0 text mentions
- Warnings: 3 characters have potentially ungrounded evidence quotes (John Donaldson: 2, Uncle Bill: 3, Ted Frith: 2)
- 1 JSON parse failure (Pronunciation Guide batch enrichment)
- Uncle Bill correctly identified as protagonist with is_narrator: true
- "John Donaldson" is now ONLY the son (aliases: John, the boy, Johnny)
- Father is MISSING entirely from character list (filtered by F6 as hallucination)

## Latest Scores
- Structure Detection: 7/10 ✗
- Character Extraction: 6/10 ✗
  - Completeness: 6/10
  - Identity Resolution: 7/10
  - Alias Grouping: 8/10
- Character Profiles: 7.5/10 ✗
- Chapter Summaries: 7.5/10 ✗
- Pronunciation Guide: 7/10 ✗
- HTML Presentation: 8/10 ✓
- **Overall: 7.05/10** (reference only)

## Overall Score Calculation

```
Overall = (7 × 0.20) + (6 × 0.25) + (7.5 × 0.15) + (7.5 × 0.20) + (7 × 0.10) + (8 × 0.10)
        = 1.40 + 1.50 + 1.125 + 1.50 + 0.70 + 0.80
        = 7.025
```

**Overall: 7.05/10** (UP from 6.80 in attempt 34)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (5 categories below threshold)

## Detailed Evaluation

### 2.1 Structure Detection: 7/10 ✗

Unchanged from previous attempts. "American, Sir" is a continuous short story with no chapter markers. The tool produces 2 sections, both with null titles. Per the rubric, a continuous text should be identified as a single section (9-10); splitting into 2 sections is a structural error (6-7). Score 7 because the summaries for each section are coherent and usable despite the artificial split.

### 2.2 Character Extraction: 6/10 ✗

**The HARD constraint WORKED — no false merge this time!** The father and son were kept separate by the identity graph. However, the father was then rejected by the grounding gate (F6/F2b) because it searched for "John Donaldson Sr." in the text and found 0 exact matches. The text never literally uses "Sr." — it refers to the father as "John Donaldson", "his father", "the father", etc.

**Character list (5 total, 1 main_cast + 4 supporting):**
- `main_cast_1`: **John Donaldson** — 44 mentions, role: `supporting` — this is the SON only
  - Aliases: ["John", "the boy", "Johnny"] ✓✓ (Johnny now correctly an alias, not separate)
  - Relationships: Uncle Bill (mentor), John Donaldson Sr. (parent), American Red Cross (ally) ✓
- `supporting_0`: **Uncle Bill** — 18 mentions, role: `protagonist`, `is_narrator: true` ✓✓✓
  - Aliases: ["Bill"] ✓
  - Note: ID is `supporting_0` but role is protagonist — likely a pipeline inconsistency
- `supporting_2`: **Joe Barron** — 3 mentions ✓
- `supporting_3`: **Red Cross** — 4 mentions — organization, not character ✗
- `supporting_4`: **Ted Frith** — 5 mentions, alias: "Ted" ✓

**Sub-Dimension A: Completeness: 6/10** (DOWN from 7)
- Uncle Bill present and correctly identified as protagonist ✓✓
- Son (John Donaldson) correctly identified with proper aliases ✓
- Father (John Donaldson Sr.) MISSING entirely from final output ✗✗ — critical missing character
- "Red Cross" is an organization, not a character ✗
- Margaret Donaldson still missing (minor — only ~2 mentions)
- Johnny correctly folded into John Donaldson as alias ✓ (improvement)

**Sub-Dimension B: Identity Resolution: 7/10** (UP from 4!)
- Father/son NO LONGER falsely merged! ✓✓✓ The HARD constraint worked.
- BUT the father was then filtered out by grounding gate — effectively a "false deletion" ✗
- Uncle Bill correctly resolved ✓
- Johnny correctly an alias, not separate ✓ (improvement)
- The identity resolution itself is correct — the problem is downstream filtering

**Sub-Dimension C: Alias Grouping: 8/10** (UP from 7) ✓
- Uncle Bill has alias "Bill" ✓
- John Donaldson has aliases "John", "the boy", "Johnny" ✓✓ — all correct for the son
- Ted Frith has alias "Ted" ✓
- No self-aliases, no possessive forms ✓

### 2.3 Character Profiles: 7.5/10 ✗ (UP from 6)

**Major improvement: Uncle Bill now has a full profile!**

- **Uncle Bill**: Excellent profile — personality captures "reluctantly compassionate", "emotionally restrained but deeply loyal". Evidence quotes are accurate and well-chosen. Voice guidance with "calm, weathered, low-volume voice" is useful. "Selfless in sacrifice" trait is appropriate. ✓✓
- **John Donaldson (son only)**: Good profile — describes heroism and self-sacrifice. Evidence includes father's iconic "American, sir" line which is WRONG (that's the father's line, not the son's). The rest of the profile is about the son's wartime service which is accurate. Relationships correctly identify Uncle Bill as mentor and John Donaldson Sr. as parent. ✗ for contamination
- **Ted Frith**: Has profile with personality and voice guidance. Evidence STILL contaminated: "'But if I'm helping, it's the game to keep whole. You see, sir, this is my good day. I'm American to-day, sir!'" — this is the FATHER's line, not Ted's. The "'Ah, but you are--my superior officer'" quote also belongs to the father. Both quotes attributed to Ted are actually the father speaking. ✗✗
- **Joe Barron, Red Cross**: Null profiles — expected for minor/invalid entries

**Why 7.5/10:** Uncle Bill's profile going from empty to excellent is a major improvement (+1.5). John Donaldson's profile is mostly good but has the "American, sir" contamination. Ted Frith's profile is entirely built from the father's quotes — without the father as a separate character, his dialogue gets misattributed.

### 2.4 Chapter Summaries: 7.5/10 ✗ (stable)

**Section 1:** Excellent. Correctly describes the cousin relationship, the narrator's background, Margaret Donaldson, the scandal and faked death. Comprehensive and well-written.

**Section 2:** Good quality but the recurring hallucination persists:
- "his deceased sister's son" — WRONG. Uncle Bill is the father's COUSIN, not sibling. Section 1 correctly says "cousin."
- Otherwise excellent: covers Yale, fishing trip, WWI, Caporetto, reunion, deathbed revelation.

**Why 7.5/10:** The "sister" factual error in section 2 prevents a higher score. Otherwise both summaries are comprehensive, well-written, and useful for narrators.

### 2.5 Pronunciation Guide: 7/10 ✗ (stable)

20 entries, 15 with IPA.

**Genuinely useful foreign terms (8):** Caporetto, Piave, Solferino, Guerre, Venetia, Tagliamento, Bersagliari, Bordeaux — excellent ✓

**Acceptable homographs (5):** live, minute, read, close, moderate — context-dependent, genuinely useful ✓

**False positives (7):**
- Common English words: whippersnapper, thriftless, thickset, manliness — uncommon but not pronunciation challenges ✗
- Military/medical terms: dum-dums, orderlies — standard pronunciation ✗
- Archaic contraction: mayn't — borderline ✗

**Why 7/10:** 7/20 entries (35%) are false positives. The core foreign terms and homographs are excellent, but the false positives drag the score down.

### 2.6 HTML Presentation: 8/10 ✓

Navigation works, character profiles render well. Uncle Bill correctly displayed as protagonist and narrator with full profile and voice guidance. Minor: "Red Cross" in Supporting Characters. Father's absence from the character list reflects the upstream extraction issue.

## Configuration Audit
- Model: qwen3-next:80b-a3b-instruct-q8_0 (user-configured, appropriate)
- Pipeline: V2 with Phase 2 graph-based identity resolution
- 0 LLM retries — good
- 1 JSON parse failure (Pronunciation Guide batch enrichment)
- Character Profiles: 8 LLM calls, 39,732 tokens, 762s — Uncle Bill profile now working ✓
- Identity graph HARD constraint prevented father/son merge ✓
- But grounding gate then rejected the father for 0 text mentions of "John Donaldson Sr." ✗

## Current Issues (Priority Order)

### CRITICAL

1. **Father (John Donaldson Sr.) rejected by grounding gate — 0 text mentions** [Completeness]
   - Problem: The identity graph correctly kept father and son separate (HARD constraint working!), but the grounding gate then searched for "John Donaldson Sr." in the text and found 0 exact matches. The text never literally says "John Donaldson Sr." — it refers to the father as "John Donaldson", "his father", "the father", etc. The grounding gate treated this as a hallucination and filtered the character out.
   - Evidence: Pipeline note: "F6 filter rejected 'John Donaldson Sr. (the father)' as having 0 text mentions". The character was in the identity graph as a separate node but eliminated downstream.
   - Root cause: The grounding gate does exact-match search for the canonical name. When the canonical name includes disambiguation labels like "Sr." that don't appear literally in the text, the search fails. The grounding gate needs to also search for the character's aliases (e.g., "his father", "the father") or the base name without the label.
   - Location: `src/pipeline/character_extraction_v2/grounding.py` — `GroundingGate.apply()` — likely searches only for `canonical_name`, not aliases.
   - Fix approach: When computing mention counts for the grounding gate, search for ALL of a character's names — canonical name, base name (without Sr./Jr./labels), and aliases. If ANY name variant has mentions above the threshold, the character should be grounded. The father should match on "John Donaldson" (his base name) and/or "his father"/"the father" aliases.
   - **IMPORTANT:** This is the inverse of the previous problem. Before, father and son were falsely merged (Identity Resolution issue). Now they're correctly separated but the father gets filtered out (Completeness issue). The fix must be in the grounding gate, NOT in the identity graph.

### HIGH

2. **Ted Frith profile entirely contaminated with father's dialogue** [Profiles]
   - Problem: Both evidence quotes for Ted are actually the father's lines: "'Ah, but you are--my superior officer'" and "'This is my good day. I'm American to-day, sir!'" Both are spoken by John Donaldson (the father), not Ted Frith.
   - Evidence: The "American, sir" verbal tic and the "superior officer" exchange belong exclusively to the father in the text.
   - Location: `src/pipeline/character_profiling/` — passage gathering assigns nearby dialogue to wrong character
   - Impact: With the father missing from the character list, his dialogue gets attributed to nearby characters. Fixing CRITICAL #1 (restoring the father) should largely fix this — the profiler would have the correct speaker available.

3. **John Donaldson (son) profile contaminated with father's quote** [Profiles]
   - Problem: "'American, sir,' he said proudly. ... 'This is my good day. I'm American to-day, sir!'" appears in the son's evidence, but this is spoken by the father on his deathbed.
   - Root cause: Same as #2 — with only one "John Donaldson" in the character list, both father and son's dialogue gets attributed to the same entity.
   - Impact: Will likely resolve when father is restored as separate character.

4. **Summary "sister" hallucination persists** [Summaries]
   - Problem: Section 2 says "his deceased sister's son" — Uncle Bill is the father's COUSIN, not sibling.
   - Evidence: Section 1 correctly says "cousin" but Section 2 hallucinates "sister."
   - Location: LLM generation in summary pipeline. Non-deterministic.

### MEDIUM

5. **Pronunciation: 7/20 false positives (35%)** [Pronunciation]
   - Remaining false positives: whippersnapper, thriftless, thickset, manliness, dum-dums, orderlies, mayn't.

6. **Structure: 2 sections for continuous short story** [Structure]
   - Same as all prior attempts. Not worth a targeted fix for this text alone.

7. **"Red Cross" extracted as character** [Completeness]
   - Organization, not a character (supporting_3, 4 mentions).

### LOW

8. **Uncle Bill ID is `supporting_0` despite role=protagonist** — cosmetic inconsistency in ID naming

## Fix Priority

**Attempt 35 was a PARTIAL SUCCESS.** The HARD constraint worked perfectly — father and son are no longer falsely merged (Identity Resolution 4→7!). Uncle Bill profile is now populated (Profiles 6→7.5!). Johnny is now correctly an alias (Alias Grouping 7→8!). But the father character was filtered out by the grounding gate because it searched for "John Donaldson Sr." literally and found 0 matches.

**This is a classic "fix one thing, expose another" pattern.** The identity graph correctly separates father/son, but then gives the father a canonical name with "Sr." that doesn't appear in the text, causing the grounding gate to reject him.

**Recommended fix for attempt 36:**
1. **CRITICAL #1: Grounding gate alias search** — When the grounding gate checks whether a character is grounded in the text, it should search for ALL name variants (canonical name, base name without labels, aliases), not just the canonical name. If any variant has mentions >= threshold, the character is grounded. This would find "John Donaldson" (base name) or "the father" (alias) in the text and keep the father character.

**Do NOT touch the identity graph or constraint logic — it's working correctly now.**

## Fix History

### Attempt 35 — Make ROLE_CONFLICT constraint HARD (strength 1.0) — PARTIAL SUCCESS
- **Issue targeted:** CRITICAL #1 — Father/son false merge (regression from attempt 31)
- **Root cause:** `ROLE_CONFLICT` constraint strength was 0.9, allowing merge evidence weight > 0.9 to override it
- **Changes made:**
  1. Changed `ROLE_CONFLICT` constraint strength from 0.9 to 1.0 in `identity_graph.py` line 83
  2. This makes it a HARD constraint that cannot be overridden by merge evidence
  3. The deterministic same-name check in `evidence_collectors.py` (lines 1033-1040) already creates this constraint
- **Result:** PARTIAL SUCCESS — Father/son no longer merged ✓. BUT father filtered out by grounding gate ✗. Uncle Bill profile now working ✓. Johnny now alias ✓. Identity Resolution 4→7, Alias Grouping 7→8, Profiles 6→7.5.
- **Files modified:**
  - `src/pipeline/character_extraction_v2/identity_graph.py` (line 83)
- **Test results:** All 38 identity graph unit tests pass

### Attempt 34 — Adaptive promotion thresholds (length-scaled) — PARTIAL SUCCESS
- **Issues targeted:**
  1. CRITICAL #1 — Uncle Bill demoted from main_cast to supporting
  2. CRITICAL #2 — Profile data loss (FALSE ALARM in attempt 33 — data existed at `personality.summary` not `personality_summary`)
- **Changes made:**
  1. Added `adaptive_promotion_thresholds(word_count)` function to `src/agents/characters.py`
  2. Updated Step 5.8 promotion logic to use adaptive thresholds instead of hardcoded values
  3. Thresholds scale with text length: ≤10K → 15/10/8; 10K-50K → 50/30/20; >50K → 200/100/50
- **Result:** PARTIAL SUCCESS — Uncle Bill restored to main_cast as protagonist/narrator ✓. BUT father/son falsely merged ✗. Uncle Bill profile still empty ✗. Score: 6.65 → 6.80 (+0.15)
- **Files modified:**
  - `src/agents/characters.py` (lines 47-75, 457-479)

### Attempt 33 — Possessive stripping in supporting cast + deterministic narrator detection
- **Result:** MIXED — Score: 6.65 (-0.63)

### Attempt 32 — Alias cleanup (possessive + nicknames) — DID NOT WORK
- **Score impact:** 7.33 → 7.28 (-0.05)

### Attempt 31 — Deterministic same-name constraint (SUCCESS!)
- **Score impact:** 6.78 → 7.33 (+0.55)

### Attempt 30 — Pronunciation false positive reduction (PARTIAL SUCCESS + REGRESSION)
- Score: 6.78

### Attempt 29 — Disambiguation labels via post-processing (SUCCESS!)
- Score: 7.13

### Previous attempts — see earlier evaluation states

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 35 | ROLE_CONFLICT hard constraint | `identity_graph.py` | PARTIAL SUCCESS — no false merge ✓, father filtered by grounding ✗. IR 4→7, AG 7→8, Profiles 6→7.5. Score: 6.80→7.05 |
| 34 | Adaptive promotion thresholds | `characters.py` | PARTIAL SUCCESS — Uncle Bill restored to main_cast, but father/son merged. Score: 6.65→6.80 |
| 33 | Possessive stripping + narrator detection | `supporting.py`, `narrator.py` | MIXED — possessive fixed, Uncle Bill demoted to supporting, profiles empty. Score: 6.65 (-0.63) |
| 32 | Alias cleanup (possessive + nicknames) | `evidence_collectors.py`, `main_cast.py` | NO EFFECT — aliases unchanged, narrator regression |
| 31 | Deterministic same-name constraint | `evidence_collectors.py` | SUCCESS — father/son split restored, score 6.78→7.33 |
| 30 | Pronunciation false positives | `character_proposer.py`, `foreign_proposer.py` | Pronunciation improved (5→7), BUT character regression |
| 29 | Disambiguation labels post-processing | `characters.py` | SUCCESS — labels applied, score 7.13 |
| 28 | Revert to attempt 25 (undo regression) | `characters.py` | SUCCESS — main_cast restored |
| 27 | Revert + re-implement disambiguation labels | `characters.py` | WORSE REGRESSION — main_cast_count: 0 |
| 26 | Disambiguation labels for same-name characters | `characters.py` | REGRESSION — main_cast_2 dropped |
| 25 | Father/son disambiguation (data flow fix) | `characters.py` | SUCCESS — split works but identical names |
| 24 | Father/son disambiguation | `evidence_collectors.py`, `characters.py` | NO EFFECT |
| 23 (baseline) | Clean baseline + Phase 2 pipeline | N/A | Score: 6.30 |

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.60 | — | Original baseline |
| 22 | 7.55 | +0.95 | Best score (all fixes active) |
| 23 | 6.30 | -0.30 | Clean baseline + Phase 2 pipeline |
| 24 | 6.15 | -0.45 | Fix had no effect; profiles worse |
| 25 | 6.50 | -0.10 | Father/son split working but needs labels |
| 26 | 6.40 | -0.20 | REGRESSION — labels dropped main_cast_2 |
| 27 | 5.75 | -0.85 | WORSE REGRESSION — main_cast pipeline broken |
| 28 | 6.65 | +0.05 | Revert successful — main_cast restored |
| 29 | 7.13 | +0.53 | Disambiguation labels SUCCESS |
| 30 | 6.78 | +0.18 | Pronunciation improved but father/son merge regression |
| 31 | 7.33 | +0.73 | Deterministic same-name fix SUCCESS — highest since attempt 22 |
| 32 | 7.28 | +0.68 | Alias fix NO EFFECT, Uncle Bill narrator regression, profiles improved |
| 33 | 6.65 | +0.05 | Possessive fix worked, BUT Uncle Bill demoted, profiles empty |
| 34 | 6.80 | +0.20 | Uncle Bill restored ✓, father/son merged ✗, profile still empty |
| 35 | 7.05 | +0.45 | HARD constraint works ✓, father filtered by grounding ✗, profiles improved ✓ |

## Next Action

**Phase:** awaiting_fix

Run PROMPT_fix.md to fix CRITICAL #1: Grounding gate needs to search for ALL name variants (canonical name, base name without labels, aliases) when determining if a character is grounded in the text. Currently it only searches for the exact canonical name "John Donaldson Sr." which never appears literally in the text.

**Expected outcome after fix:**
- Father should be grounded via "John Donaldson" (base name without "Sr.") or aliases like "his father", "the father"
- Father should appear in final character list as a separate character from the son
- Ted Frith and John Donaldson (son) profile contamination should decrease once father is a separate character with his own dialogue attributed correctly
