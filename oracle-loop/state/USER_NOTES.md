# User Notes for Oracle Loop

## Current Guidance (Updated 2026-01-28)

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
