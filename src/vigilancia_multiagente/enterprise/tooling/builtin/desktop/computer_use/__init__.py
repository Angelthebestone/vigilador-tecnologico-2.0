"""Computer use submodule — exposes ``ComputerUseTool`` to the registry."""

from vigilancia_multiagente.enterprise.tooling.builtin.desktop.computer_use.backend import (
    ActionResult,
    CaptureResult,
    ComputerUseBackend,
    UIElement,
)
from vigilancia_multiagente.enterprise.tooling.builtin.desktop.computer_use.schema import (
    COMPUTER_USE_SCHEMA,
    get_computer_use_schema,
)
from vigilancia_multiagente.enterprise.tooling.builtin.desktop.computer_use.tool import (
    ComputerUseTool,
    reset_session_approvals,
    set_approval_callback,
)
from vigilancia_multiagente.enterprise.tooling.builtin.desktop.computer_use.windows_backend import (
    WindowsBackend,
)

__all__ = [
    "COMPUTER_USE_SCHEMA",
    "ActionResult",
    "CaptureResult",
    "ComputerUseBackend",
    "ComputerUseTool",
    "UIElement",
    "WindowsBackend",
    "get_computer_use_schema",
    "reset_session_approvals",
    "set_approval_callback",
]
