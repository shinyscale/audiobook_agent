"""
Consensus builder for chapter detection.

Stage 4: Reconcile proposals from multiple strategies into a final chapter map.
"""

from dataclasses import dataclass
from typing import Optional
import re
import logging

from .models import (
    ChapterProposal,
    ValidationResult,
    ChapterBoundary,
    Chapter,
    ChapterMap,
    DocumentProfile,
)
from ..llm import LLMClient

logger = logging.getLogger(__name__)


SEQUENCE_VALIDATION_SYSTEM = """You are a document structure analyst validating chapter sequences.

Your task is to identify chapters that don't belong in the sequence - usually because they are:
1. References to chapters in the text (not actual chapter headings)
2. Out-of-order numbering that breaks the logical sequence
3. Back matter (glossary, bibliography) that mentions chapter numbers

A valid chapter sequence typically:
- Starts with Chapter 1 (or Prologue) and increments logically
- May restart numbering if there are Book/Part divisions
- Has consistent spacing and formatting"""


SEQUENCE_VALIDATION_PROMPT = """Validate this proposed chapter sequence for a book.

Proposed chapter markers in order:
{chapter_list}

Analyze the sequence and identify any chapters that should be REMOVED because:
1. They break the logical numbering (e.g., "Chapter 1" appearing after "Chapter 9" without a Part/Book division)
2. They appear to be textual references, not structural markers
3. They appear to be back matter (glossary, appendix, bibliography) disguised as chapters

Return JSON with:
{{
  "analysis": "Brief explanation of the sequence pattern you see",
  "invalid_indices": [list of 0-based indices that should be removed],
  "reasoning": {{"<index>": "why this should be removed"}}
}}

IMPORTANT: Books with "Part 1, Part 2" divisions may legitimately restart chapter numbering.
Only mark chapters as invalid if they clearly don't fit the pattern.

Return ONLY valid JSON."""


@dataclass
class ProposalCluster:
    """A cluster of proposals that refer to the same boundary."""
    proposals: list[ValidationResult]
    center_position: int
    best_title: Optional[str]
    combined_score: float
    strategies: list[str]


