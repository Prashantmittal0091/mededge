"""
MedEdge Intelligence - FastAPI Core Application & WebSocket Server
Serves Real-Time IoT Telemetry WebSockets, Local SLM Anomaly Alerts, REST APIs, RBAC Auth, and Local Static Dashboard.
"""

import os
import json
import asyncio
from datetime import datetime
from typing import Optional, List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status, Form, Body
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import init_db, get_db, hash_password, verify_password
from models import User, Patient, Doctor, Nurse, Compounder, Receptionist, PatientVital, Alert, Appointment, MedicalRecord, AuditLog, ECGRecord, PPGRecord
from auth import create_access_token, get_current_user, require_admin, require_doctor, require_nurse, require_staff
from hardware_sensor_pipeline import sensor_pipeline
from slm_integration import phi3_engine

# Initialize FastAPI App
app = FastAPI(
    title="MedEdge Intelligence",
    description="Real-Time Healthcare Analytics with Small Language Models on Edge Hardware",
    version="1.0.0"
)

# Enable CORS for local and production deployment
FRONTEND_URL = os.getenv("FRONTEND_URL")
origins = ["*"]
if FRONTEND_URL:
    origins = [FRONTEND_URL, "http://localhost:8000", "http://127.0.0.1:8000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# Health Check Endpoint
@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "app": "MedEdge Intelligence",
        "timestamp": datetime.utcnow().isoformat()
    }


import threading

# Initialize database in background thread on startup (non-blocking for instant cloud health checks)
@app.on_event("startup")
def startup_event():
    threading.Thread(target=init_db, daemon=True).start()


# WebSocket Connection Manager for Real-Time Telemetry Streaming
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass


ws_manager = ConnectionManager()


# Background Task for Streaming Telemetry & Phi-3 Anomaly Detection over WebSockets
@app.websocket("/ws/telemetry")
async def websocket_telemetry_endpoint(websocket: WebSocket, db: Session = Depends(get_db)):
    await ws_manager.connect(websocket)
    try:
        while True:
            # Check for incoming client messages (e.g., anomaly test triggers)
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
                msg = json.loads(data)
                if "anomaly_mode" in msg:
                    sensor_pipeline.set_anomaly_mode(msg["anomaly_mode"])
            except asyncio.TimeoutError:
                pass
            except Exception:
                pass

            # Fetch sensor frame (scipy Butterworth filtered ECG & PPG + Vitals)
            frame = sensor_pipeline.get_telemetry_frame(buffer_size=50)

            # Evaluate vitals via local Phi-3 Small Language Model
            slm_eval = phi3_engine.evaluate_vitals(
                heart_rate=frame["heart_rate"],
                spo2=frame["spo2"],
                anomaly_mode=frame["anomaly_mode"]
            )

            # If an anomaly was triggered, save alert to SQLite DB
            if slm_eval["triggered"]:
                new_alert = Alert(
                    patient_id="P-1001",
                    severity=slm_eval["severity"],
                    diagnosis_anomaly=slm_eval["diagnosis"],
                    heart_rate=frame["heart_rate"],
                    spo2=frame["spo2"],
                    clinical_assessment=slm_eval["assessment"]
                )
                db.add(new_alert)

                vital_entry = PatientVital(
                    patient_id="P-1001",
                    heart_rate=frame["heart_rate"],
                    spo2=frame["spo2"],
                    status=slm_eval["severity"]
                )
                db.add(vital_entry)
                db.commit()

            telemetry_payload = {
                "patient_id": "P-1001",
                "timestamp": frame["timestamp"],
                "heart_rate": frame["heart_rate"],
                "spo2": frame["spo2"],
                "anomaly_mode": frame["anomaly_mode"],
                "dsp_status": frame["dsp_status"],
                "raw_ecg": frame["raw_ecg"],
                "filtered_ecg": frame["filtered_ecg"],
                "ppg": frame["ppg"],
                "slm_eval": slm_eval
            }

            await websocket.send_json(telemetry_payload)
            await asyncio.sleep(0.15)  # ~6.6 Hz update rate for live scrolling waveform

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


