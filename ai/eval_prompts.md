# Evaluation Prompts for Audiobook Analysis

Use these prompts to evaluate pipeline output. Read the output JSON, then apply the appropriate evaluation.

---

## How to Evaluate

1. **Run the pipeline**: `python ai/run_analysis.py gatsby`
2. **Read the output**: `ai/eval_results/gatsby_latest.json`
3. **Apply evaluation criteria** from sections below
4. **Record results** in structured format
5. **Update progress.log** with findings

---

## Structure Evaluation (Chapters)

### The Great Gatsby

The Great Gatsby has exactly **9 chapters**, numbered Chapter I through Chapter IX (or 1-9).
There are no titled chapters, no prologue, no epilogue.

**Checklist:**
- [ ] Exactly 9 chapters detected
- [ ] No spurious chapters from section breaks or epigraphs
- [ ] Chapter boundaries are at actual chapter starts
- [ ] Confidence >= 0.8 for all chapters
- [ ] No front matter (title page, copyright) included as chapters
- [ ] No back matter (about author, other books) included as chapters

### Frankenstein

Frankenstein has a **frame narrative structure**:
- **Letters I-IV**: Walton's letters to his sister (4 sections)
- **Chapters 1-24**: Victor's narrative (24 sections)
- Total: **28 sections**

The creature's tale is embedded within Victor's narrative (not separate chapters).

**Checklist:**
- [ ] Frame structure detected (letters + chapters)
- [ ] 4 letters detected (Letter I, II, III, IV)
- [ ] 24 chapters detected (Chapter I through XXIV)
- [ ] Total of 28 sections
- [ ] No false chapters from letter closings or scene breaks
- [ ] Letters are NOT merged into single section

---

## Character Evaluation

### The Great Gatsby

**Main characters (MUST be found):**
| Character | Role | Expected Aliases |
|-----------|------|------------------|
| Nick Carraway | Narrator | Nick |
| Jay Gatsby | Protagonist | Gatsby, Mr. Gatsby, James Gatz |
| Daisy Buchanan | Main | Daisy |
| Tom Buchanan | Antagonist | Tom |
| Jordan Baker | Main | Jordan, Miss Baker |

**Supporting characters (SHOULD be found):**
| Character | Notes | Expected Aliases |
|-----------|-------|------------------|
| Myrtle Wilson | Tom's mistress | Myrtle, Mrs. Wilson |
| George Wilson | Myrtle's husband | Wilson |
| Meyer Wolfsheim | Gatsby's associate | Wolfsheim, Mr. Wolfsheim |
| Owl Eyes | Party guest | - |

**CRITICAL - Must NOT merge:**
- Tom Buchanan and Daisy Buchanan (married couple, SEPARATE entries)
- George Wilson and Myrtle Wilson (married couple, SEPARATE entries)

**Checklist:**
- [ ] All 5 main characters found
- [ ] Tom and Daisy Buchanan are SEPARATE entries
- [ ] George and Myrtle Wilson are SEPARATE entries
- [ ] Jay Gatsby aliases correctly merged (Gatsby, Mr. Gatsby, James Gatz)
- [ ] No hallucinated characters (characters not in the book)
- [ ] Mention counts roughly match importance (Gatsby > Owl Eyes)

### Frankenstein

**Main characters (MUST be found):**
| Character | Role | Expected Aliases |
|-----------|------|------------------|
| Victor Frankenstein | Protagonist | Victor, Frankenstein |
| The Creature | Antagonist | Monster, Creature, Fiend, Daemon, Wretch |
| Elizabeth Lavenza | Victor's love | Elizabeth |
| Henry Clerval | Victor's friend | Henry, Clerval |
| Robert Walton | Frame narrator | Walton, Captain |

**Supporting characters (SHOULD be found):**
| Character | Notes |
|-----------|-------|
| Alphonse Frankenstein | Victor's father |
| William Frankenstein | Victor's brother, murdered |
| Justine Moritz | Wrongly executed |
| De Lacey family | Felix, Agatha, Safie, the old man |

**CRITICAL checks:**
- [ ] All creature aliases merged (Monster, Creature, Fiend, Daemon, Wretch)
- [ ] Victor Frankenstein NOT confused with the creature
- [ ] "Frankenstein" refers to Victor, not the monster
- [ ] De Lacey family members may be separate or grouped (both acceptable)

---

## Summary Evaluation

For each chapter summary, verify:

**Checklist per chapter:**
- [ ] Key events of that chapter are mentioned
- [ ] No events from other chapters incorrectly included
- [ ] No hallucinated events that don't occur in the text
- [ ] Character names are accurate (match character list)
- [ ] Length is 100-300 words (useful for narrator prep)
- [ ] Focus is on plot events, not literary interpretation

### The Great Gatsby - Key Events by Chapter

