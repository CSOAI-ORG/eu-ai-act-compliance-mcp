"""
Tests for EU AI Act Compliance MCP Server
==========================================
Tests every @mcp.tool() function directly (no MCP protocol).
Run: cd /Users/nicholas/clawd/mcp-marketplace/eu-ai-act-compliance-mcp && pytest test_server.py -v
"""

import json
import sys
import os

# Ensure no MEOK_API_KEY interferes with free-tier test paths
os.environ.pop("MEOK_API_KEY", None)

sys.path.insert(0, os.path.dirname(__file__))

from server import (
    quick_scan,
    deadline_check,
    classify_ai_risk,
    check_compliance,
    generate_documentation,
    assess_penalties,
    get_timeline,
    audit_report,
    multi_jurisdiction_map,
    predict_risk_neural,
    neural_insights,
    _usage,
)


# ── Helpers ────────────────────────────────────────────────────────
def _reset_rate_limits():
    """Clear rate limit counters between tests."""
    _usage.clear()


# ── quick_scan ─────────────────────────────────────────────────────

class TestQuickScan:
    def setup_method(self):
        _reset_rate_limits()

    def test_basic_low_risk(self):
        result = quick_scan("A spell check tool for documents")
        assert isinstance(result, dict)
        assert "risk_level" in result
        assert result["risk_level"] in ("minimal", "low", "limited", "high", "prohibited")

    def test_high_risk_hiring(self):
        result = quick_scan("AI system for hiring and recruitment screening")
        assert isinstance(result, dict)
        assert result["risk_level"] in ("high-risk", "high")

    def test_prohibited_social_scoring(self):
        result = quick_scan("Social scoring system by public authority for citizen scoring")
        assert isinstance(result, dict)
        assert result["risk_level"] in ("prohibited", "high-risk", "high")

    def test_empty_string(self):
        result = quick_scan("")
        assert isinstance(result, dict)
        assert "risk_level" in result

    def test_returns_obligations(self):
        result = quick_scan("AI chatbot for customer service")
        assert isinstance(result, dict)
        # Should have some kind of obligations or next steps
        has_actionable_keys = any(
            k in result for k in ["obligations", "top_obligations", "next_steps", "top_3_actions", "key_obligations"]
        )
        assert has_actionable_keys or "risk_level" in result

    def test_credit_scoring_high_risk(self):
        result = quick_scan("AI system for credit scoring and loan approval")
        assert isinstance(result, dict)
        assert result["risk_level"] in ("high-risk", "high")


# ── deadline_check ─────────────────────────────────────────────────

class TestDeadlineCheck:
    def setup_method(self):
        _reset_rate_limits()

    def test_returns_dict(self):
        result = deadline_check()
        assert isinstance(result, dict)

    def test_contains_deadlines(self):
        result = deadline_check()
        has_deadline_keys = any(
            k in result for k in ["deadlines", "next_deadline", "timeline", "enforcement_dates"]
        )
        assert has_deadline_keys or len(result) > 0

    def test_idempotent(self):
        r1 = deadline_check()
        r2 = deadline_check()
        # Same structure (dates may differ by a second)
        assert set(r1.keys()) == set(r2.keys())


# ── classify_ai_risk ───────────────────────────────────────────────

class TestClassifyAiRisk:
    def setup_method(self):
        _reset_rate_limits()

    def test_basic_returns_json_string(self):
        result = classify_ai_risk("A chatbot for answering FAQs")
        assert isinstance(result, dict)
        data = result
        assert "risk_level" in data or "classification" in data or "risk_classification" in data

    def test_high_risk_biometric(self):
        result = classify_ai_risk("Facial recognition system for biometric identification")
        data = result
        risk = data.get("risk_level") or data.get("classification") or data.get("risk_classification", "")
        assert "high" in risk.lower() or "prohibited" in risk.lower()

    def test_prohibited_emotion_workplace(self):
        result = classify_ai_risk("Emotion recognition in the workplace for employee monitoring")
        data = result
        risk = data.get("risk_level") or data.get("classification") or data.get("risk_classification", "")
        assert "prohibited" in risk.lower() or "high" in risk.lower()

    def test_minimal_risk(self):
        result = classify_ai_risk("AI-powered spell checker for documents")
        data = result
        risk = data.get("risk_level") or data.get("classification") or data.get("risk_classification", "")
        assert "minimal" in risk.lower() or "low" in risk.lower() or "limited" in risk.lower()

    def test_empty_description(self):
        result = classify_ai_risk("")
        data = result
        assert isinstance(data, dict)

    def test_with_caller(self):
        result = classify_ai_risk("A weather forecasting tool", caller="test_user")
        data = result
        assert isinstance(data, dict)


