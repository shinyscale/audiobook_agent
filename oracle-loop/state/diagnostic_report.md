# Cross-Book Diagnostic Report

Generated: 2026-03-06T14:45:29-07:00
Texts scored: 7

## Failure Matrix

Text                                   Str   Chr   Pro   Sum   Prn   Prs    Avg       
--------------------------------------------------------------------------------------
a_camping_trip                        7.0*  6.0*  6.0*  9.0   8.0   7.0*  7.17   FAIL
american_sir                          9.0   7.0*  7.0*  8.5   8.5   8.5   8.00   FAIL
berenice                              8.0   7.0*  8.0   9.0   6.0*  8.0   7.67   FAIL
cask_of_amontillado                   9.0   6.0*  7.0*  9.0   7.0*  8.0   7.67   FAIL
gift_of_the_magi                      8.0   9.0   8.0   9.0   7.0*  7.0*  8.00   FAIL
masque_of_red_death                   9.0   6.0*  8.0   9.0   7.0*  9.0   8.00   FAIL
monkeys_paw                           3.0*  7.0*  5.0*  7.0*  7.0*  8.0   6.17   FAIL

(* = below 8.0 threshold)

## Systemic Patterns (Column Analysis)

### Characters — CRITICAL (6/7 texts failing, 86%)
  Mean: 6.86 | Min: 6.0 | Max: 9.0
  Failing: a_camping_trip, berenice, cask_of_amontillado, masque_of_red_death, monkeys_paw, american_sir

### Pronunciation — CRITICAL (5/7 texts failing, 71%)
  Mean: 7.21 | Min: 6.0 | Max: 8.5
  Failing: berenice, cask_of_amontillado, gift_of_the_magi, masque_of_red_death, monkeys_paw

### Profiles — CRITICAL (4/7 texts failing, 57%)
  Mean: 7.00 | Min: 5.0 | Max: 8.0
  Failing: a_camping_trip, cask_of_amontillado, monkeys_paw, american_sir

### Structure — MEDIUM (2/7 texts failing, 29%)
  Mean: 7.57 | Min: 3.0 | Max: 9.0
  Failing: a_camping_trip, monkeys_paw

### Presentation — MEDIUM (2/7 texts failing, 29%)
  Mean: 7.93 | Min: 7.0 | Max: 9.0
  Failing: a_camping_trip, gift_of_the_magi

### Summaries — LOW (1/7 texts failing, 14%)
  Mean: 8.64 | Min: 7.0 | Max: 9.0
  Failing: monkeys_paw

## Priority Fix Recommendations

Fix systemic patterns (column issues) before per-text issues (row issues).
A fix is only accepted if it helps multiple texts without regressing others.

1. **Characters** (6 texts failing, weight: 25%)
  - [a_camping_trip] "The Boat" extracted as a protagonist character — inanimate object should not be a character entry
  - [a_camping_trip] Milton Jennings incorrectly marked as first-person narrator; this is a third-person narrative
  - [a_camping_trip] Role-based aliases ("treasurer" for Rance, "cook" for Bert) are unusual and could confuse a narrator
  - [berenice] Berenice labeled 'antagonist' when she is a victim/object of obsession, not an active antagonist
  - [berenice] Berenice gender is null despite being clearly female

2. **Pronunciation** (5 texts failing, weight: 10%)
  - [berenice] Jove IPA /dʒʌv/ is wrong — should be /dʒoʊv/ (rhymes with stove, not love)
  - [berenice] pertinaciously phonetic spelling 'puh-TIN-uh-SIS-uh-lee-lee' is garbled — should be 'pur-tin-AY-shus-lee'
  - [berenice] emaciation IPA uses /mæʃ/ — the 'ci' is /si/ not /ʃ/
  - [berenice] False positives: tarried, sentient, conformation, unloveliness are common English words that don't need pronunciation guidance
  - [berenice] Mad'selle note says contraction of 'Madame' — it's 'Mademoiselle'

3. **Profiles** (4 texts failing, weight: 15%)
  - [a_camping_trip] Bert Jenks profile has null personality/voice_guidance and description field contains malformed JSON-like text instead of prose
  - [a_camping_trip] Mr. Jennings description incorrectly begins with "Milton Jennings is a supportive adult" — wrong character name
  - [a_camping_trip] Some relationship labels are questionable: Rance→Mr. Jennings as "protégé", Lincoln→Mr. Jennings as "employer"
  - [cask_of_amontillado] Fortunato missing iconic physical description: parti-striped jester costume with conical cap and bells
  - [monkeys_paw] Sergeant-Major Morris relationships completely wrong: listed as husband of Mrs. White and father of Herbert White. Morris is an old friend/visitor, not family

4. **Structure** (2 texts failing, weight: 20%)
  - [a_camping_trip] Metadata title is "Hamlin Garland" (author name) instead of the story title "A Camping Trip"
  - [monkeys_paw] Story has 3 parts (I, II, III) but pipeline detected only 1 chapter with wrong title 'The Lady Of The Barge And Other Stories' (collection title, not story title)

5. **Presentation** (2 texts failing, weight: 10%)
  - [a_camping_trip] Report header displays "Hamlin Garland" (author) as the title rather than the story name
  - [gift_of_the_magi] HTML title contains BOM character and shows author name instead of story title: '﻿O. Henry - Audiobook Prep Report'


## Per-Text Notes

- **a_camping_trip**: Summaries and pronunciation are strong, but character extraction is undermined by an inanimate object (The Boat) being treated as a protagonist, a false narrator assignment to Milton, and a corrupted Bert Jenks profile. The wrong title in metadata propagates through the HTML report.
- **american_sir** (historical): (historical baseline from checkpoints.json)
- **berenice**: Strong summary and character profiles for a short Poe story, but pronunciation section has several IPA errors on well-known words and flags common English terms as needing guidance. Berenice's gender and role classification need correction.
- **cask_of_amontillado**: Real characters (Montresor, Fortunato, Luchresi) are well-identified with strong profiles and evidence, but the phantom 'The Amontillado' character is a significant false positive that drags down the characters score. Summaries and structure are excellent for this short story.
- **gift_of_the_magi**: Strong character extraction and summaries for this short story. Main gaps are in pronunciation (missing 'Magi' and 'Dillingham') and metadata (title/author swap causing presentation issues).
- **masque_of_red_death**: Good overall analysis of a short story with strong summaries and presentation, but the Red Death's nonsensical room aliases and the mispronunciation of the title character's name are significant issues that would mislead a narrator.
- **monkeys_paw**: Structure detection completely failed — missed the story's 3 Roman-numeral parts and used the collection title instead. Relationship extraction has a systematic bug where characters' own roles (wife, father) are assigned as their relationship to unrelated characters.
