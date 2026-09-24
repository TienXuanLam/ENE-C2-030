"""AGENTIC STAR Marketplace entrypoint for ENE-C2-030."""

from pathlib import Path
from typing import Any

from framework.utils.config_loader import load_agent_config
from shared.bootstrap.marketplace_app import run_agent_marketplace

from src.graph.graph import HydrogenSupplyChainComplianceDocAgent

extend_config: dict[str, Any] = {}

if __name__ == "__main__":
    run_agent_marketplace(
        HydrogenSupplyChainComplianceDocAgent,
        agent_name="ENE-C2-030",
        namespace="ene",
        config={**load_agent_config(Path(__file__).resolve().parent), **extend_config},
    )
