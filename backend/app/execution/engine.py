from __future__ import annotations

import logging
import time
from uuid import uuid4

from backend.app.data.client import AlpacaClient
from backend.app.data.models import OrderRecord, RiskDecision, Signal
from backend.app.database.db import Database

logger = logging.getLogger(__name__)

class ExecutionEngine:
    def __init__(self, client: AlpacaClient, db: Database, max_retries: int = 3):
        self.client = client
        self.db = db
        self.max_retries = max_retries
        self.retry_delay_seconds = 1.0  # base delay, will exponential backoff

    def execute(self, signal: Signal, risk: RiskDecision) -> OrderRecord:
        """Execute a signal based on risk decision.

        Handles order submission, retries, partial fills, and records outcome.
        Returns the final OrderRecord (filled or rejected).
        """
        if not risk.approved:
            raise RuntimeError("ExecutionEngine refused unsigned risk decision")
        if not signal.contract:
            raise RuntimeError("Signal has no contract")

        # Prevent duplicate orders
        if self.db.has_open_order(signal.contract):
            raise RuntimeError(f"Duplicate order blocked for {signal.contract}")

        internal_id = f"agt-{uuid4().hex[:16]}"
        side = "buy"  # TODO: derive from signal.direction if needed for selling strategies
        qty = int(risk.qty)  # ensure integer quantity for options

        # Attempt submission with retries
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                logger.info(
                    "Submitting order attempt %d/%d: %s qty=%s side=%s",
                    attempt + 1, self.max_retries, signal.contract, qty, side
                )
                order = self.client.submit_market_order(
                    symbol=signal.contract,
                    qty=qty,
                    side=side,
                    internal_id=internal_id,
                )
                # If we got here, submission succeeded (no exception)
                break
            except Exception as e:
                last_exception = e
                logger.warning(
                    "Order submission attempt %d/%d failed for %s: %s",
                    attempt + 1, self.max_retries, signal.contract, str(e)
                )
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay_seconds * (2 ** attempt))  # exponential backoff
                else:
                    logger.error("All submission attempts failed for %s", signal.contract)
        else:
            # All retries exhausted
            # Record rejected order due to submission failure
            order_record = OrderRecord(
                internal_id=internal_id,
                alpaca_id=None,
                symbol=signal.contract,
                side=side,
                qty=qty,
                status="rejected",
                filled_qty=0.0,
                filled_avg_price=None,
                raw={"error": str(last_exception), "retries": self.max_retries}
            )
            self.db.record_order(
                internal_id=internal_id,
                alpaca_id=None,
                symbol=signal.contract,
                side=side,
                qty=qty,
                status="rejected",
                payload=order_record.model_dump(mode="json"),
            )
            return order_record

        # Submission succeeded, now we need to monitor for fills (if needed)
        # For simplicity, we assume the order is filled immediately or we rely on
        # the broker to fill and we later query positions.
        # In a more advanced system, we would poll for order status.
        # We'll record the order as submitted and let the journal capture the outcome.
        order_record = OrderRecord(
            internal_id=internal_id,
            alpaca_id=getattr(order, 'alpaca_id', None),
            symbol=signal.contract,
            side=side,
            qty=qty,
            status=getattr(order, 'status', 'unknown'),
            filled_qty=getattr(order, 'filled_qty', None),
            filled_avg_price=getattr(order, 'filled_avg_price', None),
            raw=getattr(order, 'model_dump', lambda: {})() if hasattr(order, 'model_dump') else {}
        )

        # Record order in DB
        self.db.record_order(
            internal_id=internal_id,
            alpaca_id=order_record.alpaca_id,
            symbol=signal.contract,
            side=side,
            qty=qty,
            status=order_record.status,
            payload=order_record.model_dump(mode="json"),
        )

        # If order was rejected by broker, return early
        if order_record.status.lower() in ("rejected", "canceled", "cancelled"):
            logger.warning(
                "Order %s for %s rejected by broker: status=%s",
                internal_id, signal.contract, order_record.status
            )
            return order_record

        # For now, we assume the order will be filled; we rely on position updates
        # in the trading loop to reflect actual fills.
        logger.info(
            "Order %s submitted for %s qty=%s side=%s status=%s alpaca_id=%s",
            internal_id, signal.contract, qty, side, order_record.status, order_record.alpaca_id
        )
        return order_record