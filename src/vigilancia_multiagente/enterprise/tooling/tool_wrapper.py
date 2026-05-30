"""Contrato de tool del Vigilador 3.0 (T015).

`ToolWrapper` es el Protocol que toda tool (interna o MCP externa) implementa para
ser registrable en el `ToolRegistry` y monitoreada por el `HealthMonitor`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class HealthcheckResult:
    """Resultado de un healthcheck de tool.

    Attributes:
        status: Estado resultante ("UP", "DOWN", "UNCONFIGURED", "UNKNOWN").
        latency_ms: Latencia del chequeo en milisegundos (None si no aplica).
        error: Mensaje de error si el chequeo falló (None si fue exitoso).
    """

    status: str
    latency_ms: float | None = None
    error: str | None = None


@runtime_checkable
class ToolWrapper(Protocol):
    """Contrato de una tool registrable.

    Atributos declarativos (leídos por el registry para gating y catálogo) y
    dos operaciones async: el healthcheck (lo invoca el HealthMonitor) y la
    ejecución real de la herramienta.
    """

    name: str
    domain: str
    is_external_mcp: bool
    requires_auth: bool

    async def healthcheck(self) -> HealthcheckResult:
        """Comprueba disponibilidad de la tool sin efectos secundarios."""
        ...

    async def execute(self, tool_name: str, args: dict[str, object]) -> dict[str, object]:
        """Ejecuta una operación concreta de la tool."""
        ...
