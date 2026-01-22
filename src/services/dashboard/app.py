from flask import Flask, render_template
from google.cloud import firestore
from src.config.settings import config
from src.shared.utils import get_logger

logger = get_logger("Dashboard")
app = Flask(__name__)
db = firestore.Client(project=config.PROJECT_ID)

@app.route('/')
def index():
    # Lógica de Wallet (Resumida para V14)
    wallet = {"usdt_balance": config.INITIAL_CAPITAL, "total_equity": config.INITIAL_CAPITAL, "positions": []}
    try:
        w_doc = db.collection('wallet').document('main_account').get()
        if w_doc.exists:
            wd = w_doc.to_dict()
            wallet['usdt_balance'] = wd.get('usdt_balance', 0)
            
        pos_docs = db.collection('portfolio').stream()
        equity = wallet['usdt_balance']
        for p in pos_docs:
            pd = p.to_dict()
            val = pd.get('amount',0) * pd.get('current_price',0)
            if pd.get('type') == 'LONG': equity += val
            wallet['positions'].append({
                "type": pd.get('type'), "symbol": pd.get('symbol'),
                "amount": round(pd.get('amount'),4), "current_price": round(pd.get('current_price'),2),
                "value": round(val,2)
            })
        wallet['total_equity'] = round(equity, 2)
    except Exception as e:
        logger.error(f"DB Error: {e}")
    return render_template('index.html', wallet=wallet)

@app.route('/pairs')
def pairs():
    # Aquí podrías consultar la colección 'pairs_status' de Firestore
    return render_template('pairs.html')

@app.route('/simulator')
def simulator():
    return render_template('simulator.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8050, debug=True)
