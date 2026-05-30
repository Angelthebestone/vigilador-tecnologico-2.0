# 00 — Canon Operativo Corregido

> Fuente de verdad vigente desde 2026-05-25. Si este documento contradice un archivo previo del set, **manda este documento** y el otro debe corregirse. Su objetivo es quitar dispersion, decisiones obsoletas y sobreingenieria antes de empezar a perfeccionar el sistema.

---

## Lectura obligatoria

Este canon corrige el set de planes 3.0 con 16 decisiones operativas:

1. El **frontend web** es la consola principal del producto, no un canal secundario de comunicacion.
2. Los providers ya existentes en 2.0 para **embeddings por API** y **reranking por API** se preservan y se vuelven seleccionables en onboarding/configuracion.
3. Los **workstreams, modulos de `application/`, ports e infra** del 2.0 son activos del sistema, no deuda a reescribir.
4. La capa de vectorizacion se simplifica: **TurboVecIndex es el indice vectorial unico del 3.0**; no hay doble stack pgvector/TurboVec ni A/B obligatorio.
5. Los modos deben ser **sensibles al pais, departamento y municipio** del usuario/empresa.
6. Cada modelo/proveedor se integra con **adapter propio**; el resto de capacidades se prefieren por libreria/SDK estable.
7. Se pueden importar **skills y comandos de Claude** como catalogo interno versionado.
8. Las decisiones obsoletas quedan marcadas y no deben repetirse en implementacion.
9. Tool calling y skill calling usan **descubrimiento semantico y carga progresiva** para minimizar contexto.
10. Codigo tomado de Hermes/OpenClaw se modulariza antes de entrar al core.
11. No hay **quotas por usuario** en esta version de prueba; solo telemetria y circuit breakers tecnicos.
12. Hay modo de **automantenimiento admin** para repositorios clonados de tools/MCPs.
13. El catalogo de tools/MCPs debe tener un SSOT operativo con origen, estado, estrategia y ownership.
14. Hay **indexacion empresarial** de archivos cloud y locales por conectores nativos o MCPs.
15. Existe modulo de **optimizacion empresarial** para ISO, NTC y normas tecnicas similares.
16. Existe modulo de **artefactos** para crear dashboards, pipelines y visualizaciones de metricas empresariales.

---

## Stack simplificado vigente

| Area | Decision vigente |
|---|---|
| Frontend | `frontend/src` se conserva y se expande como consola: login, onboarding, chat, modos, workstreams, configuracion de providers, fuentes, indexacion, tools/MCPs, Dreaming, artefactos, optimizacion y admin. |
| LLM | Adapter por modelo/proveedor. MiniMax puede ser el default inicial, pero el runtime no debe acoplarse al SDK concreto. |
| Embeddings | Adapter seleccionable. El 2.0 ya tiene `infra/embeddings/gemini_gateway.py`; se preserva como opcion API. Adaptadores locales como `bge-m3` son opcionales, no reemplazo obligatorio. |
| Reranker | Adapter seleccionable. El 2.0 ya tiene `infra/reranking/semantic_reranker.py` con Cohere Rerank por API y fallback por embeddings; se preserva. |
| Vector index | `TurboVecIndex` implementa `domain/ports/vector_index.py` como indice vectorial unico del 3.0. PostgreSQL conserva metadata relacional, auditoria y configuracion operacional; no se exige pgvector como backup. |
| Integracion RAG | Se puede usar LlamaIndex si reduce codigo propio: loaders, chunkers, retrievers o bridge a TurboVec. No se usa para ocultar contratos de dominio. |
| Persistencia auxiliar | JSONL para auditoria operacional, YAML/Markdown para configuracion versionable. SQLite FTS5 queda opcional para busqueda textual de sesiones si ya aporta valor, no como pilar obligatorio. |
| Seguridad | Sin cuotas por usuario. Se mantienen tool-gating, no-delete, capability tokens para acciones autonomas, anomaly detection y audit trail. |

---

## Preservar 2.0 antes de construir 3.0

El 3.0 debe envolver y extender el 2.0. No debe perder:

