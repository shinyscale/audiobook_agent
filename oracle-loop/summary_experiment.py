#!/usr/bin/env python3
"""
Summary Generation Experiment

Tests ChapterSummarizer across multiple models on short stories with known content.
Evaluates both summary quality AND character list quality (the [Characters: ...] output).

Key insight: The character list in summaries feeds into MainCastExtractor, so
poor character lists here cause downstream failures in character extraction.

Usage:
    python oracle-loop/summary_experiment.py           # Run all models on all texts
    python oracle-loop/summary_experiment.py --quick   # Quick test: 2 models, 2 texts
    python oracle-loop/summary_experiment.py berenice  # Run all models on one text
    python oracle-loop/summary_experiment.py --resume  # Resume from crash, skip completed

Results saved to: oracle-loop/state/summary_results.json
"""

import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.llm.client import LLMClient, LLMConfig
from src.pipeline.chapter_detection.pipeline import ChapterDetectionPipeline
from src.pipeline.chapter_summary.summarizer import ChapterSummarizer
from src.pipeline.chapter_summary.models import ChapterSummary


# =============================================================================
# GROUND TRUTH - Expected content for each test text
# =============================================================================

EXPECTED_CONTENT = {
    "cask_of_amontillado": {
        # Characters that MUST appear in the character list
        "required_characters": ["Montresor", "Fortunato"],
        # Characters that should NOT appear (hallucinations, minor mentions)
        "forbidden_characters": ["Luchresi"],  # Only mentioned, never appears
        # Aliases that should be grouped (same person)
        "alias_groups": [
            # No complex aliases in this story
        ],
        # Key events that should be mentioned in summary
        "key_events": [
            "carnival",  # Setting is carnival season
            "catacombs",  # Goes to catacombs
            "wine",  # Amontillado wine is the lure
            "chain",  # Fortunato is chained
            "wall",  # Walled up alive
        ],
        # Things that should NOT be treated as characters
        "non_characters": ["Amontillado", "catacombs", "carnival"],
    },
    "gift_of_the_magi": {
        "required_characters": ["Della", "Jim"],
        "forbidden_characters": ["Queen of Sheba", "King Solomon"],  # Biblical allusions, not characters
        "alias_groups": [
            ["Jim", "James Dillingham Young"],  # Same person
            ["Della", "Mrs. James Dillingham Young"],  # Same person
        ],
        "key_events": [
            "hair",  # Della sells her hair
            "watch",  # Jim sells his watch
            "combs",  # Gift of combs
            "chain",  # Gift of watch chain
            "Christmas",  # It's Christmas
        ],
        "non_characters": ["combs", "watch", "chain", "flat"],
    },
    "monkeys_paw": {
        "required_characters": ["Mr. White", "Mrs. White", "Herbert", "Morris"],
        "forbidden_characters": [],
        "alias_groups": [
            ["Mr. White", "the old man", "father"],
            ["Mrs. White", "the old woman", "mother"],
            ["Herbert White", "Herbert"],
            ["Sergeant-Major Morris", "Morris", "the sergeant-major"],
        ],
        "key_events": [
            "paw",  # The monkey's paw
            "wish",  # Making wishes
            "200",  # 200 pounds compensation
            "machinery",  # Herbert caught in machinery
            "knock",  # Knocking at the door
        ],
        "non_characters": ["paw", "fire", "door"],
    },
    "berenice": {
        "required_characters": ["Egaeus", "Berenice"],
        "forbidden_characters": ["Mad'selle Salle"],  # Dancer mentioned in passing
        "alias_groups": [
            ["Egaeus", "the narrator"],
        ],
        "key_events": [
            "teeth",  # Obsession with teeth
            "library",  # Setting in library
            "illness",  # Berenice's illness
            "tomb",  # Violation of tomb
            "box",  # Box with teeth
        ],
        "non_characters": ["teeth", "library", "box"],
    },
    "masque_of_red_death": {
        "required_characters": ["Prince Prospero", "Red Death"],
        "forbidden_characters": [],
        "alias_groups": [
            ["Prince Prospero", "Prospero"],
            ["the Red Death", "Red Death", "the masked figure"],
        ],
        "key_events": [
            "plague",  # The Red Death plague
            "abbey",  # Castellated abbey
            "masquerade",  # Masquerade ball
            "rooms",  # Seven colored rooms
            "clock",  # Ebony clock
            "midnight",  # Strikes midnight
        ],
        "non_characters": ["clock", "abbey", "rooms"],
    },
    "i_have_no_mouth": {
        "required_characters": ["AM", "Ted", "Gorrister", "Benny", "Nimdok", "Ellen"],
        "forbidden_characters": [],
        "alias_groups": [
            ["AM", "the computer", "Allied Mastercomputer"],
            ["Ted", "the narrator"],
        ],
        "key_events": [
            "computer",  # AM is a computer
            "torture",  # Eternal torture
            "ice",  # Ice caverns
            "food",  # Canned food
            "kill",  # Ted kills the others
        ],
        "non_characters": ["ice", "caverns", "cans"],
    },
}


