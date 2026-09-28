"""
MedEdge Intelligence - Database Engine & Auto-Seeding
Sets up SQLite database (`mededge.db`), SQLAlchemy sessions, and seeds standard demo accounts for testing all roles.
"""

import os
import hashlib
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, User, Patient, Doctor, Nurse, Compounder, Receptionist, PatientVital, Alert, Appointment, MedicalRecord, AuditLog

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # Render PostgreSQL URLs start with postgres:// which SQLAlchemy 2.0 requires to be postgresql://
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
    SQLALCHEMY_DATABASE_URL = DATABASE_URL
    engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)
else:
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mededge.db")
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def hash_password(password: str) -> str:
    """Hashes password securely using PBKDF2-HMAC-SHA256 with salt."""
    salt = b"mededge_secure_salt_2026"
    pwd_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return pwd_hash.hex()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies plain text password against stored hash."""
    return hash_password(plain_password) == hashed_password


def get_db():
    """FastAPI Dependency for database session management."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initializes tables and seeds default demo accounts if not present."""
    try:
        print("[INFO] Initializing MedEdge database and tables...")
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()

        try:
            # Check if users exist
            if db.query(User).count() == 0:
                print("[INFO] Seeding MedEdge Intelligence Demo Accounts...")

            # 1. Admin Account
            admin_user = User(
                username="admin",
                email="admin@mededge.local",
                password_hash=hash_password("admin123"),
                role="ADMIN",
                name="System Administrator"
            )

            # 2. Doctor Account
            doctor_user = User(
                username="doctor",
                email="doctor@mededge.local",
                password_hash=hash_password("doctor123"),
                role="DOCTOR",
                name="Dr. Ananya Sharma"
            )

            # 3. Nurse Account
            nurse_user = User(
                username="nurse",
                email="nurse@mededge.local",
                password_hash=hash_password("nurse123"),
                role="NURSE",
                name="Sister Priya Verma"
            )

            # 4. Compounder Account
            compounder_user = User(
                username="compounder",
                email="compounder@mededge.local",
                password_hash=hash_password("compounder123"),
                role="COMPOUNDER",
                name="Ramesh Kumar"
            )

            # 5. Receptionist Account
            receptionist_user = User(
                username="receptionist",
                email="reception@mededge.local",
                password_hash=hash_password("reception123"),
                role="RECEPTIONIST",
                name="Sunita Rao"
            )

            # 6. Patient Account
            patient_user = User(
                username="patient",
                email="patient@mededge.local",
                password_hash=hash_password("patient123"),
                role="PATIENT",
                name="Rajesh Sharma"
            )

            db.add_all([admin_user, doctor_user, nurse_user, compounder_user, receptionist_user, patient_user])
            db.commit()

            # Refresh to get IDs
            db.refresh(patient_user)

            # Seed Doctor profile
            doctor_profile = Doctor(
                doctor_id="DOC-101",
                name="Dr. Ananya Sharma",
                specialization="Cardiology & Critical Care",
                email="doctor@mededge.local",
                phone="+91 98112 34567"
            )

            # Seed Nurse profile
            nurse_profile = Nurse(
                nurse_id="NRS-201",
                name="Sister Priya Verma",
                department="ICU & Telemetry Unit",
                email="nurse@mededge.local",
                phone="+91 98223 45678"
            )

            # Seed Compounder profile
            compounder_profile = Compounder(
                compounder_id="CMP-301",
                name="Ramesh Kumar",
                shift="Morning Shift (8 AM - 4 PM)",
                email="compounder@mededge.local",
                phone="+91 98334 56789"
            )

            # Seed Receptionist profile
            receptionist_profile = Receptionist(
                receptionist_id="RCP-401",
                name="Sunita Rao",
                shift="Day Shift",
                email="reception@mededge.local",
                phone="+91 98445 67890"
            )

            # Seed Patient Profile
            patient_profile = Patient(
                patient_id="P-1001",
                user_id=patient_user.id,
                name="Rajesh Sharma",
                age=48,
                gender="Male",
                phone="+91 98765 43210",
                address="Sector 62, Noida, Uttar Pradesh",
                emergency_contact="Sunita Sharma (+91 98765 43211)",
                status="MONITORING"
            )

            db.add_all([doctor_profile, nurse_profile, compounder_profile, receptionist_profile, patient_profile])
            db.commit()

            # Seed initial Vitals for P-1001
            vitals = PatientVital(
                patient_id="P-1001",
                heart_rate=72.0,
                spo2=98.0,
                temp=98.6,
                bp_sys=120,
                bp_dia=80,
                status="NORMAL"
            )

            # Seed initial Alert for P-1001
            initial_alert = Alert(
                patient_id="P-1001",
                severity="NORMAL",
                diagnosis_anomaly="Normal Sinus Rhythm",
                heart_rate=72.0,
                spo2=98.0,
                clinical_assessment="Patient vitals normal. Continuous edge telemetry active via AD8232 & MAX30102 sensors."
            )

            # Seed Initial Appointment
            appointment = Appointment(
                patient_id="P-1001",
                doctor_name="Dr. Ananya Sharma",
                date="2026-09-28",
                time="10:30 AM",
                status="SCHEDULED",
                notes="Routine post-telemetry cardiology consultation."
            )

            # Seed Initial Medical Record
            med_record = MedicalRecord(
                patient_id="P-1001",
                doctor_name="Dr. Ananya Sharma",
                diagnosis="Hypertension Management & Routine Telemetry Monitoring",
                prescription="Amlodipine 5mg (Once Daily), Aspirin 75mg",
                notes="Patient under continuous sub-second MedEdge IoT monitoring. Stable sinus rhythm observed."
            )

            # Seed Initial Audit Log
            audit = AuditLog(
                user_email="system@mededge.local",
                user_role="SYSTEM",
                action="Database initialized and default demo records seeded."
            )

            db.add_all([vitals, initial_alert, appointment, med_record, audit])
            db.commit()

            print("[SUCCESS] MedEdge Intelligence Database Initialized & Seeded!")
        finally:
            db.close()
    except Exception as e:
        print(f"[WARNING] Database initialization deferred: {e}")
