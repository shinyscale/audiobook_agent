"""
Pronunciation flagging module.
Identifies words that may need pronunciation attention.
"""

import re
from collections import defaultdict
from typing import Optional, Set

try:
    import pronouncing
except ImportError:
    pronouncing = None

from ..models import (
    PronunciationEntry,
    PronunciationFlag,
    Character,
)


# Common words that might look unusual but have standard pronunciations
COMMON_WORDS_WHITELIST = {
    # Common names
    'michael', 'james', 'william', 'david', 'richard', 'joseph', 'thomas',
    'mary', 'patricia', 'jennifer', 'linda', 'elizabeth', 'barbara', 'susan',
    # Common places
    'london', 'paris', 'york', 'boston', 'chicago', 'angeles',
    # Common titles
    'chapter', 'prologue', 'epilogue', 'part', 'section',
    # Days/months
    'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
    'january', 'february', 'march', 'april', 'june', 'july', 'august',
    'september', 'october', 'november', 'december',
}

# Contraction fragments that result from tokenization splitting contractions
# These should never be flagged as they're not real words
CONTRACTION_FRAGMENTS = {
    # Negative contractions (n't splits off)
    "hadn", "wouldn", "couldn", "shouldn", "didn", "isn", "aren",
    "wasn", "weren", "don", "doesn", "won", "can", "mustn",
    "needn", "shan", "mightn", "hasn", "haven", "ain", "oughtn",
    # Verb contractions ('ll, 've, 're split off)
    "ll", "ve", "re",
    # Other common fragments
    "em",  # from 'em
    "twas", "tis",  # archaic contractions
    # Possessive 's that might get split
    "s",
}

# Homographs: words spelled the same but with different pronunciations
HOMOGRAPHS = {
    'read': ['present tense (reed)', 'past tense (red)'],
    'lead': ['to guide (leed)', 'metal (led)'],
    'live': ['to exist (liv)', 'in real time (lyve)'],
    'tear': ['to rip (tair)', 'from eye (teer)'],
    'wind': ['air movement (wind)', 'to turn (wynd)'],
    'bow': ['weapon/ribbon (boh)', 'to bend (bow)'],
    'row': ['line (roh)', 'argument (row)'],
    'sow': ['plant seeds (soh)', 'female pig (sow)'],
    'does': ['female deer (dohz)', 'verb form (duz)'],
    'bass': ['fish (bass)', 'low sound (base)'],
    'close': ['nearby (klohs)', 'to shut (klohz)'],
    'content': ['satisfied (kun-TENT)', 'what\'s inside (KON-tent)'],
    'desert': ['abandon (di-ZERT)', 'dry land (DEZ-ert)'],
    'entrance': ['way in (EN-truns)', 'to charm (en-TRANS)'],
    'invalid': ['not valid (in-VAL-id)', 'sick person (IN-vuh-lid)'],
    'minute': ['time unit (MIN-it)', 'tiny (my-NOOT)'],
    'object': ['thing (OB-jekt)', 'to oppose (ob-JEKT)'],
    'polish': ['to shine (POL-ish)', 'from Poland (POH-lish)'],
    'present': ['gift/current (PREZ-ent)', 'to give (pri-ZENT)'],
    'produce': ['vegetables (PROH-doos)', 'to make (pruh-DOOS)'],
    'project': ['plan (PROJ-ekt)', 'to forecast (pruh-JEKT)'],
    'rebel': ['revolutionary (REB-ul)', 'to revolt (ri-BEL)'],
    'record': ['disc/log (REK-ord)', 'to capture (ri-KORD)'],
    'refuse': ['decline (ri-FYOOZ)', 'trash (REF-yoos)'],
    'resume': ['continue (ri-ZOOM)', 'CV (REZ-oo-may)'],
    'separate': ['adj: distinct (SEP-rit)', 'verb: divide (SEP-uh-rayt)'],
    'subject': ['topic (SUB-jekt)', 'to expose (sub-JEKT)'],
    'wound': ['injury (woond)', 'past of wind (wownd)'],
}

