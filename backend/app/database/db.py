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

CREATE TABLE IF NOT EXISTS agent_config (
    config_id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    parameter_values TEXT NOT NULL,  -- JSON string of the configuration
    active BOOLEAN NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS agent_config_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_id INTEGER NOT NULL,
    changed_at TEXT NOT NULL,
    changed_by TEXT NOT NULL,  -- e.g., 'dashboard', 'user'
    changes TEXT NOT NULL,     -- JSON string of the changes
    FOREIGN KEY (config_id) REFERENCES agent_config (config_id)
);
"""


class Database:
    def __init__(self, path: str, settings: Settings | None = None) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        self._conn.commit()
        # Initialize agent configuration from settings if provided and no active config exists
        if settings is not None:
            self.initialize_agent_config_from_settings(settings)

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

    def set_agent_config(self, parameter_values: dict, changed_by: str = "system") -> int:
        """Store a new agent configuration, set it as active, and record the change.

        Args:
            parameter_values: Dictionary of configuration parameters.
            changed_by: Entity that made the change (default: "system").

        Returns:
            The config_id of the new configuration.
        """
        # Deactivate any existing active configuration
        self._conn.execute(
            "UPDATE agent_config SET active = 0 WHERE active = 1"
        )

        # Insert new configuration
        created_at = datetime.now(timezone.utc).isoformat()
        updated_at = created_at
        parameter_values_json = json.dumps(parameter_values, default=str)

        cursor = self._conn.execute(
            """
            INSERT INTO agent_config (created_at, updated_at, parameter_values, active)
            VALUES (?, ?, ?, 1)
            """,
            (created_at, updated_at, parameter_values_json)
        )
        config_id = cursor.lastrowid

        # Record in history (this is the initial creation)
        changes_json = json.dumps({"initial": parameter_values}, default=str)
        self._conn.execute(
            """
            INSERT INTO agent_config_history (config_id, changed_at, changed_by, changes)
            VALUES (?, ?, ?, ?)
            """,
            (config_id, created_at, changed_by, changes_json)
        )

        self._conn.commit()
        return config_id

    def get_active_agent_config(self) -> dict | None:
        """Get the currently active agent configuration.

        Returns:
            Dictionary of configuration parameters, or None if no active configuration.
        """
        row = self._conn.execute(
            """
            SELECT parameter_values FROM agent_config
            WHERE active = 1
            ORDER BY updated_at DESC
            LIMIT 1
            """
        ).fetchone()
        if row is None:
            return None
        try:
            return json.loads(row[0])
        except (json.JSONDecodeError, TypeError):
            return None

    def get_agent_config_history(self, limit: int = 10) -> list[dict]:
        """Get the history of agent configuration changes.

        Args:
            limit: Maximum number of history records to return.

        Returns:
            List of dictionaries, each containing config_id, changed_at, changed_by, and changes.
        """
        rows = self._conn.execute(
            """
            SELECT ach.history_id, ach.config_id, ach.changed_at, ach.changed_by, ach.changes,
                   ac.parameter_values
            FROM agent_config_history ach
            JOIN agent_config ac ON ach.config_id = ac.config_id
            ORDER BY ach.changed_at DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()

        history = []
        for row in rows:
            try:
                changes = json.loads(row[4])  # changes column
                parameter_values = json.loads(row[5])  # parameter_values from joined config
                history.append({
                    "history_id": row[0],
                    "config_id": row[1],
                    "changed_at": row[2],
                    "changed_by": row[3],
                    "changes": changes,
                    "parameter_values": parameter_values
                })
            except (json.JSONDecodeError, TypeError):
                # Skip if JSON parsing fails
                continue
        return history

    def initialize_agent_config_from_settings(self, settings) -> int:
        """Initialize the agent configuration from the current settings if no active config exists.

        Returns:
            The config_id of the initialized configuration, or None if already initialized.
        """
        # Check if there's already an active configuration
        active_config = self.get_active_agent_config()
        if active_config is not None:
            return None  # Already initialized

        # Convert settings object to a dictionary
        # We'll extract the relevant settings for the agent configuration
        parameter_values = {
            # Trading parameters
            "trading_enabled": settings.trading_enabled,
            "max_risk_per_trade": settings.max_risk_per_trade,
            "max_portfolio_exposure": settings.max_portfolio_exposure,
            "max_daily_loss": settings.max_daily_loss,
            "max_drawdown": settings.max_drawdown,
            "max_positions": settings.max_positions,
            "max_underlying_concentration": settings.max_underlying_concentration,
            "max_bid_ask_spread": settings.max_bid_ask_spread,
            "min_option_volume": settings.min_option_volume,
            "min_open_interest": settings.min_open_interest,
            "min_dte": settings.min_dte,
            "max_dte": settings.max_dte,
            "loop_interval_seconds": settings.loop_interval_seconds,
            "max_consecutive_failures": settings.max_consecutive_failures,
            # Underlyings
            "underlyings": settings.underlyings,
            # AI parameters
            "ai_enabled": settings.ai_enabled,
            "use_ai_supervisor": settings.use_ai_supervisor,
            "ai_temperature": settings.ai_temperature,
            "ai_max_tokens": settings.ai_max_tokens,
            "ai_model": settings.ai_model,
            # Environment
            "alpaca_paper": settings.alpaca_paper,
            # Note: we do not store API keys in the configuration for security
        }

        return self.set_agent_config(parameter_values, changed_by="system")


def _dump(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return json.dumps(value.model_dump(mode="json"), default=str)
    if isinstance(value, (dict, list)):
        return json.dumps(value, default=str)
    return json.dumps(value, default=str)