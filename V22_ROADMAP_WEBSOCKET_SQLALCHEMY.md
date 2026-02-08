# V22 "REAL-TIME CORE" - ROADMAP

**Fecha Planificación:** 2026-02-08  
**Versión Objetivo:** V22  
**Fundamento:** V21.3 (Canonical Core - 100% Complete)  
**Enfoque:** WebSockets + SQLAlchemy Custom Types + Multi-Quote Support

---

## 🎯 OBJETIVOS V22

### **1. Real-Time Dashboard (WebSockets)**
**Problema Actual (V21.3):**
- Dashboard hace polling cada 2 segundos (`setInterval(2000)`)
- 30 requests/minuto por usuario (ineficiente)
- Latencia visible (hasta 2s para updates)

**Solución V22:**
- WebSocket bidireccional (Flash + Socket.IO)
- Server pushes updates cuando hay cambios (event-driven)
- Latencia < 100ms (vs 2000ms polling)
- Reducción de requests: 30/min → 0/min (solo conexión persistente)

---

### **2. SQLAlchemy Custom Type (TradingSymbol)**
**Problema Actual (V21.3):**
- `TradingSymbol` es Value Object pero se almacena como `str` en SQLite
- Necesita conversión manual: `TradingSymbol.from_str(trade.symbol)`
- Pérdida de type safety en database layer

**Solución V22:**
- Crear `SQLAlchemyTradingSymbol` custom type
- Almacenar `base` y `quote` en columnas separadas (o JSON)
- Query type-safe: `session.query(Trade).filter(Trade.symbol == TradingSymbol.from_str("BTC"))`
- Migración automática de schema

---

### **3. Multi-Quote Currency Support**
**Problema Actual (V21.3):**
- Solo soporta USDT pairs (`BTCUSDT`, `ETHUSDT`)
- Hardcoded `QuoteCurrency.USDT`

**Solución V22:**
- Extender `QuoteCurrency` Enum: `USDT`, `BTC`, `ETH`, `BUSD`
- Parser inteligente: detecta quote currency automáticamente
  - `"ETHBTC"` → `TradingSymbol(base="ETH", quote=QuoteCurrency.BTC)`
- Actualizar Binance API client para soportar múltiples pairs

---

### **4. Advanced Strategy System**
**Problema Actual (V21.3):**
- Estrategias reciben `symbol: str` (legacy)
- No hay validación de símbolos soportados

**Solución V22:**
- Refactorizar `StrategyInterface` con `TradingSymbol` type hints
- Añadir método `is_applicable(symbol: TradingSymbol) -> bool`
- Permitir estrategias específicas por quote currency (ej: estrategia solo para BTC pairs)

---

## 📋 FASES DE IMPLEMENTACIÓN

### **Fase 1: WebSocket Infrastructure (30% effort)**

#### **1.1: Backend (Flask-SocketIO)**
**Archivo:** `src/services/dashboard/websocket_server.py` (NUEVO)

```python
from flask_socketio import SocketIO, emit
from src.shared.memory import memory
from src.domain import TradingSymbol

socketio = SocketIO(app, cors_allowed_origins="*")

@socketio.on('connect')
def handle_connect():
    emit('status', {'message': 'Connected to V22 Real-Time Core'})

@socketio.on('subscribe_symbol')
def handle_subscribe(data):
    symbol = TradingSymbol.from_str(data['symbol'])
    # Subscribe client to Redis channel for this symbol
    # ...
```

**Integración:**
- Modificar `src/services/dashboard/app.py` para inicializar SocketIO
- Crear worker thread para escuchar Redis Pub/Sub y broadcast a clientes WebSocket

#### **1.2: Frontend (Socket.IO Client)**
**Archivo:** `src/services/dashboard/templates/dashboard.html` (MODIFICAR)

```html
<script src="https://cdn.socket.io/4.5.0/socket.io.min.js"></script>
<script>
  const socket = io('http://localhost:5000');
  
  socket.on('price_update', (data) => {
    // Update UI instantly (no polling)
    updatePriceCard(data.symbol, data.price);
  });
  
  socket.emit('subscribe_symbol', {symbol: 'BTC'});
</script>
```