# =============================================================================
# MODELS TO TEST
# =============================================================================

MODELS = [
    # Small models
    "qwen2.5:7b",
    "qwen2.5:14b",
    "qwen3:14b",
    # Medium models
    "mistral-small3.2:24b",
    "qwen3:30b-instruct",
    "qwen2.5:32b",
    # Large models
    "qwen3-next:80b-a3b-instruct-q8_0",
    "gpt-oss:120b",
]


# =============================================================================
# TEST TEXTS
# =============================================================================

TEST_TEXTS = {
    "cask_of_amontillado": Path("/home/zacharymandrews/Tools/audiobook_agent/Test_Texts/The Cask of Amontillado - Poe.txt"),
    "gift_of_the_magi": Path("/home/zacharymandrews/Tools/audiobook_agent/Test_Texts/The Gift of the Magi - O_Henry.txt"),
    "monkeys_paw": Path("/home/zacharymandrews/Tools/audiobook_agent/Test_Texts/The_Monkey's_Paw.txt"),
    "berenice": Path("/home/zacharymandrews/Tools/audiobook_agent/Test_Texts/Berenice - Poe.txt"),
    "masque_of_red_death": Path("/home/zacharymandrews/Tools/audiobook_agent/Test_Texts/Masque of the Red Death - Poe.txt"),
    "i_have_no_mouth": Path("/home/zacharymandrews/Tools/audiobook_agent/Test_Texts/I_Have_No_Mouth_And_I_Must_Scream.pdf"),
}


# =============================================================================
# OUTPUT PATHS
# =============================================================================

OUTPUT_PATH = Path(__file__).parent / "state" / "summary_results.json"
STRUCTURE_CACHE_DIR = Path(__file__).parent / "state" / "structure_cache"


# =============================================================================
# STRUCTURE CACHING (chapters)
# =============================================================================

def get_structure_cache_path(text_name: str) -> Path:
    """Get the path to the cached structure file for a text."""
    return STRUCTURE_CACHE_DIR / f"{text_name}.json"


def load_cached_structure(text_name: str) -> Optional[list[dict]]:
    """Load cached chapter structure if it exists."""
    cache_path = get_structure_cache_path(text_name)
    if cache_path.exists():
        try:
            with open(cache_path) as f:
                data = json.load(f)
                return data.get("chapters", [])
        except (json.JSONDecodeError, IOError) as e:
            print(f"  Warning: Failed to load cached structure: {e}")
    return None


def save_structure_to_cache(text_name: str, chapters: list[dict]) -> None:
    """Save chapter structure to cache."""
    STRUCTURE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = get_structure_cache_path(text_name)

    data = {
        "text_name": text_name,
        "generated_at": datetime.now().isoformat(),
        "chapters": chapters,
    }

    with open(cache_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"  Cached {len(chapters)} chapters to {cache_path}")


