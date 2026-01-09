# Audiobook Prep: Long-Task Harness Integration Spec

**Purpose:** Guide Claude Code in building a self-evaluating audiobook analysis pipeline that runs entirely on local LLMs.

**Repository:** https://github.com/shinyscale/audiobook_agent
**Branch:** `feature/agent-infrastructure`

---

## Overview

### The End Goal

A **fully local, self-evaluating runtime system** where:
- Local LLMs (via Ollama) perform all analysis: structure detection, character extraction, summaries, pronunciation
- A local LLM also serves as the **evaluator/judge**, assessing output quality
- The system can analyze **any book** and validate its own output without external dependencies
- No Claude in the loop at runtime — completely self-contained

### The Problem

Right now, there are too many variables to dial in:
- Agent prompts need tuning
- Consensus mechanisms need calibration  
- Verification criteria are incomplete
- Output quality is inconsistent
- You can't trust the local LLM to judge itself when the pipeline itself is unreliable

### The Solution: Two-Phase Approach

**Phase 1: Development (Claude-Assisted)**
- Use Claude Code + known works (Gatsby, Frankenstein) as a temporary "oracle"
- Claude's literary knowledge validates output while we dial in the local components
- Iterate on prompts, agent logic, and verification criteria until reliable
- **Goal:** Figure out what "good" looks like and codify it

**Phase 2: Runtime (Fully Local)**
- Graduate verification logic from "Claude judges" to "local LLM judges"
- The `verify()` methods in each agent become sophisticated enough to self-assess
- Evaluation prompts are refined to work with local models
- **Goal:** Self-evaluating system with zero Claude dependency

### What This Spec Covers

1. **Development harness** — Files and workflow for Claude-assisted iteration
2. **Evaluation criteria** — What "good" means for each agent, codified explicitly
3. **Verification system** — How agents assess their own output quality
4. **Graduation path** — How to transfer evaluation from Claude to local LLMs

The harness is temporary scaffolding. The verification system is permanent infrastructure.

---

## Part 1: Harness File Structure

Create the following files in the repository root under `ai/`:

```
ai/
├── feature_list.json      # Feature backlog with acceptance criteria
├── progress.log           # Session handoff log
├── eval_results/          # Evaluation outputs per test run
│   └── .gitkeep
├── ground_truth/          # Expected outputs for test corpus
│   ├── gatsby_chapters.json
│   ├── gatsby_characters.json
│   ├── frankenstein_chapters.json
│   └── frankenstein_characters.json
└── init.sh                # Environment bootstrap script
```

### 1.1 feature_list.json

