#!/usr/bin/env python3
"""Kindle Paperwhite 4 Zen Desk Dashboard — Renderer, Web Studio, & Auto-Bootstrapping USBNetwork Pusher."""

from __future__ import annotations

import argparse
import json
import logging
import os
import shlex
import socket
import stat
import subprocess
import tempfile
import threading
import time
from dataclasses import asdict
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from quotes import AUTHORS, BUDDY_BY_KEY, ZEN_BUDDIES, Quote, ZenBuddy, select_quote_and_buddy
from renderer import render_dashboard_files, render_svg
from weather import WeatherData, fetch_weather

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
OUTPUT_DIR = BASE_DIR / "output"
SVG_PATH = OUTPUT_DIR / "dashboard.svg"
PNG_PATH = OUTPUT_DIR / "dashboard.png"
PREVIEW_PNG_PATH = OUTPUT_DIR / "dashboard_preview.png"
WEATHER_CACHE_PATH = OUTPUT_DIR / "weather_cache.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("kindle-dashboard")

ROTATION_ORDER = ("portrait", "landscape", "portrait_inverted", "landscape_ccw")

SSH_COMPAT_OPTS = [
    "-o",
    "ConnectTimeout=4",
    "-o",
    "StrictHostKeyChecking=accept-new",
    "-o",
    "WarnWeakCrypto=no",
    "-o",
    "PubkeyAcceptedAlgorithms=+ssh-rsa",
    "-o",
    "HostKeyAlgorithms=+ssh-rsa",
]


