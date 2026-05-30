# 08 — Gobernanza, Seguridad y Operaciones

> Documento transversal que define las políticas, guardrails y mecanismos operacionales que sustentan al Vigilador 3.0 en entornos empresariales. Es el doc al que apunta cualquier decisión de seguridad/compliance/observabilidad de los demás docs.

> **Reformulación clave esta sesión**: la política de approvals (decisión #44 original) se redujo significativamente por D4 (full autonomy con audit trail). Aquí se documenta el set residual de approvals + los 3 guardrails que SÍ se conservan.

> **Corrección vigente**: en esta version de prueba no hay quotas por usuario. Se conservan telemetria de uso, costos, circuit breakers tecnicos, capability tokens y anomaly detection. Ver [00-canon-operativo-corregido.md](00-canon-operativo-corregido.md).

---

## SystemBase + DomainProfile + SOUL + COMPANY

### SystemBase (preservado del 2.0)

`domain/system_base.py`. Frozen global rules. Single source of truth para:
- Tool policy global (qué tools son permitidas/prohibidas universalmente).
- Safety limits (max LLM calls por sesión absoluto, max sub-agente depth absoluto).
- Output style global (no inventar, no afirmar sin evidencia, citar fuentes).
- Idioma interno (inglés, decisión #40).

**Inmutable en runtime**. Cambiarlo requiere modificación de código + redeploy.

### BranchOverlay → DomainProfile (extendido)

`domain/system_base.py:BranchOverlay` se preserva intacto. `domain/domain_profile.py:DomainProfile(BranchOverlay)` añade:

- `connectors_required: list[str]` — qué connectors deben estar configurados para que el playbook asociado se ofrezca.
- `acl_default_scopes: list[str]` — qué scopes ACL se aplican por default a queries de este dominio.
- `playbook_id: str` — qué playbook usa este DomainProfile.

Usado por `PromptComposer` para componer SystemBase + DomainProfile + ModeOverlay + user query → `ComposedPrompt` final.

### SOUL (`config/soul.md`)

Personalidad base del asistente. Lectura frozen-snapshot al inicio de sesión. Modificable por el agente con audit trail (D4 esta sesión).

Contenido típico:
- Tono base (formal-cordial / ejecutivo / técnico).
- Valores rectores (transparencia, no inventar, citar fuentes).
- Vocativos preferidos.
- Estilo de firma de correos (si writing_style aún no ha aprendido).

Los Modos extienden SOUL con `soul_overlay` (doc 02).

### COMPANY (`config/company/*.md`)

5 archivos partidos (decisión #16):

| Archivo | Contenido |
|---|---|
| `identity.md` | Misión, visión, valores corporativos. Lectura inmutable por el agente (approval-gate doc 05). |
| `organization.md` | Estructura organizacional, cargos, responsables, equipos, paths de archivos clave. |
| `processes.md` | Procesos operacionales documentados (cierre mensual, onboarding, ventas, etc.). |
| `systems.md` | Sistemas usados (CRM, ERP, BI, file servers), URLs, accesos. |
| `policies.md` | Políticas internas (compliance, seguridad, vacaciones, gastos). **Único con approval-gate**. |

Cargados como frozen snapshot por Mode según `company_subset.files`.

### COMPANY GEO (`company_geo`)

Contexto geografico de la empresa:

```yaml
country: "Colombia"
department: "Santander"
municipality: "Barrancabermeja"
timezone: "America/Bogota"
```

Uso obligatorio en modos y playbooks que dependan de normativa, impuestos, tasas, permisos, normas tecnicas o fuentes oficiales. El sistema debe buscar fuentes vigentes antes de afirmar y registrar citas/fecha de consulta.

---

## Autenticación multi-canal

### OAuth (Drive / OneDrive / Slack / GitHub / etc.)

Implementado en `enterprise/auth/oauth_manager.py`. Tokens encriptados Fernet en `~/.vigilador/credentials/` (decisión #53).

**Scopes restrictivos** (decisión #45 — política "no delete"):
- Drive: `drive.file` + `drive.readonly` (NO `drive` full).
- MS Graph: `Files.ReadWrite` sin `Files.ReadWrite.All` ni permisos delete específicos.
- Slack: `chat:write` + `channels:read` (NO `chat:write.public` ni admin).
- GitHub: `repo:status` + `read:org` (NO `delete_repo`).

**Refresh automático**: tokens próximos a expirar (< 7 días) se refrescan en Dreaming.

### Token auth + Device token

`enterprise/auth/token_auth.py` para API tokens HMAC. `enterprise/auth/device_token.py` para iOS/Android/web.

### SSO / SAML / OIDC (decisión #30)

Para tenants empresariales. Azure AD, Google Workspace SSO, Okta via SAML 2.0 / OIDC. Reemplaza el password auth como método primario.

Configuración por tenant en `config/tenants/<tenant>/sso.yaml`.

---

## Tool-gating + Capability tokens

### Tool-gating

Mecanismo unificado que oculta tools del listing del agente. Activación en 4 escenarios:

| Trigger | Causa | Comportamiento |
|---|---|---|
| Falta API key | `requires_key: true` y env_var no presente | Tool no aparece en `ToolRegistry.list_tools_for_role` |
| Circuit breaker DOWN | 3 fallos en 60s | Tool excluida hasta cooldown 5 min |
| App local no instalada | `*_local.py` y `LocalAppDetector.has_X = False` | Tool no se registra al boot |
| Capability token expirado/revocado | Sesión opera con scope/TTL específico | Tool no aparece para esa sesión |

Implementado en `enterprise/tooling/tool_registry.py:list_tools_for_role()` (query pura, sin side-effects — fix CQS #81).

### Capability tokens (decisión #107)

`enterprise/auth/capability_tokens.py` (~300 LOC). Tokens efímeros, revocables, con scope/TTL/rate-limit per-token.

```python
@dataclass
class CapabilityToken:
    id: UUID
    parent_session_id: UUID
    scopes: list[str]      # ej: ["modify:config/skills/learned/*", "send:email:#ventas:until_18:00"]
    rate_limit: str        # "10/hour"
    expires_at: datetime
    revoked_at: datetime | None
```

Tabla `capability_tokens(id, parent_session_id, scopes, rate_limit, expires_at, revoked_at)`.

**Cuándo se emiten**:
- Goal-pursuit autónomo extendido (TTL típico: 8h).
- Skills aprendidos primera ejecución (TTL: 1 ejecución).
- Sesiones AUTONOMOUS de modos con `mode_settings.intensity = AUTONOMOUS`.

**Revocación**:
- CLI: `vigilador-admin token revoke <id>`.
- UI: vista `/admin/tokens` con botón revoke.
- Automática: cuando la sesión padre cierra.

---

## PI defense (Prompt Injection)

Decisión #106. `enterprise/governance/prompt_injection_detector.py` (~200 LOC).

**Pipeline**: todo input externo (correos entrantes, PDFs indexados, contenido scrapeado, mensajes WhatsApp) pasa por el detector **ANTES** de tocar el LLM.

**Detección multi-capa**:

1. **Heurísticas regex**: `ignore previous instructions`, `system:`, `you are now`, `disregard the above`, etc.
2. **Dataset Lakera** (open-source): patrones conocidos de inyección.
3. **Embedding comparison**: compara contra corpus de ataques conocidos (similarity > 0.85 → flag).

**Acción si positivo**:
- Input se **cuarentena**: NO llega al LLM.
- Entrada en tabla `pi_quarantine(id, tenant_id, source, content_excerpt, detected_patterns, severity, quarantined_at, approved_at, approved_by)`.
- Alerta al usuario por canal preferido con detalle.
- Audit log estructurado.
- Métrica `vigilador_pi_quarantined_total{source,severity}`.

**Falsos positivos**: usuario aprueba explícitamente en dashboard ("este correo es legítimo, despublicar de cuarentena"). Solo el usuario humano puede despublicar — el agente no.

**Crítico**: sin esto, un PDF malicioso indexado puede secuestrar al agente. Por eso PI defense está en F0 (audit) y F3 (implementación) del cronograma.

---

## Anomaly detection (decisión #108)

`enterprise/governance/anomaly_detector.py` (~250 LOC).

**Stats sobre `audit_events_jsonl_index`**: baseline de patrones del usuario en ventana móvil 30 días:
- Qué tools usa típicamente.
- En qué horarios.
- Sobre qué entidades (clientes, archivos, cuentas).
- Frecuencia y magnitud de modificaciones a config.

**Detección**: desviación >3σ del baseline → bloquea acción + alerta.

**Aplicación principal**:
- Goal-driven mode: cualquier desviación durante ejecución autónoma → pausa + aprobación humana.
- AgentModifier (doc 05): bloquea cambios anormales a config antes de aplicar.
- Acciones masivas (envío >50 emails súbito, eliminación de 100 contactos): bloquea aunque no exista quota por usuario.

**Defensa contra cuentas comprometidas**: cero conocimiento previo del atacante sobre patrones del usuario real, por lo que sus acciones casi siempre rompen baseline.

Métrica `vigilador_anomaly_blocked_total{target,reason}`.

---

## Audit estructurado JSONL

`~/.vigilador/audit/` con rotación diaria. 3 archivos por día:

| Archivo | Contenido |
|---|---|
| `events_<fecha>.jsonl` | Todos los eventos: invocaciones de tools, llamadas LLM, decisiones del ComplexityClassifier, spawns de subagentes, etc. |
| `agent_mods_<fecha>.jsonl` | Modificaciones del agente a config (replica JSONL de tabla `agent_modifications`, doc 05) |
| `pi_quarantine_<fecha>.jsonl` | Inputs cuarentenados por PI defense |

**Índice SQL** (decisión #92): tabla `audit_events_jsonl_index(id UUID DEFAULT uuidv7(), tenant_id, file_path, event_kind, occurred_at, indexed_keys JSONB)` para queries rápidas sin parsear JSONL completo.

**Retención**: 30 días en JSONL crudo (efímero, no se backupea). Para retención SOC 2: migrar entradas críticas a tabla SQL `audit_events_archive` (post-v3.0, decisión #87).

**Acceso**:
- `vigilador-admin audit query --since <date> --tenant <uuid> --event-kind <kind>`.
- UI `/admin/audit/explorer` con filtros y export.

---

## Multi-tenancy

Decisión #26 y #86. `tenant_id UUID NOT NULL` en TODAS las tablas nuevas desde día 1. v3.0 inicial single-tenant, pero el schema lo soporta.

Aplicación por capa:

| Capa | Mecanismo |
|---|---|
| PostgreSQL | `tenant_id` en cada tabla; queries siempre filtradas |
| TurboVec | 1 archivo `.tq` por tenant en `~/.vigilador/turbovec/<tenant_uuid>.tq` (aislamiento físico) |
| SQLite FTS5 | 1 archivo `.db` por tenant en `~/.vigilador/sessions/<tenant_uuid>.db` (aislamiento físico) |
| JSONL audit | Prefijo `tenant_id` en cada línea (filtro `grep`/`jq`) |
| YAML config | `config/tenants/<tenant>/` para configs per-tenant (activación en v3.1) |

**En v3.0 single-tenant**: todas las queries usan un `tenant_id` constante hardcoded `00000000-0000-0000-0000-000000000001`. El multi-tenancy real se activa en v3.1 sin schema migration adicional.

---

## Observabilidad

### Prometheus

Métricas expuestas en `/metrics`:

```
vigilador_llm_tokens_total{model, playbook}
vigilador_llm_calls_total{model, playbook, status}
vigilador_llm_latency_seconds{model, playbook}
vigilador_session_cost_usd{playbook, mode, tenant_id}
vigilador_tool_invocations_total{tool, status}
vigilador_tool_latency_seconds{tool}
vigilador_mcp_process_status{name}
vigilador_mcp_process_restarts_total{name}
vigilador_pi_quarantined_total{source, severity}
vigilador_anomaly_blocked_total{target, reason}
vigilador_cache_hit_ratio{tool, domain}
vigilador_response_confidence{playbook, domain}
vigilador_agent_modifications_total{target_kind, triggered_by, status}
vigilador_agent_modifications_reverted_total{target_kind, reason}
vigilador_skill_invocations_total{skill_id, mode}
vigilador_skill_success_rate{skill_id}
vigilador_admin_repo_updates_detected_total{repo, impact}
vigilador_regulatory_watch_total{geo, result}
```

### OpenTelemetry tracing

Tracing distribuido por sesión. Spans:

- `session.lifecycle` (root span por sesión)
- `mode.resolve`
- `complexity.classify`
- `playbook.run`
- `agent.execute` (un span por agente; sub-agentes anidados)
- `skill.invoke`
- `capability.execute`
- `tool.call` (incluye latencia + error si aplica)
- `llm.call`

Exportable a Jaeger, Tempo, o vendor cloud (configurable).

### Dashboard

`enterprise/observability/dashboard.py`. Vista web `/admin/dashboard`:

- Cards por componente (LLM, MCPs, TurboVecIndex, metadata DB, busqueda textual opcional).
- Tabla de últimas 50 sesiones con coste y estado.
- Gráficos: tokens/día, latencia p50/p95/p99, error rate.
- Audit explorer integrado.
- Cola de pending approvals (botones approve/reject).
- Lista de MCPs con estado UP/DOWN y botón restart.

---

## Disaster Recovery + Backup (decisión #28, #87)

**RTO 1h / RPO 24h** declarados.

### Backup automatizado (Dreaming Fase 5 + cron diario adicional 2 AM)

3 fuentes vivas:

1. `pg_dump --format=custom` de PostgreSQL (metadata, auditoria y configuracion operacional).
2. `tar -czf turbovec-<tenant>-<fecha>.tar.gz ~/.vigilador/turbovec/<tenant>.tq` por tenant.
3. `tar -czf sessions-<tenant>-<fecha>.tar.gz ~/.vigilador/sessions/<tenant>.db` por tenant.

**No se backupea**:
- JSONL audit (efímero, rotan a 30 días). Si compliance exige retención: migrar entradas a tabla SQL.
- YAML config (responsabilidad del usuario en git separado).

Destino: configurable en `config/settings.yaml > backup.destination` (path local, S3, Azure Blob, GCS).

### Restore probado semanal

En Dreaming (Fase 5): ejecuta restore parcial sobre instancia sandbox y valida integridad de datos. Si falla: alerta crítica al usuario.

---

## Sin quotas por usuario en version de prueba (C0)

La decision #29 queda obsoleta para esta version. No se implementa `quota_manager.py`, tiers Free/Pro/Enterprise ni `429` por consumo de usuario.

Se conserva:

| Mecanismo | Motivo |
|---|---|
| Telemetria de tokens/costo/sesiones | Visibilidad operacional y estimacion de costos. |
| Circuit breakers tecnicos | Proteger contra tools/MCPs caidos o loops fallidos. |
| Capability tokens | Limitar scope/TTL de acciones autonomas. |
| Anomaly detection | Bloquear patrones raros o peligrosos. |
| Rate limits por proveedor externo | Respetar APIs y evitar ban/costos inesperados. |

---

## Compliance

### Data residency declarada (decisión #31)

`config/settings.yaml > compliance.data_residency: <region>`. Validado al boot: los servicios externos usados (MCPs, LLM) deben respetar la región declarada.

`company_geo` no reemplaza data residency: orienta normativa y fuentes locales; data residency orienta donde se procesan/guardan datos.

### Right to be forgotten

Tool admin `forget_user(user_id)`. Borrado en cascada de:
- `audit_events_jsonl_index` filtrado por user_id (líneas JSONL relevantes purgadas).
- `subagents`, `pending_approvals`, `agent_modifications` con session_id asociado.
- Chunks en TurboVecIndex cuya `acl_scopes` incluyan user_id como único owner.
- OAuth credentials del usuario.

Solo invocable por admin con confirmación escrita explícita.

### DPA template + SOC 2 readiness checklist

`docs/compliance/dpa-template.md` y `docs/compliance/soc2-readiness-checklist.md` (creados en F0).

---

## Encryption (decisión #32)

- **At rest**: TDE en PostgreSQL. TurboVec/SQLite encryption opcional con LUKS/BitLocker a nivel disco.
- **In transit**: TLS obligatorio en SSE, webhooks, MCPs. Cert validation no-skip.
- **Key rotation policy**: 90 días para Fernet keys de OAuth credentials.

---

## PII detection + redaction (decisión #33)

`enterprise/governance/pii_redactor.py` usando Microsoft Presidio.

**Idiomas**: español (`es_core_news_md` spaCy) + inglés (`en_core_web_sm`). Validar A7 al inicio de F0.

**Cuándo se aplica**:
- ANTES de indexar (opcional, configurable per-connector): redacta cédulas, emails, teléfonos, nombres antes de chunkear/embedar.
- ANTES de pasar al LLM (opcional, configurable per-playbook): redacta PII detectado en el contexto enviado.

**Opt-in**: deshabilitado por default. Activación per-tenant en `config/settings.yaml > pii.enabled: true` + lista de entidades a redactar.

---

## Approval workflows (reformulados por D4 esta sesión)

### Set residual después de D4

Antes (decisión #44 original): cualquier modificación a `config/` requería approval o estaba prohibida.

Ahora (D4): el agente puede modificar TODO con audit trail. Approvals residuales:

| Escenario | Approval requerido | Implementación |
|---|---|---|
| Envío masivo emails > 10 destinatarios | Sí | `enterprise/governance/approval_queue.py` |
| Mutaciones masivas CRM > 5 registros | Sí | Idem |
| Modificación a `config/company/policies.md` | Sí | `AgentModifier._requires_approval` (doc 05) |
| Modificación a archivos en `audit.approval_required_for_files` del Modo | Sí (configurable per-Mode) | Idem |
| Primera ejecución autónoma de skill aprendido por demostración | Sí | Doc 04 |
| Acción en goal-pursuit detectada como anómala por `AnomalyDetector` | Sí | Doc 03 + #108 |
| Cualquier acción que el playbook declare `require_approval_at_end_of: [fase]` | Sí | Doc 03 |

**Cola de approvals**: tabla `pending_approvals(id, tenant_id, kind, payload, requested_by_agent, requested_at, status)`. UI `/admin/audit/pending` muestra con botones Aprobar / Rechazar / Modificar.

**TTL**: approvals sin acción humana en 24h → notificación; en 72h → expiran (rechazo automático con motivo "timeout").

---

## Política "no delete" (decisión #45)

Cualquier método `delete_*` en todas las tools se **gating-out automáticamente** al boot. El `ToolRegistry` inspecciona las capabilities declaradas y excluye las que empiezan por `delete`.

**Excepciones** (lista mantenida en `config/settings.yaml > tools.delete_whitelist`):
- `forget_user` (right to be forgotten — admin only).
- Eliminación de archivos temporales del propio harness (`tempfile.unlink`).

Cualquier otra eliminación es responsabilidad humana directa.

---

## Idioma + LanguageRouter (decisión #40)

`enterprise/governance/language_router.py`.

**Regla**: interno (lo que ve el LLM) en **inglés**. Externo (lo que ve el usuario) en idioma detectado, default **español**.

Aplica a:
- System prompts, BranchOverlay, AgentRole, tool descriptions, schemas, SOUL.md, COMPANY.md, playbooks YAML → inglés.
- Respuestas finales, correos, informes, mensajes en canales, entregables de templates → idioma detectado por turno.

Detección: heurística + LLM fallback. Override per-Mode con `mode_settings.language_default`.

---

## Migration runner + update mechanism (decisión #43)

### Migraciones SQL crudo (MigrationRunner)

> **Reformulada**: el 2.0 usa `MigrationRunner` forward-only + SQL crudo en `infra/db/migrations/NNN_*.sql`; Alembic descartado (spec 009 T009).

Schema versionado. Auto-run en boot.

### Automantenimiento admin de tools/MCPs

Aplica a `WRAP-SDK`, `CLONE-UPSTREAM`, MCPs externos, skills marketplace y adapters locales. Cuando upstream publica fix de seguridad (CVE), nueva release, cambio de schema o nuevas capabilities:

1. Dreaming admin verifica versiones nuevas en PyPI/npm/repos Git.
2. Si hay CVE crítico o cambio relevante → notifica al admin en Dreaming Report.
3. Crea propuesta con diff, impacto, riesgo y pruebas.
4. Admin aprueba upgrade vía frontend admin o `vigilador-admin update <tool>`.
5. Tests E2E del tool/MCP se ejecutan automáticamente en sandbox; si fallan, rollback.

Para `COPY-HERMES` modularizado, no se auto-pisa codigo local: se abre propuesta de cherry-pick/manual port con atribucion.

---

## Versionado de prompts/playbooks (decisión #35)

Tabla `prompt_versions(id, file, content_hash, activated_at, rollback_to)` — subsumida en `agent_modifications` por D4 (doc 05). El tracking sigue siendo el mismo, solo cambia la tabla destino.

---

## Resumen de los 3 guardrails que sostienen D4

D4 (full autonomy) sería peligrosa sin estos 3 guardrails que conservan su rigor:

1. **AnomalyDetector** (decisión #108) — bloquea desviaciones del baseline.
2. **Capability tokens** (decisión #107) — limitan scope/TTL de sesiones autónomas.
3. **Approval-gate residual** — exige aprobación humana para los casos críticos listados arriba.

Si alguno se desactivara, D4 sería inseguro.

---

## Integración con el resto del set

| Doc | Cómo se integra |
|---|---|
| [01 Arquitectura](01-vision-y-arquitectura.md) | Define dónde viven los componentes de governance/observability dentro de `enterprise/`. |
| [02 Modos](02-modos-y-personalidades.md) | `mode_settings.require_approval_for` y `audit.approval_required_for_files` configuran las políticas per-Mode. |
| [03 Playbooks](03-playbooks-y-orquestacion.md) | `require_approval_at_end_of` declara approvals per-fase. `cove_required`, `sandbox_required` aplican las políticas. |
| [04 Skills](04-skills-y-capacidades.md) | `audit.level` declarado en cada skill dispara el nivel de logging definido aquí. |
| [05 Autoaprendizaje](05-autoaprendizaje-y-autonomia.md) | `AgentModifier`, `agent_modifications`, los 3 guardrails — viven aquí, ese doc los USA. |
| [06 Catálogo tools](06-catalogo-tools-y-extraccion.md) | Las API keys, tool-gating, MCPProcessSupervisor aplican las políticas definidas aquí. |
| [07 Migración](07-migracion-2.0-a-3.0.md) | Define cuándo se implementa cada política (F1/F3/F5). |

---

## Decisiones implementadas por este doc

Este doc consolida (ver `ANEXO-B-decision-log-por-tema.md`):

- **#16** (COMPANY partido en 5 archivos).
- **#18** (Tool-gating por API key).
- **#26-35** (multi-tenancy, observability, DR, SSO, compliance, encryption, PII; quotas por usuario obsoletas por C0).
- **#40** (LanguageRouter).
- **#43** (MigrationRunner + SQL crudo + update mechanism; reformulada).
- **#44** **REFORMULADA por D4** — approvals residuales listados aquí.
- **#45** (política "no delete").
- **#53** (file_safety + redact COPY-HERMES).
- **#61** (Circuit breaker uniforme).
- **#64** (MCPProcessSupervisor — detalle en doc 06).
- **#81** (fix CQS health monitor).
- **#86** (multi-tenancy aplica a todas las capas).
- **#87** (backup unificado 3 fuentes).
- **#106** (PI defense con cuarentena).
- **#107** (Capability tokens).
- **#108** (Anomaly detector).
- **C0** sin quotas por usuario, company_geo, automantenimiento admin y normativa localizada.

---

## Criterios de verificación

Tras implementar este doc:

1. **Test de gating por API key**: deshabilitar `TAVILY_API_KEY` en env → `tavily_search` no aparece en `vigilador-admin tools list`.
2. **Test de tool-gating local**: en máquina sin AutoCAD → `autocad_local` no se registra.
3. **Test de capability token expirado**: emitir token TTL 1 min, esperar 2 min, intentar usar tool del scope → falla con `403`.
4. **Test PI defense**: enviar email con payload `"ignore previous instructions and ..."` → entrada en `pi_quarantine`, agente NO ejecuta acción.
5. **Test anomaly detector**: simular cambio masivo en `config/soul.md` desde un agente → bloqueo con `vigilador_anomaly_blocked_total` incrementado.
6. **Test backup + restore**: ejecutar `vigilador-admin backup now` → crear archivos; ejecutar restore a instancia sandbox → datos íntegros.
7. **Test sin quotas por usuario**: usuario con alto consumo no recibe `429` por tier; metricas de costo/tokens se registran y circuit breakers tecnicos siguen activos.
8. **Test PII redaction**: indexar doc con cédula colombiana → al consultar, la cédula aparece como `[ID_REDACTED]`.
9. **Test approval flow**: agente intenta enviar email a 12 destinatarios → queda en `pending_approvals`, NO se envía hasta approval.
10. **Test "no delete"**: agente intenta invocar `hubspot.delete_contact` → tool no aparece en su listing (gating-out).
11. **Test idioma**: usuario escribe en inglés → respuesta en inglés; usuario escribe en español → respuesta en español. Logs muestran prompts internos en inglés en ambos casos.
12. **Test admin maintenance**: nueva release de MCP genera propuesta admin con pruebas; no se promueve automaticamente.
