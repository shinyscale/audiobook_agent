"""
Named-entity pronunciation proposer.

Catches multi-word foreign place names (e.g. "Chu Lai", "Da Nang", "Qui Nhon")
that the single-token CMU proposer never sees as units, plus short place names
("Hue") that fall below the CMU minimum-word-length cutoff. Uses spaCy GPE/LOC
named-entity recognition over the narrative body.
"""

import logging
from typing import TYPE_CHECKING, Optional

from ..models import PronunciationFlag, PronunciationMention, PronunciationProposal
from .base import BasePronunciationProposer
from .cmu_proposer import COMMON_WORDS_WHITELIST

if TYPE_CHECKING:
    from ..word_index import WordIndex

logger = logging.getLogger(__name__)


class EntityProposer(BasePronunciationProposer):
    """Proposes multi-word / short foreign place names via spaCy NER."""

    name = "entity"

    # Place labels we always consider. spaCy frequently mislabels foreign
    # multi-word place names as PERSON (e.g. "Chu Lai"), so PERSON is also
    # consulted but constrained to multi-word, non-character entities below.
    _PLACE_LABELS = {"GPE", "LOC"}

    def __init__(
        self,
        body_range: Optional[tuple[int, int]] = None,
        min_occurrences: int = 1,
    ):
        """
        Args:
            body_range: (start, end) of the narrative body; entities outside it
                (front/back matter, glossary, acknowledgements) are ignored.
            min_occurrences: Minimum occurrences to propose an entity.
        """
        self.body_range = body_range
        self.min_occurrences = min_occurrences
        self._nlp = None

    def _get_nlp(self):
        """Lazy-load spaCy model (mirrors supporting.py)."""
        if self._nlp is None:
            try:
                import spacy

                self._nlp = spacy.load("en_core_web_lg")
            except OSError:
                logger.warning("spaCy en_core_web_lg not found, trying small model")
                import spacy

                try:
                    self._nlp = spacy.load("en_core_web_sm")
                except OSError:
                    logger.error("No spaCy model available, entity proposer disabled")
                    return None
        return self._nlp

    def _is_all_english(self, entity_text: str) -> bool:
        """True if every token of the entity is ordinary English.

        Checked against the common-word WHITELIST only — NOT the CMU dictionary,
        which contains many foreign proper nouns (saigon, hue, chu, lai), so a
        CMU check would wrongly classify those cities as English and drop them.
        The whitelist still contains common English place tokens (new, york,
        london, river, road), so "New York"/"River Road" are correctly skipped.
        """
        tokens = [t for t in entity_text.lower().split() if t.isalpha()]
        if not tokens:
            return False
        return all(tok in COMMON_WORDS_WHITELIST for tok in tokens)

    @staticmethod
    def _is_acronym(entity_text: str) -> bool:
        """All-caps initialisms (VC, CP, ARVN, ROTC) — handled by the acronym /
        glossary paths, not the place proposer."""
        compact = entity_text.replace(".", "").replace(" ", "")
        return compact.isupper() and len(compact) <= 5

    @staticmethod
    def _tokens_title_case(entity_text: str) -> bool:
        """Every alpha token starts uppercase (drops dialogue junk like
        'mi chica', 'villes')."""
        toks = [t for t in entity_text.split() if any(c.isalpha() for c in t)]
        return bool(toks) and all(t[0].isupper() for t in toks)

    def propose(
        self,
        full_text: str,
        chapter_boundaries: list[tuple[int, int, int]],
        character_names: Optional[list[str]] = None,
        word_index: Optional["WordIndex"] = None,
    ) -> list[PronunciationProposal]:
        nlp = self._get_nlp()
        if nlp is None:
            return []

        # Tokens that already belong to a known character — don't re-flag them.
        char_tokens = {
            w.lower() for n in (character_names or []) for w in str(n).split() if w.isalpha()
        }

        # First gather every PERSON/GPE/LOC occurrence, tracking which entity
        # texts EVER receive a place (GPE/LOC) label. spaCy mislabels foreign
        # place names as PERSON ("Chu Lai" = PERSON 16x / GPE 1x), while real
        # person name-drops ("Ron Ellis") never get a place label — so a place
        # label anywhere is the signal that a PERSON-tagged mention is a place.
        place_keys: set[str] = set()
        # key -> {"forms": {text: count}, "positions": [int]}
        candidates: dict[str, dict] = {}

        chunk_size = 100000
        for start in range(0, len(full_text), chunk_size):
            chunk = full_text[start : start + chunk_size]
            doc = nlp(chunk)
            for ent in doc.ents:
                is_place = ent.label_ in self._PLACE_LABELS
                is_person = ent.label_ == "PERSON"
                if not (is_place or is_person):
                    continue
                ent_pos = start + ent.start_char
                # Restrict to the narrative body when known.
                if self.body_range is not None and not (
                    self.body_range[0] <= ent_pos < self.body_range[1]
                ):
                    continue
                text = " ".join(ent.text.split())
                if not text or not any(c.isalpha() for c in text):
                    continue
                if self._is_acronym(text):
                    continue
                if not self._tokens_title_case(text):
                    continue
                if self._is_all_english(text):
                    continue
                key = text.lower()
                # Skip entities that overlap a known character — those are people.
                if key in char_tokens or any(
                    tok in char_tokens for tok in key.split() if tok.isalpha()
                ):
                    continue
                if is_place:
                    place_keys.add(key)
                rec = candidates.setdefault(key, {"forms": {}, "positions": []})
                rec["forms"][text] = rec["forms"].get(text, 0) + 1
                rec["positions"].append(ent_pos)

        # Keep only entities that earned a place label somewhere — this drops
        # pure-PERSON name-drops while retaining mislabeled foreign place names.
        entities = {k: v for k, v in candidates.items() if k in place_keys}

        proposals = []
        for key, rec in entities.items():
            positions = rec["positions"]
            if len(positions) < self.min_occurrences:
                continue
            canonical = max(rec["forms"], key=rec["forms"].get)
            mentions = [
                PronunciationMention(
                    word_form=canonical,
                    position=pos,
                    chapter_index=self._get_chapter_for_position(pos, chapter_boundaries),
                    context=self._extract_context(full_text, pos, len(canonical)),
                )
                for pos in positions
            ]
            proposals.append(
                PronunciationProposal(
                    strategy=self.name,
                    word=canonical,
                    flag_reason=PronunciationFlag.FOREIGN,
                    mentions=mentions,
                    confidence=0.65,
                    reasoning="Place name detected by named-entity recognition",
                )
            )

        logger.info(f"Entity proposer found {len(proposals)} place names")
        return proposals
