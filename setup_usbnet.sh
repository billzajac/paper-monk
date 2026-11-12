#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KEY_PATH="$HOME/.ssh/kindle_usbnet"
STAGE_DIR="$SCRIPT_DIR/kindle-packages/kindle-root-stage"

echo "=== Kindle Paperwhite 4 · All-in-One Setup & USBNetwork Helper ==="
echo

# 1. Check Arch/EndeavourOS kernel module sync
RUNNING_KERNEL="$(uname -r)"
if [ ! -d "/lib/modules/${RUNNING_KERNEL}" ]; then
    echo "[!] Heads-up: Running kernel (${RUNNING_KERNEL}) does not match /lib/modules ($(ls /lib/modules | tr '\n' ' '))."
    echo "    Reboot this PC once so Linux can load USB Storage & USB Ethernet modules, then run ./setup_usbnet.sh!"
    echo
fi

# 2. Ensure dedicated SSH key exists & is wired into config.json
mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh"
if [ ! -f "$KEY_PATH" ]; then
    echo "[+] Generating dedicated SSH key for Kindle at $KEY_PATH ..."
    ssh-keygen -t ed25519 -N "" -C "kindle-dashboard" -f "$KEY_PATH" >/dev/null
fi

python3 - "$SCRIPT_DIR/config.json" "$KEY_PATH" <<'PY'
import json, sys
from pathlib import Path
cfg_path = Path(sys.argv[1])
cfg = json.loads(cfg_path.read_text())
cfg["kindle"]["ssh_key"] = "~/.ssh/kindle_usbnet"
cfg_path.write_text(json.dumps(cfg, indent=2) + "\n")
PY
echo "[✓] SSH key ready: $KEY_PATH"

# 3. Check if Kindle USB storage is mounted (auto-mounts under /run/media/$USER/Kindle, or offer udisksctl mount)
KINDLE_MNT=""
for candidate in "/run/media/$USER/Kindle" "/media/$USER/Kindle" "/mnt/kindle"; do
    if [ -d "$candidate/documents" ] || [ -d "$candidate/system" ]; then
        KINDLE_MNT="$candidate"
        break
    fi
done

if [ -z "$KINDLE_MNT" ]; then
    # Check if an unmounted FAT32 partition labeled "Kindle" is attached
    KINDLE_DEV="$(lsblk -rno PATH,LABEL | awk '$2=="Kindle"{print $1; exit}')"
    if [ -n "${KINDLE_DEV:-}" ]; then
        if command -v udisksctl >/dev/null 2>&1 && udisksctl mount --no-user-interaction -b "$KINDLE_DEV" >/dev/null 2>&1; then
            for candidate in "/run/media/$USER/Kindle" "/media/$USER/Kindle"; do
                if [ -d "$candidate/documents" ] || [ -d "$candidate/system" ]; then
                    KINDLE_MNT="$candidate"
                    break
                fi
            done
        else
            echo "[+] Mounting Kindle USB drive ($KINDLE_DEV) at /mnt/kindle..."
            sudo mkdir -p /mnt/kindle
            sudo mount -o "uid=$(id -u),gid=$(id -g),umask=0022" "$KINDLE_DEV" /mnt/kindle || true
            if [ -d "/mnt/kindle/documents" ] || [ -d "/mnt/kindle/system" ]; then
                KINDLE_MNT="/mnt/kindle"
            fi
        fi
    fi
fi

