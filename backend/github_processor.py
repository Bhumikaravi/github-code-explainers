from __future__ import annotations

import os
import re
import shutil
import stat
import tempfile
from pathlib import Path
from typing import Dict, List, Set, Tuple
from urllib.parse import urlparse

from git import Repo
from git.exc import GitCommandError

# Directories that should never be analyzed
IGNORED_DIRS: Set[str] = {
    ".git",
    ".github",
    "node_modules",
    "venv",
    ".venv",
    "env",
    "ENV",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "dist",
    "build",
    "coverage",
    ".idea",
    ".vscode",
    ".streamlit",
    "bin",
    "obj",
}

# Recognized source code extensions and language labels
LANGUAGE_MAP: Dict[str, str] = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript (React)",
    ".ts": "TypeScript",
    ".tsx": "TypeScript (React)",
    ".java": "Java",
    ".c": "C",
    ".cpp": "C++",
    ".h": "C/C++ Header",
    ".hpp": "C++ Header",
    ".cs": "C#",
    ".go": "Go",
    ".rs": "Rust",
    ".php": "PHP",
    ".rb": "Ruby",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".html": "HTML",
    ".css": "CSS",
    ".sql": "SQL",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".xml": "XML",
    ".md": "Markdown",
    ".txt": "Text",
    ".toml": "TOML",
    ".sh": "Shell",
}

# Priority filenames that explain project structure best
PRIORITY_FILES: List[str] = [
    "README.md",
    "requirements.txt",
    "package.json",
    "pyproject.toml",
    "main.py",
    "app.py",
    "server.py",
    "index.js",
    "index.ts",
]

MAX_FILES_TO_ANALYZE = 10
MAX_FILE_CHARS = 2500
MAX_TOTAL_CHARS = 9000


def validate_github_url(url: str) -> Tuple[bool, str]:
    """Validates the input string to ensure it is a valid public GitHub repository URL."""
    if not url or not isinstance(url, str):
        return False, "Please enter a valid GitHub repository URL."

    cleaned = url.strip()
    if not (cleaned.startswith("https://github.com/") or cleaned.startswith("http://github.com/")):
        return False, "Please enter a valid GitHub repository URL (e.g. https://github.com/owner/repository)."

    parsed = urlparse(cleaned)
    parts = [p for p in parsed.path.strip("/").split("/") if p]
    if len(parts) < 2:
        return False, "Please enter a complete GitHub repository URL containing username and repository name."

    # Repo name should not be blank or just .git
    repo_name = parts[1].replace(".git", "").strip()
    if not repo_name:
        return False, "Please enter a valid GitHub repository URL."

    return True, ""


def _remove_readonly(func, path, exc_info):
    """Windows-safe handler to remove read-only attribute on locked Git files."""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass


def cleanup_repository(repo_path: str | None) -> None:
    """Safely delete cloned temporary repository files."""
    if repo_path and os.path.exists(repo_path):
        try:
            shutil.rmtree(repo_path, onerror=_remove_readonly)
        except Exception:
            pass


def clone_repository(url: str) -> Tuple[str, str]:
    """Clones a public GitHub repository into a temporary directory.

    Returns:
        (repo_path, error_message): repo_path is non-empty on success; error_message is non-empty on failure.
    """
    is_valid, validation_err = validate_github_url(url)
    if not is_valid:
        return "", validation_err

    target = tempfile.mkdtemp(prefix="github_repo_")
    clean_url = url.strip().rstrip("/")
    clone_url = clean_url if clean_url.endswith(".git") else f"{clean_url}.git"

    try:
        Repo.clone_from(clone_url, target, depth=1)
        return target, ""
    except GitCommandError as exc:
        cleanup_repository(target)
        msg = str(exc).lower()
        if "repository not found" in msg or "not found" in msg or "404" in msg:
            return "", "Repository not found. Please check the GitHub URL."
        if (
            "authentication failed" in msg
            or "terminal prompts disabled" in msg
            or "could not read username" in msg
            or "permission denied" in msg
        ):
            return "", "This repository may be private. Please use a public repository or configure authentication."
        return "", f"Git clone failed: {str(exc)}"
    except Exception as exc:
        cleanup_repository(target)
        return "", f"Git clone failure: {str(exc)}"


def _is_priority_file(rel_path: str) -> bool:
    name = Path(rel_path).name
    if name in PRIORITY_FILES:
        return True
    if rel_path.startswith("src/") or rel_path.startswith("backend/") or rel_path.startswith("frontend/"):
        return True
    return False


def scan_and_extract_code(repo_path: str) -> Dict[str, object]:
    """Scans the cloned repository, identifies relevant source files, and extracts code with size limits.

    Returns a dict with:
        - "success": bool
        - "error": str
        - "file_tree": List[str]
        - "code_files": Dict[str, str]
        - "files_analyzed": int
        - "total_files": int
        - "languages": List[str]
        - "skipped_count": int
    """
    root = Path(repo_path)
    all_candidate_files: List[Path] = []

    # 1. Walk repository and filter out ignored directories
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in IGNORED_DIRS for part in path.parts):
            continue
        if path.suffix.lower() in LANGUAGE_MAP:
            all_candidate_files.append(path)

    total_supported_files = len(all_candidate_files)
    if total_supported_files == 0:
        return {
            "success": False,
            "error": "No supported source-code files were found in this repository.",
            "file_tree": [],
            "code_files": {},
            "files_analyzed": 0,
            "total_files": 0,
            "languages": [],
            "skipped_count": 0,
        }

    # Relative paths for tree view
    file_tree = sorted(
        str(p.relative_to(repo_path)).replace(os.sep, "/") for p in all_candidate_files
    )

    # Sort files: priority files first, then smaller files
    def sort_key(p: Path):
        rel = str(p.relative_to(repo_path)).replace(os.sep, "/")
        is_prio = 0 if _is_priority_file(rel) else 1
        return (is_prio, p.name)

    sorted_files = sorted(all_candidate_files, key=sort_key)

    extracted_code: Dict[str, str] = {}
    languages_detected: Set[str] = set()
    total_chars = 0
    skipped_count = 0

    for path in sorted_files:
        if len(extracted_code) >= MAX_FILES_TO_ANALYZE:
            break
        if total_chars >= MAX_TOTAL_CHARS:
            break

        rel_str = str(path.relative_to(repo_path)).replace(os.sep, "/")
        suffix = path.suffix.lower()

        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            skipped_count += 1
            continue

        stripped = content.strip()
        if not stripped:
            skipped_count += 1
            continue

        # Add detected language
        lang_name = LANGUAGE_MAP.get(suffix, suffix)
        languages_detected.add(lang_name)

        # Truncate large single file
        truncated = stripped[:MAX_FILE_CHARS]
        remaining = MAX_TOTAL_CHARS - total_chars
        truncated = truncated[:remaining]

        extracted_code[rel_str] = truncated
        total_chars += len(truncated)

    if not extracted_code:
        return {
            "success": False,
            "error": "No readable source-code files were found in this repository.",
            "file_tree": file_tree,
            "code_files": {},
            "files_analyzed": 0,
            "total_files": total_supported_files,
            "languages": sorted(list(languages_detected)),
            "skipped_count": skipped_count,
        }

    return {
        "success": True,
        "error": "",
        "file_tree": file_tree[:200],
        "code_files": extracted_code,
        "files_analyzed": len(extracted_code),
        "total_files": total_supported_files,
        "languages": sorted(list(languages_detected)),
        "skipped_count": skipped_count,
    }
