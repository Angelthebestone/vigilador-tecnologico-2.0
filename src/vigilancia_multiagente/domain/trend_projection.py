from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TrendProjection:
    source_data: dict
    projected_values: list[dict] = field(default_factory=list)
    confidence_intervals: dict = field(default_factory=lambda: {"95": 1.96, "80": 1.28})
    inflection_points: list[dict] = field(default_factory=list)
    model_type: str = "polynomial"
    data_quality: str = "sufficient"
    created_at: datetime = field(default_factory=datetime.utcnow)
