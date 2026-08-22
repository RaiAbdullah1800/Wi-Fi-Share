import time
import json
import secrets
import random
import string
import urllib.parse
from datetime import datetime

from core.auth import (
    pending_requests, approved_ips, temp_passwords,
    clean_expired_states, generate_session_token
)

def handle_access_routes(handler, path, method):
    client_ip = handler.get_client_ip()

    if method == 'GET':
        # Public IP Request Status Check (Guest Polling)
        if path == '/api/access/request-status':
            clean_expired_states()
            if client_ip in approved_ips:
                info = approved_ips[client_ip]
                handler.send_json({
                    "status": "approved",
                    "client_ip": client_ip,
                    "token": info["token"],
                    "permissions": info["permissions"],
                    "expires_at": info["expires_at"],
                    "expires_in_seconds": max(0, int(info["expires_at"] - time.time()))
                })
            elif client_ip in pending_requests:
                info = pending_requests[client_ip]
                handler.send_json({
                    "status": "pending",
                    "client_ip": client_ip,
                    "device_name": info["device_name"],
                    "requested_at_formatted": datetime.fromtimestamp(info["requested_at"]).strftime("%H:%M:%S")
                })
            else:
                handler.send_json({"status": "none", "client_ip": client_ip})
            return True

        # Admin: List Pending IP Requests
        if path == '/api/access/pending':
            session = handler.authenticate(required_permission='admin')
            if not session:
                return True
            requests_list = []
            for ip, req in pending_requests.items():
                requests_list.append({
                    "ip": ip,
                    "device_name": req["device_name"],
                    "requested_at": req["requested_at"],
                    "requested_at_formatted": datetime.fromtimestamp(req["requested_at"]).strftime("%H:%M:%S")
                })
            handler.send_json({"pending_requests": requests_list})
            return True

        # Admin: List Approved Whitelisted IPs
        if path == '/api/access/approved-ips':
            session = handler.authenticate(required_permission='admin')
            if not session:
                return True
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
            handler.send_json({"approved_ips": ip_list})
            return True

        # Admin: List Temp Passwords
        if path == '/api/passwords/list':
            session = handler.authenticate(required_permission='admin')
            if not session:
                return True
            clean_expired_states()
            pass_list = []
            now = time.time()
            for code, data in temp_passwords.items():
                remaining = max(0, int(data['expires_at'] - now))
                pass_list.append({
                    "code": code,
                    "label": data["label"],
                    "permissions": data["permissions"],
                    "access_type": data["access_type"],
                    "expires_in_seconds": remaining,
                    "expires_at_formatted": datetime.fromtimestamp(data['expires_at']).strftime("%H:%M:%S (%b %d)")
                })
            handler.send_json({"temp_passwords": pass_list})
            return True

    elif method == 'POST':
        # Guest IP Access Request
        if path == '/api/access/request':
            content_length = int(handler.headers.get('Content-Length', 0))
            body = handler.rfile.read(content_length)
            try:
                data = json.loads(body.decode('utf-8'))
                device_name = data.get("device_name", "Local Device").strip() or "Local Device"

                pending_requests[client_ip] = {
                    "device_name": device_name,
                    "requested_at": time.time(),
                    "client_ip": client_ip
                }
                handler.send_json({
                    "status": "pending",
                    "client_ip": client_ip,
                    "device_name": device_name,
                    "message": "Access request submitted. Waiting for Admin approval."
                })
            except Exception as e:
                handler.send_error_msg(f"Request error: {str(e)}", status=400)
            return True

        # Admin: Approve Guest IP Request
        if path == '/api/access/approve':
            session = handler.authenticate(required_permission='admin')
            if not session:
                return True
            content_length = int(handler.headers.get('Content-Length', 0))
            body = handler.rfile.read(content_length)
            try:
                data = json.loads(body.decode('utf-8'))
                target_ip = data.get("ip")
                duration_minutes = int(data.get("duration_minutes", 60))
                access_type = data.get("access_type", "read_write")

                if not target_ip:
                    handler.send_error_msg("IP address required", status=400)
                    return True

                if access_type == "read_only":
                    perms = ["read"]
                elif access_type == "read_write":
                    perms = ["read", "write"]
                else:
                    perms = ["read", "write", "delete"]

                expires_at = time.time() + (duration_minutes * 60)
                token = generate_session_token()

                device_name = "Local Device"
                if target_ip in pending_requests:
                    device_name = pending_requests[target_ip]["device_name"]
                    del pending_requests[target_ip]

                from core.auth import sessions
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

                handler.send_json({
                    "status": "success",
                    "message": f"Approved access for IP {target_ip} ({duration_minutes}m limit)",
                    "ip": target_ip,
                    "expires_at": expires_at
                })
            except Exception as e:
                handler.send_error_msg(f"Approval error: {str(e)}", status=400)
            return True

        # Admin: Reject Pending IP Request
        if path == '/api/access/reject':
            session = handler.authenticate(required_permission='admin')
            if not session:
                return True
            content_length = int(handler.headers.get('Content-Length', 0))
            body = handler.rfile.read(content_length)
            try:
                data = json.loads(body.decode('utf-8'))
                target_ip = data.get("ip")
                if target_ip in pending_requests:
                    del pending_requests[target_ip]
                handler.send_json({"status": "success", "message": f"Rejected request from {target_ip}"})
            except Exception as e:
                handler.send_error_msg(f"Reject error: {str(e)}", status=400)
            return True

        # Admin: Generate Temp Password
        if path == '/api/passwords/generate':
            session = handler.authenticate(required_permission='admin')
            if not session:
                return True
            content_length = int(handler.headers.get('Content-Length', 0))
            body = handler.rfile.read(content_length)
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

                handler.send_json({
                    "status": "success",
                    "code": code,
                    "label": label,
                    "permissions": perms,
                    "expires_at": expires_at,
                    "expires_at_formatted": datetime.fromtimestamp(expires_at).strftime("%H:%M:%S (%b %d)"),
                    "duration_minutes": duration_minutes
                })
            except Exception as e:
                handler.send_error_msg(f"Failed to generate key: {str(e)}", status=400)
            return True

    elif method == 'DELETE':
        # Admin: Revoke Whitelisted IP
        if path.startswith('/api/access/revoke-ip/'):
            session = handler.authenticate(required_permission='admin')
            if not session:
                return True
            target_ip = urllib.parse.unquote(path[len('/api/access/revoke-ip/'):])
            if target_ip in approved_ips:
                token = approved_ips[target_ip].get('token')
                from core.auth import sessions
                if token and token in sessions:
                    del sessions[token]
                del approved_ips[target_ip]
                handler.send_json({"status": "success", "message": f"Revoked IP access for {target_ip}"})
            else:
                handler.send_error_msg("IP not found in whitelist", status=404)
            return True

        # Admin: Revoke Temp Password
        if path.startswith('/api/passwords/revoke/'):
            session = handler.authenticate(required_permission='admin')
            if not session:
                return True
            code = urllib.parse.unquote(path[len('/api/passwords/revoke/'):])
            if code in temp_passwords:
                del temp_passwords[code]
                handler.send_json({"status": "success", "message": f"Revoked password {code}"})
            else:
                handler.send_error_msg("Password not found", status=404)
            return True

    return False
