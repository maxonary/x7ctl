#!/usr/bin/env python3
"""Live three-band PipeWire EQ, with persistent settings and boost headroom."""
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

STATE = Path('/var/lib/office-audio/eq.json')
PRESETS = {'flat': (0, 0, 0), 'night': (-6, 0, -2), 'speech': (-3, 2, -2)}
BANDS = ('bass', 'mid', 'treble')

def run(*args):
    return subprocess.check_output(args, text=True, timeout=5,
                                   env={**os.environ, 'XDG_RUNTIME_DIR': '/run/user/1000'})

def node():
    for item in json.loads(run('/usr/bin/pw-dump')):
        if item.get('info', {}).get('props', {}).get('node.name') == 'office.eq':
            return item
    raise RuntimeError('Office equalizer unavailable')

def get():
    item = node()
    params = {}
    for props in item['info']['params'].get('Props', []):
        seq = props.get('params', [])
        params.update(zip(seq[::2], seq[1::2]))
    values = {b: params[b + ':Gain'] for b in BANDS}
    values['preamp_db'] = -sum(max(0, values[b]) for b in BANDS)
    values['preset'] = next((p for p, v in PRESETS.items()
                             if tuple(values[b] for b in BANDS) == v), 'custom')
    return values

def apply(values):
    params = [v for b in BANDS for v in (b + ':Gain', values[b])]
    # Conservative attenuation covers the sum of all positive band gains.
    gain = 10 ** (-sum(max(0, values[b]) for b in BANDS) / 20)
    run('/usr/bin/pw-cli', 'set-param', 'office.eq', 'Props',
        json.dumps({'params': params, 'channelVolumes': [gain, gain]}))

def set_values(body):
    if not isinstance(body, dict) or not body or set(body) - {*BANDS, 'preset'}:
        raise ValueError('Expected bass, mid, treble or preset')
    if 'preset' in body:
        if set(body) != {'preset'} or not isinstance(body['preset'], str) or body['preset'] not in PRESETS:
            raise ValueError('preset must be flat, night or speech')
        values = dict(zip(BANDS, PRESETS[body['preset']]))
    else:
        current = get()
        values = {b: current[b] for b in BANDS}
        for b, value in body.items():
            if type(value) not in (int, float) or not math.isfinite(value) or not -6 <= value <= 6:
                raise ValueError('Band gains must be numbers from -6 to 6 dB')
            values[b] = value
    apply(values)
    STATE.parent.mkdir(parents=True, exist_ok=True)
    temp = STATE.with_suffix('.tmp')
    temp.write_text(json.dumps(values))
    temp.replace(STATE)
    return get()

if __name__ == '__main__':
    try:
        if sys.argv[1:] == ['restore']:
            values = json.loads(STATE.read_text()) if STATE.exists() else dict.fromkeys(BANDS, 0)
            for attempt in range(20):
                try:
                    apply(values)
                    break
                except (RuntimeError, subprocess.SubprocessError):
                    if attempt == 19:
                        raise
                    time.sleep(1)
            print(json.dumps(get()))
        elif sys.argv[1:] == ['get']:
            print(json.dumps(get()))
        else:
            print(json.dumps(set_values(json.loads(sys.argv[1]))))
    except ValueError as exc:
        print(json.dumps({'error': str(exc)}))
        sys.exit(2)