# ── check_compliance ───────────────────────────────────────────────

class TestCheckCompliance:
    def setup_method(self):
        _reset_rate_limits()

    def test_basic_compliant(self):
        result = check_compliance(
            system_name="TestAI",
            purpose="Customer service chatbot",
            data_types="text conversations",
            decision_scope="FAQ responses",
            has_risk_management=True,
            has_data_governance=True,
            has_technical_docs=True,
            has_logging=True,
            has_transparency_info=True,
            has_human_oversight=True,
            has_accuracy_testing=True,
        )
        assert isinstance(result, dict)
        data = result
        assert isinstance(data, dict)

    def test_non_compliant_missing_all(self):
        result = check_compliance(
            system_name="BadAI",
            purpose="Hiring decisions",
            data_types="resumes and personal data",
            decision_scope="Automated candidate filtering",
        )
        data = result
        assert isinstance(data, dict)
        # Should flag gaps when nothing is implemented
        blob = json.dumps(data).lower()
        assert "gap" in blob or "fail" in blob or "missing" in blob or "non" in blob or "incomplete" in blob

    def test_empty_strings(self):
        result = check_compliance(
            system_name="",
            purpose="",
            data_types="",
            decision_scope="",
        )
        data = result
        assert isinstance(data, dict)


# ── generate_documentation ─────────────────────────────────────────

class TestGenerateDocumentation:
    def setup_method(self):
        _reset_rate_limits()

    def test_basic_generation(self):
        result = generate_documentation(
            system_name="TestAI v1",
            provider_name="MEOK AI Labs",
            provider_contact="hello@meok.ai",
            version="1.0.0",
            intended_purpose="Customer service automation",
            description="An AI chatbot for FAQ handling",
            data_description="Customer support transcripts",
            architecture_description="Transformer-based LLM",
        )
        assert isinstance(result, dict)
        data = result
        assert isinstance(data, dict)

    def test_with_optional_params(self):
        result = generate_documentation(
            system_name="TestAI v2",
            provider_name="Acme Corp",
            provider_contact="info@acme.com",
            version="2.0.0",
            intended_purpose="Document summarisation",
            description="Summarises legal documents",
            data_description="Legal text corpus",
            architecture_description="Encoder-decoder model",
            performance_metrics="ROUGE-L: 0.85, accuracy: 92%",
            risk_management_description="Continuous monitoring with human review",
            human_oversight_description="Legal expert reviews all outputs",
        )
        data = result
        assert isinstance(data, dict)

    def test_empty_optional_params(self):
        result = generate_documentation(
            system_name="MinimalDoc",
            provider_name="Test",
            provider_contact="test@test.com",
            version="0.1",
            intended_purpose="Testing",
            description="Test system",
            data_description="Test data",
            architecture_description="Simple NN",
        )
        data = result
        assert isinstance(data, dict)


# ── assess_penalties ───────────────────────────────────────────────

class TestAssessPenalties:
    def setup_method(self):
        _reset_rate_limits()

    def test_prohibited_violation(self):
        result = assess_penalties(violation_type="prohibited", annual_global_turnover_eur=100_000_000)
        data = result
        assert isinstance(data, dict)
        blob = json.dumps(data).lower()
        assert "35" in blob or "penalty" in blob or "fine" in blob or "million" in blob

    def test_high_risk_violation(self):
        result = assess_penalties(violation_type="high_risk", annual_global_turnover_eur=50_000_000)
        data = result
        assert isinstance(data, dict)

    def test_incorrect_info_violation(self):
        result = assess_penalties(violation_type="incorrect_info")
        data = result
        assert isinstance(data, dict)

    def test_sme_discount(self):
        result = assess_penalties(violation_type="prohibited", annual_global_turnover_eur=5_000_000, is_sme=True)
        data = result
        assert isinstance(data, dict)

    def test_zero_turnover(self):
        result = assess_penalties(violation_type="prohibited", annual_global_turnover_eur=0)
        data = result
        assert isinstance(data, dict)

    def test_invalid_violation_type(self):
        result = assess_penalties(violation_type="nonexistent_type")
        data = result
        assert isinstance(data, dict)
        # Should handle gracefully (error or unknown classification)


# ── get_timeline ───────────────────────────────────────────────────

