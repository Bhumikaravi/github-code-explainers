from __future__ import annotations

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.github_processor import (
    cleanup_repository,
    clone_repository,
    fetch_repository_fast,
    scan_and_extract_code,
    validate_github_url,
)
from backend.llm import (
    OLLAMA_MODEL,
    check_ollama_status,
    generate_code_explanation,
    get_active_model,
)
from backend.models import ExplainRequest, ExplainResponse, HealthResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("backend.main")

app = FastAPI(
    title="Local GitHub Repository Code Explainer API",
    description="Backend API to clone GitHub repositories, process source files, and generate explanations with a local Ollama LLM.",
    version="1.0.0",
)

# Enable CORS for frontend flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["General"])
def root():
    return {
        "name": "Local GitHub Repository Code Explainer API",
        "status": "online",
        "docs_url": "/docs",
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check():
    """Checks whether the backend and the local Ollama LLM are reachable and ready."""
    is_ready, message = check_ollama_status()
    active_model = get_active_model()
    return HealthResponse(
        status="ok" if is_ready else "degraded",
        ollama_ready=is_ready,
        model=active_model,
        message=message,
    )


@app.post("/explain", response_model=ExplainResponse, tags=["Explainer"])
def explain_repository(request: ExplainRequest):
    """Clones a GitHub repository, extracts code, and generates an explanation via local Ollama LLM."""
    url = str(request.repo_url).strip()
    logger.info("Received explanation request for URL: %s", url)

    # 1. Validate GitHub URL
    is_valid, validation_err = validate_github_url(url)
    if not is_valid:
        logger.warning("Invalid GitHub URL provided: %s - %s", url, validation_err)
        return ExplainResponse(
            success=False,
            error=validation_err,
        )

    # 2. Check if local Ollama LLM is available before doing work
    ollama_ready, ollama_msg = check_ollama_status()
    if not ollama_ready:
        logger.error("Ollama health check failed: %s", ollama_msg)
        return ExplainResponse(
            success=False,
            error=ollama_msg,
        )

    repo_path: str | None = None
    try:
        # 3. Attempt fast extraction via GitHub API (sub-second)
        logger.info("Attempting fast extraction for: %s", url)
        extracted = fetch_repository_fast(url)

        if not extracted or not extracted.get("success"):
            # Fallback to local clone
            logger.info("Cloning repository: %s", url)
            repo_path, clone_err = clone_repository(url)
            if clone_err:
                logger.error("Clone error: %s", clone_err)
                return ExplainResponse(
                    success=False,
                    error=clone_err,
                )

            logger.info("Scanning and extracting source files from %s", repo_path)
            extracted = scan_and_extract_code(repo_path)
            if not extracted.get("success"):
                error_msg = str(extracted.get("error", "No supported source-code files were found in this repository."))
                logger.warning("Code extraction issue: %s", error_msg)
                return ExplainResponse(
                    success=False,
                    error=error_msg,
                    total_files=int(extracted.get("total_files", 0)),
                )

        file_tree = list(extracted.get("file_tree", []))
        code_files = dict(extracted.get("code_files", {}))
        files_analyzed = int(extracted.get("files_analyzed", 0))
        total_files = int(extracted.get("total_files", 0))
        languages = list(extracted.get("languages", []))

        # 5. Generate explanation using Local Ollama LLM
        logger.info(
            "Sending %d files (%d total found) to local LLM (%s)...",
            files_analyzed,
            total_files,
            OLLAMA_MODEL,
        )
        explanation = generate_code_explanation(file_tree, code_files)
        logger.info("Successfully generated explanation from local LLM.")

        return ExplainResponse(
            success=True,
            explanation=explanation,
            files_analyzed=files_analyzed,
            total_files=total_files,
            languages=languages,
            files=file_tree,
        )

    except Exception as exc:
        logger.exception("Unexpected error while explaining repository: %s", exc)
        return ExplainResponse(
            success=False,
            error=f"Processing error: {str(exc)}",
        )
    finally:
        if repo_path:
            logger.info("Cleaning up temporary clone directory: %s", repo_path)
            cleanup_repository(repo_path)
