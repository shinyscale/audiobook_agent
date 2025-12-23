"""
Homograph proposer.

Identifies known homographs - words spelled the same but with different pronunciations.
"""

import re
from typing import Optional
import logging

from .base import BasePronunciationProposer
from ..models import PronunciationProposal, PronunciationMention, PronunciationFlag

logger = logging.getLogger(__name__)

# Homographs: words spelled the same but with different pronunciations
HOMOGRAPHS = {
    'read': ['present tense (REED)', 'past tense (RED)'],
    'lead': ['to guide (LEED)', 'metal (LED)'],
    'live': ['to exist (LIV)', 'in real time (LYVE)'],
    'tear': ['to rip (TAIR)', 'from eye (TEER)'],
    'wind': ['air movement (WIND)', 'to turn (WYND)'],
    'bow': ['weapon/ribbon (BOH)', 'to bend (BOW)'],
    'row': ['line (ROH)', 'argument (ROW)'],
    'sow': ['plant seeds (SOH)', 'female pig (SOW)'],
    'does': ['female deer (DOHZ)', 'verb form (DUZ)'],
    'bass': ['fish (BASS)', 'low sound (BASE)'],
    'close': ['nearby (KLOHS)', 'to shut (KLOHZ)'],
    'content': ['satisfied (kun-TENT)', "what's inside (KON-tent)"],
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
    'wound': ['injury (WOOND)', 'past of wind (WOWND)'],
    'use': ['noun (YOOS)', 'verb (YOOZ)'],
    'abuse': ['noun (uh-BYOOS)', 'verb (uh-BYOOZ)'],
    'excuse': ['noun (ek-SKYOOS)', 'verb (ek-SKYOOZ)'],
    'house': ['noun (HOWS)', 'verb (HOWZ)'],
    'alternate': ['adj (AWL-ter-nit)', 'verb (AWL-ter-nayt)'],
    'deliberate': ['adj (di-LIB-er-it)', 'verb (di-LIB-er-ayt)'],
    'duplicate': ['noun/adj (DOO-pli-kit)', 'verb (DOO-pli-kayt)'],
    'elaborate': ['adj (i-LAB-er-it)', 'verb (i-LAB-er-ayt)'],
    'estimate': ['noun (ES-ti-mit)', 'verb (ES-ti-mayt)'],
    'moderate': ['adj (MOD-er-it)', 'verb (MOD-er-ayt)'],
    'intimate': ['adj (IN-ti-mit)', 'verb (IN-ti-mayt)'],
}


class HomographProposer(BasePronunciationProposer):
    """Proposes known homographs with multiple pronunciations."""

    name = "homograph"

    def propose(
        self,
        full_text: str,
        chapter_boundaries: list[tuple[int, int, int]],
        character_names: Optional[list[str]] = None,
    ) -> list[PronunciationProposal]:
        """Find known homographs in text."""
        proposals = []

        for word, pronunciations in HOMOGRAPHS.items():
            # Find all occurrences
            pattern = r'\b' + re.escape(word) + r'\b'
            mentions = []

            for match in re.finditer(pattern, full_text, re.IGNORECASE):
                position = match.start()
                chapter_idx = self._get_chapter_for_position(position, chapter_boundaries)
                context = self._extract_context(full_text, position, len(word))

                mentions.append(PronunciationMention(
                    word_form=match.group(0),
                    position=position,
                    chapter_index=chapter_idx,
                    context=context,
                ))

            if mentions:
                proposals.append(PronunciationProposal(
                    strategy=self.name,
                    word=word,
                    flag_reason=PronunciationFlag.HOMOGRAPH,
                    mentions=mentions,
                    confidence=0.9,  # High confidence - these are known homographs
                    homograph_options=pronunciations,
                    reasoning=f"Homograph with {len(pronunciations)} pronunciations",
                ))

        logger.info(f"Homograph proposer found {len(proposals)} homographs")
        return proposals
