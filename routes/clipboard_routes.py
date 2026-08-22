import json
from core.clipboard import get_clipboard_data, set_clipboard_data

def handle_clipboard_routes(handler, path, method):
    if method == 'GET':
        if path == '/api/clipboard':
            session = handler.authenticate(required_permission='read')
            if not session:
                return True
            handler.send_json(get_clipboard_data())
            return True

    elif method == 'POST':
        if path == '/api/clipboard':
            session = handler.authenticate(required_permission='write')
            if not session:
                return True
            content_length = int(handler.headers.get('Content-Length', 0))
            body = handler.rfile.read(content_length)
            try:
                data = json.loads(body.decode('utf-8'))
                updated_clipboard = set_clipboard_data(data.get('text', ''))
                handler.send_json({"status": "success", "clipboard": updated_clipboard})
            except Exception as e:
                handler.send_error_msg(f"Invalid JSON: {str(e)}", status=400)
            return True

    return False
