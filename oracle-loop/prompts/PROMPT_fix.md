# Phase: FIX

You are fixing issues identified in the evaluation phase of an autonomous improvement loop for an audiobook narrator preparation tool.

> **⚠️ V2 PIPELINE IS ACTIVE**
>
> The oracle loop now uses **V2 character extraction** (the only implementation). When fixing character-related issues:
> - **USE:** `src/pipeline/character_extraction_v2/` (main_cast.py, grounding.py, narrator.py, supporting.py)
> - **USE:** `src/agents/characters.py`
> - **Note:** V1 character extraction has been removed from the codebase

---

## 🎯 The Universal Goal

**You are not fixing THIS book. You are finding the configuration that works for ALL books.**

The oracle loop exists to discover the optimal combination of:
- Model selection (which LLM, what temperature)
- Prompt wording (minimal, universal guidance)
- Thresholds (grounding min_mentions, promotion counts, etc.)
- Verification logic (what to check, how strictly)

### The Universality Test

**Every fix must pass this test:**

| Question | GOOD Fix | BAD Fix |
|----------|----------|---------|
| Does it help THIS book? | Yes | Yes |
| Would it help a book you've never seen? | **Yes** | No/Maybe |
| Does it regress previously-passing books? | No | Yes/Unknown |

**If a fix only helps the current book, it's the WRONG fix.** Go back and find a more general solution.

### Mandatory Regression Check

After implementing ANY fix:
1. Re-run analysis on at least 2 previously-analyzed books
2. Compare scores - if ANY category regresses, REVERT the fix
3. Only fixes that improve OR maintain ALL tested books are valid

This is slower. That's the point. Fewer, better fixes that actually move toward the universal formula.

### What You're Actually Tuning

| Tunable | Location | Universal Sweet Spot = |
|---------|----------|------------------------|
| Model selection | config.py | The model that balances cost/quality for all texts |
| Temperature | config.py | The setting that's creative but not hallucinatory |
| Grounding threshold | grounding.py | The min_mentions that catches hallucinations without filtering real characters |
| Promotion thresholds | characters.py | The mention counts that correctly identify protagonists across genres |
| Prompt wording | main_cast.py | The minimal guidance that extracts the right cast from ANY summary |

**You are searching for these numbers and words. Not adding code branches.**

---

## Fix Philosophy: Simple, Fluid, Efficient

**CRITICAL: Read this section before implementing ANY fix.**

### Prefer Programmatic Fixes Over Prompt Engineering

The previous approach of adding rules and defensive prompting **fell apart on longer, more complex books**. The LLM often ignored complex prompts entirely. Learn from this:

| Approach | When It Works | When It Fails |
|----------|---------------|---------------|
| **Adding prompt rules** | Never reliably | Always - LLM ignores long rule lists |
| **Defensive prompting** | Simple cases | Complex books - context rot, ignored rules |
| **Programmatic post-processing** | ✅ Reliably | Rarely - deterministic logic is predictable |
| **Soft prompts + hard verification** | ✅ Best approach | Rarely |

### The Right Pattern

```
❌ BAD: Add 10 rules to prompt hoping LLM follows them
✅ GOOD: Simple prompt + deterministic post-processing to enforce invariants

❌ BAD: "NEVER extract non-sentient objects" (LLM ignores this)
✅ GOOD: Let LLM extract what seems important, filter programmatically if needed

❌ BAD: Complex conditional logic in prompts
✅ GOOD: Let LLM express uncertainty (uncertain_aliases), verify deterministically
```

### Prompt Hygiene

- **Keep prompts SHORT** - Under 30 lines, 5 rules max
- **Don't accumulate rules** - If adding a rule line, remove at least one existing rule line (net prompt length must not increase)
- **Trust plot importance** - If something drives the narrative, it's probably worth extracting
- **Don't fight the LLM** - If it keeps ignoring a rule, the rule is wrong or unnecessary

### When to Use Each Approach

| Issue Type | Recommended Fix |
|------------|-----------------|
| LLM extracts wrong entity | Programmatic filter (post-processing) |
| LLM misses important entity | Check upstream data (summaries), not prompt |
| Alias not resolved | Improve mention_search, not prompt |
| Wrong canonical name | Programmatic normalization (prefer full names) |
| Role assignment wrong | Programmatic promotion by mention count |

