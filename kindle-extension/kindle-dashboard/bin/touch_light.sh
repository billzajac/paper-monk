#!/bin/sh
# Zero-CPU Touch-to-Light + Triple-Tap 90° Clockwise Rotation Daemon
# for Kindle Paperwhite 4 (goodix-ts / evdev + LuaJIT FFI poll()).
#
# Gestures:
#   • Single tap: Turns frontlight ON (auto-offs after HOLD_SECS), or OFF if already lit.
#   • Triple tap: Rotates display 90° clockwise (0° -> 90° -> 180° -> 270° -> 0°) via host API!

CONF_FILE="/tmp/zen_touch_light.conf"
PID_FILE="/tmp/zen_touch_light.pid"

# Auto-detect capacitive touchscreen input device (goodix-ts on Paperwhite 4)
TOUCH_DEV=""
for sysf in /sys/class/input/event*; do
    [ -e "$sysf/device/name" ] || continue
    name="$(cat "$sysf/device/name" 2>/dev/null || true)"
    case "$name" in
        *goodix*|*touch*|*cyttsp*|*elan*|*fts*|*-ts)
            TOUCH_DEV="/dev/input/$(basename "$sysf")"
            break
            ;;
    esac
done
[ -z "$TOUCH_DEV" ] && TOUCH_DEV="/dev/input/event2"

# Terminate any previous instance cleanly
if [ -f "$PID_FILE" ]; then
    OLD_PID="$(cat "$PID_FILE" 2>/dev/null || true)"
    if [ -n "$OLD_PID" ] && [ "$OLD_PID" != "$$" ] && kill -0 "$OLD_PID" 2>/dev/null; then
        kill "$OLD_PID" 2>/dev/null || true
        usleep 150000 2>/dev/null || sleep 1
    fi
fi
echo "$$" > "$PID_FILE"

LUAJIT_BIN="/mnt/us/koreader/luajit"
if [ -x "$LUAJIT_BIN" ]; then
    exec "$LUAJIT_BIN" - "$TOUCH_DEV" "$CONF_FILE" "$PID_FILE" <<'LUA'
local ffi = require("ffi")
local bit = require("bit")

ffi.cdef[[
struct pollfd {
    int fd;
    short events;
    short revents;
};
struct input_event {
    long tv_sec;
    long tv_usec;
    uint16_t type;
    uint16_t code;
    int32_t value;
};
struct timespec {
    long tv_sec;
    long tv_nsec;
};
int open(const char *pathname, int flags);
int close(int fd);
int read(int fd, void *buf, size_t count);
int poll(struct pollfd *fds, unsigned long nfds, int timeout);
int clock_gettime(int clk_id, struct timespec *tp);
]]

local touch_dev = arg[1] or "/dev/input/event2"
local conf_file = arg[2] or "/tmp/zen_touch_light.conf"
local O_RDONLY = 0
local POLLIN = 1
local CLOCK_MONOTONIC = 1
local EV_ABS = 3
local ABS_MT_TRACKING_ID = 57
local EV_KEY = 1
local BTN_TOUCH = 330

local ts = ffi.new("struct timespec")
local function mono_now()
    ffi.C.clock_gettime(CLOCK_MONOTONIC, ts)
    return tonumber(ts.tv_sec) + tonumber(ts.tv_nsec) * 1e-9
end

local function read_conf()
    local cfg = {
        MODE = "touch",
        BRIGHT = 14,
        HOLD_SECS = 20,
        HOST_USB = "http://192.168.15.201:8788",
        HOST_LAN = "http://192.168.50.222:8788",
    }
    local f = io.open(conf_file, "r")
    if f then
        for line in f:lines() do
            local k, v = line:match("^%s*([A-Z_]+)%s*=%s*(.-)%s*$")
            if k and v then
                v = v:gsub('^"(.*)"$', "%1"):gsub("^'(.*)'$", "%1")
                if tonumber(v) then
                    cfg[k] = tonumber(v)
                else
                    cfg[k] = v
                end
            end
        end
        f:close()
    end
    return cfg
end

local is_lit = false
local function set_light(val)
    val = math.max(0, math.min(24, math.floor(tonumber(val) or 0)))
    os.execute(string.format("lipc-set-prop -i com.lab126.powerd flIntensity %d >/dev/null 2>&1", val))
    if val == 0 then
        local bf = io.open("/sys/class/backlight/bl/brightness", "w")
        if bf then
            bf:write("0\n")
            bf:close()
        end
        is_lit = false
    else
        is_lit = true
    end
end

local function trigger_rotate(cfg)
    os.execute(
        string.format(
            "(/mnt/us/libkh/bin/fbink -qpmh -y -2 ' Rotating 90 deg... ' >/dev/null 2>&1 || true; " ..
            "wget -T 4 -q -O /dev/null '%s/api/rotate' 2>/dev/null || " ..
            "wget -T 4 -q -O /dev/null '%s/api/rotate' 2>/dev/null || true) &",
            cfg.HOST_USB,
            cfg.HOST_LAN
        )
    )
