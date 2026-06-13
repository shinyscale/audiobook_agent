# Golden Corpus Spec — held-out evaluation set

Goal: a fixed, diverse book set with hand-verified ground truth so every pipeline
change gets a deterministic score (`tools/score_analysis.py --batch`), and the
oracle loop gets a held-out validation set. Scoring is pure set comparison — no
LLM judge — so the full corpus scores in seconds from cached analyses.

## Already seeded (8 truth files in validation/golden/)

| Book | Dimension exercised |
|---|---|
| gatsby | first-person narrator, ensemble, same-surname spouses (Buchanans, Wilsons) |
| frankenstein | nested/epistolary narration (Walton→Victor→Creature), unnamed character |
| cask_of_amontillado | first-person villain narrator, 2-person cast |
| monkeys_paw | third-person, family same-surname cast (the Whites) |
| berenice | unreliable narrator, forbidden-name canary (Mad'selle Salle) |
| gift_of_the_magi | nickname↔formal alias (Jim / James Dillingham Young) |
| masque_of_red_death | symbolic/personified antagonist, title-stripped alias |
| i_have_no_mouth | invented names (AM, Nimdok), modern prose, PDF ingestion |

## Proposed additions (owner verifies each truth file before it counts)

| Book (in Test_Texts/) | Why this one |
|---|---|
| Dracula | hardest narrator test: epistolary, 6+ rotating diarists |
| Pride and Prejudice | five Bennet sisters + Mr./Mrs. Bennet — maximal same-surname stress |
| The Hound of the Baskervilles | Watson narrates (not the protagonist); identity-reveal villain |
| Moby-Dick | "Call me Ishmael" narrator; long non-narrative chapters (cetology) test chapter/summary robustness |
| Don Quixote | translation; epithet aliases ("Knight of the Sorrowful Countenance"); nested tales |
| War and Peace | huge cast; Russian patronymics + diminutives (Natasha/Natalya) — alias logic without English priors |
| Flowers for Algernon | diary form; narrator's spelling changes over time (ingestion + narrator stress) |
| See the Light, Kiss the Ground | modern unpublished manuscript; military titles; front/back matter traps — owner hand-verifies cast |

Optionally add one public-domain invented-name novel (e.g. *A Princess of Mars* —
Dejah Thoris, Tars Tarkas) via tools/curate_gutenberg.py to harden the
"future novel" case: names with zero real-world priors.

## Ground-truth protocol

1. Draft: run the pipeline, convert its cast to a truth file (script can seed this).
2. Verify: a HUMAN corrects the draft against the book — canonical names,
   acceptable aliases, narrator, roles. LLM-drafted truth that isn't human-verified
   does not enter the corpus.
3. Canaries: each book should list 1–3 `forbidden` names — real-world or
   passing-mention names that a hallucinating pipeline plausibly invents
   (Berenice's "Mad'selle Salle" pattern; e.g. "Audie Murphy" for See the Light).
4. Truth files are append-only in spirit: adding missed characters is fine;
   loosening alias sets to make a failing run pass is not.

## Usage

- Manual: `python tools/score_analysis.py <analysis.json> validation/golden/<book>.json`
- Batch: `python tools/score_analysis.py --batch <dir-of-analyses>`
- Fast iteration: `python tools/replay_characters.py Test_Texts/gatsby.txt --golden validation/golden/gatsby.json`
  (uses cached chapter/summary artifacts from output/stage_cache/, written
  automatically by every full analyze() run)
- Oracle loop (when restarted): score the corpus before accepting any fix;
  reject fixes that lower mean character F1 or trigger any forbidden-name hit.

## Metrics reported per book

character F1 (required-recall × main-cast precision), alias P/R,
narrator correctness, forbidden-name hits, missing/spurious lists.
Corpus roll-up: mean F1 + total forbidden hits.
