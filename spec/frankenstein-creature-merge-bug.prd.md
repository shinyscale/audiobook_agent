# PRD: Frankenstein Creature/Character Merge Bug

## Status: Partially Fixed (Creature/De Lacey resolved, fragmentation remains)

**Created:** 2026-01-23
**Updated:** 2026-01-24
**Priority:** Critical
**Affected Text:** Frankenstein (and likely other novels with unnamed characters described by multiple terms)
**Oracle Loop Attempts:** 15 (loop killed for manual investigation)

---

## Latest Finding (2026-01-24)

**The creature/De Lacey merge is FIXED** (Attempt 14), but character fragmentation persists.

**Critical Discovery:** The oracle loop was modifying the WRONG PIPELINE for 5+ attempts.

| Fragment | ID | Source |
|----------|-----|--------|
| "the creature" | `main_cast_2` | Main cast ✓ |
| "the monster" | `50c19d96ece4` | **Supporting cast** |
| "the creature (implied presence)" | `44707147ad9b` | **Supporting cast** |

The loop modified `main_cast.py` repeatedly, but 3/4 fragments come from **supporting cast** (NER-based extraction). The main cast merge logic never sees them.

**Oracle loop prompts updated** to require data investigation before modifying code (commit 7e66665).

---

## Problem Statement

