# Audiobook Prep Output Quality Rubric

This rubric defines evaluation criteria for audiobook narrator preparation documents. Use this to assess analysis output quality.

## Scoring Overview

| Category | Weight | Focus |
|----------|--------|-------|
| Structure Detection | 20% | Chapter boundaries, front/back matter |
| Character Extraction | 25% | All characters identified, correct aliases |
| Character Profiles | 15% | Accurate descriptions, relationships |
| Chapter Summaries | 20% | Key events, narrator-useful details |
| Pronunciation Guide | 10% | Unusual words flagged, no false positives |
| HTML Presentation | 10% | Navigation, readability, organization |

**Threshold:** Overall score >= 8.0 to pass

---

## Category Details

### 1. Structure Detection (Weight: 20%)

**What we're measuring:** Did the tool correctly identify the book's organization?

| Score | Criteria |
|-------|----------|
| 10 | Perfect: All chapters identified, correct boundaries, handles unusual structures |
| 8-9 | Excellent: All major divisions correct, minor issues with epigraphs or breaks |
| 6-7 | Good: Most chapters correct, some boundary errors or missed subdivisions |
| 4-5 | Fair: Significant errors but majority of structure captured |
| 1-3 | Poor: Major structural errors, merged or missing chapters |
| 0 | Failed: Structure completely wrong or not detected |

**Checklist:**
- [ ] All chapters detected (compare to expected chapter count)
- [ ] Chapter titles extracted correctly
- [ ] Front matter (dedication, preface) identified separately
- [ ] Back matter (notes, appendices) identified separately
- [ ] No merged chapters (two chapters treated as one)
- [ ] No split chapters (one chapter treated as multiple)
- [ ] Roman numerals handled correctly
- [ ] "Chapter" vs "Book" vs "Part" hierarchy correct

---

### 2. Character Extraction (Weight: 25%)

**What we're measuring:** Are all significant characters identified with correct information?

| Score | Criteria |
|-------|----------|
| 10 | Perfect: All named characters, correct aliases, accurate relationships |
| 8-9 | Excellent: All major characters, most minor, few alias issues |
| 6-7 | Good: Major characters correct, some missing minors or alias errors |
| 4-5 | Fair: Main characters present but significant gaps or errors |
| 1-3 | Poor: Major characters missing or incorrectly merged/split |
| 0 | Failed: Character extraction completely wrong |

