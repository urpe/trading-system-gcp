import random
import time
from flask import Flask, request, jsonify
from google.cloud import firestore
from google.api_core import exceptions
from src.config.settings import config
from src.shared.utils import get_logger

logger = get_logger("PortfolioSvc")
app = Flask(__name__)
db = firestore.Client(project=config.PROJECT_ID)

@app.route('/update', methods=['POST'])
def update_position():
    try:
        data = request.json
        # Algoritmo de reintento "Full Jitter" para evitar colisiones DB
        for i in range(5):
            try:
                transaction = db.transaction()
                res = execute_atomic_trade(transaction, data)
                logger.info(f"✅ Committed: {data['side']} {data['symbol']} | Qty: {res}")
                return jsonify({"status": "success", "new_amount": res}), 200
            except exceptions.Conflict:
                wait = (0.1 * (2 ** i)) + random.uniform(0, 0.05)
                logger.warning(f"⚠️ DB Busy (Attempt {i+1}). Wait {wait:.2f}s")
                time.sleep(wait)
        
        return jsonify({"error": "DB Locked"}), 429
    except Exception as e:
        logger.error(f"❌ Critical: {e}")
        return jsonify({"error": str(e)}), 500

@firestore.transactional
def execute_atomic_trade(transaction, data):
    # --- LOGICA DE NEGOCIO PURA ---
    w_ref = db.collection('wallet').document('main_account')
    p_ref = db.collection('portfolio').document(data['symbol'])
    
    w_snap = w_ref.get(transaction=transaction)
    p_snap = p_ref.get(transaction=transaction)
    
    usdt = w_snap.get('usdt_balance') if w_snap.exists else config.INITIAL_CAPITAL
    
    curr_amt = 0.0
    if p_snap.exists:
        curr_amt = float(p_snap.to_dict().get('amount', 0.0))
    
    price = float(data['price'])
    amount = float(data['amount'])
    cost = price * amount
    
    new_usdt = usdt
    new_amt = curr_amt
    
    if data['side'] == 'BUY':
        if curr_amt >= 0: # Long opening or adding
            if usdt < cost: raise ValueError("Insufficient Funds")
            new_usdt -= cost
        else: # Short closing
            new_usdt -= cost
        new_amt += amount
        
    elif data['side'] == 'SELL':
        new_usdt += cost
        new_amt -= amount

    transaction.set(w_ref, {'usdt_balance': new_usdt}, merge=True)
    
    if abs(new_amt) < 1e-5:
        transaction.delete(p_ref)
        return 0.0
    else:
        transaction.set(p_ref, {
            'symbol': data['symbol'],
            'amount': new_amt,
            'current_price': price,
            'avg_price': price, # Simplificación V13
            'type': 'SHORT' if new_amt < 0 else 'LONG',
            'timestamp': firestore.SERVER_TIMESTAMP
        }, merge=True)
        return new_amt

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, threaded=True)
