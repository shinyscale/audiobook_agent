#!/usr/bin/env python3
"""
Quick test script to verify chapter detection fixes.
Tests just the structure detection without running full analysis pipeline.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ingestion import get_ingester, refine_extracted_document
from agents.structure import StructureAgent
from agents.config import AgentConfig, AgentContext
from pipeline.llm import LLMClient, LLMConfig

def test_chapter_detection(file_path: str, model: str = "qwen3:8b"):
    """Test chapter detection on a single file."""
    print(f"📖 Testing chapter detection on: {file_path}")
    print(f"🤖 Using model: {model}\n")

    # Ingest file
    print("1. Ingesting file...")
    ingester = get_ingester(Path(file_path))
    doc_result = ingester.ingest(Path(file_path))
    text = doc_result.text
    print(f"   ✓ Extracted {len(text.split())} words\n")

    # Refine text
    print("2. Refining text...")
    refined_doc = refine_extracted_document(doc_result)
    refined = refined_doc.text
    print(f"   ✓ Refined to {len(refined.split())} words\n")

    # Run structure agent
    print("3. Running StructureAgent...")
    llm_client = LLMClient(LLMConfig.ollama(model=model))
    agent_config = AgentConfig(model=model)

    context = AgentContext(
        text=refined,
        metadata={"source": file_path},
        llm_client=llm_client,
        agent_config=agent_config
    )

    agent = StructureAgent()
    result = agent.run(context)

    # Display results
    print(f"\n{'='*60}")
    print(f"RESULTS: {len(result.data.chapters)} chapters detected")
    print(f"{'='*60}\n")

    for i, chapter in enumerate(result.data.chapters, 1):
        title = chapter.title or f"Chapter {i}"
        print(f"Chapter {i}: {title}")
        print(f"  Position: {chapter.position}")
        print(f"  Words: {chapter.word_count}")
        print(f"  Confidence: {chapter.confidence}")
        print()

    return result.data

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_chapter_fix.py <file_path> [model]")
        sys.exit(1)

    file_path = sys.argv[1]
    model = sys.argv[2] if len(sys.argv) > 2 else "qwen3:8b"

    result = test_chapter_detection(file_path, model)
    print(f"\n✅ Test complete: {len(result.chapters)} chapters detected")
    print(f"Expected for Gatsby: 9 chapters (was 14 before fix)")
