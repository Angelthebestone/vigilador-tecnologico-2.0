"""Tests for Backend Intelligence v3 features."""

import pytest


class TestSmartRouter:
    def test_classify_academic(self):
        from vigilancia_multiagente.application.governance.smart_router import SmartToolRouter
        router = SmartToolRouter()
        assert router.classify("machine learning paper 2025") == "academic"
    
    def test_classify_company(self):
        from vigilancia_multiagente.application.governance.smart_router import SmartToolRouter
        router = SmartToolRouter()
        assert router.classify("best AI startups for healthcare") == "company"

    def test_classify_general_fallback(self):
        from vigilancia_multiagente.application.governance.smart_router import SmartToolRouter
        router = SmartToolRouter()
        assert router.classify("hello world") == "general"

    def test_select_returns_tuple(self):
        from vigilancia_multiagente.application.governance.smart_router import SmartToolRouter
        router = SmartToolRouter()
        result = router.select("deep research on transformers")
        assert isinstance(result, tuple)


class TestObsolescenceDetector:
    @pytest.mark.asyncio
    async def test_analyze_returns_signal(self):
        from vigilancia_multiagente.application.evaluation.obsolescence_detector import ObsolescenceDetector
        detector = ObsolescenceDetector()
        result = await detector.analyze("React Native")
        assert result.tech == "React Native"
        assert isinstance(result.confidence, float)


class TestHypeDetector:
    @pytest.mark.asyncio
    async def test_analyze_returns_report(self):
        from vigilancia_multiagente.application.evaluation.hype_detector import HypeDetector
        detector = HypeDetector()
        report = await detector.analyze("Web3")
        assert report.tech == "Web3"
        assert report.verdict in ("real", "exagerada", "insufficient_data", "unknown")


class TestDecisionAssistant:
    @pytest.mark.asyncio
    async def test_analyze_returns_report(self):
        from vigilancia_multiagente.application.fusion.decision_assistant import DecisionAssistant
        assistant = DecisionAssistant()
        report = await assistant.analyze("Should we adopt WebAssembly?")
        assert report.question == "Should we adopt WebAssembly?"
        assert isinstance(report.confidence, float)
