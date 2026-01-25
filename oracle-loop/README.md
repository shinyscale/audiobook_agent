# Oracle Loop

An automated improvement loop for the audiobook-prep analysis pipeline. The oracle loop iteratively runs analysis, evaluates quality against a rubric, and attempts fixes until the output meets quality thresholds.

> **⚠️ V2 Pipeline Active**
>
> The V2 character extraction pipeline is now the only implementation. V1 has been removed from the codebase.
>
> When making fixes:
> - Focus on **V2 pipeline files** in `src/pipeline/character_extraction_v2/`
> - Use the agent at `src/agents/characters.py` (renamed from characters_v2.py)
> - Historical attempt summaries from V1 may not be relevant to current issues
>
> See `docs/CODEBASE_SUMMARY.md` for V2 file locations and fix patterns.

## Overview

The oracle loop is a development tool (not part of the main audiobook-prep package) that:

1. **Analyzes** text files using the audiobook-prep pipeline
2. **Evaluates** output quality against defined criteria (see `docs/output_quality.md`)
3. **Fixes** issues by modifying pipeline code when quality is below threshold
4. **Iterates** until the quality threshold (default 8.0/10) is met

## Usage

```bash
# From the oracle-loop directory
cd oracle-loop

# Run with auto-detection of current phase
./oracle-loop.sh

# Force a specific phase
./oracle-loop.sh analyze    # Run analysis
./oracle-loop.sh evaluate   # Run evaluation
./oracle-loop.sh fix        # Run fix phase

# Set max iterations
./oracle-loop.sh auto 50    # Run up to 50 iterations
```

## Monitor

Watch the loop progress in real-time:

```bash
python monitor/oracle_monitor.py
```

The monitor displays:
- Current text and attempt number
- Scores for each category
- Progress toward threshold
- Recent issues

## Directory Structure

```
oracle-loop/
├── oracle-loop.sh          # Main loop script
├── prompts/                 # Claude prompts for each phase
│   ├── PROMPT_analyze.md
│   ├── PROMPT_evaluate.md
│   └── PROMPT_fix.md
├── state/                   # Runtime state (gitignored)
│   ├── EVALUATION_STATE.md  # Current evaluation status
│   └── manifest.json        # Test texts and progress
├── logs/                    # Iteration logs (gitignored)
├── docs/                    # Documentation
│   ├── output_quality.md    # Evaluation rubric
│   └── *.md                 # Attempt summaries, design docs
├── tests/                   # Ad-hoc test scripts
├── monitor/                 # TUI monitor
│   └── oracle_monitor.py
└── README.md
```

## Configuration

Edit `state/manifest.json` to configure:

```json
{
  "quality_threshold": 8.0,
  "texts": [
    {
      "name": "my_text",
      "file": "../Test_Texts/my_text.txt",
      "complete": false,
      "attempts": 0
    }
  ]
}
```

## Models Used

- **Analysis/Fix phases**: Claude Sonnet (faster, cost-effective)
- **Evaluation phase**: Claude Opus (the "oracle" - more thorough evaluation)

## Safety Features

- **No-progress guardrail**: Exits after 3 consecutive iterations with no state change
- **Regression detection**: Auto-reverts fixes that cause score to drop > 0.3 points
- **Max iterations**: Configurable limit (default 100)

## Related Files

The oracle loop tests and improves code in the main `src/` directory. Test texts are stored in `Test_Texts/` (shared with main tool).
