"""
Validation agent for chapter proposals.

Stage 3: Validate each proposal independently to build confidence.
"""

import re
from typing import Optional
import logging
from difflib import SequenceMatcher

from .models import ChapterProposal, ValidationResult, DocumentProfile, TOCEntry
from ..llm import LLMClient

logger = logging.getLogger(__name__)


VALIDATION_SYSTEM_PROMPT = """You are validating whether a proposed location is actually a chapter boundary.

CRITICAL: Base your analysis ONLY on the text provided below.
Do NOT use any prior knowledge about this book, author, or its structure.
If you recognize this as a famous work, IGNORE what you know about it.
Analyze only what is explicitly written in the provided text.

You will see:
1. Text ENDING before the proposed boundary
2. Text BEGINNING after the proposed boundary
3. The proposed chapter title (if any)

Evaluate:
- Does the ending text feel like a natural chapter ending? (conclusion, resolution, cliffhanger)
- Does the beginning text feel like a natural chapter beginning? (new scene, time jump, fresh start)
- If there's a title, is it actually a chapter marker (not just appearing in prose)?"""

VALIDATION_PROMPT_TEMPLATE = """Validate this proposed chapter boundary.

TEXT BEFORE BOUNDARY (last ~500 characters):
---
{text_before}
---

TEXT AFTER BOUNDARY (first ~500 characters):
---
{text_after}
---

PROPOSED TITLE: {title}

Rate each on a scale of 0-10:
1. ending_score: How much does the text before feel like a chapter ending?
2. beginning_score: How much does the text after feel like a chapter beginning?
3. title_validity: Is the proposed title actually a chapter marker (not in prose)? (0 if no title)

Return JSON:
```json
{{
  "ending_score": 7,
  "beginning_score": 8,
  "title_validity": 9,
  "reasoning": "Brief explanation of your evaluation"
}}
```"""