The V2 character extraction pipeline incorrectly merges unrelated characters when they share descriptive patterns or appear in proximity in chapter summaries. The most severe manifestation: **"the creature" (Frankenstein's monster) is listed as an alias of "the old man (De Lacey)"** - two completely different characters who merely interact in the story.

**Expected Character Entries:**
- "The Creature" with aliases ["the monster", "the fiend", "the daemon", "the wretch", "the being"]
- "De Lacey" / "the old man (De Lacey)" - separate character, the blind father of Felix and Agatha

**Actual Output (Attempt 12):**
```json
{
  "canonical_name": "the old man (De Lacey)",
  "aliases": ["the old man", "the creature"],
  "is_narrator": true
}
```
Plus 4 orphaned creature-related entries:
- "the creature (implied)" - 1 mention
- "creature" - 1 mention
- "the monster" - 3 mentions
- (creature as wrong alias of De Lacey)

**Impact:**
- Score regression: 7.05 (attempt 5) → 6.40 (attempt 12)
- De Lacey incorrectly marked as narrator (because creature narrates parts)
- Character list unusable for audiobook narrator preparation

---

## Why This Bug Is Hard

### The Whack-a-Mole Pattern

Every fix catches one pattern but introduces or misses another:

| Attempt | Fix Applied | Outcome |
|---------|-------------|---------|
| 1-7 | MAIN_CAST_PROMPT modifications | No effect - LLM ignores rules |
| 8 | `merge_descriptive_entities()` in main_cast.py | Can't merge if creature isn't a profile |
| 10 | `_are_different_titled_people()` fix | Fixed Waldman/Krempe, missed creature |
| 12 | `_split_wrongly_merged_titled_characters()` | Fixed Waldman/Krempe, **introduced** creature/De Lacey merge |
| 13 | `_split_semantic_conflicts()` | Splits creature from De Lacey, but creates 5 separate entries |

### The Fundamental Issue

Post-processing can only **fix bad merges** or **merge existing profiles**. It cannot:
1. Create proper character profiles the LLM failed to extract
2. Add aliases the LLM didn't identify
3. Fix fundamentally wrong LLM interpretation of character relationships

---

## Root Cause Analysis

### Root Cause #1: LLM Misinterprets Character Proximity as Identity

**Location:** `src/pipeline/character_extraction_v2/main_cast.py` - `MAIN_CAST_PROMPT`

**Problem:** The LLM reads summaries like:
> "the creature knocks on the cottage door, enters, and begins a tense conversation with the blind De Lacey"

And somehow concludes "the creature" is a descriptive term FOR De Lacey, rather than a separate character INTERACTING WITH De Lacey.

**Evidence:** The summaries are accurate - they clearly describe two characters:
```
"the creature confesses he is seeking protection from the very family
he has secretly loved and aided—Felix, Safie, and Agatha"

"Felix violently attacks the creature, dragging him from the old man's
embrace and striking him with a stick"
```

The creature and De Lacey are clearly separate entities in these summaries. The LLM is failing to interpret this correctly.

**Contributing Factor:** The MAIN_CAST_PROMPT is 140+ lines with 13 rules. Complex prompts with many rules often lead to LLM confusion - the model may focus on some rules while ignoring others.

### Root Cause #2: No Semantic Validation at Extraction Time

**Location:** `src/pipeline/character_extraction_v2/main_cast.py` - `extract()` method

**Problem:** The LLM returns character profiles with aliases, and the code trusts them. There's no validation that aliases are semantically compatible with the canonical name.

**Example of Invalid Alias:**
- Canonical: "the old man (De Lacey)" - a human descriptor
- Alias: "the creature" - a supernatural/created being descriptor

These are fundamentally incompatible semantic categories, but the extraction pipeline accepts them.

**Current Validation:**
1. `verify_aliases()` - checks title+surname patterns (catches "Mr. White" ≠ "Mrs. White")
2. `merge_descriptive_entities()` - merges existing "the X" profiles by semantic cluster

**Missing Validation:** Neither function validates that an alias is semantically compatible with its canonical name.

### Root Cause #3: Semantic Clusters Are Incomplete

**Location:** `src/pipeline/character_extraction_v2/main_cast.py` - `merge_descriptive_entities()`

**Problem:** The semantic clusters only handle MERGING of separate profiles:
```python
semantic_clusters = [
    {"the creature", "the monster", "the fiend", "the daemon", "the being", "the wretch"},
    {"the old man", "the elder", "the old one"},
]
```

But there's no logic to PREVENT cross-cluster merging. "The creature" and "the old man" are in different clusters, but the LLM can still put one as an alias of the other.

### Root Cause #4: Post-Processing Creates Orphan Entries

**Location:** `src/agents/characters_v2.py` - `_split_semantic_conflicts()` (Attempt 13)

**Problem:** When the semantic conflict splitter detects "the creature" as a wrongly-merged alias, it:
1. Removes "the creature" from De Lacey's aliases ✓
2. Creates a NEW character entry "the creature" with 0 mentions and no aliases ✗

This leaves us with 5 separate creature-related entries that should be ONE character:
- "the creature" (split from De Lacey, 0 mentions)
- "the creature (implied)" (1 mention)
- "creature" (1 mention)
- "the monster" (3 mentions)
- (Missing: "the fiend", "the daemon", etc.)

### Root Cause #5: Plot Summary Has Factual Error

**Location:** `src/pipeline/chapter_summary/summarizer.py` output

**Problem:** The plot summary contains:
> "His journey takes a profound turn when he encounters a mysterious man in a sledge, who is later revealed to be the Creature—Victor Frankenstein's creation"

This is **factually incorrect**. The man Walton rescues from the sledge is **Victor Frankenstein**, not the Creature. The Creature is the giant figure Walton sees on a DIFFERENT sledge being pulled by dogs.

**Impact:** This error may contribute to downstream character confusion, though it's not the primary cause of the De Lacey/creature merge.

---

## Failed Approaches (Do Not Retry)

### Approach 1: Adding More Rules to MAIN_CAST_PROMPT
- **Attempts:** 1, 2, 6, 7
- **Result:** No measurable improvement
- **Why it failed:** LLM either ignores complex rules or follows some while violating others
- **Lesson:** More rules ≠ better extraction

### Approach 2: Post-Processing Merge Logic
- **Attempts:** 4, 5, 8, 9
- **Files:** `main_cast.py` - `merge_descriptive_entities()`
- **Result:** Can only merge EXISTING profiles; if creature isn't a profile, nothing to merge
- **Lesson:** Can't fix what the LLM didn't create

### Approach 3: Defensive Split by Title Pattern
- **Attempts:** 10, 11, 12
- **Files:** `characters_v2.py` - `_split_wrongly_merged_titled_characters()`
- **Result:** Fixed Waldman/Krempe, but doesn't catch "the X" patterns
- **Lesson:** Pattern-based splits need to cover ALL patterns

### Approach 4: Defensive Split by Semantic Conflict
- **Attempt:** 13 (pending test)
- **Files:** `characters_v2.py` - `_split_semantic_conflicts()`
- **Expected Result:** Will split creature from De Lacey, but leaves 5 orphan entries
- **Lesson:** Splitting isn't enough - need to also MERGE the split entries

---

## Data Flow Analysis

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           V2 CHARACTER EXTRACTION                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Chapter Summaries (ACCURATE)                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ "the creature knocks on the cottage door, enters, and begins a      │   │
│  │  tense conversation with the blind De Lacey"                        │   │
│  │                                                                     │   │
│  │ ✓ Summaries correctly distinguish creature and De Lacey             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              │                                              │
│                              ▼                                              │
│  MAIN_CAST_PROMPT (140+ lines, 13 rules)                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Rule 5: Unnamed characters with descriptive handles...              │   │
│  │ Rule 9: Different titles + surnames = different people...           │   │
│  │ Rule 11: Only group if same person in same contexts...              │   │
│  │                                                                     │   │
│  │ ✗ LLM ignores/misinterprets rules, merges creature into De Lacey   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              │                                              │
│                              ▼                                              │
│  LLM Output (WRONG)                                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ { "canonical_name": "the old man (De Lacey)",                       │   │
│  │   "aliases": ["the old man", "the creature"] }  ← WRONG!            │   │
│  │                                                                     │   │
│  │ { "canonical_name": "the monster", "aliases": [] }  ← Separate      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              │                                              │
│                              ▼                                              │
│  Post-Processing (CAN'T FULLY FIX)                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ verify_aliases() → Only checks title+surname patterns               │   │
│  │ merge_descriptive_entities() → Only merges existing profiles        │   │
│  │ _split_semantic_conflicts() → Splits but creates orphans            │   │
│  │                                                                     │   │
│  │ ✗ Cannot create profiles LLM didn't extract                         │   │
│  │ ✗ Cannot add aliases LLM didn't identify                            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              │                                              │
│                              ▼                                              │
│  Final Output (STILL BROKEN)                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ 5 separate creature entries instead of 1                            │   │
│  │ De Lacey incorrectly marked as narrator                             │   │
│  │ Character list unusable                                             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Proposed Solutions

### Solution A: Two-Pass Extraction (Recommended)

**Concept:** Separate named and unnamed character extraction to prevent cross-contamination.

**Implementation:**
1. **Pass 1: Named Characters Only**
   - New prompt: "Extract only characters with proper names (first name, last name, or both)"
   - Output: Victor Frankenstein, Elizabeth Lavenza, Henry Clerval, Robert Walton, etc.

2. **Pass 2: Unnamed Characters Only**
   - New prompt: "Extract characters referred to only by descriptive terms (the creature, the old man, etc.)"
   - Input includes Pass 1 results to avoid confusion
   - Output: The Creature (with aliases), the old man (De Lacey), etc.

3. **Merge passes** with validation

**Pros:**
- Prevents cross-contamination between named and unnamed characters
- Simpler prompts = more reliable LLM responses
- Each pass can have specialized validation

**Cons:**
- Two LLM calls instead of one (cost/latency)
- Need to handle edge cases (characters with both proper names AND descriptive handles)

**Estimated Effort:** Medium

### Solution B: Pre-Extraction Unnamed Character Detection

**Concept:** Programmatically identify potential unnamed characters BEFORE LLM extraction.

**Implementation:**
1. Scan summaries for "the X" patterns (e.g., "the creature", "the monster", "the old man")
2. Group patterns by semantic similarity using predefined clusters
3. Pass these pre-identified groups to the LLM as hints:
   ```
   HINT: The following descriptive terms likely refer to the same unnamed character:
   - Group 1: "the creature", "the monster", "the fiend", "the daemon"
   - Group 2: "the old man", "De Lacey"
   ```

**Pros:**
- Single LLM call
- Leverages programmatic pattern detection for reliability
- LLM has explicit guidance on grouping

**Cons:**
- Pre-defined clusters may miss novel patterns
- Still relies on LLM to follow hints

**Estimated Effort:** Medium

### Solution C: Semantic Validation Layer

**Concept:** Add a validation layer that rejects semantically incompatible aliases.

**Implementation:**
1. Define semantic categories:
   - CREATURE: creature, monster, fiend, daemon, wretch, being
   - HUMAN_MALE: man, old man, gentleman, father, boy
   - HUMAN_FEMALE: woman, old woman, lady, mother, girl
   - etc.

2. After LLM extraction, validate each alias:
   ```python
   def is_valid_alias(canonical: str, alias: str) -> bool:
       canonical_category = get_semantic_category(canonical)
       alias_category = get_semantic_category(alias)
       return canonical_category == alias_category or categories_compatible(...)
   ```

3. Reject incompatible aliases and create separate entries

**Pros:**
- Works with existing single-pass extraction
- Catches a broad class of semantic conflicts
- Deterministic validation

**Cons:**
- Still leaves orphan entries that need merging
- Need comprehensive category definitions
- May have edge cases with ambiguous terms

**Estimated Effort:** Low-Medium

### Solution D: Simplified Prompt + Aggressive Post-Processing

**Concept:** Dramatically simplify the prompt and rely more on post-processing.

**Implementation:**
1. Simplify MAIN_CAST_PROMPT to 5-7 core rules only
2. Accept that LLM output will have errors
3. Build robust post-processing to:
   - Split ALL incompatible semantic pairs
   - Merge ALL entries within same semantic cluster
   - Re-search mentions for merged entries

**Pros:**
- Simpler prompt may work better
- Post-processing is deterministic and testable

**Cons:**
- Post-processing complexity increases
- May create new edge cases

**Estimated Effort:** Medium

### Solution E: Different/Larger Model

**Concept:** The current model may lack capacity for this task.

**Implementation:**
- Try Claude 3.5 Sonnet, GPT-4, or larger Qwen model for character extraction
- Keep smaller model for other tasks (summaries, pronunciation)

**Pros:**
- May "just work" with more capable model
- Minimal code changes

**Cons:**
- Higher cost
- May still fail on edge cases
- Doesn't address fundamental architecture issues

**Estimated Effort:** Low

---

## Recommended Approach

**Primary:** Solution A (Two-Pass Extraction) + Solution C (Semantic Validation)

**Rationale:**
1. Two-pass extraction prevents the fundamental cross-contamination problem
2. Semantic validation catches any errors that slip through
3. Together they address both extraction AND validation gaps
4. Both are testable and debuggable

**Implementation Order:**
1. Implement Solution C (semantic validation) first - quick win, catches current bug
2. Implement Solution A (two-pass) if validation alone isn't sufficient
3. Consider Solution E (larger model) if both fail

---

## Debug Commands

```bash
# Check current character entries for creature/De Lacey
jq '.characters[] | select(.canonical_name | test("creature|lacey|old man|monster"; "i")) |
    {name: .canonical_name, aliases: .aliases, mentions: .mention_count, narrator: .is_narrator}' \
    output/frankenstein/analysis.json

# Check summaries for creature/De Lacey context
jq -r '.structure[] | .summary' output/frankenstein/analysis.json | \
    grep -i -o "[^.]*creature[^.]*\." | head -20

# Count creature-related entries
jq '[.characters[] | select(.canonical_name | test("creature|monster|fiend"; "i"))] | length' \
    output/frankenstein/analysis.json

# Check if semantic split is working (after attempt 13)
grep -i "SEMANTIC CONFLICT" /path/to/analysis.log

# Verify De Lacey is NOT marked as narrator
jq '.characters[] | select(.canonical_name | test("lacey"; "i")) | .is_narrator' \
    output/frankenstein/analysis.json
```

---

## Acceptance Criteria

1. **"The Creature" exists as a single character** with aliases including:
   - "the monster"
   - "the fiend"
   - "the daemon"
   - "the wretch"
   - "the being"

2. **"De Lacey" / "the old man (De Lacey)" is a separate character** with:
   - NO creature-related aliases
   - `is_narrator: false`

3. **No orphan creature entries** - all creature-related terms merged into one entry

4. **Score improvement** - Character Extraction score ≥ 7/10 (currently 4-5/10)

5. **No regression** on previously-fixed issues:
   - Waldman/Krempe remain separate
   - Robert Walton correctly merged with "Captain Walton"

---

## Related Issues

- M. Waldman / M. Krempe merge (FIXED in attempt 12)
- Robert Walton / Captain Walton merge (FIXED in attempt 10)
- 54 characters (too many) - need filtering of generic entries
- All character profiles have null physical_description and empty relationships
- Plot summary factual error (Victor vs Creature in Walton's rescue)

---

## Appendix: Modification History

| Attempt | Issue | Files Modified | Result |
|---------|-------|----------------|--------|
| 1 | Waldman/Krempe | main_cast.py (prompt) | No change |
| 3 | Waldman/Krempe | pronunciation.py | Fixed temporarily |
| 4 | creature/monster | main_cast.py (filtering) | No change |
| 5 | creature/monster | main_cast.py (merging) | No change |
| 6 | Waldman/Krempe | main_cast.py (cross-cast) | REGRESSION |
| 7 | Both issues | main_cast.py (prompt) | No change |
| 8 | Both issues | main_cast.py (post-proc) | Partial |
| 9 | Both issues | main_cast.py (debug) | Investigation |
| 10 | Waldman/Krempe | characters_v2.py (honorifics) | Failed |
| 10 | creature/monster | main_cast.py (startswith) | Partial |
| 11 | Both issues | characters_v2.py (logic) | Not tested |
| 12 | Waldman/Krempe | characters_v2.py (title split) | **FIXED** |
| 12 | creature/De Lacey | - | **NEW BUG** |
| 13 | creature/De Lacey | characters_v2.py (semantic split) | Pending |
