"""
Main Cast Extraction from Chapter Summaries (F1)

This module extracts the main cast (10-15 characters) from chapter summaries.
The LLM provides canonical names AND aliases together - no merge step needed.

Key principles:
- Summaries are the source of truth for WHO matters
- Raw text is the source of truth for WHAT they're called (grounding)
- Unnamed/descriptive characters are supported (e.g., "the creature")
- No inventing proper names not supported by the text
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ...agents.config import CompetitiveConfig

from ...llm.client import LLMClient, LLMConfig
from ...models import Character, ConfidenceLevel
from ...utils.debug_log import append_debug_event

logger = logging.getLogger(__name__)


@dataclass
class MainCastProfile:
    """Profile for a main cast character extracted from summaries."""

    canonical_name: str
    aliases: list[str] = field(default_factory=list)
    role: str = "supporting"  # protagonist, antagonist, supporting, minor
    description: str = ""
    is_unnamed: bool = False  # True for descriptive handles like "the creature"
    # True for plot-central symbolic objects/forces (e.g., "the monkey's paw", "the green light").
    # These are allowed in main cast by design.
    is_symbolic: bool = False
    # Aliases the model is unsure about. These are NOT treated as true aliases unless
    # later validated (e.g., by deterministic verification or grounding).
    uncertain_aliases: list[str] = field(default_factory=list)


MAIN_CAST_PROMPT = """You are extracting the MAIN CAST from chapter summaries.

Return JSON ONLY. Do not include any explanatory text.

Task:
- Identify 10–15 plot-central entities (people/creatures AND allowed symbolic objects/forces).
- Always include the narrator (if a character) and the title character/entity if applicable.
- Do not invent names not supported by the summaries.
- Provide canonical_name and aliases/variants used in summaries.

Output format - return a JSON object with a "characters" array:
{
  "characters": [
    {
      "canonical_name": "Name",
      "aliases": ["Alias1", "Alias2"],
      "role": "protagonist",
      "description": "Brief description",
      "is_unnamed": false,
      "is_symbolic": false
    }
  ]
}

CHAPTER SUMMARIES:
{summaries}

{plot_summary_section}
"""


# Pass 1: Character Identification Prompt
CHARACTER_IDENTIFICATION_PROMPT = """You are a literary analyst identifying the MAIN CAST of characters from a novel.

TASK: Identify the main characters based on the chapter summaries below. Typically 10-15 characters, but extract ALL significant characters regardless of count (could be fewer for short stories, more for epics).

NOTE: Chapter summaries include a [Characters: ...] list showing who appears in each chapter. Extract ALL characters who appear multiple times across chapters. Treat each entry as a distinct character even if names are similar (e.g., "John" and "John Donaldson" are separate if both appear in the lists).

IMPORTANT RULES:
1. Include plot-central people/creatures AND symbolic objects/forces that have AGENCY or POWER (e.g., a cursed object that grants wishes, a haunting presence that affects characters). Do NOT include settings/locations where events happen (e.g., a library, a house, a garden, a room) - these are backdrops, not characters.
2. **NARRATOR DETECTION (CRITICAL)**: Always include the narrator as a main character. Look for these signals:
   - Phrases like "letter written by X", "X writes to Y", "X expresses/describes/recounts"
   - Repeated third-person references to a character across many summaries (e.g., "Victor Frankenstein receiving...", "Victor consumed by...", "Victor's obsessive pursuit...")
   - If a character's perspective dominates the summaries, they are likely the narrator
   - **EPISTOLARY NARRATIVES**: If early summaries describe letters signed with initials or varying forms (e.g., "R. Walton", "Robert Walton", "R.W.", "Captain Walton"), these refer to ONE narrator - use the FULL NAME form as canonical
3. Use the most common name form in the summaries as canonical_name (or the FULL NAME form if multiple variants exist)
4. Do NOT invent names not supported by the summaries
5. **RELATIONSHIP-BASED REFERENCES**: If summaries frequently mention "his father", "her mother", "the narrator's X", look for the FULL NAME in other summaries and use that as canonical_name (e.g., "his father" + "letter from Alphonse" = "Alphonse Frankenstein"). Include family members who appear across multiple chapters.
6. **FAMILY MEMBERS WITH SHARED NAMES**: If summaries mention family relationships (father/son, uncle/nephew) with shared first names, they are DIFFERENT people. Check for phrases like "X's father Y" or "receives letter from father, Y" - these indicate TWO characters even if names overlap.
7. Do NOT list aliases in this pass
8. **ROLE ASSIGNMENT**:
   - **protagonist**: Main character(s), narrators (especially first-person narrators), characters the story follows
   - **antagonist**: Characters who ACTIVELY OPPOSE the protagonist (villains, rivals) - requires active harmful intent
   - **supporting**: Important recurring characters, title characters, victims, family members (NOT antagonists)
   - **minor**: Characters with limited appearances

CHAPTER SUMMARIES:
{summaries}

{plot_summary_section}

OUTPUT FORMAT:
You MUST return ONLY valid JSON (not an object with an "error" or "message" field).
Return a JSON object with a "characters" array:

{{
  "characters": [
    {{
      "canonical_name": "Full Name or Descriptive Handle",
      "role": "protagonist|antagonist|supporting|minor",
      "description": "Brief description of character's role",
      "is_unnamed": false,
      "is_symbolic": false
    }}
  ]
}}

Do not include explanations or reasoning. Return ONLY the JSON object above.

Extract the main characters now:"""


# Pass 2: Alias Resolution Prompt
ALIAS_RESOLUTION_PROMPT = """You are analyzing the different names and references for a specific character in a novel.

CHARACTER: {character_name}
Role: {role}
Description: {description}

{other_characters_context}

TASK: Find ALL the different ways this character is referred to in the chapter summaries below.

IMPORTANT RULES:
1. Only include an alias if it refers to the SAME entity as {character_name}
2. Include nicknames/titles/shortened forms and obvious spelling variants
3. For unnamed characters or symbolic entities, include all descriptive handles that refer to the same thing
4. If you are unsure, put it in `uncertain_aliases` instead of `aliases`
5. Do NOT include names of other characters/entities
6. CRITICAL: Characters with the same title/profession but different names are DIFFERENT PEOPLE (e.g., "Professor Smith" ≠ "Professor Jones", "Dr. Brown" ≠ "Dr. Green"). Only group names if they clearly refer to the same individual.

CHAPTER SUMMARIES:
{summaries}

OUTPUT FORMAT (JSON):
Return a JSON object with all aliases found:
```json
{{
  "canonical_name": "{character_name}",
  "aliases": ["Alias1", "Alias2", "Title + Name"],
  "uncertain_aliases": ["MaybeAlias1"],
  "confidence_notes": "Optional notes about any uncertain aliases"
}}
```

Find all aliases for {character_name} now:"""


# Consolidated Pass 2: All characters together for alias resolution + duplicate detection
CONSOLIDATED_ALIAS_PROMPT = """You are analyzing characters extracted from chapter summaries of a novel.

## Characters Found in Pass 1
{character_list}

## Your Task

For EACH character above:
1. List ALL aliases (every other name, title, or description referring to this person)
2. Identify if any characters in this list are actually THE SAME PERSON (duplicates)

## Alias Rules — Be Thorough

Include EVERY variant used in the summaries. Common alias types to look for:

- **Shortened names**: first-name-only or last-name-only forms (e.g., "Herbert White" → "Herbert", "Prince Prospero" → "Prospero")
- **Title variations**: with or without title/rank (e.g., "Sergeant-Major Morris" → "Morris", "the sergeant-major")
- **Family/role terms**: if summaries refer to a character as "father", "mother", "the old man", "the old woman", etc., include these as aliases for the named character they describe
- **Descriptive handles**: phrases like "the stranger", "the creature", "the old man" that refer to a named character
- **Narrator references**: if a character IS the first-person narrator, include "the narrator" as their alias
- **Formal/informal forms**: married names, maiden names, full name vs. nickname

Scan every chapter summary for references to each character — aliases often appear in chapters where the proper name is not used.

## Merge Rules

- If two entries are the same person, mark the LESS COMMON name as "merge_into" the MORE COMMON name
- DO NOT merge characters who are different people with similar names (e.g., siblings, spouses with same surname)
- Characters with different first names are usually DIFFERENT people (e.g., "George Wilson" ≠ "Myrtle Wilson")
- Characters with the same title/profession but different names are DIFFERENT people (e.g., "Professor Smith" ≠ "Professor Jones")
- If a character IS the narrator, DO NOT add "the narrator" as a separate character - add it as an alias instead

## Chapter Summaries (for reference)
{summaries}

## Output Format
Return a JSON object with a "characters" array:
```json
{{
  "characters": [
    {{
      "canonical_name": "Victor Frankenstein",
      "aliases": ["Victor", "Frankenstein", "the narrator"],
      "uncertain_aliases": [],
      "merge_into": null
    }},
    {{
      "canonical_name": "the narrator",
      "aliases": [],
      "uncertain_aliases": [],
      "merge_into": "Victor Frankenstein"
    }}
  ]
}}
```

Note: "merge_into" should be null for characters that are unique, or the canonical_name of the character this entry should merge into.

