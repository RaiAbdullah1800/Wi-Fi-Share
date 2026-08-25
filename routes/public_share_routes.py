import os
import json
import urllib.parse
import mimetypes
import shutil
from core.public_share import (
    create_public_share,
    list_public_shares,
    unlock_public_share,
    get_share_file_path
)

def handle_public_share_routes(handler, path, method):
    parsed = urllib.parse.urlparse(handler.path)
    clean_path = parsed.path

    # Public List Endpoint
    if method == 'GET' and clean_path == '/api/public/list':
        shares = list_public_shares()
        handler.send_json({"public_shares": shares})
        return True

    # Public Unlock Endpoint
    if method == 'POST' and clean_path == '/api/public/unlock':
        content_length = int(handler.headers.get('Content-Length', 0))
        body = handler.rfile.read(content_length)
        try:
            data = json.loads(body.decode('utf-8'))
            share_id = data.get("share_id", "").strip()
            password = data.get("password", "").strip()

            if not share_id or not password:
                handler.send_error_msg("Share ID and Password are required", status=400)
                return True

            result, error = unlock_public_share(share_id, password)
            if error:
                handler.send_error_msg(error, status=401)
                return True

            handler.send_json({"status": "success", "unlocked": result})
        except Exception as e:
            handler.send_error_msg(f"Unlock error: {str(e)}", status=400)
        return True

    # Public Create Drop Endpoint (Multipart Upload)
    if method == 'POST' and clean_path == '/api/public/create':
        content_type = handler.headers.get('Content-Type', '')
        if 'multipart/form-data' not in content_type:
            handler.send_error_msg("Content-Type must be multipart/form-data", status=400)
            return True

        boundary = content_type.split("boundary=")[-1].encode('ascii')
        content_length = int(handler.headers.get('Content-Length', 0))
        
        uploaded_files = []
        password = ""
        title = "Public Share Drop"

        try:
            body = handler.rfile.read(content_length)
            parts = body.split(b'--' + boundary)
            
            for part in parts:
                if not part or part == b'--\r\n' or part == b'--':
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
                    elif 'filename=' in headers_str:
                        filename_part = headers_str.split('filename=')[1].split('\r\n')[0].strip('"')
                        filename = os.path.basename(filename_part)
                        if filename:
                            uploaded_files.append({
                                "filename": filename,
                                "data": field_data
                            })

            if not password:
                handler.send_error_msg("Password is required for public share drops", status=400)
                return True

            if not uploaded_files:
                handler.send_error_msg("At least one file must be selected for upload", status=400)
                return True

            client_ip = handler.get_client_ip()
            share_data = create_public_share(uploaded_files, password, title, client_ip)

            handler.send_json({
                "status": "success",
                "message": "Public Share Drop created successfully! It will expire in 30 minutes.",
                "share_id": share_data["share_id"],
                "expires_at": share_data["expires_at"],
                "files_count": len(share_data["files"])
            })
        except Exception as e:
            handler.send_error_msg(f"Failed to create public drop: {str(e)}", status=500)
        return True

    # Public Download File Endpoint
    if method == 'GET' and clean_path.startswith('/api/public/download/'):
        # URL format: /api/public/download/<share_id>/<filename>
        parts = clean_path[len('/api/public/download/'):].split('/', 1)
        if len(parts) < 2:
            handler.send_error_msg("Invalid download path format", status=400)
            return True

        share_id = urllib.parse.unquote(parts[0])
        filename = urllib.parse.unquote(parts[1])

        params = urllib.parse.parse_qs(parsed.query)
        unlock_token = params.get('unlock_token', [''])[0] or handler.headers.get('X-Unlock-Token', '')

        file_path, error = get_share_file_path(share_id, filename, unlock_token)
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
            handler.send_error_msg(f"Error reading file: {str(e)}", status=500)
        return True

    return False
