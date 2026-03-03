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

Return JSON ONLY.

Task:
- Identify 10–15 plot-central entities (people/creatures AND allowed symbolic objects/forces).
- Always include the narrator (if a character) and the title character/entity if applicable.
- Do not invent names not supported by the summaries.
- Provide canonical_name and aliases/variants used in summaries.

Output a JSON object with a "characters" array, each item:
{{
  "characters": [
    {{
      "canonical_name": string,
      "aliases": [string],
      "role": "protagonist"|"antagonist"|"supporting"|"minor",
      "description": string,
      "is_unnamed": boolean,
      "is_symbolic": boolean
    }}
  ]
}}

CHAPTER SUMMARIES:
{summaries}

{plot_summary_section}
"""


# Pass 1: Character Identification Prompt
CHARACTER_IDENTIFICATION_PROMPT = """You are a literary analyst identifying the MAIN CAST of characters from a novel.

TASK: Identify the 10-15 most important characters based on the chapter summaries below.

NOTE: When chapter summaries include a `characters_present` list, treat each entry as a distinct character even if names are similar (e.g., "John" and "John Donaldson" are separate if both are in the list).

IMPORTANT RULES:
1. Include plot-central people/creatures AND symbolic objects/forces that have AGENCY or POWER (e.g., a cursed object that grants wishes, a haunting presence that affects characters). Do NOT include settings/locations where events happen (e.g., a library, a house, a garden, a room) - these are backdrops, not characters. Set `is_symbolic: true` for non-person entities (objects, forces, supernatural presences); leave it `false` for people and creatures.
2. Always include the narrator (if a character) and the title character/entity if applicable
3. Use the most common name form in the summaries as canonical_name (or a distinctive descriptive handle)
4. Do NOT invent names not supported by the summaries
5. **FAMILY MEMBERS WITH SHARED NAMES**: If summaries mention family relationships (father/son, uncle/nephew) with shared first names, they are DIFFERENT people. Check for phrases like "X's father Y" or "receives letter from father, Y" - these indicate TWO characters even if names overlap.
6. Do NOT list aliases in this pass
7. **ROLE ASSIGNMENT**:
   - **protagonist**: Main character(s), narrators, characters the story follows
   - **antagonist**: Characters who ACTIVELY OPPOSE the protagonist (villains, rivals) - requires active harmful intent
   - **supporting**: Important recurring characters, title characters, victims, family members (NOT antagonists)
   - **minor**: Characters with limited appearances

CHAPTER SUMMARIES:
{summaries}

{plot_summary_section}

OUTPUT FORMAT (JSON):
Return a JSON object with a "characters" array:
```json
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
```

Extract the main characters now:"""


# Pass 2: Alias Resolution Prompt
ALIAS_RESOLUTION_PROMPT = """You are analyzing the different names and references for a specific character in a novel.

CHARACTER: {character_name}
Role: {role}
Description: {description}

TASK: Find ALL the different ways this character is referred to in the chapter summaries below.