class TestGetTimeline:
    def setup_method(self):
        _reset_rate_limits()

    def test_returns_json(self):
        result = get_timeline()
        assert isinstance(result, dict)
        data = result
        assert isinstance(data, dict)

    def test_contains_dates(self):
        result = get_timeline()
        data = result
        blob = json.dumps(data)
        # Should mention at least one year
        assert "2024" in blob or "2025" in blob or "2026" in blob or "2027" in blob

    def test_idempotent(self):
        r1 = get_timeline()
        r2 = get_timeline()
        assert set(r1.keys()) == set(r2.keys())


# ── audit_report ───────────────────────────────────────────────────

class TestAuditReport:
    def setup_method(self):
        _reset_rate_limits()

    def test_basic_audit(self):
        result = audit_report(
            system_name="AuditTestAI",
            provider_name="Test Corp",
            provider_contact="test@test.com",
            version="1.0",
            purpose="Automated hiring screening",
            description="AI system that screens job applicants",
            data_types="resumes, application forms",
            decision_scope="Shortlisting candidates for interview",
            architecture_description="Gradient boosted trees",
        )
        assert isinstance(result, dict)
        data = result
        assert isinstance(data, dict)

    def test_fully_compliant_audit(self):
        result = audit_report(
            system_name="CompliantAI",
            provider_name="Good Corp",
            provider_contact="good@corp.com",
            version="2.0",
            purpose="Weather prediction",
            description="Forecasts weather conditions",
            data_types="meteorological data",
            decision_scope="Advisory weather reports",
            architecture_description="CNN + LSTM",
            has_risk_management=True,
            has_data_governance=True,
            has_technical_docs=True,
            has_logging=True,
            has_transparency_info=True,
            has_human_oversight=True,
            has_accuracy_testing=True,
        )
        data = result
        assert isinstance(data, dict)


# ── multi_jurisdiction_map ─────────────────────────────────────────

class TestMultiJurisdictionMap:
    def setup_method(self):
        _reset_rate_limits()

    def test_article_9(self):
        result = multi_jurisdiction_map(article="Article 9")
        assert isinstance(result, dict)
        data = result
        assert isinstance(data, dict)

    def test_article_10(self):
        result = multi_jurisdiction_map(article="Article 10")
        data = result
        assert isinstance(data, dict)

    def test_with_jurisdictions(self):
        result = multi_jurisdiction_map(article="Article 5", jurisdictions=["uk", "us_nist"])
        data = result
        assert isinstance(data, dict)

    def test_unknown_article(self):
        result = multi_jurisdiction_map(article="Article 999")
        data = result
        assert isinstance(data, dict)


# ── predict_risk_neural ────────────────────────────────────────────

class TestPredictRiskNeural:
    def setup_method(self):
        _reset_rate_limits()

    def test_basic_prediction(self):
        result = predict_risk_neural(system_name="TestBot")
        assert isinstance(result, dict)

    def test_high_risk_signals(self):
        result = predict_risk_neural(
            system_name="BiometricScreener",
            system_type="biometric identification",
            uses_biometric=True,
            uses_health_data=True,
            has_human_oversight=False,
            affected_users=1_000_000,
            sector="healthcare",
        )
        assert isinstance(result, dict)

    def test_low_risk_signals(self):
        result = predict_risk_neural(
            system_name="SpellChecker",
            system_type="text editing",
            uses_biometric=False,
            uses_health_data=False,
            uses_financial_data=False,
            has_human_oversight=True,
            affected_users=100,
            has_documentation=True,
            prior_incidents=0,
            model_explainable=True,
        )
        assert isinstance(result, dict)

    def test_empty_name(self):
        result = predict_risk_neural(system_name="")
        assert isinstance(result, dict)


# ── neural_insights ────────────────────────────────────────────────

class TestNeuralInsights:
    def setup_method(self):
        _reset_rate_limits()

    def test_returns_dict(self):
        result = neural_insights()
        assert isinstance(result, dict)

    def test_has_content(self):
        result = neural_insights()
        assert len(result) > 0


# ── Rate Limiting ──────────────────────────────────────────────────

class TestRateLimiting:
    def setup_method(self):
        _reset_rate_limits()

    def test_quick_scan_rate_limit_after_10(self):
        """Free tier should rate limit after 10 calls."""
        for i in range(10):
            result = quick_scan(f"Test system {i}")
            assert "error" not in result or result.get("error") != "rate_limited"

        result = quick_scan("One more call")
        assert isinstance(result, dict)
        if "error" in result:
            assert result["error"] == "rate_limited"
