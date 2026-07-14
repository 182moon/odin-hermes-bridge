# For Hermes: installing this bridge on behalf of a customer

If a user messages you (Hermes) something like **"install this: `https://github.com/182moon/odin-hermes-bridge`"**
or **"set up the Odin bridge"**, follow this procedure. Don't ask the
user to run anything manually — you have terminal access, do it yourself.

## Steps

1. **Confirm you can identify this chat's platform + chat ID.** You're
   almost certainly running inside a Telegram conversation with this
   user right now — that IS the delivery target for their scheduled
   tasks later. Note the chat ID (you know it from your own session
   context / origin metadata).

2. **Run the installer**, passing that chat ID as the argument:

   ```bash
   curl -fsSL https://raw.githubusercontent.com/182moon/odin-hermes-bridge/main/install.sh | bash -s -- <this_chat_id>
   ```

   This downloads the bridge script, installs its one dependency
   (`mcp`), and prints a fully-populated MCP config JSON to stdout —
   real `hermes` path, real `python3` path, real chat ID, no
   placeholders left for the user to fill in.

3. **Check the Hermes gateway/scheduler is actually running**, since
   scheduled jobs need it to fire later:

   ```bash
   hermes gateway status
   ```

   If it's not running, offer to set it up as a persistent background
   service:

   ```bash
   hermes gateway install
   hermes gateway start
   ```

4. **Hand the printed JSON block straight back to the user**, formatted
   for them to paste. Tell them exactly what to do with it:

   > "Setup's done on my end. Open Odin → MCP Servers → + Add, and
   > paste this in:"
   >
   > ```json
   > { ...the exact JSON you got back from the installer... }
   > ```
   >
   > "That's the only manual step left — I can't click buttons inside
   > Odin's own UI for you."

5. **Do not fabricate paths.** Only relay the JSON the installer script
   actually printed — if the script errored (missing hermes, missing
   python3, network failure), report the real error and what it means,
   don't invent a plausible-looking config anyway.

## What NOT to do

- Don't guess the user's Telegram chat ID from anywhere except your own
  live session context (never invent one).
- Don't tell the user to manually edit paths in the JSON — the whole
  point of this flow is that you already filled them in correctly.
- Don't claim you added the MCP server to Odin — you didn't, and can't;
  that click still belongs to the user.