def detect_chapters(text: str, text_name: str) -> list[dict]:
    """Detect chapters in text, using cache if available."""
    # Try to load from cache first
    cached = load_cached_structure(text_name)
    if cached:
        print(f"  Loaded {len(cached)} cached chapters")
        return cached

    # Detect chapters using deterministic pipeline (no LLM variance)
    print(f"  Detecting chapters...")
    pipeline = ChapterDetectionPipeline.deterministic_only()
    chapter_map = pipeline.run(text, source_file=text_name)

    if not chapter_map or not chapter_map.chapters:
        print(f"  No chapters detected, treating as single chapter")
        chapters = [{
            "index": 0,
            "title": "Full Text",
            "start": 0,
            "end": len(text),
        }]
    else:
        chapters = []
        for ch in chapter_map.chapters:
            chapters.append({
                "index": ch.index,
                "title": ch.title or f"Chapter {ch.index + 1}",
                "start": ch.start_position,
                "end": ch.end_position,
            })

    # Cache for future use
    save_structure_to_cache(text_name, chapters)
    return chapters


# =============================================================================
# MODEL PRE-WARMING (for large models like gpt-oss)
# =============================================================================

# Maximum retries for model loading
MAX_LOAD_RETRIES = 3
LOAD_RETRY_DELAY = 10  # seconds
LOAD_TIMEOUT = 120  # seconds - shorter timeout for load test (not 1200s inference timeout)


def load_model(model: str, base_url: str = "http://localhost:11434") -> tuple[bool, float, str]:
    """Load a model and measure the loading time.

    This serves two purposes:
    1. Ensures the model is fully loaded before analysis begins
    2. Measures the load/swap time as a separate metric

    Uses a direct httpx call with a shorter timeout (120s) instead of going
    through LLMClient which has a 1200s timeout for inference. This prevents
    20-minute hangs when model swaps fail.

    For models already loaded in Ollama, this will be very fast (~1s).
    For models that need to be swapped in, this captures the full swap time.

    Args:
        model: Model name
        base_url: Ollama base URL

    Returns:
        Tuple of (success, load_time_seconds, message)
    """
    import httpx

    print(f"  Loading model {model}...")

    load_start = time.time()
    last_error = None

    # Use shorter timeout for load test - 120s is plenty for model swap
    timeout = httpx.Timeout(connect=30.0, read=LOAD_TIMEOUT, write=30.0, pool=30.0)

    for attempt in range(MAX_LOAD_RETRIES):
        if attempt > 0:
            print(f"  Load retry {attempt}/{MAX_LOAD_RETRIES-1} after {LOAD_RETRY_DELAY}s delay...")
            time.sleep(LOAD_RETRY_DELAY)

        try:
            # Send a simple query directly to Ollama to force model load
            with httpx.Client(base_url=base_url, timeout=timeout) as client:
                response = client.post(
                    "/api/generate",
                    json={
                        "model": model,
                        "prompt": "Hello. Reply with just 'OK'.",
                        "stream": False,
                    },
                )

            load_time = time.time() - load_start

            if response.status_code == 200:
                print(f"  Model loaded in {load_time:.1f}s (attempt {attempt + 1})")
                return True, load_time, "Model loaded"
            else:
                last_error = f"HTTP {response.status_code}: {response.text[:200]}"
                print(f"  Load attempt {attempt + 1} failed: {last_error}")
                # Check for specific error that indicates model swap issue
                if "EOF" in str(last_error) or "load request" in str(last_error):
                    print(f"  Model swap in progress, will retry...")
                    continue
                # For other errors, don't retry
                break

        except httpx.TimeoutException as e:
            last_error = f"Timeout after {LOAD_TIMEOUT}s: {e}"
            print(f"  Load TIMEOUT (attempt {attempt + 1}): {last_error}")
            # Timeouts are worth retrying - model might be swapping
            continue

        except Exception as e:
            last_error = str(e)
            print(f"  Load EXCEPTION (attempt {attempt + 1}): {e}")

    load_time = time.time() - load_start
    print(f"  Load FAILED after {MAX_LOAD_RETRIES} attempts ({load_time:.1f}s): {last_error}")
    return False, load_time, last_error or "Unknown error"


