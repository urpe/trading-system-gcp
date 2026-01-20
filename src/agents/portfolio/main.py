import os
from flask import Flask, jsonify, request
from google.cloud import firestore
from datetime import datetime
import logging

app = Flask(__name__)

# Configuración de Logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('PortfolioAgent')

PROJECT_ID = os.environ.get("PROJECT_ID", "mi-proyecto-trading-12345")
db = firestore.Client(project=PROJECT_ID)

# --- CONFIGURACIÓN DE TRADING (NUEVO) ---
ALLOW_SHORT = True  # <--- ✅ HABILITADO PARA GANAR EN CAÍDAS
MAX_POSITION_SIZE = 2000

# --- CONFIGURACIÓN DE MERCADO (TU CÓDIGO ORIGINAL) ---
FIXED_ASSETS = ['BTC', 'ETH', 'SOL', 'BNB']
UNIVERSE = [
    'BTC', 'ETH', 'BNB', 'SOL', 'XRP', 'ADA', 'DOGE', 'AVAX', 'DOT', 'MATIC',
    'LINK', 'LTC', 'ATOM', 'UNI', 'ETC', 'XLM', 'NEAR', 'APT', 'FIL', 'ARB',
    'OP', 'INJ', 'SUI', 'SEI', 'TIA', 'RUNE', 'FTM', 'AAVE', 'MKR', 'SNX',
    'LDO', 'RNDR', 'GRT', 'IMX', 'SAND', 'MANA', 'AXS', 'APE', 'GMT', 'GALA',
    'CHZ', 'ENJ', 'FLOW', 'KAVA', 'ALGO', 'VET', 'ICP', 'HBAR', 'QNT', 'EGLD'
]

@app.route('/')
def health():
    return "Portfolio Manager v10.0 (Shorting Enabled) Running"

# ==========================================
# 🧠 SECCIÓN 1: CONTABILIDAD Y EJECUCIÓN (NUEVO)
# ==========================================

@app.route('/update', methods=['POST'])
def update_position():
    """Ejecuta la compra/venta real y maneja el dinero"""
    try:
        data = request.json
        symbol = data['symbol']
        side = data['side'] # 'BUY' o 'SELL'
        price = float(data['price'])
        amount = float(data['amount'])
        
        wallet_ref = db.collection('wallet').document('main_account')
        portfolio_ref = db.collection('portfolio').document(symbol)
        
        @firestore.transactional
        def execute_trade(transaction, wallet_doc, portfolio_doc):
            # 1. Leer Billetera
            wallet = wallet_doc.get(transaction).to_dict() or {'usdt_balance': 10000}
            usdt_balance = wallet.get('usdt_balance', 10000)
            
            # 2. Leer Posición Actual
            snapshot = portfolio_doc.get(transaction)
            current_pos = snapshot.to_dict() if snapshot.exists else {'amount': 0.0, 'avg_price': 0.0}
            
            curr_amt = float(current_pos.get('amount', 0.0))
            curr_avg = float(current_pos.get('avg_price', 0.0))
            
            cost = price * amount
            new_usdt = usdt_balance
            new_amt = curr_amt
            new_avg = curr_avg
            
            # --- LÓGICA DE TRADING ---
            if side == 'BUY':
                # Si estamos en Short (negativo), comprar reduce la deuda (Cerrar Short)
                # Si estamos en 0 o Long, comprar requiere USDT
                if curr_amt >= 0: 
                    if usdt_balance < cost:
                        raise Exception("Saldo insuficiente para comprar")
                    new_usdt -= cost
                else: # Cubriendo Short
                    new_usdt -= cost # Pagamos deuda con USDT
                
                # Promedio Ponderado
                if curr_amt >= 0:
                    total_val = (curr_amt * curr_avg) + cost
                    new_amt += amount
                    new_avg = total_val / new_amt if new_amt != 0 else 0
                else:
                    new_amt += amount # Nos acercamos a 0

            elif side == 'SELL':
                # Si no permitimos short y no tenemos monedas -> Error
                if not ALLOW_SHORT and curr_amt < amount:
                    raise Exception(f"No tienes suficientes {symbol} para vender (Spot Only).")
                
                # Al vender recibimos cash (incluso si entramos en negativo/short)
                new_usdt += cost
                new_amt -= amount
                
                # Lógica de Precio Promedio para Shorts
                if curr_amt <= 0: # Ya estábamos short o estamos entrando
                    if curr_amt == 0:
                        new_avg = price # Precio de entrada del short
                    elif new_amt < curr_amt: # Aumentando short
                        total_val = (abs(curr_amt) * curr_avg) + cost
                        new_avg = total_val / abs(new_amt)

            # 3. Guardar
            transaction.set(wallet_ref, {'usdt_balance': new_usdt}, merge=True)
            transaction.set(portfolio_ref, {
                'amount': new_amt,
                'avg_price': new_avg,
                'current_price': price,
                'symbol': symbol,
                'type': 'SHORT' if new_amt < 0 else 'LONG',
                'timestamp': firestore.SERVER_TIMESTAMP
            })
            return new_amt

        transaction = db.transaction()
        new_pos = execute_trade(transaction, wallet_ref, portfolio_ref)
        
        logger.info(f"✅ Trade Ejecutado: {side} {symbol} | Nueva Posición: {new_pos}")
        return jsonify({"status": "success", "new_amount": new_pos}), 200

    except Exception as e:
        logger.error(f"❌ Error Trade: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/balance', methods=['GET'])
def get_balance():
    try:
        doc = db.collection('wallet').document('main_account').get()
        return jsonify(doc.to_dict() if doc.exists else {'usdt_balance': 10000}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==========================================
# 📊 SECCIÓN 2: ANÁLISIS Y RANKINGS (TU CÓDIGO ORIGINAL)
# ==========================================

@app.route('/portfolio', methods=['GET'])
def get_portfolio_analysis():
    """Calcula la asignación ideal basada en el universo"""
    market_data = {}
    for symbol in UNIVERSE:
        doc = db.collection('market_data').document(symbol).get()
        if doc.exists:
            market_data[symbol] = doc.to_dict()
    
    candidates = {k: v for k, v in market_data.items() if k not in FIXED_ASSETS}
    sorted_by_change = sorted(candidates.items(), key=lambda x: x[1].get('change', 0), reverse=True)
    variable_assets = [item[0] for item in sorted_by_change[:2]]
    
    portfolio = {
        "timestamp": datetime.now().isoformat(),
        "fixed_assets": {
            "symbols": FIXED_ASSETS,
            "allocation_pct": 60,
            "strategy": "Buy & Hold"
        },
        "variable_assets": {
            "symbols": variable_assets,
            "allocation_pct": 40,
            "strategy": "Active Trading"
        },
        "active_monitoring": len(market_data)
    }
    return jsonify(portfolio)

@app.route('/rankings', methods=['GET'])
def get_rankings():
    market_data = {}
    for symbol in UNIVERSE:
        doc = db.collection('market_data').document(symbol).get()
        if doc.exists:
            market_data[symbol] = doc.to_dict()
    
    gainers = sorted(market_data.items(), key=lambda x: x[1].get('change', 0), reverse=True)[:10]
    losers = sorted(market_data.items(), key=lambda x: x[1].get('change', 0))[:10]
    
    return jsonify({
        "top_gainers": [{"symbol": s, **d} for s, d in gainers],
        "top_losers": [{"symbol": s, **d} for s, d in losers]
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)