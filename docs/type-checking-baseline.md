# Type Checking Baseline

**Date:** 2026-05-18

**Tool:** basedpyright

**Target:** `src/vigilancia_multiagente/`

**Result: 87 errors, 0 warnings, 0 notes**

---

## Error Breakdown by Directory

| Directory | Errors |
|-----------|--------|
| `infra/persistence/postgres_repositories.py` | 40 |
| `application/graph/knowledge_graph_service.py` | 11 |
| `infra/mcp/provider_registry.py` | 9 |
| `api/routes/research_outputs.py` | 6 |
| `application/routing/source_scorer.py` | 5 |
| `application/governance/prompt_composer.py` | 3 |
| `api/routes/research_approve.py` | 2 |
| `application/execution/branch_coordinator.py` | 2 |
| `application/fusion/report_synthesizer.py` | 2 |
| `application/governance/contract_loader.py` | 2 |
| `infra/reranking/semantic_reranker.py` | 2 |
| `application/agents/base.py` | 1 |
| `api/routes/sessions.py` | 1 |
| `application/governance/validators.py` | 1 |
| `infra/mcp/playwright_mcp.py` | 1 |
| `infra/persistence/global_knowledge_repository.py` | 1 |
| **Total** | **87** |

---

## Error Categories

| Category | Count |
|----------|-------|
| `reportArgumentType` | 54 |
| `reportAttributeAccessIssue` | 16 |
| `reportGeneralTypeIssues` | 6 |
| `reportOptionalMemberAccess` | 8 |
| `reportCallIssue` | 1 |
| `reportReturnType` | 1 |
| `reportOptionalMemberAccess` | 1 |

---

## All Errors

### `api/routes/research_approve.py` (2 errors)
1. L110: `reportArgumentType` — `list[dict[Unknown, Unknown]]` not assignable to `dict[str, Any]`
2. L398: `reportArgumentType` — `dict[str, str | int | float | object]` not assignable to `dict[str, str | int | float]`

### `api/routes/research_outputs.py` (6 errors)
1. L234: `reportArgumentType` — `Sequence[BranchResult]` not assignable to `list[Unknown] | None`
2. L274: `reportArgumentType` — `object` not assignable to `Iterable[_T@list]`
3. L275: `reportArgumentType` — `object` not assignable to `Iterable[_T@list]`
4. L328: `reportArgumentType` — `object` not assignable to `Iterable[_T@list]`
5. L329: `reportArgumentType` — `object` not assignable to `Iterable[_T@list]`
6. L431: `reportArgumentType` — `list[VectorRecord]` not assignable to `list[dict[str, object]] | None`

### `api/routes/sessions.py` (1 error)
1. L17: `reportOptionalMemberAccess` — `get_session_timeline` not a known attribute of `None`

### `application/agents/base.py` (1 error)
1. L424: `reportArgumentType` — `object` not assignable to `ConvertibleToFloat`

### `application/execution/branch_coordinator.py` (2 errors)
1. L70: `reportCallIssue` — No overloads for `gather` match the provided arguments
2. L70: `reportArgumentType` — `Task[None]` not assignable to `_FutureLike[AgentRunOutput]`

### `application/fusion/report_synthesizer.py` (2 errors)
1. L76: `reportArgumentType` — `list[Recommendation] | list[object]` not assignable to `list[object]`
2. L118: `reportArgumentType` — `list[dict[str, str]]` not assignable to `list[Recommendation] | None`

### `application/governance/contract_loader.py` (2 errors)
1. L285: `reportArgumentType` — `object` not assignable to `Iterable[_T_co@tuple]`
2. L287: `reportArgumentType` — `object` not assignable to `Iterable[_T_co@tuple]`

### `application/governance/prompt_composer.py` (3 errors)
1. L118: `reportArgumentType` — `dict[str, str]` not assignable to `dict[str, object]`
2. L120: `reportArgumentType` — `dict[str, int | float | str]` not assignable to `dict[str, object]`
3. L124: `reportArgumentType` — `dict[str, str | int | float]` not assignable to `dict[str, object]`

### `application/governance/validators.py` (1 error)
1. L96: `reportArgumentType` — `object` not assignable to `DataclassInstance | type[DataclassInstance]`

### `application/graph/knowledge_graph_service.py` (11 errors)
1. L255: `reportAttributeAccessIssue` — `get` unknown on `object`
2. L287: `reportArgumentType` — `object` not assignable to `ConvertibleToFloat`
3. L426: `reportAttributeAccessIssue` — `lower` unknown on `object`
4. L455: `reportAttributeAccessIssue` — `append` unknown on `object`
5. L465: `reportAttributeAccessIssue` — `append` unknown on `object`
6. L482: `reportAttributeAccessIssue` — `append` unknown on `object`
7. L494: `reportAttributeAccessIssue` — `get` unknown on `object`
8. L496: `reportAttributeAccessIssue` — `get` unknown on `object`
9. L497: `reportAttributeAccessIssue` — `append` unknown on `object`
10. L526: `reportArgumentType` — `object` not assignable to `dict[str, object]`

### `application/routing/source_scorer.py` (5 errors)
1. L15: `reportOptionalMemberAccess` — `update_score` not a known attribute of `None`
2. L18: `reportOptionalMemberAccess` — `update_score` not a known attribute of `None`
3. L25: `reportOptionalMemberAccess` — `update_score` not a known attribute of `None`
4. L28: `reportOptionalMemberAccess` — `update_score` not a known attribute of `None`
5. L35: `reportOptionalMemberAccess` — `get_top_sources` not a known attribute of `None`

