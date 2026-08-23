# 🤖 GEMINI.md — Discord Bots Architecture, Operations & GitOps SOP

This document provides system context, architecture details, operational standards, and CI/CD GitOps workflows for developing, testing, and deploying Discord bots in this repository.

---

## 🏛️ Repository Overview & Tech Stack

- **Purpose**: Home repository for custom Discord automation bots (e.g. `weekly-boysnight-poll`).
- **Core Stack**: Python 3.12, `discord.py` (v2), `aiohttp`, `python-dotenv`, `zoneinfo`, `certifi`.
- **Target Infrastructure**: MiniPC k3s Kubernetes cluster in homelab LAN under the `discord-bots` namespace.
- **GitOps Config Repository**: [`/Users/codyuhi/dev/repos/app-deployments`](file:///Users/codyuhi/dev/repos/app-deployments) (`minipc/boys-night-bot/`).
- **Container Registry**: Private Harbor Registry at `harbor.minipc.local/library/`.
- **CI/CD Build Engine**: Argo Workflows on k3s using Kaniko executor (`workflowtemplate/docker-build-push`).

---

## 🧭 Server & Channel Topology

| Environment | Discord Server (Guild) | Guild ID | Channel Name | Channel ID | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Production** | shooty bois | — | `#shooty-bois` | `1194842799405797456` | Primary gaming poll target |
| **Testing** | SnakeCode | `1484997607465160796` | `#bot-tests` | `1540941534138994758` | Sandbox for verifying bot behavior |
| **Decommissioned** | Uhi Family | — | — | `1462649691383791680` | *Removed from deployments* |

### Test Webhook Endpoint
- **URL**: `https://discord.com/api/webhooks/1540942878115631146/L7TL3U8HVgrcZKO36l7CU__Kh39Kke4KiOfUcIzjASeLBrasukpXuOePUevavdzhGXlK`
- **Testing Utility**: [`scripts/test_webhook.py`](file:///Users/codyuhi/dev/repos/discord-bots/scripts/test_webhook.py) can be executed locally to test webhook deliverability.

---

## 🔑 Discord Bot Setup & Developer Portal Rules

- **Application ID / Client ID**: `1461893627411169433`
- **Privileged Gateway Intents**:
  - **Message Content Intent** MUST be enabled in the Discord Developer Portal under the **Bot** tab. Without this, the bot cannot read text-based prefix commands (`!sendpoll`, `!testpoll`).
- **Bot Permissions**: View Channels, Send Messages, Embed Links, Attach Files, Read Message History, Add Reactions (`permissions=274878024768`).
- **OAuth2 Invite Link**:
  ```
  https://discord.com/oauth2/authorize?client_id=1461893627411169433&permissions=274878024768&integration_type=0&scope=bot
  ```

---

## 📐 Bot Design & Coding Patterns

### 1. Multi-Channel Configuration
Bots must parse channel IDs flexibly to support single IDs, comma-separated lists, and explicit test channels:
```python
raw_channel_inputs = [
    os.getenv("CHANNEL_IDS", ""),
    os.getenv("CHANNEL_ID", ""),
    os.getenv("TEST_CHANNEL_ID", ""),
    os.getenv("SNAKECODE_TEST_CHANNEL_ID", ""),
    os.getenv("SHOOTY_BOIS_CHANNEL_ID", ""),
]
```

### 2. Context-Aware Command Responses
Commands like `!sendpoll` must respond directly in the channel where invoked (`target_channel=ctx.channel`), rather than broadcasting to all production channels:
```python
@bot.command(name="sendpoll", aliases=["testpoll"])
async def send_poll_command(ctx):
    await send_poll(target_channel=ctx.channel)
```

### 3. Dynamic Stateless RSVP & Clean Embed Layout
- **No Empty Groups**: Groups (`✅ Yes`, `⏰ Maybe/late`, `❌ No`) only render as embed fields if they have $\ge 1$ vote.
- **Vote Switching**: When a user clicks a new option, `update_card` strips their name from all existing lists before adding them to the selected list.
- **No Text Clutter**: Do not include placeholder strings (e.g. *"I plan to join"* or *"Unable to join"*) or footer timestamps.
- **Rotating Greetings**: Use `random.choice(POLL_MESSAGES)` to pick a friendly, lighthearted morning greeting when generating new cards.

---

## 🚀 End-to-End SOP: Updating and Deploying Bots

Follow this exact procedure whenever updating bot code or configs:

### Step 1: Update Bot Code & Push to GitHub
Make code changes in this repository (`discord-bots`), commit, and push to `origin/main`:
```bash
git add .
git commit -m "feat(poll): describe your change"
git push origin main
```

### Step 2: Build & Push Container Image via Argo Workflows
Trigger the Kaniko build on the MiniPC k3s cluster using `argo`:
```bash
argo submit --from workflowtemplate/docker-build-push -n argo-workflows \
  -p repo-name=discord-bots \
  -p image-name=boys-night-bot \
  -p image-tag=<new-tag> \
  -p dockerfile-path=weekly-boysnight-poll/Dockerfile \
  --wait
```

### Step 3: Update `app-deployments` (100% Pure GitOps)
1. In `/Users/codyuhi/dev/repos/app-deployments/minipc/boys-night-bot/values.yaml`, update `image.tag` to `<new-tag>`.
2. Re-render `out.yaml`:
   ```bash
   cd /Users/codyuhi/dev/repos/app-deployments
   helm template boys-night-bot minipc/boys-night-bot > minipc/boys-night-bot/out.yaml
   ```
3. Commit and push:
   ```bash
   git add minipc/boys-night-bot/
   git commit -m "feat(boys-night-bot): bump image to <new-tag>"
   git push origin main
   ```

### Step 4: ArgoCD Synchronization
ArgoCD's automated reconciler (`prune: true`, `selfHeal: true`) will detect the commit and roll out the new image to k3s.

> [!IMPORTANT]
> **Deployment Strategy (`Recreate`)**:
> The `Deployment` manifest MUST use `strategy: type: Recreate`. Because Discord bots maintain stateful Gateway WebSocket connections, `Recreate` ensures the old pod terminates before the new pod connects, preventing duplicate bot responses during rollouts.

---

## 🧪 Local Testing Workflow

1. Use the local virtual environment:
   ```bash
   cd /Users/codyuhi/dev/repos/discord-bots/weekly-boysnight-poll
   ../discord-venv/bin/python poll.py
   ```
2. Verify SSL / CA cert handling (`certifi` is loaded automatically in `poll.py` to support macOS local execution).
3. Test in Discord UI:
   - Go to **SnakeCode** server $\to$ **`#bot-tests`**.
   - Type `!sendpoll` to post a test card and test RSVP button clicks.
