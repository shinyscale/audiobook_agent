# Current Evaluation State

## Active Text
- **Name:** frankenstein
- **Attempt:** 2
- **Phase:** awaiting_fix
- **baseline_score:** 7.35

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 8/10 ✓
  - Completeness: 9/10
  - Identity Resolution: 7.5/10
  - Alias Grouping: 7.5/10
- Character Profiles: 6.5/10 ✗ (FAILING)
- Chapter Summaries: 7/10 ✗ (FAILING)
- Pronunciation Guide: 8/10 ✓
- HTML Presentation: 8/10 ✓
- **Overall: 7.75/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold)

## Progress Since Attempt 1 (Δ+0.40)

**Fixed in attempt 2:**
- Victor's own chapters (4, 8, 10, 21) no longer misattributed to "Robert Walton" ✓
- Victor→Safie "brother" removed ✓
- Safie→Victor "sister" removed ✓
- Safie→De Lacey "lover" removed ✓
- Clerval→Creature "friend" removed ✓
- Creature→Clerval "friend" → now correctly "victim" ✓
- Creature role changed from "supporting" to "antagonist" ✓

## Current Issues (Priority Order)

### CRITICAL

1. **Creature's chapters (11-16) misattributed to Victor Frankenstein** [Summaries]
   - Problem: All 6 chapters narrated by the Creature (indices 14-19) say "Victor Frankenstein" as the acting character instead of "the Creature" or "the narrator"
   - Evidence:
     - Ch 11 (index 14): "Victor Frankenstein, a newly conscious being, recounts his earliest sensory experiences" — this is THE CREATURE describing its awakening
     - Ch 12 (index 15): "Victor Frankenstein, living in a hovel near a cottage, spends the winter observing the cottagers" — this is THE CREATURE in the hovel
     - Ch 13 (index 16): "Victor Frankenstein's observations as a beautiful stranger named Safie arrives" — CREATURE watching Safie arrive
     - Ch 14 (index 17): "Victor Frankenstein recounts the tragic history of the De Lacey family" — CREATURE telling De Lacey's backstory
     - Ch 15 (index 18): "Victor Frankenstein, having discovered a leathern portmanteau containing Paradise Lost" — CREATURE discovering books
     - Ch 16 (index 19): "Victor Frankenstein, having been rejected by the De Lacey family, burning down their cottage... to confront his creator, Victor Frankenstein" — internally contradictory (the Creature goes to confront VICTOR, but summary names both as "Victor Frankenstein")
   - Root cause: Victor Frankenstein's name DOES appear in the Creature's chapters (the Creature refers to him as "my creator" and "Victor Frankenstein"). The fix to "use names only from the text" doesn't help because Victor is mentioned. The LLM then uses Victor's name as the narrator because his name is present.
   - Location: `src/pipeline/chapter_summary/summarizer.py` — all three prompts need stronger instruction distinguishing NARRATOR from MENTIONED characters
   - Fix approach: Add explicit instruction that the first-person "I" narrator is the acting subject. If "I" resolves to a character different from the frame narrator, use that character's name. The key distinguisher: Creature chapters describe "I" experiencing things no human could (awakening to new senses, living in the woods, observing humans from hiding). Adding a note like "The acting subject is who says 'I' in this text — not necessarily the character most often mentioned" may help. Alternatively, instruct the model: "If 'I' describes awakening, observing from hiding, or being rejected by humans, attribute to 'the narrator' (not Victor Frankenstein)."

