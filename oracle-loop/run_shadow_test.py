#!/usr/bin/env python3
"""
Run character extraction on a test text with shadow mode logging enabled.
Shows the identity graph shadow comparison output.
"""

import sys
import os
import logging
import json

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ingestion import get_ingester, refine_extracted_document
from src.agents.characters import CharacterAgent
from src.agents.base import AgentContext
from src.agents.config import AgentConfig
from src.llm.client import LLMClient, LLMConfig

# Configure logging — show identity graph shadow mode output
logging.basicConfig(
    level=logging.WARNING,
    format='%(name)s | %(message)s',
    handlers=[logging.StreamHandler()]
)

# Enable INFO for identity graph and character agent shadow mode
logging.getLogger('src.pipeline.character_extraction_v2.identity_graph').setLevel(logging.INFO)
logging.getLogger('src.pipeline.character_extraction_v2.evidence_collectors').setLevel(logging.INFO)
logging.getLogger('src.agents.characters').setLevel(logging.INFO)

def main():
    text_name = sys.argv[1] if len(sys.argv) > 1 else "The_Monkey's_Paw"
    text_dir = "/home/zacharymandrews/Tools/audiobook_agent/Test_Texts"

    # Find the text file
    text_path = None
    for f in os.listdir(text_dir):
        if text_name.lower().replace(" ", "_") in f.lower().replace(" ", "_"):
            text_path = os.path.join(text_dir, f)
            break

    if not text_path or not os.path.exists(text_path):
        print(f"ERROR: Text not found matching '{text_name}' in {text_dir}")
        print(f"Available: {os.listdir(text_dir)}")
        sys.exit(1)

    print(f"=== Shadow Mode Test: {os.path.basename(text_path)} ===\n")

    # Ingest
    print("Loading text...")
    from pathlib import Path
    ingester = get_ingester(Path(text_path))
    doc = ingester.extract(Path(text_path))
    doc = refine_extracted_document(doc)
    print(f"Loaded: {len(doc.text)} chars\n")

    # Set up LLM client
    llm_config = LLMConfig.ollama(model="qwen3-next:80b-a3b-instruct-q8_0")
    llm_client = LLMClient(llm_config)

    # Set up agent
    agent = CharacterAgent(
        llm_client=llm_client,
        config=AgentConfig(
            model="qwen3-next:80b-a3b-instruct-q8_0",
            temperature=0.3,
            max_tokens=8192,
        ),
    )

    # Build context
    # We need structure and summaries first
    print("Running structure agent...")
    from src.agents.structure import StructureAgent
    structure_agent = StructureAgent(llm_client=llm_client)

    context = AgentContext(text=doc.text, chapter_map=None)
    structure_result = structure_agent.run(context)

    print(f"Found {len(structure_result.data.chapters)} chapters\n")

    print("Running summary agent...")
    from src.agents.summaries import SummaryAgent
    summary_agent = SummaryAgent(llm_client=llm_client)

    context = AgentContext(
        text=doc.text,
        chapter_map=structure_result.data,
        previous_results={"structure": structure_result.data},
    )
    summary_result = summary_agent.run(context)

    print(f"Generated {len(summary_result.data.summaries)} summaries\n")

    # Now run character extraction with shadow mode
    print("=" * 60)
    print("Running character extraction (with identity graph shadow mode)...")
    print("=" * 60 + "\n")

    context = AgentContext(
        text=doc.text,
        chapter_map=structure_result.data,
        previous_results={
            "structure": structure_result.data,
            "summaries": summary_result.data,
        },
    )

    char_result = agent.run(context)

    # Print results
    print("\n" + "=" * 60)
    print("FINAL CHARACTER RESULTS")
    print("=" * 60)

    for char in char_result.data.characters:
        cast = "MAIN" if char.role and char.role != "minor" else "SUPPORTING"
        print(f"\n  [{cast}] {char.canonical_name} ({char.mention_count} mentions)")
        if char.aliases:
            print(f"         Aliases: {char.aliases}")
        if char.is_narrator:
            print(f"         ** NARRATOR **")

    print(f"\nTotal: {len(char_result.data.characters)} characters")
    print(f"Processing time: {char_result.processing_time_seconds:.1f}s")

if __name__ == "__main__":
    main()
