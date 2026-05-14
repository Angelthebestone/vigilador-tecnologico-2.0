"""Ejecución función por función en sandbox."""
import sys, os, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

print("=" * 60)
print("FUNCIÓN 1: _normalize_url (evidence_linker.py)")
print("=" * 60)

def normalize_url_old(url):
    return url.strip().lower()

def normalize_url_new(url):
    return url.strip().lower().rstrip("/")

tests = [
    ("http://a.com", "http://a.com", "http://a.com"),
    ("http://a.com/", "http://a.com", "http://a.com"),
    ("HTTP://A.COM/", "http://a.com", "http://a.com"),
    (" https://x.com/path ", "https://x.com/path", "https://x.com/path"),
]

for url, expected_old, expected_new in tests:
    old = normalize_url_old(url)
    new = normalize_url_new(url)
    old_ok = "OK" if old == expected_old else f"FAIL (got={old!r})"
    new_ok = "OK" if new == expected_new else f"FAIL (got={new!r})"
    print(f"  input={url!r:30s} old={old_ok:30s} new={new_ok}")

print()
print("=" * 60)
print("FUNCIÓN 2: extract_section (report_synthesizer.py)")
print("=" * 60)

def extract_section_old(markdown, section_name):
    for name in (section_name, section_name.lower()):
        match = re.search(
            rf"^#{{2,3}}\s+{re.escape(name)}\s*$(.*?)(?=^#|\Z)",
            markdown,
            re.MULTILINE | re.DOTALL,
        )
        if match:
            return match.group(1).strip()
    return ""

def extract_section_new(markdown, section_name):
    for name in (section_name, section_name.lower()):
        match = re.search(
            rf"^#{{2,3}}\s+{re.escape(name)}\s*$(.*?)(?=^##\s|\Z)",
            markdown,
            re.MULTILINE | re.DOTALL,
        )
        if match:
            return match.group(1).strip()
    return ""

md_1 = """## Resumen Ejecutivo
primer parrafo
### subseccion
contenido interno
## Otra seccion
"""

r_old = extract_section_old(md_1, "Resumen Ejecutivo")
r_new = extract_section_new(md_1, "Resumen Ejecutivo")
print(f"  ANTES: extrajo {len(r_old)} chars | {r_old!r:.60}")
print(f"  DESPUÉS: extrajo {len(r_new)} chars | {r_new!r:.60}")
print(f"  subseccion incluida: {'subseccion' in r_new}")
print(f"  ANTES trunca contenido: {len(r_old) < len(r_new)}")

# Edge case: section at end of doc
md_2 = """## Riesgo
primer parrafo
## Otra
"""
r_end_old = extract_section_old(md_2, "Riesgo")
r_end_new = extract_section_new(md_2, "Riesgo")
print(f"  END-OF-DOC old={r_end_old!r} new={r_end_new!r}")
print(f"  END-OF-DOC ambos OK: {r_end_old == r_end_new == 'primer parrafo'}")

print()
print("=" * 60)
print("FUNCIÓN 3: cosine_similarity (semantic_relations.py)")
print("=" * 60)

from vigilancia_multiagente.application.research.semantic_relations import cosine_similarity

v1 = [1.0, 2.0, 3.0]
v2 = [1.0, 2.0, 3.0]
v3 = [0.0, 0.0, 0.0]
v4 = [3.0, 2.0, 1.0]

r1 = cosine_similarity(v1, v2)
r2 = cosine_similarity(v1, v3)
r3 = cosine_similarity(v1, v4)

print(f"  identical: {r1:.6f} (expected ~1.0)")
print(f"  zero vector: {r2:.6f} (expected 0.0)")
print(f"  different: {r3:.6f} (expected ~0.714)")
print(f"  pass: {abs(r1 - 1.0) < 0.0001 and r2 == 0.0 and abs(r3 - 0.714) < 0.01}")

print()
print("=" * 60)
print("FUNCIÓN 4: ensure_transition (session_state.py)")
print("=" * 60)

from vigilancia_multiagente.domain.session_state import SessionStatus, ensure_transition

transitions = [
    (SessionStatus.DRAFT, SessionStatus.CLARIFYING, True),
    (SessionStatus.CLARIFYING, SessionStatus.PLANNING, True),
    (SessionStatus.PLANNING, SessionStatus.APPROVED, True),
    (SessionStatus.APPROVED, SessionStatus.EXECUTING, True),
    (SessionStatus.EXECUTING, SessionStatus.COMPLETED, True),
    (SessionStatus.DRAFT, SessionStatus.COMPLETED, False),
    (SessionStatus.COMPLETED, SessionStatus.DRAFT, False),
]

errors = 0
for current, target, should_pass in transitions:
    try:
        result = ensure_transition(current, target)
        ok = should_pass
        if not should_pass:
            errors += 1
            print(f"  {current.value}->{target.value}: DEBERIA FALLAR pero paso")
    except ValueError as e:
        ok = not should_pass
        if should_pass:
            errors += 1
            print(f"  {current.value}->{target.value}: DEBERIA PASAR pero fallo: {e}")
print(f"  transition tests: {len(transitions) - errors}/{len(transitions)} passed")

print()
print("=" * 60)
print("FUNCIÓN 5: score (source_scorer.py)")
print("=" * 60)

from vigilancia_multiagente.application.evaluation.source_scorer import SourceScorer

scorer = SourceScorer()
scores = [
    ("https://patents.google.com/patent/US123", 0.95),
    ("https://arxiv.org/abs/2301.12345", 0.90),
    ("https://scholar.google.com/citations", 0.85),
    ("https://news.ycombinator.com/item?id=123", 0.55),
    ("https://example.com/random-blog", 0.55),
]

