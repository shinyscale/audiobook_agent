# User Notes for Oracle Loop

## Current Guidance (Updated 2026-01-29 - Upstream Data Fix Applied)

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

### Recent Example (2026-01-28)

**Bad approach (reverted):**
- Oracle loop added ~140 lines of regex salvage code for malformed JSON
- Score dropped from 6.5 to 5.0 - the salvage code made things worse

**Good approach (applied):**
- Added `json_mode=True` to LLMClient.query() (~14 lines)
- Ollama now enforces JSON at token-sampling level
- Provider physically cannot emit tokens that break JSON structure
