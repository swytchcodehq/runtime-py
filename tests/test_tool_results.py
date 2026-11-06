import json
import subprocess
import unittest
from types import SimpleNamespace
from unittest import mock

from swytchcode_runtime import Swytchcode


def _done(stdout="", returncode=0, stderr=""):
    return subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout=stdout.encode(), stderr=stderr.encode()
    )


@mock.patch("swytchcode_runtime.exec._resolve_bin", return_value="swytchcode")
class TestHandleToolCallsContent(unittest.TestCase):
    def _run(self, stdout):
        block = SimpleNamespace(
            type="tool_use", id="t1", name="stripe_refund", input={}
        )
        with mock.patch("subprocess.run", return_value=_done(stdout)):
            return Swytchcode().handle_tool_calls(SimpleNamespace(content=[block]))

    def test_dict_result_is_sent_as_json(self, *_):
        results = self._run('{"id": "re_1", "paid": true, "reason": null}')
        content = results[0]["content"]
        self.assertEqual(
            json.loads(content), {"id": "re_1", "paid": True, "reason": None}
        )
        self.assertFalse(results[0]["is_error"])

    def test_empty_output_is_sent_as_json_null(self, *_):
        results = self._run("")
        self.assertEqual(results[0]["content"], "null")


if __name__ == "__main__":
    unittest.main()