| Ch | Key Events |
|----|------------|
| 1 | Nick moves to West Egg, visits Tom and Daisy, first sees Gatsby reaching toward green light |
| 2 | Valley of Ashes, Tom's mistress Myrtle, party in NYC apartment, Tom breaks Myrtle's nose |
| 3 | Gatsby's party, Nick meets Gatsby, learns Gatsby asks about him, Jordan |
| 4 | Gatsby's car ride with Nick, Gatsby's history claims, Wolfsheim lunch, Jordan tells Gatsby-Daisy story |
| 5 | Gatsby and Daisy reunite at Nick's house, tour of Gatsby's mansion, emotional reunion |
| 6 | Gatsby's true origins (James Gatz), Tom and Daisy attend Gatsby's party |
| 7 | Hottest day, confrontation at Plaza Hotel, Myrtle's death (hit by Gatsby's car driven by Daisy) |
| 8 | Gatsby's vigil outside Daisy's house, his past with Daisy revealed, Wilson kills Gatsby in pool |
| 9 | Gatsby's funeral (poorly attended), Nick's disillusionment with East, green light meditation |

### Frankenstein - Key Events (Selected)

| Section | Key Events |
|---------|------------|
| Letter I-IV | Walton's expedition, meets Victor on ice, Victor begins his tale |
| Ch 1-2 | Victor's childhood, family, early interests in science |
| Ch 4-5 | Victor creates the creature, immediately abandons it in horror |
| Ch 7-8 | William murdered, Justine wrongly executed |
| Ch 11-16 | Creature's perspective: learning, De Lacey family, rejection, revenge |
| Ch 20 | Victor destroys female creature, creature vows revenge |
| Ch 23 | Elizabeth killed on wedding night |
| Ch 24 | Victor pursues creature to Arctic, dies, creature's final appearance |

---

## Pronunciation Evaluation

**Checklist:**
- [ ] All character names flagged with pronunciation guidance
- [ ] Foreign phrases identified with language tag
- [ ] No common English words incorrectly flagged
- [ ] IPA notation provided where applicable
- [ ] Phonetic spelling is readable (e.g., "GATS-bee" not "ˈɡætsbɪ" alone)

### Gatsby-specific checks:
- [ ] "old sport" noted as recurring phrase
- [ ] "Wolfsheim" flagged (pronunciation varies)
- [ ] "Carraway" flagged (proper noun)

### Frankenstein-specific checks:
- [ ] "Frankenstein" flagged (often mispronounced)
- [ ] "Clerval" flagged (French origin)
- [ ] "De Lacey" flagged (French)
- [ ] "Ingolstadt" flagged (German city)

---

## Evaluation Output Format

After evaluating, provide structured feedback:

```json
{
  "feature": "structure.chapter_detection",
  "book": "The Great Gatsby",
  "passed": true,
  "score": 0.95,
  "criteria": {
    "CHAPTER_COUNT": {"passed": true, "expected": 9, "actual": 9},
    "NO_SPURIOUS": {"passed": true},
    "NO_MISSING": {"passed": true},
    "CONFIDENCE": {"passed": true, "min_confidence": 0.85}
  },
  "issues": [],
  "suggestions": [],
  "code_changes_needed": []
}
```

For failures:

```json
{
  "feature": "characters.extraction",
  "book": "The Great Gatsby",
  "passed": false,
  "score": 0.78,
  "criteria": {
    "MAIN_CHARS_FOUND": {"passed": true},
    "NO_FALSE_MERGES": {"passed": false, "details": "Tom and Daisy Buchanan merged"},
    "ALIAS_RESOLUTION": {"passed": true},
    "NO_HALLUCINATIONS": {"passed": true}
  },
  "issues": [
    "Tom Buchanan merged with Daisy Buchanan (should be separate)"
  ],
  "suggestions": [
    "Add check for same-surname different-first-name pairs"
  ],
  "code_changes_needed": [
    "src/pipeline/character_extraction/consensus.py: Update _should_merge() to check first names"
  ]
}
```

---

## Evaluation Workflow

### Full Evaluation Cycle

```
1. RUN PIPELINE
   python ai/run_analysis.py gatsby --model qwen2.5:72b

2. READ OUTPUT
   Read ai/eval_results/gatsby_latest.json

3. EVALUATE EACH FEATURE
   - Structure (chapter detection)
   - Characters (extraction and profiles)
   - Summaries
   - Pronunciations

4. RECORD RESULTS
   Save to ai/eval_results/gatsby_eval_<timestamp>.json

5. UPDATE HARNESS
   - Update ai/feature_list.json status
   - Append to ai/progress.log

6. IF ISSUES FOUND
   - Identify root cause in code
   - Make fix
   - Re-run evaluation

7. IF ALL PASS
   - Run on second book (frankenstein)
   - Verify no regression
```

### Quick Evaluation (Single Feature)

```
1. Read ai/eval_results/gatsby_latest.json
2. Evaluate only the requested feature
3. Report pass/fail with specific issues
```

---

## Triggering Evaluation

Ask Claude Code:

```
"Run the pipeline on gatsby and evaluate chapter detection"

"Evaluate ai/eval_results/gatsby_latest.json for character extraction"

"Compare characters in gatsby_latest.json against The Great Gatsby - are all main characters found?"

"Do a full evaluation cycle: run gatsby, evaluate all features, update feature_list.json"

"Check if Tom and Daisy Buchanan are correctly separated in the latest gatsby analysis"
```

---

## Graduation Criteria

A feature is ready for graduation when:

1. **Passes on both test books** (Gatsby AND Frankenstein)
2. **Structural checks implemented** in agent's verify() method
3. **Self-check prompts work** without book-specific knowledge
4. **Local LLM verification** catches same issues Claude would
5. **Tested on unknown work** (e.g., "I Have No Mouth And I Must Scream")

Update graduation status in feature_list.json when criteria met.
