# Oracle Loop Attempt 3 Summary (Attempts 3-7)

**Purpose:** Document findings from attempts 3-7 on "The Cask of Amontillado" and why the oracle loop approach isn't working.

---

## Executive Summary

| Metric | Value |
|--------|-------|
| **Date Range** | January 18, 2026 |
| **Iterations** | 13+ |
| **Text** | cask_of_amontillado |
| **Attempts** | 3-7 |
| **Starting Score** | 6.45/10 (baseline from attempt 1) |
| **Ending Score** | 5.95/10 (regression) |
| **Result** | FAILED - Score went DOWN |

### Key Finding

The oracle loop is **fixing the wrong problems**. It keeps modifying the character extraction validator while the actual issues are:

1. **Narrator detection algorithm** - Fundamentally flawed logic
2. **Plot summary generator** - Uses highest-mention character as "main character"
3. **Cascading failures** - Wrong character → wrong narrator → wrong plot summary

---

## What Happened

### Attempt 3: Person-Action Heuristic
**Fix:** Added heuristic to reject entities that have many mentions but never perform person-like actions (said, walked, laughed, etc.)

**Commit:** `8aebebc`

**Smoke test:** PASS - The heuristic correctly identified "Amontillado" as not performing person actions.

**Full pipeline:** FAIL - "Amontillado" still appeared as a character in the final output.

**Why it failed:** The smoke test tested the heuristic in isolation, but the full pipeline has multiple character sources and the heuristic may not be the only path through validation.

### Attempts 4-5: JSON Format Fixes
**Problem:** LLM validation was returning empty arrays `[]` instead of JSON objects.

**Fix:** Added explicit prompt instructions ("return a JSON object, not an array") and array unwrapping logic.

**Commit:** `0018fab`

**Result:** Fixed the pipeline crash but didn't improve output quality.

### Attempts 6-7: Re-running Analysis
Multiple analysis runs with the fixes in place. Score remained at 5.95/10 (regression from baseline).

---

## Root Cause Analysis

### The Real Problem: Not the Validator

Through manual investigation (not done by the oracle loop), we discovered:

#### 1. Narrator Detection Algorithm is Flawed

Location: `src/analyzer.py:_detect_narrator()` (lines 1746-1835)

The algorithm:
```python
# For each character, count first-person pronouns ("I", "my") in
# the context window (±200 chars) around their mentions
for char in characters:
    for mention in char.mentions:
        context = full_text[mention.position-200 : mention.position+200]
        pronoun_count += context.count("I ") + context.count(" my ")
    density = pronoun_count / total_context_length

# Character with highest pronoun density = narrator
narrator = max(characters, key=lambda c: pronoun_density[c])
```

**The bug:** This measures pronouns AROUND mentions, not who the pronouns REFER TO.

In "The Cask of Amontillado", Montresor (the actual narrator) says "I" constantly while talking about the wine. So contexts around "Amontillado" mentions have HIGH first-person pronoun density - because the narrator is discussing the wine!

Example:
> "**I** have received a pipe of what passes for Amontillado, and **I** have **my** doubts"

The algorithm sees "Amontillado has lots of 'I' around it" and concludes "Amontillado is the narrator."

#### 2. Plot Summary Generator Uses Wrong Signal

Location: `src/pipeline/overview/generator.py` (lines 201-215)

```python
# Sort by mention count (descending) and take top 3
sorted_chars = sorted(
    result.characters,
    key=lambda c: c.mention_count,
    reverse=True
)[:3]
main_characters = "MAIN CHARACTERS (use these names):\n" + ...
```

So the LLM prompt receives:
```
MAIN CHARACTERS (use these names, do NOT invent others):
- Amontillado: 16 mentions
- Fortunato: 14 mentions
- Montresor: 1 mention
```

The LLM writes: "Amontillado recounts the chilling tale..."

#### 3. The Cascade

1. Character extraction passes "Amontillado" (16 mentions) ← First error
2. Narrator detection picks "Amontillado" (high pronoun density) ← Second error
3. Plot summary says "Amontillado recounts..." ← Third error
4. Profile stage assigns narrator description to "Amontillado" ← Fourth error

---

## Why the Oracle Loop Didn't Find This

### What the Oracle Loop Did
1. Read EVALUATION_STATE.md: "Amontillado wrongly identified as character"
2. Concluded: "The validator must be broken"
3. Made code changes to the validator
4. Re-ran analysis
5. Still failed → Made more validator changes

