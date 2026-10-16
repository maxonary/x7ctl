# x7ctl — Raspberry Pi Sound Blaster X7

Configuration and control tools for maxonary's Office AirPlay receiver and Creative
Sound Blaster X7 (USB VID 041e, PID 323a). Private infrastructure repository.
No Katana configuration or power-management changes are included.

## Audio path

Apple Music → AirPlay 2 → Shairport Sync → PipeWire `office.eq` → three-band software
EQ → `office.x7` → X7 USB DAC/amplifier. NQPTP supplies AirPlay timing.
WirePlumber manages the hardware node and suspends it when playback becomes idle.
Homebridge currently runs on Gallery and calls Office's authenticated HTTP API.

Current host: pi@192.168.2.132, Raspberry Pi4 8GB, Debian13. A future physical swap
with Bedroom Pi3 is planned but has NOT happened. Use ALSA card name `X7`, not a
numeric card index, so USB enumeration changes do not redirect controls.

## Idle USB release — fixed 2026-10-16

The unused `office-usb-input.service` ran a permanent `pw-loopback` from the USB-C
gadget into the EQ sink. This kept the X7 streaming silence even with no AirPlay.
Disabling this user service lets the EQ and X7 suspend and closes the ALSA playback
PCM. Wired Mac input is intentionally out of scope.

Run `scripts/enable-idle-release.sh` as pi to reproduce the change. It first checks
that the X7 speaker mixer exists and touches only the named Office loopback unit.
No receiver, EQ, API or USB sound-card drivers are disabled.
WirePlumber's normal suspend timeout is five seconds. Active AirPlay, including
silence in an active stream, can still keep the device open. Pausing or disconnecting
must make the source stream inactive before suspension can happen.

This releases USB playback; it does NOT command the amplifier to power off or
prove that its own power-saving mode activates. The X7's native Auto Standby setting
has not been read or changed. Verify its LED/power behaviour separately.

## Verified controls

- ALSA hardware Speaker volume and mute via `scripts/x7-api.py`.
- Software bass/mid/treble EQ, each -6..+6dB, and Flat/Night/Speech presets through
  `scripts/office-eq.py`. Positive boosts receive matching preamp attenuation.
- Existing Gallery HomeKit accessories: X7 Volume, Office EQ Flat/Night/Speech.
- Read-only native USB headphone-jack query: `sudo x7-native status`.

`scripts/x7-native.py` also prepares native SBX, ten-band EQ and output-routing
packets. These DSP writes are NOT yet validated on this X7 or exposed in HomeKit.
Default is dry run; `--apply` sends a command. It reports no verified DSP readback.
Native hardware EQ and software EQ are separate stages; avoid stacking boosts.
ALSA Capture Source controls are not verified playback-input selectors.

## Files and deployment mapping

| Repository file | Current Pi path |
|---|---|
| config/office-wireplumber.conf | ~/.config/wireplumber/wireplumber.conf.d/office.conf |
| config/office-eq.conf | ~/.config/pipewire/pipewire.conf.d/office-eq.conf |
| config/office-shairport-pipewire.conf | /etc/shairport-sync.conf |
| scripts/office-eq.py | /usr/local/bin/office-eq |
| scripts/x7-native.py | /usr/local/bin/x7-native |
| scripts/x7-api.py | /opt/pi-home-audio/scripts/x7-api.py |
| systemd/office-eq-restore.service | ~/.config/systemd/user/office-eq-restore.service |
| systemd/office-shairport-pipewire.conf | /etc/systemd/system/shairport-sync.service.d/office.conf |
| systemd/office-shairport-logging.conf | /etc/systemd/system/shairport-sync.service.d/logging.conf |
| systemd/x7-api.service | /etc/systemd/system/x7-api.service |

The legacy /opt/pi-home-audio path is retained to match the running API service.
User pi has linger enabled, supplying PipeWire's /run/user/1000 runtime without an
interactive login. EQ state persists in /var/lib/office-audio/eq.json.
Current stable software: Shairport Sync5.6 with native PipeWire backend, NQPTP1.2.9,
PipeWire1.4.2 and WirePlumber0.5 on Debian13.

API: Office TCP8100, Bearer token from root-readable /etc/x7-api.env. GET/POST /state
(volume0..100, muted boolean) and GET/POST /eq. Credentials are never committed.
Keep this endpoint on the trusted LAN; it does not provide TLS or Internet access.

## Recovery and migration

Before the idle change, WirePlumber config was copied on Office to
/var/backups/pi-home-audio/pre-idle-release/. Older full configuration backups live
under /var/backups/pi-home-audio/pre-update-20261015/ and off-Pi private backups.
Never commit those backups: they contain credentials and HomeKit pairing material.

Restoring the old USB-C path would require enabling office-usb-input again, but
would restore its always-open stream behaviour; do not do that by default.
For the upcoming Pi swap, copy audio configuration and credentials securely,
retain HomeKit identities, update host routing, then repeat the idle/wake check.
Do not copy the Pi4 USB-C gadget configuration to Pi3.

The original multi-room configuration remains in the private repository
https://github.com/maxonary/pi-home-audio (Homebridge plugin and historical setup).
This dedicated repository records X7 behaviour and current source files.

## References

- WirePlumber ALSA suspend policy: https://pipewire.pages.freedesktop.org/wireplumber/daemon/configuration/alsa.html
- X7 native USB protocol reference: https://github.com/alcatron/mb-x7-control/blob/main/PROTOCOL.md
- Shairport Sync: https://github.com/mikebrady/shairport-sync
