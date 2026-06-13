# Output Quality Audit — 2026-06-10

Audited against the June 2 run of *See the Light, Kiss the Ground*
(`output/run_20260602_post_tweaks_v2/`), with confirmed ground-truthing against the
source PDF text.

## Confirmed output defects (June 2 run)

| Defect | Example | Root cause |
|---|---|---|
| Hallucinated aliases | "Audie Murphy" alias of Murphy; "Mary Wilson" alias of Wilson — neither first name appears anywhere in the book | `verify_aliases` substring fast-path accepted any "X <Surname>" without checking that X exists in the text |
| Distinct people merged | Rev. Jesse Jackson + SSgt Nate Jackson → one "Jackson"; Lyndon Johnson alias of Leroy Johnson; boxer Jimmy Ellis alias of Ron Ellis | No given-name conflict detection for shared surnames |
| Junk parenthetical aliases | "Reaper (former CO)", "Billy (via letter)" | Parentheticals stripped from canonicals but not aliases |
| Locations/groups as characters | "Hill" (= firebase San Juan Hill) as *protagonist* with `has_dialogue: true`; "Lai" (= My Lai); "Bravo"/"Charlie" (companies); came in as "San Juan Hill personnel" then renamed | No group-descriptor gate on Pass 1/2 canonicals; NER PERSON hits never cross-checked against GPE/LOC/EVENT votes |
| Front/back matter leakage | Susan Perkins + Charlie Varon (acknowledgments) as aliases; "The Purple Heart" (appendix) as character | Appendix titled "…Lingo, Acronyms, Weapons and Terminology" matched no back-matter pattern (0 back-matter regions detected); character extraction never consulted regions anyway |
| Bare-title character | "Sgt" with alias "TOC Sgt Swanson" | `_is_valid_name` had no bare-title rejection |
| Pronunciation all-proper_noun | NVA, VC, RTO, TOC, PFC all `proper_noun` | Blind UNKNOWN→PROPER_NOUN upgrade for capitalized words; no acronym concept |
| Dialogue attribution invisible | CRF `dialogue_speakers` computed per chapter, never exported; `has_dialogue` derived from "any quote char near any mention" | `StructuralElement`/`AnalysisResult` had no field for it |
| Relationship pollution | "Nam": "deployment zone", "Claymore": "tactical weapon" | Downstream of bogus non-person cast members (clean_orphaned_relationships only removes non-cast targets) |
| Profile errors | Lefty `age_indication: "eight years old"`; empty `physical_description` on protagonists | LLM attribution drift; un-grounded age field (NOT yet fixed — see proposals) |

## Fixes applied (all tested, 396 passing)

### Alias verification (`character_extraction_v2/main_cast.py`)
- **Rule 0.0** — parenthetical qualifiers stripped from aliases; redundant results dropped.
- **Rule 0.1** — group/role descriptors ("<X> personnel", "<Y> Company RTO") blocked as aliases.
- **Rule 1.5 token grounding** — every substantive alias token must appear in the summaries
  the LLM saw (titles/canonical tokens/fillers exempt). Kills fabricated aliases.
- **Rule 1.6 / 2.5 given-name conflict** — same surname + different given name = different
  people (nickname/prefix/hyphen escape hatches; known NICKNAME_TO_FORMAL pairs exempt).
  Losers are routed to the Rule-1 candidate-character buffer.
- Group-descriptor gate also applied to Pass 1/Pass 2 canonical names
  (`_parse_pass1_results`, `_parse_profiles`), with leading-title stripping so
  "Staff Sergeant X" isn't misread as a group.
- Replay on the June run data: 87 → 59 aliases; every confirmed-bad alias removed.

### Supporting cast (`character_extraction_v2/supporting.py`)
- NER label-vote veto: names tagged GPE/LOC/FAC/ORG/EVENT/etc. at least as often as
  PERSON (including as components of multi-word place entities) are rejected.