# =============================================================================
# CORE SUMMARIZATION
# =============================================================================

def run_summarization(
    text: str,
    chapters: list[dict],
    model: str,
) -> tuple[list[ChapterSummary], float, float, bool]:
    """Run ChapterSummarizer with a specific model.

    Args:
        text: Full text content
        chapters: List of chapter dicts with start/end positions
        model: Model to use for summarization

    Returns:
        Tuple of (summaries, analysis_time_seconds, load_time_seconds, load_success)
    """
    # Create LLM client
    llm_config = LLMConfig.ollama(model=model)
    llm_client = LLMClient(llm_config)

    # Load model and measure load time (separate from analysis time)
    load_success, load_time, load_msg = load_model(model)
    if not load_success:
        print(f"  WARNING: Model load failed for {model}: {load_msg}")
        print(f"  Skipping analysis (load failed)")
        return [], 0.0, load_time, False

    # Start timing analysis AFTER model is loaded
    start = time.time()

    # Create summarizer
    summarizer = ChapterSummarizer(
        llm_client=llm_client,
        summary_length="detailed",
    )

    # Summarize each chapter
    summaries = []
    for ch in chapters:
        chapter_text = text[ch["start"]:ch["end"]]
        summary = summarizer.summarize_chapter(
            chapter_text=chapter_text,
            chapter_index=ch["index"],
            chapter_title=ch["title"],
        )
        summaries.append(summary)

    elapsed = time.time() - start
    return summaries, elapsed, load_time, load_success


# =============================================================================
# SCORING
# =============================================================================

def normalize_name(name: str) -> str:
    """Normalize a character name for comparison."""
    return name.lower().strip()


def names_match(name1: str, name2: str) -> bool:
    """Check if two names match (case-insensitive, handles substrings)."""
    n1 = normalize_name(name1)
    n2 = normalize_name(name2)

    # Exact match
    if n1 == n2:
        return True

    # Substring match (e.g., "Morris" matches "Sergeant-Major Morris")
    if n1 in n2 or n2 in n1:
        return True

    return False


def extract_character_list(summaries: list[ChapterSummary]) -> list[str]:
    """Extract all characters mentioned in summaries."""
    all_chars = set()
    for summary in summaries:
        # Get active and mentioned characters
        all_chars.update(summary.active_characters or [])
        all_chars.update(summary.mentioned_characters or [])
    return list(all_chars)


def find_in_list(char_list: list[str], target: str) -> bool:
    """Check if a character is in the list (fuzzy match)."""
    for char in char_list:
        if names_match(char, target):
            return True
    return False


def check_alias_grouping(summaries: list[ChapterSummary], alias_groups: list[list[str]]) -> tuple[int, int]:
    """Check if aliases are properly grouped (appear together, not separately).

    Returns: (correct_groups, total_groups)
    """
    if not alias_groups:
        return 0, 0

    all_chars = extract_character_list(summaries)
    correct = 0
    total = len(alias_groups)

    for group in alias_groups:
        # Find which aliases from this group appear in the character list
        found_aliases = []
        for alias in group:
            if find_in_list(all_chars, alias):
                found_aliases.append(alias)

        # Good: only one alias from the group appears (properly merged)
        # Bad: multiple aliases from the group appear separately
        if len(found_aliases) <= 1:
            correct += 1
        # If 0 found, that's also "correct" for this metric (no split)

    return correct, total


