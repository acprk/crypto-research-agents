# ChatGPT step by step

[中文版](../zh/integrations.md#chatgpt-逐步接入) · [Back to integrations](README.md)

> Status: the cra-mcp side is tested. That covers the HTTP transport, the secret path, and the
> Host/Origin checks for a tunnelled request carrying ChatGPT's Origin. The ChatGPT menu names below come
> from OpenAI's docs and recent third-party guides as of 2026-11. ChatGPT changes them often; if yours
> differ, look for "Developer mode" and "Create app".

## What you need
- A paid ChatGPT plan (Plus / Pro / Business / Enterprise / Edu). Developer mode is on **ChatGPT web**. OpenAI's
  pages differ on which plans may use *write* tools. If write calls are blocked on your plan, the read-only
  tools (`cra_resume`, `claim_list`, `gate_check`, `search`, `fetch`, …) still work.
- A computer that holds the research project, with cra installed (`pip install -e lib/core -e lib/mcp …`,
  see [README](README.md)).
- A tunnel program, because ChatGPT connects from OpenAI's cloud and cannot reach `localhost`.
  [cloudflared](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/)
  works without an account:
  `brew install cloudflared` · `winget install --id Cloudflare.cloudflared` · Linux: the .deb/.rpm from that page.

## 1. Project
```bash
cra init ~/papers/my-paper          # skip if it exists
cra-mcp doctor --project ~/papers/my-paper
```

## 2. Tunnel (terminal 1, keep it open)
```bash
cloudflared tunnel --url http://127.0.0.1:8765
```
Copy the `https://<random>.trycloudflare.com` URL it prints. A quick tunnel gets a new URL every time it
starts. For a stable URL, use a named Cloudflare tunnel or ngrok with a reserved domain.

## 3. Server (terminal 2, keep it open)
```bash
cra-mcp --project ~/papers/my-paper --http --profile remote --secret-path \
        --public-url https://<random>.trycloudflare.com
```
It prints a line like
`>>> paste this as the MCP server URL: https://<random>.trycloudflare.com/mcp/<secret>`.
- The `<secret>` part is stored in `<project>/.cra/mcp-secret`, which is git-ignored. It stays the same
  across server restarts, so the ChatGPT app keeps working while the tunnel URL is unchanged.
- To rotate the secret, add `--new-secret`.

## 4. ChatGPT
1. **Settings → Apps → Advanced settings → Developer mode: on.**
2. Still under Apps: **Create app**.
   - Name: `cra`.
   - MCP server URL: the `>>>` URL.
   - Authentication: **No authentication**. The secret path is the credential.
   - Tick that you trust the app, then create it.
3. ChatGPT now lists the tools: 21 in the remote profile. If it shows none, see Troubleshooting below.
4. Start a **new chat** → **+** → **Developer mode** → enable **cra**.
5. First message:
   > Use the cra app. Call cra_resume, then do the first task in next_tasks (load its role with role_card).
   > Report what changed.
6. Write tools (`claim_register`, `evidence_add`, `file_write`, …) ask for confirmation. Read the arguments
   before you approve them.

After updating cra, open the app in **Settings → Apps** and press **Refresh**, because ChatGPT caches tool
definitions.

## What works differently in ChatGPT
- ChatGPT has no shell, so it **cannot run experiments**. Run them on your machine. ChatGPT can then
  register the log with `evidence_add`, which only accepts logs that exist in the project, and cite the
  number.
- It reads and writes project files only through `file_read` / `file_write`. The ledgers (CLAIMS / EVIDENCE /
  DECISIONS) are refused there and must go through the typed tools.
- `search` / `fetch` also let ChatGPT's deep-research mode cite your project's notes and drafts.

## Troubleshooting
| Symptom | Fix |
|---|---|
| ChatGPT: "couldn't connect" / no tools | Both terminals must still be running. Open the `>>>` URL in a browser. A JSON line `"Not Acceptable: Client must accept text/event-stream"` means everything is reachable (browsers are not MCP clients); a Cloudflare error page means the tunnel is down. |
| Server log shows `Invalid Host header` (HTTP 421) | The tunnel URL changed. Restart step 3 with the new `--public-url`, then update the app's URL. |
| 404 | Wrong path: paste the full `>>>` URL, including `/mcp/<secret>`. |
| Tools are stale after an update | Settings → Apps → cra → Refresh. |
| Write call blocked | Your plan or workspace may not allow write actions in developer mode (admins can restrict it). Read-only tools still work. |

## Security
Anyone with the `>>>` URL can read and write the project's files through the tools, which stay inside the
project directory. Stop both terminals when you are done. Never paste the URL into shared chats or commit it.
cra has no tool that submits, e-mails or publishes anything.
