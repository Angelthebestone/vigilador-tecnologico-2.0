# Feature Specification: Multi-Agent System Enhancements v2

## Problem Statement

The current multi-agent system for technology surveillance has several critical gaps that limit its effectiveness as a continuous intelligence platform:

1. **No analytical capability**: Agents collect data but cannot analyze it programmatically — they cannot run statistical models, generate charts, detect bibliometric patterns, or compute novelty/disruption scores on collected data.

2. **Static execution model**: The planner dispatches all branches in parallel and waits passively. Branches cannot signal new findings mid-execution, and the planner cannot replan based on emerging discoveries.

3. **No cross-session memory**: Each research session starts from zero. Knowledge accumulated in one session is invisible to the next — no cumulative learning, no trend tracking across time, no detection of recurring authors or technologies.

4. **Single-use interaction**: After a research report is generated, the conversation ends. Users cannot ask follow-up questions, drill into specific findings, or continue exploring without launching a completely new investigation.

5. **Limited data sources**: Agents cannot convert PDF documents to analyzable text, cannot interact dynamically with websites (fill forms, navigate paginated results), and cannot capture visual content from web pages.

6. **One-size-fits-all reporting**: Every stakeholder receives the same report format, despite having very different information needs (technical depth vs. business overview vs. compliance risks vs. investment opportunities).

7. **No trend prediction**: The system describes the current state but does not project where technologies are heading.

8. **No source authority tracking**: All sources are treated equally regardless of historical accuracy or relevance.

## Scope Boundaries

### In Scope

1. **Analytical Sandbox**: A controlled execution environment where agents can run Python code for statistical analysis, bibliometric computation (co-citation networks, novelty scores, disruption indices), data visualization (publication trends, collaboration maps, technology maturity curves), and generation of next-query recommendations based on analytical findings.

2. **Document Conversion Service**: A tool that accepts document URIs (PDF, DOCX, PPTX, XLSX, HTML, images) and returns clean Markdown text, enabling agents to extract and process content from papers, patents, regulatory documents, and reports.

3. **Browser Automation Service**: A tool that provides full browser automation — navigate to URLs, capture accessibility snapshots, interact with forms and pagination, take screenshots, and extract structured data from dynamic web pages.

4. **Reactive Execution Planner**: An upgraded branch coordinator that listens to signals emitted by branches during execution, detects emerging patterns mid-research, and can redistribute directives (new search queries, adjusted focus) to active branches before they complete.

5. **Cross-Session Memory**: A persistent knowledge store that accumulates findings, relations, embeddings, and source metadata across all research sessions. New sessions automatically consult prior knowledge to avoid redundant work and detect cross-session patterns.

6. **Continuous Conversation Mode**: After a research session completes and delivers a report, users can continue interacting with the system — asking follow-up questions, exploring specific findings, comparing branches — without launching a new investigation. The system responds from the existing graph and findings, only requesting new searches when explicitly needed.

7. **Trend Forecasting**: A dedicated analytical stage that takes numerical data collected during research (publication counts per year, patent filing rates, investment volumes, citation trajectories) and projects 12-24 month trends, detecting acceleration, stagnation, or inflection points.

8. **Multi-Stakeholder Reporting**: A synthesis stage that generates multiple report variants from the same research findings, each tailored to a specific audience (technical/R&D, business development, legal/compliance, investment).

9. **Source Trust Scoring**: A feedback mechanism that tracks source reliability over time — cross-validated findings increase a source's score, contradicted findings decrease it — feeding into the source routing logic for smarter prioritization in future sessions.

### Out of Scope

- Real-time streaming ingestion of news feeds or RSS
- Integration with external research information systems (WoS, Scopus APIs) beyond web scraping and MCP tools
- Natural language generation for full narrative reports (the existing fuse mechanism handles this)
- Deployment infrastructure (Docker, Kubernetes, CI/CD pipelines)
- User access control or multi-tenant isolation
- Mobile application or native desktop client
- Direct integration with patent databases (USPTO, EPO APIs) — these would be additional MCP providers in future phases
- Automated social media monitoring

## Assumptions

