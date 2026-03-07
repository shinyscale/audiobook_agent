# Current Evaluation State

## Active Text
- **Name:** i_have_no_mouth
- **Attempt:** 18
- **Phase:** awaiting_analysis
- **baseline_score:** 6.35
- **Competitive Mode:** none

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 8.5/10 ✓
  - Completeness: 9/10
  - Identity Resolution: 9/10
  - Alias Grouping: 8/10
- Character Profiles: 6/10 ✗ (FAILING)
- Chapter Summaries: 5/10 ✗ (FAILING)
- Pronunciation Guide: 9/10 ✓
- HTML Presentation: 8/10 ✓
- **Overall: 7.53/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold)

## What Improved (Attempt 16 → 17)
- **FIXED: "the ice caverns" removed** — no longer in character list (6 chars, clean)
- **FIXED: AM alias** — "Allied Mastercomputer" now present (Rule 0.5 acronym exemption worked)
- **FIXED: Ted is_narrator=True** — narrator badge shows correctly in HTML
- Character Extraction jumped from ~4.5 to 8.5 — major improvement

## Current Issues (Priority Order)

### CRITICAL
1. **Summary attributes Ted's entire role to Ellen** [Summaries]
   - Problem: The summary never mentions Ted by name. It says "Ellen, Ellen, Nimdok, Gorrister, and Benny" (Ellen duplicated, Ted missing). The entire first-person narrative is attributed to Ellen as POV character.
   - Evidence: Ted narrates the entire story in first person. The text's final line "I have no mouth. And I must scream" is Ted's. The summary says "AM keeps Ellen alive in a mutilated, mouthless body" — this is WRONG. AM keeps TED alive as the mouthless blob.
   - Root cause: `narrator_character_id=None` at top level. The summary agent doesn't know Ted is the narrator, so it picks Ellen (highest-mention non-AM character) as POV. The summary was generated BEFORE narrator detection completed.
   - Location: The cascade is: (1) `narrator_character_id=None` means narrator name substitution doesn't fire, (2) summary prompt doesn't know to use "Ted" as POV
   - Fix: The root cause is `narrator_character_id=None`. Ted has `is_narrator=True` but the top-level field isn't set. STEP 5.9.6 should set `narrator_character_id` when it finds a character with `is_narrator=True`. Check why it doesn't fire — likely because Ted's `role=main` not `protagonist`, or because the step checks conditions that aren't met.

2. **Ted role=main instead of protagonist** [Profiles + Summaries]
   - Problem: Ted has `id=supporting_0, role=main, mentions=5`. As the first-person narrator of the entire story, Ted should be `role=protagonist`.
   - Evidence: Every sentence is Ted's narration. 5 explicit name mentions is correct (first-person narrators rarely say their own name), but role should reflect narrative importance.
   - Root cause: STEP 5.9.6 narrator role invariant should elevate Ted to protagonist AND set `narrator_character_id`. Either it doesn't fire or its conditions are too strict.
   - Location: `src/agents/characters.py` — STEP 5.9.6
   - Fix: Debug STEP 5.9.6 — check if it requires `narrator_character_id` to already be set (circular dependency) or if it checks for role already being protagonist. The step should: (1) find any character with `is_narrator=True`, (2) set their role to `protagonist`, (3) set `narrator_character_id` to their ID.

### HIGH
3. **Ted has no physical_description or personality_traits** [Profiles]
   - Problem: Ted's profile has `physical_description=null, personality=null`. Only has voice_guidance (tone: flat, verbal tics, quotes) and relationships.
   - Evidence: The text describes Ted as handsome, "the unaltered one" — he's the only one AM didn't physically transform. This is narratively significant.
   - Root cause: With `role=main` and only 5 mentions, the profiler likely gives Ted minimal treatment. If Ted were `protagonist`, he'd get full profiling. Also, since the summary doesn't mention Ted by name, the profiler has no text evidence to work with.
   - Fix: Will largely auto-resolve when Ted is promoted to protagonist and narrator_character_id is set. The profiler gives deeper treatment to protagonists and narrators.

4. **Gorrister role=antagonist** [Profiles]
   - Problem: Gorrister is a fellow victim of AM, not an antagonist. He's described as having "a weary stoicism" — a sufferer, not an aggressor.
   - Evidence: All five humans are victims of AM. Gorrister never acts as an antagonist.
   - Root cause: Role assignment logic may be confused by Gorrister recounting AM's backstory or by the "abuser" relationship label from Ellen's profile.
   - Location: `src/analyzer.py` — role assignment logic
   - Fix: This is a recurring issue (seen in multiple attempts). The role assignment should recognize that characters labeled as "victim" by the primary antagonist (AM) should not themselves be "antagonist". Check if there's a rule that prevents AM's victims from being labeled antagonist.

5. **Summary ending factually wrong** [Summaries]
   - Problem: "Ellen kills all four companions with ice spears" and "AM keeps Ellen alive" — in the text, TED is the one who kills the others and is kept alive as the mouthless blob. Ellen is one of the victims Ted kills.
   - Evidence: The story's climax: Ted realizes killing the others would free them from AM. He and Ellen kill the other three, then Ted kills Ellen. AM transforms Ted into a slug-like creature without a mouth.
   - Root cause: Same as CRITICAL #1 — the summary treats Ellen as POV character instead of Ted.
   - Fix: Resolves with CRITICAL #1 — once narrator_character_id is set and summary uses Ted as POV.

### MEDIUM
6. **"Ellen, Ellen" duplication in summary** [Summaries]
   - Problem: Summary begins "The chapter follows Ellen, Ellen, Nimdok, Gorrister, and Benny" — Ellen appears twice.
   - Root cause: Likely a character list deduplication issue in the summary prompt, or the LLM echoed a malformed character list.
   - Location: Summary generation in `src/agents/summary_agent.py` or `src/pipeline/summarizer/`

