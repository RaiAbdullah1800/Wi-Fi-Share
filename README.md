# ⚡ Wi-Fi Drop

A sleek, ultra-lightweight, zero-dependency local Wi-Fi file & locked text sharing application built with Python 3. Easily transfer files and share private text snippets between computers, smartphones, and tablets on the same Wi-Fi network with **zero login required**, **custom PIN/password locks**, and **automatic self-destruct timers**.

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen.svg)
![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows-lightgrey.svg)

---

## ✨ Features

- ⚡ **Zero External Dependencies**: Built entirely with standard Python 3 standard libraries (`http.server`, `socket`, `threading`). Runs out of the box on Linux, macOS, and Windows.
- 🚀 **Zero Login Required**: No admin credentials, user accounts, or IP approval queues. Just open the URL and start sharing instantly.
- 📦 **Ephemeral File Drops**: Upload multiple files into password-protected drops with drag-and-drop support.
- 📝 **Locked Text Pastes**: Share passwords, OTP codes, Wi-Fi credentials, terminal commands, or notes securely with a PIN/password and 1-click clipboard copy.
- 🔥 **Burn-After-Reading Option**: Optionally destroy sensitive text notes immediately after their first unlock.
- 💬 **Password-Protected Wi-Fi Chat**: Slide-out right-side chat drawer to create and join password-locked ephemeral rooms with custom time limits (up to 24 hours), nickname support, and real-time delta synchronization.
- 📱 **QR Code Mobile Access**: Automatically detects local network IP and renders a scannable QR code for instant phone/tablet pairing.
- 🎨 **Modern Glassmorphic UI**: High-contrast dark design system with live countdown timers, tab switching, and responsive layout.
- ⚙️ **Automatic System Startup**: Includes an autostart setup script (`setup-autostart.sh`) for Linux desktop/systemd environments.

---

## 🚀 Quick Start

### 1. Clone & Run
```bash
git clone git@github.com:RaiAbdullah1800/Wi-Fi-Share.git
cd Wi-Fi-Share
python3 app.py
```

### 2. Connect
Open any web browser on your computer or mobile device connected to the same Wi-Fi network:
```
http://<YOUR_LOCAL_IP>:5000
```
*(The exact IP and a phone QR code are displayed in the terminal and in the web interface)*

---

## ⚙️ Background & Auto-Start Setup (Linux)

To run Wi-Fi Drop automatically in the background whenever your system starts:

```bash
chmod +x setup-autostart.sh
./setup-autostart.sh
```

---

## 📁 Project Structure

```
Wi-Fi-Share/
├── app.py                  # Multi-threaded Python 3 HTTP Server & Dispatcher
├── config.py               # Server port, directory paths, and expiry limits
├── setup-autostart.sh      # Linux autostart setup script
├── core/
│   ├── chat_engine.py      # Thread-safe in-memory room store & token auth
│   ├── drops_engine.py     # In-memory & disk storage engine with daemon cleanup
│   └── storage.py          # IP discovery, file category & size formatting
├── routes/
│   ├── base_handler.py     # Base HTTP handler with static file serving & CORS
│   ├── chat_routes.py      # REST endpoints for rooms, joining, messaging & leave
│   └── drop_routes.py      # Unified REST API for file and text drops
├── public/
│   ├── index.html          # Responsive Glassmorphic Single Page App & Chat Drawer
│   ├── styles.css          # Dark glass design system with animations
│   ├── app.js              # Client controller, live timers, QR modal & chat sync
│   └── favicon.svg         # Tab logo icon
└── README.md
```

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
