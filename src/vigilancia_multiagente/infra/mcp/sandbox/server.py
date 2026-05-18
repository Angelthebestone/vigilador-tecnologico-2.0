"""Sandbox MCP server — executes user-submitted Python code in-process.

El servidor corre como proceso MCP separado del backend (ahí reside el
aislamiento de proceso). El código del usuario se ejecuta con ``exec()`` en
un hilo con timeout: anidar un subproceso bajo el loop JSON-RPC del SDK MCP
cuelga en Windows, así que se evita el anidamiento.
"""

import asyncio
import base64
import importlib.metadata as md
import io
import json
import os
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from contextlib import redirect_stderr, redirect_stdout
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import aiofiles
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server

_PROJECT_ROOT = Path(__file__).resolve().parents[5]
_LOG_DIR = _PROJECT_ROOT / "logs" / "sandbox"

app = Server("sandbox-mcp")

# Referencias fuertes a tareas fire-and-forget: sin esto el GC puede
# recolectar la tarea de audit log antes de que termine de escribir.
_background_tasks: set[asyncio.Task] = set()


def _ensure_log_dir() -> None:
    _LOG_DIR.mkdir(parents=True, exist_ok=True)


async def _append_audit_log(entry: dict[str, Any]) -> None:
    _ensure_log_dir()
    log_path = _LOG_DIR / "audit.log"
    line = json.dumps(entry, ensure_ascii=False, default=str) + "\n"
    async with aiofiles.open(log_path, mode="a", encoding="utf-8") as f:
        await f.write(line)


# ── Tool list ─────────────────────────────────────────────────────────────


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="execute_code",
            description=(
                "Execute Python code in an isolated subprocess. "
                "Returns stdout, stderr, and execution result."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Python code to execute",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Max execution time in seconds",
                        "default": 120,
                    },
                },
                "required": ["code"],
            },
        ),
        types.Tool(
            name="list_libraries",
            description="List available pre-loaded libraries with versions",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        types.Tool(
            name="visualize",
            description=("Generate a visualization from data. Returns base64-encoded image."),
            inputSchema={
                "type": "object",
                "properties": {
                    "data": {
                        "type": "object",
                        "description": "Chart data (keys depend on plot_type)",
                    },
                    "plot_type": {
                        "type": "string",
                        "enum": [
                            "line",
                            "bar",
                            "scatter",
                            "histogram",
                            "heatmap",
                            "pie",
                        ],
                        "description": "Type of chart",
                    },
                    "format": {
                        "type": "string",
                        "enum": ["png", "svg", "pdf"],
                        "description": "Output format",
                        "default": "png",
                    },
                },
                "required": ["data", "plot_type"],
            },
        ),
    ]


# ── call_tool dispatcher ─────────────────────────────────────────────────


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    try:
        if name == "execute_code":
            result = await _execute_code(
                arguments.get("code", ""),
                arguments.get("timeout", 120),
            )
        elif name == "list_libraries":
            result = await _list_libraries()
        elif name == "visualize":
            result = await _visualize(
                arguments.get("data", {}),
                arguments.get("plot_type", ""),
                arguments.get("format", "png"),
            )
        else:
            result = {"status": "error", "error": f"Unknown tool: {name}"}
        return [
            types.TextContent(
                type="text",
                text=json.dumps(result, ensure_ascii=False, default=str),
            )
        ]
    except (TimeoutError, subprocess.CalledProcessError, ValueError, OSError) as e:
        return [
            types.TextContent(
                type="text",
                text=json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False),
            )
        ]


# ── T016: execute_code ───────────────────────────────────────────────────


async def _execute_code(code: str, timeout: int) -> dict[str, Any]:
    start = time.monotonic()
    code_preview = code[:200]
    error: str | None = None
    success = False
    result: dict[str, Any] = {"status": "error", "error": "Execution failed"}

    try:
        with tempfile.TemporaryDirectory(prefix="sandbox_") as tmpdir:
            # Ejecución IN-PROCESS con exec() en un hilo, NO subprocess.
            # Este servidor ya corre como proceso MCP separado del backend
            # (ahí está el aislamiento de proceso); anidar un subproceso bajo
            # el loop JSON-RPC del SDK cuelga en Windows. exec() en un thread
            # con timeout evita el anidamiento y mantiene cwd aislado en un
            # tempdir efímero. Globals acotados; stdout/stderr capturados.
            out_buf = io.StringIO()
            err_buf = io.StringIO()
            exec_globals: dict[str, Any] = {
                "__name__": "__sandbox__",
                "__builtins__": __builtins__,
            }

            def _run_code() -> None:
                prev_cwd = os.getcwd()
                try:
                    os.chdir(tmpdir)
                    with redirect_stdout(out_buf), redirect_stderr(err_buf):
                        exec(compile(code, "<sandbox>", "exec"), exec_globals)
                finally:
                    os.chdir(prev_cwd)

            timed_out = False
            run_error: BaseException | None = None
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(_run_code)
                try:
                    future.result(timeout=timeout)
                except FuturesTimeout:
                    timed_out = True
                except BaseException as exc:
                    run_error = exc

            if timed_out:
                error = f"Execution timed out after {timeout}s"
                result = {"status": "error", "error": error}
            elif run_error is not None:
                error = f"{type(run_error).__name__}: {run_error}"
                result = {
                    "status": "error",
                    "error": error,
                    "stdout": out_buf.getvalue(),
                    "stderr": err_buf.getvalue() or error,
                    "returncode": 1,
                }
            else:
                success = True
                result = {
                    "status": "success",
                    "stdout": out_buf.getvalue(),
                    "stderr": err_buf.getvalue(),
                    "returncode": 0,
                }

            result["duration_ms"] = int((time.monotonic() - start) * 1000)
    except Exception as e:
        error = str(e)
        result = {
            "status": "error",
            "error": error,
            "duration_ms": int((time.monotonic() - start) * 1000),
        }
    finally:
        task = asyncio.create_task(
            _append_audit_log(
                {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "code_preview": code_preview,
                    "duration_ms": int((time.monotonic() - start) * 1000),
                    "success": success,
                    "error": error,
                }
            )
        )
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)

    return result


