#!/usr/bin/env python3
"""
Diagnostic script to understand why main_cast_count=0 in attempt 4.

Runs the character extraction pipeline in isolation with DEBUG logging.
"""

import sys
import logging
import json

# Set up DEBUG logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s [%(name)s] %(message)s"
)

# Add parent directory to path
sys.path.insert(0, "/home/zacharymandrews/Tools/audiobook_agent")

from src.pipeline.llm import LLMClient, LLMConfig
from src.agents.characters import CharacterAgent
from src.agents.base import AgentContext
from src.ingestion import ingest_document

# Load the text
print("Loading american_sir.txt...")
doc = ingest_document("../test_texts/american_sir.txt")
print(f"Loaded {len(doc.text)} characters")

# Create LLM client
print("\nInitializing LLM client...")
llm_config = LLMConfig.ollama(model="qwen3-next:80b-a3b-instruct-q8_0", temperature=0.7)
llm_client = LLMClient(llm_config)

# Load structure and summaries from analysis output
print("\nLoading structure and summaries from analysis output...")
with open("../output/american_sir/analysis.json") as f:
    analysis = json.load(f)

structure = analysis["structure"]
print(f"Loaded {len(structure)} structural elements")

# Create minimal context
context = AgentContext(
    text=doc.text,
    chapter_map=None,
    metadata={},
    previous_results={
        "structure": structure,
        # We need to reconstruct summaries from structure
    }
)

# Create character agent
print("\nCreating CharacterAgent...")
agent = CharacterAgent(llm_client=llm_client, min_grounding_mentions=3)

# Try to extract chapter_summaries the same way the agent does
print("\nExtracting chapter_summaries...")
chapter_summaries = []
for elem in structure:
    if elem.get("summary"):
        # Format like the agent does
        chars = elem.get("characters_present", [])
        if chars:
            char_list = ", ".join(chars)
            formatted = f"[Characters: {char_list}]\n{elem['summary']}"
        else:
            formatted = elem["summary"]
        chapter_summaries.append(formatted)
        print(f"  Section {elem.get('index', '?')}: {len(formatted)} chars, {len(chars)} characters_present")

print(f"\nTotal: {len(chapter_summaries)} summaries")

# Print first summary to verify format
print("\n=== First Summary ===")
print(chapter_summaries[0][:500] if chapter_summaries else "(none)")

print("\n=== Running character extraction agent ===")
print("NOTE: This will call the LLM. Watch for Step 1, Step 1.6, and Step 3 logging.")
print()

# We can't easily run the agent without a full context, so instead let's
# test the split method directly
from src.models import Character

# Create dummy characters to test the split logic
print("\n=== Testing _split_disambiguated_same_name_characters directly ===")
dummy_chars = [
    Character(
        id="test_0",
        canonical_name="John Donaldson",
        role="protagonist",
        aliases=[],
        mention_count=0,
    ),
    Character(
        id="test_1",
        canonical_name="Uncle Bill",
        role="protagonist",
        aliases=[],
        mention_count=0,
    ),
]

print(f"Input: {len(dummy_chars)} characters")
for c in dummy_chars:
    print(f"  - {c.canonical_name}")

print("\nCalling _split_disambiguated_same_name_characters with chapter_summaries...")
try:
    result = agent._split_disambiguated_same_name_characters(dummy_chars, chapter_summaries)
    print(f"Output: {len(result)} characters")
    for c in result:
        print(f"  - {c.canonical_name} (ID: {c.id})")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print("\n=== Done ===")