### What Manual Investigation Did
1. Looked at the actual output JSON
2. Noticed: Chapter summary says "Montresor" but plot summary says "Amontillado"
3. Asked: "Where does the plot summary get its character list?"
4. Found the sorting by mention_count in generator.py
5. Asked: "Why does narrator detection pick Amontillado?"
6. Found the pronoun density algorithm bug

### The Difference

**Oracle loop approach:**
- Symptom-focused: "Amontillado is in the output"
- Single-hypothesis: "The validator must be the problem"
- No data tracing: Doesn't examine intermediate pipeline values

**Manual investigation approach:**
- Data-focused: "What's in the JSON? Where did it come from?"
- Multiple hypotheses: Check validator, narrator detection, plot summary
- Traces full data flow: Found the cascade of errors

---

## Fixes That Were Tried (and Why They Failed)

| Attempt | Fix | Commit | Result | Why It Failed |
|---------|-----|--------|--------|---------------|
| 3 | Person-action heuristic | `8aebebc` | No impact | Correct fix, wrong problem location |
| 4-5 | JSON format handling | `0018fab` | Fixed crash | Symptom fix, not root cause |
| 6-7 | Re-run analysis | - | No change | Same bugs, same results |

---

## Actual Fixes Needed

### Priority 1: Fix Narrator Detection
The algorithm should identify WHO the first-person pronouns refer to, not just count them around entity mentions.

Options:
- Look for direct address patterns: "For the love of God, Montresor!" → Montresor is being addressed as "I"
- Look for narrator-specific patterns: "I vowed revenge" → The "I" IS a character
- Use LLM to determine: "Who is speaking in first person in this text?"

### Priority 2: Fix Plot Summary Character Selection
Don't just use highest mention count. Consider:
- Narrator should be weighted highly
- Objects (wines, places) should be filtered
- Use the character's role/type, not just mention count

### Priority 3: The Validator Heuristic
The person-action heuristic IS correct and should be kept, but it's not sufficient alone when other parts of the pipeline are broken.

---

## Lessons Learned

### 1. Symptom ≠ Root Cause
"Amontillado is wrongly identified as a character" is a symptom with multiple possible causes:
- Validator passing it (partial cause)
- Narrator detection selecting it (major cause)
- Plot summary using highest mentions (contributing cause)

### 2. Smoke Tests Can Pass While Full Pipeline Fails
The person-action heuristic passed its smoke test but didn't fix the full pipeline issue because there are multiple paths through the system.

### 3. The Oracle Loop Needs Better Investigation
PROMPT_fix.md says "investigate" but doesn't enforce:
- Tracing actual data values through the pipeline
- Testing intermediate stages
- Verifying assumptions with real inputs

### 4. Cascading Failures Require System-Level Thinking
Fixing one component (validator) doesn't help when downstream components (narrator detection, plot summary) are also broken.

---

## Recommended Changes to Oracle Loop Design

### 1. Require Data Tracing
Before making any fix, the fix phase must:
```
- Read the actual output JSON
- Identify WHERE incorrect data first appears
- Trace backward to find the source
- Test the specific component in isolation
```

### 2. Test Intermediate Stages
Don't just test the final output. Verify:
- Character extraction output (before narrator detection)
- Narrator detection output (before plot summary)
- Plot summary output (before profiles)

### 3. Consider Multiple Hypotheses
If "Amontillado is wrongly identified as character", check:
- [ ] Is validator passing it? (partial)
- [ ] Is narrator detection selecting it? (YES - major bug)
- [ ] Is plot summary using it incorrectly? (YES - contributing)

### 4. Fix Root Causes First
The narrator detection bug is more fundamental than the validator bug. Fixing the validator doesn't help if narrator detection still picks "Amontillado" based on pronoun density.

---

## Files to Examine

| File | Issue | Priority |
|------|-------|----------|
| `src/analyzer.py:_detect_narrator()` | Pronoun density algorithm bug | HIGH |
| `src/pipeline/overview/generator.py` | Uses mention count for "main characters" | MEDIUM |
| `src/pipeline/character_extraction/validator.py` | Person-action heuristic (correct but insufficient) | LOW |

---

## Git Reference

Commits from this attempt cycle:
```
b064266 Analysis complete: cask_of_amontillado attempt 7
4d68281 Analysis complete: cask_of_amontillado attempt 6
9aad83c Pipeline error: LLM validation empty array in attempt 5
344ca91 Analysis complete: cask_of_amontillado attempt 4
0018fab Fix: LLM validation JSON format - handle array responses
0f77da4 Pipeline error: LLM validation JSON format issue in attempt 3
8aebebc Fix: Reject non-person entities via person-action verb detection
```

Reverted to: `6ef2046` (pre-attempt-3 state)
