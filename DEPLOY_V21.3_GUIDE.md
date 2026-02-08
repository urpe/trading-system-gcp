# V21.3 "CANONICAL CORE" - DEPLOYMENT GUIDE

**Versión:** V21.3 (100% Complete)  
**Build Status:** ✅ Docker 9/9 images successful  
**Tests:** ✅ 19/19 PASSED  
**Git Status:** ✅ Committed & Pushed to `main`

---

## 🎯 PRE-DEPLOYMENT CHECKLIST

Antes de deploy, verifica:

- [x] ✅ Docker build exitoso (9/9 imágenes)
- [x] ✅ Tests pasados (19/19)
- [x] ✅ Código commiteado y pushed
- [x] ✅ Redis configurado (AOF persistence)
- [x] ✅ Variables de entorno configuradas
- [ ] ⏳ Backup de base de datos (si aplica)

---

## 🚀 OPCIÓN 1: DEPLOY LOCAL (Testing)

### **Paso 1: Levantar Sistema**

```bash
cd /home/jhersonurpecanchanya/trading-system-gcp

# Bajar servicios anteriores (si existen)
docker compose down

# Construir imágenes V21.3 (ya hecho)
# docker compose build --no-cache  # (Ya completado)

# Levantar servicios
docker compose up -d

# Verificar que todos los servicios estén corriendo
docker compose ps
```

**Expected Output:**
```
NAME                           STATUS
trading-system-gcp-alerts      Up
trading-system-gcp-brain       Up
trading-system-gcp-dashboard   Up
trading-system-gcp-historical  Up
trading-system-gcp-market-data Up
trading-system-gcp-orders      Up
trading-system-gcp-persistence Up
trading-system-gcp-redis       Up (healthy)
trading-system-gcp-simulator   Up
trading-system-gcp-strategy-optimizer Up
```

### **Paso 2: Verificar Warm-up System**

```bash
# Ver logs de Brain para confirmar warm-up
docker compose logs brain --tail 50 | grep "WARM-UP"
```

**Expected Output:**
```
🔥 WARM-UP SYSTEM ACTIVADO: Descargando historial inicial...
✅ BTC: 200 velas cargadas | Régimen: 📈 bull_trend | Último precio: $75200.00
✅ ETH: 200 velas cargadas | Régimen: ↔️ sideways_range | Último precio: $4100.50
🎯 WARM-UP COMPLETADO: 5 símbolos listos para trading
```

### **Paso 3: Verificar Dashboard**

```bash
# Abrir Dashboard en browser
xdg-open http://localhost:5000

# O desde otro terminal:
curl http://localhost:5000/health
```

**Expected:** Dashboard muestra precios en tiempo real, sin $0.00.

### **Paso 4: Audit Redis Keys**

```bash
# Copiar script al container
docker compose cp audit_redis_keys.py dashboard:/app/

# Ejecutar audit
docker compose exec dashboard python3 /app/audit_redis_keys.py
```

**Expected Output:**
```
🔍 REDIS KEYS AUDIT
===================
active_symbols: ['BTC', 'ETH', 'SOL', 'ADA', 'DOT']
price: keys: 5
market_regime: keys: 5

✅ NO DISCREPANCIES
```

---

## 🌐 OPCIÓN 2: DEPLOY GCP VM (Production)

### **Pre-requisitos**

1. Tener acceso SSH a la VM:
   ```bash
   ssh vm-trading-bot
   ```

2. Git configurado en VM:
   ```bash
   git config --global user.email "bot@trading.com"
   git config --global user.name "Trading Bot"
   ```

### **Paso 1: Pull Latest Code**

```bash
ssh vm-trading-bot
cd ~/trading-system-gcp

# Pull V21.3
git fetch origin main
git reset --hard origin/main
```

### **Paso 2: Clean Redis (Importante)**

```bash
# Detener servicios
docker compose down

# Limpiar Redis data (opcional, si quieres empezar limpio)
docker compose run --rm redis redis-cli FLUSHALL

# O solo eliminar keys obsoletas
docker compose run --rm redis redis-cli DEL active_symbols
docker compose run --rm redis redis-cli --scan --pattern "price:*" | xargs docker compose run --rm redis redis-cli DEL
```