class ConsensusBuilder:
    """
    Builds consensus from validated proposals.

    Approach:
    1. Cluster proposals by position (within threshold)
    2. Score each cluster based on agreement and validation scores
    3. Select high-confidence boundaries
    4. Flag low-confidence for review
    5. Build final chapter map
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        position_threshold: int = 200,
        high_confidence_threshold: float = 0.7,
        low_confidence_threshold: float = 0.4,
        min_chapter_words: int = 300,
    ):
        """
        Args:
            llm_client: LLM client for sequence validation
            position_threshold: Max distance (chars) to consider proposals as same boundary
            high_confidence_threshold: Score above this = auto-accept
            low_confidence_threshold: Score below this = reject
            min_chapter_words: Minimum words per chapter
        """
        self.llm = llm_client
        self.position_threshold = position_threshold
        self.high_confidence_threshold = high_confidence_threshold
        self.low_confidence_threshold = low_confidence_threshold
        self.min_chapter_words = min_chapter_words

        # Strategy weights for scoring
        self.strategy_weights = {
            "regex": 1.0,
            "llm_marker": 0.9,
            "llm_narrative": 0.7,
            "toc_match": 1.2,  # TOC match is strong signal
        }

    def build_consensus(
        self,
        validations: list[ValidationResult],
        text: str,
        profile: DocumentProfile,
    ) -> ChapterMap:
        """
        Build consensus chapter map from validated proposals.

        Args:
            validations: Validated proposals
            text: Full document text
            profile: Document profile

        Returns:
            Final ChapterMap
        """
        # 1. Filter to valid proposals
        valid_proposals = [v for v in validations if v.is_valid]

        if not valid_proposals:
            logger.warning("No valid proposals - returning single chapter")
            return self._single_chapter_map(text, profile)

        # 2. Cluster by position
        clusters = self._cluster_proposals(valid_proposals)

        # 3. Score clusters
        scored_clusters = self._score_clusters(clusters, profile)

        # 4. Validate chapter sequence with LLM (removes out-of-order chapters)
        if self.llm:
            scored_clusters = self._validate_chapter_sequence(scored_clusters)

        # 5. Select boundaries
        high_confidence, low_confidence, rejected = self._select_boundaries(scored_clusters)

        # 6. Validate chapter sizes
        high_confidence = self._validate_chapter_sizes(high_confidence, text)

        # 7. Build chapter map
        return self._build_chapter_map(
            high_confidence, low_confidence, text, profile
        )

    def _cluster_proposals(
        self,
        validations: list[ValidationResult],
    ) -> list[ProposalCluster]:
        """Cluster proposals by position."""
        if not validations:
            return []

        # Sort by position
        sorted_vals = sorted(validations, key=lambda v: v.proposal.position)

        clusters = []
        current_cluster = [sorted_vals[0]]

        for val in sorted_vals[1:]:
            # Check if close to current cluster
            cluster_center = sum(v.proposal.position for v in current_cluster) // len(current_cluster)

            if val.proposal.position - cluster_center <= self.position_threshold:
                current_cluster.append(val)
            else:
                # Start new cluster
                clusters.append(self._make_cluster(current_cluster))
                current_cluster = [val]

        # Don't forget last cluster
        clusters.append(self._make_cluster(current_cluster))

        return clusters

    def _make_cluster(self, validations: list[ValidationResult]) -> ProposalCluster:
        """Create a cluster from a list of validations."""
        positions = [v.proposal.position for v in validations]
        center = sum(positions) // len(positions)

        # Pick best title (highest confidence proposal with a title)
        best_title = None
        best_title_score = 0
        for v in validations:
            if v.proposal.title and v.overall_score > best_title_score:
                best_title = v.proposal.title
                best_title_score = v.overall_score

        # Strategies that contributed
        strategies = list(set(v.proposal.strategy for v in validations))

        # Combined score (average weighted by strategy)
        total_weight = 0
        weighted_score = 0
        for v in validations:
            weight = self.strategy_weights.get(v.proposal.strategy, 0.8)
            weighted_score += v.overall_score * weight
            total_weight += weight

        combined_score = weighted_score / total_weight if total_weight > 0 else 0

        return ProposalCluster(
            proposals=validations,
            center_position=center,
            best_title=best_title,
            combined_score=combined_score,
            strategies=strategies,
        )

    def _score_clusters(
        self,
        clusters: list[ProposalCluster],
        profile: DocumentProfile,
    ) -> list[ProposalCluster]:
        """Enhance cluster scores with additional signals."""
        for cluster in clusters:
            # Bonus for multiple agreeing strategies
            agreement_bonus = min(0.2, (len(cluster.strategies) - 1) * 0.1)
            cluster.combined_score = min(1.0, cluster.combined_score + agreement_bonus)

            # Bonus for TOC match
            for val in cluster.proposals:
                if val.toc_match_score > 0.8:
                    cluster.combined_score = min(1.0, cluster.combined_score + 0.15)
                    break

            # Bonus for explicit chapter titles
            if cluster.best_title and any(
                kw in cluster.best_title.lower()
                for kw in ["chapter", "part", "book", "prologue", "epilogue"]
            ):
                cluster.combined_score = min(1.0, cluster.combined_score + 0.1)

        return clusters

    def _select_boundaries(
        self,
        clusters: list[ProposalCluster],
    ) -> tuple[list[ProposalCluster], list[ProposalCluster], list[ProposalCluster]]:
        """Categorize clusters by confidence."""
        high_confidence = []
        low_confidence = []
        rejected = []

        for cluster in clusters:
            if cluster.combined_score >= self.high_confidence_threshold:
                high_confidence.append(cluster)
            elif cluster.combined_score >= self.low_confidence_threshold:
                low_confidence.append(cluster)
            else:
                rejected.append(cluster)

        logger.info(
            f"Boundary selection: {len(high_confidence)} high, "
            f"{len(low_confidence)} low, {len(rejected)} rejected"
        )

        return high_confidence, low_confidence, rejected

    def _validate_chapter_sizes(
        self,
        clusters: list[ProposalCluster],
        text: str,
    ) -> list[ProposalCluster]:
        """Remove boundaries that would create too-small chapters."""
        if len(clusters) < 2:
            return clusters

        # Sort by position
        sorted_clusters = sorted(clusters, key=lambda c: c.center_position)

        valid = []
        for i, cluster in enumerate(sorted_clusters):
            # Calculate chapter size this would create
            start = cluster.center_position
            if i + 1 < len(sorted_clusters):
                end = sorted_clusters[i + 1].center_position
            else:
                end = len(text)

            chapter_text = text[start:end]
            word_count = len(chapter_text.split())

            if word_count >= self.min_chapter_words:
                valid.append(cluster)
            else:
                logger.debug(
                    f"Removing boundary at {cluster.center_position}: "
                    f"would create {word_count} word chapter"
                )

        return valid

    def _build_chapter_map(
        self,
        high_confidence: list[ProposalCluster],
        low_confidence: list[ProposalCluster],
        text: str,
        profile: DocumentProfile,
    ) -> ChapterMap:
        """Build final chapter map from selected clusters."""
        # Sort boundaries by position
        boundaries = sorted(high_confidence, key=lambda c: c.center_position)

        # Create chapters
        chapters = []
        total_words = 0

        for i, cluster in enumerate(boundaries):
            start = cluster.center_position

            # End is start of next chapter or end of text
            if i + 1 < len(boundaries):
                end = boundaries[i + 1].center_position
            else:
                end = len(text)

            # Count words
            chapter_text = text[start:end]
            word_count = len(chapter_text.split())
            total_words += word_count

            # Check TOC validation
            toc_validated = any(v.toc_match_score > 0.8 for v in cluster.proposals)

            # Clean the title to remove redundant "Chapter X:" prefixes
            cleaned_title = self._clean_title(cluster.best_title)

            chapters.append(Chapter(
                index=i + 1,
                title=cleaned_title,
                start_position=start,
                end_position=end,
                word_count=word_count,
                confidence=cluster.combined_score,
                toc_validated=toc_validated,
            ))

        # Handle case where first chapter doesn't start at front matter end
        if chapters and chapters[0].start_position > profile.front_matter_end + 100:
            # There's significant text before first chapter marker
            pre_chapter_text = text[profile.front_matter_end:chapters[0].start_position]
            pre_word_count = len(pre_chapter_text.split())

            if pre_word_count >= self.min_chapter_words:
                # Insert a chapter 0 or renumber
                chapters.insert(0, Chapter(
                    index=0,
                    title=None,
                    start_position=profile.front_matter_end,
                    end_position=chapters[0].start_position,
                    word_count=pre_word_count,
                    confidence=0.5,  # Lower confidence - inferred
                    toc_validated=False,
                ))
                # Renumber
                for i, ch in enumerate(chapters):
                    ch.index = i + 1
                total_words += pre_word_count

        # Create low-confidence boundary list
        low_conf_boundaries = [
            ChapterBoundary(
                position=c.center_position,
                title=c.best_title,
                confidence=c.combined_score,
                supporting_strategies=c.strategies,
                validation_score=c.combined_score,
                evidence=c.proposals[0].proposal.evidence if c.proposals else "",
                toc_validated=any(v.toc_match_score > 0.8 for v in c.proposals),
            )
            for c in low_confidence
        ]

        # Calculate TOC agreement
        toc_agreement = self._calculate_toc_agreement(chapters, profile)

        # Fallback: if no chapters were created (no high-confidence boundaries),
        # return a single-chapter map. This handles short stories and documents
        # without explicit chapter structure.
        if not chapters:
            logger.warning("No high-confidence chapter boundaries found - treating as single chapter")
            return self._single_chapter_map(text, profile)

        return ChapterMap(
            chapters=chapters,
            low_confidence_boundaries=low_conf_boundaries,
            document_profile=profile,
            total_word_count=total_words,
            toc_agreement_score=toc_agreement,
            pipeline_metadata={
                "high_confidence_count": len(high_confidence),
                "low_confidence_count": len(low_confidence),
            },
        )

    def _calculate_toc_agreement(
        self,
        chapters: list[Chapter],
        profile: DocumentProfile,
    ) -> float:
        """Calculate how well our chapters match the TOC."""
        if not profile.table_of_contents:
            return -1.0  # No TOC to compare

        toc_entries = profile.table_of_contents.entries

        if not toc_entries or not chapters:
            return 0.0

        # Count matches
        matches = sum(1 for ch in chapters if ch.toc_validated)

        # Agreement score
        max_possible = max(len(toc_entries), len(chapters))
        return matches / max_possible if max_possible > 0 else 0.0

    def _validate_chapter_sequence(
        self,
        clusters: list[ProposalCluster],
    ) -> list[ProposalCluster]:
        """
        Use LLM to validate the chapter sequence and remove out-of-order chapters.

        This catches issues like "Chapter 1" appearing after "Chapter 9".
        """
        if not clusters or len(clusters) < 3:
            return clusters

        # Sort by position
        sorted_clusters = sorted(clusters, key=lambda c: c.center_position)

        # Build chapter list for LLM
        chapter_list = []
        for i, cluster in enumerate(sorted_clusters):
            title = cluster.best_title or "(no title)"
            conf = "high" if cluster.combined_score >= self.high_confidence_threshold else "medium"
            chapter_list.append(f"{i}. {title} (confidence: {conf})")

        chapter_list_str = "\n".join(chapter_list)

        prompt = SEQUENCE_VALIDATION_PROMPT.format(chapter_list=chapter_list_str)

        try:
            result, response = self.llm.query_json(prompt, system=SEQUENCE_VALIDATION_SYSTEM)

            if result is None:
                logger.warning("LLM sequence validation failed to return JSON, keeping all chapters")
                return clusters

            invalid_indices = result.get("invalid_indices", [])

            if invalid_indices:
                analysis = result.get("analysis", "")
                reasoning = result.get("reasoning", {})
                logger.info(f"LLM sequence validation: {analysis}")

                for idx in invalid_indices:
                    reason = reasoning.get(str(idx), "no reason given")
                    if 0 <= idx < len(sorted_clusters):
                        title = sorted_clusters[idx].best_title
                        logger.info(f"Removing invalid chapter at index {idx}: '{title}' - {reason}")

                # Filter out invalid clusters
                valid_clusters = [
                    c for i, c in enumerate(sorted_clusters)
                    if i not in invalid_indices
                ]
                return valid_clusters

        except Exception as e:
            logger.warning(f"LLM sequence validation error: {e}")

        return clusters

    def _clean_title(self, title: Optional[str]) -> Optional[str]:
        """
        Clean chapter title by removing redundant 'Chapter X:' prefixes.

        The detected title might already include "Chapter 12: Cooking with Explosives"
        but we assign our own index, so we'd get "Chapter 13: Chapter 12: Cooking with Explosives".
        This extracts just the subtitle part.
        """
        if not title:
            return None

        # If title starts with "Chapter N:" or similar, extract just the subtitle
        # Handles: "Chapter 12: Title", "Chapter XII - Title", "CHAPTER 5: Title"
        match = re.match(
            r'^(?:Chapter|CHAPTER)\s+(?:\d+|[IVXLC]+|One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten)\s*[:\-—–]\s*(.+)$',
            title,
            re.IGNORECASE
        )
        if match:
            return match.group(1).strip()

        # If title is JUST "Chapter N" with no subtitle, return None (we'll use our index)
        if re.match(r'^(?:Chapter|CHAPTER)\s+(?:\d+|[IVXLC]+|One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten)\s*$', title, re.IGNORECASE):
            return None

        return title

    def _single_chapter_map(self, text: str, profile: DocumentProfile) -> ChapterMap:
        """Create a single-chapter map when no boundaries are found."""
        content_start = profile.front_matter_end
        word_count = len(text[content_start:].split())

        return ChapterMap(
            chapters=[
                Chapter(
                    index=1,
                    title=None,
                    start_position=content_start,
                    end_position=len(text),
                    word_count=word_count,
                    confidence=0.5,
                    toc_validated=False,
                )
            ],
            low_confidence_boundaries=[],
            document_profile=profile,
            total_word_count=word_count,
            toc_agreement_score=-1.0,
            pipeline_metadata={"note": "No chapter boundaries detected"},
        )
