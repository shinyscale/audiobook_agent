# Current Evaluation State

## Active Text
- **Name:** monkeys_paw
- **Attempt:** 2
- **Phase:** awaiting_fix
- **baseline_score:** 7.90

## Output Files
- HTML: ../output/monkeys_paw/report.html
- JSON: ../output/monkeys_paw/analysis.json

## Latest Scores
- Structure Detection: 10/10 ✓
- Character Extraction: 5/10 ✗ (FAILING)
- Character Profiles: 7.5/10 ✗ (FAILING)
- Chapter Summaries: 9/10 ✓
- Pronunciation Guide: 9/10 ✓
- HTML Presentation: 9/10 ✓
- **Overall: 7.65/10** (reference only)

**Pass Criteria:** ALL categories must be >= 8.0
**Status:** FAIL (2 categories below threshold)

---

## Score Justification

### Structure Detection: 10/10 ✓
The Monkey's Paw is divided into 3 parts (unnamed chapters). All 3 are correctly identified with appropriate boundaries. The structure shows:
- Part I (lines 0-9627): Introduction, Morris brings the paw, first wish
- Part II (lines 9627-14903): Herbert's death, compensation arrives
- Part III (lines 14903-21968): The final wishes

**No issues.** Perfect structure for this short story.

### Character Extraction: 5/10 ✗
**CRITICAL issues found:**

1. **FALSE SPLIT: "the old man" (26 mentions) is separate from "Mr. White" (10 mentions)**
   - These are the same character - the text uses both terms interchangeably
   - The profile for "the old man" even states `"Mr. White": "self"` in relationships!
   - Both have matching distinguishing features: "thin grey beard"
   - The pipeline did NOT attempt any merges (merge_decisions.total_merges = 0)

2. **FALSE MERGE: "the old woman" aliased to "the old man"**
   - "the old woman" is Mrs. White (the wife)
   - "the old man" is Mr. White (the husband)
   - They are husband and wife - TWO DIFFERENT PEOPLE!
   - This is a catastrophic error that corrupts the character relationships

3. **Chapter 3 characters_present uses wrong names**
   - Chapter 3 lists: `["the old man", "the old woman"]`
   - Should be: `["Mr. White", "Mrs. White"]`
   - This indicates the summary agent is using descriptive terms instead of canonical names

**Expected main characters:**
- Mr. White (the father who makes the wishes) ✓ present but fragmented
- Mrs. White (the wife) ✓ present but incorrectly aliased
- Herbert White (the son) ✓ correct
- Sergeant-Major Morris ✓ present as "Morris"
- The representative from Maw and Meggins ✓ present

