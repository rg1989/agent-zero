import os
import subprocess
import time
import atexit
import signal
from flask import Flask, send_from_directory, jsonify

app = Flask(__name__)

DISPLAY = ":99"
VNC_PORT = 5900
WS_PORT = 6080
FLASK_PORT = int(os.environ.get('PORT', 9002))

processes = {}

def cleanup():
    for name, proc in processes.items():
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except:
                proc.kill()

atexit.register(cleanup)

def start_xvfb():
    if "xvfb" in processes and processes["xvfb"].poll() is None:
        return True
    try:
        proc = subprocess.Popen(
            ['Xvfb', DISPLAY, '-screen', '0', '1920x1080x24', '-nolisten', 'tcp', '-ac'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        processes["xvfb"] = proc
        time.sleep(2)
        return proc.poll() is None
    except Exception as e:
        print(f"Failed to start Xvfb: {e}")
        return False

def start_vnc():
    if "vnc" in processes and processes["vnc"].poll() is None:
        return True
    try:
        env = os.environ.copy()
        env['DISPLAY'] = DISPLAY
        proc = subprocess.Popen(
            ['x11vnc', '-display', DISPLAY, '-rfbport', str(VNC_PORT),
             '-forever', '-shared', '-nopw', '-quiet'],
            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        processes["vnc"] = proc
        time.sleep(2)
        return proc.poll() is None
    except Exception as e:
        print(f"Failed to start x11vnc: {e}")
        return False

def start_browser():
    if "browser" in processes and processes["browser"].poll() is None:
        return True
    try:
        env = os.environ.copy()
        env['DISPLAY'] = DISPLAY
        proc = subprocess.Popen(
            ['chromium', '--no-sandbox', '--disable-dev-shm-usage',
             '--start-maximized', '--no-first-run', 'https://www.google.com'],
            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        processes["browser"] = proc
        time.sleep(3)
        return proc.poll() is None
    except Exception as e:
        print(f"Failed to start Chromium: {e}")
        return False

def start_websockify():
    if "websockify" in processes and processes["websockify"].poll() is None:
        return True
    try:
        proc = subprocess.Popen(
            ['websockify', '--web', '/a0/apps/browser-vnc/static/novnc',
             str(WS_PORT), f'localhost:{VNC_PORT}'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        processes["websockify"] = proc
        time.sleep(2)
        return proc.poll() is None
    except Exception as e:
        print(f"Failed to start websockify: {e}")
        return False

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/init')
def api_init():
    try:
        if not start_xvfb():
            return jsonify({'success': False, 'error': 'Failed to start Xvfb'})
        if not start_vnc():
            return jsonify({'success': False, 'error': 'Failed to start x11vnc'})
        if not start_browser():
            return jsonify({'success': False, 'error': 'Failed to start Chromium'})
        if not start_websockify():
            return jsonify({'success': False, 'error': 'Failed to start websockify'})
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/status')
def api_status():
    return jsonify({
        'xvfb': 'xvfb' in processes and processes['xvfb'].poll() is None,
        'vnc': 'vnc' in processes and processes['vnc'].poll() is None,
        'browser': 'browser' in processes and processes['browser'].poll() is None,
        'websockify': 'websockify' in processes and processes['websockify'].poll() is None,
    })

if __name__ == '__main__':
    print(f"🚀 VNC Browser Viewer starting on port {FLASK_PORT}")
    app.run(host='0.0.0.0', port=FLASK_PORT, debug=False)