- `src/vigilancia_multiagente/application/agents/` y sus 6 ramas.
- `src/vigilancia_multiagente/application/agents/pipeline/` y los pasos de workstreams.
- `src/vigilancia_multiagente/application/evaluation/ws_a..ws_e/` y los contratos de evaluacion inteligente.
- `src/vigilancia_multiagente/application/orchestration/`, `planning/`, `research/`, `fusion/`, `graph/`, `memory/`, `routing/`, `artifacts/` y `observability/`.
- `src/vigilancia_multiagente/domain/ports/` como frontera contractual.
- `src/vigilancia_multiagente/infra/mcp/`, `infra/embeddings/`, `infra/reranking/`, `infra/persistence/`, `infra/llm/` y migraciones existentes.
- `frontend/src/chat`, `frontend/src/analysis`, `frontend/src/agents`, `frontend/src/graph`, `frontend/src/history`, stores y API clients existentes.

El playbook `technology-watch` debe ser una envoltura del flujo existente, no una reimplementacion.

---

## Frontend como consola del sistema

El frontend debe permitir, como minimo:

| Superficie | Debe incluir |
|---|---|
| Autenticacion | Inicio de sesion, perfiles, estado de credenciales y permisos. |
| Configuracion inicial | Onboarding de empresa, ubicacion, sector, providers LLM/embedding/reranker, fuentes e indexacion. |
| Operacion diaria | Chat, seleccion de modo, workstreams, aprobaciones, historial, reportes y artefactos. |
| Tools y MCPs | Catalogo disponible, estado, credenciales, health, logs, actualizaciones y repositorios clonados. |
| Datos empresariales | Conectores cloud/locales, progreso de indexacion, ACL, busqueda y reindexacion. |
| Artefactos | Dashboards, pipelines, notebooks/scripts internos, reportes programados y metricas. |
| Optimizacion | Diagnosticos ISO/NTC, planes de mejora, evidencia, responsables y seguimiento. |
| Admin | Dreaming, automantenimiento, rollback de cambios, auditoria y salud del sistema. |

CLI queda como fallback tecnico para administracion, no como experiencia principal del usuario.

---

## Localizacion empresarial

Los modos tienen habilidades estandar, pero el contexto empresarial incluye:

```yaml
company_geo:
  country: "Colombia"
  department: "Santander"
  municipality: "Barrancabermeja"
  timezone: "America/Bogota"
  regulatory_sources_policy: "buscar fuentes oficiales vigentes antes de afirmar"
```

En Dreaming y en modos como `Consultor Legal`, `CFO`, `Operaciones PYME` y `company-optimization`, el sistema debe buscar normativa vigente, impuestos, tasas, requisitos municipales/departamentales/nacionales y normas tecnicas aplicables al pais/region. El plan no debe hardcodear valores tributarios o legales: debe recuperar fuentes actuales, citarlas y guardar evidencia.

---

## Descubrimiento semantico de tools y skills

El runtime no carga todo el catalogo en el prompt. Usa tres niveles:

1. **Lista minima**: id, descripcion corta, dominios, permisos, costo/credenciales, estado.
2. **Ficha resumida**: schema de inputs/outputs y ejemplos cortos solo de candidatos relevantes.
3. **Contenido completo**: `SKILL.md`, instrucciones largas o docs del tool solo cuando ya fue elegido.

La busqueda se hace por embeddings sobre descripciones, tags, capacidades, historico de uso, modo activo, geografia y archivos COMPANY relevantes. El `Mode` y el `Playbook` filtran antes de exponer candidatos al agente.

---

## Importacion de skills y comandos Claude

El sistema puede leer `.claude/skills/*/SKILL.md` y comandos equivalentes como fuente `external:claude-local`.

Reglas:

- Se importan por adapter a `SkillLoader`; no se copian ciegamente al core.
- Se registra licencia/origen/path/hash.
- Los comandos se modelan como `CommandSkill`: receta invocable con parametros, permisos y precondiciones.
- Skills tipo Spec-Kit ya presentes (`speckit-constitution`, `speckit-specify`, `speckit-plan`, `speckit-tasks`, `speckit-analyze`, `speckit-implement`) alimentan el playbook `app-development`.
- Ningun comando con efectos destructivos se expone sin approval o sandbox.

---

## Extraccion de Hermes/OpenClaw sin monolitos

Cada archivo externo pasa por una fase de descomposicion:

