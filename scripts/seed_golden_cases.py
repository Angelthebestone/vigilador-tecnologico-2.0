#!/usr/bin/env python3
"""Seed the minimum WS-E golden cases."""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import dataclass
from uuid import UUID, uuid5

from sqlalchemy import text

from vigilancia_multiagente.infra.db.connection import Database


@dataclass(frozen=True, slots=True)
class GoldenCaseSeed:
    name: str
    description: str
    seed_query: str
    expected_findings: list[dict[str, object]]
    expected_confidence: float
    priority: str = "p2_normal"

    @property
    def id(self) -> UUID:
        return uuid5(UUID("8c0c9d6c-6d57-4a8c-9c4d-6c2a52e8f2d1"), self.name)


MINIMUM_SUITE = (
    GoldenCaseSeed(
        name="alphafold-baseline",
        description="Baseline on structure prediction claims.",
        seed_query="alphafold baseline claim",
        expected_findings=[
            {
                "topic": "alphafold",
                "statement": "structure prediction baseline remains strong",
                "confidence_min": 0.7,
                "confidence_max": 0.9,
            }
        ],
        expected_confidence=0.74,
    ),
    GoldenCaseSeed(
        name="llm-chem",
        description="Chemistry claims around LLM assistance.",
        seed_query="llm chemistry claim",
        expected_findings=[
            {
                "topic": "llm-chem",
                "statement": "assistant-assisted chemistry claims need caution",
                "confidence_min": 0.65,
                "confidence_max": 0.85,
            }
        ],
        expected_confidence=0.72,
    ),
    GoldenCaseSeed(
        name="convergence-ai-bio",
        description="Convergence claims across AI and biology.",
        seed_query="ai biology convergence claim",
        expected_findings=[
            {
                "topic": "convergence",
                "statement": "cross-domain convergence is plausible but noisy",
                "confidence_min": 0.6,
                "confidence_max": 0.82,
            }
        ],
        expected_confidence=0.78,
    ),
)


async def _seed_cases(database: Database, cases: tuple[GoldenCaseSeed, ...]) -> None:
    async with database.session() as session:
        for case in cases:
            await session.execute(
                text(
                    "INSERT INTO golden_case"
                    " (id, name, description, seed_query, expected_findings,"
                    "  expected_confidence, priority, is_active)"
                    " VALUES (:id, :name, :description, :seed_query,"
                    "         CAST(:expected_findings AS JSONB),"
                    "         :expected_confidence, :priority, TRUE)"
                    " ON CONFLICT (name) DO UPDATE SET"
                    " description = EXCLUDED.description,"
                    " seed_query = EXCLUDED.seed_query,"
                    " expected_findings = EXCLUDED.expected_findings,"
                    " expected_confidence = EXCLUDED.expected_confidence,"
                    " priority = EXCLUDED.priority,"
                    " is_active = TRUE"
                ),
                {
                    "id": str(case.id),
                    "name": case.name,
                    "description": case.description,
                    "seed_query": case.seed_query,
                    "expected_findings": json.dumps(case.expected_findings),
                    "expected_confidence": case.expected_confidence,
                    "priority": case.priority,
                },
            )
        await session.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed WS-E golden cases")
    parser.add_argument("--suite", default="minimum", choices=["minimum"])
    args = parser.parse_args()

    if args.suite != "minimum":
        raise SystemExit(f"unsupported suite: {args.suite}")

    database = Database()
    asyncio.run(_seed_cases(database, MINIMUM_SUITE))
    print(f"Seeded {len(MINIMUM_SUITE)} golden cases.")


if __name__ == "__main__":
    main()
