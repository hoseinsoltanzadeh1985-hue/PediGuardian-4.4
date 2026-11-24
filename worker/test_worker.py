"""Regression tests for worker health, safe playback, retry policy, and queue leases."""
from __future__ import annotations

import time
import unittest
from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.error import HTTPError
from urllib.request import urlopen
from unittest.mock import Mock, patch

import requests
import worker


class WorkerHealthTests(unittest.TestCase):
    def setUp(self) -> None:
        worker.READY = False
        worker.LAST_HEARTBEAT = 0.0
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), worker.HealthHandler)
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = "http://127.0.0.1:" + str(self.server.server_port)

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        worker.READY = False
        worker.LAST_HEARTBEAT = 0.0

    def status(self, path: str) -> int:
        try:
            with urlopen(self.base + path, timeout=2) as response:
                return response.status
        except HTTPError as error:
            return error.code

    def test_health_is_not_ready_before_dependencies_start(self) -> None:
        self.assertEqual(self.status("/health"), 503)
        self.assertEqual(self.status("/heartbeat"), 503)

    def test_health_becomes_ready_after_fresh_heartbeat(self) -> None:
        worker.READY = True
        worker.LAST_HEARTBEAT = time.monotonic()
        self.assertEqual(self.status("/health"), 200)
        self.assertEqual(self.status("/heartbeat"), 200)

    def test_health_fails_when_heartbeat_is_stale(self) -> None:
        worker.READY = True
        worker.LAST_HEARTBEAT = time.monotonic() - 600
        self.assertEqual(self.status("/health"), 503)

    def test_liveness_is_independent_of_readiness(self) -> None:
        self.assertEqual(self.status("/live"), 200)
        self.assertEqual(self.status("/health"), 503)

    def test_unknown_path_is_not_found(self) -> None:
        self.assertEqual(self.status("/not-a-health-route"), 404)


class WorkerConfigurationTests(unittest.TestCase):
    def _with_config(self, values: dict[str, str | None], callback) -> None:
        names = ("SUPABASE_URL", "SUPABASE_KEY", "BOT_TOKEN", "TG_API_ID", "TG_API_HASH", "TG_SESSION_STRING")
        previous = {name: getattr(worker, name) for name in names}
        try:
            for name, value in values.items():
                setattr(worker, name, value)
            callback()
        finally:
            for name, value in previous.items():
                setattr(worker, name, value)

    def test_missing_secret_names_are_reported_without_values(self) -> None:
        def check() -> None:
            with self.assertRaises(RuntimeError) as raised:
                worker.validate_environment()
            message = str(raised.exception)
            self.assertIn("SUPABASE_URL", message)
            self.assertIn("BOT_TOKEN", message)
            self.assertIn("TG_SESSION_STRING", message)
            self.assertNotIn("test-secret", message)
        values = {name: (None if name == "SUPABASE_KEY" else "") for name in (
            "SUPABASE_URL", "SUPABASE_KEY", "BOT_TOKEN", "TG_API_ID", "TG_API_HASH", "TG_SESSION_STRING"
        )}
        self._with_config(values, check)

    def test_invalid_api_id_is_rejected(self) -> None:
        values = {
            "SUPABASE_URL": "https://example.supabase.co",
            "SUPABASE_KEY": "placeholder-secret",
            "BOT_TOKEN": "placeholder-token",
            "TG_API_ID": "not-an-integer",
            "TG_API_HASH": "placeholder-hash",
            "TG_SESSION_STRING": "placeholder-session",
        }
        def check() -> None:
            with self.assertRaisesRegex(RuntimeError, "TG_API_ID must be a positive integer"):
                worker.validate_environment()
        self._with_config(values, check)

    def test_non_positive_api_id_is_rejected(self) -> None:
        values = {
            "SUPABASE_URL": "https://example.supabase.co",
            "SUPABASE_KEY": "placeholder-secret",
            "BOT_TOKEN": "placeholder-token",
            "TG_API_ID": "0",
            "TG_API_HASH": "placeholder-hash",
            "TG_SESSION_STRING": "placeholder-session",
        }
        def check() -> None:
            with self.assertRaisesRegex(RuntimeError, "TG_API_ID must be a positive integer"):
                worker.validate_environment()
        self._with_config(values, check)

    def test_valid_configuration_passes(self) -> None:
        values = {
            "SUPABASE_URL": "https://example.supabase.co",
            "SUPABASE_KEY": "placeholder-secret",
            "BOT_TOKEN": "placeholder-token",
            "TG_API_ID": "12345",
            "TG_API_HASH": "placeholder-hash",
            "TG_SESSION_STRING": "placeholder-session",
        }
        self._with_config(values, worker.validate_environment)


