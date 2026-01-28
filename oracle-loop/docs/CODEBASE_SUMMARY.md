# Audiobook Prep Codebase Summary

Pre-computed summary of codebase structure to minimize exploration overhead.

> **⚠️ IMPORTANT: V2 Pipeline is Active**
>
> As of **monkeys_paw attempt 14**, the oracle loop uses the **V2 character extraction pipeline**.
> Earlier attempts (1-13) used the V1 pipeline and those logs/summaries may not be relevant.
>
> **When making fixes, focus on V2 files:**
> - `src/pipeline/character_extraction_v2/` (main_cast.py, grounding.py, narrator.py, etc.)
> - `src/agents/characters.py`
>
> **Note:** V1 character extraction has been removed from the codebase.

## Data Flow for Character Extraction V2

Understanding the full data flow is critical for root cause analysis. **If you keep modifying the same file without success, look UPSTREAM.**

```
Source File (txt/pdf/epub)
       │
       ▼
┌─────────────────────────┐
│      Ingestion          │  ← Text normalization can destroy patterns
│   (src/ingestion/)      │     or corrupt character names
│   base.py, refine.py    │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│   Structure Detection   │  ← Chapter boundaries affect EVERYTHING downstream
│ (chapter_detection/)    │     Wrong chapters = wrong context for all later stages
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│   Chapter Summaries     │  ← V2 extracts characters FROM THESE SUMMARIES
│ (chapter_summary/       │     If summaries confuse characters, V2 will too!
│  summarizer.py)         │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│   Character V2          │  ← Reads SUMMARIES, not raw text
│ (character_extraction_v2/│     Fixing here won't help if input is wrong
│  main_cast.py)          │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│   Grounding Gate        │  ← Verifies characters against raw text
│   (grounding.py)        │     Rejects hallucinations with 0 text matches
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│   Narrator Detection    │  ← Uses summaries + main cast context
│   (narrator.py)         │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│   Supporting Cast       │  ← NER-based extraction for minor characters
│   (supporting.py)       │
└─────────────────────────┘
```

### Critical Insight for Debugging

**If character extraction keeps failing despite multiple fixes to `main_cast.py`:**

1. **Check summaries FIRST** - Do the chapter summaries correctly distinguish the characters?
   ```bash
   grep -i "character_name" ../output/{book}/analysis.json | head -20
   ```

2. **Check ingestion** - Is the source text being corrupted?
   ```bash
   grep -i "character_name" ../test_texts/{book}.txt | head -10
   ```

3. **Check structure** - Are chapter boundaries causing context confusion?

The bug you're looking for may be several layers upstream from where the symptom appears.

---

## Key Directories

| Directory | Purpose | Key Files |
|-----------|---------|-----------|
| `src/analyzer.py` | Main orchestrator | 2587 lines - entry point for analysis |
| `src/pipeline/` | Analysis pipelines | Character, chapter, summary, pronunciation |
| `src/agents/` | Agent infrastructure | Base classes, config, specialized agents |
| `src/models.py` | Pydantic data models | AnalysisResult, Character, etc. |
| `src/ingestion/` | Document parsers | PDF, EPUB, DOCX, TXT |
| `src/export/` | Output generation | HTML report, JSON export |

## Character Extraction Pipeline (V1 - Legacy)

The V1 character extraction flow (merge heuristics):

```
Text → NER Extraction → Proposers → Consensus → Alias Resolution → Profile Generation
```

| Component | File | Key Lines | Purpose |
|-----------|------|-----------|---------|
| Pipeline orchestration | `src/pipeline/character_extraction/pipeline.py` | Full file | Main extraction logic |
| Consensus builder | `src/pipeline/character_extraction/consensus.py` | 2520 lines total | Alias resolution, merging |
| Merge candidate pairs | `consensus.py` | 873-984 | `_candidate_pairs_for_merge()` |
| LLM pairwise merge | `consensus.py` | 985-1309 | `_llm_pairwise_merge_decision()` |
| Post-LLM merge check | `consensus.py` | 1310-1570 | `_post_llm_merge_check()` |
| Merge validation | `consensus.py` | 1571-1700 | `_validate_merge()` - **KEY FIX LOCATION** |
| Heuristic alias resolution | `consensus.py` | 578-660 | `_heuristic_alias_resolution()` |
| LLM alias resolution | `consensus.py` | 1207-1250 | `_llm_alias_resolution()` |
| Pairwise alias resolution | `consensus.py` | 1036-1130 | `_llm_alias_resolution_pairwise()` |
| Aggressive alias patterns | `consensus.py` | 1411-1500 | `_check_aggressive_alias_patterns()` |
| Character agent wrapper | `src/agents/characters.py` | Full file | Agent that wraps pipeline |

