"""Run a swytchcode CLI subcommand with --json and parse the output."""

from __future__ import annotations

import json
import os
import subprocess
from typing import Any

from .errors import SwytchcodeError
from .exec import _resolve_bin


def run_cli(
    args: list[str],
    *,
    cwd: str | None = None,
    env: dict | None = None,
    timeout: float | None = 60,
    input: str | None = None,
    json_output: bool = True,
) -> Any:
    cmd = [_resolve_bin(), *args]
    if json_output and "--json" not in args:
        cmd.append("--json")

    run_env = os.environ.copy()
    if env:
        run_env.update(env)

    try:
        r = subprocess.run(
            cmd,
            input=input.encode("utf-8") if input is not None else None,
            capture_output=True,
            cwd=cwd or os.getcwd(),
            env=run_env,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as e:
        raise SwytchcodeError(
            "Failed to spawn swytchcode; is the CLI installed?", e
        ) from e
    except subprocess.TimeoutExpired as e:
        raise SwytchcodeError(
            f"swytchcode command timed out after {timeout}s", e
        ) from e

    if r.returncode != 0:
        raise SwytchcodeError(
            r.stderr.decode("utf-8", "replace").strip() or "command failed",
            r.returncode,
        )

    out = r.stdout.decode("utf-8", "replace").strip()
    if not out or not json_output:
        return None

    try:
        return json.loads(out)
    except json.JSONDecodeError as e:
        raise SwytchcodeError("Invalid JSON from swytchcode", out) from e
