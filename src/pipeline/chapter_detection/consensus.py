"""
Consensus builder for chapter detection.

Stage 4: Reconcile proposals from multiple strategies into a final chapter map.

Supports competitive multi-model consensus for boundary validation when enabled.
"""

import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from ..llm import LLMClient, LLMConfig
from .models import (
    Chapter,
    ChapterBoundary,
    ChapterMap,
    DocumentProfile,
    ValidationResult,
)

if TYPE_CHECKING:
    from ...agents.config import CompetitiveConfig

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


# Prompt for competitive boundary validation
BOUNDARY_VALIDATION_SYSTEM = """You are a document structure analyst determining whether a text position marks a chapter boundary.

Analyze the text around the proposed boundary and determine if it's a real chapter/section start."""

BOUNDARY_VALIDATION_PROMPT = """Is this a valid chapter/section boundary?

PROPOSED BOUNDARY:
- Title: {title}
- Position: {position}

TEXT BEFORE (last 200 chars):
{text_before}

TEXT AT BOUNDARY (500 chars):
{text_at}

A valid chapter boundary typically has:
1. A chapter heading (Chapter 1, I, ONE, Part I, etc.)
2. Clear visual separation from previous content
3. A new narrative section starting

Return JSON:
{{
  "is_valid_boundary": true/false,
  "confidence": 0.0-1.0,
  "boundary_type": "chapter" | "part" | "section" | "scene" | null,
  "reason": "brief explanation"
}}

Return ONLY valid JSON."""


@dataclass
class ProposalCluster:
    """A cluster of proposals that refer to the same boundary."""

    proposals: list[ValidationResult]
    center_position: int
    best_title: Optional[str]
    combined_score: float
    strategies: list[str]
    # F10: Hard boundaries dominate over soft signals
    is_hard_boundary: bool = False  # True if any proposal is a hard boundary


