# API Contracts: Research Evaluation

## GET /research/{session_id}/evaluation

Returns evaluation results from all workstreams active during the research session.

### Response `200 OK`
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "active_workstreams": ["ws_a", "ws_c", "ws_e"],
  "ws_a": {
    "author_reputations": [
      {
        "author_id": "A123",
        "name": "Jane Smith",
        "h_index": 42,
        "retraction_count": 0,
        "affiliation": "MIT",
        "domain_weights": {"ai": 0.8, "robotics": 0.2},
        "last_refreshed": "2026-05-20T10:30:00Z"
      }
    ],
    "conflicts_of_interest": [
      {
        "author_id": "A123",
        "funder_entity": "Google Research",
        "corporate_ratio": 0.75,
        "risk_level": "high"
      }
    ],
    "external_validations": [],
    "retraction_records": [],
    "reproducibility_scores": [],
    "effective_freshness": [0.85, 0.92]
  },
  "ws_b": null,
  "ws_c": {
    "s_curves": [
      {
        "technology": "Quantum ML",
        "growth_rate": 0.15,
        "inflection_year": 2028,
        "ceiling": 0.92,
        "r_squared": 0.87,
        "confidence": 0.78,
        "samples_count": 45
      }
    ],
    "meta_analyses": [],
    "implicit_assumptions": [
      {
        "text": "Quantum advantage will persist at scale",
        "severity": "high",
        "affects_confidence": true
      }
    ],
    "counterfactuals": [],
    "critical_dependencies": []
  },
  "ws_d": null,
  "ws_e": {
    "bias_audit": {
      "geographic_distribution": {"north_america": 0.6, "europe": 0.3, "asia": 0.1},
      "gender_distribution": {"male": 0.7, "female": 0.25, "unknown": 0.05},
      "institutional_distribution": {"academia": 0.5, "corporate": 0.4, "government": 0.1},
      "critical_bias_detected": false,
      "language_bias": {"en": 0.95, "other": 0.05}
    },
    "forensic_traces": [
      {
        "claim_id": "C001",
        "trace_steps": [
          {"step_type": "source_extraction", "description": "Extracted from arXiv:2301.00001", "confidence": 0.95},
          {"step_type": "reasoning", "description": "Claim derived from experimental results section", "confidence": 0.88}
        ]
      }
    ],
    "stakeholder_simulations": [
      {
        "stakeholder_type": "investor",
        "critique": "High capital requirements limit near-term ROI",
        "counterpoints": ["Government grants available", "Hardware costs declining 30%/year"]
      }
    ],
    "falsification_scenarios": [
      {
        "scenario": "If error correction thresholds are not met by 2028...",
        "plausibility": "medium",
        "would_invalidate": "Growth rate projection"
      }
    ],
    "calibration_curve": {
      "model_version": "2026-05-15",
      "is_active": true,
      "curve_points": [
        {"raw": 0.1, "calibrated": 0.08},
        {"raw": 0.5, "calibrated": 0.45},
        {"raw": 0.9, "calibrated": 0.88}
      ],
      "samples_count": 12
    },
    "quality_gate_passed": true,
    "calibrated_confidence": 0.84
  },
  "branch_evaluations": [
    {
      "branch_type": "AVANCES",
      "coverage_kpi": 0.75,
      "precision_kpi": 0.82,
      "latency_ms_kpi": 12500,
      "cost_kpi": 0.15
    }
  ]
}
```

### Errors
- `404` — Session not found
- `500` — Error retrieving evaluation data

### Notes
- Any workstream not active during the session returns `null`
- `branch_evaluations` retains the existing legacy format for backward compatibility
- `calibration_curve` is `null` when fewer than 5 calibration samples exist
