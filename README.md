# Odin → Hermes Bridge

Give Odin (or any MCP-compatible agent) a way to hand off tasks it can't
do itself to a local [Hermes Agent](https://github.com/NousResearch/hermes-agent)
install — full terminal, file, browser, and coding tool access — and get
a real answer back.

No webhooks, no servers, no Telegram relay. Just one Python file that
Odin talks to directly on your own machine.

## What you get

Once set up, Odin gains one new tool: **`run_hermes_task`**. Whenever
Odin hits something outside its own capabilities, it can call this tool
with a task description and Hermes will actually go do it — run
commands, edit files, search the web, write code — then hand the
result straight back to Odin.

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

## How it works

1. Odin calls `run_hermes_task(task="...")`
2. The bridge script runs `hermes chat -q "<task>"` as a subprocess on
   your machine
3. Hermes runs its full agent loop (its own tools, memory, skills — all
   of it) until the task is done
4. The final text answer is returned to Odin as the tool result

Every call is a fresh, independent Hermes session — pass everything
Odin knows about the task into the `task` text, since Hermes can't see
Odin's conversation history.

## Configuration knobs

| Env var | Purpose | Default |
|---|---|---|
| `HERMES_BIN` | Full path to the `hermes` executable | first match on PATH |
| `HERMES_TASK_TIMEOUT` | Max seconds to wait for a task | `280` |

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
