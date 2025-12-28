# Specialized Agent Architecture for Audiobook Prep

**Status:** Planning
**Created:** 2025-12-27
**Last Updated:** 2025-12-27

## Executive Summary

This document specifies a multi-phase enhancement to the audiobook analysis tool. The goal is to achieve **business-grade reliability** - analysis that works perfectly regardless of book format, length, or complexity.

The approach:
1. **Phase 1: Profiling** - Understand current performance and quality bottlenecks
2. **Phase 2: Agent Infrastructure** - Build the foundation for specialized agents
3. **Phase 3: Specialized Agents** - Replace monolithic pipelines with task-specific agents
4. **Phase 4: Orchestration** - Enable parallel execution and quality gates

---

## Current State

### Architecture

The current system uses a sequential pipeline with a single LLM:

```
Document → ChapterDetection → CharacterExtraction → ChapterSummaries → Pronunciation → Output
```

Each pipeline stage:
- Uses the same LLM model (user-specified, typically Ollama)
- Runs sequentially (no parallelization)
- Has basic confidence scoring
- Uses checkpointing for resume capability

### Key Files

| Component | Location | Description |
|-----------|----------|-------------|
| Main Analyzer | `src/analyzer.py` | Orchestrates all pipelines |
| LLM Client | `src/pipeline/llm.py` | `LLMClient` ABC, Ollama/OpenAI implementations |
| Chapter Detection | `src/pipeline/chapter_detection/` | Multi-proposer consensus system |
| Character Extraction | `src/pipeline/character_extraction.py` | NER + LLM merge |
| Chapter Summaries | `src/pipeline/chapter_summary.py` | Per-chapter summarization |
| Pronunciation | `src/pipeline/pronunciation.py` | Proper noun pronunciation guide |

### Current Metrics Capabilities

The system currently tracks:
- Basic timing (total analysis duration)
- LLM model name and provider
- Token usage (if returned by LLM)

**Missing:**
- Per-stage timing breakdown
- Per-stage token usage
- Latency per LLM call
- Quality metrics (confidence distribution)

### Known Quality Challenges

| Area | Issue | Example |
|------|-------|---------|
| Structure | Unusual formats confuse detection | Letters with dividers creating spurious chapters |
| Characters | Alias resolution | "Mark Otto" vs "SSgt Otto" vs "Staff Sergeant Mark Otto" |
| Summaries | Key event coverage | Missing important plot points |
| Pronunciation | Context-dependent words | Homographs like "lead" (metal vs verb) |

---

## Goals

### Primary Goal
Achieve **near-perfect analysis quality** regardless of:
- Book format (chapters, letters, diary entries, mixed)
- Length (novellas to epic series)
- Complexity (many characters, invented words, foreign names)

### Secondary Goals
1. **Observability** - Understand where time and tokens are spent
2. **Flexibility** - Use different models for different tasks
3. **Reliability** - Graceful handling of edge cases with confidence flagging
4. **Maintainability** - Clear separation of concerns for future improvements

---

## Phase 1: Comprehensive Profiling

### Objective
Add detailed metrics collection to understand current performance and identify bottlenecks.

### Safety Considerations

**This phase is LOW RISK:**
- Work on feature branch (`feature/profiling`)
- Profiling is purely observational - no logic changes
- All additions are backwards compatible
- Each commit can be validated and reverted independently

### Deliverables

#### 1. Enhanced LLM Response Tracking

**File:** `src/pipeline/llm.py`

Add optional timing field to `LLMResponse`:
```python
@dataclass
class LLMResponse:
    content: str
    model: str
    usage: Optional[dict] = None  # Token usage
    error: Optional[str] = None
    latency_ms: Optional[float] = None  # NEW: Time to complete call
```

Update `OllamaClient.query()` to measure and record duration.

#### 2. Metrics Collection System

**File:** `src/pipeline/metrics.py` (NEW)

```python
@dataclass
class StageMetrics:
    stage_name: str
    duration_seconds: float
    llm_calls: int
    tokens_prompt: int
    tokens_completion: int
    tokens_total: int
    items_processed: int
    high_confidence_count: int
    medium_confidence_count: int
    low_confidence_count: int

class MetricsCollector:
    """Collects and aggregates pipeline metrics."""

    @contextmanager
    def stage(self, name: str) -> StageContext:
        """Context manager for measuring a pipeline stage."""
        ...

    def record_llm_call(self, response: LLMResponse) -> None:
        """Record metrics from an LLM call."""
        ...

    def record_items(self, high: int, medium: int, low: int) -> None:
        """Record confidence breakdown for processed items."""
        ...

    def get_report(self) -> ProfilingReport:
        """Generate aggregated report."""
        ...
```