IMPORTANT RULES:
1. An alias is another name or reference for the EXACT SAME entity as {character_name} — not a different person or object.
2. Include nicknames, titles, shortened forms, spelling variants, and descriptive references (e.g., "the old man", "the woman") used in any chapter — a character may be called by description instead of name in some chapters.
3. Do NOT include persons who created, gave, received, or interacted with this entity — they are separate characters, not aliases.
4. If you are unsure, put it in `uncertain_aliases` instead of `aliases`

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
    ):
        self.llm = llm_client
        self.competitive_config = competitive_config
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
            if not profiles:
                logger.warning("Two-pass extraction returned 0 characters; retrying with single-pass")
                profiles = self._extract_single_pass(summaries_text, plot_section, pattern_hints)
        else:
            profiles = self._extract_single_pass(summaries_text, plot_section, pattern_hints)

        if not profiles:
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

        # AUTO-ADD title-stripped aliases (e.g., "Prospero" for "Prince Prospero")
        profiles = self._add_title_stripped_aliases(profiles)

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

        if not response.success:
            logger.error(f"LLM query failed: {response.error}")
            return []

        if result is None:
            logger.error("Failed to parse JSON from LLM response")
            return []

        # Parse the result into profiles
        profiles = self._parse_profiles(result)
        return profiles

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

        result, response = self.llm.query_json(pass1_prompt)

        if not response.success:
            logger.error(f"Pass 1 LLM query failed: {response.error}")
            return []

        if result is None:
            logger.error("Failed to parse JSON from Pass 1 LLM response")
            return []

        # Parse Pass 1 results
        initial_characters = self._parse_pass1_results(result)
        logger.info(f"Pass 1 identified {len(initial_characters)} main characters")

        # Programmatic is_symbolic correction: the LLM sometimes misses is_symbolic=True
        # for artifact/object names.  Two universal invariants:
        # 1. "the X's Y" (possessive object form) is an artifact, not a person.
        # 2. article + 2+ modifier words + non-human core noun = multi-word object description
        #    (e.g., "the gigantic ebony clock", "the great green light")
        import re as _re_sym
        _possessive_pattern = _re_sym.compile(r"^the\s+\w+[''\u2019]s\s+\w", _re_sym.IGNORECASE)
        # Core nouns that describe humans/beings — exclude from object detection
        _human_core_nouns = {
            "man", "woman", "boy", "girl", "person", "figure", "stranger",
            "visitor", "creature", "being", "one", "self", "fellow", "soul",
            "narrator", "voice", "ghost", "spirit", "phantom", "specter",
        }
        for _char in initial_characters:
            if _char.is_symbolic:
                continue
            name_stripped = _char.canonical_name.strip()
            if _possessive_pattern.match(name_stripped):
                logger.info(
                    f"Programmatic is_symbolic correction: '{_char.canonical_name}' "
                    f"matches possessive-object pattern; marking is_symbolic=True"
                )
                _char.is_symbolic = True
            else:
                # Multi-word object descriptor: article + 1+ modifier + non-human core noun
                # All non-article words must start lowercase (proper names like "the Red Death"
                # have uppercase words — those are entities, not objects).
                _words = name_stripped.lower().split()
                _name_words_orig = name_stripped.split()
                _non_article_orig = [w for w in _name_words_orig if w.lower() not in ("the", "a", "an")]
                _all_lowercase = all(w[0].islower() for w in _non_article_orig if w)
                if (
                    len(_words) >= 3
                    and _words[0] in ("the", "a", "an")
                    and _words[-1] not in _human_core_nouns
                    and _all_lowercase
                ):
                    logger.info(
                        f"Programmatic is_symbolic correction: '{_char.canonical_name}' "
                        f"matches multi-word object descriptor pattern (3+ words, "
                        f"all-lowercase, non-human core noun '{_words[-1]}'); marking is_symbolic=True"
                    )
                    _char.is_symbolic = True

        # Pass 2: Alias Resolution for each character
        profiles = []
        for char in initial_characters:
            logger.info(f"Pass 2: Resolving aliases for {char.canonical_name}")

            pass2_prompt = ALIAS_RESOLUTION_PROMPT.format(
                character_name=char.canonical_name,
                role=char.role,
                description=char.description,
                summaries=summaries_text,
            )

            alias_result, alias_response = self.llm.query_json(pass2_prompt)

            if alias_response.success and alias_result:
                # Merge aliases into the character profile
                aliases = alias_result.get("aliases", [])
                char.aliases = [a.strip() for a in aliases if a.strip()]

                # Optional: keep uncertain aliases separate for later validation
                uncertain = alias_result.get("uncertain_aliases", []) or []
                if isinstance(uncertain, list):
                    char.uncertain_aliases = [
                        a.strip() for a in uncertain if isinstance(a, str) and a.strip()
                    ]

                # Remove canonical name from aliases
                char.aliases = [a for a in char.aliases if a.lower() != char.canonical_name.lower()]

                logger.info(f"Found {len(char.aliases)} aliases for {char.canonical_name}")
            else:
                logger.warning(f"Pass 2 failed for {char.canonical_name}, keeping without aliases")

            profiles.append(char)

        return profiles

    def _parse_pass1_results(self, result: list | dict) -> list[MainCastProfile]:
        """Parse Pass 1 character identification results."""
        profiles = []

        # Handle both list and dict formats
        if isinstance(result, dict):
            # Try known wrapper keys in order of likelihood
            unwrapped = False
            for key in ("characters", "main_cast", "cast", "character_list", "main_characters", "result"):
                if key in result and isinstance(result[key], list):
                    result = result[key]
                    unwrapped = True
                    break
            if not unwrapped:
                # Fall back to first list-valued key
                for val in result.values():
                    if isinstance(val, list):
                        result = val
                        break
                else:
                    result = []

        if not isinstance(result, list):
            logger.warning(f"Expected list from Pass 1, got {type(result)}")
            return []

        for item in result:
            if not isinstance(item, dict):
                continue

            # Accept "name" or "character_name" as fallbacks for "canonical_name"
            canonical = (
                item.get("canonical_name") or item.get("name") or item.get("character_name") or ""
            ).strip()
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
            # Try known wrapper keys in order of likelihood
            unwrapped = False
            for key in ("characters", "main_cast", "cast", "character_list", "main_characters", "result"):
                if key in result and isinstance(result[key], list):
                    result = result[key]
                    unwrapped = True
                    break
            if not unwrapped:
                for val in result.values():
                    if isinstance(val, list):
                        result = val
                        break
                else:
                    result = []

        if not isinstance(result, list):
            logger.warning(f"Expected list, got {type(result)}")
            return []

        for item in result:
            if not isinstance(item, dict):
                continue

            # Accept "name" or "character_name" as fallbacks for "canonical_name"
            canonical = (
                item.get("canonical_name") or item.get("name") or item.get("character_name") or ""
            ).strip()
            if not canonical:
                continue

            profile = MainCastProfile(
                canonical_name=canonical,
                aliases=[a.strip() for a in item.get("aliases", []) if a.strip()],
                uncertain_aliases=[
                    a.strip()
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

        # Pre-build all name forms per profile (canonical, aliases, surname fragments).
        # Fragments ensure e.g. "De Lacey" from alias "Felix De Lacey" is marked as taken.
        profile_names: dict[int, set[str]] = {}
        for p in profiles:
            names: set[str] = set()
            for phrase in [p.canonical_name] + list(p.aliases):
                phrase_l = phrase.lower()
                names.add(phrase_l)
                words = phrase_l.split()
                names.update(
                    " ".join(words[i:]) for i in range(1, len(words))
                    if len(" ".join(words[i:])) >= 3
                )
            profile_names[id(p)] = names

        # Kinship terms: aliases using these words are used INSTEAD of proper names
        # in first-person narration and may not appear verbatim in summaries.
        _KINSHIP_TERMS = {
            "father", "mother", "brother", "sister",
            "son", "daughter", "uncle", "aunt",
            "nephew", "niece", "cousin", "grandfather",
            "grandmother", "grandson", "granddaughter",
            "husband", "wife", "spouse", "partner",
            "parent", "child", "guardian", "ward",
        }

        verified_profiles = []

        for profile in profiles:
            canonical_lower = profile.canonical_name.lower()
            verified_aliases = []

            # Build the union of all other characters' names/aliases for conflict detection
            other_aliases: set[str] = set()
            for p_id, names in profile_names.items():
                if p_id != id(profile):
                    other_aliases.update(names)

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
                    logger.warning(
                        f"BLOCKED alias: '{alias}' is a meta-reference (storytelling device), "
                        f"not a valid character alias for '{profile.canonical_name}'"
                    )
                    continue

                # NOTE: Object keyword blocking for aliases (clock, door, etc.) is handled by
                # CharacterAgent._is_valid_alias() which runs during merge operations.
                # This avoids duplicate filtering and keeps alias validation in one place.

                # RULE 0.6: Block plural group noun descriptors as aliases for singular characters.
                # Plural agent/role nouns (courtiers, musicians, waltzers, servants, soldiers)
                # describe groups of people — they are never valid aliases for an individual.
                # Universal linguistic invariant: article+plural_noun = group reference ≠ individual.
                # Exception: if the canonical name is itself a group noun, allow plural aliases.
                _PLURAL_AGENT_SUFFIXES_R06 = (
                    "ers", "ors", "ians", "ists", "ants", "ents", "iers", "ees", "smen", "ies"
                )
                _articles_r06 = {"the", "a", "an", "of", "in", "from", "at", "by", "with"}
                alias_tokens_r06 = [
                    w.strip(".,;:'\"()")
                    for w in alias_lower.split()
                    if w.strip(".,;:'\"()") and w.strip(".,;:'\"()") not in _articles_r06
                ]
                if alias_tokens_r06:
                    alias_head_r06 = alias_tokens_r06[-1]  # already lowercase via alias_lower
                    is_plural_group_r06 = any(
                        alias_head_r06.endswith(sfx) and len(alias_head_r06) > len(sfx) + 1
                        for sfx in _PLURAL_AGENT_SUFFIXES_R06
                    )
                    if is_plural_group_r06:
                        # Don't block if canonical is itself a group noun (collective character)
                        canonical_head_r06 = profile.canonical_name.split()[-1].lower()
                        canonical_is_group_r06 = any(
                            canonical_head_r06.endswith(sfx) and len(canonical_head_r06) > len(sfx) + 1
                            for sfx in _PLURAL_AGENT_SUFFIXES_R06
                        )
                        if not canonical_is_group_r06:
                            logger.warning(
                                f"BLOCKED alias: '{alias}' is a plural group noun and cannot be an "
                                f"alias for individual character '{profile.canonical_name}'"
                            )
                            continue

                # RULE 0.5: Semantic coherence check for symbolic objects
                # If the canonical name is a symbolic entity (is_symbolic=True — an object/artifact),
                # verify that aliases refer to THE SAME object, not just any co-occurring nouns.
                # IMPORTANT: This rule does NOT apply to personified concepts (forces/abstractions
                # like "the Red Death", "Death", "Fear") because they can legitimately manifest
                # under different physical descriptions (e.g., "the Red Death" → "the masked figure").
                # Symbolic objects, however, are fixed entities: "the monkey's paw" ≠ "the sergeant".

                if getattr(profile, "is_symbolic", False):
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
                        logger.warning(
                            f"BLOCKED alias: '{alias}' (core noun: '{alias_noun}') is semantically "
                            f"unrelated to symbolic object '{profile.canonical_name}' (core noun: '{canonical_noun}'). "
                            f"Symbolic objects must have aliases referring to the SAME object."
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

                # RULE 3: Cross-character conflict check
                # If an alias already belongs to another character in this cast, it's
                # theirs — not this character's (catches narrator-subject confusion).
                # Skip when alias is a substring of this canonical name (own components ok).
                if alias_lower in other_aliases and alias_lower not in canonical_lower:
                    logger.warning(
                        f"BLOCKED alias: '{alias}' is already claimed as a name or alias "
                        f"by another character in this cast — cannot be an alias for "
                        f"'{profile.canonical_name}'"
                    )
                    continue

                # RULE 3b: Block aliases whose parenthetical content references another character.
                # e.g., "the blind father (De Lacey)" — "(De Lacey)" belongs to another cast member.
                import re as _re_p
                _pm = _re_p.search(r'\(([^)]+)\)', alias_lower)
                if _pm:
                    _pc = _pm.group(1).strip()
                    if any(_pc in on or on in _pc for pid, ns in profile_names.items()
                           if pid != id(profile) for on in ns if len(on) >= 3):
                        logger.warning(f"BLOCKED alias: '{alias}' parenthetical references another character")
                        continue

                # RULE 2: Skip co-occurrence check if alias is a substring of canonical name.
                if alias_lower in canonical_lower or canonical_lower in alias_lower:
                    verified_aliases.append(alias)
                    continue

                # Check co-occurrence in summaries
                # Use base canonical form (strip parenthetical) for searching, since the full
                # string "the old man (De Lacey)" never appears literally in summaries but
                # "the old man" does. Without this, canonical_found is always False for
                # parenthetical canonical names, bypassing the co-occurrence block entirely.
                canonical_base = canonical_lower
                if " (" in canonical_base:
                    canonical_base = canonical_base.split(" (")[0].strip()

                canonical_found = False
                alias_found = False

                for summary in chapter_summaries:
                    summary_lower = summary.lower()
                    if canonical_base in summary_lower:
                        canonical_found = True
                    if alias_lower in summary_lower:
                        alias_found = True

                # RULE 2a: Block aliases absent from summaries (LLM hallucination).
                # Exception: kinship terms may be paraphrased and won't appear verbatim.
                if not alias_found:
                    alias_tokens = set(alias.lower().split())
                    if not (alias_tokens & _KINSHIP_TERMS) and alias_lower not in canonical_lower:
                        logger.warning(
                            f"BLOCKED alias: '{alias}' for '{profile.canonical_name}' "
                            f"not found in any chapter summary (likely hallucinated)"
                        )
                        continue

                # Block only when both appear but NEVER in the same summary AND share no name parts.
                if canonical_found and alias_found:
                    # Check if they ever co-occur in the same summary (use base canonical form)
                    cooccur = False
                    for summary in chapter_summaries:
                        summary_lower = summary.lower()
                        if canonical_base in summary_lower and alias_lower in summary_lower:
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
                        # Check if they share a meaningful name part (excluding stop words
                        # so "the creature" and "the Turk" don't share "the" as a name part).
                        _SW = {"the","a","an","of","and","or","in","on","at","for","with","by","to","from"}
                        canonical_parts = {p for p in profile.canonical_name.lower().split() if p not in _SW}
                        alias_parts = {p for p in alias.lower().split() if p not in _SW}
                        shared_parts = canonical_parts & alias_parts

                        # Also check for partial matches (e.g., "Gatz" vs "Gatsby")
                        has_similar_part = False
                        for cpart in canonical_parts:
                            for apart in alias_parts:
                                # Check if one is a substring of the other (min length 4 to avoid false positives)
                                if len(cpart) >= 4 and len(apart) >= 4:
                                    if cpart[:4] == apart[:4]:  # Same first 4 chars
                                        has_similar_part = True
                                        break

                        # Kinship carve-out: aliases like "father", "my father",
                        # "old Frankenstein" use kinship terms that are naturally
                        # used INSTEAD of proper names, so co-occurrence will
                        # always fail. Allow them unconditionally.
                        alias_tokens = set(alias.lower().split())
                        is_kinship = bool(alias_tokens & _KINSHIP_TERMS)

                        if is_kinship:
                            logger.info(
                                f"ALLOWED kinship alias despite no co-occurrence: "
                                f"'{alias}' → '{profile.canonical_name}'"
                            )
                            verified_aliases.append(alias)
                            continue

                        # Descriptor alias exemption: common-noun descriptors (no proper nouns)
                        # are often used in place of a character's name in certain chapters.
                        # E.g., "the old man" for a character known as "Mr. White" in other chapters.
                        # Allow if alias has NO capitalized non-article words (pure descriptor).
                        _articles_sw = {"the", "a", "an", "of", "in", "from", "at", "by", "with"}
                        alias_content_words = [
                            w.strip(".,;:'\"()") for w in alias.split()
                            if w.strip(".,;:'\"()").lower() not in _articles_sw
                        ]
                        is_pure_descriptor = alias_content_words and all(
                            not w[0].isupper() for w in alias_content_words if w
                        )
                        if is_pure_descriptor:
                            logger.info(
                                f"ALLOWED descriptor alias despite no co-occurrence: "
                                f"'{alias}' → '{profile.canonical_name}' "
                                f"(common-noun descriptor; character may be referenced differently in some chapters)"
                            )
                            verified_aliases.append(alias)
                            continue

                        if not shared_parts and not has_similar_part:
                            logger.warning(
                                f"BLOCKED alias: '{alias}' and '{profile.canonical_name}' appear in summaries "
                                f"but NEVER co-occur in the same chapter and have no name overlap"
                            )
                            continue
                        else:
                            logger.info(
                                f"ALLOWED alias despite no co-occurrence: '{alias}' → '{profile.canonical_name}' "
                                f"(share name parts or have similar surname, likely birth name/former identity)"
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

        return verified_profiles

    def _add_title_stripped_aliases(self, profiles: list[MainCastProfile]) -> list[MainCastProfile]:
        """
        Auto-add shortened name forms for characters with noble/royal title prefixes.

        'Prince Prospero' → adds 'Prospero' as alias.
        'King Lear' → adds 'Lear' as alias.

        This handles the universal pattern where formal titles are used in some contexts
        and the name alone in others. The stripped form is always a valid reference.
        """
        _NOBLE_TITLES = {
            "prince", "princess", "king", "queen", "duke", "duchess",
            "count", "countess", "lord", "lady", "earl", "baron", "baroness",
            "sir", "dame", "emperor", "empress", "archduke", "archduchess",
            "viscount", "viscountess", "marquis", "marchioness",
        }
        for profile in profiles:
            words = profile.canonical_name.split()
            if len(words) >= 2 and words[0].lower() in _NOBLE_TITLES:
                stripped_name = " ".join(words[1:])
                stripped_lower = stripped_name.lower()
                existing_lower = {a.lower() for a in profile.aliases}
                if stripped_lower not in existing_lower and stripped_lower != profile.canonical_name.lower():
                    profile.aliases.append(stripped_name)
                    logger.info(
                        f"AUTO-ADDED title-stripped alias: '{stripped_name}' for '{profile.canonical_name}'"
                    )
        return profiles

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

        # Create a summary context for the LLM.
        # Use ALL chapter summaries (not just the first 5) so characters introduced
        # in later chapters have context for accurate alias voting. Sampling only the
        # first few chapters causes false rejections for characters appearing mid-book
        # and false acceptances when the LLM lacks enough context to distinguish them.
        all_summaries = "\n".join(chapter_summaries)
        if len(all_summaries) > 10000:
            all_summaries = all_summaries[:10000] + "..."

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

    def _are_different_titled_people(self, name1: str, name2: str) -> bool:
        """
        Check if two names represent different people based on different title prefixes.

        Examples:
        - "Mr. Sloane" + "Mr. McKee" → True (different surnames with same title = different people)
        - "Mr. Smith" + "Mrs. Smith" → True (different titles = different people)
        - "Catherine" + "Mrs. McKee" → True (one has title + different surname = different people)
        - "Jay Smith" + "Smith" → False (no title conflict)
        - "Mr. Smith" + "Smith" → False (same person with/without title)
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

        if name1_lower in generic_descriptors or name2_lower in generic_descriptors:
            # Generic descriptors are valid aliases for anyone
            logger.debug(
                f"_are_different_titled_people: '{name1}' + '{name2}' -> False "
                f"(generic descriptor detected)"
            )
            return False

        # Extract titles and surnames
        # M. = Monsieur (French equivalent of Mr.)
        # Professor/Prof./Captain/Sergeant/Lord/Lady are universal academic/military/noble titles
        title_pattern = r"^(Mr\.|Mrs\.|Miss|Ms\.|Dr\.|M\.|Professor|Prof\.|Captain|Sergeant|Colonel|General|Lord|Lady|Baron|Count|Countess|Sir)\s+(.+)$"

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
        elif match1 and not match2:
            # name1 has title, name2 doesn't
            surname1 = match1.group(2).strip().lower()
            name2_lower = name2.lower()

            # If the untitled name is NOT contained in the surname, different people
            # Exception: substring relationships are OK (e.g., "Smith" in "Mr. Smith")
            if name2_lower not in surname1 and surname1 not in name2_lower:
                return True

        elif match2 and not match1:
            # name2 has title, name1 doesn't
            surname2 = match2.group(2).strip().lower()
            name1_lower = name1.lower()

            # If the untitled name is NOT contained in the surname, different people
            if name1_lower not in surname2 and surname2 not in name1_lower:
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
