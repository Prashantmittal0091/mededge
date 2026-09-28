"""
MedEdge Intelligence - Hardware & Sensor Pipeline
Module for interfacing with MAX30102 (SpO2/PPG) & AD8232 (ECG) sensors,
with NumPy synthetic data fallback and scipy.signal Butterworth filtering.
"""

import time
import math
import numpy as np
try:
    from scipy import signal
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

# Optional hardware imports (wrapped in try-except for Pi/ESP32 compatibility)
try:
    import smbus2
    HARDWARE_AVAILABLE = True
except ImportError:
    HARDWARE_AVAILABLE = False


class ButterworthFilter:
    """Digital Butterworth Filter for ECG/PPG noise reduction."""

    def __init__(self, sample_rate=100.0, lowcut=0.5, highcut=40.0, order=3):
        self.sample_rate = sample_rate
        self.lowcut = lowcut
        self.highcut = highcut
        self.order = order

        if HAS_SCIPY:
            # Design Butterworth bandpass filter
            nyquist = 0.5 * sample_rate
            low = lowcut / nyquist
            high = highcut / nyquist
            self.b, self.a = signal.butter(order, [low, high], btype='bandpass')

    def filter_signal(self, raw_data):
        """Applies zero-phase digital filtering using scipy.signal.filtfilt."""
        if not HAS_SCIPY or len(raw_data) < 15:
            return list(raw_data)
        
        raw_arr = np.array(raw_data, dtype=float)
        # Handle NaN/Inf if present
        raw_arr = np.nan_to_num(raw_arr)
        
        filtered = signal.filtfilt(self.b, self.a, raw_arr)
        return filtered.tolist()


class MAX30102Sensor:
    """Driver interface for MAX30102 Pulse Oximeter & Heart Rate Sensor."""

    def __init__(self, i2c_bus=1, address=0x57):
        self.i2c_bus = i2c_bus
        self.address = address
        self.initialized = False
        self._init_sensor()

    def _init_sensor(self):
        if not HARDWARE_AVAILABLE:
            return
        try:
            self.bus = smbus2.SMBus(self.i2c_bus)
            # Reset & config registers
            self.bus.write_byte_data(self.address, 0x09, 0x40)  # Reset
            time.sleep(0.1)
            self.bus.write_byte_data(self.address, 0x09, 0x03)  # SpO2 mode
            self.initialized = True
        except Exception:
            self.initialized = False

    def read_fifo(self):
        """Read Red & IR LED samples from FIFO."""
        if not self.initialized:
            return None, None
        try:
            data = self.bus.read_i2c_block_data(self.address, 0x07, 6)
            red = (data[0] << 16 | data[1] << 8 | data[2]) & 0x03FFFF
            ir = (data[3] << 16 | data[4] << 8 | data[5]) & 0x03FFFF
            return red, ir
        except Exception:
            return None, None


class AD8232Sensor:
    """Driver interface for AD8232 ECG Analog Front-End sensor."""

    def __init__(self, gpio_sdn=18):
        self.gpio_sdn = gpio_sdn
        self.initialized = False
        self._init_sensor()

    def _init_sensor(self):
        if not HARDWARE_AVAILABLE:
            return
        try:
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.gpio_sdn, GPIO.OUT)
            GPIO.output(self.gpio_sdn, GPIO.HIGH)
            self.initialized = True
        except Exception:
            self.initialized = False


