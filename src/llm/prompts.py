"""
LLM Prompts Configuration Module.

This module defines default prompts used by the LLM refiner and allows
users to customize them through a PromptConfig dataclass.
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class PromptConfig:
    """
    User-customizable LLM prompts for audiobook analysis.

    Each prompt field corresponds to a specific analysis task.
    Users can modify these through the GUI or by loading from a JSON file.
    """

    # Character extraction prompt
    character_extraction: str = """You are a literary analyst extracting STRICT, CITED character facts for audiobook narration.

Return JSON ONLY. No markdown. No commentary.

Rules:
- Only include facts explicitly supported by the provided text chunk
- Every fact must include 1+ exact quote strings copied verbatim from the chunk
- Do not infer (no guessing age/ethnicity/occupation unless explicitly stated)
- If you cannot find explicit physical description/voice/relationships for a character in this chunk, omit those facts"""

    # Pronunciation filtering prompt
    pronunciation_filter: str = """You are a linguistic assistant helping audiobook narrators identify words that need pronunciation attention.

Your task: Given a list of words, identify which ones actually require special attention from a narrator.

KEEP words that:
- Are rare, unusual, or archaic
- Could be mispronounced by an average reader
- Are proper nouns with non-obvious pronunciation
- Are technical, scientific, or domain-specific terms

REMOVE words that:
- Are common English words (even if not in a pronunciation dictionary)
- Are contraction fragments (like "hadn" from "hadn't", "wouldn" from "wouldn't")
- Are standard verb forms, adverbs, or adjectives
- Are words any fluent English speaker would pronounce correctly"""

    # Character alias detection prompt
    character_aliases: str = """You are a literary analyst helping identify character aliases in novels.
Your task is to determine which character names refer to the same person."""

    # Character relationship extraction prompt
    character_relationships: str = """You are a literary analyst extracting character relationships from novels.
Identify relationships like: spouse, sibling, parent, child, friend, enemy, employer, employee, lover, cousin, neighbor, etc.

IMPORTANT: Only report relationships that are EXPLICITLY stated or clearly demonstrated in the text.
Do NOT infer or guess relationships. If a relationship is not clearly established in the text, omit it.
Be conservative - it's better to miss a relationship than to report an incorrect one."""

    # Homograph disambiguation prompt
    homograph_disambiguation: str = """You are a pronunciation expert helping audiobook narrators.
For each homograph (word with multiple pronunciations), determine the correct pronunciation based on context."""

    # Chapter detection prompt
    chapter_detection: str = """You are a document structure analyst. Your task is to identify chapter boundaries in books.

You must distinguish between:
1. ACTUAL chapter markers (the start of real chapters in the book content)
2. TABLE OF CONTENTS entries (lists of chapter names/numbers that appear at the start)
3. Other structural elements (title pages, dedication, etc.)

Only identify ACTUAL chapter starts, not TOC entries."""

    # Chapter summary prompt - UPDATED for narrative style
    chapter_summary: str = """You are a literary analyst summarizing novel chapters.
Write a detailed narrative summary (4-6 sentences) describing WHAT HAPPENS in the chapter:
- Key plot events and scenes that occur
- Which characters appear and what they do
- The emotional arc and tone of the chapter
- Important dialogue moments or revelations

Write in third person, past tense, as if describing the chapter's content.
DO NOT write instructions for how to read or perform the chapter.
DO NOT use phrases like "the narrator should" or "the reader must".
Simply describe what happens in the story."""

    # Character profile enrichment prompt
    character_profile: str = """You are a literary analyst creating character profiles for audiobook narrators.

IMPORTANT: Do NOT use <think> tags or any internal reasoning tags. Write your response directly.

CRITICAL FORMAT REQUIREMENT:
Write in FLOWING PROSE PARAGRAPHS only. Do NOT use bullet points, lists, or dashes.
Synthesize information into natural, readable paragraphs that a narrator can reference.

CONTENT REQUIREMENTS:
- Only include information EXPLICITLY stated in the provided text
- Do NOT invent, assume, or infer details not directly supported by the text
- When information is not available, simply omit that topic
- Weave quotes naturally into your prose (e.g., "described as having 'piercing blue eyes'")

FORBIDDEN:
- Bullet points (lines starting with - or * or •)
- Lists of any kind
- Enumerated points
- Quote dumps without synthesis

Write 2-4 paragraphs of flowing prose covering:
- Physical appearance (if described)
- Personality and behavior (based on actions)
- Speech patterns and voice (based on dialogue)
- Key relationships (only what's explicitly shown)

Write naturally, as if describing the character to a colleague."""

    @classmethod
    def load_from_file(cls, path: str | Path) -> "PromptConfig":
        """
        Load custom prompts from a JSON file.

        Args:
            path: Path to the JSON file

        Returns:
            PromptConfig with loaded values (defaults used for missing fields)
        """
        path = Path(path)
        if not path.exists():
            return cls()

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return cls(**{k: v for k, v in data.items() if hasattr(cls, k)})
        except (json.JSONDecodeError, TypeError):
            return cls()

    def save_to_file(self, path: str | Path) -> None:
        """
        Save prompts to a JSON file.

        Args:
            path: Path to save the JSON file
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2, ensure_ascii=False)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def get_prompt_descriptions(cls) -> dict[str, str]:
        """
        Get human-readable descriptions for each prompt field.

        Returns:
            Dict mapping field names to descriptions
        """
        return {
            "character_extraction": "Character Facts Extraction",
            "pronunciation_filter": "Pronunciation Word Filtering",
            "character_aliases": "Character Alias Detection",
            "character_relationships": "Character Relationship Extraction",
            "homograph_disambiguation": "Homograph Disambiguation",
            "chapter_detection": "Chapter Detection",
            "chapter_summary": "Chapter Summary Generation",
            "character_profile": "Character Profile Enrichment",
        }


# Default config instance for convenience
DEFAULT_PROMPTS = PromptConfig()
