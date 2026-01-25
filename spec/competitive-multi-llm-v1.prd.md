# PRD: Competitive Multi-LLM Architecture

**Version:** 1.0
**Status:** Draft
**Priority:** Medium
**Target:** Improved character extraction quality through ensemble consensus

## Executive Summary

Implement a competitive multi-LLM approach where multiple LLM configurations run in parallel on character merge decisions, then voting determines the outcome. This leverages the DGX Spark's 128GB unified memory and GB10 Blackwell to improve quality through diversity, specifically targeting false merge problems like "Mr. Sloane" + "Mr. McKee" being incorrectly combined.

**Proposal:** Add competitive consensus voting to the character extraction pipeline where 3 LLMs with different temperatures and prompt styles vote on merge decisions. Supermajority (2/3) agreement required to merge, preventing single-LLM hallucinations from causing false merges.

---

## Problem Statement

### Current State

The character extraction pipeline uses a single LLM to make merge decisions. When the LLM hallucinates or makes an error, there's no safety net.

**Example failures observed:**
- "Mr. Sloane" merged with "Mr. McKee" (different people, single LLM said yes)
- "M. Waldman" merged with "M. Krempe" (different professors in Frankenstein)
- "Catherine" merged with "Mrs. McKee" (sister vs wife)

### Root Cause

Single-LLM decisions are vulnerable to:
1. **Temperature variance** - same model can give different answers
2. **Context sensitivity** - small prompt changes affect decisions
3. **Hallucination** - LLM confidently asserts incorrect information

### Why Competitive Approach Helps

If 3 LLMs are asked "Are Mr. Sloane and Mr. McKee the same person?":
- Precise LLM (temp=0.5, strict prompt): "NO - different surnames"
- Balanced LLM (temp=0.7): "NO - no evidence they're the same"
- Inclusive LLM (temp=0.9): "YES - both are men mentioned at parties" (hallucination)

Result: 1/3 vote → merge rejected. The supermajority requirement prevents the hallucination from causing damage.

---

## Proposed Solution

### Architecture Overview

```
                    ┌─────────────────────────────────────┐
                    │         Competitive Layer           │
                    ├─────────────────────────────────────┤
                    │  LLM Config A (temp=0.5, strict)    │
   Merge Decision ─▶│  LLM Config B (temp=0.7, balanced)  ├─▶ Voting ─▶ Merge/No-Merge
                    │  LLM Config C (temp=0.9, inclusive) │
                    └─────────────────────────────────────┘
```

### Injection Point: Consensus Layer

Focus on the merge decision step in character extraction:
- **V1 Pipeline:** `src/pipeline/character_extraction/consensus.py` - `_llm_pairwise_merge_decision()`
- **V2 Pipeline:** `src/pipeline/character_extraction_v2/main_cast.py` - `verify_aliases()`

This is the most impactful point because:
1. Merge decisions are the source of false merge errors
2. Each decision is independent (parallelizable)
3. Relatively few decisions per book (100s, not 1000s)

---

## Features

### Feature 1: Competitor Configurations

**Priority:** CRITICAL
**Rationale:** Diversity of perspectives requires different configurations.

**Current behavior:** Single LLM config for all merge decisions.

**Proposed behavior:** Three competitor configs combining temperature + prompt style variations.

```python
COMPETITOR_CONFIGS = [
    {
        "name": "precise",
        "temperature": 0.5,
        "prompt_style": "strict",
    },
    {
        "name": "balanced",
        "temperature": 0.7,
        "prompt_style": "contextual",
    },
    {
        "name": "inclusive",
        "temperature": 0.9,
        "prompt_style": "inclusive",
    },
]
```

**Affected files:**
- New: `src/pipeline/character_extraction/prompts.py` (merge prompt variations)
- Modified: `src/agents/config.py` (CompetitiveConfig dataclass)

---

### Feature 2: Competitive Merge Voting

**Priority:** CRITICAL
**Rationale:** Core mechanism for preventing false merges.

**Current behavior:** Single LLM returns yes/no on merge decision.

**Proposed behavior:** Three LLMs vote in parallel, supermajority required.

