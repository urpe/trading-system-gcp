# 🧪 GUÍA DE TESTING EN PRODUCCIÓN - V21.2

**Versión:** V21.2 SYNCHRONIZED ARCHITECTURE  
**Fecha:** 2026-02-07  
**Estado:** Producción Ready  

---

## 📋 PRE-REQUISITOS

Antes de ejecutar el testing en producción:

```bash
# 1. Verificar acceso SSH a la VM
ssh vm-trading-bot "echo 'SSH OK'"

# 2. Verificar que tienes los cambios V21.2 locales
git log --oneline -3
# Debe mostrar:
# 95339fb docs: Add V21.2 Executive Summary
# e2ec024 feat: V21.2 SYNCHRONIZED ARCHITECTURE

# 3. Backup de la base de datos actual (opcional pero recomendado)
ssh vm-trading-bot "cd trading-system-gcp && cp src/data/trading_bot_v16.db src/data/trading_bot_v16.db.backup_$(date +%Y%m%d_%H%M%S)"
```

---

## 🚀 FASE 1: DEPLOYMENT EN PRODUCCIÓN

### Paso 1.1: Conectar a la VM

```bash
ssh vm-trading-bot
cd trading-system-gcp
```

**Verificación esperada:**
```
usuario@vm-trading-bot:~/trading-system-gcp$
```

---

### Paso 1.2: Pull de Cambios V21.2

```bash
# Verificar estado actual
git status
git log --oneline -1

# Pull de GitHub
git fetch origin
git pull origin main

# Verificar que se descargaron los cambios V21.2
git log --oneline -3
```

**Output esperado:**
```
From https://github.com/urpe/trading-system-gcp
 * branch            main       -> FETCH_HEAD
Updating df82ba3..95339fb
Fast-forward
 V21.2_ARCHITECTURE_FIXES_REPORT.md | 1100 ++++++++++++++++
 V21.2_EXECUTIVE_SUMMARY.md         |  267 ++++
 audit_redis_keys.py                 |  360 +++++
 continuous_redis_monitor.sh         |  198 +++
 src/services/brain/main.py          |   85 +-
 src/services/dashboard/app.py       |   55 +-
 src/services/market_data/main.py    |   12 +-
 src/services/orders/main.py         |   32 +-
 src/shared/utils.py                 |  113 ++
 9 files changed, 2197 insertions(+), 25 deletions(-)
```

---

### Paso 1.3: Deployment con deploy_prod.sh

```bash
# Opción A: Fast restart (recomendado para V21.2)
./deploy_prod.sh

# Opción B: Full rebuild (si quieres forzar rebuild de imágenes)
./deploy_prod.sh --full-rebuild
```

**Output esperado:**
```
🚀 HFT Bot V21 - Production Deployment
=======================================

📥 Pulling latest code from GitHub...
Already up to date.
✅ Code updated to latest version

⚡ Fast deployment: Restart services (sin rebuild)...
Restarting market-data ... done
Restarting brain       ... done
Restarting dashboard   ... done
Restarting orders      ... done
(... otros servicios ...)
✅ Services restarted

🔍 Verificando servicios...
NAME                COMMAND                  SERVICE             STATUS              PORTS
dashboard           "python src/services…"   dashboard           running             0.0.0.0:8050->8050/tcp
brain               "python src/services…"   brain               running             
market-data         "python src/services…"   market-data         running             
orders              "python src/services…"   orders              running             
redis               "docker-entrypoint.s…"   redis               running (healthy)   

✅ DEPLOYMENT EXITOSO: 10/10 servicios corriendo
```

---

## 🧪 FASE 2: VERIFICACIÓN DEL WARM-UP SYSTEM

### Paso 2.1: Verificar Logs del Brain (Warm-up)

```bash
# Ver logs del Brain en tiempo real
docker compose logs -f brain

# O ver últimas 50 líneas
docker compose logs --tail=50 brain | grep "WARM-UP"
```

