"""F2.C ingestion smoke tests (Spec 021).

Covers: chunking windowing, dedup exact + near, ACL allowlist build,
orchestrator wiring against fake connectors and a fake vector index.
Each module has at least 3 focused tests. Network isolation: zero.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

import pytest

from vigilancia_multiagente.domain.ports.ingestion_connector import (
    ACLScope,
    DocumentRef,
    RawDoc,
)
from vigilancia_multiagente.enterprise.ingestion.acl_resolver import (
    ACLResolver,
    Principal,
)
from vigilancia_multiagente.enterprise.ingestion.chunking import (
    Chunk,
    chunk_text,
)
from vigilancia_multiagente.enterprise.ingestion.dedup import dedup_chunks
from vigilancia_multiagente.enterprise.ingestion.orchestrator import (
    IngestionOrchestrator,
)

_TENANT = UUID("00000000-0000-0000-0000-000000000001")


# ---------------------------------------------------------------------------
# chunking
# ---------------------------------------------------------------------------


def test_chunk_text_returns_empty_for_blank_input():
    assert chunk_text(document_id="d", text="") == []
    assert chunk_text(document_id="d", text="   \n  ") == []


def test_chunk_text_windows_with_overlap():
    text = "a" * (4 * 512 + 100)  # 2148 chars → 2 windows w/ overlap
    chunks = chunk_text(
        document_id="d", text=text, tokens_per_chunk=512, overlap_tokens=64
    )
    assert len(chunks) >= 2
    # Overlap means chunk2 starts before chunk1 ends.
    if len(chunks) >= 2:
        assert chunks[1].char_start < chunks[0].char_end


def test_chunk_text_invalid_overlap_raises():
    with pytest.raises(ValueError, match="overlap_tokens"):
        chunk_text(document_id="d", text="x", tokens_per_chunk=10, overlap_tokens=10)


def test_chunk_text_assigns_sequential_chunk_ids():
    chunks = chunk_text(
        document_id="d", text="x" * 4000, base_chunk_id=100,
        tokens_per_chunk=128, overlap_tokens=16,
    )
    ids = [c.chunk_id for c in chunks]
    assert ids == list(range(100, 100 + len(chunks)))


# ---------------------------------------------------------------------------
# dedup
# ---------------------------------------------------------------------------


def _mk_chunk(cid: int, text: str) -> Chunk:
    return Chunk(
        chunk_id=cid, document_id="d", text=text,
        char_start=0, char_end=len(text), metadata={},
    )


def test_dedup_drops_exact_duplicates():
    chunks = [
        _mk_chunk(1, "the quick brown fox"),
        _mk_chunk(2, "the quick brown fox"),
        _mk_chunk(3, "different content here"),
    ]
    res = dedup_chunks(chunks)
    assert len(res.kept) == 2
    assert (2, 1) in res.duplicates


def test_dedup_drops_near_duplicates():
    chunks = [
        _mk_chunk(1, "the quick brown fox jumps over the lazy dog"),
        _mk_chunk(2, "the quick brown fox jumps over the lazy dog!"),  # 1 char diff
        _mk_chunk(3, "totally unrelated and very different text content here please"),
    ]
    res = dedup_chunks(chunks)
    # near-duplicate dropped
    assert len(res.kept) == 2


def test_dedup_preserves_order_of_first_seen():
    chunks = [_mk_chunk(i, f"unique-{i}-{'x' * 30}") for i in (1, 2, 3, 4)]
    res = dedup_chunks(chunks)
    assert [c.chunk_id for c in res.kept] == [1, 2, 3, 4]


# ---------------------------------------------------------------------------
# acl_resolver
# ---------------------------------------------------------------------------


def test_acl_allowlist_returns_only_tenant_owned_chunks():
    other_tenant = UUID("99999999-9999-9999-9999-999999999999")
    r = ACLResolver()
    r.register_chunk(1, ACLScope(tenant_id=_TENANT, public=True))
    r.register_chunk(2, ACLScope(tenant_id=other_tenant, public=True))
    out = r.allowlist_for(Principal(tenant_id=_TENANT, user="alice"))
    assert out == [1]


def test_acl_allowlist_honors_role_membership():
    r = ACLResolver()
    r.register_chunk(1, ACLScope(tenant_id=_TENANT, roles=frozenset({"admin"})))
    r.register_chunk(2, ACLScope(tenant_id=_TENANT, roles=frozenset({"viewer"})))
    out = r.allowlist_for(
        Principal(tenant_id=_TENANT, user="alice", roles=frozenset({"viewer"}))
    )
    assert out == [2]


def test_acl_allowlist_includes_public_chunks():
    r = ACLResolver()
    r.register_chunk(1, ACLScope(tenant_id=_TENANT, public=True))
    r.register_chunk(2, ACLScope(tenant_id=_TENANT, users=frozenset({"bob"})))
    out = r.allowlist_for(Principal(tenant_id=_TENANT, user="alice"))
    assert out == [1]


# ---------------------------------------------------------------------------
# orchestrator (with fakes)
# ---------------------------------------------------------------------------


@dataclass
class _FakeConnector:
    name: str = "fake_drive"
    docs: list[DocumentRef] = None  # type: ignore[assignment]
    raw_text_by_id: dict[str, str] = None  # type: ignore[assignment]
    fail_extract: set[str] = None  # type: ignore[assignment]

    def __post_init__(self):
        if self.docs is None:
            now = datetime.now(UTC)
            self.docs = [
                DocumentRef(
                    connector=self.name,
                    external_id="doc-1",
                    title="Doc One",
                    mime_type="text/plain",
                    last_modified=now,
                ),
            ]
        if self.raw_text_by_id is None:
            self.raw_text_by_id = {"doc-1": "alpha beta gamma delta " * 50}
        if self.fail_extract is None:
            self.fail_extract = set()

    async def discover(self):
        return list(self.docs)

    async def extract(self, ref):
        if ref.external_id in self.fail_extract:
            raise RuntimeError(f"forced extract failure for {ref.external_id}")
        text = self.raw_text_by_id.get(ref.external_id, "")
        return RawDoc(ref=ref, text=text, bytes_size=len(text.encode()))

    async def acl_for(self, ref):
        return ACLScope(tenant_id=_TENANT, public=True)


class _FakeEmbedder:
    async def embed_batch(self, texts):
        # Stable 4-dim embedding per text (length-based).
        return [[float(len(t)), 0.1, 0.2, 0.3] for t in texts]


class _FakeIndex:
    def __init__(self):
        self.added = 0
        self.persisted = False
        self.tenant_seen: UUID | None = None

    async def add(self, tenant_id, chunks):
        self.tenant_seen = tenant_id
        self.added += len(chunks)
        return len(chunks)

    async def persist(self, tenant_id):
        self.persisted = True


@pytest.mark.asyncio
async def test_orchestrator_happy_path():
    embedder = _FakeEmbedder()
    index = _FakeIndex()
    resolver = ACLResolver()
    orch = IngestionOrchestrator(
        embedding_gateway=embedder, vector_index=index, acl_resolver=resolver
    )
    report = await orch.run_for_connector(_FakeConnector(), _TENANT)
    assert report.discovered == 1
    assert report.extracted == 1
    assert report.indexed > 0
    assert index.persisted is True
    assert index.tenant_seen == _TENANT
    assert resolver.total_for_tenant(_TENANT) > 0
    assert report.errors == []


@pytest.mark.asyncio
async def test_orchestrator_extract_failure_records_error_and_continues():
    """A failure on one doc must not abort the whole run."""
    now = datetime.now(UTC)
    docs = [
        DocumentRef(connector="fake_drive", external_id="bad", title="bad",
                    mime_type="text/plain", last_modified=now),
        DocumentRef(connector="fake_drive", external_id="ok", title="ok",
                    mime_type="text/plain", last_modified=now),
    ]
    connector = _FakeConnector(
        docs=docs,
        raw_text_by_id={"bad": "x" * 100, "ok": "y" * 100},
        fail_extract={"bad"},
    )
    orch = IngestionOrchestrator(
        embedding_gateway=_FakeEmbedder(),
        vector_index=_FakeIndex(),
        acl_resolver=ACLResolver(),
    )
    report = await orch.run_for_connector(connector, _TENANT)
    assert report.discovered == 2
    assert report.extracted == 1
    assert any("extract(bad)" in e for e in report.errors)


@pytest.mark.asyncio
async def test_orchestrator_run_all_keeps_independent_failures():
    """A connector raising at orchestrator level still produces a report."""

    class _Boom(_FakeConnector):
        async def discover(self):
            raise RuntimeError("auth missing")

    orch = IngestionOrchestrator(
        embedding_gateway=_FakeEmbedder(),
        vector_index=_FakeIndex(),
        acl_resolver=ACLResolver(),
    )
    reports = await orch.run_all([_Boom(name="bad"), _FakeConnector()], _TENANT)
    assert len(reports) == 2
    assert reports[0].errors  # failure recorded
    assert reports[1].indexed > 0