2. **Letters 1-3 have wrong or dual attribution** [Summaries]
   - Problem: Letters 1-2 say "Victor Frankenstein, Robert Walton, writes/reflects" (dual comma attribution). Letter 3 says "Victor Frankenstein, writing from a ship" — wrong character entirely.
   - Evidence:
     - Letter 1 (index 0): "Victor Frankenstein, Robert Walton, writes to his sister Margaret from St. Petersburg" — Victor's name does not appear in Letter 1 (predates meeting him)
     - Letter 2 (index 1): "Victor Frankenstein, Robert Walton, reflects on his isolation" — same issue
     - Letter 3 (index 2): "Victor Frankenstein, writing from a ship advancing through high-latitude Arctic waters" — should be Robert Walton (Victor is not on the ship)
     - Letter 4 (index 3): "Captain Walton and his crew witness" ✓ correct
   - Root cause: The LLM is prepending "Victor Frankenstein" when uncertain about who the narrator is, possibly because "Victor Frankenstein" is the most prominent name in its training data for this text. For letters 1-2, the dual attribution suggests the model is providing both names as a hedge. For letter 3, the model confuses the unnamed narrator with Victor.
   - Location: Same as above — summarizer.py narrator attribution prompts
   - Fix approach: The prompt change needs stronger guidance for frame-narrator letters. These letters are signed "R.W." or "Robert Walton" and addressed to "Margaret Saville" — the summarizer should extract the author from the letter header/signature.

### HIGH