**Output esperado (V21.2):**
```
brain  | ═══════════════════════════════════════════════════════════
brain  | 🔥 WARM-UP SYSTEM ACTIVADO: Descargando historial inicial...
brain  |    Símbolos: ['BTC', 'ETH', 'SOL', 'BNB', 'XRP']
brain  |    Objetivo: 200 velas por símbolo (1m interval)
brain  | ═══════════════════════════════════════════════════════════
brain  | 📥 Warm-up: BTC...
brain  | ✅ Descargadas 200 velas de BTCUSDT (1m)
brain  | ✅ BTC: 200 velas cargadas | Régimen: ↔️ sideways_range | Último precio: $68234.50
brain  | 📥 Warm-up: ETH...
brain  | ✅ Descargadas 200 velas de ETHUSDT (1m)
brain  | ✅ ETH: 200 velas cargadas | Régimen: ↔️ sideways_range | Último precio: $3456.78
brain  | ═══════════════════════════════════════════════════════════
brain  | 🎯 WARM-UP COMPLETADO: 5 símbolos listos para trading
brain  |    ⚡ Sistema operativo en <10 segundos (vs 3.3 horas anterior)
brain  | ═══════════════════════════════════════════════════════════
brain  | ✅ Brain escuchando mercado en tiempo real...
```

**Si NO ves esto:**
- ❌ Problema: Warm-up system no se ejecutó
- 🔧 Solución: Verificar que se pulleó correctamente la V21.2

---

### Paso 2.2: Verificar Tiempo de Arranque

```bash
# Ver timestamp de inicio del Brain
docker compose logs brain | grep "Brain V21.2" | head -1

# Ver timestamp de "WARM-UP COMPLETADO"
docker compose logs brain | grep "WARM-UP COMPLETADO" | head -1

# Calcular diferencia (debe ser <10 segundos)
```

---

## 🔍 FASE 3: AUDITORÍA DE REDIS KEYS

### Paso 3.1: Ejecutar audit_redis_keys.py

```bash
# Ejecutar auditoría
docker compose exec dashboard python audit_redis_keys.py
```

**Output esperado (Sistema Sano):**
```
🔍 AUDITORÍA DE CLAVES REDIS - V21.2 SYNCHRONIZED ARCHITECTURE
================================================================================

📊 Total de keys en Redis: 23

📋 KEYS POR CATEGORÍA:
   - price:* (Market Data)      : 5 keys
   - market_regime:* (Brain)    : 5 keys
   - strategy_config:* (Optimizer): 5 keys
   - active_symbols (Market Data): ✅ Existe

🎯 ACTIVE SYMBOLS (de Market Data):
   ['BTC', 'ETH', 'SOL', 'BNB', 'XRP']

💰 SÍMBOLOS EN PRICE:* KEYS:
   ['BNB', 'BTC', 'ETH', 'SOL', 'XRP']

📈 SÍMBOLOS EN MARKET_REGIME:* KEYS:
   ['BNB', 'BTC', 'ETH', 'SOL', 'XRP']

================================================================================
🔬 VERIFICACIÓN DE INTEGRIDAD (V21.2 FIX)
================================================================================

✅ PERFECT SYNC: active_symbols coinciden 100% con price:* keys
✅ BRAIN OK: Todos los active_symbols tienen market_regime:* key

================================================================================
🧪 PRUEBA DE NORMALIZACIÓN normalize_symbol()
================================================================================

✅ normalize_symbol('btcusdt', 'short') = 'BTC' (esperado: 'BTC')
✅ normalize_symbol('BTCUSDT', 'short') = 'BTC' (esperado: 'BTC')
✅ normalize_symbol('BTC', 'short') = 'BTC' (esperado: 'BTC')
✅ normalize_symbol('eth', 'long') = 'ETHUSDT' (esperado: 'ETHUSDT')
✅ normalize_symbol('SOL', 'lower') = 'solusdt' (esperado: 'solusdt')

✅ Todas las pruebas de normalización PASARON

================================================================================
📊 RESUMEN DE AUDITORÍA
================================================================================

🎉 ¡SISTEMA PERFECTO! Arquitectura V21.2 sincronizada correctamente

   ✅ active_symbols → price:* keys: SYNC
   ✅ active_symbols → market_regime:* keys: SYNC
   ✅ normalize_symbol(): FUNCIONA

================================================================================
```

**Si encuentras discrepancias:**

```
⚠️ DISCREPANCIA: Símbolos en active_symbols pero SIN price:* key:
   - BTC (Market Data NO está publicando datos)
```

**Acciones:**
1. Verificar logs de market_data: `docker compose logs market-data`
2. Verificar que market_data esté corriendo: `docker compose ps market-data`
3. Reiniciar market_data: `docker compose restart market-data`

