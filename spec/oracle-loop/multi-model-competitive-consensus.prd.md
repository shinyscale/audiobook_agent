# Multi-Model Competitive Consensus

## Overview

Enable competitive consensus to use different LLM models (not just different temperatures) for each competitor. This adds model diversity to the voting system, reducing single-model bias in character merge decisions.

## Problem Statement

Currently, competitive consensus runs 3 LLM calls with different temperatures (0.5, 0.7, 0.9) and prompt styles (strict, contextual, inclusive), but all 3 use the **same underlying model**. This limits the diversity of perspectives - if the model has a systematic bias, all 3 competitors will share it.

**Current behavior (line 298 in main_cast.py):**
```python
model=base_config.model  # Same for all competitors
```

## Requirements

### R1: Per-Competitor Model Configuration

Each competitor must be independently configurable with:
- Model name (e.g., `qwen3:30b-instruct`, `qwen2.5:32b`, `llama3.1:70b`)
- Provider (e.g., `ollama`, `openai`, `anthropic`)
- Temperature (existing: 0.5, 0.7, 0.9)
- Prompt style (existing: strict, contextual, inclusive)

### R2: Backward Compatibility

- If no per-competitor models specified, fall back to current behavior (same model, different temps)
- `--competitive-consensus` flag must continue working unchanged
- Existing `gui_settings.json` files must work without modification

### R3: CLI Interface

Add `--competitive-model` flag that can be specified multiple times:
```bash
audiobook-prep analyze book.txt \
  --competitive-model "qwen3:30b-instruct:0.5:strict" \
  --competitive-model "qwen2.5:32b:0.7:contextual" \
  --competitive-model "llama3.1:70b:0.9:inclusive"
```

Format: `model[@provider][:temperature][:prompt_style]`

### R4: Configuration File Support

Support in `gui_settings.json`:
```json
{
  "competitive_consensus": {
    "enabled": true,
    "competitor_models": [
      {"model": "qwen3:30b-instruct", "provider": "ollama", "temperature": 0.5, "prompt_style": "strict"},
      {"model": "qwen2.5:32b", "provider": "ollama", "temperature": 0.7, "prompt_style": "contextual"},
      {"model": "llama3.1:70b", "provider": "ollama", "temperature": 0.9, "prompt_style": "inclusive"}
    ]
  }
}
```

### R5: Logging

Log which model is being used for each competitor vote to aid debugging:
```
Competitor 'precise' (qwen3:30b-instruct @ 0.5): YES (confidence=0.85)
Competitor 'balanced' (qwen2.5:32b @ 0.7): YES (confidence=0.72)
Competitor 'inclusive' (llama3.1:70b @ 0.9): NO (confidence=0.45)
Result: APPROVED (2/3 votes)
```

## Technical Design

### New Data Model

Add to `src/agents/config.py`:

```python
@dataclass
class CompetitorModelConfig:
    """Configuration for a single competitor in multi-model consensus."""
    model: str
    provider: str = "ollama"
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    prompt_style: str = "contextual"
    temperature: float = 0.7
    name: Optional[str] = None
```

### Extended CompetitiveConfig

Add to `CompetitiveConfig` in `src/agents/config.py`:

```python
competitor_models: list[CompetitorModelConfig] = field(default_factory=list)

def get_competitor_configs(self, base_model, base_provider, base_url, base_api_key):
    """Return competitor configs, falling back to base model if none specified."""
    if self.competitor_models:
        return self.competitor_models
    # Generate from COMPETITOR_CONFIGS with base model (backward compatible)
    from ..pipeline.character_extraction.prompts import COMPETITOR_CONFIGS
    return [
        CompetitorModelConfig(
            model=base_model, provider=base_provider, base_url=base_url,
            api_key=base_api_key, prompt_style=c["prompt_style"],
            temperature=c["temperature"], name=c["name"]
        )
        for c in COMPETITOR_CONFIGS
    ]
```

### Updated Client Initialization

Modify `_init_competitor_clients()` in `src/pipeline/character_extraction_v2/main_cast.py`:

```python
def _init_competitor_clients(self) -> None:
    competitor_configs = self.competitive_config.get_competitor_configs(
        base_model=base_config.model,
        base_provider=base_config.provider,
        base_url=base_config.base_url,
        base_api_key=base_config.api_key,
    )

    for comp_config in competitor_configs:
        new_config = LLMConfig(
            provider=comp_config.provider,
            model=comp_config.model,
            base_url=comp_config.base_url or base_config.base_url,
            api_key=comp_config.api_key or base_config.api_key,
            temperature=comp_config.temperature,
            # ... other params from base_config
        )
        client = LLMClient(new_config, metrics=self.llm.metrics)
        self._competitor_clients.append((client, comp_config.prompt_style))
```

## Files to Modify

| File | Changes |
|------|---------|
| `src/agents/config.py` | Add `CompetitorModelConfig` dataclass, extend `CompetitiveConfig` |
| `src/pipeline/character_extraction_v2/main_cast.py` | Update `_init_competitor_clients()` to use per-model configs |
| `src/cli.py` | Add `--competitive-model` argument and parser function |
| `src/analyzer.py` | Pass competitor config from gui_settings to agent |

## Acceptance Criteria

- [ ] `CompetitorModelConfig` dataclass added to config.py
- [ ] `CompetitiveConfig.competitor_models` field added
- [ ] `CompetitiveConfig.get_competitor_configs()` method implemented with fallback
- [ ] `MainCastExtractor._init_competitor_clients()` uses per-competitor models
- [ ] `--competitive-model` CLI flag works (repeatable)
- [ ] Backward compatible: `--competitive-consensus` alone uses same-model behavior
- [ ] Logs show which model voted for each decision
- [ ] All existing tests pass

## Testing

### Unit Tests
```python
def test_competitor_config_backward_compatible():
    """Empty competitor_models uses base model for all."""
    config = CompetitiveConfig(enabled=True)
    configs = config.get_competitor_configs(base_model="qwen2.5:32b", ...)
    assert all(c.model == "qwen2.5:32b" for c in configs)

def test_competitor_config_explicit_models():
    """Explicit models override base model."""
    competitors = [
        CompetitorModelConfig(model="model1"),
        CompetitorModelConfig(model="model2"),
    ]
    config = CompetitiveConfig(enabled=True, competitor_models=competitors)
    configs = config.get_competitor_configs(base_model="ignored", ...)
    assert configs[0].model == "model1"
    assert configs[1].model == "model2"
```

### CLI Test
```bash
audiobook-prep analyze Test_Texts/The\ Cask\ of\ Amontillado\ -\ Poe.txt \
  --competitive-model "qwen3:30b-instruct:0.5:strict" \
  --competitive-model "qwen2.5:32b:0.7:contextual" \
  --html output/test/report.html
```

### Integration Test
Run full analysis and verify logs show different models per competitor vote.