```json
{
  "project_goal": "Build a fully local, self-evaluating audiobook analysis system that works on any book without external dependencies",
  "current_phase": "development",
  "phases": {
    "development": "Claude-assisted iteration on known works (Gatsby, Frankenstein)",
    "graduation": "Transferring evaluation from Claude to local LLM",
    "runtime": "Fully local self-evaluation on any book"
  },
  "features": [
    {
      "id": "structure.chapter_detection",
      "name": "Bulletproof Chapter Detection",
      "status": "failing",
      "priority": 1,
      "acceptance_criteria": [
        "Gatsby: Exactly 9 chapters detected with correct boundaries",
        "Frankenstein: Detects frame narrative structure (letters + chapters)",
        "No spurious chapters from section breaks, letters, or epigraphs",
        "Confidence score >= 0.8 for all detected chapters",
        "TOC agreement >= 0.9 when TOC present"
      ],
      "graduation": {
        "status": "not_started",
        "structural_checks": false,
        "self_check_prompts": false,
        "tested_unknown_works": false,
        "local_matches_claude": false,
        "notes": ""
      },
      "test_command": "python -m pytest tests/test_structure_agent.py -v"
    },
    {
      "id": "characters.extraction",
      "name": "Complete Character Extraction",
      "status": "failing",
      "priority": 2,
      "depends_on": ["structure.chapter_detection"],
      "acceptance_criteria": [
        "Gatsby: All 9 named characters identified (Nick, Gatsby, Daisy, Tom, Jordan, Myrtle, George, Meyer, Owl Eyes)",
        "Gatsby: No false merges (Tom Buchanan ≠ Daisy Buchanan)",
        "Gatsby: Correct alias resolution (Jay Gatsby = Mr. Gatsby = Gatsby)",
        "Frankenstein: Victor, Monster, Elizabeth, Henry, Alphonse, William, Justine, Walton all identified",
        "Frankenstein: 'The Creature' / 'the monster' / 'the fiend' correctly aliased",
        "No hallucinated characters",
        "Confidence >= 0.7 for main characters (>10 mentions)"
      ],
      "graduation": {
        "status": "not_started",
        "structural_checks": false,
        "self_check_prompts": false,
        "tested_unknown_works": false,
        "local_matches_claude": false,
        "notes": ""
      },
      "test_command": "python -m pytest tests/test_character_agent.py -v"
    },
    {
      "id": "characters.profiles",
      "name": "Accurate Character Profiles",
      "status": "failing",
      "priority": 3,
      "depends_on": ["characters.extraction"],
      "acceptance_criteria": [
        "Physical descriptions extracted where present in text",
        "Key relationships identified (married to, friend of, etc.)",
        "No invented details not supported by text",
        "Profile confidence >= 0.6 for all main characters"
      ],
      "graduation": {
        "status": "not_started",
        "structural_checks": false,
        "self_check_prompts": false,
        "tested_unknown_works": false,
        "local_matches_claude": false,
        "notes": ""
      },
      "test_command": "python -m pytest tests/test_character_profiles.py -v"
    },
    {
      "id": "summaries.chapter_summaries",
      "name": "Comprehensive Chapter Summaries",
      "status": "failing",
      "priority": 4,
      "depends_on": ["structure.chapter_detection", "characters.extraction"],
      "acceptance_criteria": [
        "Each summary captures 3-5 key events from the chapter",
        "Main characters appearing in chapter are mentioned",
        "No hallucinated events or characters",
        "Summaries are narrator-useful (focus on what happens, not interpretation)",
        "Length: 100-300 words per chapter"
      ],
      "graduation": {
        "status": "not_started",
        "structural_checks": false,
        "self_check_prompts": false,
        "tested_unknown_works": false,
        "local_matches_claude": false,
        "notes": ""
      },
      "test_command": "python -m pytest tests/test_summary_agent.py -v"
    },
    {
      "id": "pronunciation.foreign_words",
      "name": "Foreign Word Detection",
      "status": "failing",
      "priority": 5,
      "depends_on": ["structure.chapter_detection"],
      "acceptance_criteria": [
        "Gatsby: 'old sport' flagged as recurring phrase",
        "All character names flagged with pronunciation guidance",
        "Foreign phrases identified with language tag",
        "No common English words incorrectly flagged"
      ],
      "graduation": {
        "status": "not_started",
        "structural_checks": false,
        "self_check_prompts": false,
        "tested_unknown_works": false,
        "local_matches_claude": false,
        "notes": ""
      },
      "test_command": "python -m pytest tests/test_pronunciation_agent.py -v"
    },
    {
      "id": "pronunciation.homographs",
      "name": "Homograph Disambiguation",
      "status": "failing",
      "priority": 6,
      "depends_on": ["pronunciation.foreign_words"],
      "acceptance_criteria": [
        "read (past) vs read (present) correctly disambiguated by context",
        "lead (metal) vs lead (verb) correctly disambiguated",
        "Context examples provided for each homograph instance",
        "False positive rate < 5%"
      ],
      "graduation": {
        "status": "not_started",
        "structural_checks": false,
        "self_check_prompts": false,
        "tested_unknown_works": false,
        "local_matches_claude": false,
        "notes": ""
      },
      "test_command": "python -m pytest tests/test_homographs.py -v"
    },
    {
      "id": "pipeline.performance",
      "name": "Pipeline Performance",
      "status": "failing",
      "priority": 7,
      "acceptance_criteria": [
        "Gatsby full analysis completes in < 60 minutes on DGX Spark",
        "Memory usage stays under 32GB during analysis",
        "No redundant LLM calls (caching works)",
        "Checkpointing enables resume from any agent boundary"
      ],
      "graduation": {
        "status": "n/a",
        "notes": "Performance is not graduated — same metrics apply in runtime"
      },
      "test_command": "python ai/benchmark.py --book gatsby --timeout 3600"
    },
    {
      "id": "pipeline.reliability",
      "name": "Pipeline Reliability",
      "status": "failing",
      "priority": 8,
      "acceptance_criteria": [
        "3 consecutive runs on same book produce identical output",
        "Agent orchestration respects dependency graph",
        "Graceful degradation when LLM calls fail",
        "All verification issues logged with actionable detail"
      ],
      "graduation": {
        "status": "n/a",
        "notes": "Reliability is not graduated — same requirements apply in runtime"
      },
      "test_command": "python ai/reliability_test.py --book gatsby --runs 3"
    }
  ]
}
```

### 1.2 progress.log Format

Each session appends entries in this format:

```
=== Session: 2026-01-07T14:30:00Z ===
Branch: feature/agent-infrastructure
Commit: abc1234

## Status Check
- structure.chapter_detection: failing → passing
- characters.extraction: failing (3 issues remain)
- characters.profiles: blocked (waiting on extraction)

## Work Completed
1. Fixed chapter boundary regex to handle "CHAPTER ONE" format
2. Added validation for alias merging (catches Tom/Daisy Buchanan case)
3. Ran evaluation: structure 100%, characters 78%

## Issues Found
- CharacterAgent merges "Meyer Wolfsheim" with "Wolfsheim" but misses "Mr. Wolfsheim"
- SummaryAgent occasionally hallucinates minor events

## Next Steps
1. Fix alias resolution to handle title variations (Mr., Mrs., Dr.)
2. Add hallucination detection to summary verification
3. Re-run evaluation after fixes

## Handoff Notes
Character extraction is close. The merge logic in `src/agents/characters.py:_merge_aliases()` 
needs to check for title prefixes. See line 234 for the current implementation.
```

### 1.3 init.sh