end

-- Apply initial frontlight mode on startup
local init_cfg = read_conf()
if init_cfg.MODE == "always" then
    set_light(init_cfg.BRIGHT)
else
    set_light(0)
end

local fd = ffi.C.open(touch_dev, O_RDONLY)
if fd < 0 then
    os.exit(1)
end

local pfd = ffi.new("struct pollfd[1]")
pfd[0].fd = fd
pfd[0].events = POLLIN

local ev_buf = ffi.new("struct input_event[32]")
local ev_size = ffi.sizeof("struct input_event")
local buf_bytes = ffi.sizeof(ev_buf)

local TAP_WINDOW = 0.55
local DEBOUNCE = 0.06
local tap_count = 0
local last_tap_at = -10.0
local gesture_deadline = nil
local first_tap_was_lit = false
local light_until = nil
local cfg = init_cfg

while true do
    local now = mono_now()

    -- Finalize pending single/double tap once multi-tap window closes
    if gesture_deadline and now >= gesture_deadline then
        if tap_count == 1 and first_tap_was_lit and cfg.MODE == "touch" then
            set_light(0)
            light_until = nil
        end
        tap_count = 0
        gesture_deadline = nil
    end

    -- Turn off touch frontlight once hold timer expires
    if is_lit and light_until and now >= light_until then
        cfg = read_conf()
        if cfg.MODE == "touch" then
            set_light(0)
        end
        light_until = nil
    end

    -- Compute exact sleep duration (-1 = infinite 0.0% CPU kernel sleep!)
    local timeout_ms = -1
    if gesture_deadline then
        timeout_ms = math.max(10, math.floor((gesture_deadline - now) * 1000))
    elseif is_lit and light_until then
        timeout_ms = math.max(50, math.floor((light_until - now) * 1000))
    end

    local rc = ffi.C.poll(pfd, 1, timeout_ms)
    if rc > 0 and bit.band(pfd[0].revents, POLLIN) ~= 0 then
        local nbytes = ffi.C.read(fd, ev_buf, buf_bytes)
        if nbytes >= ev_size then
            local count = math.floor(nbytes / ev_size)
            for i = 0, count - 1 do
                local ev = ev_buf[i]
                local is_finger_down = (ev.type == EV_ABS and ev.code == ABS_MT_TRACKING_ID and ev.value >= 0)
                    or (ev.type == EV_KEY and ev.code == BTN_TOUCH and ev.value == 1)

                if is_finger_down then
                    local t = mono_now()
                    if (t - last_tap_at) >= DEBOUNCE then
                        last_tap_at = t
                        cfg = read_conf()

                        if tap_count == 0 then
                            tap_count = 1
                            first_tap_was_lit = is_lit
                            gesture_deadline = t + TAP_WINDOW
                            if cfg.MODE == "touch" and not is_lit then
                                set_light(cfg.BRIGHT)
                                light_until = t + cfg.HOLD_SECS
                            elseif cfg.MODE == "touch" and is_lit then
                                light_until = t + cfg.HOLD_SECS
                            end
                        else
                            tap_count = tap_count + 1
                            gesture_deadline = t + TAP_WINDOW
                        end

                        if tap_count >= 3 then
                            tap_count = 0
                            gesture_deadline = nil
                            if cfg.MODE == "touch" and is_lit then
                                light_until = t + cfg.HOLD_SECS
                            end
                            trigger_rotate(cfg)
                        end
                    end
                end
            end
        end
    end
end
LUA
fi

# Fallback pure-BusyBox touch-light loop if LuaJIT is unavailable
trap 'lipc-set-prop -i com.lab126.powerd flIntensity 0 >/dev/null 2>&1; rm -f "$PID_FILE"; exit 0' INT TERM
lipc-set-prop -i com.lab126.powerd flIntensity 0 >/dev/null 2>&1 || true
while true; do
    dd if="$TOUCH_DEV" of=/dev/null bs=16 count=1 2>/dev/null || { sleep 2; continue; }
    BRIGHT=14
    HOLD_SECS=20
    [ -f "$CONF_FILE" ] && . "$CONF_FILE"
    lipc-set-prop -i com.lab126.powerd flIntensity "$BRIGHT" >/dev/null 2>&1 || true
    timeout 1 dd if="$TOUCH_DEV" of=/dev/null bs=512 2>/dev/null || true
    WAIT_S=$((HOLD_SECS > 2 ? HOLD_SECS - 1 : 1))
    timeout "$WAIT_S" dd if="$TOUCH_DEV" of=/dev/null bs=16 count=1 2>/dev/null || true
    lipc-set-prop -i com.lab126.powerd flIntensity 0 >/dev/null 2>&1 || true
done
