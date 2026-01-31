# User Notes for Oracle Loop

## Current Guidance (Updated 2026-01-31 - Architectural Improvements)

### Co-occurrence Validation (NEW - 2026-01-31)

Added structural validation for merge decisions independent of LLM reasoning.

**What it does:**
- Computes pairwise Jaccard similarity of text chunk presence for all character pairs
- If two characters appear in same ~1-page chunks frequently → high confidence they're same person
- If they never appear together → flag merge for review or block it

**Key thresholds:**
- Score >= 0.5: High confidence merge (auto-approve)
- Score 0.2-0.5: Medium confidence (merge with logging)
- Score < 0.2: Low confidence (flag for TUI review)
- Score = 0.0: Never co-occur (don't merge)

**Usage:**
- Merge decisions are recorded in `pipeline_metadata.pending_reviews`
- Low-confidence merges have `needs_review: true`
- TUI can display these for narrator to verify

**Key files:**
- `src/models.py` - `MergeDecision` model
- `src/agents/characters.py` - `_compute_cooccurrence()`, `_should_merge()`, `_record_merge_decision()`

---

### Consolidated Pass 2 Alias Resolution (NEW - 2026-01-31)

Changed alias resolution from per-character to consolidated view.

**Old approach (problematic):**
```
Pass 1: "Who are characters?" → [Victor, the Creature, the narrator, ...]
Pass 2 (loop): For each character, "What are X's aliases?"
```
Problem: When asking about Victor, LLM didn't know "the narrator" was also extracted.

**New approach:**
```
Pass 1: "Who are characters?" → [Victor, the Creature, the narrator, ...]
Pass 2 (single): "Here are ALL characters. Assign aliases AND identify duplicates."
```
LLM returns `merge_into` field to indicate duplicates (e.g., "the narrator" merge_into "Victor Frankenstein").

**Benefits:**
- LLM sees full context before making alias decisions
- Can identify duplicates upfront (reduces Step 3.6 activations)
- Falls back to per-character if consolidated fails

**Key files:**
- `src/pipeline/character_extraction_v2/main_cast.py`:
  - `CONSOLIDATED_ALIAS_PROMPT` - new prompt with full character list
  - `_process_consolidated_pass2()` - handles merge_into directives
  - `_extract_two_pass_per_character()` - fallback to original approach

---

### Defensive Step Measurement (NEW - 2026-01-31)

Steps 3.4, 3.6, 3.7, 3.8 are defensive fixes for upstream LLM errors. Now tracked in metadata.

**What gets tracked:**
```json
"defensive_steps": {
  "step_3_4_same_firstname_merges": 0,
  "step_3_6_alias_canonical_merges": 0,
  "step_3_7_titled_splits": 0,
  "step_3_8_semantic_splits": 0,
  "total_activations": 0
}
```

**How to interpret:**
- `total_activations = 0`: Upstream extraction worked perfectly
- `total_activations > 0`: Defensive steps had to fix something
- High counts suggest upstream extraction needs improvement

**Usage:** After analysis, check `pipeline_metadata.defensive_steps` to see if architectural improvements are reducing defensive step reliance.

---

## CRITICAL: Model Configuration Rules (DO NOT CHANGE)

**The oracle loop MUST NOT change the model configuration.** The user has explicitly set the model and any changes require user approval.

### Current Model: `qwen3-next:80b-a3b-instruct-q8_0`

This model is SET BY THE USER and must be used for all analysis. Do NOT:
- Switch to qwen2.5:32b or any other model
- Claim "compatibility issues" as a reason to change models
- Modify `~/.config/audiobook_prep/gui_settings.json`

### If JSON Issues Occur

1. **Use wrapped object prompts** - All LLM prompts now use wrapped format:
   - `main_cast.py`: `{"characters": [...]}`
   - `chapter_detection/proposers/llm.py`: `{"markers": [...]}` and `{"breaks": [...]}`
2. **If a fallback is needed**, use `nemotron-3-nano:30b` (NOT qwen2.5:32b)
3. **Report the issue** - Do not silently switch models; document what happened

### Why qwen3-next?

- MoE architecture is ~3x faster than dense qwen2.5:32b on DGX Spark
- Has already successfully analyzed Gatsby before
- Works correctly with wrapped JSON object prompts

---

## Current Guidance (Updated 2026-01-30 - Structure Detection Wrapped JSON)

### Structure Detection Wrapped JSON Format (NEW - 2026-01-30)

Applied wrapped JSON format fix to structure detection LLM proposers to match qwen3-next requirements.

**Problem:** qwen3-next was returning `{"error": "No explicit chapter markers found..."}` instead of `[]` when no markers were found. This caused infinite retry loops and structure detection failures.

**Solution:** Updated both prompts to use wrapped format with strict instructions:

**MARKER_SYSTEM_PROMPT** now includes:
```
MANDATORY JSON FORMAT - You MUST use this EXACT structure:
{"markers": [...]}

FORBIDDEN RESPONSES - These will cause system failure:
- {"error": "..."} - NEVER use an error field
- {"message": "..."} - NEVER use a message field
```

**NARRATIVE_SYSTEM_PROMPT** uses same pattern with `{"breaks": [...]}`.

**Files modified:**
- `src/pipeline/chapter_detection/proposers/llm.py`:
  - `MARKER_SYSTEM_PROMPT` - added mandatory format and forbidden responses
  - `MARKER_PROMPT_TEMPLATE` - changed to `{"markers": [...]}` format
  - `NARRATIVE_SYSTEM_PROMPT` - added mandatory format and forbidden responses
  - `NARRATIVE_PROMPT_TEMPLATE` - changed to `{"breaks": [...]}` format
  - `_analyze_chunk()` in both proposers - updated to unwrap the format

**Backward compatibility:** Parsing code accepts both wrapped format and raw arrays.

---

## Previous Guidance (2026-01-30 - Wrapped JSON Prompts + MoE Model)

### Wrapped JSON Object Prompts (NEW - 2026-01-30)

Changed prompt format from raw arrays to wrapped objects for consistent JSON output across models.

**Problem:** When prompts requested raw JSON arrays like `[{...}]`, some models (especially MoE models) would return single objects or malformed output.

**Solution:** Request wrapped objects explicitly:
```
Output format - return a JSON object with a "characters" array:
{"characters": [{"canonical_name": "Name", "role": "protagonist", ...}]}
```

**Testing results:**
| Model | Raw Array Prompt | Wrapped Object Prompt |
|-------|------------------|----------------------|
| qwen2.5:14b | Works | Works |
| qwen2.5:32b | Works | Works |
| qwen3-next:80b-a3b-instruct | Single object (broken) | Works |
| nemotron-3-nano:30b | Works | Works |
| gpt-oss:20b | Malformed | Malformed |
| gpt-oss:120b | Malformed | Malformed |

**Files modified:**
- `src/pipeline/character_extraction_v2/main_cast.py`:
  - `MAIN_CAST_PROMPT` (lines 47-72) - wrapped object format
  - `CHARACTER_IDENTIFICATION_PROMPT` (lines 100-115) - wrapped object format
  - System prompt (line 478) - updated for JSON compatibility

**Code already handles wrapped format:** The `_parse_pass1_results()` and `_parse_profiles()` methods already unwrap `{"characters": [...]}` format.

---

### Oracle Loop Model Configuration (Updated 2026-01-30)

Now using `qwen3-next:80b-a3b-instruct-q8_0` (MoE model) for all phases:
- **Why:** ~3x faster than dense qwen2.5:32b on DGX Spark (MoE activates ~24B params per forward pass)
- **JSON compatibility:** Works with wrapped object prompts (updated above)
- **Config file:** `~/.config/audiobook_prep/gui_settings.json`

| Model | Architecture | Speed on DGX Spark |
|-------|--------------|-------------------|
| qwen2.5:32b | Dense (32B active) | Slow (~3+ hours for Gatsby) |
| qwen3-next:80b | MoE (~24B active) | ~3x faster |

---

### JSON-Capable Model Fallback (Available)

For models that don't support `json_mode` properly, a user-configurable fallback is available.

**CLI Usage:**
```bash
audiobook-prep analyze book.pdf --json-model qwen2.5:32b-instruct-q8_0
```

**How it works:**
1. Primary model attempts JSON extraction
2. If JSON parsing fails AND `--json-model` is set, retry with fallback model
3. Fallback is logged clearly: "Primary model failed JSON extraction, retrying with..."

**Key files:**
- `src/agents/config.py` - `json_model` field in OrchestratorConfig
- `src/analyzer.py` - `_get_json_llm_client()` method
- `src/pipeline/character_extraction_v2/main_cast.py` - fallback in `_extract_single_pass()`, `_extract_two_pass()`
- `src/pipeline/chapter_summary/summarizer.py` - fallback in summary methods
- `src/cli.py` - `--json-model` CLI argument

**Note:** This is USER-CONFIGURABLE, not a hardcoded fallback. The user explicitly chooses the fallback model.

---

### Non-Human Entity Extraction

The summarizer prompts include non-human entity examples to help extract AI, monsters, and supernatural entities with agency.

**Change in `src/pipeline/chapter_summary/summarizer.py`:**
```python
# JSON example now shows:
"active_characters": ["Michael", "Sarah", "HAL", "the Monster"],

# With guidance note:
"Note: Include non-human entities with names (AI systems, creatures, supernatural beings)
in active_characters if they act with agency in the chapter."
```

**Impact:** For "I Have No Mouth, and I Must Scream", AM (the sentient supercomputer) now appears in `characters_present`.

---

## Previous Guidance (2026-01-29 - Upstream Data Fix Applied)

### Context-Aware Disambiguation (MAJOR FIX)

For same-name character handling (e.g., father/son sharing "John"):

**Signal priority (highest to lowest):**

1. **Relationship markers (0.95)** - "his father John", "Sr./Jr.", "the elder"
   - **NEW:** Added memoir-style patterns:
     - Elder: "my brother John", "poor John" → full-name character
     - Younger: "the boy", "my nephew" → short-name character
2. **Name-shape (0.90)** - If sentence has "Donaldson", attribute to "John Donaldson"
3. **Temporal markers (0.80)** - "years ago", past perfect → older generation
   - Now checks SURROUNDING CONTEXT (2 sentences before) for temporal markers
4. **Chapter-range prior (0.85)** - Uses `chapters_present` from IdentifiedCharacter
   - **FIXED:** `chapters_present` now populated for supporting cast (was hardcoded to `[]`)
   - **NEW:** Falls back to `summary_map.character_appearances` if empty
   - If only one candidate appears in the current chapter, prefer them
5. **Chapter presence (0.70)** - Prefer active character from chapter summary
6. **LLM fallback (0.70)** - Gated, uses `temperature=0.1`, `max_tokens=128`

**Critical upstream fix (attempt 13):**
- `src/agents/characters.py` now runs deterministic mention search for supporting cast
- `chapters_present` and `mentions` fields are now populated (not hardcoded empty)
- This unblocks the chapter-range disambiguation signal

**Key files:**
- `src/agents/characters.py` - supporting cast data population
- `src/pipeline/character_profiling/name_disambiguator.py` - all disambiguation signals
- `src/pipeline/character_profiling/passage_gatherer.py` - context_window (2000 chars)
- `src/llm/client.py` - temperature and max_tokens override for per-call control

---

### Narrator Perspective Contamination Filter (NEW)

For first-person narratives, non-narrator characters can get contaminated with narrator evidence:
- "I repaid John's debts" describes the NARRATOR's action, not John's character
- But naive extraction assigns this to John's profile

**Two-layer defense:**

1. **Block ambiguous narrator names** (`pipeline.py`)
   - If narrator name is ambiguous (e.g., "John" when "John Donaldson" exists)
   - Clear narrator assignment to prevent first-person passage gathering for wrong character

2. **Filter narrator-perspective passages** (`perspective_filter.py`)
   - For NON-narrators in first-person text
   - Exclude passages where narrator is subject ("I did X to John")
   - KEEP passages where character is:
     - Co-subject: "John and I drove the ambulance"
     - Appositive: "my nephew John was brave"
     - Subject: "John drove the ambulance"

**Implementation**: See `src/pipeline/character_profiling/perspective_filter.py`
- `should_exclude_narrator_perspective_for_non_narrator()` - core filter function
- Applied in both `passage_gatherer.py` and `summary_evidence.py`

**When to use**: Any first-person narrative where narrator mentions other characters

---

### Keyword Lists Are Forbidden

**DO NOT** create deny-list filters like:
- `object_keywords = {"clock", "bell", "door"...}`
- `mundane_location_keywords = {"library", "room", "house"...}`
- Any `*_keywords` set used to REJECT candidates

**WHY:** These are book-specific overfitting. The list can never be complete. The next book will have a word not in your list.

### What To Do Instead

1. **Clarify prompts** - Teach the LLM the CONCEPT, not a list of words
   - Example: "Include entities with AGENCY or POWER, not settings where events happen"

2. **Use universal invariants** - Grounding, NER, mention thresholds
   - These work across all books without vocabulary dependence

3. **Reference lexicons ARE allowed** - For recognition, not rejection
   - Military ranks, religious titles, honorifics (Mr., Dr., Colonel, Sister)
   - These help PARSE names, not filter them

### Recent Changes

A prompt fix was applied to `CHARACTER_IDENTIFICATION_PROMPT` to distinguish:
- **Characters with agency** (people, symbolic objects with power) → EXTRACT
- **Settings/backdrops** (library, room, house) → DO NOT EXTRACT

This is being tested on berenice. If it works, the same prompt will help all future books without modification.

### If the Prompt Fix Doesn't Work

1. Check the chapter summaries - do they describe the library as having agency?
2. Check if the LLM is ignoring the prompt - add diagnostic logging
3. DO NOT fall back to keyword lists - find the root cause instead

---

## Root Cause Fixes vs Salvage Code

### Salvage Code Is Forbidden

**DO NOT** add increasingly complex recovery heuristics like:
- Regex-based JSON field extraction
- Brace-balanced parsing with fallback chains
- "Salvage what we can" from malformed output

**WHY:** Salvage code chases symptoms. Each new failure pattern requires new salvage logic. The codebase grows brittle and complex.

### What To Do Instead

1. **Ask why the output is malformed** - Is the prompt unclear? Is the model misconfigured?

2. **Fix at the source** - Examples:
   - LLM returns non-JSON → Enable `json_mode=True` at provider level
   - LLM misunderstands task → Clarify the prompt
   - LLM output truncated → Check max_tokens, simplify expected output

3. **Leverage provider capabilities** - Ollama's `format: "json"`, OpenAI's `response_format`

---

## Relationship Extraction: Use Focused LLM Call (No Keyword Salvage)

If relationship information appears in evidence text (e.g., "beloved cousin named John Donaldson") but the
structured `relationships` dict is empty, **do NOT** add regex/keyword-list salvage code.

Instead, use a **dedicated second LLM call** that only extracts relationships from:
- The current character name
- Other characters (canonical + aliases)
- The already-extracted evidence statements/quotes

This keeps prompts simple and avoids brittle vocabulary-dependent heuristics.

### Recent Example (2026-01-28)

**Bad approach (reverted):**
- Oracle loop added ~140 lines of regex salvage code for malformed JSON
- Score dropped from 6.5 to 5.0 - the salvage code made things worse

**Good approach (applied):**
- Added `json_mode=True` to LLMClient.query() (~14 lines)
- Ollama now enforces JSON at token-sampling level
- Provider physically cannot emit tokens that break JSON structure

---

## Hardcoded Model Fallbacks Are Forbidden

**DO NOT** add code that silently swaps to a different model when extraction fails:
```python
# BAD - hardcoded model fallback
if not result:
    fallback_config = LLMConfig(model="qwen2.5:32b-instruct-q8_0", ...)
    result = fallback_client.query(...)
```

**WHY:**
1. **Environment-specific**: The fallback model may not exist on the user's system
2. **Masks the problem**: User doesn't know their configured model is incompatible
3. **Unpredictable behavior**: Different models produce different results silently

### What To Do Instead

1. **Detect model errors at the LLM client layer** (`src/llm/client.py`)
   - If model returns `{"error": ..., "message": ...}` instead of expected data, treat as failure
   - Log a clear warning: "This model may not support json_mode properly"

2. **Fail clearly, don't silently swap**
   - Return empty/None and let the pipeline handle it
   - User sees the error and can choose a compatible model

3. **Document model requirements**
   - Some models don't support structured JSON output
   - Compatible models: llama3.2, qwen2.5, gpt-4o-mini, claude-3
   - Incompatible: Some reasoning models that ignore format instructions

### Recent Example (2026-01-29)

**Bad approach (reverted):**
- Oracle loop added 33-line fallback to hardcoded "qwen2.5:32b-instruct-q8_0"
- Would fail on systems without that exact model

**Good approach (applied):**
- Added error-response detection in `_extract_json()` (~10 lines)
- If model returns `{"error": ...}`, logs warning and returns None
- User sees clear message about model compatibility