## Character Extraction V2 Pipeline (Summary-Driven)

V2 uses a profile-first approach that eliminates complex merge heuristics:

```
Chapter Summaries → Main Cast Extraction → Mention Search → Grounding Gate → Narrator Detection → Supporting Cast
```

**Key insight**: Extract character PROFILES (with aliases) from summaries, not names from raw text.

| Component | File | Purpose |
|-----------|------|---------|
| Main cast extraction | `src/pipeline/character_extraction_v2/main_cast.py` | Extract 10-15 main characters from summaries |
| Mention search | `src/pipeline/character_extraction_v2/mention_search.py` | Find all name variants in text |
| Grounding gate | `src/pipeline/character_extraction_v2/grounding.py` | Reject hallucinated characters (0 text hits) |
| Narrator detection | `src/pipeline/character_extraction_v2/narrator.py` | Detect POV from summaries with main cast context |
| Supporting cast | `src/pipeline/character_extraction_v2/supporting.py` | NER-based minor character extraction |
| V2 Agent | `src/agents/characters.py` | Orchestrates V2 pipeline |

**V2 CLI Usage**: `audiobook-prep analyze book.txt` (V2 is the default and only implementation)

**V2 Dependency**: V2 requires summaries FIRST (structure → summaries → characters_v2)

### V2 Architecture (Simplified Prompts - Jan 2026)

The V2 pipeline was refactored to use **simple prompts + deterministic verification**:

**Two-Pass Extraction (Default)**
- **Pass 1**: Identify cast members (canonical names only, NO aliases)
- **Pass 2**: For each character, resolve aliases with focused context

**Key Data Structures in `main_cast.py`**:
```python
@dataclass
class MainCastProfile:
    canonical_name: str
    aliases: list[str]           # Confirmed aliases
    uncertain_aliases: list[str] # LLM unsure - let verification decide
    role: str                    # protagonist/antagonist/supporting/minor
    is_symbolic: bool            # True for objects/forces (e.g., "the monkey's paw")
    description: str
```

**Philosophy: Soft Prompts + Hard Verification**
- Prompts are ~30 lines with 5 simple rules (not 100+ lines with 17 rules)
- LLM can express uncertainty via `uncertain_aliases`
- Deterministic verification (mention_search, grounding) makes final decisions
- `is_symbolic=True` marks plot-central objects/forces as valid extractions

**Mention Search Robustness**:
- Handles apostrophe variants (' vs ')
- Handles hyphen variants (- vs – vs —)
- Optional periods in titles ("Mr." matches "Mr")
- Span-based overlap detection (longest match wins)

## Narrator Detection

| Component | File | Key Lines | Purpose |
|-----------|------|-----------|---------|
| Main detection | `src/analyzer.py` | 1986-2076 | `_detect_narrator()` |
| Mark narrator in map | `src/analyzer.py` | 2077-2146 | `_mark_narrator_in_character_map()` |
| Role injection | `src/analyzer.py` | 2147-2200 | `_apply_narrator_role_injection()` |
| Summary-based detection | `src/analyzer.py` | 1322-1360 | Step 6.5 in main flow |

## Profile Generation

| Component | File | Key Lines | Purpose |
|-----------|------|-----------|---------|
| Profile generator | `src/analyzer.py` | 1570-1700 | `_generate_character_profile()` |
| Profile enrichment | `src/analyzer.py` | 1200-1250 | Called in main extraction loop |

## Chapter Detection

| Component | File | Purpose |
|-----------|------|---------|
| Pipeline | `src/pipeline/chapter_detection/` | Structure detection |
| Proposers | `src/pipeline/chapter_detection/proposers/` | Multiple detection strategies |
| Structure agent | `src/agents/structure.py` | Agent wrapper |