class WorkerHttpRetryTests(unittest.TestCase):
    @patch("worker.time.sleep")
    @patch("worker.requests.request")
    def test_default_post_is_not_retried(self, mock_request, _sleep) -> None:
        mock_request.side_effect = requests.ConnectionError("sensitive URL must not be shown")
        with self.assertRaises(RuntimeError) as raised:
            worker.request("POST", "https://api.example.invalid/update", json={})
        self.assertEqual(mock_request.call_count, 1)
        self.assertNotIn("sensitive URL", str(raised.exception))

    @patch("worker.time.sleep")
    @patch("worker.requests.request")
    def test_explicit_safe_request_can_retry(self, mock_request, _sleep) -> None:
        response = Mock()
        response.raise_for_status.return_value = None
        mock_request.side_effect = [requests.ConnectionError("temporary"), response]
        self.assertIs(worker.request("GET", "https://example.invalid/resource", retry_safe=True), response)
        self.assertEqual(mock_request.call_count, 2)


class SupabaseAuthHeaderTests(unittest.TestCase):
    def test_new_secret_key_is_sent_only_as_apikey(self) -> None:
        with patch.object(worker, "SUPABASE_SECRET_KEY", "sb_secret_test"), patch.object(
            worker, "SUPABASE_SERVICE_ROLE_KEY", ""
        ), patch.object(worker, "SUPABASE_KEY", "sb_secret_test"):
            result = worker.headers()
        self.assertEqual(result["apikey"], "sb_secret_test")
        self.assertNotIn("Authorization", result)

    def test_legacy_service_role_key_keeps_bearer_compatibility(self) -> None:
        with patch.object(worker, "SUPABASE_SECRET_KEY", ""), patch.object(
            worker, "SUPABASE_SERVICE_ROLE_KEY", "legacy-jwt"
        ), patch.object(worker, "SUPABASE_KEY", "legacy-jwt"):
            result = worker.headers()
        self.assertEqual(result["apikey"], "legacy-jwt")
        self.assertEqual(result["Authorization"], "Bearer legacy-jwt")


class WorkerSourceSafetyTests(unittest.TestCase):
    def test_media_source_requires_allowlist(self) -> None:
        with patch.object(worker, "MEDIA_ALLOWED_HOSTS", set()), patch("worker.socket.getaddrinfo") as resolver:
            self.assertFalse(worker.safe_source("https://media.example/audio.mp3"))
            resolver.assert_not_called()

    def test_media_source_rejects_private_dns(self) -> None:
        private_dns = [(None, None, None, None, ("10.0.0.4", 443))]
        with patch.object(worker, "MEDIA_ALLOWED_HOSTS", {"example.com"}), patch("worker.socket.getaddrinfo", return_value=private_dns):
            self.assertFalse(worker.safe_source("https://example.com/audio.mp3"))

    def test_media_source_accepts_public_allowlisted_host(self) -> None:
        public_dns = [(None, None, None, None, ("93.184.216.34", 443))]
        with patch.object(worker, "MEDIA_ALLOWED_HOSTS", {"example.com"}), patch("worker.socket.getaddrinfo", return_value=public_dns):
            self.assertTrue(worker.safe_source("https://example.com/audio.mp3"))

    def test_redirect_to_non_allowlisted_host_is_rejected(self) -> None:
        public_dns = [(None, None, None, None, ("93.184.216.34", 443))]
        redirect = Mock()
        redirect.is_redirect = True
        redirect.is_permanent_redirect = False
        redirect.headers = {"Location": "https://evil.example/audio.mp3"}
        with patch.object(worker, "MEDIA_ALLOWED_HOSTS", {"example.com"}), patch("worker.socket.getaddrinfo", return_value=public_dns), patch("worker.requests.get", return_value=redirect):
            with self.assertRaisesRegex(RuntimeError, "allowlisted host"):
                worker.resolve_safe_source("https://example.com/start")
        redirect.close.assert_called_once()


