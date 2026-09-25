# 🚀 Production Deployment Guide: MedEdge Intelligence

This guide explains how to deploy **MedEdge Intelligence** to a public HTTPS URL (such as `https://mededge-intelligence.onrender.com`) so it can be accessed from any device (mobile phones, laptops, tablets, iPads) without running localhost.

---

## 🏗️ Architecture Overview

- **Deployment Platform:** [Render](https://render.com) (Free Tier Web Service + Free Managed PostgreSQL)
- **Frontend & Backend Hosting:** Single-Service Deployment (FastAPI serves both the REST APIs, WebSockets, and HTML5/JS frontend pages from `/static`).
- **Database:** PostgreSQL in production (automatically falls back to SQLite `mededge.db` for local offline development).
- **Communication:** Real-time WebSockets (`/ws/telemetry`) & REST APIs over public HTTPS (`https://...` and `wss://...`).

---

## 📋 Step-by-Step Deployment Instructions

### Step 1: Push Project to GitHub

1. Open your terminal in the `MEDEDGE` project directory.
2. Initialize Git (if not already initialized) and commit all files:
   ```bash
   git init
   git add .
   git commit -m "Prepare MedEdge Intelligence for production deployment"
   ```
3. Create a new repository on [GitHub](https://github.com/new) named `mededge-intelligence`.
4. Link your local repository and push to GitHub:
   ```bash
   git remote add origin https://github.com/YOUR_GITHUB_USERNAME/mededge-intelligence.git
   git branch -M main
   git push -u origin main
   ```

---

### Step 2: Deploy Database & Web Service on Render

#### Option A: One-Click Render Blueprint (Recommended)

1. Sign in or create a free account at [Render.com](https://render.com).
2. Click **New +** in the top header and select **Blueprint**.
3. Connect your GitHub account and select your `mededge-intelligence` repository.
4. Render will automatically detect `render.yaml` and configure:
   - **PostgreSQL Database** (`mededge-db`)
   - **Web Service** (`mededge-intelligence`) with command `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Click **Apply**. Render will automatically provision PostgreSQL and deploy your web application!

#### Option B: Manual Setup on Render (Alternative)

If you prefer setting up services manually on Render:

1. **Create PostgreSQL Database:**
   - On Render Dashboard, click **New +** &rarr; **PostgreSQL**.
   - Set Name: `mededge-db` | Database: `mededgedb` | User: `mededge_user`.
   - Select **Free Plan** and click **Create Database**.
   - Copy the **Internal Database URL** (e.g. `postgres://mededge_user:...@dpg-...-a/mededgedb`).

2. **Create Web Service:**
   - On Render Dashboard, click **New +** &rarr; **Web Service**.
   - Connect your `mededge-intelligence` GitHub repository.
   - Set **Runtime:** `Python 3`
   - Set **Build Command:** `pip install -r requirements.txt`
   - Set **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - Under **Environment Variables**, add:
     - `DATABASE_URL` = *(Paste the Internal Database URL from Render PostgreSQL)*
     - `SECRET_KEY` = *(Click Generate or enter a secure random string)*
     - `PYTHON_VERSION` = `3.12.0`
   - Click **Create Web Service**.

---

### Step 3: Verify & Test Public URL

1. Render will build and deploy your project in 2-3 minutes.
2. Your public HTTPS URL will be displayed at the top of the Render dashboard (e.g. `https://mededge-intelligence.onrender.com`).
3. Open the URL on **iPhone, Android, Laptop, or Tablet**:
   - **Public Home:** `https://mededge-intelligence.onrender.com/`
   - **Staff Login:** `https://mededge-intelligence.onrender.com/login`
   - **Patient Login:** `https://mededge-intelligence.onrender.com/patient-login`
   - **Live Telemetry & Anomaly Bench:** `https://mededge-intelligence.onrender.com/telemetry`

---

## 🔐 Seeded Production Demo Accounts

On initial startup in PostgreSQL, the database is automatically seeded with demo accounts:

| Role | Username / Email | Password |
|---|---|---|
| **System Admin** | `admin@mededge.local` or `admin` | `admin123` |
| **Doctor** | `doctor@mededge.local` or `doctor` | `doctor123` |
| **Nurse** | `nurse@mededge.local` or `nurse` | `nurse123` |
| **Compounder** | `compounder@mededge.local` or `compounder` | `compounder123` |
| **Receptionist** | `reception@mededge.local` or `receptionist` | `reception123` |
| **Patient** | `P-1001` or `patient@mededge.local` | `patient123` |

---

## 🛠️ How Local Development Continues Working

- Running locally without `DATABASE_URL` uses SQLite (`mededge.db`):
  ```bash
  python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
  ```
- In production, when `DATABASE_URL` is set, PostgreSQL is automatically used!
