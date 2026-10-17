"""Connect, save and remove accounts for the end users (tenants) of your app."""

from __future__ import annotations

import json

from .cli import run_cli
from .errors import SwytchcodeError


def _tenant_args(provider: str, tenant_id: str) -> list[str]:
    provider = (provider or "").strip()
    tenant_id = (tenant_id or "").strip()
    if not provider:
        raise SwytchcodeError("provider must be a non-empty string")
    # An empty tenant id would act on the developer's own account.
    if not tenant_id:
        raise SwytchcodeError("tenant_id must be a non-empty string")
    return [provider, "--tenant", tenant_id]


def connect(
    provider: str,
    tenant_id: str,
    *,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
) -> dict:
    """
    Start an OAuth connection for one end user and return the link they open.

    tenant_id is your own id for the end user, taken from your server's session,
    never from the browser. The account is ready once they finish in the popup;
    the first exec() with this tenant_id picks it up. The provider app used
    (Swytchcode's or your own) is the one you chose with `swytchcode auth connect`.

    Returns {"url": ..., "connected_account_uuid": ...}.
    """
    out = run_cli(
        ["auth", "connect", *_tenant_args(provider, tenant_id), "--json"],
        cwd=cwd,
        env=env,
    )
    if not isinstance(out, dict) or not out.get("authorization_url"):
        raise SwytchcodeError(
            f"{provider} does not connect with OAuth; collect the end user's key "
            "in your app and save it with save_key()",
            out,
        )
    return {
        "url": out["authorization_url"],
        "connected_account_uuid": out.get("connected_account_uuid", ""),
    }


def save_key(
    provider: str,
    tenant_id: str,
    key: str,
    *,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
) -> None:
    """
    Save an end user's API key for a provider that uses keys. The key is stored
    encrypted on this machine only and never sent to Swytchcode; the end user is
    recorded (without the key) toward your plan's end-user limit, so this needs a
    login or API key, and at the limit it raises and nothing is saved.
    """
    key = (key or "").strip()
    if not key:
        raise SwytchcodeError("key must be a non-empty string")
    out = run_cli(
        ["auth", "connect", *_tenant_args(provider, tenant_id), "--json"],
        cwd=cwd,
        env=env,
        input=key + "\n",
    )
    if not isinstance(out, dict) or out.get("stored") != "local":
        raise SwytchcodeError(
            f"{provider} does not use an API key; use connect() instead", out
        )


def save_credentials(
    provider: str,
    tenant_id: str,
    credentials: dict[str, str],
    *,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
) -> None:
    """
    Save an end user's credentials for a provider whose requests are signed
    (crypto exchanges): several fields, such as ``{"api_key": ..., "secret_key":
    ..., "passphrase": ...}``, named as the provider's signing recipe names them
    (``swytchcode info`` shows the auth block). They are stored encrypted on this
    machine only and never sent to Swytchcode; the CLI signs each of this end
    user's requests with them. Like ``save_key()``, this counts the end user
    toward your plan's end-user limit.
    """
    if not isinstance(credentials, dict):
        raise SwytchcodeError("credentials must be a dict of field names to values")
    fields: dict[str, str] = {}
    for name, value in credentials.items():
        if not isinstance(value, str):
            raise SwytchcodeError(f"credential {name} must be a string")
        if value.strip():
            fields[name] = value.strip()
    if not fields:
        raise SwytchcodeError("credentials must not be empty")
    # One JSON line on stdin: the values never appear in the process arguments.
    out = run_cli(
        ["auth", "connect", *_tenant_args(provider, tenant_id), "--json"],
        cwd=cwd,
        env=env,
        input=json.dumps(fields, separators=(",", ":")) + "\n",
    )
    if (
        not isinstance(out, dict)
        or out.get("stored") != "local"
        or out.get("auth_type") != "request_signature"
    ):
        raise SwytchcodeError(
            f"{provider} does not use signed requests; use save_key() or connect() instead",
            out,
        )


def disconnect(
    provider: str,
    tenant_id: str,
    *,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
) -> None:
    """Remove one end user's account for a provider, on this machine and on Swytchcode."""
    run_cli(
        ["auth", "disconnect", *_tenant_args(provider, tenant_id)],
        cwd=cwd,
        env=env,
        json_output=False,
    )