**Eliminación:**
- Remover `setInterval(updateDashboard, 2000)` (polling legacy)

---

### **Fase 2: SQLAlchemy Custom Type (25% effort)**

#### **2.1: Crear Custom Type**
**Archivo:** `src/shared/database_types.py` (NUEVO)

```python
from sqlalchemy.types import TypeDecorator, String
from src.domain import TradingSymbol
import json

class TradingSymbolType(TypeDecorator):
    """
    SQLAlchemy custom type para almacenar TradingSymbol.
    
    Almacena como JSON: {"base": "BTC", "quote": "USDT"}
    """
    impl = String(50)
    cache_ok = True
    
    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if not isinstance(value, TradingSymbol):
            raise TypeError(f"Expected TradingSymbol, got {type(value)}")
        # Serialize to JSON string
        return json.dumps({'base': value.base, 'quote': value.quote.value})
    
    def process_result_value(self, value, dialect):
        if value is None:
            return value
        # Deserialize from JSON
        data = json.loads(value)
        return TradingSymbol(base=data['base'], quote=QuoteCurrency(data['quote']))
```

#### **2.2: Migrar Models**
**Archivo:** `src/shared/database.py` (MODIFICAR)

```python
from src.shared.database_types import TradingSymbolType

class Trade(Base):
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(TradingSymbolType, nullable=False, index=True)  # ✅ Type-safe!
    side = Column(String, nullable=False)
    # ...
```

**Migración de Datos:**
```python
# Script: migrate_symbols_to_v22.py
session = SessionLocal()
trades = session.query(Trade).all()

for trade in trades:
    # Convert string to TradingSymbol
    trade.symbol = TradingSymbol.from_str(trade.symbol)
session.commit()
```

---

### **Fase 3: Multi-Quote Support (20% effort)**

#### **3.1: Extender QuoteCurrency Enum**
**Archivo:** `src/domain/trading_symbol.py` (MODIFICAR)

```python
class QuoteCurrency(Enum):
    USDT = "USDT"
    BTC = "BTC"
    ETH = "ETH"
    BUSD = "BUSD"
    USDC = "USDC"
    
    @classmethod
    def detect_from_pair(cls, pair: str) -> 'QuoteCurrency':
        """Detecta quote currency automáticamente."""
        pair_upper = pair.upper()
        for quote in cls:
            if pair_upper.endswith(quote.value):
                return quote
        return cls.USDT  # Default
```

#### **3.2: Smart Parser**
**Archivo:** `src/domain/trading_symbol.py` (MODIFICAR)

```python
@classmethod
def from_str(cls, symbol: str, default_quote: QuoteCurrency = None) -> 'TradingSymbol':
    """
    V22: Parser inteligente con auto-detección de quote currency.
    
    Examples:
        - "ETHBTC" → TradingSymbol(base="ETH", quote=BTC)
        - "BTCUSDT" → TradingSymbol(base="BTC", quote=USDT)
        - "BTC" → TradingSymbol(base="BTC", quote=USDT) [default]
    """
    if not isinstance(symbol, str):
        raise TypeError(f"Symbol must be str, got {type(symbol)}")
    
    symbol = symbol.strip().upper()
    
    # Auto-detect quote currency
    detected_quote = QuoteCurrency.detect_from_pair(symbol)
    if symbol.endswith(detected_quote.value):
        base = symbol[:-len(detected_quote.value)]
        return cls(base=base, quote=detected_quote)
    
    # Fallback: assume short format
    return cls(base=symbol, quote=default_quote or QuoteCurrency.USDT)
```

---

### **Fase 4: Advanced Strategy System (15% effort)**

#### **4.1: Refactorizar StrategyInterface**
**Archivo:** `src/services/brain/strategies/__init__.py` (MODIFICAR)

