import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def test_required_files_exist():
    required = [
        "backend/main.py",
        "backend/models.py",
        "backend/github_processor.py",
        "backend/llm.py",
        "backend/services/repo_processor.py",
        "backend/services/llm_service.py",
        "frontend/app.py",
        "requirements.txt",
        ".gitignore",
        ".env.example",
        "README.md",
    ]
    assert all((ROOT / p).exists() for p in required), "Not all required project files exist."


def test_prompt_has_required_sections():
    from backend.llm import build_explanation_prompt

    prompt = build_explanation_prompt(["main.py"], {"main.py": "print('hello world')"})
    for section in [
        "## Project Overview",
        "## Main Technologies",
        "## Main Features",
        "## How It Works",
        "## Important Files",
        "## Simple Explanation",
    ]:
        assert section in prompt, f"Missing section '{section}' in LLM prompt."


def test_github_url_validation():
    from backend.github_processor import validate_github_url

    # Valid URLs
    valid, _ = validate_github_url("https://github.com/Bhumikaravi/github-code-explainers")
    assert valid is True

    valid, _ = validate_github_url("https://github.com/fastapi/fastapi.git")
    assert valid is True

    # Invalid URLs
    invalid, err = validate_github_url("hello")
    assert invalid is False
    assert "valid" in err.lower()

    invalid, err = validate_github_url("https://google.com")
    assert invalid is False

    invalid, err = validate_github_url("https://github.com/onlyuser")
    assert invalid is False


def test_no_gemini_in_requirements():
    req_text = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert "google-genai" not in req_text
    assert "gemini" not in req_text.lower()
