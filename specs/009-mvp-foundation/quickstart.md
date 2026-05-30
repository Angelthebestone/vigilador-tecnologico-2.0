# Quickstart — Vigilador 3.0 MVP Foundation (spec 009)

Arranque local del MVP de fundación (F0 + F1): adapter Xiaomimimo, ToolRegistry, HealthMonitor,
OAuthManager, onboarding y listado de tools.

## 1. Prerequisitos

- Python 3.11+, Node 18+, PostgreSQL con extensión `pgvector`.
- Dependencias backend: `pip install -e ".[dev]"`
- Dependencias frontend: `npm install --prefix frontend`

## 2. Variables de entorno

Copiar `.env.example` a `.env` y completar al menos:

```
VT_DATABASE_URL=postgresql+asyncpg://USER:PASS@localhost:5432/vigilancia
VT_XIAOMIMIMO_API_KEY=<tu_api_key>      # platform.xiaomimimo.com
VT_EMBEDDING_API_KEY=<gemini_key>
VT_EMBEDDING_DIMENSIONS=<dim del modelo activo>   # alinear (ver postgres-readiness.md)
```

Defaults relevantes ya provistos: `VT_LLM_DEFAULT=xiaomimimo`,
`VT_XIAOMIMIMO_MODEL=mimo-v2-flash`, `VT_HEALTH_MONITOR_ENABLED=true`.

## 3. Migraciones

Las 5 tablas enterprise (`tool_health`, `oauth_credentials`, `subagents`,
`pending_approvals`, `company_profile`) se aplican automáticamente al arrancar la app
(`database.initialize()` ejecuta `infra/db/migrations/006_mvp_foundation.sql`). No usa Alembic.

## 4. Arranque

```bash
# Backend
uvicorn vigilancia_multiagente.api.app:app --reload --host 0.0.0.0 --port 8000
# Frontend (otra terminal)
npm run dev --prefix frontend
```

## 5. Smoke tests manuales

1. **Health**: `GET http://localhost:8000/health` -> `{"status":"ok"}`.
2. **Login**: navegar a `/enterprise/login`, entrar con `admin` / `admin` (MVP sin hash).
3. **Onboarding**: completar empresa (paso 1) y proveedor LLM (paso 2). En el paso 2 pulsar
   "Probar conectividad" -> debe devolver modelo `mimo-v2-flash` + latencia.
4. **Tools**: `/enterprise/tools` lista el estado de las tools (badges UP/DOWN/UNCONFIGURED).
5. **Metricas**: `GET http://localhost:8000/api/v2/enterprise/metrics` -> texto Prometheus.

## 6. Tests

```bash
pytest tests/enterprise/        # 41 tests backend
npm test --prefix frontend      # tests Vitest (incluye src/enterprise)
```

## 7. Troubleshooting

| Sintoma | Causa probable | Solucion |
|---------|----------------|----------|
| `Xiaomimimo 401` al probar conectividad | API key invalida/ausente | revisar `VT_XIAOMIMIMO_API_KEY`. |
| App no arranca, error pgvector en migracion | `pgvector` no instalado | `CREATE EXTENSION vector;` en la DB. |
| `Unexpected embedding dimension` | `VT_EMBEDDING_DIMENSIONS` != modelo Gemini | alinear la dimension con el modelo activo. |
| HealthMonitor no corre | `VT_HEALTH_MONITOR_ENABLED=false` o sin `tool_registry` en `app.state` | habilitar flag y registrar tools. |
| Frontend build: import no resuelto `@/...` | alias `@` no configurado | verificar `vitest.config.ts` / `tsconfig`. |
| Puerto 8000 en uso (tests de integracion del 2.0) | hay un server corriendo | liberar el puerto o ignorar (esos tests son del 2.0). |

## 8. Deshabilitar enterprise

`VT_HEALTH_MONITOR_ENABLED=false` apaga el monitor. Los routers `/api/v2/enterprise/*` son
aditivos; quitarlos de `api/router.py` deja el 2.0 intacto.
