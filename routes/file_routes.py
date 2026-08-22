import os
import shutil
import urllib.parse
import mimetypes
from datetime import datetime

from config import PORT, STORAGE_DIR
from core.storage import get_local_ips, format_size, get_file_category, get_preview_info

def handle_file_routes(handler, path, method):
    if method == 'GET':
        # Public Info Endpoint
        if path == '/api/info':
            ips = get_local_ips()
            client_ip = handler.get_client_ip()
            handler.send_json({
                "local_ips": ips,
                "port": PORT,
                "primary_ip": ips[0] if ips else '127.0.0.1',
                "primary_url": f"http://{ips[0]}:{PORT}" if ips else f"http://127.0.0.1:{PORT}",
                "storage_dir": STORAGE_DIR,
                "your_client_ip": client_ip
            })
            return True

        # Protected File Listing
        if path == '/api/files':
            session = handler.authenticate(required_permission='read')
            if not session:
                return True
            files_info = []
            try:
                for entry in sorted(os.listdir(STORAGE_DIR)):
                    if entry == '.gitkeep':
                        continue
                    full_path = os.path.join(STORAGE_DIR, entry)
                    if os.path.isfile(full_path):
                        stat = os.stat(full_path)
                        prev_info = get_preview_info(entry)
                        files_info.append({
                            "name": entry,
                            "size": stat.st_size,
                            "size_formatted": format_size(stat.st_size),
                            "mod_time": stat.st_mtime,
                            "mod_time_formatted": datetime.fromtimestamp(stat.st_mtime).strftime("%b %d, %Y %H:%M"),
                            "category": get_file_category(entry),
                            "previewable": prev_info["previewable"],
                            "preview_type": prev_info["preview_type"],
                            "url": f"/shared_files/{urllib.parse.quote(entry)}"
                        })
            except Exception as e:
                handler.send_error_msg(f"Failed to list files: {str(e)}", status=500)
                return True
            handler.send_json({"files": files_info})
            return True

        # Serve / Stream Shared File
        if path.startswith('/shared_files/'):
            session = handler.authenticate(required_permission='read')
            if not session:
                return True
            filename = urllib.parse.unquote(path[len('/shared_files/'):])
            file_path = os.path.abspath(os.path.join(STORAGE_DIR, filename))
            if not file_path.startswith(STORAGE_DIR) or not os.path.exists(file_path):
                handler.send_error_msg("File not found", status=404)
                return True
            try:
                mime_type, _ = mimetypes.guess_type(file_path)
                if not mime_type:
                    mime_type = 'application/octet-stream'
                file_size = os.path.getsize(file_path)
                handler.send_response(200)
                handler.send_header('Content-Type', mime_type)
                handler.send_header('Content-Length', str(file_size))
                handler.send_header('Content-Disposition', f'inline; filename="{urllib.parse.quote(filename)}"')
                handler.send_header('Access-Control-Allow-Origin', '*')
                handler.end_headers()
                with open(file_path, 'rb') as f:
                    shutil.copyfileobj(f, handler.wfile)
            except Exception as e:
                handler.send_error_msg(f"Error reading file: {str(e)}", status=500)
            return True

    elif method == 'POST':
        # File Upload Endpoint
        if path == '/api/upload':
            session = handler.authenticate(required_permission='write')
            if not session:
                return True
            content_type = handler.headers.get('Content-Type', '')
            if 'multipart/form-data' not in content_type:
                handler.send_error_msg("Content-Type must be multipart/form-data", status=400)
                return True

            boundary = content_type.split("boundary=")[-1].encode('ascii')
            content_length = int(handler.headers.get('Content-Length', 0))
            uploaded_files = []
            try:
                body = handler.rfile.read(content_length)
                parts = body.split(b'--' + boundary)
                for part in parts:
                    if not part or part == b'--\r\n' or part == b'--':
                        continue
                    if b'\r\n\r\n' in part:
                        headers_raw, file_data = part.split(b'\r\n\r\n', 1)
                        if file_data.endswith(b'\r\n'):
                            file_data = file_data[:-2]
                        headers_str = headers_raw.decode('utf-8', errors='replace')
                        if 'filename=' in headers_str:
                            filename_part = headers_str.split('filename=')[1].split('\r\n')[0].strip('"')
                            filename = os.path.basename(filename_part)
                            if filename:
                                dest_path = os.path.join(STORAGE_DIR, filename)
                                with open(dest_path, 'wb') as f:
                                    f.write(file_data)
                                uploaded_files.append(filename)
                handler.send_json({
                    "status": "success",
                    "uploaded_files": uploaded_files,
                    "message": f"Successfully uploaded {len(uploaded_files)} file(s)"
                })
            except Exception as e:
                handler.send_error_msg(f"Failed to process file upload: {str(e)}", status=500)
            return True

    elif method == 'DELETE':
        # File Deletion Endpoint
        if path.startswith('/api/files/'):
            session = handler.authenticate(required_permission='delete')
            if not session:
                return True
            filename = urllib.parse.unquote(path[len('/api/files/'):])
            if filename == '.gitkeep':
                handler.send_error_msg("Protected file cannot be deleted", status=403)
                return True
            file_path = os.path.abspath(os.path.join(STORAGE_DIR, filename))
            if not file_path.startswith(STORAGE_DIR) or not os.path.exists(file_path):
                handler.send_error_msg("File not found or access denied", status=404)
                return True
            try:
                os.remove(file_path)
                handler.send_json({"status": "success", "message": f"Deleted {filename}"})
            except Exception as e:
                handler.send_error_msg(f"Failed to delete file: {str(e)}", status=500)
            return True

    return False
