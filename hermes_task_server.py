#!/usr/bin/env python3
"""
Hermes Task Bridge — MCP server exposing one tool: run_hermes_task.

Lets any MCP-compatible client (Odin, Claude Desktop, Cursor, etc.) hand off
a task it can't do itself to a local Hermes Agent installation, and get the
final answer back synchronously.

Hermes runs the FULL agent loop for the task (terminal, files, browser,
web search, code execution, delegation to other coding agents, etc.) and
returns its final text response.

--------------------------------------------------------------------------
SETUP (customer-facing — see README.md for the full walkthrough)
--------------------------------------------------------------------------
1. Install Hermes Agent if you haven't:
     curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash

2. Install the MCP python package (only needed to RUN this bridge script,
   not part of Hermes itself):
     pip3 install mcp

3. In your MCP client (e.g. Odin's "MCP Servers" panel), click "+ Add" and
   paste this config, editing the path to wherever you saved this file:

   {
     "mcpServers": {
       "hermes": {
         "command": "python3",
         "args": ["/full/path/to/hermes_task_server.py"]
       }
     }
   }

4. That's it. Your agent can now call the "run_hermes_task" tool whenever
   it hits something it can't do on its own.

--------------------------------------------------------------------------
Troubleshooting
--------------------------------------------------------------------------
- "hermes: command not found" errors coming back from the tool: Hermes
  isn't on PATH for the process that launches this script. Either add
  Hermes's install directory to PATH, or set an explicit HERMES_BIN env
  var in the MCP client config, e.g.:

    "env": { "HERMES_BIN": "/Users/you/.local/bin/hermes" }

- "No module named mcp": run `pip3 install mcp` using the SAME python3
  that your MCP client's "command" points to.

- Tasks time out: raise HERMES_TASK_TIMEOUT (seconds, default 280) in the
  MCP client's "env" block, or pass timeout_seconds explicitly per call.
"""
import os
import shutil
import subprocess
import sys

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    sys.stderr.write(
        "ERROR: the 'mcp' package is not installed for this Python.\n"
        "Install it with: pip3 install mcp\n"
    )
    sys.exit(1)

# Resolve the hermes binary: explicit env var wins, then PATH lookup.
HERMES_BIN = os.environ.get("HERMES_BIN") or shutil.which("hermes") or "hermes"

# Default timeout, overridable via env var so customers don't have to edit code.
DEFAULT_TIMEOUT = int(os.environ.get("HERMES_TASK_TIMEOUT", "280"))

mcp = FastMCP("hermes-task-bridge")


@mcp.tool()
def run_hermes_task(task: str, timeout_seconds: int = DEFAULT_TIMEOUT) -> str:
    """Delegate a task to a local Hermes Agent and return its final answer.

    Use this when the calling agent cannot complete a task itself —
    coding, file operations, terminal commands, web research/browsing,
    or anything requiring a full tool-using agent loop. Hermes runs the
    task to completion using its own tools and returns the final result
    as plain text.

    Args:
        task: A full, self-contained description of what to do. Include
            all context the task needs — Hermes has no memory of the
            calling agent's conversation, files it referenced, or prior
            turns. Be explicit (file paths, URLs, exact wording wanted).
        timeout_seconds: Max time to wait for Hermes to finish. Increase
            for long research/coding tasks.
    """
    if not task or not task.strip():
        return "ERROR: task text is required."

    try:
        proc = subprocess.run(
            [HERMES_BIN, "chat", "-q", task, "-Q"],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return (
            f"ERROR: Hermes did not finish within {timeout_seconds}s. "
            "The task may still be running in its own session — try again "
            "with a higher timeout_seconds, or check Hermes directly."
        )
    except FileNotFoundError:
        return (
            f"ERROR: could not find the 'hermes' executable at '{HERMES_BIN}'. "
            "Set the HERMES_BIN environment variable to the full path to your "
            "hermes binary (find it by running `which hermes` in a terminal)."
        )

    if proc.returncode != 0:
        stderr_tail = (proc.stderr or "").strip()[-2000:]
        return f"ERROR: Hermes exited with code {proc.returncode}.\nstderr:\n{stderr_tail}"

    # Strip harmless startup warnings that shouldn't be shown to the caller.
    noisy_prefixes = ("Warning: Unknown toolsets",)
    lines = [
        line for line in proc.stdout.splitlines()
        if not line.startswith(noisy_prefixes)
    ]
    output = "\n".join(lines).strip()
    return output if output else "(Hermes finished with no text output.)"


if __name__ == "__main__":
    mcp.run()
