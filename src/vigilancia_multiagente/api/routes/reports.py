from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from datetime import datetime

router = APIRouter(prefix="/reports", tags=["reports"])

_report_store: dict[str, dict] = {}


def store_report(report_id: str, report: dict) -> None:
    """Store a report variant for later export."""
    _report_store[report_id] = report


@router.get("/{report_id}/export")
async def export_report(report_id: str, format: str = "md"):
    """Export a generated report in the requested format."""
    report = _report_store.get(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if format not in ("md", "html"):
        raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")

    content = _render_markdown(report)
    media_type = "text/markdown" if format == "md" else "text/html"
    ext = "md" if format == "md" else "html"

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{report_id}.{ext}"'},
    )


def _render_markdown(report: dict) -> str:
    """Render a report variant as Markdown."""
    lines = [f"# {report.get('title', 'Report')}"]
    lines.append(f"_Generated: {report.get('generated_at', datetime.utcnow().isoformat())}_\n")

    for section in report.get("sections", []):
        lines.append(f"## {section.get('heading', '')}")
        lines.append(section.get("content", ""))
        lines.append("")

    return "\n".join(lines)