# ==========================================
# AUTHENTICATION APIS
# ==========================================

@app.post("/api/auth/login")
def staff_login(
    username_or_email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Staff Login Endpoint for Admin, Doctor, Nurse, Compounder, Receptionist."""
    user = db.query(User).filter(
        (User.email == username_or_email) | (User.username == username_or_email)
    ).first()

    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid email/username or password.")

    if user.status != "ACTIVE":
        raise HTTPException(status_code=400, detail="Account is deactivated. Contact Administrator.")

    access_token = create_access_token(data={"sub": user.email, "role": user.role, "name": user.name})

    # Log audit
    db.add(AuditLog(user_email=user.email, user_role=user.role, action=f"Staff logged in ({user.role})"))
    db.commit()

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role,
        "name": user.name,
        "email": user.email
    }


@app.post("/api/auth/patient-login")
def patient_login(
    patient_id_or_email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Dedicated Patient Login Endpoint."""
    user = db.query(User).filter(
        (User.email == patient_id_or_email) | (User.username == patient_id_or_email)
    ).first()

    # If searched by patient_id
    if not user:
        patient_rec = db.query(Patient).filter(Patient.patient_id == patient_id_or_email).first()
        if patient_rec and patient_rec.user:
            user = patient_rec.user

    if not user or user.role != "PATIENT" or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid Patient ID/Email or password.")

    access_token = create_access_token(data={"sub": user.email, "role": "PATIENT", "name": user.name})

    db.add(AuditLog(user_email=user.email, user_role="PATIENT", action="Patient logged into Patient Portal"))
    db.commit()

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": "PATIENT",
        "name": user.name,
        "patient_id": user.patient_profile.patient_id if user.patient_profile else "P-1001"
    }


@app.get("/api/auth/me")
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Returns profile information for the authenticated user."""
    patient_info = None
    if current_user.role == "PATIENT" and current_user.patient_profile:
        p = current_user.patient_profile
        patient_info = {
            "patient_id": p.patient_id,
            "age": p.age,
            "gender": p.gender,
            "phone": p.phone,
            "address": p.address,
            "emergency_contact": p.emergency_contact,
            "status": p.status
        }

    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "username": current_user.username,
        "role": current_user.role,
        "status": current_user.status,
        "patient_profile": patient_info
    }


# ==========================================
# ADMIN MANAGEMENT APIS
# ==========================================

@app.get("/api/admin/users")
def get_all_users(current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Admin Endpoint: List all users in system."""
    users = db.query(User).all()
    res = []
    for u in users:
        res.append({
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "username": u.username,
            "role": u.role,
            "status": u.status,
            "created_at": u.created_at.strftime("%Y-%m-%d %H:%M") if u.created_at else ""
        })
    return res


