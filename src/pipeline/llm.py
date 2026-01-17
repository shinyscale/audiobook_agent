"""
Backward-compatible shim for LLM client.

This module re-exports from src.llm.client for backward compatibility.
All new code should import directly from src.llm instead.
"""

# Re-export everything from the new location
from ..llm.client import LLMClient, LLMConfig, LLMResponse, create_client

__all__ = ["LLMClient", "LLMConfig", "LLMResponse", "create_client"]
