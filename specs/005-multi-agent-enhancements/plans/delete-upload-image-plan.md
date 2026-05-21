# Implementation Plan: Delete Chats, File Upload & Image Understanding

## Problem

Three feature gaps exist in the current system:

1. **No delete capability**: Users cannot delete research sessions. Sessions accumulate indefinitely with no way to remove old or irrelevant data. The frontend `HistoryBar` renders sessions but has no delete action.

2. **No file upload → document conversion**: Users have documents (PDFs, patents, reports) on their local machine but no way to upload them into the system for analysis via Markitdown MCP. The Markitdown provider exists (`infra/mcp/markitdown_mcp.py`) but there's no API endpoint to receive uploaded files, save them temporarily, and invoke the conversion.

3. **No image understanding**: The MiniMax chat API (`minimax_client.py`) is text-only — it does not accept file attachments or image inputs. The MiniMax Token Plan MCP provides `understand_image(prompt, image_url)` as a separate tool, but it's not registered or wrapped in the project.

## Approach

Implement three independent components:

**A. Delete Conversations**: Backend `DELETE /research/{session_id}` endpoint + frontend delete button in `HistoryBar` + confirmation dialog. Leverages existing `ON DELETE CASCADE` foreign keys.

**B. File Upload → Markitdown**: Backend `POST /upload/document` endpoint that accepts multipart file upload, saves to a temp directory, calls `MarkitdownProvider.convert_to_markdown(file://...)`, returns markdown content. Frontend upload component + result preview.

**C. MiniMax Image MCP**: Register `minimax-image` provider in mcp-providers.json using `uvx minimax-coding-plan-mcp`, create wrapper `infra/mcp/minimax_image_mcp.py` with `understand_image(prompt, image_url)`, add env vars to settings. This is a separate MCP service, NOT a modification to the existing `minimax_client.py`.

---

## Technical Context

| Area | Decision |
|------|----------|
| Delete transport | `DELETE /research/{session_id}` via FastAPI, cascade deletes via PostgreSQL FK |
| File upload storage | Temp directory `uploads/` in project root, cleaned after conversion |
| Markitdown invocation | Via existing `MarkitdownProvider.convert_to_markdown(file://...)` |
| Image MCP transport | STDIO, `uvx minimax-coding-plan-mcp -y` |
| Image MCP tool | `understand_image(prompt: str, image_url: str)` — supports JPEG/PNG/GIF/WebP, max 20MB |
| Image MCP auth | `MINIMAX_API_KEY` env var (separate from `VT_MINIMAX_API_KEY` — uses Token Plan key) |
| Frontend state | Zustand store (`historyStore.ts`) — add `removeSession` action |
| Frontend HTTP | `apiClient.ts` — add `del` method if not exists |

## External Constraints

| Constraint | Impact |
|------------|--------|
| MiniMax chat API does NOT support file attachments | Must use separate MCP tool `understand_image` instead of modifying messages |
| `VT_MINIMAX_API_KEY` may differ from Token Plan key | Need `VT_MINIMAX_IMAGE_API_KEY` env var for the image MCP |
| Image MCP requires `uvx` installed | Must add `uvx` to prerequisites / Docker setup |
| `reasoning_split=True` in minimax_client.py is hardcoded | The image MCP is a separate service — no conflict |
| `uvx minimax-coding-plan-mcp` is an external Python package via `uvx` | Similar to how `npx @playwright/mcp` works — no vendored code |

---

## Files to Create / Modify

### New Files

| File | Purpose |
|------|---------|
| `src/vigilancia_multiagente/api/routes/research_delete.py` | `DELETE /research/{session_id}` endpoint |
| `src/vigilancia_multiagente/api/routes/upload.py` | `POST /upload/document` endpoint for file upload → Markitdown |
| `src/vigilancia_multiagente/infra/mcp/minimax_image_mcp.py` | MiniMax Image MCP provider wrapper (`understand_image`) |
| `frontend/src/components/FileUpload.tsx` | File upload component with drag-and-drop |
| `frontend/src/components/ConfirmDialog.tsx` | Reusable confirmation dialog for delete |

### Modified Files

| File | Changes |
|------|---------|
| `src/vigilancia_multiagente/infra/mcp/mcp-providers.json` | Add `minimax-image` provider entry |
| `src/vigilancia_multiagente/infra/mcp/provider_registry.py` | Register minimax-image in `ensure_standard_providers()` |
| `src/vigilancia_multiagente/config/settings.py` | Add `VT_MINIMAX_IMAGE_API_KEY`, `VT_MINIMAX_API_HOST` |
| `.env.example` | Document new env vars |
| `src/vigilancia_multiagente/api/dependencies.py` | Wire upload service, image provider |
| `src/vigilancia_multiagente/api/router.py` | Register new route files |
| `src/vigilancia_multiagente/application/governance/prompt_composer.py` | Add `understand_image` to `_TOOL_PROMPT_NAMES` |
| `src/vigilancia_multiagente/prompts/tools/minimax_image.txt` | New tool prompt for `understand_image` |
| `frontend/src/history/HistoryBar.tsx` | Add `onDelete` prop, delete button per item |
| `frontend/src/state/historyStore.ts` | Add `removeSession` action |
| `frontend/src/api/endpoints.ts` | Add `deleteSession(id)`, `uploadDocument(file)` |
| `frontend/src/api/client.ts` | Add `apiDel` and `apiUpload` methods |
| `frontend/src/App.tsx` | Wire `onDelete` through to store |
| `frontend/src/components/index.ts` | Export new components |
| `frontend/src/chat/InputBar.tsx` | Add attach/upload button next to input |

