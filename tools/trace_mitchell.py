#!/usr/bin/env python3
"""One-off replay trace: why did Mike Mitchell vanish from the 2026-06-11 run?

Re-runs ONLY the character stage from cached summaries with DEBUG logging,
using the same model as the full run.
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s %(name)s - %(message)s",
    filename="/tmp/mitchell_trace.log",
    filemode="w",
)
console = logging.StreamHandler()
console.setLevel(logging.WARNING)
logging.getLogger().addHandler(console)

from src.agents.base import AgentContext  # noqa: E402
from src.agents.characters import CharacterAgent  # noqa: E402
from src.ingestion import get_ingester  # noqa: E402
from src.ingestion.refine import refine_extracted_document  # noqa: E402
from src.ingestion.regions import RegionType  # noqa: E402
from src.llm.client import LLMClient, LLMConfig  # noqa: E402
from src.pipeline.chapter_detection.models import ChapterMap  # noqa: E402
from src.pipeline.chapter_summary.models import ChapterSummaryMap  # noqa: E402
from src.pipeline.stage_cache import StageCache  # noqa: E402

PDF = "see_the_light_final.pdf"
MODEL = "qwen3-next:80b-a3b-instruct-q8_0"

print("1) ingest + refine (no LLM)...", flush=True)
ingester = get_ingester(Path(PDF))
doc = ingester.extract(Path(PDF))
doc = refine_extracted_document(doc)
print(f"   text: {len(doc.text)} chars; Mitchell occurrences: {doc.text.count('Mitchell')}", flush=True)

body_range = None
if doc.regions:
    body = [r for r in doc.regions if r.region_type == RegionType.BODY]
    if body:
        body_range = (body[0].start_position, body[0].end_position)
print(f"   body_range: {body_range}", flush=True)

print("2) load cached stage artifacts...", flush=True)
cache = StageCache("output/stage_cache")
summaries = ChapterSummaryMap.from_dict(cache.latest("see_the_light_final", "summaries"))
ch = cache.latest("see_the_light_final", "chapters")
chapter_map = ChapterMap.from_dict(ch) if ch else None
print(f"   {len(summaries.summaries)} summaries, chapters: {bool(chapter_map)}", flush=True)

print(f"3) run character stage with {MODEL} (DEBUG -> /tmp/mitchell_trace.log)...", flush=True)
agent = CharacterAgent(llm_client=LLMClient(LLMConfig.ollama(model=MODEL)))
context = AgentContext(
    text=doc.text,
    source_file=PDF,
    chapter_map=chapter_map,
    previous_results={"summaries": summaries},
    metadata={"body_range": body_range},
)
result = agent.run(context)
chars = list(result.data.characters)

print(f"\n=== {len(chars)} characters ===", flush=True)
mitchells = [c for c in chars if "mitchell" in c.canonical_name.lower()
             or any("mitchell" in a.lower() for a in (c.aliases or []))]
for c in mitchells:
    print(f"  MITCHELL-RELATED: {c.canonical_name} role={getattr(c,'role','?')} "
          f"mentions={getattr(c,'mention_count',0)} aliases={list(c.aliases or [])}", flush=True)
if not mitchells:
    print("  NO Mitchell-related characters in final output", flush=True)
narr = getattr(result.data, "narrator_character_id", None)
byid = {c.id: c.canonical_name for c in chars}
print(f"  narrator: {byid.get(narr)}", flush=True)
