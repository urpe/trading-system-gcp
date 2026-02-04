import logging

logger = logging.getLogger(__name__)

class MarketSelector:
    def __init__(self):
        self.top_coins = []
        # Monedas base que NO queremos operar (Stablecoins)
        # Quitamos 'USDT' de esta lista para evitar falsos positivos
        # LISTA NEGRA AMPLIADA: Stablecoins y pares aburridos
        self.ignore_list = [
            'USDC', 'BUSD', 'DAI', 'TUSD', 'FDUSD', 'EUR', 'GBP', 
            'USDP', 'USD1', 'USDD', 'WBTC', 'BTCST'
        ]

    def filter_candidates(self, market_tickers):
        """
        Filtra el Top 100 de Binance y selecciona el Top 5
        basado en Volumen y Volatilidad (donde está la acción).
        """
        candidates = []
        
        for symbol, data in market_tickers.items():
            # 1. Solo pares contra USDT
            if not symbol.endswith('USDT'): 
                continue
            
            # 2. Obtener el activo base (ej: 'BTC' de 'BTCUSDT')
            base_asset = symbol.replace('USDT', '')
            
            # 3. Filtrar si es una moneda estable (ej: USDCUSDT)
            if base_asset in self.ignore_list: 
                continue
            
            # 4. Convertir y validar datos
            try:
                vol_24h = float(data.get('quoteVolume', 0)) # Volumen en USDT
                price_change = abs(float(data.get('priceChangePercent', 0))) # Usamos valor absoluto
                last_price = float(data.get('lastPrice', 0))
            except ValueError:
                continue

            # 5. Filtro de Liquidez Mínima (50 Millones USDT diarios)
            # Esto elimina monedas "basura" o ilíquidas
            if vol_24h < 50_000_000:
                continue

            # 6. Filtro de Volatilidad: Mínimo 1.5% de movimiento en 24h
            if price_change < 1.5:
                continue

            candidates.append({
                'symbol': symbol,
                'volume': vol_24h,
                'change_24h': price_change,
                'price': last_price
            })

        # 7. Ordenar por Volumen descendente (Los reyes del mercado)
        candidates.sort(key=lambda x: x['volume'], reverse=True)
        
        # 8. Seleccionar el Top 5
        self.top_coins = [c['symbol'] for c in candidates[:5]]
        
        # Si no encontramos nada (mercado muerto?), usar backup
        if not self.top_coins:
            logger.warning("⚠️ Mercado muy quieto (Baja volatilidad). Usando clásicos.")
            self.top_coins = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT']

        logger.info(f"🏆 Top 5 Monedas (Vol > 50M & Volatilidad > 1.5%): {self.top_coins}")
        return self.top_coins

    def check_rotation(self, current_portfolio, market_data):
        """
        Decide si vender una moneda vieja para entrar en una nueva.
        Regla Mejorada: Smart Eject.
        """
        actions = []
        
        for position in current_portfolio:
            symbol = position['symbol']
            
            # Si sigue en el Top, no hacemos nada
            if symbol in self.top_coins:
                continue
                
            # Lógica de expulsión para monedas que salieron del Top
            profit = position.get('unrealized_profit', 0)
            
            if profit > 0.5:
                actions.append({'action': 'SELL', 'symbol': symbol, 'reason': 'Rotation_Profit'})
            elif profit < -3.0:
                actions.append({'action': 'SELL', 'symbol': symbol, 'reason': 'Rotation_StopLoss'})
            else:
                logger.info(f"🛡️ Manteniendo {symbol} (Old Top) esperando definición.")

        return actions