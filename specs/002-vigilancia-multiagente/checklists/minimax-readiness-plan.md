# Plan: MiniMax Readiness + Embedding Fix + Prompts Separation

**Created**: 2026-05-12  
**Goal**: Que al configurar `VT_MINIMAX_API_KEY`, todo funcione sin reescribir código.

---

## Fase 1: MiniMax Client — Parámetros faltantes

### 1.1 Base URL incorrecta

```diff
# src/config/settings.py
- minimax_base_url: str = "https://api.minimax.chat/v1"
+ minimax_base_url: str = "https://api.minimax.io"
```

La documentación oficial usa `api.minimax.io`, no `.chat`. El cliente hace POST a `/v1/chat/completions`, así que la URL final correcta es `https://api.minimax.io/v1/chat/completions`.

### 1.2 Faltan `max_tokens` y `temperature` en el payload

```diff
# src/infra/llm/minimax_client.py
  json={
      "model": self._settings.minimax_model,
      "messages": [...],
+     "max_tokens": 100000,
+     "temperature": 0.3,
      "tools": tools or [],
      "tool_choice": tool_choice or "auto",
  },
```

Estos valores están definidos en `system-base.md` (Model Behavior) pero el cliente nunca los envía. MiniMax usa sus valores por defecto (probablemente más bajos).

### 1.3 Agregar soporte `stream`

```diff
  async def complete(
      self,
      messages: list[MiniMaxMessage],
      *,
      tools: list[dict[str, Any]] | None = None,
      tool_choice: str | None = None,
+     stream: bool = False,
  ) -> MiniMaxResponse:
      ...
      json={
          ...,
+         "stream": stream,
      },
```

La documentación de MiniMax muestra `stream: true` como parte del payload. Necesario para SSE.

### 1.4 Agregar `reasoning_split` (Interleaved Thinking)

MiniMax-M2.7 soporta interleaved thinking — el modelo razona entre tool calls. El parámetro `reasoning_split=True` separa el thinking en `reasoning_details`. Sin esto, el thinking viene envuelto en `<think>` tags dentro del `content`.

```diff
  json={
      ...,
+     "reasoning_split": True,
  },
```

**Impacto en `_parse_response`**: Si `reasoning_split=True`, el thinking llega en `reasoning_details` en vez de dentro de `<think>` tags.

---

## Fase 2: Gemini Embedding — Task Prefix fijo

### 2.1 Estado actual

| Archivo | Línea | Uso | Prefix |
|---------|-------|-----|--------|
| `gemini_gateway.py:26` | `embed_document(text)` | `f"document: {text}"` | Siempre `document:` |
| `research_outputs.py:110` | `embed_document(query)` | Búsqueda semántica **query** | ❌ Usa `document:` |
| `base.py:130` | `embed_documents(embeddings)` | **Documentos** de iteraciones | ✅ Usa `document:` |

### 2.2 Documentación Gemini

`gemini-embedding-2` recomienda usar **task prefixes** para retrieval asimétrico:
- **Query**: `query: {text}`
- **Document**: `document: {text}`

### 2.3 Fix

Agregar método `embed_query()` y una enumeración de task types:

```python
# src/infra/embeddings/gemini_gateway.py

class TaskType:
    RETRIEVAL_QUERY = "RETRIEVAL_QUERY"
    RETRIEVAL_DOCUMENT = "RETRIEVAL_DOCUMENT"

class GeminiEmbeddingGateway:
    async def embed_document(self, text: str) -> list[float]:
        # Mantiene compatibilidad — equivale a RETRIEVAL_DOCUMENT
        ...

    async def embed(self, text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> list[float]:
        prefix = "query:" if task_type == "RETRIEVAL_QUERY" else "document:"
        # Usa el prefix correcto
        ...
```

```diff
# src/api/routes/research_outputs.py:110
- query_vector = await embedding_gateway.embed_document(query)
+ query_vector = await embedding_gateway.embed(query, task_type="RETRIEVAL_QUERY")
```

---

## Fase 3: Conectar MiniMax al Flujo

### 3.1 Clarificación

```diff
# src/application/clarification/clarification_service.py
- def generate_questions(self, user_query: str) -> list[ClarificationQuestion]:
-     del user_query
-     return [preguntas fijas...]
+ def generate_questions(self, user_query: str, llm: MiniMaxClient | None) -> list[ClarificationQuestion]:
+     if llm is not None:
+         prompt = load_prompt("orchestration/clarify.txt")
+         response = await llm.complete(messages=[MiniMaxMessage(role="user", content=prompt.format(user_query=user_query))])
+         # parsear respuesta JSON → questions
+     else:
+         return [preguntas_fijas]  # fallback actual
```

**Archivo prompt**: `src/prompts/orchestration/clarify.txt`

### 3.2 Planificación

```diff
# src/application/planning/plan_builder.py
- def build(self, session_id, answers) -> ResearchPlan:
-     # templates hardcodeados
+ def build(self, session_id, answers, llm: MiniMaxClient | None) -> ResearchPlan:
+     if llm is not None:
+         prompt = load_prompt("orchestration/planning.txt")
+         response = await llm.complete(...)
+         # parsear plan JSON
+     else:
+         # fallback actual con templates
```

**Archivo prompt**: `src/prompts/orchestration/planning.txt`

### 3.3 Síntesis