```bash
#!/bin/bash
# Environment bootstrap for audiobook_agent development

set -e

echo "=== Audiobook Agent Development Environment ==="

# Check Python version
python_version=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
if [[ "$python_version" != "3.10" && "$python_version" != "3.11" && "$python_version" != "3.12" ]]; then
    echo "ERROR: Python 3.10+ required, found $python_version"
    exit 1
fi

# Check virtual environment
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "WARNING: No virtual environment active"
    echo "Run: python -m venv venv && source venv/bin/activate"
fi

# Install dependencies
echo "Installing dependencies..."
pip install -e ".[dev]" --quiet

# Download spaCy model if missing
if ! python -c "import spacy; spacy.load('en_core_web_lg')" 2>/dev/null; then
    echo "Downloading spaCy model..."
    python -m spacy download en_core_web_lg
fi

# Check Ollama
if command -v ollama &> /dev/null; then
    echo "Ollama: $(ollama --version)"
    echo "Models available:"
    ollama list 2>/dev/null || echo "  (ollama not running)"
else
    echo "WARNING: Ollama not found. Install from https://ollama.ai"
fi

# Check test corpus
echo ""
echo "Test corpus status:"
for book in gatsby frankenstein; do
    if [[ -f "data/sample_books/${book}.txt" ]]; then
        echo "  ✓ ${book}.txt"
    else
        echo "  ✗ ${book}.txt (missing)"
    fi
done

# Run quick validation
echo ""
echo "Running quick validation..."
python -c "from src.analyzer import AudiobookAnalyzer; print('  ✓ Imports OK')"

# Show feature status
echo ""
echo "Feature status:"
if [[ -f "ai/feature_list.json" ]]; then
    python -c "
import json
with open('ai/feature_list.json') as f:
    data = json.load(f)
for f in data['features']:
    status = f['status']
    icon = '✓' if status == 'passing' else '○' if status == 'failing' else '⊘'
    print(f'  {icon} {f[\"id\"]}: {status}')
"
else
    echo "  (no feature_list.json found)"
fi

echo ""
echo "Ready for development!"
```

---

## Part 2: Evaluation System

Since you're using Claude Code Max (not the API), evaluation works differently: **Claude Code itself is the judge**. No API calls needed — Claude Code reads the pipeline output and evaluates it using its own literary knowledge.

### 2.1 Pipeline Runner (ai/run_analysis.py)

This script just runs the analysis and saves output for Claude Code to evaluate:

```python
#!/usr/bin/env python3
"""
Run the audiobook analysis pipeline and save results for evaluation.

This script runs the pipeline only. Evaluation is performed by Claude Code
directly, using its literary knowledge to assess output quality.
"""

import argparse
import json
import os
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analyzer import AudiobookAnalyzer
from src.agents.config import OrchestratorConfig, create_optimized_config


def run_analysis(book_path: str, model: str = "llama3.2", output_dir: str = "ai/eval_results") -> str:
    """
    Run the full analysis pipeline on a book.
    
    Returns path to the output JSON file.
    """
    config = OrchestratorConfig(default_model=model)
    analyzer = AudiobookAnalyzer(
        llm_refine=True,
        orchestrator_config=config,
    )
    
    print(f"Analyzing: {book_path}")
    print(f"Model: {model}")
    
    result = analyzer.analyze(book_path)
    result_dict = result.to_dict() if hasattr(result, 'to_dict') else asdict(result)
    
    # Save output
    os.makedirs(output_dir, exist_ok=True)
    book_name = Path(book_path).stem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"{output_dir}/{book_name}_{timestamp}.json"
    
    with open(output_path, "w") as f:
        json.dump(result_dict, f, indent=2, default=str)
    
    # Also save as "latest" for easy access
    latest_path = f"{output_dir}/{book_name}_latest.json"
    with open(latest_path, "w") as f:
        json.dump(result_dict, f, indent=2, default=str)
    
    print(f"Output saved: {output_path}")
    print(f"Latest copy: {latest_path}")
    
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Run audiobook analysis pipeline")
    parser.add_argument("book", help="Path to book file or name (gatsby, frankenstein)")
    parser.add_argument("--model", default="llama3.2", help="LLM model for analysis")
    parser.add_argument("--output", default="ai/eval_results", help="Output directory")
    
    args = parser.parse_args()
    
    # Handle shorthand book names
    book_path = args.book
    if args.book in ("gatsby", "frankenstein"):
        book_path = f"data/sample_books/{args.book}.txt"
    
    if not os.path.exists(book_path):
        print(f"ERROR: Book not found: {book_path}")
        sys.exit(1)
    
    output_path = run_analysis(book_path, args.model, args.output)
    
    print("\n" + "="*60)
    print("NEXT STEP: Ask Claude Code to evaluate the output")
    print("="*60)
    print(f"\nRun this command or ask Claude Code directly:")
    print(f"  'Evaluate the analysis output at {output_path}'")
    print(f"\nOr for specific features:")
    print(f"  'Evaluate the chapter detection in {output_path}'")
    print(f"  'Evaluate character extraction in {output_path}'")


if __name__ == "__main__":
    main()
```

### 2.2 Evaluation Prompts (ai/eval_prompts.md)

Claude Code uses these prompts to evaluate output. Save this file so Claude Code can reference it:

