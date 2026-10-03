import json
import subprocess
import unittest
from unittest import mock

from swytchcode_runtime import SwytchcodeError, connect, disconnect, exec, save_key


def _done(stdout="", returncode=0, stderr=""):
    return subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout=stdout.encode(), stderr=stderr.encode()
    )


@mock.patch("swytchcode_runtime.exec._resolve_bin", return_value="swytchcode")
@mock.patch("swytchcode_runtime.cli._resolve_bin", return_value="swytchcode")
class TestTenants(unittest.TestCase):
    def test_exec_passes_tenant(self, *_):
        with mock.patch("subprocess.run", return_value=_done('{"ok": true}')) as run:
            exec("gmail.send", {"body": {}}, tenant_id=" alice ")
        self.assertEqual(run.call_args.args[0][-2:], ["--tenant", "alice"])

    def test_exec_without_tenant_passes_no_flag(self, *_):
        with mock.patch("subprocess.run", return_value=_done("{}")) as run:
            exec("gmail.send", {"body": {}})
        self.assertNotIn("--tenant", run.call_args.args[0])

    def test_exec_passes_tenant_label(self, *_):
        with mock.patch("subprocess.run", return_value=_done('{"ok": true}')) as run:
            exec("gmail.send", {}, tenant_id="alice", tenant_label=" Alice Smith ")
        self.assertEqual(run.call_args.args[0][-4:], ["--tenant", "alice", "--tenant-label", "Alice Smith"])

    def test_exec_refuses_label_without_tenant(self, *_):
        with mock.patch("subprocess.run") as run:
            with self.assertRaisesRegex(SwytchcodeError, "tenant_label needs tenant_id"):
                exec("gmail.send", {}, tenant_label="Alice")
        run.assert_not_called()

    def test_exec_rejects_empty_tenant(self, *_):
        with mock.patch("subprocess.run") as run:
            with self.assertRaises(SwytchcodeError):
                exec("gmail.send", {}, tenant_id="  ")
        run.assert_not_called()

    def test_exec_reports_tenant_not_connected(self, *_):
        err = json.dumps(
            {
                "error": "alice has not connected google",
                "category": "tenant_not_connected",
                "retryable": False,
            }
        )
        with mock.patch("subprocess.run", return_value=_done("", 3, err)):
            with self.assertRaises(SwytchcodeError) as ctx:
                exec("gmail.send", {}, tenant_id="alice")
        self.assertEqual(ctx.exception.details["category"], "tenant_not_connected")

    def test_connect_returns_link(self, *_):
        out = json.dumps(
            {
                "authorization_url": "https://auth.example/?state=s",
                "connected_account_uuid": "ca-1",
                "provider_slug": "google",
                "tenant_id": "alice",
            }
        )
        with mock.patch("subprocess.run", return_value=_done(out)) as run:
            res = connect("google", "alice")
        self.assertEqual(
            res, {"url": "https://auth.example/?state=s", "connected_account_uuid": "ca-1"}
        )
        self.assertEqual(
            run.call_args.args[0][1:],
            ["auth", "connect", "google", "--tenant", "alice", "--json"],
        )

    def test_connect_on_key_provider_points_to_save_key(self, *_):
        with mock.patch("subprocess.run", return_value=_done("")):
            with self.assertRaisesRegex(SwytchcodeError, "save_key"):
                connect("stripe", "alice")

    def test_save_key_uses_stdin(self, *_):
        out = json.dumps({"provider_slug": "stripe", "tenant_id": "alice", "auth_type": "api_key", "stored": "local"})
        with mock.patch("subprocess.run", return_value=_done(out)) as run:
            save_key("stripe", "alice", "sk_test_123")
        self.assertNotIn("sk_test_123", run.call_args.args[0])
        self.assertEqual(run.call_args.kwargs["input"], b"sk_test_123\n")

    def test_disconnect_has_no_json_flag(self, *_):
        with mock.patch("subprocess.run", return_value=_done("Disconnected")) as run:
            disconnect("google", "alice")
        self.assertEqual(
            run.call_args.args[0][1:], ["auth", "disconnect", "google", "--tenant", "alice"]
        )

    def test_helpers_refuse_empty_tenant(self, *_):
        with mock.patch("subprocess.run") as run:
            with self.assertRaises(SwytchcodeError):
                connect("google", "")
            with self.assertRaises(SwytchcodeError):
                disconnect("google", " ")
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()


@mock.patch("swytchcode_runtime.exec._resolve_bin", return_value="swytchcode")
class TestBoundClient(unittest.TestCase):
    def test_tools_execute_passes_bound_tenant(self, *_):
        from swytchcode_runtime import Swytchcode

        with mock.patch("subprocess.run", return_value=_done('{"ok": true}')) as run:
            Swytchcode(tenant_id="alice").tools.execute("gmail.send", {"to": "x@y.z"})
        self.assertEqual(run.call_args.args[0][-2:], ["--tenant", "alice"])

    def test_handle_tool_calls_runs_for_bound_tenant(self, *_):
        from types import SimpleNamespace

        from swytchcode_runtime import Swytchcode

        block = SimpleNamespace(type="tool_use", id="t1", name="gmail_send", input={})
        with mock.patch("subprocess.run", return_value=_done("{}")) as run:
            Swytchcode(tenant_id="bob").handle_tool_calls(SimpleNamespace(content=[block]))
        self.assertEqual(run.call_args.args[0][-2:], ["--tenant", "bob"])

    def test_unbound_client_passes_no_tenant(self, *_):
        from swytchcode_runtime import Swytchcode

        with mock.patch("subprocess.run", return_value=_done("{}")) as run:
            Swytchcode().tools.execute("gmail.send", {})
        self.assertNotIn("--tenant", run.call_args.args[0])

    def test_empty_tenant_refused(self, *_):
        from swytchcode_runtime import Swytchcode

        with self.assertRaises(SwytchcodeError):
            Swytchcode(tenant_id=" ")

    def test_bound_label_goes_with_bound_tenant_only(self, *_):
        from swytchcode_runtime import Swytchcode

        client = Swytchcode(tenant_id="alice", tenant_label="Alice Smith")
        with mock.patch("subprocess.run", return_value=_done("{}")) as run:
            client.tools.execute("gmail.send", {})
            alice = run.call_args.args[0]
            client.tools.execute("gmail.send", {}, tenant_id="bob")
            bob = run.call_args.args[0]
        self.assertEqual(alice[-4:], ["--tenant", "alice", "--tenant-label", "Alice Smith"])
        self.assertEqual(bob[-2:], ["--tenant", "bob"])
        with self.assertRaises(SwytchcodeError):
            Swytchcode(tenant_label="Alice")
