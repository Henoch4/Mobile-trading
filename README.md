# MobileTrading — TARS on Celo

**Mobile-first AI trading agent on Celo that sells ensemble market analysis for USDC via x402.**

TARS (Trade Audit & Risk System) retargeted for the [Celo Agents at Work Hackathon](https://celoplatform.notion.site/Agents-at-Work-Hackathon-3c1d5cb803de81139de7f4f3d09e55dc) — **Track 2: Real World Adoption (Best Stablecoin Adoption)**.

## What it does

The agent runs a multi-strategy signal engine (mean reversion + momentum + funding carry, combined by weighted ensemble vote) and **sells each analysis for $0.01 USDC on Celo mainnet** via the [x402 protocol](https://www.x402.org):

- `GET /api/v1/analysis` — paywalled with x402: clients pay USDC on Celo (`eip155:42220`) through the hosted facilitator (`api.x402.celo.org`); settlement is gas-sponsored (EIP-3009). Free in demo mode when the paywall is inert.
- `GET /api/v1/celo-status` — live paywall/chain configuration.
- Telegram bot (`telegram_bot.py`) — distribution channel: `/analysis`, `/status`.

## Celo configuration

| Setting | Value |
|---|---|
| Network | Celo Mainnet (`eip155:42220`) |
| RPC | `https://forno.celo.org` |
| USDC | `0xcEBA9300f2b948710d2653dD7B07f33A8B32118C` |
| Facilitator | `https://api.x402.celo.org` |
| Price | `10000` atomics = $0.01 USDC |

Copy `.env.example` to `.env` and set `PAY_TO_ADDRESS` (your USDC receiving wallet) to activate the paywall. Set `CELO_BUILDER_CODE` to your ERC-8021 attribution tag so transactions earn leaderboard credit.

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env   # then fill in PAY_TO_ADDRESS, TELEGRAM_BOT_TOKEN, etc.

# API server
python -m uvicorn src.main:app --port 8000

# Telegram bot (needs TELEGRAM_BOT_TOKEN, calls the API on localhost:8000)
python telegram_bot.py

# Tests
python -m pytest tests/test_celo_retarget.py -q
```

## Architecture

```
Market Data → Signal Agents (mean reversion / momentum / funding)
                     ↓
              Ensemble (weighted vote)
                     ↓
   Risk Gate (non-overridable limits) → Analysis payload
                     ↓
        x402 paywall → USDC settlement on Celo
```

Safety posture carried over from TARS: hard pre-trade risk gate the agent cannot override, kill switch, position/daily-loss caps, fat-finger checks, onchain audit trail.

## Safety / risk

- Risk gate limits are non-overridable by the agent and can only be tightened.
- Dry-run by default (`DRY_RUN=true`); exchange credentials stay blank for demo mode.
- Testnet activity counts for nothing in the hackathon — all x402 settlement is Celo mainnet.

## License

MIT
