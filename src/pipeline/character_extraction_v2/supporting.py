"""
Supporting Cast Extraction (F3)

Minor characters still matter for pronunciation and context, but don't need
the same accuracy as main cast. Simple NER + filtering is sufficient.

The tiered approach:
- Main cast: Profile-first from summaries (high accuracy)
- Supporting cast: NER + light filtering (best effort)
"""

import logging
import re
from dataclasses import dataclass
from typing import Optional

from ...llm.client import LLMClient
from ...models import Character, ConfidenceLevel

logger = logging.getLogger(__name__)


@dataclass
class SupportingCharacter:
    """A supporting/minor character extracted via NER."""

    name: str
    mention_count: int
    first_position: int
    role: str = "minor"
    aliases: list[str] = None  # Populated during merge

    def __post_init__(self):
        if self.aliases is None:
            self.aliases = []
    description: str = ""


class SupportingCastExtractor:
    """
    Extracts supporting characters via NER, filtering out main cast names.

    This provides best-effort extraction for minor characters without
    the complex merge logic that causes v1 to fail on main cast.
    """

    def __init__(
        self,
        full_text: str,
        min_mentions: int = 3,
    ):
        """
        Initialize the extractor.

        Args:
            full_text: Complete text of the book
            min_mentions: Minimum mentions for a character to be included
        """
        self.full_text = full_text
        self.min_mentions = min_mentions
        self._nlp = None

    def _get_nlp(self):
        """Lazy-load spaCy model."""
        if self._nlp is None:
            try:
                import spacy

                self._nlp = spacy.load("en_core_web_lg")
            except OSError:
                logger.warning("spaCy model not found, using small model")
                import spacy

                try:
                    self._nlp = spacy.load("en_core_web_sm")
                except OSError:
                    logger.error("No spaCy model available")
                    return None
        return self._nlp

    def extract(
        self,
        main_cast_names: set[str],
        llm_client: Optional[LLMClient] = None,
    ) -> list[Character]:
        """
        Extract supporting characters via NER.

        Args:
            main_cast_names: Set of main cast names/aliases to exclude
            llm_client: Optional LLM for generating brief profiles

        Returns:
            List of supporting Character objects
        """
        nlp = self._get_nlp()
        if nlp is None:
            logger.warning("NER unavailable, skipping supporting cast extraction")
            return []

        # Build normalized name set for filtering
        main_cast_normalized = {self._normalize_name(n) for n in main_cast_names}

        # Process text in chunks (spaCy has memory limits)
        chunk_size = 100000
        name_counts: dict[str, int] = {}
        name_positions: dict[str, int] = {}

        for start in range(0, len(self.full_text), chunk_size):
            chunk = self.full_text[start : start + chunk_size]
            doc = nlp(chunk)

            for ent in doc.ents:
                # Accept PERSON entities and ORG entities (some names misclassified as organizations)
                # Reject GPE (geopolitical entities), LOC (locations), and other non-character types
                if ent.label_ not in ("PERSON", "ORG"):
                    continue

                name = ent.text.strip()

                # Skip if it's a main cast name
                if self._normalize_name(name) in main_cast_normalized:
                    continue

                # Skip if it's a likely synonym of a main cast descriptive handle
                if self._is_descriptive_synonym(name, main_cast_names):
                    continue

                # Skip if it looks like a partial name or noise
                if not self._is_valid_name(name):
                    continue

                # Skip if it's likely a geographic entity (even if labeled as ORG)
                if self._is_likely_geographic(name):
                    continue

                # Skip if it's an organization (tagged as ORG and matches org patterns)
                if self._is_organization_name(name, ent.label_):
                    continue

                # Track counts and positions
                name_counts[name] = name_counts.get(name, 0) + 1
                if name not in name_positions:
                    name_positions[name] = start + ent.start_char

        # Filter by minimum mentions
        supporting = []
        for name, count in name_counts.items():
            if count >= self.min_mentions:
                supporting.append(
                    SupportingCharacter(
                        name=name,
                        mention_count=count,
                        first_position=name_positions[name],
                    )
                )

        # Sort by mention count (most mentioned first)
        supporting.sort(key=lambda x: -x.mention_count)

        # Merge obvious aliases (e.g., "Ted Frith" and "Ted")
        supporting = self._merge_obvious_aliases(supporting)

        # Convert to Character objects
        characters = self._to_characters(supporting)

        logger.info(f"Extracted {len(characters)} supporting characters via NER")
        return characters

    def _normalize_name(self, name: str) -> str:
        """Normalize a name for comparison."""
        # Lowercase, remove titles, collapse whitespace
        name = name.lower().strip()
        titles = ["mr.", "mrs.", "ms.", "miss", "dr.", "lord", "lady", "sir"]
        for title in titles:
            if name.startswith(title + " "):
                name = name[len(title) + 1 :]
        return re.sub(r"\s+", " ", name)

    def _is_valid_name(self, name: str) -> bool:
        """Check if a name looks like a valid character name."""
        # Must have at least one letter
        if not any(c.isalpha() for c in name):
            return False

        # Skip single letters or very short
        if len(name) < 2:
            return False

        # Skip multi-word phrases with Latin/Greek grammatical patterns
        # This catches epigraph fragments like "amicae visitarem" without vocabulary lists
        if self._is_likely_foreign_phrase(name):
            return False

        # Skip common false positives (religious terms, titles, etc.)
        skip_terms = {
            "god",
            "lord",
            "christ",
            "jesus",  # Religious exclamation, not character
            "heaven",
            "hell",
            "sir",
            "madam",
            "ma'am",
            "dear",
        }
        if name.lower() in skip_terms:
            return False

        # Skip wine types and alcoholic beverages (common false positives)
        wine_types = {
            "amontillado",
            "sherry",
            "medoc",
            "port",
            "bordeaux",
            "champagne",
            "burgundy",
            "chianti",
            "cognac",
            "brandy",
        }
        if name.lower() in wine_types:
            return False

        # Skip educational institutions (common false positives)
        institutions = {
            "oxford",
            "cambridge",
            "harvard",
            "yale",
            "princeton",
            "stanford",
            "mit",
            "eton",
            "westminster",
        }
        if name.lower() in institutions:
            return False

        return True

    def _is_likely_foreign_phrase(self, name: str) -> bool:
        """
        Detect if a multi-word phrase is likely a foreign language quote/epigraph.

        Uses universal grammatical patterns (Latin/Greek/French verb endings),
        not vocabulary lists. This prevents extracting Latin epigraphs like
        "amicae visitarem" or French quotes as characters.

        Returns True if the phrase should be filtered out.
        """
        # Only check multi-word phrases (2+ words)
        words = name.strip().split()
        if len(words) < 2:
            return False

        # Check for Latin verb conjugation endings (very common in epigraphs)
        # These are grammatical patterns, not vocabulary
        latin_verb_endings = (
            # Present/imperfect subjunctive
            "arem", "erem", "irem",  # 1st person (visitarem = "I should visit")
            "ares", "eres", "ires",  # 2nd person
            "aret", "eret", "iret",  # 3rd person
            # Perfect/pluperfect
            "avi", "ivi", "atum", "itum",
            # Gerunds/gerundives
            "andi", "endi", "undi",
        )

        # Check for Greek grammatical endings
        greek_endings = (
            "ος", "ον", "ων", "ας",  # Nominative/genitive markers
        )

        # If any word has these endings, likely foreign
        for word in words:
            word_lower = word.lower().strip(".,;:!?\"'")
            for ending in latin_verb_endings:
                if word_lower.endswith(ending):
                    logger.debug(
                        f"Filtering '{name}' as likely Latin phrase (word '{word}' has Latin ending '{ending}')"
                    )
                    return True
            for ending in greek_endings:
                if word.endswith(ending):
                    logger.debug(
                        f"Filtering '{name}' as likely Greek phrase (word '{word}' has Greek ending '{ending}')"
                    )
                    return True

        return False

    def _is_descriptive_synonym(self, name: str, main_cast_names: set[str]) -> bool:
        """
        Check if a descriptive handle is a likely synonym of a main cast character.

        This handles cases where unnamed characters are referenced by multiple
        descriptive terms (e.g., "the creature", "the monster", "the fiend").

        Returns True if the name should be filtered (is likely a duplicate).
        """
        name_lower = name.lower()

        # Only check descriptive patterns like "the X" or "the X Y"
        if not name_lower.startswith("the "):
            return False

        # Extract the descriptor (e.g., "creature" from "the creature")
        descriptor = name_lower[4:].strip()  # Remove "the "

        # Common synonym groups for unnamed characters
        # Each group contains descriptive terms that often refer to the same entity
        synonym_groups = [
            # Supernatural/created beings
            {"creature", "monster", "fiend", "daemon", "wretch", "being", "thing"},
            # Authority figures
            {"stranger", "visitor", "guest", "traveler", "intruder"},
            # Generic descriptors
            {"man", "woman", "boy", "girl", "child", "person"},
        ]

        # Check if descriptor matches any synonym group
        for group in synonym_groups:
            if descriptor in group:
                # Check if any other term from the group exists in main cast
                for term in group:
                    if f"the {term}" in main_cast_names:
                        logger.debug(
                            f"Filtering '{name}' as likely synonym of 'the {term}' "
                            f"(both in synonym group: {group})"
                        )
                        return True

        return False

    def _is_likely_geographic(self, name: str) -> bool:
        """
        Check if a name is likely a geographic entity (city, river, country, etc.).

        Returns True if the name should be filtered (is likely a place, not a person).
        """
        # Common geographic entities that appear in literature
        # Focus on entities that spaCy often mislabels as ORG
        common_places = {
            "rhine",
            "thames",
            "seine",
            "danube",
            "nile",
            "mississippi",
            "arve",  # Rivers (Arve is a river near Geneva in Frankenstein)
            "alps",
            "pyrenees",
            "andes",
            "himalaya",  # Mountains
            "geneva",
            "paris",
            "london",
            "rome",
            "venice",
            "milan",  # Cities (European classics)
            "ingolstadt",
            "strasbourg",
            "strasburgh",  # Old spelling variant of Strasbourg
            "heidelberg",
            "zurich",  # German/Swiss cities (Frankenstein)
            "oxford",
            "cambridge",
            "edinburgh",
            "dublin",  # UK/Ireland cities
            "america",
            "england",
            "france",
            "germany",
            "italy",
            "switzerland",  # Countries
            "europe",
            "asia",
            "africa",  # Continents
        }

        name_lower = name.lower().strip()

        # Check against known geographic entities
        if name_lower in common_places:
            logger.debug(f"Filtering '{name}' as likely geographic entity")
            return True

        # Check if it ends with common geographic suffixes
        geographic_suffixes = (
            "river",
            "mountain",
            "sea",
            "ocean",
            "lake",
            "bay",
            "valley",
            "forest",
        )
        if any(name_lower.endswith(suffix) for suffix in geographic_suffixes):
            logger.debug(f"Filtering '{name}' as likely geographic entity (suffix match)")
            return True

        # Check for French mountain prefixes (Mont = mountain)
        # Examples: Mont Blanc, Mont Salêve
        if name_lower.startswith("mont ") and len(name_lower) > 5:
            logger.debug(f"Filtering '{name}' as likely geographic entity (Mont prefix)")
            return True

        return False

    def _is_organization_name(self, name: str, entity_label: str) -> bool:
        """
        Check if a name is likely an organization/institution rather than a character.
        
        This method uses a small, universal reference list of organizational indicators
        (allowed per CLAUDE.md), not a growing vocabulary deny-list.
        
        Args:
            name: The entity text
            entity_label: The NER label (PERSON, ORG, etc.)
            
        Returns:
            True if the name should be filtered (is likely an organization)
        """
        name_lower = name.lower().strip()
        
        # If NER tagged as PERSON, trust it (don't filter)
        if entity_label == "PERSON":
            return False
        
        # Common organizational suffixes (universal indicators)
        org_suffixes = (
            "company",
            "corporation",
            "corp",
            "inc",
            "ltd",
            "llc",
            "association",
            "society",
            "foundation",
            "institute",
            "university",
            "college",
            "academy",
            "department",
            "ministry",
            "bureau",
            "agency",
            "commission",
        )
        if any(name_lower.endswith(suffix) for suffix in org_suffixes):
            logger.debug(f"Filtering '{name}' as organization (suffix match)")
            return True
        
        # Common organizational name patterns (small universal list)
        # These are organizational entity types, not book-specific vocabulary
        org_patterns = {
            "red cross",
            "white house",
            "pentagon",
            "congress",
            "parliament",
            "senate",
            "house of commons",
            "house of lords",
            "the army",
            "the navy",
            "the marines",
            "air force",
            "police",
            "fbi",
            "cia",
            "mi6",
            "un",
            "nato",
            "eu",
        }
        if name_lower in org_patterns:
            logger.debug(f"Filtering '{name}' as organization (known entity)")
            return True
        
        return False


    def _merge_obvious_aliases(
        self,
        supporting: list[SupportingCharacter],
    ) -> list[SupportingCharacter]:
        """
        Merge obvious aliases in supporting characters using deterministic rules.

        Examples:
        - "Ted Frith" and "Ted" → merge into "Ted Frith" with "Ted" as alias
        - "Dr. Watson" and "Watson" → merge into "Dr. Watson"
        - "Johnny" may be a nickname for "John" if both exist

        Uses simple substring and common nickname patterns (no LLM calls).
        """
        if len(supporting) < 2:
            return supporting

        # Track which characters have been merged
        merged_indices = set()
        result = []

        for i, char in enumerate(supporting):
            if i in merged_indices:
                continue

            # Normalize for comparison
            name_norm = self._normalize_name(char.name)
            words_in_name = set(name_norm.split())

            # Look for shorter names that might be aliases
            for j in range(i + 1, len(supporting)):
                if j in merged_indices:
                    continue

                other = supporting[j]
                other_norm = self._normalize_name(other.name)
                other_words = set(other_norm.split())

                should_merge = False

                # Rule 1: Substring match (shorter name is substring of longer)
                # "Ted" is substring of "Ted Frith"
                if other_norm in name_norm or name_norm in other_norm:
                    should_merge = True
                    logger.debug(f"Merging '{other.name}' into '{char.name}' (substring match)")

                # Rule 2: Common word overlap (single-word vs multi-word)
                # "Ted" and "Ted Frith" share "ted"
                elif len(other_words) == 1 and other_words.issubset(words_in_name):
                    should_merge = True
                    logger.debug(f"Merging '{other.name}' into '{char.name}' (word overlap)")

                # Rule 3: Common nickname patterns
                # "Johnny" for "John", "Teddy" for "Ted", "Billy" for "Bill"
                elif self._is_likely_nickname(other_norm, words_in_name):
                    should_merge = True
                    logger.debug(f"Merging '{other.name}' into '{char.name}' (nickname pattern)")

                # Rule 4: Spelling variants (Levenshtein distance <= 1)
                # "Ted Frith" and "Ted Firth" differ by 1 character
                elif self._is_spelling_variant(name_norm, other_norm):
                    should_merge = True
                    logger.debug(f"Merging '{other.name}' into '{char.name}' (spelling variant)")

                if should_merge:
                    # Merge: add mention counts, track as merged
                    char.mention_count += other.mention_count
                    char.first_position = min(char.first_position, other.first_position)
                    merged_indices.add(j)
                    # Track the merged name as an alias
                    if other.name not in char.aliases and other.name != char.name:
                        char.aliases.append(other.name)

            result.append(char)

        logger.info(f"Merged {len(merged_indices)} alias candidates in supporting cast")
        return result

    def _is_likely_nickname(self, nickname: str, full_name_words: set[str]) -> bool:
        """
        Check if a single-word name is a likely nickname for a longer name.

        Common patterns:
        - "Johnny" for "John"
        - "Teddy" for "Ted" or "Theodore"
        - "Billy" for "Bill" or "William"
        - "Tommy" for "Tom" or "Thomas"
        """
        # Common -y/-ie diminutive endings
        if nickname.endswith('y') or nickname.endswith('ie'):
            base = nickname[:-1] if nickname.endswith('y') else nickname[:-2]

            # Check if base matches any word in the full name
            for word in full_name_words:
                if word.startswith(base):
                    return True

                # Special cases: "Johnny" for "John", "Billy" for "Bill"
                if base.endswith('nn') and (base[:-2] + 'n' in word or base[:-1] in word):
                    return True


    def _is_spelling_variant(self, name1: str, name2: str) -> bool:
        """
        Check if two names are spelling variants (Levenshtein distance <= 1).
        
        Examples:
        - "ted frith" and "ted firth" → True (1 character difference)
        - "john" and "johnny" → False (3 character difference - handled by nickname rules)
        
        This catches minor spelling inconsistencies in the source text.
        """
        # Simple Levenshtein distance calculation for short strings
        if abs(len(name1) - len(name2)) > 1:
            # If lengths differ by more than 1, can't be 1-edit distance
            return False
        
        # Count differences
        differences = 0
        i, j = 0, 0
        
        while i < len(name1) and j < len(name2):
            if name1[i] != name2[j]:
                differences += 1
                if differences > 1:
                    return False
                # Try both deletion and substitution
                if len(name1) > len(name2):
                    i += 1  # Deletion from name1
                elif len(name2) > len(name1):
                    j += 1  # Deletion from name2
                else:
                    i += 1  # Substitution
                    j += 1
            else:
                i += 1
                j += 1
        
        # Account for trailing character difference
        differences += (len(name1) - i) + (len(name2) - j)
        
        return differences <= 1

        return False

    def _to_characters(
        self,
        supporting: list[SupportingCharacter],
    ) -> list[Character]:
        """Convert supporting characters to Character model objects."""
        characters = []

        for i, sc in enumerate(supporting):
            char = Character(
                id=f"supporting_{i}",
                canonical_name=sc.name,
                aliases=sc.aliases,
                role="minor",
                mention_count=sc.mention_count,
                confidence=ConfidenceLevel.LOW,  # NER extraction is lower confidence
            )

            # Set first appearance based on position
            # (We don't have chapter info here, but it could be added)

            characters.append(char)

        return characters

    def generate_profiles(
        self,
        characters: list[Character],
        llm_client: LLMClient,
        chapter_summaries: list[str],
    ) -> list[Character]:
        """
        Optionally generate brief profiles for supporting characters.

        This is a light LLM call - no complex merge logic.
        """
        if not characters:
            return characters

        # For efficiency, batch characters
        names = [c.canonical_name for c in characters[:20]]  # Limit to top 20

        prompt = f"""Given these chapter summaries and minor character names,
provide a ONE SENTENCE role description for each character if they appear.

SUMMARIES:
{chr(10).join(chapter_summaries[:5])}

CHARACTERS: {', '.join(names)}

OUTPUT FORMAT (JSON):
```json
{{
  "Character Name": "Brief one-sentence role"
}}
```

Only include characters that appear in the summaries. Return empty {{}} if none found."""

        result, response = llm_client.query_json(prompt)

        if result and isinstance(result, dict):
            for char in characters:
                if char.canonical_name in result:
                    desc = result[char.canonical_name]
                    if desc:
                        from ...models import CharacterDescription

                        char.descriptions = [
                            CharacterDescription(
                                text=desc,
                                source_position=0,
                                confidence=ConfidenceLevel.LOW,
                            )
                        ]

        return characters
