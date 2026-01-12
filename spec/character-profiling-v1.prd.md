# PRD: Summary-Driven Character Profiling Pipeline

**Version:** 1.0
**Status:** Draft
**Priority:** Critical
**Target:** Complete redesign of character extraction and profiling

## Executive Summary

The current character extraction pipeline is fundamentally broken. It optimizes for metrics that don't matter (mention counts, positions) while failing at what audiobook narrators actually need (accurate character identification, rich profiles, voice guidance).

Meanwhile, the chapter summary pipeline works excellently - correctly identifying characters, their relationships, and even complex cases like birth names (James Gatz = Jay Gatsby) and narrator identification.

**Proposal:** Replace the extraction-first approach with a summary-driven profiling approach that leverages the proven success of chapter summaries.

---

## Problem Statement

### Current Architecture Failures

Analysis of `output/gatsby_010` reveals six critical failures:

| Issue | What Happened | Root Cause |
|-------|---------------|------------|
| Wrong merge: McKee | Mr. McKee + Mrs. McKee merged | No cross-alias gendered title check |
| Wrong merge: Wilson | George Wilson merged into Mrs. Wilson | Last-name-only merge without family check |
| Split character: Myrtle | "Myrtle" and "Mrs. Wilson" kept separate | No word overlap = rejected merge |
| Split character: Gatsby | "James Gatz" and "Jay Gatsby" kept separate | No word overlap = rejected merge |
| Malformed profiles | Raw JSON in description field | Nested JSON parsing failure |
| Narrator missed | Nick Carraway not identified | Low mention count for self-referencing narrator |

### The Paradox