### **Paso 3: Deploy V21.3**

```bash
# Build & Start
docker compose build --no-cache
docker compose up -d

# Verificar logs
docker compose logs -f --tail 50
```

### **Paso 4: Warm-up Verification**

```bash
# Esperar 30 segundos para warm-up
sleep 30

# Verificar Brain logs
docker compose logs brain | grep "WARM-UP COMPLETADO"
```

**Expected:**
```
🎯 WARM-UP COMPLETADO: 5 símbolos listos para trading
⚡ Sistema operativo en <10 segundos (vs 3.3 horas anterior)
```

### **Paso 5: Redis Audit (Production)**

```bash
# Ejecutar audit
docker compose exec dashboard python3 /app/audit_redis_keys.py

# O si no existe, crearlo:
docker compose cp audit_redis_keys.py dashboard:/app/
docker compose exec dashboard python3 /app/audit_redis_keys.py
```

### **Paso 6: Dashboard External Access**

Obtener IP externa de VM:
```bash
gcloud compute instances describe vm-trading-bot \
  --zone=us-central1-a \
  --format='get(networkInterfaces[0].accessConfigs[0].natIP)'
```

Abrir en browser:
```
http://[VM_EXTERNAL_IP]:5000
```

---

## 🧪 POST-DEPLOYMENT TESTING

### **Test Suite 1: Health Checks**

```bash
# Dashboard
curl http://localhost:5000/health
# Expected: "Market Data Hub v15.0 | Redis: ✅ Connected"

# Market Data
curl http://localhost:8080/
# Expected: "Market Data Hub ... | Monitoreando: [...]"
```

### **Test Suite 2: Data Integrity**

```bash
# Check realtime prices
curl http://localhost:5000/api/realtime_price/BTC
# Expected: {"symbol": "BTC", "price": 75200.50, ...}

# Check market regimes
curl http://localhost:5000/api/market_regimes
# Expected: {"BTC": {"regime": "bull_trend", ...}, ...}
```

### **Test Suite 3: Trading Simulation**

```bash
# Esperar 5 minutos para que Brain genere señales
sleep 300

# Ver señales generadas
docker compose logs brain | grep "📊 SIGNAL"

# Ver trades ejecutadas
docker compose logs orders | grep "✅ ORDER"
```

**Expected:**
```
📊 SIGNAL: BUY BTC @ $75200 | Strategy: RsiMeanReversion | Confidence: 0.85
✅ ORDER: Opened BUY BTC @ $75200 | Amount: $1000 | Stop Loss: $73696
```

---

## 📊 MONITORING CONTINUO

### **Script de Monitoreo (Opcional)**

```bash
# Crear script de monitoreo
cat > monitor_v21.3.sh <<'EOF'
#!/bin/bash

echo "========================================"
echo "V21.3 CANONICAL CORE - HEALTH MONITOR"
echo "========================================"

# 1. Check services
echo ""
echo "📦 SERVICES STATUS:"
docker compose ps

# 2. Check Redis keys
echo ""
echo "🔑 REDIS KEYS:"
docker compose exec -T redis redis-cli --scan --pattern "*" | wc -l
echo "   Total keys in Redis"

# 3. Check Brain activity
echo ""
echo "🧠 BRAIN ACTIVITY (Last 10 lines):"
docker compose logs brain --tail 10 | grep -E "SIGNAL|REGIME"

# 4. Check Wallet
echo ""
echo "💰 WALLET STATUS:"
docker compose exec -T dashboard python3 -c "
from src.shared.database import SessionLocal, Wallet
session = SessionLocal()
wallet = session.query(Wallet).order_by(Wallet.last_updated.desc()).first()
print(f'Balance: \${wallet.usdt_balance:.2f} | Equity: \${wallet.total_equity:.2f}')
session.close()
"

echo ""
echo "========================================"
echo "Monitoring completed at $(date)"
echo "========================================"
EOF

chmod +x monitor_v21.3.sh

# Ejecutar cada 5 minutos (opcional)
watch -n 300 ./monitor_v21.3.sh
```

---

## 🚨 TROUBLESHOOTING

