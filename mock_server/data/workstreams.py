"""Mock evaluation data for workstreams A–E.

Provides realistic simulated results for all 5 evaluation workstreams.
Used by mock_server/routes/research.py to populate SessionEvaluation.
"""

MOCK_WSA_DATA = {
    "author_reputations": [
        {
            "author_id": "A123",
            "name": "Jane Smith",
            "h_index": 42,
            "retraction_count": 0,
            "affiliation": "MIT",
            "domain_weights": {"ai": 0.8, "robotics": 0.2},
            "last_refreshed": "2026-05-20T10:30:00Z",
        },
        {
            "author_id": "A456",
            "name": "Carlos Mendez",
            "h_index": 28,
            "retraction_count": 0,
            "affiliation": "Bosch Research",
            "domain_weights": {"manufacturing": 0.9, "ai": 0.6},
            "last_refreshed": "2026-05-20T10:30:00Z",
        },
    ],
    "conflicts_of_interest": [
        {
            "author_id": "A123",
            "funder_entity": "Google Research",
            "corporate_ratio": 0.75,
            "risk_level": "high",
        },
    ],
    "external_validations": [
        {
            "claim_id": "C001",
            "status": "verified",
            "source": "Google FactCheck API",
            "summary": "Claim about ViT weld detection accuracy verified by independent lab.",
        },
        {
            "claim_id": "C002",
            "status": "not_found",
            "source": "Wikidata",
            "summary": "No external validation found for digital twin ROI claim.",
        },
    ],
    "retraction_records": [
        {
            "doi": "10.1234/retracted.2023.001",
            "title": "AI-based Defect Detection in Automotive Assembly",
            "retraction_date": "2024-03-15",
            "reason": "Data fabrication",
        },
    ],
    "reproducibility_scores": [
        {"source_id": "s1", "score": 0.85, "artifacts_available": True, "last_checked": "2026-05-19"},
        {"source_id": "s2", "score": 0.62, "artifacts_available": False, "last_checked": "2026-05-19"},
    ],
    "effective_freshness": [0.85, 0.92],
}

MOCK_WSB_DATA = {
    "hybrid_search_stats": {
        "total_queries": 24,
        "bm25_hits": 156,
        "embedding_hits": 183,
        "combined_hits": 312,
    },
    "dedup_rate": 0.34,
    "deduped_sources": [
        {"canonical_id": "cs1", "original_ids": ["o1", "o2"], "title": "Vision Transformers for Manufacturing QC", "provider": "arxiv"},
        {"canonical_id": "cs2", "original_ids": ["o3", "o4", "o5"], "title": "Generative AI in Automotive Industry 2024", "provider": "tavily"},
    ],
    "authenticity_signals": [
        {"source_id": "s1", "ai_probability": 0.18, "human_probability": 0.82, "verdict": "likely_human"},
        {"source_id": "s3", "ai_probability": 0.71, "human_probability": 0.29, "verdict": "likely_ai"},
    ],
    "consensus_disputes": [
        {"topic": "digital-twin-roi", "agreement": False, "source_count": 5, "confidence": 0.65},
    ],
}

MOCK_WSC_DATA = {
    "s_curves": [
        {
            "technology": "Quantum ML",
            "domain": "manufacturing",
            "growth_rate": 0.15,
            "inflection_year": 2028,
            "ceiling": 0.92,
            "r_squared": 0.87,
            "confidence": 0.78,
            "samples_count": 45,
            "chart_image": "/charts/scurve-quantum-ml.png",
        },
        {
            "technology": "Edge AI Inspection",
            "domain": "automotive",
            "growth_rate": 0.22,
            "inflection_year": 2027,
            "ceiling": 0.88,
            "r_squared": 0.91,
            "confidence": 0.85,
            "samples_count": 62,
            "chart_image": "/charts/scurve-edge-ai.png",
        },
    ],
    "charts": [
        {
            "title": "Convergencia de inversión vs. publicaciones (2018-2027)",
            "image": "/charts/convergence-investment.png",
            "caption": "Correlación entre flujo de inversión y producción científica. Generado por el agente de análisis profundo con matplotlib.",
        },
    ],
    "meta_analyses": [
        {
            "topic": "ViT vs CNN in weld detection",
            "effect_size_range": [0.12, 0.38],
            "i_squared": 0.45,
            "sample_count": 14,
        },
    ],
    "implicit_assumptions": [
        {"text": "Quantum advantage will persist at scale", "severity": "high", "affects_confidence": True},
        {"text": "AI training data is representative of production environments", "severity": "medium", "affects_confidence": True},
        {"text": "Hardware costs will follow Moore's law trajectory", "severity": "low", "affects_confidence": False},
    ],
    "counterfactuals": [
        {"scenario": "If error correction thresholds are not met by 2028...", "plausibility": "medium", "would_invalidate": "Growth rate projection"},
        {"scenario": "If regulatory bodies impose mandatory human oversight...", "plausibility": "high", "would_invalidate": "Full automation timeline"},
    ],
    "critical_dependencies": [
        {"dependency_name": "NVIDIA GPU supply chain", "impact_if_removed": "critical", "alternatives": ["AMD MI300X", "Intel Gaudi 3"]},
        {"dependency_name": "Rare earth magnets for sensors", "impact_if_removed": "high", "alternatives": ["Synthetic alternatives (TRL 4)"]},
    ],
}

