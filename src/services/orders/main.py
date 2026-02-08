import time
import json
import logging
from datetime import datetime
from src.config.settings import config
from src.shared.utils import get_logger, normalize_symbol  # Keep for backward compat
from src.domain import TradingSymbol  # V21.3: Value Object
from src.shared.memory import memory
from src.shared.database import init_db, SessionLocal, Trade, Wallet

logger = get_logger("OrdersSvcV21.3")

# Inicializar Base de Datos
init_db()

# V21.2: Usar configuración centralizada (NO hard-coded values)
MAX_OPEN_POSITIONS = config.MAX_OPEN_POSITIONS  # 2 (desde settings.py)
TRADE_AMOUNT_USD = config.TRADE_AMOUNT

def initialize_wallet():
    """Inicializa la wallet si no existe"""
    session = SessionLocal()
    try:
        wallet = session.query(Wallet).first()
        if not wallet:
            wallet = Wallet(
                usdt_balance=config.INITIAL_CAPITAL,
                total_equity=config.INITIAL_CAPITAL,
                last_updated=datetime.utcnow()
            )
            session.add(wallet)
            session.commit()
            logger.info(f"💰 Wallet inicializada: ${config.INITIAL_CAPITAL}")
    except Exception as e:
        logger.error(f"Error inicializando wallet: {e}")
        session.rollback()
    finally:
        session.close()

def get_wallet():
    """Obtiene el estado actual de la wallet"""
    session = SessionLocal()
    try:
        wallet = session.query(Wallet).order_by(Wallet.last_updated.desc()).first()
        return wallet
    finally:
        session.close()

def update_wallet(usdt_balance, total_equity):
    """Actualiza el balance de la wallet"""
    session = SessionLocal()
    try:
        wallet = session.query(Wallet).order_by(Wallet.last_updated.desc()).first()
        if wallet:
            wallet.usdt_balance = usdt_balance
            wallet.total_equity = total_equity
            wallet.last_updated = datetime.utcnow()
            session.commit()
    except Exception as e:
        logger.error(f"Error actualizando wallet: {e}")
        session.rollback()
    finally:
        session.close()

def get_open_positions_count():
    """Cuenta posiciones abiertas"""
    session = SessionLocal()
    try:
        count = session.query(Trade).filter(Trade.status == 'OPEN').count()
        return count
    finally:
        session.close()

def stop_loss_worker():
    """
    V21.3: Worker que verifica stop loss cada 30 segundos (Value Object Pattern).
    Cierra automáticamente posiciones con pérdida > -2%
    """
    import time
    
    logger.info("🛡️ Stop Loss Worker V21.3 (Canonical Core) iniciado (check cada 30s)")
    
    while True:
        try:
            time.sleep(30)  # Check cada 30 segundos
            
            session = SessionLocal()
            try:
                # Buscar posiciones abiertas
                open_trades = session.query(Trade).filter(Trade.status == 'OPEN').all()
                
                if not open_trades:
                    continue
                
                # Verificar cada posición
                for trade in open_trades:
                    try:
                        # V21.3: Parse to TradingSymbol (validates automatically)
                        symbol = TradingSymbol.from_str(trade.symbol)
                        current_price_key = symbol.to_redis_key("price")  # "price:BTC"
                        
                        # Obtener precio actual desde Redis (formato OHLCV)
                        price_data = memory.get(current_price_key)
                        
                        if not price_data:
                            logger.warning(f"⚠️ Stop Loss: No se encontró precio para {symbol} (key: {current_price_key})")
                            continue
                        
                        # V21.2: Manejar formato OHLCV
                        if isinstance(price_data, dict):
                            current_price = float(price_data.get('close') or price_data.get('price') or 0)
                        else:
                            current_price = float(price_data)
                        
                        if current_price <= 0:
                            logger.warning(f"⚠️ Stop Loss: Precio inválido para {trade.symbol}: {current_price}")
                            continue
                        
                        # Calcular PnL %
                        pnl_pct = ((current_price - trade.entry_price) / trade.entry_price) * 100
                        
                        # Trigger stop loss si pérdida > threshold
                        if pnl_pct <= -config.STOP_LOSS_PCT:
                            logger.warning(f"🛑 STOP LOSS TRIGGERED: {symbol_normalized} @ ${current_price:.2f} (PnL: {pnl_pct:.1f}%)")
                            
                            # Ejecutar venta forzada - publicar señal de SELL en Redis
                            stop_loss_signal = {
                                "symbol": symbol_normalized,  # V21.2: Normalizado
                                "type": "SELL",
                                "price": current_price,
                                "timestamp": datetime.utcnow().isoformat(),
                                "reason": f"STOP_LOSS triggered (PnL: {pnl_pct:.1f}%)",
                                "force": True  # Flag para indicar venta forzada
                            }
                            
                            memory.publish('signals', stop_loss_signal)
                            logger.info(f"📤 Stop loss signal published for {symbol_normalized}")
                    
                    except ValueError as e:
                        logger.error(f"❌ Error normalizando símbolo '{trade.symbol}': {e}")
                        continue
                    except Exception as e:
                        logger.error(f"❌ Error procesando trade {trade.id}: {e}")
                        continue
                        
            except Exception as e:
                logger.error(f"Error en stop loss worker: {e}")
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error crítico en stop loss worker: {e}")
            time.sleep(60)  # Esperar más si hay error crítico

