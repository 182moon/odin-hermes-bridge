# Odin → Hermes Bridge

Give Odin (or any MCP-compatible agent) a way to hand off tasks it can't
do itself to a local [Hermes Agent](https://github.com/NousResearch/hermes-agent)
install — full terminal, file, browser, and coding tool access — and get
a real answer back.

No webhooks, no servers, no Telegram relay. Just one Python file that
Odin talks to directly on your own machine.

## What you get

Once set up, Odin gains four new tools:

| Tool | What it does |
|---|---|
| **`run_hermes_task`** | Hand off a one-off task Odin can't do itself — Hermes runs it now and returns the result |
| **`schedule_hermes_task`** | Set up a RECURRING job (a morning routine, daily report, etc.) that Hermes runs on its own schedule, independent of Odin |
| **`list_scheduled_tasks`** | See what's currently scheduled |
| **`remove_scheduled_task`** | Cancel a scheduled job |

`run_hermes_task` runs a full agent loop for a single task and returns
the answer — use it for anything "do this now." `schedule_hermes_task`
sets up a recurring job inside the user's own Hermes install using
Hermes's built-in cron scheduler — use it for "do this every morning /
every day / every Monday," etc. Scheduled jobs keep running even when
Odin isn't open, as long as Hermes's own gateway/scheduler process is
running on the user's machine (check with `hermes cron status`).

**Important — where scheduled results go:** Odin only *creates* the
job; it has no way to receive results back later, since the job runs
completely independently. `schedule_hermes_task` delivers results to a
**Telegram chat** (the chat ID you already use with Hermes), not back
into Odin. If you don't pass a `telegram_chat_id` (or set
`HERMES_TELEGRAM_CHAT_ID` as a default — see Configuration knobs
below), the job is created with `deliver=local` and its output only
shows up in `list_scheduled_tasks` / `hermes cron list` — nobody gets
notified. For an actual "morning briefing that lands on your phone,"
you need Hermes's Telegram gateway already connected
(`hermes gateway setup`) and pass that chat's ID.

## Requirements

- macOS, Linux, or WSL (same as Hermes itself)
- Python 3.9+
- [Hermes Agent](https://github.com/NousResearch/hermes-agent) installed
  and configured with a working model (you'll use your own OpenRouter/
  Anthropic/etc. key, same as Odin)

## Setup (5 minutes)

### 1. Install Hermes, if you haven't already

```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
hermes setup
```

Confirm it works:

```bash
hermes chat -q "say hello"
```

### 2. Download this bridge folder

Save `hermes_task_server.py` and `requirements.txt` from this folder
somewhere on your machine, e.g. `~/hermes-mcp-bridge/`.

### 3. Install the one dependency

```bash
pip3 install -r ~/hermes-mcp-bridge/requirements.txt
```

(This installs the `mcp` Python package — the bridge script needs it to
speak the MCP protocol. It's separate from Hermes itself.)

### 4. Find your `hermes` path

```bash
which hermes
```

Copy that path — you'll need it in the next step if `hermes` isn't
already on Odin's PATH.

### 5. Add Hermes as an MCP server in Odin

Open Odin → **MCP Servers** → **+ Add** → paste config, editing the
paths to match your machine:

```json
{
  "mcpServers": {
    "hermes": {
      "command": "python3",
      "args": ["/Users/yourname/hermes-mcp-bridge/hermes_task_server.py"],
      "env": {
        "HERMES_BIN": "/Users/yourname/.local/bin/hermes"
      }
    }
  }
}
```

Save. Odin should now show `run_hermes_task` as an available tool.

### 6. Test it

In Odin, ask it something you know it can't do on its own — e.g. "use
Hermes to list the files in my Downloads folder" — and confirm it
calls the tool and comes back with a real answer.

Then test scheduling — ask Odin something like "set up a Hermes job
that runs every morning at 7am and gives me a weather + calendar
briefing." Confirm it shows up with `hermes cron list` in a terminal,
or ask Odin to list your scheduled tasks.

### 7. Keep the scheduler running

Recurring jobs created with `schedule_hermes_task` only fire while
Hermes's scheduler is actually running in the background — not just
when Odin happens to be open. Check status with:

```bash
hermes cron status
```

If it's not running, either start it in the foreground for testing:

```bash
hermes gateway run
```

(stays alive only while that terminal window is open — good for a
quick test, not for production)

or install it as a real background service that survives reboots and
terminal closures:

```bash
hermes gateway install
hermes gateway start
hermes gateway status   # confirm it's running
```

## How it works

**One-off tasks (`run_hermes_task`):**
1. Odin calls `run_hermes_task(task="...")`
2. The bridge script runs `hermes chat -q "<task>"` as a subprocess on
   your machine
3. Hermes runs its full agent loop (its own tools, memory, skills — all
   of it) until the task is done
4. The final text answer is returned to Odin as the tool result

**Recurring tasks (`schedule_hermes_task`):**
1. Odin calls `schedule_hermes_task(schedule="every day at 7am", task="...")`
2. The bridge runs `hermes cron create` under the hood, registering a
   real job in the user's own Hermes install
3. Hermes's own scheduler fires the job on schedule — with or without
   Odin open — as long as the Hermes gateway/scheduler is running
4. `list_scheduled_tasks` / `remove_scheduled_task` wrap `hermes cron
   list` / `hermes cron remove` so Odin can manage jobs it created

Every call is independent — pass everything the calling agent knows
about the task into the `task` text, since Hermes can't see Odin's
conversation history or previous scheduled runs.

## Configuration knobs

| Env var | Purpose | Default |
|---|---|---|
| `HERMES_BIN` | Full path to the `hermes` executable | first match on PATH |
| `HERMES_TASK_TIMEOUT` | Max seconds to wait for a task | `280` |
| `HERMES_TELEGRAM_CHAT_ID` | Default Telegram chat ID for `schedule_hermes_task` results, so Odin doesn't need to ask for it every time | none — must be passed per call if unset |

Find your Telegram chat ID by messaging your Hermes bot once, then
checking `hermes gateway status` or your Hermes logs for the chat ID,
or by asking Hermes itself "what's this chat's ID" in a Telegram
conversation with it.

Set these in the `"env"` block of the MCP config shown above.

## Troubleshooting

**"No module named mcp"**
Run `pip3 install mcp` using the exact `python3` your MCP config's
`"command"` points to. If you have multiple Python installs, use the
full path in both the install command and the config, e.g.
`/usr/bin/python3 -m pip install mcp`.

**"could not find the 'hermes' executable"**
Set `HERMES_BIN` in the MCP config's `"env"` block to the output of
`which hermes`.

**Tool call times out on long tasks**
Raise `HERMES_TASK_TIMEOUT` in the `"env"` block (seconds), or ask Odin
to pass a higher `timeout_seconds` per call.

**Odin doesn't see the tool after adding the server**
Restart Odin, or check its MCP server list for a connection error —
usually a wrong path in `"args"` or `"env"`.

## Security note

This bridge runs Hermes with whatever tool access and permissions your
Hermes install already has configured (terminal commands, file access,
etc.). Anything Odin delegates through this tool runs with those same
permissions on your machine. Only connect this to agents you trust.
