import os
import requests
from flask import Flask, render_template, jsonify, request
from google.cloud import firestore

app = Flask(__name__)
PROJECT_ID = os.environ.get("PROJECT_ID", "mi-proyecto-trading-12345")
db = firestore.Client(project=PROJECT_ID)

# URLs de servicios internos
SIMULATOR_URL = os.environ.get("SIMULATOR_URL", "http://simulator:5000")
PAIRS_URL = os.environ.get("PAIRS_URL", "http://pairs-trading:5000")
HISTORICAL_URL = os.environ.get("HISTORICAL_URL", "http://historical-data:5000")

def get_active_assets():
    """Consulta monedas activas"""
    try:
        docs = db.collection('market_data').stream()
        data = {}
        asset_list = []
        for doc in docs:
            symbol = doc.id.upper()
            data[symbol] = doc.to_dict()
            asset_list.append(symbol)
        asset_list.sort()
        return data, asset_list
    except Exception:
        return {}, []

def get_wallet_info():
    """Obtiene el estado de la cuenta y portafolio (Soporte Short)"""
    try:
        # 1. Saldo USDT (Efectivo)
        wallet_doc = db.collection('wallet').document('main_account').get()
        wallet = wallet_doc.to_dict() if wallet_doc.exists else {'usdt_balance': 10000, 'initial_capital': 10000}
        
        # 2. Posiciones
        portfolio_docs = db.collection('portfolio').stream()
        positions = []
        total_equity = wallet['usdt_balance'] # Patrimonio empieza con el efectivo
        
        for doc in portfolio_docs:
            pos = doc.to_dict()
            amount = pos.get('amount', 0)
            
            # Si la cantidad es casi 0, ignorar (basura flotante)
            if abs(amount) < 0.000001:
                continue

            current_price = pos.get('current_price', pos.get('avg_price', 0))
            
            # Valor de la posición (Puede ser negativo si es Short)
            # Ejemplo: -1 BTC * $90,000 = -$90,000 (Deuda)
            position_value = amount * current_price
            
            # PNL No realizado de esta posición
            # Long: (Precio Actual - Promedio) * Cantidad
            # Short: (Precio Promedio - Actual) * Abs(Cantidad) -> simplificado es lo mismo:
            unrealized_pnl = (current_price - pos['avg_price']) * amount

            # Añadir datos calculados para el HTML
            pos['current_value'] = position_value
            pos['unrealized_pnl'] = unrealized_pnl
            pos['type'] = 'SHORT' if amount < 0 else 'LONG'
            
            total_equity += position_value
            positions.append(pos)
            
        # PNL Total de la cuenta
        initial_capital = wallet.get('initial_capital', 10000)
        total_pnl = total_equity - initial_capital
        pnl_percent = (total_pnl / initial_capital) * 100
        
        return {
            'usdt': wallet['usdt_balance'],
            'total_balance': total_equity, # Equity Real
            'pnl_percent': pnl_percent,
            'positions': positions
        }
    except Exception as e:
        print(f"Error wallet: {e}")
        return None

@app.route('/')
def index():
    data, active_assets = get_active_assets()
    wallet_info = get_wallet_info()
    
    # Resumen Mercado
    total_change = sum([d.get('change', 0) for d in data.values()])
    active_count = len(active_assets)
    summary = {
        "active_assets": active_count,
        "avg_change": round(total_change / active_count, 2) if active_count > 0 else 0
    }
    
    signals_ref = db.collection('signals').order_by('timestamp', direction=firestore.Query.DESCENDING).limit(20)
    signals = [s.to_dict() for s in signals_ref.stream()]
    
    return render_template('index.html', 
                           data=data, 
                           summary=summary, 
                           signals=signals, 
                           assets=active_assets,
                           wallet=wallet_info)

# ... (Resto de rutas igual: /asset, /simulator, /pairs, /api ...)
@app.route('/asset/<symbol>')
def asset_view(symbol):
    symbol = symbol.upper()
    doc = db.collection('market_data').document(symbol).get()
    data = doc.to_dict() if doc.exists else {}
    signals_ref = db.collection('signals').where('symbol', '==', symbol).order_by('timestamp', direction=firestore.Query.DESCENDING).limit(20)
    signals = [s.to_dict() for s in signals_ref.stream()]
    return render_template('asset.html', symbol=symbol, data=data, signals=signals)

@app.route('/simulator')
def simulator_view():
    _, active_assets = get_active_assets()
    return render_template('simulator.html', assets=active_assets)

@app.route('/pairs')
def pairs_view():
    _, active_assets = get_active_assets()
    try:
        signals_ref = db.collection('signals')\
                        .where('type', '==', 'PAIR_TRADE')\
                        .order_by('timestamp', direction=firestore.Query.DESCENDING)\
                        .limit(20)
        pair_signals = [s.to_dict() for s in signals_ref.stream()]
    except Exception:
        pair_signals = []
    return render_template('pairs.html', assets=active_assets, signals=pair_signals)

@app.route('/api/run-simulation', methods=['POST'])
def run_simulation():
    try:
        resp = requests.post(f"{SIMULATOR_URL}/run", json=request.json, timeout=30)
        return jsonify(resp.json()), resp.status_code
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/load-historical/<symbol>', methods=['POST'])
def load_historical(symbol):
    try:
        days = request.args.get('days', 30)
        resp = requests.post(f"{HISTORICAL_URL}/load/{symbol}?days={days}", timeout=60)
        return jsonify(resp.json()), resp.status_code
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8050))
    app.run(host='0.0.0.0', port=port)