- All new MCP services run locally via STDIO transport (no cloud dependency)
- Node.js 18+ is available on the system for Playwright MCP
- Python 3.11+ is available with pip for Markitdown MCP and the analytical sandbox
- PostgreSQL with pgvector extension is available and configured (already present in the project)
- The existing session state machine, knowledge graph service, and branch coordinator are stable and can be extended without breaking changes
- Environment variables with `VT_` prefix follow the project's existing settings pattern
- New environment variables will be optional unless required for service operation
- Browser automation runs in headless mode by default, headed mode available for debugging
- Document conversion handles file sizes up to 50MB per document
- Cross-session memory retains data indefinitely unless explicitly pruned
- The sandbox execution environment has no network access by default (air-gapped)
- Trend forecasting uses numpy polyfit directly (not sandbox code generation) — polynomial curve fitting with inflection detection via second-derivative analysis
- Source trust scoring uses a simple weighted score (0-100) that combines confirmation ratio, recency, and source diversity

## User Scenarios & Testing

### Primary User Story

As a **technology surveillance analyst**, I want the system to not only find and collect information but also analyze it, learn across sessions, let me continue exploring after a report, and deliver insights tailored to different audiences — so that I can make informed strategic decisions without manually stitching together data from multiple investigations.

### Acceptance Scenarios

1. **Analytical feedback loop**
   **Given** a branch agent has collected bibliometric data (papers, authors, citations),
   **When** the agent invokes the analytical sandbox on this data,
   **Then** the sandbox returns novelty scores, identifies emerging clusters, and generates recommended next queries, which the reactive planner feeds back to active branches.

2. **Document-based research**
   **Given** the user uploads or references a PDF/patent document,
   **When** an agent needs to process its content,
   **Then** the document conversion service transforms it to Markdown, and the agent analyzes the extracted text as if it were a web source.

3. **Dynamic web interaction**
   **Given** a target website requires form submission or pagination to access data,
   **When** a branch agent needs to extract information from that site,
   **Then** the browser automation service navigates, fills forms, handles pagination, and returns structured data without requiring manual intervention.

4. **Reactive replanning**
   **Given** a branch discovers an unexpected high-novelty technology cluster mid-execution,
   **When** it emits a signal to the planner,
   **Then** the planner immediately adjusts the directives of other active branches to investigate this cluster, without waiting for all branches to complete.

5. **Cross-session continuity**
   **Given** the user ran a session on "Blockchain in Supply Chain" last week,
   **When** they start a new session on "Blockchain in Finance" today,
   **Then** the system automatically retrieves related prior findings, notes the recurring authors and technologies, and indicates which areas were already covered.

6. **Post-research conversation**
   **Given** a research session has completed and a report has been delivered,
   **When** the user asks "Show me only the 2024 patents from the AVANCES branch",
   **Then** the system responds by querying the existing graph and findings, without launching a new investigation.

7. **Trend projection**
   **Given** the research collected numerical time-series data (e.g., patent filings per year, 2018-2025),
   **When** the trend forecaster analyzes this data,
   **Then** it produces a 12-24 month projection with confidence intervals and identifies potential inflection points.

8. **Stakeholder report generation**
   **Given** a complete research session with findings across all branches,
   **When** the user requests reports for different audiences,
   **Then** the system generates a technical report (R&D), an executive brief (business), a compliance risk table (legal), and an investment landscape summary (investors) — all from the same data.

9. **Source trust evolution**
   **Given** a source has provided accurate information across multiple sessions,
   **When** the system routes new queries,
   **Then** that source is preferred over lower-scored alternatives. Conversely, a source that consistently provides contradictory data is deprioritized.

### Edge Cases

