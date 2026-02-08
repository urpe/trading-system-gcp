# POST-DEPLOY VALIDATION CHECKLIST - V22.1.2

**Fecha:** 2026-02-08  
**Versión:** V22.1.2 "Post-Production Hardening"  
**Objetivo:** Validar que el sistema en producción está 100% funcional  

---

## ✅ CHECKLIST DE VALIDACIÓN INMEDIATA (T+5 min)

### **1. Servicios Running**

```bash
docker compose ps
```

**Esperado:**
- ✅ 10/10 servicios en estado "Up"
- ✅ Todos con uptime > 1 minuto
- ❌ Ninguno en estado "Restarting" o "Exited"

---

### **2. Commit Verification**

```bash
git log --oneline -1
```

**Esperado:**
```
d4be0d1 fix: V22.1.2 POST-PRODUCTION HARDENING - Dashboard Bugs Fixed
```

---

### **3. Health Score**

```bash
docker compose exec dashboard python3 /app/monitor_v21.3_health.py
```

**Esperado:**
- ✅ Overall Health Score: **>= 95/100**
- ✅ Services Running: **10/10**
- ✅ Brain Warm-up: **COMPLETED**
- ✅ Errors (last 5 min): **< 5 errors total**

**Criterios de Fallo:**
- ❌ Health Score < 90/100
- ❌ Services Running < 9/10
- ❌ Brain warm-up NOT completed
- ❌ Errors > 20 en 5 minutos

---

### **4. Error Detection (Dashboard)**

```bash
docker compose logs dashboard --since 5m | grep "ERROR"
```

**Esperado:**
- ✅ **Sin output** (cero errores)
- ✅ O máximo 1-2 errores legacy (de antes del restart)

**Buscar específicamente:**
```bash
docker compose logs dashboard --since 5m | grep "Invalid symbol\|not JSON serializable"
```

**Esperado:**
- ✅ **Sin output** (bugs V22.1.2 ya no deben aparecer)

---

### **5. Error Detection (Orders)**

```bash
docker compose logs orders --since 5m | grep "ERROR"
```

**Esperado:**
- ✅ **Sin output** (cero errores)

**Buscar específicamente el bug de stop-loss:**
```bash
docker compose logs orders --since 5m | grep "TypeError.*from_str"
```

**Esperado:**
- ✅ **Sin output** (bug V22.1.1 ya no debe aparecer)

---

### **6. Brain Signal Generation**

```bash
docker compose logs brain --since 10m | grep "SIGNAL"
```

**Esperado:**
- ✅ Al menos 1 signal generada en últimos 10 minutos
- ⚠️ Si no hay signals: OK si no hay oportunidades de trading

**Verificar warm-up:**
```bash
docker compose logs brain | grep "WARM-UP COMPLETADO"
```

**Esperado:**
```
🎯 WARM-UP COMPLETADO: 5 símbolos listos para trading
```

---

### **7. Dashboard Web Access**

```bash
# Obtener IP externa
curl -s http://checkip.amazonaws.com
```

**Luego abrir en navegador:**
```
http://[IP-EXTERNA]:5007
```

**Validar:**
- ✅ Página carga sin errores 500
- ✅ Equity chart visible
- ✅ Tabla de posiciones carga
- ✅ Historial de signals carga

**Navegación detallada:**
- ✅ `/asset/BTC` - Carga sin errores
- ✅ `/asset/ETH` - Carga sin errores
- ✅ `/pairs` - Carga sin errores
- ✅ `/download_trades` - Descarga Excel

---

### **8. Redis Integrity**

```bash
docker compose exec dashboard python3 /app/audit_redis_keys.py
```

**Esperado:**
```
✅ Symbol Normalization Check: PASSED
✅ All price:* keys match active_symbols format
✅ No orphaned keys detected
```

---

### **9. Database Integrity**

```bash
docker compose exec dashboard python3 << 'EOF'
from src.shared.database import SessionLocal, Trade, Signal, MarketSnapshot
from src.domain import TradingSymbol

session = SessionLocal()

# Check trades
trades = session.query(Trade).limit(5).all()
print("Recent Trades:")
for t in trades:
    print(f"  - {t.symbol} (type: {type(t.symbol).__name__})")

# Check signals
signals = session.query(Signal).limit(5).all()
print("\nRecent Signals:")
for s in signals:
    print(f"  - {s.symbol} (type: {type(s.symbol).__name__})")

session.close()
EOF
```

**Esperado:**
```
Recent Trades:
  - TradingSymbol(base='BTC', quote='USDT') (type: TradingSymbol)
  ...

Recent Signals:
  - TradingSymbol(base='ETH', quote='USDT') (type: TradingSymbol)
  ...
```

**Criterio de Éxito:**
- ✅ Todos los símbolos son de tipo `TradingSymbol`
- ❌ Si aparecen strings, la migración no se aplicó

---

## 📊 CHECKLIST DE MONITOREO CONTINUO (T+1h, T+6h, T+24h)

### **Cada 1 hora (primeras 6 horas):**

```bash
# Quick check
docker compose exec dashboard python3 /app/monitor_v21.3_health.py | tail -20
```

**Anotar:**
- Health Score: ___/100
- Errors: ___
- Signals generadas: ___
- Trades ejecutadas: ___