```python
def _competitive_merge_decision(
    self,
    name_a: str,
    name_b: str,
    evidence: str,
) -> tuple[bool, float]:  # (should_merge, confidence)
    """Multiple LLMs vote on merge decision."""

    votes = []
    with ThreadPoolExecutor(max_workers=len(self.llm_clients)) as executor:
        futures = [
            executor.submit(
                self._single_merge_decision,
                client, name_a, name_b, evidence, prompt_style
            )
            for client, prompt_style in zip(self.llm_clients, self.prompt_styles)
        ]
        votes = [f.result() for f in futures]

    # Require supermajority for merge (prevents false merges)
    merge_votes = sum(1 for v in votes if v.should_merge)
    confidence = merge_votes / len(votes)

    # Require 2/3 agreement to merge
    should_merge = merge_votes >= len(votes) * 0.67

    return should_merge, confidence
```

**Affected files:**
- Modified: `src/pipeline/character_extraction/consensus.py`
- Modified: `src/pipeline/character_extraction_v2/main_cast.py`

---

### Feature 3: Prompt Variations

**Priority:** HIGH
**Rationale:** Different prompts elicit different reasoning strategies.

**Prompt Styles:**

**STRICT_MERGE_PROMPT** (for temp=0.5 "precise" competitor):
```
You are a CONSERVATIVE character analyst. Only say YES if you are CERTAIN these names refer to the SAME person.
Different surnames = DIFFERENT people (e.g., "Mr. McKee" vs "Mr. Sloane" are NEVER the same).
When in doubt, say NO.
```

**CONTEXTUAL_MERGE_PROMPT** (for temp=0.7 "balanced" competitor):
```
Analyze whether these names refer to the same character based on:
1. Do they appear in the same scenes?
2. Do other characters treat them as the same person?
3. Are the names plausibly related (nickname, title variation)?
```

**INCLUSIVE_MERGE_PROMPT** (for temp=0.9 "inclusive" competitor):
```
Consider whether these names might refer to the same character.
Look for any evidence they could be the same person.
Titles like "Mr." should match the same surname.
```

**Affected files:**
- New: `src/pipeline/character_extraction/prompts.py`

---

### Feature 4: Configuration Integration

**Priority:** HIGH
**Rationale:** Enable/disable competitive mode via config and CLI.

**Configuration dataclass:**

```python
@dataclass
class CompetitiveConfig:
    """Configuration for competitive multi-LLM execution."""

    enabled: bool = False
    num_competitors: int = 3
    temperature_range: tuple[float, float] = (0.5, 0.9)

    # Voting thresholds
    merge_threshold: float = 0.67  # Supermajority for merges

@dataclass
class OrchestratorConfig:
    # ... existing fields ...
    competitive: CompetitiveConfig = field(default_factory=CompetitiveConfig)
```

**CLI flag:**
```bash
audiobook-prep analyze book.txt --competitive-consensus
```

**Affected files:**
- Modified: `src/agents/config.py`
- Modified: `src/agents/characters_v2.py`
- Modified: `src/cli.py`

---

## Architecture

### Data Flow (Competitive Mode)

```
Chapter Summaries
       │
       ▼
┌──────────────────┐
│  Main Cast       │
│  Extraction      │
└────────┬─────────┘
         │
         ▼
┌──────────────────────────────────────────────────────┐
│                 Alias Verification                    │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐       │
│  │ Precise    │ │ Balanced   │ │ Inclusive  │       │
│  │ temp=0.5   │ │ temp=0.7   │ │ temp=0.9   │       │
│  │ strict     │ │ contextual │ │ inclusive  │       │
│  └─────┬──────┘ └─────┬──────┘ └─────┬──────┘       │
│        │              │              │               │
│        └──────────────┼──────────────┘               │
│                       ▼                              │
│              ┌─────────────────┐                     │
│              │  Vote Aggregator │                     │
│              │  (2/3 majority)  │                     │
│              └────────┬────────┘                     │
└───────────────────────┼──────────────────────────────┘
                        │
                        ▼
               Verified Character Map
```

### Hardware Utilization

With DGX Spark (128GB unified memory, GB10 Blackwell):

| Model Size | Memory per Instance | 3 Concurrent | Remaining |
|------------|--------------------:|-------------:|----------:|
| 30B model  | ~20GB              | 60GB         | 68GB      |
| 4B model   | ~3GB               | 9GB          | 119GB     |

The competitive approach is well within hardware limits. Running 3 concurrent LLM calls utilizes the GPU more efficiently than sequential processing.

---

## Implementation Phases

### Phase 1: Prompt Variations

