"""Regression tests for the Celo retarget (Agents at Work hackathon).

Covers:
  - Celo chain constants (chainId 42220, USDC, facilitator) match docs.celo.org.
  - Attribution helper (ERC-8021) encode/decode.
  - Paid analysis endpoint GET /api/v1/analysis (free when paywall inert) returns
    well-formed per-asset signals and does not execute trades.
  - Celo status endpoint GET /api/v1/celo-status reflects configured wiring.
  - x402 paywall is inert when PAY_TO_ADDRESS is empty (no 402s).

The x402 middleware is not exercised with a real facilitator here — that is an
integration test (requires CELO_RPC_URL + X402_API_KEY + funded wallet). These
tests guard the wiring that would otherwise silently regress (e.g. reintroducing
eip155:196, dropping the Celo USDC address, or breaking the analysis endpoint).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def test_celo_config_constants():
    from src.celo_config import (
        CELO_MAINNET_CHAIN_ID,
        CELO_MAINNET_CAIP2,
        CELO_MAINNET_RPC,
        CELO_FACILITATOR_MAINNET,
        CELO_USDC_MAINNET,
        USDC_DECIMALS,
    )

    assert CELO_MAINNET_CHAIN_ID == 42220
    assert CELO_MAINNET_CAIP2 == "eip155:42220"
    assert CELO_MAINNET_RPC == "https://forno.celo.org"
    assert CELO_FACILITATOR_MAINNET == "https://api.x402.celo.org"
    assert CELO_USDC_MAINNET == "0xcEBA9300f2b948710d2653dD7B07f33A8B32118C"
    assert USDC_DECIMALS == 6


def test_celo_config_helpers_default_to_mainnet(monkeypatch):
    monkeypatch.delenv("CELO_CHAIN_ID", raising=False)
    monkeypatch.delenv("CELO_RPC_URL", raising=False)
    monkeypatch.delenv("X402_FACILITATOR_URL", raising=False)
    monkeypatch.delenv("CELO_FACILITATOR_URL", raising=False)
    from src.celo_config import celo_chain_id, celo_rpc_url, celo_facilitator_url, celo_caip2

    assert celo_chain_id() == 42220
    assert celo_rpc_url() == "https://forno.celo.org"
    assert celo_facilitator_url() == "https://api.x402.celo.org"
    assert celo_caip2() == "eip155:42220"


def test_celo_config_helpers_respect_env(monkeypatch):
    monkeypatch.setenv("CELO_CHAIN_ID", "11142220")
    monkeypatch.setenv("CELO_RPC_URL", "https://forno.celo-sepolia.celo-testnet.org")
    monkeypatch.setenv("X402_FACILITATOR_URL", "https://api.x402.sepolia.celo.org")
    from src.celo_config import celo_chain_id, celo_rpc_url, celo_facilitator_url, celo_caip2

    assert celo_chain_id() == 11142220
    assert "sepolia" in celo_rpc_url().lower()
    assert "sepolia" in celo_facilitator_url().lower()
    assert celo_caip2() == "eip155:11142220"


def test_attribution_encode_decode_roundtrip():
    from src.attribution import to_data_suffix, from_data_suffix

    suffix = to_data_suffix("celo_abc12345")
    assert suffix.startswith("0x02174df3")
    decoded = from_data_suffix(suffix)
    assert decoded is not None
    assert "celo_abc12345" in decoded["codes"]


def test_attribution_multi_code():
    from src.attribution import to_data_suffix, from_data_suffix

    suffix = to_data_suffix(["celo_abc12345", "my_app"])
    decoded = from_data_suffix(suffix)
    assert decoded is not None
    assert decoded["codes"] == ["celo_abc12345", "my_app"]


def test_attribution_from_data_suffix_rejects_non_tag():
    from src.attribution import from_data_suffix

    assert from_data_suffix("0x1234567890") is None
    assert from_data_suffix("") is None
    assert from_data_suffix("0x") is None


def test_attribution_tag_reads_env(monkeypatch):
    monkeypatch.setenv("CELO_BUILDER_CODE", "celo_testtag1")
    monkeypatch.delenv("BUILDER_CODE", raising=False)
    from src.attribution import attribution_tag

    assert attribution_tag() == "celo_testtag1"


def test_attribution_tag_falls_back_to_builder_code(monkeypatch):
    monkeypatch.delenv("CELO_BUILDER_CODE", raising=False)
    monkeypatch.setenv("BUILDER_CODE", "celo_fallback1")
    from src.attribution import attribution_tag

    assert attribution_tag() == "celo_fallback1"


def test_attribution_tag_none_when_unset(monkeypatch):
    monkeypatch.delenv("CELO_BUILDER_CODE", raising=False)
    monkeypatch.delenv("BUILDER_CODE", raising=False)
    from src.attribution import attribution_tag

    assert attribution_tag() is None


def test_analysis_endpoint_free_mode_returns_signals():
    """GET /api/v1/analysis is free when PAY_TO_ADDRESS is empty (default in CI)."""
    from src.main import app

    client = TestClient(app)
    resp = client.get("/api/v1/analysis?assets=BTC-USDT-SWAP")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "signals" in data
    assert isinstance(data["signals"], list)
    assert len(data["signals"]) == 1
    sig = data["signals"][0]
    assert sig["asset"] == "BTC-USDT-SWAP"
    assert sig["direction"] in ("LONG", "SHORT", "NEUTRAL")
    assert "confidence_bps" in sig
    assert "confidence" in sig
    assert "rationale" in sig


def test_analysis_endpoint_default_assets():
    from src.main import app

    client = TestClient(app)
    resp = client.get("/api/v1/analysis")
    assert resp.status_code == 200
    data = resp.json()
    # Default is _ALLOWED_ASSETS (4 assets)
    assert len(data["signals"]) == 4
    assert data["disclaimer"] is not None


def test_analysis_endpoint_rejects_invalid_assets():
    from src.main import app

    client = TestClient(app)
    resp = client.get("/api/v1/analysis?assets=FAKE-XXX")
    assert resp.status_code == 400


def test_analysis_endpoint_filters_to_allowed():
    from src.main import app

    client = TestClient(app)
    resp = client.get("/api/v1/analysis?assets=BTC-USDT-SWAP,FAKE-XXX,ETH-USDT-SWAP")
    assert resp.status_code == 200
    data = resp.json()
    assets = {s["asset"] for s in data["signals"]}
    assert assets == {"BTC-USDT-SWAP", "ETH-USDT-SWAP"}


def test_celo_status_endpoint():
    from src.main import app

    client = TestClient(app)
    resp = client.get("/api/v1/celo-status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["chain"] == "celo"
    assert data["chain_id"] == 42220
    assert data["caip2"] == "eip155:42220"
    assert "forno.celo.org" in data["rpc_url"]
    assert "api.x402.celo.org" in data["facilitator_url"]
    assert data["usdc_address"].lower() == "0xcEBA9300f2b948710d2653dD7B07f33A8B32118C".lower()
    assert "paywall_active" in data
    assert "x402_available" in data


def test_celo_status_reflects_builder_code(monkeypatch):
    monkeypatch.setenv("CELO_BUILDER_CODE", "celo_mystatus1")
    from src.main import app
    from src.attribution import attribution_tag

    # Re-read via attribution helper (main's celo-status reads same env at request time)
    assert attribution_tag() == "celo_mystatus1"
    client = TestClient(app)
    resp = client.get("/api/v1/celo-status")
    assert resp.status_code == 200
    assert resp.json()["builder_code"] == "celo_mystatus1"


def test_main_does_not_register_x_layer_x402_network():
    """Celo retarget must not register the old eip155:196 X Layer network for x402."""
    import pathlib

    main_text = pathlib.Path("src/main.py").read_text(encoding="utf-8")
    # The old hard-coded X Layer x402 network must be gone from the wiring.
    assert 'eip155:196' not in main_text, "src/main.py still registers eip155:196 — should be eip155:42220"
    assert '_celo_network' in main_text
    assert 'CELO_CHAIN_ID' in main_text or 'celo_chain_id' in main_text.lower()


def test_main_x402_wiring_uses_celo_facilitator():
    import pathlib

    main_text = pathlib.Path("src/main.py").read_text(encoding="utf-8")
    assert "api.x402.celo.org" in main_text
    assert "X402_FACILITATOR_URL" in main_text or "CELO_FACILITATOR_URL" in main_text


def test_manifest_declares_celo_chain():
    import json
    import pathlib

    manifest = json.loads(pathlib.Path("manifest.json").read_text(encoding="utf-8"))
    assert manifest["chain"] == "celo"
    assert manifest["celo_chain_id"] == 42220
    assert manifest["celo_caip2"] == "eip155:42220"
    assert "paid_analysis_celo_x402" in manifest["capabilities"]
    assert manifest["paid_endpoint"] == "/api/v1/analysis"


def test_manifest_lists_new_endpoints():
    import json
    import pathlib

    manifest = json.loads(pathlib.Path("manifest.json").read_text(encoding="utf-8"))
    paths = {(e["path"], e["method"]) for e in manifest["endpoints"]}
    assert ("/api/v1/analysis", "GET") in paths
    assert ("/api/v1/celo-status", "GET") in paths
