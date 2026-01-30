from dataclasses import dataclass, field

from src.analyzer import AudiobookAnalyzer
from src.llm.client import LLMResponse


@dataclass
class FakeChar:
    canonical_name: str
    aliases: list[str] = field(default_factory=list)


class FakeLLM:
    def __init__(self, content: str):
        self._content = content

    def query(self, prompt, system=None, json_mode=False, temperature=None, max_tokens=None):
        # Minimal stub that returns a JSON string payload
        return LLMResponse(content=self._content, model="fake")

    def _extract_json(self, text: str):
        import json
        return json.loads(text)


def test_extract_relationships_llm_normalizes_alias_to_canonical():
    analyzer = AudiobookAnalyzer()

    # Evidence contains relationship; LLM returns alias key ("Johnny") instead of canonical.
    fake_llm = FakeLLM('{"Johnny":"nephew","John Donaldson":"father"}')

    all_chars = [
        FakeChar("John", aliases=["Johnny"]),
        FakeChar("John Donaldson", aliases=["Mr. Donaldson"]),
        FakeChar("Uncle Bill", aliases=["Bill"]),
    ]

    out = analyzer._extract_relationships_llm(
        llm=fake_llm,
        validated_evidence=[{"statement": "My nephew Johnny wrote a note.", "quote": "my nephew Johnny", "position": 1}],
        all_characters=all_chars,
        current_character_name="Uncle Bill",
    )

    # Alias key should normalize to canonical "John"
    assert out.get("John") == "nephew"
    assert out.get("John Donaldson") == "father"
