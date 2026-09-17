import os
import time
import shutil
import hashlib
import secrets
import random
import string
import threading
from datetime import datetime

from config import DROPS_DIR, DEFAULT_EXPIRY_MINUTES
from core.storage import format_size, get_file_category

# Thread-safe in-memory drops registry & token store
drops = {}
unlocked_tokens = {}
drops_lock = threading.RLock()
cleanup_thread_started = False

def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def generate_drop_id():
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=6))

def create_file_drop(uploaded_files, password, title="", uploader_ip="127.0.0.1", lifetime_minutes=DEFAULT_EXPIRY_MINUTES):
    with drops_lock:
        drop_id = generate_drop_id()
        while drop_id in drops:
            drop_id = generate_drop_id()

        drop_dir = os.path.join(DROPS_DIR, drop_id)
        os.makedirs(drop_dir, exist_ok=True)

        saved_files = []
        for file_info in uploaded_files:
            # file_info = { "filename": str, "data": bytes }
            filename = os.path.basename(file_info["filename"])
            if not filename:
                continue

            file_path = os.path.join(drop_dir, filename)
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
        lifetime = max(1, int(lifetime_minutes)) * 60
        expires_at = now + lifetime

        clean_title = title.strip() if title and title.strip() else f"File Drop ({len(saved_files)} file{'s' if len(saved_files) != 1 else ''})"

        drop_data = {
            "drop_id": drop_id,
            "drop_type": "files",
            "title": clean_title,
            "password_hash": hash_password(password),
            "uploader_ip": uploader_ip,
            "created_at": now,
            "expires_at": expires_at,
            "created_at_formatted": datetime.fromtimestamp(now).strftime("%H:%M:%S (%b %d)"),
            "files": saved_files
        }

        drops[drop_id] = drop_data
        return drop_data

def create_text_drop(content, password, title="", uploader_ip="127.0.0.1", lifetime_minutes=DEFAULT_EXPIRY_MINUTES, burn_after_read=False):
    with drops_lock:
        drop_id = generate_drop_id()
        while drop_id in drops:
            drop_id = generate_drop_id()

        now = time.time()
        lifetime = max(1, int(lifetime_minutes)) * 60
        expires_at = now + lifetime

        clean_content = content or ""
        lines = clean_content.splitlines()
        line_count = len(lines)
        char_count = len(clean_content)

        clean_title = title.strip() if title and title.strip() else "Quick Text Note"

        drop_data = {
            "drop_id": drop_id,
            "drop_type": "text",
            "title": clean_title,
            "content": clean_content,
            "line_count": line_count,
            "char_count": char_count,
            "burn_after_read": bool(burn_after_read),
            "password_hash": hash_password(password),
            "uploader_ip": uploader_ip,
            "created_at": now,
            "expires_at": expires_at,
            "created_at_formatted": datetime.fromtimestamp(now).strftime("%H:%M:%S (%b %d)")
        }

        drops[drop_id] = drop_data
        return drop_data

def cleanup_expired_drops():
    with drops_lock:
        now = time.time()
        expired_ids = [d_id for d_id, data in drops.items() if data['expires_at'] < now]

        for d_id in expired_ids:
            _delete_drop_resources(d_id)
            del drops[d_id]

        expired_tokens = [tok for tok, data in unlocked_tokens.items() if data['expires_at'] < now]
        for tok in expired_tokens:
            del unlocked_tokens[tok]

def _delete_drop_resources(drop_id):
    drop_dir = os.path.join(DROPS_DIR, drop_id)
    if os.path.exists(drop_dir):
        try:
            shutil.rmtree(drop_dir)
        except Exception as e:
            print(f"Error removing drop folder {drop_id}: {e}")

def list_drops():
    cleanup_expired_drops()
    with drops_lock:
        now = time.time()
        result = []
        for d_id, data in drops.items():
            remaining = max(0, int(data['expires_at'] - now))
            item = {
                "drop_id": d_id,
                "drop_type": data["drop_type"],
                "title": data["title"],
                "created_at": data["created_at"],
                "created_at_formatted": data["created_at_formatted"],
                "expires_at": data["expires_at"],
                "expires_in_seconds": remaining,
                "is_locked": True
            }

            if data["drop_type"] == "files":
                item["file_count"] = len(data["files"])
                item["total_size"] = sum(f["size"] for f in data["files"])
                item["total_size_formatted"] = format_size(item["total_size"])
            elif data["drop_type"] == "text":
                item["line_count"] = data["line_count"]
                item["char_count"] = data["char_count"]
                item["burn_after_read"] = data.get("burn_after_read", False)

            result.append(item)

        # Newest first
        result.sort(key=lambda x: x["created_at"], reverse=True)
        return result

def unlock_drop(drop_id, password):
    cleanup_expired_drops()
    with drops_lock:
        if drop_id not in drops:
            return None, "Drop not found or has expired"

        drop = drops[drop_id]
        if hash_password(password) != drop["password_hash"]:
            return None, "Incorrect password or PIN"

        token = secrets.token_hex(20)
        unlocked_tokens[token] = {
            "drop_id": drop_id,
            "expires_at": drop["expires_at"]
        }

        # Response payload based on drop type
        if drop["drop_type"] == "files":
            files_info = []
            for f in drop["files"]:
                files_info.append({
                    "name": f["name"],
                    "size": f["size"],
                    "size_formatted": f["size_formatted"],
                    "category": f["category"],
                    "download_url": f"/api/drops/download/{drop_id}/{f['name']}?token={token}"
                })

            return {
                "token": token,
                "drop_id": drop_id,
                "drop_type": "files",
                "title": drop["title"],
                "expires_in_seconds": max(0, int(drop["expires_at"] - time.time())),
                "files": files_info
            }, None

        elif drop["drop_type"] == "text":
            content = drop["content"]
            is_burned = drop.get("burn_after_read", False)

            result_data = {
                "token": token,
                "drop_id": drop_id,
                "drop_type": "text",
                "title": drop["title"],
                "content": content,
                "line_count": drop["line_count"],
                "char_count": drop["char_count"],
                "burn_after_read": is_burned,
                "expires_in_seconds": max(0, int(drop["expires_at"] - time.time()))
            }

            # If burn after read: remove from active drops immediately
            if is_burned:
                _delete_drop_resources(drop_id)
                del drops[drop_id]

            return result_data, None

def is_unlocked(drop_id, token):
    with drops_lock:
        if not token or token not in unlocked_tokens:
            return False
        info = unlocked_tokens[token]
        return info["drop_id"] == drop_id and info["expires_at"] > time.time()

def get_drop_file_path(drop_id, filename, token):
    cleanup_expired_drops()
    with drops_lock:
        if drop_id not in drops:
            return None, "Drop expired or not found"
        if not is_unlocked(drop_id, token):
            return None, "Unauthorized. Valid unlock token required"

        drop_dir = os.path.abspath(os.path.join(DROPS_DIR, drop_id))
        safe_filename = os.path.basename(filename)
        file_path = os.path.abspath(os.path.join(drop_dir, safe_filename))

        if not file_path.startswith(drop_dir) or not os.path.exists(file_path):
            return None, "File not found in drop"

        return file_path, None

def _cleanup_loop():
    while True:
        try:
            cleanup_expired_drops()
        except Exception as e:
            print(f"Error in drops cleanup loop: {e}")
        time.sleep(30)

def start_drops_cleanup_thread():
    global cleanup_thread_started
    if not cleanup_thread_started:
        cleanup_thread_started = True
        t = threading.Thread(target=_cleanup_loop, daemon=True)
        t.start()