**Scope:** Create prompt variations file
**Risk:** Low - additive only
**Deliverables:**
- Create `src/pipeline/character_extraction/prompts.py`
- Define STRICT, CONTEXTUAL, INCLUSIVE merge prompts

### Phase 2: Competitive Consensus (V2 Pipeline)

**Scope:** Add competitive voting to V2 character extraction
**Risk:** Medium - modifies core logic
**Deliverables:**
- Modify `src/pipeline/character_extraction_v2/main_cast.py`
- Add `_competitive_merge_decision()` method
- Add voting logic with 2/3 threshold
- Log individual votes for debugging

### Phase 3: Configuration & CLI

**Scope:** Wire up configuration
**Risk:** Low - configuration only
**Deliverables:**
- Add `CompetitiveConfig` to `src/agents/config.py`
- Add `--competitive-consensus` flag to CLI
- Wire through `CharacterAgentV2`

### Phase 4: Testing & Tuning

**Scope:** Validate on test texts
**Risk:** Low - testing only
**Deliverables:**
- Run on Gatsby, verify Mr. Sloane / Mr. McKee NOT merged
- Run on Frankenstein, verify Waldman / Krempe NOT merged
- Compare quality scores vs single-LLM baseline
- Tune thresholds if needed

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/pipeline/character_extraction/prompts.py` | NEW - merge prompt variations |
| `src/pipeline/character_extraction_v2/main_cast.py` | Add competitive alias verification |
| `src/agents/config.py` | Add CompetitiveConfig dataclass |
| `src/agents/characters_v2.py` | Pass competitive config to pipeline |
| `src/cli.py` | Add `--competitive-consensus` flag |

**Deferred (Future Phase):**
| File | Deferred Changes |
|------|------------------|
| `src/pipeline/character_extraction/consensus.py` | V1 competitive merge voting |
| `src/pipeline/character_extraction/proposers/competitive.py` | Competitive proposer (union pooling) |
| `src/pipeline/character_extraction/validator.py` | Ensemble validation |

---

## Expected Benefits

1. **Reduced False Merges:** Supermajority voting prevents single-LLM hallucinations
2. **Higher Precision:** Strict prompt catches obviously wrong merges
3. **Confidence Calibration:** Vote counts provide natural confidence scores (3/3 vs 2/3)
4. **Debuggability:** Individual votes logged for analysis
5. **GPU Efficiency:** Parallel execution uses hardware better than sequential

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Increased LLM cost (3x calls) | Certain | Medium | Start with consensus-only (least calls) |
| Thread safety issues | Low | High | Use ThreadPoolExecutor with fresh clients |
| Inconsistent results | Medium | Low | Use voting thresholds, not averages |
| Slower on small texts | Medium | Low | Skip competitive for texts < 10k words |
| Valid merges rejected | Medium | Medium | Tune temperature/prompts; 2/3 not 3/3 |

---

## Validation Strategy

### Test Cases

| Test Case | Expected Result |
|-----------|-----------------|
| "Mr. Sloane" + "Mr. McKee" | NOT merged (0/3 or 1/3 votes) |
| "Catherine" + "Mrs. McKee" | NOT merged (0/3 or 1/3 votes) |
| "M. Waldman" + "M. Krempe" | NOT merged (different professors) |
| "Jay Gatsby" + "Mr. Gatsby" | Merged (3/3 votes) |
| "Daisy Buchanan" + "Daisy" | Merged (3/3 votes) |
| "the creature" + "the monster" | Merged (3/3 votes) |

### Success Metrics

1. **False Merge Rate:** Reduce from ~5% to <1%
2. **Valid Merge Rate:** Maintain at >95%
3. **Quality Score:** Improve overall score by 0.3+ points
4. **Latency:** <2x increase (parallel execution)

---

## Open Questions

1. **Voting threshold:** 2/3 (67%) vs 3/3 (unanimous)?
   - *Recommendation:* Start with 2/3 to allow some flexibility

2. **Apply to V1 pipeline?**
   - *Recommendation:* Focus on V2 first, V1 is legacy

3. **Log individual votes?**
   - *Recommendation:* Yes, essential for debugging

4. **Different models per competitor?**
   - *Recommendation:* Same model, different temp/prompt first; multi-model later

---

## References

- Oracle loop evaluations showing false merge issues
- Chapter V detection PRD (similar multi-proposer pattern)
- DGX Spark hardware specs (128GB unified memory)
