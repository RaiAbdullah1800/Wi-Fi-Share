from datetime import datetime

# Shared in-memory clipboard text state
_shared_clipboard = {
    "text": "Welcome to Wi-Fi File & Text Share! Type text here to sync across devices.",
    "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
}

def get_clipboard_data():
    return _shared_clipboard

def set_clipboard_data(text):
    global _shared_clipboard
    _shared_clipboard["text"] = text
    _shared_clipboard["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return _shared_clipboard