```markdown
# Evaluation Prompts for Audiobook Analysis

Use these prompts to evaluate pipeline output. Read the output JSON, then apply the appropriate evaluation.

---

## Structure Evaluation (Chapters)

When evaluating chapter detection for **The Great Gatsby**:

The Great Gatsby has exactly 9 chapters, numbered Chapter I through Chapter IX (or 1-9). 
There are no titled chapters, no prologue, no epilogue.

Check:
- [ ] Exactly 9 chapters detected
- [ ] No spurious chapters from section breaks or epigraphs
- [ ] Chapter boundaries are at actual chapter starts
- [ ] Confidence >= 0.8 for all chapters

When evaluating chapter detection for **Frankenstein**:

Frankenstein has a frame narrative structure:
- Letters I-IV (Walton's letters)
- Chapters 1-24 (Victor's narrative, though some editions vary)
- The creature's tale is embedded within Victor's narrative

Check:
- [ ] Frame structure detected (letters + chapters)
- [ ] No false chapters from letter closings or scene breaks
- [ ] Total structure accounts for ~24-28 sections depending on edition

---

## Character Evaluation

When evaluating characters for **The Great Gatsby**:

Main characters (MUST be found):
- Nick Carraway (narrator)
- Jay Gatsby / James Gatz / Mr. Gatsby
- Daisy Buchanan
- Tom Buchanan (Daisy's husband - MUST NOT merge with Daisy)
- Jordan Baker

Supporting characters (SHOULD be found):
- Myrtle Wilson (Tom's mistress)
- George Wilson (Myrtle's husband - MUST NOT merge with Myrtle)
- Meyer Wolfsheim / Mr. Wolfsheim
- Owl Eyes (the man with enormous spectacles)

Check:
- [ ] All main characters found
- [ ] Tom and Daisy Buchanan are SEPARATE entries (married couple)
- [ ] George and Myrtle Wilson are SEPARATE entries (married couple)
- [ ] Jay Gatsby aliases correctly merged (Gatsby, Mr. Gatsby, James Gatz)
- [ ] No hallucinated characters
- [ ] Mention counts roughly match importance

When evaluating characters for **Frankenstein**:

Main characters (MUST be found):
- Victor Frankenstein
- The Creature / Monster / Fiend / Wretch (all same entity)
- Elizabeth Lavenza (Victor's adopted sister/wife)
- Henry Clerval (Victor's friend)
- Robert Walton (frame narrator)

Supporting characters (SHOULD be found):
- Alphonse Frankenstein (Victor's father)
- William Frankenstein (Victor's brother, murdered)
- Justine Moritz (wrongly executed)
- The De Lacey family (Felix, Agatha, Safie, the old man)

Check:
- [ ] All creature aliases merged (Monster, Creature, Fiend, Daemon, Wretch)
- [ ] Victor Frankenstein not confused with the creature
- [ ] De Lacey family members may be separate or grouped

---

## Summary Evaluation

When evaluating chapter summaries:

For each chapter summary, verify:
- [ ] Key events of that chapter are mentioned
- [ ] No events from other chapters incorrectly included
- [ ] No hallucinated events that don't occur
- [ ] Character names are accurate
- [ ] Length is 100-300 words (useful for narrator prep)

**The Great Gatsby** key events by chapter:
- Ch 1: Nick moves to West Egg, visits Tom and Daisy, sees Gatsby reaching toward green light
- Ch 2: Valley of Ashes, Tom's mistress Myrtle, party in NYC apartment
- Ch 3: Gatsby's party, Nick meets Gatsby, Jordan
- Ch 4: Gatsby's car ride with Nick, Gatsby's history, Wolfsheim lunch
- Ch 5: Gatsby and Daisy reunite at Nick's house, tour of Gatsby's mansion
- Ch 6: Gatsby's true origins (James Gatz), Tom and Daisy at Gatsby's party
- Ch 7: Hottest day, confrontation at Plaza Hotel, Myrtle's death
- Ch 8: Gatsby's vigil, his past with Daisy, Wilson kills Gatsby
- Ch 9: Gatsby's funeral, Nick's disillusionment, green light meditation

---

## Evaluation Output Format

After evaluating, provide structured feedback:

```json
{
  "feature": "structure.chapter_detection",
  "book": "The Great Gatsby",
  "passed": true/false,
  "score": 0.0-1.0,
  "criteria": {
    "CHAPTER_COUNT": {"passed": true, "expected": 9, "actual": 9},
    "NO_SPURIOUS": {"passed": true},
    "NO_MISSING": {"passed": true},
    "CONFIDENCE": {"passed": true, "min_confidence": 0.85}
  },
  "issues": ["list of specific problems found"],
  "suggestions": ["actionable improvements"],
  "code_changes_needed": ["specific files/functions to modify"]
}
```

---

## Evaluation Workflow

1. Run: `python ai/run_analysis.py gatsby --model qwen2.5:72b`
2. Read: `ai/eval_results/gatsby_latest.json`
3. Evaluate using prompts above
4. Record results in `ai/progress.log`
5. If issues found: identify root cause, make code changes, re-run
6. If passed: update `ai/feature_list.json` status
```

### 2.3 Claude Code Evaluation Workflow

