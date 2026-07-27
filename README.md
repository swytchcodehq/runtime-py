# swytchcode-runtime (Python)

Thin runtime wrapper around the Swytchcode CLI. Calls `swytchcode exec` for you so you can stay in Python without shell boilerplate.

**Requires:** The `swytchcode` CLI must be installed. The binary is located automatically - no configuration needed in most environments. Resolution order:

1. `SWYTCHCODE_BIN` env var - explicit override.
2. `$PATH` lookup via `shutil.which` - the standard system resolution.
3. Common install paths - `~/.local/bin`, `/usr/local/bin` (Unix) or `%LOCALAPPDATA%\Programs\swytchcode\bin` (Windows).

## Install

```bash
pip install swytchcode-runtime
```

Or from the repo:

```bash
pip install /path/to/runtime-libraries/python-runtime
```

## Use

### JSON mode (default)

```python
from swytchcode_runtime import exec

result = exec("api.account.create", {"email": "test@example.com"})
# result is parsed JSON (any)
```

Equivalent to: `swytchcode exec api.account.create --json` with args on stdin.

**Request input (args):** The second argument is the kernel **args** object (sent as JSON on stdin). Use this shape so the kernel builds the request correctly:
- **body** - Request body (dict).
- **params** - Query/path params (e.g. `{"id": "cluster-123"}`).
- **Authorization** - Auth header value (e.g. `"Bearer token123"`).
- **headers** - Additional request headers (e.g. `{"X-Request-Id": "abc-123"}`).
- Other top-level keys are passed as query params.

Example with body, params, and headers:

```python
exec("api.cluster.get", {
    "params": {"id": "cluster-123"},
    "Authorization": "Bearer token123",
    "headers": {"X-Request-Id": "abc-123"},
})
```

### Raw mode

Get stdout as a string instead of parsing JSON:

```python
from swytchcode_runtime import exec

output = exec("api.report.export", {"id": "123"}, raw=True)
# output is the raw stdout string
```

### Options

- **cwd** - Working directory for the process (default: current directory).
- **env** - Extra environment variables (merged with `os.environ`).
- **raw** - If `True`, use `--raw` and return stdout as a string.
- **dry_run** - If `True`, pass `--dry-run` to the CLI; request details (method, url, headers, body) are output instead of calling the server.
- **allow_raw** - If `True`, pass `--allow-raw` to the CLI; required for executing raw methods (kernel has this disabled by default).

This runtime invokes `swytchcode exec [canonical_id]` with the flags above. For full exec behavior, see the Swytchcode kernel documentation.

### Environment variables

This runtime itself needs no environment configuration to run - all auth lives in the CLI's own session (`swytchcode login`, stored under `~/.swytchcode/`) or in `.swytchcode/` in your project. The variables below are for the rarer cases where you need to override that:

| Variable | Description |
|----------|-------------|
| `SWYTCHCODE_BIN` | Override the resolved binary path. Set this only when automatic resolution does not find the correct binary (e.g. non-standard install locations or virtualised environments). |
| `SWYTCHCODE_TOKEN` | Service-token auth for headless environments (CI, servers) where an interactive `swytchcode login` isn't possible. Not needed for local development once you've run `swytchcode login`. |

### Error handling

Failures raise `SwytchcodeError` (spawn error, non-zero exit, invalid JSON). Use the helper to narrow:

```python
from swytchcode_runtime import exec, SwytchcodeError, is_swytchcode_error

try:
    exec("api.account.create", {"email": "test@example.com"})
except Exception as e:
    if is_swytchcode_error(e):
        print(e.message, e.cause)
    raise
```

On a non-zero exit the CLI writes a classified JSON error to stderr; `exec()` parses it into a clean `.message` and a structured `.details` dict (`category`, `retryable`, `suggested_action`, `docs_url`) instead of leaving you to parse the raw JSON yourself:

```python
except SwytchcodeError as e:
    if e.details and e.details.get("category") == "auth":
        print(e.details.get("suggested_action"))
```

## What this library is

- A thin process wrapper over the Swytchcode shell.
- A stable call surface: `exec(canonical_id, input=None, *, cwd=..., env=..., raw=...)`.
- A convenience for developers and IDE agents.

## What this library is not

- An HTTP SDK or API client.
- A replacement for the shell. All authority stays in the Swytchcode CLI.

This library **must not** and **does not**:

- Read `.swytchcode/*` or parse `tooling.json`.
- Validate schemas or add retries/timeouts.
- Call the registry or embed auth logic.

It is a pipe, not a brain.

## For Cursor / IDE agents

Generate code that uses this runtime instead of subprocess boilerplate.

**Preferred:**

```python
from swytchcode_runtime import exec

def create_account(input: dict) -> any:
    return exec("api.account.create", input)
```

**Avoid:** subprocess boilerplate, HTTP calls, or config parsing. Use `exec(...)` and let the CLI handle execution and policy.

## Agentic workflows (framework integrations)

