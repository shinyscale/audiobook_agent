# PRD: Competitive Consensus for Profile Generation & Overview Summary

**Version:** 1.0
**Status:** Draft
**Priority:** Medium
**Target:** Improved profile and overview quality through multi-model consensus
**Depends On:** competitive-multi-llm-v1 (implemented)

## Executive Summary

Extend the competitive multi-LLM architecture to two additional stages:
1. **Character Profile Generation** - Rich profiles with appearance, personality, voice guidance
2. **Overview/Plot Summary** - Book-level narrative synthesized from chapter summaries

Both stages benefit from multi-model consensus to catch hallucinations, improve trait identification accuracy, and prevent villain whitewashing in moral alignment.

**Proposal:** Add competitive consensus voting to profile generation and overview summary, following the established pattern from character extraction. Multiple LLMs generate content in parallel, then results are merged using voting/union strategies.

---

## Problem Statement

### Current State

Both profile generation and overview summary use a single LLM call:
- **Profile Generation:** `CharacterProfileGenerator.generate_profile()` - one LLM call per character
- **Overview Summary:** `OverviewGenerator._generate_plot_summary()` - one LLM call per book

### Root Cause

Single-LLM decisions are vulnerable to:
1. **Missed details** - one model might not notice subtle personality traits or appearance details
2. **Moral misalignment** - LLM might describe villains as "charming" without emphasizing harmful actions
3. **Theme hallucination** - invented themes not supported by chapter summaries
4. **Inconsistent tone/style** - single perspective on narrative style

### Why Competitive Approach Helps

**Profile Example:** For a villain character:
- Model A (strict): Identifies "manipulative, deceitful" traits, moral_alignment="antagonist"
- Model B (balanced): Identifies "charming, intelligent" traits, moral_alignment="morally_ambiguous"
- Model C (inclusive): Identifies "sophisticated, charismatic" traits, moral_alignment="complex"

With union strategy for harmful_actions and majority vote for moral_alignment:
- Harmful actions are never missed (union)
- Moral alignment reflects consensus (antagonist wins if 2/3)

**Overview Example:** For theme extraction:
- Model A: ["obsession", "revenge", "mortality"]
- Model B: ["obsession", "madness", "isolation"]
- Model C: ["obsession", "revenge", "madness"]

With 2/3 voting: themes = ["obsession", "revenge", "madness"] (each appears 2+ times)

---

## Proposed Solution

### Part 1: Overview/Plot Summary

**File:** `src/pipeline/overview/generator.py`

**Current flow:**
```
Chapter Summaries → Single LLM → {plot_summary, themes, narrative_style}
```

**Proposed flow:**
```
Chapter Summaries
       │
       ├─▶ Model A (temp=0.5) ─┐
       ├─▶ Model B (temp=0.7) ─┼─▶ Merge/Vote ─▶ {plot_summary, themes, narrative_style}
       └─▶ Model C (temp=0.9) ─┘
```

**Consensus Strategy:**

| Field | Strategy | Rationale |
|-------|----------|-----------|
| `plot_summary` | Best-of-N (most theme overlap) | Pick most comprehensive |
| `themes` | Union + voting (2/3) | Keep themes mentioned by majority |
| `narrative_style` | Majority vote | Critical for narrator |

**Implementation:**

