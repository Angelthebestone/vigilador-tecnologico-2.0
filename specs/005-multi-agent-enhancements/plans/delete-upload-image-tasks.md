# Tasks: Delete Chats, File Upload & Image Understanding

**Input**: `specs/005-multi-agent-enhancements/plans/delete-upload-image-plan.md`
**Feature**: Three independent features: delete research sessions, file upload to Markitdown conversion, and MiniMax Image MCP integration.

---

## Phase 1: Backend — Delete Conversations

- [X] T001 Create `DELETE /research/{session_id}` endpoint at `src/vigilancia_multiagente/api/routes/research_delete.py`
- [X] T002 Register delete router in `src/vigilancia_multiagente/api/router.py`
- [X] T003 Add `apiDel` method to `frontend/src/api/client.ts`
- [X] T004 Add `deleteSession` function to `frontend/src/api/endpoints.ts`

---

## Phase 2: Frontend — Delete UI

- [X] T005 Create `ConfirmDialog` reusable component at `frontend/src/components/ConfirmDialog.tsx`
- [X] T006 Update `HistoryBar.tsx` — add `onDelete` prop, delete button (trash icon), confirmation dialog
- [X] T007 Update `historyStore.ts` — add `removeSession` async action
- [X] T008 Wire `onDelete` through parent component in `frontend/src/App.tsx` or `MainLayout.tsx`

---

## Phase 3: Backend — File Upload to Markitdown

- [X] T009 Create `POST /upload/document` endpoint at `src/vigilancia_multiagente/api/routes/upload.py` (multipart file, save to `uploads/`, call MarkitdownProvider, return markdown)
- [X] T010 Create `uploads/` directory in project root, add to `.gitignore`
- [X] T011 Register upload router in `src/vigilancia_multiagente/api/router.py`
- [X] T012 Wire upload service in `src/vigilancia_multiagente/api/dependencies.py`
- [X] T013 Add `apiUpload` method to `frontend/src/api/client.ts`
- [X] T014 Add `uploadDocument` function to `frontend/src/api/endpoints.ts`

---

## Phase 4: Frontend — File Upload UI

- [X] T015 Create `FileUpload` component at `frontend/src/components/FileUpload.tsx` (drag-and-drop zone, file type filter, progress indicator)
- [X] T016 Update `InputBar.tsx` — add attach/upload button that opens FileUpload
- [X] T017 Display converted Markdown preview after upload (expandable)

---

## Phase 5: Backend — MiniMax Image MCP

- [X] T018 Add `minimax-image` provider entry to `src/vigilancia_multiagente/infra/mcp/mcp-providers.json` (STDIO, `uvx minimax-coding-plan-mcp -y`, env vars `MINIMAX_API_KEY` and `MINIMAX_API_HOST`)
- [X] T019 Create `MinimaxImageProvider` wrapper at `src/vigilancia_multiagente/infra/mcp/minimax_image_mcp.py` with `understand_image(prompt, image_url)` tool
- [X] T020 Register minimax-image in `ensure_standard_providers()` at `src/vigilancia_multiagente/infra/mcp/provider_registry.py`
- [X] T021 Add `VT_MINIMAX_IMAGE_API_KEY` and `VT_MINIMAX_API_HOST` env vars to `src/vigilancia_multiagente/config/settings.py`
- [X] T022 Document new env vars in `.env.example`
- [X] T023 Wire minimax-image provider in `src/vigilancia_multiagente/api/dependencies.py`
- [X] T024 Add `understand_image` to `_TOOL_PROMPT_NAMES` in `src/vigilancia_multiagente/application/governance/prompt_composer.py`
- [X] T025 Create tool prompt at `src/vigilancia_multiagente/prompts/tools/minimax_image.txt`

---

## Phase 6: Polish & Cleanup

- [X] T026 Run ruff check on all modified/new Python files
- [X] T027 Verify `uploads/` is in `.gitignore`
- [X] T028 Run frontend type check (`tsc --noEmit`)
- [X] T029 Write backend tests for delete endpoint in `tests/test_research_delete.py`
- [X] T030 Write backend tests for upload endpoint in `tests/test_upload.py`

---

## Dependencies

- **T001–T004** (Phase 1) independent from T005–T008 (Phase 2) — can run in parallel
- **T001** must precede T006 (backend must exist before frontend can call it)
- **T009–T014** (Phase 3) independent from T015–T017 (Phase 4) — can run in parallel
- **T009** must precede T015 (endpoint must exist before upload component can use it)
- **T018–T025** (Phase 5) independent from all other phases — can run in parallel
- T026–T030 (Phase 6) after all other phases

## Parallel Execution

```
[Agent 1]: T001→T002→T003→T004 (Delete backend) then T005→T006→T007→T008 (Delete frontend)
[Agent 2]: T009→T010→T011→T012→T013→T014 (Upload backend) then T015→T016→T017 (Upload frontend)
[Agent 3]: T018→T019→T020→T021→T022→T023→T024→T025 (MiniMax Image MCP)
  → Agents 1, 2, 3 run in parallel (zero conflicts)
Then: [Agent 4]: T026→T027→T028→T029→T030 (Polish)
```