class DashboardState:
    def __init__(self, config_path: Path = CONFIG_PATH) -> None:
        self.config_path = config_path
        self.lock = threading.Lock()
        self.config = self._load_config()
        self.quote_offset: int = 0
        self.push_count: int = 0
        self.last_render_epoch: float = 0.0
        self.last_push_epoch: float = 0.0
        self.last_push_ok: bool = False
        self.last_push_msg: str = "Waiting for Kindle USBNetwork (192.168.15.244)"
        self.latest_weather: WeatherData | None = None
        self.latest_quote: Quote | None = None
        self.latest_buddy: ZenBuddy | None = None

    def _load_config(self) -> dict[str, Any]:
        return json.loads(self.config_path.read_text(encoding="utf-8"))

    def save_config(self) -> None:
        self.config_path.write_text(json.dumps(self.config, indent=2) + "\n", encoding="utf-8")

    def rotate_clockwise(self) -> str:
        with self.lock:
            disp = self.config["display"]
            cur = str(disp.get("orientation", "portrait"))
            idx = ROTATION_ORDER.index(cur) if cur in ROTATION_ORDER else 0
            nxt = ROTATION_ORDER[(idx + 1) % len(ROTATION_ORDER)]
            disp["orientation"] = nxt
            self.save_config()
        self.render_now()
        self.push_to_kindle(force_full_refresh=True)
        log.info("Rotated orientation 90° CW -> %s", nxt)
        return nxt

    def render_now(self) -> tuple[WeatherData, Quote, ZenBuddy]:
        with self.lock:
            cfg = self.config
            loc = dict(cfg["location"])
            disp = dict(cfg["display"])
            q_cfg = dict(cfg["quotes"])
            w_cfg = dict(cfg["weather"])
            offset = self.quote_offset

        orientation = str(disp.get("orientation", "portrait"))
        use_24h = bool(disp.get("time_format_24h", False))

        weather = fetch_weather(
            latitude=float(loc["latitude"]),
            longitude=float(loc["longitude"]),
            timezone=str(loc["timezone"]),
            location_name=str(loc["name"]),
            cache_path=WEATHER_CACHE_PATH,
            refresh_minutes=int(w_cfg.get("refresh_minutes", 15)),
            use_24h=use_24h,
        )
        quote, buddy = select_quote_and_buddy(
            rotate_minutes=int(q_cfg.get("rotate_minutes", 60)),
            offset=offset,
            author_filter=str(q_cfg.get("author_filter", "all")),
            buddy_mode=str(q_cfg.get("buddy_mode", "auto")),
        )
        now_dt = datetime.now(ZoneInfo(str(loc["timezone"])))
        svg = render_svg(
            weather=weather,
            quote=quote,
            buddy=buddy,
            now=now_dt,
            tz_name=str(loc["timezone"]),
            short_location=str(loc.get("short_name", "PASADENA · CALIFORNIA")),
            theme=str(disp.get("theme", "light")),
            use_24h=use_24h,
            orientation=orientation,
        )
        render_dashboard_files(
            svg_content=svg,
            svg_path=SVG_PATH,
            png_path=PNG_PATH,
            preview_png_path=PREVIEW_PNG_PATH,
            width=int(disp.get("width", 1072)),
            height=int(disp.get("height", 1448)),
            orientation=orientation,
        )

        with self.lock:
            self.latest_weather = weather
            self.latest_quote = quote
            self.latest_buddy = buddy
            self.last_render_epoch = time.time()

        log.info(
            "Rendered %s [%s] (%d°C / %d°F, %s — %s · %s)",
            PNG_PATH.name,
            orientation,
            weather.temp_c,
            weather.temp_f,
            weather.condition,
            quote.author,
            buddy.label,
        )
        return weather, quote, buddy

    def _bootstrap_ssh_key(self, host: str, port: int, user: str, ssh_key_path: Path, default_pw: str) -> bool:
        """Automatically enroll SSH public key on first USBNetLite/USBNetwork connection using OpenSSH ASKPASS."""
        pub_path = Path(f"{ssh_key_path}.pub")
        if not pub_path.exists():
            return False
        pub_key = pub_path.read_text(encoding="utf-8").strip()
        if not pub_key:
            return False

        enroll_cmd = (
            "pub=$(cat); "
            "mkdir -p /mnt/us/usbnetlite/etc/dropbear /mnt/us/usbnet/etc /tmp/root/.ssh 2>/dev/null || true; "
            "for f in /mnt/us/usbnetlite/etc/dropbear/authorized_keys /mnt/us/usbnet/etc/authorized_keys /tmp/root/.ssh/authorized_keys; do "
            'd=$(dirname "$f"); [ -d "$d" ] || continue; '
            '[ -s "$f" ] || rm -f "$f"; '
            'grep -qxF "$pub" "$f" 2>/dev/null || printf "%s\\n" "$pub" >> "$f"; '
            'chmod 600 "$f" 2>/dev/null || true; '
            "done"
        )

        for candidate_pw in (default_pw, ""):
            with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as tf:
                tf.write(f"#!/bin/sh\necho {shlex.quote(candidate_pw)}\n")
                askpass_script = Path(tf.name)
            try:
                askpass_script.chmod(stat.S_IRWXU)
                env = dict(os.environ)
                env["SSH_ASKPASS"] = str(askpass_script)
                env["SSH_ASKPASS_REQUIRE"] = "force"
                env["DISPLAY"] = ":0"

                res = subprocess.run(
                    [
                        "ssh",
                        *SSH_COMPAT_OPTS,
                        "-o",
                        "PreferredAuthentications=password,keyboard-interactive",
                        "-p",
                        str(port),
                        f"{user}@{host}",
                        enroll_cmd,
                    ],
                    env=env,
                    input=(pub_key + "\n").encode("utf-8"),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=8,
                )
                if res.returncode == 0:
                    log.info("Auto-enrolled SSH public key onto Kindle (%s)!", host)
                    return True
            except Exception:
                pass
            finally:
                askpass_script.unlink(missing_ok=True)
        return False

    def push_to_kindle(self, force_full_refresh: bool = False) -> tuple[bool, str]:
        with self.lock:
            k_cfg = dict(self.config.get("kindle", {}))
            disp = dict(self.config.get("display", {}))
            push_num = self.push_count

        if not k_cfg.get("enabled", True):
            return False, "Kindle SSH push disabled in config.json"

        host = str(k_cfg.get("host", "192.168.15.244"))
        port = int(k_cfg.get("port", 22))
        user = str(k_cfg.get("user", "root"))
        ssh_key = str(k_cfg.get("ssh_key", "")).strip()
        default_pw = str(k_cfg.get("default_password", "kindle"))
        remote_img = str(k_cfg.get("remote_image_path", "/tmp/dashboard.png"))
        full_every = max(1, int(disp.get("full_refresh_every_n_pushes", 20)))

        try:
            with socket.create_connection((host, port), timeout=1.5):
                pass
        except OSError:
            msg = f"Standby · Waiting for Kindle at {host}:{port} (;un)"
            with self.lock:
                self.last_push_ok = False
                self.last_push_msg = msg
            return False, msg

        featherweight = bool(k_cfg.get("featherweight_mode", True))
        fl_mode = str(k_cfg.get("frontlight_mode", "touch"))
        fl_level = max(1, min(24, int(k_cfg.get("frontlight_level", 14))))
        fl_secs = max(5, int(k_cfg.get("frontlight_seconds", 20)))
        do_full = force_full_refresh or (push_num % full_every == 0)
        q_remote = shlex.quote(remote_img)

        fw_snippet = (
            'if status lab126_gui 2>/dev/null | grep -q "start/running"; then stop lab126_gui >/dev/null 2>&1 || true; sleep 1; fi; '
            if featherweight
            else ""
        )
        srv_port = int(self.config.get("server", {}).get("port", 8788))
        fl_conf = (
            f'printf "MODE={fl_mode}\\nBRIGHT={fl_level}\\nHOLD_SECS={fl_secs}\\n'
            f'HOST_USB=http://192.168.15.201:{srv_port}\\nHOST_LAN=http://192.168.50.222:{srv_port}\\n" > /tmp/zen_touch_light.conf; '
            'LPID=$(cat /tmp/zen_touch_light.pid 2>/dev/null || true); '
            'if [ -z "$LPID" ] || ! kill -0 "$LPID" 2>/dev/null; then '
            "rm -f /tmp/zen_touch_light.pid; "
            "start-stop-daemon -S -b -p /tmp/zen_touch_light.pid -x /bin/sh -- /mnt/us/extensions/kindle-dashboard/bin/touch_light.sh >/dev/null 2>&1 || true; "
            "fi; "
        )
        if fl_mode == "off":
            fl_snippet = fl_conf + "lipc-set-prop -i com.lab126.powerd flIntensity 0 >/dev/null 2>&1 || true; "
        elif fl_mode == "always":
            fl_snippet = fl_conf + f"lipc-set-prop -i com.lab126.powerd flIntensity {fl_level} >/dev/null 2>&1 || true; "
        else:
            fl_snippet = fl_conf

        draw_cmd = (
            f'{{ [ -n "$FBINK_BIN" ] && "$FBINK_BIN" -q -c -f -g file={q_remote} 2>/dev/null; }} || /usr/sbin/eips -f -g {q_remote} >/dev/null 2>&1'
            if do_full
            else f'{{ [ -n "$FBINK_BIN" ] && "$FBINK_BIN" -q -g file={q_remote} 2>/dev/null; }} || /usr/sbin/eips -g {q_remote} >/dev/null 2>&1'
        )

        remote_script = (
            f"cat > {q_remote} && "
            "lipc-set-prop -i com.lab126.powerd preventScreenSaver 1 >/dev/null 2>&1 || true; "
            + fw_snippet
            + fl_snippet
            + "FBINK_BIN=$(command -v fbink || ls /mnt/us/usbnet/bin/fbink /mnt/us/koreader/fbink /mnt/us/libkh/bin/fbink 2>/dev/null | head -n 1); "
            + draw_cmd
        )

        key_path = Path(ssh_key).expanduser() if ssh_key else None
        ssh_cmd = ["ssh", "-o", "BatchMode=yes", *SSH_COMPAT_OPTS, "-p", str(port)]
        if key_path and key_path.exists():
            ssh_cmd.extend(["-i", str(key_path)])
        ssh_cmd.extend([f"{user}@{host}", remote_script])

        png_bytes = PNG_PATH.read_bytes()
        try:
            proc = subprocess.run(
                ssh_cmd,
                input=png_bytes,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=12,
            )
            # If key isn't enrolled yet on a brand-new USBNetLite install, enroll automatically and retry once!
            if proc.returncode != 0 and key_path and key_path.exists():
                if self._bootstrap_ssh_key(host, port, user, key_path, default_pw):
                    proc = subprocess.run(
                        ssh_cmd,
                        input=png_bytes,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=12,
                    )

            if proc.returncode == 0:
                mode_lbl = "full flash" if do_full else "gentle refresh"
                msg = f"Live on Kindle ({host} · {mode_lbl})"
                with self.lock:
                    self.push_count += 1
                    self.last_push_epoch = time.time()
                    self.last_push_ok = True
                    self.last_push_msg = msg
                log.info(msg)
                return True, msg

            err = proc.stderr.decode("utf-8", errors="replace").strip()
            msg = f"SSH auth/cmd error ({host}): {err[:120]}"
            with self.lock:
                self.last_push_ok = False
                self.last_push_msg = msg
            log.warning(msg)
            return False, msg
        except Exception as exc:
            msg = f"Push error ({host}): {exc}"
            with self.lock:
                self.last_push_ok = False
                self.last_push_msg = msg
            log.warning(msg)
            return False, msg


