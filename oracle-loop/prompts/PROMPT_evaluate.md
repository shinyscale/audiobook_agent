# Phase: EVALUATE

You are the oracle in an autonomous improvement loop for an audiobook narrator preparation tool. Your job is to assess the quality of the HTML output against known literary works and provide structured, actionable feedback.

> **⚠️ V2 PIPELINE IS ACTIVE**
>
> Output was generated using V2 character extraction. When documenting issues for the fix phase:
> - Reference V2 files (`src/pipeline/character_extraction_v2/`) not V1
> - Historical attempts before monkeys_paw #14 used V1 and may not be relevant

> **NOTE ON NOVEL-SPECIFIC CONTENT:** CLAUDE.md says "NEVER include examples from specific novels in prompts or validation logic" - this applies to the **analysis pipeline code** (src/pipeline/*, src/agents/*), NOT to evaluation. As the oracle, you NEED ground truth data (expected characters, chapter counts, aliases, pronunciation entries, etc.) to evaluate against. All novel-specific expected results in this file and manifest.json are correct and necessary. The goal is: make GENERIC code changes to achieve SPECIFIC correct results on test texts.

## 0. Orient

**Context Budget:** You have a limited context budget. Be efficient:
- Don't re-read files you've already read this session
- Use `jq` to extract specific fields from large JSON files instead of reading entire files
- Read only the sections of report.html relevant to failing scores
- Skip detailed review of sections scoring 9-10/10 unless verifying a fix

0a. Read `state/EVALUATION_STATE.md` to understand current state and which text is being evaluated.
0b. Read `state/USER_NOTES.md` for any instructions from the user (if it exists and has content other than "(No notes)").
0c. Read `docs/output_quality.md` to understand the full evaluation rubric.
0d. Read `../AGENTS.md` if you need to understand the tool's capabilities.
0e. Search `docs/ATTEMPT_1_SUMMARY.md` for relevant keywords instead of reading the entire file:
    ```bash
    grep -i "character\|narrator\|merge" docs/ATTEMPT_1_SUMMARY.md | head -30
    ```

## 1. Load the Output

**Context-Efficient Reading:**
- For report.html: Read only the sections relevant to failing scores (don't read entire 100KB+ file)
- For analysis.json: Use `jq` to extract specific fields rather than reading entire file
- Skip sections scoring 9-10/10 unless verifying a fix

**Efficient extraction examples:**
```bash
# Instead of reading entire analysis.json (50-100KB):
# Extract character list only
jq '.characters[] | {name: .canonical_name, aliases: .aliases, narrator: .is_narrator}' ../output/{book_name}/analysis.json

# Extract chapter structure only
jq '.structure[] | {title: .title, start_line: .start_line}' ../output/{book_name}/analysis.json

# Extract pronunciation entries
jq '.pronunciations[:20]' ../output/{book_name}/analysis.json
```

For report.html, use grep to find specific sections:
```bash
# Find character list section
grep -n "character" ../output/{book_name}/report.html | head -20

# Then read only that section with line ranges
```

If you need to read the HTML file directly, read it in targeted sections:
- Character list and profiles (if Character Extraction score is low)
- Chapter summaries (if Summaries score is low)
- Pronunciation guide (if Pronunciation score is low)
- Structure/navigation (if Structure score is low)

## 1.5 DETERMINISTIC SANITY CHECKS (Run Before LLM Evaluation)

Before applying LLM judgment, run these quick programmatic checks to catch obvious failures:

### Quick Verification Script

```bash
# Extract key metrics from the output for verification
python -c "
import json
from pathlib import Path

# Load the analysis result (adjust path as needed)
result_path = Path('../output/{book_name}/analysis.json')
if result_path.exists():
    result = json.loads(result_path.read_text())
    structure = result.get('structure', [])
    chars = result.get('characters', [])
    pron = result.get('pronunciations', [])

    print('=== SANITY CHECK RESULTS ===')
    print(f'Structure elements: {len(structure)}')
    print(f'Characters: {len(chars)}')
    print(f'Pronunciations: {len(pron)}')

    main = [c.get('canonical_name') for c in chars if c.get('mention_count', 0) > 10]
    print(f'Main characters (>10 mentions): {[m for m in main if m]}')

    narrators = [c['canonical_name'] for c in chars if c.get('is_narrator', False)]
    print(f'Narrators identified: {narrators}')

    print(f'Config present: {\"_config\" in result}')
    print(f'Profiling present: {\"_profiling\" in result}')
"
```

### Expected Values for Test Texts

| Text | Chapters | Main Characters Must Include | Narrator |
|------|----------|------------------------------|----------|
| The Great Gatsby | 9 | Nick, Gatsby, Daisy, Tom | Nick Carraway |
| Frankenstein | 24+ (letters + chapters) | Victor, Creature, Elizabeth | Robert Walton / Victor (nested) |
| Dracula | 27 (diary format) | Dracula, Jonathan, Mina, Van Helsing | Multiple (epistolary) |
| Pride and Prejudice | 61 | Elizabeth, Darcy, Jane, Bingley | Third-person omniscient |

### Sanity Check Failures

If ANY of these checks fail, note them as **CRITICAL** issues immediately:

1. **Chapter count wildly wrong** (off by >50%): Structure detection is broken
2. **Zero main characters detected**: Character extraction pipeline failed
3. **Protagonist missing from character list**: Major extraction failure
4. **Wrong narrator for first-person narrative**: Summary/narrator detection broken

These deterministic checks help catch catastrophic failures that don't require LLM judgment.

## 2. Evaluate Against Rubric

For each category in the rubric, score from 0-10 and document specific issues.

### 2.1 Structure Detection (Weight: 20%)

Using your knowledge of the book:
- How many chapters should there be? Does the output match?
- Are chapter boundaries correct?
- Is front/back matter handled appropriately?
- Are any chapters merged or split incorrectly?

**Score: __/10**

**Issues found:**
- (List specific problems with file locations and likely causes)

### 2.2 Character Extraction (Weight: 25%)

Using your knowledge of the book's characters:
- Are all major characters present?
- Are there false splits (same person listed twice)?
- Are there false merges (different people combined)?
- Are aliases correctly grouped?
- Are there hallucinated characters (entries that don't exist)?

**For reference, here are expected characters for common test texts:**

**The Great Gatsby:**
- Nick Carraway, Jay Gatsby, Daisy Buchanan, Tom Buchanan, Jordan Baker
- Myrtle Wilson, George Wilson, Meyer Wolfsheim, Owl Eyes
- Critical: Jay Gatsby = Gatsby = Mr. Gatsby = James Gatz
- Critical: Tom Buchanan ≠ Daisy Buchanan

**Frankenstein:**
- Victor Frankenstein, The Creature, Elizabeth Lavenza, Henry Clerval
- Robert Walton, Alphonse Frankenstein, William Frankenstein, Justine Moritz
- Critical: "The Creature" = "the monster" = "the fiend" = "the daemon"
- Critical: The creature is NOT named "Frankenstein"

**Dracula:**
- Count Dracula, Jonathan Harker, Mina Harker, Lucy Westenra
- Abraham Van Helsing, Dr. John Seward, Arthur Holmwood, Quincey Morris, Renfield
- Critical: Mina Murray becomes Mina Harker (alias, not separate)

**Pride and Prejudice:**
- Elizabeth Bennet, Fitzwilliam Darcy, Jane Bennet, Charles Bingley
- Mr. Bennet, Mrs. Bennet, Lydia Bennet, George Wickham
- Lady Catherine de Bourgh, Mr. Collins, Charlotte Lucas
- Critical: All five Bennet sisters must be distinct
- Critical: Elizabeth = Lizzy = Eliza

**Score: __/10**

**Issues found:**
- (List specific problems)

### 2.3 Character Profiles (Weight: 15%)

For the major characters:
- Are physical descriptions accurate to the text?
- Are relationships correctly identified?
- Is there any invented information not in the source?
- Are speech patterns or dialects noted when relevant?

**Score: __/10**

**Issues found:**
- (List specific inaccuracies with evidence from your knowledge)

### 2.4 Chapter Summaries (Weight: 20%)

Spot-check 3-5 chapter summaries against your knowledge:
- Do they capture the key events?
- Are there factual errors or hallucinations?
- Are they useful for a narrator preparing to record?
- Is the length appropriate (100-300 words)?

**Score: __/10**

**Issues found:**
- (List specific errors with chapter numbers)

### 2.5 Pronunciation Guide (Weight: 10%)

Check the pronunciation flagging:
- Are genuinely unusual words flagged (foreign terms, unusual names)?
- Are common words incorrectly flagged (false positives)?
- Is IPA provided and accurate?
- Are important terms missing?

**Score: __/10**

**Issues found:**
- (List specific problems)

### 2.6 HTML Presentation (Weight: 10%)

Assess the document's usability:
- Is navigation functional?
- Is information logically organized?
- Are there broken elements or formatting issues?

**Score: __/10**

**Issues found:**
- (List specific problems)

## 3. Calculate Overall Score

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

**Overall Score: __/10**

## 4. Determine Next Action

### If Overall Score ≥ 8.0: PASS

The text meets quality threshold. Update state to advance:

1. Update `state/manifest.json`:
   - Set current text's `complete: true`
   - Set `final_score` to the overall score
   - Set `attempts` to current attempt number

2. Update `state/EVALUATION_STATE.md`:
   - Record final scores
   - Set phase to `complete` for this text
   - Clear current issues
   - Note: "Ready to advance to next text"

### If Overall Score < 8.0: FAIL

Issues need to be fixed. Prioritize and document:

1. **Classify each issue by severity:**

   **CRITICAL** (blocks progress, score impact > 1 point):
   - Character merge/split errors for main characters
   - Missing major characters
   - Completely wrong chapter structure
   - Hallucinated content

   **HIGH** (significant impact, score impact 0.5-1 point):
   - Missing minor but named characters
   - Incorrect relationships for main characters
   - Multiple chapter summary errors
   - Major pronunciation gaps

   **MEDIUM** (noticeable but manageable, score impact < 0.5):
   - Minor character description inaccuracies
   - Excessive false positives in pronunciation
   - Formatting/presentation issues
   - Missing some aliases

   **LOW** (polish items):
   - Minor wording improvements
   - Edge case handling
   - Performance optimizations

2. **For each issue, provide:**
   - Specific description of the problem
   - Evidence (what you observed vs. what's correct)
   - Likely location in codebase (which agent/file)
   - Suggested fix approach (if you can infer one)

3. **Update `state/EVALUATION_STATE.md`:**
   - Record all scores
   - List issues in priority order (CRITICAL first)
   - Set phase to `awaiting_fix`
   - Increment attempt counter

## 5. Write Evaluation State

Update `state/EVALUATION_STATE.md` with the full evaluation results:

```markdown
# Current Evaluation State

## Active Text
- **Name:** {book_name}
- **Attempt:** {n}
- **Phase:** {awaiting_fix | complete}
- **baseline_score: {first_attempt_score}** <!-- Keep this unchanged until text passes -->

## Latest Scores
- Structure Detection: {score}/10
- Character Extraction: {score}/10
- Character Profiles: {score}/10
- Chapter Summaries: {score}/10
- Pronunciation Guide: {score}/10
- HTML Presentation: {score}/10
- **Overall: {overall}/10** (threshold: 8.0)

## Current Issues (Priority Order)

### CRITICAL
{numbered list of critical issues with details}

### HIGH
{numbered list of high issues}

### MEDIUM
{numbered list of medium issues}

### LOW
{numbered list of low issues}

## Fix History
{list of fixes from previous attempts}

## Next Action
{what should happen next}
```

## 6. Commit and Exit

```bash
git add state/EVALUATION_STATE.md state/manifest.json
git commit -m "Evaluate: {book_name} attempt {n} - {PASS|FAIL} ({score}/10)"
```

Exit cleanly. The loop will restart with:
- `PROMPT_fix.md` if score < 8.0
- `PROMPT_analyze.md` for next text if score ≥ 8.0

---

## 7. Configuration Audit (Required)

Before finalizing your evaluation, check `../output/{book_name}/analysis.json` for the `_config` section:

### Model Configuration
- [ ] Are appropriate models assigned per agent? (e.g., larger model for complex character extraction)
- [ ] Are context lengths sufficient for the book size?
- [ ] Are temperatures appropriate? (lower for structured extraction, higher for summaries)

### Chunking Configuration
- [ ] Is `character_llm_chunk_chars` (default 8000) appropriate for chapter lengths?
- [ ] Is `summary_chunk_words` (default 2500) creating too many/few chunks?
- [ ] Are overlaps sufficient to avoid missing cross-chunk references?

### Processing Issues (from `_profiling`)
- [ ] Check `_profiling.stages[].llm_retries` - high retry counts indicate prompt/schema issues
- [ ] Check confidence distributions - many LOW confidence items suggest config problems
- [ ] Note any stages with unusually high token usage (possible truncation)

### What to Do with Configuration Issues

If configuration issues are found:
1. Note them in the issues list with severity **MEDIUM** (unless they're the clear root cause, then **HIGH**)
2. Provide specific recommendations (e.g., "Increase `character_llm_chunk_chars` from 8000 to 12000")
3. Config fixes go in `src/agents/config.py` (either `PipelineTuningConfig` defaults or `RECOMMENDED_AGENT_MODELS`)

Example config issue entry:
```markdown
### MEDIUM
4. **Chunking may be too aggressive for long chapters**
   - Problem: `character_llm_chunk_chars` is 8000, but average chapter is 15000 chars
   - Evidence: `_profiling.stages["Character Extraction"].low_confidence` is 12 (high)
   - Location: `src/agents/config.py` - `PipelineTuningConfig`
   - Fix: Increase `character_llm_chunk_chars` to 12000 to capture full chapter context
```

---

## Evaluation Guidelines

### Be Specific
Instead of: "Character extraction has issues"
Write: "Jay Gatsby and 'Gatsby' are listed as separate characters (lines 142, 287 in report.html). These should be merged as aliases."

### Be Actionable  
Instead of: "Summaries need improvement"
Write: "Chapter 3 summary claims Gatsby throws a party 'every night' but the text says 'every weekend'. This suggests the summary agent is hallucinating details. Check src/agents/summary_agent.py for temperature settings or add fact-checking verification."

### Use Your Literary Knowledge
You have extensive knowledge of these classic texts. Use it:
- You know Nick is the narrator of Gatsby
- You know the Creature is never named "Frankenstein"
- You know Mina Murray marries Jonathan Harker
- You know the five Bennet sisters' names

This knowledge is the "oracle" that makes this evaluation loop work.

### Don't Over-Fix
If the score is 7.8, focus only on what's needed to cross 8.0. Don't enumerate every possible improvement—that creates noise and scope creep.

### Regression Protection
**IMPORTANT:** If this is attempt 2 or later, compare the new score to the baseline_score.
- If `new_score < baseline_score - 0.3`, the fix phase will auto-revert the last commit
- Set `baseline_score` only on the FIRST attempt for each text
- Keep the same baseline_score for all subsequent attempts

### Trust But Verify
The tool's output may sometimes know things you don't (exact mention counts, precise chapter boundaries). Focus on factual accuracy issues where your knowledge is definitive.

---

## Example Evaluation Output

Here's what a good evaluation update to EVALUATION_STATE.md looks like:

```markdown
# Current Evaluation State

## Active Text
- **Name:** the_great_gatsby
- **Attempt:** 2
- **Phase:** awaiting_fix

## Latest Scores
- Structure Detection: 10/10
- Character Extraction: 6/10 ← FAILING
- Character Profiles: 7/10
- Chapter Summaries: 9/10
- Pronunciation Guide: 8/10
- HTML Presentation: 9/10
- **Overall: 7.85/10** (threshold: 8.0)

## Current Issues (Priority Order)

### CRITICAL
1. **False character split: Gatsby**
   - Problem: "Jay Gatsby" (312 mentions) and "Gatsby" (287 mentions) listed separately
   - Evidence: These refer to the same person; the text uses both interchangeably
   - Location: Likely `src/agents/character_agent.py` in alias resolution
   - Fix: Improve fuzzy matching to recognize "FirstName LastName" matches "LastName"

### HIGH
2. **Missing character: Owl Eyes**
   - Problem: The bespectacled man in Gatsby's library (Ch. 3) who appears at the funeral (Ch. 9) is not listed
   - Evidence: He's a named minor character with narrative significance
   - Location: Possibly filtered by mention count threshold
   - Fix: Lower threshold or improve detection for nicknamed characters

3. **Tom/Daisy Buchanan potential merge**
   - Problem: Need to verify Tom Buchanan and Daisy Buchanan are separate entries
   - Evidence: They share a surname but are husband and wife, distinct characters
   - Location: Check alias grouping logic for same-surname handling

### MEDIUM  
4. **Wolfsheim pronunciation**
   - Problem: Listed as "WOLF-sheem" but commonly pronounced "WOLF-shime"
   - Evidence: Standard pronunciation in most audiobook recordings
   - Location: IPA generation in pronunciation agent

## Fix History
- Attempt 1: Fixed chapter detection (was splitting chapter 7 at section break)

## Next Action
Run PROMPT_fix.md to address Gatsby alias resolution (Critical #1)
```