#### 3. Pipeline Instrumentation

**Files:** `src/analyzer.py`, various pipeline files

Wrap each pipeline stage:
```python
with self.metrics.stage("chapter_detection"):
    chapter_map = self.chapter_pipeline.run(text)
    self.metrics.record_items(
        high=sum(1 for c in chapter_map.chapters if c.confidence >= 0.7),
        medium=sum(1 for c in chapter_map.chapters if 0.4 <= c.confidence < 0.7),
        low=sum(1 for c in chapter_map.chapters if c.confidence < 0.4),
    )
```

#### 4. Profiling Report Output

**Format:**
```
=== Pipeline Profiling Report ===

Stage                  | Time    | LLM Calls | Tokens   | Items | Confidence
-----------------------|---------|-----------|----------|-------|------------
Chapter Detection      | 45.2s   | 12        | 24,500   | 22    | 20H/2M/0L
Character Extraction   | 128.3s  | 89        | 156,000  | 47    | 35H/8M/4L
Character Profiles     | 234.1s  | 35        | 89,000   | 35    | 33H/2M/0L
Chapter Summaries      | 312.5s  | 22        | 112,000  | 22    | 20H/2M/0L
Pronunciation Guide    | 67.8s   | 45        | 34,000   | 156   | 120H/25M/11L
-----------------------|---------|-----------|----------|-------|------------
TOTAL                  | 787.9s  | 203       | 415,500  | -     | -

Bottleneck: Chapter Summaries (39.6% of time)
Quality concerns: 4 low-confidence characters, 11 low-confidence pronunciations
```

### Implementation Steps

| Step | Description | Risk | Validation |
|------|-------------|------|------------|
| 1 | Add `latency_ms` to `LLMResponse` | Low | Existing tests pass |
| 2 | Create `metrics.py` | None | New file, no dependencies |
| 3 | Instrument `analyzer.py` | Low | Output matches previous |
| 4 | Add profiling report | None | Additive output only |

### Acceptance Criteria

- [ ] LLM calls record latency in milliseconds
- [ ] Each pipeline stage reports timing and token usage
- [ ] Confidence distribution reported per stage
- [ ] Profiling report displays after analysis
- [ ] Profiling data included in JSON output
- [ ] Existing output unchanged (aside from new profiling section)

---

## Phase 2: Agent Infrastructure

### Objective
Create the foundation for specialized agents without changing pipeline behavior.

### Deliverables

#### Agent Base Class

**File:** `src/agents/base.py` (NEW)

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional

@dataclass
class AgentContext:
    """Input context for an agent."""
    text: str
    metadata: dict
    previous_results: dict[str, Any]

@dataclass
class AgentResult:
    """Output from an agent."""
    data: Any
    confidence_scores: list[float]
    issues: list[str]
    metrics: StageMetrics

class Agent(ABC):
    """Base class for specialized analysis agents."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Agent identifier."""
        ...

    @property
    @abstractmethod
    def recommended_models(self) -> list[str]:
        """Models known to work well for this task, in preference order."""
        ...

    @property
    @abstractmethod
    def depends_on(self) -> list[str]:
        """Names of agents that must run before this one."""
        ...

    @abstractmethod
    async def run(self, context: AgentContext) -> AgentResult:
        """Execute the agent's task."""
        ...

    @abstractmethod
    async def verify(self, result: AgentResult) -> VerificationResult:
        """Self-check the result for quality issues."""
        ...
```

#### Agent Configuration

**File:** `src/agents/config.py` (NEW)

```python
@dataclass
class AgentConfig:
    """Configuration for a specific agent."""
    model: str
    temperature: float = 0.7
    max_tokens: int = 4096
    retry_on_low_confidence: bool = True
    max_retries: int = 2

@dataclass
class OrchestratorConfig:
    """Configuration for the agent orchestrator."""
    agents: dict[str, AgentConfig]
    parallel_execution: bool = True
    quality_gate_threshold: float = 0.7