MOCK_WSD_DATA = {
    "convergence_clusters": [
        {"cluster_id": "cl1", "domains": ["AI", "robotics", "manufacturing"], "growth_trend": "accelerating", "density": 0.82},
        {"cluster_id": "cl2", "domains": ["digital-twins", "simulation", "IoT"], "growth_trend": "stable", "density": 0.71},
    ],
    "collaboration_network": [
        {
            "nodes": [
                {"id": "a1", "label": "MIT", "type": "institution"},
                {"id": "a2", "label": "Toyota Research", "type": "institution"},
                {"id": "a3", "label": "Bosch", "type": "institution"},
            ],
            "edges": [
                {"source": "a1", "target": "a2", "weight": 0.8, "type": "co_author"},
                {"source": "a2", "target": "a3", "weight": 0.5, "type": "co_author"},
            ],
        },
    ],
    "idea_lineages": [
        {"seminal_work_id": "SW001", "seminal_title": "Attention Is All You Need (2017)", "leaf_works": [{"id": "LW001", "title": "ViT for Manufacturing Defect Detection (2024)", "year": 2024}, {"id": "LW002", "title": "Multimodal Quality Inspection with Transformers (2025)", "year": 2025}]},
    ],
    "narrative_shifts": [
        {"topic": "AI safety in manufacturing", "sentiment_pre": 0.35, "sentiment_post": 0.72, "direction": "positive"},
    ],
    "talent_mobilities": [
        {"person_name": "Dr. Akira Yoshino", "from_affiliation": "Toyota", "to_affiliation": "Bosch", "year": 2025},
        {"person_name": "Dr. Maria Chen", "from_affiliation": "MIT", "to_affiliation": "Tesla", "year": 2024},
    ],
    "patenting_gaps": [
        {"domain": "AI-driven paint inspection", "classification": "blue_ocean", "patent_density": 0.12, "key_assignees": ["StartupX", "UniversityY"]},
    ],
}

MOCK_WSE_DATA = {
    "bias_audit": {
        "geographic_distribution": {"north_america": 0.6, "europe": 0.3, "asia": 0.1},
        "gender_distribution": {"male": 0.7, "female": 0.25, "unknown": 0.05},
        "institutional_distribution": {"academia": 0.5, "corporate": 0.4, "government": 0.1},
        "critical_bias_detected": False,
        "language_bias": {"en": 0.95, "other": 0.05},
    },
    "forensic_traces": [
        {
            "claim_id": "C001",
            "trace_steps": [
                {"step_type": "source_extraction", "description": "Extracted from arXiv:2301.00001", "confidence": 0.95},
                {"step_type": "reasoning", "description": "Claim derived from experimental results section", "confidence": 0.88},
            ],
        },
        {
            "claim_id": "C002",
            "trace_steps": [
                {"step_type": "source_extraction", "description": "Extracted from MarketsAndMarkets 2024 report", "confidence": 0.82},
                {"step_type": "reasoning", "description": "Claim derived from market projection model", "confidence": 0.75},
                {"step_type": "cross_reference", "description": "Cross-referenced with Gartner Hype Cycle", "confidence": 0.68},
            ],
        },
    ],
    "stakeholder_simulations": [
        {"stakeholder_type": "investor", "critique": "High capital requirements limit near-term ROI", "counterpoints": ["Government grants available", "Hardware costs declining 30%/year"]},
        {"stakeholder_type": "regulator", "critique": "AI Act compliance adds 15-20% cost overhead", "counterpoints": ["Pre-compliance certification program launching 2025", "Competitive advantage for early adopters"]},
        {"stakeholder_type": "competitor", "critique": "Toyota and BMW already 2+ years ahead in deployment", "counterpoints": ["Tier-2/3 market is unaddressed by majors", "SaaS model enables faster iteration than in-house"]},
        {"stakeholder_type": "academic", "critique": "Published benchmarks may not generalize to production environments", "counterpoints": ["Industry-academia partnerships address this gap", "Transfer learning from benchmarks to production shown effective"]},
    ],
    "falsification_scenarios": [
        {"scenario": "If error correction thresholds are not met by 2028...", "plausibility": "medium", "would_invalidate": "Growth rate projection"},
        {"scenario": "If a major automotive recall is traced to AI quality control failure...", "plausibility": "low", "would_invalidate": "Industry adoption timeline"},
    ],
    "calibration_curve": {
        "model_version": "2026-05-15",
        "is_active": True,
        "curve_points": [
            {"raw": 0.1, "calibrated": 0.08},
            {"raw": 0.5, "calibrated": 0.45},
            {"raw": 0.9, "calibrated": 0.88},
        ],
        "samples_count": 12,
        "chart_image": "/charts/calibration-curve.png",
    },
    "quality_gate_passed": True,
    "calibrated_confidence": 0.84,
}
