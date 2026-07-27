import json
import unittest

from swytchcode_runtime.exec import _parse_classified_error


class TestParseClassifiedError(unittest.TestCase):
    def test_extracts_the_clis_classified_json_error_from_stderr(self):
        stderr = json.dumps(
            {
                "error": "missing credentials for github - run `swytchcode auth connect github`",
                "category": "auth",
                "retryable": False,
                "suggested_action": "to access registry features, run: swytchcode login",
                "docs_url": "https://docs.swytchcode.com/auth",
            }
        )
        parsed = _parse_classified_error(stderr)
        self.assertEqual(
            parsed["error"],
            "missing credentials for github - run `swytchcode auth connect github`",
        )
        self.assertEqual(parsed["category"], "auth")
        self.assertEqual(
            parsed["suggested_action"],
            "to access registry features, run: swytchcode login",
        )

    def test_returns_none_for_non_json_or_shapeless_stderr(self):
        self.assertIsNone(_parse_classified_error(""))
        self.assertIsNone(_parse_classified_error("a plain-text panic, not JSON"))
        self.assertIsNone(_parse_classified_error('{"not_error_field": true}'))


if __name__ == "__main__":
    unittest.main()
