# Ola 2 Status: N+1 fix tools

**Fecha**: 2026-06-02
**Estado**: ✅ COMPLETADA

## Resumen de cambios

### Archivos modificados
1. `src/vigilancia_multiagente/infra/persistence/tool_health_repository.py` (+14 LOC): Añadido `get_statuses_batch` para consulta SQL en lote.
2. `src/vigilancia_multiagente/enterprise/tooling/tool_registry.py` (+25 LOC): Pre-cómputo de embeddings en `register()`, uso de cache en `discover()`, batch SQL para statuses.
3. `src/vigilancia_multiagente/api/enterprise_composition.py` (+10 LOC): Inyección y flush de `EmbeddingCache` en la composición de `ToolRegistry`.

### Nuevos archivos creados
1. `tests/infra/persistence/test_tool_health_batch.py` (2 tests)
2. `tests/enterprise/tooling/test_discover_precomputed_embeddings.py` (2 tests)
3. `tests/enterprise/tooling/benchmark_discover_latency.py` (1 test)

## Verificaciones

- **Gate sagrado**: ✅ 119 passed (0 failed)
- **SC-002 (Latencia discover)**: ✅ p95 < 200ms verificado en benchmark con mocks.
- **Tests específicos**: ✅ 5 tests nuevos pasando.

## Próximos pasos
Proceder con **Ola 3: Skills boot optimization** (T031-T060), que depende de la existencia de `EmbeddingCache` y la estructura de adapters.
