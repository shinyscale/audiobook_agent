# Autonomous Audiobook Analysis Improvement Loop

## Planning Document

**Purpose:** Enable Claude Code to autonomously iterate on the audiobook analysis tool, using a Ralph Wiggum-style loop that clears context between iterations while persisting state to disk.

**Goal:** Take Zach out of the loop. Feed in public domain novels, let the system iterate until output quality meets threshold, then advance to the next text—building a robust, thoroughly-vetted tool.

---

## Architecture Overview

### The Core Insight

The Ralph Wiggum technique solves context accumulation by:
1. Starting each iteration with **fresh context** (same deterministic files)
2. Persisting **shared state to disk** (progress, issues, scores)
3. Completing **one task** per iteration
4. Exiting cleanly so the bash loop can restart

For your audiobook tool, this becomes a three-phase cycle:

```
┌─────────────────────────────────────────────────────────────────┐
│                    OUTER LOOP (bash)                            │
│   for each test_text in manifest:                               │
│       while quality < threshold and attempts < max:             │
│           Phase 1: ANALYZE (run Qwen3 pipeline)                 │
│           Phase 2: EVALUATE (Claude assesses HTML output)       │
│           Phase 3: FIX (Claude modifies code/prompts)           │
│       mark text complete, advance                               │
└─────────────────────────────────────────────────────────────────┘
```

Each phase is a **separate Claude Code invocation** with fresh context.

---

## File Structure

```
audiobook_agent/
├── loop.sh                      # Outer loop orchestrator
├── PROMPT_analyze.md            # Instructions for running analysis
├── PROMPT_evaluate.md           # Instructions for evaluating output (oracle)
├── PROMPT_fix.md                # Instructions for fixing issues
├── AGENTS.md                    # How to run the tool, what commands work
├── EVALUATION_STATE.md          # Current scores, issues, iteration count
├── specs/
│   └── output_quality.md        # The rubric - what good output looks like
├── test_texts/
│   ├── manifest.json            # List of texts with completion status
│   ├── the_great_gatsby.txt
│   ├── frankenstein.txt
│   ├── dracula.txt
│   ├── pride_and_prejudice.txt
│   └── ...
├── outputs/                     # Where HTML outputs land
│   └── {book_name}/
│       └── report.html
├── src/                         # Your tool's source code
│   ├── agents/
│   ├── pipeline/
│   └── ...
└── logs/
    └── iteration_{n}.log        # Logs from each iteration
```

---

## Key Files

### `manifest.json`

Tracks which texts have been processed and their final scores:

```json
{
  "quality_threshold": 8.0,
  "max_attempts_per_text": 5,
  "texts": [
    {
      "name": "the_great_gatsby",
      "file": "test_texts/the_great_gatsby.txt",
      "complete": false,
      "attempts": 0,
      "final_score": null,
      "issues_resolved": []
    },
    {
      "name": "frankenstein",
      "file": "test_texts/frankenstein.txt",
      "complete": false,
      "attempts": 0,
      "final_score": null,
      "issues_resolved": []
    },
    {
      "name": "dracula",
      "file": "test_texts/dracula.txt",
      "complete": false,
      "attempts": 0,
      "final_score": null,
      "issues_resolved": []
    },
    {
      "name": "pride_and_prejudice",
      "file": "test_texts/pride_and_prejudice.txt",
      "complete": false,
      "attempts": 0,
      "final_score": null,
      "issues_resolved": []
    }
  ]
}
```

### `EVALUATION_STATE.md`

Persists between iterations. Updated by each phase:

```markdown
# Current Evaluation State

## Active Text
- **Name:** the_great_gatsby
- **Attempt:** 2 of 5
- **Phase:** awaiting_fix

## Latest Scores
- Structure Detection: 9/10
- Character Extraction: 6/10 ← FAILING
- Pronunciation Guide: 7/10
- Summary Quality: 8/10
- HTML Presentation: 9/10
- **Overall: 7.8/10** (threshold: 8.0)

## Current Issues (Priority Order)

### CRITICAL
1. **Character merge failure**: Jay Gatsby and "Gatsby" treated as separate characters
   - File: `src/agents/character_agent.py`
   - Likely cause: Alias resolution not handling first-name-only references
   - Suggested fix: Improve fuzzy matching threshold or add name-part matching

### HIGH
2. **Missing character**: Owl Eyes not detected (minor but named character)
   - Appears in Ch. 3 and Ch. 9
   - May need to lower mention threshold or improve NER

### MEDIUM
3. **Pronunciation false positive**: "Buchanan" flagged but is common surname
   - Consider adding common surname whitelist

## Fix History
- Attempt 1: Fixed chapter detection regex for Roman numerals
- Attempt 2: (pending)

## Next Action
Run PROMPT_fix.md to address character merge failure
```