class ConsensusBuilder:
    """
    Builds consensus from validated proposals.

    Approach:
    1. Cluster proposals by position (within threshold)
    2. Score each cluster based on agreement and validation scores
    3. Select high-confidence boundaries
    4. Flag low-confidence for review
    5. Build final chapter map

    Supports competitive multi-model consensus for boundary validation when enabled.
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        position_threshold: int = 200,
        high_confidence_threshold: float = 0.7,
        low_confidence_threshold: float = 0.4,
        min_chapter_words: int = 300,
        competitive_config: Optional["CompetitiveConfig"] = None,
    ):
        """
        Args:
            llm_client: LLM client for sequence validation
            position_threshold: Max distance (chars) to consider proposals as same boundary
            high_confidence_threshold: Score above this = auto-accept
            low_confidence_threshold: Score below this = reject
            min_chapter_words: Minimum words per chapter
            competitive_config: Optional config for multi-model consensus
        """
        self.llm = llm_client
        self.position_threshold = position_threshold
        self.high_confidence_threshold = high_confidence_threshold
        self.low_confidence_threshold = low_confidence_threshold
        self.min_chapter_words = min_chapter_words
        self.competitive_config = competitive_config

        # Collect vote records for consensus logging
        self.vote_records: list[dict] = []

        # Initialize competitor clients if competitive structure is enabled
        self._competitor_clients: list[LLMClient] = []
        if self._use_competitive_structure():
            self._init_competitor_clients()

        # Strategy weights for scoring
        self.strategy_weights = {
            "regex": 1.0,
            "llm_marker": 0.9,
            "llm_narrative": 0.7,
            "toc_match": 1.2,  # TOC match is strong signal
        }

    def _use_competitive_structure(self) -> bool:
        """Check if competitive structure detection should be used."""
        return (
            self.competitive_config is not None
            and self.competitive_config.enabled
            and self.competitive_config.competitive_structure
            and self.llm is not None
        )

    def _init_competitor_clients(self) -> None:
        """Initialize LLM clients for competitive boundary voting."""
        if not self.llm or not self.competitive_config:
            return

        base_config = self.llm.config

        # Get competitor configurations
        competitor_configs = self.competitive_config.get_competitor_configs(
            base_model=base_config.model,
            base_provider=base_config.provider,
            base_url=base_config.base_url,
            base_api_key=base_config.api_key,
        )

        logger.info(
            f"ConsensusBuilder: Initializing competitive structure with {len(competitor_configs)} competitors"
        )

        for comp_config in competitor_configs:
            logger.info(f"  Competitor: {comp_config.model} @ {comp_config.temperature}")

            new_config = LLMConfig(
                provider=comp_config.provider,
                model=comp_config.model,
                base_url=comp_config.base_url or base_config.base_url,
                api_key=comp_config.get_api_key() or base_config.api_key,
                temperature=comp_config.temperature,
                max_tokens=base_config.max_tokens,
                context_length=base_config.context_length,
            )
            client = LLMClient(new_config)
            self._competitor_clients.append(client)

    def _warm_competitor_models(self) -> None:
        """Pre-load all competitor models into Ollama memory for true parallel execution.

        When running multiple LLM models in parallel, Ollama may need to load/unload
        models between requests if they aren't already in memory. This method sends
        a minimal prompt to each competitor model to force Ollama to load them all
        into memory before the actual analysis begins.

        Configure Ollama with:
        - OLLAMA_MAX_LOADED_MODELS=3 (or higher based on available memory)
        - OLLAMA_KEEP_ALIVE=30m (keep models loaded longer)
        """
        if not self._competitor_clients:
            return

        # Check if we have multiple different models (multi-model setup)
        unique_models = {client.config.model for client in self._competitor_clients}

        if len(unique_models) <= 1:
            # Single model with different temperatures - no pre-warming needed
            logger.debug("Single model competitive setup - skipping pre-warm")
            return

        logger.info(
            f"Pre-warming {len(unique_models)} competitor models for parallel execution: "
            f"{sorted(unique_models)}"
        )

        def warm_model(client: LLMClient) -> tuple[str, bool]:
            """Send minimal prompt to force model load."""
            model_name = client.config.model
            try:
                # Minimal prompt to force model load without heavy computation
                client.query("Hello", system="Respond with 'OK'")
                logger.info(f"  Warmed: {model_name}")
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

    def _competitive_boundary_validation(
        self,
        clusters: list["ProposalCluster"],
        text: str,
    ) -> list["ProposalCluster"]:
        """
        Use multiple LLMs to vote on whether each boundary is valid.

        Requires supermajority (2/3) agreement to keep a boundary.
        """
        if not self._competitor_clients:
            return clusters

        # Pre-warm competitor models for true parallel execution
        self._warm_competitor_models()

        logger.info(f"Running competitive boundary validation on {len(clusters)} boundaries")

        validated_clusters = []
        threshold = (
            self.competitive_config.structure_vote_threshold
            if self.competitive_config
            else 0.67
        )

        for cluster in clusters:
            # Hard boundaries (explicit markers) skip voting
            if cluster.is_hard_boundary:
                logger.debug(
                    f"Skipping vote for hard boundary at {cluster.center_position}: '{cluster.best_title}'"
                )
                validated_clusters.append(cluster)
                continue

            # Get context around the boundary
            pos = cluster.center_position
            text_before = text[max(0, pos - 200) : pos]
            text_at = text[pos : min(len(text), pos + 500)]

            # Vote on this boundary
            votes = self._vote_on_boundary(cluster.best_title, pos, text_before, text_at)

            vote_ratio = sum(votes) / len(votes) if votes else 0
            outcome = "accepted" if vote_ratio >= threshold else "rejected"

            # Record vote for consensus log
            from ..consensus_collector import consensus_collector
            consensus_collector.record_vote(
                vote_type="boundary",
                subject=f"Position {pos}: {cluster.best_title or '(no title)'}",
                context=f"text_at: {text_at[:50]}...",
                votes=votes,
                threshold=threshold,
                outcome=outcome,
            )

            if vote_ratio >= threshold:
                validated_clusters.append(cluster)
                logger.debug(
                    f"Boundary ACCEPTED at {pos}: '{cluster.best_title}' "
                    f"({sum(votes)}/{len(votes)} votes, {vote_ratio:.0%})"
                )
            else:
                logger.info(
                    f"Boundary REJECTED at {pos}: '{cluster.best_title}' "
                    f"({sum(votes)}/{len(votes)} votes, {vote_ratio:.0%} < {threshold:.0%})"
                )

        return validated_clusters

    def _vote_on_boundary(
        self,
        title: Optional[str],
        position: int,
        text_before: str,
        text_at: str,
    ) -> list[bool]:
        """
        Have multiple LLMs vote on whether a boundary is valid.

        Returns:
            List of boolean votes (True = valid boundary, False = invalid)
        """
        prompt = BOUNDARY_VALIDATION_PROMPT.format(
            title=title or "(no title)",
            position=position,
            text_before=text_before,
            text_at=text_at,
        )

        def query_competitor(client: LLMClient) -> bool:
            try:
                result, response = client.query_json(prompt, system=BOUNDARY_VALIDATION_SYSTEM)
                if not response.success or result is None or not isinstance(result, dict):
                    return False

                is_valid = bool(result.get("is_valid_boundary", False))
                confidence = float(result.get("confidence", 0.0) or 0.0)

                # Only count as YES if valid AND confidence >= 0.6
                return is_valid and confidence >= 0.6
            except Exception as e:
                logger.warning(f"Competitive boundary vote failed: {e}")
                return False

        # Execute all competitors in parallel
        votes = []
        with ThreadPoolExecutor(max_workers=len(self._competitor_clients)) as executor:
            futures = [executor.submit(query_competitor, client) for client in self._competitor_clients]
            for future in as_completed(futures):
                votes.append(future.result())

        return votes

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
        logger.info(f"ConsensusBuilder: received {len(validations)} validations")

        # 1. Filter to valid proposals
        valid_proposals = [v for v in validations if v.is_valid]
        invalid_count = len(validations) - len(valid_proposals)
        if invalid_count > 0:
            logger.info(f"ConsensusBuilder: filtered {invalid_count} invalid proposals")

        if not valid_proposals:
            logger.warning("No valid proposals - returning single chapter")
            return self._single_chapter_map(text, profile)

        logger.info(f"ConsensusBuilder: {len(valid_proposals)} valid proposals")
        for v in sorted(valid_proposals, key=lambda x: x.proposal.position):
            logger.debug(
                f"  [{v.proposal.position}] '{v.proposal.title}' "
                f"(strategy={v.proposal.strategy}, score={v.overall_score:.2f})"
            )

        # 2. Cluster by position
        clusters = self._cluster_proposals(valid_proposals)
        logger.info(f"ConsensusBuilder: formed {len(clusters)} clusters")
        for i, c in enumerate(sorted(clusters, key=lambda x: x.center_position)):
            logger.debug(
                f"  Cluster {i}: pos={c.center_position}, title='{c.best_title}', "
                f"score={c.combined_score:.2f}, strategies={c.strategies}"
            )

        # 3. Score clusters
        scored_clusters = self._score_clusters(clusters, profile)
        logger.debug("ConsensusBuilder: scored clusters")
        for c in sorted(scored_clusters, key=lambda x: x.center_position):
            logger.debug(
                f"  [{c.center_position}] '{c.best_title}' -> score={c.combined_score:.2f}"
            )

        # 3.5. Competitive boundary validation (if enabled)
        if self._use_competitive_structure():
            pre_competitive_count = len(scored_clusters)
            scored_clusters = self._competitive_boundary_validation(scored_clusters, text)
            if len(scored_clusters) != pre_competitive_count:
                logger.info(
                    f"ConsensusBuilder: Competitive validation removed "
                    f"{pre_competitive_count - len(scored_clusters)} clusters"
                )

        # 4. Validate chapter sequence with LLM (removes out-of-order chapters)
        if self.llm:
            pre_validation_count = len(scored_clusters)
            scored_clusters = self._validate_chapter_sequence(scored_clusters, profile)
            if len(scored_clusters) != pre_validation_count:
                logger.info(
                    f"ConsensusBuilder: LLM validation removed "
                    f"{pre_validation_count - len(scored_clusters)} clusters"
                )

        # 5. Select boundaries
        high_confidence, low_confidence, rejected = self._select_boundaries(scored_clusters)

        logger.info(
            f"ConsensusBuilder: selected {len(high_confidence)} high-confidence, "
            f"{len(low_confidence)} low-confidence, {len(rejected)} rejected"
        )
        for c in sorted(high_confidence, key=lambda x: x.center_position):
            logger.info(
                f"  HIGH: [{c.center_position}] '{c.best_title}' (score={c.combined_score:.2f})"
            )
        for c in sorted(low_confidence, key=lambda x: x.center_position):
            logger.debug(
                f"  LOW: [{c.center_position}] '{c.best_title}' (score={c.combined_score:.2f})"
            )
        for c in sorted(rejected, key=lambda x: x.center_position):
            logger.debug(
                f"  REJECTED: [{c.center_position}] '{c.best_title}' (score={c.combined_score:.2f})"
            )

        # 5.5. STRICT TOC enforcement (if TOC exists)
        if profile.table_of_contents and profile.table_of_contents.entries:
            expected_count = len(profile.table_of_contents.entries)
            pre_toc_count = len(high_confidence)
            logger.info(
                f"ConsensusBuilder: TOC specifies {expected_count} chapters - enforcing strict count"
            )
            logger.info(
                f"[DEBUG] Before TOC enforcement: {pre_toc_count} high-confidence, {len(low_confidence)} low-confidence"
            )
            logger.info(
                f"[DEBUG] High-confidence titles: {[c.best_title for c in high_confidence[:12]]}"
            )
            logger.info(
                f"[DEBUG] Low-confidence titles: {[c.best_title for c in low_confidence[:12]]}"
            )
            # Pass BOTH high and low confidence pools so TOC enforcement can rescue low-scoring chapters
            high_confidence = self._enforce_toc_count(
                high_confidence, low_confidence, expected_count
            )
            logger.info(
                f"[DEBUG] After TOC enforcement: {len(high_confidence)} chapters with titles: {[c.best_title for c in high_confidence[:12]]}"
            )
            if len(high_confidence) != pre_toc_count:
                logger.info(
                    f"ConsensusBuilder: TOC enforcement adjusted from {pre_toc_count} to {len(high_confidence)} boundaries"
                )

        # 6. Validate chapter sizes
        pre_size_count = len(high_confidence)
        high_confidence = self._validate_chapter_sizes(high_confidence, text, profile)
        if len(high_confidence) != pre_size_count:
            logger.info(
                f"ConsensusBuilder: size validation removed "
                f"{pre_size_count - len(high_confidence)} boundaries"
            )

        # 7. Build chapter map
        return self._build_chapter_map(high_confidence, low_confidence, text, profile)

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
            cluster_center = sum(v.proposal.position for v in current_cluster) // len(
                current_cluster
            )

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

        # F10: Check if any proposal is a hard boundary (explicit marker)
        is_hard = any(getattr(v.proposal, "is_hard_boundary", False) for v in validations)

        return ProposalCluster(
            proposals=validations,
            center_position=center,
            best_title=best_title,
            combined_score=combined_score,
            strategies=strategies,
            is_hard_boundary=is_hard,
        )

    def _score_clusters(
        self,
        clusters: list[ProposalCluster],
        profile: DocumentProfile,
    ) -> list[ProposalCluster]:
        """Enhance cluster scores with additional signals.

        F10: Hard boundaries (explicit markers like 'Chapter N', centered Roman numerals)
        receive maximum score to dominate over soft signals.
        """
        for cluster in clusters:
            # F10: Hard boundaries get maximum score
            if cluster.is_hard_boundary:
                cluster.combined_score = 1.0
                logger.debug(
                    f"Hard boundary at {cluster.center_position}: '{cluster.best_title}' "
                    f"- assigned maximum score"
                )
                continue  # Skip other scoring adjustments for hard boundaries

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
        profile: DocumentProfile,
    ) -> list[ProposalCluster]:
        """Remove boundaries that create too-small chapters or fragment existing structure."""
        if len(clusters) < 2:
            return clusters

        sorted_clusters = sorted(clusters, key=lambda c: c.center_position)

        # Phase 1: Calculate all chapter sizes
        chapter_sizes = []
        for i, cluster in enumerate(sorted_clusters):
            start = cluster.center_position
            end = (
                sorted_clusters[i + 1].center_position
                if i + 1 < len(sorted_clusters)
                else len(text)
            )
            chapter_text = text[start:end]
            word_count = len(chapter_text.split())
            chapter_sizes.append((cluster, word_count, i))

        # Phase 2: Determine size threshold (TOC-aware if available)
        if profile.table_of_contents and profile.table_of_contents.entries:
            # TOC-based threshold: use expected average chapter size
            expected_count = len(profile.table_of_contents.entries)
            len(text) - profile.front_matter_end
            total_words = len(text[profile.front_matter_end :].split())
            expected_avg_size = total_words / expected_count

            # Small chapter = less than 30% of expected average
            small_threshold = int(expected_avg_size * 0.3)
            logger.info(
                f"Size validation: TOC-based threshold = {small_threshold} words "
                f"(30% of expected avg {expected_avg_size:.0f} words)"
            )
        elif len(chapter_sizes) >= 3:
            # Fallback: median-based threshold
            word_counts = [size for _, size, _ in chapter_sizes]
            median_size = sorted(word_counts)[len(word_counts) // 2]

            # A chapter is suspiciously small if it's <40% of median AND <2000 words
            # This catches fragmentation without being too aggressive
            small_threshold = min(median_size * 0.4, 2000)
            logger.info(
                f"Size validation: median-based threshold = {small_threshold} words "
                f"(40% of median {median_size} words, capped at 2000)"
            )
        else:
            # Very few chapters - use absolute minimum
            small_threshold = self.min_chapter_words
            logger.info(f"Size validation: using absolute minimum = {small_threshold} words")

        # Phase 3: Remove small chapters with confidence weighting
        valid = []
        removed_count = 0

        if len(chapter_sizes) >= 2:

            for cluster, word_count, idx in chapter_sizes:
                # Check 0: Always preserve special sections (Foreword, Epilogue, Letters, etc.)
                # These are explicitly marked structural elements that narrators need
                is_special_section = any(
                    p.description in ["special_section", "letter_section"]
                    for p in cluster.proposals
                    if hasattr(p, "description")
                )

                if is_special_section:
                    logger.debug(
                        f"Preserving special section at {cluster.center_position}: "
                        f"{word_count} words (special sections always kept)"
                    )
                    valid.append(cluster)
                    continue

                # Check 1: Absolute minimum (300 words)
                if word_count < self.min_chapter_words:
                    logger.debug(
                        f"Removing boundary at {cluster.center_position}: "
                        f"{word_count} words < {self.min_chapter_words} minimum"
                    )
                    removed_count += 1
                    continue

                # Check 2: Relative to median (detect fragmentation)
                if word_count < small_threshold:
                    # Check if it's a high-confidence explicit marker
                    has_explicit_marker = any(
                        s in ["regex", "llm_marker", "toc_match"] for s in cluster.strategies
                    )

                    if has_explicit_marker and cluster.combined_score >= 0.85:
                        # High confidence explicit marker - probably legitimate (e.g., short epilogue)
                        valid.append(cluster)
                    elif cluster.combined_score < 0.75:
                        # Low-ish confidence and small - likely false positive
                        logger.info(
                            f"Removing small chapter boundary at {cluster.center_position}: "
                            f"{word_count} words (median: {median_size:.0f}), "
                            f"confidence: {cluster.combined_score:.2f}, "
                            f"strategies: {cluster.strategies}"
                        )
                        removed_count += 1
                        continue
                    else:
                        # Medium confidence - keep but warn
                        logger.warning(
                            f"Keeping small chapter at {cluster.center_position}: "
                            f"{word_count} words, confidence: {cluster.combined_score:.2f}"
                        )
                        valid.append(cluster)
                else:
                    # Normal size
                    valid.append(cluster)

            if removed_count > 0:
                logger.info(f"Size validation removed {removed_count} boundaries")

            return valid

        # Fallback for <3 chapters: use simple threshold check
        return [c for c, wc, _ in chapter_sizes if wc >= self.min_chapter_words]

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

            chapters.append(
                Chapter(
                    index=i + 1,
                    title=cleaned_title,
                    start_position=start,
                    end_position=end,
                    word_count=word_count,
                    confidence=cluster.combined_score,
                    toc_validated=toc_validated,
                )
            )

        # Handle case where first chapter doesn't start at front matter end
        # IMPORTANT: If the first chapter is AT or very close to front_matter_end,
        # it means the chapter marker itself was used to calculate front_matter_end
        # (e.g., centered Roman numeral "I"). Don't insert a synthetic chapter in this case.
        FRONT_MATTER_POSITION_TOLERANCE = 50  # chars

        logger.info(
            f"[DEBUG] Synthetic chapter check: chapters[0].start={chapters[0].start_position if chapters else 'N/A'}, "
            f"front_matter_end={profile.front_matter_end}, tolerance={FRONT_MATTER_POSITION_TOLERANCE}, "
            f"gap={chapters[0].start_position - profile.front_matter_end if chapters else 'N/A'}"
        )

        if (
            chapters
            and chapters[0].start_position
            > profile.front_matter_end + FRONT_MATTER_POSITION_TOLERANCE
        ):
            # There's significant text before first chapter marker
            pre_chapter_text = text[profile.front_matter_end : chapters[0].start_position]
            pre_word_count = len(pre_chapter_text.split())

            # Only insert synthetic chapter if there's substantial content
            # (not just whitespace or front matter remnants)
            if pre_word_count >= self.min_chapter_words:
                logger.info(
                    f"Inserting synthetic Chapter 0 from front_matter_end ({profile.front_matter_end}) "
                    f"to first detected boundary ({chapters[0].start_position}), {pre_word_count} words"
                )
                # Insert a chapter 0 or renumber
                chapters.insert(
                    0,
                    Chapter(
                        index=0,
                        title=None,
                        start_position=profile.front_matter_end,
                        end_position=chapters[0].start_position,
                        word_count=pre_word_count,
                        confidence=0.5,  # Lower confidence - inferred
                        toc_validated=False,
                    ),
                )
                # Renumber
                for i, ch in enumerate(chapters):
                    ch.index = i + 1
                total_words += pre_word_count
        elif chapters and chapters[0].start_position < profile.front_matter_end:
            # First chapter starts BEFORE front_matter_end - this means the chapter marker
            # was detected before the profiler's content start position. Adjust the start
            # to use the detected boundary instead.
            logger.info(
                f"First chapter at {chapters[0].start_position} is before front_matter_end "
                f"({profile.front_matter_end}). Using detected boundary position."
            )
            # No adjustment needed - trust the detected boundary

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
            logger.warning(
                "No high-confidence chapter boundaries found - treating as single chapter"
            )
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
        profile: Optional[DocumentProfile] = None,
    ) -> list[ProposalCluster]:
        """
        Use LLM to validate the chapter sequence and remove out-of-order chapters.

        This catches issues like "Chapter 1" appearing after "Chapter 9".
        For simple sequential patterns (I, II, III or 1, 2, 3), skips LLM validation.

        IMPORTANT: Never removes chapters that match TOC entries - TOC is authoritative.
        """
        if not clusters or len(clusters) < 3:
            return clusters

        # Sort by position
        sorted_clusters = sorted(clusters, key=lambda c: c.center_position)

        # Check if sequence is already valid (simple pattern)
        # Skip LLM for sequential Roman numerals (I, II, III...) or Arabic (1, 2, 3...)
        if self._is_simple_sequence(sorted_clusters):
            logger.debug("Skipping LLM validation - simple sequential pattern detected")
            return clusters

        # Build set of TOC titles for protection (normalized)
        toc_protected_titles = set()
        if profile and profile.table_of_contents:
            for entry in profile.table_of_contents.entries:
                # Normalize TOC titles for matching
                title = entry.title.strip().upper()
                toc_protected_titles.add(title)
                # Also add "Chapter X" variants
                toc_protected_titles.add(f"CHAPTER {title}")
                toc_protected_titles.add(f"PART {title}")
            logger.debug(f"TOC-protected titles: {toc_protected_titles}")

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
                logger.warning(
                    "LLM sequence validation failed to return JSON, keeping all chapters"
                )
                return clusters

            invalid_indices = result.get("invalid_indices", [])

            if invalid_indices:
                analysis = result.get("analysis", "")
                reasoning = result.get("reasoning", {})
                logger.info(f"LLM sequence validation: {analysis}")

                # Filter invalid_indices to exclude TOC-protected chapters
                actually_invalid = []
                for idx in invalid_indices:
                    if 0 <= idx < len(sorted_clusters):
                        title = sorted_clusters[idx].best_title or ""
                        normalized_title = title.strip().upper()

                        # Check if this title matches any TOC entry
                        is_toc_protected = (
                            normalized_title in toc_protected_titles
                            or
                            # Also check if title contains a TOC numeral
                            any(
                                toc_title in normalized_title or normalized_title in toc_title
                                for toc_title in toc_protected_titles
                            )
                        )

                        if is_toc_protected:
                            reason = reasoning.get(str(idx), "no reason given")
                            logger.info(
                                f"PROTECTING TOC-matched chapter at index {idx}: '{title}' "
                                f"(LLM wanted to remove: {reason})"
                            )
                        else:
                            reason = reasoning.get(str(idx), "no reason given")
                            logger.info(
                                f"Removing invalid chapter at index {idx}: '{title}' - {reason}"
                            )
                            actually_invalid.append(idx)

                # Filter out actually invalid clusters (excluding TOC-protected)
                valid_clusters = [
                    c for i, c in enumerate(sorted_clusters) if i not in actually_invalid
                ]
                return valid_clusters

        except Exception as e:
            logger.warning(f"LLM sequence validation error: {e}")

        return clusters

    def _is_simple_sequence(self, clusters: list[ProposalCluster]) -> bool:
        """
        Check if chapters form a simple sequential pattern.

        Returns True for:
        - Sequential Roman numerals: I, II, III, IV, V...
        - Sequential Arabic numerals: 1, 2, 3, 4, 5...
        - Chapter N format in order: Chapter 1, Chapter 2...

        These don't need LLM validation - the pattern is self-validating.
        """
        if len(clusters) < 2:
            return True

        # Roman numeral values for conversion
        roman_values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}

        def roman_to_int(s: str) -> int:
            """Convert Roman numeral to integer."""
            s = s.upper()
            result = 0
            prev = 0
            for c in reversed(s):
                curr = roman_values.get(c, 0)
                if curr < prev:
                    result -= curr
                else:
                    result += curr
                prev = curr
            return result

        def extract_number(title: str) -> Optional[int]:
            """Extract chapter number from title."""
            if not title:
                return None

            # Try "Chapter N" format
            match = re.match(r"^Chapter\s+(\d+)", title, re.IGNORECASE)
            if match:
                return int(match.group(1))

            # Try "Chapter ROMAN" format
            match = re.match(r"^Chapter\s+([IVXLC]+)$", title, re.IGNORECASE)
            if match:
                return roman_to_int(match.group(1))

            # Try pure Roman numeral (e.g., just "III")
            if re.match(r"^[IVXLC]+$", title):
                return roman_to_int(title)

            # Try pure Arabic numeral
            if title.isdigit():
                return int(title)

            return None

        # Extract numbers from all titles
        numbers = []
        for cluster in clusters:
            num = extract_number(cluster.best_title)
            if num is None:
                # Can't determine pattern - need LLM
                return False
            numbers.append(num)

        # Check if strictly increasing (allows gaps)
        for i in range(1, len(numbers)):
            if numbers[i] <= numbers[i - 1]:
                # Out of order - need LLM to decide
                return False

        # Check for reasonable sequence (no huge gaps)
        # e.g., 1, 2, 15, 16 is suspicious
        max_gap = 5  # Allow gaps up to 5 for books with Part divisions
        for i in range(1, len(numbers)):
            if numbers[i] - numbers[i - 1] > max_gap:
                # Large gap - need LLM to validate
                return False

        logger.debug(f"Detected simple sequence: {numbers}")
        return True

    def _enforce_toc_count(
        self,
        high_confidence: list[ProposalCluster],
        low_confidence: list[ProposalCluster],
        expected_count: int,
    ) -> list[ProposalCluster]:
        """
        STRICTLY enforce TOC count by selecting top N clusters.

        User requirement: If TOC says 9, result must be exactly 9.
        No tolerance - this is a hard constraint.

        Args:
            high_confidence: High-scoring clusters
            low_confidence: Lower-scoring clusters (may be rescued if TOC requires them)
            expected_count: Number of chapters expected from TOC
        """
        # Combine all available clusters
        all_clusters = high_confidence + low_confidence

        if len(all_clusters) < expected_count:
            logger.warning(
                f"TOC enforcement: Only {len(all_clusters)} total boundaries found but TOC expects {expected_count}. "
                f"This may indicate missed chapter markers. Returning all {len(all_clusters)} clusters."
            )
            return all_clusters  # Can't create chapters that don't exist

        # Select top N boundaries by position and confidence
        if len(all_clusters) > expected_count:
            logger.info(
                f"TOC enforcement: {len(all_clusters)} boundaries found ({len(high_confidence)} high, {len(low_confidence)} low) but TOC expects {expected_count}. "
                f"Selecting top {expected_count} by confidence and TOC match."
            )
        else:
            logger.info(
                f"TOC enforcement: {len(all_clusters)} boundaries found ({len(high_confidence)} high, {len(low_confidence)} low), TOC expects {expected_count}. "
                f"Using position-based selection to ensure correct chapter sequence."
            )

        # Sort by combined score (descending)
        sorted(all_clusters, key=lambda c: c.combined_score, reverse=True)

        # Prioritize in this order:
        # 1. TOC-validated boundaries (TOC match score > 0.8)
        # 2. Hard boundaries (explicit markers like "Chapter N", centered Roman numerals)
        # 3. Remaining boundaries by score
        toc_validated = [
            c for c in all_clusters if any(v.toc_match_score > 0.8 for v in c.proposals)
        ]
        hard_boundaries = [c for c in all_clusters if c.is_hard_boundary and c not in toc_validated]
        soft_boundaries = [
            c for c in all_clusters if c not in toc_validated and c not in hard_boundaries
        ]

        logger.debug(
            f"TOC enforcement: {len(toc_validated)} TOC-validated, "
            f"{len(hard_boundaries)} hard boundaries, "
            f"{len(soft_boundaries)} soft boundaries"
        )

        # FIXED: If we have enough TOC-validated or hard boundaries to meet the expected count,
        # prefer them by POSITION (sequential order) rather than by score.
        # This prevents dropping Chapter V just because it has a slightly lower score.
        primary_boundaries = toc_validated + hard_boundaries
        if len(primary_boundaries) >= expected_count:
            # We have enough high-confidence boundaries - select by position, not score
            primary_by_position = sorted(primary_boundaries, key=lambda c: c.center_position)
            selected = primary_by_position[:expected_count]
            logger.info(
                f"TOC enforcement: selected {expected_count} boundaries by position "
                f"({len([c for c in selected if c in toc_validated])} TOC-validated, "
                f"{len([c for c in selected if c in hard_boundaries])} hard)"
            )
        else:
            # Not enough high-confidence boundaries - fall back to score-based selection
            selected = toc_validated[:expected_count]
            remaining_slots = expected_count - len(selected)
            if remaining_slots > 0:
                # Sort hard boundaries by score for selection
                hard_by_score = sorted(
                    hard_boundaries, key=lambda c: c.combined_score, reverse=True
                )
                selected.extend(hard_by_score[:remaining_slots])
                remaining_slots = expected_count - len(selected)
            if remaining_slots > 0:
                # Sort soft boundaries by score for selection
                soft_by_score = sorted(
                    soft_boundaries, key=lambda c: c.combined_score, reverse=True
                )
                selected.extend(soft_by_score[:remaining_slots])

        logger.debug(
            f"TOC enforcement: selected {len([c for c in selected if c in toc_validated])} TOC-validated + "
            f"{len([c for c in selected if c in hard_boundaries])} hard boundaries + "
            f"{len([c for c in selected if c in soft_boundaries])} soft boundaries"
        )

        # Re-sort by position for output
        selected_sorted = sorted(selected, key=lambda c: c.center_position)

        # Log what we kept vs dropped
        dropped = [c for c in all_clusters if c not in selected]
        rescued = [c for c in selected if c in low_confidence]
        if rescued:
            logger.info(f"TOC enforcement: RESCUED {len(rescued)} low-confidence boundaries:")
            for c in sorted(rescued, key=lambda x: x.center_position):
                logger.info(
                    f"  RESCUED: [{c.center_position}] '{c.best_title}' "
                    f"(score={c.combined_score:.2f})"
                )
        if dropped:
            logger.info(f"TOC enforcement: dropped {len(dropped)} boundaries:")
            for c in sorted(dropped, key=lambda x: x.center_position):
                logger.info(
                    f"  DROPPED: [{c.center_position}] '{c.best_title}' "
                    f"(score={c.combined_score:.2f})"
                )

        return selected_sorted

    def _clean_title(self, title: Optional[str]) -> Optional[str]:
        """
        Clean chapter title by removing redundant 'Chapter X:' prefixes.

        The detected title might already include "Chapter 12: Cooking with Explosives"
        but we assign our own index, so we'd get "Chapter 13: Chapter 12: Cooking with Explosives".
        This extracts just the subtitle part.

        Special case: Preserve standalone Roman numerals (I, II, III, etc.) as they are
        meaningful chapter identifiers in classic literature.
        """
        if not title:
            return None

        # Check if title is "Chapter" followed by standalone Roman numeral
        # Extract just the Roman numeral part
        match = re.match(r"^(?:Chapter|CHAPTER)\s+([IVXLC]+)\s*$", title, re.IGNORECASE)
        if match:
            # Preserve standalone Roman numerals
            return match.group(1)

        # If title starts with "Chapter N:" or similar, extract just the subtitle
        # Handles: "Chapter 12: Title", "Chapter XII - Title", "CHAPTER 5: Title"
        match = re.match(
            r"^(?:Chapter|CHAPTER)\s+(?:\d+|[IVXLC]+|One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten)\s*[:\-—–]\s*(.+)$",
            title,
            re.IGNORECASE,
        )
        if match:
            return match.group(1).strip()

        # If title is JUST "Chapter N" (Arabic numeral or word) with no subtitle, return None (we'll use our index)
        if re.match(
            r"^(?:Chapter|CHAPTER)\s+(?:\d+|One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten)\s*$",
            title,
            re.IGNORECASE,
        ):
            return None

        # Preserve any other title as-is (including standalone Roman numerals)
        if re.match(r"^[IVXLC]+$", title.strip()):
            return title.strip()

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
