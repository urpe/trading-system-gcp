from flask import Flask, render_template_string, jsonify
import os

app = Flask(__name__)

@app.route('/')
def debug_index():
    # Esto forzará una respuesta simple para descartar errores de servidor
    return "<h1>¡El servidor Dashboard está VIVO!</h1><p>Si ves esto, el problema es el archivo index.html</p>"

@app.route('/test-html')
def test_html():
    # Intentar cargar el archivo real para ver si lanza error
    try:
        return render_template('index.html', signals=[], orders=[], buys=0, sells=0, win_rate=0, pnl=0, volume=0, services={})
    except Exception as e:
        return f"<h1>Error en el HTML:</h1><pre>{str(e)}</pre>"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
