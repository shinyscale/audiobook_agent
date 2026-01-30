"""
Diagnostic script to test main cast extraction on i_have_no_mouth.

This will help us understand if the LLM is failing to extract AM,
or if it's being filtered out by post-processing.
"""

import json
import sys
sys.path.insert(0, '/home/zacharymandrews/Tools/audiobook_agent')

from src.llm.client import LLMClient, LLMConfig
from src.pipeline.character_extraction_v2.main_cast import MainCastExtractor

# Load analysis.json to get the summary
with open('../output/i_have_no_mouth/analysis.json', 'r') as f:
    analysis = json.load(f)

# Get chapter summary
chapter_summaries = [analysis['structure'][0]['summary']]

print("=" * 80)
print("CHAPTER SUMMARY:")
print("=" * 80)
print(chapter_summaries[0])
print("\n")

# Initialize LLM
config = analysis['_config']['agents']['characters']
llm_config = LLMConfig.ollama(
    model=config['model']
)
llm_client = LLMClient(llm_config)

# Run main cast extraction
print("=" * 80)
print("RUNNING MAIN CAST EXTRACTION...")
print("=" * 80)

extractor = MainCastExtractor(llm_client)

# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Manual Pass 1 to see raw response
from src.pipeline.character_extraction_v2.main_cast import CHARACTER_IDENTIFICATION_PROMPT

summaries_text = f"Chapter 1:\n{chapter_summaries[0]}"
pass1_prompt = CHARACTER_IDENTIFICATION_PROMPT.format(
    summaries=summaries_text,
    plot_summary_section=""
)

print("=" * 80)
print("PASS 1 PROMPT (first 500 chars):")
print("=" * 80)
print(pass1_prompt[:500])
print("\n")

result, response = llm_client.query_json(pass1_prompt)

print("=" * 80)
print("PASS 1 LLM RESPONSE:")
print("=" * 80)
print(f"Success: {response.success}")
print(f"Error: {response.error}")
print(f"Result type: {type(result)}")
print(f"Result: {result}")
print("\n")

profiles = extractor.extract(chapter_summaries, use_two_pass=True)

print(f"\nExtracted {len(profiles)} main cast profiles:")
print("=" * 80)

for p in profiles:
    print(f"\nCanonical: {p.canonical_name}")
    print(f"Role: {p.role}")
    print(f"Aliases: {p.aliases}")
    print(f"is_symbolic: {p.is_symbolic}")
    print(f"Description: {p.description[:100]}...")

print("\n")
print("=" * 80)
print("CHECKING FOR AM:")
print("=" * 80)

am_found = any('AM' in p.canonical_name.upper() or
               any('AM' in a.upper() for a in p.aliases)
               for p in profiles)

if am_found:
    print("✓ AM WAS EXTRACTED by the LLM")
    am_profile = next((p for p in profiles if 'AM' in p.canonical_name.upper()), None)
    if am_profile:
        print(f"  Role assigned: {am_profile.role}")
        print(f"  Would be filtered: {'device' in am_profile.role.lower() or 'object' in am_profile.role.lower()}")
else:
    print("✗ AM WAS NOT EXTRACTED by the LLM")
    print("\nThe prompt failed to make the LLM extract AM despite:")
    print("  - Summary mentioning 'AM, a sentient, malevolent supercomputer'")
    print("  - Prompt saying 'Include plot-central people/creatures AND symbolic objects/forces'")
    print("\nThis is a PROMPT ISSUE, not a filtering issue.")