### `infra/mcp/playwright_mcp.py` (1 error)
1. L61: `reportReturnType` — `CoroutineType` not assignable to `dict[str, Any]`

### `infra/mcp/provider_registry.py` (9 errors)
1. L329: `reportArgumentType` — `object` not assignable to `Iterable[_T@list]`
2. L331 (×2): `reportArgumentType` — `object` not assignable to `ConvertibleToInt`
3. L333: `reportAttributeAccessIssue` — `get` unknown on `object`
4. L334: `reportAttributeAccessIssue` — `get` unknown on `object`
5. L336: `reportGeneralTypeIssues` — `object` is not iterable
6. L337: `reportGeneralTypeIssues` — `object` is not iterable
7. L338: `reportAttributeAccessIssue` — `items` unknown on `object`
8. L345: `reportAttributeAccessIssue` — `get_secret_value` unknown on `object`

### `infra/persistence/global_knowledge_repository.py` (1 error)
1. L125: `reportAttributeAccessIssue` — `rowcount` unknown on `Result[Any]`

### `infra/persistence/postgres_repositories.py` (40 errors)
1. L58: `reportArgumentType` — `RowMapping` not assignable to `dict[str, object]`
2. L67: `reportArgumentType` — `RowMapping` not assignable to `dict[str, object]`
3. L96: `reportArgumentType` — `RowMapping` not assignable to `dict[str, object]`
4. L144: `reportArgumentType` — `RowMapping` not assignable to `dict[str, object]`
5. L184: `reportArgumentType` — `RowMapping` not assignable to `dict[str, object]`
6. L384: `reportArgumentType` — `dict[str, object] | None` not assignable to `dict[str, str] | None`
7. L389: `reportArgumentType` — `object | None` not assignable to `str | None`
8. L390: `reportArgumentType` — `object | None` not assignable to `str | None`
9. L411 (×2): `reportArgumentType` — `object` not assignable to `ConvertibleToInt`
10. L412: `reportArgumentType` — `object` not assignable to `dict[str, object]`
11. L413: `reportArgumentType` — `dict[str, object] | dict[str, str | int | float]` not assignable to `dict[str, str | int | float]`
12. L441: `reportArgumentType` — `object` not assignable to `dict[str, object]`
13. L442: `reportArgumentType` — `object` not assignable to `dict[str, object]`
14. L466: `reportArgumentType` — `object` not assignable to `Iterable[_T@list]`
15. L467: `reportArgumentType` — `object` not assignable to `Iterable[_T@list]`
16. L468: `reportArgumentType` — `object | None` not assignable to `str | None`
17. L469 (×2): `reportArgumentType` — `object` not assignable to `ConvertibleToInt`
18. L490: `reportArgumentType` — `object` not assignable to `ConvertibleToFloat`
19. L491: `reportGeneralTypeIssues` — `object` is not iterable
20. L492: `reportGeneralTypeIssues` — `object` is not iterable
21. L517: `reportArgumentType` — `object | None` not assignable to `str | None`
22. L518: `reportArgumentType` — `object | None` not assignable to `str | None`
23. L591: `reportArgumentType` — `object` not assignable to `ConvertibleToFloat`
24. L620: `reportArgumentType` — `datetime | object | None` not assignable to `datetime`
25. L623: `reportArgumentType` — `object` not assignable to `str`
26. L624: `reportArgumentType` — `object` not assignable to `str`
27. L625: `reportArgumentType` — `object` not assignable to `str`
28. L626: `reportArgumentType` — `object` not assignable to `str`
29. L627: `reportArgumentType` — `object` not assignable to `str`
30. L628: `reportArgumentType` — `object` not assignable to `str`
31. L635: `reportGeneralTypeIssues` — `object` is not iterable
32. L637: `reportGeneralTypeIssues` — `object` is not iterable
33. L638 (×2): `reportArgumentType` — `object` not assignable to `ConvertibleToInt`
34. L639 (×2): `reportArgumentType` — `object` not assignable to `ConvertibleToInt`
35. L640: `reportArgumentType` — `object` not assignable to `ConvertibleToFloat`

### `infra/reranking/semantic_reranker.py` (2 errors)
1. L102: `reportOptionalMemberAccess` — `embed_document` not a known attribute of `None`
2. L103: `reportOptionalMemberAccess` — `embed_documents` not a known attribute of `None`

---

## Known Issues / Notes

- The majority of errors (40/87) are concentrated in `infra/persistence/postgres_repositories.py`, which uses JSON columns (`JSONType`) returned as untyped `object` — a common pattern with SQLAlchemy + JSON columns. These are mostly false positives from SQLAlchemy's dynamic return types.
- `RowMapping` not assignable to `dict[str, object]` (5 errors) is a basedpyright strictness issue — SQLAlchemy rows structurally satisfy the dict interface but are not nominally a `dict`.
- `reportOptionalMemberAccess` errors in `source_scorer.py` (5 errors) and `semantic_reranker.py` (2 errors) indicate missing `None` checks on optional dependencies (source_trust_repository, embedding_client).
- `reportAttributeAccessIssue` errors in `knowledge_graph_service.py` (8 errors) and `provider_registry.py` (4 errors) are caused by values typed as `object` from dynamic JSON/batch results.
- The `asyncio.gather` error in `branch_coordinator.py` is a known issue with the typed `Task[None]` vs `_FutureLike[AgentRunOutput]` — the gather call works at runtime but the typing is imprecise.
- All `reportArgumentType` errors with `object` not assignable to `ConvertibleToFloat`/`ConvertibleToInt`/`Iterable` are downstream effects of the JSON column typing problem.
