# F0 — Plan de Rollback por Fase (F0-F5)

**Fuente**: `plan vigilador 3.0/07-migracion-2.0-a-3.0.md` (sección "Plan de rollback por fase")
**Fecha**: 2026-05-29
**Principio**: en cualquier fase, la reversión deja el 2.0 funcionando idéntico al baseline registrado en `docs/f0-baseline.md`.

---

## Tabla resumen

| Fase | Riesgo principal | Complejidad de reversión | Tiempo estimado |
|---|---|---|---|
| F0 | Supuesto desmentido | Trivial | < 5 min |
| F1 | Schema migration falla | Baja | < 30 min |
| F2 | TurboVecIndex corrupto | Media | < 1h |
| F3a | Tool específica rota | Baja | < 5 min por tool |
| F3b | Catálogo completo inestable | Baja | < 15 min |
| F4a | Modos/playbooks rompen flujo | Baja | < 10 min |
| F4b | CrewAI/debate inestable | Baja | < 10 min |
| F4c | Modo específico falla | Trivial | < 5 min |
| F5a | Dreaming consume recursos | Trivial | < 5 min |
| F5b | AgentModifier aplica cambio dañino | Baja | < 10 min (1 click) |
| F5c | Frontend enterprise roto | Baja | < 10 min |
| F5d | SSO/DR falla | Media | < 1h |

---

## Procedimientos detallados

### F0 — Auditoría + setup

**Riesgo**: supuesto desmentido que invalida el plan.
**Procedimiento**:
1. Descartar documentos generados en `docs/f0-*.md`.
2. Eliminar estructura de carpetas vacías `enterprise/` (si se creó).
3. Eliminar `config/{modes,playbooks,company,templates,skills,mcp}/` (si se creó).
4. Sin impacto en código ni DB.

**Estado post-rollback**: idéntico al baseline. Tests: 329 passed.

---

### F1 — Foundation

**Riesgo**: schema migration falla o corrompe DB.
**Procedimiento**:
1. `DROP TABLE IF EXISTS oauth_credentials, subagents, prompt_versions, tool_health, pending_approvals, agent_modifications CASCADE;`
2. Eliminar directorio `src/vigilancia_multiagente/enterprise/` completo.
3. Revertir cambios en `pyproject.toml` si se añadieron dependencias (git checkout).
4. Verificar: `python -m pytest tests/enterprise -q` → 329 passed.

**Estado post-rollback**: 2.0 funcional. `enterprise/` no se importa desde ningún módulo del 2.0.

---

### F2 — Ingestion + TurboVecIndex

**Riesgo**: TurboVecIndex corrupto o ingestion falla.
**Procedimiento**:
1. Deshabilitar búsqueda semántica nueva: `features.vector_search: false` en config.
2. Si TurboVecIndex corrupto: reconstruir desde fuentes/metadata indexadas.
3. Si ingestion falla: eliminar datos ingestados; fuentes originales intactas.
4. Fallback: usar embeddings Gemini existentes del 2.0 (port `EmbeddingGateway` sigue funcional).
5. Verificar tests baseline.

**Estado post-rollback**: 2.0 funcional sin búsqueda semántica enterprise.

---

### F3a — Catálogo MVP de tools (4 Tier 1 + 16 Tier 2)

**Riesgo**: tool específica rota o MCP no arranca.
**Procedimiento**:
1. Marcar tool problemática como `enabled: false` en config.
2. Si MCPProcessSupervisor falla: reiniciar proceso individual.
3. Si todo F3a falla: `features.enterprise_tools: false` → runtime usa solo tools del 2.0.
4. Verificar tests baseline.

**Estado post-rollback**: 2.0 funcional con sus 15 MCPs originales.

---

### F3b — Catálogo completo

**Riesgo**: tool del catálogo extendido inestable.
**Procedimiento**: igual que F3a — tool por tool con `enabled: false`.

---

### F4a — Orquestación MVP + Modos + Frontend mínimo

**Riesgo**: modos/playbooks rompen flujo existente.
**Procedimiento**:
1. `features.modes: false` → runtime cae a comportamiento 2.0 puro.
2. `features.playbooks: false` → desactiva PlaybookRunner.
3. Frontend: revertir rutas `/enterprise/*` (no afecta rutas existentes del 2.0).
4. Verificar tests baseline.

**Estado post-rollback**: 2.0 funcional sin modos ni playbooks enterprise.

---

### F4b — Playbooks avanzados

**Riesgo**: CrewAI bridge o debate coordinator inestable.
**Procedimiento**:
1. Deshabilitar playbooks avanzados individualmente en `config/playbooks/`.
2. `features.crewai: false` si CrewAI es el problema.
3. Playbooks MVP (F4a) siguen funcionando.

**Estado post-rollback**: F4a funcional sin playbooks avanzados.

---

### F4c — Modos restantes

**Riesgo**: modo específico falla.
**Procedimiento**:
1. Eliminar archivo YAML del modo problemático en `config/modes/`.
2. Los 3 modos MVP (default, vigilancia-tech, CEO) siguen funcionando.

**Estado post-rollback**: F4a funcional con modos MVP.

---

### F5a — Dreaming básico + PI defense + Tool-gating

**Riesgo**: dreaming consume recursos excesivos.
**Procedimiento**:
1. `features.dreaming: false` → loops vuelven a manual.
2. PI defense regex: deshabilitar si genera falsos positivos.
3. Tool-gating: revertir a listing completo sin filtro.

**Estado post-rollback**: F4 funcional sin ciclo nocturno.

---

### F5b — Autoaprendizaje completo

**Riesgo**: AgentModifier aplica cambio dañino a config/soul.md.
**Procedimiento**:
1. Rollback de 1 click vía audit trail (`agent_modifications` table).
2. `features.self_learning: false` → loops desactivados.
3. AnomalyDetector debería haber bloqueado antes (defensa en profundidad).

**Estado post-rollback**: F5a funcional sin autoaprendizaje.

---

### F5c — Frontend completo

**Riesgo**: frontend enterprise rompe UI existente.
**Procedimiento**:
1. Eliminar rutas `/admin/*` y `/enterprise/artifacts/*`.
2. Frontend 2.0 sigue funcional (rutas independientes).

**Estado post-rollback**: Frontend 2.0 + superficies MVP de F4a.

---

### F5d — DR + SSO + compliance

**Riesgo**: SSO mal configurado bloquea acceso.
**Procedimiento**:
1. Deshabilitar SSO: `auth.sso_enabled: false` → fallback a auth local.
2. DR: restaurar último backup verificado.
3. Capability tokens: revocar tokens problemáticos.

**Estado post-rollback**: F5b funcional con auth local.

---

## Garantía transversal

- **Cada fase** tiene feature flag que permite desactivar sin tocar código.
- **Cada rollback** referencia el baseline de F0 como estado objetivo.
- **Tests del 2.0** (329 passed) deben pasar tras cualquier rollback.
- **DB**: las tablas enterprise son independientes; `DROP CASCADE` no afecta tablas del 2.0.
- **Código**: `enterprise/` es subpaquete aislado; eliminarlo no rompe imports del 2.0.
