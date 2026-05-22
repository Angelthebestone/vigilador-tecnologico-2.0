# Research: Activación de Workstreams desde Frontend

## Decision 1: Persistencia de overrides de configuración

**Decision**: Archivo JSON local (`config/workstream_overrides.json`) + directorio de archivos de texto (`config/prompt_overrides/`).

**Rationale**: 
- Simplicidad obligatoria — sin base de datos, sin migraciones, sin ORM
- Los flags ya son `bool`, los prompts ya son texto plano — JSON y archivos son naturales
- El mecanismo `.env` existente se preserva como default; el JSON solo almacena deltas
- Rollback trivial: borrar los archivos

**Alternatives considered**:
- SQLite local: overkill para 5 booleanos y 8 strings
- Redis/etcd: requiere infraestructura extra, viola KISS
- Variables de entorno en runtime: no sobreviven reinicios

---

## Decision 2: Sistema de doble capa para prompts

**Decision**: El `FilesystemPromptLoader` busca primero en `config/prompt_overrides/{path}.txt`. Si no existe, usa `prompts/{path}.txt`. El `@lru_cache` se mantiene pero la clave incluye la ruta completa.

**Rationale**:
- Extiende el comportamiento existente sin modificar el mecanismo core
- Cero impacto en performance: el cache sigue funcionando, solo cambia la fuente
- Los placeholders actuales (texto descriptivo) se preservan como defaults — el usuario los reemplaza con templates reales
- Los archivos en `config/prompt_overrides/` son `.gitignore`-eables para no versionar overrides locales

**Alternatives considered**:
- Base de datos para prompts: viola KISS para 8 strings
- API de prompts con versionado: YAGNI — no hay requisito de historial de versiones
- Hot-reload sin cache: rompería performance existente

---

## Decision 3: Arquitectura de componentes frontend para workstreams

**Decision**: Un componente por workstream (`WSASection`, `WSBSection`, etc.) + un wrapper `WorkstreamSection` colapsable. Renderizado condicional basado en `evaluation.ws_a !== null`.

**Rationale**:
- SRP: cada componente renderiza una sola entidad de dominio
- SoC: la lógica de "¿este workstream está activo?" está separada de "¿cómo se ve este workstream?"
- Reutiliza Tailwind existente — sin nuevas dependencias de visualización
- Los datos ya vienen en el `FinalReport.evaluation` — no se necesita fetch extra

**Alternatives considered**:
- Un solo componente `WorkstreamViewer` con switch case: viola SRP, sería un monolito de 1000+ líneas
- Gráficos D3/Canvas para curvas-S y redes: YAGNI en spec 008, se puede agregar después; por ahora texto y badges son suficientes
- Lazy loading por workstream: añade complejidad innecesaria; los datos ya están en memoria

---

## Decision 4: Mock server — refactor modular vs monolito

**Decision**: Refactorizar `mock_server.py` (2072 líneas) en paquete `mock_server/` con módulos: `data/` (branches, workstreams, report), `routes/` (research, config), `sse_emitter.py`, `__main__.py`. El entry point `mock_server.py` se convierte en un thin wrapper.

**Rationale**:
- El archivo actual es inmanejable para agregar datos de workstreams (~500 líneas extra)
- La modularidad permite trabajar en workstreams sin tocar research routes
- Compatibilidad hacia atrás: `python mock_server.py` sigue funcionando igual
- Los datos de workstreams son estáticos y grandes — merecen su propio módulo

**Alternatives considered**:
- Mantener monolito y agregar ~500 líneas: archivo de 2500+ líneas, inmantenible
- Reescribir en Node.js/TS: añade un runtime diferente, rompe compatibilidad
- Usar JSON fixtures: posible, pero Python dicts son más flexibles para datos anidados

---

## Decision 5: Endpoint de evaluación — embebido en report o separado

**Decision**: Extender `GET /research/{id}/report` para incluir campo `evaluation: SessionEvaluation` con datos de workstreams. El endpoint `GET /research/{id}/evaluation` existente se extiende con los mismos datos.

**Rationale**:
- El frontend ya hace `getReport()` al recibir `ReportGenerated` — incluir evaluación ahí evita un segundo fetch
- SC-005 exige que la carga del reporte no aumente >2s — un solo fetch es más rápido que dos
- El endpoint `/evaluation` separado sirve para consultas on-demand sin recargar el reporte completo

**Alternatives considered**:
- Solo endpoint separado: requeriría segundo fetch en el frontend, viola SC-005
- Solo en el reporte: no permitiría consultar evaluación sin el reporte completo (menos flexible)
- GraphQL: YAGNI, añade dependencia innecesaria

---

## Decision 6: Mock server — eventos SSE faltantes

**Decision**: El mock server actual emite 14 tipos de eventos. El spec pide 17. Se agregan: `SessionStarted`, `ClarificationRequested`, `PlanGenerated` al inicio del stream (actualmente solo se devuelven como respuesta REST, no como SSE).

**Rationale**:
- El frontend tiene handlers para estos eventos vía `useSSE.ts` — ya espera recibirlos
- En el backend real, estos eventos se emiten durante el flujo; el mock debe reflejarlo
- Agregarlos no rompe compatibilidad — el frontend simplemente los procesa

**Alternatives considered**:
- Mantener solo REST para sesión/clarificación/plan: inconsistente con el backend real
- Emitir todo por SSE y eliminar endpoints REST: rompería el flujo actual del frontend