7. **Gorrister described as "reluctant narrator"** [Profiles]
   - Problem: Gorrister's personality says he's "a reluctant narrator who repeatedly recounts AM's origin." He's not a narrator — he's a character who tells backstory. This phrasing would confuse an audiobook narrator about who the actual narrator is.
   - Fix: Minor — would improve with correct narrator attribution.

### LOW
8. **Chapter title is null** [Structure]
   - Single section with `title: null`. Minor for a short story with no heading.

## Fix Priority

**The cascade:** Everything flows from `narrator_character_id=None` and `Ted.role=main`:

1. Fix STEP 5.9.6 to: find character with `is_narrator=True` → set role to `protagonist` → set `narrator_character_id` to their ID
2. This enables: narrator name substitution in summaries (Ted replaces "the narrator")
3. This enables: full profiling for Ted as protagonist
4. This enables: correct summary POV (Ted, not Ellen)
5. Fix Gorrister role=antagonist (separate issue)

**Note:** The summary was already generated with Ellen as POV. Even if narrator_character_id is fixed, the existing summary text won't change unless the summary is regenerated OR there's a post-hoc narrator name substitution step. Check if the pipeline has a step that replaces "the narrator" → actual narrator name in existing summaries.

**Expected score improvements if fixed:**
- Summaries: 5 → 8+ (Ted as POV, correct ending)
- Profiles: 6 → 8+ (Ted gets full profile, Gorrister role fixed)
- Overall: 7.53 → ~8.5

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
| 17 | 7.53 | +1.18 | Ice caverns gone, AM aliases fixed, Ted=narrator but role/summary wrong |

## Fix History (Attempt 17)
- **Ted narrator fix (CRITICAL):**
  - Root cause: LLM returns narrator_name="the narrator" (generic) not "Ted"; STEP 4.5b only fires when narrator_name is None, missing generic placeholders; STEP 5.8.5 then re-runs LLM with wrong main_cast
  - Fix A: Extended STEP 4.5b condition to also fire when narrator_name is a generic placeholder ("the narrator", "narrator", "protagonist", etc.) — vocative search then returns "Ted"
  - Fix B: Extended STEP 5.8.4b to search supporting_cast for narrator_name (after self-id scan) — finds Ted in supporting_0, promotes to main_cast, sets narrator_character_id before STEP 5.8.5 can run
  - Fix C: Added STEP 4.24 else branch update — saves self-id name (belt-and-suspenders)
  - Smoke test: `_find_narrator_name_from_vocative` confirmed returns "Ted" (vocative=3, total=5) from actual text
- **AM aliases fix (HIGH):**
  - Root cause: Rule 0.5 in verify_aliases blocks "Allied Mastercomputer" because core noun "mastercomputer" != "am"
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
- Attempt 16: STEP 5.8.4 narrator name resolver, STEP 1.2 standalone char removal (neither worked — name was generic, Rule 0.5 blocked first)

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
| 17 | Generic narrator name | characters.py (STEP 4.5b) | **Fixed** (Ted found via vocative) |
| 17 | Supporting→main narrator | characters.py (STEP 5.8.4b) | **Partial** (is_narrator=True but narrator_character_id=None) |
| 17 | Rule 0.5 acronym | main_cast.py (Rule 0.5) | **Fixed** (AM aliases work) |

## Fix History (Attempt 18)
- **Ted role=protagonist fix:**
  - Root cause A: `narrator.py:update_characters_with_narrator` only elevated role from ("minor","supporting",None) — not from "main". Added "main" to the condition.
  - Root cause B: `characters.py:STEP 5.9.6` same condition. Changed to `!= "protagonist"` to catch all non-protagonist roles.
  - Modified: `src/pipeline/character_extraction_v2/narrator.py` (line 329), `src/agents/characters.py` (STEP 5.9.6)
- **Gorrister role=antagonist fix:**
  - Root cause: `analyzer.py` protagonist→antagonist check used `_ADVERSARIAL_LABELS` which includes victim-of-others labels ("tormentor", "captor"). Gorrister's outgoing "AM: tormentor" (AM torments Gorrister = Gorrister is VICTIM) was counted as adversarial. Fix: use only outgoing-aggressor labels (labels where the TARGET is the victim: "victim", "prisoner", "captive", etc.).
  - Smoke test: Gorrister adversarial_count=1/4 → stays protagonist ✓; AM 4/4 → stays antagonist ✓
  - Modified: `src/analyzer.py` (lines ~2153-2170)
- **narrator_detected preservation:**
  - Root cause: "early narrator detection" step in analyzer.py (line ~1865) overwrote `narrator_detected="Ted"` (set by V2 pipeline) with LLM re-detection result "Ellen" (from summaries generated without narrator info). Fixed: only overwrite narrator_detected if V2 didn't already find one.
  - Modified: `src/analyzer.py` (line ~1865)
- **Pipeline crash fix (attempt 18b):**
  - Root cause: `_ADVERSARIAL_LABELS` was referenced at analyzer.py:2198 but the Gorrister fix renamed it. The incoming-adversarial check for the protagonist→antagonist loop referenced the old name.
  - Fix: Defined `_INCOMING_AGGRESSOR_LABELS_EARLY` before the first loop and replaced the undefined `_ADVERSARIAL_LABELS` reference with it.
  - Modified: `src/analyzer.py` (lines ~2165-2202)
- Smoke test: 332 tests passed

## Next Action
Re-run analysis to verify fixes (Ted protagonist, Gorrister not antagonist, narrator_detected preserved).
