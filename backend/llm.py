from __future__ import annotations

import os
from typing import Dict, List, Tuple

import requests

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:1.5b")
FALLBACK_MODEL = "qwen2.5:3b"
TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "180"))


def get_active_model() -> str:
    """Returns the fastest available installed model (preferring lightweight coder 1.5b)."""
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict):
                models = [
                    m.get("name", "")
                    for m in data.get("models", [])
                    if isinstance(m, dict) and isinstance(m.get("name"), str)
                ]
                for candidate in [OLLAMA_MODEL, FALLBACK_MODEL]:
                    if any(m == candidate or m.startswith(f"{candidate}:") for m in models):
                        return candidate
    except Exception:
        pass
    return OLLAMA_MODEL


def check_ollama_status() -> Tuple[bool, str]:
    """Verifies that Ollama is running and that a supported model is installed."""
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
    except requests.exceptions.ConnectionError:
        return (
            False,
            f"Ollama is not running.\n\nPlease start Ollama and try again (default URL: {OLLAMA_URL}).",
        )
    except requests.exceptions.Timeout:
        return (
            False,
            "Connecting to Ollama timed out. Please check if Ollama is responsive.",
        )
    except requests.RequestException as exc:
        return False, f"Could not connect to Ollama: {str(exc)}"

    if response.status_code != 200:
        return False, f"Ollama returned HTTP status {response.status_code}."

    try:
        data = response.json()
    except Exception:
        return False, "Failed to parse Ollama status response as JSON."

    if not isinstance(data, dict):
        return False, "Unexpected response format from Ollama status endpoint."

    models_raw = data.get("models")
    if not isinstance(models_raw, list):
        return False, "Invalid models list returned by Ollama."

    installed_names: List[str] = []
    for item in models_raw:
        if isinstance(item, dict):
            name = item.get("name", "")
            if isinstance(name, str):
                installed_names.append(name)

    active = get_active_model()
    model_found = any(
        name == active or name.startswith(f"{active}:")
        for name in installed_names
    )

    if not model_found:
        return (
            False,
            f"The required Ollama model is not installed.\n\nPlease run:\nollama pull {OLLAMA_MODEL}",
        )

    return True, f"Local model '{active}' is ready."


def build_explanation_prompt(file_tree: List[str], code_files: Dict[str, str]) -> str:
    """Builds a structured prompt for the local LLM following exact assignment requirements."""
    tree_lines = file_tree[:60]
    tree_text = "\n".join(tree_lines) if tree_lines else "No directory tree available."

    code_sections = []
    for filename, code in code_files.items():
        code_sections.append(f"--- FILE: {filename} ---\n{code}\n")
    code_text = "\n".join(code_sections)

    return f"""You are a software project explainer. Analyze the supplied repository information and source code. Explain the project in simple English for a beginner college student. Do not invent functionality that is not present in the code.

The explanation MUST include these exact headings:
## Project Overview
## Main Technologies
## Main Features
## How It Works
## Important Files
## Simple Explanation

Keep each section concise, direct, and under 3-4 sentences.

### REPOSITORY FILE TREE:
{tree_text}

### SOURCE CODE SAMPLES:
{code_text}
"""


def generate_code_explanation(file_tree: List[str], code_files: Dict[str, str]) -> str:
    """Sends the structured code context to the local Ollama LLM and safely extracts the explanation."""
    is_ready, status_msg = check_ollama_status()
    if not is_ready:
        raise RuntimeError(status_msg)

    active_model = get_active_model()
    prompt = build_explanation_prompt(file_tree, code_files)

    payload = {
        "model": active_model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2,
            "num_predict": 220,
            "num_ctx": 1536,
        },
    }

    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json=payload,
            timeout=TIMEOUT,
        )
    except requests.exceptions.Timeout:
        raise RuntimeError(
            "The local LLM took too long to respond.\nTry analyzing a smaller repository or using a smaller model."
        )
    except requests.exceptions.ConnectionError:
        raise RuntimeError("Ollama is not running.\n\nPlease start Ollama and try again.")
    except requests.RequestException as exc:
        raise RuntimeError(f"Ollama connection error: {str(exc)}")

    if response.status_code != 200:
        raise RuntimeError(f"Ollama returned HTTP error {response.status_code}: {response.text}")

    try:
        data = response.json()
    except Exception:
        raise RuntimeError("Ollama response could not be parsed as JSON.")

    if not isinstance(data, dict):
        raise RuntimeError(
            f"Ollama returned an unexpected data format: expected dict, got {type(data).__name__}"
        )

    if data.get("error"):
        raise RuntimeError(f"Ollama error: {data['error']}")

    explanation_raw = data.get("response")
    if not isinstance(explanation_raw, str) or not explanation_raw.strip():
        raise RuntimeError("The local LLM returned an empty response. Please try again.")

    return explanation_raw.strip()


_GEMINI_MODEL_CACHE: Dict[str, List[str]] = {}


def get_available_gemini_models(clean_key: str) -> List[str]:
    """Queries Google Gemini API dynamically to discover available models for this specific API key."""
    if clean_key in _GEMINI_MODEL_CACHE and _GEMINI_MODEL_CACHE[clean_key]:
        return _GEMINI_MODEL_CACHE[clean_key]

    discovered: List[str] = []
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={clean_key}"
        res = requests.get(url, timeout=8)
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, dict):
                for m in data.get("models", []):
                    if isinstance(m, dict):
                        methods = m.get("supportedGenerationMethods", [])
                        if isinstance(methods, list) and "generateContent" in methods:
                            name = str(m.get("name", "")).replace("models/", "").strip()
                            if name:
                                discovered.append(name)
    except Exception:
        pass

    # Prioritize flash models, then other gemini models
    flash_models = [m for m in discovered if "flash" in m.lower()]
    other_models = [m for m in discovered if "flash" not in m.lower() and "gemini" in m.lower()]
    candidates = flash_models + other_models
    if not candidates and discovered:
        candidates = discovered
    if not candidates:
        candidates = ["gemini-3.8-flash", "gemini-2.5-flash", "gemini-1.5-flash", "gemini-pro"]

    _GEMINI_MODEL_CACHE[clean_key] = candidates
    return candidates


def generate_gemini_explanation(file_tree: List[str], code_files: Dict[str, str], api_key: str) -> str:
    """Generates an explanation using Google Gemini API for standalone cloud deployments."""
    clean_key = api_key.strip().strip('"').strip("'")
    prompt = build_explanation_prompt(file_tree, code_files)
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 450,
        },
    }

    models_to_try = get_available_gemini_models(clean_key)

    errors: List[str] = []
    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={clean_key}"
        try:
            resp = requests.post(url, json=payload, timeout=25)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict):
                    candidates = data.get("candidates", [])
                    if isinstance(candidates, list) and len(candidates) > 0:
                        candidate = candidates[0]
                        if isinstance(candidate, dict):
                            content = candidate.get("content", {})
                            if isinstance(content, dict):
                                parts = content.get("parts", [])
                                if isinstance(parts, list) and len(parts) > 0:
                                    part = parts[0]
                                    if isinstance(part, dict):
                                        text = part.get("text", "")
                                        if text and isinstance(text, str) and text.strip():
                                            return text.strip()
            errors.append(f"{model_name} (HTTP {resp.status_code})")
        except Exception as exc:
            errors.append(f"{model_name} (error: {str(exc)})")

    raise RuntimeError(f"Cloud AI failed on models: {', '.join(errors)}")
