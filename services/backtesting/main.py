import os
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def health():
    return jsonify({"status": "healthy", "service": "backtesting-simulator"}), 200

@app.route('/run', methods=['POST'])
def run_simulation():
    return jsonify({"message": "Simulación iniciada", "result": "success"}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