### `AGENTS.md`

Operational guide loaded each iteration:

```markdown
# Audiobook Agent - Operational Guide

## Running the Analysis Pipeline

```bash
# Full analysis on a text file
python -m src.pipeline.run --input test_texts/the_great_gatsby.txt --output outputs/the_great_gatsby/

# Quick test (first 3 chapters only)
python -m src.pipeline.run --input test_texts/the_great_gatsby.txt --output outputs/the_great_gatsby/ --quick

# With specific models
python -m src.pipeline.run --input test_texts/the_great_gatsby.txt \
    --structure-model qwen3-30b \
    --character-model qwen3-next-80b \
    --summary-model qwen3-30b
```

## Output Location
- HTML report: `outputs/{book_name}/report.html`
- JSON data: `outputs/{book_name}/analysis.json`
- Logs: `outputs/{book_name}/pipeline.log`

## Key Source Files
- Agent base class: `src/agents/base.py`
- Structure agent: `src/agents/structure_agent.py`
- Character agent: `src/agents/character_agent.py`
- Summary agent: `src/agents/summary_agent.py`
- Pronunciation agent: `src/agents/pronunciation_agent.py`
- Pipeline orchestrator: `src/pipeline/orchestrator.py`

## Configuration
- Model settings: `src/config/models.yaml`
- Agent prompts: `src/prompts/`
- Verification thresholds: `src/config/verification.yaml`

## Common Issues & Fixes
- If Ollama connection fails: `ollama serve` must be running
- If model not found: `ollama pull qwen3:30b`
- If OOM on 80B model: Reduce batch size in `models.yaml`

## Testing
```bash
# Run all tests
pytest tests/ -v

# Run specific agent tests
pytest tests/test_character_agent.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```
```

---

## The Three Prompts

### `PROMPT_analyze.md`

Runs the local LLM pipeline on the current test text.

```markdown
# Phase: ANALYZE

You are running the audiobook analysis pipeline on a test text.

## 0. Orient

0a. Read `EVALUATION_STATE.md` to understand current state.
0b. Read `manifest.json` to identify the current active text.
0c. Read `AGENTS.md` for operational commands.

## 1. Run Analysis

If EVALUATION_STATE.md shows phase is `awaiting_analysis` or this is a fresh start:

1. Identify the current text from manifest.json (first incomplete text)
2. Run the full analysis pipeline:
   ```bash
   python -m src.pipeline.run --input {text_file} --output outputs/{book_name}/
   ```
3. Wait for completion (this may take 1-6 hours depending on text length)
4. Verify output exists: `outputs/{book_name}/report.html`

## 2. Update State

Update `EVALUATION_STATE.md`:
- Set phase to `awaiting_evaluation`
- Increment attempt counter if this is a re-run
- Note any pipeline errors or warnings

## 3. Exit

Commit changes and exit cleanly. The loop will restart with PROMPT_evaluate.md.

```bash
git add EVALUATION_STATE.md outputs/
git commit -m "Analysis complete: {book_name} attempt {n}"
```
```

### `PROMPT_evaluate.md`

See separate file: This is the oracle phase where Claude assesses output quality.

### `PROMPT_fix.md`

Addresses issues identified during evaluation.