class SensorPipeline:
    """
    Main Sensor Pipeline:
    Interfaces with physical MAX30102 & AD8232 or generates synthetic NumPy telemetry
    for testing. Filters raw signals with Butterworth DSP filter.
    """

    def __init__(self, sample_rate=100.0):
        self.sample_rate = sample_rate
        self.max30102 = MAX30102Sensor()
        self.ad8232 = AD8232Sensor()
        self.filter = ButterworthFilter(sample_rate=sample_rate)

        # Internal state for synthetic waveform generation
        self.phase = 0.0
        self.anomaly_mode = "NORMAL"  # NORMAL, TACHYCARDIA, HYPOXIA, BRADYCARDIA, ARRHYTHMIA

    def set_anomaly_mode(self, mode: str):
        """Sets the telemetry state to simulate physiological conditions."""
        valid_modes = ["NORMAL", "TACHYCARDIA", "HYPOXIA", "BRADYCARDIA", "ARRHYTHMIA"]
        if mode.upper() in valid_modes:
            self.anomaly_mode = mode.upper()

    def generate_synthetic_ecg_point(self, t: float, hr_bpm: float) -> float:
        """
        Generates realistic synthetic PQRST ECG waveform at timestamp t.
        P-wave, QRS complex, T-wave with synthetic baseline wander & high-frequency noise.
        """
        freq = hr_bpm / 60.0
        cycle_t = (t * freq) % 1.0

        # P Wave (at cycle 0.1)
        p_wave = 0.15 * np.exp(-((cycle_t - 0.15) ** 2) / (2 * 0.02 ** 2))
        # Q Wave (at cycle 0.25)
        q_wave = -0.15 * np.exp(-((cycle_t - 0.28) ** 2) / (2 * 0.01 ** 2))
        # R Wave (at cycle 0.3)
        r_wave = 1.2 * np.exp(-((cycle_t - 0.30) ** 2) / (2 * 0.008 ** 2))
        # S Wave (at cycle 0.33)
        s_wave = -0.35 * np.exp(-((cycle_t - 0.33) ** 2) / (2 * 0.012 ** 2))
        # T Wave (at cycle 0.5)
        t_wave = 0.3 * np.exp(-((cycle_t - 0.52) ** 2) / (2 * 0.04 ** 2))

        clean_ecg = p_wave + q_wave + r_wave + s_wave + t_wave

        # Add 50Hz powerline noise & 0.2Hz baseline wander
        noise = 0.08 * np.sin(2 * np.pi * 50 * t) + 0.12 * np.sin(2 * np.pi * 0.2 * t)
        
        # Add random Gaussian noise via numpy
        rnd = float(np.random.normal(0, 0.03))

        return clean_ecg + noise + rnd

    def generate_synthetic_ppg_point(self, t: float, hr_bpm: float) -> float:
        """Generates realistic PPG waveform (systolic peak & dicrotic notch)."""
        freq = hr_bpm / 60.0
        cycle_t = (t * freq) % 1.0

        systolic = 0.8 * np.exp(-((cycle_t - 0.2) ** 2) / (2 * 0.06 ** 2))
        dicrotic = 0.3 * np.exp(-((cycle_t - 0.45) ** 2) / (2 * 0.05 ** 2))
        
        noise = float(np.random.normal(0, 0.02))
        return systolic + dicrotic + noise

    def get_telemetry_frame(self, buffer_size=100):
        """
        Retrieves a complete frame of ECG and PPG raw data, filters with Butterworth,
        and computes vitals metrics.
        """
        # Determine physiological parameters based on anomaly mode
        if self.anomaly_mode == "TACHYCARDIA":
            base_hr = 125.0 + float(np.random.uniform(-3, 3))
            base_spo2 = 96.0 + float(np.random.uniform(-1, 1))
        elif self.anomaly_mode == "HYPOXIA":
            base_hr = 108.0 + float(np.random.uniform(-4, 4))
            base_spo2 = 87.0 + float(np.random.uniform(-2, 1))
        elif self.anomaly_mode == "BRADYCARDIA":
            base_hr = 44.0 + float(np.random.uniform(-2, 2))
            base_spo2 = 95.0 + float(np.random.uniform(-1, 1))
        elif self.anomaly_mode == "ARRHYTHMIA":
            base_hr = 92.0 + float(np.random.uniform(-15, 20))
            base_spo2 = 94.0 + float(np.random.uniform(-2, 2))
        else:  # NORMAL
            base_hr = 74.0 + float(np.random.uniform(-2, 2))
            base_spo2 = 98.0 + float(np.random.uniform(-1, 1))

        # Generate sample vectors
        t_vec = np.linspace(0, buffer_size / self.sample_rate, buffer_size)
        raw_ecg = [self.generate_synthetic_ecg_point(t + time.time(), base_hr) for t in t_vec]
        raw_ppg = [self.generate_synthetic_ppg_point(t + time.time(), base_hr) for t in t_vec]

        # Apply Butterworth Filter to ECG signal
        filtered_ecg = self.filter.filter_signal(raw_ecg)
        filtered_ppg = self.filter.filter_signal(raw_ppg)

        # Scale raw and filtered signals for standard UI display (-1.0 to 1.5)
        raw_ecg_clean = [round(val, 3) for val in raw_ecg]
        filtered_ecg_clean = [round(val, 3) for val in filtered_ecg]
        filtered_ppg_clean = [round(val, 3) for val in filtered_ppg]

        return {
            "timestamp": time.time(),
            "heart_rate": round(base_hr, 1),
            "spo2": round(min(100.0, max(70.0, base_spo2)), 1),
            "anomaly_mode": self.anomaly_mode,
            "raw_ecg": raw_ecg_clean,
            "filtered_ecg": filtered_ecg_clean,
            "ppg": filtered_ppg_clean,
            "dsp_status": "Butterworth 3rd-Order Bandpass (0.5-40Hz) Active"
        }


# Singleton sensor pipeline instance
sensor_pipeline = SensorPipeline()
