"""
Overview generator for analysis results.

Creates high-level book overview including structure, plot summary,
model usage, and timing information.
"""

import logging
from typing import Optional

from ...models import AnalysisResult
from ..llm import LLMClient

logger = logging.getLogger(__name__)


PLOT_SUMMARY_SYSTEM = """You are a literary analyst creating plot summaries for audiobook narration preparation.

CRITICAL: Base your analysis ONLY on the chapter summaries provided below.
Do NOT use any prior knowledge about this book.

Create a coherent plot summary that gives narrators a complete understanding of the story arc.

Always respond with valid JSON. No other text."""


PLOT_SUMMARY_PROMPT = """Create a comprehensive plot summary from these chapter summaries.

BOOK TITLE: {title}
CHAPTER COUNT: {chapter_count}
{narrator_context}
{main_characters}
CHAPTER SUMMARIES:
{chapter_summaries}

Create a plot summary that:
- Is 3-5 paragraphs long
- Covers the main story arc from beginning to end
- Mentions key character relationships and developments
- Highlights major plot points and turning points
- Flows naturally as a cohesive narrative
{narrator_instruction}
Return a JSON response with this structure:

```json
{{
  "plot_summary": "Paragraph 1 about the setup and main characters...\\n\\nParagraph 2 about rising action...\\n\\nParagraph 3 about climax and resolution...",
  "themes": ["identity", "ambition", "loss"],
  "narrative_style": "first-person retrospective"
}}
```

Return ONLY valid JSON. No other text."""