```diff
# src/application/fusion/report_synthesizer.py
- def synthesize(self, ...) -> SynthesizedReport:
-     # concatenación básica
+ def synthesize(self, ..., llm: MiniMaxClient | None) -> SynthesizedReport:
+     if llm is not None:
+         prompt = load_prompt("orchestration/synthesis.txt")
+         response = await llm.complete(...)
+         # parsear reporte estructurado con cross-analysis
+     else:
+         # fallback actual
```

**Archivo prompt**: `src/prompts/orchestration/synthesis.txt`

---

## Fase 4: Prompts en Archivos Separados

### 4.1 Estructura

```
src/prompts/
├── orchestration/
│   ├── clarify.txt        # Generación de preguntas de clarificación
│   ├── planning.txt       # Generación de plan de investigación
│   └── synthesis.txt      # Síntesis y generación de reporte
└── branches/
    ├── avances.txt        # Prompt rama Avances (branch overlay)
    ├── comercial.txt
    ├── riesgo.txt
    ├── pi_normativa.txt
    ├── competitivo.txt
    └── oportunidades.txt
```

### 4.2 Loader

```python
# src/infra/prompts/loader.py
from pathlib import Path

_PROMPTS_ROOT = Path(__file__).parent


def load_prompt(path: str) -> str:
    """Load a prompt template from src/prompts/{path}.txt"""
    file = _PROMPTS_ROOT / f"{path}.txt"
    return file.read_text(encoding="utf-8")
```

### 4.3 Migración de BranchOverlay

Hoy los `_BRANCH_OVERLAYS` están hardcodeados en `contract_loader.py`. La idea es:

1. Crear `src/prompts/branches/{branch_type}.txt` con el contenido del overlay
2. `load_branch_overlay()` lee del archivo en vez del dict hardcodeado
3. Mantener compatibilidad: si el archivo no existe, usar el dict actual como fallback

---

## Fase 5: MiniMax Interleaved Thinking

### 5.1 Preservar `reasoning_details` en historial

Cuando se usa `reasoning_split=True`, la respuesta de MiniMax incluye `reasoning_details` que debe preservarse en el historial de mensajes para mantener la continuidad del razonamiento.

```diff
# mini max_client.py — _parse_response
+ if "reasoning_details" in choice.get("reasoning_details", {}):
+     # extraer thinking del campo reasoning_details
+ else:
+     # extraer content (puede contener <think> tags)
```

### 5.2 `MiniMaxResponse` debe exponer `reasoning`

```diff
@dataclass(slots=True, frozen=True)
class MiniMaxResponse:
    content: str
+   reasoning: str = ""
    tool_calls: tuple[MiniMaxToolCall, ...] = field(default_factory=tuple)
    raw: dict[str, Any] = field(default_factory=dict)
```

---

## Resumen de Archivos a Modificar

| Archivo | Cambio | Líneas |
|---------|--------|--------|
| `config/settings.py` | Base URL `.chat` → `.io` | 1 |
| `infra/llm/minimax_client.py` | `max_tokens`, `temperature`, `stream`, `reasoning_split` | +8 |
| `infra/embeddings/gemini_gateway.py` | `embed()` con task prefix, `embed_query()` | +15 |
| `api/routes/research_outputs.py` | Usar `embed(..., task_type="RETRIEVAL_QUERY")` | 1 |
| `application/clarification/clarification_service.py` | Llamar a MiniMax si está disponible | +20 |
| `application/planning/plan_builder.py` | Llamar a MiniMax si está disponible | +20 |
| `application/fusion/report_synthesizer.py` | Llamar a MiniMax si está disponible | +20 |
| `infra/prompts/loader.py` | **Nuevo** — loader de prompts | +10 |
| `src/prompts/orchestration/clarify.txt` | **Nuevo** | +15 |
| `src/prompts/orchestration/planning.txt` | **Nuevo** | +25 |
| `src/prompts/orchestration/synthesis.txt` | **Nuevo** | +30 |
| `src/prompts/branches/*.txt` | **6 archivos nuevos** | +30 total |
| `application/governance/contract_loader.py` | Cargar overlays desde archivos | +15 |
| `domain/system_base.py` | `reasoning` field en `MiniMaxResponse` | +1 |

**Total**: ~200 líneas nuevas, 2 existentes modificadas.

## Tasks Propuestas

| ID | Descripción | Subagente |
|----|-------------|-----------|
| T101 | Fix base URL en settings.py | ✅ |
| T102 | Agregar max_tokens, temperature, stream, reasoning_split a MiniMaxClient | ✅ |
| T103 | Agregar embed() con task prefix + embed_query() en gemini_gateway.py | ✅ |
| T104 | Actualizar research_outputs.py a embed(task_type="RETRIEVAL_QUERY") | ✅ |
| T105 | Conectar MiniMax a ClarificationService | ❌ (mismo archivo que T106) |
| T106 | Conectar MiniMax a PlanBuilder | ❌ |
| T107 | Conectar MiniMax a ReportSynthesizer | ❌ |
| T108 | Crear src/prompts/orchestration/ (3 archivos) | ✅ |
| T109 | Crear src/prompts/branches/ (6 archivos) | ✅ |
| T110 | Crear infra/prompts/loader.py | ✅ |
| T111 | Migrar BranchOverlay de contract_loader.py a archivos | ❌ |
| T112 | Tests: verificar que MiniMaxClient envía los parámetros correctos | ✅ |
