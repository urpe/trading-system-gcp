import time
import logging
import os
import threading
from datetime import datetime, timezone
from google.cloud import firestore

# Configuración Logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('OrdersAgent')

PROJECT_ID = os.environ.get("PROJECT_ID", "mi-proyecto-trading-12345")
db = firestore.Client(project=PROJECT_ID)

# --- CONFIGURACIÓN DE LA CUENTA VIRTUAL ---
INITIAL_CAPITAL = 10000.0  # 10,000 USDT para empezar
FEE_PERCENT = 0.001        # 0.1% de comisión

def initialize_wallet():
    """Crea la billetera si no existe"""
    wallet_ref = db.collection('wallet').document('main_account')
    doc = wallet_ref.get()
    if not doc.exists:
        logger.info(f"💰 Creando cuenta nueva con ${INITIAL_CAPITAL} USDT")
        wallet_ref.set({
            'usdt_balance': INITIAL_CAPITAL,
            'initial_capital': INITIAL_CAPITAL,
            'total_value': INITIAL_CAPITAL,
            'updated_at': firestore.SERVER_TIMESTAMP
        })

def execute_trade(signal_data):
    """Lógica principal de Compra/Venta"""
    symbol = signal_data['symbol']
    action = signal_data['type']
    price = float(signal_data['price'])
    reason = signal_data.get('reason', 'Signal')
    
    wallet_ref = db.collection('wallet').document('main_account')
    portfolio_ref = db.collection('portfolio').document(symbol)
    
    transaction = db.transaction()
    
    try:
        _execute_transaction(transaction, wallet_ref, portfolio_ref, action, price, symbol, reason)
        logger.info(f"✅ ORDEN EJECUTADA: {action} {symbol} a ${price}")
    except Exception as e:
        logger.error(f"❌ Fallo al ejecutar orden: {e}")

@firestore.transactional
def _execute_transaction(transaction, wallet_ref, portfolio_ref, action, price, symbol, reason):
    wallet = wallet_ref.get(transaction=transaction).to_dict()
    portfolio_doc = portfolio_ref.get(transaction=transaction)
    portfolio = portfolio_doc.to_dict() if portfolio_doc.exists else {'amount': 0.0, 'avg_price': 0.0}
    
    usdt_balance = wallet.get('usdt_balance', 0.0)
    current_qty = portfolio.get('amount', 0.0)
    
    if action == "BUY":
        invest_amount = usdt_balance * 0.20 # 20% del capital disponible
        
        if invest_amount < 10:
            raise Exception("Saldo insuficiente")
            
        fee = invest_amount * FEE_PERCENT
        net_invest = invest_amount - fee
        qty_bought = net_invest / price
        
        new_usdt = usdt_balance - invest_amount
        new_qty = current_qty + qty_bought
        # Precio promedio ponderado
        old_cost = current_qty * portfolio.get('avg_price', 0)
        new_avg = (old_cost + (qty_bought * price)) / new_qty
        
        transaction.update(wallet_ref, {'usdt_balance': round(new_usdt, 2)})
        transaction.set(portfolio_ref, {
            'symbol': symbol,
            'amount': new_qty,
            'avg_price': new_avg,
            'current_price': price,
            'timestamp': firestore.SERVER_TIMESTAMP
        })
        
    elif action == "SELL":
        if current_qty <= 0:
            raise Exception("No tienes monedas para vender")
            
        gross_return = current_qty * price
        fee = gross_return * FEE_PERCENT
        net_return = gross_return - fee
        
        new_usdt = usdt_balance + net_return
        
        # Calcular PNL
        buy_cost = current_qty * portfolio.get('avg_price', 0)
        pnl = net_return - buy_cost
        pnl_percent = (pnl / buy_cost) * 100 if buy_cost > 0 else 0
        
        transaction.update(wallet_ref, {'usdt_balance': round(new_usdt, 2)})
        transaction.delete(portfolio_ref)
        
        logger.info(f"💵 VENTA: PNL ${round(pnl, 2)} ({round(pnl_percent, 2)}%)")

def listen_for_signals():
    """Escucha la colección de señales en tiempo real"""
    # CORRECCIÓN: Usar hora local en lugar de SERVER_TIMESTAMP para el filtro
    now = datetime.now(timezone.utc)
    
    signals_ref = db.collection('signals').where('timestamp', '>', now)
    
    def on_snapshot(col_snapshot, changes, read_time):
        for change in changes:
            if change.type.name == 'ADDED':
                signal_data = change.document.to_dict()
                # Pequeño filtro para no procesar señales muy viejas
                logger.info(f"📩 Nueva señal recibida: {signal_data['type']} {signal_data['symbol']}")
                threading.Thread(target=execute_trade, args=(signal_data,)).start()

    signals_ref.on_snapshot(on_snapshot)
    
    while True:
        time.sleep(1)

if __name__ == '__main__':
    logger.info("👐 AGENTE DE ÓRDENES (Paper Trading) INICIADO")
    initialize_wallet()
    listen_for_signals()