# Cross-Book Diagnostic Report

Generated: 2026-02-16T18:01:29-07:00
Texts scored: 11

## Failure Matrix

Text                                   Str   Chr   Pro   Sum   Prn   Prs    Avg       
--------------------------------------------------------------------------------------
a_camping_trip                       10.0   9.0   8.0  10.0   8.5   9.0   9.20   PASS
american_sir                          7.0*  5.0*  5.0*  8.0   7.0*  7.0*  6.50   FAIL
berenice                             10.0   9.0   8.0   9.0   9.0   9.0   9.10   PASS
cask_of_amontillado                  10.0   8.0   8.0   9.0   9.0   9.0   8.95   PASS
frankenstein                          8.0   8.0   7.0*  8.0   8.0   9.0   8.10   FAIL
gatsby                                9.5   9.0   8.0   9.5   9.0   9.0   8.98   PASS
gift_of_the_magi                     10.0   9.0   8.0   9.5   8.0   8.5   9.00   PASS
i_have_no_mouth                       9.0   8.0   8.0   9.0   9.0   9.0   8.80   PASS
john_g                               10.0   9.0   8.5   9.0   8.0   9.0   8.90   PASS
masque_of_red_death                  10.0   9.0   8.0  10.0   9.0  10.0   9.35   PASS
monkeys_paw                          10.0   9.0   8.0  10.0   9.0   9.0   9.20   PASS

(* = below 8.0 threshold)

## Systemic Patterns (Column Analysis)

### Profiles — MEDIUM (2/11 texts failing, 18%)
  Mean: 7.68 | Min: 5.0 | Max: 8.5
  Failing: american_sir, frankenstein

### Structure — LOW (1/11 texts failing, 9%)
  Mean: 9.41 | Min: 7.0 | Max: 10.0
  Failing: american_sir

### Characters — LOW (1/11 texts failing, 9%)
  Mean: 8.36 | Min: 5.0 | Max: 9.0
  Failing: american_sir

### Pronunciation — LOW (1/11 texts failing, 9%)
  Mean: 8.50 | Min: 7.0 | Max: 9.0
  Failing: american_sir

### Presentation — LOW (1/11 texts failing, 9%)
  Mean: 8.86 | Min: 7.0 | Max: 10.0
  Failing: american_sir

### Summaries — LOW (0/11 texts failing, 0%)
  Mean: 9.18 | Min: 8.0 | Max: 10.0

## Priority Fix Recommendations

Fix systemic patterns (column issues) before per-text issues (row issues).
A fix is only accepted if it helps multiple texts without regressing others.

1. **Profiles** (2 texts failing, weight: 15%)
  - [american_sir] Son's profile describes a 'dark-skinned, middle-aged man who committed grave betrayals' — entirely wrong person's data
  - [american_sir] Quote 'No--no. It's covered over...' attributed to Uncle Bill but spoken by John the son


## Per-Text Notes

- **a_camping_trip** (historical): (historical baseline from checkpoints.json)
- **american_sir**: The critical flaw is a full identity swap between John Donaldson father and son — the son's profile contains the father's physical description, personality, quotes, and relationships, making the character guide unreliable for an audiobook narrator. Structure, summaries, and pronunciation are adequate but the character confusion undermines the core use case.
- **berenice** (historical): (historical baseline from checkpoints.json)
- **cask_of_amontillado** (historical): (historical baseline from checkpoints.json)
- **frankenstein** (historical): (historical baseline from checkpoints.json)
- **gatsby** (historical): (historical baseline from checkpoints.json)
- **gift_of_the_magi** (historical): (historical baseline from checkpoints.json)
- **i_have_no_mouth** (historical): (historical baseline from checkpoints.json)
- **john_g** (historical): (historical baseline from checkpoints.json)
- **masque_of_red_death** (historical): (historical baseline from checkpoints.json)
- **monkeys_paw** (historical): (historical baseline from checkpoints.json)
