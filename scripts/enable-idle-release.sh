#!/bin/sh
# Run as the existing Office audio user (pi), not root.
set -eu
if [ "$(id -u)" = 0 ]; then echo 'Run as the audio user, not root.' >&2; exit 1; fi
amixer -c X7 sget Speaker >/dev/null
# This loopback is only the unused USB-C Mac input. Do not touch other audio units.
if systemctl --user cat office-usb-input.service >/dev/null 2>&1; then
 systemctl --user disable --now office-usb-input.service
fi
printf 'Unused USB-C loopback disabled. Active AirPlay playback can still hold the X7 open.\n'