Instead of running a script, Claude Code performs evaluation inline:

**Step 1: Run the pipeline**
```bash
python ai/run_analysis.py gatsby --model qwen2.5:72b
```

**Step 2: Claude Code reads and evaluates**
Claude Code reads `ai/eval_results/gatsby_latest.json` and evaluates it against its literary knowledge using the prompts in `ai/eval_prompts.md`.

**Step 3: Record results**
Claude Code writes evaluation results to `ai/eval_results/gatsby_eval_<timestamp>.json` and updates `ai/progress.log`.

### 2.4 Why This Works Better

1. **No API key management** — Claude Code Max includes Claude access
2. **Richer evaluation** — Claude Code can ask follow-up questions, cross-reference files
3. **Integrated workflow** — Evaluation happens in the same context as code changes
4. **Better debugging** — Claude Code can immediately investigate issues in the codebase

### 2.5 Triggering Evaluation

Ask Claude Code any of these:

```
"Run the pipeline on gatsby and evaluate the output"

"Evaluate ai/eval_results/gatsby_latest.json for chapter detection accuracy"

"Check if the character extraction passes for Frankenstein"

"Run a full evaluation cycle on gatsby - analyze, evaluate, and report"
```

Claude Code will:
1. Run the analysis (if needed)
2. Read the output JSON
3. Apply its literary knowledge to evaluate
4. Report issues and suggest fixes
5. Update harness files (feature_list.json, progress.log)

---

## Part 3: Development Workflow Protocol

### 3.1 Session Startup Protocol

When starting a new session, Claude Code must:

1. **Read context files:**
   ```bash
   cat ai/progress.log | tail -100
   cat ai/feature_list.json
   git log --oneline -10
   ```

2. **Run environment check:**
   ```bash
   bash ai/init.sh
   ```

3. **Identify next task:**
   - Find first feature with `status: "failing"` whose dependencies are `"passing"`
   - If blocked, note in progress.log and find alternative

4. **Announce work plan:**
   - State which feature being worked on
   - List specific acceptance criteria being targeted
   - Estimate number of iteration cycles needed

### 3.2 Development Cycle

For each feature:

```
┌─────────────────────────────────────────────────────────────────────┐
│                     DEVELOPMENT CYCLE                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. IMPLEMENT                                                        │
│     - Make code changes to address failing criteria                  │
│     - Run unit tests: pytest tests/test_<agent>.py                   │
│     - Fix any test failures                                          │
│                                                                      │
│  2. RUN PIPELINE                                                     │
│     - python ai/run_analysis.py gatsby --model qwen2.5:72b           │
│     - Wait for analysis to complete                                  │
│     - Output saved to ai/eval_results/gatsby_latest.json             │
│                                                                      │
│  3. EVALUATE (Claude Code as Judge)                                  │
│     - Read ai/eval_results/gatsby_latest.json                        │
│     - Apply literary knowledge to assess output quality              │
│     - Reference ai/eval_prompts.md for evaluation criteria           │
│     - Record structured evaluation result                            │
│                                                                      │
│  4. ANALYZE                                                          │
│     - If all criteria pass: proceed to verification                  │
│     - If criteria fail: identify root cause in code                  │
│     - Plan specific fix based on what's wrong                        │
│                                                                      │
│  5. ITERATE                                                          │
│     - If < 3 iterations: return to step 1                            │
│     - If >= 3 iterations: log blockers, request human review         │
│                                                                      │
│  6. VERIFY                                                           │
│     - Run on second book (frankenstein)                              │
│     - Evaluate that output too                                       │
│     - Ensure no regression                                           │
│     - Update feature status to "passing" if both books pass          │
│                                                                      │
│  7. COMMIT                                                           │
│     - git add -A                                                     │
│     - git commit -m "feat(<feature_id>): <description>"              │
│     - Update progress.log with session summary                       │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.3 Example Claude Code Session

Here's what a typical autonomous session looks like:

```
User: "Work on the characters.extraction feature"

Claude Code:
1. Reads ai/feature_list.json → sees characters.extraction is "failing"
2. Reads ai/progress.log → sees last session notes about alias issues
3. Checks dependency → structure.chapter_detection must be "passing" ✓
4. Runs: python ai/run_analysis.py gatsby --model qwen2.5:72b
5. [waits 30-60 min for analysis]
6. Reads ai/eval_results/gatsby_latest.json
7. Evaluates character list against Gatsby knowledge:
   - Nick Carraway ✓
   - Jay Gatsby ✓ (but missing "James Gatz" alias)
   - Tom Buchanan ✓
   - Daisy Buchanan ✓
   - Tom and Daisy correctly separate ✓
   - Meyer Wolfsheim... merged with "Wolfshiem" (typo variant) ✓
   - George Wilson ✓
   - Myrtle Wilson ✓
   - ISSUE: "Mr. Wolfsheim" is a separate entry (should merge)
