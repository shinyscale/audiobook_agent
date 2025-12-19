"""
Character extraction module.
Uses NER to identify characters, then clusters aliases and extracts descriptions.
"""

import re
from collections import defaultdict
from typing import Optional
from dataclasses import dataclass, field

try:
    import spacy
    from spacy.tokens import Doc, Span
except ImportError:
    spacy = None

from ..models import (
    Character,
    CharacterMention,
    CharacterDescription,
    ConfidenceLevel,
    StructuralElement,
    StructureType,
)


@dataclass
class CharacterCandidate:
    """A potential character found via NER."""
    name: str
    mentions: list[tuple[int, str]] = field(default_factory=list)  # (position, context)
    is_person: bool = True
    
    @property
    def mention_count(self) -> int:
        return len(self.mentions)


class CharacterExtractor:
    """Extracts and analyzes characters from text."""
    
    # Common words that get false-positive tagged as PERSON
    FALSE_POSITIVE_NAMES = {
        'god', 'lord', 'sir', 'madam', 'ma\'am', 'mr', 'mrs', 'ms', 'miss',
        'dr', 'doctor', 'professor', 'captain', 'colonel', 'general',
        'king', 'queen', 'prince', 'princess', 'duke', 'duchess',
        'dear', 'honey', 'sweetheart', 'darling',
        'mom', 'dad', 'mother', 'father', 'grandma', 'grandpa',
        'uncle', 'aunt', 'brother', 'sister', 'son', 'daughter',
        'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
        'january', 'february', 'march', 'april', 'may', 'june',
        'july', 'august', 'september', 'october', 'november', 'december',
        # Common words that look like names
        'chapter', 'prologue', 'epilogue', 'part', 'the', 'and', 'but',
    }
    
    # Common title prefixes to strip
    TITLE_PREFIXES = {'mr', 'mrs', 'ms', 'miss', 'dr', 'sir', 'lady', 'lord', 'comte', 'madame', 'monsieur'}
    
    # Patterns suggesting a place rather than a person
    PLACE_SUFFIXES = {'manor', 'house', 'castle', 'hall', 'park', 'gardens', 'street', 
                      'road', 'abbey', 'priory', 'inn', 'hotel', 'cottage', 'estate',
                      'cemetery', 'boulangerie', 'café', 'château', 'salon'}
    
    # Patterns that suggest a description near a name
    DESCRIPTION_PATTERNS = [
        # "X was a tall man"
        r'{name}\s+was\s+(?:a\s+)?([^.!?]+(?:man|woman|person|boy|girl|child|lady|gentleman)[^.!?]*)',
        # "X, a tall woman,"
        r'{name},\s+a\s+([^,]+),',
        # "X, who was..."
        r'{name},\s+who\s+(?:was|had|looked)\s+([^,]+)',
        # "the tall X" (adjective before name)
        r'the\s+(\w+(?:\s+\w+)?)\s+{name}',
        # "X's blue eyes"
        r'{name}\'s\s+([\w\s]+(?:eyes|hair|face|voice|smile|hands|skin))',
        # "X looked/appeared/seemed..."
        r'{name}\s+(?:looked|appeared|seemed)\s+([^.!?]+)',
    ]
    
    def __init__(
        self,
        spacy_model: str = "en_core_web_lg",
        min_mentions: int = 2,  # Minimum mentions to be considered a character
        context_window: int = 100,  # Characters of context around each mention
    ):
        self.min_mentions = min_mentions
        self.context_window = context_window
        self.nlp = None
        self.use_spacy = False
        
        if spacy is not None:
            # Try to load spaCy model
            for model_name in [spacy_model, "en_core_web_lg", "en_core_web_md", "en_core_web_sm"]:
                try:
                    self.nlp = spacy.load(model_name)
                    self.use_spacy = True
                    break
                except OSError:
                    continue
        
        if not self.use_spacy:
            print("⚠️  spaCy model not available, using regex-based character extraction (less accurate)")
    
    def _extract_candidates_regex(self, text: str) -> dict[str, CharacterCandidate]:
        """
        Fallback: Extract character candidates using regex patterns.
        Less accurate than NER but works without spaCy.
        """
        candidates = defaultdict(lambda: CharacterCandidate(name=""))
        
        # Pattern for potential character names:
        # - Title + Name: "Mr. Blackwood", "Lady Margaret"
        # - Two capitalized words: "Edmund Blackwood"
        # - Single capitalized words in dialogue tags: '"...," said Edmund'
        
        patterns = [
            # Title + Name
            r'\b((?:Mr|Mrs|Ms|Miss|Dr|Sir|Lady|Lord|Comte|Madame|Monsieur)\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b',
            # Full name (two or more capitalized words, not at sentence start)
            r'(?<=[a-z]\s)([A-Z][a-z]+\s+[A-Z][a-z]+)\b',
            # Name in dialogue tag
            r'[,""]\s*said\s+([A-Z][a-z]+)',
            r'[,""]\s*asked\s+([A-Z][a-z]+)',
            r'[,""]\s*replied\s+([A-Z][a-z]+)',
            r'[,""]\s*murmured\s+([A-Z][a-z]+)',
            r'[,""]\s*whispered\s+([A-Z][a-z]+)',
            # Name after "young/old"
            r'\b(?:young|old)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b',
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, text):
                name = match.group(1).strip()
                
                # Skip if too short or in false positives
                if len(name) < 2:
                    continue
                if name.lower() in self.FALSE_POSITIVE_NAMES:
                    continue
                
                # Skip if it looks like a place (ends with place suffix)
                name_words = name.lower().split()
                if name_words and name_words[-1] in self.PLACE_SUFFIXES:
                    continue
                
                # Get context
                global_start = match.start(1)
                context_start = max(0, global_start - self.context_window)
                context_end = min(len(text), global_start + len(name) + self.context_window)
                context = text[context_start:context_end]
                
                # Normalize name for grouping
                normalized = self._normalize_name(name)
                
                if candidates[normalized].name == "":
                    candidates[normalized].name = name
                candidates[normalized].mentions.append((global_start, context))
        
        return dict(candidates)
    
    def extract(
        self,
        text: str,
        structure: Optional[list[StructuralElement]] = None,
    ) -> list[Character]:
        """
        Extract characters from text.
        
        Args:
            text: Full book text
            structure: Optional structure elements for chapter tracking
            
        Returns:
            List of Character objects
        """
        # Process text with spaCy (in chunks for long texts) or regex fallback
        if self.use_spacy:
            candidates = self._extract_candidates(text)
        else:
            candidates = self._extract_candidates_regex(text)
        
        # Filter by minimum mentions
        candidates = {
            name: cand for name, cand in candidates.items()
            if cand.mention_count >= self.min_mentions
        }
        
        # Cluster aliases
        character_clusters = self._cluster_aliases(candidates)
        
        # Build Character objects
        characters = []
        for cluster_id, (canonical_name, aliases, all_mentions) in enumerate(character_clusters):
            # Get descriptions
            descriptions = self._extract_descriptions(canonical_name, aliases, text)
            
            # Find first appearance chapter
            first_chapter = None
            if structure and all_mentions:
                first_pos = min(m[0] for m in all_mentions)
                first_chapter = self._find_chapter_at_position(first_pos, structure)
            
            # Track which chapters character appears in
            chapter_appearances = set()
            if structure:
                for pos, _ in all_mentions:
                    ch = self._find_chapter_at_position(pos, structure)
                    if ch is not None:
                        chapter_appearances.add(ch)
            
            char = Character(
                id=f"char_{cluster_id:03d}",
                canonical_name=canonical_name,
                aliases=[a for a in aliases if a != canonical_name],
                descriptions=descriptions,
                first_appearance_chapter=first_chapter,
                mention_count=len(all_mentions),
                confidence=ConfidenceLevel.MEDIUM,
            )
            characters.append(char)
        
        # Sort by mention count (most mentioned first)
        characters.sort(key=lambda c: c.mention_count, reverse=True)
        
        return characters
    
    def _extract_candidates(self, text: str) -> dict[str, CharacterCandidate]:
        """Extract person entities from text using NER."""
        candidates = defaultdict(lambda: CharacterCandidate(name=""))
        
        # Process in chunks for memory efficiency
        chunk_size = 100000  # 100k characters per chunk
        
        for chunk_start in range(0, len(text), chunk_size):
            chunk_end = min(chunk_start + chunk_size, len(text))
            chunk = text[chunk_start:chunk_end]
            
            # Process with spaCy
            doc = self.nlp(chunk)
            
            for ent in doc.ents:
                if ent.label_ == "PERSON":
                    # Normalize whitespace (removes newlines, multiple spaces)
                    name = ' '.join(ent.text.split())
                    
                    # Skip false positives
                    if name.lower() in self.FALSE_POSITIVE_NAMES:
                        continue
                    
                    # Skip single letters or very short names
                    if len(name) < 2:
                        continue
                    
                    # Skip if mostly punctuation
                    if sum(1 for c in name if c.isalpha()) < len(name) * 0.5:
                        continue
                    
                    # Get context
                    global_start = chunk_start + ent.start_char
                    context_start = max(0, global_start - self.context_window)
                    context_end = min(len(text), global_start + len(name) + self.context_window)
                    context = text[context_start:context_end]
                    
                    # Normalize name for grouping
                    normalized = self._normalize_name(name)
                    
                    if candidates[normalized].name == "":
                        candidates[normalized].name = name  # Keep first form
                    candidates[normalized].mentions.append((global_start, context))
        
        return dict(candidates)
    
    def _normalize_name(self, name: str) -> str:
        """Normalize a name for comparison/grouping."""
        # Strip leading/trailing punctuation commonly attached to entity spans
        # e.g. '"Baker,"' -> 'Baker'
        name = name.strip().strip('\'"“”‘’.,;:!?()[]{}')
        # Lowercase
        name = name.lower()
        # Remove titles
        name = re.sub(r'^(mr|mrs|ms|miss|dr|prof|sir|lady|lord)\s*\.?\s*', '', name)
        # Remove stray punctuation again after title stripping
        name = name.strip('\'"“”‘’.,;:!?()[]{}')
        # Remove extra whitespace
        name = ' '.join(name.split())
        return name
    
    def _cluster_aliases(
        self,
        candidates: dict[str, CharacterCandidate],
    ) -> list[tuple[str, list[str], list[tuple[int, str]]]]:
        """
        Cluster name variants that likely refer to the same character.
        
        Returns list of (canonical_name, [aliases], [all_mentions])
        """
        clusters = []
        used_names = set()
        
        # Sort by mention count to start with most common names
        sorted_candidates = sorted(
            candidates.items(),
            key=lambda x: x[1].mention_count,
            reverse=True
        )
        
        for normalized, candidate in sorted_candidates:
            if normalized in used_names:
                continue
            
            # Start a new cluster
            cluster_names = [candidate.name]
            cluster_mentions = list(candidate.mentions)
            used_names.add(normalized)
            
            # Find potential aliases
            name_parts = normalized.split()
            
            for other_normalized, other_candidate in sorted_candidates:
                if other_normalized in used_names:
                    continue
                
                # Check if names are related
                if self._names_might_be_same_person(normalized, other_normalized, name_parts):
                    cluster_names.append(other_candidate.name)
                    cluster_mentions.extend(other_candidate.mentions)
                    used_names.add(other_normalized)
            
            # Pick canonical name (longest, most complete)
            canonical = max(cluster_names, key=lambda n: (n.count(' '), len(n)))
            
            clusters.append((canonical, cluster_names, cluster_mentions))
        
        return clusters
    
    def _names_might_be_same_person(
        self,
        name1: str,
        name2: str,
        name1_parts: list[str],
    ) -> bool:
        """Check if two names might refer to the same person."""
        name2_parts = name2.split()

        # Single name matches any part of multi-part name
        # e.g., "Tom" matches "Tom Buchanan"
        if len(name1_parts) == 1 and name1 in name2_parts:
            return True
        if len(name2_parts) == 1 and name2 in name1_parts:
            return True

        # Same first name
        if name1_parts and name2_parts and name1_parts[0] == name2_parts[0]:
            return True

        # Same last name (if both have multiple parts)
        if len(name1_parts) > 1 and len(name2_parts) > 1:
            if name1_parts[-1] == name2_parts[-1]:
                return True

        # One is substring of other
        if name1 in name2 or name2 in name1:
            return True

        # One name is just first or last name of other
        if len(name1_parts) > 1 and name2 in name1_parts:
            return True
        if len(name2_parts) > 1 and name1 in name2_parts:
            return True

        return False
    
    def _extract_descriptions(
        self,
        canonical_name: str,
        aliases: list[str],
        text: str,
    ) -> list[CharacterDescription]:
        """Extract descriptions associated with a character."""
        descriptions = []
        
        for name in aliases:
            for pattern_template in self.DESCRIPTION_PATTERNS:
                # Escape name for regex
                escaped_name = re.escape(name)
                pattern = pattern_template.format(name=escaped_name)
                
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    desc_text = match.group(1).strip()
                    
                    # Clean up description
                    desc_text = ' '.join(desc_text.split())
                    
                    # Skip very short or very long descriptions
                    if len(desc_text) < 5 or len(desc_text) > 200:
                        continue
                    
                    descriptions.append(CharacterDescription(
                        text=desc_text,
                        source_position=match.start(),
                        confidence=ConfidenceLevel.MEDIUM,
                    ))
        
        # Deduplicate similar descriptions
        unique_descriptions = []
        seen_texts = set()
        for desc in descriptions:
            normalized = desc.text.lower()
            if normalized not in seen_texts:
                seen_texts.add(normalized)
                unique_descriptions.append(desc)
        
        return unique_descriptions[:10]  # Limit to 10 descriptions
    
    def _find_chapter_at_position(
        self,
        position: int,
        structure: list[StructuralElement],
    ) -> Optional[int]:
        """Find which chapter a position falls within."""
        for elem in structure:
            if elem.type == StructureType.CHAPTER:
                if elem.start_position <= position < elem.end_position:
                    return elem.index
        return None


def extract_characters(
    text: str,
    structure: Optional[list[StructuralElement]] = None,
    min_mentions: int = 2,
) -> list[Character]:
    """
    Convenience function to extract characters from text.
    
    Args:
        text: Full book text
        structure: Optional structure elements
        min_mentions: Minimum mentions to include a character
        
    Returns:
        List of Character objects
    """
    extractor = CharacterExtractor(min_mentions=min_mentions)
    return extractor.extract(text, structure)