### **Problema 1: Brain no hace warm-up**

**Síntoma:**
```
⚠️ No se encontraron active_symbols en Redis, usando canonical default
```

**Solución:**
```bash
# Verificar que Market Data esté corriendo
docker compose logs market-data --tail 20

# Verificar que active_symbols esté en Redis
docker compose exec redis redis-cli GET active_symbols

# Si está vacío, setearlo manualmente:
docker compose exec redis redis-cli SET active_symbols '["BTC","ETH","SOL","ADA","DOT"]'

# Restart Brain
docker compose restart brain
```

### **Problema 2: Dashboard muestra $0.00**

**Síntoma:** Dashboard carga pero precios son $0.00

**Solución:**
```bash
# Verificar keys de precio en Redis
docker compose exec redis redis-cli --scan --pattern "price:*"

# Si no hay keys, verificar Market Data:
docker compose logs market-data --tail 50 | grep "OHLCV"

# Si Market Data no está publicando, reiniciarlo:
docker compose restart market-data

# Esperar 60s y verificar:
docker compose exec redis redis-cli GET price:BTC
```

### **Problema 3: TypeError en TradingSymbol**

**Síntoma:**
```
TypeError: Symbol must be str, got <class 'NoneType'>
```

**Solución:**
```bash
# Verificar que active_symbols tenga valores válidos
docker compose exec redis redis-cli GET active_symbols

# Si tiene valores como ["btcusdt", "ethusdt"], está correcto
# Si tiene None o formato incorrecto, limpiarlo:
docker compose exec redis redis-cli DEL active_symbols

# Restart Market Data para re-popularlo:
docker compose restart market-data
```

---

## 🔄 ROLLBACK (Si es necesario)

Si V21.3 tiene problemas críticos, rollback a V21.2.1:

```bash
# 1. Bajar servicios
docker compose down

# 2. Checkout V21.2.1
git fetch origin main
git log --oneline -10  # Buscar commit V21.2.1
git reset --hard [COMMIT_HASH_V21.2.1]

# 3. Rebuild
docker compose build --no-cache

# 4. Start
docker compose up -d

# 5. Verificar
docker compose logs -f --tail 50
```

**Nota:** V21.3 es backward compatible con V21.2.1 (tests pasaron), así que rollback NO debería ser necesario.

---

## ✅ SUCCESS CRITERIA

Deploy es **exitoso** cuando:

1. ✅ Todos los servicios están `Up` (9/9)
2. ✅ Brain logs muestran `WARM-UP COMPLETADO` en < 30s
3. ✅ Dashboard muestra precios reales (no $0.00)
4. ✅ `audit_redis_keys.py` reporta `NO DISCREPANCIES`
5. ✅ Brain genera señales después de 5 minutos
6. ✅ Orders ejecuta trades (si hay señales)
7. ✅ No hay errores en `docker compose logs`

---

## 📈 NEXT STEPS (Post-Deployment)

1. **Monitoreo 24h:**
   - Ejecutar `monitor_v21.3.sh` cada 5 minutos
   - Verificar que Wallet equity crece (o se mantiene estable)

2. **Backup Base de Datos:**
   ```bash
   # Hacer backup de SQLite
   docker compose exec dashboard cp /app/src/data/trading_bot_v16.db /app/src/data/trading_bot_v16_backup_$(date +%Y%m%d).db
   ```

3. **Comenzar Planificación V22:**
   - Leer `V22_ROADMAP_WEBSOCKET_SQLALCHEMY.md`
   - Estimar timeline
   - Asignar recursos

---

## 📞 SUPPORT

Si encuentras problemas:

1. **Revisar logs:**
   ```bash
   docker compose logs [service_name] --tail 100
   ```

2. **Ejecutar tests:**
   ```bash
   python3 test_trading_symbol.py
   python3 verify_integrity_v21.2.1.py
   ```

3. **Redis audit:**
   ```bash
   docker compose exec dashboard python3 /app/audit_redis_keys.py
   ```

---

**Deploy preparado por:** HFT Trading Bot Team  
**Fecha:** 2026-02-08  
**Versión:** V21.3 "Canonical Core"  
**Status:** ✅ READY FOR PRODUCTION
