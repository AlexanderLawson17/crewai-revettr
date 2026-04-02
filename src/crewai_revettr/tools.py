"""Revettr counterparty risk scoring tools for CrewAI agents."""

from __future__ import annotations

import os
from typing import Any

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_client() -> Any:
    """Instantiate Revettr client, passing wallet key if available."""
    from revettr import Revettr

    wallet_key = os.getenv("REVETTR_WALLET_KEY")
    client_kwargs: dict[str, Any] = {}
    if wallet_key:
        client_kwargs["wallet_key"] = wallet_key
    return Revettr(**client_kwargs)


def _handle_error(e: Exception, action: str = "scoring counterparty") -> str:
    """Standard error formatting for all tools."""
    error_msg = str(e)
    if "402" in error_msg:
        return (
            f"Payment required: Set REVETTR_WALLET_KEY environment variable "
            f"with an EVM private key funded with USDC on Base. "
            f"Cost: $0.01 per score. Details: {error_msg}"
        )
    return f"Error {action}: {error_msg}"


# ---------------------------------------------------------------------------
# RevettrScoreTool
# ---------------------------------------------------------------------------

class RevettrScoreToolSchema(BaseModel):
    """Input schema for RevettrScoreTool."""

    domain: str | None = Field(
        None,
        description="Domain or URL of the counterparty (e.g., 'uniswap.org')",
    )
    ip: str | None = Field(
        None,
        description="IP address of the counterparty server",
    )
    wallet_address: str | None = Field(
        None,
        description="EVM wallet address (0x...)",
    )
    chain: str = Field(
        "base",
        description="Blockchain network for wallet analysis (default: 'base')",
    )
    company_name: str | None = Field(
        None,
        description="Legal name to screen against OFAC/EU/UN sanctions lists",
    )
    stellar_wallet: str | None = Field(
        None,
        description="Stellar wallet address (G...)",
    )
    email: str | None = Field(
        None,
        description="Email address associated with the counterparty",
    )
    amount: float | None = Field(
        None,
        description="Transaction amount in USD for risk-adjusted scoring",
    )


class RevettrScoreTool(BaseTool):
    """Score a counterparty before sending money using Revettr.

    Returns a risk score 0-100 with per-signal breakdown covering domain
    intelligence, IP reputation, wallet history, and sanctions screening.

    Use before any x402 payment or financial transaction in agentic commerce.
    Pricing: $0.01 USDC per score via x402 on Base. No API keys needed.
    """

    name: str = "Revettr Counterparty Risk Score"
    description: str = (
        "Score a counterparty 0-100 before sending payments in agentic commerce. "
        "Covers domain intelligence, IP reputation, wallet history, and sanctions "
        "screening. Accepts any combination of domain, IP, wallet address, stellar "
        "wallet, email, or company name. Pricing: $0.01 USDC per score via x402 on Base."
    )
    args_schema: type[BaseModel] = RevettrScoreToolSchema

    def _run(
        self,
        domain: str | None = None,
        ip: str | None = None,
        wallet_address: str | None = None,
        chain: str = "base",
        company_name: str | None = None,
        stellar_wallet: str | None = None,
        email: str | None = None,
        amount: float | None = None,
    ) -> str:
        if not any([domain, ip, wallet_address, company_name, stellar_wallet, email]):
            return (
                "Error: At least one identifier is required. "
                "Provide a domain, IP address, wallet address, stellar wallet, "
                "email, or company name."
            )

        try:
            client = _build_client()

            score_kwargs: dict[str, Any] = {}
            if domain:
                score_kwargs["domain"] = domain
            if ip:
                score_kwargs["ip"] = ip
            if wallet_address:
                score_kwargs["wallet_address"] = wallet_address
                score_kwargs["chain"] = chain
            if company_name:
                score_kwargs["company_name"] = company_name
            if stellar_wallet:
                score_kwargs["stellar_wallet"] = stellar_wallet
            if email:
                score_kwargs["email"] = email
            if amount is not None:
                score_kwargs["amount_usd"] = amount

            result = client.score(**score_kwargs)

            lines = [
                "Revettr Counterparty Risk Score",
                "=" * 40,
                f"Score: {result.score}/100",
                f"Tier: {result.tier}",
                f"Confidence: {result.confidence}",
            ]

            if hasattr(result, "flags") and result.flags:
                lines.append("\nFlags:")
                for flag in result.flags:
                    lines.append(f"  - {flag}")

            if hasattr(result, "signals") and result.signals:
                lines.append("\nSignal Breakdown:")
                for signal in result.signals:
                    name = getattr(signal, "name", str(signal))
                    score = getattr(signal, "score", "N/A")
                    lines.append(f"  {name}: {score}")

            return "\n".join(lines)

        except Exception as e:
            return _handle_error(e, "scoring counterparty")


# ---------------------------------------------------------------------------
# RevettrIsSafeTool
# ---------------------------------------------------------------------------