## Summaries

| Component | File | Purpose |
|-----------|------|---------|
| Pipeline | `src/pipeline/summary/` | Chapter summary generation |
| Summarizer | `src/pipeline/chapter_summary/summarizer.py` | Core summary logic |
| Summary agent | `src/agents/summaries.py` | Agent wrapper |

## Pronunciation

| Component | File | Purpose |
|-----------|------|---------|
| Pipeline | `src/pipeline/pronunciation/` | Pronunciation guide |
| Extractor | `src/pipeline/pronunciation_guide/extractor.py` | Core extraction logic |
| Pronunciation agent | `src/agents/pronunciation.py` | Agent wrapper |

## Configuration

| File | Purpose |
|------|---------|
| `src/agents/config.py` | Model settings, chunk sizes, `PipelineTuningConfig` |
| `~/.config/audiobook_prep/gui_settings.json` | Runtime model configuration |
| `RECOMMENDED_AGENT_MODELS` in config.py | Per-agent model recommendations |

## Common Fix Locations by Issue Type

### V1 (Legacy) Fix Locations

| Issue | Primary Fix Location | Lines |
|-------|---------------------|-------|
| Character false split | `consensus.py` - `_validate_merge()` | 1571-1700 |
| Character false merge | `consensus.py` - `_validate_merge()` | 1571-1700 |
| Alias not resolved | `consensus.py` - `_llm_alias_resolution()` | 1207-1250 |
| Wrong narrator | `analyzer.py` - `_detect_narrator()` | 1986-2076 |
| Profile issues | `analyzer.py` - `_generate_character_profile()` | 1570-1700 |
| LLM merge decision | `consensus.py` - `_llm_pairwise_merge_decision()` | 985-1309 |
| Chunking issues | `src/agents/config.py` - `PipelineTuningConfig` | N/A |

### V2 Fix Locations

**⚠️ IMPORTANT: Prefer programmatic fixes over prompt changes. See PROMPT_fix.md "Fix Philosophy" section.**

| Issue | Primary Fix Location | Recommended Approach |
|-------|---------------------|----------------------|
| Main cast missing character | Check **summaries first** | If summaries have it, check grounding threshold |
| Alias not resolved | `mention_search.py` | Improve pattern matching, not prompt |
| Wrong canonical name | `characters.py` post-processing | Programmatic: prefer longer/fuller names |
| Wrong role assignment | `characters.py` promotion logic | Programmatic: mention count thresholds |
| Hallucinated character | `grounding.py` - `GroundingGate` | Adjust min_mentions threshold |
| Wrong narrator | `narrator.py` | Check summaries for POV clues first |
| Non-character extracted | `characters.py` post-processing | Programmatic filter if needed |
| Symbolic entity issues | No fix needed | `is_symbolic=True` marks these as valid |

**Remember**: If a prompt fix doesn't work after 2 attempts, switch to programmatic approach.

## Key Prompts for LLM Operations

| Operation | File | Search Pattern |
|-----------|------|----------------|
| Character extraction prompts | `src/pipeline/character_extraction/proposers/*.py` | `system.*prompt` |
| Alias resolution prompt | `consensus.py` | `_build_alias_prompt_global` (line 844) |
| Epithet resolution prompt | `consensus.py` | Line 63 comment |
| Summary prompts | `src/pipeline/chapter_summary/summarizer.py` | `system.*prompt` |
| Pronunciation prompts | `src/pipeline/pronunciation_guide/extractor.py` | `system.*prompt` |

## Quick Grep Commands

```bash
# Find where a specific character issue originates
grep -n "canonical_name" src/pipeline/character_extraction/consensus.py | head -20

# Find merge validation logic
grep -n "_validate_merge\|should_merge" src/pipeline/character_extraction/consensus.py

# Find narrator logic
grep -n "is_narrator\|narrator" src/analyzer.py | head -30

# Find profile generation
grep -n "_generate_character_profile\|profile" src/analyzer.py | head -20

# Find LLM prompts in character extraction
grep -rn "system.*=.*\"" src/pipeline/character_extraction/ | grep -i prompt
```
