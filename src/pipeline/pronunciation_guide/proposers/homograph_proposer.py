"""
Homograph proposer.

Identifies known homographs - words spelled the same but with different pronunciations.
"""

import logging
import re
from typing import TYPE_CHECKING, Optional

from ..models import PronunciationFlag, PronunciationMention, PronunciationProposal
from .base import BasePronunciationProposer

if TYPE_CHECKING:
    from ..word_index import WordIndex

logger = logging.getLogger(__name__)

# Common homographs to exclude - too common for narrators to need pronunciation help
# These are valid homographs but appear frequently enough that narrators know them
COMMON_HOMOGRAPHS_EXCLUSION = {
    "object",   # "an object" vs "to object" - extremely common
    "record",   # "a record" vs "to record" - extremely common
    "use",      # "noun: a use" vs "verb: to use" - extremely common
    "present",  # "a present/be present" vs "to present" - extremely common
}

# Homographs: words spelled the same but with different pronunciations
HOMOGRAPHS = {
    "read": ["present tense (REED)", "past tense (RED)"],
    "lead": ["to guide (LEED)", "metal (LED)"],
    "live": ["to exist (LIV)", "in real time (LYVE)"],
    "tear": ["to rip (TAIR)", "from eye (TEER)"],
    "wind": ["air movement (WIND)", "to turn (WYND)"],
    "bow": ["weapon/ribbon (BOH)", "to bend (BOW)"],
    "row": ["line (ROH)", "argument (ROW)"],
    "sow": ["plant seeds (SOH)", "female pig (SOW)"],
    "does": ["female deer (DOHZ)", "verb form (DUZ)"],
    "bass": ["fish (BASS)", "low sound (BASE)"],
    "close": ["nearby (KLOHS)", "to shut (KLOHZ)"],
    "content": ["satisfied (kun-TENT)", "what's inside (KON-tent)"],
    "desert": ["abandon (di-ZERT)", "dry land (DEZ-ert)"],
    "entrance": ["way in (EN-truns)", "to charm (en-TRANS)"],
    "invalid": ["not valid (in-VAL-id)", "sick person (IN-vuh-lid)"],
    "minute": ["time unit (MIN-it)", "tiny (my-NOOT)"],
    "polish": ["to shine (POL-ish)", "from Poland (POH-lish)"],
    "produce": ["vegetables (PROH-doos)", "to make (pruh-DOOS)"],
    "project": ["plan (PROJ-ekt)", "to forecast (pruh-JEKT)"],
    "rebel": ["revolutionary (REB-ul)", "to revolt (ri-BEL)"],
    "refuse": ["decline (ri-FYOOZ)", "trash (REF-yoos)"],
    "resume": ["continue (ri-ZOOM)", "CV (REZ-oo-may)"],
    "separate": ["adj: distinct (SEP-rit)", "verb: divide (SEP-uh-rayt)"],
    "subject": ["topic (SUB-jekt)", "to expose (sub-JEKT)"],
    "wound": ["injury (WOOND)", "past of wind (WOWND)"],
    "abuse": ["noun (uh-BYOOS)", "verb (uh-BYOOZ)"],
    "excuse": ["noun (ek-SKYOOS)", "verb (ek-SKYOOZ)"],
    # Removed 'house' - too common, distinction not useful for narrators
    # Removed 'object', 'record', 'use', 'present' - moved to COMMON_HOMOGRAPHS_EXCLUSION
    "alternate": ["adj (AWL-ter-nit)", "verb (AWL-ter-nayt)"],
    "deliberate": ["adj (di-LIB-er-it)", "verb (di-LIB-er-ayt)"],
    "duplicate": ["noun/adj (DOO-pli-kit)", "verb (DOO-pli-kayt)"],
    "elaborate": ["adj (i-LAB-er-it)", "verb (i-LAB-er-ayt)"],
    "estimate": ["noun (ES-ti-mit)", "verb (ES-ti-mayt)"],
    "moderate": ["adj (MOD-er-it)", "verb (MOD-er-ayt)"],
    "intimate": ["adj (IN-ti-mit)", "verb (IN-ti-mayt)"],
}


class HomographProposer(BasePronunciationProposer):
    """Proposes known homographs with multiple pronunciations."""

    name = "homograph"

    def propose(
        self,
        full_text: str,
        chapter_boundaries: list[tuple[int, int, int]],
        character_names: Optional[list[str]] = None,
        word_index: Optional["WordIndex"] = None,
    ) -> list[PronunciationProposal]:
        """Find known homographs in text.

        Uses WordIndex if available for O(1) lookups, otherwise falls back
        to full text scanning.
        """
        proposals = []

        for word, pronunciations in HOMOGRAPHS.items():
            # Use WordIndex if available (O(1) lookup)
            if word_index is not None:
                if not word_index.has_word(word):
                    continue

                occurrences = word_index.get_occurrences(word)
                mentions = []
                for occ in occurrences:
                    context = self._extract_context(full_text, occ.position, len(occ.original_form))
                    mentions.append(
                        PronunciationMention(
                            word_form=occ.original_form,
                            position=occ.position,
                            chapter_index=occ.chapter_index,
                            context=context,
                        )
                    )
            else:
                # Fallback: regex scan
                pattern = r"\b" + re.escape(word) + r"\b"
                mentions = []

                for match in re.finditer(pattern, full_text, re.IGNORECASE):
                    position = match.start()
                    chapter_idx = self._get_chapter_for_position(position, chapter_boundaries)
                    context = self._extract_context(full_text, position, len(word))

                    mentions.append(
                        PronunciationMention(
                            word_form=match.group(0),
                            position=position,
                            chapter_index=chapter_idx,
                            context=context,
                        )
                    )

            if mentions:
                proposals.append(
                    PronunciationProposal(
                        strategy=self.name,
                        word=word,
                        flag_reason=PronunciationFlag.HOMOGRAPH,
                        mentions=mentions,
                        confidence=0.9,  # High confidence - these are known homographs
                        homograph_options=pronunciations,
                        reasoning=f"Homograph with {len(pronunciations)} pronunciations",
                    )
                )

        logger.info(f"Homograph proposer found {len(proposals)} homographs")
        return proposals
