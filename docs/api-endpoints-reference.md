# API Endpoints Reference

> Linea base de endpoints del backend Vigilador Tecnologico 2.0
> Generado: Mayo 2026

---

## Convenciones

- **Base URL**: `/api/v2/` en desarrollo (proxy Vite), `http://localhost:8000/api/v2/` directo
- **Snake_case**: backend real devuelve keys en snake_case
- **CamelCase**: frontend espera camelCase (convertido via transform layer en `frontend/src/api/transform.ts`)
- **SSE**: Server-Sent Events en `text/event-stream`

---

## Endpoints REST

### 1. Start Research

| Metodo | Ruta | Estado |
|--------|------|--------|
| POST | `/research/start` | ✅ Backend + Mock |

**Request body**: `{ "query": string, "scope?" : Record<string, string> }`

**Response (200)**:
```json
{
  "sessionId": "uuid",
  "status": "CLARIFYING",
  "questions": [{ "id": "q1", "text": "..." }]
}
```

---

### 2. Clarify Session

| Metodo | Ruta | Estado |
|--------|------|--------|
| POST | `/research/{session_id}/clarify` | ✅ Backend + Mock |

**Request body**: `{ "answers": Record<string, string> }`

**Response (200)**:
```json
{
  "sessionId": "uuid",
  "status": "PLANNING",
  "requiresApproval": true,
  "plan": { ... ResearchPlan }
}
```

---

### 3. Get Plan

| Metodo | Ruta | Estado |
|--------|------|--------|
| GET | `/research/{session_id}/plan` | ✅ Backend + Mock |

**Response (200)**:
```json
{
  "sessionId": "uuid",
  "plan": { "id": "uuid", "version": 1, "branches": [...], "requiresApproval": true, "globalConstraints": {...} }
}
```

---

### 4. Approve Plan

| Metodo | Ruta | Estado |
|--------|------|--------|
| POST | `/research/{session_id}/approve` | ✅ Backend + Mock |

**Request body**: `{ "approved": true }`

**Response (200)**:
```json
{
  "sessionId": "uuid",
  "status": "EXECUTING",
  "message": "..."
}
```

---

### 5. Get Report

| Metodo | Ruta | Estado |
|--------|------|--------|
| GET | `/research/{session_id}/report` | ✅ Backend + Mock |

**Response (200)**:
```json
{
  "sessionId": "uuid",
  "markdown": "# ...",
  "executiveSummary": "...",
  "technicalSection": "...",
  "commercialSection": "...",
  "riskSection": "...",
  "crossAnalysis": "...",
  "recommendations": [{ "text": "...", "priority": "alta|media|baja", "basedOn": ["..."] }],
  "totalSourcesConsulted": 12,
  "totalLearnings": 28,
  "confidenceScore": 0.847,
  "generatedAt": "ISO8601"
}
```

---

### 6. Get Sources

| Metodo | Ruta | Estado |
|--------|------|--------|
| GET | `/research/{session_id}/sources` | ✅ Backend + Mock |

**Response (200)**:
```json
{
  "sessionId": "uuid",
  "total": 12,
  "items": [{ "id": "uuid", "url": "...", "title": "...", "provider": "...", "branchType": "...", "accessedAt": "ISO8601" }]
}
```

---

### 7. Get Graph

| Metodo | Ruta | Estado |
|--------|------|--------|
| GET | `/research/{session_id}/graph` | ✅ Backend + Mock |

**Response (200)**:
```json
{
  "sessionId": "uuid",
  "nodes": [{ "id": "n1", "label": "...", "centrality": 0.95, "branchType": "...", "nodeType": "...", "sourceIds": [], "confidence": 0.9 }],
  "edges": [{ "id": "e1", "source": "n1", "target": "n2", "relationType": "...", "similarityScore": 0.88 }]
}
```

---

### 8. Graph Analytics

| Metodo | Ruta | Estado |
|--------|------|--------|
| GET | `/research/{session_id}/graph/analytics` | ✅ Backend + Mock |