STUDIO_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Pasadena Zen Desk Studio · Kindle Paperwhite 4</title>
  <style>
    :root {
      --bg-top: #f7f4ed;
      --bg-bot: #e3dfd5;
      --card: rgba(255, 255, 255, 0.85);
      --border: rgba(20, 20, 20, 0.1);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      font-family: "Noto Sans", system-ui, -apple-system, sans-serif;
      background: radial-gradient(circle at 50% 10%, var(--bg-top) 0%, var(--bg-bot) 100%);
      color: #191919;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 24px 18px 48px;
    }
    .studio-bar {
      max-width: 1080px;
      width: 100%;
      background: var(--card);
      backdrop-filter: blur(12px);
      border: 1px solid var(--border);
      border-radius: 20px;
      padding: 16px 22px;
      margin-bottom: 24px;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.05);
      display: flex;
      flex-direction: column;
      gap: 14px;
    }
    .row-top {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }
    .brand h1 {
      margin: 0;
      font-size: 18px;
      font-weight: 700;
      letter-spacing: 0.02em;
    }
    .substatus {
      font-size: 13px;
      color: #555;
      margin-top: 4px;
    }
    .pill-conn {
      font-size: 12px;
      font-weight: 700;
      padding: 6px 12px;
      border-radius: 999px;
      background: #f0eee8;
      border: 1px solid rgba(0,0,0,0.12);
    }
    .pill-conn.live {
      background: #e3f5e8;
      color: #125b2a;
      border-color: #9ad4ac;
    }
    .controls-row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }
    button, select, a.btn {
      appearance: none;
      font-family: inherit;
      font-size: 13px;
      font-weight: 600;
      padding: 8px 14px;
      border-radius: 999px;
      border: 1px solid #262626;
      background: #fff;
      color: #141414;
      cursor: pointer;
      text-decoration: none;
      transition: all 0.14s ease;
    }
    select { padding-right: 28px; }
    button:hover, a.btn:hover {
      background: #161616;
      color: #fff;
    }
    button.primary {
      background: #161616;
      color: #fff;
    }
    button.primary:hover {
      background: #333;
    }
    .kindle-bezel {
      background: linear-gradient(155deg, #27272a 0%, #141416 100%);
      padding: 34px 32px 62px;
      border-radius: 36px;
      border: 2px solid #38383d;
      box-shadow:
        0 30px 65px rgba(0, 0, 0, 0.24),
        0 4px 14px rgba(0, 0, 0, 0.14),
        inset 0 1px 1px rgba(255, 255, 255, 0.14);
      position: relative;
      max-width: 560px;
      width: 100%;
      transition: max-width 0.25s ease, padding 0.25s ease;
    }
    .kindle-bezel.landscape {
      max-width: 820px;
      padding: 30px 52px 44px 34px;
    }
    .screen-well {
      background: #fff;
      border-radius: 6px;
      overflow: hidden;
      box-shadow: inset 0 0 0 2px rgba(0, 0, 0, 0.35);
    }
    .screen-well img {
      display: block;
      width: 100%;
      height: auto;
    }
    .kindle-wordmark {
      position: absolute;
      bottom: 20px;
      left: 0;
      right: 0;
      text-align: center;
      color: #7c7c82;
      font-size: 15px;
      letter-spacing: 0.2em;
      font-weight: 500;
    }
    .kindle-bezel.landscape .kindle-wordmark {
      bottom: 13px;
    }
  </style>
</head>
<body>
  <div class="studio-bar">
    <div class="row-top">
      <div class="brand">
        <h1>Pasadena Zen Desk Studio · Kindle Paperwhite 4</h1>
        <div class="substatus" id="weatherSummary">Syncing Pasadena weather &amp; quote…</div>
      </div>
      <div class="pill-conn" id="connPill">Checking Kindle…</div>
    </div>

    <div class="controls-row">
      <button class="primary" onclick="postJSON('/api/next-quote', {})">Next Quote ✨</button>

      <select id="authorSelect" onchange="updateSettings({author_filter: this.value})" title="Filter by Teacher">
        <option value="all">Teacher: All Five</option>
        <option value="Alan Watts">Alan Watts</option>
        <option value="Thích Nhất Hạnh">Thích Nhất Hạnh</option>
        <option value="Ram Dass">Ram Dass</option>
        <option value="Pema Chödrön">Pema Chödrön</option>
        <option value="Jon Kabat-Zinn">Jon Kabat-Zinn</option>
      </select>

      <select id="buddySelect" onchange="updateSettings({buddy_mode: this.value})" title="Choose Zen Companion">
        <option value="auto">Buddy: Auto Rotate</option>
      </select>

      <select id="orientSelect" onchange="updateSettings({orientation: this.value})" title="Screen Orientation">
        <option value="portrait">Portrait · 0° (USB Bottom)</option>
        <option value="landscape">Landscape · 90° (USB Right)</option>
        <option value="portrait_inverted">Portrait · 180° (USB Top)</option>
        <option value="landscape_ccw">Landscape · 270° (USB Left)</option>
      </select>
      <button onclick="postJSON('/api/rotate', {})" title="Rotate 90° clockwise (or triple-tap Kindle screen!)">Rotate 90° ↻</button>

      <select id="themeSelect" onchange="updateSettings({theme: this.value})" title="E-Ink Theme">
        <option value="light">Theme: Classic Paper</option>
        <option value="dark">Theme: Dark Ink</option>
        <option value="auto">Theme: Auto Day/Night</option>
      </select>

      <select id="lightSelect" onchange="updateSettings({frontlight_mode: this.value})" title="Frontlight Behavior">
        <option value="touch">Light: Touch Only (20s)</option>
        <option value="off">Light: Always Off</option>
        <option value="always">Light: Always On</option>
      </select>

      <button onclick="toggleClock()" id="clockBtn">12h / 24h</button>
      <button onclick="toggleFeatherweight()" id="fwBtn" title="Stops Amazon's heavy lab126_gui while in Desk Mode">Featherweight: ON</button>
      <button onclick="postJSON('/api/push', {})">Push to Kindle</button>
      <a class="btn" href="/dashboard.png" target="_blank">Kindle PNG</a>
    </div>
  </div>

  <div class="kindle-bezel" id="bezel">
    <div class="screen-well">
      <img id="dashImg" src="/dashboard_preview.png" alt="Kindle E-Ink Preview">
    </div>
    <div class="kindle-wordmark">kindle</div>
  </div>

  <script>
    let current24h = false;
    let currentFeatherweight = true;
    let buddiesPopulated = false;

    async function refreshStatus() {
      try {
        const res = await fetch('/api/status');
        const d = await res.json();
        const w = d.weather || {};
        const q = d.quote || {};
        const b = d.buddy || {};
        const cfg = d.settings || {};

        if (!buddiesPopulated && d.available_buddies) {
          const sel = document.getElementById('buddySelect');
          for (const item of d.available_buddies) {
            const opt = document.createElement('option');
            opt.value = item.key;
            opt.textContent = `${item.emoji} ${item.label}`;
            sel.appendChild(opt);
          }
          buddiesPopulated = true;
        }

        document.getElementById('authorSelect').value = cfg.author_filter || 'all';
        document.getElementById('buddySelect').value = cfg.buddy_mode || 'auto';
        document.getElementById('orientSelect').value = cfg.orientation || 'portrait';
        document.getElementById('themeSelect').value = cfg.theme || 'light';
        document.getElementById('lightSelect').value = cfg.frontlight_mode || 'touch';
        current24h = !!cfg.time_format_24h;
        document.getElementById('clockBtn').textContent = current24h ? 'Clock: 24h' : 'Clock: 12h';
        currentFeatherweight = cfg.featherweight_mode !== false;
        document.getElementById('fwBtn').textContent = currentFeatherweight ? 'Featherweight: ON' : 'Kindle UI: ON';

        const bezel = document.getElementById('bezel');
        bezel.classList.toggle('landscape', (cfg.orientation || '').startsWith('landscape'));

        document.getElementById('weatherSummary').textContent =
          `Pasadena: ${w.temp_c ?? '--'}°C / ${w.temp_f ?? '--'}°F · ${w.condition || ''} · AQI ${w.us_aqi ?? '--'} (${w.aqi_status || ''}) · “${(q.text || '').slice(0, 52)}…” — ${q.author || ''}`;

        const pill = document.getElementById('connPill');
        pill.textContent = d.last_push_msg || 'Standby';
        pill.classList.toggle('live', !!d.last_push_ok);

        document.getElementById('dashImg').src = '/dashboard_preview.png?t=' + Date.now();
      } catch (e) {}
    }

    async function postJSON(url, body) {
      await fetch(url, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(body || {})
      });
      await refreshStatus();
    }

    async function updateSettings(patch) {
      await postJSON('/api/settings', patch);
    }

    async function toggleClock() {
      await updateSettings({time_format_24h: !current24h});
    }

    async function toggleFeatherweight() {
      await updateSettings({featherweight_mode: !currentFeatherweight});
    }

    refreshStatus();
    setInterval(refreshStatus, 15000);
  </script>
