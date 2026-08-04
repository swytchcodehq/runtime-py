"""Simplify a tool's input schema for the LLM: expose all fields, mark required ones."""

from __future__ import annotations

from typing import Any

# Map wrekenfile/CLI type names onto JSON Schema types. Lowercase keys already in
# JSON Schema form (e.g. "string", "integer") map to themselves so a nested
# `schema` block from `swytchcode info` passes through unchanged.
_TYPE_MAP = {
    "int": "integer",
    "integer": "integer",
    "float": "number",
    "number": "number",
    "double": "number",
    "bool": "boolean",
    "boolean": "boolean",
    "object": "object",
    "any": "object",
    "string": "string",
    "array": "array",
}


def _json_type(raw: Any) -> str:
    t = str(raw or "string").strip().lower()
    if t.startswith("[]"):
        return "array"
    if t.startswith("struct(") or t.startswith("map("):
        return "object"
    return _TYPE_MAP.get(t, "string")


def _is_valid_name(name: str) -> bool:
    """Return True if name is a valid tool parameter identifier.

    Anthropic and OpenAI require parameter names to match ^[a-zA-Z0-9_-]+$.
    Google API schemas include system parameters like $.xgafv which cause
    Anthropic API 400 Bad Request errors if included in tool schemas.
    """
    if not name or name.startswith("$"):
        return False
    return all(c.isalnum() or c in ("_", "-") for c in name)


def _nested(spec: dict) -> dict | None:
    """Locate the nested object schema on a field spec.

    `swytchcode info` nests an object body's fields under a `schema` key
    (``{"TYPE": "OBJECT", "schema": {"properties": {...}, "required": [...]}}``),
    while a plain JSON Schema keeps `properties` inline. Handle both.
    """
    inner = spec.get("schema")
    if isinstance(inner, dict) and isinstance(inner.get("properties"), dict):
        return inner
    if isinstance(spec.get("properties"), dict):
        return spec
    return None


def _is_required(spec: dict) -> bool:
    r = spec.get("required", spec.get("REQUIRED"))
    return r is True or (isinstance(r, str) and r.strip().lower() == "true")


def _expand(spec: Any) -> dict:
    """Convert one field spec into a JSON Schema fragment, recursing into nested
    object properties and array items so the model sees the full shape."""
    if not isinstance(spec, dict):
        return {"type": "string"}

    t = _json_type(spec.get("TYPE", spec.get("type", "string")))
    out: dict = {"type": t}

    desc = spec.get("DESC", spec.get("description"))
    if desc:
        out["description"] = desc

    if t == "object":
        nested = _nested(spec)
        if nested is not None:
            props = nested["properties"]
            out["properties"] = {
                name: _expand(child)
                for name, child in props.items()
                if _is_valid_name(name)
            }
            explicit = nested.get("required")
            required = list(explicit) if isinstance(explicit, list) else []
            for name, child in props.items():
                if (
                    _is_valid_name(name)
                    and isinstance(child, dict)
                    and _is_required(child)
                    and name not in required
                ):
                    required.append(name)
            out["required"] = [name for name in required if name in out["properties"]]
    elif t == "array":
        items = spec.get("items")
        if items is None and isinstance(spec.get("schema"), dict):
            items = spec["schema"].get("items")
        if isinstance(items, dict):
            out["items"] = _expand(items)

    return out


def simplify(inputs: Any) -> dict:
    # Handle Wrekenfile shape: a list of single-key dicts (e.g. [{"amount": {"TYPE": "INT"...}}])
    if isinstance(inputs, list):
        props = {}
        required = []
        for item in inputs:
            if not isinstance(item, dict):
                continue
            for name, spec in item.items():
                if not isinstance(spec, dict) or not _is_valid_name(name):
                    continue

                # Expand into full JSON Schema, keeping nested object/array shape
                # (a body's fields live under spec["schema"] and were previously
                # dropped, leaving the model blind to what to send).
                props[name] = _expand(spec)

                req = spec.get("REQUIRED", False)
                loc = str(spec.get("LOCATION", spec.get("location", ""))).lower()
                is_required = (
                    loc == "path"
                    or req is True
                    or (isinstance(req, str) and req.strip().lower() == "true")
                )
                if is_required:
                    required.append(name)

        # rule: expose ALL fields to the model and list only the
        # truly-required ones in `required`. A required-only approach hid optional
        # fields - which left all-optional tools (e.g. Stripe) with an empty schema
        # so the model called them with no arguments, and blinded the model to
        # optional fields on tools that do have some required ones.
        return {"type": "object", "properties": props, "required": required}

    # Fallback to standard JSON Schema handling
    if not isinstance(inputs, dict):
        return {"type": "object", "properties": {}, "required": []}

    props = inputs.get("properties") or {}
    required = inputs.get("required") or []
    keep = {}

    # Expose all fields (same rule as the wrekenfile branch above); use the
    # original required list only for the `required` key so optional/nested
    # fields stay optional instead of being dropped or forced required.
    for name, spec in props.items():
        if not _is_valid_name(name):
            continue
        if isinstance(spec, dict):
            loc = str(spec.get("LOCATION", spec.get("location", ""))).lower()
            if loc == "path" and name not in required:
                required.append(name)

            if _json_type(spec.get("type", spec.get("TYPE"))) in ("object", "array"):
                spec = _expand(spec)  # expand nested objects/arrays
        keep[name] = spec

    return {
        "type": "object",
        "properties": keep,
        "required": [r for r in required if r in keep],
    }


def to_pydantic_model(schema: dict, name: str = "ArgsSchema") -> Any:
    """Dynamically build a Pydantic model from a JSON schema for LangGraph args_schema."""
    from pydantic import create_model

    if not schema or "properties" not in schema:
        return create_model(name)

    fields = {}
    properties = schema.get("properties", {})
    required = set(schema.get("required", []))

    for field_name, field_info in properties.items():
        field_type = str
        t = field_info.get("type")
        if t == "integer":
            field_type = int
        elif t == "number":
            field_type = float
        elif t == "boolean":
            field_type = bool
        elif t == "array":
            field_type = list
        elif t == "object":
            # Only build a nested model when the object's fields are known.
            # A property-less object (freeform body) becomes a plain dict: an
            # empty model would silently drop every value the agent passed and
            # then fail to JSON-serialize.
            if field_info.get("properties"):
                field_type = to_pydantic_model(field_info, f"{name}_{field_name}")
            else:
                field_type = dict

        if field_name in required:
            fields[field_name] = (field_type, ...)
        else:
            # `X | None` so an explicit null is accepted (pydantic v2 rejects
            # None for a bare non-optional annotation).
            fields[field_name] = (field_type | None, None)

    return create_model(name, **fields)
