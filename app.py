import urllib.parse
from http.server import HTTPServer
from socketserver import ThreadingMixIn

from config import PORT, DROPS_DIR
from core.storage import get_local_ips
from core.drops_engine import start_drops_cleanup_thread
from routes.base_handler import BaseRequestHandler
from routes.drop_routes import handle_drop_routes

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

class RequestHandler(BaseRequestHandler):

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if handle_drop_routes(self, path, 'GET'):
            return
        if self.serve_static_file(path):
            return

        self.send_error_msg("Page not found", status=404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if handle_drop_routes(self, path, 'POST'):
            return

        self.send_error_msg("Invalid endpoint", status=404)

def run_server():
    start_drops_cleanup_thread()
    server_address = ('0.0.0.0', PORT)
    httpd = ThreadedHTTPServer(server_address, RequestHandler)
    ips = get_local_ips()

    print("\n" + "="*60)
    print("⚡ Wi-Fi Quick Drop & Locked Text Paste Server Started")
    print("="*60)
    print(f"📁 Temporary Drops Storage: {DROPS_DIR}")
    print("🔒 Zero Login Required • Protected by Custom PIN/Password • Auto-Expiring")
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
