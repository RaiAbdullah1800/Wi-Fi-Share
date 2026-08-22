import os
import sys
import json
import mimetypes
from datetime import datetime
from http.server import BaseHTTPRequestHandler

from config import PUBLIC_DIR
from core.auth import get_auth_token, authenticate

class BaseRequestHandler(BaseHTTPRequestHandler):

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

    def serve_static_file(self, target_path):
        target_file = target_path.lstrip('/')
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
            return True
        return False
