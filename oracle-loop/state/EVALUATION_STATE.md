# Current Evaluation State

## Active Text
- **Name:** american_sir
- **Attempt:** 23
- **Phase:** awaiting_fix
- **baseline_score:** 6.55
- **Competitive Mode:** none

## Output Files
- HTML: ../output/american_sir/report.html
- JSON: ../output/american_sir/analysis.json

## Latest Scores
- Structure Detection: 9/10 ✓
- Character Extraction: 4.5/10 ✗ (FAILING)
  - Completeness: 5/10
  - Identity Resolution: 3/10
  - Alias Grouping: 5.5/10
- Character Profiles: 4/10 ✗ (FAILING)
- Chapter Summaries: 5/10 ✗ (FAILING)
- Pronunciation Guide: 9/10 ✓
- HTML Presentation: 8.5/10 ✓
- **Overall: 6.3/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (3 categories below threshold)

## Current Issues (Priority Order)

### CRITICAL
1. **Father/son "John Donaldson" merged into one entity** [Identity Resolution]
   - Problem: "John Donaldson" (main_cast_2, 31 mentions) has aliases "his father" and "John" — this is a merged father+son entity. The story has TWO distinct characters both named John Donaldson: the father (embezzler who faked his death, ~55, lives in Italy, dies as stretcher-bearer) and the son (the boy, ~22, ambulance driver, finds his father). They are distinct people with different ages, descriptions, and arcs.
   - Evidence: 31 mentions combines both characters. Alias "his father" confirms the father is in there. But "Johnny" (main_cast_0, 1 mention) is supposed to be the son — it's a fragment split off with almost no mentions.
   - This is the CORE blocker. After 23 attempts, the pipeline cannot reliably separate same-name characters. Attempts 8-9 succeeded (7.85, 8.0) but the result is stochastic — it depends on LLM output variance, not stable code.
   - Location: V2 pipeline — `src/pipeline/character_extraction_v2/main_cast.py` (STEP 3.95b/3.95c split logic)
   - **Pattern:** This text is adversarial for the pipeline because BOTH characters share the exact same canonical name "John Donaldson". The LLM sees one name and merges them. Post-extraction split heuristics fire inconsistently.

2. **"American, sir" is a hallucinated character** [Completeness / Identity Resolution]
   - Problem: "'American, sir'" (main_cast_5, 5 mentions) is listed as a character with role "antagonist". It is NOT a character — it's a catchphrase spoken by John Donaldson (the father) when asked if he's Italian. The 5 "mentions" are dialogue instances of the phrase.
   - Evidence: In the source text, "American, sir" appears only as dialogue: `"'American, sir,' he said proudly"` (line 246), `"American, sir--I heard the call"` (line 506), `"'American, sir,' he said in a strong voice. And fell back dead."` (line 526), `"'American, sir,' whispered my dear boy"` (line 547).
   - The physical description assigned to "'American, sir'" ("Tall and broad-shouldered, with dark brown skin") is actually the FATHER's description, cross-contaminated.
   - Location: Character extraction Pass 1 is extracting dialogue as a character name. Needs filtering in `main_cast.py` or `supporting.py`.

3. **Wrong narrator identification** [Identity Resolution]
   - Problem: "Johnny" (main_cast_0, 1 mention) is tagged as narrator. The actual first-person narrator is Uncle Bill — the entire story is told in his voice ("I threw the letter in the scrap-basket", "I sat down to my orderly desk", "I met him"). The boy John tells his war story in DIALOGUE within Uncle Bill's narration.
   - Evidence: Every first-person passage outside quotation marks is Uncle Bill speaking. "Johnny" appears exactly once in the text, as Ted Frith's nickname for the boy (line 326: "'That you, Johnny?' he shouted").
   - Location: Narrator detection in `src/agents/characters.py` or `src/analyzer.py` — the 1-mention "Johnny" was selected as narrator, failed the low-mention invariant, then narrator was reset. Uncle Bill (18 mentions, actual first-person speaker) should be narrator.

### HIGH
4. **Johnny is a 1-mention fragment, not a real character** [Identity Resolution]
   - Problem: "Johnny" (main_cast_0) has only 1 mention. It should be an alias of John Donaldson (the son), not a separate character. "Johnny" is just Ted Frith's nickname for the boy.
   - Evidence: Line 326: "'That you, Johnny?'" — this is the only occurrence. The boy is called "John" throughout.
   - Location: Fragment merge in `characters.py` should merge this into the son character.

5. **Profile cross-contamination** [Character Profiles]
   - Problem: Multiple characters have WRONG physical descriptions:
     - "Johnny" (the boy) shows "an elderly, grizzled, small man, grim and unexhilarating" — this is Uncle Bill's self-description (line 128-129), NOT the boy
     - "'American, sir'" shows the father's description ("Tall and broad-shouldered, with dark brown skin and thick black lashes")
     - Uncle Bill has NO physical description despite being described in text
     - John Donaldson has a mixed description ("Tall, olive-skinned, with blue eyes beneath thickset and long lashes; physically resembles his son") — this combines traits of BOTH father and son
   - Root cause: Father/son merge causes the profiler to conflate descriptions. The narrator misidentification causes Uncle Bill's self-description to be attributed to "Johnny".

6. **Summary major factual error: Uncle Bill dying on battlefield** [Chapter Summaries]
   - Problem: The summary states "Uncle Bill, mortally wounded on the battlefield, confesses his fear of dishonor, corrects a mistaken belief that he was Italian by declaring 'American, sir,' and moments later sits up laughing, repeats the phrase with strength, and dies"
   - This is COMPLETELY WRONG. Uncle Bill is the narrator, sitting in his den listening to the boy's story. He is NEVER on the battlefield. The person who dies saying "American, sir" is John Donaldson THE FATHER.
   - The summary also says "his deceased brother's twelve-year-old son" — John is his COUSIN's son, not brother's.
   - Root cause: The LLM summarizer is confusing Uncle Bill with the father, likely because the character extraction merged them or because the names are confusing.

