import os
from flask import Flask, render_template, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    # Enviamos datos mínimos para asegurar el renderizado
    return render_template('index.html', signals=[], win_rate=0, pnl=0)

@app.route('/api/status')
def status():
    return jsonify({"status": "ok", "version": "v3.1.3"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
