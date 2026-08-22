import os
import sys
import socket
import json
import urllib.parse
import mimetypes
import shutil
import time
import secrets
import random
import string
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

from config import PORT, BASE_DIR, STORAGE_DIR, PUBLIC_DIR, CONFIG_FILE, config, save_config
from core.storage import get_local_ips, format_size, get_file_category, get_preview_info
from core.clipboard import get_clipboard_data, set_clipboard_data
from core.auth import (
    temp_passwords, sessions, pending_requests, approved_ips,
    clean_expired_states, get_auth_token, authenticate, generate_session_token
)

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

class RequestHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        sys.stdout.write(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]} {args[1]}\n")

    def get_client_ip(self):
        ff = self.headers.get('X-Forwarded-For')
        if ff:
            return ff.split(',')[0].strip()
        return self.client_address[0]

    def send_json(self, data, status=200):
        body = json.dumps(data).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def send_error_msg(self, message, status=400):
        self.send_json({"error": message}, status=status)

    def get_auth_token(self):
        return get_auth_token(self)

    def authenticate(self, required_permission=None):
        return authenticate(self, required_permission)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        client_ip = self.get_client_ip()

        # Public Info Endpoint
        if path == '/api/info':
            ips = get_local_ips()
            self.send_json({
                "local_ips": ips,
                "port": PORT,
                "primary_ip": ips[0] if ips else '127.0.0.1',
                "primary_url": f"http://{ips[0]}:{PORT}" if ips else f"http://127.0.0.1:{PORT}",
                "storage_dir": STORAGE_DIR,
                "your_client_ip": client_ip
            })
            return

        # Check Auth Status (Works with Token OR Approved IP)
        if path == '/api/auth/status':
            session = self.authenticate()
            if session:
                self.send_json({
                    "authenticated": True,
                    "role": session['role'],
                    "permissions": session['permissions'],
                    "expires_at": session.get('expires_at'),
                    "token": self.get_auth_token() or session.get('token')
                })
            return

        # Public API: Check IP Request Status (Used by Guest Polling Screen)
        if path == '/api/access/request-status':
            clean_expired_states()
            if client_ip in approved_ips:
                info = approved_ips[client_ip]
                self.send_json({
                    "status": "approved",
                    "client_ip": client_ip,
                    "token": info["token"],
                    "permissions": info["permissions"],
                    "expires_at": info["expires_at"],
                    "expires_in_seconds": max(0, int(info["expires_at"] - time.time()))
                })
            elif client_ip in pending_requests:
                info = pending_requests[client_ip]
                self.send_json({
                    "status": "pending",
                    "client_ip": client_ip,
                    "device_name": info["device_name"],
                    "requested_at_formatted": datetime.fromtimestamp(info["requested_at"]).strftime("%H:%M:%S")
                })
            else:
                self.send_json({"status": "none", "client_ip": client_ip})
            return

        # Admin API: List Pending Access Requests
        if path == '/api/access/pending':
            session = self.authenticate(required_permission='admin')
            if not session:
                return
            requests_list = []
            for ip, req in pending_requests.items():
                requests_list.append({
                    "ip": ip,
                    "device_name": req["device_name"],
                    "requested_at": req["requested_at"],
                    "requested_at_formatted": datetime.fromtimestamp(req["requested_at"]).strftime("%H:%M:%S")
                })
            self.send_json({"pending_requests": requests_list})
            return

        # Admin API: List Active Approved IPs
        if path == '/api/access/approved-ips':
            session = self.authenticate(required_permission='admin')
            if not session:
                return
            clean_expired_states()
            ip_list = []
            now = time.time()
            for ip, data in approved_ips.items():
                remaining = max(0, int(data['expires_at'] - now))
                ip_list.append({
                    "ip": ip,
                    "device_name": data["device_name"],
                    "permissions": data["permissions"],
                    "expires_in_seconds": remaining,
                    "expires_at_formatted": datetime.fromtimestamp(data['expires_at']).strftime("%H:%M:%S (%b %d)")
                })
            self.send_json({"approved_ips": ip_list})
            return

        # Admin API: List Temp Passwords
        if path == '/api/passwords/list':
            session = self.authenticate(required_permission='admin')
            if not session:
                return
            clean_expired_states()
            pass_list = []
            now = time.time()
            for code, data in temp_passwords.items():
                remaining = max(0, int(data['expires_at'] - now))
                pass_list.append({
                    "code": code,
                    "label": data.get("label", "Guest Key"),
                    "permissions": data["permissions"],
                    "expires_in_seconds": remaining,
                    "expires_at_formatted": datetime.fromtimestamp(data['expires_at']).strftime("%H:%M:%S (%b %d)")
                })
            self.send_json({"passwords": pass_list})
            return

        # Serve static frontend files
        target_file = path.lstrip('/')
        if not target_file:
            target_file = 'index.html'

        static_path = os.path.abspath(os.path.join(PUBLIC_DIR, target_file))

        if static_path.startswith(PUBLIC_DIR) and os.path.isfile(static_path):
            mime_type, _ = mimetypes.guess_type(static_path)
            if not mime_type:
                mime_type = 'text/plain'
            with open(static_path, 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', mime_type)
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        # Protected File & API Routes
        if path == '/api/files':
            session = self.authenticate(required_permission='read')
            if not session:
                return
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
                self.send_error_msg(f"Failed to list files: {str(e)}", status=500)
                return
            self.send_json({"files": files_info})
            return

        if path == '/api/clipboard':
            session = self.authenticate(required_permission='read')
            if not session:
                return
            self.send_json(get_clipboard_data())
            return

        if path.startswith('/shared_files/'):
            session = self.authenticate(required_permission='read')
            if not session:
                return
            filename = urllib.parse.unquote(path[len('/shared_files/'):])
            file_path = os.path.abspath(os.path.join(STORAGE_DIR, filename))
            if not file_path.startswith(STORAGE_DIR) or not os.path.exists(file_path):
                self.send_error_msg("File not found", status=404)
                return
            try:
                mime_type, _ = mimetypes.guess_type(file_path)
                if not mime_type:
                    mime_type = 'application/octet-stream'
                file_size = os.path.getsize(file_path)
                self.send_response(200)
                self.send_header('Content-Type', mime_type)
                self.send_header('Content-Length', str(file_size))
                self.send_header('Content-Disposition', f'inline; filename="{urllib.parse.quote(filename)}"')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                with open(file_path, 'rb') as f:
                    shutil.copyfileobj(f, self.wfile)
            except Exception as e:
                self.send_error_msg(f"Error reading file: {str(e)}", status=500)
            return

        self.send_error_msg("Page not found", status=404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        client_ip = self.get_client_ip()

        # Public API: Guest Request Access
        if path == '/api/access/request':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode('utf-8'))
                device_name = data.get("device_name", "Local Device").strip() or "Local Device"

                pending_requests[client_ip] = {
                    "device_name": device_name,
                    "requested_at": time.time(),
                    "client_ip": client_ip
                }
                self.send_json({
                    "status": "pending",
                    "client_ip": client_ip,
                    "device_name": device_name,
                    "message": "Access request submitted. Waiting for Admin approval."
                })
            except Exception as e:
                self.send_error_msg(f"Request error: {str(e)}", status=400)
            return

        # Public API: Login (Password or Temp Passcode)
        if path == '/api/login':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode('utf-8'))
                input_pass = data.get("password", "").strip()

                if input_pass == config["admin_password"]:
                    token = secrets.token_hex(24)
                    sessions[token] = {
                        "role": "admin",
                        "permissions": ["read", "write", "delete", "admin"],
                        "expires_at": None
                    }
                    self.send_json({
                        "status": "success",
                        "token": token,
                        "role": "admin",
                        "permissions": ["read", "write", "delete", "admin"]
                    })
                    return

                clean_expired_states()
                if input_pass in temp_passwords:
                    pass_info = temp_passwords[input_pass]
                    token = secrets.token_hex(24)
                    sessions[token] = {
                        "role": "guest",
                        "permissions": pass_info["permissions"],
                        "expires_at": pass_info["expires_at"]
                    }
                    self.send_json({
                        "status": "success",
                        "token": token,
                        "role": "guest",
                        "permissions": pass_info["permissions"],
                        "expires_at": pass_info["expires_at"]
                    })
                    return

                self.send_error_msg("Invalid password. Check your password or request access from Admin.", status=401)
            except Exception as e:
                self.send_error_msg(f"Login error: {str(e)}", status=400)
            return

        # Admin API: Approve Pending IP Access Request
        if path == '/api/access/approve':
            session = self.authenticate(required_permission='admin')
            if not session:
                return
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode('utf-8'))
                target_ip = data.get("ip")
                duration_minutes = int(data.get("duration_minutes", 60))
                access_type = data.get("access_type", "read_write")

                if not target_ip:
                    self.send_error_msg("IP address required", status=400)
                    return

                if access_type == "read_only":
                    perms = ["read"]
                elif access_type == "read_write":
                    perms = ["read", "write"]
                else:
                    perms = ["read", "write", "delete"]

                expires_at = time.time() + (duration_minutes * 60)
                token = secrets.token_hex(24)

                device_name = "Local Device"
                if target_ip in pending_requests:
                    device_name = pending_requests[target_ip]["device_name"]
                    del pending_requests[target_ip]

                sessions[token] = {
                    "role": "guest_ip",
                    "permissions": perms,
                    "expires_at": expires_at,
                    "ip": target_ip,
                    "device_name": device_name
                }

                approved_ips[target_ip] = {
                    "device_name": device_name,
                    "permissions": perms,
                    "expires_at": expires_at,
                    "token": token
                }

                self.send_json({
                    "status": "success",
                    "message": f"Approved access for IP {target_ip} ({duration_minutes}m limit)",
                    "ip": target_ip,
                    "expires_at": expires_at
                })
            except Exception as e:
                self.send_error_msg(f"Approval error: {str(e)}", status=400)
            return

        # Admin API: Reject Pending IP Access Request
        if path == '/api/access/reject':
            session = self.authenticate(required_permission='admin')
            if not session:
                return
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode('utf-8'))
                target_ip = data.get("ip")
                if target_ip in pending_requests:
                    del pending_requests[target_ip]
                self.send_json({"status": "success", "message": f"Rejected request from {target_ip}"})
            except Exception as e:
                self.send_error_msg(f"Reject error: {str(e)}", status=400)
            return

        # Logout Endpoint
        if path == '/api/logout':
            token = self.get_auth_token()
            if token in sessions:
                del sessions[token]
            if client_ip in approved_ips:
                del approved_ips[client_ip]
            self.send_json({"status": "success"})
            return

        # Admin API: Generate Temporary Password
        if path == '/api/passwords/generate':
            session = self.authenticate(required_permission='admin')
            if not session:
                return
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode('utf-8'))
                duration_minutes = int(data.get("duration_minutes", 60))
                access_type = data.get("access_type", "read_write")
                label = data.get("label", "Guest Pass").strip()

                if access_type == "read_only":
                    perms = ["read"]
                elif access_type == "read_write":
                    perms = ["read", "write"]
                else:
                    perms = ["read", "write", "delete"]

                code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                expires_at = time.time() + (duration_minutes * 60)

                temp_passwords[code] = {
                    "permissions": perms,
                    "expires_at": expires_at,
                    "label": label,
                    "duration_minutes": duration_minutes,
                    "access_type": access_type
                }

                self.send_json({
                    "status": "success",
                    "code": code,
                    "label": label,
                    "permissions": perms,
                    "expires_at": expires_at,
                    "expires_at_formatted": datetime.fromtimestamp(expires_at).strftime("%H:%M:%S (%b %d)"),
                    "duration_minutes": duration_minutes
                })
            except Exception as e:
                self.send_error_msg(f"Failed to generate key: {str(e)}", status=400)
            return

        # Admin API: Change Permanent Password
        if path == '/api/admin/change-password':
            session = self.authenticate(required_permission='admin')
            if not session:
                return
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode('utf-8'))
                new_pass = data.get("new_password", "").strip()
                if len(new_pass) < 4:
                    self.send_error_msg("Password must be at least 4 characters long", status=400)
                    return
                config["admin_password"] = new_pass
                with open(CONFIG_FILE, 'w') as f:
                    json.dump(config, f, indent=2)
                self.send_json({"status": "success", "message": "Admin password updated successfully!"})
            except Exception as e:
                self.send_error_msg(f"Error: {str(e)}", status=400)
            return

        # API: Update Clipboard Text
        if path == '/api/clipboard':
            session = self.authenticate(required_permission='write')
            if not session:
                return
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode('utf-8'))
                updated_clipboard = set_clipboard_data(data.get('text', ''))
                self.send_json({"status": "success", "clipboard": updated_clipboard})
            except Exception as e:
                self.send_error_msg(f"Invalid JSON: {str(e)}", status=400)
            return

        # API: File Upload
        if path == '/api/upload':
            session = self.authenticate(required_permission='write')
            if not session:
                return
            content_type = self.headers.get('Content-Type', '')
            if 'multipart/form-data' not in content_type:
                self.send_error_msg("Content-Type must be multipart/form-data", status=400)
                return

            boundary = content_type.split("boundary=")[-1].encode('ascii')
            content_length = int(self.headers.get('Content-Length', 0))
            uploaded_files = []
            try:
                body = self.rfile.read(content_length)
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
                self.send_json({
                    "status": "success",
                    "uploaded_files": uploaded_files,
                    "message": f"Successfully uploaded {len(uploaded_files)} file(s)"
                })
            except Exception as e:
                self.send_error_msg(f"Failed to process file upload: {str(e)}", status=500)
            return

        self.send_error_msg("Invalid endpoint", status=404)

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # Admin API: Revoke IP Access
        if path.startswith('/api/access/revoke-ip/'):
            session = self.authenticate(required_permission='admin')
            if not session:
                return
            target_ip = urllib.parse.unquote(path[len('/api/access/revoke-ip/'):])
            if target_ip in approved_ips:
                token = approved_ips[target_ip].get('token')
                if token and token in sessions:
                    del sessions[token]
                del approved_ips[target_ip]
                self.send_json({"status": "success", "message": f"Revoked IP access for {target_ip}"})
            else:
                self.send_error_msg("IP not found in whitelist", status=404)
            return

        # Admin API: Revoke Temporary Password
        if path.startswith('/api/passwords/revoke/'):
            session = self.authenticate(required_permission='admin')
            if not session:
                return
            code = urllib.parse.unquote(path[len('/api/passwords/revoke/'):])
            if code in temp_passwords:
                del temp_passwords[code]
                self.send_json({"status": "success", "message": f"Revoked password {code}"})
            else:
                self.send_error_msg("Password not found", status=404)
            return

        # API: File Deletion
        if path.startswith('/api/files/'):
            session = self.authenticate(required_permission='delete')
            if not session:
                return
            filename = urllib.parse.unquote(path[len('/api/files/'):])
            if filename == '.gitkeep':
                self.send_error_msg("Protected file cannot be deleted", status=403)
                return
            file_path = os.path.abspath(os.path.join(STORAGE_DIR, filename))
            if not file_path.startswith(STORAGE_DIR) or not os.path.exists(file_path):
                self.send_error_msg("File not found or access denied", status=404)
                return
            try:
                os.remove(file_path)
                self.send_json({"status": "success", "message": f"Deleted {filename}"})
            except Exception as e:
                self.send_error_msg(f"Failed to delete file: {str(e)}", status=500)
            return

        self.send_error_msg("Invalid endpoint", status=404)

def run_server():
    server_address = ('0.0.0.0', PORT)
    httpd = ThreadedHTTPServer(server_address, RequestHandler)
    ips = get_local_ips()
    
    print("\n" + "="*60)
    print("🔒 Protected Wi-Fi Share & Timed IP Approval Hub Started!")
    print("="*60)
    print(f"🔑 Admin Password: '{config['admin_password']}'")
    print(f"📁 Storage Folder: {STORAGE_DIR}")
    print("\n🌐 Access URLs:")
    for ip in ips:
        print(f"   👉 http://{ip}:{PORT}")
    print(f"   👉 http://localhost:{PORT}")
    print("="*60 + "\n")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server gracefully...")
        httpd.server_close()

if __name__ == '__main__':
    run_server()
