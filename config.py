import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# API Configuration
CURSOR_API_KEY = os.getenv("CURSOR_API_KEY")
CURSOR_API_BASE = os.getenv("CURSOR_API_BASE", "https://api.cursor.sh/v1")

# Video Configuration
TARGET_ASPECT_RATIO = (9, 16)  # Vertical format for Instagram Reels
MIN_CLIP_LENGTH = 15  # seconds
MAX_CLIP_LENGTH = 60  # seconds
TARGET_CLIP_LENGTH = 30  # seconds
OUTPUT_FORMAT = "mp4"
OUTPUT_CODEC = "libx264"
OUTPUT_BITRATE = "5000k"
OUTPUT_RESOLUTION = (1080, 1920)  # 9:16 vertical

# Motion Detection Configuration
MOTION_THRESHOLD = 0.15  # 0-1, higher = more sensitive
FRAME_SAMPLE_RATE = 2  # Analyze every Nth frame for speed
OPTICAL_FLOW_PYR_SCALE = 0.5
OPTICAL_FLOW_LEVELS = 3
OPTICAL_FLOW_WINSIZE = 15

# Clipping API Configuration (optional - for advanced scene detection)
CLIPPING_API_ENABLED = os.getenv("CLIPPING_API_ENABLED", "false").lower() == "true"
CLIPPING_API_KEY = os.getenv("CLIPPING_API_KEY")
CLIPPING_API_URL = os.getenv("CLIPPING_API_URL", "https://api.vidyo.ai/v1/clips")

# Caption Configuration
NUM_CAPTIONS = 5
MAX_CAPTION_LENGTH = 150  # characters excluding hashtags
HASHTAG_COUNT = 5  # number of hashtags per caption

# Storage Configuration
BASE_OUTPUT_DIR = Path("output")
TODAY_OUTPUT = BASE_OUTPUT_DIR / datetime.now().strftime("%Y-%m-%d")
TEMP_DIR = TODAY_OUTPUT / "temp"
CLIPS_DIR = TODAY_OUTPUT / "clips"
CAPTIONS_DIR = TODAY_OUTPUT / "captions"
METADATA_DIR = TODAY_OUTPUT / "metadata"

# Ensure directories exist
TODAY_OUTPUT.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)
CLIPS_DIR.mkdir(parents=True, exist_ok=True)
CAPTIONS_DIR.mkdir(parents=True, exist_ok=True)
METADATA_DIR.mkdir(parents=True, exist_ok=True)

# OpenClaw Gateway Configuration
OPENCLAW_GATEWAY_URL = os.getenv("OPENCLAW_GATEWAY_URL", "http://127.0.0.1:18789/api/message")
WHATSAPP_APPROVAL_NUMBER = os.getenv("WHATSAPP_APPROVAL_NUMBER", "+917705060708")
APPROVAL_ENABLED = os.getenv("APPROVAL_ENABLED", "true").lower() == "true"

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