1. Identificar contratos reutilizables.
2. Separar cliente SDK/API, normalizacion, politica de seguridad, cache y tool wrapper.
3. Mantener archivos preferiblemente menores a 300-400 LOC salvo excepcion justificada.
4. Agregar tests por modulo, no solo prueba E2E del wrapper.
5. Mantener atribucion y licencia en cabecera y en inventario.

OpenClaw se usa principalmente como referencia de patrones y MCPs; Hermes puede aportar codigo Python, pero no se acepta copiar archivos extensos sin modularizacion.

---

## Automantenimiento admin

El Dreaming de admin revisa repositorios clonados de tools/MCPs:

- Detecta nuevas releases, commits, CVEs, cambios de schema, nuevas capabilities y bugfixes.
- Compara la version local contra upstream.
- Genera propuesta con diff, impacto, riesgo y pruebas a ejecutar.
- Puede actualizar repos/clones en rama temporal o sandbox.
- Requiere aprobacion admin antes de promover cambios a runtime estable.

Esto aplica a MCPs externos, skills marketplace, adapters propios y herramientas copiadas de repos terceros.

---

## Indexacion empresarial

El 3.0 indexa conocimiento empresarial por dos vias:

| Via | Uso |
|---|---|
| Conectores nativos | Drive, OneDrive/SharePoint, local filesystem, Outlook/Gmail, carpetas de red, exports de ERP/CRM/BI. Preferida cuando hay SDK/API estable. |
| MCPs | Fuente alternativa cuando el usuario ya usa un MCP o cuando un repositorio externo ofrece mejor integracion que escribir un conector propio. |

Pipeline minimo: discovery -> permisos/ACL -> extraccion -> normalizacion -> chunking -> dedup -> embeddings -> TurboVecIndex -> metadata relacional -> busqueda con citas.

---

## Optimizacion empresarial

Nuevo modulo: `enterprise/optimization/`.

Responsabilidades:

- Diagnosticar brechas contra ISO, NTC, BPM, SST, calidad, seguridad de informacion, gestion documental u otras normas aplicables.
- Generar plan de mejora por proceso, responsable, evidencia requerida y fecha objetivo.
- Crear checklists, procedimientos, formatos y artefactos de soporte.
- Conectar resultados con dashboards y reportes programados.
- En Colombia, priorizar busqueda de fuentes oficiales y normas vigentes antes de recomendar acciones.

Playbook asociado: `company-optimization`.

---

## Artefactos, dashboards y pipelines

Nuevo modulo: `enterprise/artifacts/`, extendiendo lo ya existente en `application/artifacts/`.

Debe poder crear:

- Dashboards HTML/Streamlit/React internos.
- Pipelines de datos para metricas empresariales.
- Reportes programados y notebooks reproducibles.
- Visualizaciones de KPIs por area.
- Artefactos enlazados a fuentes indexadas y audit trail.

El playbook `app-development` puede producir estos artefactos, pero no es el unico camino. Tambien debe existir flujo directo `artifact-development` para dashboards y pipelines de metricas.

---

## Decisiones obsoletas

No deben implementarse como vigentes:

- Frontend entendido solo como canal de chat/comunicacion.
- Embeddings/reranker locales como reemplazo obligatorio de los providers API existentes.
- pgvector como backup vectorial obligatorio o A/B permanente contra TurboVec.
- Multiplicar motores de persistencia sin rol claro.
- Quotas por usuario para la version de prueba.
- Copiar monolitos grandes de Hermes/OpenClaw sin modularizacion.
- Perder workstreams o modulos 2.0 al crear `enterprise/`.

---

## Checklist de verificacion

- [ ] README enlaza este canon como primera lectura.
- [ ] Doc 01 refleja frontend completo, adapters seleccionables y TurboVecIndex unico.
- [ ] Doc 02 incluye `company_geo` y comportamiento por pais/departamento/municipio.
- [ ] Doc 03 incluye `company-optimization` y `artifact-development`.
- [ ] Doc 04 incluye `external:claude-local` y discovery semantico de skills.
- [ ] Doc 05 incluye automantenimiento admin y busqueda normativa localizada en Dreaming.
- [ ] Doc 06 declara SSOT de tools/MCPs, modularizacion y catalogo por estado.
- [ ] Doc 07 preserva workstreams, ports e infra 2.0 explicitamente.
- [ ] Doc 08 elimina quotas por usuario y conserva telemetria/circuit breakers.
- [ ] ANEXO-B marca decisiones corregidas/obsoletas.