8. Identifies fix: src/agents/characters.py alias merging doesn't handle "Mr." prefix
9. Makes code change
10. Re-runs pipeline, re-evaluates
11. All criteria pass → runs on Frankenstein to verify
12. Both pass → updates feature_list.json status to "passing"
13. Commits with message "feat(characters.extraction): fix title prefix alias merging"
14. Updates progress.log with session summary
```

### 3.3 Quality Gates

**Passing threshold:** Feature is `"passing"` when:
- Score >= 0.9 on ALL test books
- Zero "error" severity issues
- Unit tests pass
- No regressions in dependent features

**Human review required when:**
- 3+ iteration cycles without progress
- Conflicting evaluation feedback
- Architectural changes needed
- Performance regression > 20%

### 3.4 Session Handoff

Before ending a session:

1. **Update progress.log** with:
   - Features worked on and status changes
   - Specific issues encountered
   - Next steps for following session
   - Any blockers requiring human input

2. **Update feature_list.json:**
   - Change status for completed features
   - Add any new issues discovered

3. **Commit all changes:**
   ```bash
   git add -A
   git commit -m "session: <date> - <summary>"
   ```

---

## Part 4: Integration with Existing Agent System

### 4.1 Enhanced Verification

Update `src/agents/base.py` to support the harness evaluation:

```python
# Add to AgentResult dataclass
@dataclass
class AgentResult(Generic[T]):
    # ... existing fields ...
    
    # Harness integration
    evaluation_ready: bool = True  # Can be evaluated by harness
    
    def to_eval_format(self) -> dict:
        """Convert to format expected by ai/evaluate.py"""
        raise NotImplementedError("Subclasses should implement")
```

### 4.2 Ground Truth Integration

For known books, agents can validate against expected outputs:

```python
# In StructureAgent.verify()
def verify(self, result: AgentResult[ChapterMap]) -> VerificationResult:
    issues = []
    
    # ... existing verification ...
    
    # Ground truth check (if available)
    ground_truth_path = f"ai/ground_truth/{self._get_book_key()}_chapters.json"
    if os.path.exists(ground_truth_path):
        with open(ground_truth_path) as f:
            expected = json.load(f)
        
        if len(result.data.chapters) != expected["chapter_count"]:
            issues.append(VerificationIssue(
                description=f"Expected {expected['chapter_count']} chapters, got {len(result.data.chapters)}",
                severity="error",
            ))
    
    return VerificationResult(passed=len([i for i in issues if i.severity == "error"]) == 0, issues=issues)
```

---

## Part 5: Test Corpus

### 5.1 Required Books

Place in `data/sample_books/`:

| File | Source | Notes |
|------|--------|-------|
| `gatsby.txt` | Project Gutenberg | The Great Gatsby (public domain) |
| `frankenstein.txt` | Project Gutenberg | Frankenstein (public domain) |

### 5.2 Ground Truth Files

Create in `ai/ground_truth/`:

**gatsby_chapters.json:**
```json
{
  "book": "The Great Gatsby",
  "chapter_count": 9,
  "chapters": [
    {"index": 1, "has_title": false},
    {"index": 2, "has_title": false},
    {"index": 3, "has_title": false},
    {"index": 4, "has_title": false},
    {"index": 5, "has_title": false},
    {"index": 6, "has_title": false},
    {"index": 7, "has_title": false},
    {"index": 8, "has_title": false},
    {"index": 9, "has_title": false}
  ]
}
```

**gatsby_characters.json:**
```json
{
  "book": "The Great Gatsby",
  "main_characters": [
    {"canonical_name": "Nick Carraway", "aliases": ["Nick"], "role": "narrator"},
    {"canonical_name": "Jay Gatsby", "aliases": ["Gatsby", "Mr. Gatsby", "James Gatz"], "role": "protagonist"},
    {"canonical_name": "Daisy Buchanan", "aliases": ["Daisy"], "role": "main"},
    {"canonical_name": "Tom Buchanan", "aliases": ["Tom"], "role": "antagonist"},
    {"canonical_name": "Jordan Baker", "aliases": ["Jordan", "Miss Baker"], "role": "main"}
  ],
  "supporting_characters": [
    {"canonical_name": "Myrtle Wilson", "aliases": ["Myrtle", "Mrs. Wilson"]},
    {"canonical_name": "George Wilson", "aliases": ["Wilson"]},
    {"canonical_name": "Meyer Wolfsheim", "aliases": ["Wolfsheim", "Mr. Wolfsheim"]},
    {"canonical_name": "Owl Eyes", "aliases": []}
  ],
  "distinct_pairs": [
    ["Tom Buchanan", "Daisy Buchanan"],
    ["George Wilson", "Myrtle Wilson"]
  ]
}
```

---

## Part 6: Commands Reference

### Analysis Commands

```bash
# Full analysis via CLI
audiobook-prep analyze data/sample_books/gatsby.txt --output Output/gatsby.json

# With specific model
audiobook-prep analyze data/sample_books/gatsby.txt --model qwen2.5:72b

# Via harness runner (saves to ai/eval_results/)
python ai/run_analysis.py gatsby --model qwen2.5:72b
python ai/run_analysis.py frankenstein --model llama3.2

# TUI for reviewing results
audiobook-prep analyze data/sample_books/gatsby.txt --tui
```

### Harness Commands

```bash
# Environment check
bash ai/init.sh

# View current status
cat ai/feature_list.json | python -c "import json,sys; d=json.load(sys.stdin); [print(f'{f[\"status\"]:10} {f[\"id\"]}') for f in d['features']]"