**Remember:** The goal is a working pipeline, not a "smart" prompt. If the LLM needs 100 lines of rules, the architecture is wrong.

### Known Anti-Patterns (DO NOT REPEAT)

These approaches were tried and **failed repeatedly**:

| Anti-Pattern | Why It Failed | What To Do Instead |
|--------------|---------------|-------------------|
| "MANDATORY INCLUSIONS" in prompt | LLM ignored it completely | Check upstream summaries, use post-processing |
| "NEVER extract inanimate objects" | Blocked valid symbolic entities | Let LLM extract, mark `is_symbolic=True` |
| Adding NON_SENTIENT_KEYWORDS list | Book-specific overfitting, violated CLAUDE.md | Trust plot importance |
| 17-rule prompts | Context rot, LLM ignored most rules | Keep prompts under 5 rules |
| Defensive "HARD RULES" sections | Created false constraints | Use soft guidance + hard verification |
| Adding book-specific examples | Overfitting, violated CLAUDE.md | Use generic patterns only |

---

## 0. Orient

**Context Budget:** You have a limited context budget. Be efficient:
- Read `docs/CODEBASE_SUMMARY.md` FIRST for file locations (don't explore blindly)
- Don't re-read files you've already read this session
- Use Haiku (via `model: haiku` in Task agents) for exploration/search tasks
- Use line ranges when reading source files (e.g., `Read file.py lines 100-200`)

0a. Read `state/EVALUATION_STATE.md` to understand current issues and their priorities.
0b. Read `state/USER_NOTES.md` for any instructions from the user (if it exists and has content other than "(No notes)").
0c. Read `docs/output_quality.md` to understand the quality criteria.
0d. Read `docs/CODEBASE_SUMMARY.md` for file locations and common fix locations.
0e. Read `../CLAUDE.md` for coding standards (especially: no novel-specific hardcoding).
0f. **CRITICAL:** Search `docs/ATTEMPT_1_SUMMARY.md` for keywords related to the current issue.
0g. **CRITICAL - CHECK FOR EXTERNAL CHANGES:** Run `git log --oneline -10` to see recent commits.
    - If commits were made OUTSIDE the oracle loop (not by "Oracle Loop" or similar), those changes must be TESTED FIRST
    - If EVALUATION_STATE.md mentions "External Changes Applied", set phase to `awaiting_analysis` and EXIT
    - Do NOT apply additional fixes on top of untested external changes
    - The external changes may have already fixed the issue - run analysis first to verify
    Do NOT read the entire file - grep for relevant terms:
    ```bash
    grep -i "narrator\|merge\|alias" docs/ATTEMPT_1_SUMMARY.md
    ```
    Only read full sections if grep finds relevant matches.

> **DO NOT RETRY FAILED APPROACHES:** The summary documents approaches that had ZERO impact or caused regressions. Before implementing any fix, check if a similar approach was already tried. If so, you MUST try a DIFFERENT approach.

## 0.5 Efficient Exploration

**IMPORTANT: Minimize context usage during codebase exploration.**

When you need to search the codebase:
1. First check `docs/CODEBASE_SUMMARY.md` for file locations and line numbers
2. Use `model: haiku` when spawning Task agents for grep/search operations
3. Only deep-read specific functions once you've identified the exact location
4. Do NOT read entire files - use line ranges (e.g., `Read consensus.py lines 1571-1650`)

Example efficient pattern:
```
BAD: Read entire consensus.py (2500 lines) → wastes 50K+ tokens
GOOD: Read CODEBASE_SUMMARY.md → grep for function → Read consensus.py:1571-1650
```

For common issues, use the "Common Fix Locations" table in CODEBASE_SUMMARY.md.

**Character extraction fix locations (V2 is always active):**
- Main cast issues → `src/pipeline/character_extraction_v2/main_cast.py` - `CHARACTER_IDENTIFICATION_PROMPT` (Pass 1)
- Alias issues → `src/pipeline/character_extraction_v2/main_cast.py` - `ALIAS_RESOLUTION_PROMPT` (Pass 2) + `verify_aliases()`
- Competitive alias vote issues (if enabled) → `src/pipeline/character_extraction_v2/main_cast.py` - `_competitive_alias_vote()` prompt template
- Competitive merge rubric prompts → `src/pipeline/character_extraction/prompts.py` (STRICT/CONTEXTUAL/INCLUSIVE/NEUTRAL)
- Hallucinated characters → `grounding.py` - `GroundingGate`
- Narrator issues → `narrator.py` - `NARRATOR_DETECTION_PROMPT`
- Character merge issues → `consensus.py` lines 1571-1700
- Narrator issues → `analyzer.py` lines 1986-2076
- Profile issues → `analyzer.py` lines 1570-1700

## 1. ROOT CAUSE ANALYSIS (MANDATORY)

**DO NOT SKIP THIS PHASE.** Previous attempts failed because fixes were applied to the wrong location in the pipeline. For each issue identified by the evaluator:

### 1.1 Trace Data Flow

For each CRITICAL/HIGH issue:
1. **Identify where the symptom appears** (e.g., "incorrect character in HTML output")
2. **Trace backwards through the pipeline** to find where the incorrect data ORIGINATES:
   ```
   HTML Output ← Export ← AnalysisResult ← Agent ← Pipeline Stage ← Input
   ```
3. **Read the code at each stage** until you find where the problem is introduced

### 1.2 Document Root Causes

For EACH issue you plan to fix, you MUST document:

```markdown
### Issue: {description}
- **Symptom:** {what the evaluator observed}
- **Data flow trace:**
  1. Appears in: {export/report.html}
  2. Stored in: {AnalysisResult.characters}
  3. Generated by: {CharacterAgent.run()}
  4. **Originates in:** {src/pipeline/character_extraction/merge.py:function_name():line_N}
- **Root cause:** {why the code produces incorrect output}
- **Confidence:** {HIGH|MEDIUM|LOW}
```

### 1.3 Verify Before Proceeding

**DO NOT proceed to Phase 2 if:**
- You cannot identify the specific file/function/line where the issue originates
- Your confidence in the root cause is LOW
- The issue appears to originate in a different location than the symptom

**If blocked:** Add diagnostic logging to trace the data flow, then re-run analysis to gather evidence.

### 1.4 Root Cause Categories (Expanded)

When tracing the issue, consider ALL these categories:

### 1.5 Escalate Upstream (MANDATORY after 3 failed attempts)

Check the "Modification History" table in `state/EVALUATION_STATE.md`.

**If the same file or layer has been modified 3+ times without fixing the issue:**

You MUST look UPSTREAM. The bug is NOT in the file you keep modifying.

**Data Flow for Character Extraction V2:**
```
Source File (txt/pdf/epub)
       │
       ▼
┌─────────────────┐
│   Ingestion     │  ← Text normalization can destroy patterns
│ (base.py)       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Structure     │  ← Chapter boundaries affect everything
│ (chapter_detection/) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Summaries     │  ← If summaries confuse characters, so will extraction
│ (summarizer.py) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Character V2    │  ← EXTRACTS FROM SUMMARIES, not raw text
│ (main_cast.py)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Grounding Gate  │  ← Verifies against raw text
│ (grounding.py)  │
└─────────────────┘
```

**Key Insight:** If characters are wrong in V2, check SUMMARIES first.
The `main_cast.py` prompt reads summaries, not the source text.

**For Character Extraction issues, upstream layers are (in order):**
1. **Summaries** - Do the chapter summaries correctly distinguish the characters?
2. **NER/Entity extraction** - Is spaCy detecting both names?
3. **Ingestion** - Is the source text being corrupted or normalized incorrectly?
4. **Input file** - Is the original text correct?

**Diagnostic steps when escalating upstream:**

```bash
# 1. Check summaries for the problematic characters
grep -i "waldman\|krempe" ../output/{book_name}/analysis.json | head -20

# 2. If summaries already confuse them, the bug is in summary generation
# 3. If summaries are correct, the bug is in character extraction reading summaries

# 4. Check raw text extraction
grep -i "waldman\|krempe" ../test_texts/{book_name}.txt | head -10
```

**DO NOT modify the same layer again without upstream evidence.**

**Example escalation pattern:**
- Attempts 4, 5, 6: Modified `main_cast.py` → No improvement
- Escalation action: Check summaries for character confusion
- If summaries are wrong: Fix `summarizer.py` instead
- If summaries are correct: Add diagnostic logging to trace how main_cast.py processes them

---

### 1.6 Data Investigation (MANDATORY before modifying code)

**DO NOT MODIFY CODE until you have answered these questions about the actual data.**

#### 1.6.1 Character Issues - Check Which Pipeline Produced Them

```bash
# Check character IDs to determine source pipeline
jq '.characters[] | select(.canonical_name | test("PROBLEM_NAME"; "i")) | {id: .id, name: .canonical_name, mentions: .mention_count}' ../output/{book_name}/analysis.json
```

**ID Pattern Interpretation:**
- `main_cast_{i}` (e.g., `main_cast_2`) → Main cast extraction (LLM-based, from summaries)
- `supporting_{i}` (e.g., `supporting_6`) → Supporting cast extraction (NER-based, from text)
- 12-char hash (e.g., `50c19d96ece4`) → **F6 Summary Reconciliation** (analyzer.py:1220-1240)
- `split_{name}` (e.g., `split_the_creature`) → Semantic conflict split

**CRITICAL:** 12-char hash IDs are from F6 reconciliation, NOT supporting cast!
- F6 scans summaries for character names not found in the extraction pipeline
- It creates new Character entries with hashed IDs
- If fragments have hash IDs, the fix belongs in `analyzer.py` F6 logic, not main_cast.py or supporting.py

**If fragments have different ID patterns, they come from DIFFERENT PIPELINES!**
- Modifying `main_cast.py` won't fix fragments from supporting cast or F6 reconciliation
- You may need to fix BOTH pipelines or add cross-pipeline merge logic

#### 1.6.2 Pipeline Stages - Check If They Ran

```bash
# List all stage names that executed (profiling.stages is a list of objects, not a dict)
jq '._profiling.stages[].name' ../output/{book_name}/analysis.json

# Check if Character Profiles stage ran (note: stage name is "Character Profiles", NOT "Profile Generation")
jq '._profiling.stages[] | select(.name == "Character Profiles") | {name, duration_seconds, llm_calls}' ../output/{book_name}/analysis.json

# Check any other stage by name
jq '._profiling.stages[] | select(.name == "STAGE_NAME_HERE")' ../output/{book_name}/analysis.json
```

**If a stage is missing from profiling data, it DID NOT RUN.** This is a configuration or pipeline issue, not a logic bug.

#### 1.6.3 Verify Evaluation Claims

**DO NOT trust evaluation claims blindly.** Spot-check against actual data:

```bash
# Evaluation says "all pronunciation entries have null phonetic"
# Verify by checking actual data:
jq '[.pronunciations[] | select(.ipa != null)] | length' ../output/{book_name}/analysis.json

# Evaluation says "all profiles empty"
# Verify:
jq '[.characters[] | select(.physical_description != null)] | length' ../output/{book_name}/analysis.json
```

**Document your findings before proposing a fix:**
```markdown
### Data Investigation for Issue: {description}
- **Character IDs:** {main_cast_* / supporting_* / mixed}
- **Source pipeline:** {main cast / supporting cast / both}
- **Profiling data:** {stage ran / stage missing}
- **Evaluation claim verified:** {yes / no - actual finding}
```

---

| Category | Description | Where to Look |
|----------|-------------|---------------|
| **Code Logic Bug** | Algorithm/flow error in Python code | `src/pipeline/*/`, `src/agents/*.py` |
| **Prompt Issue** | LLM system prompt too strict/vague/wrong | `src/pipeline/*/proposers/*.py`, `*_validator.py` |
| **Configuration Issue** | Wrong model, chunk size, temperature, context length | `src/agents/config.py`, `analysis.json._config` |
| **Threshold Issue** | Confidence/filtering thresholds too aggressive | `src/pipeline/*/`, agent configs |
| **Data Flow Issue** | Information lost between pipeline stages | Trace through agent outputs |

### Configuration Fixes (when root cause is config)

If the issue is configuration-related:
1. Document current config values from `analysis.json._config`
2. Propose specific new values with rationale
3. Config changes should be made in `src/agents/config.py`:
   - `PipelineTuningConfig` for chunking params
   - `RECOMMENDED_AGENT_MODELS` for per-agent model/temperature settings
4. Test with re-analysis before declaring fix complete

Example config fix:
```python
# In src/agents/config.py - PipelineTuningConfig
# Before: character_llm_chunk_chars: int = 8000
# After (with rationale):
character_llm_chunk_chars: int = 12000  # Increased to capture full chapter context for long chapters
```

### Prompt Fixes (when root cause is prompt)

If the issue is a system prompt:
1. Identify which prompt file:
   - Chapter detection: `src/pipeline/chapter_detection/proposers/*.py`
   - Character extraction: `src/pipeline/character_extraction/proposers/*.py`
   - Summaries: `src/pipeline/chapter_summary/summarizer.py`
   - Pronunciation: `src/pipeline/pronunciation_guide/extractor.py`
2. Quote the problematic instruction
3. Propose minimal change (don't rewrite entire prompt)
4. Verify prompt change doesn't break other texts

Example prompt fix:
```python
# Before: "Identify all character names in the text"
# Problem: Too vague, misses nicknames
# After: "Identify all character names including nicknames, titles, and informal references"
```

## 2. Analyze Issues

Review the issues in `state/EVALUATION_STATE.md`, prioritized by severity:
- **CRITICAL**: Must fix before re-running - blocks progress
- **HIGH**: Significant impact on quality score
- **MEDIUM**: Noticeable but manageable impact
- **LOW**: Polish items, can defer

Focus on **CRITICAL** issues first. You may address **one issue per scoring category** per iteration (see Guidelines for category definitions and coupling warnings).

## 3. Investigate

Before making changes, understand the current implementation:

1. **Locate the relevant code** - Use the file hints in the issue description
   ```bash
   # Example searches
   grep -r "alias" src/agents/characters.py
   grep -r "merge" src/pipeline/character_extraction/
   ```

2. **Understand the current behavior** - Read the relevant functions/classes

3. **Identify the root cause** - Is it:
   - A prompt issue? → Edit prompts in the agent files
   - A code logic issue? → Edit `src/agents/` or `src/pipeline/`
   - A configuration issue? → Edit `src/agents/config.py`
   - A threshold issue? → Adjust parameters in the relevant module

## 4. Implement Fix

Make minimal, targeted changes:

1. **ONLY modify files identified in Phase 1** - Do not modify files where the symptom appears if the root cause is elsewhere
2. **Fix up to one issue per scoring category** (see Guidelines for category list)
3. **Make the smallest change that solves each problem**
4. **Do NOT refactor surrounding code** - Stay focused
5. **Do NOT add features** - Only fix the identified issues
6. **Follow coding standards** from `../CLAUDE.md`:
   - No novel-specific hardcoding (no "Gatsby", "Frankenstein", etc. in prompts)
   - Use generic guidance patterns

## 5. QUICK SMOKE TEST (MANDATORY)

**DO NOT SKIP THIS PHASE.** Before running the full test suite, verify your fix actually addresses the specific issue.

### 5.1 Choose Appropriate Smoke Test

| Issue Type | Smoke Test Approach | Expected Duration |
|------------|---------------------|-------------------|
| Character merge failure | Run character extraction on 2-3 chapters | 2-5 min |
| Narrator misidentification | Run narrator detection on mock data | 1-2 min |
| Pronunciation false positives | Run pronunciation on single chapter | 1-2 min |
| Chapter detection | Run structure detection on first 10% of text | 2-3 min |
| Summary hallucination | Run summary on single chapter, verify facts | 2-3 min |

### 5.2 Run Smoke Test

```bash
# Example: Test character extraction on specific chapters
python -c "
from src.pipeline.character_extraction import extract_characters
from src.ingestion import ingest_document

# Load first 2-3 chapters only
doc = ingest_document('test_texts/gatsby.txt')
chapters = doc.chapters[:3]

# Run extraction
result = extract_characters(chapters)

# Check if specific fix worked
print('Characters found:', [c.name for c in result.characters])
# Verify the specific issue is addressed
"
```

### 5.3 Evaluate Smoke Test Results

**PASS criteria:**
- The specific issue identified in Phase 1 is no longer present
- No obvious new regressions introduced

**FAIL criteria:**
- The issue still appears in output
- New errors introduced

**If smoke test FAILS:**
1. DO NOT proceed to commit
2. Return to Phase 1 and re-examine root cause
3. The fix location or approach is incorrect

## 6. Full Test Suite

Run relevant tests to ensure you haven't broken anything:

```bash
# Run all tests
pytest tests/ -v

# Or run specific tests for the area you modified
pytest tests/test_character_agent.py -v
pytest tests/test_alias_merging.py -v
# etc.
```

If tests fail:
- Fix the test failures before proceeding
- If the test itself is wrong, document why and fix the test

## 7. Document Changes

Update `state/EVALUATION_STATE.md`:

1. Move the fixed issue from "Current Issues" to "Fix History" with:
   - What was changed
   - Which file(s) modified
   - Brief description of the fix
   - **Root cause documented in Phase 1**
   - **Smoke test results**

2. Set `**Phase:**` to `awaiting_analysis`

3. Note any concerns about the fix or potential side effects

Example:
```markdown
## Fix History
- Attempt 1: Fixed chapter detection regex for Roman numerals (src/agents/structure.py)
- Attempt 2: Improved alias resolution to handle "FirstName LastName" -> "LastName" matching
  - Root cause: src/pipeline/character_extraction/merge.py:similarity_score() line 142 wasn't handling single-word names
  - Smoke test: Ran on chapters 1-3, confirmed "Jay Gatsby" now merges with "Gatsby"
  - Modified: src/pipeline/character_extraction/merge.py

## Next Action
Re-run analysis to verify fix
```

## 8. Commit and Exit

```bash
git add -A
git commit -m "Fix: {brief description of the fix}

Root cause: {file}:{function}:{line}
Smoke test: {PASS - brief description of what was verified}
Addresses: {issue description from EVALUATION_STATE.md}
Modified: {file paths}"
```

The loop will restart with PROMPT_analyze.md to re-run the pipeline with your fix.

## Guidelines

### Check Failed Approaches First
Before implementing ANY fix, read `docs/ATTEMPT_1_SUMMARY.md` and verify your approach wasn't already tried. Known failed approaches include:
- Filter ambiguous last-name-only entries (ZERO impact)
- Block family member merges globally (caused regressions)
- Adding diagnostic logging without implementing fixes (wasted attempt)
- Moving code position without addressing LLM merge decision logic

If the root cause is "LLM is rejecting valid merges", address the **LLM prompt or context**, not the candidate generation.

### One Fix Per Category
You may fix **one issue per scoring category** in a single iteration. The categories are:

| Category | Code Areas | Notes |
|----------|------------|-------|
| Structure Detection | `src/pipeline/chapter_detection/` | Coupled with Summaries |
| Character Extraction | `src/pipeline/character_extraction/` | Coupled with Profiles |
| Character Profiles | `src/pipeline/character_extraction/` | Coupled with Extraction |
| Chapter Summaries | `src/agents/summary_agent.py` | Coupled with Structure |
| Pronunciation Guide | `src/agents/pronunciation_agent.py` | Independent |
| HTML Presentation | `src/export/`, templates | Independent |

**Coupling warnings:**
- **Structure ↔ Summaries**: Chapter boundaries affect summary generation. If fixing both, test carefully.
- **Characters ↔ Profiles**: Same underlying data. Fixing both in one iteration is fine but changes may interact.

**Example valid multi-fix iteration:**
- Fix a Character Extraction issue AND a Pronunciation issue (independent categories)

**Example requiring caution:**
- Fix a Structure issue AND a Summaries issue (coupled - changes may interact)

### Preserve Working Behavior
Run tests before AND after your changes. If you break something, revert and try a different approach.

### Document the Why
Future iterations depend on understanding what was tried. Be explicit about your reasoning.

### If Stuck
If you can't figure out how to fix an issue after reasonable investigation:
1. Document what you tried in `state/EVALUATION_STATE.md`
2. Lower the issue priority or mark it as "deferred"
3. Move on to the next issue in the same text
4. The loop stays on this text until it passes - try different approaches

### If Root Cause Cannot Be Found
If Phase 1 fails to identify a clear root cause:
1. **Add diagnostic logging** to trace the data flow
2. **Document what you've traced** and where you're blocked
3. Set phase to `awaiting_analysis` with a note to run with diagnostics
4. DO NOT make speculative code changes without root cause confidence

### Avoid Over-Engineering
The goal is to cross the 8.0 quality threshold, not to achieve perfection. If the score is 7.8, make the minimum change needed to pass.
