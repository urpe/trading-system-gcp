"""
Binance Data Fetcher - V19.1
=============================
Descarga datos históricos de 1 minuto de Binance API.
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BinanceDataFetcher")

BINANCE_API_URL = "https://api.binance.com/api/v3/klines"


def fetch_1m_data(symbols: List[str], hours_back: int = 48) -> Dict[str, pd.DataFrame]:
    """
    Descarga datos OHLCV de 1 minuto de Binance.
    
    Args:
        symbols: Lista de símbolos (ej: ['BTC', 'ETH', 'SOL'])
        hours_back: Cuántas horas hacia atrás (default: 48)
    
    Returns:
        Diccionario {symbol: DataFrame(timestamp, open, high, low, close, volume)}
    
    Notas:
        - Binance limite: 1000 velas por request
        - Para 48h = 2880 minutos → necesita 3 requests
        - Rate limit: 1200 requests/min (weight=1 por request)
    """
    logger.info(f"📥 Descargando datos de {len(symbols)} símbolos ({hours_back}h hacia atrás)...")
    
    market_data = {}
    
    for symbol in symbols:
        logger.info(f"   Descargando {symbol}...")
        try:
            df = _fetch_symbol_data(symbol, hours_back)
            market_data[symbol] = df
            logger.info(f"   ✅ {symbol}: {len(df)} velas descargadas")
            time.sleep(0.1)  # Rate limiting cortés
        except Exception as e:
            logger.error(f"   ❌ Error descargando {symbol}: {e}")
    
    logger.info(f"✅ Descarga completada: {len(market_data)} símbolos")
    return market_data


def _fetch_symbol_data(symbol: str, hours_back: int) -> pd.DataFrame:
    """
    Descarga datos de un símbolo específico.
    
    Args:
        symbol: Símbolo (ej: 'BTC')
        hours_back: Horas hacia atrás
    
    Returns:
        DataFrame con columnas: timestamp, open, high, low, close, volume
    """
    # Calcular timestamps
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=hours_back)
    
    # Convertir a milisegundos (formato Binance)
    start_ms = int(start_time.timestamp() * 1000)
    end_ms = int(end_time.timestamp() * 1000)
    
    # Binance retorna max 1000 velas por request
    # Calcular cuántos requests necesitamos
    minutes_needed = hours_back * 60
    requests_needed = (minutes_needed // 1000) + 1
    
    all_data = []
    current_start = start_ms
    
    for i in range(requests_needed):
        params = {
            'symbol': f'{symbol}USDT',
            'interval': '1m',
            'startTime': current_start,
            'endTime': end_ms,
            'limit': 1000
        }
        
        response = requests.get(BINANCE_API_URL, params=params, timeout=10)
        
        if response.status_code != 200:
            raise Exception(f"Binance API error: {response.status_code} - {response.text}")
        
        data = response.json()
        
        if not data:
            break
        
        all_data.extend(data)
        
        # Actualizar start time para próximo request
        last_timestamp = data[-1][0]
        current_start = last_timestamp + 1  # +1ms para evitar duplicados
        
        # Si ya alcanzamos el end_time, terminar
        if last_timestamp >= end_ms:
            break
    
    # Convertir a DataFrame
    df = pd.DataFrame(all_data, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'number_of_trades',
        'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
    ])
    
    # Limpiar y convertir tipos
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df['open'] = df['open'].astype(float)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    df['close'] = df['close'].astype(float)
    df['volume'] = df['volume'].astype(float)
    
    # Seleccionar columnas relevantes
    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    
    # Eliminar duplicados (por si acaso)
    df = df.drop_duplicates(subset=['timestamp']).reset_index(drop=True)
    
    # Ordenar por timestamp
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    return df


def validate_data(market_data: Dict[str, pd.DataFrame]) -> bool:
    """
    Valida que los datos descargados sean correctos.
    
    Args:
        market_data: Diccionario de DataFrames
    
    Returns:
        True si los datos son válidos, False en caso contrario
    """
    logger.info("🔍 Validando datos descargados...")
    
    if not market_data:
        logger.error("❌ No hay datos descargados")
        return False
    
    for symbol, df in market_data.items():
        # Check 1: DataFrame no vacío
        if df.empty:
            logger.error(f"❌ {symbol}: DataFrame vacío")
            return False
        
        # Check 2: Columnas requeridas presentes
        required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        if not all(col in df.columns for col in required_cols):
            logger.error(f"❌ {symbol}: Faltan columnas requeridas")
            return False
        
        # Check 3: No hay valores NaN en close price
        if df['close'].isna().any():
            logger.warning(f"⚠️ {symbol}: Hay valores NaN en close price")
            # Forward fill NaNs
            df['close'].fillna(method='ffill', inplace=True)
        
        # Check 4: Precios positivos
        if (df['close'] <= 0).any():
            logger.error(f"❌ {symbol}: Hay precios <= 0")
            return False
        
        # Check 5: Timestamps ordenados
        if not df['timestamp'].is_monotonic_increasing:
            logger.warning(f"⚠️ {symbol}: Timestamps no ordenados, reordenando...")
            df.sort_values('timestamp', inplace=True)
        
        logger.info(f"   ✅ {symbol}: {len(df)} velas válidas")
    
    logger.info("✅ Validación completada")
    return True


def get_data_summary(market_data: Dict[str, pd.DataFrame]) -> str:
    """
    Genera un resumen de los datos descargados.
    
    Args:
        market_data: Diccionario de DataFrames
    
    Returns:
        String con resumen legible
    """
    if not market_data:
        return "No data available"
    
    summary_lines = ["📊 DATOS DESCARGADOS - RESUMEN"]
    summary_lines.append("=" * 60)
    
    for symbol, df in market_data.items():
        if df.empty:
            summary_lines.append(f"{symbol}: No data")
            continue
        
        start_time = df['timestamp'].min()
        end_time = df['timestamp'].max()
        duration_hours = (end_time - start_time).total_seconds() / 3600
        
        price_range = f"${df['close'].min():.2f} - ${df['close'].max():.2f}"
        
        summary_lines.append(
            f"{symbol:8s}: {len(df):5d} velas | "
            f"{duration_hours:.1f}h | "
            f"Range: {price_range}"
        )
    
    return "\n".join(summary_lines)


if __name__ == "__main__":
    # Test de descarga
    symbols = ['BTC', 'ETH', 'SOL']
    data = fetch_1m_data(symbols, hours_back=2)
    
    if validate_data(data):
        print(get_data_summary(data))
    else:
        print("❌ Data validation failed")
