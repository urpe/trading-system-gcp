from flask import Flask, render_template, jsonify, request, send_file
from src.config.settings import config
from src.config.symbols import ACTIVE_SYMBOLS, FALLBACK_SYMBOLS, DEFAULT_SYMBOLS_LOWER
from src.shared.utils import get_logger, normalize_symbol  # Keep for backward compat
from src.domain import TradingSymbol, parse_symbol_list  # V21.3: Value Object
from src.shared.memory import memory # Redis Client
from src.shared.database import SessionLocal, Signal, Trade, Wallet, PairsSignal # Local DB
import requests
import json
from datetime import datetime, timedelta
from openpyxl import Workbook
from io import BytesIO

logger = get_logger("DashboardV21.3")
app = Flask(__name__)

# --- Helper Functions ---

def get_realtime_price(symbol_str):
    """
    V21.3: Fetch realtime price from Redis usando TradingSymbol Value Object.
    
    Args:
        symbol_str: Símbolo en cualquier formato (será parseado a TradingSymbol)
    
    Returns:
        float: Precio actual o 0 si no se encuentra
    """
    try:
        # V21.3: Parse to TradingSymbol (validates automatically)
        symbol = TradingSymbol.from_str(symbol_str)
        key = symbol.to_redis_key("price")  # "price:BTC"
        
        data = memory.get(key)
        
        if data and isinstance(data, dict):
            # V21: Priorizar 'close' sobre 'price' (formato OHLCV)
            price = data.get('close') or data.get('price')
            if price:
                return float(price)
            else:
                logger.warning(f"⚠️ Dashboard: Redis key '{key}' exists but has no price/close field: {data}")
                return 0
        else:
            # V21.2: NO masking silencioso - Log explícito de key miss
            logger.warning(f"⚠️ Dashboard Key Miss: '{key}' not found in Redis or not a dict (type: {type(data)})")
            return 0
    
    except (ValueError, TypeError) as e:
        logger.error(f"❌ Invalid symbol '{symbol_str}': {e}")
        return 0
    except Exception as e:
        logger.error(f"❌ Redis Error get_realtime_price({symbol_str}): {e}")
        return 0

def get_active_symbols():
    """
    V21.2.1: Fetch Top 5 Monitored Symbols from Redis con fallback a canonical source.
    """
    try:
        data = memory.get("active_symbols")
        if data and isinstance(data, list):
            return data
    except Exception as e:
        logger.error(f"Redis Error get_active_symbols: {e}")
    
    # V21.2.1: Usar canonical source (NO magic strings)
    return DEFAULT_SYMBOLS_LOWER

def get_wallet_data():
    """Fetch wallet data from Local DB (SQLite)."""
    wallet = {
        "usdt_balance": config.INITIAL_CAPITAL, 
        "total_equity": config.INITIAL_CAPITAL, 
        "positions": []
    }
    
    session = SessionLocal()
    try:
        # Leer balance real de la tabla Wallet
        wallet_db = session.query(Wallet).order_by(Wallet.last_updated.desc()).first()
        if wallet_db:
            wallet['usdt_balance'] = wallet_db.usdt_balance
            wallet['total_equity'] = wallet_db.total_equity
        
        # Obtener posiciones abiertas
        trades = session.query(Trade).filter(Trade.status == 'OPEN').all()
        
        for t in trades:
            current_price = get_realtime_price(t.symbol)
            if current_price == 0: current_price = t.entry_price
            
            val = t.amount * current_price
            
            wallet['positions'].append({
                "type": t.side,
                "symbol": t.symbol,
                "amount": round(t.amount, 4),
                "current_price": round(current_price, 2),
                "value": round(val, 2),
                "entry_price": round(t.entry_price, 2),
                "pnl": round(val - (t.amount * t.entry_price), 2)
            })
        
    except Exception as e:
        logger.error(f"❌ DB Error get_wallet_data: {e}")
    finally:
        session.close()
        
    return wallet

def get_signals_history(limit=20):
    """Fetch signals from Local SQLite DB."""
    signals = []
    session = SessionLocal()
    try:
        db_signals = session.query(Signal).order_by(Signal.timestamp.desc()).limit(limit).all()
        for s in db_signals:
            signals.append({
                "timestamp": s.timestamp.strftime('%H:%M:%S'),
                "symbol": s.symbol,
                "signal": s.signal_type,
                "price": s.price,
                "reason": s.reason,
                "status": s.status
            })
    except Exception as e:
        logger.error(f"DB Error get_signals_history: {e}")
    finally:
        session.close()
    return signals

def get_active_assets():
    """
    V21.2.1: Retorna símbolos activos en formato corto desde canonical source.
    """
    return ACTIVE_SYMBOLS  # V21.2.1: Canonical source