# View recent progress
tail -50 ai/progress.log

# Check latest analysis output
cat ai/eval_results/gatsby_latest.json | python -c "import json,sys; d=json.load(sys.stdin); print(f'Chapters: {len(d.get(\"structure\",{}).get(\"chapters\",[]))}'); print(f'Characters: {len(d.get(\"characters\",[]))}')"
```

### Claude Code Evaluation Prompts

Ask Claude Code directly:

```
"Run the pipeline on gatsby and evaluate the chapter detection"

"Read ai/eval_results/gatsby_latest.json and evaluate the character extraction"

"Compare the character list in ai/eval_results/gatsby_latest.json against The Great Gatsby - are all main characters found?"

"Evaluate ai/eval_results/frankenstein_latest.json for the pronunciation feature"

"Do a full evaluation cycle: run gatsby, evaluate all features, update feature_list.json"
```

---

## Part 7: Success Criteria

The harness integration is complete when:

1. **Files exist:** All files in `ai/` directory are created and functional
2. **Evaluation works:** Claude Code can evaluate pipeline output against known works
3. **Workflow documented:** progress.log has at least one complete session entry
4. **Verification improving:** Agent `verify()` methods catch real issues
5. **Human handoff clean:** A new session can start from progress.log alone

---

## Part 8: Graduation Path (Claude → Local LLM)

This is the critical section. The development harness is temporary — the goal is a self-evaluating runtime system.

### 8.1 What "Graduation" Means

| Aspect | Phase 1 (Development) | Phase 2 (Runtime) |
|--------|----------------------|-------------------|
| Analysis | Local LLM (Ollama) | Local LLM (Ollama) |
| Evaluation | Claude Code | Local LLM (Ollama) |
| Ground truth | Claude's literary knowledge | Codified criteria + heuristics |
| Works on | Known books (Gatsby, etc.) | Any book |
| Human in loop | For review/iteration | Only for edge cases |

### 8.2 Graduation Criteria Per Agent

Each agent "graduates" when its `verify()` method can reliably assess output quality without Claude. This requires:

**StructureAgent graduation:**
```python
# Phase 1: Claude evaluates "does this chapter list look right for Gatsby?"
# Phase 2: Local verification checks:
def verify(self, result: AgentResult[ChapterMap]) -> VerificationResult:
    issues = []
    chapters = result.data.chapters
    
    # Structural heuristics (no Claude needed)
    # - Chapter count reasonable for word count (1 per 3-8k words typical)
    # - No chapter < 500 words (likely false positive)
    # - No chapter > 3x average (likely missed boundary)
    # - Sequential numbering if numbered
    # - Confidence scores from consensus pipeline
    
    # LLM self-check (local model)
    # - "Given these chapter titles/first lines, does this sequence make sense?"
    # - Not asking "is this correct for Book X" — asking "is this internally coherent?"
```

**CharacterAgent graduation:**
```python
# Phase 1: Claude evaluates "are all Gatsby characters found?"
# Phase 2: Local verification checks:
def verify(self, result: AgentResult[CharacterMap]) -> VerificationResult:
    issues = []
    characters = result.data.characters
    
    # Structural heuristics (no Claude needed)
    # - Main characters should have 50+ mentions
    # - No duplicate canonical names
    # - Aliases should share name components
    # - Married couples flagged for review (same surname)
    
    # Cross-reference checks
    # - Characters in summaries should exist in character list
    # - NER entities should be accounted for (merged or excluded with reason)
    
    # LLM self-check (local model)
    # - "Are any of these characters likely the same person?"
    # - "Do these alias groupings make sense?"
```

**SummaryAgent graduation:**
```python
# Phase 1: Claude evaluates "does this summary capture Chapter 3 of Gatsby?"
# Phase 2: Local verification checks:
def verify(self, result: AgentResult[list[Summary]]) -> VerificationResult:
    issues = []
    
    # Structural heuristics
    # - Summary length proportional to chapter length
    # - Characters mentioned should exist in character list
    # - No summary references events from other chapters (sequence check)
    
    # LLM self-check (local model)
    # - "Does this summary mention specific events, or is it vague?"
    # - "Given the chapter text, does this summary seem complete?"
    # - Key: asking about THIS text, not relying on external knowledge
```

### 8.3 The Graduation Process

For each agent:

1. **Catalog Claude's feedback** — During Phase 1, track every issue Claude identifies
2. **Identify patterns** — What types of issues recur? What heuristics would catch them?
3. **Codify as verification rules** — Add checks to `verify()` that don't require literary knowledge
4. **Create self-check prompts** — Write prompts that work WITHOUT knowing the book
5. **Test on unknown works** — Run on books Claude hasn't seen, verify locally
6. **Compare judgments** — Does local verification catch the same issues Claude would?

### 8.4 Self-Check Prompts (Book-Agnostic)

The key insight: **runtime verification can't rely on knowing the book**. Prompts must be structured to assess quality using only the input text and output.

**Bad prompt (requires literary knowledge):**
> "Is this character list complete for The Great Gatsby?"

**Good prompt (book-agnostic):**
> "Given this text excerpt and this character list, are there any frequently-mentioned names in the text that don't appear in the character list?"

**Bad prompt:**
> "Does this summary accurately describe Chapter 5 of Gatsby?"

**Good prompt:**
> "Given this chapter text and this summary, does the summary mention specific events from the text, or does it contain claims not supported by the text?"

### 8.5 Verification Levels

Each agent's `verify()` should implement three tiers:

```python
class VerificationLevel(Enum):
    STRUCTURAL = "structural"  # Heuristics, no LLM needed
    SELF_CHECK = "self_check"  # Local LLM, book-agnostic prompts
    ORACLE = "oracle"          # Claude, used only in development