class ProposalValidator:
    """
    Validates chapter proposals to build confidence.

    Validation includes:
    - LLM assessment of boundary quality
    - TOC matching (if TOC is available)
    - Structural heuristics
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        context_chars: int = 500,
    ):
        self.llm = llm_client
        self.context_chars = context_chars

    def validate(
        self,
        proposals: list[ChapterProposal],
        text: str,
        profile: DocumentProfile,
    ) -> list[ValidationResult]:
        """
        Validate all proposals against the text and profile.

        Args:
            proposals: List of proposals to validate
            text: Full document text
            profile: Document profile (includes TOC if available)

        Returns:
            List of validation results
        """
        logger.info(f"ProposalValidator: validating {len(proposals)} proposals")

        results = []
        valid_count = 0
        invalid_count = 0

        for proposal in proposals:
            result = self._validate_single(proposal, text, profile)
            results.append(result)

            if result.is_valid:
                valid_count += 1
                logger.debug(
                    f"  VALID: [{proposal.position}] '{proposal.title}' "
                    f"(score={result.overall_score:.2f})"
                )
            else:
                invalid_count += 1
                logger.debug(
                    f"  INVALID: [{proposal.position}] '{proposal.title}' "
                    f"(score={result.overall_score:.2f}) - {result.reasoning[:50]}"
                )

        logger.info(
            f"ProposalValidator: {valid_count} valid, {invalid_count} invalid "
            f"(threshold=0.5)"
        )

        return results

    def _validate_single(
        self,
        proposal: ChapterProposal,
        text: str,
        profile: DocumentProfile,
    ) -> ValidationResult:
        """Validate a single proposal."""
        # Extract context around the boundary
        text_before = self._get_text_before(text, proposal.position)
        text_after = self._get_text_after(text, proposal.position)

        # 1. LLM validation (if available)
        if self.llm:
            llm_scores = self._llm_validate(text_before, text_after, proposal.title)
        else:
            llm_scores = self._heuristic_validate(text_before, text_after, proposal.title)

        # 2. TOC matching
        toc_score = self._check_toc_match(proposal, profile)

        # 3. Calculate overall score
        overall_score = self._calculate_overall_score(
            llm_scores, toc_score, proposal.confidence
        )

        # Determine if valid (threshold = 0.5)
        is_valid = overall_score >= 0.5

        # Build reasoning
        reasoning_parts = [llm_scores.get("reasoning", "")]
        if toc_score > 0:
            reasoning_parts.append(f"TOC match score: {toc_score:.2f}")

        return ValidationResult(
            proposal=proposal,
            ending_score=llm_scores.get("ending_score", 0) / 10,
            beginning_score=llm_scores.get("beginning_score", 0) / 10,
            title_validity=llm_scores.get("title_validity", 0) / 10,
            toc_match_score=toc_score,
            overall_score=overall_score,
            is_valid=is_valid,
            reasoning=" | ".join(reasoning_parts),
        )

    def _get_text_before(self, text: str, position: int) -> str:
        """Get text before the boundary position."""
        start = max(0, position - self.context_chars)
        return text[start:position].strip()

    def _get_text_after(self, text: str, position: int) -> str:
        """Get text after the boundary position."""
        end = min(len(text), position + self.context_chars)
        return text[position:end].strip()

    def _llm_validate(
        self,
        text_before: str,
        text_after: str,
        title: Optional[str],
    ) -> dict:
        """Use LLM to validate the boundary."""
        prompt = VALIDATION_PROMPT_TEMPLATE.format(
            text_before=text_before,
            text_after=text_after,
            title=title or "(no title proposed)",
        )

        result, response = self.llm.query_json(prompt, system=VALIDATION_SYSTEM_PROMPT)

        if not response.success:
            # HTTP error or connection failure
            logger.debug(f"LLM validation failed: {response.error}")
            return self._heuristic_validate(text_before, text_after, title)

        if result is None or not isinstance(result, dict):
            # JSON parsing failure or wrong type
            error_detail = f"got {type(result).__name__}" if result is not None else "failed to parse JSON"
            logger.warning(f"LLM validation failed ({error_detail}): {response.content[:200] if response.content else 'empty response'}")
            return self._heuristic_validate(text_before, text_after, title)

        return {
            "ending_score": float(result.get("ending_score", 5)),
            "beginning_score": float(result.get("beginning_score", 5)),
            "title_validity": float(result.get("title_validity", 5)),
            "reasoning": result.get("reasoning", ""),
        }

    def _heuristic_validate(
        self,
        text_before: str,
        text_after: str,
        title: Optional[str],
    ) -> dict:
        """Heuristic validation when LLM is not available."""
        scores = {"ending_score": 5, "beginning_score": 5, "title_validity": 5, "reasoning": "Heuristic validation"}

        # Check for ending indicators
        if text_before:
            # Ends with period/quote suggests complete thought
            if text_before.rstrip()[-1] in '.!?"\'':
                scores["ending_score"] += 2

            # Multiple paragraph breaks before suggest natural division
            if text_before.count("\n\n") >= 1:
                scores["ending_score"] += 1

        # Check for beginning indicators
        if text_after:
            # Capital letter start suggests new section
            stripped = text_after.lstrip()
            if stripped and stripped[0].isupper():
                scores["beginning_score"] += 1

            # Starts with time/place indicator
            if re.match(r"^(The|In|On|At|When|After|Before|That|It was)", stripped):
                scores["beginning_score"] += 1

        # Check title validity
        if title:
            # Explicit chapter markers are highly valid
            if re.match(r"^(Chapter|Part|Book|Prologue|Epilogue)", title, re.IGNORECASE):
                scores["title_validity"] = 9
            # Roman numerals
            elif re.match(r"^[IVXLC]+$", title):
                scores["title_validity"] = 8
            # Numbered
            elif re.match(r"^\d+$", title):
                scores["title_validity"] = 7
        else:
            scores["title_validity"] = 0

        return scores

    def _check_toc_match(self, proposal: ChapterProposal, profile: DocumentProfile) -> float:
        """Check if proposal matches a TOC entry."""
        if not profile.table_of_contents:
            return 0.0

        if not proposal.title:
            return 0.0

        best_match = 0.0

        for entry in profile.table_of_contents.entries:
            # Calculate similarity
            similarity = self._title_similarity(proposal.title, entry.title)

            if similarity > best_match:
                best_match = similarity

        return best_match

    def _title_similarity(self, title1: str, title2: str) -> float:
        """Calculate similarity between two titles."""
        # Normalize titles
        t1 = self._normalize_title(title1)
        t2 = self._normalize_title(title2)

        # Exact match
        if t1 == t2:
            return 1.0

        # One contains the other
        if t1 in t2 or t2 in t1:
            return 0.9

        # Sequence matching
        ratio = SequenceMatcher(None, t1, t2).ratio()

        return ratio

    def _normalize_title(self, title: str) -> str:
        """Normalize a title for comparison."""
        # Lowercase
        title = title.lower()

        # Remove punctuation
        title = re.sub(r"[^\w\s]", "", title)

        # Normalize whitespace
        title = " ".join(title.split())

        # Convert word numbers to digits
        word_to_num = {
            "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
            "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10",
        }
        for word, num in word_to_num.items():
            title = re.sub(rf"\b{word}\b", num, title)

        return title

    def _calculate_overall_score(
        self,
        llm_scores: dict,
        toc_score: float,
        proposal_confidence: float,
    ) -> float:
        """Calculate overall validation score."""
        # Normalize LLM scores (they're 0-10, we want 0-1)
        ending = llm_scores.get("ending_score", 5) / 10
        beginning = llm_scores.get("beginning_score", 5) / 10
        title_valid = llm_scores.get("title_validity", 5) / 10

        # Weight the components
        # TOC match is strong signal if present
        if toc_score > 0.8:
            # High TOC match dominates
            base_score = toc_score * 0.6 + (ending + beginning) / 2 * 0.3 + title_valid * 0.1
        elif toc_score > 0:
            # Partial TOC match contributes
            base_score = toc_score * 0.3 + (ending + beginning) / 2 * 0.4 + title_valid * 0.3
        else:
            # No TOC - rely on boundary quality and title
            base_score = (ending + beginning) / 2 * 0.5 + title_valid * 0.5

        # Factor in original proposal confidence
        final_score = base_score * 0.7 + proposal_confidence * 0.3

        return min(1.0, max(0.0, final_score))
