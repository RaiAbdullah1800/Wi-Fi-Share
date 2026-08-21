# 📁 Wi-Fi Share

A sleek, lightweight, zero-dependency local Wi-Fi file & text sharing application built with Python 3. Easily transfer files and share clipboard text between computers, smartphones, and tablets on the same Wi-Fi network.

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen.svg)
![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows-lightgrey.svg)

---

## ✨ Features

- ⚡ **Zero External Dependencies**: Built entirely with standard Python 3 libraries (`http.server`, `socket`, `threading`). Runs out of the box on Ubuntu/Linux.
- 📱 **QR Code Mobile Access**: Automatically detects your Wi-Fi IP address and generates a scannable QR code on screen for quick phone connection.
- 🔒 **Password Protection**: Permanent Admin access + timed temporary guest passcodes with custom validity (15m, 1h, 6h, 24h).
- 🛡️ **Granular Permission Controls**: Assign `Read-Only` (View & Download), `Read & Write` (Upload & Text Sync), or `Full Access` (Delete enabled).
- 🔄 **Live Text & Clipboard Sync**: Instant real-time text snippet sharing across devices.
- 🎨 **Glassmorphism UI**: Modern dark theme with drag-and-drop file upload, search filter, and tab favicon logo.
- ⚙️ **Automatic System Startup**: Includes an autostart setup script (`setup-autostart.sh`) and background `systemd` user service setup.

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
- **Default Admin Password**: `admin123` *(changeable anytime in the Admin panel)*

---

## ⚙️ Background & Auto-Start Setup (Linux)

To run Wi-Fi Share automatically in the background whenever your system starts:

```bash
chmod +x setup-autostart.sh
./setup-autostart.sh
```

### Systemd Service Commands:
```bash
# Check Status
systemctl --user status wifi-share.service

# Restart Service
systemctl --user restart wifi-share.service
```

---

## 📁 Project Structure

```
Wi-Fi-Share/
├── app.py                # Multi-threaded Python 3 HTTP Server & Auth Engine
├── shared_storage/       # Subfolder storing all shared files (.gitignore protected)
├── setup-autostart.sh    # Linux autostart setup script
├── public/
│   ├── index.html        # Glassmorphic UI layout & modals
│   ├── styles.css        # Responsive dark glass design system
│   ├── app.js            # Frontend API client & real-time sync
│   └── favicon.svg       # Browser tab logo
└── README.md
```

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