</body>
</html>
"""

KINDLE_BROWSER_HTML = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="60">
  <title>Kindle Dashboard</title>
  <style>
    html, body { margin: 0; padding: 0; background: #fff; overflow: hidden; text-align: center; }
    img { width: 100%; height: auto; display: block; border: 0; }
  </style>
</head>
<body>
  <img src="/dashboard_preview.png" alt="Dashboard">
</body>
</html>
"""


def make_handler(state: DashboardState) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: Any) -> None:
            return

        def _send_bytes(self, content: bytes, content_type: str, status: int = 200) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.end_headers()
            self.wfile.write(content)

        def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
            raw = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            self._send_bytes(raw, "application/json; charset=utf-8", status=status)

        def _read_json_body(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0") or "0")
            if length <= 0:
                return {}
            try:
                return json.loads(self.rfile.read(length).decode("utf-8"))
            except Exception:
                return {}

        def do_GET(self) -> None:
            path = urlparse(self.path).path

            if path == "/":
                self._send_bytes(STUDIO_HTML.encode("utf-8"), "text/html; charset=utf-8")
            elif path == "/kindle":
                self._send_bytes(KINDLE_BROWSER_HTML.encode("utf-8"), "text/html; charset=utf-8")
            elif path == "/dashboard.png":
                if not PNG_PATH.exists():
                    state.render_now()
                self._send_bytes(PNG_PATH.read_bytes(), "image/png")
            elif path == "/dashboard_preview.png":
                target = PREVIEW_PNG_PATH if PREVIEW_PNG_PATH.exists() else PNG_PATH
                if not target.exists():
                    state.render_now()
                    target = PREVIEW_PNG_PATH if PREVIEW_PNG_PATH.exists() else PNG_PATH
                self._send_bytes(target.read_bytes(), "image/png")
            elif path == "/dashboard.svg":
                if not SVG_PATH.exists():
                    state.render_now()
                self._send_bytes(SVG_PATH.read_bytes(), "image/svg+xml; charset=utf-8")
            elif path == "/api/status":
                with state.lock:
                    disp = state.config["display"]
                    q_cfg = state.config["quotes"]
                    k_cfg = state.config.get("kindle", {})
                    payload = {
                        "ok": True,
                        "last_render_epoch": state.last_render_epoch,
                        "last_push_epoch": state.last_push_epoch,
                        "last_push_ok": state.last_push_ok,
                        "last_push_msg": state.last_push_msg,
                        "settings": {
                            "theme": disp.get("theme", "light"),
                            "orientation": disp.get("orientation", "portrait"),
                            "time_format_24h": bool(disp.get("time_format_24h", False)),
                            "featherweight_mode": bool(k_cfg.get("featherweight_mode", True)),
                            "frontlight_mode": str(k_cfg.get("frontlight_mode", "touch")),
                            "author_filter": q_cfg.get("author_filter", "all"),
                            "buddy_mode": q_cfg.get("buddy_mode", "auto"),
                        },
                        "available_authors": list(AUTHORS),
                        "available_buddies": [asdict(b) for b in ZEN_BUDDIES],
                        "weather": asdict(state.latest_weather) if state.latest_weather else None,
                        "quote": asdict(state.latest_quote) if state.latest_quote else None,
                        "buddy": asdict(state.latest_buddy) if state.latest_buddy else None,
                    }
                self._send_json(payload)
            elif path == "/api/rotate":
                nxt = state.rotate_clockwise()
                self._send_json({"ok": True, "orientation": nxt})
            else:
                self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:
            path = urlparse(self.path).path
            body = self._read_json_body()

            if path == "/api/next-quote":
                with state.lock:
                    state.quote_offset += 1
                state.render_now()
                state.push_to_kindle(force_full_refresh=False)
                self._send_json({"ok": True, "quote_offset": state.quote_offset})
            elif path == "/api/rotate":
                nxt = state.rotate_clockwise()
                self._send_json({"ok": True, "orientation": nxt})
            elif path == "/api/settings":
                full_flash = False
                restore_ui = False
                with state.lock:
                    disp = state.config["display"]
                    q_cfg = state.config["quotes"]
                    k_cfg = state.config.setdefault("kindle", {})
                    if "theme" in body and body["theme"] in ("light", "dark", "auto"):
                        disp["theme"] = body["theme"]
                        full_flash = True
                    if "orientation" in body and body["orientation"] in ROTATION_ORDER:
                        disp["orientation"] = body["orientation"]
                        full_flash = True
                    if "time_format_24h" in body:
                        disp["time_format_24h"] = bool(body["time_format_24h"])
                    if "featherweight_mode" in body:
                        fw_val = bool(body["featherweight_mode"])
                        k_cfg["featherweight_mode"] = fw_val
                        full_flash = True
                        if not fw_val:
                            restore_ui = True
                    if "frontlight_mode" in body and body["frontlight_mode"] in ("touch", "off", "always"):
                        k_cfg["frontlight_mode"] = str(body["frontlight_mode"])
                    if "author_filter" in body:
                        val = str(body["author_filter"])
                        if val == "all" or val in AUTHORS:
                            q_cfg["author_filter"] = val
                    if "buddy_mode" in body:
                        bval = str(body["buddy_mode"])
                        if bval == "auto" or bval in BUDDY_BY_KEY:
                            q_cfg["buddy_mode"] = bval
                    state.save_config()
                if restore_ui:
                    host = str(k_cfg.get("host", "192.168.15.244"))
                    port = int(k_cfg.get("port", 22))
                    user = str(k_cfg.get("user", "root"))
                    fl_lvl = max(1, min(24, int(k_cfg.get("frontlight_level", 14))))
                    key_path = Path(str(k_cfg.get("ssh_key", "")).strip()).expanduser()
                    cmd = ["ssh", "-o", "BatchMode=yes", *SSH_COMPAT_OPTS, "-p", str(port)]
                    if key_path.exists():
                        cmd.extend(["-i", str(key_path)])
                    cmd.extend(
                        [
                            f"{user}@{host}",
                            f'LPID=$(cat /tmp/zen_touch_light.pid 2>/dev/null || true); [ -n "$LPID" ] && kill "$LPID" >/dev/null 2>&1 || true; rm -f /tmp/zen_touch_light.pid; lipc-set-prop -i com.lab126.powerd flIntensity {fl_lvl} >/dev/null 2>&1 || true; start lab126_gui >/dev/null 2>&1 || true',
                        ]
                    )
                    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=8)
                state.render_now()
                if not restore_ui:
                    state.push_to_kindle(force_full_refresh=full_flash)
                self._send_json({"ok": True})
            elif path == "/api/toggle-theme":
                order = ["light", "dark", "auto"]
                with state.lock:
                    cur = state.config["display"].get("theme", "light")
                    nxt = order[(order.index(cur) + 1) % len(order)] if cur in order else "light"
                    state.config["display"]["theme"] = nxt
                    state.save_config()
                state.render_now()
                state.push_to_kindle(force_full_refresh=True)
                self._send_json({"ok": True, "theme": nxt})
            elif path == "/api/push":
                state.render_now()
                ok, msg = state.push_to_kindle(force_full_refresh=True)
                self._send_json({"ok": ok, "message": msg})
            else:
                self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

    return Handler


