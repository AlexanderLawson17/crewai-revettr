"""Tests for RevettrScoreTool."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from crewai_revettr.tools import RevettrScoreTool


@pytest.fixture
def tool():
    return RevettrScoreTool()


@pytest.fixture
def mock_client():
    return MagicMock()


@pytest.fixture
def mock_score_result():
    """A typical score response."""
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


class TestInputValidation:
    def test_no_identifiers_returns_error(self, tool):
        result = tool._run()
        assert "Error" in result
        assert "At least one identifier" in result

    def test_all_none_returns_error(self, tool):
        result = tool._run(domain=None, ip=None, wallet_address=None, company_name=None)
        assert "Error" in result


class TestScoring:
    @patch("crewai_revettr.tools._build_client")
    def test_score_by_domain(self, mock_build, tool, mock_score_result, mock_client):
        mock_client.score.return_value = mock_score_result
        mock_build.return_value = mock_client

        result = tool._run(domain="uniswap.org")

        mock_client.score.assert_called_once_with(domain="uniswap.org")
        assert "82/100" in result
        assert "low_risk" in result

    @patch("crewai_revettr.tools._build_client")
    def test_score_by_wallet(self, mock_build, tool, mock_score_result, mock_client):
        mock_client.score.return_value = mock_score_result
        mock_build.return_value = mock_client

        result = tool._run(wallet_address="0xabc", chain="ethereum")

        mock_client.score.assert_called_once_with(
            wallet_address="0xabc", chain="ethereum"
        )
        assert "82/100" in result

    @patch("crewai_revettr.tools._build_client")
    def test_score_by_company_name(self, mock_build, tool, mock_score_result, mock_client):
        mock_client.score.return_value = mock_score_result
        mock_build.return_value = mock_client

        result = tool._run(company_name="Acme Corp")

        mock_client.score.assert_called_once_with(company_name="Acme Corp")

    @patch("crewai_revettr.tools._build_client")
    def test_score_by_ip(self, mock_build, tool, mock_score_result, mock_client):
        mock_client.score.return_value = mock_score_result
        mock_build.return_value = mock_client

        result = tool._run(ip="1.2.3.4")

        mock_client.score.assert_called_once_with(ip="1.2.3.4")

    @patch("crewai_revettr.tools._build_client")
    def test_combined_signals(self, mock_build, tool, mock_score_result, mock_client):
        mock_client.score.return_value = mock_score_result
        mock_build.return_value = mock_client

        result = tool._run(
            domain="merchant.com",
            wallet_address="0xabc",
            company_name="Merchant Inc",
        )

        mock_client.score.assert_called_once_with(
            domain="merchant.com",
            wallet_address="0xabc",
            chain="base",
            company_name="Merchant Inc",
        )


class TestOutputFormatting:
    @patch("crewai_revettr.tools._build_client")
    def test_flags_displayed(self, mock_build, tool, mock_score_result, mock_client):
        mock_client.score.return_value = mock_score_result
        mock_build.return_value = mock_client

        result = tool._run(domain="example.com")

        assert "Flags:" in result
        assert "verified_domain" in result

    @patch("crewai_revettr.tools._build_client")
    def test_signals_displayed(self, mock_build, tool, mock_score_result, mock_client):
        mock_client.score.return_value = mock_score_result
        mock_build.return_value = mock_client

        result = tool._run(domain="example.com")

        assert "Signal Breakdown:" in result
        assert "domain_age: 90" in result
        assert "ssl_valid: 85" in result

    @patch("crewai_revettr.tools._build_client")
    def test_no_flags_or_signals(self, mock_build, tool, mock_client):
        mock_client.score.return_value = SimpleNamespace(
            score=50, tier="medium_risk", confidence=0.7
        )
        mock_build.return_value = mock_client

        result = tool._run(domain="example.com")

        assert "Flags:" not in result
        assert "Signal Breakdown:" not in result
        assert "50/100" in result


class TestWalletKey:
    @patch.dict("os.environ", {"REVETTR_WALLET_KEY": "0xsecret"})
    @patch("revettr.Revettr")
    def test_wallet_key_passed_to_client(self, mock_revettr_cls, tool, mock_score_result):
        mock_client = MagicMock()
        mock_client.score.return_value = mock_score_result
        mock_revettr_cls.return_value = mock_client

        tool._run(domain="example.com")

        mock_revettr_cls.assert_called_once_with(wallet_key="0xsecret")

    @patch.dict("os.environ", {}, clear=True)
    @patch("revettr.Revettr")
    def test_no_wallet_key(self, mock_revettr_cls, tool, mock_score_result):
        mock_client = MagicMock()
        mock_client.score.return_value = mock_score_result
        mock_revettr_cls.return_value = mock_client

        tool._run(domain="example.com")

        mock_revettr_cls.assert_called_once_with()


class TestErrorHandling:
    @patch("crewai_revettr.tools._build_client")
    def test_402_error(self, mock_build, tool, mock_client):
        mock_client.score.side_effect = Exception("402 Payment Required")
        mock_build.return_value = mock_client

        result = tool._run(domain="example.com")

        assert "Payment required" in result
        assert "REVETTR_WALLET_KEY" in result

    @patch("crewai_revettr.tools._build_client")
    def test_generic_error(self, mock_build, tool, mock_client):
        mock_client.score.side_effect = Exception("Connection refused")
        mock_build.return_value = mock_client

        result = tool._run(domain="example.com")

        assert "Error scoring counterparty" in result
        assert "Connection refused" in result