---

## 📊 FASE 4: VERIFICACIÓN DEL DASHBOARD

### Paso 4.1: Verificar Endpoint API

```bash
# Desde la VM
curl http://localhost:8050/api/dashboard-data | jq '.'
```

**Output esperado:**
```json
{
  "usdt_balance": 750.31,
  "total_equity": 984.66,
  "positions": [
    {
      "type": "LONG",
      "symbol": "BTC",
      "amount": 0.0012,
      "current_price": 68234.50,
      "value": 81.88,
      "entry_price": 67800.00,
      "pnl": 0.52
    }
  ],
  "scanner": ["BTC", "ETH", "SOL", "BNB", "XRP"],  // ✅ Normalizados
  "regimes": {
    "BTC": {
      "regime": "sideways_range",
      "adx": 17.5,
      "ema_200": 68782.8,
      "atr_percent": 0.06
    }
  }
}
```

**Verificaciones:**
- ✅ `scanner` contiene símbolos en formato corto ("BTC", no "btcusdt")
- ✅ `total_equity` NO es $0.00
- ✅ `regimes` tiene datos para cada símbolo en scanner

---

### Paso 4.2: Verificar Dashboard Web UI

```bash
# Obtener IP de la VM
hostname -I | awk '{print $1}'
```

Abrir en navegador: `http://[IP_VM]:8050`

**Verificaciones visuales:**
1. ✅ **Equity** muestra valor correcto (NO $0.00)
2. ✅ **Scanner** muestra 5 símbolos (BTC, ETH, SOL, BNB, XRP)
3. ✅ **Positions** muestra posiciones activas
4. ✅ Hacer clic en un símbolo del scanner (ej: BTC)
   - URL: `http://[IP]:8050/asset/BTC`
   - ✅ NO debe mostrar TypeError
   - ✅ Debe mostrar precio actual

---

## 🛡️ FASE 5: VERIFICACIÓN DEL STOP LOSS WORKER

### Paso 5.1: Verificar Logs de Orders

```bash
docker compose logs orders | grep "Stop Loss Worker"
```

**Output esperado:**
```
orders | 🛡️ Stop Loss Worker V21.2 iniciado (check cada 30s)
```

### Paso 5.2: Simular Stop Loss (Opcional)

```bash
# Ver posiciones abiertas
docker compose exec dashboard python -c "
from src.shared.database import SessionLocal, Trade
session = SessionLocal()
trades = session.query(Trade).filter(Trade.status == 'OPEN').all()
for t in trades:
    print(f'{t.symbol}: Entry=${t.entry_price:.2f}')
session.close()
"

# Monitorear logs de orders en tiempo real
docker compose logs -f orders
```

**Si hay una posición con pérdida > -2%:**
```
orders | 🛑 STOP LOSS TRIGGERED: BTC @ $66000.00 (PnL: -2.5%)
orders | 📤 Stop loss signal published for BTC
```

---

## 🔄 FASE 6: MONITOREO CONTINUO (OPCIONAL)

### Paso 6.1: Iniciar Monitor Continuo

```bash
# Opción 1: En una sesión screen (recomendado)
screen -S redis-monitor
./continuous_redis_monitor.sh

# Detach: Ctrl+A, luego D
# Reattach: screen -r redis-monitor

# Opción 2: Con nohup
nohup ./continuous_redis_monitor.sh > monitor.log 2>&1 &
```

**Output esperado (cada 1 hora):**
```
[2026-02-07 20:00:00] ℹ️ ═══════════════════════════════════════════
[2026-02-07 20:00:00] ℹ️ Iteración #1 - 2026-02-07 20:00:00
[2026-02-07 20:00:00] ℹ️ ═══════════════════════════════════════════
[2026-02-07 20:00:01] ℹ️ Verificando salud del sistema...
[2026-02-07 20:00:02] ℹ️ Sistema saludable ✅
[2026-02-07 20:00:02] ℹ️ Ejecutando auditoría de Redis...
[2026-02-07 20:00:05] ℹ️ Auditoría exitosa - Sistema en estado óptimo ✅
[2026-02-07 20:00:05] ℹ️ ⏳ Próxima auditoría en 1h...
```

---

## 📈 FASE 7: MÉTRICAS DE ÉXITO

### Checklist de Verificación V21.2

