# SSE Event Contract

## Stream Endpoint

- `GET /api/v2/research/{session_id}/stream`
- Content-Type: `text/event-stream`

## Standard Envelope

```text
event: <EventName>
data: {"session_id":"...","timestamp":"...","payload":{...}}
```

## Event Types

1. `SessionStarted`
   - Payload: `status`, `user_query`
2. `ClarificationRequested`
   - Payload: `questions[]`
3. `PlanGenerated`
   - Payload: `plan_id`, `branches[]`, `requires_approval`
4. `PlanApproved`
   - Payload: `approved_by`, `approved_at`
5. `BranchStarted`
   - Payload: `branch_type`
6. `BranchProgress`
   - Payload: `branch_type`, `progress_percent`, `current_step`
7. `BranchCompleted`
   - Payload: `branch_type`, `findings_count`, `sources_count`, `coverage_score`
8. `BranchFailed`
   - Payload: `branch_type`, `error_code`, `error_message`
9. `AllBranchesCompleted`
   - Payload: `completed_branches`, `failed_branches`
10. `FusionStarted`
    - Payload: `total_branch_results`
11. `FusionProgress`
    - Payload: `progress_percent`
12. `ReportGenerated`
    - Payload: `report_id`, `confidence_score`
13. `GraphBuildingStarted`
    - Payload: `node_estimate`, `edge_estimate`
14. `GraphAnalyticsComputed`
    - Payload: `centrality_ready`, `clustering_ready`, `pathfinder_ready`
15. `Error`
    - Payload: `scope`, `error_code`, `error_message`, `recoverable`
16. `TemporalWindowResolved`
    - Payload: `window_start`, `window_end`, `basis`
17. `IterationStarted`
    - Payload: `branch_type`, `iteration_index`, `query`, `query_type`
18. `IterationCompleted`
    - Payload: `branch_type`, `iteration_index`, `needs_follow_up`, `stop_reason`
19. `SemanticRelationsUpdated`
    - Payload: `branch_type`, `new_relations_count`, `relation_types`
20. `PromptContractApplied`
    - Payload: `branch_type`, `contract_version`, `system_base_version`, `prompt_composition_id`, `overlay_version`
21. `EvaluationComputed`
    - Payload: `branch_type`, `coverage_kpi`, `precision_kpi`, `latency_ms_kpi`, `cost_kpi`
22. `SystemBaseLoaded`
    - Payload: `version`, `sections_count`, `enabled`

## Delivery Rules

- Events are ordered per session.
- `BranchProgress` may arrive interleaved across branches.
- `Error` does not imply session termination unless followed by terminal status event.
- `IterationCompleted` con `stop_reason=depth_limit` MUST finalizar el loop de esa rama.
- Terminal event is one of:
  - `ReportGenerated`
  - `Error` with unrecoverable session scope
