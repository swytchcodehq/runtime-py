"""Reduce a tool's input schema to its strictly-required fields for the LLM."""
from __future__ import annotations
from typing import Any

def simplify(inputs: Any) -> dict:
    # Handle Wrekenfile shape: a list of single-key dicts (e.g. [{"amount": {"TYPE": "INT"...}}])
    if isinstance(inputs, list):
        all_props = {}
        required_props = {}
        required = []
        for item in inputs:
            if not isinstance(item, dict):
                continue
            for name, spec in item.items():
                if not isinstance(spec, dict):
                    continue

                # Default to string if TYPE is missing
                t = spec.get("TYPE", "STRING").lower()
                if t == "int": t = "integer"
                elif t == "bool": t = "boolean"
                elif t == "object": t = "object"
                elif t == "any": t = "object"
                elif t.startswith("[]"): t = "array"
                else: t = "string"

                prop = {"type": t, "description": spec.get("DESC", "")}
                all_props[name] = prop

                req = spec.get("REQUIRED", False)
                is_required = req is True or (isinstance(req, str) and req.strip().lower() == "true")
                if is_required:
                    required_props[name] = prop
                    required.append(name)

        # Prefer required-only fields (criterion #2: don't surface optional noise).
        # But some tools (e.g. Stripe) mark EVERY field optional — a required-only
        # schema would then be empty, and the model calls the tool with no args.
        # So fall back to exposing all fields when nothing is marked required.
        props = required_props if required else all_props
        return {"type": "object", "properties": props, "required": required}

    # Fallback to standard JSON Schema handling
    if not isinstance(inputs, dict):
        return {"type": "object", "properties": {}, "required": []}
        
    props = inputs.get("properties") or {}
    required = inputs.get("required") or list(props.keys())
    keep = {}
    
    for name in required:
        spec = props.get(name, {})
        if isinstance(spec, dict) and spec.get("type") == "object" and "properties" in spec:
            spec = simplify(spec) # recurse into nested objects
        keep[name] = spec
        
    return {"type": "object", "properties": keep, "required": list(keep.keys())}


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
        if t == "integer": field_type = int
        elif t == "number": field_type = float
        elif t == "boolean": field_type = bool
        elif t == "object": 
            field_type = to_pydantic_model(field_info, f"{name}_{field_name}")
            
        if field_name in required:
            fields[field_name] = (field_type, ...)
        else:
            fields[field_name] = (field_type, None)
            
    return create_model(name, **fields)