```

### Acceptance Criteria

- [ ] Agent ABC defined with clear interface
- [ ] AgentContext and AgentResult types defined
- [ ] Configuration system supports per-agent model selection
- [ ] No changes to existing pipeline behavior

---

## Phase 3: Specialized Agents

### Objective
Wrap existing pipelines as agents with self-verification capabilities.

### Agents

#### StructureAgent
- **Wraps:** `ChapterDetectionPipeline`
- **Purpose:** Perfect chapter detection regardless of format
- **Model preference:** Fast model for initial scan, deeper model for validation
- **Self-verification:** "Does this chapter sequence make logical sense for a book?"

#### CharacterAgent
- **Wraps:** `CharacterExtractionPipeline` + profile generation
- **Purpose:** Complete character map with correct aliases
- **Model preference:** Deep narrative understanding model
- **Self-verification:** "Are all character references accounted for? Any duplicates?"

#### SummaryAgent
- **Wraps:** `ChapterSummaryPipeline`
- **Purpose:** Accurate, consistent chapter summaries
- **Model preference:** Narrative-focused model
- **Self-verification:** "Does this summary capture key events?"

#### PronunciationAgent
- **Wraps:** `PronunciationGuidePipeline`
- **Purpose:** Comprehensive pronunciation guide with accurate IPA
- **Model preference:** Phonetically-aware model
- **Self-verification:** "Are homographs correctly contextualized?"

### Files to Create

| File | Purpose |
|------|---------|
| `src/agents/__init__.py` | Package exports |
| `src/agents/structure.py` | StructureAgent |
| `src/agents/characters.py` | CharacterAgent |
| `src/agents/summaries.py` | SummaryAgent |
| `src/agents/pronunciation.py` | PronunciationAgent |

### Acceptance Criteria

- [ ] Each agent wraps its corresponding pipeline
- [ ] Each agent implements self-verification
- [ ] Output identical to current pipeline (agents are wrappers)
- [ ] Can swap models per-agent via configuration

---

## Phase 4: Orchestration

### Objective
Enable parallel execution and quality gates.

### Dependency Graph

```
Document
    │
    ▼
[StructureAgent] ─────────────────────┐
    │                                 │
    ▼                                 ▼
[CharacterAgent] ──────┐    [PronunciationAgent]
    │                  │              │
    ▼                  ▼              ▼
[SummaryAgent] ────────┴──────────────┘
    │
    ▼
Final Result
```

**Parallel Opportunities:**
- CharacterAgent and PronunciationAgent can run in parallel (both depend only on StructureAgent)

### Orchestrator

**File:** `src/agents/orchestrator.py` (NEW)

Responsibilities:
1. **Dependency management** - Execute agents in correct order
2. **Parallel execution** - Run independent agents concurrently
3. **Model allocation** - Load correct model for each agent
4. **Quality gates** - Re-run agents with too many low-confidence items
5. **Checkpointing** - Save state between agents for resume

### Acceptance Criteria

- [ ] Orchestrator respects agent dependencies
- [ ] Parallel agents run concurrently where possible
- [ ] Quality gates trigger re-runs when thresholds not met
- [ ] Checkpointing enables resume from any agent boundary

---

## Open Questions

1. **Model selection:** Which models work best for each task? Requires experimentation.
2. **Multi-model overhead:** How to minimize model switching cost on DGX?
3. **Quality metrics:** How do we objectively measure "quality" per task?
4. **Verification prompts:** What makes a good self-verification prompt?

---

## Appendix: File Structure

After all phases complete:

```
src/
├── analyzer.py              # Updated to use orchestrator
├── pipeline/
│   ├── llm.py               # Enhanced with timing
│   ├── metrics.py           # NEW: Metrics collection
│   ├── chapter_detection/   # Unchanged
│   ├── character_extraction.py
│   ├── chapter_summary.py
│   └── pronunciation.py
└── agents/
    ├── __init__.py          # NEW
    ├── base.py              # NEW: Agent ABC
    ├── config.py            # NEW: Configuration
    ├── orchestrator.py      # NEW: Coordination
    ├── structure.py         # NEW: StructureAgent
    ├── characters.py        # NEW: CharacterAgent
    ├── summaries.py         # NEW: SummaryAgent
    └── pronunciation.py     # NEW: PronunciationAgent
```

---

## Revision History

| Date | Change |
|------|--------|
| 2025-12-27 | Initial draft |
