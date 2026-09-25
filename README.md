# MedEdge Intelligence: Real-Time Healthcare Analytics with Small Language Models

> **Project Type:** 4th-Year B.Tech Computer Science Capstone Project / Internship Portfolio  
> **Domain:** IoT Healthcare, Biomedical Signal Processing & Edge AI Telemetry  
> **Deployment:** 100% Local Edge Hardware (Raspberry Pi / ESP32 / Local Workstation) with Zero Cloud Dependency & Sub-Second Latency  

---

## 📌 Project Overview

**MedEdge Intelligence** is an edge-native IoT healthcare telemetry and emergency analytics platform. The system interfaces directly with physical biomedical sensors (**MAX30102** for Blood Oxygen / PPG and **AD8232** for single-lead ECG) or runs a high-fidelity synthetic **NumPy telemetry fallback** for testing. 

Bio-potential signals are filtered in real-time using a 3rd-order digital **SciPy Butterworth filter** to eliminate power line noise and baseline wander. Incoming vitals are continuously evaluated by a local, quantized **Small Language Model (Phi-3 Mini)** running entirely on-device (via Ollama or an embedded engine), delivering immediate contextual emergency insights without transmitting patient data to cloud servers.

---

## 🛠️ Key Architectural Features

1. **Hardware & Sensor Pipeline (`hardware_sensor_pipeline.py`)**:
   - Direct I2C/SMBus drivers for **MAX30102** Pulse Oximeter & **AD8232** ECG analog front-end.
   - Offline **NumPy synthetic telemetry generator** generating PQRST ECG complexes and PPG pulse waveforms.
   - **SciPy Signal Filtering:** 3rd-order Butterworth bandpass digital filter (`0.5 Hz - 40 Hz`) applied via `scipy.signal.filtfilt`.

2. **Zero-Cloud SLM Integration (`slm_integration.py`)**:
   - Anomaly detection module checking vitals against clinical reference ranges.
   - Queries local **Phi-3 Mini Small Language Model** (Ollama REST endpoint `http://localhost:11434/api/generate` or embedded GGUF engine).
   - Generates natural language risk explanations, physiological summaries, and immediate clinical action recommendations.

3. **FastAPI Backend & Persistence (`main.py`, `database.py`, `models.py`)**:
   - High-throughput asynchronous WebSockets (`/ws/telemetry`) streaming live scrolling waveforms at ~10Hz.
   - Persistent **SQLite database (`mededge.db`)** storing user accounts, patient records, vitals, alerts, and security audit logs.
   - Role-Based Access Control (RBAC) with secure **PBKDF2-SHA256 password hashing** and JWT authentication.

4. **Responsive Healthcare Frontend (`/static`)**:
   - Light, human-friendly medical interface (`#F4F7FA` neutral background, white cards, sky blue accents).
   - **Chart.js** real-time line charts for Raw vs Filtered ECG and PPG waveforms.
   - Role-based dashboards for **Admin**, **Doctor**, **Nurse**, **Compounder**, **Receptionist**, and **Patient**.

---

## 🔑 Seeded Demo Credentials for Testing

The system automatically initializes and populates `mededge.db` with the following demo accounts on first launch:

| Role | Username / Email | Password | Allowed Dashboards & Permissions |
|---|---|---|---|
| **System Admin** | `admin@mededge.local` or `admin` | `admin123` | Full system control, user creation, password resets, audit logs, patient directory |
| **Doctor** | `doctor@mededge.local` or `doctor` | `doctor123` | Assigned patient telemetry, AI assessment stream, medical notes & prescriptions |
| **Nurse** | `nurse@mededge.local` or `nurse` | `nurse123` | Ward vital station, live emergency triage queue, vitals monitoring |
| **Compounder** | `compounder@mededge.local` or `compounder` | `compounder123` | Medication dispensing queue, prescription fulfillment |
| **Receptionist** | `reception@mededge.local` or `receptionist` | `reception123` | Patient registration, scheduling doctor appointments |
| **Patient** | `patient@mededge.local` or `P-1001` | `patient123` | Private patient portal (`/patient/dashboard`), vitals overview, health history |

---

## 🚀 Local Network Hosting & Deployment

### Step 1: Install Dependencies

Ensure Python 3.10+ is installed on your system.

```bash
pip install -r requirements.txt
```

### Step 2: Launch FastAPI Server & Frontend

Run Uvicorn bound to `0.0.0.0` so any device (mobile phone, laptop, tablet) on your local Wi-Fi / LAN network can connect without internet access:

```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 🌐 Navigating the Application

Once launched, access the system in your web browser:

- **Public Home & Project Specs:** `http://localhost:8000/`
- **Hospital Staff Login:** `http://localhost:8000/login`
- **Patient Portal Login:** `http://localhost:8000/patient-login`
- **Live Waveform & Anomaly Test Bench:** `http://localhost:8000/telemetry`

---

## 🧪 Testing Anomaly Simulation & Phi-3 Alerts

1. Open `http://localhost:8000/telemetry` in your browser.
2. Observe the live **Chart.js** scrolling waveforms (Blue: Filtered ECG, Gray: Raw ECG, Red: PPG).
3. Click any of the anomaly test buttons:
   - **Simulate Tachycardia:** Triggers HR > 120 BPM & activates Phi-3 SLM alert.
   - **Simulate Hypoxia:** Triggers SpO₂ < 88% & generates urgent oxygenation alert.
   - **Simulate Bradycardia:** Triggers HR < 50 BPM & alerts attending staff.
   - **Simulate Arrhythmia:** Triggers irregular PQRST intervals via AD8232 simulation.
4. Verify that generated alerts are automatically saved to the persistent SQLite database and visible across Doctor, Nurse, and Admin dashboards!
