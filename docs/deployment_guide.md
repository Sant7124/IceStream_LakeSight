# Ice Stream — Dual-Host Deployment Guide

This guide provides step-by-step instructions for deploying the **Frontend** and **Backend** of Ice Stream onto separate websites and servers.

---

## Architecture Overview

```text
┌───────────────────────────────────────┐
│              FRONTEND                 │
│  Hosted on: Vercel / Netlify / Render │
│  Domain: https://ice-stream.vercel.app│
└──────────────────┬────────────────────┘
                   │
         REST API  │  WebSocket
      HTTPS / JSON │  WSS / Frames
                   ▼
┌───────────────────────────────────────┐
│              BACKEND                  │
│ Hosted on: Render / Railway / Fly.io  │
│ Domain: https://api-icestream.com     │
│        (FastAPI + Uvicorn)            │
└──────────────────┬────────────────────┘
                   │
    ┌──────────────┼──────────────┐
    ▼              ▼              ▼
Aiven Kafka   Backblaze B2    DuckDB / SQLite
(SASL_SSL)   (Iceberg S3)   (Observability)
```

---

## 1. Backend Deployment (Render Free Web Service — $0 / month)

Render provides a completely free tier for Python web services with 512MB RAM and automatic HTTPS.

### Option A: 1-Click Render Blueprint (Recommended)
1. Log in to [Render](https://dashboard.render.com).
2. Click **New +** → **Blueprint**.
3. Select your repository `Ice-stream-lakehouse-observability`.
4. Render will detect `render.yaml` automatically, configure the free plan, set the root directory to `backend`, and prompt you only for your environment variables!

### Option B: Manual Web Service Setup
1. Click **New +** → **Web Service** on Render.
2. Connect your GitHub repository.
3. In settings:
   - **Name**: `ice-stream-backend`
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.api.main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: `Free` ($0)

### Step 3: Configure Environment Variables in Hosting Dashboard
> [!IMPORTANT]
> **Never commit your `.env` file to GitHub.** Add these environment variables directly inside the hosting provider's Dashboard (e.g., Render Environment tab, Railway Variables tab):

| Variable | Description | Example Value |
| :--- | :--- | :--- |
| `ALLOWED_ORIGINS` | Comma-separated list of your deployed frontend URLs | `https://ice-stream.vercel.app` |
| `APP_ENV` | Application environment | `production` |
| `KAFKA_BOOTSTRAP_SERVERS` | Aiven Kafka broker URL | `kafka-prod-xyz.aivencloud.com:12345` |
| `KAFKA_SECURITY_PROTOCOL` | Security protocol | `SASL_SSL` |
| `KAFKA_SASL_MECHANISMS` | SASL mechanism | `PLAIN` |
| `KAFKA_SASL_USERNAME` | Kafka SASL username | `avnadmin` |
| `KAFKA_SASL_PASSWORD` | Kafka SASL password | `your_sasl_password` |
| `B2_BUCKET_NAME` | Backblaze B2 bucket name | `ice-stream-lakehouse` |
| `B2_ENDPOINT` | Backblaze S3 endpoint | `https://s3.us-east-005.backblazeb2.com` |
| `B2_ACCESS_KEY_ID` | Backblaze B2 Key ID | `your_key_id` |
| `B2_SECRET_ACCESS_KEY` | Backblaze Application Key | `your_application_key` |
| `EMAIL_USER` | Notification Gmail sender | `Sant7124@gmail.com` |
| `EMAIL_PASSWORD` | 16-character Google App Password | `xxxx xxxx xxxx xxxx` |
| `SANTOSH_EMAIL` | Primary contact recipient | `Sant7124@gmail.com` |
| `COPY_EMAIL` | Secondary contact recipient (optional) | `Sant7124@gmail.com` |

---

## 2. Frontend Deployment (e.g. Vercel / Netlify / Cloudflare)

### Option A: Vercel (Recommended)
1. In Vercel, click **Add New Project** and import your GitHub repository.
2. In the project setup settings:
   - **Root Directory**: `frontend`
   - **Framework Preset**: `Vite`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
3. In **Environment Variables**, add:
   ```env
   VITE_API_URL=https://your-backend-service.onrender.com
   ```
   *(Optional: `VITE_WS_URL=wss://your-backend-service.onrender.com/ws` — if omitted, Ice Stream derives it automatically from `VITE_API_URL`)*.
4. Click **Deploy**.
5. Client-side SPA routing (`/console/pipeline`, `/console/quality`, etc.) is automatically handled by the included [`frontend/vercel.json`](../frontend/vercel.json).

### Option B: Netlify
1. In Netlify, click **Import an existing project** from GitHub.
2. Settings:
   - **Base directory**: `frontend`
   - **Build command**: `npm run build`
   - **Publish directory**: `frontend/dist`
3. In **Environment variables**, set `VITE_API_URL=https://your-backend-service.onrender.com`.
4. Client-side routing is automatically handled by [`frontend/public/_redirects`](../frontend/public/_redirects).

---

## 3. Connecting Frontend and Backend

1. Once the frontend is deployed (e.g., `https://ice-stream.vercel.app`), go to your **Backend Service** dashboard (e.g., on Render or Railway).
2. Update the `ALLOWED_ORIGINS` environment variable to include your frontend URL:
   ```env
   ALLOWED_ORIGINS=https://ice-stream.vercel.app
   ```
3. Restart the backend service.
4. Open `https://ice-stream.vercel.app` in your browser. All REST endpoints and live WebSocket telemetry will connect securely across hosts.

---

## 4. Credential & Secret Safety Checklist

- [x] `.env` is listed in `.gitignore` and is never committed.
- [x] `secrets/` (e.g. `ca.pem`) is listed in `.gitignore` and is never committed.
- [x] All client-facing JavaScript bundles (`dist/`) only contain public endpoints; zero secrets are bundled.
- [x] API responses redact all credentials, passwords, and tokens (`system.py` strict invariant).
- [x] Production secrets are injected exclusively through hosting provider environment variable managers.
