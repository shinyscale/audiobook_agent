"""
Ollama Model Manager

Provides reliable model loading with explicit lifecycle management.
Instead of hoping Ollama handles model swaps gracefully, this module:
  1. Checks what's currently loaded via /api/ps
  2. Explicitly unloads it via keep_alive=0
  3. Polls until the VRAM is actually free
  4. Loads the requested model
  5. Verifies it responds

Usage:
    from ollama_manager import load_model

    success, load_time, message = load_model("qwen2.5:32b")
"""

import time
from typing import Optional

import httpx


# Defaults - can be overridden per call
DEFAULT_BASE_URL = "http://localhost:11434"
MAX_LOAD_RETRIES = 3
LOAD_TIMEOUT = 300       # seconds per load attempt
UNLOAD_POLL_INTERVAL = 5  # seconds between /api/ps checks
UNLOAD_TIMEOUT = 120      # seconds to wait for unload to complete


def get_loaded_models(base_url: str = DEFAULT_BASE_URL) -> list[dict]:
    """Check which models are currently loaded in Ollama.

    Returns list of model dicts with 'name', 'size', etc.
    """
    try:
        r = httpx.get(f"{base_url}/api/ps", timeout=10.0)
        if r.status_code == 200:
            return r.json().get("models", [])
    except Exception as e:
        print(f"  [ollama] Failed to query /api/ps: {e}")
    return []


def unload_model(model_name: str, base_url: str = DEFAULT_BASE_URL) -> bool:
    """Explicitly unload a model by setting keep_alive to 0.

    Returns True if the unload request was accepted.
    """
    try:
        r = httpx.post(
            f"{base_url}/api/generate",
            json={
                "model": model_name,
                "prompt": "",
                "keep_alive": 0,
            },
            timeout=httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0),
        )
        return r.status_code == 200
    except Exception as e:
        print(f"  [ollama] Unload request failed for {model_name}: {e}")
        return False


def wait_for_idle(base_url: str = DEFAULT_BASE_URL, timeout: float = UNLOAD_TIMEOUT) -> bool:
    """Poll /api/ps until no models are loaded.

    Returns True if Ollama is idle, False if timed out.
    """
    start = time.time()
    while time.time() - start < timeout:
        models = get_loaded_models(base_url)
        if not models:
            return True
        names = [m.get("name", "?") for m in models]
        elapsed = time.time() - start
        print(f"  [ollama] Waiting for unload... ({elapsed:.0f}s) still loaded: {', '.join(names)}")
        time.sleep(UNLOAD_POLL_INTERVAL)

    return False


def unload_all(base_url: str = DEFAULT_BASE_URL) -> bool:
    """Unload all currently loaded models and wait for VRAM to be free.

    Returns True if all models were successfully unloaded.
    """
    models = get_loaded_models(base_url)
    if not models:
        return True

    for model in models:
        name = model.get("name", "")
        if name:
            print(f"  [ollama] Unloading {name}...")
            unload_model(name, base_url)

    # Poll until all models are gone
    if wait_for_idle(base_url):
        print(f"  [ollama] All models unloaded")
        return True
    else:
        remaining = get_loaded_models(base_url)
        names = [m.get("name", "?") for m in remaining]
        print(f"  [ollama] WARNING: Timed out waiting for unload, still loaded: {', '.join(names)}")
        return False


def load_model(
    model: str,
    base_url: str = DEFAULT_BASE_URL,
    max_retries: int = MAX_LOAD_RETRIES,
    load_timeout: float = LOAD_TIMEOUT,
) -> tuple[bool, float, str]:
    """Load a model with explicit lifecycle management.

    Steps:
      1. Check what's currently loaded
      2. If a different model is loaded, explicitly unload it and wait
      3. Send a test prompt to load and verify the model
      4. Retry with full unload cycle on failure

    Returns:
        Tuple of (success, load_time_seconds, message)
    """
    load_start = time.time()
    last_error = None

    # Check if the requested model is already loaded
    loaded = get_loaded_models(base_url)
    loaded_names = [m.get("name", "") for m in loaded]

    if any(model in name or name in model for name in loaded_names):
        print(f"  [ollama] {model} already loaded, verifying...")
    elif loaded:
        # Different model loaded - explicitly unload first
        print(f"  [ollama] Currently loaded: {', '.join(loaded_names)}")
        print(f"  [ollama] Unloading before loading {model}...")
        unload_all(base_url)
    else:
        print(f"  [ollama] No models loaded, loading {model}...")

    timeout = httpx.Timeout(connect=30.0, read=load_timeout, write=30.0, pool=30.0)

    for attempt in range(max_retries):
        if attempt > 0:
            # On retry, do a full unload cycle in case something is stuck
            print(f"  [ollama] Retry {attempt}/{max_retries - 1}: unloading everything first...")
            unload_all(base_url)
            print(f"  [ollama] Waiting 15s before retry...")
            time.sleep(15)

        try:
            with httpx.Client(base_url=base_url, timeout=timeout) as client:
                response = client.post(
                    "/api/generate",
                    json={
                        "model": model,
                        "prompt": "Reply with just the word OK.",
                        "stream": False,
                    },
                )

            load_time = time.time() - load_start

            if response.status_code == 200:
                # Verify it's actually loaded
                loaded_after = get_loaded_models(base_url)
                loaded_names_after = [m.get("name", "") for m in loaded_after]
                if any(model in name or name in model for name in loaded_names_after):
                    print(f"  [ollama] {model} loaded and verified in {load_time:.1f}s")
                    return True, load_time, "Model loaded and verified"
                else:
                    print(f"  [ollama] {model} responded but not in /api/ps: {loaded_names_after}")
                    # Still counts as success - it responded to a prompt
                    return True, load_time, "Model loaded (not visible in /api/ps)"
            else:
                last_error = f"HTTP {response.status_code}: {response.text[:200]}"
                print(f"  [ollama] Load attempt {attempt + 1} failed: {last_error}")

        except httpx.TimeoutException as e:
            last_error = f"Timeout after {load_timeout}s: {e}"
            print(f"  [ollama] Load TIMEOUT (attempt {attempt + 1}): {last_error}")

        except Exception as e:
            last_error = str(e)
            print(f"  [ollama] Load EXCEPTION (attempt {attempt + 1}): {e}")

    load_time = time.time() - load_start
    print(f"  [ollama] FAILED after {max_retries} attempts ({load_time:.1f}s): {last_error}")
    return False, load_time, last_error or "Unknown error"