# Patterns suggesting foreign words
FOREIGN_PATTERNS = [
    # French
    (r'\b\w*(?:eau|eux|aux|ois|oir|eur|ienne|ette)\b', 'French'),
    (r'\b(?:le|la|les|du|des|un|une|mon|ma|mes)\s+\w+', 'French'),
    # German
    (r'\b\w*(?:burg|berg|stein|mann|schaft|keit|heit|chen)\b', 'German'),
    # Spanish
    (r'\b\w*(?:ción|ñ|ería|ero|illo|ita)\b', 'Spanish'),
    # Italian
    (r'\b\w*(?:zione|etto|etta|issimo|ino|ini)\b', 'Italian'),
    # Latin (excluding "in" - too common in English)
    (r'\b(?:et|ad|de|ex|per|pro|sub)\s+[a-z]{4,}', 'Latin'),
]


class PronunciationFlagger:
    """Flags words that may need pronunciation attention."""
    
    def __init__(
        self,
        context_window: int = 50,
        max_examples: int = 3,
        use_cmu_dict: bool = True,
    ):
        self.context_window = context_window
        self.max_examples = max_examples
        self.use_cmu_dict = use_cmu_dict and pronouncing is not None
        
        # Build set of words in CMU dictionary
        self.known_words: Set[str] = set()
        if self.use_cmu_dict:
            # Get all words from CMU dict
            for word in pronouncing.cmudict.dict().keys():
                self.known_words.add(word.lower())
    
    def flag(
        self,
        text: str,
        characters: Optional[list[Character]] = None,
    ) -> list[PronunciationEntry]:
        """
        Flag words that may need pronunciation attention.
        
        Args:
            text: Full book text
            characters: Optional list of characters (their names will be flagged)
            
        Returns:
            List of PronunciationEntry objects
        """
        entries: dict[str, PronunciationEntry] = {}
        
        # Flag character names
        if characters:
            for char in characters:
                all_names = [char.canonical_name] + char.aliases
                for name in all_names:
                    for word in name.split():
                        word_lower = word.lower()
                        if word_lower not in COMMON_WORDS_WHITELIST:
                            self._add_entry(entries, word, text, PronunciationFlag.PROPER_NOUN)
        
        # Find all capitalized words (potential proper nouns)
        self._flag_proper_nouns(text, entries)
        
        # Flag homographs
        self._flag_homographs(text, entries)
        
        # Flag foreign words
        self._flag_foreign_words(text, entries)
        
        # Flag words not in dictionary
        if self.use_cmu_dict:
            self._flag_unknown_words(text, entries)
        
        # Convert to list and sort by occurrence count
        result = list(entries.values())
        result.sort(key=lambda e: e.occurrences, reverse=True)
        
        return result
    
    def _add_entry(
        self,
        entries: dict[str, PronunciationEntry],
        word: str,
        text: str,
        flag_reason: PronunciationFlag,
        position: Optional[int] = None,
    ) -> None:
        """Add or update a pronunciation entry."""
        word_lower = word.lower()
        
        # Skip very short words
        if len(word) < 2:
            return
        
        # Skip if in whitelist
        if word_lower in COMMON_WORDS_WHITELIST:
            return
        
        if word_lower not in entries:
            # Find first occurrence if not provided
            if position is None:
                match = re.search(r'\b' + re.escape(word) + r'\b', text, re.IGNORECASE)
                position = match.start() if match else 0
            
            # Get context
            context = self._get_context(text, position, len(word))
            
            entries[word_lower] = PronunciationEntry(
                word=word,
                flag_reason=flag_reason,
                occurrences=1,
                first_position=position,
                context_examples=[context] if context else [],
            )
        else:
            entries[word_lower].occurrences += 1
            
            # Add more context examples
            if position and len(entries[word_lower].context_examples) < self.max_examples:
                context = self._get_context(text, position, len(word))
                if context and context not in entries[word_lower].context_examples:
                    entries[word_lower].context_examples.append(context)
    
    def _get_context(self, text: str, position: int, word_length: int) -> str:
        """Get context around a word."""
        start = max(0, position - self.context_window)
        end = min(len(text), position + word_length + self.context_window)
        
        context = text[start:end].strip()
        # Clean up
        context = ' '.join(context.split())
        
        # Add ellipsis if truncated
        if start > 0:
            context = '...' + context
        if end < len(text):
            context = context + '...'
        
        return context
    
    def _flag_proper_nouns(self, text: str, entries: dict) -> None:
        """Flag capitalized words that appear to be proper nouns."""
        # Find capitalized words not at start of sentences
        # This pattern finds capitalized words preceded by lowercase letter and space
        pattern = r'(?<=[a-z]\s)([A-Z][a-z]+)'
        
        for match in re.finditer(pattern, text):
            word = match.group(1)
            word_lower = word.lower()
            
            # Skip if common word
            if word_lower in COMMON_WORDS_WHITELIST:
                continue
            
            # Skip if in dictionary
            if self.use_cmu_dict and word_lower in self.known_words:
                continue
            
            self._add_entry(entries, word, text, PronunciationFlag.PROPER_NOUN, match.start())
    
    def _flag_homographs(self, text: str, entries: dict) -> None:
        """Flag known homographs."""
        for word, pronunciations in HOMOGRAPHS.items():
            pattern = r'\b' + word + r'\b'
            for match in re.finditer(pattern, text, re.IGNORECASE):
                if word.lower() not in entries:
                    self._add_entry(entries, word, text, PronunciationFlag.HOMOGRAPH, match.start())
                    # Add pronunciation options as notes
                    entries[word.lower()].notes = f"Options: {'; '.join(pronunciations)}"
                else:
                    entries[word.lower()].occurrences += 1
    
    def _flag_foreign_words(self, text: str, entries: dict) -> None:
        """Flag words that appear to be from foreign languages."""
        for pattern, language in FOREIGN_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                word = match.group(0)
                word_lower = word.lower()
                
                # Skip very common words
                if word_lower in COMMON_WORDS_WHITELIST:
                    continue
                
                # Skip if already flagged for another reason
                if word_lower in entries:
                    continue
                
                self._add_entry(entries, word, text, PronunciationFlag.FOREIGN, match.start())
                if word_lower in entries:
                    entries[word_lower].notes = f"Appears to be {language}"
    
    def _flag_unknown_words(self, text: str, entries: dict) -> None:
        """Flag words not in the CMU pronunciation dictionary."""
        # Extract all words
        words = re.findall(r'\b[a-zA-Z]+\b', text)
        word_counts = defaultdict(int)
        word_first_pos = {}

        for i, word in enumerate(words):
            word_lower = word.lower()
            word_counts[word_lower] += 1
            if word_lower not in word_first_pos:
                # Find actual position in text
                match = re.search(r'\b' + re.escape(word) + r'\b', text)
                if match:
                    word_first_pos[word_lower] = match.start()

        for word_lower, count in word_counts.items():
            # Skip if already flagged
            if word_lower in entries:
                continue

            # Skip common/whitelist
            if word_lower in COMMON_WORDS_WHITELIST:
                continue

            # Skip contraction fragments (e.g., "hadn" from "hadn't")
            if word_lower in CONTRACTION_FRAGMENTS:
                continue

            # Skip if in dictionary
            if word_lower in self.known_words:
                continue

            # Skip very short words
            if len(word_lower) < 4:
                continue

            # Skip if just looks like a normal word (all lowercase, no unusual patterns)
            if word_lower.isalpha() and count < 3:
                continue

            position = word_first_pos.get(word_lower, 0)
            self._add_entry(entries, word_lower, text, PronunciationFlag.UNKNOWN, position)


def flag_pronunciations(
    text: str,
    characters: Optional[list[Character]] = None,
) -> list[PronunciationEntry]:
    """
    Convenience function to flag pronunciation items.
    
    Args:
        text: Full book text
        characters: Optional list of characters
        
    Returns:
        List of PronunciationEntry objects
    """
    flagger = PronunciationFlagger()
    return flagger.flag(text, characters)