@app.post("/api/admin/users")
def create_user(
    name: str = Form(...),
    email: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Admin Endpoint: Add new staff or patient user."""
    existing = db.query(User).filter((User.email == email) | (User.username == username)).first()
    if existing:
        raise HTTPException(status_code=400, detail="User with this email or username already exists.")

    new_user = User(
        name=name,
        email=email,
        username=username,
        password_hash=hash_password(password),
        role=role.upper(),
        status="ACTIVE"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # If role is PATIENT, create patient profile
    if role.upper() == "PATIENT":
        p_count = db.query(Patient).count() + 1002
        new_patient = Patient(
            patient_id=f"P-{p_count}",
            user_id=new_user.id,
            name=name,
            age=35,
            gender="Unspecified",
            phone="+91 98000 00000",
            status="MONITORING"
        )
        db.add(new_patient)
        db.commit()

    db.add(AuditLog(user_email=current_user.email, user_role=current_user.role, action=f"Created user {email} ({role})"))
    db.commit()

    return {"message": f"User {name} created successfully as {role}."}


@app.post("/api/admin/users/{user_id}/reset-password")
def reset_password(
    user_id: int,
    new_password: str = Form(...),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Admin Endpoint: Reset password for any user securely."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.password_hash = hash_password(new_password)
    db.add(AuditLog(user_email=current_user.email, user_role=current_user.role, action=f"Reset password for user {user.email}"))
    db.commit()

    return {"message": f"Password for user {user.name} has been reset successfully."}


@app.put("/api/admin/users/{user_id}/toggle-status")
def toggle_user_status(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Admin Endpoint: Activate / Deactivate user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.status = "INACTIVE" if user.status == "ACTIVE" else "ACTIVE"
    db.add(AuditLog(user_email=current_user.email, user_role=current_user.role, action=f"Toggled status for {user.email} to {user.status}"))
    db.commit()

    return {"message": f"User status changed to {user.status}."}


@app.get("/api/admin/system-activity")
def get_system_audit_logs(current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Admin Endpoint: Get system audit logs."""
    logs = db.query(AuditLog).order_by(AuditLog.id.desc()).limit(100).all()
    return [{
        "id": l.id,
        "user_email": l.user_email,
        "user_role": l.user_role,
        "action": l.action,
        "timestamp": l.timestamp.strftime("%Y-%m-%d %H:%M:%S")
    } for l in logs]


# ==========================================
# PATIENT & CLINICAL DOMAIN APIS
# ==========================================

@app.get("/api/patients")
def get_patients(db: Session = Depends(get_db)):
    """Get list of monitored patients."""
    patients = db.query(Patient).all()
    res = []
    for p in patients:
        latest_vital = db.query(PatientVital).filter(PatientVital.patient_id == p.patient_id).order_by(PatientVital.id.desc()).first()
        res.append({
            "id": p.id,
            "patient_id": p.patient_id,
            "name": p.name,
            "age": p.age,
            "gender": p.gender,
            "phone": p.phone,
            "address": p.address,
            "emergency_contact": p.emergency_contact,
            "status": p.status,
            "latest_hr": latest_vital.heart_rate if latest_vital else 72.0,
            "latest_spo2": latest_vital.spo2 if latest_vital else 98.0,
            "created_at": p.created_at.strftime("%Y-%m-%d")
        })
    return res


@app.get("/api/patients/{patient_id}")
def get_patient_detail(patient_id: str, db: Session = Depends(get_db)):
    """Get detail for specific patient."""
    p = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Patient not found.")

    vitals = db.query(PatientVital).filter(PatientVital.patient_id == patient_id).order_by(PatientVital.id.desc()).limit(20).all()
    alerts = db.query(Alert).filter(Alert.patient_id == patient_id).order_by(Alert.id.desc()).limit(20).all()
    records = db.query(MedicalRecord).filter(MedicalRecord.patient_id == patient_id).order_by(MedicalRecord.id.desc()).all()
    appointments = db.query(Appointment).filter(Appointment.patient_id == patient_id).all()

    return {
        "patient_id": p.patient_id,
        "name": p.name,
        "age": p.age,
        "gender": p.gender,
        "phone": p.phone,
        "address": p.address,
        "emergency_contact": p.emergency_contact,
        "status": p.status,
        "vitals": [{
            "heart_rate": v.heart_rate,
            "spo2": v.spo2,
            "temp": v.temp,
            "bp": f"{v.bp_sys}/{v.bp_dia}",
            "status": v.status,
            "timestamp": v.timestamp.strftime("%H:%M:%S")
        } for v in vitals],
        "alerts": [{
            "id": a.id,
            "severity": a.severity,
            "diagnosis": a.diagnosis_anomaly,
            "heart_rate": a.heart_rate,
            "spo2": a.spo2,
            "assessment": a.clinical_assessment,
            "timestamp": a.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        } for a in alerts],
        "medical_records": [{
            "id": m.id,
            "doctor": m.doctor_name,
            "diagnosis": m.diagnosis,
            "prescription": m.prescription,
            "notes": m.notes,
            "timestamp": m.timestamp.strftime("%Y-%m-%d")
        } for m in records],
        "appointments": [{
            "id": app.id,
            "doctor": app.doctor_name,
            "date": app.date,
            "time": app.time,
            "status": app.status,
            "notes": app.notes
        } for app in appointments]
    }


@app.get("/api/doctors")
def get_doctors(db: Session = Depends(get_db)):
    return db.query(Doctor).all()


@app.get("/api/nurses")
def get_nurses(db: Session = Depends(get_db)):
    return db.query(Nurse).all()


@app.get("/api/compounders")
def get_compounders(db: Session = Depends(get_db)):
    return db.query(Compounder).all()


@app.get("/api/receptionists")
def get_receptionists(db: Session = Depends(get_db)):
    return db.query(Receptionist).all()


@app.get("/api/alerts")
def get_alerts(db: Session = Depends(get_db)):
    """Fetch persistent alert history from SQLite database."""
    alerts = db.query(Alert).order_by(Alert.id.desc()).limit(50).all()
    return [{
        "id": a.id,
        "patient_id": a.patient_id,
        "severity": a.severity,
        "diagnosis": a.diagnosis_anomaly,
        "heart_rate": a.heart_rate,
        "spo2": a.spo2,
        "assessment": a.clinical_assessment,
        "timestamp": a.timestamp.strftime("%Y-%m-%d %H:%M:%S")
    } for a in alerts]


@app.post("/api/simulate/trigger-anomaly")
def trigger_anomaly(mode: str = Body(embed=True)):
    """Simulate physiological anomalies (Tachycardia, Hypoxia, Bradycardia, Arrhythmia, Normal)."""
    sensor_pipeline.set_anomaly_mode(mode)
    return {"message": f"Sensor simulation anomaly mode set to {mode.upper()}."}


# ==========================================
# HTML ROUTING & FRONTEND PAGES
# ==========================================

@app.get("/", response_class=HTMLResponse)
def page_home():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

@app.get("/login", response_class=HTMLResponse)
def page_staff_login():
    return FileResponse(os.path.join(STATIC_DIR, "login.html"))

@app.get("/patient-login", response_class=HTMLResponse)
def page_patient_login():
    return FileResponse(os.path.join(STATIC_DIR, "patient-login.html"))

@app.get("/admin", response_class=HTMLResponse)
def page_admin():
    return FileResponse(os.path.join(STATIC_DIR, "admin.html"))

@app.get("/doctor", response_class=HTMLResponse)
def page_doctor():
    return FileResponse(os.path.join(STATIC_DIR, "doctor.html"))

@app.get("/nurse", response_class=HTMLResponse)
def page_nurse():
    return FileResponse(os.path.join(STATIC_DIR, "nurse.html"))

@app.get("/compounder", response_class=HTMLResponse)
def page_compounder():
    return FileResponse(os.path.join(STATIC_DIR, "compounder.html"))

@app.get("/reception", response_class=HTMLResponse)
def page_reception():
    return FileResponse(os.path.join(STATIC_DIR, "receptionist.html"))

@app.get("/patient/dashboard", response_class=HTMLResponse)
def page_patient_dashboard():
    return FileResponse(os.path.join(STATIC_DIR, "patient-dashboard.html"))

@app.get("/telemetry", response_class=HTMLResponse)
def page_telemetry():
    return FileResponse(os.path.join(STATIC_DIR, "telemetry.html"))


if __name__ == "__main__":
    import uvicorn
    port_env = os.getenv("PORT", "8000")
    try:
        port = int(port_env)
    except ValueError:
        port = 8000
    uvicorn.run(app, host="0.0.0.0", port=port)
