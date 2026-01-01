import os
from flask import Flask, jsonify, request
app = Flask(__name__)
@app.route('/api/backtest', methods=['POST'])
def run_backtest():
    return jsonify({"status": "complete", "pnl": 24.5, "win_rate": 62.3, "trades": 145})
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))