- **Sandbox execution timeout**: If analytical code takes longer than 120 seconds, it is terminated and a partial result is returned with a warning
- **Cross-session memory conflict**: If a new finding contradicts a stored finding from a prior session, both are preserved with a "contradiction" annotation for user review
- **Conversation drift**: If the user's follow-up question requires information not in the existing graph, the system explicitly asks "This requires a new search. Should I launch one?" rather than silently returning incomplete results
- **Document conversion failure**: If a document cannot be parsed (corrupted file, unsupported format), the system returns a clear error and suggests alternatives
- **Browser automation blocked**: If a website blocks automated access, the system logs the failure, scores the source negatively, and moves to alternative sources
- **Negative trend data**: If insufficient historical data exists (< 3 data points), trend forecasting returns "insufficient data" rather than generating unreliable projections
- **Empty stakeholder audience**: If requested stakeholder type has no relevant findings, the report for that audience indicates "no relevant data found" instead of omitting the section
- **Source score floor**: A source's trust score cannot drop below 10 (always retain some baseline utility) and cannot exceed 100

## Functional Requirements

### Component A: Analytical Sandbox

- **FR-A01**: The sandbox shall accept Python code as input and return stdout, stderr, and execution result within a configurable timeout
- **FR-A02**: The sandbox shall pre-load matplotlib, seaborn, numpy, and pandas in every execution environment
- **FR-A03**: The sandbox shall expose a function to read collected research data (papers, patents, citations) as DataFrames for analysis
- **FR-A04**: The sandbox shall pre-load metaknowledge, PySciSci, scipy, and scikit-learn so agents can perform bibliometric analysis (co-authorship networks, keyword co-occurrence, citation distribution, publication trends) via execute_code without a separate analytics module
- **FR-A05**: Agents shall compute novelty scores and cluster detection via execute_code using pre-loaded scipy/numpy/sklearn — no separate analytics module needed
- **FR-A06**: Agents shall generate next-search queries via execute_code analysis of data gaps — no separate analytics module needed
- **FR-A07**: The sandbox shall include a function to export generated visualizations (PNG, SVG, PDF) for inclusion in reports
- **FR-A08**: The sandbox shall log all executed code and results for auditability

### Component B: Document Conversion Service

- **FR-B01**: The service shall accept URIs of type http:, https:, file:, and data: and return the content as Markdown text
- **FR-B02**: The service shall support conversion of PDF, DOCX, PPTX, XLSX, HTML, CSV, JSON, XML, and common image formats (with OCR)
- **FR-B03**: The service shall preserve document structure including headings, lists, tables, and links in the output Markdown
- **FR-B04**: The service shall return a clear error message for unsupported or corrupted file formats

### Component C: Browser Automation Service

- **FR-C01**: The service shall navigate to any HTTP/HTTPS URL and return the page content as an accessibility snapshot
- **FR-C02**: The service shall support clicking, typing, selecting options, hovering, and form filling on identified page elements
- **FR-C03**: The service shall support multi-tab management (open, close, switch tabs)
- **FR-C04**: The service shall capture screenshots of the current viewport or full page
- **FR-C05**: The service shall extract and return network requests made during page load
- **FR-C06**: The service shall support headless operation by default with optional headed mode
- **FR-C07**: The service shall enforce configurable allowed-host restrictions to prevent navigation to external/unauthorized domains

### Component D: Reactive Execution Planner

- **FR-D01**: The planner shall maintain a signal queue that receives messages from any active branch during execution
- **FR-D02**: The planner shall process signals within 5 seconds of receipt while continuing to monitor branch execution
- **FR-D03**: Upon receiving a "gap detected" signal, the planner shall generate a new search directive and route it to the most relevant branch within 10 seconds
- **FR-D04**: Upon receiving a "high-value finding" signal, the planner shall notify all other branches with relevant context
- **FR-D05**: The planner shall log all replanning decisions with timestamp, triggering signal, and resulting action for audit
- **FR-D06**: The planner shall prevent infinite replanning loops by limiting replan iterations per session to a configurable maximum

### Component E: Cross-Session Memory

- **FR-E01**: All research findings, entity relationships, and embedding vectors from every session shall be persisted in a long-term store indexed by a globally unique session identifier
- **FR-E02**: When a new session is initiated, the system shall automatically query the cross-session memory for related prior research using semantic similarity of the research query
- **FR-E03**: Cross-session results shall include: related prior findings, recurring named entities (authors, organizations, technologies), and coverage gaps identified in prior sessions
- **FR-E04**: Users shall be able to view a timeline of sessions showing how understanding of a topic evolved over time
- **FR-E05**: The cross-session store shall support pruning (delete sessions older than a configurable retention period) without impacting the current session