```markdown
# Phase: FIX

You are fixing issues identified in the evaluation phase.

## 0. Orient

0a. Read `EVALUATION_STATE.md` to understand current issues.
0b. Read `specs/output_quality.md` to understand quality criteria.
0c. Read `AGENTS.md` for codebase navigation.
0d. Study `src/` with attention to files mentioned in issues.

## 1. Analyze Issues

Review the issues in EVALUATION_STATE.md, prioritized by severity:
- CRITICAL: Must fix before re-running
- HIGH: Should fix, significant impact on quality
- MEDIUM: Nice to fix, minor impact
- LOW: Can defer

## 2. Implement Fixes

For each CRITICAL and HIGH issue:

1. **Investigate first** - Search the codebase to understand the current implementation
   ```bash
   grep -r "alias" src/agents/character_agent.py
   ```

2. **Identify root cause** - Is it:
   - A prompt issue? → Edit `src/prompts/`
   - A code logic issue? → Edit `src/agents/` or `src/pipeline/`
   - A configuration issue? → Edit `src/config/`
   - A threshold issue? → Adjust verification parameters

3. **Make minimal, targeted changes** - Fix the specific issue without over-engineering

4. **Run relevant tests**
   ```bash
   pytest tests/test_character_agent.py -v
   ```

## 3. Document Changes

Update `EVALUATION_STATE.md`:
- Move fixed issues to "Fix History" with description of change
- Set phase to `awaiting_analysis`
- Note any concerns about the fix

## 4. Commit and Exit

```bash
git add -A
git commit -m "Fix: {brief description of primary fix}"
```

The loop will restart with PROMPT_analyze.md to re-run the pipeline.

## Guidelines

- **One issue at a time**: Fix the most critical issue, then re-run. Don't batch fixes.
- **Preserve working behavior**: Run tests before and after changes.
- **Document the why**: Future iterations depend on understanding what was tried.
- **If stuck**: Document the blocker in EVALUATION_STATE.md and move on.
```

---

## The Loop Script

### `loop.sh`

```bash
#!/bin/bash
set -euo pipefail

# Audiobook Analysis Improvement Loop
# Usage: ./loop.sh [phase] [max_iterations]
# Examples:
#   ./loop.sh                    # Auto-detect phase, run until complete
#   ./loop.sh analyze            # Force analyze phase
#   ./loop.sh evaluate           # Force evaluate phase  
#   ./loop.sh fix                # Force fix phase
#   ./loop.sh full 50            # Run full cycle, max 50 iterations total

PHASE="${1:-auto}"
MAX_ITERATIONS="${2:-100}"
ITERATION=0

# Quality threshold from manifest
THRESHOLD=$(jq -r '.quality_threshold' manifest.json)
MAX_ATTEMPTS=$(jq -r '.max_attempts_per_text' manifest.json)

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Audiobook Analysis Improvement Loop"
echo "Quality Threshold: $THRESHOLD"
echo "Max Attempts per Text: $MAX_ATTEMPTS"
echo "Max Total Iterations: $MAX_ITERATIONS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Determine which prompt to use
get_prompt_file() {
    if [ "$PHASE" != "auto" ]; then
        echo "PROMPT_${PHASE}.md"
        return
    fi
    
    # Auto-detect from EVALUATION_STATE.md
    if [ ! -f "EVALUATION_STATE.md" ]; then
        echo "PROMPT_analyze.md"
        return
    fi
    
    local current_phase=$(grep -oP '(?<=Phase:\*\* )\w+' EVALUATION_STATE.md 2>/dev/null || echo "analyze")
    
    case "$current_phase" in
        awaiting_analysis|analyze)
            echo "PROMPT_analyze.md"
            ;;
        awaiting_evaluation|evaluate)
            echo "PROMPT_evaluate.md"
            ;;
        awaiting_fix|fix)
            echo "PROMPT_fix.md"
            ;;
        complete)
            # Check if there are more texts
            local incomplete=$(jq '[.texts[] | select(.complete == false)] | length' manifest.json)
            if [ "$incomplete" -eq 0 ]; then
                echo "ALL_COMPLETE"
            else
                echo "PROMPT_analyze.md"
            fi
            ;;
        *)
            echo "PROMPT_analyze.md"
            ;;
    esac
}

# Check if all texts are complete
all_complete() {
    local incomplete=$(jq '[.texts[] | select(.complete == false)] | length' manifest.json)
    [ "$incomplete" -eq 0 ]
}

# Main loop
while [ $ITERATION -lt $MAX_ITERATIONS ]; do
    PROMPT_FILE=$(get_prompt_file)
    
    if [ "$PROMPT_FILE" = "ALL_COMPLETE" ]; then
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "✅ ALL TEXTS COMPLETE"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        jq '.texts[] | "\(.name): \(.final_score)/10 in \(.attempts) attempts"' manifest.json
        break
    fi
    
    if [ ! -f "$PROMPT_FILE" ]; then
        echo "Error: $PROMPT_FILE not found"
        exit 1
    fi
    
    ITERATION=$((ITERATION + 1))
    echo ""
    echo "======================== ITERATION $ITERATION ========================"
    echo "Prompt: $PROMPT_FILE"
    echo "Time: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""
    
    # Run Claude Code with the appropriate prompt
    # Using claude CLI in headless mode
    cat "$PROMPT_FILE" | claude -p \
        --dangerously-skip-permissions \
        --output-format=stream-json \
        --model sonnet \
        --verbose \
        2>&1 | tee "logs/iteration_${ITERATION}.log"
    
    # Brief pause between iterations
    sleep 5
done

if [ $ITERATION -ge $MAX_ITERATIONS ]; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "⚠️  MAX ITERATIONS REACHED: $MAX_ITERATIONS"
    echo "Review logs/ and EVALUATION_STATE.md for status"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
fi
```

