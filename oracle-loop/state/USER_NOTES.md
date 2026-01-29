# User Notes for Oracle Loop

## Current Guidance (Updated 2026-01-29)

### Context-Aware Disambiguation (NEW)

For same-name character handling (e.g., father/son sharing "John"):

1. **Use multi-signal disambiguation** - Don't rely on string matching alone
   - Relationship markers: "his father John", "Sr./Jr.", "the elder"
   - Name-shape: If sentence has "Donaldson", attribute to "John Donaldson"
   - Temporal: "years ago", past perfect → older generation
   - Chapter presence: Prefer active character over just mentioned

2. **Don't drop low-confidence passages** - Mark as `ambiguous=True` instead
   - Downweight in profile generation, don't discard
   - Preserves data for characters with many weak-mention forms

3. **Implementation**: See `src/pipeline/character_profiling/name_disambiguator.py`
   - `NameAmbiguityMap` identifies which names are ambiguous
   - `ContextDisambiguator` applies signals in priority order
   - LLM fallback is gated (only when heuristics fail)

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
