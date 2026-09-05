"""Simple Telegram bot for MobileTrading — sells TARS ensemble analysis via x402 on Celo.

Commands:
  /start       - Welcome message
  /analysis    - Get paid trading analysis (USDC on Celo via x402)
  /status      - Check paywall status and configuration
"""

import os
import asyncio
import aiohttp
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN must be set in .env")

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# MobileTrading API base (same host when deployed to Vercel, or localhost when local)
MOBILE_TRADING_BASE = os.getenv(
    "MOBILE_TRADING_BASE",
    "http://localhost:8000",
)


async def telegram_api(method: str, json_data: dict) -> dict:
    """Make a request to the Telegram Bot API."""
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{BASE_URL}/{method}", json=json_data) as resp:
            data = await resp.json()
            if not resp.status == 200 or not data.get("ok"):
                raise Exception(f"Telegram API error: {data}")
            return data["result"]


async def send_telegram_message(chat_id: int, text: str, parse_mode: str = "Markdown") -> None:
    """Send a message to a Telegram chat."""
    await telegram_api("sendMessage", {"chat_id": chat_id, "text": text, "parse_mode": parse_mode})


async def get_update_offset(offset: Optional[int] = None) -> int:
    """Get updates from Telegram; returns the highest update_id."""
    async with aiohttp.ClientSession() as session:
        params = {"offset": offset} if offset else {}
        async with session.get(f"{BASE_URL}/getUpdates", params=params) as resp:
            data = await resp.json()
            result = data.get("result", [])
            if result:
                return result[-1]["update_id"] + 1
            return offset or 1


async def fetch_analysis(assets: str = "") -> dict:
    """Call the MobileTrading /api/v1/analysis endpoint."""
    url = f"{MOBILE_TRADING_BASE}/api/v1/analysis"
    params = {}
    if assets:
        params["assets"] = assets
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                return {"error": f"API returned {resp.status}"}


async def handle_update(update: dict) -> None:
    """Process a single Telegram update."""
    message = update.get("message", {})
    if not message:
        return

    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")
    user = message.get("from", {})

    if not chat_id:
        return

    # Commands
    if text.startswith("/"):
        parts = text.split()
        cmd = parts[0].lower()

        if cmd == "/start" or cmd == "/help":
            await send_telegram_message(
                chat_id,
                "🤖 *MobileTrading Bot*\n\n"
                "I sell TARS ensemble trading analysis for USDC on Celo.\n"
                "Use `/analysis` to get market signals (paid via x402).\n"
                "Use `/status` to check paywall status.",
            )

        elif cmd == "/analysis":
            # Optional: ask which assets, or use defaults
            assets = ",".join(["BTC-USDT-SWAP", "ETH-USDT-SWAP"]) if not parts[1:] else ",".join(parts[1:])
            result = await fetch_analysis(assets)

            if "error" in result:
                await send_telegram_message(chat_id, f"❌ Error: {result['error']}")
                return

            # Format response
            paid_text = "💳 *Paid via x402 on Celo* " if result.get("paid_via") == "x402 on Celo" else "🆓 *Free (paywall inactive)* "
            network_text = f"\n🌐 Network: {result.get('network', 'N/A')}"
            price_text = f"\n💰 Price: {result.get('price_atom', 'N/A')} atomics USDC"

            lines = [f"📊 *TARS Ensemble Analysis*{network_text}{price_text}"]

            for signal in result.get("signals", []):
                direction = signal.get("direction", "NEUTRAL")
                confidence = signal.get("confidence", 0)
                confidence_pct = confidence / 100.0 if confidence else 0.0
                rationale = signal.get("rationale", "")
                asset = signal.get("asset", "UNKNOWN")

                dir_emoji = "🟢" if direction == "LONG" else "🔴" if direction == "SHORT" else "⚪"
                lines.append(
                    f"\n{dir_emoji} *{asset}*\n"
                    f"   Direction: {direction}\n"
                    f"   Confidence: {confidence_pct:.1%} ({confidence} bps)\n"
                    f"   Rationale: {rationale}"
                )

            await send_telegram_message(chat_id, "\n".join(lines), parse_mode="Markdown")

        elif cmd == "/status":
            # Call the celo-status endpoint
            status_url = f"{MOBILE_TRADING_BASE}/api/v1/celo-status"
            async with aiohttp.ClientSession() as session:
                async with session.get(status_url) as resp:
                    status = await resp.json()

            paywall = status.get("paywall_active", False)
            lines = [
                "📡 *MobileTrading Paywall Status*",
                f"\n🌐 Chain: {status.get('chain', 'N/A')}",
                f"🔢 Chain ID: {status.get('chain_id', 'N/A')}",
                f"💳 Pay-to: {status.get('pay_to', 'Not set') or 'Not configured'}",
                f"🔐 Paywall: {'🟢 Active' if paywall else '🔴 Inactive'}",
                f"💰 Price: {status.get('price_atom', 'N/A')} atomics USDC (=$0.01 if active)",
                f"🏷️ Builder code: {status.get('builder_code', 'Not set')}",
                f"🔧 x402 available: {'🟢 Yes' if status.get('x402_available') else '🔴 No'}",
            ]

            if paywall:
                lines.insert(2, "⚠️ *Paywall is active - users must pay via x402 to access analysis*")
            else:
                lines.insert(2, "ℹ️ *Paywall is inactive - set PAY_TO_ADDRESS to enable*")

            await send_telegram_message(chat_id, "\n".join(lines), parse_mode="Markdown")

        else:
            await send_telegram_message(chat_id, f"❓ Unknown command: {cmd}\nUse /start, /analysis, or /status.")


async def bot_polling() -> None:
    """Main bot polling loop."""
    offset = None
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                params = {"offset": offset} if offset else {}
                async with session.get(f"{BASE_URL}/getUpdates", params=params) as resp:
                    data = await resp.json()

            updates = data.get("result", [])
            for update in updates:
                offset = update["update_id"] + 1
                await handle_update(update)

            if not updates:
                await asyncio.sleep(1)  # No new updates, wait a bit
            else:
                await asyncio.sleep(0.5) # Small delay after processing

        except Exception as e:
            print(f"Bot polling error: {e}")
            await asyncio.sleep(5)  # Back off on error


if __name__ == "__main__":
    print("🤖 Starting MobileTrading Telegram Bot...")
    asyncio.run(bot_polling())