---

## Quality Rubric

### `specs/output_quality.md`

```markdown
# Audiobook Prep Output Quality Rubric

This rubric defines what "good" output looks like for an audiobook narrator's prep document.

## Evaluation Categories

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

**Specific checks:**
- [ ] All chapters detected (compare to known chapter count)
- [ ] Chapter titles extracted correctly
- [ ] Front matter (dedication, preface) identified separately
- [ ] Back matter (notes, appendices) identified separately
- [ ] No merged chapters (two chapters treated as one)
- [ ] No split chapters (one chapter treated as multiple)
- [ ] Roman numerals handled correctly
- [ ] "Chapter" vs "Book" vs "Part" hierarchy correct

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

**Specific checks:**
- [ ] All major characters (>10 mentions) identified
- [ ] No false character splits (same person as two entries)
- [ ] No false character merges (two people as one entry)
- [ ] Aliases correctly grouped (e.g., "Jay Gatsby" = "Gatsby" = "Mr. Gatsby")
- [ ] Titles handled correctly (Dr., Mr., Mrs., etc.)
- [ ] Nicknames linked to canonical names
- [ ] No hallucinated characters (entries that don't exist in text)
- [ ] First appearance chapter is accurate

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

**Specific checks:**
- [ ] Physical descriptions match text (when provided)
- [ ] Personality traits supported by text evidence
- [ ] Key relationships identified (family, romantic, professional)
- [ ] No invented details (information not in the source text)
- [ ] Speech patterns or dialect noted (when present)
- [ ] Character arc summary useful for narrator

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

**Specific checks:**
- [ ] Key plot events captured (3-5 per chapter)
- [ ] Characters appearing in chapter mentioned
- [ ] No hallucinated events (things that didn't happen)
- [ ] No major spoilers from future chapters
- [ ] Tone and mood indicated (useful for narrator)
- [ ] Length appropriate (100-300 words)
- [ ] Setting/location changes noted

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

**Specific checks:**
- [ ] Foreign words/phrases identified
- [ ] Unusual proper nouns flagged (names, places)
- [ ] Period-specific terms noted
- [ ] IPA provided and accurate (when present)
- [ ] No common words flagged (false positives)
- [ ] Context provided for homographs (read vs. read)
- [ ] Regional/dialect pronunciations noted

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

**Specific checks:**
- [ ] Navigation works (can jump to chapters, characters)
- [ ] Typography is readable
- [ ] Information is logically organized
- [ ] No broken elements or missing sections
- [ ] Prints cleanly (if applicable)
- [ ] Mobile-friendly (if applicable)

---

## Scoring Calculation

```
Overall Score = (
    Structure × 0.20 +
    Characters × 0.25 +
    Profiles × 0.15 +
    Summaries × 0.20 +
    Pronunciation × 0.10 +
    Presentation × 0.10
)
```

**Thresholds:**
- **≥ 8.0**: Pass - advance to next text
- **< 8.0**: Fail - iterate with fixes

---

## Book-Specific Ground Truth

### The Great Gatsby

**Structure:** 9 chapters, no parts or subdivisions
**Major Characters (must identify all):**
- Nick Carraway (narrator)
- Jay Gatsby
- Daisy Buchanan
- Tom Buchanan
- Jordan Baker
- Myrtle Wilson
- George Wilson
- Meyer Wolfsheim

**Critical Aliases:**
- Jay Gatsby = Gatsby = Mr. Gatsby = James Gatz
- Tom Buchanan ≠ Daisy Buchanan (different people, same surname)

**Pronunciation Flags Expected:**
- Wolfsheim (WOLF-shime, not WOLF-sheem)
- Louisville (narrator mentions Daisy's hometown)
- Various jazz-age slang

### Frankenstein

**Structure:** Letters + 24 chapters, frame narrative
**Major Characters:**
- Victor Frankenstein
- The Creature (aliases: monster, fiend, daemon, wretch)
- Elizabeth Lavenza
- Henry Clerval
- Robert Walton
- Alphonse Frankenstein
- William Frankenstein
- Justine Moritz

**Critical Note:** The Creature is never named "Frankenstein" - that's Victor's surname

**Pronunciation Flags Expected:**
- Ingolstadt
- Geneva locations
- Various German/Swiss proper nouns

### Dracula

**Structure:** Chapters with dated journal entries, epistolary format
**Major Characters:**
- Count Dracula
- Jonathan Harker
- Mina Harker (née Murray)
- Lucy Westenra
- Abraham Van Helsing
- Dr. John Seward
- Arthur Holmwood (Lord Godalming)
- Quincey Morris
- Renfield

**Pronunciation Flags Expected:**
- Transylvanian place names
- Romanian/Hungarian terms
- "Nosferatu", "Szgany", etc.

### Pride and Prejudice

**Structure:** 61 chapters in 3 volumes
**Major Characters:**
- Elizabeth Bennet (Lizzy)
- Fitzwilliam Darcy (Mr. Darcy)
- Jane Bennet
- Charles Bingley
- Mr. Bennet
- Mrs. Bennet
- Lydia Bennet
- George Wickham
- Lady Catherine de Bourgh
- Mr. Collins

**Critical Aliases:**
- All five Bennet sisters must be distinct
- Elizabeth = Lizzy = Eliza
- Fitzwilliam Darcy = Mr. Darcy (not to be confused with Colonel Fitzwilliam)
```

