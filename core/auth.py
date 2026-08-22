import time
import secrets
import urllib.parse

# Auth & Sessions State
temp_passwords = {}
sessions = {}
# IP Access State
pending_requests = {} # { "ip": { "device_name": "...", "requested_at": epoch } }
approved_ips = {}     # { "ip": { "device_name": "...", "permissions": [...], "expires_at": epoch, "token": "..." } }

def clean_expired_states():
    now = time.time()
    # Clean temp passwords
    expired_pass = [code for code, data in temp_passwords.items() if data['expires_at'] < now]
    for code in expired_pass:
        del temp_passwords[code]

    # Clean IP approvals
    expired_ip_list = [ip for ip, data in approved_ips.items() if data['expires_at'] < now]
    for ip in expired_ip_list:
        token = approved_ips[ip].get('token')
        if token and token in sessions:
            del sessions[token]
        del approved_ips[ip]

def get_auth_token(handler):
    auth_header = handler.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        return auth_header[7:].strip()
    parsed = urllib.parse.urlparse(handler.path)
    params = urllib.parse.parse_qs(parsed.query)
    if 'token' in params:
        return params['token'][0]
    return None

def authenticate(handler, required_permission=None):
    clean_expired_states()
    token = get_auth_token(handler)
    session = None

    # 1. Check Token Session
    if token and token in sessions:
        sess = sessions[token]
        if not sess['expires_at'] or sess['expires_at'] > time.time():
            session = sess
        else:
            del sessions[token]

    # 2. Check Client IP Approval (Auto IP Whitelist Auth)
    if not session:
        client_ip = handler.get_client_ip()
        if client_ip in approved_ips:
            ip_info = approved_ips[client_ip]
            if ip_info['expires_at'] > time.time():
                session = {
                    "role": "guest_ip",
                    "permissions": ip_info["permissions"],
                    "expires_at": ip_info["expires_at"],
                    "device_name": ip_info["device_name"],
                    "ip": client_ip
                }

    if not session:
        handler.send_error_msg("Unauthorized. Authentication required.", status=401)
        return None

    if required_permission and required_permission not in session['permissions']:
        handler.send_error_msg(f"Forbidden. Missing '{required_permission}' permission.", status=403)
        return None

    return session

def generate_session_token():
    return secrets.token_hex(24)
