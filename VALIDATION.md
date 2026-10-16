# Validation — 2026-10-16

Host pi@192.168.2.132, X7 connected over USB. No Katana changes made.

- Before change: office-usb-input enabled/running; X7 PCM RUNNING continuously.
- Disabled and stopped office-usb-input user service (survives reboot).
- After settling: office.eq suspended, office.x7 suspended, X7 playback PCM closed.
- Three-second silent 48kHz stereo WAV played through pw-play --target=office.eq.
- Before test: closed. During test: RUNNING. Seven seconds after completion: closed.
- No hardware volume or mute changes were made for this test.
- Python sources compile successfully.

This proves automatic USB PCM open/close through the EQ graph. It does not prove
an audible AirPlay resume, X7 native sleep status, or a power reduction measurement.
Physical LED/power-saving behaviour and first audio after longer inactivity still
need observation. An active source stream can intentionally prevent suspension.

Rollback: systemctl --user enable --now office-usb-input
Only use if deliberately restoring the previously configured USB-C gadget path.
