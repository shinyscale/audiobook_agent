"""
CharacterAgent - Summary-Driven Character Extraction

This agent implements the profile-first approach:
1. Extract main cast profiles from chapter summaries (F1)
2. Search for mentions deterministically (F2)
3. Apply grounding gate to reject hallucinations (F2b)
4. Detect narrator from summaries (F4)
5. Extract supporting cast via NER (F3)

Key improvements over v1:
- No complex merge heuristics
- Summaries provide identity context upfront
- Grounding prevents hallucinated characters
- Dramatically simpler code (<500 lines vs 2500+)
"""

import logging
import time
from typing import Optional

from ..llm.client import LLMClient
from ..models import Character, StructuralElement, StructureType
from ..pipeline.character_extraction.models import Character as PipelineCharacter
from ..pipeline.character_extraction.models import CharacterMap
from ..pipeline.character_extraction_v2 import (
    GroundingGate,
    MainCastExtractor,
    MentionSearcher,
    NarratorDetector,
    NarratorInfo,
    SupportingCastExtractor,
)
from ..utils.similarity import names_similar, string_similarity
from .base import (
    Agent,
    AgentContext,
    AgentResult,
    VerificationIssue,
    VerificationLevel,
    VerificationResult,
)
from .config import AgentConfig, CompetitiveConfig

logger = logging.getLogger(__name__)

# Standard English diminutive forms mapped to their canonical long-form equivalents.
# Used to merge nickname variants extracted by NER (e.g., "Johnny" → alias of "John").
# Only unambiguous one-to-one mappings are included; standalone names like "Ted" or "Bob"
# are intentionally excluded to avoid merging genuinely different characters.
STANDARD_DIMINUTIVES: dict[str, str] = {
    "johnny": "john",
    "johnnie": "john",
    "jimmy": "james",
    "jimmie": "james",
    "charlie": "charles",
    "tommy": "thomas",
    "bobby": "robert",
    "robbie": "robert",
    "billy": "william",
    "willie": "william",
    "freddie": "frederick",
    "freddy": "frederick",
}

# Common English nicknames mapped to their standard formal first names.
# Used to recognize when a supporting character with a multi-word formal name
# (e.g., "James Dillingham Young") is the same person as a main cast character
# identified only by nickname (e.g., "Jim").
# Only clear, widely-used nickname↔formal pairings are included.
# This is a RECOGNITION lexicon, not a rejection list.
NICKNAME_TO_FORMAL: dict[str, str] = {
    "jim": "james",
    "jimmy": "james",
    "bill": "william",
    "billy": "william",
    "bob": "robert",
    "dick": "richard",
    "rick": "richard",
    "rich": "richard",
    "tom": "thomas",
    "tommy": "thomas",
    "jack": "john",
    "harry": "henry",
    "ned": "edward",
    "ted": "edward",
    "betty": "elizabeth",
    "bess": "elizabeth",
    "liz": "elizabeth",
    "kate": "catherine",
    "kit": "christopher",
    "molly": "mary",
    "meg": "margaret",
    "peggy": "margaret",
    "sue": "susan",
    "joe": "joseph",
    "joey": "joseph",
    "mike": "michael",
    "andy": "andrew",
    "nick": "nicholas",
    "chris": "christopher",
    "sal": "sarah",
    "bart": "bartholomew",
    "gus": "augustus",
    "milt": "milton",
}

# Reverse mapping: formal first name → list of known nicknames.
# Computed once from NICKNAME_TO_FORMAL for efficient lookup.
_FORMAL_TO_NICKNAMES: dict[str, list[str]] = {}
for _nick, _formal in NICKNAME_TO_FORMAL.items():
    _FORMAL_TO_NICKNAMES.setdefault(_formal, []).append(_nick)


