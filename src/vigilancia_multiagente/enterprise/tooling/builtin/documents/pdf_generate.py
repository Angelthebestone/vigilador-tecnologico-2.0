"""pdf_generate — Tool Tier 1 para generación de PDF (FR-021).

Genera documentos PDF desde HTML usando WeasyPrint.
Implementa el protocolo ToolWrapper.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from vigilancia_multiagente.enterprise.tooling.tool_wrapper import HealthcheckResult


class PdfGenerateTool:
    """Genera documentos PDF desde contenido HTML."""

    name: str = "pdf_generate"
    domain: str = "documents"
    is_external_mcp: bool = False
    requires_auth: bool = False

    async def healthcheck(self) -> HealthcheckResult:
        """Verifica que WeasyPrint está disponible."""
        try:
            import weasyprint  # noqa: F401

            return HealthcheckResult(status="UP")
        except ImportError:
            return HealthcheckResult(status="DOWN", error="weasyprint not installed")

    async def execute(self, tool_name: str, args: dict[str, Any]) -> dict[str, object]:
        """Genera un PDF desde HTML.

        Args esperados en `args`:
            html_content: str — HTML a convertir a PDF.
            css_path: str | None — hoja de estilos opcional.
            output_path: str — ruta destino del PDF.

        Returns:
            dict con output_path (str) y page_count (int).
        """
        html_content = args.get("html_content")
        if not html_content or not isinstance(html_content, str):
            return {"error": "Missing or invalid 'html_content' argument"}

        output_path = args.get("output_path")
        if not output_path or not isinstance(output_path, str):
            return {"error": "Missing or invalid 'output_path' argument"}

        try:
            from weasyprint import HTML
        except ImportError:
            return {"error": "weasyprint is not installed; cannot generate PDF"}

        css_path = args.get("css_path")
        stylesheets = None
        if css_path and Path(css_path).exists():
            from weasyprint import CSS

            stylesheets = [CSS(filename=css_path)]

        dest = Path(output_path)
        dest.parent.mkdir(parents=True, exist_ok=True)

        doc = HTML(string=html_content).render(stylesheets=stylesheets)
        doc.write_pdf(str(dest))
        page_count = len(doc.pages)

        return {"output_path": str(dest), "page_count": page_count}