```python
from abc import ABC, abstractmethod
from src.domain import TradingSymbol

class StrategyInterface(ABC):
    @abstractmethod
    def analyze(self, symbol: TradingSymbol, ohlcv_history: dict) -> dict:
        """
        V22: Type-safe symbol parameter.
        
        Args:
            symbol: TradingSymbol (garantiza validez)
            ohlcv_history: {'open': [...], 'high': [...], ...}
        
        Returns:
            {'signal': 'BUY'|'SELL'|'HOLD', 'confidence': 0.0-1.0}
        """
        pass
    
    def is_applicable(self, symbol: TradingSymbol) -> bool:
        """
        V22: Valida si estrategia soporta este símbolo.
        
        Example:
            - BTC-only strategy: return symbol.base == "BTC"
            - USDT pairs only: return symbol.quote == QuoteCurrency.USDT
        """
        return True  # Default: aplica a todos
```

#### **4.2: Actualizar Estrategias Existentes**
**Archivo:** `src/services/brain/strategies/rsi_mean_reversion.py` (MODIFICAR)

```python
class RsiMeanReversion(StrategyInterface):
    def analyze(self, symbol: TradingSymbol, ohlcv_history: dict) -> dict:
        # ✅ symbol es TradingSymbol (type-safe)
        logger.info(f"Analyzing {symbol} with RSI strategy")
        # ...
    
    def is_applicable(self, symbol: TradingSymbol) -> bool:
        # Only apply to USDT pairs (legacy compatibility)
        return symbol.quote == QuoteCurrency.USDT
```

---

### **Fase 5: Performance Optimizations (10% effort)**

#### **5.1: Redis Pipeline**
**Problema:** `memory.get()` hace 1 request por símbolo (N calls)

**Solución:**
```python
# ANTES (V21.3)
prices = []
for symbol in symbols:
    price = memory.get(symbol.to_redis_key("price"))
    prices.append(price)

# DESPUÉS (V22)
keys = [s.to_redis_key("price") for s in symbols]
prices = memory.mget(keys)  # Single round-trip
```

#### **5.2: SQLAlchemy Eager Loading**
**Problema:** N+1 queries en dashboard

**Solución:**
```python
# ANTES (V21.3)
trades = session.query(Trade).filter(Trade.status=='open').all()
for trade in trades:
    print(trade.wallet)  # ❌ N queries

# DESPUÉS (V22)
from sqlalchemy.orm import joinedload
trades = session.query(Trade).options(joinedload(Trade.wallet)).all()
# ✅ Single JOIN query
```

---

## 🧪 TESTING STRATEGY

### **1. Unit Tests**
- `test_websocket_server.py`: WebSocket connect/disconnect/emit
- `test_trading_symbol_type.py`: SQLAlchemy serialization/deserialization
- `test_multi_quote_parser.py`: Quote currency detection

### **2. Integration Tests**
- `test_websocket_e2e.py`: Client subscribes → Server emits → Client receives
- `test_sqlalchemy_custom_type.py`: Insert TradingSymbol → Query → Verify
- `test_multi_quote_strategies.py`: ETHBTC strategy execution

### **3. Performance Tests**
- WebSocket latency: < 100ms
- SQLAlchemy bulk inserts: > 1000 trades/sec
- Redis pipeline: > 10K keys/sec

---

## 📊 METRICS & SUCCESS CRITERIA

| **Métrica** | **V21.3 (Before)** | **V22 (Target)** | **Improvement** |
|-------------|-------------------|------------------|-----------------|
| Dashboard Latency | 2000ms (polling) | < 100ms (WebSocket) | **20x faster** |
| Network Requests | 30/min per user | 0/min (persistent) | **∞ reduction** |
| Type Safety (DB) | 0% (strings) | 100% (Value Objects) | **100% gain** |
| Supported Pairs | USDT only | USDT/BTC/ETH/BUSD | **4x coverage** |
| Query Performance | N+1 queries | Eager loading | **10x faster** |

---

## 🛣️ TIMELINE ESTIMATE

