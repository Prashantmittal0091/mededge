"""
MedEdge Intelligence - Database Models (SQLAlchemy ORM)
Defines schema for Users, Patients, Staff, Vitals, ECG/PPG telemetry, Alerts, Appointments, Records, and Audit Logs.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)  # ADMIN, DOCTOR, NURSE, COMPOUNDER, RECEPTIONIST, PATIENT
    name = Column(String(100), nullable=False)
    status = Column(String(20), default="ACTIVE")  # ACTIVE, INACTIVE
    created_at = Column(DateTime, default=datetime.utcnow)

    patient_profile = relationship("Patient", back_populates="user", uselist=False)


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(String(20), unique=True, index=True, nullable=False)  # e.g., P-1001
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    name = Column(String(100), nullable=False)
    age = Column(Integer, nullable=False)
    gender = Column(String(10), nullable=False)
    phone = Column(String(20), nullable=False)
    address = Column(String(200), nullable=True)
    emergency_contact = Column(String(100), nullable=True)
    status = Column(String(20), default="MONITORING")  # MONITORING, STABLE, DISCHARGED, CRITICAL
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="patient_profile")
    vitals = relationship("PatientVital", back_populates="patient", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="patient", cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="patient", cascade="all, delete-orphan")
    medical_records = relationship("MedicalRecord", back_populates="patient", cascade="all, delete-orphan")


class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    specialization = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False)
    status = Column(String(20), default="ACTIVE")


class Nurse(Base):
    __tablename__ = "nurses"

    id = Column(Integer, primary_key=True, index=True)
    nurse_id = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    department = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False)
    status = Column(String(20), default="ACTIVE")


class Compounder(Base):
    __tablename__ = "compounders"

    id = Column(Integer, primary_key=True, index=True)
    compounder_id = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    shift = Column(String(50), nullable=False)
    email = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False)
    status = Column(String(20), default="ACTIVE")


class Receptionist(Base):
    __tablename__ = "receptionists"

    id = Column(Integer, primary_key=True, index=True)
    receptionist_id = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    shift = Column(String(50), nullable=False)
    email = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False)
    status = Column(String(20), default="ACTIVE")


class PatientVital(Base):
    __tablename__ = "patient_vitals"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(String(20), ForeignKey("patients.patient_id"), nullable=False)
    heart_rate = Column(Float, nullable=False)
    spo2 = Column(Float, nullable=False)
    temp = Column(Float, default=98.6)
    bp_sys = Column(Integer, default=120)
    bp_dia = Column(Integer, default=80)
    status = Column(String(20), default="NORMAL")
    timestamp = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="vitals")


class ECGRecord(Base):
    __tablename__ = "ecg_records"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(String(20), nullable=False)
    raw_signal = Column(Text, nullable=False)  # JSON serialized list
    filtered_signal = Column(Text, nullable=False)  # JSON serialized list
    timestamp = Column(DateTime, default=datetime.utcnow)


class PPGRecord(Base):
    __tablename__ = "ppg_records"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(String(20), nullable=False)
    raw_signal = Column(Text, nullable=False)  # JSON serialized list
    filtered_signal = Column(Text, nullable=False)  # JSON serialized list
    timestamp = Column(DateTime, default=datetime.utcnow)


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(String(20), ForeignKey("patients.patient_id"), nullable=False)
    severity = Column(String(20), nullable=False)  # NORMAL, WARNING, CRITICAL
    diagnosis_anomaly = Column(String(100), nullable=False)
    heart_rate = Column(Float, nullable=False)
    spo2 = Column(Float, nullable=False)
    clinical_assessment = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="alerts")


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(String(20), ForeignKey("patients.patient_id"), nullable=False)
    doctor_name = Column(String(100), nullable=False)
    date = Column(String(20), nullable=False)
    time = Column(String(20), nullable=False)
    status = Column(String(20), default="SCHEDULED")  # SCHEDULED, COMPLETED, CANCELLED
    notes = Column(Text, nullable=True)

    patient = relationship("Patient", back_populates="appointments")


class MedicalRecord(Base):
    __tablename__ = "medical_records"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(String(20), ForeignKey("patients.patient_id"), nullable=False)
    doctor_name = Column(String(100), nullable=False)
    diagnosis = Column(String(200), nullable=False)
    prescription = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="medical_records")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String(100), nullable=False)
    user_role = Column(String(20), nullable=False)
    action = Column(String(255), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
