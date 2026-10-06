from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class ExplainRequest(BaseModel):
    repo_url: str = Field(..., description="Public GitHub repository URL")


class ExplainResponse(BaseModel):
    success: bool
    explanation: Optional[str] = None
    error: Optional[str] = None
    files_analyzed: int = 0
    total_files: int = 0
    languages: List[str] = []
    files: List[str] = []


class HealthResponse(BaseModel):
    status: str
    ollama_ready: bool
    model: str
    message: str
