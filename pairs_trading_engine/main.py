import os
from flask import Flask, jsonify
app = Flask(__name__)
@app.route('/api/correlation')
def correlation():
    return jsonify({"status": "active", "pairs": [{"pair": "BTC/ETH", "corr": 0.92}, {"pair": "SOL/ETH", "corr": 0.78}]})
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))