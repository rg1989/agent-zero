from flask import Flask, request, send_file, jsonify, send_from_directory
from flask_cors import CORS
from rembg import remove
from PIL import Image
import os
import io
import uuid
from datetime import datetime, timedelta

app = Flask(__name__, static_folder='.')
CORS(app)

# Ensure directories exist
os.makedirs('/tmp/uploads', exist_ok=True)
os.makedirs('/tmp/outputs', exist_ok=True)

def cleanup_old_files():
    """Remove files older than 1 hour"""
    now = datetime.now()
    for directory in ['/tmp/uploads', '/tmp/outputs']:
        if os.path.exists(directory):
            for filename in os.listdir(directory):
                filepath = os.path.join(directory, filename)
                if os.path.isfile(filepath):
                    file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                    if now - file_time > timedelta(hours=1):
                        try:
                            os.remove(filepath)
                        except Exception:
                            pass

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/remove-bg', methods=['POST'])
def remove_background():
    try:
        # Clean up old files
        cleanup_old_files()

        # Validate file upload
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400

        file = request.files['image']

        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        # Validate file type
        allowed_extensions = {'png', 'jpg', 'jpeg', 'webp', 'bmp'}
        file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''

        if file_ext not in allowed_extensions:
            return jsonify({'error': f'Invalid file type. Allowed: {allowed_extensions}'}), 400

        # Generate unique filename
        unique_id = str(uuid.uuid4())
        input_path = f'/tmp/uploads/{unique_id}_input.{file_ext}'
        output_path = f'/tmp/outputs/{unique_id}_output.png'

        # Save uploaded file
        file.save(input_path)

        # Open and process image
        with open(input_path, 'rb') as input_file:
            input_data = input_file.read()

        # Remove background
        output_data = remove(input_data)

        # Save output
        with open(output_path, 'wb') as output_file:
            output_file.write(output_data)

        # Clean up input file
        try:
            os.remove(input_path)
        except Exception:
            pass

        # Return processed image
        return send_file(
            output_path,
            mimetype='image/png',
            as_attachment=True,
            download_name=f'removed_bg_{file.filename.rsplit(".", 1)[0]}.png'
        )

    except Exception as e:
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9000, debug=False)
