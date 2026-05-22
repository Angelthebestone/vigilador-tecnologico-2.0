# Deprecated: use mock_server/ package instead. Kept for backward compat.
"""Thin wrapper that delegates to the modular mock_server package."""

from mock_server import app

if __name__ == "__main__":
    import uvicorn
    from mock_server.routes.config import get_active_workstreams
    from mock_server.data.report import QUERY_EJEMPLO, SESSION_ID

    config = get_active_workstreams()
    active = [k.upper().replace("WS_", "WS-") for k, v in config.items() if v]

    print("=" * 60)
    print("  Vigilador Tecnológico 2.0 — Mock Server")
    print("=" * 60)
    print("  URL base API : http://localhost:8000/api/v2")
    print(f"  Tema demo    : {QUERY_EJEMPLO}")
    print(f"  Session ID   : {SESSION_ID}")
    if active:
        print(f"  Workstreams  : {', '.join(active)}")
    print()
    print("  Flujo de prueba:")
    print("   1. Abre el frontend (npm run dev en frontend/)")
    print("   2. Escribe cualquier consulta en el chat")
    print("   3. Responde las 3 preguntas de aclaración")
    print("   4. Aprueba el plan de investigación")
    print("   5. Observa el progreso en tiempo real (~30s)")
    print("   6. Explora el reporte, grafo y métricas")
    print("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
