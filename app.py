from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import base64
import os
import tempfile
import logging

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "message": "EPS Converter is running"})

@app.route('/convert', methods=['POST'])
def convert():
    try:
        data = request.get_json()
        if not data or 'file' not in data:
            return jsonify({"error": "No file data provided"}), 400

        # Decode base64 EPS file
        file_data = base64.b64decode(data['file'])

        with tempfile.TemporaryDirectory() as tmpdir:
            eps_path = os.path.join(tmpdir, 'input.eps')
            png_path = os.path.join(tmpdir, 'output.png')

            # Write EPS file
            with open(eps_path, 'wb') as f:
                f.write(file_data)

            # Convert EPS to PNG using Ghostscript
            result = subprocess.run([
                'gs',
                '-dNOPAUSE',
                '-dBATCH',
                '-dSAFER',
                '-sDEVICE=png16m',
                '-r150',
                '-dEPSCrop',
                f'-sOutputFile={png_path}',
                eps_path
            ], capture_output=True, text=True, timeout=60)

            if result.returncode != 0:
                logger.error(f"Ghostscript error: {result.stderr}")
                return jsonify({"error": "Conversion failed", "details": result.stderr}), 500

            if not os.path.exists(png_path):
                return jsonify({"error": "Output file not created"}), 500

            # Read and encode PNG
            with open(png_path, 'rb') as f:
                png_data = base64.b64encode(f.read()).decode('utf-8')

            logger.info("EPS converted successfully")
            return jsonify({"image": png_data, "format": "png"})

    except subprocess.TimeoutExpired:
        return jsonify({"error": "Conversion timeout"}), 504
    except Exception as e:
        logger.error(f"Conversion error: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 7860))
    app.run(host='0.0.0.0', port=port)
