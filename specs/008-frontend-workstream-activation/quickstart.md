# Quickstart: Activación de Workstreams desde Frontend

## Desarrollo con mock server

```bash
# Terminal 1 — Mock server (simula backend completo con workstreams)
cd frontend
python ../mock_server.py
# → http://localhost:8000

# Terminal 2 — Frontend
cd frontend
npm run dev
# → http://localhost:5173
```

El frontend se conecta al mock server automáticamente (`VITE_API_BASE_URL=http://localhost:8000`).

## Flujo de prueba

1. **Activar workstreams**: Ve a la pestaña "Configuración" (ícono ⚙️), activa los toggles WS-A y WS-E, guarda.
2. **Iniciar investigación**: En la pestaña "Chat", escribe una query y haz clic en "Iniciar investigación".
3. **Ver workstreams en acción**: Durante la ejecución, los badges de workstreams aparecen junto al estado de la sesión.
4. **Ver resultados**: Al finalizar, el reporte muestra secciones colapsables "Source Quality" y "Output Assurance" con datos simulados.

## Desarrollo con backend real

```bash
# Con workstreams activados
VT_EVAL_WS_A_ENABLED=true VT_EVAL_WS_E_ENABLED=true uvicorn main:app
```

Los toggles en la UI escriben `config/workstream_overrides.json`. Si el archivo existe, sus valores prevalecen sobre `.env`.

## Estructura de archivos

```
config/
├── workstream_overrides.json     # Flags modificados desde UI
└── prompt_overrides/             # Prompts modificados desde UI
    └── assumption_detection.txt  # (ejemplo de override)

frontend/src/
├── types/evaluation.ts           # Tipos de spec 007 para frontend
├── state/configStore.ts          # Store de configuración (Zustand)
├── api/evaluation.ts             # Fetch functions para endpoints
└── analysis/
    ├── ConfigView.tsx             # Pestaña de configuración
    ├── WorkstreamToggles.tsx      # 5 toggles con tooltips
    ├── PromptEditor.tsx           # Editor de prompts
    ├── WorkstreamIndicator.tsx    # Badges de workstreams activos
    ├── WorkstreamSection.tsx      # Wrapper colapsable
    ├── WSASection.tsx             # Visualización WS-A
    ├── WSBSection.tsx             # Visualización WS-B
    ├── WSCSection.tsx             # Visualización WS-C
    ├── WSDSection.tsx             # Visualización WS-D
    └── WSESection.tsx             # Visualización WS-E
```

## Rollback

Para revertir a comportamiento pre-008:
```bash
rm config/workstream_overrides.json
rm -rf config/prompt_overrides/
```
Los flags de `.env` vuelven a ser la única fuente de verdad.