**Response (200)**:
```json
{
  "sessionId": "uuid",
  "centralNodes": ["n1", ...],
  "clusters": [{ "id": "cl1", "label": "...", "nodeIds": [...] }],
  "density": 0.134,
  "avgPathLength": 2.47,
  "clusteringCoefficient": 0.412
}
```

---

### 9. Search Graph

| Metodo | Ruta | Estado |
|--------|------|--------|
| GET | `/research/{session_id}/graph/search?query=...` | ✅ Backend + Mock |

**Response (200)**:
```json
{
  "items": [{ "nodeId": "n1", "label": "...", "score": 0.9 }]
}
```

---

### 10. Graph Path

| Metodo | Ruta | Estado |
|--------|------|--------|
| GET | `/research/{session_id}/graph/path?sourceNodeId=x&targetNodeId=y` | ✅ Backend + Mock |

**Response (200)**:
```json
{
  "nodeIds": ["x", "n1", "y"],
  "edgeIds": ["e1", "e4"],
  "totalCost": 0.42
}
```

---

### 11. Get Providers / Metrics

| Metodo | Ruta | Estado |
|--------|------|--------|
| GET | `/research/{session_id}/providers` | ✅ Backend + Mock |

**Response (200)**:
```json
{
  "sessionId": "uuid",
  "providers": [{ "name": "tavily", "avgLatencyMs": 843, "errorRate": 0.02, "retryRate": 0.03 }],
  "branchKpis": [{ "branchType": "AVANCES", "coverageKpi": 0.91, "precisionKpi": 0.87, "latencyMsKpi": 4320 }],
  "confidenceScore": 0.847,
  "totalSources": 12,
  "totalFindings": 28,
  "confidenceCalibration": [{ "bucket": "0.6-0.8", "predicted": 0.71, "observed": 0.64, "samples": 23, "factor": 0.90 }]
}
```

---

### 12. Delete Session

| Metodo | Ruta | Estado |
|--------|------|--------|
| DELETE | `/research/{session_id}` | ✅ Backend + Mock |

**Response (200)**:
```json
{ "status": "deleted", "sessionId": "uuid" }
```

---

### 13. Follow-up Question (Conversation)

| Metodo | Ruta | Estado |
|--------|------|--------|
| POST | `/sessions/{session_id}/ask` | ✅ Backend + Mock |

**Request body**: `{ "query": "..." }`

**Response (200)**:
```json
{
  "answer": "...",
  "sources": ["source-id-1"],
  "requiresPermission": false
}
```

---

### 14. End Conversation

| Metodo | Ruta | Estado |
|--------|------|--------|
| DELETE | `/sessions/{session_id}/conversation` | ✅ Backend + Mock |

**Response (200)**:
```json
{ "status": "closed" }
```

---

### 15. Session Timeline

| Metodo | Ruta | Estado |
|--------|------|--------|
| GET | `/sessions/timeline` | ✅ Backend + Mock |

**Response (200)**:
```json
{
  "sessions": [{ "sessionId": "uuid", "querySummary": "...", "timestamp": "ISO8601", "entities": [], "findingCount": 28 }]
}
```

---

### 16. Report Export

| Metodo | Ruta | Estado |
|--------|------|--------|
| GET | `/reports/{report_id}/export?format=md|html` | ✅ Backend + Mock |

**Response (200)**:
```json
{ "content": "#...", "format": "md", "reportId": "uuid" }
```

---

### 17. Adjust Source Score

| Metodo | Ruta | Estado |
|--------|------|--------|
| PATCH | `/sources/{source_id}/score` | ✅ Backend + Mock |

**Request body**: `{ "delta": 1, "reason": "..." }`

**Response (200)**:
```json
{ "sourceId": "uuid", "newScore": 76, "adjustment": 1, "reason": "..." }
```

---

### 18. Upload Document

| Metodo | Ruta | Estado |
|--------|------|--------|
| POST | `/upload/document` | ✅ Backend + Mock |

**Response (200)**:
```json
{ "markdown": "#...", "format": "pdf", "filename": "documento.pdf" }
```

---

## SSE Events Stream

**Endpoint**: `GET /research/{session_id}/stream`
**Content-Type**: `text/event-stream`

### Event Sequence (orden cronologico, ~35s total)