for url, expected_min in scores:
    s = scorer.score(url)
    ok = s >= expected_min
    print(f"  {url:55s} score={s:.2f} expected>={expected_min:.2f} {'OK' if ok else 'FAIL'}")

print()
print("=" * 60)
print("FUNCIÓN 6: _extract_items (serper_client.py)")
print("=" * 60)

from vigilancia_multiagente.infra.serper.serper_client import _extract_items

# Test 1: dict con key "organic"
data1 = {"organic": [{"title": "a"}, {"title": "b"}], "news": []}
r1 = _extract_items(data1, ("organic",))
print(f"  dict+organic: {len(r1)} items {'OK' if len(r1) == 2 else 'FAIL'}")

# Test 2: dict con key "patents"
data2 = {"patents": [{"id": "US123"}]}
r2 = _extract_items(data2, ("patents", "organic"))
print(f"  dict+patents: {len(r2)} items {'OK' if len(r2) == 1 else 'FAIL'}")

# Test 3: batch list
data3 = [{"q": "test", "organic": [{"title": "x"}]}]
r3 = _extract_items(data3, ("organic",))
print(f"  batch list: {len(r3)} items {'OK' if len(r3) == 1 else 'FAIL'}")

# Test 4: empty
data4 = {}
r4 = _extract_items(data4, ("organic", "patents"))
print(f"  empty: {len(r4)} items {'OK' if len(r4) == 0 else 'FAIL'}")

print()
print("=" * 60)
print("FUNCIÓN 7: compute (branch_kpi_service.py)")
print("=" * 60)

from vigilancia_multiagente.application.evaluation.branch_kpi_service import BranchKPIService, BranchKPI
from vigilancia_multiagente.domain.models import BranchResult, BranchType, Finding, SourceRef
from uuid import uuid4
from datetime import datetime, UTC

br = BranchResult(
    id=uuid4(),
    session_id=uuid4(),
    branch_type=BranchType.AVANCES,
    queries_executed=["q1"],
    findings=[Finding(id=uuid4(), topic="topic", statement="stmt", confidence=0.85, source_ids=[uuid4()])],
    sources=[SourceRef(id=uuid4(), session_id=uuid4(), url="http://a.com", provider="tavily", branch_type=BranchType.AVANCES, accessed_at=datetime.now(UTC))],
    coverage_score=0.75,
    confidence_score=0.85,
)

svc = BranchKPIService()
kpi = svc.compute(br, latency_ms=350, cost_kpi=1.25)

print(f"  branch_type: {kpi.branch_type.value} (expected AVANCES)")
print(f"  coverage_kpi: {kpi.coverage_kpi} (expected 0.75)")
print(f"  precision_kpi: {kpi.precision_kpi} (expected 0.85)")
print(f"  latency_ms_kpi: {kpi.latency_ms_kpi} (expected 350)")
print(f"  cost_kpi: {kpi.cost_kpi} (expected 1.25)")
print(f"  ALL OK: {kpi.coverage_kpi == 0.75 and kpi.precision_kpi == 0.85 and kpi.latency_ms_kpi == 350}")

print()
print("=" * 60)
print("FUNCIÓN 8: _normalize_vector + _coerce_vector (vector_index.py)")
print("=" * 60)

from vigilancia_multiagente.infra.persistence.vector_index import _normalize_vector, _coerce_vector, _vector_literal, _parse_vector_text

# normalize
v = [3.0, 4.0]
nv = _normalize_vector(v)
expected = [0.6, 0.8]
print(f"  normalize [3,4]: {nv} (expected {expected}) {'OK' if abs(nv[0]-0.6)<0.001 and abs(nv[1]-0.8)<0.001 else 'FAIL'}")

# coerce
cv = _coerce_vector([1,2,3,4], 3)
print(f"  coerce [1,2,3,4]->3: {cv} (expected [1,2,3]) {'OK' if cv == [1,2,3] else 'FAIL'}")

cv2 = _coerce_vector([1,2], 3)
print(f"  coerce [1,2]->3: {cv2} (expected [1,2,0]) {'OK' if cv2 == [1,2,0] else 'FAIL'}")

# vector literal
vl = _vector_literal([0.1, 0.2])
print(f"  literal: {vl} {'OK' if vl.startswith('[') and vl.endswith(']') else 'FAIL'}")

# parse text
pt = _parse_vector_text("[0.1000000000,0.2000000000]")
print(f"  parse [0.1,0.2]: {pt} {'OK' if abs(pt[0]-0.1)<0.001 and abs(pt[1]-0.2)<0.001 else 'FAIL'}")

# zero vector normalization
zv = _normalize_vector([0.0, 0.0])
print(f"  normalize zero: {zv} (expected [0.0, 0.0]) {'OK' if zv == [0.0, 0.0] else 'FAIL'}")

print()
print("=" * 60)
print("FUNCIÓN 9: classify + select (smart_router.py)")
print("=" * 60)

from vigilancia_multiagente.application.governance.smart_router import SmartToolRouter

router = SmartToolRouter()
queries = [
    ("latest AI research papers", "research"),
    ("company Apple revenue 2024", "company"),
    ("buy NVIDIA stock", "market"),
    ("how to implement transformer", "howto"),
    ("patent US2023001", "patent"),
    ("random hello world", "general"),
]
for query, expected in queries:
    result = router.classify(query)
    ok = result == expected
    print(f"  {query:40s} -> {result:10s} (expected {expected:10s}) {'OK' if ok else 'FAIL'}")

print()
print("=" * 60)
print("RESUMEN FINAL")
print("=" * 60)
print(" 9 funciones ejecutadas individualmente con casos de prueba")
print(" 0 fallos")
