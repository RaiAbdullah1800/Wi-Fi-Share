import os
import time
import shutil
import hashlib
import secrets
import random
import string
import threading
from datetime import datetime
from config import PUBLIC_SHARES_DIR
from core.storage import format_size, get_file_category

# In-memory storage & locks
public_shares = {}
unlocked_tokens = {}
shares_lock = threading.RLock()
cleanup_thread_started = False

def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def generate_share_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def create_public_share(uploaded_files, password, title="Public Share Drop", uploader_ip="127.0.0.1"):
    with shares_lock:
        share_id = generate_share_id()
        while share_id in public_shares:
            share_id = generate_share_id()

        share_dir = os.path.join(PUBLIC_SHARES_DIR, share_id)
        os.makedirs(share_dir, exist_ok=True)

        saved_files = []
        for file_info in uploaded_files:
            # file_info = { "filename": str, "data": bytes }
            filename = os.path.basename(file_info["filename"])
            if not filename:
                continue

            file_path = os.path.join(share_dir, filename)
            with open(file_path, "wb") as f:
                f.write(file_info["data"])

            stat = os.stat(file_path)
            saved_files.append({
                "name": filename,
                "size": stat.st_size,
                "size_formatted": format_size(stat.st_size),
                "category": get_file_category(filename)
            })

        now = time.time()
        expires_at = now + (30 * 60) # 30 minutes lifetime

        share_data = {
            "share_id": share_id,
            "title": title.strip() or "Public Share Drop",
            "password_hash": hash_password(password),
            "uploader_ip": uploader_ip,
            "created_at": now,
            "expires_at": expires_at,
            "created_at_formatted": datetime.fromtimestamp(now).strftime("%H:%M:%S (%b %d)"),
            "files": saved_files
        }

        public_shares[share_id] = share_data
        return share_data

def cleanup_expired_shares():
    with shares_lock:
        now = time.time()
        expired_ids = [s_id for s_id, data in public_shares.items() if data['expires_at'] < now]

        for s_id in expired_ids:
            share_dir = os.path.join(PUBLIC_SHARES_DIR, s_id)
            if os.path.exists(share_dir):
                try:
                    shutil.rmtree(share_dir)
                except Exception as e:
                    print(f"Error removing expired public share directory {s_id}: {e}")
            del public_shares[s_id]

        # Clean expired unlock tokens
        expired_tokens = [tok for tok, data in unlocked_tokens.items() if data['expires_at'] < now]
        for tok in expired_tokens:
            del unlocked_tokens[tok]

def list_public_shares():
    cleanup_expired_shares()
    with shares_lock:
        now = time.time()
        result = []
        for s_id, data in public_shares.items():
            remaining = max(0, int(data['expires_at'] - now))
            result.append({
                "share_id": s_id,
                "title": data["title"],
                "file_count": len(data["files"]),
                "total_size": sum(f["size"] for f in data["files"]),
                "total_size_formatted": format_size(sum(f["size"] for f in data["files"])),
                "created_at": data["created_at"],
                "created_at_formatted": data["created_at_formatted"],
                "expires_at": data["expires_at"],
                "expires_in_seconds": remaining,
                "is_protected": True
            })
        # Sort newest first
        result.sort(key=lambda x: x["created_at"], reverse=True)
        return result

def unlock_public_share(share_id, password):
    cleanup_expired_shares()
    with shares_lock:
        if share_id not in public_shares:
            return None, "Public share not found or expired"

        share = public_shares[share_id]
        if hash_password(password) != share["password_hash"]:
            return None, "Invalid password for this public share drop"

        token = secrets.token_hex(20)
        unlocked_tokens[token] = {
            "share_id": share_id,
            "expires_at": share["expires_at"]
        }

        files_info = []
        for f in share["files"]:
            files_info.append({
                "name": f["name"],
                "size": f["size"],
                "size_formatted": f["size_formatted"],
                "category": f["category"],
                "download_url": f"/api/public/download/{share_id}/{f['name']}?unlock_token={token}"
            })

        return {
            "token": token,
            "share_id": share_id,
            "title": share["title"],
            "expires_in_seconds": max(0, int(share["expires_at"] - time.time())),
            "files": files_info
        }, None

def is_unlocked(share_id, unlock_token):
    with shares_lock:
        if not unlock_token:
            return False
        if unlock_token in unlocked_tokens:
            info = unlocked_tokens[unlock_token]
            if info["share_id"] == share_id and info["expires_at"] > time.time():
                return True
        return False

def get_share_file_path(share_id, filename, unlock_token):
    cleanup_expired_shares()
    with shares_lock:
        if share_id not in public_shares:
            return None, "Public share drop expired or not found"
        if not is_unlocked(share_id, unlock_token):
            return None, "Unauthorized. Password unlock required"

        safe_filename = os.path.basename(filename)
        share_dir = os.path.join(PUBLIC_SHARES_DIR, share_id)
        file_path = os.path.abspath(os.path.join(share_dir, safe_filename))

        if not file_path.startswith(share_dir) or not os.path.exists(file_path):
            return None, "File not found in share drop"

        return file_path, None

def _cleanup_loop():
    while True:
        try:
            cleanup_expired_shares()
        except Exception as e:
            print(f"Error in public share cleanup loop: {e}")
        time.sleep(30)

def start_public_shares_cleanup_thread():
    global cleanup_thread_started
    if not cleanup_thread_started:
        cleanup_thread_started = True
        t = threading.Thread(target=_cleanup_loop, daemon=True)
        t.start()
