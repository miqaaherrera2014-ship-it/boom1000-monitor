#!/usr/bin/env python3
"""Publishable, public-market-data-only snapshot of Deriv Boom 1000 Index.

No trading, no private user credentials. No made-up prices. On failure leaves
previous good snapshot untouched; readers must validate generated_at and tick age.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import websockets

PRIMARY = "wss://api.derivws.com/trading/v1/options/ws/public"
LEGACY = "wss://ws.derivws.com/websockets/v3?app_id=1089"
ENDPOINTS = (PRIMARY, LEGACY)
PERIODS = {"H1": (3600, 140), "H4": (14400, 140), "D1": (86400, 140)}
OUTPUT = Path(__file__).resolve().parents[1] / "docs" / "data" / "latest.json"


def utc_iso(epoch: int | float) -> str:
    return datetime.fromtimestamp(int(epoch), tz=timezone.utc).isoformat().replace("+00:00", "Z")


def choose_boom1000(items: list[dict[str, Any]]) -> tuple[str, str]:
    """Reject confusingly similar indices (Boom 100, 500, 1000 1s, etc.)."""
    for item in items:
        label = (item.get("underlying_symbol_name") or item.get("display_name") or item.get("name") or "").strip()
        label = re.sub(r"\s+", " ", label)
        # Exact name only: no Boom 1000 (1s), Crash 1000, Boom 500.
        if re.fullmatch(r"Boom 1000 Index", label, flags=re.I):
            symbol = item.get("underlying_symbol") or item.get("symbol")
            if symbol and re.fullmatch(r"[A-Za-z0-9_]{2,30}", symbol):
                return symbol, label
    raise ValueError("El listado activo no contiene una entrada inequívoca de Boom 1000 Index")


def clean_candles(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_time = {}
    for r in items:
        ts = int(r["epoch"])
        o, h, l, c = (float(r[k]) for k in ("open", "high", "low", "close"))
        if not (l <= min(o, c) <= max(o, c) <= h):
            raise ValueError(f"OHLC inconsistente en {ts}")
        by_time[ts] = {"epoch": ts, "open": o, "high": h, "low": l, "close": c}
    return [by_time[k] for k in sorted(by_time)]


async def request(ws: Any, payload: dict, target_type: str, timeout: int = 18) -> dict:
    req_id = payload["req_id"]
    await ws.send(json.dumps(payload))
    while True:
        raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
        msg = json.loads(raw)
        if msg.get("error"):
            if msg.get("req_id") == req_id:
                error = msg["error"]
                raise RuntimeError(f"{error.get('code', 'API')} — {error.get('message', error)}")
            continue
        if msg.get("req_id") == req_id and msg.get("msg_type") == target_type:
            return msg


async def fetch_endpoint(endpoint: str) -> dict:
    async with websockets.connect(endpoint, open_timeout=18, close_timeout=6, ping_interval=20, max_size=5_000_000) as ws:
        active = await request(ws, {"active_symbols": "brief", "req_id": 100}, "active_symbols")
        symbol, display_name = choose_boom1000(active.get("active_symbols") or [])

        periods = {}
        for idx, (key, (granularity, count)) in enumerate(PERIODS.items()):
            msg = await request(ws, {
                "ticks_history": symbol,
                "style": "candles", "granularity": granularity,
                "count": count, "end": "latest", "req_id": 200 + idx,
            }, "candles")
            candles = clean_candles(msg.get("candles") or [])
            if len(candles) < 10:
                raise RuntimeError(f"Solo {len(candles)} velas en {key}")
            periods[key] = candles

        tick = None
        tick_error = None
        try:
            msg = await request(ws, {"ticks": symbol, "subscribe": 1, "req_id": 300}, "tick", timeout=9)
            td = msg.get("tick") or {}
            if "quote" in td and "epoch" in td:
                tick = {"price": float(td["quote"]), "epoch": int(td["epoch"]), "utc": utc_iso(td["epoch"])}
                # The public tick feed is the source of current price, not candle close.
        except Exception as e:
            tick_error = str(e)

        now = datetime.now(timezone.utc)
        snapshot = {
            "schema_version": 1,
            "instrument": "Boom 1000 Index",
            "symbol": symbol,
            "api_instrument_name": display_name,
            "source": "Deriv API / active_symbols, ticks_history, ticks",
            "websocket_endpoint": endpoint,
            "generated_at": now.isoformat().replace("+00:00", "Z"),
            "generated_epoch": int(now.timestamp()),
            "last_tick": tick,
            "tick_delay_seconds": int(now.timestamp()) - tick["epoch"] if tick else None,
            "tick_error": tick_error,
            "candles": periods,
            "notes": "D1, H4 y H1 son velas UTC. La última vela de cada marco puede seguir abierta; no asumir cierre confirmado.",
            "trade_execution": False,
        }
        # The API may return a valid historical tick; do not claim it is live.
        if tick and (snapshot["tick_delay_seconds"] < 0 or snapshot["tick_delay_seconds"] > 600):
            snapshot["tick_error"] = "El tick devuelto no es suficientemente reciente"
        return snapshot


async def run() -> dict:
    failures = []
    for endpoint in ENDPOINTS:
        try:
            return await fetch_endpoint(endpoint)
        except Exception as e:
            failures.append(f"{endpoint}: {type(e).__name__}: {e}")
    raise RuntimeError("Sin datos Deriv verificados. " + " | ".join(failures))


def main():
    try:
        snap = asyncio.run(run())
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        tmp = OUTPUT.with_suffix(".tmp")
        tmp.write_text(json.dumps(snap, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        os.replace(tmp, OUTPUT)
        print(f"OK: {snap['instrument']} ({snap['symbol']}), last_tick={snap['last_tick']}, snapshot={snap['generated_at']}")
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