def check_key_events(summaries: list[ChapterSummary], key_events: list[str]) -> tuple[int, int]:
    """Check if key events are mentioned in summaries.

    Returns: (found_events, total_events)
    """
    # Combine all summary text
    all_text = " ".join(s.summary.lower() for s in summaries)

    found = 0
    for event in key_events:
        if event.lower() in all_text:
            found += 1

    return found, len(key_events)


def score_result(summaries: list[ChapterSummary], expected: dict) -> dict:
    """Score the summarization result.

    Metrics (weights):
    - Character Recall (25%): Found all required characters?
    - Character Precision (25%): No forbidden characters (hallucinations)?
    - Alias Quality (25%): Aliases properly grouped (not split)?
    - Event Coverage (25%): Key events mentioned in summary?

    Returns:
        Dictionary with scores and details
    """
    required_chars = expected["required_characters"]
    forbidden_chars = expected.get("forbidden_characters", [])
    alias_groups = expected.get("alias_groups", [])
    key_events = expected.get("key_events", [])

    # Extract character list from summaries
    char_list = extract_character_list(summaries)

    # Check required characters (recall)
    found_required = []
    missing_required = []
    for req in required_chars:
        if find_in_list(char_list, req):
            found_required.append(req)
        else:
            missing_required.append(req)

    recall_score = len(found_required) / len(required_chars) if required_chars else 1.0

    # Check forbidden characters (precision)
    found_forbidden = []
    for forbidden in forbidden_chars:
        if find_in_list(char_list, forbidden):
            found_forbidden.append(forbidden)

    # Precision: penalize for each forbidden character found
    if forbidden_chars:
        precision_score = 1.0 - (len(found_forbidden) / len(forbidden_chars))
    else:
        precision_score = 1.0

    # Check alias grouping
    correct_groups, total_groups = check_alias_grouping(summaries, alias_groups)
    alias_score = correct_groups / total_groups if total_groups > 0 else 1.0

    # Check key events
    found_events, total_events = check_key_events(summaries, key_events)
    event_score = found_events / total_events if total_events > 0 else 1.0

    # Calculate overall score (weighted average, scale to 0-10)
    overall = (
        recall_score * 0.25 +
        precision_score * 0.25 +
        alias_score * 0.25 +
        event_score * 0.25
    ) * 10.0

    # Determine status
    if recall_score == 1.0 and precision_score == 1.0 and alias_score >= 0.75:
        status = "PASS"
    elif recall_score >= 0.75 and precision_score >= 0.75:
        status = "PARTIAL"
    else:
        status = "FAIL"

    return {
        "char_recall": round(recall_score * 10, 2),
        "char_precision": round(precision_score * 10, 2),
        "alias_quality": round(alias_score * 10, 2),
        "event_coverage": round(event_score * 10, 2),
        "overall": round(overall, 2),
        "status": status,
        "characters_found": char_list,
        "required_found": found_required,
        "required_missing": missing_required,
        "forbidden_found": found_forbidden,
        "alias_groups_correct": correct_groups,
        "alias_groups_total": total_groups,
        "events_found": found_events,
        "events_total": total_events,
    }


# =============================================================================
# RESULTS MANAGEMENT
# =============================================================================

def load_existing_results() -> Optional[dict]:
    """Load existing results file if it exists."""
    if OUTPUT_PATH.exists():
        try:
            with open(OUTPUT_PATH) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None
    return None


def is_completed(results: dict, text_name: str, model: str) -> bool:
    """Check if a text/model combination has already been completed."""
    if text_name not in results.get("texts", {}):
        return False
    model_result = results["texts"][text_name].get("models", {}).get(model)
    if model_result is None:
        return False
    return model_result.get("status") not in (None, "ERROR")


