"""Celo chain constants for the Agents at Work hackathon.

Celo mainnet is the only chain that counts for the leaderboard — testnet
activity is ignored. These defaults are used when CELO_* env vars are not set.

References:
  - Celo mainnet chainId 42220 / CAIP-2 eip155:42220
  - Celo Sepolia testnet chainId 11142220
  - Forno RPC https://forno.celo.org
  - Celo hosted x402 facilitator https://api.x402.celo.org (mainnet)
  - USDC on Celo mainnet 0xcEBA9300f2b948710d2653dD7B07f33A8B32118C (6 decimals)
  - docs.celo.org/build-on-celo/build-with-ai/x402
"""
from __future__ import annotations

import os

CELO_MAINNET_CHAIN_ID: int = 42220
CELO_SEPOLIA_CHAIN_ID: int = 11142220
CELO_MAINNET_CAIP2: str = f"eip155:{CELO_MAINNET_CHAIN_ID}"
CELO_SEPOLIA_CAIP2: str = f"eip155:{CELO_SEPOLIA_CHAIN_ID}"

CELO_MAINNET_RPC: str = "https://forno.celo.org"
CELO_SEPOLIA_RPC: str = "https://forno.celo-sepolia.celo-testnet.org"

# Celo mainnet USDC (6 decimals) — used for x402 ExactEvmScheme price.
# From docs.celo.org x402 page; verified on celoscan.io
CELO_USDC_MAINNET: str = "0xcEBA9300f2b948710d2653dD7B07f33A8B32118C"
CELO_USDC_SEPOLIA: str = "0x01C5C0122039549AD1493B8220cABEdD739BC44E"

# Track 2 stablecoin set (Real World Adoption — Best Stablecoin Adoption sub-track)
# includes cNGN, Ripio wFIAT, USDT settled over x402. USDC is the primary
# settlement asset for the paywall; others are documented for extendability.
CELO_USDT_MAINNET: str = "0x48065fbBE25f71C9282ddf5e1cD05E8f6B02086"
CELO_CNGN_MAINNET: str = "0x1af3f2421d7c9ffd30521c6c0f446b32688b7284"

# Hosted facilitator endpoints (dashboard at x402.celo.org is NOT the facilitator)
CELO_FACILITATOR_MAINNET: str = "https://api.x402.celo.org"
CELO_FACILITATOR_SEPOLIA: str = "https://api.x402.sepolia.celo.org"

# Default price for the paid analysis endpoint: $0.01 in USDC (6 decimals => 10000)
# Zero means the paywall is inert (Phase 1 behaviour) — no 402s emitted.
DEFAULT_ANALYSIS_PRICE_USDC_ATOMICS: str = "10000"  # $0.01

# Human-readable alias for 1 USDC in atomics
USDC_DECIMALS: int = 6


def celo_chain_id() -> int:
    return int(os.getenv("CELO_CHAIN_ID", str(CELO_MAINNET_CHAIN_ID)))


def celo_rpc_url() -> str:
    return os.getenv("CELO_RPC_URL", CELO_MAINNET_RPC).strip()


def celo_facilitator_url() -> str:
    """Facilitator URL — prefer explicit X402_FACILITATOR_URL, then CELO_FACILITATOR_URL."""
    return (
        os.getenv("X402_FACILITATOR_URL", "").strip()
        or os.getenv("CELO_FACILITATOR_URL", "").strip()
        or CELO_FACILITATOR_MAINNET
    )


def celo_usdc_address() -> str:
    return os.getenv("CELO_USDC_ADDRESS", CELO_USDC_MAINNET).strip()


def celo_caip2() -> str:
    """CAIP-2 network identifier for the configured Celo chain."""
    return f"eip155:{celo_chain_id()}"
