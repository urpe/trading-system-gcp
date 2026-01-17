import logging
from google.cloud import firestore
import pandas as pd

logger = logging.getLogger('Optimizer')

class StrategyOptimizer:
    def __init__(self, db):
        self.db = db
        # Rangos a probar (Grid Search)
        self.fast_range = range(5, 25, 2)  # Probar 5, 7, 9... hasta 23
        self.slow_range = range(25, 65, 5) # Probar 25, 30, 35... hasta 60

    def get_historical_data(self, symbol, days=7):
        """Obtiene velas de los últimos X días para entrenar"""
        docs = self.db.collection('historical_data').document(symbol).collection('1h')\
            .order_by('timestamp', direction=firestore.Query.DESCENDING).limit(days * 24).stream()
        
        data = [d.to_dict() for d in docs]
        if not data:
            return []
        # Ordenar cronológicamente (antiguo -> nuevo)
        return sorted(data, key=lambda x: x['timestamp'])

    def backtest(self, closes, fast, slow):
        """Simulación ultrarrápida en memoria"""
        if len(closes) < slow: return -100
        
        capital = 1000
        entry_price = 0
        position = False
        
        # Pre-calcular SMAs (usando Pandas es más rápido, pero lo haremos manual para no añadir deps)
        # Lógica simplificada para velocidad
        trades = 0
        
        for i in range(slow, len(closes)):
            price = closes[i]
            # Cálculo simple de medias
            sma_f = sum(closes[i-fast:i]) / fast
            sma_s = sum(closes[i-slow:i]) / slow
            sma_f_prev = sum(closes[i-fast-1:i-1]) / fast
            sma_s_prev = sum(closes[i-slow-1:i-1]) / slow

            # Cruce Dorado (Compra)
            if not position and sma_f_prev <= sma_s_prev and sma_f > sma_s:
                entry_price = price
                position = True
            
            # Cruce Muerte o Stop Loss (Venta)
            elif position:
                # Venta por cruce inverso
                if sma_f_prev >= sma_s_prev and sma_f < sma_s:
                    profit = (price - entry_price) / entry_price
                    capital *= (1 + profit)
                    position = False
                    trades += 1
        
        return capital

    def find_best_params(self, symbol):
        """Busca la aguja en el pajar"""
        logger.info(f"🧠 Optimizando parámetros para {symbol}...")
        data = self.get_historical_data(symbol)
        if not data: return 10, 30 # Default si falla

        closes = [d['close'] for d in data]
        
        best_profit = 0
        best_fast = 10
        best_slow = 30
        
        # Grid Search (Fuerza Bruta Inteligente)
        for f in self.fast_range:
            for s in self.slow_range:
                if f >= s: continue # La rápida debe ser menor a la lenta
                
                final_cap = self.backtest(closes, f, s)
                
                if final_cap > best_profit:
                    best_profit = final_cap
                    best_fast = f
                    best_slow = s
        
        logger.info(f"✨ GANADOR {symbol}: SMA {best_fast}/{best_slow} (Profit Est: {round(best_profit, 2)})")
        return best_fast, best_slow