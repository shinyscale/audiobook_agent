"""
LLM refinement layer for audiobook analysis.
Uses local models via LM Studio (OpenAI-compatible API) to filter false positives and enrich results.
"""

import json
import re
import time
from typing import Optional, Literal
from dataclasses import dataclass

import requests

from ..models import (
    AnalysisResult,
    PronunciationEntry,
    PronunciationFlag,
    Character,
    ConfidenceLevel,
    StructuralElement,
    StructureType,
)
from .config import get_default_model, LLMProvider, CONTEXT_PERCENT
from .prompts import PromptConfig, DEFAULT_PROMPTS
from .exceptions import (
    ChapterDetectionError,
    CharacterProfileError,
    ChapterSummaryError,
)


@dataclass
class RefinementStats:
    """Statistics from a refinement run."""
    chapters_detected: int = 0
    chapter_summaries_generated: int = 0
    pronunciations_removed: int = 0
    characters_merged: int = 0
    relationships_added: int = 0
    character_profiles_generated: int = 0
    homographs_resolved: int = 0


class LLMRefiner:
    """Refines analysis results using LLM via various providers (Ollama, LM Studio, OpenAI, Anthropic)."""

    def __init__(
        self,
        model: Optional[str] = None,
        base_url: str = "http://localhost:1234/v1",
        timeout: int = 300,
        provider: str = "lm_studio",
        api_key: Optional[str] = None,
        context_length: int = 32768,
        custom_prompts: Optional[PromptConfig] = None,
    ):
        """
        Initialize the LLM refiner.

        Args:
            model: Model identifier
            base_url: URL of the LLM server
            timeout: Request timeout in seconds (default 300s for large models)
            provider: LLM provider ("ollama", "lm_studio", "openai", "anthropic")
            api_key: API key for cloud providers (OpenAI, Anthropic)
            context_length: Model context length in tokens (used to scale input limits)
            custom_prompts: User-customizable prompts (uses defaults if not provided)
        """
        self.model = model or get_default_model()
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.provider = LLMProvider(provider) if isinstance(provider, str) else provider
        self.api_key = api_key
        self.context_length = context_length
        self.prompts = custom_prompts or DEFAULT_PROMPTS

    def _context_chars(self, purpose: str) -> int:
        """
        Calculate max input characters for a purpose based on context length.

        Args:
            purpose: The purpose key (e.g., "chapter_detection", "character_profile")

        Returns:
            Maximum number of characters to use for this purpose
        """
        percent = CONTEXT_PERCENT.get(purpose, 0.50)
        tokens = int(self.context_length * percent)
        return tokens * 4  # ~4 chars per token

    def _query(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.1,
        raise_on_http_error: bool = False,
    ) -> str:
        """
        Send a query to the LLM via the configured provider.

        Args:
            prompt: The user prompt
            system: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (low for factual tasks)
            raise_on_http_error: Whether to raise HTTPError on failure

        Returns:
            The model's response text
        """
        # Dispatch to Anthropic-specific method if needed
        if self.provider == LLMProvider.ANTHROPIC:
            return self._query_anthropic(prompt, system, max_tokens, temperature, raise_on_http_error)

        # OpenAI-compatible providers (Ollama, LM Studio, OpenAI)
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }

        if self.model:
            payload["model"] = self.model

        # Build headers with auth for OpenAI
        headers = {"Content-Type": "application/json"}
        if self.api_key and self.provider == LLMProvider.OPENAI:
            headers["Authorization"] = f"Bearer {self.api_key}"

        provider_name = self.provider.value.replace("_", " ").title()
        try:
            print(f"      → Sending request to {provider_name}...")
            print(f"      → Prompt length: {len(prompt)} chars, max_tokens: {max_tokens}")
            start_time = time.time()

            response = requests.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                timeout=self.timeout,
                headers=headers,
            )

            elapsed = time.time() - start_time
            if not response.ok:
                body = response.text
                if len(body) > 4000:
                    body = body[:4000] + "...(truncated)"
                print(f"   ⚠️  LLM HTTP {response.status_code} error. Body:\n{body}")
                response.raise_for_status()
            result = response.json()

            # Extract response from OpenAI-compatible format
            choices = result.get("choices", [])
            if not choices:
                print("   ⚠️  No response choices returned")
                return ""

            response_text = choices[0].get("message", {}).get("content", "")

            # Show timing and token info
            usage = result.get("usage", {})
            completion_tokens = usage.get("completion_tokens", 0)
            prompt_tokens = usage.get("prompt_tokens", 0)
            print(f"      ✓ Response received in {elapsed:.1f}s ({completion_tokens} completion tokens, {prompt_tokens} prompt tokens)")

            return response_text
        except requests.exceptions.Timeout:
            print(f"   ⚠️  LLM request timed out after {self.timeout}s")
            print(f"      Check {provider_name} is running and model is loaded")
            return ""
        except requests.exceptions.ConnectionError:
            print(f"   ⚠️  Cannot connect to {provider_name} at {self.base_url}")
            print(f"      Make sure {provider_name} is running with server enabled")
            return ""
        except requests.exceptions.RequestException as e:
            print(f"   ⚠️  LLM query failed: {e}")
            if raise_on_http_error and isinstance(e, requests.exceptions.HTTPError):
                raise
            return ""

    def _query_anthropic(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.1,
        raise_on_http_error: bool = False,
    ) -> str:
        """
        Send a query to Anthropic's Messages API.

        Args:
            prompt: The user prompt
            system: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            raise_on_http_error: Whether to raise HTTPError on failure

        Returns:
            The model's response text
        """
        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }
        if system:
            payload["system"] = system

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key or "",
            "anthropic-version": "2023-06-01",
        }

        try:
            print(f"      → Sending request to Anthropic...")
            print(f"      → Prompt length: {len(prompt)} chars, max_tokens: {max_tokens}")
            start_time = time.time()

            response = requests.post(
                f"{self.base_url}/messages",
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )

            elapsed = time.time() - start_time
            if not response.ok:
                body = response.text
                if len(body) > 4000:
                    body = body[:4000] + "...(truncated)"
                print(f"   ⚠️  Anthropic HTTP {response.status_code} error. Body:\n{body}")
                if raise_on_http_error:
                    response.raise_for_status()
                return ""

            result = response.json()

            # Extract response from Anthropic Messages format
            content = result.get("content", [])
            if not content:
                print("   ⚠️  No response content returned")
                return ""

            # Anthropic returns content as array of blocks
            response_text = ""
            for block in content:
                if block.get("type") == "text":
                    response_text += block.get("text", "")

            # Show timing and token info
            usage = result.get("usage", {})
            output_tokens = usage.get("output_tokens", 0)
            input_tokens = usage.get("input_tokens", 0)
            print(f"      ✓ Response received in {elapsed:.1f}s ({output_tokens} output tokens, {input_tokens} input tokens)")

            return response_text
        except requests.exceptions.Timeout:
            print(f"   ⚠️  Anthropic request timed out after {self.timeout}s")
            return ""
        except requests.exceptions.ConnectionError:
            print(f"   ⚠️  Cannot connect to Anthropic at {self.base_url}")
            return ""
        except requests.exceptions.RequestException as e:
            print(f"   ⚠️  Anthropic query failed: {e}")
            if raise_on_http_error and isinstance(e, requests.exceptions.HTTPError):
                raise
            return ""

    def _query_with_backoff(
        self,
        prompt_variants: list[str],
        system: Optional[str],
        max_tokens: int,
        temperature: float = 0.1,
    ) -> str:
        """
        Try multiple prompt variants, backing off on size/complexity if the server rejects the request.

        This is primarily to handle cases where LM Studio model context is configured smaller than
        the text sample we attempt to send (often resulting in HTTP 400).
        """
        last_error = None
        for i, prompt in enumerate(prompt_variants, 1):
            try:
                if len(prompt_variants) > 1:
                    print(f"      → Attempt {i}/{len(prompt_variants)} (prompt {len(prompt)} chars)")
                return self._query(
                    prompt,
                    system=system,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    raise_on_http_error=True,
                )
            except requests.exceptions.HTTPError as e:
                last_error = e
                # Try next variant
                continue
        if last_error:
            print(f"   ⚠️  All prompt variants failed: {last_error}")
        return ""

    def _clean_thinking_tags(self, response: str) -> str:
        """
        Remove <think>...</think> tags from LLM responses.

        Some models (like Qwen3) output chain-of-thought reasoning in these tags
        which should be stripped from the final output.
        """
        # Remove <think>...</think> blocks (can span multiple lines)
        cleaned = re.sub(r"<think>.*?</think>", "", response, flags=re.DOTALL)
        # Also handle unclosed <think> tags (output may be truncated)
        cleaned = re.sub(r"<think>.*$", "", cleaned, flags=re.DOTALL)
        return cleaned.strip()

    def _iter_paragraph_spans(self, text: str) -> list[tuple[int, int, str]]:
        """
        Split text into paragraph spans (start, end, paragraph_text).

        Paragraphs are separated by one or more blank lines.
        """
        spans: list[tuple[int, int, str]] = []
        # Match one or more blank lines (handles \n and \r\n)
        sep_re = re.compile(r"(?:\r?\n\s*){2,}")
        start = 0
        for m in sep_re.finditer(text):
            end = m.start()
            if end > start:
                para = text[start:end]
                if para.strip():
                    spans.append((start, end, para))
            start = m.end()
        # Trailing paragraph
        if start < len(text):
            para = text[start:]
            if para.strip():
                spans.append((start, len(text), para))
        return spans

    def extract_chunk_character_facts(
        self,
        chunk_text: str,
        chunk_start: int,
        character_names: list[str],
        max_tokens: int = 1200,
    ) -> list[dict]:
        """
        Extract structured character facts from a chunk of text.

        The LLM is instructed to only use explicit information from the provided chunk,
        and to include exact quotes as evidence. We then locate those quotes in the chunk
        to compute approximate absolute offsets.
        """
        if not chunk_text.strip() or not character_names:
            return []

        system = self.prompts.character_extraction

        prompt = f"""Extract character facts from this text chunk.

Characters of interest:
{json.dumps(character_names, indent=2)}

TEXT CHUNK:
\"\"\"
{chunk_text}
\"\"\"

Return JSON with this shape:
{{
  "characters": [
    {{
      "name": "Canonical Name",
      "aliases": ["Alias1", "Alias2"],
      "facts": [
        {{
          "type": "appearance|voice|personality|role|relationship|other",
          "statement": "one-sentence factual statement",
          "quotes": ["exact quote 1", "exact quote 2"]
        }}
      ],
      "relationships": [
        {{
          "other": "Other Character",
          "relation": "spouse|friend|acquaintance|employer|lover|... (only if explicit)",
          "quotes": ["exact quote"]
        }}
      ]
    }}
  ]
}}

Important:
- Quotes MUST be exact substrings of the TEXT CHUNK.
- Keep it concise: include only the strongest 3-8 facts per character that appear in this chunk.

JSON:"""

        response = self._query(prompt, system=system, max_tokens=max_tokens, temperature=0.1)
        parsed = self._parse_json_response(response)
        if not isinstance(parsed, dict):
            return []

        chars = parsed.get("characters")
        if not isinstance(chars, list):
            return []

        def _locate_quote(q: str) -> Optional[int]:
            if not isinstance(q, str) or not q.strip():
                return None
            pos = chunk_text.find(q)
            if pos >= 0:
                return chunk_start + pos
            # Try a whitespace-normalized match as a fallback
            qn = " ".join(q.split())
            tn = " ".join(chunk_text.split())
            pos2 = tn.find(qn)
            if pos2 >= 0:
                # Note: position in normalized text is approximate; keep as chunk_start only.
                return chunk_start
            return None

        enriched: list[dict] = []
        for c in chars:
            if not isinstance(c, dict):
                continue
            name = c.get("name")
            if not isinstance(name, str) or not name.strip():
                continue
            aliases = c.get("aliases", [])
            if not isinstance(aliases, list):
                aliases = []

            facts_out: list[dict] = []
            for f in c.get("facts", []) if isinstance(c.get("facts"), list) else []:
                if not isinstance(f, dict):
                    continue
                quotes = f.get("quotes", [])
                if not isinstance(quotes, list) or not quotes:
                    continue
                quote_spans = []
                for q in quotes:
                    pos = _locate_quote(q)
                    if pos is not None:
                        quote_spans.append({"quote": q, "position": pos})
                if not quote_spans:
                    continue
                facts_out.append({
                    "type": f.get("type"),
                    "statement": f.get("statement"),
                    "quotes": quote_spans,
                })

            rels_out: list[dict] = []
            for r in c.get("relationships", []) if isinstance(c.get("relationships"), list) else []:
                if not isinstance(r, dict):
                    continue
                quotes = r.get("quotes", [])
                if not isinstance(quotes, list) or not quotes:
                    continue
                quote_spans = []
                for q in quotes:
                    pos = _locate_quote(q)
                    if pos is not None:
                        quote_spans.append({"quote": q, "position": pos})
                if not quote_spans:
                    continue
                rels_out.append({
                    "other": r.get("other"),
                    "relation": r.get("relation"),
                    "quotes": quote_spans,
                })

            enriched.append({
                "name": name,
                "aliases": [a for a in aliases if isinstance(a, str) and a.strip()],
                "facts": facts_out,
                "relationships": rels_out,
            })

        return enriched

    def _parse_json_response(self, response: str) -> Optional[dict | list]:
        """Extract and parse JSON from LLM response."""
        # Try to find JSON in the response
        response = response.strip()

        # Remove thinking tags if present
        response = self._clean_thinking_tags(response)

        # Remove markdown code blocks if present
        if "```json" in response:
            match = re.search(r"```json\s*(.*?)\s*```", response, re.DOTALL)
            if match:
                response = match.group(1)
        elif "```" in response:
            match = re.search(r"```\s*(.*?)\s*```", response, re.DOTALL)
            if match:
                response = match.group(1)

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Try to find JSON object or array in text
            for pattern in [r"\{[^{}]*\}", r"\[[^\[\]]*\]"]:
                match = re.search(pattern, response, re.DOTALL)
                if match:
                    try:
                        return json.loads(match.group(0))
                    except json.JSONDecodeError:
                        continue
            return None

    def filter_false_positives(
        self,
        pronunciations: list[PronunciationEntry],
        batch_size: int = 50,
    ) -> list[PronunciationEntry]:
        """
        Use LLM to filter false positives from pronunciation flags.

        Removes:
        - Contraction fragments ("hadn", "wouldn", etc.)
        - Common English words not in CMU dictionary
        - Words that don't actually need narrator attention

        Args:
            pronunciations: List of pronunciation entries to filter
            batch_size: Number of words to process per LLM call

        Returns:
            Filtered list of pronunciation entries
        """
        # Separate by flag type - only filter "unknown" flags
        unknown_entries = [p for p in pronunciations if p.flag_reason == PronunciationFlag.UNKNOWN]
        other_entries = [p for p in pronunciations if p.flag_reason != PronunciationFlag.UNKNOWN]

        if not unknown_entries:
            return pronunciations

        # Extract words to check
        words_to_check = [e.word for e in unknown_entries]

        # Process in batches
        words_to_keep = set()

        for i in range(0, len(words_to_check), batch_size):
            batch = words_to_check[i:i + batch_size]
            keep_words = self._filter_word_batch(batch)
            words_to_keep.update(keep_words)

        # Filter unknown entries
        filtered_unknown = [
            e for e in unknown_entries
            if e.word.lower() in words_to_keep
        ]

        # Update confidence for LLM-filtered entries
        for entry in filtered_unknown:
            entry.confidence = ConfidenceLevel.LLM_REFINED

        return other_entries + filtered_unknown

    def _filter_word_batch(self, words: list[str]) -> set[str]:
        """
        Ask LLM which words from a batch actually need pronunciation attention.

        Args:
            words: List of words to evaluate

        Returns:
            Set of words that should be kept (need attention)
        """
        system = self.prompts.pronunciation_filter

        prompt = f"""Here are words flagged as potentially needing pronunciation attention:

{json.dumps(words, indent=2)}

Return a JSON array containing ONLY the words that actually need narrator attention.
Do not include common words, contraction fragments, or standard English words.

Example: If given ["hadn", "incredulously", "Cthulhu", "sauntered"], return ["Cthulhu"]
because "hadn" is a contraction fragment, "incredulously" and "sauntered" are common words.

JSON array of words to keep:"""

        response = self._query(prompt, system=system, max_tokens=1000)
        result = self._parse_json_response(response)

        if isinstance(result, list):
            return {w.lower() for w in result if isinstance(w, str)}

        return set()  # If parsing fails, keep nothing (be conservative)

    def resolve_character_aliases(
        self,
        characters: list[Character],
        text_sample: str,
    ) -> list[Character]:
        """
        Use LLM to determine if characters should be merged.

        Args:
            characters: List of Character objects from initial extraction
            text_sample: Sample of book text for context

        Returns:
            Updated character list with merged aliases
        """
        if len(characters) < 2:
            return characters

        # Get top characters by mention count
        char_names = [c.canonical_name for c in characters[:30]]

        system = self.prompts.character_aliases

        def _build_prompt(sample_chars: int) -> str:
            return f"""Analyze these character names from a novel and identify which ones refer to the same person.

Character names found:
{json.dumps(char_names, indent=2)}

Sample text for context (first {sample_chars} characters):
"{text_sample[:sample_chars]}"

Output a JSON object mapping canonical names to their aliases.
Only include characters that have aliases (names that refer to the same person).
Use the most complete name as the key.

Example format:
{{"John Smith": ["John", "Smith", "her husband"], "Mary Johnson": ["Mary", "Mrs. Johnson"]}}

JSON output:"""

        # Use percentage-based context limits with backoff (100%, 50%, 25%, 12.5%)
        max_chars = self._context_chars("alias_resolution")
        prompt_variants = [_build_prompt(int(max_chars * f)) for f in (1.0, 0.5, 0.25, 0.125)]
        response = self._query_with_backoff(prompt_variants, system=system, max_tokens=1500)
        aliases_map = self._parse_json_response(response)

        if not isinstance(aliases_map, dict):
            return characters

        # Build mention count lookup for validation
        mention_counts = {c.canonical_name.lower(): c.mention_count for c in characters}
        top_characters = set(
            name for name, _ in sorted(mention_counts.items(), key=lambda x: x[1], reverse=True)[:20]
        )

        # Build a mapping from alias -> canonical name with validation
        canonical_lookup = {}
        for canonical, aliases in aliases_map.items():
            if isinstance(aliases, list):
                for alias in aliases:
                    if isinstance(alias, str):
                        alias_lower = alias.lower()
                        canonical_lower = canonical.lower()

                        # Validation: Alias should share at least one name part with canonical
                        # e.g., "Tom" can merge with "Tom Buchanan", but not "Myrtle" with "George"
                        alias_parts = set(alias_lower.split())
                        canonical_parts = set(canonical_lower.split())
                        if not alias_parts & canonical_parts:
                            # No shared name parts - skip this merge
                            continue

                        # Only block merge if both are top-20 AND they don't share a name part
                        # This allows "Baker" + "Jordan Baker" to merge (they share "baker")
                        # but still prevents "George Wilson" + "Myrtle Wilson" (no shared parts)
                        if alias_lower in top_characters and canonical_lower in top_characters:
                            if not (alias_parts & canonical_parts):
                                continue
                            # If they share a name part, allow the merge

                        canonical_lookup[alias_lower] = canonical

        # Merge characters
        merged = {}
        for char in characters:
            canonical = canonical_lookup.get(char.canonical_name.lower(), char.canonical_name)

            if canonical not in merged:
                char.canonical_name = canonical
                char.confidence = ConfidenceLevel.LLM_REFINED
                merged[canonical] = char
            else:
                # Merge into existing character
                existing = merged[canonical]
                existing.mention_count += char.mention_count
                existing.aliases.extend([char.canonical_name] + char.aliases)
                existing.descriptions.extend(char.descriptions)

        # Deduplicate aliases
        for char in merged.values():
            char.aliases = list(set(a for a in char.aliases if a.lower() != char.canonical_name.lower()))

        return list(merged.values())

    def extract_relationships(
        self,
        characters: list[Character],
        text_sample: str,
    ) -> dict[str, dict[str, str]]:
        """
        Extract character relationships from text using LLM.

        Args:
            characters: List of Character objects
            text_sample: Sample of book text

        Returns:
            Dict mapping character_name -> {other_char_name: relationship}
        """
        if len(characters) < 2:
            return {}

        char_names = [c.canonical_name for c in characters[:20]]

        system = self.prompts.character_relationships

        def _build_prompt(sample_chars: int) -> str:
            return f"""Identify relationships between these characters based ONLY on what is explicitly stated in the text.

Characters:
{json.dumps(char_names, indent=2)}

Text sample:
"{text_sample[:sample_chars]}"

Output a JSON object showing ONLY relationships that are explicitly stated or clearly demonstrated.
Do NOT guess or infer relationships that aren't clear from the text.

Format: {{"Character A": {{"Character B": "relationship"}}}}

Example:
{{"John Smith": {{"Jane Smith": "spouse", "Robert Brown": "colleague"}}}}

JSON output:"""

        # Use percentage-based context limits with backoff (100%, 50%, 25%, 12.5%)
        max_chars = self._context_chars("relationship_extraction")
        prompt_variants = [_build_prompt(int(max_chars * f)) for f in (1.0, 0.5, 0.25, 0.125)]
        response = self._query_with_backoff(prompt_variants, system=system, max_tokens=1500)
        result = self._parse_json_response(response)

        if isinstance(result, dict):
            return result
        return {}

    def disambiguate_homographs(
        self,
        pronunciations: list[PronunciationEntry],
        text: str,
    ) -> list[PronunciationEntry]:
        """
        Use LLM to determine correct pronunciation of homographs in context.

        Args:
            pronunciations: List of pronunciation entries
            text: Full book text for context lookup

        Returns:
            Updated pronunciation entries with resolved homographs
        """
        homographs = [p for p in pronunciations if p.flag_reason == PronunciationFlag.HOMOGRAPH]

        if not homographs:
            return pronunciations

        system = self.prompts.homograph_disambiguation

        for entry in homographs:
            if not entry.context_examples or not entry.notes:
                continue

            # Extract options from notes
            if "Options:" not in entry.notes:
                continue

            options_str = entry.notes.split("Options:")[1].strip()

            prompt = f"""Which pronunciation is correct for "{entry.word}" in this context?

Context: "{entry.context_examples[0]}"

Options: {options_str}

Reply with just the correct option (copy it exactly from the options above)."""

            response = self._query(prompt, system=system, max_tokens=100)
            response = response.strip()

            if response:
                entry.notes = f"Likely: {response}"
                entry.confidence = ConfidenceLevel.LLM_REFINED

        return pronunciations

    def detect_chapters(
        self,
        text: str,
        words_per_minute: int = 150,
    ) -> list[StructuralElement]:
        """
        Multi-pass LLM-based chapter detection. Scans full book in overlapping chunks.

        This approach:
        1. Scans the entire book in overlapping chunks
        2. Asks LLM to identify chapters and their exact first_words in each chunk
        3. Searches for first_words to get precise positions
        4. Validates chapter sizes (no tiny fragments)

        Raises ChapterDetectionError on failure instead of falling back to garbage.

        Args:
            text: Full book text
            words_per_minute: For duration estimates

        Returns:
            List of StructuralElement objects for chapters (may be empty for chapterless books)
        """
        chunk_size = self._context_chars("chapter_detection")
        overlap = chunk_size // 10  # 10% overlap to catch chapters at boundaries

        all_chapters_found = []

        # Scan book in overlapping chunks
        pos = 0
        chunk_num = 0
        while pos < len(text):
            chunk_num += 1
            chunk_end = min(pos + chunk_size, len(text))
            chunk = text[pos:chunk_end]

            print(f"      Scanning chunk {chunk_num} (chars {pos:,}-{chunk_end:,})...")

            prompt = f"""Find ALL chapter boundaries in this book text.

CRITICAL INSTRUCTION - READ CAREFULLY:
You are analyzing a TEXT DOCUMENT provided below. You must ONLY use information from this document.
DO NOT use any knowledge you have about this book from your training data.
DO NOT assume you know what the text says - READ IT from the document below.
Even if you recognize this book, IGNORE what you "know" and only read what is provided.
The text may have different spelling, formatting, or content than versions you've seen before.

TEXT DOCUMENT (characters {pos} to {chunk_end}):
\"\"\"
{chunk}
\"\"\"

TASK: Find EVERY chapter that STARTS within this document. For each chapter provide:
1. The chapter marker/title exactly as written (e.g., "I", "II", "Chapter 1", "PART ONE")
2. The first 15 words of chapter content COPIED EXACTLY from the document above (not the title line)

Return JSON with ALL chapters:
{{
    "chapters_found": [
        {{"title": "I", "first_words": "[COPY 15 WORDS EXACTLY FROM DOCUMENT ABOVE]"}},
        {{"title": "II", "first_words": "[COPY 15 WORDS EXACTLY FROM DOCUMENT ABOVE]"}}
    ]
}}

CRITICAL RULES:
- COPY text EXACTLY as it appears, character-for-character, including unusual spellings
- Find ALL chapters (if document has I through IX, list all 9)
- Only real chapters, not Table of Contents entries or scene breaks (*** or ----)
- We will search for your first_words string - if you paraphrase, the search WILL FAIL"""

            system = self.prompts.chapter_detection

            response = self._query(prompt, system=system, max_tokens=2000, temperature=0.1)
            result = self._parse_json_response(response)

            if isinstance(result, dict) and result.get("chapters_found"):
                for ch in result["chapters_found"]:
                    ch["chunk_start"] = pos  # Track which chunk found this
                    all_chapters_found.append(ch)

            # Move to next chunk (with overlap)
            if chunk_end >= len(text):
                break
            pos = chunk_end - overlap

        if not all_chapters_found:
            # This is valid - some books don't have chapters (continuous prose, short stories, etc.)
            print("      No chapters found - book may be continuous prose")
            return []  # Empty list, not an error

        # Deduplicate chapters found in overlapping regions (same title)
        unique_chapters = []
        seen_titles = set()
        for ch in all_chapters_found:
            title = ch.get("title", "").strip()
            if title and title not in seen_titles:
                seen_titles.add(title)
                unique_chapters.append(ch)

        print(f"      Found {len(unique_chapters)} unique chapters across {chunk_num} chunk(s)")

        # Log what the LLM returned for debugging
        for ch in unique_chapters:
            fw = ch.get("first_words", "")[:60]
            print(f"        - {ch.get('title')}: \"{fw}...\"")

        # Find exact positions by searching for first_words
        # Helper: normalize whitespace for comparison (collapse multiple whitespace to single space)
        def normalize_ws(s: str) -> str:
            return ' '.join(s.split())

        elements = []
        for i, ch in enumerate(unique_chapters):
            first_words = ch.get("first_words", "")
            if not first_words or len(first_words) < 20:
                raise ChapterDetectionError(
                    f"Chapter '{ch.get('title', i+1)}' has insufficient first_words: '{first_words}'\n"
                    f"The LLM should return 10-15 words copied verbatim from the text."
                )

            # Find this text in the full book
            found_pos = text.find(first_words)
            if found_pos == -1:
                # Try case-insensitive
                found_pos = text.lower().find(first_words.lower())

            if found_pos == -1:
                # Try with normalized whitespace (text files often have line breaks mid-sentence)
                normalized_query = normalize_ws(first_words)
                # Search through text in chunks, normalizing each chunk
                for start_idx in range(0, len(text) - len(first_words), 1000):
                    chunk = text[start_idx:start_idx + len(first_words) + 200]
                    normalized_chunk = normalize_ws(chunk)
                    pos_in_chunk = normalized_chunk.find(normalized_query)
                    if pos_in_chunk != -1:
                        # Found it - but we need the actual position in original text
                        # Search for the first few words at this approximate location
                        search_start = max(0, start_idx - 100)
                        search_end = min(len(text), start_idx + 500)
                        first_few = normalize_ws(first_words[:30])
                        local_text = text[search_start:search_end]
                        local_normalized = normalize_ws(local_text)
                        local_pos = local_normalized.find(first_few)
                        if local_pos != -1:
                            # Map back to original position approximately
                            found_pos = search_start + local_text.find(first_words.split()[0])
                            break

            if found_pos == -1:
                raise ChapterDetectionError(
                    f"Could not find chapter '{ch.get('title')}' starting with:\n"
                    f"  '{first_words[:80]}...'\n\n"
                    f"This may indicate the LLM hallucinated or paraphrased the text.\n"
                    f"The first_words must be copied EXACTLY from the book."
                )

            elements.append(StructuralElement(
                type=StructureType.CHAPTER,
                title=ch.get("title", f"Chapter {i+1}"),
                index=i + 1,
                start_position=found_pos,
                end_position=0,  # Set below
                confidence=ConfidenceLevel.LLM_REFINED,
            ))

        # Sort by position and set end positions
        elements.sort(key=lambda e: e.start_position)
        for i, elem in enumerate(elements):
            elem.index = i + 1  # Re-index after sorting
            if i < len(elements) - 1:
                elem.end_position = elements[i + 1].start_position
            else:
                elem.end_position = len(text)

        # Calculate word counts and durations
        for elem in elements:
            chapter_text = text[elem.start_position:elem.end_position]
            elem.word_count = len(chapter_text.split())
            elem.estimated_duration_minutes = elem.word_count / words_per_minute

        # VALIDATION: Chapters should be substantial (no tiny fragments)
        for elem in elements:
            if elem.word_count < 500:
                raise ChapterDetectionError(
                    f"Chapter '{elem.title}' has only {elem.word_count} words at position {elem.start_position}.\n"
                    f"This is likely a detection error, not a real chapter.\n"
                    f"Real chapters typically have 1000+ words."
                )

        # VALIDATION: Not too many chapters (sanity check)
        if len(elements) > 100:
            raise ChapterDetectionError(
                f"Detected {len(elements)} chapters, which is unreasonably high.\n"
                f"This indicates a detection failure - the LLM may be identifying\n"
                f"scene breaks or paragraphs instead of actual chapters."
            )

        print(f"      ✓ Validated {len(elements)} chapters with substantial word counts")
        return elements

    def generate_chapter_summaries(
        self,
        chapters: list[StructuralElement],
        text: str,
    ) -> list[StructuralElement]:
        """
        Generate detailed summaries for each chapter using LLM.

        Creates paragraph-length summaries covering:
        - Key plot events and scenes
        - Characters who appear and their actions
        - Emotional beats and tone shifts
        - Important dialogue moments or revelations

        Args:
            chapters: List of chapter StructuralElements
            text: Full book text

        Returns:
            Chapters with summary field populated
        """
        system = self.prompts.chapter_summary

        # Calculate max chars based on context length
        max_summary_chars = self._context_chars("chapter_summary")

        for chapter in chapters:
            if chapter.type != StructureType.CHAPTER:
                continue

            chapter_text = text[chapter.start_position:chapter.end_position]

            # Truncate to context-appropriate length
            truncated = chapter_text[:max_summary_chars]
            truncation_note = "" if len(chapter_text) <= max_summary_chars else " (truncated)"

            prompt = f"""Write a narrative summary of Chapter {chapter.index} ({chapter.title or 'Untitled'}){truncation_note}.

Chapter text:
{truncated}

Summarize WHAT HAPPENS in this chapter in 4-6 sentences. Describe the key events, which characters appear, and the emotional tone. Write in third person, past tense (e.g., "John visited the Smiths..."). Do NOT write performance instructions."""

            print(f"      Generating summary for Chapter {chapter.index}...")
            response = self._query(prompt, system=system, max_tokens=500)
            chapter.summary = response.strip() if response else None

        return chapters

    def enrich_character_descriptions(
        self,
        characters: list[Character],
        text: str,
        max_chars: int = 20,
        structure: Optional[list[StructuralElement]] = None,
    ) -> list[Character]:
        """
        Generate comprehensive character profiles using LLM.

        Creates narrator-focused profiles including:
        - Physical appearance (height, build, distinctive features)
        - Personality traits and mannerisms
        - Voice/speech patterns (accent hints, vocabulary level, speech quirks)
        - Role in the story
        - Key relationships with other characters

        Args:
            characters: List of Character objects
            text: Full book text
            max_chars: Maximum number of characters to process

        Returns:
            Characters with comprehensive LLM-generated profiles
        """
        system = self.prompts.character_profile

        from ..models import CharacterDescription

        # Sort characters by mention count for importance-based length scaling
        sorted_chars = sorted(characters, key=lambda c: c.mention_count, reverse=True)

        # --- Chapter-first evidence extraction (clears context between chunks) ---
        chapters: list[StructuralElement] = []
        if structure:
            chapters = [e for e in structure if e.type == StructureType.CHAPTER]
        if not chapters:
            # Single chunk fallback
            chapters = [StructuralElement(
                type=StructureType.CHAPTER,
                title="Full Text",
                index=1,
                start_position=0,
                end_position=len(text),
                confidence=ConfidenceLevel.LOW,
                word_count=len(text.split()),
                estimated_duration_minutes=0.0,
            )]

        # Only extract evidence for the same set of characters we will generate profiles for
        target_chars = sorted_chars[:max_chars]

        # Build name/alias lookup -> Character
        name_to_char: dict[str, Character] = {}
        for c in characters:
            name_to_char[c.canonical_name.lower()] = c
            for a in c.aliases:
                name_to_char[a.lower()] = c

        # Collect evidence per canonical name
        evidence_map: dict[str, list[dict]] = {c.canonical_name: [] for c in characters}

        # Calculate max chars based on context length
        max_safe_chars = self._context_chars("character_profile")
        # Overlap size is ~10% of chunk size
        overlap_size = max(2000, max_safe_chars // 10)

        for ch in chapters:
            chunk_text = text[ch.start_position:ch.end_position]

            # Split oversized chapters into sub-chunks with overlap
            if len(chunk_text) > max_safe_chars:
                sub_chunk_size = max_safe_chars
                sub_chunks: list[tuple[int, int]] = []
                pos = 0
                while pos < len(chunk_text):
                    end = min(pos + sub_chunk_size, len(chunk_text))
                    sub_chunks.append((pos, end))
                    if end >= len(chunk_text):
                        break
                    pos = end - overlap_size
            else:
                sub_chunks = [(0, len(chunk_text))]
            
            # Determine which target characters appear in this chunk (check full chunk)
            present: list[str] = []
            for c in target_chars:
                names = [c.canonical_name] + (c.aliases or [])
                for n in names:
                    if len(n) < 2:
                        continue
                    if re.search(r"\b" + re.escape(n) + r"\b", chunk_text, flags=re.IGNORECASE):
                        present.append(c.canonical_name)
                        break

            present = list(dict.fromkeys(present))  # stable dedupe
            if not present:
                continue

            # Extract facts from each sub-chunk
            all_facts: list[dict] = []
            for sub_start, sub_end in sub_chunks:
                sub_text = chunk_text[sub_start:sub_end]
                sub_abs_start = ch.start_position + sub_start
                
                facts = self.extract_chunk_character_facts(
                    chunk_text=sub_text,
                    chunk_start=sub_abs_start,
                    character_names=present,
                    max_tokens=1200,
                )
                all_facts.extend(facts)
            
            facts = all_facts
            for entry in facts:
                name = entry.get("name")
                if not isinstance(name, str):
                    continue
                target = name_to_char.get(name.lower())
                if not target:
                    continue

                for f in entry.get("facts", []) if isinstance(entry.get("facts"), list) else []:
                    if not isinstance(f, dict):
                        continue
                    f2 = dict(f)
                    f2["chunk"] = ch.title or f"Chapter {ch.index}"
                    evidence_map[target.canonical_name].append(f2)

                for r in entry.get("relationships", []) if isinstance(entry.get("relationships"), list) else []:
                    if not isinstance(r, dict):
                        continue
                    r2 = dict(r)
                    r2["type"] = "relationship"
                    r2["chunk"] = ch.title or f"Chapter {ch.index}"
                    evidence_map[target.canonical_name].append(r2)

        # Attach evidence and apply deterministic alias merges based on surnames and explicit alias claims.
        for c in characters:
            c.evidence = evidence_map.get(c.canonical_name, [])

        # Deterministic merge: if a single-token canonical matches the last token of a multi-token canonical,
        # merge the single-token entry into the multi-token entry.
        by_name = {c.canonical_name: c for c in characters}
        singletons = [c for c in characters if len(c.canonical_name.split()) == 1]
        multi = [c for c in characters if len(c.canonical_name.split()) > 1]
        merged_into: dict[str, str] = {}
        for s in singletons:
            s_name = s.canonical_name.strip()
            for m in multi:
                last = m.canonical_name.split()[-1]
                if s_name.lower() == last.lower():
                    merged_into[s.canonical_name] = m.canonical_name
                    break

        if merged_into:
            new_chars: dict[str, Character] = {}
            for c in characters:
                target_name = merged_into.get(c.canonical_name, c.canonical_name)
                if target_name not in new_chars:
                    new_chars[target_name] = c
                    new_chars[target_name].canonical_name = target_name
                else:
                    tgt = new_chars[target_name]
                    tgt.mention_count += c.mention_count
                    tgt.aliases = list(set(tgt.aliases + [c.canonical_name] + c.aliases))
                    tgt.evidence = tgt.evidence + c.evidence
            # Re-sort
            characters = list(new_chars.values())
            characters.sort(key=lambda c: c.mention_count, reverse=True)
            sorted_chars = sorted(characters, key=lambda c: c.mention_count, reverse=True)

        # Calculate context limits based on model context length
        major_char_context = self._context_chars("character_profile")
        minor_char_context = major_char_context // 3  # Minor characters get 1/3 the budget

        for char in characters[:max_chars]:
            # Gather passages mentioning this character (paragraph-based with adjacent context)
            # Scale context budget by character importance to avoid major characters (with many mentions)
            # being dominated by early/low-signal passages.
            is_major = sorted_chars.index(char) < 3
            excerpts = self._gather_character_excerpts(
                text,
                char,
                paragraphs_before_after=1,
                max_passages=50 if is_major else 30,
                max_context_chars=major_char_context if is_major else minor_char_context,
            )

            if not excerpts:
                continue

            # Format relationship info if available
            rel_info = "None identified"
            if char.relationships:
                rel_parts = [f"{other}: {rel}" for other, rel in char.relationships.items()]
                rel_info = ", ".join(rel_parts)

            # Determine character importance rank for length scaling
            char_rank = sorted_chars.index(char)
            if char_rank < 3:
                length_instruction = "This is a MAJOR character. Write a detailed profile (4-5 paragraphs)."
                max_tokens = 1000
            elif char_rank < 10:
                length_instruction = "This is a supporting character. Write a moderate profile (2-3 paragraphs)."
                max_tokens = 700
            else:
                length_instruction = "This is a minor character. Write a brief profile (1-2 short paragraphs)."
                max_tokens = 400

            prompt = f"""Create a narrator's character profile for "{char.canonical_name}".

TEXT PASSAGES (this is your ONLY source of information):
{excerpts}

Known aliases: {', '.join(char.aliases) if char.aliases else 'None'}
Mention count: {char.mention_count}
Known relationships: {rel_info}

{length_instruction}

RULES:
- ONLY include details that appear in the passages above
- Quote the text when describing appearance, occupation, or key traits
- If the passages don't describe physical appearance, skip that section
- If occupation/role isn't stated, don't guess at it
- Focus on: how they speak (quote dialogue), how they act, their relationships

Structure your response with these sections (skip any section where the text provides no information):
- **Appearance**: [only if described in passages]
- **Personality & Behavior**: [based on their actions in the passages]
- **Speech & Voice**: [based on their dialogue, quote examples]
- **Role & Relationships**: [only what's explicitly shown]"""

            print(f"      Generating profile for {char.canonical_name}...")

            # Prefer evidence-based generation (more structured and debuggable)
            if char.evidence:
                evidence_payload = json.dumps(char.evidence[:80], indent=2)
                ev_prompt = f"""Write a narrator's character profile for "{char.canonical_name}" using ONLY the evidence JSON below.

EVIDENCE JSON (each entry contains quotes from the book):
{evidence_payload}

{length_instruction}

REQUIREMENTS - CRITICAL:
1. Write in FLOWING PROSE PARAGRAPHS - absolutely NO bullet points or lists
2. Synthesize the evidence into cohesive paragraphs
3. Use phrases like "is described as", "speaks with", "characterized by"
4. Include direct quotes naturally within sentences

FORBIDDEN - DO NOT USE:
- Lines starting with "- " or "• " or "* "
- Bullet points of any kind
- Lists or enumeration
- Quote dumps without synthesis

Write flowing prose paragraphs describing the character:"""
                response = self._query(ev_prompt, system=system, max_tokens=max_tokens)
            else:
                # Fallback to excerpt-based if no evidence (minor characters)
                response = self._query(prompt, system=system, max_tokens=max_tokens)

            if not response or not response.strip():
                print(f"      ⚠️  Empty profile returned for {char.canonical_name}")
                continue

            # Clean any thinking tags (e.g., from Qwen3 models)
            cleaned_response = self._clean_thinking_tags(response)

            if not cleaned_response:
                print(f"      ⚠️  Profile was only thinking tags for {char.canonical_name}")
                continue

            # VALIDATION: Check for bullet lists (indicates failed synthesis)
            lines = cleaned_response.split('\n')
            bullet_lines = sum(1 for line in lines if line.strip().startswith(('-', '•', '*')) and len(line.strip()) > 2)

            if bullet_lines > 3:
                # For now, warn but continue - we may want to make this an error in strict mode
                print(f"      ⚠️  Profile for {char.canonical_name} has {bullet_lines} bullet lines (expected prose)")
                # Raise error for major characters
                if char_rank < 3:
                    raise CharacterProfileError(
                        f"Profile for major character '{char.canonical_name}' contains {bullet_lines} bullet points.\n"
                        f"Expected synthesized prose paragraphs.\n"
                        f"First 500 chars of response:\n{cleaned_response[:500]}"
                    )

            # Replace with LLM-generated profile
            char.descriptions = [CharacterDescription(
                text=cleaned_response,
                source_position=0,
                confidence=ConfidenceLevel.LLM_REFINED,
            )]

        return characters

    def _gather_character_excerpts(
        self,
        text: str,
        char: Character,
        paragraphs_before_after: int = 1,
        max_passages: int = 30,
        max_context_chars: int = 32000,
    ) -> str:
        """
        Gather text passages mentioning a character.

        Args:
            text: Full book text
            char: Character to search for
            paragraphs_before_after: Number of adjacent paragraphs to include before/after a match
            max_passages: Maximum number of passages to include (safety cap)
            max_context_chars: Approximate maximum total characters to include across passages

        Returns:
            Formatted string of passages
        """
        if max_context_chars <= 0 or max_passages <= 0:
            return ""

        passages: list[str] = []
        names_to_search: list[str] = [char.canonical_name] + char.aliases

        # Also add individual parts of the canonical name (e.g., "Daisy" from "Daisy Buchanan")
        # This handles cases where the full name never appears but first/last name does
        canonical_parts = char.canonical_name.split()
        if len(canonical_parts) > 1:
            for part in canonical_parts:
                if len(part) > 2 and part.lower() not in [n.lower() for n in names_to_search]:
                    names_to_search.append(part)

        paragraph_spans = self._iter_paragraph_spans(text)
        if not paragraph_spans:
            return ""

        # Find paragraph indices containing any name/alias, then include adjacent paragraphs.
        matched_indices: set[int] = set()
        for name in names_to_search:
            # Use word boundaries to avoid partial matches
            name_re = re.compile(r"\b" + re.escape(name) + r"\b", flags=re.IGNORECASE)
            for idx, (_start, _end, para) in enumerate(paragraph_spans):
                if name_re.search(para):
                    lo = max(0, idx - paragraphs_before_after)
                    hi = min(len(paragraph_spans) - 1, idx + paragraphs_before_after)
                    for j in range(lo, hi + 1):
                        matched_indices.add(j)

        if not matched_indices:
            return ""

        ordered_indices = sorted(matched_indices)
        seen_norm: set[str] = set()
        total_chars = 0

        # Heuristic ranking: prioritize passages likely to contain descriptive information
        # (appearance/voice cues, "looked/seemed", etc.) rather than simply taking the earliest matches.
        appearance_keywords = {
            "eyes", "hair", "face", "smile", "voice", "looked", "seemed", "appeared",
            "dressed", "wearing", "suit", "hat", "hands", "skin", "tall", "short",
            "slender", "broad", "young", "old", "pale", "dark", "blond", "grey", "gray",
        }

        scored: list[tuple[int, int, str]] = []  # (score, idx, cleaned)
        for idx in ordered_indices:
            _start, _end, para = paragraph_spans[idx]
            cleaned = " ".join(para.split())
            if len(cleaned) < 40:
                continue
            lower = cleaned.lower()
            score = 0
            # Dialogue often contains what others say about a character
            if '"' in cleaned or "“" in cleaned or "”" in cleaned:
                score += 2
            # Keyword hits
            hits = sum(1 for kw in appearance_keywords if kw in lower)
            score += min(6, hits)
            # Prefer mid/late descriptive beats too (slight bias toward later passages)
            score += min(2, idx // 500)  # very small bump; stable across books
            scored.append((score, idx, cleaned))

        # Sort by score desc, then by idx asc for determinism
        scored.sort(key=lambda t: (-t[0], t[1]))

        # Select top passages under caps, then re-sort to restore narrative order
        selected: list[tuple[int, str]] = []
        for score, idx, cleaned in scored:
            if len(selected) >= max_passages:
                break
            norm = cleaned.lower()
            if norm in seen_norm:
                continue
            if total_chars + len(cleaned) > max_context_chars:
                continue
            seen_norm.add(norm)
            selected.append((idx, cleaned))
            total_chars += len(cleaned)

        # If ranked selection produced nothing, use earliest passages in order
        # (This can happen with very strict context caps)
        if not selected:
            for idx in ordered_indices:
                if len(selected) >= max_passages:
                    break
                _start, _end, para = paragraph_spans[idx]
                cleaned = " ".join(para.split())
                if len(cleaned) < 40:
                    continue
                norm = cleaned.lower()
                if norm in seen_norm:
                    continue
                if total_chars + len(cleaned) > max_context_chars:
                    break
                seen_norm.add(norm)
                selected.append((idx, cleaned))
                total_chars += len(cleaned)

        selected.sort(key=lambda t: t[0])

        for _idx, cleaned in selected:
            if len(passages) >= max_passages:
                break

            passages.append(cleaned)

        if not passages:
            return ""

        formatted = []
        for i, p in enumerate(passages, 1):
            formatted.append(f"{i}. \"{p}\"")

        return "\n".join(formatted)


def refine_analysis(
    result: AnalysisResult,
    text: str,
    refiner: Optional[LLMRefiner] = None,
    skip_chapter_detection: bool = False,
    skip_chapter_summaries: bool = False,
    skip_pronunciation_filter: bool = False,
    skip_character_merge: bool = False,
    skip_relationships: bool = False,
    skip_character_enrichment: bool = False,
    skip_homographs: bool = False,
    words_per_minute: int = 150,
    verbose: bool = True,
) -> RefinementStats:
    """
    Apply LLM refinement to an analysis result (mutates in place).

    Args:
        result: AnalysisResult object to refine
        text: Full book text
        refiner: LLMRefiner instance (creates default if None)
        skip_chapter_detection: Skip LLM-based chapter detection
        skip_chapter_summaries: Skip LLM-generated chapter summaries
        skip_pronunciation_filter: Skip filtering false positive pronunciations
        skip_character_merge: Skip character alias merging
        skip_relationships: Skip relationship extraction
        skip_character_enrichment: Skip LLM-generated character profiles
        skip_homographs: Skip homograph disambiguation
        words_per_minute: WPM for duration calculations
        verbose: Print progress messages

    Returns:
        RefinementStats with counts of changes made
    """
    if refiner is None:
        refiner = LLMRefiner()

    stats = RefinementStats()

    if verbose:
        print(f"   Running LLM refinement with {refiner.model}...")

    # 0. LLM-based chapter detection
    # Note: detect_chapters() raises ChapterDetectionError on failure (no fallbacks)
    # An empty list means the book has no chapters (valid for continuous prose)
    if not skip_chapter_detection:
        if verbose:
            print("   Detecting chapters with LLM...")
        chapters = refiner.detect_chapters(text, words_per_minute=words_per_minute)

        if chapters:
            # Replace regex-detected structure with LLM-detected chapters
            # Keep non-chapter elements from regex detection
            non_chapters = [e for e in result.structure if e.type != StructureType.CHAPTER]
            result.structure = chapters + non_chapters
            result.structure.sort(key=lambda e: e.start_position)
            stats.chapters_detected = len(chapters)

            # Recalculate total duration based on chapters
            result.metadata.estimated_total_duration_minutes = sum(
                ch.estimated_duration_minutes for ch in chapters
            )

            # Update character first_appearance_chapter with new chapter boundaries
            for char in result.characters:
                # Find earliest mention position for this character
                # We need to search the text for the character's name
                first_pos = None
                for name in [char.canonical_name] + char.aliases:
                    pattern = r'\b' + re.escape(name) + r'\b'
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        pos = match.start()
                        if first_pos is None or pos < first_pos:
                            first_pos = pos

                if first_pos is not None:
                    # Find which chapter this position falls in
                    for ch in chapters:
                        if ch.start_position <= first_pos < ch.end_position:
                            char.first_appearance_chapter = ch.index
                            break

            if verbose:
                print(f"   Detected {len(chapters)} chapters via LLM")

    # 0b. Generate chapter summaries
    if not skip_chapter_summaries:
        chapters = [e for e in result.structure if e.type == StructureType.CHAPTER]
        if chapters:
            if verbose:
                print(f"   Generating chapter summaries for {len(chapters)} chapters...")
            refiner.generate_chapter_summaries(chapters, text)
            stats.chapter_summaries_generated = sum(1 for ch in chapters if ch.summary)
            if verbose:
                print(f"   Generated {stats.chapter_summaries_generated} chapter summaries")

    # 1. Filter false positive pronunciations
    if not skip_pronunciation_filter:
        if verbose:
            print("   Filtering pronunciation false positives...")
        original_count = len(result.pronunciations)
        result.pronunciations = refiner.filter_false_positives(result.pronunciations)
        stats.pronunciations_removed = original_count - len(result.pronunciations)

    # 2. Resolve character aliases
    if not skip_character_merge:
        if verbose:
            print("   Resolving character aliases...")
        original_count = len(result.characters)
        result.characters = refiner.resolve_character_aliases(result.characters, text)
        stats.characters_merged = original_count - len(result.characters)

    # 3. Extract relationships
    if not skip_relationships:
        if verbose:
            print("   Extracting character relationships...")
        relationships = refiner.extract_relationships(result.characters, text)

        for char in result.characters:
            if char.canonical_name in relationships:
                char.relationships = relationships[char.canonical_name]
                stats.relationships_added += len(char.relationships)

    # 4. Enrich character descriptions with comprehensive profiles
    if not skip_character_enrichment:
        if verbose:
            print("   Generating character profiles...")
        original_chars = len(result.characters)
        result.characters = refiner.enrich_character_descriptions(result.characters, text, structure=result.structure)
        stats.character_profiles_generated = sum(
            1 for c in result.characters
            if c.descriptions and c.descriptions[0].confidence == ConfidenceLevel.LLM_REFINED
        )
        if verbose:
            print(f"   Generated {stats.character_profiles_generated} character profiles")

    # 5. Disambiguate homographs
    if not skip_homographs:
        if verbose:
            print("   Disambiguating homographs...")
        homograph_count = sum(1 for p in result.pronunciations if p.flag_reason == PronunciationFlag.HOMOGRAPH)
        result.pronunciations = refiner.disambiguate_homographs(result.pronunciations, text)
        stats.homographs_resolved = homograph_count

    if verbose:
        print(f"   LLM refinement complete:")
        if stats.chapters_detected > 0:
            print(f"      - Detected {stats.chapters_detected} chapters")
        if stats.chapter_summaries_generated > 0:
            print(f"      - Generated {stats.chapter_summaries_generated} chapter summaries")
        print(f"      - Removed {stats.pronunciations_removed} false positive pronunciations")
        print(f"      - Merged {stats.characters_merged} character aliases")
        print(f"      - Added {stats.relationships_added} character relationships")
        if stats.character_profiles_generated > 0:
            print(f"      - Generated {stats.character_profiles_generated} character profiles")
        print(f"      - Resolved {stats.homographs_resolved} homographs")

    return stats
