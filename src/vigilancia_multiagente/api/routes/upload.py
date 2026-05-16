"""POST /upload/document — upload a file and convert to Markdown via Markitdown MCP."""

import logging
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile

from vigilancia_multiagente.api.dependencies import (
    markitdown_execution_client,
    provider_registry,
)
from vigilancia_multiagente.infra.mcp.markitdown_mcp import MarkitdownProvider

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["upload"])

UPLOADS_DIR = Path(__file__).resolve().parents[4] / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = frozenset({
    "pdf", "docx", "pptx", "xlsx", "html", "csv",
    "json", "xml", "png", "jpg", "jpeg",
})

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


@router.post("/document")
async def upload_document(file: UploadFile):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: .{ext}",
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File exceeds 50 MB limit")

    tmp_path = UPLOADS_DIR / file.filename
    try:
        tmp_path.write_bytes(content)
        file_uri = tmp_path.as_uri()

        markitdown = MarkitdownProvider(
            execution_client=markitdown_execution_client,
            provider_registry=provider_registry,
        )
        result = await markitdown.convert_to_markdown(file_uri)

        if not result.get("success"):
            raise HTTPException(
                status_code=502,
                detail=result.get("error", "Markitdown conversion failed"),
            )

        return {
            "markdown": result["content"],
            "format": result.get("format", ext),
            "filename": file.filename,
        }
    finally:
        if tmp_path.exists():
            try:
                os.unlink(tmp_path)
            except OSError:
                logger.warning("Failed to clean up temp file: %s", tmp_path)
