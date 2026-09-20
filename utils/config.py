import os

from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()

APP_NAME = "SafeSentinel AI"
TAGLINE = "From scattered safety reports to early incident intelligence."

# Configurable risk-scoring weights (out of 100 total)
RISK_WEIGHTS = {
    "severity": 25,
    "exposure": 20,
    "recurrence": 20,
    "control_gap": 20,
    "historical_similarity": 15,
}

RISK_THRESHOLDS = {"LOW": (0, 39), "MEDIUM": (40, 69), "HIGH": (70, 100)}

GUIDANCE_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "safety_guidance")
DEFAULT_CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "sample_reports.csv")