---

## Code That Will Become Deprecated

| Code | Deprecation Reason | Replacement |
|------|-------------------|-------------|
| Any attempt to include images in `minimax_client.py` messages | MiniMax chat API does NOT support image attachments in messages | Use `MinimaxImageProvider.understand_image()` wrapper instead |
| `minimax_client.py` `complete()` method's `tool_choice` logic when used with vision tasks | The existing client is text-only; vision/image tasks must go through the image MCP | No change to minimax_client.py — it remains for text chat. Image MCP is a separate service. |
| Manual file handling in frontend (if any exists) | New standardized `apiUpload()` and `FileUpload` component | Upload files via the new endpoint |

**Note**: `minimax_client.py` itself is NOT deprecated — it continues to be the primary text LLM client. Only the concept of "sending images through the text chat API" is deprecated.

---

## Variables to Declare

### Environment Variables (`src/vigilancia_multiagente/config/settings.py`)

```python
# MiniMax Image MCP (Token Plan — separate key from text chat)
minimax_image_api_key: SecretStr | None = None
minimax_api_host: str = "https://api.minimax.io"
```

In `.env.example`:
```
VT_MINIMAX_IMAGE_API_KEY=
VT_MINIMAX_API_HOST=https://api.minimax.io
```

### Frontend State (`frontend/src/state/historyStore.ts`)

```typescript
interface HistoryState {
  sessions: SessionSummary[];
  activeSessionId: string | null;
  loading: boolean;
  error: string | null;
  removeSession: (id: string) => Promise<void>;  // NEW
}
```

### API Client (`frontend/src/api/client.ts`)

```typescript
export async function apiDel<T = unknown>(path: string): Promise<T> { ... }
export async function apiUpload<T = unknown>(path: string, file: File): Promise<T> { ... }
```

### Frontend Endpoints (`frontend/src/api/endpoints.ts`)

```typescript
export async function deleteSession(sessionId: string): Promise<{ status: string }>
export async function uploadDocument(file: File): Promise<{ markdown: string; format: string; filename: string }>
```

---

## Phases

### Phase 1 — Backend: Delete Conversations

1. Create `research_delete.py` with `DELETE /research/{session_id}` endpoint
2. Add to `router.py`
3. Add `apiDel` to frontend client
4. Add `deleteSession` to frontend endpoints

### Phase 2 — Frontend: Delete UI

1. Create `ConfirmDialog.tsx` reusable component
2. Update `HistoryBar.tsx` with `onDelete` prop and delete button
3. Update `historyStore.ts` with `removeSession` action
4. Wire through `App.tsx`

### Phase 3 — Backend: File Upload → Markitdown

1. Create `upload.py` with `POST /upload/document` endpoint
2. Create uploads temp directory (gitignored)
3. Wire in `dependencies.py` and `router.py`
4. Add `apiUpload` to frontend client

### Phase 4 — Frontend: File Upload UI

1. Create `FileUpload.tsx` component
2. Update `InputBar.tsx` with attach button
3. Wire upload result to chat context

### Phase 5 — Backend: MiniMax Image MCP

1. Add `minimax-image` to `mcp-providers.json`
2. Create `minimax_image_mcp.py` wrapper
3. Register in `provider_registry.py`
4. Add env vars to `settings.py` and `.env.example`
5. Wire in `dependencies.py`
6. Add `understand_image` to `_TOOL_PROMPT_NAMES` in `prompt_composer.py`
7. Create `prompts/tools/minimax_image.txt`

---

## Rollout Strategy

All 3 components are independent and can be shipped separately:

- **Tier 1**: Delete conversations (backend + frontend) — ~2h
- **Tier 2**: File upload → Markitdown (backend + frontend) — ~3h
- **Tier 3**: MiniMax Image MCP (backend only) — ~2h

---

## Success Criteria

- **SC-DEL-01**: A `DELETE /research/{session_id}` call removes the session and all related data (cascade verified)
- **SC-DEL-02**: Frontend HistoryBar shows a delete button per session; clicking with confirmation removes it from the list and the database
- **SC-UPL-01**: `POST /upload/document` with a PDF/DOCX file returns clean Markdown within 60s
- **SC-UPL-02**: Frontend file upload shows progress and previews the converted Markdown
- **SC-IMG-01**: `understand_image(prompt, image_url)` returns an analysis of the image content within 30s
- **SC-IMG-02**: The image MCP provider is registered and discoverable via the MCP provider registry

---

## Constitution Check

- **Status**: PASS
- **Alignment**:
  - **Simplicidad Obligatoria**: Each component is minimal — delete uses existing FK cascades, upload delegates to existing Markitdown, image MCP is a thin wrapper around uvx service
  - **Modularidad Primero**: Three independent concerns in separate files; no mixing of concerns
  - **Cambios Quirurgicos**: Delete is 1 new route file, upload is 1 new route file + 1 component, image is 1 new wrapper + provider registration
  - **Entrega Verificable**: Success criteria per component with measurable outputs
