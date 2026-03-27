"""Revettr counterparty risk scoring tool for CrewAI agents."""

from __future__ import annotations

import os
from typing import Any

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


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
        "screening. Accepts any combination of domain, IP, wallet address, or "
        "company name. Pricing: $0.01 USDC per score via x402 on Base."
    )
    args_schema: type[BaseModel] = RevettrScoreToolSchema

    def _run(
        self,
        domain: str | None = None,
        ip: str | None = None,
        wallet_address: str | None = None,
        chain: str = "base",
        company_name: str | None = None,
    ) -> str:
        if not any([domain, ip, wallet_address, company_name]):
            return (
                "Error: At least one identifier is required. "
                "Provide a domain, IP address, wallet address, or company name."
            )

        from revettr import Revettr

        wallet_key = os.getenv("REVETTR_WALLET_KEY")
        client_kwargs: dict[str, Any] = {}
        if wallet_key:
            client_kwargs["wallet_key"] = wallet_key

        client = Revettr(**client_kwargs)

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