The **plot summary** in the same analysis correctly identifies:
- Nick Carraway as the first-person narrator
- Myrtle Wilson as a single person (Tom's mistress)
- James Gatz and Jay Gatsby as the same person
- All character relationships accurately

**Why?** Because the summary pipeline:
1. Processes full chapters with complete context
2. Asks holistic questions ("What happens?")
3. Trusts the LLM's comprehension
4. Doesn't fight against itself with rule-based post-processing

### Current Pipeline Flow (Broken)

```
NER Extraction → LLM Extraction → Validation → Consensus → Profile Generation
     ↓               ↓               ↓            ↓              ↓
  Find names    Find names     Filter bad    Merge aliases   Add descriptions
  (fragments)   (fragments)    (rules)       (rules)         (afterthought)
```

Each step can introduce errors. By the time we generate profiles, the character list is already corrupted.

### What Narrators Actually Need

| Need | Current Pipeline | Priority |
|------|------------------|----------|
| Accurate character identification | FAILING | Critical |
| Rich personality descriptions | Weak (afterthought) | Critical |
| Voice/accent guidance | Not implemented | High |
| Physical appearance | Partially captured | High |
| Character relationships | Not captured | Medium |
| Mention counts | Precise but unhelpful | Low |
| First appearance position | Precise but unhelpful | Low |

---

## Proposed Solution: Summary-Driven Character Profiling

### New Pipeline Flow

```
Chapter Summaries → Character Identification → Passage Gathering → Profile Generation → Reconciliation
       ↓                    ↓                        ↓                   ↓                  ↓
  (already works)    Extract from summaries    Search full text    Rich LLM profiles    Safety merge
```

### Key Principles

1. **Leverage what works** - Chapter summaries already identify characters correctly
2. **Profiles are primary** - Not an afterthought bolted onto broken extraction
3. **Trust the LLM** - For comprehension, not just name-finding
4. **Simplify rules** - Less validation code = fewer bugs
5. **Focus on narrator needs** - Voice, appearance, personality over metrics

---

## Features and User Stories

### Feature 1: Summary-Based Character Identification

**Priority:** CRITICAL
**Rationale:** Chapter summaries already correctly identify characters and their relationships.

**Current behavior:** NER + LLM extraction on text chunks, producing fragmented name lists that require complex merging.

**Proposed behavior:** Extract character list from chapter summaries, which already understand narrative context.

**User Stories:**

```json
{
  "category": "functional",
  "description": "Characters are identified from chapter summaries rather than raw NER extraction",
  "steps": [
    "Run analysis on a book",
    "Verify chapter summaries are generated first",
    "Check that character list is derived from summary content",
    "Verify characters mentioned in summaries appear in final character list",
    "Confirm no characters are listed that don't appear in any summary"
  ],
  "passes": false
}
```

```json
{
  "category": "functional",
  "description": "Birth name / assumed name characters are correctly unified",
  "steps": [
    "Run analysis on a book with a character who changes names",
    "Example: James Gatz becomes Jay Gatsby",
    "Verify only ONE character entry exists for this person",
    "Check that both names appear as aliases",
    "Confirm the canonical name is the most commonly used form"
  ],
  "passes": false
}
```

```json
{
  "category": "functional",
  "description": "First name and formal name variants are unified",
  "steps": [
    "Run analysis on a book where characters are called by first name and title+last name",
    "Example: 'Myrtle' and 'Mrs. Wilson' refer to the same person",
    "Verify they appear as ONE character entry",
    "Check both name forms appear (canonical + alias)",
    "Confirm profile describes the unified character"
  ],
  "passes": false
}
```

```json
{
  "category": "functional",
  "description": "Family members with same last name are kept separate",
  "steps": [
    "Run analysis on a book with married couples or family members",
    "Example: Mr. Wilson (George) and Mrs. Wilson (Myrtle)",
    "Verify they are listed as SEPARATE character entries",
    "Check that last-name-only references are attributed correctly or flagged",
    "Confirm no incorrect merging of family members"
  ],
  "passes": false
}
```

**Implementation:**

```python
class SummaryDrivenCharacterIdentifier:
    """Extract character list from chapter summaries."""

    def identify_characters(
        self,
        chapter_summaries: list[ChapterSummary],
        plot_summary: str,
    ) -> list[IdentifiedCharacter]:
        """
        Extract characters from summaries.

        The LLM has already done the hard work of understanding
        who is who. We just need to extract and deduplicate.
        """
        # Step 1: Ask LLM to extract character list from summaries
        prompt = self._build_extraction_prompt(chapter_summaries, plot_summary)
        result = self.llm.query_json(prompt, system=CHARACTER_IDENTIFICATION_SYSTEM)

        # Step 2: Validate and structure the response
        characters = self._parse_character_list(result)

        return characters
```

**Affected files:**
- New: `src/pipeline/character_profiling/identifier.py`
- Modified: `src/analyzer.py` (reorder pipeline stages)

---

### Feature 2: Passage-Based Profile Generation

**Priority:** CRITICAL
**Rationale:** Rich profiles require full-text passages, not just mention counts.

**Current behavior:** Profiles generated from 10 sampled mentions with 200-char context windows.

**Proposed behavior:** Search full text for character-relevant passages, generate comprehensive profiles.

**User Stories:**

```json
{
  "category": "functional",
  "description": "Character profiles include physical appearance details",
  "steps": [
    "Run analysis on a book with character physical descriptions",
    "Review generated character profiles",
    "Verify profiles include appearance details (height, build, hair, eyes, etc.)",
    "Check that appearance details are supported by text evidence",
    "Confirm details are useful for narrator voice characterization"
  ],
  "passes": false
}
```

```json
{
  "category": "functional",
  "description": "Character profiles include personality traits",
  "steps": [
    "Run analysis on a book",
    "Review profiles for major characters",
    "Verify profiles describe personality (temperament, habits, speech patterns)",
    "Check that traits are supported by textual evidence",
    "Confirm descriptions capture character arc if applicable"
  ],
  "passes": false
}
```

```json
{
  "category": "functional",
  "description": "Character profiles include voice/speech guidance",
  "steps": [
    "Run analysis on a book with dialogue",
    "Review character profiles",
    "Verify profiles include speech pattern observations",
    "Check for dialect, accent, verbal tics, formality level",
    "Confirm guidance is actionable for narrator voice work"
  ],
  "passes": false
}
```

```json
{
  "category": "functional",
  "description": "Character profiles include key relationships",
  "steps": [
    "Run analysis on a book with character relationships",
    "Review character profiles",
    "Verify profiles mention important relationships (spouse, rival, friend, etc.)",
    "Check that relationship dynamics are described",
    "Confirm relationships are accurate per the narrative"
  ],
  "passes": false
}
```

```json
{
  "category": "functional",
  "description": "Profile evidence is gathered from throughout the narrative",
  "steps": [
    "Run analysis on a book",
    "Review character profiles and their evidence citations",
    "Verify evidence comes from early, middle, and late chapters",
    "Check that character development/arc is captured if present",
    "Confirm no bias toward early-book descriptions only"
  ],
  "passes": false
}
```

**Implementation:**

```python
class CharacterProfileGenerator:
    """Generate rich character profiles from full text."""

    def generate_profile(
        self,
        character: IdentifiedCharacter,
        full_text: str,
        chapter_map: ChapterMap,
    ) -> CharacterProfile:
        """
        Generate comprehensive profile for a character.

        Unlike the current approach (sample 10 mentions),
        we search for ALL relevant passages and let the
        LLM synthesize a complete picture.
        """
        # Step 1: Gather all passages mentioning this character
        passages = self._gather_passages(character, full_text, chapter_map)

        # Step 2: Generate comprehensive profile
        profile = self._generate_profile_from_passages(character, passages)

        return profile

    def _gather_passages(
        self,
        character: IdentifiedCharacter,
        full_text: str,
        chapter_map: ChapterMap,
    ) -> list[CharacterPassage]:
        """
        Gather passages relevant to this character.

        Search for all name variants, then filter to
        passages with descriptive content (not just mentions).
        """
        passages = []

        # Search for all name variants
        for name in [character.canonical_name] + character.aliases:
            matches = self._find_passages_containing(name, full_text)
            passages.extend(matches)

        # Deduplicate by position
        passages = self._deduplicate_passages(passages)

        # Score passages by descriptive content
        passages = self._score_passages_for_description(passages)

        # Select best passages (distributed across narrative)
        passages = self._select_representative_passages(passages, chapter_map)

        return passages
```

**Profile Structure:**

```python
@dataclass
class CharacterProfile:
    """Rich character profile for audiobook narration."""

    # Identity
    canonical_name: str
    aliases: list[str]
    role: str  # "protagonist", "antagonist", "supporting", "minor"
    is_narrator: bool

    # For Narration (PRIMARY PURPOSE)
    appearance: AppearanceProfile
    personality: PersonalityProfile
    voice_guidance: VoiceGuidance

    # Relationships
    relationships: list[CharacterRelationship]

    # Evidence
    evidence: list[ProfileEvidence]
    confidence: float

    # Metadata (SECONDARY)
    first_appearance_chapter: int
    chapters_present: list[int]
    approximate_mentions: str  # "frequent", "moderate", "occasional"


@dataclass
class AppearanceProfile:
    """Physical appearance for narrator visualization."""

    summary: str  # 1-2 sentence overview
    details: dict[str, str]  # "hair": "dark, curly", "build": "tall and lean"
    age_indication: str  # "young adult", "middle-aged", "elderly"
    distinguishing_features: list[str]
    evidence: list[str]  # Supporting quotes


@dataclass
class PersonalityProfile:
    """Personality traits for voice characterization."""

    summary: str  # 1-2 sentence overview
    traits: list[str]  # "arrogant", "insecure", "charming"
    temperament: str  # "volatile", "calm", "anxious"
    speech_patterns: list[str]  # "formal", "uses slang", "interrupts"
    evidence: list[str]


@dataclass
class VoiceGuidance:
    """Specific guidance for narrator voice work."""

    suggested_tone: str  # "aristocratic drawl", "nervous energy"
    dialect_notes: str  # "Midwestern", "British upper class"
    verbal_tics: list[str]  # "old sport", "you know"
    formality_level: str  # "very formal", "casual", "varies by context"
    emotional_range: str  # "repressed", "explosive", "steady"
    example_quotes: list[str]  # Key dialogue samples
```

**Affected files:**
- New: `src/pipeline/character_profiling/generator.py`
- New: `src/pipeline/character_profiling/models.py`
- Modified: `src/models.py` (update Character model)

---

### Feature 3: Narrator Detection from Summaries

**Priority:** HIGH
**Rationale:** The plot summary already correctly identifies the narrator.

**Current behavior:** Pronoun density scoring on character mention contexts, which fails for self-referencing narrators.

**Proposed behavior:** Extract narrator identification from plot summary, which already knows.

**User Stories:**

```json
{
  "category": "functional",
  "description": "First-person narrator is correctly identified",
  "steps": [
    "Run analysis on a first-person narrative",
    "Check character list for narrator flag",
    "Verify the narrator character has is_narrator=true",
    "Confirm narrator identification matches the actual narrator",
    "Check that narrator's profile mentions their narrative role"
  ],
  "passes": false
}
```

```json
{
  "category": "functional",
  "description": "Narrator identification uses plot summary intelligence",
  "steps": [
    "Run analysis on a book where narrator has few self-mentions",
    "Example: narrator uses 'I' but rarely states their name",
    "Verify narrator is still correctly identified",
    "Check that identification comes from summary understanding, not mention count",
    "Confirm narrator profile is complete despite low explicit mentions"
  ],
  "passes": false
}
```

```json
{
  "category": "functional",
  "description": "Third-person narratives correctly have no narrator character",
  "steps": [
    "Run analysis on a third-person narrative",
    "Check character list",
    "Verify no character has is_narrator=true",
    "Confirm narrative_style is correctly identified as 'third-person'",
    "Check that no character is incorrectly flagged as narrator"
  ],
  "passes": false
}
```

**Implementation:**

```python
def identify_narrator_from_summary(
    plot_summary: str,
    characters: list[IdentifiedCharacter],
) -> Optional[str]:
    """
    Identify narrator from plot summary.

    The plot summary already contains phrases like:
    "The story unfolds through the eyes of Nick Carraway"

    We just need to extract this information.
    """
    prompt = f"""Based on this plot summary, identify the narrator if any.

Plot Summary:
{plot_summary}

Questions:
1. Is this a first-person narrative? (narrator is a character in the story)
2. Is this a third-person narrative? (external narrator)
3. If first-person, which character is the narrator?

Return JSON:
{{
  "narrative_style": "first-person" | "third-person" | "mixed",
  "narrator_name": "Character name if first-person, null otherwise",
  "narrator_role": "Brief description of narrator's relationship to events"
}}"""

    result = llm.query_json(prompt, system=NARRATOR_IDENTIFICATION_SYSTEM)
    return result.get("narrator_name")
```

**Affected files:**
- New: `src/pipeline/character_profiling/narrator.py`
- Modified: `src/analyzer.py`

---

### Feature 4: Character Reconciliation (Safety Net)

**Priority:** MEDIUM
**Rationale:** Even with summary-driven identification, some edge cases may slip through.

**Current behavior:** Complex rule-based consensus with many failure modes.

**Proposed behavior:** Simple LLM-based final check, run once after profiles are generated.

**User Stories:**

```json
{
  "category": "functional",
  "description": "Final reconciliation catches any duplicate characters",
  "steps": [
    "Run analysis on a book",
    "After profile generation, run reconciliation pass",
    "Verify any remaining duplicates are merged",
    "Check that merging preserves all profile information",
    "Confirm final character list has no duplicates"
  ],
  "passes": false
}
```

```json
{
  "category": "functional",
  "description": "Reconciliation does not incorrectly merge distinct characters",
  "steps": [
    "Run analysis on a book with similarly-named distinct characters",
    "Verify reconciliation keeps them separate",
    "Check that family members remain distinct",
    "Confirm characters with same first name but different last names stay separate",
    "Verify high-confidence separations are preserved"
  ],
  "passes": false
}
```

**Implementation:**

```python
class CharacterReconciler:
    """Final safety check for duplicate characters."""

    def reconcile(
        self,
        profiles: list[CharacterProfile],
    ) -> list[CharacterProfile]:
        """
        Check for and merge any duplicate characters.

        This is a SAFETY NET, not the primary mechanism.
        Most duplicates should already be handled by
        summary-driven identification.
        """
        # Build summary of all characters for LLM review
        char_summary = self._build_character_summary(profiles)

        # Ask LLM to identify any duplicates
        prompt = f"""Review this character list for any duplicates (same person listed twice).

Characters:
{char_summary}

IMPORTANT:
- Only flag CLEAR duplicates where you are confident
- Family members with same last name are DIFFERENT people
- Different first names usually means different people
- Birth name / assumed name pairs ARE the same person

Return JSON:
{{
  "duplicates": [
    {{"name1": "...", "name2": "...", "reason": "...", "confidence": 0.0-1.0}}
  ],
  "analysis": "Brief summary"
}}"""

        result = self.llm.query_json(prompt, system=RECONCILIATION_SYSTEM)

        # Merge high-confidence duplicates
        for dup in result.get("duplicates", []):
            if dup.get("confidence", 0) >= 0.85:
                profiles = self._merge_profiles(profiles, dup["name1"], dup["name2"])

        return profiles
```

**Affected files:**
- New: `src/pipeline/character_profiling/reconciler.py`

---

### Feature 5: Simplified Character Output

**Priority:** MEDIUM
**Rationale:** Current output emphasizes metrics over useful information.

**Current behavior:** Character entries focus on mention counts, positions, confidence scores.

**Proposed behavior:** Character entries focus on profile content useful for narration.

**User Stories:**

```json
{
  "category": "functional",
  "description": "Character entries prioritize narrator-useful information",
  "steps": [
    "Run analysis and generate HTML report",
    "Review character section layout",
    "Verify appearance, personality, and voice guidance are prominent",
    "Check that mention counts are de-emphasized or moved to metadata",
    "Confirm layout supports narrator preparation workflow"
  ],
  "passes": false
}
```

```json
{
  "category": "functional",
  "description": "Character JSON output includes rich profile data",
  "steps": [
    "Run analysis and examine JSON output",
    "Verify each character has appearance, personality, voice_guidance fields",
    "Check that evidence citations are included",
    "Confirm relationships are captured",
    "Verify structure supports programmatic access to profile components"
  ],
  "passes": false
}
```

**New JSON Output Structure:**

```json
{
  "characters": [
    {
      "id": "char_jay_gatsby_abc123",
      "canonical_name": "Jay Gatsby",
      "aliases": ["Mr. Gatsby", "James Gatz", "Mr. Gatz"],
      "role": "protagonist",
      "is_narrator": false,

      "appearance": {
        "summary": "A handsome man in his early thirties with a rare smile that conveys eternal reassurance.",
        "details": {
          "age": "early thirties",
          "build": "elegant, well-groomed",
          "distinguishing": "rare, reassuring smile"
        },
        "evidence": [
          "He smiled understandingly—much more than understandingly. It was one of those rare smiles..."
        ]
      },

      "personality": {
        "summary": "A self-invented romantic dreamer who built an empire to recapture a lost love.",
        "traits": ["romantic", "obsessive", "generous", "mysterious"],
        "temperament": "controlled exterior with intense inner passion",
        "evidence": [
          "He had come a long way to this blue lawn, and his dream must have seemed so close..."
        ]
      },

      "voice_guidance": {
        "suggested_tone": "Measured, almost rehearsed formality with occasional cracks showing vulnerability",
        "dialect_notes": "Affected upper-class speech, deliberately obscuring humble origins",
        "verbal_tics": ["old sport"],
        "formality_level": "Very formal, even with intimates",
        "example_quotes": [
          "\"I'm going to make a big request of you today...\"",
          "\"Can't repeat the past? Why of course you can!\""
        ]
      },

      "relationships": [
        {"character": "Daisy Buchanan", "type": "love interest", "description": "Obsessive, idealized love"},
        {"character": "Nick Carraway", "type": "friend/confidant", "description": "Uses Nick to reconnect with Daisy"}
      ],

      "metadata": {
        "first_appearance_chapter": 3,
        "chapters_present": [3, 4, 5, 6, 7, 8, 9],
        "mention_frequency": "frequent",
        "confidence": 0.95
      }
    }
  ]
}
```

**Affected files:**
- Modified: `src/models.py` (update Character model)
- Modified: `src/export/html_report.py` (update character section layout)
- Modified: `src/analyzer.py` (update _convert_characters)

---

## Architecture

### New Pipeline Stages

```
Stage 1: Chapter Detection (unchanged)
    │
    ▼
Stage 2: Chapter Summaries (unchanged, but now feeds Stage 3)
    │
    ▼
Stage 3: Plot Summary Generation (unchanged)
    │
    ▼
Stage 4: Character Identification (NEW - from summaries)
    │   └── Extract character list from chapter summaries + plot summary
    │   └── Identify narrator from plot summary
    │   └── Unify name variants (birth names, nicknames, formal names)
    │
    ▼
Stage 5: Character Profiling (NEW - replaces old extraction + profile)
    │   └── Gather passages for each character
    │   └── Generate rich profiles (appearance, personality, voice)
    │   └── Extract relationships
    │
    ▼
Stage 6: Character Reconciliation (NEW - safety net)
    │   └── Final duplicate check
    │   └── Merge any remaining duplicates
    │
    ▼
Stage 7: Pronunciation Guide (unchanged, but now uses better character list)
```

### Module Structure

```
src/pipeline/character_profiling/
├── __init__.py
├── models.py           # CharacterProfile, AppearanceProfile, etc.
├── identifier.py       # SummaryDrivenCharacterIdentifier
├── passage_gatherer.py # CharacterPassageGatherer
├── generator.py        # CharacterProfileGenerator
├── narrator.py         # NarratorDetector
├── reconciler.py       # CharacterReconciler
└── pipeline.py         # CharacterProfilingPipeline (orchestrator)
```

### Deprecation Plan

The existing `src/pipeline/character_extraction/` module will be:
1. **Phase 1:** Kept as fallback, new pipeline runs in parallel
2. **Phase 2:** Old pipeline disabled by default, available via flag
3. **Phase 3:** Old pipeline removed entirely

---

## Implementation Phases

### Phase 1: Character Identification from Summaries
**Scope:** Features 1, 3 (identification + narrator)
**Estimate:** 2-3 days
**Risk:** Low - builds on existing summary pipeline
**Deliverables:**
- `SummaryDrivenCharacterIdentifier` class
- `NarratorDetector` class
- Integration with existing summary pipeline
- Unit tests

### Phase 2: Rich Profile Generation
**Scope:** Feature 2 (passage-based profiles)
**Estimate:** 3-4 days
**Risk:** Medium - new prompts, new data models
**Deliverables:**
- `CharacterPassageGatherer` class
- `CharacterProfileGenerator` class
- New profile data models
- Updated JSON/HTML output
- Unit tests

### Phase 3: Reconciliation and Polish
**Scope:** Features 4, 5 (reconciliation + output)
**Estimate:** 1-2 days
**Risk:** Low - safety net, not critical path
**Deliverables:**
- `CharacterReconciler` class
- Updated HTML report layout
- Integration tests
- Documentation

### Phase 4: Migration and Cleanup
**Scope:** Deprecate old pipeline
**Estimate:** 1 day
**Risk:** Low - old code still available
**Deliverables:**
- Feature flag for old vs new pipeline
- Migration guide
- Performance comparison

---

## Validation Strategy

### Test Cases

**Primary Test Book:** The Great Gatsby (gatsby.txt)

| Test Case | Expected Result | Validates |
|-----------|-----------------|-----------|
| Gatsby identification | Single entry for Jay Gatsby with aliases [Mr. Gatsby, James Gatz, Mr. Gatz] | Feature 1 |
| Myrtle Wilson | Single entry for Myrtle Wilson with aliases [Mrs. Wilson, Myrtle] | Feature 1 |
| Wilson separation | George Wilson and Myrtle Wilson are separate entries | Feature 1 |
| McKee separation | Mr. McKee and Mrs. McKee are separate entries | Feature 1 |
| Nick as narrator | Nick Carraway has is_narrator=true | Feature 3 |
| Gatsby appearance | Profile includes "rare smile", physical description | Feature 2 |
| Gatsby voice | Profile includes "old sport" verbal tic | Feature 2 |
| Tom personality | Profile captures arrogance, brutishness | Feature 2 |

### Success Metrics

1. **Identification Accuracy:** 100% of major characters correctly identified (no splits, no wrong merges)
2. **Profile Completeness:** All major characters have appearance, personality, and voice_guidance sections
3. **Narrator Detection:** 100% accuracy on first-person vs third-person narratives
4. **Evidence Quality:** All profile claims supported by textual evidence
5. **Performance:** Character profiling completes in <10 minutes for typical novel (vs current 30+ minutes)

### Regression Tests

Compare new pipeline output against known-good summary output to ensure we don't regress on plot understanding.

---

## Technical Notes

### LLM Prompts

**Character Identification Prompt (from summaries):**

```
You are analyzing a novel's chapter summaries to identify all characters.

Chapter Summaries:
{summaries}

Plot Summary:
{plot_summary}

Extract ALL characters mentioned, unifying different names for the same person.

IMPORTANT UNIFICATION RULES:
- Birth name and assumed name are the SAME person (e.g., "James Gatz" = "Jay Gatsby")
- First name and title+last name are often the SAME person (e.g., "Myrtle" = "Mrs. Wilson")
- Family members with same last name are DIFFERENT people (e.g., "Mr. Wilson" ≠ "Mrs. Wilson")
- Check the summaries for relationship clues (husband/wife, siblings, etc.)

Return JSON array of characters...
```

**Profile Generation Prompt:**

```
You are creating a character profile for audiobook narration.

Character: {name}
Aliases: {aliases}

Relevant Passages:
{passages}

Create a comprehensive profile covering:

1. APPEARANCE: Physical description useful for visualization
   - Age indication
   - Build/stature
   - Distinguishing features
   - Clothing style (if mentioned)

2. PERSONALITY: Traits that affect voice characterization
   - Core personality traits
   - Temperament (calm, volatile, anxious, etc.)
   - How they treat others
   - Any character arc/development

3. VOICE GUIDANCE: Specific guidance for narrator
   - Suggested tone
   - Dialect or accent clues
   - Verbal tics or catchphrases
   - Formality level
   - 2-3 example quotes showing voice

4. RELATIONSHIPS: Key relationships with other characters

CRITICAL: Only include information supported by the provided passages.
Include the supporting quote for each claim.

Return JSON matching the CharacterProfile schema...
```

### Performance Considerations

1. **Passage Gathering:** Use efficient text search, not regex on full text
2. **Profile Generation:** Can parallelize across characters
3. **LLM Calls:** Fewer total calls than current pipeline (no per-chapter extraction)

### Backward Compatibility

- JSON output structure will change (new fields, reorganized)
- HTML report layout will change
- API for `analyze()` remains the same
- Feature flag allows falling back to old pipeline

---

## Open Questions

1. **Passage Selection:** How many passages per character is optimal? (Proposal: 15-20, distributed across narrative)
2. **Profile Length:** How detailed should profiles be? (Proposal: 3-5 sentences per section)
3. **Minor Characters:** Should minor characters (1-2 mentions) get profiles? (Proposal: No, just list them)
4. **Confidence Scoring:** Do we still need confidence scores? (Proposal: Yes, but based on evidence quality, not mention count)

---

## Appendix: Current vs Proposed Comparison

### Character: Myrtle Wilson

**Current Output (Broken):**
```json
// TWO SEPARATE ENTRIES:
{
  "canonical_name": "Mrs. Wilson",
  "aliases": ["Wilson"],  // WRONG - Wilson is her husband
  "mention_count": 73
}
{
  "canonical_name": "Myrtle",
  "aliases": [],
  "mention_count": 20,
  "confidence": "low"
}
```

**Proposed Output (Correct):**
```json
{
  "canonical_name": "Myrtle Wilson",
  "aliases": ["Mrs. Wilson", "Myrtle"],
  "role": "supporting",
  "appearance": {
    "summary": "A woman in her middle thirties with a thickish figure and immediately perceptible vitality.",
    "details": {
      "age": "middle thirties",
      "build": "thickish figure, faintly stout",
      "distinguishing": "perceptible vitality, sensuous"
    }
  },
  "personality": {
    "summary": "Desperately ambitious and emotionally volatile, trapped in a loveless marriage and seeking escape through an affair.",
    "traits": ["ambitious", "volatile", "desperate", "social-climbing"]
  },
  "voice_guidance": {
    "suggested_tone": "Shrill and affected when trying to be sophisticated, raw when emotional",
    "verbal_tics": ["references to her sister Catherine"],
    "formality_level": "Affects formality, drops it under stress"
  },
  "relationships": [
    {"character": "George Wilson", "type": "spouse", "description": "Loveless marriage, contempt"},
    {"character": "Tom Buchanan", "type": "lover", "description": "Affair, dreams of escape"}
  ]
}
```

---

## References

- Current character extraction: `src/pipeline/character_extraction/`
- Current character agent: `src/agents/characters.py`
- Chapter summary pipeline: `src/pipeline/chapter_summary/`
- Plot summary generation: `src/pipeline/overview/`
- Previous quality PRD: `spec/output-quality-v2.prd`
