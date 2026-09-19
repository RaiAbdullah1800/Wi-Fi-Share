import time
import secrets
import random
import string
import threading
import hashlib
from datetime import datetime

# Maximum lifetime permitted for any chat room (24 Hours = 1440 Minutes)
MAX_LIFETIME_MINUTES = 1440
DEFAULT_LIFETIME_MINUTES = 180 # 3 Hours
MAX_MESSAGE_LENGTH = 2000
MAX_MESSAGES_PER_ROOM = 1000

# Thread-safe in-memory stores
chat_rooms = {}
chat_tokens = {}
chat_lock = threading.RLock()
chat_cleanup_started = False

def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def generate_room_id():
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=6))

def sanitize_name(name):
    clean = (name or '').strip()
    if not clean:
        clean = f"User-{random.randint(100, 999)}"
    return clean[:25]

def create_room(title, password, lifetime_minutes=DEFAULT_LIFETIME_MINUTES, creator_name="Host", client_ip="127.0.0.1"):
    with chat_lock:
        cleanup_expired_rooms()
        room_id = generate_room_id()
        while room_id in chat_rooms:
            room_id = generate_room_id()

        try:
            lifetime = int(lifetime_minutes)
        except (ValueError, TypeError):
            lifetime = DEFAULT_LIFETIME_MINUTES

        # Enforce maximum 24-hour lifetime (1440 minutes)
        lifetime = max(5, min(lifetime, MAX_LIFETIME_MINUTES))
        now = time.time()
        expires_at = now + (lifetime * 60)

        clean_title = (title or '').strip() or f"Chat Room #{room_id}"
        clean_creator = sanitize_name(creator_name)

        room = {
            "room_id": room_id,
            "title": clean_title,
            "password_hash": hash_password(password.strip()),
            "creator_ip": client_ip,
            "creator_name": clean_creator,
            "created_at": now,
            "expires_at": expires_at,
            "created_at_formatted": datetime.fromtimestamp(now).strftime("%H:%M (%b %d)"),
            "seq_counter": 1,
            "messages": [
                {
                    "id": 1,
                    "user": "System",
                    "text": f"🎉 Room created by {clean_creator}. Welcome!",
                    "timestamp": now,
                    "time_formatted": datetime.fromtimestamp(now).strftime("%H:%M"),
                    "is_system": True
                }
            ],
            "active_users": {}
        }

        # Issue creator session token
        token = secrets.token_hex(20)
        chat_tokens[token] = {
            "room_id": room_id,
            "user_name": clean_creator,
            "expires_at": expires_at
        }
        room["active_users"][token] = {
            "name": clean_creator,
            "joined_at": now,
            "last_seen": now
        }

        chat_rooms[room_id] = room

        return {
            "token": token,
            "room_id": room_id,
            "title": clean_title,
            "user_name": clean_creator,
            "expires_at": expires_at,
            "expires_in_seconds": int(expires_at - now),
            "created_at_formatted": room["created_at_formatted"]
        }

def list_rooms():
    with chat_lock:
        cleanup_expired_rooms()
        now = time.time()
        results = []
        for r_id, r in chat_rooms.items():
            remaining = max(0, int(r["expires_at"] - now))
            results.append({
                "room_id": r_id,
                "title": r["title"],
                "creator_name": r["creator_name"],
                "created_at": r["created_at"],
                "created_at_formatted": r["created_at_formatted"],
                "expires_at": r["expires_at"],
                "expires_in_seconds": remaining,
                "participant_count": len(r["active_users"]),
                "message_count": len(r["messages"]),
                "is_locked": True
            })

        results.sort(key=lambda x: x["created_at"], reverse=True)
        return results

def join_room(room_id, password, user_name, client_ip="127.0.0.1"):
    with chat_lock:
        cleanup_expired_rooms()
        room_id = (room_id or '').strip().upper()
        if room_id not in chat_rooms:
            return None, "Chat room not found or has expired"

        room = chat_rooms[room_id]
        if hash_password((password or '').strip()) != room["password_hash"]:
            return None, "Incorrect room password or PIN"

        now = time.time()
        clean_user = sanitize_name(user_name)

        token = secrets.token_hex(20)
        chat_tokens[token] = {
            "room_id": room_id,
            "user_name": clean_user,
            "expires_at": room["expires_at"]
        }
        room["active_users"][token] = {
            "name": clean_user,
            "joined_at": now,
            "last_seen": now
        }

        # Post system join message
        room["seq_counter"] += 1
        join_msg = {
            "id": room["seq_counter"],
            "user": "System",
            "text": f"👋 {clean_user} joined the chat.",
            "timestamp": now,
            "time_formatted": datetime.fromtimestamp(now).strftime("%H:%M"),
            "is_system": True
        }
        room["messages"].append(join_msg)

        return {
            "token": token,
            "room_id": room_id,
            "title": room["title"],
            "user_name": clean_user,
            "expires_at": room["expires_at"],
            "expires_in_seconds": max(0, int(room["expires_at"] - now)),
            "created_at_formatted": room["created_at_formatted"]
        }, None