---

### **Cada 6 horas (primeras 24 horas):**

```bash
# Full health check
docker compose exec dashboard python3 /app/monitor_v21.3_health.py

# Error log
docker compose logs --since 6h | grep "ERROR" | wc -l

# Trading activity
docker compose logs brain --since 6h | grep "SIGNAL" | wc -l
docker compose logs orders --since 6h | grep "EXECUTED" | wc -l
```

**Anotar:**
- Total errors (6h): ___
- Total signals (6h): ___
- Total trades (6h): ___

---

### **A las 24 horas:**

```bash
# Generate full report
docker compose exec dashboard python3 /app/monitor_v21.3_health.py --save

# PnL check
docker compose exec dashboard python3 << 'EOF'
from src.shared.database import SessionLocal, Trade
session = SessionLocal()
trades = session.query(Trade).filter(Trade.status == 'CLOSED').all()
total_pnl = sum([t.pnl for t in trades if t.pnl])
print(f"Total PnL (24h): ${total_pnl:.2f}")
session.close()
EOF
```

---

## 🚨 TROUBLESHOOTING GUIDE

### **Problema: Health Score < 90/100**

**Diagnóstico:**
```bash
docker compose logs --since 30m | grep "ERROR" | head -50
```

**Acción:**
1. Identificar servicio con errores
2. Reintentar restart del servicio:
   ```bash
   docker compose restart [service-name]
   ```
3. Si persiste, revisar logs detallados

---

### **Problema: Dashboard con errores "Invalid symbol"**

**Diagnóstico:**
```bash
docker compose logs dashboard --since 10m | grep "Invalid symbol"
```

**Acción:**
1. Verificar que el rebuild se aplicó:
   ```bash
   docker compose exec dashboard python3 -c "import src.services.dashboard.app; print('V22.1.2' if 'isinstance' in open('/app/src/services/dashboard/app.py').read() else 'OLD VERSION')"
   ```
2. Si muestra "OLD VERSION":
   ```bash
   docker compose build dashboard --no-cache
   docker compose restart dashboard
   ```

---

### **Problema: JSON Serialization Errors**

**Diagnóstico:**
```bash
docker compose logs dashboard --since 10m | grep "not JSON serializable"
```

**Acción:**
1. Rollback temporal:
   ```bash
   docker compose down
   git reset --hard 6480a68  # V22.1.1 (antes del error)
   docker compose build --no-cache
   docker compose up -d
   ```
2. Reportar issue para análisis

---

### **Problema: Stop-Loss Worker TypeError**

**Diagnóstico:**
```bash
docker compose logs orders --since 10m | grep "TypeError"
```

**Acción:**
1. Verificar versión de orders:
   ```bash
   docker compose exec orders python3 -c "import src.services.orders.main; print('V22.1.1+' if 'isinstance(symbol, str)' in open('/app/src/services/orders/main.py').read() else 'OLD VERSION')"
   ```
2. Si muestra "OLD VERSION":
   ```bash
   docker compose build orders --no-cache
   docker compose restart orders
   ```

---

## 📝 LOG TEMPLATE (Copiar y completar cada check)

```markdown
# V22.1.2 Production Deployment Validation

**Date:** 2026-02-08
**Deployer:** [Your Name]
**VM:** vm-trading-bot

## T+5 Minutes Check
- [ ] Services: ___/10 Up
- [ ] Commit: d4be0d1 verified
- [ ] Health Score: ___/100
- [ ] Dashboard errors: ___ (expected 0)
- [ ] Orders errors: ___ (expected 0)
- [ ] Dashboard web: Accessible (Y/N)

## T+1 Hour Check
- [ ] Health Score: ___/100
- [ ] Total errors: ___
- [ ] Signals generated: ___
- [ ] Trades executed: ___

## T+6 Hours Check
- [ ] Health Score: ___/100
- [ ] Total errors (6h): ___
- [ ] Signals (6h): ___
- [ ] Trades (6h): ___

## T+24 Hours Check
- [ ] Health Score: ___/100
- [ ] Total PnL: $___
- [ ] System stable: (Y/N)

## Status: ✅ SUCCESS / ⚠️ ISSUES / ❌ ROLLBACK REQUIRED
```

---

## ✅ SUCCESS CRITERIA

### **Deploy se considera EXITOSO si:**

1. ✅ Health Score >= 95/100 en primeras 6 horas
2. ✅ Dashboard accesible sin errores 500
3. ✅ Cero errores de "Invalid symbol" o "not JSON serializable"
4. ✅ Brain genera signals (al menos 1 en 24h)
5. ✅ Orders ejecuta trades sin TypeError
6. ✅ Database muestra `TradingSymbol` objects (no strings)

### **Deploy requiere ROLLBACK si:**

1. ❌ Health Score < 80/100 por más de 1 hora
2. ❌ Dashboard crashea constantemente (> 10 errores/hora)
3. ❌ Orders service no ejecuta trades por bugs
4. ❌ Database corrupta o inconsistente
5. ❌ Brain no genera signals por 6 horas consecutivas (con mercado activo)

---

**Última Actualización:** 2026-02-08 09:20 UTC  
**Autor:** HFT Trading Bot Team
