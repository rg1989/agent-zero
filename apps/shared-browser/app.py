from flask import Flask, render_template_string, send_from_directory
import os

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Shared Browser - Agent Zero</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }
        .header {
            background: rgba(255, 255, 255, 0.95);
            padding: 1.5rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header h1 {
            color: #333;
            font-size: 1.8rem;
            margin-bottom: 0.5rem;
        }
        .header p {
            color: #666;
            font-size: 0.95rem;
        }
        .status {
            display: inline-block;
            padding: 0.3rem 0.8rem;
            background: #10b981;
            color: white;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
            margin-top: 0.5rem;
        }
        .status.connecting {
            background: #f59e0b;
        }
        .status.disconnected {
            background: #ef4444;
        }
        .container {
            flex: 1;
            display: flex;
            padding: 1.5rem;
            gap: 1.5rem;
        }
        .browser-panel {
            flex: 1;
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.15);
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }
        .browser-header {
            background: #f3f4f6;
            padding: 1rem;
            border-bottom: 1px solid #e5e7eb;
        }
        .browser-header h2 {
            font-size: 1.1rem;
            color: #333;
        }
        #screen {
            flex: 1;
            background: #1f2937;
            position: relative;
        }
        .info-panel {
            width: 300px;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 4px 20px rgba(0,0,0,0.15);
            height: fit-content;
        }
        .info-panel h3 {
            color: #333;
            margin-bottom: 1rem;
            font-size: 1.2rem;
        }
        .info-item {
            margin-bottom: 1rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid #e5e7eb;
        }
        .info-item:last-child {
            border-bottom: none;
        }
        .info-item strong {
            display: block;
            color: #4b5563;
            font-size: 0.85rem;
            margin-bottom: 0.3rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .info-item span {
            color: #1f2937;
            font-size: 0.95rem;
        }
        .loading {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            color: white;
            font-size: 1.2rem;
            text-align: center;
        }
        .spinner {
            border: 4px solid rgba(255,255,255,0.3);
            border-radius: 50%;
            border-top: 4px solid white;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 1rem;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🌐 Shared Browser</h1>
        <p>Collaborative browser instance powered by Agent Zero</p>
        <div class="status connecting" id="status">⚡ Connecting...</div>
    </div>

    <div class="container">
        <div class="browser-panel">
            <div class="browser-header">
                <h2>📱 Browser View</h2>
            </div>
            <div id="screen">
                <div class="loading">
                    <div class="spinner"></div>
                    <div>Initializing browser...</div>
                </div>
            </div>
        </div>

        <div class="info-panel">
            <h3>ℹ️ Session Info</h3>
            <div class="info-item">
                <strong>Browser</strong>
                <span>Chromium (Headless)</span>
            </div>
            <div class="info-item">
                <strong>Display</strong>
                <span>1280x720 Virtual</span>
            </div>
            <div class="info-item">
                <strong>Control</strong>
                <span>Mouse &amp; Keyboard</span>
            </div>
            <div class="info-item">
                <strong>Shared Access</strong>
                <span>You &amp; Agent Zero</span>
            </div>
            <div class="info-item">
                <strong>Note</strong>
                <span style="font-size: 0.85rem; line-height: 1.4;">Both you and Agent Zero can control this browser simultaneously. Any changes made by either party are instantly visible to both.</span>
            </div>
        </div>
    </div>

    <script type="module" crossorigin="anonymous">
        import RFB from './static/noVNC/core/rfb.js';

        const statusEl = document.getElementById('status');
        const screenEl = document.getElementById('screen');

        function updateStatus(state, message) {
            statusEl.className = 'status ' + state;
            statusEl.textContent = message;
        }

        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${wsProtocol}//${window.location.host}/shared-browser/websockify`;

        console.log('Connecting to:', wsUrl);

        try {
            const rfb = new RFB(screenEl, wsUrl, {
                credentials: { password: '' }
            });

            rfb.addEventListener('connect', () => {
                updateStatus('', '✅ Connected');
                console.log('VNC connected');
            });

            rfb.addEventListener('disconnect', (e) => {
                updateStatus('disconnected', '❌ Disconnected');
                console.log('VNC disconnected:', e.detail);
                screenEl.innerHTML = `
                    <div class="loading">
                        <div>Connection lost. Refresh to reconnect.</div>
                    </div>
                `;
            });

            rfb.scaleViewport = true;
            rfb.resizeSession = true;

        } catch(e) {
            console.error('Failed to initialize RFB:', e);
            updateStatus('disconnected', '❌ Failed to connect');
            screenEl.innerHTML = `
                <div class="loading">
                    <div>Failed to initialize: ${e.message}</div>
                </div>
            `;
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 9003))
    app.run(host='0.0.0.0', port=port, debug=False)
