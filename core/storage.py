import os
import socket
import mimetypes

def get_local_ips():
    ips = []
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(('8.8.8.8', 80))
        primary_ip = s.getsockname()[0]
        s.close()
        if primary_ip and not primary_ip.startswith('127.'):
            ips.append(primary_ip)
    except Exception:
        pass

    try:
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            if not ip.startswith('127.') and ip not in ips:
                ips.append(ip)
    except Exception:
        pass

    if not ips:
        ips = ['127.0.0.1']
    return ips

def format_size(size_in_bytes):
    if size_in_bytes < 1024:
        return f"{size_in_bytes} B"
    elif size_in_bytes < 1024 * 1024:
        return f"{size_in_bytes / 1024:.1f} KB"
    elif size_in_bytes < 1024 * 1024 * 1024:
        return f"{size_in_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_in_bytes / (1024 * 1024 * 1024):.2f} GB"

def get_file_category(filename):
    ext = os.path.splitext(filename)[1].lower()
    if not ext and filename.startswith('.'):
        ext = filename.lower()

    if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp', '.ico']:
        return 'image'
    elif ext in ['.mp4', '.mkv', '.webm', '.avi', '.mov', '.wmv']:
        return 'video'
    elif ext in ['.mp3', '.wav', '.ogg', '.flac', '.m4a']:
        return 'audio'
    elif ext in ['.pdf', '.doc', '.docx', '.txt', '.md', '.xls', '.xlsx', '.ppt', '.pptx']:
        return 'document'
    elif ext in ['.zip', '.tar', '.gz', '.7z', '.rar', '.iso']:
        return 'archive'
    elif ext in ['.py', '.js', '.ts', '.jsx', '.tsx', '.html', '.css', '.json', '.c', '.cpp', '.h', '.sh', '.java', '.rs', '.go', '.sql', '.yml', '.yaml', '.env', '.gitignore', '.gitkeep', '.dockerignore', '.ini', '.conf', '.config', '.log']:
        return 'code'
    else:
        return 'file'

def get_preview_info(filename):
    ext = os.path.splitext(filename)[1].lower()
    if not ext and filename.startswith('.'):
        ext = filename.lower()

    image_exts = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp', '.ico']
    text_exts = [
        '.txt', '.md', '.json', '.csv', '.py', '.js', '.ts', '.jsx', '.tsx',
        '.html', '.htm', '.css', '.c', '.cpp', '.h', '.hpp', '.sh', '.bash', '.zsh',
        '.java', '.rs', '.go', '.php', '.xml', '.log', '.yml', '.yaml', '.ini',
        '.env', '.sql', '.gitignore', '.gitkeep', '.dockerignore', '.babelrc',
        '.eslintrc', '.editorconfig', '.conf', '.config', '.properties'
    ]
    audio_exts = ['.mp3', '.wav', '.ogg', '.flac', '.m4a', '.aac']
    video_exts = ['.mp4', '.webm', '.ogv', '.mov', '.m4v']

    if ext in image_exts:
        return {"previewable": True, "preview_type": "image"}
    elif ext in text_exts:
        return {"previewable": True, "preview_type": "text"}
    elif ext in audio_exts:
        return {"previewable": True, "preview_type": "audio"}
    elif ext in video_exts:
        return {"previewable": True, "preview_type": "video"}
    elif ext == '.pdf':
        return {"previewable": True, "preview_type": "pdf"}
    else:
        mime_type, _ = mimetypes.guess_type(filename)
        if mime_type and (mime_type.startswith('text/') or mime_type in ['application/json', 'application/javascript', 'application/xml', 'application/x-sh']):
            return {"previewable": True, "preview_type": "text"}
        return {"previewable": False, "preview_type": "none"}