class OverviewGenerator:
    """Generates analysis overview with structure, plot, and metadata."""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        Args:
            llm_client: Optional LLM client for plot summary generation
        """
        self.llm = llm_client

    def generate_overview(
        self,
        analysis_result: AnalysisResult,
        profiling_data: Optional[dict] = None,
        model_usage: Optional[dict] = None,
        narrator_name: Optional[str] = None,
        narrative_style: Optional[str] = None,
    ) -> dict:
        """
        Generate overview from analysis results.

        Args:
            analysis_result: Complete analysis results
            profiling_data: Optional profiling/timing information
            model_usage: Optional dict mapping phase -> model name
            narrator_name: Optional name of the detected narrator
            narrative_style: Optional narrative style (e.g., "first-person")

        Returns:
            Dict with overview information
        """
        overview = {}

        # Structure analysis
        overview["structure"] = self._analyze_structure(analysis_result)

        # Plot summary (if LLM available)
        if self.llm and analysis_result.structure:
            overview["plot_summary"] = self._generate_plot_summary(
                analysis_result,
                narrator_name=narrator_name,
                narrative_style=narrative_style,
            )
        else:
            overview["plot_summary"] = None

        # Model usage
        if model_usage:
            overview["model_usage"] = model_usage
        else:
            overview["model_usage"] = {}

        # Timing information
        if profiling_data:
            overview["timing"] = self._extract_timing(profiling_data)
        else:
            overview["timing"] = {}

        return overview

    def _analyze_structure(self, result: AnalysisResult) -> dict:
        """Analyze book structure from chapters."""
        if not result.structure:
            return {
                "chapter_count": 0,
                "has_titles": False,
                "has_parts": False,
                "narrative_style": "unknown",
                "description": "No structure information available.",
            }

        chapters = result.structure
        chapter_count = len(chapters)

        # Check if chapters have titles (beyond "Chapter N")
        has_titles = any(ch.title and not ch.title.startswith("Chapter") for ch in chapters)

        # Check for parts/sections (look for part markers in chapter data)
        has_parts = False  # Could be enhanced with part detection logic

        # Analyze narrative style from chapter summaries
        narrative_style = "unknown"
        if chapters and hasattr(chapters[0], "pov_character") and chapters[0].pov_character:
            narrative_style = "first-person"
        elif chapters and hasattr(chapters[0], "primary_tone"):
            narrative_style = "third-person"

        # Generate description
        description_parts = [f"This book contains {chapter_count} chapters."]

        if has_titles:
            description_parts.append("Chapters have descriptive titles.")
        else:
            description_parts.append("Chapters are numbered sequentially.")

        if has_parts:
            description_parts.append("The book is organized into distinct parts or sections.")

        description = " ".join(description_parts)

        return {
            "chapter_count": chapter_count,
            "has_titles": has_titles,
            "has_parts": has_parts,
            "narrative_style": narrative_style,
            "description": description,
        }

    def _generate_plot_summary(
        self,
        result: AnalysisResult,
        narrator_name: Optional[str] = None,
        narrative_style: Optional[str] = None,
    ) -> Optional[dict]:
        """Generate plot summary from chapter summaries using LLM."""
        if not result.structure:
            return None

        # Collect chapter summaries
        chapter_summaries = []
        for idx, chapter in enumerate(result.structure, 1):
            if hasattr(chapter, "summary") and chapter.summary:
                chapter_summaries.append(f"Chapter {idx}: {chapter.summary}")

        if not chapter_summaries:
            return None

        summaries_text = "\n\n".join(chapter_summaries)

        # Build narrator context for the prompt
        narrator_context = ""
        narrator_instruction = ""
        if narrator_name:
            narrator_context = f"NARRATOR: The story is narrated by {narrator_name}"
            if narrative_style:
                narrator_context += f" ({narrative_style})"
            narrator_instruction = (
                f"\n- Refer to the narrator by their name ({narrator_name}) "
                f"rather than 'the narrator' or 'an unnamed narrator'"
            )

        # Build main characters context to ground the LLM
        main_characters = ""
        if result.characters:
            # Filter out characters with very low mention counts (< 3)
            # These are often first-person narrators added from summaries who use "I" instead of their name
            # Including them with artificially low counts can mislead the LLM
            eligible_chars = [c for c in result.characters if c.mention_count >= 3]

            # Sort by mention count (descending) and take top 3
            sorted_chars = sorted(eligible_chars, key=lambda c: c.mention_count, reverse=True)[:3]
            if sorted_chars:
                char_lines = []
                for char in sorted_chars:
                    role_info = f" ({char.role})" if char.role else ""
                    char_lines.append(
                        f"- {char.canonical_name}{role_info}: {char.mention_count} mentions"
                    )
                main_characters = (
                    "MAIN CHARACTERS (use these names, do NOT invent others):\n"
                    + "\n".join(char_lines)
                )

        prompt = PLOT_SUMMARY_PROMPT.format(
            title=result.structure[0].title if result.structure else "Unknown",
            chapter_count=len(result.structure),
            chapter_summaries=summaries_text,
            narrator_context=narrator_context,
            narrator_instruction=narrator_instruction,
            main_characters=main_characters,
        )

        result_json, response = self.llm.query_json(prompt, system=PLOT_SUMMARY_SYSTEM)

        if not response.success or result_json is None:
            logger.warning("Failed to generate plot summary via LLM")
            return None

        return result_json

    def _extract_timing(self, profiling_data: dict) -> dict:
        """Extract timing information from profiling data."""
        timing = {}

        # Extract phase durations from profiling report
        if "stages" in profiling_data:
            for stage in profiling_data["stages"]:
                stage_name = stage["name"]
                duration_seconds = stage["duration_seconds"]

                # Format duration as human-readable string
                if duration_seconds < 60:
                    duration_str = f"{duration_seconds:.1f}s"
                else:
                    minutes = int(duration_seconds // 60)
                    secs = duration_seconds % 60
                    duration_str = f"{minutes}m {secs:.0f}s"

                timing[stage_name] = {
                    "duration_seconds": duration_seconds,
                    "duration_formatted": duration_str,
                }

        # Add total duration if available
        if "totals" in profiling_data:
            total_seconds = profiling_data["totals"]["duration_seconds"]
            if total_seconds < 60:
                total_str = f"{total_seconds:.1f}s"
            else:
                minutes = int(total_seconds // 60)
                secs = total_seconds % 60
                total_str = f"{minutes}m {secs:.0f}s"

            timing["total"] = {
                "duration_seconds": total_seconds,
                "duration_formatted": total_str,
            }

        # Add timestamps if available
        if "timestamps" in profiling_data:
            timing["started_at"] = profiling_data["timestamps"]["started"]
            timing["ended_at"] = profiling_data["timestamps"]["ended"]

        return timing
