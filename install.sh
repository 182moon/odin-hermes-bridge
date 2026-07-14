#!/usr/bin/env bash
# install.sh — one-shot installer for the Odin <-> Hermes MCP bridge.
#
# Designed to be run BY Hermes itself (as an agent, when a customer tells
# it "install this" and pastes the repo URL) or by a human directly.
#
# What it does:
#   1. Detects the running `hermes` binary path
#   2. Detects the python3 interpreter to run the bridge with
#   3. Downloads hermes_task_server.py + requirements.txt into
#      ~/.hermes/integrations/odin-bridge/
#   4. Installs the `mcp` python package for that interpreter
#   5. Prints a ready-to-paste MCP config JSON with real paths filled in
#      (Telegram chat ID is left as a placeholder here — see AGENTS.md
#      for how an agent fills that in automatically from its own context)
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/182moon/odin-hermes-bridge/main/install.sh | bash
#
# Optional: pass a Telegram chat ID as the first argument to bake it
# directly into the printed config:
#   bash install.sh 476002436

set -euo pipefail

REPO_RAW="https://raw.githubusercontent.com/182moon/odin-hermes-bridge/main"
INSTALL_DIR="${HERMES_ODIN_BRIDGE_DIR:-$HOME/.hermes/integrations/odin-bridge}"
CHAT_ID="${1:-}"

echo "== Odin <-> Hermes bridge installer ==" >&2

# --- 1. Find hermes binary ---
HERMES_BIN="$(command -v hermes || true)"
if [ -z "$HERMES_BIN" ]; then
  echo "ERROR: 'hermes' not found on PATH. Install Hermes Agent first:" >&2
  echo "  curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash" >&2
  exit 1
fi
echo "Found hermes at: $HERMES_BIN" >&2

# --- 2. Find python3 ---
PYTHON_BIN="$(command -v python3 || true)"
if [ -z "$PYTHON_BIN" ]; then
  echo "ERROR: python3 not found on PATH." >&2
  exit 1
fi
echo "Using python3 at: $PYTHON_BIN" >&2

# --- 3. Download bridge files ---
mkdir -p "$INSTALL_DIR"
curl -fsSL "$REPO_RAW/hermes_task_server.py" -o "$INSTALL_DIR/hermes_task_server.py"
curl -fsSL "$REPO_RAW/requirements.txt" -o "$INSTALL_DIR/requirements.txt"
echo "Installed bridge script to: $INSTALL_DIR/hermes_task_server.py" >&2

# --- 4. Install the mcp package ---
"$PYTHON_BIN" -m pip install -q -r "$INSTALL_DIR/requirements.txt"
echo "Installed 'mcp' python package for $PYTHON_BIN" >&2

# --- 5. Print the ready-to-paste config ---
echo "" >&2
echo "== Setup complete. Paste this into Odin's MCP Servers > + Add: ==" >&2
echo "" >&2

if [ -n "$CHAT_ID" ]; then
  cat <<EOF
{
  "mcpServers": {
    "hermes": {
      "command": "$PYTHON_BIN",
      "args": ["$INSTALL_DIR/hermes_task_server.py"],
      "env": {
        "HERMES_BIN": "$HERMES_BIN",
        "HERMES_TELEGRAM_CHAT_ID": "$CHAT_ID"
      }
    }
  }
}
EOF
else
  cat <<EOF
{
  "mcpServers": {
    "hermes": {
      "command": "$PYTHON_BIN",
      "args": ["$INSTALL_DIR/hermes_task_server.py"],
      "env": {
        "HERMES_BIN": "$HERMES_BIN",
        "HERMES_TELEGRAM_CHAT_ID": "REPLACE_WITH_YOUR_TELEGRAM_CHAT_ID"
      }
    }
  }
}
EOF
  echo "" >&2
  echo "NOTE: no Telegram chat ID was provided to this script, so" >&2
  echo "HERMES_TELEGRAM_CHAT_ID above is a placeholder. If an agent is" >&2
  echo "running this on your behalf inside a Telegram chat, it should" >&2
  echo "already know that chat's ID and substitute it in automatically." >&2
fi
