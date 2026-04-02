"""Tests for RevettrIsSafeTool, RevettrExplainTool, RevettrHealthTool, and new ScoreTool params."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from crewai_revettr.tools import (
    RevettrExplainTool,
    RevettrHealthTool,
    RevettrIsSafeTool,
    RevettrScoreTool,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def score_tool():
    return RevettrScoreTool()


@pytest.fixture
def safe_tool():
    return RevettrIsSafeTool()


@pytest.fixture
def explain_tool():
    return RevettrExplainTool()


@pytest.fixture
def health_tool():
    return RevettrHealthTool()


@pytest.fixture
def mock_score_result():
    return SimpleNamespace(
        score=82,
        tier="low_risk",
        confidence=0.95,
        flags=["verified_domain"],
        signals=[
            SimpleNamespace(name="domain_age", score=90),
            SimpleNamespace(name="ssl_valid", score=85),
        ],
    )


@pytest.fixture
def mock_client():
    return MagicMock()


# ---------------------------------------------------------------------------
# RevettrScoreTool — new parameters
# ---------------------------------------------------------------------------

class TestScoreToolNewParams:
    @patch("crewai_revettr.tools._build_client")
    def test_stellar_wallet(self, mock_build, score_tool, mock_score_result, mock_client):
        mock_client.score.return_value = mock_score_result
        mock_build.return_value = mock_client

        result = score_tool._run(stellar_wallet="GABCDEF")

        mock_client.score.assert_called_once_with(stellar_wallet="GABCDEF")
        assert "82/100" in result

    @patch("crewai_revettr.tools._build_client")
    def test_email(self, mock_build, score_tool, mock_score_result, mock_client):
        mock_client.score.return_value = mock_score_result
        mock_build.return_value = mock_client

        result = score_tool._run(email="test@example.com")

        mock_client.score.assert_called_once_with(email="test@example.com")
        assert "82/100" in result

    @patch("crewai_revettr.tools._build_client")
    def test_amount(self, mock_build, score_tool, mock_score_result, mock_client):
        mock_client.score.return_value = mock_score_result
        mock_build.return_value = mock_client

        result = score_tool._run(domain="example.com", amount=500.0)

        mock_client.score.assert_called_once_with(
            domain="example.com", amount_usd=500.0
        )
        assert "82/100" in result

    @patch("crewai_revettr.tools._build_client")
    def test_new_identifiers_prevent_error(self, mock_build, score_tool, mock_client):
        """stellar_wallet and email alone should not trigger 'no identifier' error."""
        mock_client.score.return_value = SimpleNamespace(
            score=50, tier="medium_risk", confidence=0.7
        )
        mock_build.return_value = mock_client

        result = score_tool._run(stellar_wallet="GABCDEF")
        assert "Error: At least one identifier" not in result

        result = score_tool._run(email="a@b.com")
        assert "Error: At least one identifier" not in result

    def test_no_identifiers_still_errors(self, score_tool):
        result = score_tool._run()
        assert "Error" in result
        assert "At least one identifier" in result


# ---------------------------------------------------------------------------
# RevettrIsSafeTool
# ---------------------------------------------------------------------------

class TestIsSafeTool:
    @patch("crewai_revettr.tools._build_client")
    def test_safe_wallet(self, mock_build, safe_tool, mock_client):
        mock_client.is_safe_to_transact.return_value = {
            "safe": True,
            "score": 85,
            "blocking_flags": [],
        }
        mock_build.return_value = mock_client

        result = safe_tool._run(wallet_address="0xabc")

        mock_client.is_safe_to_transact.assert_called_once_with(
            wallet_address="0xabc", chain="base", min_score=60
        )
        assert "SAFE" in result
        assert "85/100" in result

    @patch("crewai_revettr.tools._build_client")
    def test_blocked_wallet(self, mock_build, safe_tool, mock_client):
        mock_client.is_safe_to_transact.return_value = {
            "safe": False,
            "score": 25,
            "blocking_flags": ["sanctioned_entity", "mixer_usage"],
        }
        mock_build.return_value = mock_client

        result = safe_tool._run(wallet_address="0xbad", min_score=50)

        mock_client.is_safe_to_transact.assert_called_once_with(
            wallet_address="0xbad", chain="base", min_score=50
        )
        assert "BLOCKED" in result
        assert "25/100" in result
        assert "sanctioned_entity" in result
        assert "mixer_usage" in result

    @patch("crewai_revettr.tools._build_client")
    def test_amount_usd_passed(self, mock_build, safe_tool, mock_client):
        mock_client.is_safe_to_transact.return_value = {
            "safe": True,
            "score": 72,
            "blocking_flags": [],
        }
        mock_build.return_value = mock_client

        result = safe_tool._run(
            wallet_address="0xabc", amount_usd=1000.0, chain="ethereum"
        )

        mock_client.is_safe_to_transact.assert_called_once_with(
            wallet_address="0xabc",
            chain="ethereum",
            min_score=60,
            amount_usd=1000.0,
        )
        assert "72/100" in result

    @patch("crewai_revettr.tools._build_client")
    def test_error_handling(self, mock_build, safe_tool, mock_client):
        mock_client.is_safe_to_transact.side_effect = Exception("timeout")
        mock_build.return_value = mock_client

        result = safe_tool._run(wallet_address="0xabc")

        assert "Error checking transaction safety" in result
        assert "timeout" in result

    @patch("crewai_revettr.tools._build_client")
    def test_402_error(self, mock_build, safe_tool, mock_client):
        mock_client.is_safe_to_transact.side_effect = Exception("402 Payment Required")
        mock_build.return_value = mock_client

        result = safe_tool._run(wallet_address="0xabc")

        assert "Payment required" in result
        assert "REVETTR_WALLET_KEY" in result


# ---------------------------------------------------------------------------
# RevettrExplainTool
# ---------------------------------------------------------------------------

class TestExplainTool:
    @patch("crewai_revettr.tools._build_client")
    def test_explain_by_wallet(self, mock_build, explain_tool, mock_client):
        mock_client.explain_risk.return_value = {
            "summary": "Low-risk wallet with verified history.",
            "risk_factors": ["new_wallet"],
            "recommendation": "Proceed with caution.",
            "score": 75,
            "tier": "low_risk",
        }
        mock_build.return_value = mock_client

        result = explain_tool._run(wallet_address="0xabc", chain="ethereum")

        mock_client.explain_risk.assert_called_once_with(
            wallet_address="0xabc", chain="ethereum"
        )
        assert "75/100" in result
        assert "low_risk" in result
        assert "Low-risk wallet" in result
        assert "new_wallet" in result
        assert "Proceed with caution" in result

    @patch("crewai_revettr.tools._build_client")
    def test_explain_by_domain(self, mock_build, explain_tool, mock_client):
        mock_client.explain_risk.return_value = {
            "summary": "Well-established domain.",
            "risk_factors": [],
            "recommendation": "Safe to transact.",
            "score": 92,
            "tier": "trusted",
        }
        mock_build.return_value = mock_client

        result = explain_tool._run(domain="uniswap.org")

        mock_client.explain_risk.assert_called_once_with(domain="uniswap.org")
        assert "92/100" in result
        assert "Risk Factors:" not in result  # empty list

    @patch("crewai_revettr.tools._build_client")
    def test_explain_combined(self, mock_build, explain_tool, mock_client):
        mock_client.explain_risk.return_value = {
            "summary": "Mixed signals.",
            "risk_factors": ["young_domain", "high_volume"],
            "recommendation": "Review manually.",
            "score": 55,
            "tier": "medium_risk",
        }
        mock_build.return_value = mock_client

        result = explain_tool._run(
            wallet_address="0xabc", domain="new-defi.xyz", company_name="NewDeFi Inc"
        )

        mock_client.explain_risk.assert_called_once_with(
            wallet_address="0xabc",
            chain="base",
            domain="new-defi.xyz",
            company_name="NewDeFi Inc",
        )
        assert "young_domain" in result
        assert "high_volume" in result

    def test_no_identifiers_returns_error(self, explain_tool):
        result = explain_tool._run()
        assert "Error" in result
        assert "At least one identifier" in result

    @patch("crewai_revettr.tools._build_client")
    def test_error_handling(self, mock_build, explain_tool, mock_client):
        mock_client.explain_risk.side_effect = Exception("Internal server error")
        mock_build.return_value = mock_client

        result = explain_tool._run(domain="example.com")

        assert "Error explaining risk" in result
        assert "Internal server error" in result


# ---------------------------------------------------------------------------
# RevettrHealthTool
# ---------------------------------------------------------------------------

class TestHealthTool:
    @patch("crewai_revettr.tools._build_client")
    def test_healthy(self, mock_build, health_tool, mock_client):
        mock_client.health_check.return_value = {
            "status": "healthy",
            "version": "0.3.1",
            "uptime": "99.9%",
        }
        mock_build.return_value = mock_client

        result = health_tool._run()

        mock_client.health_check.assert_called_once()
        assert "Revettr API Health" in result
        assert "status: healthy" in result
        assert "version: 0.3.1" in result
        assert "uptime: 99.9%" in result

    @patch("crewai_revettr.tools._build_client")
    def test_error_handling(self, mock_build, health_tool, mock_client):
        mock_client.health_check.side_effect = Exception("Connection refused")
        mock_build.return_value = mock_client

        result = health_tool._run()

        assert "Error checking API health" in result
        assert "Connection refused" in result

    @patch("crewai_revettr.tools._build_client")
    def test_402_error(self, mock_build, health_tool, mock_client):
        mock_client.health_check.side_effect = Exception("402 Payment Required")
        mock_build.return_value = mock_client

        result = health_tool._run()

        assert "Payment required" in result


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

class TestExports:
    def test_all_tools_exported(self):
        import crewai_revettr

        assert hasattr(crewai_revettr, "RevettrScoreTool")
        assert hasattr(crewai_revettr, "RevettrIsSafeTool")
        assert hasattr(crewai_revettr, "RevettrExplainTool")
        assert hasattr(crewai_revettr, "RevettrHealthTool")

    def test_all_in___all__(self):
        import crewai_revettr

        for name in [
            "RevettrScoreTool",
            "RevettrIsSafeTool",
            "RevettrExplainTool",
            "RevettrHealthTool",
        ]:
            assert name in crewai_revettr.__all__
