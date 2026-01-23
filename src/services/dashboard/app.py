from flask import Flask, render_template, jsonify, request
from google.cloud import firestore
from src.config.settings import config
from src.shared.utils import get_logger
import requests

logger = get_logger("Dashboard")
app = Flask(__name__)
db = firestore.Client(project=config.PROJECT_ID)

# --- Helper Functions ---

def get_wallet_data():
    """Fetch wallet and positions data from Firestore."""
    wallet = {
        "usdt_balance": config.INITIAL_CAPITAL, 
        "total_equity": config.INITIAL_CAPITAL, 
        "positions": []
    }
    try:
        w_doc = db.collection('wallet').document('main_account').get()
        if w_doc.exists:
            wd = w_doc.to_dict()
            wallet['usdt_balance'] = wd.get('usdt_balance', 0)
            
        pos_docs = db.collection('portfolio').stream()
        equity = wallet['usdt_balance']
        
        for p in pos_docs:
            pd = p.to_dict()
            val = pd.get('amount', 0) * pd.get('current_price', 0)
            
            # Basic PnL calculation (Current Value - Cost Basis) if entry_price exists
            if pd.get('type') == 'LONG': 
                equity += val
            elif pd.get('type') == 'SHORT':
                 # Simplified Short Equity logic if needed
                pass 

            wallet['positions'].append({
                "type": pd.get('type'), 
                "symbol": pd.get('symbol'),
                "amount": round(pd.get('amount'), 4), 
                "current_price": round(pd.get('current_price'), 2),
                "value": round(val, 2),
                "entry_price": round(pd.get('entry_price', 0), 2),
                "pnl": round(val - (pd.get('amount', 0) * pd.get('entry_price', 0)), 2) if pd.get('entry_price') else 0
            })
        
        wallet['total_equity'] = round(equity, 2)
        wallet['usdt_balance'] = round(wallet['usdt_balance'], 2)
        
    except Exception as e:
        logger.error(f"DB Error get_wallet_data: {e}")
        
    return wallet

def get_pairs_data():
    """Fetch pairs trading signals from Firestore."""
    signals = []
    try:
        # Fetch recent signals from 'signals' collection where source is 'pairs_trading'
        # Or if there is a dedicated 'pairs_status' collection
        docs = db.collection('signals').order_by('timestamp', direction=firestore.Query.DESCENDING).limit(20).stream()
        for doc in docs:
            d = doc.to_dict()
            if d.get('source') == 'pairs_trading' or d.get('strategy') == 'PAIRS_TRADING':
                 signals.append({
                    "timestamp": d.get('timestamp').strftime('%H:%M:%S') if d.get('timestamp') else '--:--',
                    "symbol": d.get('symbol'),
                    "signal": d.get('signal'), # BUY/SELL
                    "correlation": round(d.get('correlation', 0), 2),
                    "z_score": round(d.get('z_score', 0), 2),
                    "status": d.get('status', 'OPEN')
                 })
    except Exception as e:
        logger.error(f"DB Error get_pairs_data: {e}")
    return signals

def get_active_assets():
    """Fetch list of assets available for simulation."""
    # Ideally fetch from a config or active market data collection
    # For now returning a static list or fetching from market_data collection
    try:
         # Example: fetch unique symbols from historical or market_data
         # This is a placeholder list based on common HFT pairs
         return ["BTC", "ETH", "BNB", "SOL", "ADA", "XRP", "DOGE"]
    except Exception:
        return ["BTC", "ETH"]

# --- Routes ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/dashboard-data')
def dashboard_data():
    data = get_wallet_data()
    return jsonify(data)

@app.route('/pairs')
def pairs():
    return render_template('pairs.html')

@app.route('/api/pairs-data')
def pairs_data_api():
    signals = get_pairs_data()
    return jsonify({"signals": signals})

@app.route('/simulator')
def simulator():
    assets = get_active_assets()
    return render_template('simulator.html', assets=assets)

@app.route('/api/run-simulation', methods=['POST'])
def run_simulation():
    """Proxy request to the Simulator Service"""
    try:
        data = request.json
        # Forward to Simulator Microservice
        # In Docker network: http://simulator:5000/run
        # Fallback to direct calculation if local
        simulator_url = "http://simulator:5000/run"
        try:
            resp = requests.post(simulator_url, json=data, timeout=30)
            return jsonify(resp.json())
        except requests.exceptions.RequestException:
             # Fallback MOCK if service unreachable (for dev/demo)
            return jsonify({
                "status": "success",
                "results": {
                    "capital_final": round(data['capital'] * 1.02, 2),
                    "retorno_total_pct": 2.0,
                    "win_rate_pct": 60,
                    "total_operaciones": 15,
                    "operaciones_ganadoras": 9
                },
                "explanation": {
                    "que_significa": "MOCK RESULT (Simulator Service Unreachable). Ensure container is running."
                }
            })
    except Exception as e:
        logger.error(f"Simulation error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/run-pairs-backtest', methods=['POST'])
def run_pairs_backtest():
    """Proxy request to Pairs Trading Service Backtester"""
    try:
        data = request.json
        # Forward to Pairs Microservice
        pairs_url = "http://pairs:5000/backtest"
        try:
            resp = requests.post(pairs_url, json=data, timeout=60) # Long timeout for backtest
            return jsonify(resp.json())
        except requests.exceptions.RequestException as e:
            return jsonify({"status": "error", "message": f"Pairs Service Unreachable: {e}"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/asset/<symbol>')
def asset_detail(symbol):
    # Fetch asset specific data
    data = {
        "price": 0, "change": 0, "high": 0, "low": 0
    }
    signals = []
    
    try:
        # 1. Get latest price from market_data (or price cache)
        # 2. Get recent signals for this symbol
        sig_docs = db.collection('signals').where('symbol', '==', symbol).order_by('timestamp', direction=firestore.Query.DESCENDING).limit(10).stream()
        for doc in sig_docs:
            d = doc.to_dict()
            signals.append({
                "signal": d.get('signal'),
                "price": d.get('price'),
                "reason": d.get('reason', 'N/A'),
                "timestamp": d.get('timestamp').strftime('%Y-%m-%d %H:%M:%S') if d.get('timestamp') else ''
            })
            
        # Mock market data for UI display if real data fetch is complex here
        # In prod, query a 'prices' collection
        data["price"] = 0 # Placeholder
        
    except Exception as e:
        logger.error(f"Error fetching asset detail for {symbol}: {e}")

    return render_template('asset.html', symbol=symbol, data=data, signals=signals)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8050, debug=True)
