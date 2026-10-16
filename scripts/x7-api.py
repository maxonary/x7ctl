#!/usr/bin/env python3
"""Authenticated LAN API for the X7's verified ALSA speaker controls."""
import hmac
import json
import os
import re
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TOKEN = os.environ['X7_API_TOKEN']
LOCK = threading.Lock()

def mixer(*args):
    return subprocess.check_output(
        ['/usr/bin/amixer', '-c', 'X7', 'sset' if args else 'sget', 'Speaker', *args],
        text=True, timeout=5, env={**os.environ, 'LC_ALL': 'C'})

def state(output):
    match = re.search(r'\[(\d+)%\].*\[(on|off)\]', output)
    if not match:
        raise RuntimeError('X7 speaker mixer unavailable')
    return {'volume': int(match[1]), 'muted': match[2] == 'off'}

def equalizer(body=None):
    result = subprocess.run(['/usr/local/bin/office-eq',
                             'get' if body is None else json.dumps(body)],
                            capture_output=True, text=True, timeout=10)
    if result.returncode == 2:
        raise ValueError(json.loads(result.stdout)['error'])
    result.check_returncode()
    return json.loads(result.stdout)

class Handler(BaseHTTPRequestHandler):
    def reply(self, status, body):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def authorized(self):
        return hmac.compare_digest(self.headers.get('Authorization', ''), 'Bearer ' + TOKEN)

    def do_GET(self):
        if not self.authorized():
            return self.reply(401, {'error': 'Unauthorized'})
        if self.path not in ('/state', '/eq'):
            return self.reply(404, {'error': 'Not found'})
        try:
            with LOCK:
                result = equalizer() if self.path == '/eq' else state(mixer())
            self.reply(200, result)
        except (OSError, subprocess.SubprocessError, RuntimeError):
            self.reply(503, {'error': 'X7 unavailable'})

    def do_POST(self):
        if not self.authorized():
            return self.reply(401, {'error': 'Unauthorized'})
        if self.path not in ('/state', '/eq'):
            return self.reply(404, {'error': 'Not found'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 1024:
                raise ValueError('Invalid body size')
            body = json.loads(self.rfile.read(length))
            if self.path == '/eq':
                if not isinstance(body, dict):
                    raise ValueError('Expected EQ settings object')
                with LOCK:
                    result = equalizer(body)
                return self.reply(200, result)
            if not isinstance(body, dict) or not body or set(body) - {'volume', 'muted'}:
                raise ValueError('Expected volume or muted')
            args = []
            if 'volume' in body:
                v = body['volume']
                if type(v) is not int or not 0 <= v <= 100:
                    raise ValueError('volume must be an integer from 0 to 100')
                args.append(str(v) + '%')
            if 'muted' in body:
                if type(body['muted']) is not bool:
                    raise ValueError('muted must be boolean')
                args.append('mute' if body['muted'] else 'unmute')
            with LOCK:
                result = state(mixer(*args))
            self.reply(200, result)
        except (ValueError, TypeError) as exc:
            self.reply(400, {'error': str(exc)})
        except (OSError, subprocess.SubprocessError, RuntimeError):
            self.reply(503, {'error': 'X7 unavailable'})

    def log_message(self, *_):
        pass

if __name__ == '__main__':
    ThreadingHTTPServer(('0.0.0.0', 8100), Handler).serve_forever()
