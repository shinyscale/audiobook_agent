"""
Pytest fixtures for audiobook analysis tests.

Provides common fixtures for test corpus loading, ground truth access,
and mock LLM clients.

To run integration tests (require LLM):
    pytest tests/ -v --run-integration

To run only fast tests:
    pytest tests/ -v -m "not slow"
"""

import json
import pytest
from pathlib import Path
from typing import Optional


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests that require LLM",
    )


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires LLM)"
    )


def pytest_collection_modifyitems(config, items):
    """Skip integration tests unless --run-integration is passed."""
    if config.getoption("--run-integration"):
        # --run-integration given: don't skip integration tests
        return

    skip_integration = pytest.mark.skip(reason="Need --run-integration to run")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)


# Project root
PROJECT_ROOT = Path(__file__).parent.parent

# Default model for integration tests
# Using qwen2.5:32b as it's a reliable non-reasoning model
# qwen3 instruct models are also good but may need model-specific configuration
DEFAULT_TEST_MODEL = "qwen2.5:32b"  # Reliable for testing
# Alternatives: "qwen3:14b", "qwen3:32b", "qwen2.5:14b"


@pytest.fixture
def test_model() -> str:
    """Return the model to use for integration tests."""
    return DEFAULT_TEST_MODEL


@pytest.fixture
def analyzer_with_llm(test_model):
    """Create an analyzer configured with the test LLM model."""
    from src.analyzer import AudiobookAnalyzer
    from src.agents.config import OrchestratorConfig

    # Use OrchestratorConfig to ensure context_length is properly set
    config = OrchestratorConfig(
        default_model=test_model,
        default_provider="ollama",
        context_length=32768,
    )

    return AudiobookAnalyzer(
        llm_refine=True,
        llm_model=test_model,
        llm_provider="ollama",
        llm_context_length=32768,
        orchestrator_config=config,
    )


@pytest.fixture
def test_texts_dir() -> Path:
    """Path to test texts directory."""
    return PROJECT_ROOT / "Test_Texts"


@pytest.fixture
def ai_dir() -> Path:
    """Path to ai harness directory."""
    return PROJECT_ROOT / "ai"


@pytest.fixture
def ground_truth_dir(ai_dir) -> Path:
    """Path to ground truth files."""
    return ai_dir / "ground_truth"


@pytest.fixture
def gatsby_text(test_texts_dir) -> str:
    """Load Gatsby text."""
    path = test_texts_dir / "gatsby.txt"
    if not path.exists():
        pytest.skip("gatsby.txt not found in Test_Texts/")
    return path.read_text()


@pytest.fixture
def frankenstein_text(test_texts_dir) -> str:
    """Load Frankenstein text."""
    path = test_texts_dir / "frankenstein.txt"
    if not path.exists():
        pytest.skip("frankenstein.txt not found in Test_Texts/")
    return path.read_text()


@pytest.fixture
def gatsby_chapters_ground_truth(ground_truth_dir) -> dict:
    """Load Gatsby chapters ground truth."""
    path = ground_truth_dir / "gatsby_chapters.json"
    if not path.exists():
        pytest.skip("gatsby_chapters.json not found")
    return json.loads(path.read_text())


@pytest.fixture
def gatsby_characters_ground_truth(ground_truth_dir) -> dict:
    """Load Gatsby characters ground truth."""
    path = ground_truth_dir / "gatsby_characters.json"
    if not path.exists():
        pytest.skip("gatsby_characters.json not found")
    return json.loads(path.read_text())


@pytest.fixture
def frankenstein_chapters_ground_truth(ground_truth_dir) -> dict:
    """Load Frankenstein chapters ground truth."""
    path = ground_truth_dir / "frankenstein_chapters.json"
    if not path.exists():
        pytest.skip("frankenstein_chapters.json not found")
    return json.loads(path.read_text())


@pytest.fixture
def frankenstein_characters_ground_truth(ground_truth_dir) -> dict:
    """Load Frankenstein characters ground truth."""
    path = ground_truth_dir / "frankenstein_characters.json"
    if not path.exists():
        pytest.skip("frankenstein_characters.json not found")
    return json.loads(path.read_text())


@pytest.fixture
def feature_list(ai_dir) -> dict:
    """Load feature list for status tracking."""
    path = ai_dir / "feature_list.json"
    if not path.exists():
        pytest.skip("feature_list.json not found")
    return json.loads(path.read_text())


class MockLLMResponse:
    """Mock LLM response for testing without actual LLM calls."""

    def __init__(self, content: str, success: bool = True, error: Optional[str] = None):
        self.content = content
        self.success = success
        self.error = error
        self.usage = {"total_tokens": 100}


class MockLLMClient:
    """Mock LLM client for testing without Ollama."""

    def __init__(self, responses: Optional[dict] = None):
        self.responses = responses or {}
        self.calls = []

    def generate(self, prompt: str, system: Optional[str] = None) -> MockLLMResponse:
        """Mock generate method."""
        self.calls.append({"prompt": prompt, "system": system})

        # Return canned response if configured
        for key, response in self.responses.items():
            if key in prompt:
                return MockLLMResponse(response)

        # Default response
        return MockLLMResponse("Mock response")

    def query_json(self, prompt: str, system: Optional[str] = None) -> tuple:
        """Mock JSON query method."""
        self.calls.append({"prompt": prompt, "system": system, "json": True})

        # Return canned JSON response if configured
        for key, response in self.responses.items():
            if key in prompt:
                if isinstance(response, (dict, list)):
                    return response, MockLLMResponse(json.dumps(response))
                return json.loads(response), MockLLMResponse(response)

        # Default response
        return {}, MockLLMResponse("{}")


@pytest.fixture
def mock_llm():
    """Create a mock LLM client."""
    return MockLLMClient()


@pytest.fixture
def mock_llm_with_chapters():
    """Create a mock LLM client configured for chapter detection."""
    return MockLLMClient(responses={
        "chapter": json.dumps({
            "chapters": [
                {"index": 1, "title": "Chapter I", "confidence": 0.9},
                {"index": 2, "title": "Chapter II", "confidence": 0.9},
            ]
        })
    })
