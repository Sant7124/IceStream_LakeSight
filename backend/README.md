# ⚡ Ice Stream — Backend Service

FastAPI operational gateway, streaming data quality engine, circuit breaker monitor, and Iceberg lakehouse API for Ice Stream.

---

## 📁 Architecture Overview

```text
backend/
├── app/
│   ├── api/            # REST endpoints & real-time WebSocket (/ws)
│   ├── config/         # Environment settings & configuration
│   ├── domain/         # Data contracts & transaction models
│   ├── ingestion/      # Kafka transactional producer & event generator
│   ├── logging/        # Structured JSON logging
│   ├── observability/  # Circuit Breaker, health evaluator & incident manager
│   ├── storage/        # Iceberg metadata catalog & Backblaze S3 mappings
│   └── validation/     # 8 canonical data-quality rules (DQ-001..008)
├── tests/              # Comprehensive unit and integration test suite
├── scripts/            # Incident simulation & verification utilities
├── Procfile            # Process manager for cloud platforms (Render / Railway)
├── pyproject.toml      # Packaging & testing configurations
├── requirements.txt    # Production runtime dependencies
└── .env.example        # Environment variable template
```

---

## 🚀 Local Development

### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment
Copy `.env.example` to `.env` (or link to repository root `.env`):
```bash
cp .env.example .env
```

### 3. Run FastAPI Backend
```bash
uvicorn app.api.main:app --host 127.0.0.1 --port 8000 --reload
```
Interactive Swagger documentation is available at `http://127.0.0.1:8000/docs`.

### 4. Run Tests
```bash
pytest
```

---

## ☁️ Deploying on Render (Free Tier — $0 / month)

Render provides a completely free tier for hosting web services.

1. Create a new **Web Service** on [Render](https://dashboard.render.com).
2. Connect your GitHub repository: `https://github.com/Sant7124/IceStream_LakeSight`.
3. Configure the service settings:
   - **Name**: `ice-stream-backend`
   - **Root Directory**: `backend`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.api.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: `Free` ($0)
4. Under **Environment Variables**, set:
   - `ALLOWED_ORIGINS`: `https://your-frontend-app.vercel.app` (your Vercel frontend URL)
   - `APP_ENV`: `production`
   - (Optional) Kafka, Backblaze B2, and SMTP keys as detailed in `.env.example`.
5. Click **Deploy Web Service**.

---

## 🔒 Security & Redaction

- Sensitive keys (`KAFKA_SASL_PASSWORD`, `B2_SECRET_ACCESS_KEY`, `EMAIL_PASSWORD`) are never exposed via REST endpoints.
- All `/api/system` and `/api/health` status endpoints automatically redact credentials.
- Zero secrets are committed to version control.
