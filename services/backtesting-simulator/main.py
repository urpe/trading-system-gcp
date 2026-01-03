import os
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def health():
    return "Simulator is Alive", 200

@app.route('/run', methods=['POST'])
def run_backtest():
    return jsonify({"status": "success", "message": "Simulación iniciada correctamente"}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
