import re
import unittest

from swytchcode_runtime import TOOL_USE_INSTRUCTIONS


class TestToolUseInstructions(unittest.TestCase):
    def test_is_exported_and_instructs_the_model_to_call_tools(self):
        self.assertIsInstance(TOOL_USE_INSTRUCTIONS, str)
        self.assertTrue(len(TOOL_USE_INSTRUCTIONS) > 0)
        self.assertRegex(
            TOOL_USE_INSTRUCTIONS, re.compile("call the matching tool", re.I)
        )

    def test_scopes_itself_to_swytchcode_tools_only(self):
        self.assertRegex(
            TOOL_USE_INSTRUCTIONS,
            re.compile(r"does not affect how you use any\s+other tools", re.I),
        )


if __name__ == "__main__":
    unittest.main()