Analyze all characters now:"""


class MainCastExtractor:
    """
    Extracts main cast profiles from chapter summaries.

    This is the core of the v2 architecture: instead of extracting names
    and trying to merge them, we ask the LLM to identify the important
    characters with their aliases directly from the summaries.
    """

    def __init__(
        self,
        llm_client: LLMClient,
        competitive_config: Optional["CompetitiveConfig"] = None,
        json_llm: Optional[LLMClient] = None,
    ):
        self.llm = llm_client
        self.competitive_config = competitive_config
        # JSON-capable LLM client for fallback when primary model fails JSON parsing
        self.json_llm = json_llm
        self._competitor_clients: list[tuple[LLMClient, str]] = []

        # Collect vote records for consensus logging
        self.vote_records: list[dict] = []

        # Initialize competitive LLM clients if enabled
        if (
            competitive_config
            and competitive_config.enabled
            and competitive_config.competitive_consensus
        ):
            self._init_competitor_clients()

    def _init_competitor_clients(self) -> None:
        """Initialize LLM clients for competitive consensus.

        Supports multi-model consensus: each competitor can use a different model
        (configured via CompetitiveConfig.competitor_models) or fall back to
        single-model with different temperatures (backward compatible).
        """
        if not self.llm or not self.competitive_config:
            return

        base_config = self.llm.config

        # Get competitor configurations (multi-model or single-model fallback)
        competitor_configs = self.competitive_config.get_competitor_configs(
            base_model=base_config.model,
            base_provider=base_config.provider,
            base_url=base_config.base_url,
            base_api_key=base_config.api_key,
        )

        logger.info(
            f"MainCastExtractor: Initializing competitive consensus with {len(competitor_configs)} competitors"
        )

        for comp_config in competitor_configs:
            # Determine if this is a multi-model setup (different models)
            is_multi_model = comp_config.model != base_config.model
            model_info = f"{comp_config.model}" if is_multi_model else f"{comp_config.model}@{comp_config.temperature}"

            logger.info(
                f"  Competitor '{comp_config.name or comp_config.prompt_style}': "
                f"{model_info} ({comp_config.prompt_style})"
            )

            new_config = LLMConfig(
                provider=comp_config.provider,
                model=comp_config.model,
                base_url=comp_config.base_url or base_config.base_url,
                api_key=comp_config.get_api_key() or base_config.api_key,
                temperature=comp_config.temperature,
                max_tokens=base_config.max_tokens,
                context_length=base_config.context_length,
                think=base_config.think,
                top_p=base_config.top_p,
                top_k=base_config.top_k,
                presence_penalty=base_config.presence_penalty,
            )
            client = LLMClient(new_config, metrics=self.llm.metrics)
            self._competitor_clients.append((client, comp_config.prompt_style))

    def _use_competitive_consensus(self) -> bool:
        """Check if competitive consensus should be used."""
        return (
            self.competitive_config is not None
            and self.competitive_config.enabled
            and self.competitive_config.competitive_consensus
            and len(self._competitor_clients) > 0
        )

    def _warm_competitor_models(self) -> None:
        """Pre-load all competitor models into Ollama memory for true parallel execution.

        When running multiple LLM models in parallel, Ollama may need to load/unload
        models between requests if they aren't already in memory. This method sends
        a minimal prompt to each competitor model to force Ollama to load them all
        into memory before the actual analysis begins.

        For systems with sufficient memory (e.g., 128GB), this enables true parallel
        execution without model swapping overhead. Configure Ollama with:
        - OLLAMA_MAX_LOADED_MODELS=3 (or higher based on available memory)
        - OLLAMA_KEEP_ALIVE=30m (keep models loaded longer)

        Memory estimates for 30B models:
        - Q4: ~17GB per model
        - Q5: ~21GB per model
        - Q8: ~32GB per model
        """
        if not self._competitor_clients:
            return

        # Check if we have multiple different models (multi-model setup)
        unique_models = set()
        for client, _ in self._competitor_clients:
            unique_models.add(client.config.model)

        if len(unique_models) <= 1:
            # Single model with different temperatures - no pre-warming needed
            logger.debug("Single model competitive setup - skipping pre-warm")
            return

        logger.info(
            f"Pre-warming {len(unique_models)} competitor models for parallel execution: "
            f"{sorted(unique_models)}"
        )

        def warm_model(client_tuple: tuple[LLMClient, str]) -> tuple[str, bool]:
            """Send minimal prompt to force model load."""
            client, style = client_tuple
            model_name = client.config.model
            try:
                # Minimal prompt to force model load without heavy computation
                client.query("Hello", system="Respond with 'OK'")
                logger.info(f"  Warmed: {model_name} ({style})")
                return (model_name, True)
            except Exception as e:
                logger.warning(f"  Failed to warm {model_name}: {e}")
                return (model_name, False)

        # Warm all models in parallel
        with ThreadPoolExecutor(max_workers=len(self._competitor_clients)) as executor:
            results = list(executor.map(warm_model, self._competitor_clients))

        # Log summary
        successful = sum(1 for _, success in results if success)
        logger.info(f"Model pre-warming complete: {successful}/{len(results)} models loaded")

    def extract(
        self,
        chapter_summaries: list[str],
        plot_summary: Optional[str] = None,
        use_two_pass: bool = True,
    ) -> list[MainCastProfile]:
        """
        Extract main cast profiles from chapter summaries.

        Args:
            chapter_summaries: List of chapter summary strings
            plot_summary: Optional overall plot summary
            use_two_pass: Whether to use two-pass extraction (default: True)

        Returns:
            List of MainCastProfile objects representing the main cast
        """
        if not chapter_summaries:
            logger.warning("No chapter summaries provided for main cast extraction")
            return []

        # Pre-warm competitor models for true parallel execution
        # This ensures all models are loaded into Ollama memory before analysis
        if self._use_competitive_consensus():
            self._warm_competitor_models()

        # Format summaries for the prompt
        summaries_text = "\n\n".join(
            f"Chapter {i+1}:\n{summary}" for i, summary in enumerate(chapter_summaries)
        )

        # Add plot summary if available
        plot_section = ""
        if plot_summary:
            plot_section = f"\nOVERALL PLOT SUMMARY:\n{plot_summary}\n"

        # Pre-extraction pattern detection to guide the LLM
        pattern_hints = self._detect_patterns(summaries_text, plot_summary)
        if pattern_hints:
            logger.info(f"Detected patterns to guide extraction: {pattern_hints}")

        # Choose extraction method
        if use_two_pass:
            profiles = self._extract_two_pass(summaries_text, plot_section, pattern_hints)
        else:
            profiles = self._extract_single_pass(summaries_text, plot_section, pattern_hints)

        if not profiles:
            logger.error(
                f"Main cast extraction returned 0 profiles! This means ALL characters will be extracted via "
                f"NER as supporting cast, leading to fragmentation. Check logs above for LLM failure details. "
                f"Number of summaries provided: {len(chapter_summaries)}, First summary length: "
                f"{len(chapter_summaries[0]) if chapter_summaries else 0} chars"
            )
            return []

        # region agent log
        try:
            focus = []
            for p in profiles:
                text = (p.canonical_name + " " + " ".join(p.aliases)).lower()
                if any(
                    k in text
                    for k in (
                        "creature",
                        "monster",
                        "fiend",
                        "daemon",
                        "wretch",
                        "being",
                        "lacey",
                        "old man",
                    )
                ):
                    focus.append({"canonical": p.canonical_name, "aliases": p.aliases})
            append_debug_event(
                {
                    "sessionId": "debug-session",
                    "runId": "frankenstein-pre",
                    "hypothesisId": "H1",
                    "location": "src/pipeline/character_extraction_v2/main_cast.py:extract",
                    "message": "Post-LLM parsed profiles (focused subset)",
                    "data": {"count": len(profiles), "focus": focus},
                    "timestamp": int(time.time() * 1000),
                }
            )
        except Exception:
            pass
        # endregion

        # CRITICAL: Verify aliases to prevent false merges
        # This catches LLM hallucinations like "Mr. Sloane" with alias "Mr. McKee"
        profiles = self.verify_aliases(profiles, chapter_summaries)

        # POST-PROCESSING: Merge descriptive entity references
        # The LLM sometimes creates separate entries for "the creature", "the monster", etc.
        # when they refer to the same unnamed character. Merge these programmatically.
        profiles = self.merge_descriptive_entities(profiles)

        # CRITICAL: Re-verify aliases after merging
        # merge_descriptive_entities() can add new aliases (lines 1192-1194) that bypass
        # the initial verification. Run verify_aliases again to catch any bad aliases
        # added during the merge step (e.g., "the ebony clock" merged as alias).
        profiles = self.verify_aliases(profiles, chapter_summaries)

        # NOTE: Removed non-sentient entity filter - symbolic objects/forces can be valid "characters"
        # Examples: "the monkey's paw", "the eyes of Doctor T. J. Eckleburg"
        # Trust that if something appears frequently and drives plot, it's worth extracting

        # Optional: Additional competitive LLM verification when enabled
        # Uses multiple LLMs to vote on each alias for extra confidence
        if self._use_competitive_consensus():
            profiles = self.competitive_verify_aliases(profiles, chapter_summaries)

        logger.info(f"Extracted {len(profiles)} main cast characters from summaries")
        return profiles

    def _extract_single_pass(self, summaries_text: str, plot_section: str, pattern_hints: Optional[dict] = None) -> list[MainCastProfile]:
        """Original single-pass extraction method."""
        # Build the prompt with pattern hints if available
        pattern_section = ""
        if pattern_hints and pattern_hints.get("pattern_guidance"):
            pattern_section = "\n\n**PRE-EXTRACTION PATTERN ANALYSIS:**\n"
            pattern_section += "\n".join(pattern_hints["pattern_guidance"])
            pattern_section += "\n\nUse these patterns to ensure you don't miss any aliases or merge different characters incorrectly.\n"

        prompt = MAIN_CAST_PROMPT.format(
            summaries=summaries_text,
            plot_summary_section=plot_section,
        )

        # Insert pattern hints after the rules but before the summaries
        if pattern_section:
            prompt = prompt.replace("CHAPTER SUMMARIES:", pattern_section + "\nCHAPTER SUMMARIES:")

        # Query LLM
        result, response = self.llm.query_json(prompt)

        # Check if primary model failed JSON and we have a fallback
        if (not response.success or result is None) and self.json_llm is not None:
            logger.warning(
                f"Primary model '{self.llm.config.model}' failed JSON extraction, "
                f"retrying with JSON-capable model '{self.json_llm.config.model}'"
            )
            result, response = self.json_llm.query_json(prompt)

        if not response.success:
            logger.error(f"LLM query failed: {response.error}")
            return []

        if result is None:
            logger.error("Failed to parse JSON from LLM response")
            return []

        # Parse the result into profiles
        return self._parse_profiles(result)

    def _extract_two_pass(self, summaries_text: str, plot_section: str, pattern_hints: Optional[dict] = None) -> list[MainCastProfile]:
        """Two-pass extraction: first identify characters, then resolve aliases."""
        logger.info("Using two-pass character extraction approach")

        # Add pattern hints if available
        pattern_section = ""
        if pattern_hints and pattern_hints.get("pattern_guidance"):
            pattern_section = "\n\n**PRE-EXTRACTION PATTERN ANALYSIS:**\n"
            pattern_section += "\n".join(pattern_hints["pattern_guidance"])
            pattern_section += "\n\nUse these patterns to ensure you identify all character types correctly.\n"

        # Pass 1: Character Identification
        pass1_prompt = CHARACTER_IDENTIFICATION_PROMPT.format(
            summaries=summaries_text,
            plot_summary_section=plot_section,
        )

        # Insert pattern hints after the rules but before the summaries
        if pattern_section:
            pass1_prompt = pass1_prompt.replace("CHAPTER SUMMARIES:", pattern_section + "\nCHAPTER SUMMARIES:")

        # Use strict system prompt to enforce JSON format
        system_prompt = (
            "You are a JSON-only assistant. "
            "You MUST respond with ONLY valid JSON. "
            "Do NOT wrap your response in any explanatory text, markdown code blocks, or additional commentary. "
            "Do NOT use fields like 'error' or 'message' - return the requested data structure directly."
        )

        result, response = self.llm.query_json(pass1_prompt, system=system_prompt)

        # DIAGNOSTIC: Log raw response if extraction fails
        if not response.success or result is None:
            logger.error(
                f"Pass 1 LLM extraction failed. Model: {self.llm.config.model}, "
                f"Success: {response.success}, Result type: {type(result)}, "
                f"Raw response content (first 500 chars): {response.content[:500] if hasattr(response, 'content') else 'N/A'}"
            )

        # Check if primary model failed JSON and we have a fallback
        primary_failed = (
            not response.success
            or result is None
            or (isinstance(result, dict) and ("error" in result or "message" in result))
        )

        if primary_failed and self.json_llm is not None:
            logger.warning(
                f"Primary model '{self.llm.config.model}' failed JSON extraction, "
                f"retrying with JSON-capable model '{self.json_llm.config.model}'"
            )
            result, response = self.json_llm.query_json(pass1_prompt, system=system_prompt)

            # DIAGNOSTIC: Log fallback result
            if not response.success or result is None:
                logger.error(
                    f"Pass 1 JSON fallback also failed. Model: {self.json_llm.config.model}, "
                    f"Success: {response.success}, Result type: {type(result)}, "
                    f"Raw response content (first 500 chars): {response.content[:500] if hasattr(response, 'content') else 'N/A'}"
                )

        if not response.success:
            logger.error(f"Pass 1 LLM query failed: {response.error}")
            return []

        if result is None:
            logger.error("Failed to parse JSON from Pass 1 LLM response")
            return []

        # Parse Pass 1 results
        initial_characters = self._parse_pass1_results(result)

        # If model returned error/message instead of character array, log clearly and fail
        # This indicates the model doesn't support structured JSON output properly
        if not initial_characters and isinstance(result, dict) and ("error" in result or "message" in result):
            logger.error(
                f"Model '{self.llm.config.model}' returned error instead of character array: {result}. "
                f"This model may not support json_mode properly. Consider using --json-model "
                f"to specify a JSON-capable fallback model (e.g., qwen2.5:32b, llama3.2)."
            )
            return []

        logger.info(f"Pass 1 identified {len(initial_characters)} main characters")

        # Pass 2: Consolidated alias resolution with full context
        # This gives the LLM visibility into ALL characters to prevent conflicts
        logger.info("Pass 2: Consolidated alias resolution for all characters")

        # Build character list for the prompt
        character_list = "\n".join(
            f"- {c.canonical_name} (role: {c.role}, description: {c.description})"
            for c in initial_characters
        )

        pass2_prompt = CONSOLIDATED_ALIAS_PROMPT.format(
            character_list=character_list,
            summaries=summaries_text,
        )

        alias_result, alias_response = self.llm.query_json(pass2_prompt, system=system_prompt)

        # Retry with JSON-capable model if primary failed
        if (not alias_response.success or alias_result is None) and self.json_llm is not None:
            logger.debug("Pass 2 retry with JSON-capable model")
            alias_result, alias_response = self.json_llm.query_json(pass2_prompt, system=system_prompt)

        if not alias_response.success or alias_result is None:
            logger.warning("Consolidated Pass 2 failed, falling back to per-character resolution")
            return self._extract_two_pass_per_character(initial_characters, summaries_text)

        # Process consolidated results
        profiles = self._process_consolidated_pass2(initial_characters, alias_result)
        logger.info(f"Pass 2 complete: {len(profiles)} characters after merge resolution")

        return profiles

    def _extract_two_pass_per_character(
        self,
        initial_characters: list[MainCastProfile],
        summaries_text: str,
    ) -> list[MainCastProfile]:
        """
        Fallback per-character alias resolution (original Pass 2 approach).

        Used when consolidated Pass 2 fails.
        """
        profiles = []
        for char in initial_characters:
            logger.info(f"Pass 2 (fallback): Resolving aliases for {char.canonical_name}")

            # Build context about other characters to prevent false grouping
            other_chars = [c.canonical_name for c in initial_characters if c.canonical_name != char.canonical_name]
            if other_chars:
                other_chars_text = "OTHER CHARACTERS IN THIS NOVEL:\n" + "\n".join(f"- {name}" for name in other_chars)
                other_chars_text += "\n\nDo NOT include any of these other characters as aliases unless they are clearly the same person."
            else:
                other_chars_text = ""

            pass2_prompt = ALIAS_RESOLUTION_PROMPT.format(
                character_name=char.canonical_name,
                role=char.role,
                description=char.description,
                other_characters_context=other_chars_text,
                summaries=summaries_text,
            )

            alias_result, alias_response = self.llm.query_json(pass2_prompt)

            # Retry with JSON-capable model if primary failed
            if (not alias_response.success or alias_result is None) and self.json_llm is not None:
                logger.debug(
                    f"Pass 2 retry with JSON-capable model for {char.canonical_name}"
                )
                alias_result, alias_response = self.json_llm.query_json(pass2_prompt)

            if alias_response.success and alias_result:
                # Merge aliases into the character profile
                aliases = alias_result.get("aliases", [])
                char.aliases = [self._strip_possessive(a.strip()) for a in aliases if a.strip()]

                # Optional: keep uncertain aliases separate for later validation
                uncertain = alias_result.get("uncertain_aliases", []) or []
                if isinstance(uncertain, list):
                    char.uncertain_aliases = [
                        self._strip_possessive(a.strip()) for a in uncertain if isinstance(a, str) and a.strip()
                    ]

                # Remove canonical name from aliases
                char.aliases = [a for a in char.aliases if a.lower() != char.canonical_name.lower()]

                logger.info(f"Found {len(char.aliases)} aliases for {char.canonical_name}")
            else:
                logger.warning(f"Pass 2 failed for {char.canonical_name}, keeping without aliases")

            profiles.append(char)

        return profiles

    def _process_consolidated_pass2(
        self,
        initial_characters: list[MainCastProfile],
        alias_result: dict,
    ) -> list[MainCastProfile]:
        """
        Process consolidated Pass 2 results, applying aliases and merges.

        Args:
            initial_characters: Characters from Pass 1
            alias_result: LLM response with aliases and merge_into directives

        Returns:
            Merged list of MainCastProfile with aliases applied
        """
        # Build lookup by canonical name
        char_by_name = {c.canonical_name.lower(): c for c in initial_characters}

        # Track merge relationships
        merge_map: dict[str, str] = {}  # source_name -> target_name

        # Process LLM response
        characters_data = alias_result.get("characters", [])
        if not isinstance(characters_data, list):
            logger.warning("Consolidated Pass 2 returned invalid format, skipping")
            return initial_characters

        for char_data in characters_data:
            if not isinstance(char_data, dict):
                continue

            canonical_name = self._clean_canonical_name(char_data.get("canonical_name", "").strip())
            if not canonical_name:
                continue

            canonical_lower = canonical_name.lower()

            # Find the matching character from Pass 1
            char = char_by_name.get(canonical_lower)
            if not char:
                # This might be a character the LLM added that wasn't in Pass 1
                logger.debug(f"Character '{canonical_name}' not found in Pass 1 results, skipping")
                continue

            # Apply aliases
            aliases = char_data.get("aliases", [])
            if isinstance(aliases, list):
                char.aliases = [self._strip_possessive(a.strip()) for a in aliases if isinstance(a, str) and a.strip()]
                # Remove canonical name from aliases
                char.aliases = [a for a in char.aliases if a.lower() != canonical_lower]

            # Apply uncertain aliases
            uncertain = char_data.get("uncertain_aliases", []) or []
            if isinstance(uncertain, list):
                char.uncertain_aliases = [
                    self._strip_possessive(a.strip()) for a in uncertain if isinstance(a, str) and a.strip()
                ]

            # Track merge directive
            merge_into = char_data.get("merge_into")
            if merge_into and isinstance(merge_into, str) and merge_into.strip():
                merge_map[canonical_lower] = merge_into.strip().lower()
                logger.info(
                    f"Consolidated Pass 2: '{canonical_name}' should merge into '{merge_into}'"
                )

        # Apply merges with semantic validation
        chars_to_remove = set()
        for source_name, target_name in merge_map.items():
            source = char_by_name.get(source_name)
            target = char_by_name.get(target_name)

            if not source or not target:
                logger.warning(
                    f"Cannot apply merge: '{source_name}' -> '{target_name}' "
                    f"(source found: {source is not None}, target found: {target is not None})"
                )
                continue

            # SEMANTIC VALIDATION: Check if merge makes sense
            # Block merges that are semantically incompatible (e.g., "the Creature" → "the magistrate")

            # Rule 1: Don't merge protagonist ↔ antagonist (opposite narrative functions)
            if source.role != target.role and source.role in ("protagonist", "antagonist") and target.role in ("protagonist", "antagonist"):
                logger.warning(
                    f"BLOCKED merge '{source.canonical_name}' ({source.role}) → '{target.canonical_name}' ({target.role}): "
                    f"Incompatible roles (protagonist/antagonist cannot merge)"
                )
                continue

            # Rule 2: Check for semantic incompatibility in descriptions
            # BUT: Allow merges if roles are the same (e.g., "the narrator" → "Victor" both protagonist)
            if source.description and target.description and source.role != target.role:
                # Only apply description check if roles differ (stricter validation for cross-role merges)
                source_words = set(source.description.lower().split())
                target_words = set(target.description.lower().split())
                overlap = len(source_words & target_words)
                total_unique = len(source_words | target_words)

                # Descriptive handles (e.g., "the old man") are valid merge sources
                # even with different roles and low description overlap
                source_is_descriptive = self._is_descriptive_handle(source.canonical_name)

                if total_unique > 5 and overlap / total_unique < 0.15 and not source_is_descriptive:
                    # Less than 15% word overlap in descriptions AND different roles - likely different people
                    logger.warning(
                        f"BLOCKED merge '{source.canonical_name}' ({source.role}) → '{target.canonical_name}' ({target.role}): "
                        f"Different roles with no semantic overlap ({overlap}/{total_unique} words)"
                    )
                    continue

            # Add source's canonical name as alias of target
            if source.canonical_name not in target.aliases:
                target.aliases.append(source.canonical_name)
                logger.info(
                    f"Merged '{source.canonical_name}' into '{target.canonical_name}' as alias"
                )

            # Merge source's aliases into target
            for alias in source.aliases:
                if alias not in target.aliases and alias.lower() != target.canonical_name.lower():
                    target.aliases.append(alias)

            # Transfer description if target doesn't have one
            if not target.description and source.description:
                target.description = source.description

            # Mark source for removal
            chars_to_remove.add(source_name)

        # Build final list excluding merged characters
        profiles = [
            c for c in initial_characters
            if c.canonical_name.lower() not in chars_to_remove
        ]

        if chars_to_remove:
            logger.info(
                f"Consolidated Pass 2 merged {len(chars_to_remove)} duplicate entries: "
                f"{list(chars_to_remove)}"
            )

        return profiles

    @staticmethod
    def _clean_canonical_name(name: str) -> str:
        """Strip verbose parenthetical qualifiers from canonical names, but PRESERVE disambiguators.

        PRESERVES relationship/role parentheticals that distinguish same-name characters:
          "John Donaldson (the son)" → "John Donaldson (the son)" ✓ KEPT
          "John Donaldson (father)" → "John Donaldson (father)" ✓ KEPT
          "Colonel Smith (elder)" → "Colonel Smith (elder)" ✓ KEPT
          "Mary (Sr.)" → "Mary (Sr.)" ✓ KEPT

        STRIPS verbose descriptive parentheticals:
          "the Red Death (as a spectral figure)" → "the Red Death" ✓ STRIPPED
          "the creature (eight feet tall)" → "the creature" ✓ STRIPPED

        Why: The summarizer explicitly adds disambiguators like "(the son)" and "(the father)"
        to distinguish same-name family members. Stripping these causes characters to collide
        in the char_by_name dict (line 726) where the last one overwrites the first.
        """
        import re

        # Pattern for disambiguation parentheticals (relationships/roles) - PRESERVE these
        # This includes: father, son, daughter, mother, uncle, nephew, etc.
        # Also generational suffixes: Sr., Jr., elder, younger
        disambiguation_pattern = r'\((the\s+)?(father|son|daughter|mother|parent|child|' \
                               r'uncle|nephew|aunt|niece|brother|sister|cousin|' \
                               r'grandfather|grandmother|grandson|granddaughter|' \
                               r'elder|younger|senior|junior|sr\.?|jr\.?)\)'

        # Check if name has disambiguation parenthetical
        if re.search(disambiguation_pattern, name, re.IGNORECASE):
            # Has relationship/role disambiguator - KEEP IT
            return name.strip()

        # Otherwise strip verbose parentheticals like descriptions
        cleaned = re.sub(r"\s*\(.*?\)\s*", " ", name).strip()
        return cleaned if cleaned else name

    @staticmethod
    def _strip_possessive(alias: str) -> str:
        """Strip possessive markers from aliases.

        Removes trailing "'s" or "'" from names.
        Examples:
          "John Donaldson's" → "John Donaldson"
          "the creature's" → "the creature"
          "Jesus'" → "Jesus"
        """
        alias = alias.strip()
        if alias.endswith("'s"):
            return alias[:-2].strip()
        if alias.endswith("'"):
            return alias[:-1].strip()
        return alias

    def _parse_pass1_results(self, result: list | dict) -> list[MainCastProfile]:
        """Parse Pass 1 character identification results."""
        profiles = []

        # Handle both list and dict formats
        if isinstance(result, dict):
            # Some models return reasoning in "error"/"message" field instead of array
            if "error" in result or "message" in result:
                reasoning = result.get("error") or result.get("message", "")
                logger.error(
                    f"Pass 1 LLM returned reasoning in 'error'/'message' field instead of array. "
                    f"This model may not be compatible with structured JSON output. "
                    f"Reasoning: {reasoning[:200]}..."
                )
                logger.error(
                    f"RECOMMENDATION: Try a different model for character extraction. "
                    f"Known compatible models: llama3.2, qwen2.5:72b, gpt-4o-mini"
                )
                return []

            result = result.get("characters", result.get("main_cast", []))

        if not isinstance(result, list):
            logger.warning(f"Expected list from Pass 1, got {type(result)}")
            return []

        for item in result:
            if not isinstance(item, dict):
                continue

            canonical = self._clean_canonical_name(item.get("canonical_name", "").strip())
            if not canonical:
                continue

            profile = MainCastProfile(
                canonical_name=canonical,
                aliases=[],  # No aliases in Pass 1
                role=item.get("role", "supporting"),
                description=item.get("description", ""),
                is_unnamed=item.get("is_unnamed", False),
                is_symbolic=item.get("is_symbolic", False),
            )

            profiles.append(profile)

        return profiles

    def _parse_profiles(self, result: list | dict) -> list[MainCastProfile]:
        """Parse LLM result into MainCastProfile objects."""
        profiles = []

        # Handle both list and dict with characters key
        if isinstance(result, dict):
            result = result.get("characters", result.get("main_cast", []))

        if not isinstance(result, list):
            logger.warning(f"Expected list, got {type(result)}")
            return []

        for item in result:
            if not isinstance(item, dict):
                continue

            canonical = self._clean_canonical_name(item.get("canonical_name", "").strip())
            if not canonical:
                continue

            profile = MainCastProfile(
                canonical_name=canonical,
                aliases=[self._strip_possessive(a.strip()) for a in item.get("aliases", []) if a.strip()],
                uncertain_aliases=[
                    self._strip_possessive(a.strip())
                    for a in (item.get("uncertain_aliases", []) or [])
                    if isinstance(a, str) and a.strip()
                ],
                role=item.get("role", "supporting"),
                description=item.get("description", ""),
                is_unnamed=item.get("is_unnamed", False),
                is_symbolic=item.get("is_symbolic", False),
            )

            # Ensure canonical name is not in aliases (avoid duplication)
            profile.aliases = [a for a in profile.aliases if a.lower() != canonical.lower()]

            profiles.append(profile)

        return profiles

    def verify_aliases(
        self,
        profiles: list[MainCastProfile],
        chapter_summaries: list[str],
    ) -> list[MainCastProfile]:
        """
        Verify that alleged aliases actually refer to the same character.

        This post-LLM verification step checks if aliases are plausible by:
        1. Blocking obvious false positives (different surnames on titled names)
        2. Checking if the alias and canonical name co-occur in the same summaries

        Args:
            profiles: List of MainCastProfile objects from LLM
            chapter_summaries: The summaries used for extraction

        Returns:
            Updated profiles with invalid aliases removed
        """
        # Combine all summaries into searchable text
        "\n".join(chapter_summaries).lower()

        logger.info(
            f"verify_aliases: Checking {len(profiles)} profiles: "
            f"{[(p.canonical_name, p.aliases) for p in profiles]}"
        )

        verified_profiles = []

        for profile in profiles:
            canonical_lower = profile.canonical_name.lower()
            verified_aliases = []

            for alias in profile.aliases:
                alias_lower = alias.lower()

                # region agent log
                if any(k in canonical_lower for k in ("lacey", "old man")) or any(
                    k in alias_lower
                    for k in ("creature", "monster", "fiend", "daemon", "wretch", "being")
                ):
                    try:
                        append_debug_event(
                            {
                                "sessionId": "debug-session",
                                "runId": "frankenstein-pre",
                                "hypothesisId": "H1",
                                "location": "src/pipeline/character_extraction_v2/main_cast.py:verify_aliases",
                                "message": "Evaluating alias for focused canonical/alias",
                                "data": {"canonical": profile.canonical_name, "alias": alias},
                                "timestamp": int(time.time() * 1000),
                            }
                        )
                    except Exception:
                        pass
                # endregion

                # RULE 0: Block nonsensical aliases (pronouns, common words, setting elements)
                # These are never valid character aliases
                pronouns = {
                    "he",
                    "she",
                    "it",
                    "they",
                    "them",
                    "him",
                    "her",
                    "his",
                    "hers",
                    "theirs",
                    "i",
                    "we",
                    "us",
                }

                nonsensical_patterns = {
                    # Common words that might appear in summaries but aren't character names
                    "the",
                    "a",
                    "an",
                    "and",
                    "or",
                    "but",
                    # Setting/place descriptors (often confused for characters)
                    "the wind",
                    "the ice",
                    "the caverns",
                    "the ice caverns",
                    "the darkness",
                    "the light",
                    "the world",
                    "the room",
                    "the house",
                    "the city",
                    "the town",
                    "the village",
                    # Generic descriptors
                    "the group",
                    "the others",
                    "everyone",
                    "someone",
                }

                # Pronouns are never valid aliases (even for symbolic entities)
                if alias_lower in pronouns:
                    logger.warning(
                        f"BLOCKED alias: '{alias}' is a pronoun, not a valid alias for '{profile.canonical_name}'"
                    )
                    continue

                # Check if alias is entirely nonsensical
                if alias_lower in nonsensical_patterns and not getattr(profile, "is_symbolic", False):
                    logger.warning(
                        f"BLOCKED alias: '{alias}' is a pronoun/common word, "
                        f"not a valid character alias for '{profile.canonical_name}'"
                    )
                    continue

                # Also block single-letter aliases (likely OCR errors or initials without context)
                if len(alias) == 1:
                    logger.warning(
                        f"BLOCKED alias: '{alias}' is a single letter, "
                        f"likely not a valid alias for '{profile.canonical_name}'"
                    )
                    continue

                # RULE 0.4: Block meta-references that are never character aliases
                # "narrator" is a storytelling voice/device, not a character reference
                # "reader" / "audience" are similar meta-references
                meta_references = {"narrator", "the narrator", "reader", "the reader", "audience", "the audience"}
                if alias_lower in meta_references:
                    # Exception: "the narrator" / "narrator" is valid for protagonists
                    # in first-person narratives (e.g., Montresor, Egaeus, Ted)
                    if alias_lower in ("narrator", "the narrator") and profile.role == "protagonist":
                        logger.info(
                            f"ALLOWED alias: '{alias}' for protagonist '{profile.canonical_name}' "
                            f"(narrator is a valid alias for first-person protagonist)"
                        )
                    else:
                        logger.warning(
                            f"BLOCKED alias: '{alias}' is a meta-reference (storytelling device), "
                            f"not a valid character alias for '{profile.canonical_name}'"
                        )
                        continue

                # NOTE: Object keyword blocking for aliases (clock, door, etc.) is handled by
                # CharacterAgent._is_valid_alias() which runs during merge operations.
                # This avoids duplicate filtering and keeps alias validation in one place.

                # RULE 0.5: Semantic coherence check for symbolic entities and personified concepts
                # If the canonical name is a symbolic entity (object/force) OR a personified
                # concept (abstract noun used as character), verify that aliases refer to
                # THE SAME object/concept, not just any co-occurring nouns

                # Detect personified concepts: abstract nouns that function as characters
                # (e.g., "the Red Death", "Death", "Fear", "the Plague")
                def is_personified_concept(name: str) -> bool:
                    """Check if name is likely a personified abstract concept."""
                    name_lower = name.lower().strip()
                    # Remove articles to get core phrase
                    for article in ["the ", "a ", "an "]:
                        if name_lower.startswith(article):
                            name_lower = name_lower[len(article):].strip()
                            break

                    # Abstract concepts commonly personified in literature
                    personified_keywords = {
                        "death", "plague", "disease", "pestilence", "fever",
                        "fear", "terror", "horror", "darkness", "shadow",
                        "fate", "destiny", "doom", "revenge", "madness",
                        "time", "chaos", "decay", "despair", "grief"
                    }

                    # Check if the core name is a personified concept
                    # Allow compound forms like "red death" (splits to ["red", "death"])
                    name_words = set(name_lower.split())
                    return bool(name_words & personified_keywords)

                is_symbolic_or_personified = getattr(profile, "is_symbolic", False) or is_personified_concept(profile.canonical_name)

                if is_symbolic_or_personified:
                    # Extract core nouns from both canonical and alias (strip "the", articles)
                    def extract_core_noun(text: str) -> str:
                        """Extract the main noun from a phrase like 'the Amontillado'."""
                        parts = text.lower().strip().split()
                        # Remove articles and possessives
                        articles = {"the", "a", "an", "this", "that", "these", "those"}
                        core_parts = [p for p in parts if p not in articles]
                        # Return last word as core noun (e.g., "Amontillado" from "the Amontillado")
                        return core_parts[-1] if core_parts else text.lower()

                    canonical_noun = extract_core_noun(profile.canonical_name)
                    alias_noun = extract_core_noun(alias)

                    logger.debug(
                        f"Semantic coherence check: canonical='{profile.canonical_name}' (core: '{canonical_noun}'), "
                        f"alias='{alias}' (core: '{alias_noun}')"
                    )

                    # Check if the nouns are related (substring match, plural/singular variants)
                    # "Amontillado" should match "amontillado" but NOT "catacombs" or "trowel"
                    are_related = (
                        canonical_noun in alias_noun or
                        alias_noun in canonical_noun or
                        canonical_noun[:-1] == alias_noun or  # plural check: "wines" vs "wine"
                        alias_noun[:-1] == canonical_noun or
                        canonical_noun[:-2] == alias_noun or  # "es" plural: "boxes" vs "box"
                        alias_noun[:-2] == canonical_noun
                    )

                    if not are_related:
                        entity_type = "symbolic entity" if getattr(profile, "is_symbolic", False) else "personified concept"
                        logger.warning(
                            f"BLOCKED alias: '{alias}' (core noun: '{alias_noun}') is semantically "
                            f"unrelated to '{profile.canonical_name}' (core noun: '{canonical_noun}'). "
                            f"This {entity_type} must have aliases referring to the SAME object/concept."
                        )
                        continue
                    else:
                        logger.debug(
                            f"ALLOWED alias: '{alias}' is semantically related to '{profile.canonical_name}' "
                            f"(core nouns: '{alias_noun}' ~ '{canonical_noun}')"
                        )

                # RULE 1: Hard block - different titled names (Mr. X vs Mr. Y)
                # If both canonical and alias start with a title (Mr./Mrs./Miss/Ms./Dr.)
                # AND the surnames are different, they CANNOT be the same person
                are_different = self._are_different_titled_people(profile.canonical_name, alias)
                if are_different:
                    logger.warning(
                        f"BLOCKED alias: '{alias}' cannot be alias of '{profile.canonical_name}' "
                        f"(different titled people)"
                    )
                    continue
                else:
                    # Debug: Log when we DON'T block
                    if "krempe" in alias.lower() or "waldman" in alias.lower():
                        logger.info(
                            f"NOT blocked: '{alias}' allowed as alias of '{profile.canonical_name}' "
                            f"(_are_different_titled_people returned False)"
                        )

                # RULE 2: Co-occurrence check
                # The alias should appear in summaries that also mention the canonical name
                # Exception: If alias is a substring of canonical (e.g., "Gatsby" in "Jay Gatsby"),
                # skip co-occurrence check as it's inherently valid
                if alias_lower in canonical_lower or canonical_lower in alias_lower:
                    # Substring relationship - inherently valid
                    verified_aliases.append(alias)
                    continue

                # Check if both appear in the same summaries
                # Split summaries and check chapter-by-chapter
                canonical_found = False
                alias_found = False

                for summary in chapter_summaries:
                    summary_lower = summary.lower()
                    if canonical_lower in summary_lower:
                        canonical_found = True
                    if alias_lower in summary_lower:
                        alias_found = True

                # If alias appears but canonical doesn't, they might not be the same person
                # However, this is a weak signal (summaries might use one name more than the other)
                # So we only block if BOTH appear but NEVER in the same summary
                # AND they have completely different surnames (suggesting different people)
                if canonical_found and alias_found:
                    # Check if they ever co-occur in the same summary
                    cooccur = False
                    for summary in chapter_summaries:
                        summary_lower = summary.lower()
                        if canonical_lower in summary_lower and alias_lower in summary_lower:
                            cooccur = True
                            break

                    # region agent log
                    if any(k in canonical_lower for k in ("lacey", "old man")) and any(
                        k in alias_lower
                        for k in ("creature", "monster", "fiend", "daemon", "wretch", "being")
                    ):
                        try:
                            append_debug_event(
                                {
                                    "sessionId": "debug-session",
                                    "runId": "frankenstein-pre",
                                    "hypothesisId": "H1",
                                    "location": "src/pipeline/character_extraction_v2/main_cast.py:verify_aliases",
                                    "message": "Co-occurrence check for old man/De Lacey vs creature-term alias",
                                    "data": {
                                        "canonical": profile.canonical_name,
                                        "alias": alias,
                                        "canonical_found": canonical_found,
                                        "alias_found": alias_found,
                                        "cooccur": cooccur,
                                    },
                                    "timestamp": int(time.time() * 1000),
                                }
                            )
                        except Exception:
                            pass
                    # endregion

                    if not cooccur:
                        # Before blocking, check if they share a surname
                        # Birth names / former identities often don't co-occur (flashback vs present)
                        # but should still be merged if they share part of the name
                        canonical_parts = profile.canonical_name.lower().split()
                        alias_parts = alias.lower().split()

                        # If they share ANY name part (e.g., "Gatsby"), allow the merge
                        # This handles birth names like "James Gatz" → "Jay Gatsby" (both have "Gat*")
                        shared_parts = set(canonical_parts) & set(alias_parts)

                        # Also check for partial matches (e.g., "Gatz" vs "Gatsby")
                        has_similar_part = False
                        for cpart in canonical_parts:
                            for apart in alias_parts:
                                # Check if one is a substring of the other (min length 4 to avoid false positives)
                                if len(cpart) >= 4 and len(apart) >= 4:
                                    if cpart[:4] == apart[:4]:  # Same first 4 chars
                                        has_similar_part = True
                                        break

                        # Descriptive handles (e.g., "the old man", "father") are valid
                        # aliases even without co-occurrence or name overlap
                        is_descriptive = self._is_descriptive_handle(alias)

                        if not shared_parts and not has_similar_part and not is_descriptive:
                            logger.warning(
                                f"BLOCKED alias: '{alias}' and '{profile.canonical_name}' appear in summaries "
                                f"but NEVER co-occur in the same chapter and have no name overlap"
                            )
                            continue
                        else:
                            reason = "descriptive handle" if is_descriptive else "share name parts or have similar surname"
                            logger.info(
                                f"ALLOWED alias despite no co-occurrence: '{alias}' → '{profile.canonical_name}' "
                                f"({reason})"
                            )

                # Passed verification
                verified_aliases.append(alias)

            # Update profile with verified aliases only
            if len(verified_aliases) < len(profile.aliases):
                removed = set(profile.aliases) - set(verified_aliases)
                logger.info(
                    f"Alias verification for '{profile.canonical_name}': "
                    f"kept {len(verified_aliases)}/{len(profile.aliases)} aliases "
                    f"(removed: {removed})"
                )

            profile.aliases = verified_aliases
            verified_profiles.append(profile)

        # RULE 3: Remove ambiguous bare surnames when multiple characters share the surname
        # If "Jennings" is an alias for "Milton Jennings" but "Mr. Jennings" also exists,
        # remove "Jennings" as it's ambiguous (prevents cross-talk during narration)
        logger.info("Checking for ambiguous bare surname aliases...")

        # Build a set of all surnames present in character canonical names
        surname_to_characters = {}
        for profile in verified_profiles:
            # Extract last word from multi-word names as potential surname
            name_parts = profile.canonical_name.split()
            if len(name_parts) >= 2:
                # Last part is likely surname (handles "Milton Jennings", "Mr. Jennings", etc.)
                surname = name_parts[-1].strip(".,;:")
                if surname:
                    surname_lower = surname.lower()
                    if surname_lower not in surname_to_characters:
                        surname_to_characters[surname_lower] = []
                    surname_to_characters[surname_lower].append(profile.canonical_name)

        # Filter out ambiguous bare surnames from aliases
        for profile in verified_profiles:
            filtered_aliases = []
            for alias in profile.aliases:
                alias_lower = alias.lower()
                # Check if this alias is a bare surname shared by multiple characters
                if alias_lower in surname_to_characters and len(surname_to_characters[alias_lower]) > 1:
                    logger.warning(
                        f"REMOVED ambiguous bare surname alias: '{alias}' for '{profile.canonical_name}' "
                        f"(shared by: {surname_to_characters[alias_lower]})"
                    )
                    continue
                filtered_aliases.append(alias)
            
            if len(filtered_aliases) < len(profile.aliases):
                logger.info(
                    f"Filtered ambiguous surnames for '{profile.canonical_name}': "
                    f"{len(profile.aliases)} -> {len(filtered_aliases)} aliases"
                )
            profile.aliases = filtered_aliases

        return verified_profiles

    def _detect_patterns(self, summaries_text: str, plot_summary: Optional[str] = None) -> dict[str, list[str]]:
        """
        Detect common character patterns in summaries to guide LLM extraction.

        This pre-extraction step helps the LLM by identifying patterns that often
        cause confusion or missed aliases, particularly:
        - "the [descriptor]" patterns for unnamed characters
        - Family relationship terms that may refer to named characters
        - Title patterns (Mr./Mrs./Dr. etc.)

        Returns:
            Dictionary of pattern hints to guide extraction
        """
        import re

        hints = {
            "descriptive_patterns": [],
            "family_terms": [],
            "title_patterns": [],
            "pattern_guidance": []
        }

        # Combine all text for analysis
        full_text = summaries_text
        if plot_summary:
            full_text = f"{summaries_text}\n{plot_summary}"

        # Pattern 1: Detect "the [descriptor]" patterns
        # These often indicate unnamed characters with multiple descriptive references
        the_pattern = r'\bthe\s+([a-z]+(?:\s+[a-z]+)?)\b'
        the_matches = re.findall(the_pattern, full_text.lower())

        # Filter for likely character descriptors (not common articles)
        descriptor_keywords = {
            'creature', 'monster', 'fiend', 'daemon', 'wretch', 'being',
            'stranger', 'visitor', 'traveler', 'guest',
            'old man', 'elder', 'old one', 'old woman',
            'narrator', 'speaker', 'storyteller',
            'captain', 'doctor', 'professor', 'judge'
        }

        found_descriptors = set()
        for match in the_matches:
            if match in descriptor_keywords or any(word in match for word in ['man', 'woman', 'one']):
                found_descriptors.add(f"the {match}")

        if found_descriptors:
            hints["descriptive_patterns"] = sorted(list(found_descriptors))
            hints["pattern_guidance"].append(
                "DETECTED PATTERN: Unnamed characters with descriptive handles. "
                "These terms likely refer to the same characters across chapters: " +
                ", ".join(hints["descriptive_patterns"])
            )

        # Pattern 2: Detect family relationship terms
        family_pattern = r'\b(father|mother|son|daughter|brother|sister|uncle|aunt|grandfather|grandmother)\b'
        family_matches = re.findall(family_pattern, full_text.lower())

        if family_matches:
            unique_family_terms = sorted(list(set(family_matches)))
            hints["family_terms"] = unique_family_terms
            hints["pattern_guidance"].append(
                "DETECTED PATTERN: Family relationship terms. "
                "Check if these refer to named characters (e.g., 'father' might be an alias for a named parent)."
            )

        # Pattern 3: Detect title patterns (Mr./Mrs./Miss/Dr./M.)
        title_pattern = r'\b(Mr\.|Mrs\.|Miss|Ms\.|Dr\.|M\.)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b'
        title_matches = re.findall(title_pattern, full_text)

        if title_matches:
            unique_titles = []
            seen = set()
            for title, name in title_matches:
                full_title = f"{title} {name}"
                if full_title not in seen:
                    seen.add(full_title)
                    unique_titles.append(full_title)

            if unique_titles:
                hints["title_patterns"] = sorted(unique_titles)
                hints["pattern_guidance"].append(
                    "DETECTED PATTERN: Characters with titles. "
                    "Remember: Different titles with the same surname (e.g., Mr. Smith vs Mrs. Smith) "
                    "are DIFFERENT characters. Same person with/without title are aliases."
                )

        # Clean up empty entries
        hints = {k: v for k, v in hints.items() if v}

        return hints if hints.get("pattern_guidance") else {}

    def merge_descriptive_entities(
        self,
        profiles: list[MainCastProfile],
    ) -> list[MainCastProfile]:
        """
        Merge profiles that are descriptive references to the same unnamed entity.

        Common pattern in literature: unnamed characters referred to by multiple
        descriptive terms (e.g., "the creature", "the monster", "the fiend" all
        referring to Frankenstein's creation).

        Strategy:
        1. Identify profiles starting with "the " that are marked as unnamed
        2. Group them by semantic similarity (creature/monster/fiend/daemon/being/wretch)
        3. Merge groups into single profiles with aliases

        Args:
            profiles: List of MainCastProfile objects

        Returns:
            Updated profiles with descriptive entities merged
        """
        # Define semantic clusters for common unnamed entity patterns
        # Each cluster represents terms that often refer to the same unnamed character
        semantic_clusters = [
            # Frankenstein's creation
            {"the creature", "the monster", "the fiend", "the daemon", "the being", "the wretch"},
            # Generic patterns (expand as needed)
            {"the stranger", "the visitor", "the traveler"},
            {"the old man", "the elder", "the old one"},
        ]

        # Find unnamed "the X" profiles
        # Match on pattern (starts with "the ") regardless of is_unnamed flag
        # LLM sometimes forgets to set is_unnamed=true, so we match on pattern as backup
        the_profiles = [p for p in profiles if p.canonical_name.lower().startswith("the ")]

        logger.debug(
            f"merge_descriptive_entities: Found {len(the_profiles)} 'the X' profiles: "
            f"{[p.canonical_name for p in the_profiles]}"
        )

        if len(the_profiles) < 2:
            # No merging needed
            logger.debug(
                "merge_descriptive_entities: Less than 2 'the X' profiles, no merging needed"
            )
            return profiles

        # Track which profiles to merge
        merge_groups: list[list[MainCastProfile]] = []
        processed = set()

        # FIRST: Alias-based merging
        # If Profile A has alias "X" and Profile B has canonical "X" or "the X", merge them
        # This handles identity reveals like "masked figure" (alias: "Red Death") + "the Red Death"
        def normalize_for_alias_match(name: str) -> str:
            """Strip articles for alias matching."""
            normalized = name.lower().strip()
            for article in ["the ", "a ", "an "]:
                if normalized.startswith(article):
                    return normalized[len(article):].strip()
            return normalized

        alias_merge_pairs: list[tuple[MainCastProfile, MainCastProfile]] = []
        for i, profile_a in enumerate(profiles):
            for profile_b in profiles[i + 1:]:
                # Normalize names for comparison
                canonical_a_norm = normalize_for_alias_match(profile_a.canonical_name)
                canonical_b_norm = normalize_for_alias_match(profile_b.canonical_name)

                # Check if A's canonical matches any of B's aliases (or vice versa)
                aliases_b_norm = [normalize_for_alias_match(a) for a in profile_b.aliases]
                aliases_a_norm = [normalize_for_alias_match(a) for a in profile_a.aliases]

                should_merge = False
                if canonical_a_norm in aliases_b_norm:
                    # A's canonical name appears in B's aliases
                    should_merge = True
                    logger.info(
                        f"ALIAS MERGE: '{profile_a.canonical_name}' matches alias in '{profile_b.canonical_name}' "
                        f"(aliases: {profile_b.aliases})"
                    )
                elif canonical_b_norm in aliases_a_norm:
                    # B's canonical name appears in A's aliases
                    should_merge = True
                    logger.info(
                        f"ALIAS MERGE: '{profile_b.canonical_name}' matches alias in '{profile_a.canonical_name}' "
                        f"(aliases: {profile_a.aliases})"
                    )

                if should_merge:
                    alias_merge_pairs.append((profile_a, profile_b))
                    processed.add(profile_a.canonical_name)
                    processed.add(profile_b.canonical_name)

        # Group alias merge pairs into merge groups
        if alias_merge_pairs:
            # Build groups from pairs (handle transitive merges)
            alias_groups: list[set[str]] = []
            for profile_a, profile_b in alias_merge_pairs:
                # Find existing group containing either profile
                found_group = None
                for group in alias_groups:
                    if profile_a.canonical_name in group or profile_b.canonical_name in group:
                        found_group = group
                        break

                if found_group:
                    found_group.add(profile_a.canonical_name)
                    found_group.add(profile_b.canonical_name)
                else:
                    alias_groups.append({profile_a.canonical_name, profile_b.canonical_name})

            # Convert name sets to profile lists
            profile_by_name = {p.canonical_name: p for p in profiles}
            for name_group in alias_groups:
                profile_group = [profile_by_name[name] for name in name_group if name in profile_by_name]
                if len(profile_group) >= 2:
                    merge_groups.append(profile_group)

        # SECOND: Semantic cluster merging (original logic)
        for cluster in semantic_clusters:
            group = []
            for profile in the_profiles:
                # Use startswith to handle variations like "the creature (implied presence)"
                # Normalize both sides to ensure case-insensitive matching
                profile_name_lower = profile.canonical_name.lower().strip()
                if any(profile_name_lower.startswith(term.lower().strip()) for term in cluster):
                    group.append(profile)
                    processed.add(profile.canonical_name)

            if len(group) >= 2:
                # Found a cluster with multiple profiles to merge
                merge_groups.append(group)

        if not merge_groups:
            logger.info("No descriptive entity merges needed")
            return profiles

        # Perform merges
        merged_profiles = []
        profiles_to_remove = set()

        for group in merge_groups:
            # Choose the canonical profile (prefer "creature" over "monster" for consistency)
            # Sort by: 1) prefer "creature" 2) alphabetically
            sorted_group = sorted(
                group,
                key=lambda p: (
                    p.canonical_name.lower() != "the creature",
                    p.canonical_name.lower(),
                ),
            )
            canonical_profile = sorted_group[0]

            # Merge all others into the canonical
            for other in sorted_group[1:]:
                # Add other's canonical name as an alias
                canonical_profile.aliases.append(other.canonical_name)
                # Add other's aliases
                canonical_profile.aliases.extend(other.aliases)
                # Mark for removal
                profiles_to_remove.add(other.canonical_name)

            # Deduplicate aliases
            canonical_profile.aliases = list(dict.fromkeys(canonical_profile.aliases))

            logger.info(
                f"MERGED descriptive entities: {[p.canonical_name for p in group]} "
                f"→ '{canonical_profile.canonical_name}' with aliases {canonical_profile.aliases}"
            )

            merged_profiles.append(canonical_profile)

        # Build final profile list
        final_profiles = []
        for profile in profiles:
            if profile.canonical_name in profiles_to_remove:
                continue  # Skip merged profiles
            elif any(profile.canonical_name == mp.canonical_name for mp in merged_profiles):
                # Use the merged version
                merged_version = next(
                    mp for mp in merged_profiles if mp.canonical_name == profile.canonical_name
                )
                final_profiles.append(merged_version)
            else:
                # Keep unchanged
                final_profiles.append(profile)

        return final_profiles

    def _filter_non_sentient_entities(
        self,
        profiles: list[MainCastProfile],
    ) -> list[MainCastProfile]:
        """
        Filter out non-sentient entities (inanimate objects) from character profiles.

        Even with explicit prompt instructions, LLMs sometimes classify objects as characters.
        This post-processing filter uses pattern matching to catch common cases:
        - Objects with specific keywords (paw, ring, sword, talisman, etc.)
        - Descriptions indicating object-like properties
        - Lack of sentient being indicators

        Args:
            profiles: List of MainCastProfile objects

        Returns:
            Filtered profiles with non-sentient entities removed
        """
        # Keywords that indicate an inanimate object rather than a character
        # These are typically suffixes or key terms in object names
        object_keywords = {
            "paw", "ring", "sword", "knife", "dagger", "blade",
            "talisman", "amulet", "artifact", "relic", "charm",
            "book", "tome", "manuscript", "journal", "diary",
            "crown", "throne", "scepter", "orb",
            "stone", "gem", "jewel", "crystal",
            "key", "lock", "door", "gate",
            "vessel", "cup", "chalice", "grail",
            "mirror", "portrait", "painting",
            "house", "mansion", "castle", "tower", "building",
            "ship", "boat", "vehicle",
            "weapon", "tool", "device", "machine",
        }

        filtered_profiles = []
        for profile in profiles:
            # Check canonical name and aliases for object keywords
            all_names = [profile.canonical_name] + profile.aliases
            all_names_lower = [name.lower() for name in all_names]

            # Check if any name contains object keywords
            is_likely_object = False
            for name in all_names_lower:
                # Split name into words and check for object keywords
                words = name.replace("'", " ").split()
                for word in words:
                    # Check if word ends with an object keyword (handles possessives)
                    if any(word.endswith(keyword) for keyword in object_keywords):
                        is_likely_object = True
                        logger.info(
                            f"Filtering non-sentient entity: '{profile.canonical_name}' "
                            f"(contains object keyword in '{name}')"
                        )
                        break
                if is_likely_object:
                    break

            if not is_likely_object:
                filtered_profiles.append(profile)

        return filtered_profiles

    def competitive_verify_aliases(
        self,
        profiles: list[MainCastProfile],
        chapter_summaries: list[str],
    ) -> list[MainCastProfile]:
        """
        Additional competitive LLM verification of aliases.

        Uses multiple LLMs with different temperatures/prompts to vote on whether
        each alias is valid. Aliases that don't get supermajority (2/3) approval
        are removed.

        This is an additional layer on top of the programmatic verification.

        Args:
            profiles: Profiles that have already passed programmatic verification
            chapter_summaries: The summaries for context

        Returns:
            Profiles with competitively verified aliases only
        """
        if not self._use_competitive_consensus():
            return profiles

        logger.info("Running competitive alias verification")

        # Create a summary context for the LLM
        all_summaries = "\n".join(chapter_summaries[:5])  # First 5 chapters for context
        if len(all_summaries) > 3000:
            all_summaries = all_summaries[:3000] + "..."

        verified_profiles = []

        for profile in profiles:
            if not profile.aliases:
                verified_profiles.append(profile)
                continue

            verified_aliases = []

            for alias in profile.aliases:
                # Skip aliases that are substrings (inherently valid)
                if (
                    alias.lower() in profile.canonical_name.lower()
                    or profile.canonical_name.lower() in alias.lower()
                ):
                    verified_aliases.append(alias)
                    continue

                # Run competitive verification
                votes = self._competitive_alias_vote(
                    profile.canonical_name,
                    alias,
                    all_summaries,
                    is_symbolic=bool(getattr(profile, "is_symbolic", False)),
                )

                # Require supermajority to keep the alias
                threshold = (
                    self.competitive_config.consensus_merge_threshold
                    if self.competitive_config
                    else 0.67
                )
                vote_ratio = sum(votes) / len(votes) if votes else 0
                outcome = "accepted" if vote_ratio >= threshold else "rejected"

                # Record vote for consensus log
                from ..consensus_collector import consensus_collector
                consensus_collector.record_vote(
                    vote_type="alias",
                    subject=alias,
                    context=profile.canonical_name,
                    votes=votes,
                    threshold=threshold,
                    outcome=outcome,
                )

                if vote_ratio >= threshold:
                    verified_aliases.append(alias)
                    logger.debug(
                        f"Competitive alias verified: '{alias}' as alias of '{profile.canonical_name}' "
                        f"({sum(votes)}/{len(votes)} votes)"
                    )
                else:
                    logger.info(
                        f"Competitive alias REJECTED: '{alias}' as alias of '{profile.canonical_name}' "
                        f"({sum(votes)}/{len(votes)} votes, threshold={threshold:.0%})"
                    )

            profile.aliases = verified_aliases
            verified_profiles.append(profile)

        # RULE 3: Remove ambiguous bare surnames when multiple characters share the surname
        # If "Jennings" is an alias for "Milton Jennings" but "Mr. Jennings" also exists,
        # remove "Jennings" as it's ambiguous (prevents cross-talk during narration)
        logger.info("Checking for ambiguous bare surname aliases...")

        # Build a set of all surnames present in character canonical names
        surname_to_characters = {}
        for profile in verified_profiles:
            # Extract last word from multi-word names as potential surname
            name_parts = profile.canonical_name.split()
            if len(name_parts) >= 2:
                # Last part is likely surname (handles "Milton Jennings", "Mr. Jennings", etc.)
                surname = name_parts[-1].strip(".,;:")
                if surname:
                    surname_lower = surname.lower()
                    if surname_lower not in surname_to_characters:
                        surname_to_characters[surname_lower] = []
                    surname_to_characters[surname_lower].append(profile.canonical_name)

        # Filter out ambiguous bare surnames from aliases
        for profile in verified_profiles:
            filtered_aliases = []
            for alias in profile.aliases:
                alias_lower = alias.lower()
                # Check if this alias is a bare surname shared by multiple characters
                if alias_lower in surname_to_characters and len(surname_to_characters[alias_lower]) > 1:
                    logger.warning(
                        f"REMOVED ambiguous bare surname alias: '{alias}' for '{profile.canonical_name}' "
                        f"(shared by: {surname_to_characters[alias_lower]})"
                    )
                    continue
                filtered_aliases.append(alias)
            
            if len(filtered_aliases) < len(profile.aliases):
                logger.info(
                    f"Filtered ambiguous surnames for '{profile.canonical_name}': "
                    f"{len(profile.aliases)} -> {len(filtered_aliases)} aliases"
                )
            profile.aliases = filtered_aliases

        return verified_profiles

    def _competitive_alias_vote(
        self,
        canonical_name: str,
        alias: str,
        context: str,
        is_symbolic: bool = False,
    ) -> list[bool]:
        """
        Have multiple LLMs vote on whether an alias is valid.

        Returns:
            List of boolean votes (True = valid alias, False = invalid)
        """
        from ..character_extraction.prompts import get_merge_prompts

        prompt_template = """Determine if "{alias}" is a valid alias for "{canonical_name}".

ENTITY_TYPE: {entity_type}

CONTEXT FROM THE STORY:
{context}

RULES:
- A valid alias refers to the SAME entity (person/creature OR symbolic object/force) as the canonical name.
- If ENTITY_TYPE is symbolic: focus on whether the names refer to the same object/force; ignore surname/title rules.
- If ENTITY_TYPE is character: different titles with the same surname are DIFFERENT people (e.g., Mr. Smith vs Mrs. Smith).
- Different surnames usually indicate different people; EXCEPTION when context indicates a name change/variant
  (maiden vs married, revealed former identity, explicitly stated alias).
- Prefer NO when uncertain.

Return JSON:
{{
  "is_valid_alias": true/false,
  "confidence": 0.0-1.0,
  "reason": "brief explanation"
}}"""

        def query_competitor(client_style: tuple[LLMClient, str]) -> bool:
            client, style = client_style
            system_prompt, _ = get_merge_prompts(style)

            user_prompt = prompt_template.format(
                canonical_name=canonical_name,
                alias=alias,
                context=context,
                entity_type=("symbolic" if is_symbolic else "character"),
            )

            try:
                result, response = client.query_json(user_prompt, system=system_prompt)
                if not response.success or result is None or not isinstance(result, dict):
                    return False

                is_valid = bool(result.get("is_valid_alias", False))
                confidence = float(result.get("confidence", 0.0) or 0.0)

                # Only count as YES if valid AND confidence >= 0.7
                return is_valid and confidence >= 0.7
            except Exception as e:
                logger.warning(f"Competitive alias vote failed: {e}")
                return False

        # Execute all competitors in parallel
        votes = []
        with ThreadPoolExecutor(max_workers=len(self._competitor_clients)) as executor:
            futures = [executor.submit(query_competitor, cs) for cs in self._competitor_clients]
            for future in as_completed(futures):
                votes.append(future.result())

        return votes

    def _is_descriptive_handle(self, name: str) -> bool:
        """Check if a name is a generic descriptive handle (not a proper name).

        Descriptive handles like "the old man", "father", "the stranger" are
        valid aliases for characters even when they don't co-occur or share
        name parts with the canonical name.
        """
        name_lower = name.lower().strip()

        descriptive_handles = {
            # Family relationships
            "father", "mother", "son", "daughter", "brother", "sister",
            "uncle", "aunt", "grandfather", "grandmother", "grandchild",
            "husband", "wife", "spouse", "parent", "child",
            # Age/gender descriptors
            "the old man", "the old woman", "the old one",
            "the young man", "the young woman",
            "the elder", "the younger",
            # Generic role descriptors
            "the visitor", "the guest", "the stranger",
            "the traveler", "the merchant", "the soldier",
            "the sergeant-major",
            # Narrative role descriptors
            "the narrator", "narrator",
            # Title/rank used as standalone reference
            "the professor", "the doctor", "the captain",
            "the lord", "the count", "the baron", "the colonel",
            "the reverend", "the sergeant", "the inspector",
        }

        if name_lower in descriptive_handles:
            return True

        # Match patterns like "the <words>" with 2-4 total words
        # Covers descriptive handles even when capitalized (e.g., "the Count",
        # "the Arabian", "the Creature") — these are character descriptions,
        # not proper multi-word names like "the Great Gatsby"
        if name_lower.startswith("the ") and len(name_lower.split()) <= 4:
            words_after_the = name_lower.split()[1:]
            # Allow if none of the words look like a multi-part proper name
            # (single descriptive words are fine even if capitalized in original)
            if len(words_after_the) <= 2:
                return True

        return False

    def _are_different_titled_people(self, name1: str, name2: str) -> bool:
        """
        Check if two names represent different people based on different title prefixes.

        Examples:
        - "Mr. Sloane" + "Mr. McKee" → True (different surnames with same title = different people)
        - "Mr. Smith" + "Mrs. Smith" → True (different titles = different people)
        - "Catherine" + "Mrs. McKee" → True (one has title + different surname = different people)
        - "Jay Gatsby" + "Gatsby" → False (no title conflict)
        - "Mr. Gatsby" + "Gatsby" → False (same person with/without title)
        - "Mr. White" + "father" → False (generic descriptor = valid alias)
        - "Mrs. White" + "the old woman" → False (generic descriptor = valid alias)

        Returns:
            True if they are clearly different people (DON'T allow as aliases)
        """
        import re

        # CRITICAL: Generic family/role descriptors are ALWAYS valid aliases
        # These should never be blocked, regardless of name matching
        generic_descriptors = {
            # Family relationships
            "father", "mother", "son", "daughter",  "brother", "sister",
            "uncle", "aunt", "grandfather", "grandmother", "grandchild",
            "husband", "wife", "spouse", "parent", "child",
            # Age/gender descriptors
            "the old man", "the old woman", "the old one",
            "the young man", "the young woman",
            "the elder", "the younger",
            # Generic role descriptors
            "the visitor", "the guest", "the stranger",
            "the traveler", "the merchant", "the soldier",
        }

        # Check if either name is a generic descriptor
        name1_lower = name1.lower().strip()
        name2_lower = name2.lower().strip()

        if (name1_lower in generic_descriptors or name2_lower in generic_descriptors
                or self._is_descriptive_handle(name1) or self._is_descriptive_handle(name2)):
            # Generic descriptors are valid aliases for anyone
            logger.debug(
                f"_are_different_titled_people: '{name1}' + '{name2}' -> False "
                f"(generic descriptor detected)"
            )
            return False

        # Extract titles and surnames
        # M. = Monsieur (French equivalent of Mr.)
        title_pattern = r"^(Mr\.|Mrs\.|Miss|Ms\.|Dr\.|M\.|Professor|Prof\.|Lord|Lady|Sir|Dame|Count|Countess|Baron|Baroness|Captain|Capt\.|Colonel|Col\.|Sergeant|Sgt\.|Reverend|Rev\.|Father|Brother|Sister|Madame|Mme\.|Monsieur)\s+(.+)$"

        match1 = re.match(title_pattern, name1, flags=re.IGNORECASE)
        match2 = re.match(title_pattern, name2, flags=re.IGNORECASE)

        # DEBUG LOGGING
        logger.debug(
            f"_are_different_titled_people: checking '{name1}' vs '{name2}' | "
            f"match1={match1 is not None}, match2={match2 is not None}"
        )

        # Case 1: Both have titles
        if match1 and match2:
            title1 = match1.group(1).lower()
            surname1 = match1.group(2).strip().lower()
            title2 = match2.group(1).lower()
            surname2 = match2.group(2).strip().lower()

            logger.debug(f"  Both titled: '{title1} {surname1}' vs '{title2} {surname2}'")

            # Different surnames with titles = different people (even if same title)
            # "Mr. Sloane" vs "Mr. McKee" are different people
            if surname1 != surname2:
                logger.warning(
                    f"DETECTED different titled people: '{name1}' vs '{name2}' (different surnames)"
                )
                return True

            # Same surname, different title = different people (spouses)
            # "Mr. Smith" vs "Mrs. Smith" are different people
            if title1 != title2:
                logger.warning(
                    f"DETECTED different titled people: '{name1}' vs '{name2}' (same surname, different titles)"
                )
                return True

        # Case 2: One has title, other doesn't
        # If the titled surname doesn't match the untitled name at all, different people
        # "Catherine" (single name) + "Mrs. McKee" → different people
        # "Gatsby" + "Mr. Gatsby" → same person
        #
        # Honorific titles that strongly indicate identity (Mr./Mrs./Miss/Ms./Dr./M.)
        # are more reliable for blocking than rank/nobility titles (Lord, Count,
        # Professor, Captain, etc.) which characters may acquire or be known by
        # separately from their given name.
        elif match1 and not match2:
            # name1 has title, name2 doesn't
            title1 = match1.group(1).lower().rstrip(".")
            surname1 = match1.group(2).strip().lower()
            name2_lower = name2.lower()

            # If the untitled name is NOT contained in the surname, different people
            # Exception: substring relationships are OK ("Gatsby" in "Mr. Gatsby")
            # Only block for identity titles (Mr./Mrs./Miss/Ms./Dr./M.) — rank
            # titles (Lord, Count, Professor, etc.) may represent the same person
            # under a different name (e.g., "Lord Godalming" = "Arthur Holmwood")
            identity_titles = {"mr.", "mrs.", "miss", "ms.", "dr.", "m."}
            if name2_lower not in surname1 and surname1 not in name2_lower:
                if match1.group(1).lower() in identity_titles:
                    return True

        elif match2 and not match1:
            # name2 has title, name1 doesn't
            surname2 = match2.group(2).strip().lower()
            name1_lower = name1.lower()

            # If the untitled name is NOT contained in the surname, different people
            identity_titles = {"mr.", "mrs.", "miss", "ms.", "dr.", "m."}
            if name1_lower not in surname2 and surname2 not in name1_lower:
                if match2.group(1).lower() in identity_titles:
                    return True

        # Otherwise, no conflict
        return False

    def profiles_to_characters(
        self,
        profiles: list[MainCastProfile],
    ) -> list[Character]:
        """
        Convert MainCastProfile objects to Character model objects.

        Note: These characters are NOT yet grounded - they need mention search
        and grounding gate validation before being considered high-confidence.
        """
        characters = []

        for i, profile in enumerate(profiles):
            char = Character(
                id=f"main_cast_{i}",
                canonical_name=profile.canonical_name,
                aliases=profile.aliases,
                role=profile.role,
                confidence=ConfidenceLevel.MEDIUM,  # Not yet grounded
                is_symbolic=profile.is_symbolic,
            )

            # Store description in the descriptions list for compatibility
            if profile.description:
                from ...models import CharacterDescription

                char.descriptions = [
                    CharacterDescription(
                        text=profile.description,
                        source_position=0,
                        confidence=ConfidenceLevel.MEDIUM,
                    )
                ]

            characters.append(char)

        return characters
