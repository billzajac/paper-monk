#!/bin/sh
# Kindle Paperwhite 4 KUAL helper for Pasadena Zen Dashboard

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
SERVER_URL="http://192.168.50.222:8788/dashboard.png"
PID_FILE="/tmp/zen_dashboard_pull.pid"
LIGHT_PID_FILE="/tmp/zen_touch_light.pid"
IMG_FILE="/tmp/dashboard.png"

start_touch_light() {
    if [ -x "$SCRIPT_DIR/touch_light.sh" ]; then
        start-stop-daemon -S -b -p "$LIGHT_PID_FILE" -x /bin/sh -- "$SCRIPT_DIR/touch_light.sh" >/dev/null 2>&1 || true
    fi
}

stop_touch_light() {
    if [ -f "$LIGHT_PID_FILE" ]; then
        LPID="$(cat "$LIGHT_PID_FILE" 2>/dev/null)"
        [ -n "$LPID" ] && kill "$LPID" >/dev/null 2>&1 || true
        rm -f "$LIGHT_PID_FILE"
    fi
    pkill -f touch_light.sh >/dev/null 2>&1 || true
}

draw_png() {
    FULL="$1"
    FBINK_BIN="$(command -v fbink || ls /mnt/us/usbnet/bin/fbink /mnt/us/koreader/fbink /mnt/us/libkh/bin/fbink 2>/dev/null | head -n 1)"
    if [ "$FULL" = "1" ]; then
        { [ -n "$FBINK_BIN" ] && "$FBINK_BIN" -q -c -f -g "file=$IMG_FILE" 2>/dev/null; } || /usr/sbin/eips -f -g "$IMG_FILE" >/dev/null 2>&1
    else
        { [ -n "$FBINK_BIN" ] && "$FBINK_BIN" -q -g "file=$IMG_FILE" 2>/dev/null; } || /usr/sbin/eips -g "$IMG_FILE" >/dev/null 2>&1
    fi
}

stop_pull_loop() {
    if [ -f "$PID_FILE" ]; then
        OLD_PID="$(cat "$PID_FILE" 2>/dev/null)"
        if [ -n "$OLD_PID" ]; then
            kill "$OLD_PID" >/dev/null 2>&1 || true
        fi
        rm -f "$PID_FILE"
    fi
}

case "$1" in
    usb_start)
        stop_pull_loop
        lipc-set-prop -i com.lab126.powerd preventScreenSaver 1 >/dev/null 2>&1 || true
        start_touch_light
        if [ -x /mnt/us/usbnetlite/bin/usbnetwork.sh ]; then
            /mnt/us/usbnetlite/bin/usbnetwork.sh start >/dev/null 2>&1 || true
        elif [ -x /mnt/us/usbnet/bin/usbnetwork.sh ]; then
            /mnt/us/usbnet/bin/usbnetwork.sh start >/dev/null 2>&1 || true
        fi
        /usr/sbin/eips -c >/dev/null 2>&1
        /usr/sbin/eips 10 18 "Desk Mode Active - Waiting for USB Push (192.168.15.244)..." >/dev/null 2>&1
        ;;
    wifi_pull_start)
        stop_pull_loop
        lipc-set-prop -i com.lab126.powerd preventScreenSaver 1 >/dev/null 2>&1 || true
        start_touch_light
        (
            COUNT=0
            while true; do
                if wget -q -O "$IMG_FILE" "$SERVER_URL" 2>/dev/null || curl -sf -o "$IMG_FILE" "$SERVER_URL" 2>/dev/null; then
                    if [ $((COUNT % 20)) -eq 0 ]; then
                        draw_png 1
                    else
                        draw_png 0
                    fi
                    COUNT=$((COUNT + 1))
                fi
                sleep 60
            done
        ) >/dev/null 2>&1 &
        echo "$!" > "$PID_FILE"
        ;;
    stop)
        stop_pull_loop
        stop_touch_light
        lipc-set-prop -i com.lab126.powerd flIntensity 14 >/dev/null 2>&1 || true
        lipc-set-prop -i com.lab126.powerd preventScreenSaver 0 >/dev/null 2>&1 || true
        start lab126_gui >/dev/null 2>&1 || true
        /usr/sbin/eips -c >/dev/null 2>&1
        ;;
esac
exit 0