**Acceptable extractions:**
- "the talisman" (the monkey's paw) - symbolic object with agency, acceptable per guidelines

### Character Profiles: 7.5/10 ✗
The profiles are thin but acceptable for most characters:
- Morris has good profile data: appearance, personality, voice guidance, evidence
- Mr. White has minimal data (age: elderly, distinguishing: thin grey beard)
- Mrs. White has minimal data (age: middle-aged)
- Herbert has minimal data (age: young)
- "the old man" duplicates Mr. White's profile data

**Issues:**
- The fragmentation of "the old man" from "Mr. White" means profile data may be scattered
- No physical_description field populated (but appearance.summary exists for some)

### Chapter Summaries: 9/10 ✓
All 3 chapter summaries are accurate, detailed, and useful for narrator preparation:
- Chapter 1: Correctly describes Morris's arrival, the paw's history, the first wish
- Chapter 2: Correctly describes Herbert's death and the £200 compensation
- Chapter 3: Correctly describes the final wishes and the horror at the door

Minor issue: Chapter 3 uses "the old man/woman" instead of canonical names.

### Pronunciation Guide: 9/10 ✓
37 entries with 92% IPA coverage (34/37).
Good entries include:
- Herbert, Morris, Meggins (character names)
- sergeant-major, fakir, rubicund (unusual terms)
- condoling, condoled (vocabulary)

3 entries missing IPA is acceptable for a short story.

### HTML Presentation: 9/10 ✓
- Navigation tabs work (Overview, Chapters, Characters, Pronunciations)
- Character profiles are well-formatted
- Information is logically organized
- No broken elements observed

---

## Current Issues (Priority Order)

### CRITICAL

1. **FALSE SPLIT: "the old man" extracted separately from "Mr. White"**
   - **Problem:** Same person listed as two separate characters
   - **Evidence:**
     - "the old man" (main_cast_5) has 26 mentions
     - "Mr. White" (main_cast_0) has 10 mentions
     - Profile relationship: `"Mr. White": "self"` - the system KNOWS they're the same!
     - Both have `distinguishing_features: ["thin grey beard"]`
   - **Location:** `src/pipeline/character_extraction_v2/main_cast.py` - Pass 2 alias resolution failed to merge
   - **Pipeline data:** `merge_decisions.total_merges = 0` - no merges were even attempted
   - **Fix:** Improve alias resolution to recognize descriptive references ("the old man") should merge with proper names when relationship says "self"

2. **FALSE MERGE: "the old woman" incorrectly aliased to "the old man"**
   - **Problem:** Mrs. White is aliased to Mr. White
   - **Evidence:**
     - "the old man" aliases: `["the old woman"]` - WRONG!
     - Text shows: "said the old woman" (Mrs. White) vs "said the old man" (Mr. White)
     - Line 362: `"Oh, thank God!" said the old woman` - clearly Mrs. White
     - Line 244: `"I wish for two hundred pounds," said the old man` - clearly Mr. White
   - **Location:** `src/pipeline/character_extraction_v2/main_cast.py` - Pass 2 alias resolution
   - **Fix:** When aliasing descriptive gendered terms, respect gender markers (man ≠ woman)

### HIGH

3. **Chapter characters_present uses wrong names in Chapter 3**
   - **Problem:** `characters_present: ["the old man", "the old woman"]` should use canonical names
   - **Evidence:** Chapter 1 correctly uses `["Mr. White", "Mrs. White", "Herbert White", "Sergeant-Major Morris"]`
   - **Location:** `src/pipeline/chapter_summary/summarizer.py` or post-processing
   - **Fix:** Post-process characters_present to resolve to canonical names

### MEDIUM

4. **Sergeant-Major rank not in alias**
   - **Problem:** Character is "Morris" but text often uses "Sergeant-Major Morris"
   - **Evidence:** Structure chapter 1 shows "Sergeant-Major Morris" but character is just "Morris"
   - **Location:** `src/pipeline/character_extraction_v2/supporting.py`
   - **Fix:** Include military rank in canonical name or as alias

---

## Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | Initial analysis | - | Score 7.90, Character Extraction 6/10 |
| 2 | Re-analysis (fresh) | - | Score 7.65, Character Extraction 5/10 (regression - same issues persist) |

**Pattern detected:** The core issue is in Pass 2 alias resolution in main_cast.py. The system:
1. Correctly extracts both "the old man" and "Mr. White"
2. Correctly identifies their relationship as "self"
3. FAILS to merge them
4. INCORRECTLY merges "the old woman" into "the old man" (gender mismatch ignored)

---

## Root Cause Analysis

The character extraction pipeline has two distinct failures:

### Failure 1: Descriptive-to-Proper-Name Merge
When a descriptive reference like "the old man" should merge with a proper name like "Mr. White":
- The profile correctly identifies `"Mr. White": "self"` relationship
- But no merge is triggered
- **Root cause:** The alias resolution only looks for name patterns (FirstName-LastName, nicknames), not for "self" relationships in profiles

### Failure 2: Gender-Blind Alias Grouping
When "the old woman" is aliased to "the old man":
- The system sees both are descriptive references to elderly people
- It ignores the gender markers ("man" vs "woman")
- **Root cause:** Alias matching doesn't account for gendered descriptors

---

## Suggested Fixes

### Fix for Issue #1 (Critical - FALSE SPLIT)
In `src/pipeline/character_extraction_v2/main_cast.py` or `src/agents/characters.py`:

After profile extraction, if any character's relationships contains `"X": "self"`, automatically merge that character into X:
```python
# Pseudo-code
for character in characters:
    for rel_name, rel_type in character.relationships.items():
        if rel_type.lower() == "self":
            # This character should be merged into rel_name
            merge_character(character, find_by_name(rel_name))
```

### Fix for Issue #2 (Critical - FALSE MERGE)
In `src/pipeline/character_extraction_v2/main_cast.py`:

Add gender-awareness to alias resolution:
```python
# Don't alias gendered descriptors of opposite genders
if is_gendered_descriptor(alias1) and is_gendered_descriptor(alias2):
    if get_gender(alias1) != get_gender(alias2):
        return False  # Don't merge "the old man" with "the old woman"
```

---

## Next Action
Run PROMPT_fix.md to address the two CRITICAL character extraction issues.
