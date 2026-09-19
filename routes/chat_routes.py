import json
import urllib.parse

from core.chat_engine import (
    create_room,
    list_rooms,
    join_room,
    leave_room,
    post_message,
    get_messages
)

def get_token_from_request(handler, data=None):
    # Check JSON body first if provided
    if data and isinstance(data, dict) and data.get("token"):
        return data.get("token").strip()

    # Check Authorization Header: Bearer <token>
    auth = handler.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        return auth[7:].strip()

    # Check query params: ?token=...
    parsed = urllib.parse.urlparse(handler.path)
    params = urllib.parse.parse_qs(parsed.query)
    if 'token' in params and params['token']:
        return params['token'][0].strip()

    return None

def handle_chat_routes(handler, path, method):
    parsed = urllib.parse.urlparse(handler.path)
    clean_path = parsed.path

    # List all active rooms
    if method == 'GET' and clean_path == '/api/chats':
        rooms = list_rooms()
        handler.send_json({"rooms": rooms})
        return True

    # Create new chat room
    if method == 'POST' and clean_path == '/api/chats/create':
        content_length = int(handler.headers.get('Content-Length', 0))
        if content_length == 0:
            handler.send_error_msg("Empty request body", status=400)
            return True

        try:
            body = handler.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))
            title = data.get("title", "").strip()
            password = data.get("password", "").strip()
            lifetime = data.get("lifetime_minutes", 180)
            creator_name = data.get("creator_name", "Host").strip()

            if not password:
                handler.send_error_msg("A password or PIN is required to lock this chat room", status=400)
                return True

            client_ip = handler.get_client_ip()
            room_session = create_room(
                title=title,
                password=password,
                lifetime_minutes=lifetime,
                creator_name=creator_name,
                client_ip=client_ip
            )

            handler.send_json({
                "status": "success",
                "message": "Chat room created successfully!",
                "session": room_session
            })
        except Exception as e:
            handler.send_error_msg(f"Failed to create chat room: {str(e)}", status=400)
        return True

    # Join chat room with password
    if method == 'POST' and clean_path == '/api/chats/join':
        content_length = int(handler.headers.get('Content-Length', 0))
        try:
            body = handler.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))
            room_id = data.get("room_id", "").strip().upper()
            password = data.get("password", "").strip()
            user_name = data.get("user_name", "Anonymous").strip()

            if not room_id or not password:
                handler.send_error_msg("Room ID and Password are required", status=400)
                return True

            client_ip = handler.get_client_ip()
            session, error = join_room(room_id, password, user_name, client_ip)
            if error:
                handler.send_error_msg(error, status=401)
                return True

            handler.send_json({
                "status": "success",
                "message": f"Joined room {room_id} successfully!",
                "session": session
            })
        except Exception as e:
            handler.send_error_msg(f"Failed to join chat room: {str(e)}", status=400)
        return True

    # Leave room (logout)
    if method == 'POST' and clean_path == '/api/chats/leave':
        content_length = int(handler.headers.get('Content-Length', 0))
        token = None
        if content_length > 0:
            try:
                body = handler.rfile.read(content_length)
                data = json.loads(body.decode('utf-8'))
                token = get_token_from_request(handler, data)
            except Exception:
                pass
        if not token:
            token = get_token_from_request(handler)

        leave_room(token)
        handler.send_json({"status": "success", "message": "Left chat room"})
        return True

    # Fetch delta messages
    if method == 'GET' and clean_path == '/api/chats/messages':
        params = urllib.parse.parse_qs(parsed.query)
        token = get_token_from_request(handler)
        after_seq = params.get('after', [0])[0]

        if not token:
            handler.send_error_msg("Unauthorized. Token required", status=401)
            return True

        result, error = get_messages(token, after_seq)
        if error:
            handler.send_error_msg(error, status=401)
            return True

        handler.send_json({"status": "success", **result})
        return True

    # Post message
    if method == 'POST' and clean_path == '/api/chats/message':
        content_length = int(handler.headers.get('Content-Length', 0))
        if content_length == 0:
            handler.send_error_msg("Empty message body", status=400)
            return True

        try:
            body = handler.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))
            token = get_token_from_request(handler, data)
            text = data.get("text", "").strip()

            if not token:
                handler.send_error_msg("Unauthorized. Token required", status=401)
                return True
            if not text:
                handler.send_error_msg("Message cannot be empty", status=400)
                return True

            client_ip = handler.get_client_ip()
            msg, error = post_message(token, text, client_ip)
            if error:
                handler.send_error_msg(error, status=400 if 'empty' in error else 401)
                return True

            handler.send_json({"status": "success", "message": msg})
        except Exception as e:
            handler.send_error_msg(f"Failed to post message: {str(e)}", status=400)
        return True

    return False