class WorkerQueueLeaseTests(unittest.TestCase):
    @patch("worker.request")
    def test_pending_reclaims_expired_jobs_before_read(self, mock_request) -> None:
        pending = Mock()
        pending.json.return_value = [{"id": 7}]
        mock_request.side_effect = [Mock(), pending]
        self.assertEqual(worker.Store().pending(), [{"id": 7}])
        self.assertEqual(mock_request.call_count, 2)
        self.assertIn("reclaim_expired_voice_order_requests", mock_request.call_args_list[0].args[1])
        self.assertIn("status=eq.PENDING", mock_request.call_args_list[1].args[1])

    @patch("worker.request")
    def test_claim_returns_unique_lease_token_without_retry(self, mock_request) -> None:
        response = Mock()
        response.json.return_value = "test-lease-token"
        mock_request.return_value = response
        self.assertEqual(worker.Store().claim(9), "test-lease-token")
        args, kwargs = mock_request.call_args
        self.assertEqual(args[0], "POST")
        self.assertIn("claim_voice_order_request", args[1])
        self.assertNotIn("retry_safe", kwargs)

    @patch.object(worker.Store, "claim", side_effect=requests.ConnectionError("temporary"))
    def test_claim_safely_contains_ambiguous_claim_failure(self, mock_claim) -> None:
        store = worker.Store()
        self.assertIsNone(worker.claim_safely(store, 9))
        mock_claim.assert_called_once_with(9)

    @patch.object(worker.Store, "claim", return_value="test-lease-token")
    def test_claim_safely_returns_lease_token(self, mock_claim) -> None:
        store = worker.Store()
        self.assertEqual(worker.claim_safely(store, 9), "test-lease-token")
        mock_claim.assert_called_once_with(9)

    @patch("worker.request")
    def test_completion_is_scoped_to_exact_current_lease_token(self, mock_request) -> None:
        response = Mock()
        response.json.return_value = [{"id": 9}]
        mock_request.return_value = response
        worker.Store().complete(9, "DONE", {"ok": True}, "test-lease-token")
        args, kwargs = mock_request.call_args
        self.assertEqual(args[0], "PATCH")
        self.assertIn("id=eq.9&worker_id=eq.", args[1])
        self.assertIn("lease_token=eq.test-lease-token", args[1])
        self.assertIn("status=eq.CLAIMED", args[1])
        self.assertNotIn("retry_safe", kwargs)
        self.assertIsNone(kwargs["json"]["lease_token"])

    @patch("worker.request")
    def test_empty_patch_result_is_verified_with_safe_read(self, mock_request) -> None:
        patch_response = Mock()
        patch_response.json.return_value = []
        read_response = Mock()
        read_response.json.return_value = [{"result": {"ok": True}}]
        mock_request.side_effect = [patch_response, read_response]
        worker.Store().complete(9, "DONE", {"ok": True}, "test-lease-token")
        self.assertEqual(mock_request.call_count, 2)
        self.assertEqual(mock_request.call_args_list[1].args[0], "GET")

    @patch("worker.request")
    def test_completion_rejects_lost_lease(self, mock_request) -> None:
        patch_response = Mock()
        patch_response.json.return_value = []
        read_response = Mock()
        read_response.json.return_value = []
        mock_request.side_effect = [patch_response, read_response]
        with self.assertRaisesRegex(RuntimeError, "lease was lost"):
            worker.Store().complete(9, "DONE", {}, "stale-lease-token")


class PyTgCallsRuntimeTests(unittest.TestCase):
    def test_pinned_py_tgcalls_imports_required_runtime_symbols(self) -> None:
        self.assertIsNotNone(worker.PyTgCalls, "py-tgcalls import failed")
        self.assertIsNotNone(worker.AudioQuality, "AudioQuality import failed")
        self.assertIsNotNone(worker.MediaStream, "MediaStream import failed")
        self.assertTrue(hasattr(worker.AudioQuality, "STUDIO"))
        self.assertTrue(hasattr(worker.MediaStream, "Flags"))
        self.assertTrue(hasattr(worker.MediaStream.Flags, "IGNORE"))

    def test_worker_voice_client_api_methods_exist(self) -> None:
        for method in ("start", "play", "pause", "resume", "leave_call"):
            self.assertTrue(
                callable(getattr(worker.PyTgCalls, method, None)),
                f"PyTgCalls.{method} is missing",
            )


if __name__ == "__main__":
    unittest.main()
