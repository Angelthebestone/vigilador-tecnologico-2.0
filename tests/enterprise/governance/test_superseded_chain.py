"""Tests for superseded_chain module (DB-free with mocked session)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from vigilancia_multiagente.enterprise.governance.superseded_chain import mark_superseded


class TestMarkSuperseded:
    @pytest.mark.asyncio
    async def test_calls_update_with_correct_params(self) -> None:
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.rowcount = 0
        session.execute.return_value = result_mock

        tenant_id = uuid4()
        new_id = uuid4()
        count = await mark_superseded(tenant_id, "config/skills/s.yaml", new_id, session)

        assert count == 0
        session.execute.assert_called_once()
        call_args = session.execute.call_args
        params = call_args[0][1]
        assert params["tenant_id"] == tenant_id
        assert params["target_file"] == "config/skills/s.yaml"
        assert params["new_id"] == new_id

    @pytest.mark.asyncio
    async def test_returns_rowcount_when_rows_updated(self) -> None:
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.rowcount = 2
        session.execute.return_value = result_mock

        count = await mark_superseded(uuid4(), "config/skills/s.yaml", uuid4(), session)
        assert count == 2

    @pytest.mark.asyncio
    async def test_filters_by_tenant_and_file(self) -> None:
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.rowcount = 1
        session.execute.return_value = result_mock

        tenant_id = uuid4()
        await mark_superseded(tenant_id, "config/modes/deep.yaml", uuid4(), session)

        call_args = session.execute.call_args
        sql_text = str(call_args[0][0].text)
        assert "tenant_id" in sql_text
        assert "target_file" in sql_text
        assert "status = 'applied'" in sql_text
