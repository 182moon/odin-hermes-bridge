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

# Short timeout for CLI management commands (create/list/remove) — these
# are near-instant, unlike run_hermes_task which runs a full agent loop.
CRON_CLI_TIMEOUT = 30

mcp = FastMCP("hermes-task-bridge")


def _run_hermes_cli(args, timeout=CRON_CLI_TIMEOUT):
    """Run a hermes CLI subcommand and return (ok, stdout_or_error)."""
    try:
        proc = subprocess.run(
            [HERMES_BIN, *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return False, f"ERROR: '{' '.join(args)}' timed out after {timeout}s."
    except FileNotFoundError:
        return False, (
            f"ERROR: could not find the 'hermes' executable at '{HERMES_BIN}'. "
            "Set the HERMES_BIN environment variable to the full path to your "
            "hermes binary (find it by running `which hermes` in a terminal)."
        )

    if proc.returncode != 0:
        stderr_tail = (proc.stderr or "").strip()[-1500:]
        stdout_tail = (proc.stdout or "").strip()[-500:]
        return False, f"ERROR: exited with code {proc.returncode}.\n{stderr_tail or stdout_tail}"

    return True, proc.stdout.strip()


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


@mcp.tool()
def schedule_hermes_task(
    schedule: str,
    task: str,
    name: str = "",
    repeat: int = 0,
) -> str:
    """Create a RECURRING scheduled job that Hermes runs on its own, independent of Odin.

    Use this for anything that should happen automatically on a timer —
    a morning routine, a daily report, a periodic check — rather than a
    one-off task run via run_hermes_task. The job is created inside the
    user's own Hermes install and keeps running even if Odin isn't open,
    as long as the Hermes gateway/scheduler is running on their machine.

    Args:
        schedule: When to run it. Accepts a duration ("30m", "2h"), an
            "every" phrase ("every day at 7am", "every monday 9am"), a
            5-field cron expression ("0 7 * * *"), or an ISO timestamp
            for a one-shot run.
        task: A full, self-contained description of what Hermes should
            do each time it runs. Include everything it needs — it has
            no memory of this conversation between runs.
        name: Optional human-friendly name for the job (helps identify
            it later in list_scheduled_tasks).
        repeat: Optional number of times to run before stopping. Leave
            at 0 for "repeat forever" (or once, if schedule is one-shot).
    """
    if not schedule or not schedule.strip():
        return "ERROR: schedule is required (e.g. 'every day at 7am' or '0 7 * * *')."
    if not task or not task.strip():
        return "ERROR: task text is required."

    args = ["cron", "create", schedule, task]
    if name.strip():
        args += ["--name", name.strip()]
    if repeat and repeat > 0:
        args += ["--repeat", str(repeat)]

    ok, output = _run_hermes_cli(args)
    if not ok:
        return output
    return output or "Scheduled job created."


@mcp.tool()
def list_scheduled_tasks(include_disabled: bool = False) -> str:
    """List recurring jobs currently scheduled in the user's Hermes install.

    Use this to check what's already scheduled before creating a
    duplicate, or to find a job's ID so it can be removed.

    Args:
        include_disabled: If true, also show paused/disabled jobs.
    """
    args = ["cron", "list"]
    if include_disabled:
        args.append("--all")

    ok, output = _run_hermes_cli(args)
    if not ok:
        return output
    return output or "No scheduled jobs found."


@mcp.tool()
def remove_scheduled_task(job_id: str) -> str:
    """Delete a recurring scheduled job from the user's Hermes install.

    Args:
        job_id: The job ID to remove, as shown by list_scheduled_tasks.
    """
    if not job_id or not job_id.strip():
        return "ERROR: job_id is required. Call list_scheduled_tasks first to find it."

    ok, output = _run_hermes_cli(["cron", "remove", job_id.strip()])
    if not ok:
        return output
    return output or f"Removed scheduled job {job_id}."


if __name__ == "__main__":
    mcp.run()
