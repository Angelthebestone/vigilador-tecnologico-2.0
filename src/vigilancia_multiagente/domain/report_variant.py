from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class ReportType(StrEnum):
    TECHNICAL = "technical"
    EXECUTIVE = "executive"
    RISK = "risk"
    INVESTOR = "investor"


@dataclass
class ReportSection:
    heading: str
    content: str
    source_finding_ids: list[UUID] = field(default_factory=list)


@dataclass
class ReportVariant:
    type: ReportType
    title: str
    sections: list[ReportSection] = field(default_factory=list)
    finding_ids: list[UUID] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.utcnow)
    export_formats: list[str] = field(default_factory=lambda: ["md", "html"])
