"""Find tools by intent and read their schemas."""

from __future__ import annotations
import logging
from .cli import run_cli

logger = logging.getLogger(__name__)


def search(intent: str, *, top: int = 5) -> list[dict]:
    res = run_cli(["discover", intent, "--top", str(top)]) or {}
    return res.get("capabilities", [])


def info(canonical_id: str) -> dict:
    try:
        result = run_cli(["info", canonical_id]) or {}
        # CLI returns a JSON array of ToolInfo objects; unwrap the first one
        if isinstance(result, list):
            return result[0] if result else {}
        return result
    except Exception as e:
        # Broad by design: any CLI/parse failure degrades to an empty schema
        # rather than breaking tool discovery. Logged (not printed) so it
        # respects the host app's logging config.
        logger.warning(
            "Failed to fetch info for %s (%s). Using empty schema.", canonical_id, e
        )
        return {"canonical_id": canonical_id, "inputs": {}}
