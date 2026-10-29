import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent
STORAGE_DIR = BASE_DIR / "storage"
LOGS_DIR = STORAGE_DIR / "logs"
UPLOADS_DIR = STORAGE_DIR / "uploads"
AUDIO_DIR = STORAGE_DIR / "generated_audio"
DB_PATH = STORAGE_DIR / "attendance_engagement.db"

# Create directories if not exist
for d in [STORAGE_DIR, LOGS_DIR, UPLOADS_DIR, AUDIO_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Vision Module Configuration
SUSTAINED_PRESENCE_SECONDS = 3.0       # Minimum sustained presence before marking attendance
FACE_ABSENCE_TOLERANCE_SECONDS = 2.0   # Grace period if face is temporarily obscured
MOTION_HISTORY_LENGTH = 15             # Frames to track movement history
MIN_FACE_SIZE = (40, 40)
HEAD_POSE_CENTER_THRESHOLD = 0.25      # Deviation fraction from center for frontal attention

# Audio Module Configuration
SAMPLE_RATE = 16000
AUDIO_CHANNELS = 1
SILENCE_ENERGY_THRESHOLD = 0.015       # RMS energy below this is ambient silence
SPEECH_ENERGY_THRESHOLD = 0.05         # Normal conversational speech
HIGH_ENERGY_THRESHOLD = 0.18           # Peak classroom discussion / noise
AUDIO_CHUNK_DURATION = 1.0             # Seconds per audio evaluation slice

# Multimodal Fusion Configuration
WEIGHT_VISUAL_ATTENTION = 0.45
WEIGHT_VISUAL_ACTIVITY = 0.20
WEIGHT_AUDIO_INTERACTION = 0.35
ENGAGEMENT_EXPONENTIAL_SMOOTHING = 0.7  # Alpha for EMA temporal smoothing

# Engagement Thresholds
ENGAGEMENT_LEVELS = {
    "HIGH": 70.0,
    "MODERATE": 45.0,
    "LOW": 25.0
}

# GenAI & Agent Configuration
GEMINI_MODEL = "gemini-2.0-flash"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Server Configuration
FLASK_HOST = "127.0.0.1"
FLASK_PORT = 5000
DEBUG = True