def verify(self, result: AgentResult, level: VerificationLevel = VerificationLevel.SELF_CHECK):
    issues = []
    
    # Always run structural checks (fast, no LLM)
    issues.extend(self._structural_checks(result))
    
    if level in (VerificationLevel.SELF_CHECK, VerificationLevel.ORACLE):
        # Run LLM-based self-check (local model)
        issues.extend(self._llm_self_check(result))
    
    if level == VerificationLevel.ORACLE:
        # Development only: ask Claude (via eval_prompts.md criteria)
        # This path is removed in production
        pass
    
    return VerificationResult(...)
```

### 8.6 Tracking Graduation Progress

Add to `ai/feature_list.json`:

```json
{
  "id": "structure.chapter_detection",
  "status": "passing",
  "graduation_status": "partial",
  "graduation_criteria": {
    "structural_checks": true,
    "self_check_prompts": true,
    "tested_on_unknown_works": false,
    "local_matches_claude": false
  }
}
```

A feature is fully graduated when:
- `structural_checks`: Heuristic verification implemented
- `self_check_prompts`: Book-agnostic LLM verification implemented
- `tested_on_unknown_works`: Verified on books outside training set
- `local_matches_claude`: Local verification catches same issues Claude would

### 8.7 End State

When all agents are graduated:

```python
# Runtime analysis (no Claude anywhere)
analyzer = AudiobookAnalyzer(
    llm_client=OllamaClient("qwen2.5:72b"),
    verification_level=VerificationLevel.SELF_CHECK,  # Local only
)

result = analyzer.analyze("any_book.epub")

# result.verification contains:
# - Confidence scores per agent
# - Issues found by structural checks
# - Issues found by LLM self-check
# - Overall quality assessment
# - Flags for human review if confidence low

# No Claude involved. Fully self-contained.
```

---

## Appendix A: Why This Approach

### The Core Insight

You can't tune a self-evaluating system when you don't know what "good" looks like yet. Claude serves as a temporary oracle during development — not because the runtime system will use Claude, but because you need a reliable judge to iterate against while dialing in the local components.

Once the local pipeline is reliable:
- The prompts are tuned
- The consensus mechanisms work
- The verification heuristics catch real issues
- The self-check prompts are book-agnostic

...then Claude is no longer needed. The system graduates to fully local operation.

### Development Harness vs. Runtime System

| Component | Development | Runtime |
|-----------|-------------|---------|
| `ai/feature_list.json` | Tracks progress | Removed |
| `ai/progress.log` | Session handoffs | Removed |
| `ai/eval_prompts.md` | Claude evaluation criteria | Removed |
| `ai/run_analysis.py` | Test runner | Removed |
| `src/agents/*/verify()` | Uses Claude as oracle | Uses local LLM only |
| Ground truth | Claude's literary knowledge | Codified heuristics + self-check |

The `ai/` directory is scaffolding. The `src/agents/` verification is permanent.

### Why Claude First, Local Later

1. **Claude knows the books** — Can validate "is this the right answer?" for Gatsby/Frankenstein
2. **Local LLMs don't** — Can only validate "is this internally consistent?"
3. **But runtime needs local** — Can't call Claude for every book analysis
4. **So we use Claude to train the local verification** — Figure out what heuristics and prompts catch the same issues

### The Handoff Checklist

Before removing Claude from the loop:

- [ ] Every issue Claude found is now caught by structural heuristics OR self-check prompts
- [ ] Self-check prompts work without knowing the book
- [ ] Verification tested on books outside Gatsby/Frankenstein
- [ ] Local LLM verification matches Claude's judgment 90%+ of the time
- [ ] Edge cases flagged for human review rather than silently failing

---

## Appendix B: Extending the Harness

### Adding New Features

1. Add entry to `feature_list.json` with unique ID, acceptance criteria
2. Create corresponding evaluation method in `LiteraryJudge`
3. Add ground truth file if applicable
4. Document any new test commands

### Adding New Test Books

1. Place `.txt` file in `data/sample_books/`
2. Create ground truth files in `ai/ground_truth/`
3. Update book name mapping in `evaluate.py`
4. Add book to relevant feature acceptance criteria

### Custom Evaluation Criteria

The `LiteraryJudge` class can be extended with domain-specific evaluators:

```python
def evaluate_pronunciation_for_narrator(self, book_title: str, pronunciations: list[dict]) -> EvalResult:
    """Evaluate pronunciation guide from audiobook narrator perspective."""
    # Custom prompt focusing on narrator needs
    ...
```
