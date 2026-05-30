# 05 — Autoaprendizaje y Autonomía

> Documento que cierra la **brecha 5** del set: el ciclo continuo de mejora del agente. Antes el autoaprendizaje vivía disperso (Dreaming en §10, Writing Style en §10.6, Skill Learning en §15) sin un marco unificado.

> **Decisión D4 de esta sesión** (la más impactante del refinamiento): **autoaprendizaje full-autonomy con audit trail**. El agente puede modificar TODO (skills, tools, prompts, SOUL.md, COMPANY/*, templates, políticas) con `diff` + `timestamp` + `rollback de un click`. **REESCRIBE la decisión #44 del plan maestro original**, que prohibía al agente tocar config.

> **Corrección vigente**: Dreaming tambien ejecuta indexacion empresarial, busqueda normativa localizada por `company_geo` y automantenimiento admin de repositorios clonados de tools/MCPs. Ver [00-canon-operativo-corregido.md](00-canon-operativo-corregido.md).

---

## Cambio respecto al plan maestro

### Decisión #44 anterior (ahora obsoleta)

> Cambios a `config/soul.md`, `config/company/*.md`, políticas, `config/templates/*`: el agente NUNCA los modifica directamente. Solo propone cambios en mensaje al usuario, quien edita manualmente. Esto es más estricto que approval — es prohibición.

### Decisión D4 actual (vigente desde esta sesión)

> El agente PUEDE modificar TODO: skills, tools, prompts, SOUL.md, COMPANY/*, templates, políticas. Cada modificación queda registrada con `diff` + `timestamp` + `agent_id` + `rollback_token`. El usuario revisa changelog semanal en Dreaming Report y puede revertir cualquier cambio con un click. Aprovecha la tabla `prompt_versions` ya planeada (decisión #35) y la extiende.

### Matriz before/after

| Elemento | Antes (decisión #44) | Ahora (D4) |
|---|---|---|
| `config/soul.md` | Solo el usuario edita | Agente puede editar + audit + rollback |
| `config/company/identity.md` | Solo el usuario edita | Agente puede editar + audit + rollback |
| `config/company/policies.md` | Solo el usuario edita | **Excepción**: requiere approval-gate explícito antes de aplicar |
| `config/company/{organization,processes,systems}.md` | Solo el usuario edita | Agente puede editar + audit + rollback |
| `config/templates/*` | Solo el usuario edita | Agente puede editar + audit + rollback |
| `config/playbooks/*.yaml` | Solo el usuario edita | Agente puede editar + audit + rollback |
| `config/skills/learned/*` | Agente añade tras revisión humana | Agente añade libremente + audit + rollback |
| `config/skills/curated/*` | Solo el usuario edita | Agente puede editar + audit + rollback |
| `config/modes/*.yaml` | (no existían) | Agente puede crear/editar + audit + rollback |

**Única excepción que conserva approval**: `policies.md` por su impacto en compliance. Cualquier modificación intentada por el agente queda en estado `pending_approval` hasta que el usuario confirma.

---

## Arquitectura del audit trail

### Tabla `agent_modifications`

```sql
CREATE TABLE agent_modifications (
    id              UUID PRIMARY KEY DEFAULT uuidv7(),
    tenant_id       UUID NOT NULL,
    target_file     TEXT NOT NULL,           -- path relativo desde repo root, ej: "config/soul.md"
    target_kind     TEXT NOT NULL,           -- soul | company | template | playbook | mode | skill | prompt | tool
    diff            TEXT NOT NULL,           -- unified diff completo del cambio
    diff_summary    TEXT,                    -- 1-2 líneas LLM resume el cambio
    applied_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    rollback_token  TEXT NOT NULL UNIQUE,    -- hash que permite revertir vía /rollback <token>
    agent_id        TEXT NOT NULL,           -- qué Agent (no sesión humana) lo hizo
    session_id      UUID,                    -- sesión que generó el cambio (puede ser null si Dreaming)
    triggered_by    TEXT NOT NULL,           -- demonstration | self_improvement | composition | self_update | manual_request
    justification   TEXT,                    -- por qué lo hizo (1-3 líneas)
    status          TEXT NOT NULL DEFAULT 'applied',  -- applied | pending_approval | reverted | superseded
    reverted_at     TIMESTAMPTZ,
    reverted_by     TEXT,                    -- user_id que ejecutó el rollback
    superseded_by   UUID REFERENCES agent_modifications(id),
    CONSTRAINT valid_status CHECK (status IN ('applied', 'pending_approval', 'reverted', 'superseded'))
);

CREATE INDEX idx_agent_mods_tenant_applied ON agent_modifications (tenant_id, applied_at DESC);
CREATE INDEX idx_agent_mods_target_file ON agent_modifications (target_file, applied_at DESC);
CREATE INDEX idx_agent_mods_rollback_token ON agent_modifications (rollback_token);
```

**Notas**:
- `target_kind` permite filtrar el changelog ("muéstrame solo cambios a SOUL").
- `rollback_token` se entrega al usuario en el Dreaming Report semanal como botón.
- `superseded_by` mantiene la cadena: si el agente modifica un archivo 3 veces, las dos primeras quedan `superseded`.

### Replica JSONL diaria

`~/.vigilador/audit/agent_mods/<fecha>.jsonl` con líneas:

```json
{"id":"01H...","tenant_id":"...","target_file":"config/soul.md","triggered_by":"self_improvement","diff":"@@...","summary":"Ajusta tono al detectar feedback negativo del usuario sobre formalidad excesiva","applied_at":"2026-05-24T03:14:22Z","rollback_token":"rt_a1b2c3..."}
```

Razón: queries rápidas con `grep`/`jq` sin tocar PostgreSQL, y backup natural (rotación a 30 días, JSONL no se backupea según decisión #87).

### Implementación

`enterprise/governance/agent_modifier.py` (~250 LOC):

```python
class AgentModifier:
    """Único punto de entrada para modificaciones del agente a config/."""

    async def propose_and_apply(
        self,
        target_file: str,
        new_content: str,
        triggered_by: TriggerKind,
        justification: str,
        agent_id: str,
        session_id: UUID | None,
    ) -> ModificationResult:
        """Genera diff, valida, aplica si pasa guardrails, persiste audit."""
        old_content = self._read_current(target_file)
        diff = self._compute_diff(old_content, new_content)

        if self._requires_approval(target_file):
            return self._enqueue_for_approval(target_file, diff, ...)

        if not self._passes_anomaly_check(target_file, diff, agent_id):
            return ModificationResult(blocked=True, reason="anomaly_detected")

        rollback_token = self._generate_rollback_token()
        self._write_file_atomically(target_file, new_content)
        await self._persist_audit(target_file, diff, rollback_token, ...)
        return ModificationResult(applied=True, rollback_token=rollback_token)

    async def rollback(self, rollback_token: str, user_id: str) -> RollbackResult:
        """Revierte un cambio específico. Sin cascada — solo el cambio target."""
        ...

    async def list_pending_approvals(self, tenant_id: UUID) -> list[ModificationResult]:
        ...
```

**Guardrails internos**:
- `_requires_approval`: hardcodeado para `policies.md`; configurable en `mode_settings.require_approval_for`.
- `_passes_anomaly_check`: consulta `AnomalyDetector` (#108) — si el cambio se desvía mucho del baseline, bloquea.
- `_write_file_atomically`: escribe a `<file>.tmp`, fsync, rename atomic. Cero corrupción si crash mid-write.

---

## UI de rollback de un click

### Vista web

`http://<host>/admin/audit/changelog`:

| Fecha | Archivo | Resumen | Triggered by | Agent | Rollback |
|---|---|---|---|---|---|
| 2026-05-24 03:14 | `config/soul.md` | Ajusta tono al detectar feedback... | `self_improvement` | `DreamCurator` | `[Revertir]` |
| 2026-05-23 18:02 | `config/skills/learned/sarlaft-monthly-report.yaml` | Skill nuevo aprendido por demostración | `demonstration` | `Session-abc123` | `[Revertir]` |
| 2026-05-23 14:30 | `config/company/processes.md` | Añade sección "Cierre mensual financiero" detectada como gap | `self_update` | `DreamCurator` | `[Revertir]` |
| 2026-05-23 09:15 | `config/playbooks/decision-debate.yaml` | Optimiza prompt del moderador tras A/B test | `self_improvement` | `DreamCurator` | `[Revertir]` |

Click en `[Revertir]` → confirmación modal con preview del diff inverso → ejecuta `AgentModifier.rollback(token)`.

### CLI admin fallback

```bash
vigilador-admin audit changelog --since "2026-05-20" --tenant <tenant_uuid>
vigilador-admin audit show <rollback_token>          # ver diff completo
vigilador-admin audit rollback <rollback_token>      # revertir
vigilador-admin audit pending-approvals              # cola de pending_approval
vigilador-admin audit approve <rollback_token>       # aprueba un pending
```

---

## Loops de autoaprendizaje

5 loops corren dentro de Dreaming (cron 3 AM + idle > 10 min). Cada uno detecta patrones, genera propuestas y las aplica vía `AgentModifier` (excepto los que requieren approval).

### Loop 1: Skill learning por demostración (existente, decisión #15)

**Input**: sesión donde el agente uso `computer_use` o `browser` para resolver una tarea nueva no cubierta por skills existentes.
**Procesamiento**: extrae la secuencia de acciones, parametriza inputs/outputs, genera `SKILL.md` con metadata.
**Output**: nuevo archivo en `config/skills/learned/<nombre>.yaml` + audit entry con `triggered_by: demonstration`.
**Guardrails**:
- Primera ejecución autónoma del skill aprendido requiere approval-gate (decisión #44 conserva esta cláusula porque es un nuevo skill, no una edición a uno existente).
- Tras 5 ejecuciones exitosas, se promueve a "estable" y el approval no se pide más.

### Loop 2: Writing style learning (existente, decisión #20)

**Input**: correos enviados por el usuario (Outlook/Gmail vía connectors), aprobados/rechazados al agente.
**Procesamiento**: stats sobre tono, longitud, formalidad, vocativos, firma, días/horas habituales.
**Output**: `config/skills/learned/writing_style.yaml` actualizado + audit entry con `triggered_by: self_update`.
**Guardrails**: detecta drift severo (cambio brusco vs baseline 30 días) → flag para revisión humana, no bloquea.

### Loop 3: Prompt self-improvement [NUEVO]

**Input**: outputs del agente que recibieron feedback negativo (rechazo explícito, reformulación por el usuario, "esto no me sirve") capturados en `audit_events_jsonl_index`.
**Procesamiento**:
1. Agrupa por `agent_id` + `playbook_id` + `prompt_template`.
2. Si N≥5 feedbacks negativos contra el mismo `prompt_template` en 7 días → genera variante (1 llamada MiniMax M-2.7 con instrucciones de mejora basadas en el feedback).
3. A/B test: 50% sesiones siguientes usan variante, 50% siguen con original.
4. Tras 20 sesiones (~7 días en uso moderado), si variante tiene mejor `vigilador_response_confidence` (#98) y menos feedbacks negativos → promueve a default.
**Output**: `config/playbooks/<id>.yaml` o `config/prompts/<id>.md` actualizado + audit entry con `triggered_by: self_improvement`.
**Guardrails**: A/B test obligatorio antes de promoción; revertir si confianza cae en >10%.

### Loop 4: Tool composition [NUEVO]

**Input**: patrones repetidos en `audit_events_jsonl_index` de invocación de tools (ej: cada vez que el usuario pide "informe ventas Q", el agente ejecuta `excel_local.read` → `power_bi_file_reader.extract` → `template_render` → `docx_generate`).
**Procesamiento**:
1. Detecta secuencias repetidas ≥10 veces en 30 días.
2. Genera macro como Skill compuesto que invoca esas tools en orden.
3. Sugiere al usuario en el siguiente Dreaming Report ("¿Crear skill `informe-ventas-trimestral`?").
4. Si usuario aprueba (o si `mode_settings.intensity = AUTONOMOUS`), crea el skill.
**Output**: `config/skills/learned/<nombre>.yaml` + audit entry con `triggered_by: composition`.
**Guardrails**: nunca sobrescribe un skill existente sin marcarlo como `superseded`.

### Loop 5: COMPANY self-update [NUEVO]

**Input**: preguntas del usuario al agente que el agente respondió con "no tengo información en COMPANY.md" o que requirieron consultar fuentes externas que el usuario confirmó como "información que debería estar en COMPANY".
**Procesamiento**:
1. Agrupa por categoría (organization / processes / systems).
2. Genera propuesta de párrafo o sección a añadir.
3. Para `identity.md` y `policies.md`: encola pending_approval. Para el resto: aplica directamente.
**Output**: `config/company/<archivo>.md` actualizado + audit entry con `triggered_by: self_update`.
**Guardrails**: el agente jamás elimina contenido existente; solo añade o anota como "obsoleto: ver sección X".

### Loop 6: Regulatory/local watcher [NUEVO C0]

**Input**: `company_geo`, modos activos, sector de la empresa, fuentes oficiales usadas en respuestas recientes y cambios detectados por conectores.
**Procesamiento**:
1. Construye queries por pais/departamento/municipio. Ejemplo: Colombia + Santander + Barrancabermeja + impuestos/tasas/permisos/normas tecnicas.
2. Busca fuentes oficiales vigentes antes de cualquier resumen: alcaldia, gobernacion, entidades nacionales, superintendencias, DIAN, Icontec u organismo aplicable.
3. Compara contra lo guardado en `config/company/policies.md`, `processes.md` y evidencia indexada.
4. Genera propuestas con citas y fecha de consulta.
**Output**: alerta, propuesta de actualizacion o task de `company-optimization`.
**Guardrails**: nunca hardcodea valores tributarios/legales; si no encuentra fuente oficial suficiente, marca incertidumbre y pide revision humana.

### Loop 7: Admin repository maintenance [NUEVO C0]

**Input**: repositorios clonados de MCPs/tools/skills, inventario del doc 06, hashes registrados y versiones instaladas.
**Procesamiento**:
1. Revisa releases, commits nuevos, CVEs, cambios de schema, nuevas capabilities y bugfixes.
2. Compara local vs upstream y clasifica impacto: patch, feature, breaking, security.
3. Genera rama/sandbox temporal para probar actualizacion.
4. Ejecuta tests del wrapper/tool/MCP afectado.
**Output**: propuesta admin con diff, changelog, riesgo, pruebas y boton aprobar/promover.
**Guardrails**: no promueve cambios a runtime estable sin aprobacion admin.

### Resumen de loops

| Loop | Output | Trigger | Approval default | Anomaly check |
|---|---|---|---|---|
| 1 Skill learning | `skills/learned/*.yaml` | sesión que resuelve tarea nueva | Sí, primera ejecución | Sí |
| 2 Writing style | `skills/learned/writing_style.yaml` | Dreaming nightly | No | Sí (drift) |
| 3 Prompt self-improvement | `playbooks/*.yaml`, `prompts/*.md` | feedback negativo ≥5 en 7d | No (A/B test) | Sí |
| 4 Tool composition | `skills/learned/*.yaml` | patrón ≥10 ejecuciones en 30d | No (sugiere) | Sí |
| 5 COMPANY self-update | `company/*.md` | gap detectado | Solo `identity.md` y `policies.md` | Sí |
| 6 Regulatory/local watcher | alertas + propuestas company/optimization | Dreaming o consulta geo | Sí si toca `policies.md` | Sí |
| 7 Admin repository maintenance | propuestas de update tools/MCPs | semanal o CVE | Sí admin | Sí |

---

## Guardrails residuales

A pesar de la full-autonomy, hay 3 guardrails que NO se relajan:

### Guardrail 1: AnomalyDetector (#108)

Stats sobre `audit_events_jsonl_index` para baseline:
- Frecuencia típica de modificaciones a un archivo (ej: SOUL.md cambia ~1 vez al mes).
- Magnitud típica del diff (líneas añadidas/eliminadas).
- Hora del día típica de cambios.

Si una modificación se desvía >3σ del baseline → bloquea + alerta al usuario por canal preferido + log `vigilador_anomaly_blocked_total{target_file,reason}`.

Aplica especialmente a goal-driven mode (#100): ejecución autónoma extendida no puede "escaparse" del baseline.

### Guardrail 2: Capability tokens (#107)

Ejecuciones autónomas extendidas (goal-pursuit, Dreaming) operan con tokens efímeros, revocables, con scope/TTL/rate-limit:

```python
token = CapabilityToken.issue(
    parent_session_id=session.id,
    scopes=["modify:config/skills/learned/*", "read:config/company/*"],
    rate_limit="10/hour",
    expires_at=datetime.now() + timedelta(hours=8),
)
```

Si el token expira mid-loop, el siguiente intento de modificación falla con `403 token_expired`. El loop re-solicita aprobación humana antes de continuar.

### Guardrail 3: Approval-gate para `policies.md`

Única excepción declarada. Aplica al archivo `config/company/policies.md` por su impacto en compliance.

Cualquier modificación intentada → status `pending_approval` → entra a cola visible en `/admin/audit/pending` → el usuario debe aprobar manualmente o reescribir.

Configurable por Modo: un Modo custom puede añadir más archivos al lock vía `mode_settings.audit.approval_required_for_files`.

---

## Dreaming como motor del autoaprendizaje

El ciclo Dreaming (existente, decisión #17) se extiende para orquestar los loops de autoaprendizaje, indexacion, normativa local y automantenimiento admin:

### Fases del Dreaming (ampliadas)

| Fase | Tareas | Loops disparados |
|---|---|---|
| **1. Memory consolidation** | Recoge sesiones del día, comprime, fusiona en memoria | — |
| **2. Skill curator** | Revalida skills aprendidos (test ejecuciones recientes) | 1 (Skill learning), 4 (Tool composition) |
| **3. Self-improvement** | Analiza feedbacks negativos, ejecuta A/B tests | 3 (Prompt self-improvement) |
| **4. Config refresher** | Detecta gaps en SOUL/COMPANY, propone actualizaciones | 2 (Writing style), 5 (COMPANY self-update) |
| **5. Enterprise ingestion sync** | Connectors nativos/MCPs (Drive, OneDrive, local_fs, Outlook/Gmail, WhatsApp) sync incremental | — |
| **6. Regulatory/local watch** | Revisa cambios normativos/impuestos/normas por `company_geo` | 6 |
| **7. Index maintenance** | Vacuum/compact TurboVecIndex y busqueda textual opcional | — |
| **8. Scheduled artifacts/reports** | Genera dashboards, pipelines y reportes programados | — |
| **9. Admin repo maintenance** | Revisa tools/MCPs/skills clonados contra upstream | 7 |
| **10. Audit report** | Genera Dreaming Report con changelog del día + métricas | — |

### Dreaming Report (NUEVO formato extendido)

Enviado al canal preferido del usuario tras cada ciclo:

```
🌙 Dreaming Report — 2026-05-24

📊 Resumen ejecutivo
- 47 sesiones procesadas
- 3 skills actualizados (2 mejorados, 1 deprecated)
- 1 cambio en SOUL.md (ajuste tono)
- 1 nueva sección en COMPANY/processes.md
- 2 propuestas pendientes de aprobación

📝 Cambios aplicados (revisables)
1. SOUL.md → ajuste de tono [Ver diff] [Revertir]
2. skills/learned/sarlaft-monthly-report.yaml → mejora en parser [Ver diff] [Revertir]
3. playbooks/decision-debate.yaml → optimización prompt moderador [Ver A/B] [Revertir]

⚠️ Pendientes de aprobación
1. policies.md → propuesta de actualización por nueva regulación SFC [Aprobar] [Rechazar]
2. Skill nuevo `informe-ventas-trimestral` aprendido por composición → confirmar [Aprobar] [Rechazar]

📈 Métricas del día
- vigilador_response_confidence promedio: 0.87 (+0.03 vs ayer)
- vigilador_pi_quarantined_total: 0
- vigilador_anomaly_blocked_total: 1 (Loop 5, ver detalle)

🔧 Salud del sistema
- 15/15 MCPs externos UP
- TurboVecIndex OK
- 0 errores críticos en circuit breakers
```

---

## Métricas Prometheus

```
vigilador_agent_modifications_total{target_kind, triggered_by, status}
vigilador_agent_modifications_reverted_total{target_kind, reason}
vigilador_agent_modifications_pending_approval{tenant_id}
vigilador_anomaly_blocked_total{target_file, reason}
vigilador_prompt_ab_test_active{playbook, prompt_id}
vigilador_prompt_ab_test_promoted_total{playbook, prompt_id}
vigilador_skill_learned_total{source}   # demonstration | composition
vigilador_skill_curator_revalidated_total{result}  # ok | deprecated | failed
vigilador_regulatory_watch_total{geo, result}
vigilador_admin_repo_updates_detected_total{repo, impact}
```

---

## Integración con el resto del set

| Doc | Cómo se integra |
|---|---|
| [01 Arquitectura](01-vision-y-arquitectura.md) | Define dónde vive `enterprise/governance/agent_modifier.py` y la tabla SQL. |
| [02 Modos](02-modos-y-personalidades.md) | `mode_settings.audit.full_autonomy` y `audit.approval_required_for_files` configuran este ciclo por Modo. |
| [03 Playbooks](03-playbooks-y-orquestacion.md) | Cualquier playbook puede sugerir modificaciones; el AgentModifier las aplica. |
| [04 Skills](04-skills-y-capacidades.md) | El Skill curator dentro de Dreaming consume los skills definidos ahí. |
| [06 Catálogo tools](06-catalogo-tools-y-extraccion.md) | El automantenimiento admin revisa repos/tools/MCPs del inventario operativo. |
| [08 Gobernanza](08-gobernanza-seguridad-y-operaciones.md) | Las políticas de capability tokens, anomaly detection y PI defense (los 3 guardrails) se definen ahí. Este doc las USA, no las reformula. |

---

## Decisiones implementadas por este doc

Este doc implementa la **decisión D4 de esta sesión** y referencia/extiende las siguientes del plan maestro (ver `ANEXO-B-decision-log-por-tema.md`):

- **#15** (Skill learning por demostración) → Loop 1.
- **#17** (Dreaming) → motor del autoaprendizaje, fases ampliadas.
- **#20** (Writing style learning) → Loop 2.
- **#23** (indexación automatizada en Dreaming) → Fase 7.
- **#35** (Versionado de prompts vía `prompt_versions`) → tabla `agent_modifications` la subsume.
- **#44** (prohibición de modificar config) → **REFORMULADA por D4** (esta sesión). Marcar como `reformulada` en ANEXO-B.
- **#54** (ContextCompressor) → Fase 1.
- **#107** (capability tokens) → Guardrail 2.
- **#108** (anomaly detector) → Guardrail 1.
- **#110** (scheduled reports) → Fase 6.
- **C0** automantenimiento admin, indexacion empresarial y normativa localizada por `company_geo`.

---

## Criterios de verificación

Tras implementar este doc:

1. **Test de audit trail**: aplicar 1 modificación a `config/soul.md`, verificar entrada en tabla `agent_modifications` + entrada en JSONL del día.
2. **Test de rollback**: ejecutar `vigilador-admin audit rollback <token>`, verificar que `config/soul.md` vuelve al estado anterior + status pasa a `reverted`.
3. **Test de approval-gate**: intentar modificar `config/company/policies.md` desde un Loop, verificar que queda `pending_approval` y NO se aplica.
4. **Test de anomaly**: forzar cambio masivo (>500 líneas) a `config/soul.md` desde un Agent → `AnomalyDetector` debe bloquear con `vigilador_anomaly_blocked_total` incrementado.
5. **Test de A/B**: simular 5 feedbacks negativos sobre un prompt → verificar Loop 3 genera variante + entra en A/B test (50/50).
6. **Test de Dreaming Report**: forzar ciclo Dreaming, verificar que el report incluye sección "Cambios aplicados" con los cambios del día.
7. **Test de capability token**: ejecutar goal-pursuit con TTL 1 hora, esperar 2 horas, intentar modificación → debe fallar con `403 token_expired`.
8. **Test regulatory watcher**: con `company_geo` Barrancabermeja/Santander/Colombia, Dreaming genera busquedas en fuentes oficiales y una propuesta con citas o una incertidumbre explicita.
9. **Test admin maintenance**: simular nueva release de un MCP clonado → Dreaming crea propuesta admin con diff, impacto y pruebas, sin promoverla automaticamente.
