import json
from config import config, save_config
from core.auth import (
    sessions, temp_passwords, approved_ips, clean_expired_states, generate_session_token
)

def handle_auth_routes(handler, path, method):
    if method == 'GET':
        if path == '/api/auth/status':
            session = handler.authenticate()
            if session:
                handler.send_json({
                    "authenticated": True,
                    "role": session['role'],
                    "permissions": session['permissions'],
                    "expires_at": session.get('expires_at'),
                    "token": handler.get_auth_token() or session.get('token')
                })
            return True

    elif method == 'POST':
        if path == '/api/login':
            content_length = int(handler.headers.get('Content-Length', 0))
            body = handler.rfile.read(content_length)
            try:
                data = json.loads(body.decode('utf-8'))
                input_pass = data.get("password", "").strip()

                if input_pass == config["admin_password"]:
                    token = generate_session_token()
                    sessions[token] = {
                        "role": "admin",
                        "permissions": ["read", "write", "delete", "admin"],
                        "expires_at": None
                    }
                    handler.send_json({
                        "status": "success",
                        "token": token,
                        "role": "admin",
                        "permissions": ["read", "write", "delete", "admin"]
                    })
                    return True

                clean_expired_states()
                if input_pass in temp_passwords:
                    pass_info = temp_passwords[input_pass]
                    token = generate_session_token()
                    sessions[token] = {
                        "role": "guest",
                        "permissions": pass_info["permissions"],
                        "expires_at": pass_info["expires_at"]
                    }
                    handler.send_json({
                        "status": "success",
                        "token": token,
                        "role": "guest",
                        "permissions": pass_info["permissions"],
                        "expires_at": pass_info["expires_at"]
                    })
                    return True

                handler.send_error_msg("Invalid password. Check your password or request access from Admin.", status=401)
            except Exception as e:
                handler.send_error_msg(f"Login error: {str(e)}", status=400)
            return True

        if path == '/api/logout':
            token = handler.get_auth_token()
            client_ip = handler.get_client_ip()
            if token in sessions:
                del sessions[token]
            if client_ip in approved_ips:
                del approved_ips[client_ip]
            handler.send_json({"status": "success"})
            return True

        if path == '/api/admin/change-password':
            session = handler.authenticate(required_permission='admin')
            if not session:
                return True
            content_length = int(handler.headers.get('Content-Length', 0))
            body = handler.rfile.read(content_length)
            try:
                data = json.loads(body.decode('utf-8'))
                new_pass = data.get("new_password", "").strip()
                if len(new_pass) < 4:
                    handler.send_error_msg("Password must be at least 4 characters long", status=400)
                    return True
                config["admin_password"] = new_pass
                save_config()
                handler.send_json({"status": "success", "message": "Admin password updated successfully!"})
            except Exception as e:
                handler.send_error_msg(f"Error: {str(e)}", status=400)
            return True

    return False
