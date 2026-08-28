from __future__ import annotations

from uuid import uuid4

from backend.app.data.client import AlpacaClient
from backend.app.data.models import OrderRecord, RiskDecision, Signal
from backend.app.database.db import Database


class ExecutionEngine:
    def __init__(self, client: AlpacaClient, db: Database) -> None:
        self.client = client
        self.db = db

    def execute(self, signal: Signal, risk: RiskDecision) -> OrderRecord:
        if not risk.approved:
            raise RuntimeError("ExecutionEngine refused unsigned risk decision")
        if not signal.contract:
            raise RuntimeError("Signal has no contract")

        internal_id = f"agt-{uuid4().hex[:16]}"
        if self.db.has_open_order(signal.contract):
            raise RuntimeError(f"Duplicate order blocked for {signal.contract}")

        order = self.client.submit_market_order(
            symbol=signal.contract,
            qty=risk.qty,
            side="buy",
            internal_id=internal_id,
        )
        self.db.record_order(
            internal_id=internal_id,
            alpaca_id=order.alpaca_id,
            symbol=signal.contract,
            side="buy",
            qty=risk.qty,
            status=order.status,
            payload=order.model_dump(mode="json"),
        )
        return order
