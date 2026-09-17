import os
import json
import urllib.parse
import mimetypes
import shutil

from config import PORT
from core.storage import get_local_ips
from core.drops_engine import (
    create_file_drop,
    create_text_drop,
    list_drops,
    unlock_drop,
    get_drop_file_path
)

def handle_drop_routes(handler, path, method):
    parsed = urllib.parse.urlparse(handler.path)
    clean_path = parsed.path

    # Server Info Endpoint
    if method == 'GET' and clean_path == '/api/info':
        ips = get_local_ips()
        handler.send_json({
            "primary_ip": ips[0] if ips else "127.0.0.1",
            "ips": ips,
            "port": PORT
        })
        return True

    # List All Active Drops Endpoint
    if method == 'GET' and clean_path == '/api/drops':
        active_drops = list_drops()
        handler.send_json({"drops": active_drops})
        return True

    # Create Text Paste Drop Endpoint
    if method == 'POST' and clean_path == '/api/drops/paste':
        content_length = int(handler.headers.get('Content-Length', 0))
        if content_length == 0:
            handler.send_error_msg("Empty request body", status=400)
            return True

        body = handler.rfile.read(content_length)
        try:
            data = json.loads(body.decode('utf-8'))
            content = data.get("content", "").strip()
            password = data.get("password", "").strip()
            title = data.get("title", "").strip()
            lifetime = int(data.get("lifetime", 30))
            burn_after_read = bool(data.get("burn_after_read", False))

            if not content:
                handler.send_error_msg("Text content cannot be empty", status=400)
                return True
            if not password:
                handler.send_error_msg("A password or PIN is required to lock this text paste", status=400)
                return True

            client_ip = handler.get_client_ip()
            drop_data = create_text_drop(
                content=content,
                password=password,
                title=title,
                uploader_ip=client_ip,
                lifetime_minutes=lifetime,
                burn_after_read=burn_after_read
            )

            handler.send_json({
                "status": "success",
                "message": f"Locked text note created! Expiring in {lifetime} minutes.",
                "drop_id": drop_data["drop_id"],
                "drop_type": "text",
                "title": drop_data["title"],
                "expires_at": drop_data["expires_at"],
                "burn_after_read": drop_data["burn_after_read"],
                "line_count": drop_data["line_count"],
                "char_count": drop_data["char_count"]
            })
        except Exception as e:
            handler.send_error_msg(f"Failed to create text drop: {str(e)}", status=400)
        return True

    # Create File Upload Drop Endpoint (Multipart Form Data)
    if method == 'POST' and clean_path == '/api/drops/upload':
        content_type = handler.headers.get('Content-Type', '')
        if 'multipart/form-data' not in content_type:
            handler.send_error_msg("Content-Type must be multipart/form-data", status=400)
            return True

        boundary_field = content_type.split("boundary=")[-1].strip()
        # Strip potential quotes around boundary
        if boundary_field.startswith('"') and boundary_field.endswith('"'):
            boundary_field = boundary_field[1:-1]
        boundary = boundary_field.encode('ascii')
        content_length = int(handler.headers.get('Content-Length', 0))

        uploaded_files = []
        password = ""
        title = ""
        lifetime = 30

        try:
            body = handler.rfile.read(content_length)
            parts = body.split(b'--' + boundary)

            for part in parts:
                if not part or part == b'--\r\n' or part == b'--' or part == b'--\r\n\r\n':
                    continue
                if b'\r\n\r\n' in part:
                    headers_raw, field_data = part.split(b'\r\n\r\n', 1)
                    if field_data.endswith(b'\r\n'):
                        field_data = field_data[:-2]
                    headers_str = headers_raw.decode('utf-8', errors='replace')

                    if 'name="password"' in headers_str:
                        password = field_data.decode('utf-8', errors='replace').strip()
                    elif 'name="title"' in headers_str:
                        title = field_data.decode('utf-8', errors='replace').strip()
                    elif 'name="lifetime"' in headers_str:
                        try:
                            lifetime = int(field_data.decode('utf-8', errors='replace').strip())
                        except ValueError:
                            lifetime = 30
                    elif 'filename=' in headers_str:
                        filename_part = headers_str.split('filename=')[1].split('\r\n')[0].strip('"')
                        filename = os.path.basename(filename_part)
                        if filename:
                            uploaded_files.append({
                                "filename": filename,
                                "data": field_data
                            })

            if not password:
                handler.send_error_msg("Password or PIN is required to lock file drop", status=400)
                return True

            if not uploaded_files:
                handler.send_error_msg("At least one file must be selected for upload", status=400)
                return True

            client_ip = handler.get_client_ip()
            drop_data = create_file_drop(
                uploaded_files=uploaded_files,
                password=password,
                title=title,
                uploader_ip=client_ip,
                lifetime_minutes=lifetime
            )

            handler.send_json({
                "status": "success",
                "message": f"File drop created successfully! Expiring in {lifetime} minutes.",
                "drop_id": drop_data["drop_id"],
                "drop_type": "files",
                "title": drop_data["title"],
                "expires_at": drop_data["expires_at"],
                "file_count": len(drop_data["files"])
            })
        except Exception as e:
            handler.send_error_msg(f"Failed to create file drop: {str(e)}", status=500)
        return True

    # Unlock Drop Endpoint (Universal for both files and text)
    if method == 'POST' and clean_path == '/api/drops/unlock':
        content_length = int(handler.headers.get('Content-Length', 0))
        body = handler.rfile.read(content_length)
        try:
            data = json.loads(body.decode('utf-8'))
            drop_id = data.get("drop_id", "").strip().upper()
            password = data.get("password", "").strip()

            if not drop_id or not password:
                handler.send_error_msg("Drop ID and Password are required", status=400)
                return True

            result, error = unlock_drop(drop_id, password)
            if error:
                handler.send_error_msg(error, status=401)
                return True

            handler.send_json({"status": "success", "unlocked": result})
        except Exception as e:
            handler.send_error_msg(f"Unlock error: {str(e)}", status=400)
        return True

    # Download File from Drop Endpoint
    if method == 'GET' and clean_path.startswith('/api/drops/download/'):
        # Format: /api/drops/download/<drop_id>/<filename>
        parts = clean_path[len('/api/drops/download/'):].split('/', 1)
        if len(parts) < 2:
            handler.send_error_msg("Invalid download path format", status=400)
            return True

        drop_id = urllib.parse.unquote(parts[0]).upper()
        filename = urllib.parse.unquote(parts[1])

        params = urllib.parse.parse_qs(parsed.query)
        token = params.get('token', [''])[0] or handler.headers.get('X-Unlock-Token', '')

        file_path, error = get_drop_file_path(drop_id, filename, token)
        if error:
            handler.send_error_msg(error, status=401 if 'Unauthorized' in error else 404)
            return True

        try:
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                mime_type = 'application/octet-stream'
            file_size = os.path.getsize(file_path)

            handler.send_response(200)
            handler.send_header('Content-Type', mime_type)
            handler.send_header('Content-Length', str(file_size))
            handler.send_header('Content-Disposition', f'attachment; filename="{urllib.parse.quote(filename)}"')
            handler.send_header('Access-Control-Allow-Origin', '*')
            handler.end_headers()

            with open(file_path, 'rb') as f:
                shutil.copyfileobj(f, handler.wfile)
        except Exception as e:
            handler.send_error_msg(f"Error streaming file: {str(e)}", status=500)
        return True

    return False