# ── T017: list_libraries ─────────────────────────────────────────────────


async def _list_libraries() -> dict[str, Any]:
    packages = [
        "matplotlib",
        "numpy",
        "pandas",
        "scipy",
        "scikit-learn",
        "scienceplots",
    ]
    libs: dict[str, str | None] = {}
    for pkg in packages:
        try:
            libs[pkg] = md.version(pkg)
        except md.PackageNotFoundError:
            libs[pkg] = None
    return {"status": "success", "libraries": libs}


# ── T018: visualize ──────────────────────────────────────────────────────


async def _visualize(data: dict, plot_type: str, fmt: str) -> dict[str, Any]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if fmt == "svg":
        plt.rcParams["svg.fonttype"] = "none"

    try:
        import scienceplots  # noqa: F401

        plt.style.use("science")
        plt.rcParams["text.usetex"] = False
    except Exception:
        try:
            plt.style.use("seaborn-v0_8-whitegrid")
        except Exception:
            plt.style.use("default")

    fig, ax = plt.subplots(figsize=(8, 5))

    try:
        if plot_type == "line":
            ax.plot(
                data.get("x", []),
                data.get("y", []),
                marker="o",
                linestyle="-",
            )
            ax.set_title(data.get("title", "Line Plot"))
            ax.set_xlabel(data.get("xlabel", "X"))
            ax.set_ylabel(data.get("ylabel", "Y"))
            ax.grid(True, alpha=0.3)

        elif plot_type == "bar":
            labels = data.get("labels", [])
            values = data.get("values", [])
            ax.bar(labels, values)
            ax.set_title(data.get("title", "Bar Chart"))
            ax.set_xlabel(data.get("xlabel", ""))
            ax.set_ylabel(data.get("ylabel", ""))
            ax.tick_params(axis="x", rotation=45)

        elif plot_type == "scatter":
            ax.scatter(
                data.get("x", []),
                data.get("y", []),
                alpha=0.7,
            )
            ax.set_title(data.get("title", "Scatter Plot"))
            ax.set_xlabel(data.get("xlabel", "X"))
            ax.set_ylabel(data.get("ylabel", "Y"))
            ax.grid(True, alpha=0.3)

        elif plot_type == "histogram":
            ax.hist(
                data.get("data", []),
                bins=data.get("bins", 10),
                edgecolor="white",
                alpha=0.7,
            )
            ax.set_title(data.get("title", "Histogram"))
            ax.set_xlabel(data.get("xlabel", "Value"))
            ax.set_ylabel(data.get("ylabel", "Frequency"))

        elif plot_type == "heatmap":
            matrix = data.get("matrix", [[]])
            xticklabels = data.get("xticklabels")
            yticklabels = data.get("yticklabels")
            im = ax.imshow(matrix, cmap="viridis", aspect="auto")
            fig.colorbar(im, ax=ax)
            ax.set_title(data.get("title", "Heatmap"))
            if xticklabels:
                ax.set_xticks(range(len(xticklabels)))
                ax.set_xticklabels(xticklabels, rotation=45, ha="right")
            if yticklabels:
                ax.set_yticks(range(len(yticklabels)))
                ax.set_yticklabels(yticklabels)

        elif plot_type == "pie":
            ax.pie(
                data.get("values", []),
                labels=data.get("labels", []),
                autopct="%1.1f%%",
                startangle=90,
            )
            ax.set_title(data.get("title", "Pie Chart"))

        else:
            return {"status": "error", "error": f"Unknown plot_type: {plot_type}"}

        fig.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format=fmt, dpi=150)
        buf.seek(0)
        encoded = base64.b64encode(buf.read()).decode("ascii")
        return {"status": "success", "image": encoded, "format": fmt}
    except Exception as e:
        return {"status": "error", "error": str(e)}
    finally:
        plt.close(fig)


# ── Entry point ───────────────────────────────────────────────────────────


async def main() -> None:
    _ensure_log_dir()
    async with stdio_server() as streams:
        await app.run(
            streams[0],
            streams[1],
            InitializationOptions(
                server_name="sandbox-mcp",
                server_version="1.0.0",
                capabilities=app.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
