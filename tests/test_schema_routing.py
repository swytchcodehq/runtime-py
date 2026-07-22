import unittest
from swytchcode_runtime.schema import simplify

class TestSchemaRouting(unittest.TestCase):
    def test_path_params_required(self):
        raw_schema = [
            {
                "userId": {
                    "TYPE": "STRING",
                    "LOCATION": "path",
                    "DESC": "The user ID"
                }
            },
            {
                "amount": {
                    "TYPE": "INT",
                    "LOCATION": "query"
                }
            }
        ]
        
        simplified = simplify(raw_schema)
        
        # Path parameters should be required
        self.assertIn("userId", simplified["required"])
        self.assertEqual(simplified["properties"]["userId"]["type"], "string")
        self.assertEqual(simplified["properties"]["amount"]["type"], "integer")

if __name__ == '__main__':
    unittest.main()
