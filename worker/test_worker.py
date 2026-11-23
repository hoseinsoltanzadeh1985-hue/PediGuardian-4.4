"""Non-production tests for worker liveness/readiness and config validation."""
from __future__ import annotations

import unittest
from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.error import HTTPError
from urllib.request import urlopen

import worker


class WorkerHealthTests(unittest.TestCase):
    def setUp(self) -> None:
        worker.READY = False
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), worker.HealthHandler)
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        worker.READY = False

    def status(self, path: str) -> int:
        try:
            with urlopen(self.base + path, timeout=2) as response:
                return response.status
        except HTTPError as error:
            return error.code

    def test_health_is_not_ready_before_dependencies_start(self) -> None:
        self.assertEqual(self.status("/health"), 503)
        self.assertEqual(self.status("/heartbeat"), 503)

    def test_health_becomes_ready_only_after_startup(self) -> None:
        worker.READY = True
        self.assertEqual(self.status("/health"), 200)
        self.assertEqual(self.status("/heartbeat"), 200)

    def test_liveness_does_not_claim_readiness(self) -> None:
        self.assertEqual(self.status("/live"), 200)
        self.assertEqual(self.status("/health"), 503)

    def test_unknown_path_is_not_found(self) -> None:
        self.assertEqual(self.status("/not-a-health-route"), 404)


class WorkerConfigurationTests(unittest.TestCase):
    def test_missing_secret_names_are_reported_without_values(self) -> None:
        names = (
            "SUPABASE_URL",
            "SUPABASE_KEY",
            "BOT_TOKEN",
            "TG_API_ID",
            "TG_API_HASH",
            "TG_SESSION_STRING",
        )
        previous = {name: getattr(worker, name) for name in names}
        try:
            for name in names:
                setattr(worker, name, "" if name != "SUPABASE_KEY" else None)
            with self.assertRaises(RuntimeError) as raised:
                worker.validate_environment()
            message = str(raised.exception)
            self.assertIn("SUPABASE_URL", message)
            self.assertIn("BOT_TOKEN", message)
            self.assertIn("TG_SESSION_STRING", message)
            self.assertNotIn("test-secret", message)
        finally:
            for name, value in previous.items():
                setattr(worker, name, value)

    def test_valid_configuration_passes(self) -> None:
        names = (
            "SUPABASE_URL",
            "SUPABASE_KEY",
            "BOT_TOKEN",
            "TG_API_ID",
            "TG_API_HASH",
            "TG_SESSION_STRING",
        )
        previous = {name: getattr(worker, name) for name in names}
        values = {
            "SUPABASE_URL": "https://example.supabase.co",
            "SUPABASE_KEY": "placeholder-secret",
            "BOT_TOKEN": "placeholder-token",
            "TG_API_ID": "12345",
            "TG_API_HASH": "placeholder-hash",
            "TG_SESSION_STRING": "placeholder-session",
        }
        try:
            for name, value in values.items():
                setattr(worker, name, value)
            worker.validate_environment()
        finally:
            for name, value in previous.items():
                setattr(worker, name, value)


if __name__ == "__main__":
    unittest.main()