def find_open_position(symbol):
    """Busca una posición abierta para un símbolo"""
    session = SessionLocal()
    try:
        trade = session.query(Trade).filter(
            Trade.symbol == symbol,
            Trade.status == 'OPEN'
        ).first()
        return trade
    finally:
        session.close()

def execute_buy(signal):
    """Ejecuta una orden de compra (abre posición)"""
    session = SessionLocal()
    try:
        # Verificar límite de posiciones
        open_count = get_open_positions_count()
        if open_count >= MAX_OPEN_POSITIONS:
            logger.warning(f"⚠️ Max positions reached ({MAX_OPEN_POSITIONS}). Skipping BUY {signal['symbol']}")
            return
        
        # Verificar balance
        wallet = get_wallet()
        if not wallet or wallet.usdt_balance < TRADE_AMOUNT_USD:
            logger.warning(f"⚠️ Insufficient balance. Need ${TRADE_AMOUNT_USD}, have ${wallet.usdt_balance if wallet else 0}")
            return
        
        price = float(signal.get('price', 0))
        if price <= 0:
            logger.warning(f"⚠️ Invalid price: {price}")
            return
        
        # V19: Aplicar comisión al comprar (Binance fees)
        net_amount_to_invest = TRADE_AMOUNT_USD * (1 - config.COMMISSION_RATE)
        amount = net_amount_to_invest / price
        commission_paid = TRADE_AMOUNT_USD * config.COMMISSION_RATE
        
        # Crear trade
        trade = Trade(
            symbol=signal['symbol'],
            side='LONG',
            amount=amount,
            entry_price=price,
            status='OPEN',
            timestamp=datetime.utcnow()
        )
        session.add(trade)
        
        # Actualizar balance
        new_balance = wallet.usdt_balance - TRADE_AMOUNT_USD
        update_wallet(new_balance, wallet.total_equity)
        
        session.commit()
        logger.info(f"🚀 BUY EXECUTED: {signal['symbol']} | Amount: {amount:.6f} | Price: ${price:.2f} | Cost: ${TRADE_AMOUNT_USD}")
        
    except Exception as e:
        logger.error(f"❌ Error executing BUY: {e}")
        session.rollback()
    finally:
        session.close()

def execute_sell(signal):
    """Ejecuta una orden de venta (cierra posición)"""
    session = SessionLocal()
    try:
        # Buscar posición abierta
        symbol = signal['symbol']
        trade = session.query(Trade).filter(
            Trade.symbol == symbol,
            Trade.status == 'OPEN'
        ).first()
        
        if not trade:
            logger.warning(f"⚠️ No open position found for {symbol}")
            return
        
        exit_price = float(signal.get('price', 0))
        if exit_price <= 0:
            logger.warning(f"⚠️ Invalid exit price: {exit_price}")
            return
        
        # V19: Calcular PnL con comisión al vender
        gross_exit_value = trade.amount * exit_price
        commission_on_exit = gross_exit_value * config.COMMISSION_RATE
        net_exit_value = gross_exit_value - commission_on_exit
        entry_value = trade.amount * trade.entry_price
        pnl = net_exit_value - entry_value
        
        # Cerrar trade
        trade.exit_price = exit_price
        trade.pnl = pnl
        trade.status = 'CLOSED'
        
        # Actualizar balance
        wallet = get_wallet()
        if wallet:
            new_balance = wallet.usdt_balance + net_exit_value
            new_equity = wallet.total_equity + pnl
            update_wallet(new_balance, new_equity)
        
        session.commit()
        
        roe = (pnl / entry_value * 100) if entry_value > 0 else 0
        logger.info(f"💰 SELL EXECUTED: {symbol} | PnL: ${pnl:.2f} ({roe:.2f}%) | Exit: ${exit_price:.2f} | Fee: ${commission_on_exit:.2f} | Net: ${net_exit_value:.2f}")
        
    except Exception as e:
        logger.error(f"❌ Error executing SELL: {e}")
        session.rollback()
    finally:
        session.close()

def process_signal(message):
    """Procesa señales de trading del canal Redis"""
    try:
        data = json.loads(message['data'])
        signal_type = data.get('type', '').upper()
        symbol = data.get('symbol', '')
        
        if not signal_type or not symbol:
            logger.warning(f"⚠️ Invalid signal format: {data}")
            return
        
        logger.info(f"📨 Signal received: {signal_type} {symbol}")
        
        if signal_type == 'BUY':
            execute_buy(data)
        elif signal_type == 'SELL':
            execute_sell(data)
        else:
            logger.warning(f"⚠️ Unknown signal type: {signal_type}")
            
    except Exception as e:
        logger.error(f"❌ Error processing signal: {e}")

def main():
    logger.info("🚀 Orders Service V19 (Redis + SQLite + Commissions) INICIADO")
    
    # Inicializar wallet
    initialize_wallet()
    
    # Conectar a Redis
    redis_conn = memory.get_client()
    if not redis_conn:
        logger.critical("🔥 No se pudo conectar a Redis. Reintentando...")
        time.sleep(5)
        return
    
    pubsub = redis_conn.pubsub()
    pubsub.subscribe('signals')
    
    logger.info("✅ Suscrito al canal 'signals'. Esperando señales de trading...")
    
    for message in pubsub.listen():
        if message['type'] == 'message':
            process_signal(message)

if __name__ == '__main__':
    time.sleep(5)  # Esperar a que otros servicios inicien
    while True:
        try:
            main()
        except Exception as e:
            logger.error(f"❌ Crash en loop principal: {e}")
            time.sleep(5)
