# SocketRobot
Used to control a Raspberry Pi robot through the network using sockets.
Originally written by @awyehle in 2021 or something along those lines.

Finally uploaded this as a repo 3/1/25.

## Web control (new)

This repo now includes a web-based controller served by the Pi. It exposes a simple GUI that works on phones and laptops. Control is via WASD or on-screen buttons using WebSockets.

### Quick start (development laptop)

- Install dependencies:
  - Python 3.10+
  - `pip install -r requirements.txt`
- Run the web server locally (mock motor driver):
  - Windows PowerShell: `$env:ROBOT_USE_MOCK = '1'`
  - macOS/Linux: `export ROBOT_USE_MOCK=1`
  - Start: `uvicorn webapp.main:app --host 0.0.0.0 --port 8000`
- Open `http://localhost:8000` and press WASD or use the buttons. The terminal logs show mock motor commands.

### Run on Raspberry Pi

1. Ensure wiring matches pins used by `gpiozero` in `webapp/main.py`:
   - Left motor: BCM 19 forward, 26 backward
   - Right motor: BCM 16 forward, 20 backward
2. Install dependencies:
   - `python3 -m pip install -r requirements.txt`
3. Start the web server:
   - `uvicorn webapp.main:app --host 0.0.0.0 --port 8000`
4. From your phone/laptop on the same network, browse to `http://<pi-ip>:8000`.

### Wi‑Fi hotspot (AP mode)

To make the Pi host its own Wi‑Fi network (so clients can connect directly), configure `hostapd` and `dnsmasq`.

High-level steps (Debian/Raspberry Pi OS):

1. Install packages: `sudo apt-get update && sudo apt-get install -y hostapd dnsmasq`
2. Disable wpa_supplicant on the AP interface, enable `hostapd`.
3. Configure static IP for `wlan0` (e.g., 10.10.0.1/24).
4. Configure `hostapd` SSID and WPA2 passphrase.
5. Configure `dnsmasq` for DHCP on `wlan0`.
6. Enable IP forwarding and optional NAT if you want internet sharing.

Example configs are common—search “raspberry pi access point hostapd dnsmasq” or use Raspberry Pi Imager’s “Set up Wi‑Fi as access point” where available. We can add ready-to-use config files in a follow-up.

### Legacy socket control

The original socket client/server remain in `Client/` and `Server/`. You can keep using them during the transition.