- [ ] **Warm-up System**
  - [ ] Brain muestra "WARM-UP COMPLETADO" en logs
  - [ ] Tiempo de arranque < 10 segundos
  - [ ] Regímenes detectados inmediatamente

- [ ] **Symbol Normalization**
  - [ ] audit_redis_keys.py muestra "PERFECT SYNC"
  - [ ] active_symbols coincide con price:* keys
  - [ ] Brain tiene market_regime:* para todos los símbolos

- [ ] **Dashboard**
  - [ ] `/api/dashboard-data` retorna equity != $0.00
  - [ ] Scanner muestra símbolos normalizados (BTC, ETH, etc.)
  - [ ] `/asset/BTC` NO muestra TypeError

- [ ] **Stop Loss Worker**
  - [ ] Logs muestran "Stop Loss Worker V21.2 iniciado"
  - [ ] Si hay posiciones con pérdida > -2%, se ejecuta stop loss

- [ ] **Monitoreo Continuo** (Opcional)
  - [ ] continuous_redis_monitor.sh se ejecuta sin errores
  - [ ] Auditorías cada 1 hora sin issues

---

## 🚨 TROUBLESHOOTING

### Problema 1: Brain NO muestra "WARM-UP COMPLETADO"

**Síntomas:**
```
brain | ✅ Brain escuchando mercado en tiempo real...
# (Sin mensaje de warm-up)
```

**Diagnóstico:**
```bash
# Verificar versión del código
docker compose exec brain python -c "
from src.shared.utils import normalize_symbol, fetch_binance_klines
print('normalize_symbol:', normalize_symbol.__doc__[:50])
print('fetch_binance_klines:', fetch_binance_klines.__doc__[:50])
"
```

**Solución:**
```bash
# Re-pull y rebuild
git pull origin main
./deploy_prod.sh --full-rebuild
```

---

### Problema 2: audit_redis_keys.py muestra discrepancias

**Síntomas:**
```
⚠️ DISCREPANCIA: Keys price:* sin active_symbols correspondiente:
   - price:BTCUSDT (posiblemente obsoleto)
```

**Solución:**
```bash
# Limpiar keys obsoletas manualmente
docker compose exec redis redis-cli DEL price:BTCUSDT

# Re-ejecutar auditoría
docker compose exec dashboard python audit_redis_keys.py
```

---

### Problema 3: Dashboard muestra $0.00

**Diagnóstico:**
```bash
# 1. Verificar que market_data esté publicando
docker compose logs market-data | grep "OHLCV:" | tail -5

# 2. Verificar Redis
docker compose exec redis redis-cli KEYS "price:*"

# 3. Verificar contenido de una key
docker compose exec redis redis-cli GET "price:BTC"
```

**Si Redis está vacío:**
```bash
# Reiniciar market_data
docker compose restart market-data

# Esperar 60 segundos (1 ciclo)
sleep 60

# Verificar nuevamente
docker compose exec redis redis-cli KEYS "price:*"
```

---

## 📊 REPORTES Y LOGS

### Estructura de Archivos Generados

```
trading-system-gcp/
├── redis_audit_reports/         # Reportes de auditoría
│   ├── audit_20260207_200000.txt
│   ├── audit_20260207_210000.txt
│   └── ...
├── redis_alerts.log             # Log de alertas
└── monitor.log                  # Log del monitor continuo
```

### Ver Alertas

```bash
# Ver últimas alertas
tail -20 redis_alerts.log

# Contar alertas en las últimas 24h
grep "$(date +%Y-%m-%d)" redis_alerts.log | wc -l
```

---

## ✅ CONCLUSIÓN DEL TESTING

**Si todos los checks pasan:**

```
🎉 V21.2 SYNCHRONIZED ARCHITECTURE - TESTING COMPLETO

✅ Warm-up System: Sistema operativo en <10 segundos
✅ Normalización: 100% consistencia en Redis keys
✅ Dashboard: Mostrando datos correctos (NO $0.00)
✅ Stop Loss: Worker activo y normalizado
✅ Auditoría: Sistema en estado perfecto

🚀 SISTEMA LISTO PARA PRODUCCIÓN 24/7
```

**Siguiente paso:** Monitorear durante 24-48 horas para confirmar estabilidad.

---

**Generado por:** Lead Software Architect  
**Versión:** V21.2  
**Fecha:** 2026-02-07