class CharacterAgent(Agent):
    """
    V2 Character Agent using summary-driven extraction.

    Pipeline order: summaries → main_cast → mentions → grounding → narrator → supporting
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        config: Optional[AgentConfig] = None,
        min_grounding_mentions: int = 3,
        competitive_config: Optional[CompetitiveConfig] = None,
    ):
        self.llm = llm_client
        self.config = config or AgentConfig()
        self.min_grounding_mentions = min_grounding_mentions
        self.competitive_config = competitive_config

    @property
    def name(self) -> str:
        return "characters"

    def _refresh_mentions(
        self,
        char_ids: set,
        cast: list,
        searcher,
        mention_results: dict,
    ) -> None:
        """Re-search mentions for characters that gained new aliases.

        After any merge/split step that adds aliases, the mention counts
        and chapter distributions become stale.  This helper re-runs the
        searcher for the affected characters and updates mention_results
        so downstream profile generation sees the correct data.
        """
        for char_id in char_ids:
            char = next((c for c in cast if c.id == char_id), None)
            if char:
                result = searcher.search_character(char)
                char.mention_count = result.total_mentions
                char.mentions = result.mentions
                mention_results[char.id] = result
                if result.chapter_distribution:
                    chapters = sorted(result.chapter_distribution.keys())
                    char.first_appearance_chapter = chapters[0]


    @property
    def depends_on(self) -> list[str]:
        """V2 requires summaries (from SummaryAgent) before running."""
        return ["structure", "summaries"]

    @property
    def recommended_models(self) -> list[str]:
        return [
            "qwen2.5:72b",  # Strong local model for character understanding
            "llama3.2",  # Good local alternative
            "gpt-4o-mini",  # Cloud fallback
        ]

    def run(self, context: AgentContext) -> AgentResult[CharacterMap]:
        """
        Run the v2 character extraction pipeline.

        Order:
        1. Extract main cast from summaries (F1)
        2. Search for mentions (F2)
        3. Apply grounding gate (F2b)
        4. Detect narrator (F4)
        5. Extract supporting cast (F3)
        """
        start_time = time.perf_counter()
        issues = []

        # Validate required inputs
        if not self.llm:
            return self._error_result("No LLM client configured", start_time)

        # Get chapter summaries from context
        chapter_summaries = self._get_chapter_summaries(context)
        if not chapter_summaries:
            return self._error_result(
                "No chapter summaries available - SummaryAgent must run first",
                start_time,
            )

        # Get chapters for mention position mapping
        chapters = self._get_chapters(context)

        # Get plot summary if available
        plot_summary = self._get_plot_summary(context)

        # STEP 1: Extract main cast from summaries (F1)
        logger.info("V2 Step 1: Extracting main cast from summaries")
        main_cast_extractor = MainCastExtractor(self.llm, self.competitive_config)
        profiles = main_cast_extractor.extract(chapter_summaries, plot_summary)

        if not profiles:
            issues.append("No main cast profiles extracted from summaries")

        # Convert profiles to Character objects
        characters = main_cast_extractor.profiles_to_characters(profiles)
        logger.info(f"V2 Step 1 complete: {len(characters)} main cast candidates")

        # STEP 1.2: Programmatic acronym alias injection.
        # Universal invariant: if a character has an all-caps short name (2-5 letters),
        # scan the raw text for explicit expansions ("NAME stands for ...", "NAME, Full Phrase")
        # and inject them as aliases deterministically. This handles LLM non-determinism
        # where Pass 2 may or may not capture acronym expansions on a given run.
        import re as _re12
        if context.text:
            _acronym_pat1 = _re12.compile(
                r'\b([A-Z]{2,5})\b\s+st(?:ands?|ood)\s+for\s+([A-Za-z][A-Za-z\s]{5,60}?)(?=[,.\n;]|$)',
                _re12.MULTILINE,
            )
            _acronym_pat2 = _re12.compile(
                r'\b([A-Z]{2,5})\b[,\.]\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
                _re12.MULTILINE,
            )
            for _char in characters:
                _cname = _char.canonical_name.strip()
                if not _re12.match(r'^[A-Z]{2,5}$', _cname):
                    continue
                _new_aliases: list[str] = []
                _existing_aliases = list(_char.aliases or [])
                for _m in _acronym_pat1.finditer(context.text):
                    if _m.group(1) == _cname:
                        _exp = _m.group(2).strip()
                        if _exp and _exp not in _existing_aliases and _exp not in _new_aliases and _exp != _cname:
                            _new_aliases.append(_exp)
                for _m in _acronym_pat2.finditer(context.text):
                    if _m.group(1) == _cname:
                        _exp = _m.group(2).strip()
                        if _exp and _exp not in _existing_aliases and _exp not in _new_aliases and _exp != _cname:
                            _new_aliases.append(_exp)
                if _new_aliases:
                    _char.aliases = _existing_aliases + _new_aliases
                    logger.info(
                        f"V2 Step 1.2: Injected acronym aliases for '{_cname}': {_new_aliases}"
                    )
                    # Remove any standalone characters whose canonical_name is now an alias
                    # of this acronym character. This prevents verify_aliases Rule 3 from
                    # blocking the alias because "another character" claims the expansion name.
                    _all_aliases_lower = {a.lower() for a in _char.aliases}
                    _dups_to_remove = [
                        _oc for _oc in characters
                        if _oc is not _char and _oc.canonical_name.lower() in _all_aliases_lower
                    ]
                    for _oc in _dups_to_remove:
                        characters.remove(_oc)
                        logger.info(
                            f"V2 Step 1.2: Removed standalone '{_oc.canonical_name}' "
                            f"(absorbed as alias of '{_cname}')"
                        )

        # STEP 1.4: Filter non-character entities (locations, objects, concepts)
        # Some LLMs may extract setting elements with roles like "setting/plot device"
        non_character_roles = ["setting", "location", "place", "object", "concept", "device"]
        before_filter = len(characters)
        characters = [
            c
            for c in characters
            if (
                # Keep plot-central symbolic entities explicitly marked as such
                bool(getattr(c, "is_symbolic", False))
                or not any(non_char_role in (c.role or "").lower() for non_char_role in non_character_roles)
            )
        ]
        if len(characters) < before_filter:
            filtered_count = before_filter - len(characters)
            logger.info(f"V2 Step 1.4: Filtered {filtered_count} non-character entity/entities")

        # STEP 1.5: Merge title-variant characters (deterministic post-processing)
        characters = self._merge_title_variants(characters)
        logger.info(f"V2 Step 1.5 complete: {len(characters)} after title-variant merge")

        # STEP 2: Search for mentions (F2)
        logger.info("V2 Step 2: Searching for character mentions")
        searcher = MentionSearcher(context.text, chapters)
        mention_results = searcher.search_all(characters)
        characters = searcher.update_characters_with_mentions(characters, mention_results)

        # STEP 3: Apply grounding gate (F2b)
        logger.info("V2 Step 3: Applying grounding gate")
        grounding_gate = GroundingGate(
            min_mentions=self.min_grounding_mentions,
            remove_ungrounded_aliases=True,
        )
        grounding_report = grounding_gate.apply(characters, mention_results)
        grounding_gate.log_report(grounding_report)

        # Use grounded characters as main cast
        main_cast = grounding_report.grounded_characters
        ungrounded = grounding_report.ungrounded_characters

        if ungrounded:
            issues.append(
                f"{len(ungrounded)} characters excluded by grounding gate "
                f"(insufficient text evidence)"
            )

        logger.info(f"V2 Step 3 complete: {len(main_cast)} grounded characters")

        # STEP 3.1: Fallback — when main_cast extraction returned 0 grounded characters,
        # retry with a simpler prompt on just the plot_summary text.
        # The main_cast LLM may fail on long/complex chapter summaries while succeeding
        # on a shorter, more focused summary. This is a universal safety net.
        if not main_cast and plot_summary:
            logger.warning(
                "V2 Step 3.1 FALLBACK: main_cast empty after grounding. "
                "Retrying with simpler prompt on plot_summary."
            )
            fallback_prompt = (
                "List every named character or sentient entity in this story. "
                "Include humans, non-human beings, AI, and any named force that acts with agency. "
                "Return JSON array only.\n\n"
                "STORY SUMMARY:\n{summary}\n\n"
                "Return a JSON array:\n"
                '[{{"canonical_name": "Name", "role": "protagonist|antagonist|supporting", '
                '"description": "brief description", "is_symbolic": false}}]'
            ).format(summary=plot_summary[:3000])

            fallback_result, fallback_response = self.llm.query_json(fallback_prompt)
            logger.info(
                f"V2 Step 3.1 fallback LLM: success={fallback_response.success}, "
                f"result_type={type(fallback_result).__name__ if fallback_result is not None else 'None'}"
            )
            if fallback_response.success and fallback_result is not None:
                fallback_profiles = main_cast_extractor._parse_pass1_results(fallback_result)
                logger.info(f"V2 Step 3.1 fallback parsed {len(fallback_profiles)} profiles")
                if fallback_profiles:
                    fallback_chars = main_cast_extractor.profiles_to_characters(fallback_profiles)
                    fallback_mentions = searcher.search_all(fallback_chars)
                    fallback_chars = searcher.update_characters_with_mentions(
                        fallback_chars, fallback_mentions
                    )
                    mention_results.update(fallback_mentions)
                    # Fallback characters come from the LLM-generated plot_summary, which is
                    # itself a distillation of the text. They are implicitly grounded and do
                    # NOT need the grounding gate — which would incorrectly reject short names
                    # like "AM" (2-letter abbreviation with ambiguous lowercase matches).
                    main_cast = fallback_chars
                    logger.info(
                        f"V2 Step 3.1 fallback: {len(fallback_profiles)} profiles → "
                        f"{len(main_cast)} characters (grounding skipped for plot_summary fallback)"
                    )
            else:
                logger.warning(
                    f"V2 Step 3.1 fallback LLM failed: {fallback_response.error}"
                )

        # STEP 3.4: Pre-merge same-firstname variants (e.g., maiden/married name)
        # This must run BEFORE the main merge to avoid the ambiguity problem where
        # a first-name-only reference matches multiple full names and gets skipped
        logger.info("V2 Step 3.4: Pre-merging same-firstname variants")
        main_cast = self._merge_same_firstname_variants(main_cast)
        logger.info(f"V2 Step 3.4 complete: {len(main_cast)} after same-firstname merge")

        # STEP 3.5: Merge within main cast (last-name-only, spelling variants, first-name-only)
        logger.info("V2 Step 3.5: Merging within main cast")
        main_cast, within_main_aliases_added = self._merge_within_main_cast(main_cast)

        # STEP 3.6: Deduplicate alias-canonical conflicts
        # Handles cases like "Myrtle Wilson" (canonical) + "Mrs. Wilson" (canonical with alias "Myrtle Wilson")
        logger.info("V2 Step 3.6: Deduplicating alias-canonical conflicts")
        main_cast, alias_dedupe_aliases_added = self._deduplicate_alias_canonical_conflicts(
            main_cast
        )
        if alias_dedupe_aliases_added:
            within_main_aliases_added.update(alias_dedupe_aliases_added)

        # Re-search mentions for characters that gained new aliases
        if within_main_aliases_added:
            logger.info(
                f"Re-searching mentions for {len(within_main_aliases_added)} characters with new aliases"
            )
            self._refresh_mentions(within_main_aliases_added, main_cast, searcher, mention_results)

        logger.info(f"V2 Step 3.5 complete: {len(main_cast)} main cast after within-cast merge")

        # STEP 3.6b: Merge common-noun descriptor characters into proper-name characters.
        # Handles cases where different chapters use a descriptive phrase ("the old man")
        # instead of the character's proper name ("Mr. White"), causing the LLM to extract
        # them as separate characters. This is a universal invariant: a common-noun phrase
        # with no proper nouns, substantially more mentions than the corresponding proper-name
        # character, and matching gender/role, is almost certainly a narrative alias.
        logger.info("V2 Step 3.6b: Merging descriptor characters into proper-name characters")
        main_cast, descriptor_merged = self._merge_descriptor_into_proper_name(main_cast)
        if descriptor_merged:
            logger.info(
                f"V2 Step 3.6b: Merged {len(descriptor_merged)} descriptor(s) "
                f"into proper-name character(s): {descriptor_merged}"
            )
            # Re-search mentions for characters that gained aliases from descriptor merge
            descriptor_ids = {
                c.id for c in main_cast
                if c.canonical_name in descriptor_merged
                or any(a in descriptor_merged for a in (c.aliases or []))
            }
            self._refresh_mentions(descriptor_ids, main_cast, searcher, mention_results)

        # STEP 3.7: Defensive split for wrongly-merged titled characters
        # Handles LLM hallucinations where "M. Waldman" gets "M. Krempe" as an alias
        # despite explicit prompt instructions
        logger.info("V2 Step 3.7: Splitting wrongly-merged titled characters")
        main_cast, split_count = self._split_wrongly_merged_titled_characters(main_cast)
        if split_count > 0:
            logger.warning(
                f"V2 Step 3.7: Split {split_count} wrongly-merged titled character pairs "
                f"(LLM ignored prompt instructions)"
            )

        # STEP 3.8: Defensive split for semantic conflicts
        # Handles LLM hallucinations where semantically incompatible terms get merged
        # (e.g., "the creature" as alias of "the old man")
        logger.info("V2 Step 3.8: Splitting semantically conflicting aliases")

        main_cast, semantic_split_count = self._split_semantic_conflicts(main_cast)
        if semantic_split_count > 0:
            logger.warning(
                f"V2 Step 3.8: Split {semantic_split_count} semantically conflicting alias pairs "
                f"(LLM merged incompatible entity types)"
            )

        # STEP 3.9: Post-split repair pass
        # Splitting creates new split_* character stubs with mention_count=0.
        # We must ground them and then re-run within-main merges so they can be absorbed
        # into existing descriptive clusters (e.g., creature/monster variants).
        split_stubs = [c for c in main_cast if isinstance(c.id, str) and c.id.startswith("split_")]
        if split_stubs:
            logger.info(f"V2 Step 3.9: Grounding {len(split_stubs)} split_* character stub(s)")
            split_ids = {c.id for c in split_stubs}
            self._refresh_mentions(split_ids, main_cast, searcher, mention_results)

            logger.info("V2 Step 3.9: Re-running within-main merges after split repair")
            main_cast, post_split_aliases_added = self._merge_within_main_cast(main_cast)
            main_cast, post_split_dedupe_added = self._deduplicate_alias_canonical_conflicts(
                main_cast
            )
            if post_split_dedupe_added:
                post_split_aliases_added.update(post_split_dedupe_added)

            # Re-search mentions for characters that gained new aliases during post-split merges
            if post_split_aliases_added:
                logger.info(
                    f"V2 Step 3.9: Re-searching mentions for {len(post_split_aliases_added)} post-split merged character(s)"
                )
                self._refresh_mentions(post_split_aliases_added, main_cast, searcher, mention_results)

        # STEP 3.95: Split over-merged same-name characters using alias contradiction detection.
        # Universal invariant: a single character CANNOT simultaneously hold a parent-generation
        # role alias ("the father", "the mother") AND a child-generation role alias ("the boy",
        # "the son", "the daughter"). When both tiers appear on one character, a false merge
        # occurred. Split programmatically — no external signal or prefix format required.
        _ROLE_SW_395 = {"the", "a", "an", "his", "her", "their", "my", "our"}
        _PARENT_TIER_395 = {"father", "mother", "dad", "mom", "daddy", "mama", "papa", "pa", "ma"}
        _CHILD_TIER_395 = {"son", "daughter", "boy", "girl", "child", "kid", "lad", "lass"}

        def _alias_tier_395(alias: str) -> Optional[str]:
            """Return 'parent', 'child', or None.
            Only returns a tier when the alias is a pure role-descriptor (no extraneous words
            that would indicate a proper name like "Father Brown")."""
            core = set(alias.lower().split()) - _ROLE_SW_395
            if not core:
                return None
            if core <= (_PARENT_TIER_395 | _CHILD_TIER_395):
                if core & _PARENT_TIER_395:
                    return "parent"
                return "child"
            return None

        for _char in list(main_cast):
            _parent_als = [a for a in _char.aliases if _alias_tier_395(a) == "parent"]
            _child_als = [a for a in _char.aliases if _alias_tier_395(a) == "child"]

            # Also check the canonical name's own parenthetical label.
            # e.g. "John Donaldson (the father)" → parenthetical "the father" is parent-tier.
            # This catches the case where the LLM merges father+son under the father's canonical
            # name but the son's aliases ("the boy") appear on the same character.
            _canon_paren_tier = None
            _canon_paren_str = None
            if "(" in _char.canonical_name:
                _paren_content = _char.canonical_name[_char.canonical_name.index("(") + 1:].rstrip(")").strip()
                _canon_paren_tier = _alias_tier_395(_paren_content)
                _canon_paren_str = _paren_content
                if _canon_paren_tier == "parent" and not _parent_als:
                    _parent_als = [_canon_paren_str]
                elif _canon_paren_tier == "child" and not _child_als:
                    _child_als = [_canon_paren_str]

            if not _parent_als or not _child_als:
                continue  # no contradiction — skip

            _neutral_als = [
                a for a in _char.aliases
                if _alias_tier_395(a) is None and a != _char.canonical_name
            ]

            logger.info(
                f"V2 Step 3.95: Alias contradiction on '{_char.canonical_name}' "
                f"(parent_aliases={_parent_als}, child_aliases={_child_als}); splitting"
            )

            # Extract base name (strip any parenthetical already on the canonical)
            if "(" in _char.canonical_name:
                _base_name_395 = _char.canonical_name[:_char.canonical_name.index("(")].strip()
            else:
                _base_name_395 = _char.canonical_name

            # Parent-tier character: BaseName + "(the father/mother/...)"
            _parent_label = _parent_als[0].lower().strip()  # e.g. "the father"
            _parent_canonical = f"{_base_name_395} ({_parent_label})"
            from ..models import ConfidenceLevel as _CL395
            # Aliases for parent: real parent-tier aliases (not the paren we synthesized from
            # canonical) plus the base name and old canonical (if different from new canonical)
            _parent_char_als_395 = [a for a in _parent_als if a != _canon_paren_str] + [_base_name_395]
            if _char.canonical_name != _parent_canonical:
                _parent_char_als_395.append(_char.canonical_name)
            _parent_char = Character(
                id=f"{_char.id}_parent",
                canonical_name=_parent_canonical,
                role="supporting",
                mention_count=max(1, _char.mention_count // 2),
                confidence=_CL395.MEDIUM,
                aliases=_parent_char_als_395,
            )
            main_cast.append(_parent_char)

            # Child character: if canonical currently has a parent-tier parenthetical, rename it
            if _canon_paren_tier == "parent":
                _child_label = _child_als[0].lower().strip()  # e.g. "the boy"
                _char.canonical_name = f"{_base_name_395} ({_child_label})"
            _char.aliases = _child_als + _neutral_als
            _char.mention_count = max(1, _char.mention_count - _parent_char.mention_count)

            # Mutual alias decontamination: after split, neither character should carry
            # the OTHER character's canonical name as one of its aliases.
            # This prevents cross-contamination where e.g. the son carries "John (the father)"
            # and the father carries "John (the son)" as aliases.
            _child_canonical_395 = _char.canonical_name
            _char.aliases = [a for a in _char.aliases if a != _parent_canonical]
            _parent_char.aliases = [a for a in (_parent_char.aliases or []) if a != _child_canonical_395]

            # Re-search mentions for both split characters
            self._refresh_mentions({_char.id, _parent_char.id}, main_cast, searcher, mention_results)

        # STEP 3.95b: Summary-text parent attribution split.
        # Handles the case where STEP 3.95 alias contradiction didn't fire because the LLM
        # failed to assign parent-tier aliases to a merged character, but the chapter summaries
        # explicitly identify the character's full name as another person's named parent.
        # Universal invariant: if summary text contains "named {Name} ... his/her/their father/mother"
        # (or similar introducing-verb pattern), AND the character has non-parent role evidence
        # (neutral aliases), AND has substantial mentions (≥10), a false merge is present.
        # Example: "a stretcher-bearer named John Donaldson ... to realize he was his long-lost father"
        # → "John Donaldson" was extracted as one character combining father + son.
        import re as _re395b
        _summary_all_395b = " ".join(chapter_summaries) if chapter_summaries else ""

        if _summary_all_395b:
            for _char_395b in list(main_cast):
                # Only consider multi-word names not already split by STEP 3.95
                if " " not in _char_395b.canonical_name:
                    continue
                # Skip if already split (a _parent sibling exists) — avoids double-splitting
                if any(c.id == f"{_char_395b.id}_parent" for c in main_cast):
                    continue
                # Require substantial mentions (to avoid splitting minor named-parent characters)
                if (_char_395b.mention_count or 0) < 10:
                    continue
                # Require at least one neutral (non-parent) alias as evidence of non-parent role
                _neutral_als_395b = [
                    a for a in (_char_395b.aliases or [])
                    if _alias_tier_395(a) is None
                ]
                if not _neutral_als_395b:
                    continue
                # Search for parent attribution using multiple universal patterns.
                # Pattern A: "named/called/revealed to be {Name} ... his/her father/mother"
                #            — NAME is introduced as a named parent
                # Pattern B: "{Name} ... his/her (long-lost) son/daughter/child"
                #            — NAME is the parent who has a son/daughter
                # Pattern C: "{Name}'s (long-lost) son/daughter/child"
                #            — possessive: NAME owns/has a child
                # We search both the canonical name AND multi-word neutral aliases —
                # the LLM sometimes stores the parent's formal name as an alias of the merged
                # son character (e.g., "John (Uncle Bill's son)" with alias "John Donaldson"
                # where the summary names "John Donaldson" as the parent).
                _search_names_395b = [_char_395b.canonical_name] + [
                    a for a in _neutral_als_395b if " " in a
                ]
                _m_395b = None
                _matched_base_395b = _char_395b.canonical_name
                _strong_match_395b = False  # True if Pattern A, B, or E matched (strong false-merge evidence)
                for _sn_395b in _search_names_395b:
                    _sn_esc_395b = _re395b.escape(_sn_395b)
                    _sfn_395b = _sn_395b.split()[0]
                    # Pattern A: introducer + NAME + ... + his/her father/mother
                    _pat_A_395b = _re395b.compile(
                        r"(?i)"
                        r"(?:named|called|identified as|turned out to be|found to be"
                        r"|proved to be|revealed to be)\s+"
                        + _sn_esc_395b
                        + r"[^.!?\n]{0,300}"
                        r"(?:his|her|their)\s+(?:\w+\s+){0,3}(?:father|mother)\b"
                    )
                    # Pattern B: NAME + ... + reveal/confess + ... + his/her (long-lost) son/daughter
                    # Requires a REVELATION verb to avoid false positives on ordinary parent refs.
                    _pat_B_395b = _re395b.compile(
                        r"(?i)"
                        + _sn_esc_395b
                        + r"[^.!?\n]{0,400}"
                        r"(?:reveal|revealed|revealing|reveals|found\s+out|discover|identifies?|recognized|confesses?|admitted?|declares?)\s+"
                        r"(?:\w+\s+){0,6}"
                        r"(?:his|her|their)\s+(?:long[- ]lost\s+|estranged\s+|lost\s+)?(son|daughter|child)\b"
                    )
                    # Pattern C: NAME's (long-lost) son/daughter/child
                    _pat_C_395b = _re395b.compile(
                        r"(?i)"
                        + _sn_esc_395b
                        + r"[''']?s\s+(?:long[- ]lost\s+|estranged\s+|lost\s+)?(son|daughter|child)\b"
                    )
                    # Pattern D: {FirstName}'s (long-lost) father/mother/parent
                    _pat_D_395b = None
                    if len(_sfn_395b) >= 4:  # Guard: avoid matching short common words
                        _fn_esc_395b = _re395b.escape(_sfn_395b)
                        _pat_D_395b = _re395b.compile(
                            r"(?i)\b"
                            + _fn_esc_395b
                            + r"[''']?s\s+(?:long[- ]lost\s+|estranged\s+|absent\s+|lost\s+)?(?:father|mother|parent)\b"
                        )
                    # Pattern E: NAME...reveals/confesses...he/she is X's...father/mother
                    # Handles "NAME...reveals...he is John Jr.'s long-lost father" where the
                    # name before the apostrophe may contain titles with periods (e.g., "Jr.").
                    _pat_E_395b = _re395b.compile(
                        r"(?i)"
                        + _sn_esc_395b
                        + r"[^.!?\n]{0,400}"
                        r"(?:reveal|reveals|revealed|confess|confesses|confessed)\s+"
                        r"[^.!?\n]{0,100}"
                        r"(?:he|she)\s+(?:is|was)\s+"
                        r"[\w\s.]{0,30}[\u2018\u2019\u0027]s\s+"
                        r"(?:long.{0,6})?"
                        r"(?:father|mother|parent)\b"
                    )
                    # Strong patterns (A/B/E): revelation or introduction — high-confidence
                    # evidence the character was merged from distinct parent+child roles.
                    _strong_395b = (
                        _pat_A_395b.search(_summary_all_395b)
                        or _pat_B_395b.search(_summary_all_395b)
                        or _pat_E_395b.search(_summary_all_395b)
                    )
                    if _strong_395b:
                        _m_395b = _strong_395b
                        _matched_base_395b = _sn_395b
                        _strong_match_395b = True
                        break
                    # Weak patterns (C/D): possessive references — confirm the character IS
                    # a parent but do not prove a false merge without corroboration.
                    _weak_395b = (
                        _pat_C_395b.search(_summary_all_395b)
                        or (_pat_D_395b and _pat_D_395b.search(_summary_all_395b))
                    )
                    if _weak_395b and _m_395b is None:
                        _m_395b = _weak_395b
                        _matched_base_395b = _sn_395b
                        # Don't break — keep searching for a strong pattern

                if not _m_395b:
                    continue

                # Guard: possessive patterns (C/D) alone confirm the character IS a parent
                # but do NOT prove a false merge (the character may simply be a named parent).
                # Require child-tier aliases as corroboration before splitting.
                if not _strong_match_395b:
                    _child_guard_395b = [
                        a for a in (_char_395b.aliases or []) if _alias_tier_395(a) == "child"
                    ]
                    if not _child_guard_395b:
                        logger.debug(
                            f"V2 Step 3.95b: Skipping split for '{_char_395b.canonical_name}' — "
                            f"only weak possessive pattern (C/D) matched, no child-tier alias corroboration"
                        )
                        continue

                # Determine gender from matched text
                _matched_395b = _m_395b.group(0).lower()
                _parent_label_395b = "the mother" if "mother" in _matched_395b else "the father"
                _parent_canonical_395b = f"{_matched_base_395b} ({_parent_label_395b})"

                logger.info(
                    f"V2 Step 3.95b: Summary text names '{_matched_base_395b}' as a parent "
                    f"(via {'alias' if _matched_base_395b != _char_395b.canonical_name else 'canonical'} "
                    f"of '{_char_395b.canonical_name}'); "
                    f"creating split → '{_parent_canonical_395b}' (supporting)"
                )
                from ..models import ConfidenceLevel as _CL395b
                _parent_char_395b = Character(
                    id=f"{_char_395b.id}_parent",
                    canonical_name=_parent_canonical_395b,
                    role="supporting",
                    mention_count=2,
                    confidence=_CL395b.MEDIUM,
                    aliases=[],  # No aliases — avoids mention count overlap with the child character
                )
                main_cast.append(_parent_char_395b)
                # Adjust child's mention count downward to reflect removed parent mentions
                _char_395b.mention_count = max(1, (_char_395b.mention_count or 1) - 2)

        # STEP 3.95c: Kinship-fragment sibling-name split.
        # Handles the case where a merged parent+child character A (multi-word, high-mention)
        # produced a low-mention single-word fragment B that carries a child-tier alias
        # ("his son", "the boy", etc.) and whose name is a diminutive/prefix of A's first name.
        # Universal invariant: a child-tier alias on a fragment whose name maps to A's first name
        # (via STANDARD_DIMINUTIVES) is a structural signal — independent of LLM summary wording —
        # that A is a merged parent+child. This fills the gap when STEP 3.95/3.95b don't fire
        # due to LLM wording variation.
        # Example: "Johnny" (1 mention, alias="his son") + "John Donaldson" (33 mentions)
        #   → STANDARD_DIMINUTIVES["johnny"]="john" matches "John Donaldson"'s first word
        #   → Split: "John Donaldson (the father)" created; original becomes the child.
        for _frag_395c in list(main_cast):
            if " " in _frag_395c.canonical_name:
                continue  # Only single-word fragments qualify
            _frag_count_395c = (getattr(_frag_395c, "mention_count", 0) or 0)
            if _frag_count_395c > 3:
                continue  # Too many mentions — likely a real standalone character
            if len(_frag_395c.canonical_name) < 3:
                continue  # Too short to match reliably
            # B must have at least one child-tier alias
            _child_als_395c = [a for a in (_frag_395c.aliases or []) if _alias_tier_395(a) == "child"]
            if not _child_als_395c:
                continue
            # Map B's name to a canonical first name via STANDARD_DIMINUTIVES
            _b_lower_395c = _frag_395c.canonical_name.lower()
            _b_formal_395c = STANDARD_DIMINUTIVES.get(_b_lower_395c) or _b_lower_395c
            # Find exactly one multi-word character A where A's first word == B's formal name
            _candidates_395c = [
                c for c in main_cast
                if c.id != _frag_395c.id
                and " " in c.canonical_name
                and not c.id.endswith("_parent")  # skip already-split characters
                and c.canonical_name.lower().split()[0] == _b_formal_395c
                and (getattr(c, "mention_count", 0) or 0) >= max(_frag_count_395c * 10, 10)
            ]
            if len(_candidates_395c) != 1:
                continue
            _parent_cand_395c = _candidates_395c[0]
            # Skip if STEP 3.95/3.95b already split this character
            if any(c.id == f"{_parent_cand_395c.id}_parent" for c in main_cast):
                continue
            logger.info(
                f"V2 Step 3.95c: Fragment '{_frag_395c.canonical_name}' "
                f"(child-tier aliases={_child_als_395c}, {_frag_count_395c} mentions) "
                f"signals '{_parent_cand_395c.canonical_name}' is a merged parent+child; splitting"
            )
            from ..models import ConfidenceLevel as _CL395c
            _parent_canonical_395c = f"{_parent_cand_395c.canonical_name} (the father)"
            _parent_char_395c = Character(
                id=f"{_parent_cand_395c.id}_parent",
                canonical_name=_parent_canonical_395c,
                role="supporting",
                mention_count=2,
                confidence=_CL395c.MEDIUM,
                aliases=[],  # No aliases — avoids mention count overlap with the child character
            )
            main_cast.append(_parent_char_395c)
            # Original character keeps its id and name (represents the child/son)
            _parent_cand_395c.mention_count = max(1, (_parent_cand_395c.mention_count or 1) - 2)

        # STEP 3.97: Merge low-mention nickname phantoms into their formal-name counterparts.
        # Universal invariant: a single-word main cast character that is a known nickname
        # (via NICKNAME_TO_FORMAL) for the first name of a multi-word main cast character,
        # AND has very few text mentions relative to the formal (≤3 mentions, ≥10x asymmetry),
        # is almost certainly a phantom variant reference — not a distinct character.
        # Example: "Johnny" (2 mentions) + "John Donaldson" (43 mentions) → merge Johnny
        # as alias of John Donaldson.
        # Uniqueness guard: only merge when exactly ONE candidate formal exists.
        for _nick_char_397 in list(main_cast):
            if " " in _nick_char_397.canonical_name:
                continue  # Only single-word characters qualify as nickname phantoms
            # Use canonical-name-only mention count (not total_mentions which includes aliases).
            # After _deduplicate_alias_canonical_conflicts strips cross-character aliases,
            # char.mention_count may still reflect the inflated total from grounding time
            # (e.g., "Johnny" had alias "John Donaldson" → total=30, not 2).
            # Using mentions_by_alias[canonical_name] gives the TRUE canonical-name count.
            _m_result_397 = mention_results.get(_nick_char_397.id)
            _nick_count_397 = (
                _m_result_397.mentions_by_alias.get(_nick_char_397.canonical_name, 0)
                if _m_result_397 and hasattr(_m_result_397, "mentions_by_alias") and _m_result_397.mentions_by_alias
                else (getattr(_nick_char_397, "mention_count", 0) or 0)
            )
            if _nick_count_397 > 3:
                continue  # Too many mentions — likely a real character
            _nick_lower_397 = _nick_char_397.canonical_name.lower()
            _formal_first_397 = NICKNAME_TO_FORMAL.get(_nick_lower_397) or STANDARD_DIMINUTIVES.get(_nick_lower_397)
            if not _formal_first_397:
                continue  # Not a known nickname
            _candidates_397 = [
                c for c in main_cast
                if c.id != _nick_char_397.id
                and " " in c.canonical_name
                and not c.id.endswith("_parent")  # exclude STEP 3.95/3.95b split annotations
                and c.canonical_name.lower().split()[0] == _formal_first_397
                and (getattr(c, "mention_count", 0) or 0) >= max(_nick_count_397 * 5, 5)
            ]
            if len(_candidates_397) != 1:
                continue  # Ambiguous or no match — skip
            _formal_char_397 = _candidates_397[0]
            logger.info(
                f"V2 Step 3.97: Merging nickname phantom '{_nick_char_397.canonical_name}' "
                f"({_nick_count_397} mentions) as alias of '{_formal_char_397.canonical_name}' "
                f"({getattr(_formal_char_397, 'mention_count', 0)} mentions) via NICKNAME_TO_FORMAL"
            )
            if _nick_char_397.canonical_name not in _formal_char_397.aliases:
                _formal_char_397.aliases.append(_nick_char_397.canonical_name)
            for _alias_397 in _nick_char_397.aliases:
                if _alias_397 not in _formal_char_397.aliases:
                    _formal_char_397.aliases.append(_alias_397)
            main_cast.remove(_nick_char_397)

        # STEP 4: Detect narrator (F4)
        logger.info("V2 Step 4: Detecting narrator")
        narrator_detector = NarratorDetector(self.llm)
        narrator_info = narrator_detector.detect(chapter_summaries, main_cast, plot_summary)
        main_cast = narrator_detector.update_characters_with_narrator(main_cast, narrator_info)

        logger.info(
            f"V2 Step 4 complete: POV={narrator_info.pov}, "
            f"narrator={narrator_info.narrator_name}"
        )

        # STEP 4.24: Self-identification scan.
        # Universal invariant: if the raw text contains an explicit first-person
        # self-identification ("I am {Name}", "I'm {Name}", "my name is {Name}"),
        # that character IS the narrator — this is stronger evidence than the LLM result.
        # Only fires for first-person narratives when the source text is available.
        import re as _re424
        if narrator_info.pov == "first-person" and context.text:
            _self_id_patterns = [
                r"\bI\s+am\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
                r"\bI'm\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
                r"\bmy\s+name\s+is\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
            ]
            _self_id_name: Optional[str] = None
            for _pat in _self_id_patterns:
                _m = _re424.search(_pat, context.text)
                if _m:
                    _self_id_name = _m.group(1)
                    break
            if _self_id_name:
                _self_id_lower = _self_id_name.lower()
                _self_id_match = next(
                    (c for c in main_cast
                     if c.canonical_name.lower() == _self_id_lower
                     or _self_id_lower in c.canonical_name.lower()
                     or any(_self_id_lower == a.lower() for a in (c.aliases or []))),
                    None,
                )
                if _self_id_match and _self_id_match.id != narrator_info.narrator_character_id:
                    logger.info(
                        f"V2 Step 4.24: Self-identification '{_self_id_name}' found in text — "
                        f"overriding narrator from '{narrator_info.narrator_name}' "
                        f"to '{_self_id_match.canonical_name}'"
                    )
                    # Clear old narrator flag
                    for _c424 in main_cast:
                        if _c424.is_narrator:
                            _c424.is_narrator = False
                            _c424.narrative_role = None
                    narrator_info = NarratorInfo(
                        pov="first-person",
                        narrator_character_id=_self_id_match.id,
                        narrator_name=_self_id_match.canonical_name,
                        confidence=0.95,
                    )
                    main_cast = narrator_detector.update_characters_with_narrator(main_cast, narrator_info)
                elif _self_id_match:
                    logger.info(
                        f"V2 Step 4.24: Self-identification '{_self_id_name}' confirms "
                        f"narrator '{narrator_info.narrator_name}' — no change needed"
                    )
                else:
                    logger.info(
                        f"V2 Step 4.24: Self-identification '{_self_id_name}' found but "
                        f"no matching character in main_cast — updating narrator_name for "
                        f"downstream steps (supporting_cast not yet populated)"
                    )
                    # Update narrator_name so STEP 5.8.4b can find the character in
                    # supporting_cast once it is populated (STEP 5 runs later).
                    narrator_info = NarratorInfo(
                        pov=narrator_info.pov if narrator_info.pov not in ("unknown", "") else "first-person",
                        narrator_name=_self_id_name,
                        narrator_character_id=narrator_info.narrator_character_id,
                        confidence=max(narrator_info.confidence, 0.9),
                    )
        logger.info("V2 Step 4.24 complete: self-identification scan done")

        # STEP 4.25: Vocative-based narrator correction.
        # Universal invariant: in first-person narratives the narrator uses "I" and has
        # anomalously LOW name-mention count. If the LLM was forced to pick from a single
        # main-cast character who actually has HIGH mentions (the non-narrator), the
        # assignment is likely wrong. Search raw text for vocative patterns ("Name!")
        # to find who is actually being addressed as the narrator.
        #
        # Example: Cask of Amontillado — main_cast=[Fortunato(14 mentions)]; LLM assigns
        # Fortunato as narrator. Vocative search finds "Montresor" (3 mentions) from
        # "For the love of God, Montresor!" → Montresor is the actual narrator.
        import re as _re45
        if narrator_info.pov == "first-person" and narrator_info.narrator_character_id is not None:
            narrator_char_425 = next(
                (c for c in main_cast if c.id == narrator_info.narrator_character_id), None
            )
            if narrator_char_425 is not None:
                narrator_count_425 = getattr(narrator_char_425, "mention_count", 0) or 0
                other_mention_counts_425 = [
                    getattr(c, "mention_count", 0) or 0
                    for c in main_cast
                    if c.id != narrator_char_425.id
                ]
                # Suspicious if narrator has MORE mentions than all others, or is the only
                # main-cast character (no comparison possible, forced false choice)
                narrator_suspiciously_high = (
                    narrator_count_425 > 0
                    and (
                        not other_mention_counts_425
                        or narrator_count_425 > max(other_mention_counts_425, default=0)
                    )
                )
                if narrator_suspiciously_high:
                    vocative_name_425 = self._find_narrator_name_from_vocative(context.text)
                    if (
                        vocative_name_425
                        and vocative_name_425.lower() != narrator_char_425.canonical_name.lower()
                    ):
                        voc_count_425 = len(
                            _re45.findall(
                                rf"(?<![A-Za-z0-9]){_re45.escape(vocative_name_425)}(?![A-Za-z0-9])",
                                context.text,
                                _re45.IGNORECASE,
                            )
                        )
                        if voc_count_425 < narrator_count_425:
                            # Vocative name has fewer mentions → it's the actual narrator
                            logger.info(
                                f"V2 Step 4.25: Narrator correction — '{narrator_char_425.canonical_name}' "
                                f"({narrator_count_425} mentions) seems wrong; vocative pattern "
                                f"suggests '{vocative_name_425}' ({voc_count_425} mentions) "
                                f"is the actual narrator. Resetting narrator assignment."
                            )
                            narrator_char_425.is_narrator = False
                            narrator_char_425.narrative_role = None
                            narrator_info = NarratorInfo(
                                pov="first-person",
                                narrator_name=vocative_name_425,
                                narrator_character_id=None,
                                confidence=0.75,
                            )
                else:
                    # STEP 4.25b: also correct when the narrator name never appears in any
                    # vocative (direct-address) pattern, but another name does with fewer
                    # total text mentions. Universal invariant: in a first-person story the
                    # actual narrator IS occasionally addressed by name; if the assigned
                    # narrator name never appears in direct-address context (", Name!" /
                    # ", Name,") but a vocative candidate does and has fewer total mentions,
                    # the assignment is wrong. Safeguard: narrator_voc_count == 0 prevents
                    # false corrections when the narrator IS addressed but less than others.
                    vocative_name_425 = self._find_narrator_name_from_vocative(context.text)
                    if (
                        vocative_name_425
                        and vocative_name_425.lower() != narrator_char_425.canonical_name.lower()
                    ):
                        _narrator_voc_count = len(
                            _re45.findall(
                                rf"[,!]\s+{_re45.escape(narrator_char_425.canonical_name)}"
                                rf"(?:\s+[A-Z][a-zA-Z]{{2,}})?\s*[!?,]",
                                context.text,
                                _re45.IGNORECASE,
                            )
                        )
                        if _narrator_voc_count == 0:
                            voc_count_425 = len(
                                _re45.findall(
                                    rf"(?<![A-Za-z0-9]){_re45.escape(vocative_name_425)}(?![A-Za-z0-9])",
                                    context.text,
                                    _re45.IGNORECASE,
                                )
                            )
                            if voc_count_425 < narrator_count_425:
                                logger.info(
                                    f"V2 Step 4.25b: Narrator correction — "
                                    f"'{narrator_char_425.canonical_name}' never directly addressed "
                                    f"(0 vocative occurrences); vocative pattern suggests "
                                    f"'{vocative_name_425}' ({voc_count_425} mentions < "
                                    f"{narrator_count_425}). Resetting narrator assignment."
                                )
                                narrator_char_425.is_narrator = False
                                narrator_char_425.narrative_role = None
                                narrator_info = NarratorInfo(
                                    pov="first-person",
                                    narrator_name=vocative_name_425,
                                    narrator_character_id=None,
                                    confidence=0.75,
                                )
        logger.info("V2 Step 4.25 complete: vocative narrator correction check done")

        # STEP 4.26: Low-mention narrator guard.
        # Universal invariant: a first-person narrator is PRESENT throughout the story;
        # they cannot have ≤ 2 explicit name mentions while another character has ≥ 5x
        # more. This pattern indicates the inner narrator of a nested/frame narrative was
        # mistakenly selected over the outer frame narrator (who is addressed by name far
        # more often). Reset narrator assignment so Step 5.8.5 can retry with the
        # improved prompt guidance about inner vs outer narrators.
        import re as _re426
        if (
            narrator_info.pov in ("first-person", "epistolary")
            and narrator_info.narrator_character_id is not None
        ):
            _narrator_char_426 = next(
                (c for c in main_cast if c.id == narrator_info.narrator_character_id), None
            )
            if _narrator_char_426 is not None:
                _narrator_count_426 = getattr(_narrator_char_426, "mention_count", 0) or 0
                _max_other_426 = max(
                    (getattr(c, "mention_count", 0) or 0 for c in main_cast if c.id != _narrator_char_426.id),
                    default=0,
                )
                if 0 < _narrator_count_426 <= 5 and _max_other_426 >= _narrator_count_426 * 5:
                    logger.warning(
                        f"V2 Step 4.26: Narrator '{_narrator_char_426.canonical_name}' "
                        f"has only {_narrator_count_426} mention(s) but another character "
                        f"has {_max_other_426}. Resetting narrator — Step 5.8.5 will retry."
                    )
                    _narrator_char_426.is_narrator = False
                    _narrator_char_426.narrative_role = None
                    narrator_info = NarratorInfo(
                        pov=narrator_info.pov,
                        narrator_character_id=None,
                        narrator_name=None,
                        confidence=0.3,
                    )
        logger.info("V2 Step 4.26 complete: low-mention narrator guard done")

        # STEP 4.27: Mention-ratio narrator validation.
        # Universal invariant: in first-person narration the narrator refers to themselves
        # as "I", so their proper name appears rarely relative to other named characters.
        # If the assigned narrator has ≥15 name-mentions and another main-cast character
        # has ≤7 mentions with a ≥3x discrepancy, the low-mention character is more likely
        # the actual narrator. This catches LLM non-determinism where a high-mention
        # character is wrongly assigned as narrator despite the classic low-mention pattern.
        import re as _re427
        if (
            narrator_info.pov == "first-person"
            and narrator_info.narrator_character_id is not None
        ):
            _narrator_char_427 = next(
                (c for c in main_cast if c.id == narrator_info.narrator_character_id), None
            )
            if _narrator_char_427 is not None:
                _narrator_count_427 = getattr(_narrator_char_427, "mention_count", 0) or 0
                _other_427 = [
                    (c, getattr(c, "mention_count", 0) or 0)
                    for c in main_cast
                    if c.id != _narrator_char_427.id
                ]
                if _other_427:
                    _min_char_427, _min_count_427 = min(_other_427, key=lambda x: x[1])
                    if (
                        _narrator_count_427 >= 15
                        and 0 < _min_count_427 <= 7
                        and _narrator_count_427 >= 3 * _min_count_427
                    ):
                        _min_raw_count_427 = len(
                            _re427.findall(
                                rf"(?<![A-Za-z0-9]){_re427.escape(_min_char_427.canonical_name)}(?![A-Za-z0-9])",
                                context.text,
                                _re427.IGNORECASE,
                            )
                        )
                        if _min_raw_count_427 > 0:
                            logger.info(
                                f"V2 Step 4.27: Mention-ratio narrator correction — "
                                f"'{_narrator_char_427.canonical_name}' ({_narrator_count_427} mentions) "
                                f"has ≥3x mentions of '{_min_char_427.canonical_name}' ({_min_count_427}); "
                                f"low-mention character likely the actual narrator. Reassigning."
                            )
                            _narrator_char_427.is_narrator = False
                            _narrator_char_427.narrative_role = None
                            _min_char_427.is_narrator = True
                            narrator_info = NarratorInfo(
                                pov="first-person",
                                narrator_name=_min_char_427.canonical_name,
                                narrator_character_id=_min_char_427.id,
                                confidence=0.7,
                            )
        logger.info("V2 Step 4.27 complete: mention-ratio narrator validation done")

        # STEP 4.5: Resolve narrator name from raw text vocative patterns
        # For first-person narratives where the narrator is a placeholder ("the narrator"),
        # the LLM may generate summaries that never name the narrator explicitly. Search
        # the raw text for direct address patterns (e.g., "For the love of God, Montresor!")
        # that reveal the narrator's actual name, and add it as an alias so that Step 5.2b
        # can upgrade the placeholder canonical name to the proper name.
        _narrator_placeholder_terms_45 = [
            "the protagonist", "the narrator", "narrator", "protagonist",
            "main character", "the main character",
        ]
        if narrator_info.pov == "first-person":
            for char in main_cast:
                if not any(p in char.canonical_name.lower() for p in _narrator_placeholder_terms_45):
                    continue
                # Skip if narrator already has a proper-name alias (no upgrade needed)
                has_proper_alias = any(
                    any(t[0].isupper() for t in a.split() if len(t) >= 2)
                    and not any(p in a.lower() for p in _narrator_placeholder_terms_45)
                    for a in char.aliases
                )
                if has_proper_alias:
                    break
                # Search raw text for vocative patterns to find narrator's name
                narrator_real_name = self._find_narrator_name_from_vocative(context.text)
                if narrator_real_name:
                    logger.info(
                        f"V2 Step 4.5: Found narrator name '{narrator_real_name}' "
                        f"from vocative pattern in raw text; adding as alias to "
                        f"'{char.canonical_name}'"
                    )
                    if narrator_real_name not in char.aliases:
                        char.aliases.append(narrator_real_name)
                else:
                    logger.info(
                        f"V2 Step 4.5: No vocative narrator name found in raw text "
                        f"for placeholder '{char.canonical_name}'"
                    )
                break  # Only process first narrator placeholder

        # STEP 4.5b: Vocative-based narrator name discovery for fully unidentified narrators.
        # When the narrative is first-person but narrator detection returned no name and no
        # character ID (i.e., the narrator is "the unnamed narrator" in summaries), search
        # the raw text for direct address patterns. The narrator's name appears rarely as text
        # mentions (they write "I"), so the name with the FEWEST total mentions among vocative
        # candidates is the narrator. Setting narrator_name here allows STEP 5.8.5b to
        # find the narrator in supporting_cast and promote them.
        # Also fires when narrator_name is a generic placeholder (e.g., "the narrator") — these
        # are never real character names, so the vocative search should always be tried.
        _generic_narrator_45b = {
            "the narrator", "narrator", "the protagonist", "protagonist",
            "the main character", "main character", "unknown", "the unknown",
        }
        if (
            narrator_info.pov == "first-person"
            and narrator_info.narrator_character_id is None
            and (
                narrator_info.narrator_name is None
                or narrator_info.narrator_name.lower() in _generic_narrator_45b
            )
        ):
            _voc_name_45b = self._find_narrator_name_from_vocative(context.text)
            if _voc_name_45b:
                narrator_info = NarratorInfo(
                    pov="first-person",
                    narrator_name=_voc_name_45b,
                    narrator_character_id=None,
                    confidence=0.55,
                )
                logger.info(
                    f"V2 Step 4.5b: Vocative-detected narrator candidate '{_voc_name_45b}' "
                    f"(narrator_character_id not yet resolved — will search supporting cast)"
                )

        logger.info("V2 Step 4.5 complete: narrator vocative name check done")

        # STEP 5: Extract supporting cast (F3)
        logger.info("V2 Step 5: Extracting supporting cast via NER")
        main_cast_names = self._collect_all_names(main_cast)
        # Adaptive threshold: short texts (< 10K words) need a lower threshold since
        # characters with only 2 text mentions may still be significant
        text_word_count = len(context.text.split())
        supporting_min_mentions = 2 if text_word_count < 10000 else 3
        logger.info(
            f"V2 Step 5: text_word_count={text_word_count}, "
            f"supporting_min_mentions={supporting_min_mentions}"
        )
        supporting_extractor = SupportingCastExtractor(
            context.text,
            min_mentions=supporting_min_mentions,
        )
        supporting_cast = supporting_extractor.extract(main_cast_names)

        logger.info(f"V2 Step 5 complete: {len(supporting_cast)} supporting characters")

        # STEP 5.1: Filter narrator-related entries from supporting cast
        # Handles cases where NER picks up "narrator", "the narrator", etc.
        supporting_cast = self._filter_narrator_variants(
            supporting_cast, narrator_info.narrator_name
        )
        logger.info(
            f"V2 Step 5.1 complete: {len(supporting_cast)} supporting after narrator filter"
        )

        # STEP 5.2: Also filter narrator variants from main cast (defensive)
        # In case the LLM extracted "Narrator" as a main character.
        # NOTE: Narrator placeholders that have been properly identified via
        # proper-name aliases (e.g., "The narrator" → alias "Victor Frankenstein")
        # are kept and their canonical name is upgraded below.
        original_main_count = len(main_cast)
        main_cast = self._filter_narrator_variants(
            main_cast, narrator_info.narrator_name, is_main_cast=True
        )
        if len(main_cast) < original_main_count:
            logger.info(
                f"V2 Step 5.2: Filtered {original_main_count - len(main_cast)} narrator "
                f"variant(s) from main cast"
            )

        # STEP 5.2b: Upgrade narrator placeholder canonical names to their fullest
        # proper-name alias. E.g., "The narrator" (alias: "Victor Frankenstein")
        # → canonical_name becomes "Victor Frankenstein" so that last-name merging
        # in Step 5.5 can correctly merge supporting cast fragments like "Victor"
        # and "Frankenstein" into this character.
        _narrator_placeholder_terms = [
            "the protagonist", "the narrator", "narrator", "protagonist",
            "main character", "the main character",
        ]
        _52b_chars_to_remove: list = []
        for char in main_cast:
            if not any(p in char.canonical_name.lower() for p in _narrator_placeholder_terms):
                continue
            # Find proper-name aliases (capitalized, not a placeholder)
            proper_aliases = [
                a for a in char.aliases
                if any(t[0].isupper() for t in a.split() if len(t) >= 2)
                and not any(p in a.lower() for p in _narrator_placeholder_terms)
            ]
            if not proper_aliases:
                continue
            # Choose the fullest (most tokens) proper-name alias as new canonical
            new_canonical = max(proper_aliases, key=lambda a: len(a.split()))
            old_canonical = char.canonical_name
            # Check if the new canonical name already exists in main_cast.
            # This happens when the LLM extracted both "Ted" (main_cast_5) and
            # "the narrator" (main_cast_7, with alias "Ted" from vocative detection).
            # In that case, merge the placeholder into the existing character instead
            # of renaming — renaming would create a duplicate caught only after STEP 3.5.
            _existing_52b = next(
                (c for c in main_cast if c is not char and c.canonical_name.lower() == new_canonical.lower()),
                None,
            )
            if _existing_52b is not None:
                # Merge placeholder into existing: transfer aliases (placeholder name + its aliases)
                for _alias_52b in ([old_canonical] + list(char.aliases or [])):
                    if _alias_52b.lower() != _existing_52b.canonical_name.lower() and _alias_52b not in _existing_52b.aliases:
                        _existing_52b.aliases.append(_alias_52b)
                # Transfer narrator attributes if placeholder has them
                if char.is_narrator and not _existing_52b.is_narrator:
                    _existing_52b.is_narrator = True
                    _existing_52b.narrative_role = char.narrative_role or _existing_52b.narrative_role
                # Update narrator_info if it pointed to the placeholder
                if narrator_info.narrator_character_id == char.id:
                    from ..pipeline.character_extraction_v2.narrator import NarratorInfo as _NI52b
                    narrator_info = _NI52b(
                        pov=narrator_info.pov,
                        narrator_name=narrator_info.narrator_name,
                        narrator_character_id=_existing_52b.id,
                        confidence=narrator_info.confidence,
                    )
                _52b_chars_to_remove.append(char)
                logger.info(
                    f"V2 Step 5.2b: Placeholder '{old_canonical}' → merged into existing "
                    f"'{_existing_52b.canonical_name}' (id={_existing_52b.id}); "
                    f"placeholder removed to prevent duplicate"
                )
            else:
                # Normal rename: no conflict, just upgrade the canonical name
                char.aliases = [a for a in char.aliases if a != new_canonical]
                if old_canonical not in char.aliases:
                    char.aliases.append(old_canonical)
                char.canonical_name = new_canonical
                logger.info(
                    f"V2 Step 5.2b: Upgraded narrator placeholder "
                    f"'{old_canonical}' → '{new_canonical}' "
                    f"(aliases: {char.aliases})"
                )
        if _52b_chars_to_remove:
            main_cast = [c for c in main_cast if c not in _52b_chars_to_remove]
            logger.info(
                f"V2 Step 5.2b: Removed {len(_52b_chars_to_remove)} placeholder duplicate(s) from main cast"
            )

        # STEP 5.2bb: Upgrade pure-kinship canonical names to their proper-name alias.
        # Universal invariant: if a character's canonical name is a bare kinship/role term
        # (father, mother, sister, etc.) but they have a proper-name alias, the proper name
        # is more informative and should be the canonical. This prevents "father" from being
        # the canonical for "Alphonse Frankenstein" or "mother" for named characters.
        _KINSHIP_ROLE_TERMS_52bb = {
            "father", "mother", "brother", "sister", "son", "daughter",
            "grandfather", "grandmother", "uncle", "aunt", "cousin",
            "husband", "wife", "stepfather", "stepmother", "guardian",
        }
        for char in main_cast:
            name_lower = char.canonical_name.strip().lower()
            # Remove possessive prefixes: "his father" → "father", "the father" → "father"
            for _prep in ("his ", "her ", "their ", "my ", "the ", "a "):
                if name_lower.startswith(_prep):
                    name_lower = name_lower[len(_prep):]
            if name_lower not in _KINSHIP_ROLE_TERMS_52bb:
                continue
            # Find proper-name aliases (capitalized word, not a kinship/relational term)
            proper_aliases_52bb = [
                a for a in (char.aliases or [])
                if any(t[0].isupper() for t in a.split() if len(t) >= 2)
                and a.strip().lower().rstrip("s") not in _KINSHIP_ROLE_TERMS_52bb
                and not a.startswith("his ")
                and not a.startswith("her ")
            ]
            if not proper_aliases_52bb:
                continue
            # Choose fullest (most words) proper-name alias
            new_canonical_52bb = max(proper_aliases_52bb, key=lambda a: len(a.split()))
            old_canonical_52bb = char.canonical_name
            char.canonical_name = new_canonical_52bb
            # Move old canonical + relational aliases to aliases list
            if old_canonical_52bb not in char.aliases:
                char.aliases.append(old_canonical_52bb)
            # Remove new canonical from aliases to avoid duplication
            char.aliases = [a for a in char.aliases if a.lower() != new_canonical_52bb.lower()]
            logger.info(
                f"V2 Step 5.2bb: Upgraded kinship canonical "
                f"'{old_canonical_52bb}' → '{new_canonical_52bb}' "
                f"(aliases: {char.aliases})"
            )

        # STEP 5.2c: Re-search mentions for narrator-placeholder-upgraded characters.
        # Step 5.2b may have changed a placeholder's canonical_name (e.g., "the narrator"
        # → "Montresor"). The initial mention search used the placeholder name and found
        # 0 text matches. Re-search using the new proper canonical name.
        _upgraded_narrator_ids: set[str] = set()
        for char in main_cast:
            # Detect upgrade: aliases contain a placeholder term (proof Step 5.2b ran)
            # and mention_count is 0 (placeholder name had no raw-text matches).
            if char.mention_count == 0 and any(
                p in a.lower()
                for a in char.aliases
                for p in _narrator_placeholder_terms
            ):
                _upgraded_narrator_ids.add(char.id)
        if _upgraded_narrator_ids:
            logger.info(
                f"V2 Step 5.2c: Re-searching mentions for {len(_upgraded_narrator_ids)} "
                f"narrator-placeholder-upgraded character(s)"
            )
            self._refresh_mentions(_upgraded_narrator_ids, main_cast, searcher, mention_results)

        # STEP 5.3: Merge narrator placeholders with their actual named character
        # If the narrator is "the protagonist", "the narrator", etc., find their real name
        main_cast, supporting_cast, narrator_info, narrator_merged_ids = (
            self._merge_narrator_placeholder(
                main_cast, supporting_cast, narrator_info, context.text
            )
        )
        logger.info("V2 Step 5.3 complete: narrator placeholder merge check done")

        # STEP 5.4: Re-search mentions for narrator-merged characters
        # The merge added the placeholder name as an alias, so we need to re-search
        # to capture all mentions (both the original name and the placeholder)
        if narrator_merged_ids:
            logger.info(
                f"Re-searching mentions for {len(narrator_merged_ids)} narrator-merged characters"
            )
            self._refresh_mentions(narrator_merged_ids, main_cast, searcher, mention_results)

        # STEP 5.4.5: Summary-crossref merge — consolidate single-word cast fragments into
        # multi-word names listed in the summary [Characters present: ...] prefixes.
        # Handles the case where LLM extraction produced "Milton" + "Jennings" separately
        # instead of "Milton Jennings" as a unit. The summary provides the authoritative name.
        logger.info("V2 Step 5.4.5: Merging cast fragments per summary character lists")
        main_cast, supporting_cast, crossref_merged_ids = self._merge_summary_name_fragments(
            chapter_summaries, main_cast, supporting_cast
        )
        if crossref_merged_ids:
            logger.info(
                f"V2 Step 5.4.5: Re-searching mentions for {len(crossref_merged_ids)} "
                f"summary-merged character(s)"
            )
            self._refresh_mentions(crossref_merged_ids, main_cast, searcher, mention_results)
        logger.info(
            f"V2 Step 5.4.5 complete: {len(main_cast)} main cast, "
            f"{len(supporting_cast)} supporting after summary-crossref merge"
        )

        # STEP 5.4.6: Possessive-descriptor + named-variant merge.
        # Universal pattern: "X's Son/Daughter/etc" and a separate named character Y
        # sometimes coexist when the same person is extracted twice — once by their role
        # descriptor and once by their proper name (a nickname/variant of X).
        # Example: "John's Son" (14 mentions) + "Johnny" (2 mentions) where "john" is
        # in NICKNAME_TO_FORMAL (johnny→john) AND another character has "John" as alias.
        # Rule: if Y's formal name (via NICKNAME_TO_FORMAL) == X (the parent name)
        #       AND Y is a short single-word name (≤ len(X)+3 chars)
        #       AND Y.mentions ≤ A.mentions * 0.5
        #       → merge Y into A (Y becomes alias of A)
        import re as _re546
        _POSSESSIVE_ROLES_546 = {"son", "daughter", "child", "boy", "girl", "nephew", "niece"}
        _chars_to_remove_546: list = []
        for _char_a_546 in main_cast:
            _m546 = _re546.match(
                r"^([A-Za-z]+)'s\s+(" + "|".join(_POSSESSIVE_ROLES_546) + r")$",
                _char_a_546.canonical_name,
                _re546.IGNORECASE,
            )
            if not _m546:
                continue
            _parent_name_546 = _m546.group(1).lower()  # e.g., "john"
            # Find parent character (has this name as canonical or alias)
            _parent_char_546 = next(
                (
                    p for p in main_cast
                    if p.id != _char_a_546.id
                    and (
                        p.canonical_name.lower() == _parent_name_546
                        or _parent_name_546 in [a.lower() for a in getattr(p, "aliases", [])]
                    )
                ),
                None,
            )
            if _parent_char_546 is None:
                continue
            # Look for character B: a short single-word name whose formal form == parent_name
            for _char_b_546 in main_cast:
                if (
                    _char_b_546.id in (_char_a_546.id, _parent_char_546.id)
                    or _char_b_546 in _chars_to_remove_546
                ):
                    continue
                _b_lower_546 = _char_b_546.canonical_name.lower()
                # Must be a single-word name (no spaces) and short
                if " " in _b_lower_546:
                    continue
                if len(_b_lower_546) > len(_parent_name_546) + 3:
                    continue
                # B's name must be a diminutive/nickname for parent_name.
                # Check both STANDARD_DIMINUTIVES and NICKNAME_TO_FORMAL.
                _formal_b_546 = (
                    STANDARD_DIMINUTIVES.get(_b_lower_546)
                    or NICKNAME_TO_FORMAL.get(_b_lower_546)
                    or _b_lower_546
                )
                if _formal_b_546 != _parent_name_546:
                    continue
                # B must have significantly fewer mentions than A
                _b_count_546 = getattr(_char_b_546, "mention_count", 0) or 0
                _a_count_546 = getattr(_char_a_546, "mention_count", 0) or 0
                if _a_count_546 > 0 and _b_count_546 > _a_count_546 * 0.5:
                    continue
                # Merge A (possessive descriptor) into B (proper name).
                # B is the canonical identity — "Johnny" is the character's name.
                # A ("John's Son") is a descriptor reference that should become an alias.
                logger.info(
                    f"V2 Step 5.4.6: Merging descriptor '{_char_a_546.canonical_name}' "
                    f"({_a_count_546} mentions) into proper-name '{_char_b_546.canonical_name}' "
                    f"({_b_count_546} mentions) — possessive-descriptor absorbed into canonical"
                )
                if _char_a_546.canonical_name not in _char_b_546.aliases:
                    _char_b_546.aliases.append(_char_a_546.canonical_name)
                for _alias_a_546 in getattr(_char_a_546, "aliases", []):
                    if _alias_a_546 not in _char_b_546.aliases:
                        _char_b_546.aliases.append(_alias_a_546)
                _char_b_546.mention_count = _a_count_546 + _b_count_546
                _chars_to_remove_546.append(_char_a_546)
                break  # Only one merge per descriptor character
        if _chars_to_remove_546:
            main_cast = [c for c in main_cast if c not in _chars_to_remove_546]
            logger.info(
                f"V2 Step 5.4.6: Removed {len(_chars_to_remove_546)} merged variant(s)"
            )
        logger.info(
            f"V2 Step 5.4.6 complete: {len(main_cast)} main cast after possessive-descriptor merge"
        )

        # STEP 5.4.6b: Normalize remaining "X's [role]" canonical names to "[X] [Last] (the [role])".
        # When step 5.4.6 doesn't merge a possessive-descriptor character (e.g., no matching nickname),
        # the character retains a form like "John's son" which is ambiguous — it reads as a possessive
        # reference, not as a proper disambiguated name. Rename to "[First] [Last] (the [role])" so it
        # parallels the parent's "Sr." form and is unambiguous (e.g., "John's son" → "John Donaldson
        # (the son)" when the parent is "John Donaldson Sr.").
        # Universal: applies to any book where a parent+child share names and both appear as characters.
        for _char_466b in main_cast:
            _m466b = _re546.match(
                r"^([A-Za-z]+)'s\s+(" + "|".join(_POSSESSIVE_ROLES_546) + r")$",
                _char_466b.canonical_name,
                _re546.IGNORECASE,
            )
            if not _m466b:
                continue
            _parent_first_466b = _m466b.group(1)  # e.g., "John"
            _role_466b = _m466b.group(2).lower()   # e.g., "son"
            # Find parent character: canonical starts with the same first name and has a last name
            _parent_466b = next(
                (
                    p for p in main_cast
                    if p.id != _char_466b.id
                    and p.canonical_name.lower().startswith(_parent_first_466b.lower() + " ")
                    and len(p.canonical_name.split()) >= 2
                ),
                None,
            )
            if _parent_466b is None:
                continue
            # Extract last name from parent canonical (strip parenthetical and honorific suffixes)
            _parent_base_466b = _parent_466b.canonical_name.split(" (")[0]  # strip parenthetical
            _parent_words_466b = _parent_base_466b.split()
            _HONORIFIC_SUFFIXES = {"sr.", "jr.", "sr", "jr", "ii", "iii", "iv"}
            _parent_last_466b = None
            for _w in reversed(_parent_words_466b):
                if _w.lower() not in _HONORIFIC_SUFFIXES and _w.lower() != _parent_first_466b.lower():
                    _parent_last_466b = _w
                    break
            if _parent_last_466b is None:
                continue
            _new_canonical_466b = f"{_parent_first_466b} {_parent_last_466b} (the {_role_466b})"
            logger.info(
                f"V2 Step 5.4.6b: Renaming '{_char_466b.canonical_name}' → '{_new_canonical_466b}' "
                f"(possessive-form → parenthetical disambiguation)"
            )
            _char_466b.canonical_name = _new_canonical_466b

        # STEP 5.4.6c: Merge descriptor characters with parent kinship aliases into proper-name
        # parent characters when a parent-child name split exists.
        # Universal pattern: In stories where a parent and child share a name (e.g. "John Donaldson"
        # and "John Donaldson (the son)"), the parent may appear twice — once as their proper name
        # and once as a descriptor in a narrative reveal (e.g., "Shabby American civilian" with
        # alias "his father"). These two extractions are the SAME person.
        # Detection: descriptor character D has a parent kinship alias ("his father", "the father")
        # AND there is a named "(the son)"/"(the daughter)" character S AND a proper-name parent P
        # whose name matches S's base name → merge D into P.
        import re as _re466c
        _KINSHIP_ALIAS_466c = _re466c.compile(
            r"^(his|her|the|their)\s+(father|mother|parent|dad|mum|mom|papa|mamma)$",
            _re466c.IGNORECASE,
        )
        _SON_DAUGHTER_466c = _re466c.compile(
            r"\s*\(the\s+(son|daughter|child|boy|girl)\)\s*$",
            _re466c.IGNORECASE,
        )
        _chars_to_remove_466c: list = []
        for _desc_466c in main_cast:
            if _desc_466c in _chars_to_remove_466c:
                continue
            # Must have a parent kinship alias
            _kinship_466c = next(
                (a for a in getattr(_desc_466c, "aliases", []) if _KINSHIP_ALIAS_466c.match(a)),
                None,
            )
            if not _kinship_466c:
                continue
            # Find a "(the son)"/"(the daughter)" character in main cast
            _son_chars_466c = [
                c for c in main_cast
                if c.id != _desc_466c.id
                and _SON_DAUGHTER_466c.search(c.canonical_name)
            ]
            if not _son_chars_466c:
                continue
            for _son_466c in _son_chars_466c:
                # Derive the base name (strip "(the son)" suffix)
                _base_466c = _SON_DAUGHTER_466c.sub("", _son_466c.canonical_name).strip()
                if not _base_466c:
                    continue
                # Find a proper-name parent character with that exact base name
                _parent_466c = next(
                    (
                        p for p in main_cast
                        if p.id not in (_desc_466c.id, _son_466c.id)
                        and p.canonical_name.strip().lower() == _base_466c.lower()
                    ),
                    None,
                )
                if _parent_466c is None:
                    continue
                # Merge: descriptor absorbs into proper-name parent
                logger.info(
                    f"V2 Step 5.4.6c: Merging descriptor '{_desc_466c.canonical_name}' "
                    f"(kinship alias '{_kinship_466c}') into parent "
                    f"'{_parent_466c.canonical_name}' via son char '{_son_466c.canonical_name}'"
                )
                # Transfer descriptor's canonical_name as alias (not kinship descriptors)
                if _desc_466c.canonical_name not in _parent_466c.aliases:
                    _parent_466c.aliases.append(_desc_466c.canonical_name)
                for _a466c in getattr(_desc_466c, "aliases", []):
                    # Skip relational descriptors ("his father") — not useful name aliases
                    if _KINSHIP_ALIAS_466c.match(_a466c):
                        continue
                    if _a466c not in _parent_466c.aliases:
                        _parent_466c.aliases.append(_a466c)
                _parent_466c.mention_count = (
                    (getattr(_parent_466c, "mention_count", 0) or 0)
                    + (getattr(_desc_466c, "mention_count", 0) or 0)
                )
                _chars_to_remove_466c.append(_desc_466c)
                break
        if _chars_to_remove_466c:
            _merged_parent_ids_466c = {
                p.id for p in main_cast
                if any(
                    p.canonical_name.strip().lower() == _SON_DAUGHTER_466c.sub("", s.canonical_name).strip().lower()
                    for s in main_cast
                    if _SON_DAUGHTER_466c.search(s.canonical_name)
                )
            }
            main_cast = [c for c in main_cast if c not in _chars_to_remove_466c]
            logger.info(
                f"V2 Step 5.4.6c: Removed {len(_chars_to_remove_466c)} descriptor-reveal character(s)"
            )
            # Re-search mentions so the parent's mention count reflects new aliases
            if _merged_parent_ids_466c:
                self._refresh_mentions(
                    _merged_parent_ids_466c, main_cast, searcher, mention_results
                )
        logger.info(
            f"V2 Step 5.4.6c complete: {len(main_cast)} main cast after kinship-alias merge"
        )

        # STEP 5.5a: Merge multi-word supporting formal names into single-word main cast nicknames.
        # Example: main "Jim" (26 mentions) + supporting "James Dillingham Young" (3 mentions)
        # → "James" is the formal name of nickname "Jim" → merge as alias.
        logger.info("V2 Step 5.5a: Merging formal-name supporting characters into main cast nicknames")
        main_cast, supporting_cast, formal_aliases_added = self._merge_formal_name_aliases(
            main_cast, supporting_cast
        )

        # Re-search mentions for characters that gained aliases via formal-name merge
        if formal_aliases_added:
            logger.info(
                f"V2 Step 5.5a: Re-searching mentions for {len(formal_aliases_added)} "
                f"character(s) with new formal-name aliases"
            )
            self._refresh_mentions(formal_aliases_added, main_cast, searcher, mention_results)

        logger.info(
            f"V2 Step 5.5a complete: {len(main_cast)} main cast, "
            f"{len(supporting_cast)} supporting after formal-name merge"
        )

        # STEP 5.5: Merge last-name-only supporting characters as aliases
        main_cast, supporting_cast, aliases_added = self._merge_lastname_aliases(
            main_cast, supporting_cast
        )

        # Re-search mentions for characters that gained new aliases
        if aliases_added:
            logger.info(
                f"Re-searching mentions for {len(aliases_added)} characters with new aliases"
            )
            self._refresh_mentions(aliases_added, main_cast, searcher, mention_results)

        logger.info(
            f"V2 Step 5.5 complete: {len(main_cast)} main cast, "
            f"{len(supporting_cast)} supporting after last-name merge"
        )

        # STEP 5.6: Merge within supporting cast (last-name-only, spelling variants)
        supporting_cast, supp_aliases_added = self._merge_within_supporting_cast(supporting_cast)

        # Re-search mentions for supporting characters that gained new aliases
        if supp_aliases_added:
            logger.info(
                f"Re-searching mentions for {len(supp_aliases_added)} supporting chars with new aliases"
            )
            self._refresh_mentions(supp_aliases_added, supporting_cast, searcher, mention_results)

        logger.info(
            f"V2 Step 5.6 complete: {len(supporting_cast)} supporting after within-supporting merge"
        )

        # STEP 5.6.5: Merge descriptive synonyms from supporting into main cast
        # Handles "the creature" (main) + "the monster" (supporting) → merge monster into creature
        logger.info("V2 Step 5.6.5: Merging descriptive synonyms across main/supporting casts")
        supporting_cast, cross_cast_aliases_added = self._merge_descriptive_synonyms_across_casts(
            main_cast, supporting_cast
        )

        # Re-search mentions for main cast characters that gained new aliases
        if cross_cast_aliases_added:
            logger.info(
                f"Re-searching mentions for {len(cross_cast_aliases_added)} main cast chars with new aliases"
            )
            self._refresh_mentions(cross_cast_aliases_added, main_cast, searcher, mention_results)

        logger.info(
            f"V2 Step 5.6.5 complete: {len(main_cast)} main cast, {len(supporting_cast)} supporting "
            f"after cross-cast synonym merge"
        )

        # STEP 5.6.5b: Recover creature synonym aliases blocked during pass-2 extraction.
        # When semantic split (Step 3.8) creates a split_* creature character, aliases like
        # "the monster", "the fiend", "the wretch" may have been blocked during pass-2 as
        # "already claimed" by the pre-split entry that was later consumed.  This step scans
        # the raw text for creature synonyms not yet assigned to any character and adds them
        # to the creature character.
        logger.info("V2 Step 5.6.5b: Recovering blocked creature synonym aliases")
        main_cast, creature_aliases_added = self._recover_creature_synonym_aliases(
            main_cast, context.text
        )
        if creature_aliases_added:
            logger.info(
                f"V2 Step 5.6.5b: Recovered aliases for {len(creature_aliases_added)} creature character(s)"
            )
            self._refresh_mentions(creature_aliases_added, main_cast, searcher, mention_results)

        # STEP 5.6.6: Merge bare surnames into family descriptive handles
        # Handles "De Lacey" (supporting) + "the old man" (main, father of Felix/Agatha De Lacey)
        logger.info("V2 Step 5.6.6: Merging bare surnames into family descriptive handles")
        supporting_cast, surname_aliases_added = self._merge_surname_into_family_descriptive(
            main_cast, supporting_cast
        )

        # Re-search mentions for main cast characters that gained new aliases
        if surname_aliases_added:
            logger.info(
                f"Re-searching mentions for {len(surname_aliases_added)} main cast chars with new surname aliases"
            )
            self._refresh_mentions(surname_aliases_added, main_cast, searcher, mention_results)

        logger.info(
            f"V2 Step 5.6.6 complete: {len(main_cast)} main cast, {len(supporting_cast)} supporting "
            f"after surname-family merge"
        )

        # STEP 5.6.9: Absorb supporting characters whose canonical name matches a main cast alias.
        # Universal invariant: if a supporting character's canonical name IS an alias of a main
        # cast character, they are the same person. This catches spelling variants (e.g.,
        # "Wolfshiem" as supporting canonical when "Wolfsheim" is already an alias of "Meyer
        # Wolfsheim" in main cast). Checks both exact and fuzzy alias matches.
        logger.info("V2 Step 5.6.9: Absorbing supporting chars that match main cast aliases")
        supporting_to_absorb = set()
        for supp_idx, supp_char in enumerate(supporting_cast):
            supp_lower = supp_char.canonical_name.strip().lower()
            if not supp_lower:
                continue
            for main_char in main_cast:
                # Check if supporting canonical matches main canonical (exact)
                if supp_lower == main_char.canonical_name.strip().lower():
                    main_char.mention_count = max(main_char.mention_count, supp_char.mention_count)
                    supporting_to_absorb.add(supp_idx)
                    logger.info(
                        f"V2 Step 5.6.9: Absorbed supporting '{supp_char.canonical_name}' "
                        f"(canonical match) into main '{main_char.canonical_name}'"
                    )
                    break
                # Check if supporting canonical matches any alias of main cast char (exact)
                aliases_lower = [a.strip().lower() for a in (main_char.aliases or [])]
                if supp_lower in aliases_lower:
                    old_count = main_char.mention_count
                    main_char.mention_count = max(main_char.mention_count, supp_char.mention_count)
                    supporting_to_absorb.add(supp_idx)
                    logger.info(
                        f"V2 Step 5.6.9: Absorbed supporting '{supp_char.canonical_name}' "
                        f"({supp_char.mention_count} mentions) into main '{main_char.canonical_name}' "
                        f"(mentions: {old_count} → {main_char.mention_count})"
                    )
                    break
                # Fuzzy alias match: catches spelling variants like "Wolfshiem"/"Wolfsheim"
                if any(names_similar(supp_lower, a_lower) for a_lower in aliases_lower):
                    main_char.mention_count = max(main_char.mention_count, supp_char.mention_count)
                    supporting_to_absorb.add(supp_idx)
                    logger.info(
                        f"V2 Step 5.6.9: Absorbed supporting '{supp_char.canonical_name}' "
                        f"(fuzzy alias match of '{main_char.canonical_name}')"
                    )
                    break
                # Fuzzy canonical match
                if names_similar(supp_lower, main_char.canonical_name.strip().lower()):
                    main_char.mention_count = max(main_char.mention_count, supp_char.mention_count)
                    supporting_to_absorb.add(supp_idx)
                    logger.info(
                        f"V2 Step 5.6.9: Absorbed supporting '{supp_char.canonical_name}' "
                        f"(fuzzy canonical match of '{main_char.canonical_name}')"
                    )
                    break
        if supporting_to_absorb:
            supporting_cast = [c for idx, c in enumerate(supporting_cast) if idx not in supporting_to_absorb]
            logger.info(f"V2 Step 5.6.9 complete: absorbed {len(supporting_to_absorb)} supporting char(s)")

        # STEP 5.7: Final defensive narrator filter (after all merges)
        # This catches any narrator entries that might have been introduced during merging
        logger.info("V2 Step 5.7: Final narrator filter pass")
        main_cast = self._filter_narrator_variants(
            main_cast, narrator_info.narrator_name, is_main_cast=True
        )
        supporting_cast = self._filter_narrator_variants(
            supporting_cast, narrator_info.narrator_name
        )
        logger.info(
            f"V2 Step 5.7 complete: {len(main_cast)} main cast, {len(supporting_cast)} supporting "
            f"after final narrator filter"
        )

        # STEP 5.7.5: Update mention counts for supporting cast BEFORE promotion
        # Supporting cast NER counts may undercount actual text occurrences (spaCy misses some
        # entity detections). Running deterministic mention search here ensures that STEP 5.8
        # promotion decisions are based on accurate counts, not NER approximations.
        if supporting_cast:
            logger.info(
                f"V2 Step 5.7.5: Pre-promotion mention search for {len(supporting_cast)} supporting characters"
            )
            try:
                pre_promotion_results = searcher.search_all(supporting_cast)
                supporting_cast = searcher.update_characters_with_mentions(
                    supporting_cast, pre_promotion_results
                )
                mention_results.update(pre_promotion_results)
                for char in supporting_cast:
                    r = pre_promotion_results.get(char.id)
                    if r and r.chapter_distribution:
                        chapter_indices = sorted(r.chapter_distribution.keys())
                        char.first_appearance_chapter = chapter_indices[0]
            except Exception as e:
                logger.warning(f"Pre-promotion mention search failed: {e}")

        # STEP 5.8: Post-processing - Promote high-mention supporting characters to main cast
        # This addresses cases where the LLM fails to extract key characters in main_cast
        # but they get picked up by NER-based supporting_cast extraction
        logger.info("V2 Step 5.8: Promoting high-mention supporting characters to main cast")

        # Characters with high mention counts should have protagonist/main roles
        # Thresholds based on narrative significance:
        # - 200+ mentions: Protagonist level (title character, narrator, central character)
        # - 100+ mentions: Main character level (key supporting roles, love interests)
        # - 50+ mentions: Supporting character level (recurring named characters)
        PROTAGONIST_THRESHOLD = 200
        MAIN_THRESHOLD = 100
        PROMOTION_THRESHOLD = 50

        # Scale thresholds for short texts where absolute counts are misleading
        # e.g., 14 mentions in a 2,354-word story = ~595 per 100K words (very significant)
        word_count = len(context.text.split()) if context.text else 100_000
        if word_count < 20_000:
            scale = 100_000 / max(word_count, 1000)
            effective_protagonist = max(10, int(PROTAGONIST_THRESHOLD / scale))
            effective_main = max(5, int(MAIN_THRESHOLD / scale))
            effective_promotion = max(3, int(PROMOTION_THRESHOLD / scale))
            logger.info(
                f"V2 Step 5.8: Short text ({word_count} words), scaled thresholds: "
                f"protagonist={effective_protagonist}, main={effective_main}, promotion={effective_promotion}"
            )
        else:
            effective_protagonist = PROTAGONIST_THRESHOLD
            effective_main = MAIN_THRESHOLD
            effective_promotion = PROMOTION_THRESHOLD

        promoted_chars = []
        remaining_supporting = []
        main_cast_names_lower = {c.canonical_name.lower() for c in main_cast}

        for char in supporting_cast:
            if char.mention_count >= effective_promotion:
                # Skip promotion if a character with the same name already exists in main_cast.
                # This prevents duplicates when the LLM extracted the character in Pass 1 AND
                # NER/supporting cast also produced a fragment for the same name.
                if char.canonical_name.lower() in main_cast_names_lower:
                    _existing = next(
                        (c for c in main_cast if c.canonical_name.lower() == char.canonical_name.lower()),
                        None,
                    )
                    if _existing is not None:
                        _existing.mention_count = max(_existing.mention_count, char.mention_count)
                        logger.info(
                            f"V2 Step 5.8: '{char.canonical_name}' already in main_cast "
                            f"(id={_existing.id}); merged mention_count={_existing.mention_count}, skipped duplicate promotion"
                        )
                    remaining_supporting.append(char)
                    continue
                # Promote to main cast with role based on mention count
                if char.mention_count >= effective_protagonist:
                    char.role = "protagonist"
                elif char.mention_count >= effective_main:
                    char.role = "main"
                else:
                    char.role = "supporting"
                promoted_chars.append(char)
                main_cast_names_lower.add(char.canonical_name.lower())
                logger.info(
                    f"Promoted '{char.canonical_name}' to main cast ({char.mention_count} mentions, "
                    f"role: {char.role})"
                )
            else:
                remaining_supporting.append(char)

        if promoted_chars:
            main_cast.extend(promoted_chars)
            supporting_cast = remaining_supporting
            logger.info(f"Promoted {len(promoted_chars)} character(s) from supporting to main cast")

        logger.info(
            f"V2 Step 5.8 complete: {len(main_cast)} main cast, {len(supporting_cast)} supporting "
            f"after promotion"
        )

        # STEP 5.8.4: Resolve narrator name to character ID before potentially re-running LLM.
        # When STEP 4.25b (vocative correction) or similar identifies a narrator name but
        # clears narrator_character_id (because the match failed at that point), we now have
        # a fully-populated main_cast and can do a deterministic name lookup. This prevents
        # STEP 5.8.5 from re-running LLM-based narrator detection unnecessarily.
        # Universal invariant: if narrator_name is known and matches a main_cast character
        # by name or alias, that IS the narrator — no LLM re-detection needed.
        if (
            narrator_info.narrator_name is not None
            and narrator_info.narrator_character_id is None
            and narrator_info.pov not in ("unknown", "")
            and main_cast
        ):
            _resolve_name_584 = narrator_info.narrator_name.lower()
            _resolved_584 = next(
                (
                    c for c in main_cast
                    if c.canonical_name.lower() == _resolve_name_584
                    or _resolve_name_584 in c.canonical_name.lower().split()
                    or any(_resolve_name_584 == a.lower() for a in (c.aliases or []))
                ),
                None,
            )
            if _resolved_584 is not None:
                # Universal invariant: a narrator candidate with ≤ 5 mentions but another
                # character has ≥ 5x more is almost certainly NOT the narrator.
                # This mirrors the STEP 4.26 check to prevent a blocked narrator from being
                # re-assigned here after being cleared upstream.
                _resolved_584_count = getattr(_resolved_584, "mention_count", 0) or 0
                _resolved_584_max_other = max(
                    (getattr(c, "mention_count", 0) or 0 for c in main_cast if c.id != _resolved_584.id),
                    default=0,
                )
                if 0 < _resolved_584_count <= 5 and _resolved_584_max_other >= _resolved_584_count * 5:
                    logger.warning(
                        f"V2 Step 5.8.4: Narrator candidate '{_resolved_584.canonical_name}' "
                        f"has only {_resolved_584_count} mention(s) but another character has "
                        f"{_resolved_584_max_other} — rejecting low-mention narrator; clearing name."
                    )
                    narrator_info = NarratorInfo(
                        pov=narrator_info.pov,
                        narrator_character_id=None,
                        narrator_name=None,
                        confidence=0.3,
                    )
                else:
                    narrator_info = NarratorInfo(
                        pov=narrator_info.pov,
                        narrator_name=_resolved_584.canonical_name,
                        narrator_character_id=_resolved_584.id,
                        confidence=max(narrator_info.confidence, 0.75),
                    )
                    main_cast = narrator_detector.update_characters_with_narrator(main_cast, narrator_info)
                    logger.info(
                        f"V2 Step 5.8.4: Resolved narrator '{narrator_info.narrator_name}' "
                        f"to character ID '{_resolved_584.id}' — skipping LLM re-detection"
                    )

        # STEP 5.8.4b: Self-identification scan with full cast (supporting_cast now populated).
        # STEP 4.24 could not search supporting_cast because it runs before STEP 5. Now that
        # supporting_cast is fully populated, re-scan the raw text for explicit first-person
        # self-identification ("I am Name", "I'm Name", "my name is Name") and search
        # both main_cast and supporting_cast. This is the strongest possible narrator evidence
        # and must run BEFORE LLM re-detection (STEP 5.8.5) to prevent a wrong LLM assignment.
        import re as _re584b
        if (
            narrator_info.narrator_character_id is None
            and narrator_info.pov in ("first-person", "epistolary")
            and context.text
        ):
            _self_id_pats_584b = [
                r"\bI\s+am\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
                r"\bI'm\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
                r"\bmy\s+name\s+is\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
            ]
            _found_name_584b: Optional[str] = None
            for _pat_584b in _self_id_pats_584b:
                _m_584b = _re584b.search(_pat_584b, context.text)
                if _m_584b:
                    _found_name_584b = _m_584b.group(1)
                    break
            if _found_name_584b:
                _low_584b = _found_name_584b.lower()
                # Search main_cast first, then supporting_cast
                _cast_match_584b = next(
                    (c for c in main_cast
                     if c.canonical_name.lower() == _low_584b
                     or _low_584b in c.canonical_name.lower()
                     or any(_low_584b == a.lower() for a in (c.aliases or []))),
                    None,
                )
                _from_supporting_584b = False
                if _cast_match_584b is None and supporting_cast:
                    _cast_match_584b = next(
                        (c for c in supporting_cast
                         if c.canonical_name.lower() == _low_584b
                         or _low_584b in c.canonical_name.lower()
                         or any(_low_584b == a.lower() for a in (c.aliases or []))),
                        None,
                    )
                    _from_supporting_584b = _cast_match_584b is not None
                if _cast_match_584b is not None:
                    if _from_supporting_584b:
                        supporting_cast.remove(_cast_match_584b)
                        main_cast.append(_cast_match_584b)
                        logger.info(
                            f"V2 Step 5.8.4b: Self-identification '{_found_name_584b}' found "
                            f"in text; promoted '{_cast_match_584b.canonical_name}' from "
                            f"supporting cast to main cast"
                        )
                    # Clear any old narrator flags
                    for _c584b in main_cast:
                        if _c584b.id != _cast_match_584b.id and _c584b.is_narrator:
                            _c584b.is_narrator = False
                            _c584b.narrative_role = None
                    narrator_info = NarratorInfo(
                        pov="first-person",
                        narrator_character_id=_cast_match_584b.id,
                        narrator_name=_cast_match_584b.canonical_name,
                        confidence=0.95,
                    )
                    main_cast = narrator_detector.update_characters_with_narrator(
                        main_cast, narrator_info
                    )
                    logger.info(
                        f"V2 Step 5.8.4b: Narrator confirmed as '{_cast_match_584b.canonical_name}' "
                        f"via self-identification in raw text — skipping LLM re-detection"
                    )
                else:
                    logger.info(
                        f"V2 Step 5.8.4b: Self-identification '{_found_name_584b}' found in text "
                        f"but no matching character in either cast — proceeding to narrator_name lookup"
                    )
            # Even if no self-id match in text, check if narrator_name (set by STEP 4.5b)
            # matches a supporting_cast character. This handles the common case where the
            # narrator is identified by vocative patterns ("Please, Ted") but is only in
            # the supporting cast (not extracted as main cast by the LLM).
            if narrator_info.narrator_character_id is None and narrator_info.narrator_name:
                _nname_584b = narrator_info.narrator_name.lower()
                _generic_584b = {
                    "the narrator", "narrator", "the protagonist", "protagonist",
                    "main character", "the main character", "unknown",
                }
                if _nname_584b not in _generic_584b:
                    # Check main_cast first
                    _name_match_584b = next(
                        (c for c in main_cast
                         if c.canonical_name.lower() == _nname_584b
                         or _nname_584b in c.canonical_name.lower()
                         or any(_nname_584b == a.lower() for a in (c.aliases or []))),
                        None,
                    )
                    if _name_match_584b is None and supporting_cast:
                        _name_match_584b = next(
                            (c for c in supporting_cast
                             if c.canonical_name.lower() == _nname_584b
                             or _nname_584b in c.canonical_name.lower()
                             or any(_nname_584b == a.lower() for a in (c.aliases or []))),
                            None,
                        )
                        if _name_match_584b is not None:
                            supporting_cast.remove(_name_match_584b)
                            main_cast.append(_name_match_584b)
                            logger.info(
                                f"V2 Step 5.8.4b: Narrator '{narrator_info.narrator_name}' "
                                f"found in supporting cast; promoting "
                                f"'{_name_match_584b.canonical_name}' to main cast"
                            )
                    if _name_match_584b is not None:
                        for _c584b2 in main_cast:
                            if _c584b2.id != _name_match_584b.id and _c584b2.is_narrator:
                                _c584b2.is_narrator = False
                                _c584b2.narrative_role = None
                        narrator_info = NarratorInfo(
                            pov=narrator_info.pov or "first-person",
                            narrator_character_id=_name_match_584b.id,
                            narrator_name=_name_match_584b.canonical_name,
                            confidence=max(narrator_info.confidence, 0.85),
                        )
                        main_cast = narrator_detector.update_characters_with_narrator(
                            main_cast, narrator_info
                        )
                        logger.info(
                            f"V2 Step 5.8.4b: Narrator '{_name_match_584b.canonical_name}' "
                            f"resolved from narrator_name lookup — skipping LLM re-detection"
                        )

        # STEP 5.8.5: Re-run narrator detection if narrator was not identified in STEP 4
        # This handles the case where main_cast was empty during STEP 4 (LLM extraction failed
        # or all candidates were filtered by grounding), but promotion in STEP 5.8 has now
        # added characters to main_cast. With actual characters available, narrator detection
        # has better context to match the narrator name to a known character.
        # Also re-runs when narrator was named but could not be matched (narrator_character_id is None),
        # e.g. when STEP 4 identified "Ted" as narrator but main_cast was empty so no match was possible.
        if (
            narrator_info.pov in ("unknown", "")
            or narrator_info.narrator_name is None
            or narrator_info.narrator_character_id is None
        ) and main_cast:
            logger.info(
                f"V2 Step 5.8.5: Re-running narrator detection with {len(main_cast)} characters "
                f"(initial detection returned pov='{narrator_info.pov}')"
            )
            try:
                narrator_info = narrator_detector.detect(
                    chapter_summaries, main_cast, plot_summary
                )
                main_cast = narrator_detector.update_characters_with_narrator(
                    main_cast, narrator_info
                )
                logger.info(
                    f"V2 Step 5.8.5 complete: pov={narrator_info.pov}, "
                    f"narrator={narrator_info.narrator_name}"
                )
            except Exception as e:
                logger.warning(f"Narrator re-detection failed: {e}")

        # Post-STEP-5.8.5 narrator guard: re-apply the STEP 4.26 low-mention invariant.
        # STEP 5.8.5 may re-run narrator detection after STEP 4.26 reset it, potentially
        # re-assigning the same low-mention character that was already rejected. Enforcing
        # this invariant again here prevents that re-assignment from persisting.
        if (
            narrator_info.pov in ("first-person", "epistolary")
            and narrator_info.narrator_character_id is not None
        ):
            _recheck_char = next(
                (c for c in main_cast if c.id == narrator_info.narrator_character_id), None
            )
            if _recheck_char is not None:
                _recheck_count = getattr(_recheck_char, "mention_count", 0) or 0
                _recheck_max_other = max(
                    (getattr(c, "mention_count", 0) or 0 for c in main_cast
                     if c.id != _recheck_char.id),
                    default=0,
                )
                if 0 < _recheck_count <= 5 and _recheck_max_other >= _recheck_count * 5:
                    logger.warning(
                        f"V2 Step 5.8.5 post-guard: Narrator '{_recheck_char.canonical_name}' "
                        f"({_recheck_count} mentions) still fails low-mention invariant "
                        f"(max_other={_recheck_max_other}). Resetting narrator."
                    )
                    _recheck_char.is_narrator = False
                    _recheck_char.narrative_role = None
                    narrator_info = NarratorInfo(
                        pov=narrator_info.pov,
                        narrator_character_id=None,
                        narrator_name=None,
                        confidence=0.3,
                    )

        # STEP 5.8.5 chapter-spread guard: A first-person narrator must appear in early chapters.
        # Universal invariant: the narrator's voice is present from the first chapter. A character
        # who only appears in the second half (or final chapter) of the story cannot have been the
        # first-person voice throughout — they are a late-appearing character, not the narrator.
        # This specifically catches cases where a character appears only at the end (e.g., a parent
        # who shows up in the final chapter) and is wrongly selected by LLM or heuristic as narrator.
        if (
            narrator_info.pov in ("first-person", "epistolary")
            and narrator_info.narrator_character_id is not None
            and len(chapter_summaries) >= 3
        ):
            _spread_char_585 = next(
                (c for c in main_cast if c.id == narrator_info.narrator_character_id), None
            )
            if _spread_char_585 is not None:
                _first_chap_585 = getattr(_spread_char_585, "first_appearance_chapter", None)
                _total_chaps_585 = len(chapter_summaries)
                if (
                    _first_chap_585 is not None
                    and _first_chap_585 > _total_chaps_585 // 2
                ):
                    logger.warning(
                        f"V2 Step 5.8.5 chapter-spread guard: Proposed narrator "
                        f"'{_spread_char_585.canonical_name}' first appears in chapter "
                        f"{_first_chap_585} of {_total_chaps_585} (past the halfway mark) "
                        f"— a first-person narrator must appear from early chapters; resetting."
                    )
                    _spread_char_585.is_narrator = False
                    _spread_char_585.narrative_role = None
                    narrator_info = NarratorInfo(
                        pov=narrator_info.pov,
                        narrator_character_id=None,
                        narrator_name=None,
                        confidence=0.3,
                    )

        # STEP 5.8.5b: Search supporting_cast for narrator name fragments.
        # When narrator_name was identified but not matched to any main_cast
        # character, the narrator may exist in supporting_cast as fragments
        # (e.g., first name + last name separately) that individually fell below
        # the promotion threshold.  Merge any matches and promote to main_cast
        # BEFORE the heuristic fallback, which would otherwise pick the wrong
        # character.
        if (
            narrator_info.narrator_name is not None
            and narrator_info.narrator_character_id is None
            and supporting_cast
        ):
            result = self._find_narrator_in_supporting(
                narrator_info.narrator_name, supporting_cast
            )
            if result is not None:
                merged_narrator, supporting_cast = result
                # Check if a main_cast character with the same name already exists.
                # This can happen when the LLM already extracted the narrator in Pass 1
                # and the supporting cast also has a fragment for the same name.
                # In that case, mark the existing entry as narrator instead of creating a dup.
                _existing_narrator = next(
                    (c for c in main_cast if c.canonical_name.lower() == merged_narrator.canonical_name.lower()),
                    None,
                )
                if _existing_narrator is not None:
                    _existing_narrator.is_narrator = True
                    if not _existing_narrator.narrative_role:
                        _existing_narrator.narrative_role = "First-Person Narrator"
                    _existing_narrator.mention_count = max(
                        _existing_narrator.mention_count, merged_narrator.mention_count
                    )
                    narrator_info = NarratorInfo(
                        pov=narrator_info.pov or "first-person",
                        narrator_name=_existing_narrator.canonical_name,
                        narrator_character_id=_existing_narrator.id,
                        confidence=max(narrator_info.confidence, 0.75),
                    )
                    logger.info(
                        f"V2 Step 5.8.5b: Narrator '{merged_narrator.canonical_name}' "
                        f"already exists in main_cast (id={_existing_narrator.id}); "
                        f"updated is_narrator=True instead of creating duplicate"
                    )
                else:
                    main_cast.append(merged_narrator)
                    narrator_info = NarratorInfo(
                        pov=narrator_info.pov or "first-person",
                        narrator_name=merged_narrator.canonical_name,
                        narrator_character_id=merged_narrator.id,
                        confidence=max(narrator_info.confidence, 0.75),
                    )
                    logger.info(
                        f"V2 Step 5.8.5b: Narrator '{merged_narrator.canonical_name}' "
                        f"found in supporting cast, promoted to main cast "
                        f"(mention_count={merged_narrator.mention_count})"
                    )

        # STEP 5.8.5c: Create narrator character from vocative-identified name.
        # If narrator_name is known (set in STEP 4 or 4.25) but narrator_character_id
        # is still None after searching supporting_cast (5.8.5b), the narrator was not
        # extracted by any pipeline stage. Create a minimal Character entry from the
        # narrator name so it appears in the output and is correctly marked as narrator.
        # Verify the name exists in raw text before creating (prevents hallucination).
        import re as _re585c
        if (
            narrator_info.narrator_name is not None
            and narrator_info.narrator_character_id is None
        ):
            _nname_585c = narrator_info.narrator_name
            _ncount_585c = len(
                _re585c.findall(
                    rf"(?<![A-Za-z0-9]){_re585c.escape(_nname_585c)}(?![A-Za-z0-9])",
                    context.text,
                    _re585c.IGNORECASE,
                )
            )
            if _ncount_585c >= 1:
                from ..models import ConfidenceLevel as _CL585c
                _narrator_new = Character(
                    id=f"narrator_{_nname_585c.lower().replace(' ', '_')}",
                    canonical_name=_nname_585c,
                    role="protagonist",
                    mention_count=_ncount_585c,
                    is_narrator=True,
                    narrative_role="First-Person Narrator",
                    confidence=_CL585c.MEDIUM,
                )
                main_cast.append(_narrator_new)
                narrator_info = NarratorInfo(
                    pov=narrator_info.pov or "first-person",
                    narrator_name=_nname_585c,
                    narrator_character_id=_narrator_new.id,
                    confidence=max(narrator_info.confidence, 0.7),
                )
                logger.info(
                    f"V2 Step 5.8.5c: Created narrator character '{_nname_585c}' "
                    f"from vocative-identified name (text mentions={_ncount_585c})"
                )
            else:
                logger.warning(
                    f"V2 Step 5.8.5c: Narrator name '{_nname_585c}' not found in raw text "
                    f"— skipping character creation (likely hallucinated name)"
                )

        # STEP 5.8.6: Heuristic narrator fallback for confirmed first-person narratives.
        # When LLM narrator detection has failed (narrator_character_id is still None)
        # but the summaries metadata confirms first-person POV, use a universal heuristic:
        # in first-person narratives the narrator tends to have the lowest name-mention count
        # (they use "I" instead of their own name), so the least-mentioned character who
        # appears in the plot_summary is the most likely narrator.
        narrative_style = self._get_narrative_style(context)
        if (
            narrative_style
            and "first-person" in narrative_style.lower()
            and narrator_info.narrator_character_id is None
            # Universal invariant: if the LLM already determined the POV is NOT
            # first-person, do not apply the first-person heuristic. This prevents
            # assigning a narrator in third-person/omniscient narratives.
            # Also exclude "epistolary" (frame/nested narratives like Frankenstein):
            # the outer narrator has very few mentions and will be wrongly picked by
            # the lowest-mention heuristic even though the inner narrator is the true
            # narrator. For epistolary POV, secondary narrator assignment (Fix Q) in
            # narrator.py already marked the inner narrators correctly.
            and narrator_info.pov not in ("third-person", "omniscient", "epistolary")
            # Skip if any character was already marked as narrator by a prior step
            # (e.g. secondary narrator assignment in nested narratives). The heuristic
            # is only needed when narrator detection has completely failed.
            and not any(getattr(c, "is_narrator", False) for c in main_cast)
            and main_cast
        ):
            narrator_candidate = self._heuristic_narrator_from_mention_count(
                main_cast, plot_summary
            )
            if narrator_candidate:
                narrator_candidate.is_narrator = True
                narrator_candidate.narrative_role = "First-Person Narrator"
                if narrator_candidate.role not in ("protagonist",):
                    narrator_candidate.role = "protagonist"
                narrator_info = NarratorInfo(
                    pov="first-person",
                    narrator_name=narrator_candidate.canonical_name,
                    narrator_character_id=narrator_candidate.id,
                    confidence=0.6,
                )
                logger.info(
                    f"V2 Step 5.8.6: Heuristic narrator fallback identified "
                    f"'{narrator_candidate.canonical_name}' "
                    f"(mention_count={narrator_candidate.mention_count}, "
                    f"narrative_style='{narrative_style}')"
                )

        # STEP 5.9: REMOVED - Non-sentient object filter
        # Symbolic objects/forces can be valid "characters" for narrator preparation
        # Examples: "the monkey's paw" (title antagonist), "the eyes of Doctor T. J. Eckleburg" (symbolic presence)
        # Trust plot importance over categorization - if something drives the narrative, extract it
        logger.info("V2 Step 5.9: Skipped (object filter removed - trusting plot importance)")

        logger.info(
            f"V2 Step 5.9 complete: {len(main_cast)} main cast, {len(supporting_cast)} supporting"
        )

        # STEP 5.9.2: Remove possessive sub-entities from main_cast.
        # Universal invariant: if a character's canonical name is "{known_char}'s {noun_phrase}",
        # it's a location/possession of that character, not a standalone person.
        # Examples: "AM's ice caverns", "Gatsby's mansion", "Captain Ahab's ship".
        # This check is purely structural — no keyword lists involved.
        _known_names_lower = {c.canonical_name.lower() for c in main_cast}
        _possessive_filtered: list = []
        for char in main_cast:
            name_lower = char.canonical_name.lower()
            is_possessive_subentity = False
            for other_name_lower in _known_names_lower:
                if other_name_lower == name_lower:
                    continue
                # Check both straight and curly apostrophe variants
                for apos in ("'s ", "\u2019s "):
                    if name_lower.startswith(other_name_lower + apos):
                        is_possessive_subentity = True
                        logger.info(
                            f"Step 5.9.2: Removing '{char.canonical_name}' — possessive sub-entity "
                            f"of another character (name starts with another character's name in possessive form)"
                        )
                        break
                if is_possessive_subentity:
                    break
            if not is_possessive_subentity:
                _possessive_filtered.append(char)
        if len(_possessive_filtered) < len(main_cast):
            _known_names_lower = {c.canonical_name.lower() for c in _possessive_filtered}
            main_cast = _possessive_filtered

        # STEP 5.9.5: Correct role assignments for all main_cast characters.
        # The LLM may assign roles (protagonist/main/supporting) that don't reflect mention-count
        # evidence. Apply the same mention-count thresholds used in Step 5.8 as a universal
        # invariant: a character with enough mentions cannot remain "supporting" in the main cast.
        # Only upgrades roles — never downgrades — to preserve the LLM's narrative judgment.
        logger.info("V2 Step 5.9.5: Correcting role assignments by mention count")
        for char in main_cast:
            if char.is_narrator:
                continue  # Narrator role is managed separately
            current_role = char.role or "supporting"
            if char.mention_count >= effective_protagonist and current_role not in ("protagonist",):
                logger.info(
                    f"Step 5.9.5: Upgrading '{char.canonical_name}' from '{current_role}' "
                    f"to 'protagonist' ({char.mention_count} mentions >= {effective_protagonist})"
                )
                char.role = "protagonist"
            elif char.mention_count >= effective_main and current_role in ("supporting", None, ""):
                logger.info(
                    f"Step 5.9.5: Upgrading '{char.canonical_name}' from '{current_role}' "
                    f"to 'main' ({char.mention_count} mentions >= {effective_main})"
                )
                char.role = "main"

        # STEP 5.9.6: Final narrator role invariant.
        # Universal invariant: first-person narrators are always protagonist-level.
        # This runs after all merge/split steps to catch cases where role was set to
        # "minor" or "supporting" by the LLM and was never elevated (e.g., because the
        # mention_count guard in update_characters_with_narrator blocked the assignment
        # when mention counts were zero, or because a later merge step overwrote the role).
        if narrator_info.pov == "first-person":
            for char in main_cast:
                if char.is_narrator and getattr(char, "role", None) != "protagonist":
                    old_role = char.role
                    char.role = "protagonist"
                    logger.info(
                        f"V2 Step 5.9.6: Narrator role invariant: '{char.canonical_name}' "
                        f"'{old_role}' → 'protagonist'"
                    )

        # STEP 5.10: Final alias validation
        # Clean up any invalid aliases that may have been added during merge operations
        # This ensures aliases like "the ebony clock" (object) don't appear on non-object characters
        logger.info("V2 Step 5.10: Validating aliases before final output")
        self._clean_invalid_aliases(main_cast)
        self._clean_invalid_aliases(supporting_cast)

        # STEP 5.10.5: Search for mentions for supporting cast too (chapter distributions)
        #
        # Supporting cast is initially extracted via NER and may not have deterministic
        # mention search results. However, downstream components (and debugging) benefit
        # from having grounded mentions + chapter_distribution for supporting characters,
        # especially for same-name disambiguation and chapter-range priors.
        if supporting_cast:
            logger.info(
                f"V2 Step 5.10.5: Searching mentions for {len(supporting_cast)} supporting characters"
            )
            try:
                supporting_results = searcher.search_all(supporting_cast)
                supporting_cast = searcher.update_characters_with_mentions(
                    supporting_cast, supporting_results
                )
                # Merge into global mention_results so downstream conversion can use chapter_distribution
                mention_results.update(supporting_results)

                # Populate first appearance chapter when possible
                for char in supporting_cast:
                    r = supporting_results.get(char.id)
                    if r and r.chapter_distribution:
                        chapter_indices = sorted(r.chapter_distribution.keys())
                        char.first_appearance_chapter = chapter_indices[0]
            except Exception as e:
                logger.warning(f"Supporting cast mention search failed: {e}")

        # STEP 5.11: Final promotion pass — re-check supporting cast after alias-aware mention search.
        # STEP 5.7.5 ran before aliases were added to many supporting characters, so their mention
        # counts were based on the bare canonical name only. After STEP 5.10.5, mention counts
        # reflect all aliases. Any supporting character now crossing the protagonist threshold
        # (200+ mentions) should be promoted to main cast — they are clearly central characters
        # that were missed by the main cast LLM extraction but found by NER + alias resolution.
        # Universal invariant: a character with protagonist-level mentions is ALWAYS a protagonist.
        import re as _re511

        def _count_name_511(name: str, text: str) -> int:
            return len(_re511.findall(
                rf"(?<![A-Za-z0-9]){_re511.escape(name)}(?![A-Za-z0-9])",
                text, _re511.IGNORECASE
            ))

        main_cast_names_511 = {c.canonical_name.lower() for c in main_cast}
        # Also track aliases so we don't re-add something already represented in main cast
        for c in main_cast:
            for a in (c.aliases or []):
                main_cast_names_511.add(a.lower())

        late_promoted = []
        still_supporting = []
        logger.info(
            f"V2 Step 5.11: Checking {len(supporting_cast)} supporting chars for late promotion "
            f"(effective_protagonist={effective_protagonist}, main_cast_names count={len(main_cast_names_511)})"
        )
        for char in supporting_cast:
            _511_blocked_by_name = char.canonical_name.lower() in main_cast_names_511
            if char.mention_count >= effective_protagonist:
                logger.info(
                    f"V2 Step 5.11: '{char.canonical_name}' has {char.mention_count} mentions "
                    f"(>= {effective_protagonist}), name_in_main_cast={_511_blocked_by_name}, "
                    f"aliases={char.aliases}"
                )
            if (char.mention_count >= effective_protagonist
                    and not _511_blocked_by_name):
                # Universal invariant: prefer the name the character is most commonly called.
                # If the canonical has very few text mentions but an alias has many more,
                # rename to the most common alias (prefer multi-word fullest name).
                if context.text:
                    canonical_count_511 = _count_name_511(char.canonical_name, context.text)
                    if canonical_count_511 < 10 and char.aliases:
                        best_alias_511 = None
                        best_count_511 = 0
                        for alias in (char.aliases or []):
                            ac = _count_name_511(alias, context.text)
                            if ac > canonical_count_511 * 1.5:
                                if best_alias_511 is None:
                                    best_alias_511 = alias
                                    best_count_511 = ac
                                elif len(alias.split()) > 1 and len(best_alias_511.split()) == 1:
                                    # Prefer multi-word (fuller) name over single-word
                                    best_alias_511 = alias
                                    best_count_511 = ac
                                elif (len(alias.split()) == len(best_alias_511.split())
                                      and ac > best_count_511):
                                    best_alias_511 = alias
                                    best_count_511 = ac
                        if best_alias_511:
                            old_canonical = char.canonical_name
                            char.aliases = [a for a in char.aliases if a != best_alias_511]
                            if old_canonical not in char.aliases:
                                char.aliases.append(old_canonical)
                            char.canonical_name = best_alias_511
                            logger.info(
                                f"V2 Step 5.11: Renamed '{old_canonical}' → '{best_alias_511}' "
                                f"({best_count_511} mentions vs {canonical_count_511} for canonical)"
                            )

                char.role = "protagonist"
                late_promoted.append(char)
                main_cast_names_511.add(char.canonical_name.lower())
                logger.info(
                    f"V2 Step 5.11: Late-promoting '{char.canonical_name}' to main cast "
                    f"({char.mention_count} mentions, role set to protagonist)"
                )
            else:
                still_supporting.append(char)

        if late_promoted:
            main_cast.extend(late_promoted)
            supporting_cast = still_supporting
            logger.info(f"V2 Step 5.11: Late-promoted {len(late_promoted)} character(s) to main cast")

        # STEP 5.11.5: Remove shared single-word aliases from main_cast.
        # Universal invariant: if the same single-word alias (e.g., a surname) appears on
        # 2+ characters, it is ambiguous and unhelpful for identification. Remove it from
        # all characters. This prevents married-name ambiguity (e.g., "Buchanan" on both
        # Tom Buchanan and Daisy Buchanan) from confusing alias-based lookups.
        if len(main_cast) >= 2:
            from collections import defaultdict as _defaultdict_5115
            _alias_owners_5115: dict[str, list] = _defaultdict_5115(list)
            for _char_5115 in main_cast:
                for _alias_5115 in (_char_5115.aliases or []):
                    _a_lower_5115 = _alias_5115.strip().lower()
                    # Only consider single-word aliases (surname-only or first-name-only)
                    if _a_lower_5115 and " " not in _a_lower_5115:
                        _alias_owners_5115[_a_lower_5115].append(_char_5115)
            for _a_word_5115, _owners_5115 in _alias_owners_5115.items():
                if len(_owners_5115) >= 2:
                    # Remove this ambiguous alias from all owners
                    for _owner_5115 in _owners_5115:
                        _owner_5115.aliases = [
                            a for a in (_owner_5115.aliases or [])
                            if a.strip().lower() != _a_word_5115
                        ]
                        logger.info(
                            f"V2 Step 5.11.5: Removed shared alias '{_a_word_5115}' "
                            f"from '{_owner_5115.canonical_name}' (appeared on {len(_owners_5115)} characters)"
                        )

        # Fix GG: Remove non-living environment characters from cast.
        # Universal invariant: physical environment elements (ice, sea, storm, etc.) are
        # NEVER narrative characters — they are setting elements. If a non-living noun
        # ends up in the cast with no proper-name aliases and no symbolic status,
        # it was extracted erroneously (e.g., "the ice" in Frankenstein polar scenes).
        _NON_LIVING_FILTER_GG = {
            "ice", "sea", "ocean", "water", "river", "lake", "mist", "fog",
            "wind", "storm", "forest", "wood", "mountain", "cliff", "cave",
            "snow", "frost", "darkness", "light", "fire", "void", "abyss",
            "shadow", "nature", "earth", "sky", "air", "wave", "tide",
            "current", "glacier", "wilderness", "landscape", "terrain",
            "cold", "heat", "silence", "night", "fog",
        }

        def _is_nonliving_entity_gg(char) -> bool:
            """True if this character is an erroneously extracted non-living entity."""
            if getattr(char, "is_symbolic", False):
                return False  # Symbolic objects may legitimately be characters
            name_lower = char.canonical_name.lower().strip()
            last_word = name_lower.split()[-1] if name_lower else ""
            if last_word not in _NON_LIVING_FILTER_GG:
                return False
            # Allow through if character has a proper-name alias (could be a location with a name)
            for alias in (char.aliases or []):
                # Check using _has_proper_noun logic inline
                for word in alias.split():
                    clean = word.strip(".,;:'\"()[]")
                    if clean and clean[0].isupper() and clean.lower() not in {
                        "the", "a", "an", "of", "in", "from", "to", "at", "by", "on"
                    }:
                        return False  # Has a proper-name alias — keep it
            return True  # No proper names, last word is non-living — filter out

        _gg_removed_main = [c for c in main_cast if _is_nonliving_entity_gg(c)]
        _gg_removed_supp = [c for c in supporting_cast if _is_nonliving_entity_gg(c)]
        if _gg_removed_main or _gg_removed_supp:
            for _c in _gg_removed_main + _gg_removed_supp:
                logger.warning(
                    f"Fix GG: Removing non-living environment entity '{_c.canonical_name}' "
                    f"from cast (last word: '{_c.canonical_name.lower().split()[-1]}', "
                    f"mentions={_c.mention_count})"
                )
            main_cast = [c for c in main_cast if not _is_nonliving_entity_gg(c)]
            supporting_cast = [c for c in supporting_cast if not _is_nonliving_entity_gg(c)]

        # Build final CharacterMap
        all_characters = self._convert_to_pipeline_characters(
            main_cast, supporting_cast, mention_results
        )

        # Calculate confidence breakdown
        high = sum(1 for c in all_characters if c.confidence >= 0.7)
        medium = sum(1 for c in all_characters if 0.4 <= c.confidence < 0.7)
        low = sum(1 for c in all_characters if c.confidence < 0.4)

        character_map = CharacterMap(
            characters=all_characters,
            low_confidence_characters=[c for c in all_characters if c.confidence < 0.4],
            total_mentions=sum(c.mention_count for c in all_characters),
            total_chapters=len(chapters) if chapters else 1,
            pipeline_metadata={
                "version": "v2",
                "main_cast_count": len(main_cast),
                "supporting_cast_count": len(supporting_cast),
                "grounded_count": grounding_report.total_grounded,
                "ungrounded_count": grounding_report.total_ungrounded,
                "narrator_pov": narrator_info.pov,
                # Only export narrator_name when narrator_character_id is set (narrator matched
                # to an extracted character). If narrator_name is exported without a matching
                # character, analyzer.py line ~1115 sets narrator_detected = narrator_name
                # unconditionally, causing Step 6.9 to globally substitute that name into ALL
                # chapter summaries — breaking nested narratives (e.g., Frankenstein where
                # Robert Walton is narrator but Victor/creature chapters must not use Walton).
                "narrator_name": narrator_info.narrator_name if narrator_info.narrator_character_id else None,
            },
        )

        elapsed = time.perf_counter() - start_time

        return AgentResult(
            data=character_map,
            confidence_scores=[c.confidence for c in all_characters],
            high_confidence_count=high,
            medium_confidence_count=medium,
            low_confidence_count=low,
            issues=issues,
            processing_time_seconds=elapsed,
            model_used=self.llm.config.model if self.llm else None,
            provider_used=self.llm.config.provider if self.llm else None,
        )

    def verify(
        self,
        result: AgentResult[CharacterMap],
        level: VerificationLevel = VerificationLevel.SELF_CHECK,
        context: Optional[AgentContext] = None,
    ) -> VerificationResult:
        """
        Verify V2 character extraction quality.

        Simpler than V1 - most validation is handled by grounding gate.
        """
        issues = []
        character_map = result.data

        if not character_map.characters:
            return VerificationResult(passed=True, issues=[], suggestions=[])

        # Check 1: Main cast count is reasonable
        main_count = character_map.pipeline_metadata.get("main_cast_count", 0)
        if main_count < 3:
            issues.append(
                VerificationIssue(
                    description=f"Only {main_count} main cast characters - may be incomplete",
                    severity="warning",
                )
            )
        elif main_count > 20:
            issues.append(
                VerificationIssue(
                    description=f"{main_count} main cast characters - may have over-extraction",
                    severity="warning",
                )
            )

        # Check 2: Grounding worked
        ungrounded = character_map.pipeline_metadata.get("ungrounded_count", 0)
        if ungrounded > main_count:
            issues.append(
                VerificationIssue(
                    description=f"More ungrounded ({ungrounded}) than grounded ({main_count}) characters",
                    severity="warning",
                )
            )

        # Check 3: Low confidence items
        if result.low_confidence_count > 0:
            issues.append(
                VerificationIssue(
                    description=f"{result.low_confidence_count} characters have low confidence",
                    severity="info",
                )
            )

        return VerificationResult(
            passed=len([i for i in issues if i.severity == "error"]) == 0,
            issues=issues,
            suggestions=[],
        )

    def _error_result(
        self,
        error_msg: str,
        start_time: float,
    ) -> AgentResult[CharacterMap]:
        """Create an error result."""
        elapsed = time.perf_counter() - start_time
        return AgentResult(
            data=CharacterMap(
                characters=[],
                low_confidence_characters=[],
                total_mentions=0,
                total_chapters=0,
                pipeline_metadata={"error": error_msg, "version": "v2"},
            ),
            high_confidence_count=0,
            medium_confidence_count=0,
            low_confidence_count=0,
            issues=[error_msg],
            processing_time_seconds=elapsed,
            model_used=self.llm.config.model if self.llm else None,
            provider_used=self.llm.config.provider if self.llm else None,
        )

    def _get_chapter_summaries(self, context: AgentContext) -> list[str]:
        """Extract chapter summaries from context."""
        # Try getting from previous_results (SummaryAgent output)
        summaries_result = context.get_result("summaries")
        if summaries_result:
            # SummaryAgent returns a list of ChapterSummary objects or similar
            if hasattr(summaries_result, "summaries"):
                result = []
                for s in summaries_result.summaries:
                    if not s.summary:
                        continue
                    text = s.summary
                    # Prepend structured character list when available.
                    # CHARACTER_IDENTIFICATION_PROMPT references `characters_present` lists
                    # but they were never actually included in the text — this fixes that gap.
                    chars = getattr(s, "characters_present", None) or []
                    if chars:
                        text = f"[Characters present: {', '.join(chars)}]\n{text}"
                    result.append(text)
                return result
            elif isinstance(summaries_result, list):
                result = [
                    s.get("summary") if isinstance(s, dict) else str(s)
                    for s in summaries_result
                    if s
                ]
                return result

        # Try getting from chapter_map (summaries may be stored on chapters)
        if context.chapter_map:
            summaries = []
            chapters = getattr(context.chapter_map, "chapters", [])
            for ch in chapters:
                if hasattr(ch, "summary") and ch.summary:
                    summaries.append(ch.summary)
            if summaries:
                return summaries

        logger.warning("No chapter summaries found from any source")
        return []

    def _get_chapters(self, context: AgentContext) -> list[StructuralElement]:
        """Get chapter structural elements from context."""
        if context.chapter_map:
            chapters = getattr(context.chapter_map, "chapters", [])
            # Convert to StructuralElement if needed
            result = []
            for ch in chapters:
                if isinstance(ch, StructuralElement):
                    result.append(ch)
                elif hasattr(ch, "start_position"):
                    # Create StructuralElement from chapter data
                    elem = StructuralElement(
                        type=StructureType.CHAPTER,
                        index=getattr(ch, "index", 0),
                        start_position=ch.start_position,
                        end_position=getattr(ch, "end_position", ch.start_position + 1000),
                    )
                    result.append(elem)
            return result
        return []

    def _get_plot_summary(self, context: AgentContext) -> Optional[str]:
        """Get overall plot summary if available.

        ChapterSummaryMap does not have a .plot_summary attribute, so we construct
        a combined summary from the available chapter summaries. This combined text
        gives narrator detection and main cast extraction a holistic view of the story.
        """
        summaries_result = context.get_result("summaries")
        if summaries_result:
            # Primary: ChapterSummaryMap.plot_summary (if it exists in some variant)
            if hasattr(summaries_result, "plot_summary"):
                ps = summaries_result.plot_summary
                # Handle nested dict structure (e.g., {"plot_summary": "...", "narrative_style": "..."})
                if isinstance(ps, dict):
                    ps = ps.get("plot_summary") or ps.get("summary") or ps.get("text")
                if isinstance(ps, str) and ps.strip():
                    return ps
            # Fallback: dict-type result
            if isinstance(summaries_result, dict):
                ps = summaries_result.get("plot_summary")
                if isinstance(ps, dict):
                    ps = ps.get("plot_summary") or ps.get("summary") or ps.get("text")
                if isinstance(ps, str) and ps.strip():
                    return ps
            # Construct from chapter summaries when no dedicated plot_summary exists
            # (ChapterSummaryMap has .summaries but no .plot_summary)
            if hasattr(summaries_result, "summaries") and summaries_result.summaries:
                parts = [s.summary for s in summaries_result.summaries if s.summary]
                if parts:
                    combined = "\n\n".join(parts)
                    return combined
        return None

    def _collect_all_names(self, characters: list[Character]) -> set[str]:
        """Collect all names and aliases from characters."""
        names = set()
        for char in characters:
            names.add(char.canonical_name)
            names.update(char.aliases)
        return names

    def _filter_narrator_variants(
        self,
        supporting_cast: list[Character],
        narrator_name: str | None,
        is_main_cast: bool = False,
    ) -> list[Character]:
        """
        Filter out narrator-related entries from cast.

        Removes entries like:
        - "Narrator"
        - "the narrator"
        - "The Narrator"
        - "John Smith (narrator)"

        These are descriptive references that should not be separate characters.

        Args:
            supporting_cast: List of characters to filter
            narrator_name: The identified narrator's name (if any)
            is_main_cast: If True, keep narrator placeholders that have been
                          properly identified via proper-name aliases (e.g.,
                          "The narrator" with alias "Victor Frankenstein" is
                          a real character, not a generic placeholder).

        Returns:
            Filtered list with narrator variants removed
        """
        if not supporting_cast:
            return supporting_cast

        # Placeholder patterns used for narrator identification in summaries
        placeholder_patterns = [
            "the protagonist", "the narrator", "narrator", "protagonist",
            "main character", "the main character",
        ]

        filtered = []
        removed_count = 0

        for char in supporting_cast:
            canonical_lower = char.canonical_name.lower()

            # Check if canonical name contains "narrator" (case-insensitive)
            if "narrator" in canonical_lower:
                # For main cast: keep if the placeholder has been identified by a
                # proper-name alias (e.g., "The narrator" with alias "Victor Frankenstein").
                # A proper-name alias is one that: has at least one capitalized word,
                # is not itself a placeholder pattern, and is not a generic "the X" descriptor.
                if is_main_cast:
                    has_proper_name_alias = any(
                        any(
                            token[0].isupper()
                            for token in alias.split()
                            if len(token) >= 2
                        )
                        and not any(p in alias.lower() for p in placeholder_patterns)
                        for alias in char.aliases
                    )
                    if has_proper_name_alias:
                        logger.info(
                            f"Keeping narrator placeholder '{char.canonical_name}' "
                            f"— has proper-name alias(es): {char.aliases}"
                        )
                        filtered.append(char)
                        continue

                logger.info(
                    f"Filtering narrator variant '{char.canonical_name}' "
                    f"({char.mention_count} mentions)"
                )
                removed_count += 1
                continue

            filtered.append(char)

        if removed_count > 0:
            logger.info(f"Removed {removed_count} narrator variant(s)")

        return filtered

    def _merge_summary_name_fragments(
        self,
        chapter_summaries: list[str],
        main_cast: list[Character],
        supporting_cast: list[Character],
    ) -> tuple[list[Character], list[Character], set[str]]:
        """Merge single-word cast fragments when summaries list them under a multi-word name.

        When LLM extraction fails to produce "Milton Jennings" as a unit, NER may yield
        separate "Milton" (supporting) and "Jennings" (supporting) entries.  The summary
        [Characters present: ...] prefix provides the authoritative full name.  This step
        merges such single-word fragments deterministically — no prompts, no vocabulary lists.

        Universally applicable: the only signal used is the summary character list vs the
        cast's single-word canonical names.  Works for any first-name + surname pair in
        any language/genre.

        Algorithm:
        1. Parse multi-word names from [Characters present: ...] prefixes.
        2. For each multi-word name, find one single-word cast character per word.
        3. If ALL words map to distinct single-word characters, merge them:
           - dominant (most mentions) keeps its ID, adopts the full name as canonical.
           - subordinates become aliases; removed from their cast list.
           - merged character is placed in main_cast (summary named it explicitly).
        """
        import re
        from collections import Counter

        # Parse character names from [Characters present: name1, name2, ...] prefixes.
        # Also build co_present_pairs: name pairs that were listed as SEPARATE entries in
        # the same summary section.  A pair in this set means the summarizer treated both
        # names as distinct characters — merging them is forbidden.
        name_counts: Counter = Counter()
        co_present_pairs: set[frozenset] = set()
        for summary_text in chapter_summaries:
            m = re.match(r"^\[Characters present:\s*(.+?)\]", summary_text)
            if not m:
                continue
            names = [n.strip() for n in m.group(1).split(",") if n.strip()]
            for name in names:
                name_counts[name] += 1
            # Record every pair of co-listed names (normalized: strip parenthetical qualifier)
            normalized: list[str] = []
            for name in names:
                clean = re.sub(r"\s*\(.*?\)\s*$", "", name).strip().lower()
                if clean:
                    normalized.append(clean)
            for i, n1 in enumerate(normalized):
                for n2 in normalized[i + 1 :]:
                    co_present_pairs.add(frozenset([n1, n2]))

        # Only process multi-word names (2+ words)
        multi_word_names = [n for n in name_counts if len(n.split()) >= 2]
        if not multi_word_names:
            return main_cast, supporting_cast, set()

        # Build a lookup of single-word canonical names across both casts
        # (multi-word canonical names are already properly merged — skip them)
        all_chars = main_cast + supporting_cast
        existing_full_names_lower = {c.canonical_name.lower() for c in all_chars}

        # lowercase → Character (single-word only, first occurrence wins)
        single_word_lookup: dict[str, Character] = {}
        for char in all_chars:
            if " " not in char.canonical_name:
                key = char.canonical_name.lower()
                if key not in single_word_lookup:
                    single_word_lookup[key] = char

        chars_to_remove: set[str] = set()  # IDs of absorbed (subordinate) characters
        merged_ids: set[str] = set()  # IDs of dominant characters that absorbed others

        # Process most-frequently-mentioned names first so earlier merges take priority
        for full_name in sorted(multi_word_names, key=lambda n: -name_counts[n]):
            # Skip if this full name already exists as a canonical name in the cast
            if full_name.lower() in existing_full_names_lower:
                continue

            words = full_name.split()

            # Find one matching single-word fragment per word of the full name
            fragments: list[Character] = []
            all_found = True
            for word in words:
                word_lower = word.lower()
                char = single_word_lookup.get(word_lower)
                if char is None or char.id in chars_to_remove:
                    all_found = False
                    break
                fragments.append(char)

            if not all_found:
                # Partial match: if exactly one word has a high-mention single-word
                # character (≥10 mentions), rename it to the full summary name.
                # Handles cases where, e.g., "Jennings" doesn't exist as a standalone
                # character but "Milton" (23 mentions) does — rename Milton → Milton Jennings.
                # "Exactly one" guard prevents ambiguity when multiple words match.
                fragments = []
                for word in words:
                    char = single_word_lookup.get(word.lower())
                    if char and char.id not in chars_to_remove and char.mention_count >= 10:
                        fragments.append(char)
                if len(fragments) != 1:
                    continue

            # All fragments must be distinct characters (sanity check)
            if len({f.id for f in fragments}) < len(fragments):
                continue

            # Co-present guard: if the summarizer listed a fragment AND the full name as
            # SEPARATE entries in the same section, they are different characters — skip merge.
            # Example: "John" and "John Donaldson (the father)" co-listed → father ≠ son.
            full_name_base = re.sub(r"\s*\(.*?\)\s*$", "", full_name).strip().lower()
            if any(
                frozenset([f.canonical_name.lower(), full_name_base]) in co_present_pairs
                for f in fragments
            ):
                logger.info(
                    f"V2 Step 5.4.5: Skipping merge of '{full_name}' — "
                    f"summary lists fragment(s) as separate characters: "
                    f"{[f.canonical_name for f in fragments]}"
                )
                continue

            # Dominant fragment = the one with the most mentions
            dominant = max(fragments, key=lambda c: c.mention_count)
            subordinates = [f for f in fragments if f.id != dominant.id]

            old_canonical = dominant.canonical_name
            dominant.canonical_name = full_name
            # Approximate combined mention count; _refresh_mentions will give the real count
            dominant.mention_count = sum(f.mention_count for f in fragments)

            # Absorb subordinate canonical names and aliases into dominant
            if old_canonical not in dominant.aliases:
                dominant.aliases.append(old_canonical)
            for sub in subordinates:
                if sub.canonical_name not in dominant.aliases:
                    dominant.aliases.append(sub.canonical_name)
                for alias in sub.aliases:
                    if alias not in dominant.aliases and alias != dominant.canonical_name:
                        dominant.aliases.append(alias)
                chars_to_remove.add(sub.id)

            merged_ids.add(dominant.id)
            logger.info(
                f"V2 Step 5.4.5: Summary-crossref merged '{full_name}' from fragments "
                f"{[f.canonical_name for f in fragments]} "
                f"(dominant_id={dominant.id}, approx_mentions={dominant.mention_count})"
            )

            # Keep lookup consistent: absorbed characters can no longer be matched
            for sub in subordinates:
                sub_key = sub.canonical_name.lower()
                if single_word_lookup.get(sub_key) is sub:
                    del single_word_lookup[sub_key]
            existing_full_names_lower.add(full_name.lower())

        if not chars_to_remove and not merged_ids:
            return main_cast, supporting_cast, set()

        # Remove absorbed characters from both casts
        new_main_cast = [c for c in main_cast if c.id not in chars_to_remove]
        new_supporting_cast = [c for c in supporting_cast if c.id not in chars_to_remove]

        # Promote merged characters from supporting to main cast.
        # The summary explicitly named them, which is a strong signal of narrative importance.
        for char_id in merged_ids:
            char = next((c for c in new_supporting_cast if c.id == char_id), None)
            if char:
                new_supporting_cast = [c for c in new_supporting_cast if c.id != char_id]
                new_main_cast.append(char)
                logger.info(
                    f"V2 Step 5.4.5: Promoted merged '{char.canonical_name}' to main cast "
                    f"(approx {char.mention_count} mentions)"
                )

        return new_main_cast, new_supporting_cast, merged_ids

    def _merge_narrator_placeholder(
        self,
        main_cast: list[Character],
        supporting_cast: list[Character],
        narrator_info,
        text: str,
    ) -> tuple[list[Character], list[Character], any, set[str]]:
        """
        Merge narrator placeholders (e.g., 'the protagonist', 'the narrator') with their actual named character.

        In first-person narratives, the LLM may extract a placeholder like "the protagonist"
        from summaries, when the character has an actual name mentioned in the text.
        This method attempts to identify and merge such cases.

        Args:
            main_cast: List of main cast characters
            supporting_cast: List of supporting characters
            narrator_info: NarratorInfo object from narrator detection
            text: Full text for searching

        Returns:
            Tuple of (updated_main_cast, updated_supporting_cast, updated_narrator_info, merged_char_ids)
        """
        # Only process for first-person narrators with placeholder names
        if narrator_info.pov != "first-person" or not narrator_info.narrator_character_id:
            return main_cast, supporting_cast, narrator_info, set()

        # Find the narrator character
        narrator_char = None
        narrator_in_main = True
        for char in main_cast:
            if char.id == narrator_info.narrator_character_id:
                narrator_char = char
                break

        if not narrator_char:
            # Check supporting cast
            for char in supporting_cast:
                if char.id == narrator_info.narrator_character_id:
                    narrator_char = char
                    narrator_in_main = False
                    break

        if not narrator_char:
            return main_cast, supporting_cast, narrator_info, set()

        # Check if narrator is a placeholder (unnamed or generic descriptor)
        narrator_name_lower = narrator_char.canonical_name.lower()
        placeholder_patterns = [
            "the protagonist",
            "the narrator",
            "narrator",
            "protagonist",
            "main character",
            "the main character",
        ]

        is_placeholder = any(pattern in narrator_name_lower for pattern in placeholder_patterns)

        if not is_placeholder:
            return main_cast, supporting_cast, narrator_info, set()

        logger.info(
            f"Narrator placeholder detected: '{narrator_char.canonical_name}' "
            f"- attempting to find actual character name"
        )

        # Search for the narrator's actual name in all characters
        # Look for a character that:
        # 1. Has a proper name (not another placeholder)
        # 2. Has relatively high mentions in supporting cast OR is in main cast
        # 3. Is addressed by name in first-person context

        all_characters = main_cast + supporting_cast
        candidates = []

        for char in all_characters:
            if char.id == narrator_char.id:
                continue

            char_name_lower = char.canonical_name.lower()

            # Skip other placeholders
            is_other_placeholder = any(
                pattern in char_name_lower for pattern in placeholder_patterns
            )
            if is_other_placeholder:
                continue

            # Skip generic descriptors
            if char_name_lower.startswith("the ") and len(char.canonical_name.split()) <= 3:
                continue

            # Proper name candidate (has capital letters indicating a name)
            if len(char.canonical_name) > 1 and char.canonical_name[0].isupper():
                # Simple heuristic: characters with mentions close to narrator's placeholder mentions
                # are likely the same person (the placeholder captured most first-person references)
                candidates.append(char)

        if not candidates:
            logger.info("No named character candidates found for narrator placeholder")
            return main_cast, supporting_cast, narrator_info, set()

        # PRIORITY 1: Match narrator_info.narrator_name to candidates
        # The narrator detector may have identified the narrator by name even if
        # it couldn't match to main_cast (e.g., "Uncle Bill" identified from summaries)
        merge_target = None
        if narrator_info.narrator_name:
            narrator_name_lower = narrator_info.narrator_name.lower()
            for candidate in candidates:
                candidate_name_lower = candidate.canonical_name.lower()
                # Exact match or partial match (first/last name)
                if (
                    narrator_name_lower == candidate_name_lower
                    or narrator_name_lower in candidate_name_lower
                    or candidate_name_lower in narrator_name_lower
                ):
                    merge_target = candidate
                    logger.info(
                        f"Matched narrator '{narrator_info.narrator_name}' to candidate "
                        f"'{candidate.canonical_name}' by name"
                    )
                    break

        # PRIORITY 2 (FALLBACK): Use mention count heuristic
        # For true placeholders like "the protagonist" where narrator detection
        # couldn't determine a name
        if not merge_target:
            logger.info(
                "No name match found, using mention count heuristic to identify narrator"
            )
            # Sort by mention count (higher is more likely to be the narrator)
            candidates.sort(key=lambda c: c.mention_count, reverse=True)
            # Take the top candidate
            merge_target = candidates[0]

        logger.info(
            f"Merging narrator placeholder '{narrator_char.canonical_name}' "
            f"({narrator_char.mention_count} mentions) "
            f"into '{merge_target.canonical_name}' "
            f"({merge_target.mention_count} mentions)"
        )

        # Merge the placeholder into the target character
        # Transfer mention count (will be recalculated with re-search, but keep for safety)
        merge_target.mention_count += narrator_char.mention_count

        # CRITICAL FIX: Transfer the mentions list for profile generation
        # Combine both characters' mentions into the target
        if narrator_char.mentions:
            if not merge_target.mentions:
                merge_target.mentions = []
            merge_target.mentions.extend(narrator_char.mentions)

        # Transfer narrator flag
        merge_target.is_narrator = True
        merge_target.narrative_role = narrator_char.narrative_role

        # Boost confidence for narrator (they're a key character)
        from ...models import ConfidenceLevel

        merge_target.confidence = ConfidenceLevel.HIGH

        # Add placeholder as an alias (for historical record)
        if narrator_char.canonical_name not in merge_target.aliases:
            merge_target.aliases.append(narrator_char.canonical_name)

        # Transfer any description if target doesn't have one
        if not merge_target.descriptions and narrator_char.descriptions:
            merge_target.descriptions = narrator_char.descriptions

        # Remove the placeholder from main_cast or supporting_cast
        if narrator_in_main:
            main_cast = [c for c in main_cast if c.id != narrator_char.id]
        else:
            supporting_cast = [c for c in supporting_cast if c.id != narrator_char.id]

        # Update narrator_info to point to the merged character
        narrator_info.narrator_character_id = merge_target.id
        narrator_info.narrator_name = merge_target.canonical_name

        logger.info(
            f"Narrator placeholder merge complete: narrator is now '{merge_target.canonical_name}'"
        )

        # Return the ID of the merged character so mention search can be re-run
        return main_cast, supporting_cast, narrator_info, {merge_target.id}

    def _merge_descriptor_into_proper_name(
        self, characters: list[Character]
    ) -> tuple[list[Character], list[str]]:
        """Merge common-noun descriptor characters into their proper-name counterparts.

        Some narratives use descriptive phrases ("the old man", "the young woman") in
        certain chapters instead of the character's proper name. The LLM extracts both
        as separate characters. This step detects and merges them.

        Universal signals used (no book-specific vocabulary):
        - Canonical name has no proper nouns (all-lowercase words)
        - Mention count asymmetry: descriptor has >= 2x mentions of the proper-name target
        - Gender match: inferred from universal title/keyword conventions (Mr./Mrs., man/woman)
        - Role match: both must share the same narrative role
        - Uniqueness: exactly ONE proper-name candidate in the same role+gender category

        Returns (updated_characters, list_of_merged_descriptor_canonical_names).
        NOTE: Aliases from the descriptor are NOT inherited — they may be garbage from
        LLM hallucinations. Only the descriptor's canonical_name is added as an alias.
        """

        def _has_proper_noun(name: str) -> bool:
            """True if name contains at least one proper noun (not a common descriptor word).

            Handles title-cased descriptor phrases like "The Old Man" where every
            content word is a common English word rather than an actual proper name.
            """
            _articles = {"the", "a", "an", "of", "in", "from", "to", "at", "by", "on"}
            # Universal common English words used as person descriptors — NOT proper nouns
            # even when title-cased by the LLM (e.g., "The Old Man", "The Young Woman")
            _common_descriptor_words = {
                "old", "young", "new", "great", "small", "big", "tall", "short",
                "fat", "thin", "poor", "rich", "blind", "deaf", "dark", "fair",
                "pale", "ancient", "aged", "middle", "little", "large", "kind",
                "mad", "wild", "strange", "mysterious", "silent", "lonely",
                "man", "woman", "boy", "girl", "person", "child",
                "stranger", "visitor", "figure", "creature", "ghost",
                "spirit", "shadow", "voice", "soul", "being",
                # Fix FF: Kinship terms — "Father", "Mother", "Brother" etc. when capitalized
                # are still descriptor roles, not proper nouns (e.g., "Father" → Alphonse Frankenstein).
                "father", "mother", "son", "daughter", "brother", "sister",
                "husband", "wife", "uncle", "aunt", "nephew", "niece",
                "grandfather", "grandmother", "grandma", "grandpa",
            }
            for word in name.split():
                clean = word.strip(".,;:'\"()[]")
                if clean and clean[0].isupper():
                    word_lower = clean.lower()
                    if word_lower not in _articles and word_lower not in _common_descriptor_words:
                        return True
            return False

        def _infer_gender(name: str) -> str:
            """Infer gender from universal title prefixes and common-noun keywords."""
            nl = name.lower()
            if "mr." in nl and "mrs." not in nl:
                return "male"
            if any(t in nl for t in ("mrs.", "ms.", "miss ")):
                return "female"
            # Universal gender-marker words in the canonical name itself
            _male_words = {
                "man", "boy", "father", "son", "brother", "husband",
                "gentleman", "sir", "lord", "king", "prince",
            }
            _female_words = {
                "woman", "girl", "mother", "daughter", "sister", "wife",
                "lady", "queen", "princess", "madam", "dame",
            }
            words = set(nl.split())
            if words & _male_words:
                return "male"
            if words & _female_words:
                return "female"
            return "unknown"

        descriptor_chars = []
        proper_name_chars = []

        for c in characters:
            if getattr(c, "is_symbolic", False):
                continue  # symbolic entities (e.g., monkey's paw) are intentional
            if _has_proper_noun(c.canonical_name):
                proper_name_chars.append(c)
            else:
                descriptor_chars.append(c)

        if not descriptor_chars:
            return characters, []

        merged_names: list[str] = []
        to_remove: list[Character] = []

        for desc_char in descriptor_chars:
            desc_gender = _infer_gender(desc_char.canonical_name)
            desc_role = desc_char.role or "supporting"
            desc_mentions = getattr(desc_char, "mention_count", 0) or 0

            # Require meaningful mention count to avoid merging minor descriptors
            if desc_mentions < 5:
                continue

            # Fix EE: Canonical name promotion.
            # If the descriptor character already has a proper-name alias, promote the best one
            # to canonical (moving the old descriptor canonical to aliases).
            # E.g., "Father" with alias "Alphonse Frankenstein" → canonical becomes "Alphonse Frankenstein".
            # This lets the character become a proper_name_char instead of needing a merge target.
            if desc_char.aliases:
                proper_name_aliases = [
                    a for a in desc_char.aliases if _has_proper_noun(a)
                ]
                if proper_name_aliases:
                    # Prefer clean aliases (no parenthetical annotations) over parenthetical ones.
                    # E.g., "De Lacey" is preferred over "De Lacey (the old man)".
                    clean_aliases = [a for a in proper_name_aliases if "(" not in a]
                    candidate_pool = clean_aliases if clean_aliases else proper_name_aliases
                    # Among clean aliases, choose the one with the most words (most specific name)
                    best_alias = max(candidate_pool, key=lambda a: len(a.split()))
                    old_canonical = desc_char.canonical_name
                    logger.info(
                        f"Fix EE: Promoting '{best_alias}' to canonical for '{old_canonical}' "
                        f"(was descriptor, had proper-name alias)"
                    )
                    desc_char.canonical_name = best_alias
                    if old_canonical not in desc_char.aliases:
                        desc_char.aliases.append(old_canonical)
                    desc_char.aliases.remove(best_alias)
                    # Re-classify: now has a proper noun, no longer needs merge
                    proper_name_chars.append(desc_char)
                    continue  # Skip merge attempt; now it's a proper-name char

            # Find proper-name candidates with matching role + gender + fewer mentions
            candidates = [
                p for p in proper_name_chars
                if p.role == desc_role
                and (
                    desc_gender == "unknown"
                    or _infer_gender(p.canonical_name) in (desc_gender, "unknown")
                )
                and (getattr(p, "mention_count", 0) or 0) < desc_mentions
            ]

            # Only merge if there is exactly ONE candidate (conservative: avoid ambiguity)
            if len(candidates) != 1:
                continue

            target = candidates[0]
            target_mentions = getattr(target, "mention_count", 0) or 0

            # Require strong mention asymmetry (descriptor has at least 2x target's mentions)
            if desc_mentions < target_mentions * 2:
                continue

            # Guard CC2: Person-entity descriptor must not merge into non-person entity target.
            # Universal invariant: "the creature" ≠ "the Arctic ice" — different entity categories.
            # Mirrors Rule 0.5b in verify_aliases: person last-nouns cannot merge into non-person targets.
            _PERSON_NOUNS_MERGE_GUARD_CC2 = {
                "man", "woman", "boy", "girl", "person", "figure", "stranger",
                "visitor", "creature", "being", "fellow", "ghost", "spirit", "phantom",
                "specter", "spectre", "soul", "voice", "monster", "daemon", "dæmon",
                "demon", "fiend", "wretch", "villain", "beast", "devil", "ogre", "brute",
                "father", "mother", "son", "daughter", "brother", "sister",
                "husband", "wife", "child", "gentleman", "lady",
            }
            _desc_last_cc2 = desc_char.canonical_name.lower().split()[-1] if desc_char.canonical_name.strip() else ""
            _target_last_cc2 = target.canonical_name.lower().split()[-1] if target.canonical_name.strip() else ""
            _desc_is_person_cc2 = _desc_last_cc2 in _PERSON_NOUNS_MERGE_GUARD_CC2
            _target_is_person_cc2 = _target_last_cc2 in _PERSON_NOUNS_MERGE_GUARD_CC2
            if _desc_is_person_cc2 and not _target_is_person_cc2:
                logger.warning(
                    f"Descriptor merge BLOCKED (Guard CC2): '{desc_char.canonical_name}' is a "
                    f"person entity (last word: '{_desc_last_cc2}') but target "
                    f"'{target.canonical_name}' is not (last word: '{_target_last_cc2}') — "
                    f"person/non-person category mismatch"
                )
                continue

            # Add descriptor's canonical name as alias of target (but NOT its other aliases)
            if target.aliases is None:
                target.aliases = []
            if desc_char.canonical_name not in target.aliases:
                target.aliases.append(desc_char.canonical_name)

            # Attempt to reassign descriptor's other aliases to matching proper-name chars.
            # These "garbage aliases" may legitimately belong to other characters
            # (e.g., "The Old Woman" assigned to "The Old Man" should go to Mrs. White).
            for garbage_alias in (desc_char.aliases or []):
                if _has_proper_noun(garbage_alias):
                    continue  # Only reassign descriptor-style aliases
                alias_gender = _infer_gender(garbage_alias)
                # Find a proper-name candidate that matches by gender (not the merge target)
                alias_candidates = [
                    p for p in proper_name_chars
                    if p is not target
                    and (
                        alias_gender == "unknown"
                        or _infer_gender(p.canonical_name) in (alias_gender, "unknown")
                    )
                ]
                if len(alias_candidates) == 1:
                    alias_target = alias_candidates[0]
                    if alias_target.aliases is None:
                        alias_target.aliases = []
                    alias_lower = garbage_alias.lower()
                    existing_lower = [a.lower() for a in alias_target.aliases]
                    if alias_lower not in existing_lower:
                        alias_target.aliases.append(garbage_alias)
                        logger.info(
                            f"Descriptor merge: reassigning garbage alias '{garbage_alias}' "
                            f"from '{desc_char.canonical_name}' → '{alias_target.canonical_name}'"
                        )

            to_remove.append(desc_char)
            merged_names.append(desc_char.canonical_name)
            logger.info(
                f"Descriptor merge: '{desc_char.canonical_name}' "
                f"(mentions={desc_mentions}, role={desc_role}, gender={desc_gender}) "
                f"→ '{target.canonical_name}' (mentions={target_mentions}). "
                f"Added as alias."
            )

        if not to_remove:
            return characters, merged_names

        result = [c for c in characters if c not in to_remove]
        return result, merged_names

    def _merge_title_variants(self, characters: list[Character]) -> list[Character]:
        """
        Merge characters where one canonical name contains another.

        Example: "Sergeant-Major Morris" contains "Morris" → merge as aliases

        This is a deterministic post-processing step to handle LLM variance
        where titles/ranks are inconsistently included.
        """
        if len(characters) <= 1:
            return characters

        merged = []
        skip_indices = set()

        for i, char1 in enumerate(characters):
            if i in skip_indices:
                continue

            # Check if any other character's name is contained in this one
            for j, char2 in enumerate(characters):
                if i == j or j in skip_indices:
                    continue

                name1_lower = char1.canonical_name.lower()
                name2_lower = char2.canonical_name.lower()

                # Check if one name fully contains the other as a word
                # "Sergeant-Major Morris" contains "Morris"
                if self._name_contains_other(name1_lower, name2_lower):
                    # SAFETY CHECK: Don't merge if both have different title prefixes
                    # (e.g., "Mr. White" and "Mrs. White" are DIFFERENT people)
                    if self._are_different_titled_people(
                        char1.canonical_name, char2.canonical_name
                    ):
                        continue  # Skip this merge - they're different people

                    # Merge char2 into char1
                    logger.info(
                        f"Merging title variant: '{char2.canonical_name}' → "
                        f"'{char1.canonical_name}' (as alias)"
                    )

                    # Add char2's canonical name as an alias of char1
                    if char2.canonical_name not in char1.aliases:
                        if self._is_valid_alias(char2.canonical_name, char1.canonical_name):
                            char1.aliases.append(char2.canonical_name)

                    # Add char2's aliases to char1
                    for alias in char2.aliases:
                        if alias not in char1.aliases and alias != char1.canonical_name:
                            if self._is_valid_alias(alias, char1.canonical_name):
                                char1.aliases.append(alias)

                    skip_indices.add(j)

                elif self._name_contains_other(name2_lower, name1_lower):
                    # SAFETY CHECK: Don't merge if both have different title prefixes
                    if self._are_different_titled_people(
                        char1.canonical_name, char2.canonical_name
                    ):
                        continue  # Skip this merge - they're different people

                    # Merge char1 into char2
                    logger.info(
                        f"Merging title variant: '{char1.canonical_name}' → "
                        f"'{char2.canonical_name}' (as alias)"
                    )

                    # Add char1's canonical name as an alias of char2
                    if char1.canonical_name not in char2.aliases:
                        if self._is_valid_alias(char1.canonical_name, char2.canonical_name):
                            char2.aliases.append(char1.canonical_name)

                    # Add char1's aliases to char2
                    for alias in char1.aliases:
                        if alias not in char2.aliases and alias != char2.canonical_name:
                            if self._is_valid_alias(alias, char2.canonical_name):
                                char2.aliases.append(alias)

                    skip_indices.add(i)
                    break  # Don't process this character further

            if i not in skip_indices:
                merged.append(char1)

        return merged

    def _is_valid_alias(self, alias: str, canonical_name: str) -> bool:
        """
        Check if an alias is valid for the given canonical name.

        Blocks:
        - Inanimate objects (clock, door, etc.) unless canonical also has object keyword
        - Meta-references (narrator, reader, etc.)

        This prevents merge operations from adding invalid aliases that bypass
        MainCastExtractor.verify_aliases().

        Args:
            alias: The proposed alias to validate
            canonical_name: The canonical character name

        Returns:
            True if alias is valid, False if it should be blocked
        """
        alias_lower = alias.lower().strip()
        canonical_lower = canonical_name.lower().strip()

        # Block self-aliases: alias identical to canonical name is redundant
        if alias_lower == canonical_lower:
            return False

        # Block meta-references
        meta_references = {"narrator", "the narrator", "reader", "the reader", "audience", "the audience"}
        if alias_lower in meta_references:
            logger.warning(
                f"BLOCKED alias during merge: '{alias}' is a meta-reference, "
                f"not valid for '{canonical_name}'"
            )
            return False

        # Block inanimate objects (unless canonical also has object keyword)
        object_keywords = {
            "clock", "bell", "door", "window", "mirror", "portrait", "painting",
            "statue", "coffin", "casket", "sword", "dagger", "knife", "weapon",
            "chair", "table", "bed", "chest", "book", "letter", "ring", "crown",
            "chandelier", "candle", "torch", "lamp"
        }

        # Extract core words (after removing articles)
        alias_words = set(alias_lower.replace("the ", "").replace("a ", "").replace("an ", "").split())
        canonical_words = set(canonical_lower.replace("the ", "").replace("a ", "").replace("an ", "").split())

        alias_has_object = bool(alias_words & object_keywords)
        canonical_has_object = bool(canonical_words & object_keywords)

        if alias_has_object and not canonical_has_object:
            logger.warning(
                f"BLOCKED alias during merge: '{alias}' contains object keyword "
                f"({alias_words & object_keywords}), not valid for '{canonical_name}'"
            )
            return False

        # Block plural group noun aliases for singular characters.
        # Plural agent/role nouns (courtiers, musicians, revellers, soldiers) describe groups,
        # never individual characters. Universal linguistic invariant: article+plural_noun = group.
        # Exception: if the canonical is itself a group noun (collective character), allow it.
        _PLURAL_SUFFIXES = ("ers", "ors", "ians", "ists", "ants", "ents", "iers", "ees", "smen", "ies", "stra")
        _ARTICLE_WORDS = {"the", "a", "an", "of", "in", "from", "at", "by", "with"}
        alias_tokens_p = [
            w.strip(".,;:'\"()")
            for w in alias_lower.split()
            if w.strip(".,;:'\"()") and w.strip(".,;:'\"()") not in _ARTICLE_WORDS
        ]
        if alias_tokens_p:
            alias_head_p = alias_tokens_p[-1]
            is_plural_group = any(
                alias_head_p.endswith(sfx) and len(alias_head_p) > len(sfx) + 1
                for sfx in _PLURAL_SUFFIXES
            )
            if is_plural_group:
                canonical_head_p = canonical_lower.strip(".,;:'\"()").split()[-1]
                canonical_is_group = any(
                    canonical_head_p.endswith(sfx) and len(canonical_head_p) > len(sfx) + 1
                    for sfx in _PLURAL_SUFFIXES
                )
                if not canonical_is_group:
                    logger.warning(
                        f"BLOCKED alias during merge: '{alias}' is a plural group noun, "
                        f"not valid alias for individual character '{canonical_name}'"
                    )
                    return False

        return True

    def _clean_invalid_aliases(self, characters: list[Character]) -> None:
        """
        Remove invalid aliases from character list.

        This is a final cleanup pass applied after all merge operations to catch
        any invalid aliases that slipped through. Modifies characters in-place.

        Args:
            characters: List of Character objects to clean
        """
        for char in characters:
            original_count = len(char.aliases)
            # Filter out invalid aliases
            char.aliases = [
                alias for alias in char.aliases
                if self._is_valid_alias(alias, char.canonical_name)
            ]
            removed_count = original_count - len(char.aliases)
            if removed_count > 0:
                logger.info(
                    f"Cleaned {removed_count} invalid alias(es) from '{char.canonical_name}': "
                    f"final aliases = {char.aliases}"
                )

    def _name_contains_other(self, longer_name: str, shorter_name: str) -> bool:
        """
        Check if longer_name contains shorter_name as a complete word.

        Examples:
        - "sergeant-major morris" contains "morris" → True
        - "mr. white" contains "white" → True
        - "whitehouse" contains "white" → False (not word boundary)
        """
        import re

        # Escape special regex characters in shorter_name
        escaped = re.escape(shorter_name)

        # Match as a complete word (with word boundaries or punctuation)
        pattern = r"(?:^|[\s\-\.])" + escaped + r"(?:$|[\s\-\.])"
        return bool(re.search(pattern, longer_name))

    def _strip_title(self, name: str) -> str:
        """
        Strip honorific titles from a name.

        Examples:
        - "Mr. Smith" → "Smith"
        - "Mrs. Jones" → "Jones"
        - "Dr. Jekyll" → "Jekyll"
        """
        import re

        # List of common titles
        titles = [
            r"\bMr\.",
            r"\bMrs\.",
            r"\bMs\.",
            r"\bMiss\b",
            r"\bDr\.",
            r"\bDoctor\b",
            r"\bProf\.",
            r"\bProfessor\b",
            r"\bLord\b",
            r"\bLady\b",
            r"\bSir\b",
            r"\bReverend\b",
            r"\bRev\.",
        ]

        # Remove any leading title
        for title in titles:
            name = re.sub(f"^{title}\\s+", "", name, flags=re.IGNORECASE)

        return name.strip()

    def _are_different_titled_people(self, name1: str, name2: str) -> bool:
        """
        Check if two names represent different people with different title prefixes.

        This prevents merging "Mr. White" with "Mrs. White" (husband and wife),
        while still allowing "Sergeant-Major Morris" to merge with "Morris".

        Rules:
        - If both names start with DIFFERENT honorific titles (Mr./Mrs./Miss/Ms./Dr.)
          AND the stripped names are identical → they are DIFFERENT people
        - Otherwise, allow the merge

        Examples:
        - "Mr. White" + "Mrs. White" → True (different people)
        - "Mr. Smith" + "Dr. Smith" → True (different people)
        - "Sergeant-Major Morris" + "Morris" → False (same person)
        - "Mr. White" + "White" → False (same person)

        Returns:
            True if they're different titled people (DON'T merge)
            False if they're the same person or safe to merge
        """
        import re

        # Honorific titles that indicate distinct individuals when different
        honorific_prefixes = [
            r"^(Mr\.|Mrs\.|Miss|Ms\.|Dr\.|M\.)\s+",  # Added M. for French Monsieur
        ]

        # Extract titles and stripped names
        title1 = None
        title2 = None
        stripped1 = name1
        stripped2 = name2

        for pattern in honorific_prefixes:
            match1 = re.match(pattern, name1, flags=re.IGNORECASE)
            if match1:
                title1 = match1.group(1).lower()
                stripped1 = re.sub(pattern, "", name1, flags=re.IGNORECASE).strip()

            match2 = re.match(pattern, name2, flags=re.IGNORECASE)
            if match2:
                title2 = match2.group(1).lower()
                stripped2 = re.sub(pattern, "", name2, flags=re.IGNORECASE).strip()

        # If both have honorific titles, check for different people scenarios
        if title1 and title2:
            # Case 1: Different surnames with any title = different people
            # "M. Waldman" vs "M. Krempe" are different people (same title, different surnames)
            # "Mr. Sloane" vs "Mr. McKee" are different people
            if stripped1.lower() != stripped2.lower():
                return True  # Different titled people - DON'T merge

            # Case 2: Same surname, different title = different people (spouses)
            # "Mr. White" vs "Mrs. White" are different people (same surname, different titles)
            if title1 != title2:
                return True  # Different titled people - DON'T merge

        # Otherwise, safe to merge
        return False

    def _merge_same_firstname_variants(
        self,
        main_cast: list[Character],
    ) -> list[Character]:
        """
        Pre-merge characters that share the same first name but have different last names.

        This handles cases like maiden/married name variants where a character
        appears under multiple full names sharing the same first name.

        Characters who share a last name but have DIFFERENT first names are
        typically different people (e.g., spouses, siblings). But when multiple
        matches share the SAME first name, they're probably the same person
        with name variants (maiden name, married name, title variations).

        Returns:
            Updated list with same-firstname variants merged
        """
        if len(main_cast) <= 1:
            return main_cast

        # Group multi-word names by their first name (lowercase)
        firstname_to_fullnames: dict[str, list[int]] = {}
        single_word_names: dict[str, int] = {}  # first_name_lower -> index

        for idx, char in enumerate(main_cast):
            name = char.canonical_name.strip()
            if not name:
                continue

            parts = name.split()
            first_name = parts[0].lower()

            if len(parts) == 1:
                # Single-word name (potential first-name-only reference)
                single_word_names[first_name] = idx
            else:
                # Multi-word name (full name)
                if first_name not in firstname_to_fullnames:
                    firstname_to_fullnames[first_name] = []
                firstname_to_fullnames[first_name].append(idx)

        chars_to_remove = set()

        # For each first name that has multiple full-name variants, merge them
        for first_name, indices in firstname_to_fullnames.items():
            if len(indices) < 2:
                continue

            # Multiple full names share the same first name
            # These are likely the same person with maiden/married name variants
            [(idx, main_cast[idx]) for idx in indices]

            # Find the canonical entry: prefer the one with most mentions
            canonical_idx = max(indices, key=lambda i: main_cast[i].mention_count)
            canonical_char = main_cast[canonical_idx]

            logger.info(
                f"Same-firstname merge: '{first_name}' has {len(indices)} variants, "
                f"using '{canonical_char.canonical_name}' as canonical"
            )

            # Merge others into canonical
            for idx in indices:
                if idx == canonical_idx:
                    continue
                other = main_cast[idx]

                # Add other's canonical name as alias
                if other.canonical_name not in canonical_char.aliases:
                    logger.info(
                        f"  Merging '{other.canonical_name}' → '{canonical_char.canonical_name}' as alias"
                    )
                    canonical_char.aliases.append(other.canonical_name)

                # Merge other's aliases too
                for alias in other.aliases:
                    if (
                        alias not in canonical_char.aliases
                        and alias != canonical_char.canonical_name
                    ):
                        canonical_char.aliases.append(alias)

                # Accumulate mention count
                canonical_char.mention_count += other.mention_count

                chars_to_remove.add(idx)

            # If there's a single-word name matching this first name, merge it too
            if first_name in single_word_names:
                single_idx = single_word_names[first_name]
                if single_idx not in chars_to_remove:
                    single_char = main_cast[single_idx]
                    if single_char.canonical_name not in canonical_char.aliases:
                        logger.info(
                            f"  Also merging first-name-only '{single_char.canonical_name}' → "
                            f"'{canonical_char.canonical_name}' as alias"
                        )
                        canonical_char.aliases.append(single_char.canonical_name)
                    canonical_char.mention_count += single_char.mention_count
                    chars_to_remove.add(single_idx)

        # Build result list
        result = [c for i, c in enumerate(main_cast) if i not in chars_to_remove]

        if chars_to_remove:
            logger.info(f"Same-firstname merge: removed {len(chars_to_remove)} duplicate entries")

        return result

    def _deduplicate_alias_canonical_conflicts(
        self,
        main_cast: list[Character],
    ) -> tuple[list[Character], set[str]]:
        """
        Deduplicate characters where one character's alias matches another's canonical name.

        Example: "Myrtle Wilson" (canonical) + "Mrs. Wilson" (canonical, alias="Myrtle Wilson")
        → These are the SAME person, merge them

        This handles cases where the LLM extracted both a character and a variant reference
        as separate characters, but correctly noted one as an alias of the other.

        Returns:
            Tuple of (updated_main_cast, char_ids_with_new_aliases)
        """
        if len(main_cast) <= 1:
            return main_cast, set()

        chars_to_remove = set()
        chars_with_new_aliases = set()

        # Build a map of canonical_name -> character index
        canonical_map = {char.canonical_name.lower(): idx for idx, char in enumerate(main_cast)}

        for idx, char in enumerate(main_cast):
            if idx in chars_to_remove:
                continue

            # Check if any of this character's aliases match another character's canonical name
            for alias in char.aliases:
                alias_lower = alias.lower()

                # Does this alias match another character's canonical name?
                if alias_lower in canonical_map:
                    other_idx = canonical_map[alias_lower]

                    # Skip if it's the same character (alias matches own canonical name)
                    if other_idx == idx:
                        continue

                    # Skip if already marked for removal
                    if other_idx in chars_to_remove:
                        continue

                    other_char = main_cast[other_idx]

                    # MERGE: The character whose canonical name appears as an alias
                    # should be merged INTO the character that has it as an alias
                    #
                    # Example: "Mrs. Wilson" has alias "Myrtle Wilson"
                    # → Merge "Myrtle Wilson" INTO "Mrs. Wilson"
                    #
                    # BUT: We want to keep the one with MORE mentions as canonical
                    if char.mention_count >= other_char.mention_count:
                        # Keep current char, merge other into it
                        logger.info(
                            f"Alias-canonical conflict: merging '{other_char.canonical_name}' "
                            f"({other_char.mention_count} mentions) → '{char.canonical_name}' "
                            f"({char.mention_count} mentions) - alias match"
                        )

                        # Add other's canonical name as alias (if not already there)
                        if other_char.canonical_name not in char.aliases:
                            char.aliases.append(other_char.canonical_name)

                        # Merge other's aliases too
                        for other_alias in other_char.aliases:
                            if (
                                other_alias not in char.aliases
                                and other_alias.lower() != char.canonical_name.lower()
                            ):
                                char.aliases.append(other_alias)

                        chars_with_new_aliases.add(char.id)
                        chars_to_remove.add(other_idx)
                    else:
                        # Keep other char, merge current into it
                        logger.info(
                            f"Alias-canonical conflict: merging '{char.canonical_name}' "
                            f"({char.mention_count} mentions) → '{other_char.canonical_name}' "
                            f"({other_char.mention_count} mentions) - alias match"
                        )

                        # Add current's canonical name as alias (if not already there)
                        if char.canonical_name not in other_char.aliases:
                            other_char.aliases.append(char.canonical_name)

                        # Merge current's aliases too
                        for curr_alias in char.aliases:
                            if (
                                curr_alias not in other_char.aliases
                                and curr_alias.lower() != other_char.canonical_name.lower()
                            ):
                                other_char.aliases.append(curr_alias)

                        chars_with_new_aliases.add(other_char.id)
                        chars_to_remove.add(idx)
                        break  # Don't process this char anymore

        # Remove merged characters
        updated_main_cast = [
            char for idx, char in enumerate(main_cast) if idx not in chars_to_remove
        ]

        if chars_to_remove:
            logger.info(
                f"Alias-canonical deduplication: removed {len(chars_to_remove)} duplicate entries"
            )

        return updated_main_cast, chars_with_new_aliases

    def _split_wrongly_merged_titled_characters(
        self,
        main_cast: list[Character],
    ) -> tuple[list[Character], int]:
        """
        Defensive fix: Split characters that have aliases with different title+surname combinations.

        This handles LLM hallucinations where "M. Waldman" incorrectly gets "M. Krempe" as an alias,
        despite explicit prompt instructions forbidding this.

        Examples of splits:
        - "M. Waldman" with alias "M. Krempe" → split into two separate characters
        - "Mr. Sloane" with alias "Mr. McKee" → split into two separate characters

        Returns:
            Tuple of (updated_main_cast, number_of_splits)
        """
        import re

        title_pattern = r"^(Mr\.|Mrs\.|Miss|Ms\.|Dr\.|M\.)\s+(.+)$"
        split_count = 0
        new_characters = []

        for char in main_cast:
            # Check if canonical name has a title
            canonical_match = re.match(title_pattern, char.canonical_name, flags=re.IGNORECASE)
            if not canonical_match:
                # No title in canonical name - nothing to split
                new_characters.append(char)
                continue

            canonical_title = canonical_match.group(1).lower()
            canonical_surname = canonical_match.group(2).strip().lower()

            # Check each alias for different title+surname combinations
            aliases_to_split = []
            valid_aliases = []

            for alias in char.aliases:
                alias_match = re.match(title_pattern, alias, flags=re.IGNORECASE)
                if not alias_match:
                    # Alias doesn't have a title
                    # Check if this is a bare surname of a different person
                    # (e.g., canonical="M. Waldman", alias="Krempe" - should split)
                    # vs. (e.g., canonical="M. Waldman", alias="Professor" - should keep)
                    alias_lower = alias.strip().lower()
                    # If the alias is a single capitalized word that doesn't match the canonical surname,
                    # it's likely a different person's surname
                    if (
                        len(alias.split()) == 1  # Single word
                        and alias[0].isupper()  # Capitalized (likely a name)
                        and alias_lower != canonical_surname  # Different from canonical surname
                        and alias_lower not in canonical_surname
                    ):  # Not a substring of canonical surname
                        logger.warning(
                            f"SPLIT: '{alias}' cannot be alias of '{char.canonical_name}' "
                            f"(untitled surname doesn't match canonical surname '{canonical_surname}')"
                        )
                        aliases_to_split.append(alias)
                        split_count += 1
                    else:
                        # Keep as valid alias (could be a title, descriptor, etc.)
                        valid_aliases.append(alias)
                    continue

                alias_title = alias_match.group(1).lower()
                alias_surname = alias_match.group(2).strip().lower()

                # Check if this is a different titled person
                # Different surnames = different people (even if same title)
                # Different titles with same surname = different people (spouses)
                if alias_surname != canonical_surname:
                    logger.warning(
                        f"SPLIT: '{alias}' cannot be alias of '{char.canonical_name}' "
                        f"(different surnames: '{alias_surname}' vs '{canonical_surname}')"
                    )
                    aliases_to_split.append(alias)
                    split_count += 1
                elif alias_title != canonical_title:
                    logger.warning(
                        f"SPLIT: '{alias}' cannot be alias of '{char.canonical_name}' "
                        f"(same surname but different titles: '{alias_title}' vs '{canonical_title}')"
                    )
                    aliases_to_split.append(alias)
                    split_count += 1
                else:
                    # Same title and surname - valid alias
                    valid_aliases.append(alias)

            # Update character with only valid aliases
            char.aliases = valid_aliases
            new_characters.append(char)

            # Create new character entries for the split aliases
            # These will be minimal stubs that may get fleshed out in later processing
            for split_alias in aliases_to_split:
                new_char = Character(
                    id=f"split_{split_alias.lower().replace(' ', '_').replace('.', '')}",
                    canonical_name=split_alias,
                    aliases=[],
                    role="supporting",
                    mention_count=0,  # Will be updated by mention search
                    confidence="medium",
                )
                new_characters.append(new_char)
                logger.info(f"Created new character from split alias: '{split_alias}'")

        return new_characters, split_count

    def _split_semantic_conflicts(
        self,
        main_cast: list[Character],
    ) -> tuple[list[Character], int]:
        """
        Defensive fix: Split characters that have semantically conflicting aliases.

        This handles LLM hallucinations where descriptive terms from conflicting semantic
        categories get merged as aliases (e.g., "the creature" as alias of "the old man").

        Semantic conflict rules:
        - Creature-related terms (creature, monster, fiend, daemon, wretch) should NEVER
          be aliases of human descriptors (man, woman, boy, girl, old man, etc.)
        - These are fundamentally different types of entities

        Examples of splits:
        - "the old man (De Lacey)" with alias "the creature" → split into two separate characters
        - "the woman" with alias "the monster" → split into two separate characters

        Returns:
            Tuple of (updated_main_cast, number_of_splits)
        """

        # Define semantic conflict groups
        # Group 1: Supernatural/created beings
        creature_terms = {"creature", "monster", "fiend", "daemon", "dæmon", "wretch", "being",
                          "demon", "devil", "beast", "brute", "ogre", "phantom", "specter",
                          "spectre", "ghost", "spirit"}

        # Group 2: Human descriptors (when used in "the X" pattern)
        # These should NOT merge with creature terms.
        # Includes age/gender forms, social roles, and occupation titles that
        # unambiguously denote human persons (universal across genres and eras).
        human_descriptors = {
            "man",
            "woman",
            "boy",
            "girl",
            "child",
            "person",
            "old man",
            "young man",
            "old woman",
            "young woman",
            "gentleman",
            "lady",
            "peasant",
            "sailor",
            "cottager",
            # Occupation/civic titles — unambiguously human in any literary work
            "merchant",
            "magistrate",
            "officer",
            "soldier",
            # Family roles — unambiguously human
            "father",
            "mother",
            "son",
            "daughter",
            "brother",
            "sister",
            "husband",
            "wife",
        }

        # Group 3: Non-living environment/object terms.
        # These should NEVER have creature/person aliases — they represent settings or things.
        # Universal invariant: natural phenomena and objects are distinct from sentient beings.
        non_living_terms = {
            "ice", "sea", "ocean", "water", "river", "lake", "mist", "fog", "wind", "storm",
            "forest", "wood", "mountain", "cliff", "cave", "snow", "frost", "darkness",
            "light", "fire", "void", "abyss", "shadow", "nature", "earth", "sky", "air",
            "wave", "tide", "current", "glacier", "wilderness", "landscape", "terrain",
            "cold", "heat", "silence", "night",
        }

        split_count = 0
        new_characters = []

        for char in main_cast:
            canonical_lower = char.canonical_name.lower().strip()

            # Extract descriptor from "the X" or "X (surname)" patterns
            canonical_descriptor = None
            if canonical_lower.startswith("the "):
                # "the creature", "the old man", etc.
                canonical_descriptor = canonical_lower[4:].strip()
                # Handle patterns like "the old man (De Lacey)" - extract just "old man"
                if " (" in canonical_descriptor:
                    canonical_descriptor = canonical_descriptor.split(" (")[0].strip()

            # Determine canonical's semantic group
            canonical_is_creature = canonical_descriptor and any(
                term in canonical_descriptor for term in creature_terms
            )
            canonical_is_human = canonical_descriptor and any(
                canonical_descriptor == desc or canonical_descriptor.endswith(" " + desc)
                for desc in human_descriptors
            )
            # Non-living: check if last word of canonical descriptor is an environment/object term
            _canon_desc_last = canonical_descriptor.split()[-1] if canonical_descriptor else ""
            canonical_is_non_living = (
                canonical_descriptor is not None
                and _canon_desc_last in non_living_terms
                and not canonical_is_creature
                and not canonical_is_human
            )

            # Check each alias for semantic conflicts
            aliases_to_split = []
            valid_aliases = []

            for alias in char.aliases:
                alias_lower = alias.lower().strip()

                # Extract descriptor from alias
                alias_descriptor = None
                if alias_lower.startswith("the "):
                    alias_descriptor = alias_lower[4:].strip()
                    if " (" in alias_descriptor:
                        alias_descriptor = alias_descriptor.split(" (")[0].strip()

                # Determine alias's semantic group
                alias_is_creature = alias_descriptor and any(
                    term in alias_descriptor for term in creature_terms
                )
                alias_is_human = alias_descriptor and any(
                    alias_descriptor == desc or alias_descriptor.endswith(" " + desc)
                    for desc in human_descriptors
                )
                _alias_desc_last = alias_descriptor.split()[-1] if alias_descriptor else ""
                alias_is_non_living = (
                    alias_descriptor is not None
                    and _alias_desc_last in non_living_terms
                    and not alias_is_creature
                    and not alias_is_human
                )

                # Check for semantic conflict
                conflict = False
                if canonical_is_creature and alias_is_human:
                    conflict = True
                    logger.warning(
                        f"SEMANTIC CONFLICT: '{alias}' (human descriptor) cannot be alias of "
                        f"'{char.canonical_name}' (creature-related term)"
                    )
                elif canonical_is_human and alias_is_creature:
                    conflict = True
                    logger.warning(
                        f"SEMANTIC CONFLICT: '{alias}' (creature-related term) cannot be alias of "
                        f"'{char.canonical_name}' (human descriptor)"
                    )
                elif canonical_is_non_living and (alias_is_creature or alias_is_human):
                    # Non-living environment/object cannot have sentient-being aliases.
                    # Universal invariant: "the Arctic ice" ≠ "the creature" or "the man".
                    conflict = True
                    _alias_type = "creature" if alias_is_creature else "human descriptor"
                    logger.warning(
                        f"SEMANTIC CONFLICT: '{alias}' ({_alias_type}) cannot be alias of "
                        f"'{char.canonical_name}' (non-living entity, last word: '{_canon_desc_last}')"
                    )
                elif (alias_is_non_living) and (canonical_is_creature or canonical_is_human):
                    # Reverse: non-living alias cannot describe a sentient being canonical.
                    conflict = True
                    _canon_type = "creature" if canonical_is_creature else "human descriptor"
                    logger.warning(
                        f"SEMANTIC CONFLICT: '{alias}' (non-living entity, last word: '{_alias_desc_last}') "
                        f"cannot be alias of '{char.canonical_name}' ({_canon_type})"
                    )

                if conflict:

                    aliases_to_split.append(alias)
                    split_count += 1
                else:
                    valid_aliases.append(alias)

            # Update character with only valid aliases
            char.aliases = valid_aliases
            new_characters.append(char)

            # Create new character entries for the semantically conflicting aliases
            for split_alias in aliases_to_split:
                new_char = Character(
                    id=f"split_{split_alias.lower().replace(' ', '_').replace('.', '').replace('(', '').replace(')', '')}",
                    canonical_name=split_alias,
                    aliases=[],
                    role="supporting",
                    mention_count=0,  # Will be updated by mention search
                    confidence="medium",
                )
                new_characters.append(new_char)
                logger.info(
                    f"Created new character from semantically conflicting alias: '{split_alias}'"
                )

        return new_characters, split_count

    def _merge_within_main_cast(
        self,
        main_cast: list[Character],
    ) -> tuple[list[Character], set[str]]:
        """
        Merge characters within main cast that are variants of each other.

        Handles four patterns:
        1. Middle initial variants: "George B. Wilson" → alias of "George Wilson"
        2. Last-name-only → Full name: "Wilson" (65 mentions) → alias of "George B. Wilson"
        3. Spelling variants: "Wolfsheim" ↔ "Wolfshiem" (85% fuzzy match)
        4. First-name-only → Full name: "George" → alias of "George B. Wilson"

        Returns:
            Tuple of (updated_main_cast, char_ids_with_new_aliases)
        """
        import re

        chars_to_remove = set()
        chars_with_new_aliases = set()

        # Pass -1: Merge exact canonical name duplicates
        # Universal invariant: two characters cannot have the same canonical name.
        # When the LLM emits duplicates (e.g., "Benny" twice in Pass 1), collapse them.
        for idx, char in enumerate(main_cast):
            if idx in chars_to_remove:
                continue
            for other_idx in range(idx + 1, len(main_cast)):
                if other_idx in chars_to_remove:
                    continue
                other_char = main_cast[other_idx]
                if char.canonical_name.lower() == other_char.canonical_name.lower():
                    # Keep the one with more mentions; merge aliases and remove the other
                    keep, drop, drop_idx = (
                        (char, other_char, other_idx)
                        if char.mention_count >= other_char.mention_count
                        else (other_char, char, idx)
                    )
                    for alias in ([drop.canonical_name] + list(drop.aliases or [])):
                        if alias.lower() != keep.canonical_name.lower() and alias not in keep.aliases:
                            keep.aliases.append(alias)
                    chars_with_new_aliases.add(keep.id)
                    chars_to_remove.add(drop_idx)
                    logger.info(
                        f"Dedup exact canonical match: '{drop.canonical_name}' (id={drop.id}) "
                        f"→ merged into '{keep.canonical_name}' (id={keep.id})"
                    )
                    if drop_idx == idx:
                        break  # current char was merged away; stop inner loop

        # Pass 0: Merge middle initial variants
        # "George B. Wilson" (1 mention) → alias of "George Wilson" (91 mentions)
        for idx, char in enumerate(main_cast):
            if idx in chars_to_remove:
                continue

            char_name = char.canonical_name.strip()
            if not char_name or " " not in char_name:
                continue  # Skip empty or single-word names

            # Check if this name has a middle initial pattern: "FirstName I. LastName"
            # Middle initial pattern: single letter followed by period
            middle_initial_pattern = r"^(\w+)\s+([A-Z]\.)\s+(.+)$"
            match = re.match(middle_initial_pattern, char_name)
            if not match:
                continue  # Not a middle initial pattern

            firstname = match.group(1)
            match.group(2)
            lastname = match.group(3)

            # Construct the name without middle initial
            name_without_middle = f"{firstname} {lastname}"

            # Check if this matches any other character
            for other_idx, other_char in enumerate(main_cast):
                if other_idx == idx or other_idx in chars_to_remove:
                    continue

                other_name = other_char.canonical_name.strip()
                if other_name.lower() == name_without_middle.lower():
                    # Found a match! Merge the one with FEWER mentions into the one with MORE
                    if char.mention_count <= other_char.mention_count:
                        # Current char (with middle initial) has fewer mentions → make it alias
                        if char_name not in other_char.aliases:
                            logger.info(
                                f"Merging middle initial variant: '{char_name}' ({char.mention_count} mentions) "
                                f"→ '{other_char.canonical_name}' ({other_char.mention_count} mentions) as alias"
                            )
                            other_char.aliases.append(char_name)
                            # Also transfer char's aliases
                            for alias in char.aliases:
                                if alias not in other_char.aliases:
                                    other_char.aliases.append(alias)
                            chars_with_new_aliases.add(other_char.id)
                        chars_to_remove.add(idx)
                    else:
                        # Other char (without middle initial) has fewer mentions → make it alias
                        if other_name not in char.aliases:
                            logger.info(
                                f"Merging middle initial variant: '{other_char.canonical_name}' ({other_char.mention_count} mentions) "
                                f"→ '{char_name}' ({char.mention_count} mentions) as alias"
                            )
                            char.aliases.append(other_name)
                            # Also transfer other's aliases
                            for alias in other_char.aliases:
                                if alias not in char.aliases:
                                    char.aliases.append(alias)
                            chars_with_new_aliases.add(char.id)
                        chars_to_remove.add(other_idx)
                    break  # Only merge with first match

        # Pass 0a: Merge first-initial-only variants
        # "R. Walton" → alias of "Robert Walton" (initial + last name matches full name)
        _first_initial_re = re.compile(r"^([A-Z])\.\s+(.+)$")
        for idx, char in enumerate(main_cast):
            if idx in chars_to_remove:
                continue

            char_name = char.canonical_name.strip()
            m0a = _first_initial_re.match(char_name)
            if not m0a:
                continue  # Not an initial + last name pattern

            initial = m0a.group(1)
            lastname = m0a.group(2).strip()

            # Find full-name characters where: first letter of firstname matches
            # the initial AND the last word of their name matches our lastname
            candidates = []
            for other_idx, other_char in enumerate(main_cast):
                if other_idx == idx or other_idx in chars_to_remove:
                    continue
                other_name = other_char.canonical_name.strip()
                other_parts = other_name.split()
                if len(other_parts) < 2:
                    continue
                other_firstname = other_parts[0].strip(".,;:")
                other_lastname = other_parts[-1].strip(".,;:")
                if (
                    other_firstname
                    and other_firstname[0].upper() == initial
                    and other_lastname.lower() == lastname.lower()
                ):
                    candidates.append(other_idx)

            if len(candidates) == 1:
                other_idx = candidates[0]
                other_char = main_cast[other_idx]
                if char_name not in other_char.aliases:
                    logger.info(
                        f"Merging first-initial variant: '{char_name}' ({char.mention_count} mentions) "
                        f"→ '{other_char.canonical_name}' ({other_char.mention_count} mentions) as alias"
                    )
                    other_char.aliases.append(char_name)
                    for alias in char.aliases:
                        if alias not in other_char.aliases:
                            other_char.aliases.append(alias)
                    chars_with_new_aliases.add(other_char.id)
                chars_to_remove.add(idx)

        # Pass 1: Merge last-name-only and title-variant characters
        for idx, char in enumerate(main_cast):
            if idx in chars_to_remove:
                continue

            char_name = char.canonical_name.strip()
            if not char_name or " " in char_name:
                continue  # Skip empty or multi-word names

            # This is a single-word name (potential last name or first name)
            # Check if it matches the last word OR title-stripped version of any OTHER main cast character

            matches = []
            for other_idx, other_char in enumerate(main_cast):
                if other_idx == idx or other_idx in chars_to_remove:
                    continue

                other_name = other_char.canonical_name.strip()
                if not other_name or " " not in other_name:
                    continue  # Only match against multi-word names

                # First check: exact match with title-stripped version
                # E.g., "Sloane" matches "Mr. Sloane" after stripping "Mr."
                other_title_stripped = self._strip_title(other_name)
                if char_name.lower() == other_title_stripped.lower():
                    matches.append((other_idx, "exact_title_stripped"))
                    continue

                # Second check: last name match
                other_parts = other_name.split()
                other_lastname = other_parts[-1].strip(".,;:")

                # Exact last name match
                if char_name.lower() == other_lastname.lower():
                    matches.append((other_idx, "exact_lastname"))
                    continue

                # Fuzzy last name match (handles Wolfsheim/Wolfshiem)
                if names_similar(char_name, other_lastname):
                    matches.append((other_idx, "fuzzy_lastname"))
                    continue

                # Check first name match (if other_name has multiple parts)
                if len(other_parts) >= 2:
                    other_firstname = other_parts[0].strip(".,;:")
                    if char_name.lower() == other_firstname.lower():
                        matches.append((other_idx, "exact_firstname"))

            # Merge if exactly ONE match (avoids ambiguity like "Wilson" matching both George and Myrtle)
            if len(matches) == 1:
                other_idx, match_type = matches[0]
                other_char = main_cast[other_idx]

                # Add single-word name as alias to the full name character
                if char_name not in other_char.aliases:
                    logger.info(
                        f"Merging within main cast: '{char_name}' ({char.mention_count} mentions) "
                        f"→ '{other_char.canonical_name}' as alias ({match_type})"
                    )
                    other_char.aliases.append(char_name)
                    chars_with_new_aliases.add(other_char.id)

                # Mark single-word character for removal
                chars_to_remove.add(idx)

        # Pass 2: Merge spelling variants (e.g., "Meyer Wolfsheim" ↔ "Meyer Wolfshiem")
        for idx, char in enumerate(main_cast):
            if idx in chars_to_remove:
                continue

            char_name = char.canonical_name.strip()
            if not char_name:
                continue

            for other_idx, other_char in enumerate(main_cast):
                if other_idx <= idx or other_idx in chars_to_remove:
                    continue  # Only check each pair once

                other_name = other_char.canonical_name.strip()
                if not other_name:
                    continue

                # Check if names are very similar (spelling variants)
                if names_similar(char_name, other_name):  # 85% similar
                    # SAFETY CHECK: Don't merge if both have different title prefixes
                    # (e.g., "Mr. White" vs "Mrs. White" are different people)
                    if self._are_different_titled_people(char_name, other_name):
                        continue  # Skip - they're different people

                    # Calculate similarity for logging
                    similarity = string_similarity(char_name, other_name)

                    # Merge the one with FEWER mentions into the one with MORE mentions
                    if char.mention_count >= other_char.mention_count:
                        # Merge other → char
                        if other_name not in char.aliases:
                            logger.info(
                                f"Merging spelling variant within main cast: '{other_name}' "
                                f"({other_char.mention_count} mentions) → '{char_name}' "
                                f"({char.mention_count} mentions) as alias (similarity={similarity:.2f})"
                            )
                            char.aliases.append(other_name)
                            # Also merge other's existing aliases
                            for alias in other_char.aliases:
                                if alias not in char.aliases:
                                    char.aliases.append(alias)
                            chars_with_new_aliases.add(char.id)
                        chars_to_remove.add(other_idx)
                    else:
                        # Merge char → other
                        if char_name not in other_char.aliases:
                            logger.info(
                                f"Merging spelling variant within main cast: '{char_name}' "
                                f"({char.mention_count} mentions) → '{other_name}' "
                                f"({other_char.mention_count} mentions) as alias (similarity={similarity:.2f})"
                            )
                            other_char.aliases.append(char_name)
                            # Also merge char's existing aliases
                            for alias in char.aliases:
                                if alias not in other_char.aliases:
                                    other_char.aliases.append(alias)
                            chars_with_new_aliases.add(other_char.id)
                        chars_to_remove.add(idx)
                        break  # Don't process this char anymore

        # Remove merged characters from Pass 2
        updated_main_cast = [
            char for idx, char in enumerate(main_cast) if idx not in chars_to_remove
        ]

        # Pass 3: Re-run last-name matching after spelling variants are merged
        # This handles cases like "Wolfshiem" which initially had ambiguous matches,
        # but after Pass 2 merging has only one match remaining
        chars_to_remove_pass3 = set()

        for idx, char in enumerate(updated_main_cast):
            char_name = char.canonical_name.strip()
            if not char_name or " " in char_name:
                continue  # Skip empty or multi-word names

            # Check if this single-word name now has exactly ONE match
            matches = []
            for other_idx, other_char in enumerate(updated_main_cast):
                if other_idx == idx:
                    continue

                other_name = other_char.canonical_name.strip()
                if not other_name or " " not in other_name:
                    continue

                other_parts = other_name.split()
                other_lastname = other_parts[-1].strip(".,;:")

                # Exact or fuzzy last name match
                if char_name.lower() == other_lastname.lower():
                    matches.append((other_idx, "exact_lastname"))
                else:
                    if names_similar(char_name, other_lastname):
                        matches.append((other_idx, "fuzzy_lastname"))

            # Merge if exactly ONE match
            if len(matches) == 1:
                other_idx, match_type = matches[0]
                other_char = updated_main_cast[other_idx]

                if char_name not in other_char.aliases:
                    logger.info(
                        f"Merging within main cast (Pass 3): '{char_name}' ({char.mention_count} mentions) "
                        f"→ '{other_char.canonical_name}' as alias ({match_type})"
                    )
                    other_char.aliases.append(char_name)
                    chars_with_new_aliases.add(other_char.id)

                chars_to_remove_pass3.add(idx)

        # Remove Pass 3 merged characters
        final_main_cast = [
            char for idx, char in enumerate(updated_main_cast) if idx not in chars_to_remove_pass3
        ]

        # Pass 4: Merge descriptive synonyms within main cast
        # Handles cases like "the creature", "the monster", "the fiend" referring to same entity
        chars_to_remove_pass4 = set()

        # Synonym groups for unnamed characters (same as in supporting.py)
        synonym_groups = [
            # Supernatural/created beings
            {"creature", "monster", "fiend", "daemon", "wretch", "being", "thing"},
            # Authority figures
            {"stranger", "visitor", "guest", "traveler", "intruder"},
            # Generic descriptors
            {"man", "woman", "boy", "girl", "child", "person"},
        ]

        def _normalize_descriptor(raw_name: str) -> tuple[bool, str]:
            """
            Normalize a descriptive handle into a synonym-group descriptor.

            Examples:
            - "the creature" -> (True, "creature")
            - "the creature (implied)" -> (True, "creature")
            - "creature" -> (False, "creature")   # bare form (special-cased for creature group)
            """
            name = (raw_name or "").lower().strip()
            is_the_form = name.startswith("the ")
            desc = name[4:].strip() if is_the_form else name
            if " (" in desc:
                desc = desc.split(" (", 1)[0].strip()
            desc = desc.strip(".,;:!?\"'“”")
            return is_the_form, desc

        for idx, char in enumerate(final_main_cast):
            if idx in chars_to_remove_pass4:
                continue

            char_name = char.canonical_name.lower().strip()

            char_is_the_form, descriptor = _normalize_descriptor(char.canonical_name)

            # Check if descriptor matches any synonym group (creature group also allows bare "creature"/"monster"/etc.)
            for group in synonym_groups:
                allow_bare = "creature" in group  # only the creature/supernatural group
                if descriptor not in group:
                    continue
                if not char_is_the_form and not allow_bare:
                    continue

                # Found a match! Check if any other characters use terms from the same group
                for other_idx, other_char in enumerate(final_main_cast):
                    if other_idx <= idx or other_idx in chars_to_remove_pass4:
                        continue  # Only check each pair once

                    other_name = other_char.canonical_name.lower().strip()
                    other_is_the_form, other_descriptor = _normalize_descriptor(
                        other_char.canonical_name
                    )

                    # If both descriptors are in the same synonym group, merge them
                    if other_descriptor in group:
                        if not other_is_the_form and not allow_bare:
                            continue
                        # Merge the one with FEWER mentions into the one with MORE mentions
                        if char.mention_count >= other_char.mention_count:
                            # Merge other → char
                            if other_char.canonical_name not in char.aliases:
                                logger.info(
                                    f"Merging descriptive synonym within main cast: '{other_char.canonical_name}' "
                                    f"({other_char.mention_count} mentions) → '{char.canonical_name}' "
                                    f"({char.mention_count} mentions) as alias (synonym group: {group})"
                                )
                                char.aliases.append(other_char.canonical_name)
                                # Also merge other's existing aliases
                                for alias in other_char.aliases:
                                    if alias not in char.aliases:
                                        char.aliases.append(alias)
                                chars_with_new_aliases.add(char.id)
                            chars_to_remove_pass4.add(other_idx)
                        else:
                            # Merge char → other
                            if char.canonical_name not in other_char.aliases:
                                logger.info(
                                    f"Merging descriptive synonym within main cast: '{char.canonical_name}' "
                                    f"({char.mention_count} mentions) → '{other_char.canonical_name}' "
                                    f"({other_char.mention_count} mentions) as alias (synonym group: {group})"
                                )
                                other_char.aliases.append(char.canonical_name)
                                # Also merge char's existing aliases
                                for alias in char.aliases:
                                    if alias not in other_char.aliases:
                                        other_char.aliases.append(alias)
                                chars_with_new_aliases.add(other_char.id)
                            chars_to_remove_pass4.add(idx)
                            break  # Don't process this char anymore

                if idx in chars_to_remove_pass4:
                    break  # This char was merged, stop checking other synonym groups

        # Remove Pass 4 merged characters
        final_main_cast = [
            char for idx, char in enumerate(final_main_cast) if idx not in chars_to_remove_pass4
        ]

        return final_main_cast, chars_with_new_aliases

    def _merge_formal_name_aliases(
        self,
        main_cast: list[Character],
        supporting_cast: list[Character],
    ) -> tuple[list[Character], list[Character], set[str]]:
        """
        Merge multi-word supporting formal names into main cast nickname characters.

        Patterns handled:
          Single-word main cast: "Jim" + supporting "James Dillingham Young"
            → "James" is the formal first name of "Jim" via NICKNAME_TO_FORMAL
            → merge "James Dillingham Young" as alias of "Jim"
          Multi-word main cast: "Jim Young" + supporting "James Dillingham Young"
            → first name "Jim" → formal "James" matches; surnames "Young" match
            → merge "James Dillingham Young" as alias of "Jim Young"

        Safeguards:
        - Supporting must be multi-word (the formal name form)
        - First name of supporting must be the formal version of main cast first name
        - For multi-word main cast: surname (last word) must match supporting surname
        - Main cast must have ≥ 4x more mentions (the supporting ref is a rare formal citation)
        - Exactly one main cast character must match (no ambiguity)

        Returns:
            Tuple of (updated_main_cast, updated_supporting_cast, char_ids_with_new_aliases)
        """
        supporting_to_remove: set[int] = set()
        chars_with_new_aliases: set[str] = set()

        for supp_idx, supp_char in enumerate(supporting_cast):
            supp_name = supp_char.canonical_name.strip()

            # Only handle multi-word supporting names
            if not supp_name or " " not in supp_name:
                continue

            supp_parts = supp_name.split()
            supp_first = supp_parts[0].lower().strip(".,;:")

            # Only proceed if the first name is a known formal name in our table
            if supp_first not in _FORMAL_TO_NICKNAMES:
                continue

            matching_nicknames = _FORMAL_TO_NICKNAMES[supp_first]

            # Find main cast characters whose canonical nickname form matches supp_first.
            # Handles two patterns:
            #   Single-word: main "Jim" → nickname for formal "James"
            #   Multi-word:  main "Jim Young" first name "Jim" → nickname for "James",
            #                surname "Young" matches supporting "James Dillingham Young"
            matches: list[int] = []
            for main_idx, main_char in enumerate(main_cast):
                main_parts = main_char.canonical_name.strip().split()
                main_first = main_parts[0].lower().strip(".,;:")

                if len(main_parts) == 1:
                    # Single-word main cast: check if it's a nickname for supp_first
                    if main_first in matching_nicknames:
                        matches.append(main_idx)
                else:
                    # Multi-word main cast: first name must be a nickname whose formal
                    # version equals supp_first, AND surnames must match.
                    if (
                        main_first in NICKNAME_TO_FORMAL
                        and NICKNAME_TO_FORMAL[main_first] == supp_first
                    ):
                        main_last = main_parts[-1].lower().strip(".,;:")
                        supp_last = supp_parts[-1].lower().strip(".,;:")
                        if main_last == supp_last:
                            matches.append(main_idx)

            # Require exactly one match to avoid ambiguity
            if len(matches) != 1:
                continue

            main_idx = matches[0]
            main_char = main_cast[main_idx]

            # Safeguard: main must have significantly more mentions.
            # The supporting character is a rare formal reference, not a distinct person.
            # Allow merge if supporting has 0 mentions (grounding corner case) or
            # main has ≥ 4x more mentions than supporting.
            if supp_char.mention_count > 0 and main_char.mention_count < 4 * supp_char.mention_count:
                continue

            # Merge: add supporting formal name as alias of main
            if supp_name not in main_char.aliases:
                logger.info(
                    f"V2 Step 5.5a: Merging formal-name supporting '{supp_name}' "
                    f"({supp_char.mention_count} mentions) → "
                    f"'{main_char.canonical_name}' ({main_char.mention_count} mentions) "
                    f"as alias (nickname→formal: '{main_char.canonical_name}' → '{supp_first}')"
                )
                main_char.aliases.append(supp_name)
                chars_with_new_aliases.add(main_char.id)

            supporting_to_remove.add(supp_idx)

        updated_supporting = [
            char for idx, char in enumerate(supporting_cast) if idx not in supporting_to_remove
        ]

        return main_cast, updated_supporting, chars_with_new_aliases

    def _merge_lastname_aliases(
        self,
        main_cast: list[Character],
        supporting_cast: list[Character],
    ) -> tuple[list[Character], list[Character], set[str]]:
        """
        Merge last-name-only supporting characters as aliases of main cast.

        Common pattern: "Wilson" (65 mentions) should be an alias of "George B. Wilson"
        when there's only one Wilson in the main cast.

        Also handles title variants like "Mr. Gatsby" → alias of "Jay Gatsby"

        NEW: Also handles reverse case where main_cast has single-word name and
        supporting_cast has full name (e.g., "Wolfshiem" in main, "Meyer Wolfshiem" in supporting)

        Returns:
            Tuple of (updated_main_cast, updated_supporting_cast, char_ids_with_new_aliases)
        """
        import re

        if not supporting_cast:
            return main_cast, supporting_cast, set()

        supporting_to_remove = set()
        chars_with_new_aliases = set()

        for supp_idx, supp_char in enumerate(supporting_cast):
            supp_name = supp_char.canonical_name.strip()

            # Skip if empty
            if not supp_name:
                continue

            # Check for title + name pattern (e.g., "Mr. Gatsby")
            title_stripped = self._strip_title(supp_name)
            if title_stripped != supp_name:
                # This is a title + name - check if it matches any main cast canonical or alias
                for main_idx, main_char in enumerate(main_cast):
                    # Check canonical name
                    if title_stripped.lower() == main_char.canonical_name.lower():
                        if supp_name not in main_char.aliases:
                            logger.info(
                                f"Merging title variant '{supp_name}' → "
                                f"'{main_char.canonical_name}' as alias"
                            )
                            main_char.aliases.append(supp_name)
                            chars_with_new_aliases.add(main_char.id)
                        supporting_to_remove.add(supp_idx)
                        break

                    # Check aliases
                    for alias in main_char.aliases:
                        if title_stripped.lower() == alias.lower():
                            if supp_name not in main_char.aliases:
                                logger.info(
                                    f"Merging title variant '{supp_name}' → "
                                    f"'{main_char.canonical_name}' (matches alias '{alias}')"
                                )
                                main_char.aliases.append(supp_name)
                                chars_with_new_aliases.add(main_char.id)
                            supporting_to_remove.add(supp_idx)
                            break

                # If we processed this as a title variant, skip last-name processing
                if supp_idx in supporting_to_remove:
                    continue

            # Check reverse: MAIN cast has title, SUPPORTING cast does not.
            # e.g., main = "Doctor T. J. Eckleburg", supporting = "T. J. Eckleburg"
            if supp_idx not in supporting_to_remove:
                for main_idx, main_char in enumerate(main_cast):
                    main_title_stripped = self._strip_title(main_char.canonical_name)
                    if (
                        main_title_stripped != main_char.canonical_name
                        and main_title_stripped.lower() == supp_name.lower()
                    ):
                        if supp_name not in main_char.aliases:
                            logger.info(
                                f"Merging title-free variant '{supp_name}' → "
                                f"'{main_char.canonical_name}' as alias (main has title)"
                            )
                            main_char.aliases.append(supp_name)
                            chars_with_new_aliases.add(main_char.id)
                        supporting_to_remove.add(supp_idx)
                        break

            if supp_idx in supporting_to_remove:
                continue

            # Check for "the X" → "X" normalization (e.g., "Owl-eyed man" vs "the owl-eyed man")
            # Strip leading "the " for comparison
            supp_name_normalized = re.sub(r"^the\s+", "", supp_name, flags=re.IGNORECASE).strip()

            # Check against main cast canonical names and aliases
            for main_idx, main_char in enumerate(main_cast):
                # Normalize main canonical name
                main_canonical_normalized = re.sub(
                    r"^the\s+", "", main_char.canonical_name, flags=re.IGNORECASE
                ).strip()

                # Check canonical name (with and without "the")
                if (
                    supp_name_normalized.lower() == main_canonical_normalized.lower()
                    or supp_name.lower() == main_char.canonical_name.lower()
                ):
                    if supp_name not in main_char.aliases:
                        logger.info(
                            f"Merging 'the' variant '{supp_name}' → "
                            f"'{main_char.canonical_name}' as alias"
                        )
                        main_char.aliases.append(supp_name)
                        chars_with_new_aliases.add(main_char.id)
                    supporting_to_remove.add(supp_idx)
                    break

                # Check aliases
                for alias in main_char.aliases:
                    alias_normalized = re.sub(r"^the\s+", "", alias, flags=re.IGNORECASE).strip()
                    if (
                        supp_name_normalized.lower() == alias_normalized.lower()
                        or supp_name.lower() == alias.lower()
                    ):
                        if supp_name not in main_char.aliases:
                            logger.info(
                                f"Merging 'the' variant '{supp_name}' → "
                                f"'{main_char.canonical_name}' (matches alias '{alias}')"
                            )
                            main_char.aliases.append(supp_name)
                            chars_with_new_aliases.add(main_char.id)
                        supporting_to_remove.add(supp_idx)
                        break

                if supp_idx in supporting_to_remove:
                    break

            # Only process single-word names (potential last names)
            if " " in supp_name:
                continue

            # Check if this could be a last name of any main cast character
            matches = []

            for main_idx, main_char in enumerate(main_cast):
                # Extract last name from main character's canonical name
                main_name_parts = main_char.canonical_name.strip().split()

                if not main_name_parts:
                    continue

                # Get last word as potential surname
                main_lastname = main_name_parts[-1].strip(".,;:")

                # Check for exact match (case-insensitive)
                if supp_name.lower() == main_lastname.lower():
                    matches.append((main_idx, "exact"))
                    continue

                # Check for fuzzy match (handles Wolfsheim/Wolfshiem)
                if names_similar(supp_name, main_lastname):  # 85% similar
                    matches.append((main_idx, "fuzzy_lastname"))
                    continue

                # Check first name match (if main_name has multiple parts)
                if len(main_name_parts) >= 2:
                    main_firstname = main_name_parts[0].strip(".,;:")
                    if supp_name.lower() == main_firstname.lower():
                        matches.append((main_idx, "exact_firstname"))
                        continue

                # Check nickname → formal first name (e.g., "Milt" supporting → "Milton Jennings" main cast)
                if len(main_name_parts) >= 2:
                    main_firstname_lower = main_name_parts[0].strip(".,;:").lower()
                    supp_lower = supp_name.lower()
                    if supp_lower in NICKNAME_TO_FORMAL and NICKNAME_TO_FORMAL[supp_lower] == main_firstname_lower:
                        matches.append((main_idx, "nickname_firstname"))
                        continue

                # Check alias component match: supp_name is a word inside a confirmed alias.
                # Example: "Dillingham" is a middle-name component of alias "James Dillingham Young".
                # This only works after _merge_formal_name_aliases has added the formal name as
                # an alias (Step 5.5a), so the alias is available here.
                for alias in main_char.aliases:
                    alias_words = [w.strip(".,;:") for w in alias.lower().split()]
                    if supp_name.lower() in alias_words:
                        matches.append((main_idx, "alias_component"))
                        break

            # Handle merging based on match count
            if len(matches) == 1:
                # Exactly one match - straightforward merge
                main_idx, match_type = matches[0]
                main_char = main_cast[main_idx]

                # For nickname matches, require strong mention asymmetry to avoid wrong merges.
                # The supporting char is a rare nickname reference; the main cast char is the full name.
                if match_type == "nickname_firstname" and supp_char.mention_count > 0:
                    if main_char.mention_count < 4 * supp_char.mention_count:
                        continue

                # Check if already an alias
                if supp_name not in main_char.aliases:
                    logger.info(
                        f"Merging last-name-only '{supp_name}' ({supp_char.mention_count} mentions) "
                        f"→ '{main_char.canonical_name}' as alias ({match_type} match)"
                    )
                    main_char.aliases.append(supp_name)
                    chars_with_new_aliases.add(main_char.id)

                # Mark for removal from supporting cast
                supporting_to_remove.add(supp_idx)

            elif len(matches) > 1:
                # Multiple characters share this surname
                # Use title-based disambiguation: if one character has "Mrs. [LastName]" as alias,
                # merge bare last name with a character that does NOT have that female title
                # (This handles cases like George Wilson vs Myrtle Wilson in Gatsby)

                # Find which characters have gendered title variants
                matches_with_mrs = []
                matches_without_mrs = []

                for main_idx, match_type in matches:
                    main_char = main_cast[main_idx]

                    # Check if this character has "Mrs. [LastName]" as alias
                    has_mrs_variant = any(
                        alias.lower().startswith("mrs.") and supp_name.lower() in alias.lower()
                        for alias in main_char.aliases
                    )

                    if has_mrs_variant:
                        matches_with_mrs.append((main_idx, match_type))
                    else:
                        matches_without_mrs.append((main_idx, match_type))

                # If we have exactly ONE match WITHOUT the Mrs. title, merge with that one
                # (This means bare "Wilson" → "George Wilson", not "Myrtle Wilson" who has "Mrs. Wilson")
                if len(matches_without_mrs) == 1:
                    main_idx, match_type = matches_without_mrs[0]
                    main_char = main_cast[main_idx]

                    if supp_name not in main_char.aliases:
                        logger.info(
                            f"Merging last-name-only '{supp_name}' ({supp_char.mention_count} mentions) "
                            f"→ '{main_char.canonical_name}' as alias (title-disambiguated {match_type} match, "
                            f"{len(matches)} total surname matches)"
                        )
                        main_char.aliases.append(supp_name)
                        chars_with_new_aliases.add(main_char.id)

                    supporting_to_remove.add(supp_idx)
                else:
                    # Can't disambiguate - merge to ALL matching characters
                    # (This means bare "Wilson" becomes alias for both George and Myrtle)
                    # Rationale: If we can't tell which character a bare surname refers to,
                    # both family members should get credit for those mentions
                    logger.info(
                        f"Merging last-name-only '{supp_name}' ({supp_char.mention_count} mentions) "
                        f"→ ALL {len(matches)} characters with this surname (disambiguation failed)"
                    )
                    for main_idx, match_type in matches:
                        main_char = main_cast[main_idx]
                        if supp_name not in main_char.aliases:
                            main_char.aliases.append(supp_name)
                            chars_with_new_aliases.add(main_char.id)
                            logger.debug(
                                f"  Added '{supp_name}' as alias to '{main_char.canonical_name}'"
                            )

                    supporting_to_remove.add(supp_idx)

        # Remove merged characters from supporting cast
        updated_supporting = [
            char for idx, char in enumerate(supporting_cast) if idx not in supporting_to_remove
        ]

        # REVERSE PASS: Check if any MULTI-WORD supporting characters should merge
        # with SINGLE-WORD main cast characters (e.g., "Wolfshiem" main + "Meyer Wolfshiem" supporting)
        # This handles cases where NER extracted the full name but summaries only mentioned last name
        reverse_supporting_to_remove = set()

        for main_idx, main_char in enumerate(main_cast):
            main_name = main_char.canonical_name.strip()

            # Only process single-word main cast names
            if not main_name or " " in main_name:
                continue

            # Check if this matches any multi-word supporting character's last name
            matches = []

            for supp_idx, supp_char in enumerate(updated_supporting):
                if supp_idx in reverse_supporting_to_remove:
                    continue

                supp_name = supp_char.canonical_name.strip()

                # Only match against multi-word names
                if not supp_name or " " not in supp_name:
                    continue

                # Extract last name from supporting character
                supp_parts = supp_name.split()
                supp_lastname = supp_parts[-1].strip(".,;:")

                # Check for exact match
                if main_name.lower() == supp_lastname.lower():
                    matches.append((supp_idx, supp_name, "exact"))
                    continue

                # Check for fuzzy match (handles spelling variants)
                if names_similar(main_name, supp_lastname):
                    matches.append((supp_idx, supp_name, "fuzzy"))

            # Merge if exactly ONE match
            if len(matches) == 1:
                supp_idx, supp_name, match_type = matches[0]
                supp_char = updated_supporting[supp_idx]

                # Add supporting full name as alias to main cast character
                if supp_name not in main_char.aliases:
                    logger.info(
                        f"Merging full-name supporting char '{supp_name}' ({supp_char.mention_count} mentions) "
                        f"→ '{main_char.canonical_name}' ({main_char.mention_count} mentions) as alias ({match_type} match)"
                    )
                    main_char.aliases.append(supp_name)
                    chars_with_new_aliases.add(main_char.id)

                # Mark for removal from supporting cast
                reverse_supporting_to_remove.add(supp_idx)

        # Remove reverse-merged characters
        final_supporting = [
            char
            for idx, char in enumerate(updated_supporting)
            if idx not in reverse_supporting_to_remove
        ]

        return main_cast, final_supporting, chars_with_new_aliases

    def _merge_within_supporting_cast(
        self,
        supporting_cast: list[Character],
    ) -> tuple[list[Character], set[str]]:
        """
        Merge characters within supporting cast that are variants of each other.

        Handles two patterns:
        1. Last-name-only → Full name: "Wolfshiem" (20 mentions) → alias of "Meyer Wolfshiem"
        2. Spelling variants: "Wolfsheim" ↔ "Wolfshiem" (85% fuzzy match)

        This is similar to _merge_within_main_cast but for supporting characters.

        Returns:
            Tuple of (updated_supporting_cast, char_ids_with_new_aliases)
        """
        chars_to_remove = set()
        chars_with_new_aliases = set()

        # Pass 1: Merge last-name-only characters
        for idx, char in enumerate(supporting_cast):
            if idx in chars_to_remove:
                continue

            char_name = char.canonical_name.strip()
            if not char_name or " " in char_name:
                continue  # Skip empty or multi-word names

            # This is a single-word name (potential last name)
            # Check if it matches the last word of any OTHER supporting character

            matches = []
            for other_idx, other_char in enumerate(supporting_cast):
                if other_idx == idx or other_idx in chars_to_remove:
                    continue

                other_name = other_char.canonical_name.strip()
                if not other_name or " " not in other_name:
                    continue  # Only match against multi-word names

                # Check last name match
                other_parts = other_name.split()
                other_lastname = other_parts[-1].strip(".,;:")

                # Exact last name match
                if char_name.lower() == other_lastname.lower():
                    matches.append((other_idx, "exact_lastname"))
                    continue

                # Fuzzy last name match (handles Wolfsheim/Wolfshiem)
                if names_similar(char_name, other_lastname):
                    matches.append((other_idx, "fuzzy_lastname"))
                    continue  # Skip first-name check for this other_char

                # First-name match for two cases:
                # Case A: "FirstName LastInitial." pattern (e.g., "John" → "John G.")
                #   When a full name uses a single-letter last initial, a reference to
                #   just the first name is always the same person. Universal: any book
                #   with initial-style names (military, formal, period fiction) benefits.
                # Case B: Rare full-name characters (e.g., "Ted" → "Ted Frith").
                #   Universal pattern: character introduced by full name, then referenced
                #   by first name only. The ≤3 guard prevents false merges with
                #   frequently-mentioned characters.
                other_firstname = other_parts[0].strip(".,;:")
                if char_name.lower() == other_firstname.lower():
                    remaining_parts = other_parts[1:]
                    all_initials = bool(remaining_parts) and all(
                        len(p.strip(".,;:")) == 1 and p.strip(".,;:").isalpha()
                        for p in remaining_parts
                    )
                    if all_initials:
                        matches.append((other_idx, "firstname_of_initial_name"))
                    elif other_char.mention_count <= 3:
                        matches.append((other_idx, "exact_firstname_of_rare_fullname"))

            # Merge if exactly ONE match
            if len(matches) == 1:
                other_idx, match_type = matches[0]
                other_char = supporting_cast[other_idx]

                # Add single-word name as alias to the full name character
                if char_name not in other_char.aliases:
                    logger.info(
                        f"Merging within supporting cast: '{char_name}' ({char.mention_count} mentions) "
                        f"→ '{other_char.canonical_name}' as alias ({match_type})"
                    )
                    other_char.aliases.append(char_name)
                    chars_with_new_aliases.add(other_char.id)

                # Mark single-word character for removal
                chars_to_remove.add(idx)

        # Pass 2: Merge spelling variants (e.g., "Meyer Wolfsheim" ↔ "Meyer Wolfshiem")
        for idx, char in enumerate(supporting_cast):
            if idx in chars_to_remove:
                continue

            char_name = char.canonical_name.strip()
            if not char_name:
                continue

            for other_idx, other_char in enumerate(supporting_cast):
                if other_idx <= idx or other_idx in chars_to_remove:
                    continue  # Only check each pair once

                other_name = other_char.canonical_name.strip()
                if not other_name:
                    continue

                # Calculate similarity for spelling variant detection
                # Use direct string similarity (NOT names_similar which has subset matching)
                # This prevents false merges like "John" + "John Donaldson" (father/son with same first name)
                # while still catching spelling variants like "Wolfsheim"/"Wolfshiem" (89% similar)
                # Note: Pass 1 handles legitimate last-name-only merges ("Wilson" → "George Wilson")
                similarity = string_similarity(char_name, other_name)

                # Check if names are very similar (spelling variants only, threshold 85%)
                if similarity >= 0.85:
                    # SAFETY CHECK: Don't merge if both have different title prefixes
                    # (e.g., "Mr. White" vs "Mrs. White" are different people)
                    if self._are_different_titled_people(char_name, other_name):
                        continue  # Skip - they're different people

                    # Merge the one with FEWER mentions into the one with MORE mentions
                    if char.mention_count >= other_char.mention_count:
                        # Merge other → char
                        if other_name not in char.aliases:
                            logger.info(
                                f"Merging spelling variant within supporting cast: '{other_name}' "
                                f"({other_char.mention_count} mentions) → '{char_name}' "
                                f"({char.mention_count} mentions) as alias (similarity={similarity:.2f})"
                            )
                            char.aliases.append(other_name)
                            # Also merge other's existing aliases
                            for alias in other_char.aliases:
                                if alias not in char.aliases:
                                    char.aliases.append(alias)
                            chars_with_new_aliases.add(char.id)
                        chars_to_remove.add(other_idx)
                    else:
                        # Merge char → other
                        if char_name not in other_char.aliases:
                            logger.info(
                                f"Merging spelling variant within supporting cast: '{char_name}' "
                                f"({char.mention_count} mentions) → '{other_name}' "
                                f"({other_char.mention_count} mentions) as alias (similarity={similarity:.2f})"
                            )
                            other_char.aliases.append(char_name)
                            # Also merge char's existing aliases
                            for alias in char.aliases:
                                if alias not in other_char.aliases:
                                    other_char.aliases.append(alias)
                            chars_with_new_aliases.add(other_char.id)
                        chars_to_remove.add(idx)
                        break  # Don't process this char anymore

        # Pass 3: Merge standard English diminutives as aliases.
        # Handles cases where NER extracts a nickname form separately from the canonical name.
        # Example: "Johnny" (2 mentions) → alias of "John" (16 mentions).
        # Uses the module-level STANDARD_DIMINUTIVES mapping.
        for idx, char in enumerate(supporting_cast):
            if idx in chars_to_remove:
                continue

            char_name = char.canonical_name.strip()
            if not char_name or " " in char_name:
                continue  # Only single-word names

            canonical_form = STANDARD_DIMINUTIVES.get(char_name.lower())
            if not canonical_form:
                continue  # Not a known diminutive

            # Find exactly one supporting character whose canonical name is the long form
            dim_matches = []
            for other_idx, other_char in enumerate(supporting_cast):
                if other_idx == idx or other_idx in chars_to_remove:
                    continue
                if other_char.canonical_name.lower() == canonical_form:
                    dim_matches.append(other_idx)

            # Merge if exactly ONE match (avoid ambiguity when multiple same-name characters)
            if len(dim_matches) == 1:
                other_idx = dim_matches[0]
                other_char = supporting_cast[other_idx]

                if char_name not in other_char.aliases:
                    logger.info(
                        f"Merging diminutive '{char_name}' ({char.mention_count} mentions) "
                        f"→ '{other_char.canonical_name}' as alias (standard English diminutive)"
                    )
                    other_char.aliases.append(char_name)
                    chars_with_new_aliases.add(other_char.id)

                chars_to_remove.add(idx)

        # Remove merged characters
        updated_supporting = [
            char for idx, char in enumerate(supporting_cast) if idx not in chars_to_remove
        ]

        return updated_supporting, chars_with_new_aliases

    def _merge_descriptive_synonyms_across_casts(
        self,
        main_cast: list[Character],
        supporting_cast: list[Character],
    ) -> tuple[list[Character], set[str]]:
        """
        Merge descriptive synonym characters from supporting cast into main cast.

        Handles cases like:
        - "the creature" (main cast, antagonist) + "the monster" (supporting) → merge monster into creature
        - "the stranger" (main cast) + "the visitor" (supporting) → merge visitor into stranger

        This only merges supporting→main when both use "the X" pattern from same synonym group.

        Returns:
            Tuple of (updated_supporting_cast, char_ids_with_new_aliases_in_main_cast)
        """
        chars_to_remove = set()
        chars_with_new_aliases = set()

        # Synonym groups (same as in _merge_within_main_cast Pass 4)
        synonym_groups = [
            # Supernatural/created beings
            {"creature", "monster", "fiend", "daemon", "wretch", "being", "thing"},
            # Authority figures
            {"stranger", "visitor", "guest", "traveler", "intruder"},
            # Generic descriptors
            {"man", "woman", "boy", "girl", "child", "person"},
        ]

        # Helper function to normalize descriptors (strip parentheticals)
        def _normalize_cross_cast_descriptor(name: str) -> str:
            """
            Normalize a descriptive name by stripping parentheticals.

            Examples:
            - "the creature (implied presence)" → "creature"
            - "the monster" → "monster"
            - "the old man (De Lacey)" → "old man"
            """
            if not name.startswith("the "):
                return name

            desc = name[4:].strip().lower()

            # Strip parentheticals: "creature (implied)" → "creature"
            if " (" in desc:
                desc = desc.split(" (")[0].strip()

            # Strip trailing punctuation
            desc = desc.strip(".,;:!?\"'" "")

            return desc

        # Loop through main cast characters looking for "the X" patterns
        for main_char in main_cast:
            main_name = main_char.canonical_name.lower().strip()

            # Only check descriptive patterns like "the X"
            if not main_name.startswith("the "):
                continue

            # Extract and normalize descriptor
            main_descriptor = _normalize_cross_cast_descriptor(main_name)

            # DEBUG: Log creature/monster specifically
            if "creature" in main_descriptor or "monster" in main_descriptor:
                logger.warning(
                    f"DEBUG cross-cast merge: Main cast has '{main_char.canonical_name}' "
                    f"(normalized descriptor: '{main_descriptor}')"
                )

            # Check if descriptor matches any synonym group
            # Group elements are already lowercase strings
            for group in synonym_groups:
                if main_descriptor not in group:
                    continue

                # Found a match! Check supporting cast for synonyms from same group
                logger.info(
                    f"Main cast '{main_char.canonical_name}' (descriptor: '{main_descriptor}') "
                    f"matches synonym group: {group}. Checking supporting cast..."
                )

                for supp_idx, supp_char in enumerate(supporting_cast):
                    if supp_idx in chars_to_remove:
                        continue

                    supp_name = supp_char.canonical_name.lower().strip()
                    if not supp_name.startswith("the "):
                        continue

                    # Extract and normalize descriptor (strips parentheticals)
                    supp_descriptor = _normalize_cross_cast_descriptor(supp_name)

                    # DEBUG: Log all "the X" supporting characters when main is creature/monster
                    if "creature" in main_descriptor or "monster" in main_descriptor:
                        logger.warning(
                            f"DEBUG cross-cast merge: Checking supporting '{supp_char.canonical_name}' "
                            f"(normalized descriptor: '{supp_descriptor}') against main '{main_char.canonical_name}'"
                        )

                    # If supporting character uses synonym from same group, merge it
                    # Group elements are already lowercase strings
                    if supp_descriptor in group:
                        logger.info(
                            f"Merging descriptive synonym across casts: '{supp_char.canonical_name}' "
                            f"({supp_char.mention_count} mentions, supporting) → "
                            f"'{main_char.canonical_name}' ({main_char.mention_count} mentions, main cast) "
                            f"as alias (synonym group: {group})"
                        )

                        # Add supporting character's name as alias to main character
                        if supp_char.canonical_name not in main_char.aliases:
                            main_char.aliases.append(supp_char.canonical_name)

                        # Also merge supporting character's existing aliases
                        for alias in supp_char.aliases:
                            if alias not in main_char.aliases:
                                main_char.aliases.append(alias)

                        chars_with_new_aliases.add(main_char.id)
                        chars_to_remove.add(supp_idx)

                # Found synonym group match, no need to check other groups for this main character
                break

        # Remove merged supporting characters
        updated_supporting = [
            char for idx, char in enumerate(supporting_cast) if idx not in chars_to_remove
        ]

        return updated_supporting, chars_with_new_aliases

    def _recover_creature_synonym_aliases(
        self,
        main_cast: list[Character],
        source_text: str,
    ) -> tuple[list[Character], set[str]]:
        """
        Recover creature synonym aliases that were blocked during pass-2 extraction.

        When the LLM merges creature descriptors ("the monster", "the fiend") into a
        non-creature character during extraction, and that entry is later split by
        _split_semantic_conflicts, the resulting split_* creature character has no
        aliases because the synonyms were already marked "claimed" by the pre-split
        entry (which no longer exists).

        This step runs AFTER all cross-cast merges so the final character list is
        settled.  It finds characters whose canonical name is a creature-type
        descriptor, collects creature synonyms not yet assigned to ANY character,
        and adds those that genuinely appear in the source text as aliases.

        Universal: uses the same synonym group already defined in
        _split_semantic_conflicts and _merge_descriptive_synonyms_across_casts.
        """
        import re

        # Synonyms to recover (same group as semantic-split checks)
        creature_synonyms = ["monster", "fiend", "wretch", "daemon", "being", "creature"]
        # Text variants to check per synonym (handles ligature spellings in older texts)
        text_variants: dict[str, list[str]] = {
            "daemon": ["the daemon", "the dæmon"],
        }

        chars_with_new_aliases: set[str] = set()

        # Collect every name/alias currently claimed across ALL characters,
        # building both a set of claimed lower-case phrases and a mapping from
        # phrase → claiming character (for transfer logic below).
        all_claimed_lower: set[str] = set()
        alias_to_claimer: dict[str, "Character"] = {}  # phrase_lower → char
        for char in main_cast:
            cn_lower = char.canonical_name.lower()
            all_claimed_lower.add(cn_lower)
            alias_to_claimer[cn_lower] = char
            for alias in char.aliases:
                al = alias.lower()
                all_claimed_lower.add(al)
                alias_to_claimer[al] = char

        def _is_creature_char(c: "Character") -> bool:
            cl = c.canonical_name.lower().strip()
            if not cl.startswith("the "):
                return False
            d = cl[4:]
            if " (" in d:
                d = d.split(" (")[0]
            return d.strip().replace("æ", "ae").replace("œ", "oe") in creature_synonyms

        for char in main_cast:
            canonical_lower = char.canonical_name.lower().strip()

            # Only process "the X" descriptive names
            if not canonical_lower.startswith("the "):
                continue

            # Strip parentheticals: "the old man (De Lacey)" → "old man"
            descriptor = canonical_lower[4:]
            if " (" in descriptor:
                descriptor = descriptor.split(" (")[0]
            descriptor = descriptor.strip()
            # Normalize ligatures for synonym matching
            descriptor_norm = descriptor.replace("æ", "ae").replace("œ", "oe")

            # Only process creature-type characters
            if descriptor_norm not in creature_synonyms:
                continue

            # Collect which creature synonyms this character already has
            existing_synonyms: set[str] = set()
            for name in [char.canonical_name] + list(char.aliases):
                nl = name.lower().strip()
                if nl.startswith("the "):
                    desc = nl[4:]
                    if " (" in desc:
                        desc = desc.split(" (")[0]
                    desc = desc.strip().replace("æ", "ae").replace("œ", "oe")
                    if desc in creature_synonyms:
                        existing_synonyms.add(desc)

            # Attempt to recover each missing synonym
            for synonym in creature_synonyms:
                if synonym in existing_synonyms:
                    continue  # already have it

                phrases_to_check = text_variants.get(synonym, [f"the {synonym}"])

                found_phrase: str | None = None
                for phrase in phrases_to_check:
                    phrase_lower = phrase.lower()
                    phrase_norm = phrase_lower.replace("æ", "ae").replace("œ", "oe")

                    # If claimed, only allow transfer FROM a non-creature character.
                    # Universal invariant: a creature synonym should belong to the
                    # creature entity, not to a person/location character that the
                    # LLM happened to merge it with during extraction.
                    claimer = alias_to_claimer.get(phrase_lower) or alias_to_claimer.get(phrase_norm)
                    if claimer is not None:
                        if claimer is char:
                            break  # this creature already owns it
                        if _is_creature_char(claimer):
                            break  # another creature-type char owns it; skip
                        # Transfer from non-creature character to this creature character.
                        for rm_phrase in list(claimer.aliases):
                            if rm_phrase.lower() == phrase_lower or rm_phrase.lower().replace("æ", "ae") == phrase_norm:
                                claimer.aliases.remove(rm_phrase)
                                logger.info(
                                    f"V2 Step 5.6.5b: Transferred alias '{rm_phrase}' "
                                    f"from '{claimer.canonical_name}' to '{char.canonical_name}'"
                                )
                                break
                        found_phrase = phrase
                        break

                    # Not claimed — verify it appears in the source text.
                    pattern = re.compile(
                        rf"(?<![A-Za-z]){re.escape(phrase)}(?![A-Za-z])",
                        re.IGNORECASE,
                    )
                    if pattern.search(source_text):
                        found_phrase = phrase
                        break

                if found_phrase is None:
                    continue

                char.aliases.append(found_phrase)
                all_claimed_lower.add(found_phrase.lower())
                alias_to_claimer[found_phrase.lower()] = char
                chars_with_new_aliases.add(char.id)
                logger.info(
                    f"V2 Step 5.6.5b: Recovered alias '{found_phrase}' → '{char.canonical_name}'"
                )

        return main_cast, chars_with_new_aliases

    def _merge_surname_into_family_descriptive(
        self,
        main_cast: list[Character],
        supporting_cast: list[Character],
    ) -> tuple[list[Character], set[str]]:
        """
        Merge bare surname from supporting cast into descriptive handles when
        they share family relationships.

        Example:
        - Supporting: "De Lacey" (bare surname)
        - Main cast: "Felix De Lacey", "Agatha De Lacey" (share surname)
        - Main cast: "the old man" (descriptive, described as father of Felix/Agatha)
        → Merge "De Lacey" into "the old man" as alias

        Returns:
            Tuple of (updated_supporting_cast, char_ids_with_new_aliases_in_main_cast)
        """
        chars_to_remove = set()
        chars_with_new_aliases = set()

        # Step 1: Build map of surnames → main cast characters
        surname_to_chars: dict[str, list[Character]] = {}
        for char in main_cast:
            parts = char.canonical_name.split()
            if len(parts) >= 2:
                surname = parts[-1].lower()
                if surname not in surname_to_chars:
                    surname_to_chars[surname] = []
                surname_to_chars[surname].append(char)

        logger.debug(
            f"_merge_surname_into_family_descriptive: Found surname families: "
            f"{[(s, [c.canonical_name for c in chars]) for s, chars in surname_to_chars.items() if len(chars) >= 2]}"
        )

        # Step 2: Find bare surnames in supporting cast
        for supp_idx, supp_char in enumerate(supporting_cast):
            supp_name = supp_char.canonical_name.strip()
            supp_lower = supp_name.lower()

            # Skip if not a bare surname (single word, title-case)
            if " " in supp_name:
                continue
            if not supp_name or not supp_name[0].isupper():
                continue

            # Skip if already a descriptive handle
            if supp_lower.startswith("the "):
                continue

            # Check if this surname matches main cast family members
            if supp_lower not in surname_to_chars:
                continue

            family_members = surname_to_chars[supp_lower]
            if len(family_members) < 2:
                continue  # Need at least 2 family members to infer relationship

            logger.info(
                f"Found bare surname '{supp_name}' matching {len(family_members)} "
                f"main cast family members: {[c.canonical_name for c in family_members]}"
            )

            # Step 3: Find descriptive handles that could be this family member
            for main_char in main_cast:
                main_name = main_char.canonical_name.lower().strip()

                # Only check descriptive patterns
                if not main_name.startswith("the "):
                    continue

                # Skip if already has this surname as alias.
                # Also mark the supporting char as consumed so it isn't
                # merged into any OTHER descriptive character — the surname
                # is already represented by this family's existing alias.
                if any(supp_lower in alias.lower() for alias in main_char.aliases):
                    logger.debug(
                        f"Skipping '{main_char.canonical_name}' - already has '{supp_name}' as alias; "
                        f"marking '{supp_name}' as consumed"
                    )
                    chars_to_remove.add(supp_idx)
                    break  # Surname already accounted for — don't merge into another character

                # Check for family relationship indicators in description
                description = (main_char.description or "").lower()
                family_indicators = ["father", "mother", "parent", "patriarch", "matriarch"]

                # Check if main_char is described as family member of surname-holders
                is_family = any(ind in description for ind in family_indicators)
                if not is_family:
                    # Also check if any family member's name appears in description
                    for fm in family_members:
                        first_name = fm.canonical_name.split()[0].lower()
                        if first_name in description:
                            is_family = True
                            logger.debug(
                                f"Family relationship detected via description: "
                                f"'{main_char.canonical_name}' mentions '{first_name}'"
                            )
                            break

                if is_family:
                    logger.info(
                        f"Merging surname '{supp_name}' into descriptive handle "
                        f"'{main_char.canonical_name}' (family relationship detected)"
                    )

                    # Merge
                    if supp_char.canonical_name not in main_char.aliases:
                        main_char.aliases.append(supp_char.canonical_name)
                    for alias in supp_char.aliases:
                        if alias not in main_char.aliases:
                            main_char.aliases.append(alias)

                    main_char.mention_count += supp_char.mention_count
                    chars_to_remove.add(supp_idx)
                    chars_with_new_aliases.add(main_char.id)
                    break  # Only merge into one descriptive handle

        # Remove merged characters
        updated_supporting = [
            c for i, c in enumerate(supporting_cast) if i not in chars_to_remove
        ]

        return updated_supporting, chars_with_new_aliases

    def _convert_to_pipeline_characters(
        self,
        main_cast: list[Character],
        supporting_cast: list[Character],
        mention_results: dict = None,
    ) -> list[PipelineCharacter]:
        """Convert model Characters to pipeline Characters for output compatibility."""
        result = []
        mention_results = mention_results or {}

        for char in main_cast:
            # Get mention data if available
            mention_info = mention_results.get(char.id)

            # Convert mentions from models.CharacterMention to pipeline.CharacterMention
            mentions_list = []
            if mention_info:
                from ..pipeline.character_extraction.models import (
                    CharacterMention as PipelineMention,
                )

                for m in mention_info.mentions:
                    pipeline_mention = PipelineMention(
                        text=m.name_form,
                        position=m.position,
                        chapter_index=m.chapter_index or 0,
                        context=m.context,
                        in_dialogue=False,  # V2 doesn't track this
                        is_agentive=False,  # V2 doesn't track this
                    )
                    mentions_list.append(pipeline_mention)

            chapters_present = (
                list(mention_info.chapter_distribution.keys())
                if mention_info and mention_info.chapter_distribution
                else []
            )

            # Convert model.Character to pipeline Character
            pc = PipelineCharacter(
                id=char.id,
                canonical_name=char.canonical_name,
                aliases=list(dict.fromkeys(char.aliases or [])),
                mentions=mentions_list,  # Use actual mentions from search
                first_appearance_chapter=char.first_appearance_chapter or 0,
                mention_count=char.mention_count,
                chapters_present=chapters_present,
                confidence=0.85 if char.confidence.value == "high" else 0.6,
                supporting_strategies=["v2_summary_extraction"],
                description=self._get_description_text(char),
                is_narrator=char.is_narrator,
                narrative_role=char.narrative_role,
                role=char.role or "main",
            )
            result.append(pc)

        for char in supporting_cast:
            # Supporting cast doesn't have mention search results (uses NER counts)
            # So mentions list remains empty for them
            mention_info = mention_results.get(char.id) if mention_results else None

            mentions_list = []
            if mention_info:
                from ..pipeline.character_extraction.models import (
                    CharacterMention as PipelineMention,
                )

                for m in mention_info.mentions:
                    pipeline_mention = PipelineMention(
                        text=m.name_form,
                        position=m.position,
                        chapter_index=m.chapter_index or 0,
                        context=m.context,
                        in_dialogue=False,  # V2 doesn't track this
                        is_agentive=False,  # V2 doesn't track this
                    )
                    mentions_list.append(pipeline_mention)

            chapters_present = (
                list(mention_info.chapter_distribution.keys())
                if mention_info and mention_info.chapter_distribution
                else []
            )

            pc = PipelineCharacter(
                id=char.id,
                canonical_name=char.canonical_name,
                aliases=list(dict.fromkeys(char.aliases or [])),
                mentions=mentions_list,
                first_appearance_chapter=char.first_appearance_chapter or 0,
                mention_count=char.mention_count,
                chapters_present=chapters_present,
                confidence=0.4,  # Lower confidence for NER extraction
                supporting_strategies=["v2_ner_extraction"],
                description="",
                is_narrator=False,
                narrative_role=None,
                role="minor",
            )
            result.append(pc)

        return result

    def _get_description_text(self, char: Character) -> str:
        """Get description text from a Character."""
        if char.descriptions:
            return char.descriptions[0].text
        return ""

    def _get_narrative_style(self, context: AgentContext) -> Optional[str]:
        """Extract narrative_style from summaries result metadata or chapter POV heuristics."""
        summaries_result = context.get_result("summaries")
        if not summaries_result:
            return None

        # Check pipeline_metadata first (if populated upstream)
        if hasattr(summaries_result, "pipeline_metadata"):
            style = summaries_result.pipeline_metadata.get("narrative_style")
            if style:
                return style

        # Heuristic: check pov_character across chapter summaries
        if hasattr(summaries_result, "summaries"):
            pov_chars = [
                s.pov_character for s in summaries_result.summaries
                if s.pov_character
            ]
            if pov_chars:
                from collections import Counter
                most_common = Counter(pov_chars).most_common(1)[0]
                if most_common[1] >= len(summaries_result.summaries) * 0.5:
                    return "first-person"

        # Fallback: check summary text for first-person indicators
        if hasattr(summaries_result, "summaries") and summaries_result.summaries:
            first_summary = summaries_result.summaries[0].summary.lower()
            first_person_markers = [" i ", " my ", " me ", "narrator", "first-person", "first person"]
            if sum(1 for m in first_person_markers if m in first_summary) >= 2:
                return "first-person"

        return None

    def _find_narrator_in_supporting(
        self,
        narrator_name: str,
        supporting_cast: list[Character],
    ) -> Optional[tuple[Character, list[Character]]]:
        """
        Search supporting_cast for name fragment(s) matching the narrator name.

        Handles split identities where e.g. "Nick Carraway" was extracted as
        separate supporting entries "Nick" (24 mentions) and "Carraway" (10 mentions),
        neither of which crossed the promotion threshold.  All fragments whose
        canonical name or alias is a contiguous word-sequence within narrator_name
        are merged into a single promoted character.

        Returns (merged_character, remaining_supporting) or None if no match found.
        """
        if not narrator_name or not supporting_cast:
            return None

        narrator_words = narrator_name.strip().lower().split()
        if not narrator_words:
            return None

        matches: list[Character] = []
        for char in supporting_cast:
            all_forms = [char.canonical_name] + list(char.aliases or [])
            for form in all_forms:
                form_lower = form.strip().lower()
                if not form_lower or len(form_lower) < 3:
                    continue
                form_words = form_lower.split()
                # Accept only if form_words is a contiguous sub-sequence of narrator_words
                n = len(narrator_words)
                k = len(form_words)
                found = any(
                    narrator_words[i:i + k] == form_words
                    for i in range(n - k + 1)
                )
                if found:
                    matches.append(char)
                    break

        if not matches:
            return None

        base = max(matches, key=lambda c: c.mention_count)
        merged_count = sum(c.mention_count for c in matches)

        all_aliases: list[str] = list(base.aliases or [])
        for char in matches:
            if char is base:
                continue
            if char.canonical_name != narrator_name and char.canonical_name not in all_aliases:
                all_aliases.append(char.canonical_name)
            for a in char.aliases or []:
                if a != narrator_name and a not in all_aliases:
                    all_aliases.append(a)

        first_chap = min(
            (c.first_appearance_chapter for c in matches if c.first_appearance_chapter is not None),
            default=None,
        )

        merged = Character(
            id=base.id,
            canonical_name=narrator_name,
            aliases=all_aliases,
            role="protagonist",
            mention_count=merged_count,
            is_narrator=True,
            narrative_role="First-Person Narrator",
            confidence=base.confidence,
            first_appearance_chapter=first_chap,
        )

        matched_ids = {c.id for c in matches}
        remaining = [c for c in supporting_cast if c.id not in matched_ids]

        logger.info(
            f"_find_narrator_in_supporting: merged "
            f"{[c.canonical_name for c in matches]} → '{narrator_name}' "
            f"(total mentions: {merged_count})"
        )
        return merged, remaining

    def _heuristic_narrator_from_mention_count(
        self,
        main_cast: list[Character],
        plot_summary: Optional[str],
    ) -> Optional[Character]:
        """
        Heuristic narrator identification for confirmed first-person narratives.

        When LLM narrator detection fails, fall back to selecting the highest
        name-mention main cast character who appears in the plot_summary.

        The narrator is typically the most prominent named character: they are
        frequently addressed by name in dialogue and appear throughout the narrative,
        giving them the highest mention count among main cast members.
        """
        if not main_cast:
            return None

        # Prefer candidates who are explicitly named in the plot_summary
        # (confirms they are plot-central, not a minor character with few mentions)
        candidates = []
        if plot_summary:
            plot_lower = plot_summary.lower()
            for char in main_cast:
                if char.canonical_name.lower() in plot_lower:
                    candidates.append(char)

        if not candidates:
            candidates = list(main_cast)

        # Universal invariant: exclude 1-2 mention fragments when there are
        # substantive candidates. A ≤ 2-mention character is not the narrator —
        # even a narrator who uses "I" will be addressed by name more than twice.
        # Only apply if at least one candidate has ≥ 5 mentions (avoid filtering
        # everything in very short texts where all counts are low).
        _max_count = max((c.mention_count for c in candidates), default=0)
        if _max_count >= 5:
            _eligible = [c for c in candidates if c.mention_count > 2]
            if _eligible:
                candidates = _eligible

        # Apply max-mention guard: in first-person stories the narrator uses "I" so their
        # name appears LESS frequently than the characters they describe (e.g., Gatsby).
        # If the candidate with the most mentions would be selected, check if there are
        # plausible lower-mention candidates — those are more likely the actual narrator.
        # This mirrors the same invariant applied in narrator.py _parse_result.
        _selected = max(candidates, key=lambda c: c.mention_count, default=None)
        if _selected and len(candidates) > 1:
            _sel_count = _selected.mention_count
            _others = [c for c in candidates if c.id != _selected.id]
            _max_other = max((c.mention_count for c in _others), default=0)
            if _sel_count > _max_other:
                # Selected is the max-mention character — possibly the story's subject
                _plausible = [
                    c for c in _others
                    if c.mention_count > 15 and c.mention_count <= _sel_count // 3
                ]
                if _plausible and _sel_count >= 5 * min(c.mention_count for c in _plausible):
                    # Among plausible, prefer characters who appear from chapter 0 (early appearance)
                    # Universal invariant: the narrator is present from the beginning.
                    _from_start = [
                        c for c in _plausible
                        if getattr(c, "first_appearance_chapter", None) == 0
                    ]
                    if _from_start:
                        _selected = max(_from_start, key=lambda c: c.mention_count)
                    else:
                        _selected = max(_plausible, key=lambda c: c.mention_count)
        return _selected

    def _find_narrator_name_from_vocative(self, text: str) -> Optional[str]:
        """Search raw text for direct address patterns to identify the narrator's actual name.

        In first-person narratives, the narrator's name is sometimes revealed when another
        character directly addresses them by name (e.g., "For the love of God, Montresor!").
        The narrator rarely names themselves (they write "I"), so their proper name has
        anomalously few text mentions compared to other characters.

        This is a universal pattern: look for proper names in vocative (direct address)
        contexts (e.g., ", Name!" or ", Name?"), then prefer the name with the fewest
        total text mentions — the narrator's name appears rarely while other characters'
        names appear throughout the narrative.

        Returns the most likely narrator name, or None if not found.
        """
        import re

        # Vocative pattern 1: proper name followed by "!" or "?"
        # Covers: "For the love of God, Montresor!" / "Come, Watson!" / "Help me, John?"
        vocative_pattern = re.compile(
            r"[,!]\s+([A-Z][a-zA-Z]{2,}(?:\s+[A-Z][a-zA-Z]{2,})?)\s*[!?]",
            re.MULTILINE,
        )
        # Vocative pattern 2: name between two commas (", Ted, let's go")
        # Covers prose style where the addressee is comma-delimited mid-sentence.
        vocative_pattern_comma = re.compile(
            r"[,!]\s+([A-Z][a-zA-Z]{2,}(?:\s+[A-Z][a-zA-Z]{2,})?)\s*,",
            re.MULTILINE,
        )

        name_vocative_counts: dict[str, int] = {}
        for pattern in (vocative_pattern, vocative_pattern_comma):
            for match in pattern.finditer(text):
                name = match.group(1).strip()
                name_vocative_counts[name] = name_vocative_counts.get(name, 0) + 1

        if not name_vocative_counts:
            return None

        def total_name_mentions(name: str) -> int:
            pat = re.compile(
                rf"(?<![A-Za-z0-9]){re.escape(name)}(?![A-Za-z0-9])",
                re.IGNORECASE,
            )
            return len(pat.findall(text))

        # Among names found in vocative contexts, prefer the one with FEWER total text
        # mentions. Rationale: in first-person narration the narrator's proper name appears
        # rarely (they write "I"), but is occasionally called out by other characters.
        # Frequently-mentioned names are more likely characters whom the narrator addresses,
        # not the narrator themselves.
        best_name = min(
            name_vocative_counts,
            key=lambda n: (-name_vocative_counts[n], total_name_mentions(n)),
        )
        logger.debug(
            f"_find_narrator_name_from_vocative: vocative counts={name_vocative_counts}, "
            f"selected='{best_name}' (total mentions={total_name_mentions(best_name)})"
        )
        return best_name
