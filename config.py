import os

PORT = 5000
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DROPS_DIR = os.path.join(BASE_DIR, "drops_storage")
PUBLIC_DIR = os.path.join(BASE_DIR, "public")

# Expiry & Limits
DEFAULT_EXPIRY_MINUTES = 30
MAX_UPLOAD_SIZE = 2 * 1024 * 1024 * 1024  # 2 GB
MAX_TEXT_SIZE = 500 * 1024                # 500 KB

# Ensure required directories exist
os.makedirs(DROPS_DIR, exist_ok=True)
os.makedirs(PUBLIC_DIR, exist_ok=True)
