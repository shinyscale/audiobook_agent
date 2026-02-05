#!/usr/bin/env python3
"""
Character Extraction Experiment

Tests MainCastExtractor across multiple models on short stories with known character lists.
This isolates the LLM-dependent character identification step from the rest of the pipeline.

Usage:
    python oracle-loop/character_experiment.py           # Run all models on all texts
    python oracle-loop/character_experiment.py --quick   # Quick test: 2 models, 2 texts
    python oracle-loop/character_experiment.py berenice  # Run all models on one text
    python oracle-loop/character_experiment.py --resume  # Resume from crash, skip completed

Results saved to: oracle-loop/state/character_results.json
Cached summaries: oracle-loop/state/summary_cache/{text_name}.json
"""

import json
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
from src.pipeline.character_extraction_v2.main_cast import MainCastExtractor, MainCastProfile


# =============================================================================
# GROUND TRUTH - Expected characters for each test text
# =============================================================================

EXPECTED_CHARACTERS = {
    "cask_of_amontillado": {
        "required": ["Montresor", "Fortunato"],
        "forbidden": [],
        "aliases": {
            "Montresor": ["the narrator"],
            "Fortunato": [],
        },
        "narrator": "Montresor",
    },
    "monkeys_paw": {
        "required": ["Mr. White", "Mrs. White", "Herbert White", "Sergeant-Major Morris"],
        "forbidden": [],
        "aliases": {
            "Mr. White": ["the old man", "father"],
            "Mrs. White": ["the old woman", "mother"],
            "Herbert White": ["Herbert"],
            "Sergeant-Major Morris": ["Morris", "the sergeant-major"],
        },
        "narrator": None,  # third-person
    },
    "berenice": {
        "required": ["Egaeus", "Berenice"],
        "forbidden": ["Mad'selle Salle"],  # hallucination test - this is a dancer mentioned in passing
        "aliases": {
            "Egaeus": ["the narrator"],
            "Berenice": [],
        },
        "narrator": "Egaeus",
    },
    "gift_of_the_magi": {
        "required": ["Della", "Jim"],
        "forbidden": [],
        "aliases": {
            "Della": ["Mrs. James Dillingham Young"],
            "Jim": ["James Dillingham Young", "Mr. James Dillingham Young"],
        },
        "narrator": None,  # third-person
    },
    "masque_of_red_death": {
        "required": ["Prince Prospero", "the Red Death"],
        "forbidden": [],
        "aliases": {
            "Prince Prospero": ["Prospero"],
            "the Red Death": ["Red Death"],
        },
        "narrator": None,  # third-person
    },
    "i_have_no_mouth": {
        "required": ["AM", "Ted", "Gorrister", "Benny", "Nimdok", "Ellen"],
        "forbidden": [],
        "aliases": {
            "AM": ["the computer", "Allied Mastercomputer"],
            "Ted": ["the narrator"],
        },
        "narrator": "Ted",
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
    "qwen3:30b-instruct",  # Structure champion - test on characters
    "qwen2.5:32b",
    # Large models
    "qwen3-next:80b-a3b-instruct-q8_0",
    "gpt-oss:120b",
]


# =============================================================================
# MODEL LOADING
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

# Summary generation model (high quality for caching)
SUMMARY_MODEL = "qwen3-next:80b-a3b-instruct-q8_0"


# =============================================================================
# OUTPUT PATHS
# =============================================================================

OUTPUT_PATH = Path(__file__).parent / "state" / "character_results.json"
SUMMARY_CACHE_DIR = Path(__file__).parent / "state" / "summary_cache"


# =============================================================================
# SUMMARY CACHING
# =============================================================================

def get_summary_cache_path(text_name: str) -> Path:
    """Get the path to the cached summary file for a text."""
    return SUMMARY_CACHE_DIR / f"{text_name}.json"


def load_cached_summaries(text_name: str) -> Optional[list[str]]:
    """Load cached summaries if they exist."""
    cache_path = get_summary_cache_path(text_name)
    if cache_path.exists():
        try:
            with open(cache_path) as f:
                data = json.load(f)
                return data.get("summaries", [])
        except (json.JSONDecodeError, IOError) as e:
            print(f"  Warning: Failed to load cached summaries: {e}")
    return None


def save_summaries_to_cache(text_name: str, summaries: list[str], model: str) -> None:
    """Save summaries to cache."""
    SUMMARY_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = get_summary_cache_path(text_name)

    data = {
        "text_name": text_name,
        "model": model,
        "generated_at": datetime.now().isoformat(),
        "summaries": summaries,
    }

    with open(cache_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"  Cached {len(summaries)} summaries to {cache_path}")


def generate_summaries(text: str, text_name: str, model: str = SUMMARY_MODEL) -> list[str]:
    """Generate chapter summaries for a text using the specified model.

    This runs the full chapter detection + summarization pipeline once,
    then caches the results for all future model tests.
    """
    print(f"  Generating summaries with {model}...")

    # Create LLM client
    llm_config = LLMConfig.ollama(model=model)
    llm_client = LLMClient(llm_config)

    # Step 1: Detect chapters
    print("    Step 1: Detecting chapters...")
    chapter_pipeline = ChapterDetectionPipeline.with_ollama(model=model)
    chapter_map = chapter_pipeline.run(text, source_file=text_name)

    if not chapter_map or not chapter_map.chapters:
        print(f"    Warning: No chapters detected, treating as single chapter")
        # Treat entire text as one chapter
        chapters = [{"title": "Full Text", "text": text}]
    else:
        chapters = []
        for i, chapter in enumerate(chapter_map.chapters):
            # Extract chapter text using character offsets
            start = chapter.start_position
            end = chapter.end_position if chapter.end_position else len(text)
            chapter_text = text[start:end]
            chapters.append({
                "title": chapter.title or f"Chapter {i+1}",
                "text": chapter_text,
            })

    print(f"    Found {len(chapters)} chapters")

    # Step 2: Summarize each chapter
    print("    Step 2: Summarizing chapters...")
    summarizer = ChapterSummarizer(
        llm_client=llm_client,
        summary_length="detailed",  # Get more detail for character extraction
    )

    summaries = []
    for i, chapter in enumerate(chapters):
        print(f"      Chapter {i+1}/{len(chapters)}: {chapter['title'][:40]}...")
        summary = summarizer.summarize_chapter(
            chapter_text=chapter["text"],
            chapter_index=i,
            chapter_title=chapter["title"],
        )

        # Build summary text with character list (as expected by MainCastExtractor)
        chars_list = summary.active_characters + summary.mentioned_characters
        if chars_list:
            chars_str = f"\n[Characters: {', '.join(chars_list)}]"
        else:
            chars_str = ""

        full_summary = f"{summary.summary}{chars_str}"
        summaries.append(full_summary)

    return summaries


def load_or_generate_summaries(text: str, text_name: str) -> list[str]:
    """Load cached summaries or generate them if not available."""
    # Try to load from cache first
    summaries = load_cached_summaries(text_name)
    if summaries:
        print(f"  Loaded {len(summaries)} cached summaries")
        return summaries

    # Generate new summaries
    print(f"  No cached summaries found, generating with {SUMMARY_MODEL}...")
    summaries = generate_summaries(text, text_name)

    # Cache for future use
    save_summaries_to_cache(text_name, summaries, SUMMARY_MODEL)

    return summaries


# =============================================================================
# CORE EXTRACTION
# =============================================================================

def run_character_extraction(
    summaries: list[str],
    model: str,
) -> tuple[list[MainCastProfile], float, float, bool]:
    """Run MainCastExtractor with a specific model.

    Args:
        summaries: Chapter summaries to extract characters from
        model: Model to use for extraction

    Returns:
        Tuple of (profiles, analysis_time_seconds, load_time_seconds, load_success)
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

    # Create extractor
    extractor = MainCastExtractor(llm_client=llm_client)

    # Run extraction
    profiles = extractor.extract(
        chapter_summaries=summaries,
        use_two_pass=True,  # Use two-pass for better alias resolution
    )

    elapsed = time.time() - start
    return profiles, elapsed, load_time, load_success


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

    # Substring match (e.g., "Prospero" matches "Prince Prospero")
    if n1 in n2 or n2 in n1:
        return True

    return False


def find_character(profiles: list[MainCastProfile], target_name: str) -> Optional[MainCastProfile]:
    """Find a character profile matching the target name (including aliases)."""
    for profile in profiles:
        # Check canonical name
        if names_match(profile.canonical_name, target_name):
            return profile

        # Check aliases
        for alias in profile.aliases:
            if names_match(alias, target_name):
                return profile

    return None


def score_result(profiles: list[MainCastProfile], expected: dict) -> dict:
    """Score the extraction result against expected characters.

    Metrics:
    - Recall (35%): Did we find all required characters?
    - Precision (25%): No hallucinations (forbidden characters)?
    - Alias Quality (25%): Are aliases correctly grouped?
    - Narrator (15%): Correct narrator identification?

    Returns:
        Dictionary with scores and details
    """
    required = expected["required"]
    forbidden = expected.get("forbidden", [])
    expected_aliases = expected.get("aliases", {})
    expected_narrator = expected.get("narrator")

    # Track found characters
    found_required = []
    missing_required = []
    hallucinations = []

    # Check required characters
    for req_name in required:
        profile = find_character(profiles, req_name)
        if profile:
            found_required.append(req_name)
        else:
            missing_required.append(req_name)

    # Check for forbidden characters (hallucinations)
    for forbidden_name in forbidden:
        profile = find_character(profiles, forbidden_name)
        if profile:
            hallucinations.append(forbidden_name)

    # Calculate recall (35% weight)
    recall_score = len(found_required) / len(required) if required else 1.0
    recall_weighted = recall_score * 10.0  # Scale to 0-10

    # Calculate precision (25% weight) - penalize hallucinations
    if hallucinations:
        precision_score = 0.0  # Any hallucination is a fail
    else:
        precision_score = 1.0
    precision_weighted = precision_score * 10.0

    # Calculate alias quality (25% weight)
    alias_scores = []
    for char_name, expected_char_aliases in expected_aliases.items():
        profile = find_character(profiles, char_name)
        if not profile or not expected_char_aliases:
            continue

        # Check how many expected aliases were found
        found_aliases = 0
        for exp_alias in expected_char_aliases:
            if any(names_match(a, exp_alias) for a in profile.aliases):
                found_aliases += 1

        if expected_char_aliases:
            alias_scores.append(found_aliases / len(expected_char_aliases))

    alias_quality = sum(alias_scores) / len(alias_scores) if alias_scores else 1.0
    alias_weighted = alias_quality * 10.0

    # Calculate narrator detection (15% weight)
    narrator_score = 0.0
    if expected_narrator is None:
        # Third-person narrative - no narrator character expected
        narrator_score = 1.0
    else:
        # First-person - check if narrator is correctly identified
        narrator_profile = find_character(profiles, expected_narrator)
        if narrator_profile:
            # Check if marked as protagonist (common for narrators)
            if narrator_profile.role == "protagonist":
                narrator_score = 1.0
            else:
                narrator_score = 0.7  # Found but not marked as protagonist
    narrator_weighted = narrator_score * 10.0

    # Calculate overall score (weighted average)
    overall = (
        recall_weighted * 0.35 +
        precision_weighted * 0.25 +
        alias_weighted * 0.25 +
        narrator_weighted * 0.15
    )

    # Determine status
    if recall_score == 1.0 and precision_score == 1.0:
        status = "PASS"
    elif recall_score >= 0.75 and precision_score == 1.0:
        status = "PARTIAL"
    else:
        status = "FAIL"

    return {
        "recall": round(recall_weighted, 2),
        "precision": round(precision_weighted, 2),
        "alias_quality": round(alias_weighted, 2),
        "narrator": round(narrator_weighted, 2),
        "overall": round(overall, 2),
        "status": status,
        "characters_found": [p.canonical_name for p in profiles],
        "required_found": found_required,
        "required_missing": missing_required,
        "hallucinations": hallucinations,
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
    """Check if a text/model combination has already been completed (not errored)."""
    if text_name not in results.get("texts", {}):
        return False
    model_result = results["texts"][text_name].get("models", {}).get(model)
    if model_result is None:
        return False
    # Consider it completed if it has a status that isn't ERROR
    return model_result.get("status") not in (None, "ERROR")


def generate_summary(results: dict, models_to_test: list, texts_to_test: list) -> dict:
    """Generate summary statistics from results."""
    summary = {
        "models_tested": len(models_to_test),
        "texts_tested": len(texts_to_test),
        "champion_model": None,
        "smallest_passing_model": None,
        "model_rankings": {},
        "perfect_models": [],
    }

    # Model sizes for finding smallest passing
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

    # Calculate model rankings
    model_scores = {}
    model_pass_counts = {}

    for model in models_to_test:
        scores = []
        analysis_times = []
        load_times = []
        total_times = []
        pass_count = 0

        for text_name in texts_to_test:
            if text_name in results.get("texts", {}):
                model_result = results["texts"][text_name].get("models", {}).get(model)
                if model_result and "overall" in model_result:
                    scores.append(model_result["overall"])
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
            model_scores[model] = avg_score
            model_pass_counts[model] = pass_count

            ranking_entry = {
                "avg_score": round(avg_score, 2),
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

        # Track perfect models
        if pass_count == len(texts_to_test):
            summary["perfect_models"].append(model)

    # Find champion (highest average score)
    if model_scores:
        champion = max(model_scores, key=model_scores.get)
        summary["champion_model"] = champion

    # Find smallest passing model
    if summary["perfect_models"]:
        smallest = min(
            summary["perfect_models"],
            key=lambda m: model_sizes.get(m, float("inf"))
        )
        summary["smallest_passing_model"] = smallest

    return summary


def save_results(results: dict, models_to_test: list, texts_to_test: list):
    """Save results incrementally with updated summary."""
    # Update summary with current state
    results["summary"] = generate_summary(results, models_to_test, texts_to_test)

    # Write to file
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
            # Quick mode: just 2 texts with 2 models
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
    print("CHARACTER EXTRACTION EXPERIMENT")
    print("=" * 70)
    print(f"Texts: {texts_to_test}")
    print(f"Models: {len(models_to_test)} models")
    if resume_mode:
        print("Mode: RESUME (skipping completed combinations)")
    print("=" * 70)

    for text_name in texts_to_test:
        text_path = TEST_TEXTS[text_name]
        expected = EXPECTED_CHARACTERS[text_name]

        print(f"\n{'='*70}")
        print(f"TEXT: {text_name}")
        print(f"Required characters: {expected['required']}")
        print(f"Expected narrator: {expected.get('narrator', 'None (third-person)')}")
        print(f"{'='*70}")

        # Check if file exists
        if not text_path.exists():
            print(f"ERROR: Text file not found: {text_path}")
            continue

        # Load text
        try:
            text = load_text(text_path)
        except Exception as e:
            print(f"ERROR loading text: {e}")
            continue

        text_size = len(text)
        print(f"Size: {text_size:,} characters")

        # Initialize or preserve existing text entry
        if text_name not in results["texts"]:
            results["texts"][text_name] = {
                "expected": {
                    "required": expected["required"],
                    "narrator": expected.get("narrator"),
                },
                "char_count": text_size,
                "models": {},
            }
        else:
            if "models" not in results["texts"][text_name]:
                results["texts"][text_name]["models"] = {}

        # Load or generate summaries (cached)
        print("\n[SUMMARIES]")
        try:
            summaries = load_or_generate_summaries(text, text_name)
            print(f"  Using {len(summaries)} chapter summaries")
        except Exception as e:
            print(f"  ERROR generating summaries: {e}")
            import traceback
            traceback.print_exc()
            continue

        # Run each model
        for model in models_to_test:
            model_short = model.split(":")[0]

            # Skip if already completed in resume mode
            if resume_mode and is_completed(results, text_name, model):
                print(f"\n[{model_short}] SKIPPED (already completed)")
                continue

            print(f"\n[{model_short}] Running...")

            try:
                profiles, analysis_time, load_time, load_success = run_character_extraction(summaries, model)

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
                    score = score_result(profiles, expected)

                    results["texts"][text_name]["models"][model] = {
                        **score,
                        "time_seconds": round(analysis_time, 2),
                        "load_time_seconds": round(load_time, 2),
                        "load_success": load_success,
                        "total_time_seconds": round(analysis_time + load_time, 2),
                    }

                    print(f"  Found: {score['characters_found']}")
                    print(f"  Status: {score['status']} | Overall: {score['overall']:.1f}/10")
                    print(f"  Recall: {score['recall']:.1f} | Precision: {score['precision']:.1f} | "
                          f"Alias: {score['alias_quality']:.1f} | Narrator: {score['narrator']:.1f}")
                    print(f"  Time: {analysis_time:.1f}s (load: {load_time:.1f}s, total: {analysis_time + load_time:.1f}s)")
                    if score['required_missing']:
                        print(f"  Missing: {score['required_missing']}")
                    if score['hallucinations']:
                        print(f"  HALLUCINATIONS: {score['hallucinations']}")

            except Exception as e:
                print(f"  ERROR: {e}")
                import traceback
                traceback.print_exc()
                results["texts"][text_name]["models"][model] = {"error": str(e), "status": "ERROR"}

            # Save incrementally after each model
            save_results(results, models_to_test, texts_to_test)

    # Print summary table
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    # Create summary table header
    header = f"{'Model':<35}"
    for text_name in texts_to_test:
        short_name = text_name[:10]
        header += f" | {short_name:>10}"
    header += f" | {'Avg':>6}"
    print(header)
    print("-" * len(header))

    for model in models_to_test:
        model_short = model.split(":")[0][:33]
        row = f"{model_short:<35}"
        scores = []

        for text_name in texts_to_test:
            if text_name in results["texts"] and model in results["texts"][text_name]["models"]:
                r = results["texts"][text_name]["models"][model]
                if "error" in r:
                    row += f" | {'ERR':>10}"
                else:
                    status_marker = "+" if r["status"] == "PASS" else "-"
                    row += f" | {r['overall']:.1f}{status_marker:>5}"
                    scores.append(r["overall"])
            else:
                row += f" | {'-':>10}"

        # Add average
        if scores:
            avg = sum(scores) / len(scores)
            row += f" | {avg:>6.1f}"
        else:
            row += f" | {'-':>6}"

        print(row)

    # Print key findings
    print("\n" + "-" * 70)
    print("KEY FINDINGS:")
    if results["summary"].get("champion_model"):
        print(f"  Champion model: {results['summary']['champion_model']}")
    if results["summary"].get("smallest_passing_model"):
        print(f"  Smallest passing: {results['summary']['smallest_passing_model']}")
    if results["summary"].get("perfect_models"):
        print(f"  Perfect models: {', '.join(results['summary']['perfect_models'])}")

    # Final save
    save_results(results, models_to_test, texts_to_test)
    print(f"\nFull results saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
