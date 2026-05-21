# Research: Multi-Agent System Enhancements v2 — Design Decisions

## Sandbox Execution Protocol

### Architecture
- **Transport**: Python STDIO MCP server (following existing pattern: google_scholar, fetch)
- **Process model**: Each `execute_code` call spawns a subprocess via `subprocess.Popen` with:
  - `timeout`: Configurable via `VT_SANDBOX_TIMEOUT` (default 120s)
  - `cwd`: Temporary directory unique per sandbox session
  - `env`: Clean environment (no network access — `no_proxy=*`, no API keys inherited)
  - `stdout/stderr`: Captured and returned as structured response

### Security
- Network access blocked by default (air-gapped sandbox)
- No filesystem access outside temp directory
- Execution output size limited by `VT_SANDBOX_MAX_OUTPUT_SIZE` (default 1MB)
- All executed code logged with timestamp for audit trail

### Pre-loaded Libraries
- `matplotlib`, `seaborn` — visualization
- `numpy`, `pandas` — data manipulation
- `scipy` — scientific computing (used by trend forecaster)
- `metaknowledge` — WoS/Scopus/PubMed bibliometric parsing
- `PySciSci` — science-of-science metrics
- `scienceplots` — publication-quality plot styles

### Tools Exposed
1. `execute_code(code, timeout)` — run arbitrary Python, return stdout/stderr/result
2. `list_libraries()` — return dict of available packages with versions
3. `visualize(data, plot_type, format)` — generate charts returning base64/file path
4. Bibliometric helpers in `analytics.py` (called via execute_code wrapper)

### Audit Logging
- Format: JSONL (`sandbox_audit.log`)
- Each entry: `{timestamp, session_id, code_hash, code_preview, duration_ms, success, output_size, error?}`
- Log location: `{FEATURE_DIR}/logs/sandbox/`

---

## BranchCoordinator Signal Infrastructure Review

### Existing State
- `_signal_queue`: `asyncio.Queue` instance in `BranchCoordinator`
- `queue_signal(branch_name, signal_type, payload)`: Public method to emit signals
- Signal types: `gap_detected`, `high_value_finding`, `data_ready`, `error`
- `_process_cross_signals()`: Called **after** `asyncio.gather()` completes — signals are processed post-hoc, not during execution

### Integration Points for Reactive Planner
1. **Signal consumer loop**: Replace passive post-gather processing with `asyncio.wait(FIRST_COMPLETED)` that watches both branch futures AND the signal queue
2. **Signal dispatch**: `handle_gap_detected` → `_route_new_directive` to relevant branch; `handle_high_value_finding` → notify other branches; `handle_data_ready` → store for fuse
3. **Replan limiter**: Configurable max replans per session (default 5) prevents infinite loops
4. **Audit logging**: Every replan decision logged with timestamp, triggering signal, target branch, and directive

### No Breaking Changes
- Existing `execute()` method signature preserved
- Existing signal emitting (`queue_signal`) unchanged
- `_signal_queue` persists across sessions naturally (new queue per `execute()` call)

---

## Entity Architecture Decisions

| Entity | File | Persistence | Key Index |
|--------|------|-------------|-----------|
| GlobalKnowledgeSnapshot | `domain/global_knowledge.py` | PostgreSQL + pgvector | session_id (UUID), embedding vector |
| SourceTrustRecord | `domain/source_trust.py` | PostgreSQL | source_id (VARCHAR) |
| SessionContinuationState | `domain/conversation_state.py` | In-memory (Redis optional) | session_id |
| TrendProjection | `domain/trend_projection.py` | Ephemeral (generated per session) | N/A |
| ReportVariant | `domain/report_variant.py` | Ephemeral + optional file export | type (technical\|executive\|risk\|investor) |
| Signal | `domain/signal.py` | Ephemeral (in-memory queue) | N/A |
| SandboxSession | `domain/sandbox.py` | Ephemeral (per `execute_code` call) | session_id |
| DocumentReference | `domain/document.py` | Ephemeral (result cache) | URI hash |
| BrowserContext | `domain/browser.py` | Ephemeral (per tab) | context_id |
