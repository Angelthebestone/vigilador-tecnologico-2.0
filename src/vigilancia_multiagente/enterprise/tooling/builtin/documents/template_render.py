"""template_render — Tool Tier 1 para renderizado de templates (FR-019).

Renderiza templates Jinja2 en formatos MD, HTML o DOCX.
Implementa el protocolo ToolWrapper.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from vigilancia_multiagente.enterprise.tooling.tool_wrapper import HealthcheckResult

# Directorio base de templates (configurable via constructor)
_DEFAULT_TEMPLATES_DIR = Path("config/templates")


class TemplateRenderTool:
    """Renderiza templates Jinja2 con variables proporcionadas."""

    name: str = "template_render"
    domain: str = "documents"
    is_external_mcp: bool = False
    requires_auth: bool = False

    def __init__(self, templates_dir: Path | None = None) -> None:
        self._templates_dir = templates_dir or _DEFAULT_TEMPLATES_DIR
        self._env: Environment | None = None

    def _get_env(self) -> Environment:
        if self._env is None:
            self._env = Environment(
                loader=FileSystemLoader(str(self._templates_dir)),
                autoescape=False,
            )
        return self._env

    async def healthcheck(self) -> HealthcheckResult:
        """Verifica que el directorio de templates existe."""
        if self._templates_dir.is_dir():
            return HealthcheckResult(status="UP")
        return HealthcheckResult(
            status="DOWN",
            error=f"Templates directory not found: {self._templates_dir}",
        )

    async def execute(self, tool_name: str, args: dict[str, Any]) -> dict[str, object]:
        """Renderiza un template con las variables dadas.

        Args esperados en `args`:
            template_name: str — nombre del template en templates_dir.
            variables: dict[str, object] — datos a interpolar.
            output_format: str — uno de: md, html, docx.

        Returns:
            dict con rendered_content (str) y output_path (str | None).
        """
        template_name = args.get("template_name")
        if not template_name or not isinstance(template_name, str):
            return {"error": "Missing or invalid 'template_name' argument"}

        variables: dict[str, object] = args.get("variables", {})  # type: ignore[assignment]
        if not isinstance(variables, dict):
            return {"error": "'variables' must be a dict"}

        output_format = str(args.get("output_format", "md")).lower()
        if output_format not in ("md", "html", "docx"):
            return {"error": f"Invalid output_format '{output_format}'; must be md, html, or docx"}

        env = self._get_env()
        try:
            template = env.get_template(template_name)
        except TemplateNotFound:
            return {"error": f"Template not found: '{template_name}' in {self._templates_dir}"}

        rendered_content = template.render(**variables)

        output_path: str | None = None
        if args.get("output_path"):
            output_path = str(args["output_path"])
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_text(rendered_content, encoding="utf-8")

        return {"rendered_content": rendered_content, "output_path": output_path}