```python
class OverviewGenerator:
    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        competitive_config: Optional["CompetitiveConfig"] = None,
    ):
        self.llm = llm_client
        self.competitive_config = competitive_config
        self._competitor_clients: list[LLMClient] = []

        if self._use_competitive_overview():
            self._init_competitor_clients()

    def _use_competitive_overview(self) -> bool:
        return (
            self.competitive_config is not None
            and self.competitive_config.enabled
            and self.competitive_config.competitive_overview
        )

    def _generate_plot_summary(self, ...):
        if self._use_competitive_overview() and self._competitor_clients:
            return self._generate_plot_summary_competitive(...)
        return self._generate_plot_summary_single(...)

    def _generate_plot_summary_competitive(self, ...):
        # Run all competitors in parallel
        results = []
        with ThreadPoolExecutor(max_workers=len(self._competitor_clients)) as executor:
            futures = [executor.submit(self._query_single, client, prompt) for client in self._competitor_clients]
            results = [f.result() for f in as_completed(futures)]

        return self._merge_competitive_overviews(results)

    def _merge_competitive_overviews(self, results: list[dict]) -> dict:
        # Union + voting for themes
        theme_counts = Counter()
        for r in results:
            for theme in r.get("themes", []):
                theme_counts[theme.lower()] += 1

        threshold = len(results) * 0.67
        consensus_themes = [t for t, count in theme_counts.items() if count >= threshold]

        # Majority vote for narrative_style
        style_counts = Counter(r.get("narrative_style") for r in results)
        narrative_style = style_counts.most_common(1)[0][0]

        # Best plot_summary based on theme overlap
        best_summary = max(
            results,
            key=lambda r: sum(1 for t in r.get("themes", []) if t.lower() in consensus_themes)
        ).get("plot_summary", "")

        return {
            "plot_summary": best_summary,
            "themes": consensus_themes,
            "narrative_style": narrative_style,
        }
```

---

### Part 2: Character Profile Generation

**File:** `src/pipeline/character_profiling/generator.py`

**Current flow:**
```
Character + Passages → Single LLM → CharacterProfile
```

**Proposed flow:**
```
Character + Passages
       │
       ├─▶ Model A (temp=0.5) ─┐
       ├─▶ Model B (temp=0.7) ─┼─▶ Merge/Vote ─▶ CharacterProfile
       └─▶ Model C (temp=0.9) ─┘
```

**Consensus Strategy:**

| Field | Strategy | Rationale |
|-------|----------|-----------|
| `appearance.details` | Union + dedup | Catch details one model misses |
| `appearance.distinguishing_features` | Union + dedup | Never miss key features |
| `personality.traits` | Union + voting (2/3) | Consensus on trait identification |
| `personality.moral_alignment` | Majority vote | Critical - prevents villain whitewashing |
| `personality.key_behaviors` | Union + dedup | Catch all behaviors |
| `voice_guidance.suggested_tone` | Majority vote | Most important for narrator |
| `voice_guidance.dialect_notes` | Union | Catch all dialect hints |
| `voice_guidance.verbal_tics` | Union | Catch all speech patterns |
| `action_analysis.harmful_actions` | Union | NEVER miss harmful actions |
| `action_analysis.beneficial_actions` | Union | Catch all positive actions |
| `relationships` | Union + voting | Keep relationships with 2/3 agreement |

**Implementation:**

```python
class CharacterProfileGenerator:
    def __init__(
        self,
        llm_client: LLMClient,
        summary_map: Optional[ChapterSummaryMap] = None,
        competitive_config: Optional["CompetitiveConfig"] = None,
    ):
        self.llm = llm_client
        self.summary_map = summary_map
        self.competitive_config = competitive_config
        self._competitor_clients: list[LLMClient] = []

        if self._use_competitive_profiles():
            self._init_competitor_clients()

    def generate_profile(self, character, ...):
        if self._use_competitive_profiles() and self._competitor_clients:
            return self._generate_profile_competitive(character, ...)
        return self._generate_profile_single(character, ...)

    def _generate_profile_competitive(self, character, ...):
        # Build prompt once
        prompt = self._build_profile_prompt(character, ...)

        # Run all competitors in parallel
        results = []
        with ThreadPoolExecutor(max_workers=len(self._competitor_clients)) as executor:
            futures = [executor.submit(client.query_json, prompt, system=PROFILE_GENERATION_SYSTEM)
                      for client in self._competitor_clients]
            for future in as_completed(futures):
                result, response = future.result()
                if response.success and result:
                    results.append(result)

        return self._merge_competitive_profiles(results, character)

    def _merge_competitive_profiles(self, results: list[dict], character) -> CharacterProfile:
        # Implemented with strategies from table above
        ...
```

---

## Configuration & CLI

### Add to CompetitiveConfig (src/agents/config.py)

