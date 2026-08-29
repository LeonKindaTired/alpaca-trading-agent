from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA = """
CREATE TABLE IF NOT EXISTS decision_journal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    underlying TEXT,
    market_state TEXT,
    features TEXT,
    strategy_signal TEXT,
    ai_decision TEXT,
    ai_confidence REAL,
    ai_reasoning TEXT,
    risk_decision TEXT,
    execution TEXT,
    result TEXT
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    internal_id TEXT NOT NULL UNIQUE,
    alpaca_id TEXT,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    qty REAL NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    payload TEXT
);

CREATE TABLE IF NOT EXISTS system_status (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TEXT
);
"""


class Database:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def journal(
        self,
        *,
        underlying: str | None = None,
        market_state: Any = None,
        features: Any = None,
        strategy_signal: Any = None,
        ai_decision: str | None = None,
        ai_confidence: float | None = None,
        ai_reasoning: str | None = None,
        risk_decision: Any = None,
        execution: Any = None,
        result: Any = None,
    ) -> int:
        cur = self._conn.execute(
            """
            INSERT INTO decision_journal (
                timestamp, underlying, market_state, features, strategy_signal,
                ai_decision, ai_confidence, ai_reasoning, risk_decision, execution, result
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                underlying,
                _dump(market_state),
                _dump(features),
                _dump(strategy_signal),
                ai_decision,
                ai_confidence,
                ai_reasoning,
                _dump(risk_decision),
                _dump(execution),
                _dump(result),
            ),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def set_system_status(self, key: str, value: Any) -> None:
        """Set a system status key-value pair."""
        self._conn.execute(
            """
            INSERT OR REPLACE INTO system_status (key, value, updated_at)
            VALUES (?, ?, ?)
            """,
            (key, _dump(value), datetime.now(timezone.utc).isoformat()),
        )
        self._conn.commit()

    def get_system_status(self, key: str) -> Any:
        """Get a system status value by key."""
        row = self._conn.execute(
            "SELECT value FROM system_status WHERE key = ?",
            (key,),
        ).fetchone()
        if row is None:
            return None
        try:
            return json.loads(row[0])
        except (json.JSONDecodeError, TypeError):
            return row[0]

    def record_order(
        self,
        *,
        internal_id: str,
        alpaca_id: str | None,
        symbol: str,
        side: str,
        qty: float,
        status: str,
        payload: Any = None,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO orders (internal_id, alpaca_id, symbol, side, qty, status, created_at, payload)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                internal_id,
                alpaca_id,
                symbol,
                side,
                qty,
                status,
                datetime.now(timezone.utc).isoformat(),
                _dump(payload),
            ),
        )
        self._conn.commit()

    def has_open_order(self, symbol: str) -> bool:
        row = self._conn.execute(
            """
            SELECT 1 FROM orders
            WHERE symbol = ? AND status IN ('submitted', 'accepted', 'pending_new', 'new', 'partially_filled')
            LIMIT 1
            """,
            (symbol,),
        ).fetchone()
        return row is not None

    def close(self) -> None:
        self._conn.close()


def _dump(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return json.dumps(value.model_dump(mode="json"), default=str)
    if isinstance(value, (dict, list)):
        return json.dumps(value, default=str)
    return json.dumps(value, default=str)