| Evento | Time | Payload |
|--------|------|---------|
| `SessionStarted` | t=0s | `{ sessionId, userQuery }` |
| `ClarificationRequested` | t=0s | `{ questions: [{ id, text }] }` |
| `PlanGenerated` | t=0s | `{ plan: ResearchPlan }` |
| `BranchStarted` | t~0.3s | `{ branch: "AVANCES" }` (x6) |
| `BranchProgress` | t~2-8s | `{ branch, iteration: ThinkingStep }` (multiple) |
| `ReplanTriggered` | t~3s | `{ signalType, sourceBranch, targetBranch, description, directive }` |
| `BranchCompleted` | t~9-12s | `{ branch }` (x6) |
| `AllBranchesCompleted` | t~13s | `{ sessionId }` |
| `FusionStarted` | t~14s | `{ sessionId }` |
| `FusionProgress` | t~16s | `{ sessionId, progress: 50 }` |
| `FusionProgress` | t~18s | `{ sessionId, progress: 100 }` |
| `GraphBuildingStarted` | t~19s | `{ sessionId }` |
| `GraphAnalyticsComputed` | t~21s | `{ sessionId }` |
| `ReportGenerated` | t~24s | `{ sessionId, report_id, confidence_score }` |
| `ReportVariantsGenerated` | t~25s | `{ types: ["markdown", "html"] }` |

**Nota**: El backend real emite `ReportGenerated` solo con `{ report_id, confidence_score }`. El frontend debe obtener el reporte completo via `GET /research/{id}/report`.

---

## TypeScript Type Mapping

| Tipo TS | Archivo | Endpoint relacionado |
|---------|---------|---------------------|
| `SessionStatus` | `types/index.ts` | Todos |
| `ResearchPlan` | `types/index.ts` | GET /plan, POST /clarify |
| `FinalReport` | `types/index.ts` | GET /report |
| `GraphData` | `types/index.ts` | GET /graph |
| `GraphNode` | `types/index.ts` | GET /graph |
| `GraphEdge` | `types/index.ts` | GET /graph |
| `AnalysisMetrics` | `types/index.ts` | GET /providers |
| `BranchKPI` | `types/index.ts` | GET /providers |
| `ProviderMetric` | `types/index.ts` | GET /providers |
| `FollowUpAnswer` | `types/index.ts` | POST /ask |
| `SourceScoreResult` | `types/index.ts` | PATCH /score |
| `SessionTimelineEntry` | `types/index.ts` | GET /timeline |
| `ChatMessage` | `types/index.ts` | — (frontend-only) |
| `SSEConnectionStatus` | `types/index.ts` | — (frontend-only) |

---

## Rutas faltantes (identificadas en auditoria)

Las siguientes rutas existen en el backend real pero NO estan en el mock server (antes de Phase 5):

| Ruta | Metodo | Estado anterior | Estado actual |
|------|--------|----------------|---------------|
| `/research/{id}/graph/nodes` | GET | ❌ Solo en backend | ✅ Agregado |
| `/research/{id}/graph/edges` | GET | ❌ Solo en backend | ✅ Agregado |
| `/research/{id}/graph/{node_id}/sources` | GET | ❌ Solo en backend | ✅ Agregado |
| `/research/{id}/modify` | POST | ❌ Solo en backend | ✅ Agregado |
| `/research/{id}/graph/ecosystem` | GET | ❌ Solo en backend | ✅ Agregado |
| `/research/{id}/graph/search-cross-session` | GET | ❌ Solo en backend | ✅ Agregado |
| `/research/{id}/decision` | POST | ❌ Solo en backend | ✅ Agregado |
| `/research/{id}/obsolescence` | POST | ❌ Solo en backend | ✅ Agregado |
| `/research/{id}/hype-analysis` | POST | ❌ Solo en backend | ✅ Agregado |
| SSE `FusionProgress` | SSE | ❌ Solo en mock | ✅ Corregido |
| SSE `BranchFailed` | SSE | ❌ Solo en backend | ✅ Agregado mock |
| SSE `EvaluationComputed` | SSE | ❌ Solo en backend | ✅ Agregado mock |
