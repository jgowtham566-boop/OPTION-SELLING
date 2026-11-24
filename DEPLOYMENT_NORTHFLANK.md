# Deploying OPTION-SELLING to Northflank

This repository contains **Optopsy**, an options strategy backtesting engine and AI Chat UI (`optopsy-chat`) built on Python, Chainlit, FastAPI, and LiteLLM.

This guide explains how to deploy `jgowtham566-boop/OPTION-SELLING` to [Northflank](https://northflank.com).

---

## Architecture & Configuration Summary

| Setting | Value / Recommendation |
|---|---|
| **Service Type** | Combined Service (Build from Git & Deploy) |
| **Build Type** | Dockerfile (`Dockerfile` in root) |
| **Build Engine** | BuildKit |
| **Port** | `8000` (Protocol: `HTTP`, Public: `Yes`) |
| **Health Check Path** | `/health` (HTTP GET) |
| **Database** | Built-in SQLite (persistent with Volume mount) or Northflank PostgreSQL Addon |
| **Storage / Volume Mount** | (Optional) Mount volume at `/data` and set `OPTOPSY_DATA_DIR=/data` |

---

## Method 1: Deploy via Northflank UI (Recommended)

### Step 1: Create a Project
1. Log in to [Northflank](https://app.northflank.com).
2. Click **Create Project**.
3. Name it `option-selling` and select your preferred region.

### Step 2: (Optional) Create a Database Addon
Optopsy supports PostgreSQL for chat conversation persistence. If you want a managed database:
1. Under your project, click **Addons** -> **Create Addon**.
2. Select **PostgreSQL**.
3. Set the name to `optopsy-db` and select the deployment plan.
4. Click **Create Addon**. Once created, copy the connection string or link the addon's `DATABASE_URL` to your service.
*(Note: If you skip this, Optopsy will store data locally in SQLite).*

### Step 3: Create Combined Service
1. In your project dashboard, click **Create Service** -> **Combined Service**.
2. Service name: `option-selling-ui`.
3. In **Repository / VCS**:
   - Link your GitHub account if not already linked.
   - Select repository: `jgowtham566-boop/OPTION-SELLING`.
   - Branch: `main`.
4. In **Build Settings**:
   - Select **Dockerfile**.
   - Dockerfile path: `/Dockerfile`.
   - Build context: `/`.
   - Build engine: **BuildKit** (recommended for caching).
5. In **Networking**:
   - Add Port:
     - Name: `http`
     - Container port: `8000`
     - Protocol: `HTTP`
     - Enable **Public exposure** (this exposes a `*.northflank.app` URL and supports custom domains).
6. In **Health Checks**:
   - Add **Readiness Probe**:
     - Protocol: `HTTP`
     - Port: `8000`
     - Path: `/health`
     - Initial delay: `15s`, Period: `15s`, Timeout: `5s`
   - Add **Liveness Probe**:
     - Protocol: `HTTP`
     - Port: `8000`
     - Path: `/health`
     - Initial delay: `30s`, Period: `20s`, Timeout: `5s`
7. In **Environment Variables & Secrets**:
   Add the following variables:
   - `ANTHROPIC_API_KEY`: Your Anthropic API key (or set `OPENAI_API_KEY` if using OpenAI models).
   - `OPTOPSY_MODEL`: (Optional) e.g., `anthropic/claude-haiku-4-5-20251001` or `gpt-4o-mini` (defaults to Claude Haiku 4.5).
   - `EODHD_API_KEY`: (Optional) For fetching live options chains and historical market data from EODHD.
   - `DATABASE_URL`: (Optional) If you created the PostgreSQL addon, link or paste the PostgreSQL URL.
   - `PORT`: `8000`

### Step 4: (Optional) Persistent Volume for SQLite
If you are **not** using PostgreSQL, persist your SQLite database and cached options data by attaching a volume:
1. In the service setup or under service **Volumes**, click **Add Volume**.
2. Mount path: `/data`.
3. Size: `5 GB` (or desired size).
4. In Environment Variables, set `OPTOPSY_DATA_DIR=/data`.

### Step 5: Deploy
1. Click **Create Service**.
2. Northflank will trigger a build using BuildKit and deploy the container.
3. Once the build finishes and the `/health` check passes, your public HTTPS endpoint will be active!

---

## Method 2: Deploy using Northflank Template (`northflank.json`)

This repository includes a predefined template file: `northflank.json`.

1. Go to **Templates** in the Northflank sidebar.
2. Click **Create Template**.
3. Choose the **Code** tab.
4. Copy and paste the contents of [`northflank.json`](northflank.json).
5. Click **Save** and then click **Run Template**.
6. After provisioning, add your API keys under **Service Settings -> Variables**:
   - `ANTHROPIC_API_KEY` (or `OPENAI_API_KEY`)
   - `EODHD_API_KEY` (if downloading live options data)

---

## Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes* | Anthropic API key for Claude models (*or use `OPENAI_API_KEY`)* |
| `OPENAI_API_KEY` | Optional | OpenAI API key if using models like `gpt-4o`, `gpt-4o-mini` |
| `OPTOPSY_MODEL` | Optional | LiteLLM model string (default: `anthropic/claude-haiku-4-5-20251001`) |
| `EODHD_API_KEY` | Optional | API key for EODHD options and stock market data |
| `DATABASE_URL` | Optional | PostgreSQL connection URL (e.g. `postgresql://user:pass@host:5432/db`) |
| `OPTOPSY_DATA_DIR` | Optional | Directory for cache and SQLite DB (set to `/data` if mounting a volume) |
| `PORT` | Optional | Application listening port (defaults to `8000`) |

---

## Verification & Health Check

- **Health Check URL**: `https://<your-service-domain>.northflank.app/health` returns:
  ```json
  {"status": "ok"}
  ```
- **Web Interface**: Navigate to `https://<your-service-domain>.northflank.app` to access the Optopsy Chat UI.
