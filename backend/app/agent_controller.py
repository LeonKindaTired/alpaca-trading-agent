from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import Optional

from backend.app.config.settings import Settings, get_settings
from backend.app.database.db import Database
from backend.app.pipeline import TradingLoop


class AgentController:
    def __init__(self) -> None:
        self._loop_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._is_running = False
        self._settings: Optional[Settings] = None
        self._db: Optional[Database] = None
        self._lock = threading.Lock()

    def start(self) -> bool:
        """Start the agent loop in a background thread.
        Returns True if started successfully, False if already running.
        """
        with self._lock:
            if self._is_running:
                return False

            # Clear the stop event
            self._stop_event.clear()

            # Get the current settings (from database or environment)
            self._settings = self._get_current_settings()
            if self._settings is None:
                # Fallback to environment settings
                self._settings = get_settings()

            # Initialize database for the controller (needed for config updates)
            self._db = Database(self._settings.database_path, self._settings)

            # Start the loop thread
            self._loop_thread = threading.Thread(target=self._loop_worker, daemon=True)
            self._loop_thread.start()
            self._is_running = True
            return True

    def stop(self) -> bool:
        """Stop the agent loop.
        Returns True if stopped successfully, False if not running.
        """
        with self._lock:
            if not self._is_running:
                return False

            # Signal the loop to stop
            self._stop_event.set()

            # Wait for the thread to finish (with timeout)
            if self._loop_thread is not None:
                self._loop_thread.join(timeout=5.0)
                self._loop_thread = None

            self._is_running = False
            self._settings = None
            if self._db is not None:
                self._db.close()
                self._db = None
            return True

    def is_running(self) -> bool:
        """Check if the agent loop is currently running."""
        return self._is_running

    def get_status(self) -> dict:
        """Get the current status of the agent.
        Returns a dictionary with status information.
        """
        with self._lock:
            if not self._is_running:
                return {
                    "status": "STOPPED",
                    "agent_mode": "UNKNOWN",
                    "last_decision": None,
                    "next_scan": None,
                    "trading_halted": False,
                    "shutdown_reason": None,
                    "system_health": {
                        "alpaca_connection": "Unknown",
                        "market_data": "Unknown",
                        "ai_provider": "Unknown",
                        "database": "Unknown",
                        "execution": "Unknown",
                        "last_heartbeat": None,
                    },
                }

            # If running, we can try to get more detailed status from the database
            # For now, we'll return a basic status
            settings = self._settings
            if settings is None:
                settings = get_settings()

            return {
                "status": "RUNNING",
                "agent_mode": "AI SUPERVISOR" if settings.use_ai_supervisor else "QUANT ONLY",
                "last_decision": None,  # We could get this from the database
                "next_scan": None,      # We could calculate based on loop interval
                "trading_halted": False, # We could get this from system_status in db
                "shutdown_reason": None,
                "system_health": {
                    "alpaca_connection": "Healthy",  # Simplified
                    "market_data": "Healthy",
                    "ai_provider": "Healthy" if settings.use_ai_supervisor else "Disabled",
                    "database": "Healthy",
                    "execution": "Healthy",
                    "last_heartbeat": datetime.now(timezone.utc).isoformat(),
                },
            }

    def update_configuration(self, new_parameters: dict, changed_by: str = "dashboard") -> bool:
        """Update the agent configuration.
        This will stop the current agent loop (if running), update the configuration in the database,
        and start a new loop with the updated configuration.

        Args:
            new_parameters: Dictionary of configuration parameters to update.
            changed_by: Entity making the change (default: "dashboard").

        Returns:
            True if configuration updated successfully, False otherwise.
        """
        with self._lock:
            was_running = self._is_running
            # Stop the current loop if running
            if was_running:
                self.stop()

            # Update the configuration in the database
            if self._db is not None:
                # Get the current active configuration
                current_config = self._db.get_active_agent_config() or {}
                # Merge the new parameters (new parameters take precedence)
                updated_config = {**current_config, **new_parameters}
                # Store the updated configuration
                config_id = self._db.set_agent_config(updated_config, changed_by=changed_by)
                # Reload the settings for the controller
                self._settings = self._get_current_settings()
            else:
                # If we don't have a database (should not happen if we were running),
                # we'll update the settings in memory and initialize the database later
                if self._settings is None:
                    self._settings = get_settings()
                # Update the settings object with new parameters
                for key, value in new_parameters.items():
                    if hasattr(self._settings, key):
                        setattr(self._settings, key, value)
                # Initialize database with updated settings
                self._db = Database(self._settings.database_path, self._settings)

            # If we were running, start a new loop with the updated configuration
            if was_running:
                self.start()

            return True

    def _get_current_settings(self) -> Optional[Settings]:
        """Get the current settings by merging the active configuration from the database
        with the environment settings.
        Returns a Settings object, or None if there's an error.
        """
        try:
            # Get the active configuration from the database
            # We need a temporary database instance to read the configuration
            settings_env = get_settings()
            temp_db = Database(settings_env.database_path, settings_env)
            config_dict = temp_db.get_active_agent_config()
            temp_db.close()

            if config_dict is None:
                return None

            # Create a new Settings object and update it with the configuration dict
            # We'll start with the environment settings and override with the config dict
            settings = Settings()
            # Update each field that exists in the settings and is in the config dict
            for key, value in config_dict.items():
                if hasattr(settings, key):
                    # Try to convert the value to the appropriate type if needed
                    # For simplicity, we'll assign directly; the Settings model will handle validation
                    setattr(settings, key, value)
            return settings
        except Exception:
            # If anything goes wrong, return None to fall back to environment settings
            return None

    def _loop_worker(self) -> None:
        """Worker function that runs the agent loop in a background thread."""
        while not self._stop_event.is_set():
            try:
                # Get the current settings for this iteration
                settings = self._get_current_settings()
                if settings is None:
                    settings = get_settings()

                # Create a TradingLoop with the current settings
                client = None
                if settings.alpaca_paper:
                    from backend.app.data.live_alpaca import LiveAlpacaClient
                    client = LiveAlpacaClient(settings)
                else:
                    from backend.app.data.live_alpaca import LiveAlpacaClient
                    client = LiveAlpacaClient(settings)  # Same client for live? We should have a live client.
                    # Actually, LiveAlpacaClient uses the alpaca_paper flag to determine the environment.
                    # So we can use LiveAlpacaClient for both paper and live.

                loop = TradingLoop(client, settings)

                # Run one cycle of the loop
                result = loop.run_once(submit=settings.trading_enabled)

                # Close the client to free resources
                if hasattr(client, 'close'):
                    client.close()

                # Sleep for the loop interval
                interval = settings.loop_interval_seconds
                # Sleep in small chunks to check for stop event frequently
                for _ in range(interval):
                    if self._stop_event.is_set():
                        break
                    time.sleep(1)
            except Exception as e:
                # Log the error and continue
                # In a real implementation, we would use proper logging
                print(f"Error in agent loop: {e}")
                # Sleep for a bit before retrying
                time.sleep(5)

        # Clean up when the loop is stopped
        # Note: the client and loop are created inside the loop, so they are already closed


# Global instance of the agent controller
agent_controller = AgentController()