def leave_room(token):
    with chat_lock:
        if not token or token not in chat_tokens:
            return False

        t_data = chat_tokens.pop(token)
        room_id = t_data["room_id"]
        user_name = t_data["user_name"]

        if room_id in chat_rooms:
            room = chat_rooms[room_id]
            if token in room["active_users"]:
                del room["active_users"][token]

            now = time.time()
            room["seq_counter"] += 1
            leave_msg = {
                "id": room["seq_counter"],
                "user": "System",
                "text": f"🚪 {user_name} left the chat.",
                "timestamp": now,
                "time_formatted": datetime.fromtimestamp(now).strftime("%H:%M"),
                "is_system": True
            }
            room["messages"].append(leave_msg)

        return True

def post_message(token, text, client_ip="127.0.0.1"):
    with chat_lock:
        cleanup_expired_rooms()
        if not token or token not in chat_tokens:
            return None, "Unauthorized. Valid room token required"

        t_data = chat_tokens[token]
        room_id = t_data["room_id"]
        user_name = t_data["user_name"]

        if room_id not in chat_rooms:
            return None, "Chat room has expired or no longer exists"

        room = chat_rooms[room_id]
        clean_text = (text or '').strip()
        if not clean_text:
            return None, "Message cannot be empty"

        if len(clean_text) > MAX_MESSAGE_LENGTH:
            clean_text = clean_text[:MAX_MESSAGE_LENGTH]

        now = time.time()
        room["seq_counter"] += 1
        msg = {
            "id": room["seq_counter"],
            "user": user_name,
            "text": clean_text,
            "timestamp": now,
            "time_formatted": datetime.fromtimestamp(now).strftime("%H:%M"),
            "is_system": False
        }

        room["messages"].append(msg)
        if len(room["messages"]) > MAX_MESSAGES_PER_ROOM:
            room["messages"] = room["messages"][-MAX_MESSAGES_PER_ROOM:]

        if token in room["active_users"]:
            room["active_users"][token]["last_seen"] = now

        return msg, None

def get_messages(token, after_seq=0):
    with chat_lock:
        cleanup_expired_rooms()
        if not token or token not in chat_tokens:
            return None, "Unauthorized. Valid room token required"

        t_data = chat_tokens[token]
        room_id = t_data["room_id"]
        if room_id not in chat_rooms:
            return None, "Chat room has expired or no longer exists"

        room = chat_rooms[room_id]
        now = time.time()

        if token in room["active_users"]:
            room["active_users"][token]["last_seen"] = now

        try:
            after_id = int(after_seq)
        except (ValueError, TypeError):
            after_id = 0

        delta_messages = [m for m in room["messages"] if m["id"] > after_id]

        participants = list({u["name"] for u in room["active_users"].values()})

        return {
            "room_id": room_id,
            "title": room["title"],
            "messages": delta_messages,
            "participants": participants,
            "participant_count": len(participants),
            "expires_in_seconds": max(0, int(room["expires_at"] - now))
        }, None

def cleanup_expired_rooms():
    with chat_lock:
        now = time.time()
        expired_room_ids = [r_id for r_id, r in chat_rooms.items() if r["expires_at"] < now]

        for r_id in expired_room_ids:
            del chat_rooms[r_id]

        expired_tokens = [tok for tok, t in chat_tokens.items() if t["expires_at"] < now or t["room_id"] in expired_room_ids]
        for tok in expired_tokens:
            del chat_tokens[tok]

def _cleanup_loop():
    while True:
        try:
            cleanup_expired_rooms()
        except Exception as e:
            print(f"Error in chat cleanup loop: {e}")
        time.sleep(30)

def start_chat_cleanup_thread():
    global chat_cleanup_started
    if not chat_cleanup_started:
        chat_cleanup_started = True
        t = threading.Thread(target=_cleanup_loop, daemon=True)
        t.start()

