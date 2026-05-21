from __future__ import annotations

from uuid import uuid4

import pytest

from vigilancia_multiagente.application.evaluation.forensic.jsonb_trace_writer import (
    JsonbForensicTraceWriter,
)
from vigilancia_multiagente.domain.evaluation_entities import TraceStep, TraceStepType


@pytest.mark.asyncio
async def test_forensic_trace_writer_preserves_order_and_confidence_chain() -> None:
    writer = JsonbForensicTraceWriter()
    claim_id = uuid4()
    steps = [
        TraceStep(TraceStepType.SOURCE_FETCH, "s1", "o1", "rule-1"),
        TraceStep(TraceStepType.EXTRACTION, "s2", "o2", "rule-2"),
        TraceStep(TraceStepType.REASONING, "s3", "o3", "rule-3"),
    ]

    for confidence, step in zip((0.91, 0.83, 0.77), steps, strict=True):
        await writer.record_step(claim_id, step, confidence)

    trace = await writer.finalize(claim_id)

    assert trace.chain == steps
    assert trace.confidence_at_each_step == [0.91, 0.83, 0.77]