3. **Victor→Alphonse relationship direction wrong** [Profiles]
   - Problem: Victor→Alphonse: "brother" (WRONG — should be "father") and Alphonse→Victor: "brother" (WRONG — should be "son")
   - Evidence: Alphonse Frankenstein is Victor's father throughout the novel. This is even worse than attempt 1 (which had "father" reversed; now it says "brother")
   - Location: Profile generation hallucination or `reject_unfounded_familial_labels` over-rejection. The "brother" label may have been introduced because "father" was flagged as unverified (the word "father" appears near many different characters in the text)
   - Fix approach: Check if `reject_unfounded_familial_labels` is now rejecting the correct "father/son" labels for Alphonse/Victor. If so, the canonical-only anchoring may be too restrictive (Alphonse's canonical "Alphonse Frankenstein" may not appear near "father" in text, even though their relationship is clearly father-son)

4. **Victor→Margaret: "brother" fabricated** [Profiles]
   - Problem: Victor→Margaret: "brother" and Margaret→Victor: "brother" — Victor has no familial relationship with Margaret Saville (she is Walton's sister, not Victor's)
   - Evidence: Victor meets Walton; Walton's sister is Margaret. Victor and Margaret never interact directly in the novel
   - Location: Profile generation hallucination. Victor's profile likely included "Margaret" in context because Walton mentions her in his letters to Victor
   - Fix approach: `reject_unfounded_familial_labels` should catch this — but may need to check if it's running for Margaret

5. **De Lacey family relationship errors** [Profiles]
   - Problem: Multiple wrong labels within the De Lacey family:
     - Felix→Agatha: "son" — WRONG (they are siblings; should be "sister" or "sibling")
     - Agatha→De Lacey: "mother" — WRONG (De Lacey is Agatha's father, not mother)
   - Evidence: De Lacey is the blind old man; Felix and Agatha are his son and daughter respectively
   - Location: Profile generation hallucination; the "son" and "mother" labels may be directional confusion in the profiler

6. **Caroline Beaufort self-referential relationship** [Profiles]
   - Problem: Caroline Beaufort→Caroline Beaufort: "daughter" — self-referential entry
   - Evidence: A character cannot have a relationship with herself
   - Location: Profile generation or `_propagate_missing_reverses` logic; may be creating a reverse entry that points back to itself

7. **Creature→Felix: "beloved" persists** [Profiles]
   - Problem: The creature labels Felix as "beloved" — misleading/wrong relationship
   - Evidence: The creature observes Felix from hiding and develops admiration, but there is no romantic or beloved relationship. "Beloved" implies romantic attachment.
   - Location: Profile generation; `reject_unfounded_romantic_labels` should catch this but "beloved" may not be in the romantic_labels set
   - Fix approach: Add "beloved" to the `romantic_labels` set in `reject_unfounded_romantic_labels`

### MEDIUM

8. **Victor→M. Waldman: "protégé" direction reversal** [Profiles]
   - Problem: Victor→Waldman: "protégé" — if A→B: label means "B is A's [label]", then this reads "Waldman is Victor's protégé" which is WRONG. Victor is Waldman's protégé.
   - Evidence: Waldman→Victor: "mentor" (correct), but the reverse is wrong
   - Fix approach: `enforce_inverse_consistency` should map mentor↔student; protégé is not in the inverse map

9. **Alphonse→Kirwin: "rival" hallucination** [Profiles]
   - Problem: Alphonse→Kirwin: "rival" and Kirwin→Alphonse: "rival" — wrong. Kirwin is the magistrate who eventually helps Alphonse and Victor
   - Evidence: Kirwin is sympathetic to Victor; no rivalry exists with Alphonse

10. **"De Lacey" alias shared by both Felix and the old man** [Alias Grouping]
    - Problem: Felix has alias "De Lacey" AND the old man has alias "De Lacey" — both share the same alias
    - Evidence: Felix's full name is Felix De Lacey, but when "De Lacey" is used alone in the text it almost always refers to the blind father, not Felix. Having both claim this alias is confusing.
    - Fix approach: The old man's canonical should be "De Lacey" with "the old man" as alias. Felix's canonical should remain "Felix" or "Felix De Lacey" without "De Lacey" as a standalone alias.

11. **"Captain Walton" and "R.W." are F6 duplicates of Robert Walton** [Identity Resolution]
    - Problem: Two 1-mention entries from F6 reconciliation duplicate Robert Walton: "Captain Walton" (hash id b2158f484fa9) and "R.W." (hash id f1b39c083608)
    - Fix approach: `_is_likely_alias_of_existing` in analyzer.py should match:
      - "Captain Walton" → last name "Walton" matches Robert Walton
      - "R.W." → initials match Robert Walton

### LOW

12. **Letter 1 has null title** [Structure]
    - First structural element (index 0) has `title: null` — should be "Letter 1"
    - This was a pre-existing issue from attempt 1

13. **"his father" as alias for Alphonse** [Alias Grouping]
    - Relational descriptor is listed as a name alias

14. **3 pronunciations missing IPA** [Pronunciation]
    - Roncesvalles, resume, alternate — no IPA provided (pre-existing issue from attempt 1)

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 7.35 | - | Baseline. Profiles (5/10) and Summaries (6/10) failing |
| 2 | 7.75 | +0.40 | Profiles improved (5→6.5): fabrications fixed. Summaries improved (6→7): Victor chapters correct, Creature chapters still wrong |

## Fix History
- Attempt 1:
  - **Summarizer narrator attribution**: Changed narrator instruction in all 3 summarizer prompts (CHUNK_SUMMARY_PROMPT, CONSOLIDATE_PROMPT, SINGLE_CHAPTER_PROMPT). New instruction: "Use a character's name ONLY if that name appears explicitly in the provided text. If the 'I' narrator is unnamed in this section, refer to them as 'the narrator.'"
    - Result: PARTIAL. Fixed Victor's own chapters (no longer says Robert Walton). But Creature's chapters now say "Victor Frankenstein" (his name appears as creator reference). Letters 1-2 now show dual attribution.
  - **Fabricated relationships (canonical-only anchoring)**: Changed `reject_unfounded_familial_labels`, `reject_unfounded_romantic_labels`, and `reject_unfounded_friend_labels` to use canonical-name-only regex patterns.
    - Result: SUCCESS. Victor→Safie "brother", Safie→Victor "sister", Clerval→Creature "friend", creature→Clerval "friend", Safie→De Lacey "lover" all removed.
  - Modified: `src/pipeline/chapter_summary/summarizer.py`, `src/pipeline/character_profiling/post_corrections.py`

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | Summary narrator misattribution | summarizer.py | Partial — Victor chapters fixed, Creature chapters still wrong attribution |
| 1 | Fabricated relationships | post_corrections.py | Success — 5 fabrications removed |

## Next Action
Fix: (1) Narrator attribution for nested narration — Creature chapters still wrong. Need to distinguish first-person narrator from mentioned characters. (2) Fix remaining relationship errors in profiles. Phase: awaiting_fix.
