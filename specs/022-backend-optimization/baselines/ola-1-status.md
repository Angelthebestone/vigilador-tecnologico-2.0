# Ola 1 Status: Infra base aditiva

**Fecha**: 2026-06-02
**Estado**: ✅ COMPLETADA

## Resumen de cambios

### Nuevos archivos creados
1. `src/vigilancia_multiagente/enterprise/tooling/builtin/_base/__init__.py` (27 LOC)
2. `src/vigilancia_multiagente/enterprise/tooling/builtin/_base/retry_policy.py` (75 LOC)
3. `src/vigilancia_multiagente/enterprise/tooling/builtin/_base/http_provider.py` (113 LOC)
4. `src/vigilancia_multiagente/infra/embeddings/embedding_cache.py` (104 LOC)
5. `tests/enterprise/tooling/test_base_http_provider.py` (7 tests)
6. `tests/infra/embeddings/test_embedding_cache.py` (7 tests)

### Cambios en archivos existentes
- Ninguno. Ola 1 es 100% aditiva.

### Correcciones pre-existentes (desbloqueo)
- Se corrigieron 4 mocks de tests pre-existentes que fallaban por cambios de ruta en `prompt_messages.py`:
  - `tests/application/evaluation/ws_b/test_hybrid_search.py`
  - `tests/application/evaluation/ws_c/test_assumption_detector.py`
  - `tests/application/evaluation/ws_c/test_counterfactual_synthesizer.py`
  - `tests/application/evaluation/ws_e/test_falsification_prober.py`
- Se corrigió `if not values:` a `if len(values) == 0:` en `src/vigilancia_multiagente/infra/search/bm25_plus_embedding.py` para soportar arrays de numpy retornados por `rank_bm25`.

## Verificaciones

- **Gate sagrado**: ✅ 119 passed (0 failed)
- **LOC limit**: ✅ Todos los archivos nuevos están por debajo del límite de 400 LOC.
- **Layer imports**: ✅ `python scripts/check-layer-imports.py` retorna 0 violaciones.
- **Tests específicos**: ✅ 14 tests nuevos pasando (7 BaseHTTPProvider + 7 EmbeddingCache).

## Próximos pasos
Proceder con **Ola 2: N+1 fix tools** (T021-T030), que depende de la existencia de `EmbeddingCache`.
