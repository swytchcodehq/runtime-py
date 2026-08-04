import json
import unittest

from swytchcode_runtime import client as sc_client
from swytchcode_runtime.client import _to_plain
from swytchcode_runtime.schema import simplify, to_pydantic_model

# The shape `swytchcode info` returns for a POST tool whose body is an object:
# the body's fields live under spec["schema"], which simplify() used to drop.
BODY_INPUTS = [
    {"owner": {"LOCATION": "path", "TYPE": "STRING"}},
    {
        "body": {
            "LOCATION": "body",
            "TYPE": "OBJECT",
            "schema": {
                "properties": {
                    "prompt": {"type": "string", "required": True},
                    "create_pull_request": {"type": "boolean", "required": False},
                },
                "required": ["prompt"],
            },
        }
    },
]


class TestNestedBodySchema(unittest.TestCase):
    def test_object_body_expands_nested_properties(self):
        body = simplify(BODY_INPUTS)["properties"]["body"]
        self.assertEqual(body["type"], "object")
        self.assertIn("prompt", body["properties"])
        self.assertIn("create_pull_request", body["properties"])
        self.assertEqual(body["properties"]["prompt"]["type"], "string")
        self.assertEqual(body["properties"]["create_pull_request"]["type"], "boolean")
        self.assertEqual(body["required"], ["prompt"])

    def test_deeply_nested_object_expands(self):
        inputs = [
            {
                "body": {
                    "LOCATION": "body",
                    "TYPE": "OBJECT",
                    "schema": {
                        "properties": {
                            "start": {
                                "type": "object",
                                "schema": {
                                    "properties": {
                                        "dateTime": {"type": "string", "required": True}
                                    }
                                },
                            }
                        }
                    },
                }
            }
        ]
        body = simplify(inputs)["properties"]["body"]
        start = body["properties"]["start"]
        self.assertEqual(start["type"], "object")
        self.assertEqual(start["properties"]["dateTime"]["type"], "string")
        self.assertEqual(start["required"], ["dateTime"])

    def test_freeform_object_has_no_properties(self):
        body = simplify([{"body": {"LOCATION": "body", "TYPE": "OBJECT"}}])[
            "properties"
        ]["body"]
        self.assertEqual(body, {"type": "object"})


class TestPydanticModel(unittest.TestCase):
    def test_object_with_properties_builds_nested_model(self):
        model = to_pydantic_model(simplify(BODY_INPUTS), "T")
        # body is optional, so its annotation is `NestedModel | None`; unwrap it.
        nested = [
            a for a in body_annotation_args(model, "body") if hasattr(a, "model_fields")
        ]
        self.assertTrue(nested, "body should be a nested model, not a bare type")
        # The nested body must be a real model, not an empty one, so it can guide
        # and validate the agent's arguments.
        self.assertIn("prompt", nested[0].model_fields)

    def test_property_less_object_maps_to_dict_not_empty_model(self):
        schema = simplify([{"body": {"LOCATION": "body", "TYPE": "OBJECT"}}])
        model = to_pydantic_model(schema, "T")
        # Optional field annotation is `dict | None`; dict must be one of the args.
        self.assertIn(dict, body_annotation_args(model, "body"))


class TestToPlain(unittest.TestCase):
    def test_converts_nested_pydantic_model_to_dict(self):
        model_cls = to_pydantic_model(simplify(BODY_INPUTS), "T")
        instance = model_cls(owner="acme", body={"prompt": "hi"})
        plain = _to_plain({"body": instance.body})
        self.assertIsInstance(plain["body"], dict)
        self.assertEqual(plain["body"]["prompt"], "hi")


class TestExecuteSerializesModels(unittest.TestCase):
    """The regression guard for the reported crash: a Pydantic body must reach
    the CLI as JSON-serializable data, with empty optionals stripped."""

    def test_execute_serializes_pydantic_body(self):
        captured = {}

        def fake_exec(cid, input=None, **kwargs):
            captured["stdin"] = json.dumps(input)  # same call exec_ makes
            return {"ok": True}

        original = sc_client._exec
        sc_client._exec = fake_exec
        try:
            model_cls = to_pydantic_model(simplify(BODY_INPUTS), "T")
            body = model_cls(owner="acme", body={"prompt": "hi"}).body
            client = sc_client.Swytchcode()
            result = client.tools.execute(
                "github.agent.tasks.create",
                {"owner": "acme", "body": body},
                _raw_inputs=BODY_INPUTS,
            )
        finally:
            sc_client._exec = original

        self.assertEqual(result, {"ok": True})
        sent = json.loads(captured["stdin"])
        self.assertEqual(sent["body"]["prompt"], "hi")
        # create_pull_request was None (unset) and must be stripped, not sent.
        self.assertNotIn("create_pull_request", sent["body"])


class TestSanitizeParameterNames(unittest.TestCase):
    def test_strips_system_parameters_starting_with_dollar(self):
        inputs = [
            {"$.xgafv": {"LOCATION": "query", "TYPE": "STRING"}},
            {"q": {"LOCATION": "query", "TYPE": "STRING"}},
        ]
        res = simplify(inputs)
        self.assertNotIn("$.xgafv", res["properties"])
        self.assertIn("q", res["properties"])

    def test_strips_dollar_parameters_from_nested_objects(self):
        inputs = [
            {
                "body": {
                    "LOCATION": "body",
                    "TYPE": "OBJECT",
                    "schema": {
                        "properties": {
                            "valid": {"type": "string"},
                            "$.xgafv": {"type": "string"},
                        }
                    },
                }
            }
        ]
        body = simplify(inputs)["properties"]["body"]
        self.assertIn("valid", body["properties"])
        self.assertNotIn("$.xgafv", body["properties"])


def body_annotation_args(model, field):
    import typing

    return typing.get_args(model.model_fields[field].annotation)


if __name__ == "__main__":
    unittest.main()