### Component F: Continuous Conversation Mode

- **FR-F01**: After a research session completes, the system shall maintain the session state (graph, findings, source list) in memory for follow-up interactions
- **FR-F02**: User follow-up queries shall first be answered from the existing session state without invoking any external MCP tools or starting new branches
- **FR-F03**: If a follow-up query cannot be answered from existing state, the system shall ask the user for permission before launching a supplementary search
- **FR-F04**: Supplementary searches shall be scoped to the specific information gap and merged into the existing session state
- **FR-F05**: The continuous conversation mode shall persist until the user explicitly ends the session or a configurable idle timeout expires

### Component G: Trend Forecasting (implemented with direct numpy — no sandbox dependency)

- **FR-G01**: After all branches complete, the system shall scan collected data for numerical time-series (counts per year, per quarter, per month)
- **FR-G02**: For each detected time-series with at least 4 data points, the system shall compute a trend projection covering 12-24 months ahead using numpy directly (polyfit/poly1d) — not via sandbox code generation
- **FR-G03**: The projection shall include: projected value per future period, confidence intervals (upper/lower bounds), and inflection point detection via second-derivative coefficient analysis
- **FR-G04**: If insufficient data exists for meaningful projection (< 3 data points), the system shall return "insufficient data" rather than a low-confidence estimate
- **FR-G05**: Trend forecasting results shall be available as structured data for inclusion in any report variant

### Component H: Multi-Stakeholder Reporting

- **FR-H01**: The system shall generate at least three report variants from the same research findings: technical (R&D), executive brief (business), and risk/compliance (legal)
- **FR-H02**: The technical report shall include: methodology, data sources, quantitative findings, bibliometric analysis, trend projections, and detailed graphs
- **FR-H03**: The executive brief shall include: key takeaways, strategic recommendations, competitive landscape summary, and opportunity/risk highlights
- **FR-H04**: The risk/compliance report shall include: regulatory mentions, patent landscape risks, legal precedents, and compliance recommendations
- **FR-H05**: Each report variant shall be independently downloadable/exportable
- **FR-H06**: Report language, level of detail, and section ordering shall be configurable per stakeholder type

### Component I: Source Trust Scoring

- **FR-I01**: Every unique source (domain, API provider, document) shall have a trust score between 10 and 100, initialized at 50
- **FR-I02**: When a finding from source A is independently confirmed by source B, both sources receive a +5 score increase
- **FR-I03**: When a finding from source A is contradicted by source B, source A receives a -10 score decrease, and source B receives a +3 confirmation increase
- **FR-I04**: Source scores shall persist across sessions via a dedicated `source_trust` table in PostgreSQL
- **FR-I05**: The source router shall prioritize sources with scores above 70 over lower-scored sources for identical or similar queries
- **FR-I06**: Users shall be able to manually adjust any source's score with an annotation explaining the reason

## Key Entities

- **Sandbox Session**: An isolated execution context containing user code, pre-loaded libraries, imported research data, and generated outputs (visualizations, metrics). Has a timeout, status, and execution log.
- **Document Reference**: A pointer to a source document identified by URI, with cached Markdown content, conversion timestamp, detected format, and conversion status.
- **Browser Context**: A browser automation session with its own cookies, local storage, and network state. Maintains a snapshot tree of the current page and a list of active tabs.
- **Signal**: A structured message emitted by a branch during execution containing: signal type (gap_detected, high_value_finding, data_ready, error), payload (structured data or description), source branch, and timestamp.
- **Replan Action**: A decision record from the reactive planner containing: triggering signal, target branch, new directives issued, timestamp, and iteration counter.
- **Global Knowledge Snapshot**: A persistent snapshot of a session's findings, entity graph, embeddings, and source scores, stored with a session identifier, query summary, and timestamp for cross-session retrieval.
- **Session Continuation State**: The active in-memory state after a research session completes, containing the research graph, findings list, source registry, and timestamps, enabling follow-up Q&A without re-execution.
- **Trend Projection**: A computed structure containing the original time-series data, fitted model parameters, projected values with confidence intervals, detected inflection points, and data quality metrics.
- **Report Variant**: A tailored output document with a specific stakeholder audience, containing a subset of the total findings organized and presented according to that audience's needs.
- **Source Trust Record**: A persistent entry for each unique source containing: current score (10-100), confirmation count, contradiction count, last accessed timestamp, and a history of score changes with justifications.

