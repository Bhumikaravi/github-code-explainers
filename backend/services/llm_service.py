from __future__ import annotations

from typing import Dict, Iterator, List

from backend.llm import (
    check_ollama_status,
    build_explanation_prompt,
    generate_code_explanation,
    OLLAMA_MODEL,
    OLLAMA_URL,
)


def check_model() -> tuple[bool, str]:
    """Compatibility wrapper checking local Ollama model."""
    return check_ollama_status()


def _build_prompt(file_tree: List[str], code_files: Dict[str, str]) -> str:
    """Compatibility wrapper building prompt with all required headings."""
    return build_explanation_prompt(file_tree, code_files)


def stream_explanation(file_tree: List[str], code_files: Dict[str, str]) -> Iterator[str]:
    """Compatibility generator yielding explanation."""
    result = generate_code_explanation(file_tree, code_files)
    yield result
