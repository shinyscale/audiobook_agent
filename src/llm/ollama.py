"""
Ollama-specific utilities for model management.
"""

import json
from typing import Callable, Optional

import requests


def pull_ollama_model(
    model: str,
    base_url: str = "http://localhost:11434",
    progress_callback: Optional[Callable[[str, int, int], None]] = None,
) -> tuple[bool, str]:
    """
    Pull a model from the Ollama library.

    Args:
        model: Model name (e.g., "qwen2.5:7b", "llama3.2")
        base_url: Ollama server URL
        progress_callback: Called with (status, completed_bytes, total_bytes)

    Returns:
        Tuple of (success, message)
    """
    url = f"{base_url.rstrip('/')}/api/pull"

    try:
        with requests.post(
            url,
            json={"model": model},
            stream=True,
            timeout=600,  # 10 minute timeout for large models
        ) as response:
            if not response.ok:
                return False, f"HTTP {response.status_code}: {response.text[:100]}"

            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        status = data.get("status", "")
                        completed = data.get("completed", 0)
                        total = data.get("total", 0)

                        if progress_callback:
                            progress_callback(status, completed, total)

                        # Check for error in response
                        if "error" in data:
                            return False, data["error"]

                    except json.JSONDecodeError:
                        continue

            return True, f"Successfully pulled {model}"

    except requests.exceptions.Timeout:
        return False, "Pull timed out - model may be very large"
    except requests.exceptions.ConnectionError:
        return False, f"Cannot connect to Ollama at {base_url}"
    except Exception as e:
        return False, f"Error: {str(e)}"


def delete_ollama_model(
    model: str,
    base_url: str = "http://localhost:11434",
) -> tuple[bool, str]:
    """
    Delete a model from Ollama.

    Args:
        model: Model name to delete
        base_url: Ollama server URL

    Returns:
        Tuple of (success, message)
    """
    url = f"{base_url.rstrip('/')}/api/delete"

    try:
        response = requests.delete(
            url,
            json={"model": model},
            timeout=30,
        )

        if response.ok:
            return True, f"Deleted {model}"
        elif response.status_code == 404:
            return False, f"Model '{model}' not found"
        else:
            return False, f"HTTP {response.status_code}: {response.text[:100]}"

    except requests.exceptions.ConnectionError:
        return False, f"Cannot connect to Ollama at {base_url}"
    except Exception as e:
        return False, f"Error: {str(e)}"


def get_ollama_model_info(
    model: str,
    base_url: str = "http://localhost:11434",
) -> Optional[dict]:
    """
    Get detailed information about an Ollama model.

    Args:
        model: Model name
        base_url: Ollama server URL

    Returns:
        Dict with model info, or None if not found
    """
    url = f"{base_url.rstrip('/')}/api/show"

    try:
        response = requests.post(
            url,
            json={"model": model},
            timeout=10,
        )

        if response.ok:
            return response.json()
        return None

    except Exception:
        return None