## Success Criteria

- **SC-001**: Agents can run analytical code in the sandbox and receive results within 120 seconds for 95% of execution requests
- **SC-002**: The document conversion service successfully processes at least 90% of submitted documents (PDF, DOCX, PPTX, XLSX) and returns valid Markdown
- **SC-003**: The browser automation service completes multi-step web interactions (navigation + form fill + data extraction) with a 90% success rate across a test set of 20 diverse websites
- **SC-004**: The reactive planner detects and responds to branch signals within 5 seconds of emission in 95% of cases
- **SC-005**: New research sessions automatically surface relevant prior findings from cross-session memory within 10 seconds of session start
- **SC-006**: Users can ask at least 5 follow-up questions after a research session completes without triggering a new investigation, and answers are delivered within 15 seconds
- **SC-007**: Trend forecasting produces 12-month projections for at least 80% of detected time-series datasets that have ≥4 data points
- **SC-008**: Three distinct report variants (technical, executive, risk/compliance) can be generated from the same session's findings, each over 80% unique in content from the others
- **SC-009**: Source trust scores shift detectably (at least ±10 points) over 5 sessions with controlled contradictory/confirming data
- **SC-010**: The complete system (all components) processes a standard research session within 2x the current session time — measured before and after implementation

## Agent Prompt Updates

In addition to the functional components, the following prompt files were created or updated to guide agent behavior:

### New Tool Prompt Files (`prompts/tools/`)
- **`sandbox.txt`**: Instructions for `execute_code`, `list_libraries`, `visualize` — including chaining (collect → analyze → report), import rules, network restriction notes
- **`markitdown.txt`**: Instructions for `convert_to_markdown` — including format support, URI types, fallback to Jina/fetch
- **`playwright.txt`**: Instructions for 7 browser tools (`browser_navigate`, `browser_snapshot`, `browser_screenshot`, `browser_click`, `browser_type`, `browser_network_requests`, `browser_network_request`) — with snapshot-preference rule and blocked-access handling

### Updated Orchestration Prompts
- **`prompts/orchestration/planning.txt`**: Updated `provider_selection_heuristics` with 3 new rules for sandbox, markitdown, and Playwright

### Updated Branch Prompts (`prompts/branches/`)
All 6 branch prompts (`avances.txt`, `comercial.txt`, `competitivo.txt`, `oportunidades.txt`, `pi_normativa.txt`, `riesgo.txt`) include a new `signal_handling` section instructing agents on:
- When to emit `gap_detected` signals (high-value findings, information gaps requiring different expertise)
- When to use the sandbox (statistical analysis, visualization)
- When to use Markitdown (documents) and Playwright (dynamic websites)

### Prompt Registration
`prompt_composer.py` `_TOOL_PROMPT_NAMES` updated with 12 new mappings linking tool names to prompt files.

## Delivery Constraints

- All new components must follow the existing project's modular architecture — each component as a self-contained module with clear interfaces
- New MCP services must be registered through the existing provider registry pattern (`mcp-providers.json`, `provider_registry.py`, `mcp_cache.py`)
- Environment variables for new services must use the `VT_` prefix following the project convention
- The sandbox execution environment must not have network access by default to prevent data exfiltration
- All new components must include error handling that returns user-friendly messages for common failure modes
- New dependencies must be documented in the project's dependency files with version constraints
- Browser automation must respect robots.txt and enforce configurable domain restrictions
- Cross-session memory must support opt-out: users can disable automatic cross-session queries
- Continuous conversation state must be released when the user ends the session or after 30 minutes of inactivity