```python
@dataclass
class CompetitiveConfig:
    # Existing flags
    competitive_consensus: bool = True      # Character merges
    competitive_structure: bool = False     # Chapter boundaries
    competitive_summaries: bool = False     # Chapter summaries

    # NEW flags
    competitive_profiles: bool = False      # Character profile generation
    competitive_overview: bool = False      # Plot/book summary
```

### Add CLI Flags (src/cli.py)

```bash
--competitive-profiles    # Enable multi-model profile generation
--competitive-overview    # Enable multi-model plot summary
```

Update `--competitive-all` to include new stages:
```python
enable_profiles = competitive_profiles or competitive_all
enable_overview = competitive_overview or competitive_all
```

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/agents/config.py` | Add `competitive_profiles` and `competitive_overview` flags |
| `src/cli.py` | Add `--competitive-profiles` and `--competitive-overview` flags |
| `src/pipeline/overview/generator.py` | Add competitive plot summary generation |
| `src/pipeline/character_profiling/generator.py` | Add competitive profile generation |
| `src/pipeline/character_profiling/pipeline.py` | Pass competitive_config to generator |
| `src/analyzer.py` | Pass competitive_config to profiling and overview |
| `oracle-loop/state/manifest.json` | Add new stages to competitive_stages |
| `oracle-loop/prompts/PROMPT_analyze.md` | Document new flags |

---

## Implementation Phases

### Phase 1: Config & CLI
**Scope:** Add new flags
**Risk:** Low - additive only
**Deliverables:**
- Add `competitive_profiles` and `competitive_overview` to CompetitiveConfig
- Add CLI flags
- Update `--competitive-all` to include new stages

### Phase 2: Overview Generator
**Scope:** Add competitive plot summary
**Risk:** Low - self-contained
**Deliverables:**
- Add competitive_config to OverviewGenerator
- Implement `_generate_plot_summary_competitive()`
- Implement `_merge_competitive_overviews()`

### Phase 3: Profile Generator
**Scope:** Add competitive profile generation
**Risk:** Medium - complex merging logic
**Deliverables:**
- Add competitive_config to CharacterProfileGenerator
- Implement `_generate_profile_competitive()`
- Implement `_merge_competitive_profiles()` with all field strategies

### Phase 4: Analyzer Integration
**Scope:** Wire up both pipelines
**Risk:** Low - plumbing only
**Deliverables:**
- Pass competitive_config to OverviewGenerator
- Pass competitive_config to CharacterProfilingPipeline

### Phase 5: Oracle Loop
**Scope:** Update manifest and prompts
**Risk:** Low - documentation only
**Deliverables:**
- Add "profiles" and "overview" to competitive_stages
- Document new flags in PROMPT_analyze.md

---

## Validation Strategy

### Test Cases

**Overview:**
| Test Case | Expected Result |
|-----------|-----------------|
| Poe short story themes | Consistent horror/death themes across runs |
| First-person narrative detection | Majority vote determines style |
| Theme hallucination | Fabricated themes rejected by voting |

**Profiles:**
| Test Case | Expected Result |
|-----------|-----------------|
| Villain moral_alignment | "antagonist" wins over "complex" |
| Harmful actions | Union captures all violent/manipulative acts |
| Voice guidance tone | Consensus determines narrator guidance |

### Success Metrics

1. **Theme Consistency:** Same themes across 3 consecutive runs (>90% overlap)
2. **Moral Alignment Accuracy:** Villains correctly identified as antagonist (>95%)
3. **Trait Coverage:** Union strategy captures more traits than single-model (+20%)
4. **Quality Score:** Improve overall oracle loop score by 0.2+ points

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| 3x LLM cost per profile | Certain | Medium | Only enable for important characters |
| Conflicting traits merged | Medium | Low | Voting thresholds filter noise |
| Slower profile generation | Medium | Medium | Parallel execution minimizes impact |
| Union produces too many traits | Medium | Low | Quality filter on final output |

---

## References

- `spec/competitive-multi-llm-v1.prd.md` - Original competitive architecture
- `src/pipeline/character_extraction_v2/main_cast.py` - Reference implementation
- `src/pipeline/chapter_summary/summarizer.py` - Competitive summary implementation