def scheduler_loop(state: DashboardState, stop_event: threading.Event) -> None:
    """Re-render precisely at each minute boundary and push to Kindle when reachable."""
    while not stop_event.is_set():
        now = time.time()
        sleep_secs = 60.0 - (now % 60.0) + 0.15
        if stop_event.wait(timeout=sleep_secs):
            break
        try:
            state.render_now()
            state.push_to_kindle(force_full_refresh=False)
        except Exception as exc:
            log.exception("Minute update failed: %s", exc)


class ReusableHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True


def main() -> None:
    parser = argparse.ArgumentParser(description="Kindle Paperwhite 4 Pasadena Zen Desk Dashboard")
    parser.add_argument("--once", action="store_true", help="Render SVG + PNG once and exit")
    parser.add_argument("--push", action="store_true", help="Render once, push over SSH to Kindle, and exit")
    parser.add_argument("--full", action="store_true", help="Force a full E-Ink flash refresh on --push")
    args = parser.parse_args()

    state = DashboardState()
    state.render_now()

    if args.push:
        ok, msg = state.push_to_kindle(force_full_refresh=args.full)
        print(msg)
        raise SystemExit(0 if ok else 1)

    if args.once:
        print(f"Rendered {PNG_PATH}")
        return

    state.push_to_kindle(force_full_refresh=True)

    stop_event = threading.Event()
    worker = threading.Thread(target=scheduler_loop, args=(state, stop_event), daemon=True)
    worker.start()

    srv_cfg = state.config.get("server", {})
    bind_host = str(srv_cfg.get("host", "0.0.0.0"))
    bind_port = int(srv_cfg.get("port", 8788))

    httpd = ReusableHTTPServer((bind_host, bind_port), make_handler(state))
    log.info("Live Desk Studio:      http://localhost:%d", bind_port)
    log.info("Kindle Browser URL:    http://192.168.50.222:%d/kindle", bind_port)
    log.info("Raw Kindle PNG URL:    http://192.168.50.222:%d/dashboard.png", bind_port)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        log.info("Shutting down Kindle Dashboard...")
    finally:
        stop_event.set()
        httpd.server_close()


if __name__ == "__main__":
    main()