def generate_summary_stats(results: dict, models_to_test: list, texts_to_test: list) -> dict:
    """Generate summary statistics from results."""
    summary = {
        "models_tested": len(models_to_test),
        "texts_tested": len(texts_to_test),
        "champion_model": None,
        "best_for_characters": None,
        "best_for_events": None,
        "model_rankings": {},
        "perfect_models": [],
    }

    model_sizes = {
        "qwen2.5:7b": 4.7,
        "qwen2.5:14b": 9.0,
        "qwen3:14b": 9.3,
        "mistral-small3.2:24b": 15,
        "qwen3:30b-instruct": 18,
        "qwen2.5:32b": 20,
        "qwen3-next:80b-a3b-instruct-q8_0": 84,
        "gpt-oss:120b": 120,
    }

    model_scores = {}
    model_char_scores = {}
    model_event_scores = {}
    model_pass_counts = {}

    for model in models_to_test:
        scores = []
        char_scores = []
        event_scores = []
        analysis_times = []
        load_times = []
        total_times = []
        pass_count = 0

        for text_name in texts_to_test:
            if text_name in results.get("texts", {}):
                model_result = results["texts"][text_name].get("models", {}).get(model)
                if model_result and "overall" in model_result:
                    scores.append(model_result["overall"])
                    # Character score = average of recall + precision + alias
                    char_score = (
                        model_result.get("char_recall", 0) +
                        model_result.get("char_precision", 0) +
                        model_result.get("alias_quality", 0)
                    ) / 3
                    char_scores.append(char_score)
                    event_scores.append(model_result.get("event_coverage", 0))
                    if model_result.get("status") == "PASS":
                        pass_count += 1
                    # Timing stats
                    if "time_seconds" in model_result:
                        analysis_times.append(model_result["time_seconds"])
                    if "load_time_seconds" in model_result:
                        load_times.append(model_result["load_time_seconds"])
                    if "total_time_seconds" in model_result:
                        total_times.append(model_result["total_time_seconds"])

        if scores:
            avg_score = sum(scores) / len(scores)
            avg_char = sum(char_scores) / len(char_scores)
            avg_event = sum(event_scores) / len(event_scores)

            model_scores[model] = avg_score
            model_char_scores[model] = avg_char
            model_event_scores[model] = avg_event
            model_pass_counts[model] = pass_count

            ranking_entry = {
                "avg_score": round(avg_score, 2),
                "avg_char_score": round(avg_char, 2),
                "avg_event_score": round(avg_event, 2),
                "pass_count": pass_count,
                "total_texts": len(texts_to_test),
                "size_gb": model_sizes.get(model, "unknown"),
            }

            # Add timing stats if available
            if analysis_times:
                ranking_entry["avg_analysis_time"] = round(sum(analysis_times) / len(analysis_times), 2)
            if load_times:
                ranking_entry["avg_load_time"] = round(sum(load_times) / len(load_times), 2)
            if total_times:
                ranking_entry["avg_total_time"] = round(sum(total_times) / len(total_times), 2)

            summary["model_rankings"][model] = ranking_entry

        if pass_count == len(texts_to_test):
            summary["perfect_models"].append(model)

    # Find champions
    if model_scores:
        summary["champion_model"] = max(model_scores, key=model_scores.get)
    if model_char_scores:
        summary["best_for_characters"] = max(model_char_scores, key=model_char_scores.get)
    if model_event_scores:
        summary["best_for_events"] = max(model_event_scores, key=model_event_scores.get)

    return summary


def save_results(results: dict, models_to_test: list, texts_to_test: list):
    """Save results incrementally with updated summary."""
    results["summary"] = generate_summary_stats(results, models_to_test, texts_to_test)

    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(results, f, indent=2)


# =============================================================================
# TEXT LOADING
# =============================================================================

def load_text(text_path: Path) -> str:
    """Load text from file, handling PDFs specially.

    Also strips Project Gutenberg boilerplate to match production pipeline behavior.
    """
    from src.ingestion.refine import _strip_gutenberg_boilerplate

    if text_path.suffix.lower() == ".pdf":
        from src.ingestion.pdf import extract_text_from_pdf
        text = extract_text_from_pdf(str(text_path))
    else:
        text = text_path.read_text()

    cleaned, warnings = _strip_gutenberg_boilerplate(text)
    for w in warnings:
        print(f"  [boilerplate] {w}")
    return cleaned