class RevettrIsSafeToolSchema(BaseModel):
    """Input schema for RevettrIsSafeTool."""

    wallet_address: str = Field(
        ...,
        description="EVM or Stellar wallet address to check",
    )
    chain: str = Field(
        "base",
        description="Blockchain network (default: 'base')",
    )
    amount_usd: float | None = Field(
        None,
        description="Transaction amount in USD for risk-adjusted gating",
    )
    min_score: int = Field(
        60,
        description="Minimum acceptable score to consider safe (default: 60)",
    )


class RevettrIsSafeTool(BaseTool):
    """Quick boolean gate: is this wallet safe to transact with?

    Returns safe/unsafe verdict with score and any blocking flags.
    Use as a lightweight go/no-go check before executing a transaction.
    """

    name: str = "Revettr Is Safe To Transact"
    description: str = (
        "Quick go/no-go check on a wallet before transacting. Returns safe (bool), "
        "score, and blocking flags. Use for automated transaction gating."
    )
    args_schema: type[BaseModel] = RevettrIsSafeToolSchema

    def _run(
        self,
        wallet_address: str,
        chain: str = "base",
        amount_usd: float | None = None,
        min_score: int = 60,
    ) -> str:
        try:
            client = _build_client()

            kwargs: dict[str, Any] = {
                "wallet_address": wallet_address,
                "chain": chain,
                "min_score": min_score,
            }
            if amount_usd is not None:
                kwargs["amount_usd"] = amount_usd

            result = client.is_safe_to_transact(**kwargs)

            safe_label = "SAFE" if result["safe"] else "BLOCKED"
            lines = [
                f"Revettr Transaction Safety: {safe_label}",
                "=" * 40,
                f"Safe: {result['safe']}",
                f"Score: {result['score']}/100",
            ]

            if result.get("blocking_flags"):
                lines.append("\nBlocking Flags:")
                for flag in result["blocking_flags"]:
                    lines.append(f"  - {flag}")

            return "\n".join(lines)

        except Exception as e:
            return _handle_error(e, "checking transaction safety")


# ---------------------------------------------------------------------------
# RevettrExplainTool
# ---------------------------------------------------------------------------

class RevettrExplainToolSchema(BaseModel):
    """Input schema for RevettrExplainTool."""

    wallet_address: str | None = Field(
        None,
        description="EVM or Stellar wallet address",
    )
    chain: str = Field(
        "base",
        description="Blockchain network (default: 'base')",
    )
    domain: str | None = Field(
        None,
        description="Domain or URL of the counterparty",
    )
    ip: str | None = Field(
        None,
        description="IP address of the counterparty server",
    )
    company_name: str | None = Field(
        None,
        description="Legal name to screen against sanctions lists",
    )


class RevettrExplainTool(BaseTool):
    """Get a human-readable risk explanation for a counterparty.

    Returns a natural-language summary, list of risk factors,
    recommendation, score, and tier. Use to explain risk decisions
    to end users or for audit trails.
    """

    name: str = "Revettr Explain Risk"
    description: str = (
        "Get a human-readable risk explanation for a counterparty. Returns summary, "
        "risk factors, recommendation, score, and tier. Accepts wallet address, "
        "domain, IP, or company name."
    )
    args_schema: type[BaseModel] = RevettrExplainToolSchema

    def _run(
        self,
        wallet_address: str | None = None,
        chain: str = "base",
        domain: str | None = None,
        ip: str | None = None,
        company_name: str | None = None,
    ) -> str:
        if not any([wallet_address, domain, ip, company_name]):
            return (
                "Error: At least one identifier is required. "
                "Provide a wallet address, domain, IP, or company name."
            )

        try:
            client = _build_client()

            kwargs: dict[str, Any] = {}
            if wallet_address:
                kwargs["wallet_address"] = wallet_address
                kwargs["chain"] = chain
            if domain:
                kwargs["domain"] = domain
            if ip:
                kwargs["ip"] = ip
            if company_name:
                kwargs["company_name"] = company_name

            result = client.explain_risk(**kwargs)

            lines = [
                "Revettr Risk Explanation",
                "=" * 40,
                f"Score: {result['score']}/100",
                f"Tier: {result['tier']}",
                f"Recommendation: {result['recommendation']}",
                f"\nSummary: {result['summary']}",
            ]

            if result.get("risk_factors"):
                lines.append("\nRisk Factors:")
                for factor in result["risk_factors"]:
                    lines.append(f"  - {factor}")

            return "\n".join(lines)

        except Exception as e:
            return _handle_error(e, "explaining risk")


# ---------------------------------------------------------------------------
# RevettrHealthTool
# ---------------------------------------------------------------------------

class RevettrHealthTool(BaseTool):
    """Check Revettr API health status.

    Returns the current operational status of the Revettr scoring API.
    Use to verify connectivity before running batch scoring operations.
    """

    name: str = "Revettr Health Check"
    description: str = (
        "Check if the Revettr API is healthy and operational. "
        "No parameters required. Use before batch operations."
    )

    def _run(self) -> str:
        try:
            client = _build_client()
            result = client.health_check()

            lines = [
                "Revettr API Health",
                "=" * 40,
            ]
            for key, value in result.items():
                lines.append(f"{key}: {value}")

            return "\n".join(lines)

        except Exception as e:
            return _handle_error(e, "checking API health")