---

## Running the Loop

### Initial Setup

1. **Prepare test texts:**
   ```bash
   mkdir -p test_texts outputs logs
   # Download public domain texts from Project Gutenberg
   curl -o test_texts/the_great_gatsby.txt "https://..."
   curl -o test_texts/frankenstein.txt "https://..."
   # etc.
   ```

2. **Initialize manifest:**
   ```bash
   # Create manifest.json with your test texts
   ```

3. **Create prompt files:**
   - `PROMPT_analyze.md`
   - `PROMPT_evaluate.md` (see separate file)
   - `PROMPT_fix.md`
   - `AGENTS.md`

4. **Make loop executable:**
   ```bash
   chmod +x loop.sh
   ```

### Running

```bash
# Start the full autonomous loop
./loop.sh

# Or run specific phases manually
./loop.sh analyze
./loop.sh evaluate
./loop.sh fix

# With iteration limit
./loop.sh full 50
```

### Monitoring

- **Live logs:** `tail -f logs/iteration_*.log`
- **Current state:** `cat EVALUATION_STATE.md`
- **Progress:** `jq '.texts[] | "\(.name): \(.complete)"' manifest.json`

### Stopping

- `Ctrl+C` to stop the loop
- Resume by running `./loop.sh` again (picks up from current state)

---

## Safety & Guardrails

### Iteration Limits
- **Per text:** 5 attempts max (configurable in manifest)
- **Total:** 100 iterations max (configurable via CLI)
- **Prevents:** Infinite loops on impossible-to-fix issues

### Checkpoints
- Every iteration commits to git
- Can review changes: `git log --oneline`
- Can revert: `git reset --hard HEAD~1`

### Human Review Points
Consider pausing for human review:
- After first text completes (validate the loop is working)
- When a text hits max attempts without passing
- When overall score drops significantly between attempts

### Cost Awareness
- Each iteration = one Claude Code session
- Max plan: Included, but monitor usage
- Analysis phase: Uses local LLMs (your hardware cost)

---

## Expected Behavior

### Happy Path
1. Gatsby: 2-3 iterations to pass (initial alias issues)
2. Frankenstein: 2-3 iterations (frame narrative complexity)
3. Dracula: 3-4 iterations (epistolary format, many characters)
4. Pride & Prejudice: 2-3 iterations (many similar names)

### Stuck Detection
If same score for 3+ iterations:
- Loop should log warning
- Consider: Is the issue actually fixable?
- May need human intervention to reformulate approach

### Improvements Compound
Fixes for Gatsby (alias resolution) should help all subsequent texts.
The tool gets more robust with each text processed.