def get_market_regimes():
    """
    V21.3: Obtiene los regímenes de mercado desde Redis usando TradingSymbol.
    
    Returns:
        Dict con regímenes por símbolo activo
    """
    regimes = {}
    
    try:
        # Obtener símbolos activos
        active_symbols_raw = get_active_symbols()
        
        for symbol_raw in active_symbols_raw:
            try:
                # V21.3: Parse to TradingSymbol
                symbol = TradingSymbol.from_str(symbol_raw)
                
                # Leer régimen desde Redis
                key = symbol.to_redis_key("market_regime")  # "market_regime:BTC"
                regime_json = memory.get_client().get(key)
                
                if regime_json:
                    regime_data = json.loads(regime_json)
                    
                    regimes[symbol.to_short()] = {
                        'regime': regime_data.get('regime', 'unknown'),
                        'adx': regime_data.get('indicators', {}).get('adx', 0),
                        'ema_200': regime_data.get('indicators', {}).get('ema_200', 0),
                        'atr_percent': regime_data.get('indicators', {}).get('atr_percent', 0),
                        'timestamp': regime_data.get('timestamp', '')
                    }
                else:
                    # V21.2: Log explícito de key miss
                    logger.warning(f"⚠️ Dashboard: Régimen no encontrado para {symbol} (key: {key})")
                    regimes[symbol.to_short()] = {
                        'regime': 'no_data',
                        'adx': 0,
                        'ema_200': 0,
                        'atr_percent': 0,
                        'timestamp': ''
                    }
            
            except (ValueError, TypeError) as e:
                logger.error(f"❌ Invalid symbol '{symbol_raw}': {e}")
                continue
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo regímenes de mercado: {e}")
    
    return regimes

# --- Routes ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/dashboard-data')
def dashboard_data():
    """
    V21.2: Endpoint principal con símbolos ya normalizados para el frontend.
    """
    data = get_wallet_data()
    
    # V21.2: Normalizar active_symbols antes de enviar al frontend
    active_symbols_raw = get_active_symbols()
    data['scanner'] = []
    
    for symbol_raw in active_symbols_raw:
        try:
            symbol_normalized = normalize_symbol(symbol_raw, format='short')
            data['scanner'].append(symbol_normalized)
        except ValueError as e:
            logger.error(f"❌ Error normalizando símbolo en scanner: {symbol_raw}: {e}")
    
    data['regimes'] = get_market_regimes()
    return jsonify(data)

@app.route('/api/market-regimes')
def market_regimes_api():
    """
    V21 EAGLE EYE: Endpoint para obtener regímenes de mercado en tiempo real.
    
    Response:
    {
        "BTC": {
            "regime": "sideways_range",
            "adx": 9.48,
            "ema_200": 76516.26,
            "atr_percent": 0.06
        },
        ...
    }
    """
    return jsonify(get_market_regimes())

@app.route('/pairs')
def pairs():
    return render_template('pairs.html')

@app.route('/api/pairs-data')
def pairs_data_api():
    session = SessionLocal()
    try:
        signals = session.query(PairsSignal).order_by(PairsSignal.timestamp.desc()).limit(20).all()
        data = [{
            "timestamp": s.timestamp.strftime('%H:%M:%S'),
            "symbol": f"{s.asset_a}-{s.asset_b}",
            "signal": s.signal,
            "correlation": round(s.correlation, 2),
            "z_score": round(s.z_score, 2),
            "status": s.status
        } for s in signals]
        return jsonify({"signals": data})
    except Exception as e:
        logger.error(f"Error fetching pairs data: {e}")
        return jsonify({"signals": []})
    finally:
        session.close()

