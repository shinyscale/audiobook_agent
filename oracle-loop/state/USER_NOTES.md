# User Notes for Oracle Loop

## Current Guidance (Updated 2026-01-30 - JSON Model + Non-Human Entity Fix)

### JSON-Capable Model Fallback (NEW)

For models that don't support `json_mode` properly (e.g., `qwen3-next`), a user-configurable fallback is now available.

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

### Non-Human Entity Extraction (NEW)

The summarizer prompts now include non-human entity examples to help extract AI, monsters, and supernatural entities with agency.

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

### Oracle Loop Model Configuration (Updated 2026-01-30)

The oracle loop is now configured to use `qwen2.5:32b-instruct-q8_0` as the primary model:
- **Why:** This model properly supports `json_mode` for structured output
- **Previous:** `qwen3-next:80b-a3b-instruct-q8_0` (JSON incompatible, caused main cast extraction failures)
- **Config file:** `~/.config/audiobook_prep/gui_settings.json`

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
