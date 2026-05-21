# Research: Saneamiento Arquitectonico — Decisiones Tecnicas

## 1. Organizacion de Protocols

**Decision**: Un archivo por Protocol en `domain/ports/<name>.py`.

**Rationale**:
- ISP estricto: cada Protocol se importa independientemente sin arrastrar otros.
- Cohesion: cada archivo contiene solo lo necesario para ese contrato.
- Testabilidad: los fakes pueden importar solo el Protocol que necesitan.
- El archivo unico `domain/repositories.py` con 6 Protocols se depreca como
  contenedor, pero los Protocols existentes se migran uno a uno (sin romper
  imports existentes).

**Alternativas consideradas**:
- `domain/ports.py` unico: archivo grande, viola ISP en la practica.
- `domain/protocols/__init__.py` re-exportando todo: conveniente pero
  oculta dependencias reales.

## 2. Skill Matrices: YAML vs JSON

**Decision**: YAML con schema de validacion.

**Rationale**:
- YAML es mas legible para configuracion (comentarios, formato libre).
- Permite documentacion inline de cada skill/tool.
- Schema validador (usando `pydantic` o `dataclasses`) garantiza integridad
  al cargar.
- JSON seria mas parseable pero menos mantenible por humanos.

**Estructura YAML propuesta**:
```yaml
# config/skills/skill_matrix_default.yaml
version: 1
branches:
  AVANCES:
    tool_order:
      - tavily_search
      - exa_search
      - jina_fetch
    timeout: 30
    retry_limit: 2
  RIESGO:
    tool_order:
      - brave_search
      - serper_search
    timeout: 45
    retry_limit: 3
defaults:
  timeout: 20
  retry_limit: 1
```

## 3. Pipeline Pattern

**Decision**: Chain of Responsibility simple con interfaz generica.

**Rationale**:
- `PipelineStep[T]` con un unico metodo `execute(context: PipelineContext) -> T`
- Sin workflow engine, sin DAG, sin estado compartido entre pasos.
- El `Pipeline` orquesta secuencialmente: cada paso recibe el context,
  lo procesa y pasa al siguiente.
- Suficiente para 3-5 pasos lineales. Si en el futuro se necesitan pasos
  condicionales, se agrega un `ConditionalStep` wrapper sin cambiar la
  interfaz base.

**Alternativas consideradas**:
- Workflow engine (Temporal, Prefect): overkill para 3-5 pasos lineales.
- DAG de pasos: complejidad innecesaria (no hay bifurcaciones hoy).
- Funciones sueltas: funciona pero pierde testabilidad unitaria.

## 4. MCP Response Types: Ubicacion

**Decision**: `application/mcp/types.py`

**Rationale**:
- Son DTOs de application, no entidades de dominio (dependen del protocolo
  MCP, no del negocio).
- `domain/` no debe depender de detalles de transporte.
- `application/mcp/` agrupa toda la logica relacionada a MCP.

**Estructura**:
```python
@dataclass(frozen=True)
class NavigationResult:
    url: str
    title: str
    content: str
    screenshot_path: str | None
    blocked: bool
    block_reason: str | None

@dataclass(frozen=True)
class SearchResult:
    query: str
    results: list[dict[str, str]]
    total_results: int
    source: str  # tavily | exa | brave | serper
```

## 5. Estrategia de Coexistencia

**Decision**: `_legacy` suffix + wrapper de compatibilidad.

**Rationale**:
- Cada funcion/class vieja se renombra con sufijo `_legacy` mientras el
  reemplazo se construye.
- Los consumidores existentes siguen importando el nombre original (que
  ahora es un wrapper o redireccion).
- Cuando el reemplazo completa validacion, se elimina `_legacy` y el
  wrapper.
- Sin feature flags: la fase completa es el unico control de despliegue.

## 6. Script de Validacion de Capas

**Decision**: Script Python simple con `ast` module.

**Rationale**:
- `ast.parse()` recorre todos los archivos `.py` del proyecto.
- Detecta imports de `infra` hacia `api` o `application`.
- Detecta imports de `application` hacia `api`.
- Reporta archivo, linea, import violado.
- Exit code 0 si zero violaciones, 1 si hay alguna.
- Se ejecuta en CI antes de cada merge.

**Alternativas consideradas**:
- `pytest-archlint`: sobreingenieria para lo que necesitamos.
- `import-linter`: externo, no queremos otra dependencia.
