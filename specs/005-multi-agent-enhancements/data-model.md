# Data Model: Multi-Agent System Enhancements v2

## GlobalKnowledgeSnapshot

Persistent cross-session memory record.

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | UUID (PK) | Globally unique session identifier |
| `query_summary` | TEXT | Natural language summary of the research query |
| `findings_graph` | JSONB | Serialized NetworkX graph nodes + edges |
| `embeddings` | vector(768) | pgvector embedding of query_summary |
| `entities` | JSONB | List of recurring entities (authors, orgs, technologies) |
| `source_scores` | JSONB | Snapshot of SourceTrustRecord scores at session end |
| `created_at` | TIMESTAMPTZ | When the snapshot was saved |
| `expires_at` | TIMESTAMPTZ | NULL = never expires (configurable TTL) |

## SourceTrustRecord

Per-source reliability score.

| Field | Type | Description |
|-------|------|-------------|
| `source_id` | VARCHAR(255) (PK) | Unique source identifier (domain, API name, document URI) |
| `source_type` | VARCHAR(50) | `domain`, `api`, `document` |
| `current_score` | INTEGER | 10–100, initialized at 50 |
| `confirmation_count` | INTEGER | Times this source's findings were confirmed by others |
| `contradiction_count` | INTEGER | Times this source's findings were contradicted |
| `last_accessed` | TIMESTAMPTZ | Last query timestamp |
| `score_history` | JSONB | `[{delta, reason, timestamp}]` — full audit trail |
| `created_at` | TIMESTAMPTZ | First seen |
| `updated_at` | TIMESTAMPTZ | Last score change |

## SessionContinuationState

In-memory state for post-research Q&A.

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | UUID | Links to the research session |
| `research_graph` | NetworkX Graph | In-memory knowledge graph |
| `findings_list` | List[Finding] | All findings from all branches |
| `source_registry` | Dict[str, SourceTrustRecord] | Source scores snapshot |
| `created_at` | datetime | When conversation mode started |
| `last_active_at` | datetime | Last user interaction (for idle timeout) |
| `supplementary_count` | int | Number of supplementary searches performed |

## TrendProjection

Computed trend forecast from numerical time-series data.

| Field | Type | Description |
|-------|------|-------------|
| `source_data` | Dict[str, List] | Original series: `{year: [counts], "metric": "patents"}` |
| `projected_values` | List[Dict] | `[{period: "2026-Q1", value: 142, lower_bound: 130, upper_bound: 155}]` |
| `confidence_intervals` | Dict[str, float] | `{95: 1.96, 80: 1.28}` — z-scores used |
| `inflection_points` | List[Dict] | `[{period: "2025-Q3", type: "acceleration"}]` |
| `model_type` | str | `polynomial`, `exponential`, `logistic` |
| `data_quality` | str | `sufficient` (≥4 pts), `low` (3 pts), `insufficient` (<3 pts) |
| `created_at` | datetime | When projection was generated |

## ReportVariant

A stakeholder-specific report generated from research findings.

| Field | Type | Description |
|-------|------|-------------|
| `type` | Enum | `technical`, `executive`, `risk`, `investor` |
| `title` | str | Report title |
| `sections` | List[Dict] | `[{heading, content, source_findings}]` |
| `findings_ids` | List[UUID] | Which findings were used |
| `generated_at` | datetime | Generation timestamp |
| `export_formats` | List[str] | Available export formats (`md`, `pdf`, `html`) |

## Signal

Message emitted by a branch during execution.

| Field | Type | Description |
|-------|------|-------------|
| `type` | Enum | `gap_detected`, `high_value_finding`, `data_ready`, `error` |
| `source_branch` | str | Branch name (AVANCES, COMERCIAL, etc.) |
| `payload` | Dict | Structured data: query suggestion, finding data, error info |
| `timestamp` | datetime | When signal was emitted |
| `iteration` | int | Replan iteration counter |

## ReplanAction

Decision record from the reactive planner.

| Field | Type | Description |
|-------|------|-------------|
| `trigger_signal` | Signal | The signal that caused replanning |
| `target_branch` | str | Branch receiving the new directive |
| `directive` | Dict | `{action: "search", query: "...", focus: "..."}` |
| `timestamp` | datetime | When replan occurred |
| `iteration` | int | Replan iteration number (max enforced) |

## SandboxSession

Execution context for one `execute_code` call.

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | UUID | Unique execution ID |
| `code_preview` | str | First 200 chars of submitted code |
| `status` | Enum | `running`, `completed`, `timed_out`, `error` |
| `started_at` | datetime | Execution start |
| `duration_ms` | int | Wall-clock execution time |
| `output_size_bytes` | int | Size of captured output |
| `error_message` | str | NULL if successful |

## DocumentReference

Cached document conversion result.

| Field | Type | Description |
|-------|------|-------------|
| `uri_hash` | str (PK) | SHA256 of document URI |
| `uri` | str | Original URI (http:, file:, data:) |
| `format` | str | Detected source format (pdf, docx, etc.) |
| `markdown_content` | TEXT | Converted Markdown output |
| `conversion_time_ms` | int | How long conversion took |
| `converted_at` | datetime | When conversion happened |
| `status` | Enum | `success`, `error`, `unsupported_format` |

## BrowserContext

Browser automation session state.

| Field | Type | Description |
|-------|------|-------------|
| `context_id` | UUID | Unique context per Playwright session |
| `current_url` | str | Currently loaded URL |
| `active_tab_index` | int | Which tab is active |
| `tab_count` | int | Total open tabs |
| `cookies` | List[Dict] | Session cookies (ephemeral) |
| `viewport` | Dict | `{width, height}` |
| `started_at` | datetime | When context was created |