| **Fase** | **Duración** | **Dependencias** |
|----------|--------------|------------------|
| Fase 1: WebSockets | 2 días | Flask-SocketIO, Redis Pub/Sub |
| Fase 2: SQLAlchemy Types | 1.5 días | V21.3 TradingSymbol |
| Fase 3: Multi-Quote | 1 día | QuoteCurrency Enum |
| Fase 4: Advanced Strategies | 1 día | Fase 2 (DB migration) |
| Fase 5: Performance | 0.5 días | - |
| **TOTAL** | **6 días** | - |

**Testing & QA:** +2 días  
**Production Deployment:** +1 día  
**GRAND TOTAL:** ~9 días laborables

---

## 🚨 RISKS & MITIGATION

### **Risk 1: WebSocket Compatibility**
**Problema:** Browsers viejos no soportan WebSockets

**Mitigación:**
- Fallback automático a long-polling (Socket.IO lo maneja)
- Detectar cliente y usar mejor método disponible

### **Risk 2: SQLAlchemy Migration Downtime**
**Problema:** Cambio de schema requiere downtime

**Mitigación:**
- Blue-Green deployment: mantener V21.3 mientras migra
- Script de migración reversible (`upgrade()` + `downgrade()`)

### **Risk 3: Multi-Quote Data Availability**
**Problema:** Binance puede no tener todos los pairs (ej: `SOLBTC`)

**Mitigación:**
- Validar pairs disponibles antes de añadir al sistema
- API call: `GET /api/v3/exchangeInfo` (Binance)

---

## 🔧 BREAKING CHANGES

### **V21.3 → V22 Migration Checklist**

1. **Database Schema Change:**
   - Columna `symbol` cambia de `String` a `TradingSymbolType`
   - Requiere migración de datos existentes

2. **Frontend Update:**
   - Remover polling code (`setInterval`)
   - Añadir Socket.IO client library

3. **Strategy Signatures:**
   - `analyze(symbol: str, ...)` → `analyze(symbol: TradingSymbol, ...)`
   - Todas las estrategias custom deben actualizar firma

---

## 📚 DOCUMENTATION UPDATES

### **Nuevos Archivos:**
- `docs/WEBSOCKET_API.md`: Endpoints y eventos Socket.IO
- `docs/SQLALCHEMY_CUSTOM_TYPES.md`: Cómo crear custom types
- `docs/MULTI_QUOTE_GUIDE.md`: Cómo añadir nuevas quote currencies

### **Archivos Actualizados:**
- `README.md`: Mencionar WebSocket support
- `SYSTEM_SNAPSHOT_V22.md`: Nueva arquitectura
- `.cursorrules`: Añadir WebSocket best practices

---

## ✅ DEFINITION OF DONE

V22 estará **completa** cuando:

1. ✅ WebSocket server funciona (conexión + broadcast)
2. ✅ Dashboard recibe updates en < 100ms
3. ✅ SQLAlchemy custom type funciona (insert + query)
4. ✅ Multi-quote parser detecta BTC/ETH/BUSD correctamente
5. ✅ Todas las estrategias usan `TradingSymbol` type hints
6. ✅ Tests: 100% coverage (unit + integration + performance)
7. ✅ Docker build exitoso (9/9 imágenes)
8. ✅ GCP deployment sin downtime (blue-green)

---

## 🎯 NEXT STEPS (Post-V22)

### **V23: Machine Learning Integration**
- Predicción de precio con LSTM/Transformer
- Sentiment analysis de Twitter/Reddit
- Anomaly detection en volume patterns

### **V24: Multi-Exchange Support**
- Añadir Coinbase, Kraken, OKX
- Arbitrage opportunities detector
- Unified order routing

### **V25: Cloud-Native Scaling**
- Kubernetes deployment (vs Docker Compose)
- Horizontal scaling de Brain service
- Distributed Redis (Sentinel/Cluster)

---

**V22 MOTTO:** "If it moves, websocket it. If it's stored, type it."

---

**Documento generado:** 2026-02-08  
**Autor:** HFT Trading Bot Team  
**Status:** 📋 ROADMAP (Pending Implementation)
