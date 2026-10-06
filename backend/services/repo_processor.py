from __future__ import annotations

from typing import Dict, List

from backend.github_processor import (
    validate_github_url,
    clone_repository as _clone_repo,
    cleanup_repository,
    scan_and_extract_code,
)


def clone_repository(url: str) -> str:
    """Clones repository and returns repo_path or raises ValueError/RuntimeError."""
    repo_path, err = _clone_repo(url)
    if err:
        raise RuntimeError(err)
    return repo_path


def get_file_tree(repo_path: str) -> List[str]:
    data = scan_and_extract_code(repo_path)
    return list(data.get("file_tree", []))


def extract_code(repo_path: str) -> Dict[str, str]:
    data = scan_and_extract_code(repo_path)
    return dict(data.get("code_files", {}))