### MEDIUM
7. **All character summaries are null** [Character Profiles]
   - Problem: Every character has `"summary": null`. No character has a narrative summary explaining their role.
   - Location: Profile generation in `src/analyzer.py` — `_generate_character_profile()` is not producing summaries.

8. **Relationship errors** [Character Profiles]
   - John Donaldson lists relationship "John: father" — this is self-referential (John is an alias of John Donaldson)
   - Uncle Bill lists "'American, sir': uncle" — Uncle Bill is not uncle to a phrase
   - "'American, sir'" lists "Uncle Bill: nephew" — nonsensical
   - Missing: Uncle Bill → John (the boy): guardian/father-figure. John (the boy) → John Donaldson (father): son.

9. **Joe Barron missing** [Completeness]
   - Problem: Joe Barron is a named character who appears at least twice (helps lift the father into the car, mentioned again later). Minor but real.
   - Evidence: Lines 352, 382, 512 mention Joe Barron by name.

### LOW
10. **"Bersagliari" pronunciation** [Pronunciation]
    - The standard Italian spelling is "Bersaglieri" but the source text uses "Bersagliari" — the IPA given is reasonable for the text's spelling. Minor.

## Score History
| Attempt | Score | Delta from Baseline | Notes |
|---------|-------|---------------------|-------|
| 1 | 6.55 | 0 | Baseline |
| 2 | 6.6 | +0.05 | Narrator fix |
| 3 | 6.0 | -0.55 | REGRESSION |
| 4 | 6.4 | -0.15 | Partial fix |
| 5 | 6.7 | +0.15 | Plot summary improved |
| 6 | 7.0 | +0.45 | Uncle Bill narrator |
| 7 | 6.9 | +0.35 | Boy disappeared |
| 8 | 7.85 | +1.30 | Father/son split worked |
| 9 | 8.0 | +1.45 | Cross-character alias fix |
| 10 | 7.0 | +0.45 | REGRESSION — split didn't fire |
| 11 | 7.2 | +0.65 | Mixed |
| 12 | 7.7 | +1.15 | Split via alias contradiction |
| 13 | 5.8 | -0.75 | SEVERE REGRESSION |
| 14 | 7.6 | +1.05 | Split worked |
| 15 | 6.85 | +0.30 | Split didn't fire |
| 16 | 6.95 | +0.40 | No parenthetical |
| 17 | 6.2 | -0.35 | Summary regression |
| 18 | 6.8 | +0.25 | Father/son merged |
| 19 | 7.7 | +1.15 | Split worked (Pattern D) |
| 20 | 5.95 | -0.60 | SEVERE REGRESSION |
| 21 | 6.5 | -0.05 | Narrator ✓, alias ✓, split ✗ |
| 22 | 6.35 | -0.20 | "American, sir" regression. HTML fixed. |
| 23 | 6.3 | -0.25 | STEP 3.95b fixes had no effect. Same issues. |

## Fix History
- Attempt 22: STEP 3.95c added (kinship-fragment split). HTML BOM/title fix. 3.95c didn't fire.
- Attempt 23: STEP 3.95b: removed `"(" in canonical_name` guard → sibling-ID check; alias iteration; Pattern E. STEP 3.95c/3.97: replaced `"(" not in canonical_name` guard with `not c.id.endswith("_parent")`.

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 8 | Father/son split | main_cast.py (STEP 3.95) | Fixed (stochastic) |
| 9 | Cross-char alias | main_cast.py | Fixed |
| 10-16 | Father/son split reliability | main_cast.py (3.95, 3.95b, 3.95c) | Inconsistent — works ~40% of runs |
| 17 | Summary regression | analyzer.py | No change |
| 18-19 | Father/son split patterns | main_cast.py (Pattern D) | Inconsistent |
| 20-23 | Father/son split patterns | main_cast.py (3.95b, 3.95c, Pattern E) | No change |

**ESCALATION NOTICE:** main_cast.py STEP 3.95* has been modified 15+ times across attempts 8-23 without achieving stable results. The same-name father/son disambiguation is fundamentally stochastic — it depends on LLM output variance, not code logic. The split heuristics fire ~40% of runs.

**Root cause analysis:** The pipeline assumes characters have DIFFERENT names. When two characters share the exact same canonical name "John Donaldson", the LLM merges them in Pass 1 extraction, and post-extraction split heuristics cannot reliably un-merge them because the signals (kinship alias "his father", age references) are weak and inconsistent.

## Configuration Notes
- Model: qwen3-next:80b-a3b-instruct-q8_0 (all agents)
- Config: max_tokens=8192, context_length=32768, think_mode=false

## Next Action
**ESCALATION REQUIRED.** After 23 attempts, the same issues persist:
1. Father/son merge (stochastic, ~40% success rate with current heuristics)
2. "American, sir" hallucinated as character
3. Wrong narrator (Uncle Bill should be narrator, not Johnny)
4. Summary conflates Uncle Bill with the dying father

Recommended escalation options:
- **Option A:** Skip this text (mark as known-hard-case) and move to next text in manifest. This text is adversarial for the pipeline due to same-name characters.
- **Option B:** Add a deterministic pre-processing step that detects dialogue-phrases being extracted as characters (fixes issue #2) and forces narrator detection by first-person pronoun density outside quotation marks (fixes issue #3). This won't fix the father/son merge but would raise the score.
- **Option C:** Fundamentally redesign the same-name disambiguation logic — this is a large architectural change.

The user should decide which path to take.