**Checklist:**
- [ ] All major characters (>10 mentions) identified
- [ ] No false character splits (same person as two entries)
- [ ] No false character merges (two people as one entry)
- [ ] Aliases correctly grouped (full name = nickname = title+name)
- [ ] Titles handled correctly (Dr., Mr., Mrs., etc.)
- [ ] Nicknames linked to canonical names
- [ ] No hallucinated characters (entries that don't exist in text)
- [ ] First appearance chapter is accurate

**Common Issues:**
- Characters sharing surnames incorrectly merged (spouses, siblings)
- Full names and nicknames not linked
- Titled references (Mr. X) not linked to full names
- Minor characters filtered out too aggressively

---

### 3. Character Profiles (Weight: 15%)

**What we're measuring:** Are character descriptions accurate and useful for narration?

| Score | Criteria |
|-------|----------|
| 10 | Perfect: Rich, accurate descriptions with voice notes and relationships |
| 8-9 | Excellent: Good descriptions, accurate relationships, useful details |
| 6-7 | Good: Basic descriptions correct, some missing depth |
| 4-5 | Fair: Descriptions present but thin or partially inaccurate |
| 1-3 | Poor: Descriptions wrong or mostly missing |
| 0 | Failed: No useful profile information |

**Checklist:**
- [ ] Physical descriptions match text (when provided)
- [ ] Personality traits supported by text evidence
- [ ] Key relationships identified (family, romantic, professional)
- [ ] No invented details (information not in the source text)
- [ ] Speech patterns or dialect noted (when present)
- [ ] Character arc summary useful for narrator

---

### 4. Chapter Summaries (Weight: 20%)

**What we're measuring:** Do summaries help a narrator prepare for each chapter?

| Score | Criteria |
|-------|----------|
| 10 | Perfect: Accurate, comprehensive, narrator-focused summaries |
| 8-9 | Excellent: Captures key events and tone, useful for prep |
| 6-7 | Good: Main events correct, some gaps or minor errors |
| 4-5 | Fair: Partially accurate but missing key events or has errors |
| 1-3 | Poor: Major inaccuracies or missing most content |
| 0 | Failed: Summaries wrong or not generated |

**Checklist:**
- [ ] Key plot events captured (3-5 per chapter minimum)
- [ ] Characters appearing in chapter mentioned
- [ ] No hallucinated events (things that didn't happen)
- [ ] No major spoilers from future chapters
- [ ] Tone and mood indicated (useful for narrator)
- [ ] Length appropriate (100-300 words)
- [ ] Setting/location changes noted

---

### 5. Pronunciation Guide (Weight: 10%)

**What we're measuring:** Are unusual words flagged with helpful pronunciation info?

| Score | Criteria |
|-------|----------|
| 10 | Perfect: All unusual words flagged, accurate IPA, no false positives |
| 8-9 | Excellent: Good coverage, mostly accurate, few false positives |
| 6-7 | Good: Most unusual words caught, some gaps or errors |
| 4-5 | Fair: Partial coverage, noticeable gaps or many false positives |
| 1-3 | Poor: Major gaps or mostly incorrect |
| 0 | Failed: No useful pronunciation information |

**Checklist:**
- [ ] Foreign words/phrases identified
- [ ] Unusual proper nouns flagged (names, places)
- [ ] Period-specific terms noted
- [ ] IPA provided and accurate (when present)
- [ ] No common words flagged (false positives)
- [ ] Context provided for homographs (read vs. read, lead vs. lead)
- [ ] Regional/dialect pronunciations noted

---

### 6. HTML Presentation (Weight: 10%)

**What we're measuring:** Is the output professional and usable?

| Score | Criteria |
|-------|----------|
| 10 | Perfect: Clean, navigable, print-ready, professional appearance |
| 8-9 | Excellent: Well-organized, easy to use, minor polish issues |
| 6-7 | Good: Functional and readable, some UX improvements possible |
| 4-5 | Fair: Usable but awkward navigation or formatting issues |
| 1-3 | Poor: Difficult to use, significant formatting problems |
| 0 | Failed: Broken or unreadable |

**Checklist:**
- [ ] Navigation works (can jump to chapters, characters)
- [ ] Typography is readable
- [ ] Information is logically organized
- [ ] No broken elements or missing sections
- [ ] Prints cleanly (if applicable)

---

## Scoring Formula

```
Overall = (
    Structure × 0.20 +
    Characters × 0.25 +
    Profiles × 0.15 +
    Summaries × 0.20 +
    Pronunciation × 0.10 +
    Presentation × 0.10
)
```

**Thresholds:**
- **ALL categories >= 8.0**: PASS - advance to next text
- **ANY category < 8.0**: FAIL - iterate with fixes

Note: The overall weighted score is calculated for reference, but the pass/fail determination is based on individual category scores. Every category must independently achieve at least 8.0/10.

---

## Issue Severity Classification

When scoring below threshold, classify issues for the fix phase:

### CRITICAL (blocks progress, score impact > 1 point)
- Character merge/split errors for main characters
- Missing major characters
- Completely wrong chapter structure
- Hallucinated content

### HIGH (significant impact, score impact 0.5-1 point)
- Missing minor but named characters
- Incorrect relationships for main characters
- Multiple chapter summary errors
- Major pronunciation gaps

### MEDIUM (noticeable but manageable, score impact < 0.5)
- Minor character description inaccuracies
- Excessive false positives in pronunciation
- Formatting/presentation issues
- Missing some aliases

### LOW (polish items)
- Minor wording improvements
- Edge case handling
- Performance optimizations

---

## Evaluation Notes

### Use Your Knowledge
The evaluator (Claude) has literary knowledge of classic texts. Use this knowledge to:
- Verify character completeness against known casts
- Check summary accuracy against known plots
- Validate relationships and aliases

### Be Specific
Instead of: "Character extraction has issues"
Write: "Jay Gatsby and 'Gatsby' are listed as separate characters. These should be merged as aliases."

### Be Actionable
Include file locations and suggested fixes when possible:
- "Likely cause: alias resolution in src/agents/characters.py"
- "Suggested fix: improve fuzzy matching for FirstName-LastName to LastName"

### Focus on Threshold
If score is 7.8, focus only on what's needed to cross 8.0. Don't enumerate every possible improvement.