if [ -n "$KINDLE_MNT" ]; then
    echo "[+] Found mounted Kindle storage at: $KINDLE_MNT"
    if [ -f "$KINDLE_MNT/system/version.txt" ]; then
        echo "    Firmware info: $(head -n 1 "$KINDLE_MNT/system/version.txt")"
    fi

    # Copy pre-downloaded MRPI + KUAL Booklet (only if needed) + USBNetLite + Pasadena Dashboard KUAL menu!
    mkdir -p "$KINDLE_MNT/extensions" "$KINDLE_MNT/mrpackages"
    if [ -d "$STAGE_DIR" ]; then
        if [ ! -d "$KINDLE_MNT/extensions/MRInstaller" ] && [ -d "$STAGE_DIR/extensions/MRInstaller" ]; then
            cp -r "$STAGE_DIR/extensions/MRInstaller" "$KINDLE_MNT/extensions/"
            echo "[✓] Installed MRInstaller -> $KINDLE_MNT/extensions/MRInstaller/"
        else
            echo "[✓] MRInstaller already present on Kindle"
        fi

        if [ ! -f "$KINDLE_MNT/documents/KUAL.sh" ] && [ ! -f "$KINDLE_MNT/extensions/KUAL.cfg" ]; then
            cp -f "$STAGE_DIR/mrpackages/"Update_KUALBooklet*.bin "$KINDLE_MNT/mrpackages/" 2>/dev/null || true
            echo "[✓] Staged KUAL Booklet installer into $KINDLE_MNT/mrpackages/"
        else
            echo "[✓] KUAL already installed on Kindle (preserving existing KUAL Booklet)"
        fi

        if [ ! -d "$KINDLE_MNT/usbnetlite" ] && [ ! -d "$KINDLE_MNT/usbnet" ]; then
            cp -f "$STAGE_DIR/mrpackages/"Update_usbnetlite*.bin "$KINDLE_MNT/mrpackages/"
            echo "[✓] Staged USBNetLite (KHF) installer -> $KINDLE_MNT/mrpackages/"
        else
            echo "[✓] USBNetLite / USBNetwork already installed on Kindle"
        fi
    fi

    cp -rf "$SCRIPT_DIR/kindle-extension/kindle-dashboard" "$KINDLE_MNT/extensions/"
    echo "[✓] Installed Pasadena Zen Dashboard KUAL menu -> $KINDLE_MNT/extensions/kindle-dashboard/"

    # Also copy SSH key directly if usbnetlite or usbnet folder already exists
    for auth_dir in "$KINDLE_MNT/usbnetlite/etc/dropbear" "$KINDLE_MNT/usbnet/etc"; do
        if [ -d "$(dirname "$auth_dir")" ]; then
            mkdir -p "$auth_dir"
            cat "${KEY_PATH}.pub" >> "$auth_dir/authorized_keys"
            sort -u -o "$auth_dir/authorized_keys" "$auth_dir/authorized_keys"
            echo "[✓] Installed SSH public key -> $auth_dir/authorized_keys"
        fi
    done

    sync
    echo
    echo ">>> NEXT STEPS ON YOUR KINDLE <<<"
    echo "  1. Safely eject & unplug the Kindle."
    echo "  2. If you haven't installed KUAL/USBNetLite yet: type  ;log mrpi  in the Kindle search bar and wait ~1 min."
    echo "  3. Type  ;un  in the Kindle search bar, plug USB back in, and re-run ./setup_usbnet.sh once!"
    echo
fi

# 4. Detect USB Ethernet gadget interface (usb0 / enp*u* / enx* / any USB wired netdev)
USB_IFACE=""
for netpath in /sys/class/net/*; do
    iface="$(basename "$netpath")"
    [ "$iface" = "lo" ] && continue
    [ -d "$netpath/wireless" ] && continue
    devlink="$(readlink -f "$netpath/device" 2>/dev/null || true)"
    if [[ "$iface" == usb* ]] || [[ "$iface" == enp*u* ]] || [[ "$iface" == enx* ]] || [[ "$devlink" == *"/usb"* ]]; then
        USB_IFACE="$iface"
        break
    fi
done

if [ -n "$USB_IFACE" ]; then
    echo "[+] Found Kindle USB Ethernet interface: $USB_IFACE"
    if ! ip -4 addr show dev "$USB_IFACE" | grep -q "192.168.15."; then
        if command -v nmcli >/dev/null 2>&1; then
            echo "[+] Creating persistent NetworkManager profile 'Kindle-USBNet' (192.168.15.201/24, never-default)..."
            sudo nmcli connection delete "Kindle-USBNet" >/dev/null 2>&1 || true
            sudo nmcli connection add type ethernet con-name "Kindle-USBNet" \
                connection.interface-name "" match.interface-name "enp*u* usb* enx*" \
                ipv4.method manual ipv4.addresses 192.168.15.201/24 ipv4.never-default yes \
                ipv6.method ignore autoconnect yes
            sudo nmcli connection up "Kindle-USBNet" || true
        else
            echo "[+] Assigning host IP 192.168.15.201/24 to $USB_IFACE ..."
            sudo ip link set "$USB_IFACE" up
            sudo ip addr add 192.168.15.201/24 dev "$USB_IFACE" || true
        fi
    fi
    if command -v firewall-cmd >/dev/null 2>&1 && sudo firewall-cmd --state >/dev/null 2>&1; then
        sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="192.168.15.0/24" port port="8788" protocol="tcp" accept' >/dev/null 2>&1 || true
        sudo firewall-cmd --reload >/dev/null 2>&1 || true
    fi
    echo "[+] Pushing Pasadena Zen Dashboard to Kindle (192.168.15.244)..."
    python3 "$SCRIPT_DIR/dashboard.py" --push --full
else
    echo "[i] Kindle USB Ethernet interface (usb0) not active right now."
    echo "    Live Web Studio is running at: http://localhost:8788"
fi