@app.route('/api/export-trades')
def export_trades():
    """Exporta trades a Excel con métricas de rentabilidad"""
    symbol = request.args.get('symbol')  # Opcional: filtrar por símbolo
    days = int(request.args.get('days', 7))  # Default: última semana
    
    session = SessionLocal()
    try:
        query = session.query(Trade)
        
        if symbol:
            query = query.filter(Trade.symbol == symbol)
        
        # Filtrar por fecha
        since = datetime.utcnow() - timedelta(days=days)
        query = query.filter(Trade.timestamp >= since)
        
        trades = query.order_by(Trade.timestamp.desc()).all()
        
        # Crear Excel
        wb = Workbook()
        ws = wb.active
        ws.title = "Trading Report"
        
        # Headers
        headers = ["Timestamp", "Symbol", "Side", "Amount", "Entry Price", "Exit Price", "PnL", "Status", "ROE %"]
        ws.append(headers)
        
        # Data
        for t in trades:
            roe = (t.pnl / (t.amount * t.entry_price) * 100) if t.exit_price and t.amount * t.entry_price > 0 else 0
            ws.append([
                t.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                t.symbol,
                t.side,
                round(t.amount, 6),
                round(t.entry_price, 2),
                round(t.exit_price, 2) if t.exit_price else 'N/A',
                round(t.pnl, 2) if t.pnl else 0,
                t.status,
                round(roe, 2)
            ])
        
        # Añadir métricas al final
        ws.append([])
        ws.append(["SUMMARY METRICS"])
        
        closed_trades = [t for t in trades if t.status == 'CLOSED']
        total_pnl = sum(t.pnl for t in closed_trades if t.pnl)
        winning_trades = len([t for t in closed_trades if t.pnl and t.pnl > 0])
        win_rate = (winning_trades / len(closed_trades) * 100) if closed_trades else 0
        
        ws.append(["Total Trades", len(trades)])
        ws.append(["Closed Trades", len(closed_trades)])
        ws.append(["Win Rate", f"{win_rate:.2f}%"])
        ws.append(["Total PnL", f"${total_pnl:.2f}"])
        
        # Guardar en memoria
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        
        filename = f"trading_report_{symbol or 'all'}_{days}d.xlsx"
        return send_file(output, download_name=filename, as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    
    except Exception as e:
        logger.error(f"Error exporting trades: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()

@app.route('/simulator')
def simulator():
    assets = get_active_assets()
    return render_template('simulator.html', assets=assets)

@app.route('/api/run-simulation', methods=['POST'])
def run_simulation():
    """Proxy endpoint para el Simulator Service"""
    try:
        data = request.json
        simulator_url = f"{config.SVC_SIMULATOR}/run"
        resp = requests.post(simulator_url, json=data, timeout=60)
        return jsonify(resp.json()), resp.status_code
    except requests.exceptions.RequestException as e:
        logger.error(f"Simulator connection error: {e}")
        return jsonify({"status": "error", "message": f"Simulator unreachable: {str(e)}"}), 503
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/run-pairs-backtest', methods=['POST'])
def run_pairs_backtest():
    """Proxy endpoint para Pairs Backtesting"""
    try:
        data = request.json
        pairs_url = "http://pairs:5000/backtest"
        resp = requests.post(pairs_url, json=data, timeout=60)
        return jsonify(resp.json()), resp.status_code
    except requests.exceptions.RequestException as e:
        logger.error(f"Pairs connection error: {e}")
        return jsonify({"status": "error", "message": f"Pairs Service Unreachable: {str(e)}"}), 503
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/asset/<symbol>')
def asset_detail(symbol):
    """
    V21.2: Vista de detalle de un asset con normalización y logging mejorado.
    
    Args:
        symbol: Símbolo del asset (ej: "ETH", "eth", "ethusdt")
    
    Returns:
        Página HTML con datos del asset o mensaje de error
    """
    # V21.2: Normalizar símbolo primero
    try:
        symbol_normalized = normalize_symbol(symbol, format='short')
    except ValueError as e:
        logger.error(f"❌ Símbolo inválido en /asset/{symbol}: {e}")
        return render_template('asset.html', symbol=symbol, 
                              data={"price": 0.0, "change": 0.0, "high": 0.0, "low": 0.0}, 
                              signals=[], 
                              error=f"Símbolo inválido: {symbol}")
    
    # Default values
    data = {"price": 0.0, "change": 0.0, "high": 0.0, "low": 0.0}
    signals = []
    
    # 1. Redis Realtime Data (V21 OHLCV compatible)
    try:
        key = f"price:{symbol_normalized}"
        ticker = memory.get(key)
        
        if ticker and isinstance(ticker, dict):
            # V21: OHLCV format - priorizar 'close' sobre 'price'
            data = {
                "price": float(ticker.get('close') or ticker.get('price') or 0.0),
                "change": float(ticker.get('change') or 0.0),
                "high": float(ticker.get('high') or 0.0),
                "low": float(ticker.get('low') or 0.0)
            }
        else:
            # V21.2: NO masking - Log explícito de key miss
            logger.warning(f"⚠️ Dashboard /asset/{symbol}: Key '{key}' not found or invalid type (type: {type(ticker)})")
    
    except (TypeError, ValueError) as e:
        logger.warning(f"⚠️ Error parsing Redis data for {symbol_normalized}: {e}")
    except Exception as e:
        logger.error(f"❌ Redis error for {symbol_normalized}: {e}")

    # 2. SQLite Signals History
    session = SessionLocal()
    try:
        db_signals = session.query(Signal).filter(
            Signal.symbol == symbol_normalized
        ).order_by(Signal.timestamp.desc()).limit(20).all()
        
        for s in db_signals:
            if s and s.signal_type and s.price:
                signals.append({
                    "signal": s.signal_type,
                    "price": float(s.price) if s.price else 0.0,
                    "reason": s.reason or "N/A",
                    "timestamp": s.timestamp.strftime('%Y-%m-%d %H:%M:%S') if s.timestamp else "N/A"
                })
    except Exception as e:
        logger.error(f"❌ Error fetching signals for {symbol_normalized}: {e}")
    finally:
        session.close()

    return render_template('asset.html', symbol=symbol_normalized, data=data, signals=signals)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8050, debug=True)
