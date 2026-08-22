import urllib.parse
from http.server import HTTPServer
from socketserver import ThreadingMixIn

from config import PORT, STORAGE_DIR, config
from core.storage import get_local_ips
from routes.base_handler import BaseRequestHandler
from routes.auth_routes import handle_auth_routes
from routes.access_routes import handle_access_routes
from routes.file_routes import handle_file_routes
from routes.clipboard_routes import handle_clipboard_routes

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

class RequestHandler(BaseRequestHandler):

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if handle_auth_routes(self, path, 'GET'):
            return
        if handle_access_routes(self, path, 'GET'):
            return
        if handle_clipboard_routes(self, path, 'GET'):
            return
        if handle_file_routes(self, path, 'GET'):
            return
        if self.serve_static_file(path):
            return

        self.send_error_msg("Page not found", status=404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if handle_auth_routes(self, path, 'POST'):
            return
        if handle_access_routes(self, path, 'POST'):
            return
        if handle_clipboard_routes(self, path, 'POST'):
            return
        if handle_file_routes(self, path, 'POST'):
            return

        self.send_error_msg("Invalid endpoint", status=404)

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if handle_access_routes(self, path, 'DELETE'):
            return
        if handle_file_routes(self, path, 'DELETE'):
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