- Bare military/civil titles rejected as names ("Sgt", "Lieutenant", …).
- Optional `body_range`: entities outside the narrative body are ignored. Wired from
  `analyzer.py` via `AgentContext.metadata["body_range"]` (BODY region bounds).

### Regions (`ingestion/regions.py`)
- New back-matter patterns: glossary-style headings containing
  acronyms/terminology/abbreviations; acknowledgments at the back of the book.

### Pronunciation (`pronunciation_guide/`)
- New `ACRONYM` flag; consolidator detects all-caps 2–6 letter initialisms instead of
  blindly upgrading capitalized UNKNOWNs to PROPER_NOUN. Exported as `technical`.
- Enricher system prompt now requires letter-name IPA for letter-by-letter acronyms and
  IPA ↔ respelling agreement.

### Dialogue attribution
- `StructuralElement.dialogue_speakers` added; `_convert_chapters` now exports the CRF
  attribution results (previously computed and dropped).
- INFO logging for CRF/echo activity; explicit log when CRF is skipped.

### Observability
- `analyze()` logs a scalpel availability map at start and adds a warning listing
  unavailable scalpels. (In the June run, compass/voice/echo/CRF left no trace; all
  models load fine in the current venv, so the silence was environmental and is now
  diagnosable.)

## Scalpel status (7 + 1 in training)

All seven are wired with LLM fallbacks: beacon (`narrator.py:117`), cluster
(`main_cast.py:654`), compass (`moral_valence.py:195`), echo (`summarizer.py:937`),
voice (`passage_gatherer.py:492`), scope (gated, `narrator.py:199`), attribution_crf
(`summarizer.py:965`). June run evidence: only beacon (3×) and cluster (105 pairs → 11
chars) demonstrably ran. Kinship (8th) is in data-collection (`tools/distill_kinship_*`,
`validation/`), no model yet.

## Proposals (not implemented)

1. **Profile grounding**: verify `age_indication` and appearance claims appear in the
   character's own mention contexts before accepting them (Lefty "eight years old").
2. **Pronunciation volume**: `min_occurrences=1` floods narrators (733 entries). Add a
   frequency/percentile cap and stop boosting confidence by occurrence count
   (`consolidator.py:_calculate_confidence`).
3. **Dinks/Dinkins disambiguation**: fuzzy character-name matching in the character
   proposer so character nicknames aren't treated as dictionary slang (and vice versa).
4. **IPA↔respelling validator**: deterministic consistency check in the enricher.
5. **Protagonist promotion**: `analyzer.py` promotes any 200+-mention character to
   protagonist; should require narrative-role evidence (POV/narrator/moral-valence).
6. **has_dialogue**: derived from "quote char within mention context" — very permissive;
   consider requiring a speech-verb pattern or CRF attribution hit.
7. **Enhanced profiling path**: the F1/F2/F3 (summary-evidence + moral-valence) profiling
   branch logged "enabled" but compass never classified anyone — verify which
   `_generate_character_profile` call site runs and consolidate.

## Oracle loop verdict: salvageable, pause until fixed

Architecture (analyze→evaluate→fix with regression guards, escalation PRDs,
checkpoints) is well built, but:
- **No held-out set** — fixes are validated on the same book that motivated them;
  11/21 "passing" books have unknown regression status (checkpoints.json was reset;
  the .bak holds the old baselines).
- **LLM non-determinism spiral** — monkeys_paw oscillates 8.33–8.45 across attempts 5–8;
  EVALUATION_STATE.md documents fix A breaking B, fix B regressing A on re-run.
- **Fixes only touch downstream layers** (post_corrections.py) while upstream
  (ingestion/summaries) is stochastic.

Recommended: freeze 5–7 books as a validation set, re-run all baseline books before
accepting any fix, set temperature=0/seed for profiling during evaluation, and treat
2+ stuck books as a human-escalation trigger. The distillation tools (scalpel training)
are independent of the loop and worth continuing regardless.