For full, production-ready examples across all major frameworks, check out the [Swytchcode Examples Repository](https://github.com/swytchcodehq/swytchcode-examples).

On top of `exec`, the runtime exposes a small agentic surface that turns Swytchcode tools into the native tool objects each agent framework expects. 

### Tool-use guidance - `TOOL_USE_INSTRUCTIONS`

Without an explicit nudge, models can be conservative about side-effecting actions (starring a repo, sending a payment, creating an issue) - they'll describe what they *would* do instead of actually calling the tool. `TOOL_USE_INSTRUCTIONS` is a short, framework-agnostic string that fixes this; concatenate it into whatever your provider calls its system prompt / instructions. It's scoped to only the tools this library provides, so it's safe to combine with instructions for other, unrelated tools in the same system prompt:

```python
from swytchcode_runtime import TOOL_USE_INSTRUCTIONS

system = f"You are a helpful assistant.\n\n{TOOL_USE_INSTRUCTIONS}"
```

### Quickstart: Anthropic SDK

Here is a clean example of building a simple agent using the Anthropic SDK. It stars the [Swytchcode Examples repo](https://github.com/swytchcodehq/swytchcode-examples) on GitHub - a genuine OAuth-connected action (not just an API key passed on the request), so the setup below covers the real one-time flow: installing the CLI, logging in, and connecting a GitHub account.

**One-time setup** (run once per machine/project):

```bash
# 1. Install the CLI (macOS/Linux; see https://cli.swytchcode.com for other platforms)
curl -fsSL https://cli.swytchcode.com/install.sh | sh

# 2. Scaffold .swytchcode/ + tooling.json in your project
swytchcode init

# 3. Log in (opens a browser; creates your Swytchcode session)
swytchcode login

# 4. Fetch the GitHub integration
swytchcode get github

# 5. Enable the "star a repo" tool - the trust boundary for what this project can call
swytchcode add user.starred.update

# 6. Connect your GitHub account (opens a browser for the OAuth flow)
swytchcode auth connect github
```

Then add your Anthropic key to a `.env` file in your project root (used by `python-dotenv` below):

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...
```

**Installation:**
```bash
pip install swytchcode-runtime anthropic python-dotenv
```
*(Note: You only need to install the SDK for the framework you are actually using. You **do not** need to install `openai-agents` or `langchain` if you are only using Anthropic. The `swytchcode-runtime` isolates these dependencies via lazy loading.)*

**Example:**
```python
import os
from dotenv import load_dotenv
import anthropic
from swytchcode_runtime import Swytchcode, TOOL_USE_INSTRUCTIONS
from swytchcode_runtime.providers.anthropic import AnthropicProvider

load_dotenv()  # Loads .env automatically

def run_agent():
    client = anthropic.Anthropic()

    # 1. Initialize Swytchcode with the Anthropic provider
    swx = Swytchcode(provider=AnthropicProvider())

    # 2. Fetch the tools you want your agent to use (e.g., GitHub tools)
    tools = swx.tools.get(toolkits=["github"])

    # 3. Build the system prompt: your own instructions plus TOOL_USE_INSTRUCTIONS,
    # which tells Claude to call the tool directly for action requests instead of
    # just describing what it would do
    system = f"You are a helpful assistant.\n\n{TOOL_USE_INSTRUCTIONS}"

    response = client.messages.create(
        model="claude-3-5-sonnet-latest",
        max_tokens=1024,
        system=system,
        tools=tools,
        messages=[{"role": "user", "content": "Star the swytchcodehq/swytchcode-examples repo on GitHub for me."}],
    )

    # 4. Run any tool calls Claude made and send the results back
    results = swx.handle_tool_calls(response)
    print(results)

if __name__ == "__main__":
    run_agent()
```

### Selecting tools - `swx.tools.get(...)`

Pass exactly one selector; IDs resolve against your local Swytchcode state and remote search:

- `toolkits=["stripe"]` - every enabled tool whose integration matches a toolkit.
- `tools=["charges.charge.create"]` - explicit canonical IDs.
- `search="refund a charge"` - natural-language discovery (via `swytchcode discover`).

Each returned tool carries a **full input schema** - every field is surfaced to the model, with
only the truly-required ones marked `required` - and an `execute` callback that runs `swytchcode
exec` for you (empty optional values are stripped before the call so APIs like Stripe don't reject them).

### Supported providers

| Framework | Import | Who runs the tool loop |
|-----------|--------|------------------------|
| Anthropic Claude | `from swytchcode_runtime.providers.anthropic import AnthropicProvider` | you (Messages API + `swx.handle_tool_calls`) |
| OpenAI Agents SDK | `from swytchcode_runtime.providers.openai_agents import OpenAIAgentsProvider` | the SDK |
| Vercel AI SDK | `from swytchcode_runtime.providers.vercel import VercelProvider` | the SDK |
| LangGraph | `from swytchcode_runtime.providers.langgraph import LangGraphProvider` | the prebuilt agent |
| CrewAI | `from swytchcode_runtime.providers.crewai import CrewAIProvider` | the crew |

### Non-agentic APIs (Anthropic Messages)

When you run the tool loop yourself, `handle_tool_calls` executes each `tool_use` block and
returns the `tool_result` blocks to send back:

```python
import anthropic
client = anthropic.Anthropic()
msg = client.messages.create(
    model="claude-sonnet-5", max_tokens=1024, tools=tools,
    messages=[{"role": "user", "content": "Refund charge ch_123 for $20"}],
)
results = swx.handle_tool_calls(msg)   # runs the tool calls, returns tool_result blocks
```

One runnable file per framework lives in `sdk-examples/`. Install the matching framework SDK
(`pip install openai-agents` / `anthropic` / `ai` / `langgraph` / `crewai`) alongside the
`swytchcode` CLI.