# =============================================================================
# MAIN
# =============================================================================

def main():
    # Parse command line args
    models_to_test = MODELS
    texts_to_test = list(TEST_TEXTS.keys())
    resume_mode = False

    args = sys.argv[1:]
    if "--resume" in args:
        resume_mode = True
        args.remove("--resume")

    # Check for --model option
    model_filter = None
    for i, arg in enumerate(args):
        if arg == "--model" and i + 1 < len(args):
            model_filter = args[i + 1]
            args = args[:i] + args[i+2:]
            break
        elif arg.startswith("--model="):
            model_filter = arg.split("=", 1)[1]
            args.remove(arg)
            break

    if model_filter:
        # Filter to just the specified model
        matching = [m for m in MODELS if model_filter in m]
        if matching:
            models_to_test = matching
            print(f"Filtering to model(s): {models_to_test}")
        else:
            print(f"WARNING: No model matching '{model_filter}' found in MODELS")
            print(f"Available: {MODELS}")
            return

    if args:
        if args[0] == "--quick":
            texts_to_test = ["cask_of_amontillado", "gift_of_the_magi"]
            models_to_test = ["qwen3:30b-instruct", "qwen2.5:14b"]
        elif args[0] in TEST_TEXTS:
            texts_to_test = [args[0]]

    # Initialize or load results
    if resume_mode:
        existing = load_existing_results()
        if existing:
            results = existing
            results["resumed_at"] = datetime.now().isoformat()
            print("Resuming from existing results...")
        else:
            print("No existing results found, starting fresh...")
            results = {
                "experiment_date": datetime.now().strftime("%Y-%m-%d"),
                "experiment_timestamp": datetime.now().isoformat(),
                "texts": {},
                "summary": {},
            }
    else:
        results = {
            "experiment_date": datetime.now().strftime("%Y-%m-%d"),
            "experiment_timestamp": datetime.now().isoformat(),
            "texts": {},
            "summary": {},
        }

    print("=" * 70)
    print("SUMMARY GENERATION EXPERIMENT")
    print("=" * 70)
    print(f"Texts: {texts_to_test}")
    print(f"Models: {len(models_to_test)} models")
    if resume_mode:
        print("Mode: RESUME (skipping completed combinations)")
    print("=" * 70)

    for text_name in texts_to_test:
        text_path = TEST_TEXTS[text_name]
        expected = EXPECTED_CONTENT[text_name]

        print(f"\n{'='*70}")
        print(f"TEXT: {text_name}")
        print(f"Required characters: {expected['required_characters']}")
        print(f"Key events: {expected['key_events'][:5]}...")
        print(f"{'='*70}")

        if not text_path.exists():
            print(f"ERROR: Text file not found: {text_path}")
            continue

        try:
            text = load_text(text_path)
        except Exception as e:
            print(f"ERROR loading text: {e}")
            continue

        print(f"Size: {len(text):,} characters")

        # Initialize text entry
        if text_name not in results["texts"]:
            results["texts"][text_name] = {
                "expected": {
                    "required_characters": expected["required_characters"],
                    "key_events": expected["key_events"],
                },
                "char_count": len(text),
                "models": {},
            }
        else:
            if "models" not in results["texts"][text_name]:
                results["texts"][text_name]["models"] = {}

        # Detect/load chapters (cached, deterministic)
        print("\n[STRUCTURE]")
        try:
            chapters = detect_chapters(text, text_name)
            print(f"  Using {len(chapters)} chapters")
        except Exception as e:
            print(f"  ERROR detecting chapters: {e}")
            continue

        # Run each model
        for model in models_to_test:
            model_short = model.split(":")[0]

            if resume_mode and is_completed(results, text_name, model):
                print(f"\n[{model_short}] SKIPPED (already completed)")
                continue

            print(f"\n[{model_short}] Running summarization...")

            try:
                summaries, analysis_time, load_time, load_success = run_summarization(text, chapters, model)

                if not load_success:
                    # Record load failure without scoring
                    results["texts"][text_name]["models"][model] = {
                        "status": "LOAD_FAILED",
                        "load_time_seconds": round(load_time, 2),
                        "load_success": False,
                    }
                    print(f"  Status: LOAD_FAILED (skipped analysis)")
                    print(f"  Load time: {load_time:.1f}s")
                else:
                    score = score_result(summaries, expected)

                    results["texts"][text_name]["models"][model] = {
                        **score,
                        "time_seconds": round(analysis_time, 2),
                        "load_time_seconds": round(load_time, 2),
                        "load_success": load_success,
                        "total_time_seconds": round(analysis_time + load_time, 2),
                        "num_chapters": len(chapters),
                    }

                    print(f"  Characters found: {score['characters_found'][:5]}..." if len(score['characters_found']) > 5 else f"  Characters found: {score['characters_found']}")
                    print(f"  Status: {score['status']} | Overall: {score['overall']:.1f}/10")
                    print(f"  CharRecall: {score['char_recall']:.1f} | CharPrecision: {score['char_precision']:.1f} | "
                          f"Alias: {score['alias_quality']:.1f} | Events: {score['event_coverage']:.1f}")
                    if score['required_missing']:
                        print(f"  Missing chars: {score['required_missing']}")
                    if score['forbidden_found']:
                        print(f"  HALLUCINATIONS: {score['forbidden_found']}")
                    print(f"  Time: {analysis_time:.1f}s (load: {load_time:.1f}s, total: {analysis_time + load_time:.1f}s)")

            except Exception as e:
                print(f"  ERROR: {e}")
                import traceback
                traceback.print_exc()
                results["texts"][text_name]["models"][model] = {"error": str(e), "status": "ERROR"}

            save_results(results, models_to_test, texts_to_test)

    # Print summary table
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    header = f"{'Model':<35}"
    for text_name in texts_to_test:
        short_name = text_name[:8]
        header += f" | {short_name:>8}"
    header += f" | {'Avg':>6} | {'Char':>5}"
    print(header)
    print("-" * len(header))

    for model in models_to_test:
        model_short = model.split(":")[0][:33]
        row = f"{model_short:<35}"
        scores = []
        char_scores = []

        for text_name in texts_to_test:
            if text_name in results["texts"] and model in results["texts"][text_name]["models"]:
                r = results["texts"][text_name]["models"][model]
                if "error" in r:
                    row += f" | {'ERR':>8}"
                else:
                    status_marker = "+" if r["status"] == "PASS" else "-"
                    row += f" | {r['overall']:.1f}{status_marker:>3}"
                    scores.append(r["overall"])
                    char_score = (r.get("char_recall", 0) + r.get("char_precision", 0) + r.get("alias_quality", 0)) / 3
                    char_scores.append(char_score)
            else:
                row += f" | {'-':>8}"

        if scores:
            avg = sum(scores) / len(scores)
            char_avg = sum(char_scores) / len(char_scores)
            row += f" | {avg:>6.1f} | {char_avg:>5.1f}"
        else:
            row += f" | {'-':>6} | {'-':>5}"

        print(row)

    # Print key findings
    print("\n" + "-" * 70)
    print("KEY FINDINGS:")
    if results["summary"].get("champion_model"):
        print(f"  Overall champion: {results['summary']['champion_model']}")
    if results["summary"].get("best_for_characters"):
        print(f"  Best for characters: {results['summary']['best_for_characters']}")
    if results["summary"].get("best_for_events"):
        print(f"  Best for events: {results['summary']['best_for_events']}")
    if results["summary"].get("perfect_models"):
        print(f"  Perfect models: {', '.join(results['summary']['perfect_models'])}")

    save_results(results, models_to_test, texts_to_test)
    print(f"\nFull results saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
