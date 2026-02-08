# V21.3 MONITORING CHECKLIST - 24h/48h/72h

**Sistema:** V21.3 "Canonical Core"  
**Fecha Inicio:** 2026-02-08  
**Laboratorio:** Local (antes de producción)

---

## 🎯 OBJETIVO

Monitorear V21.3 en entorno controlado (local) durante 72 horas para detectar:
- Memory leaks
- Performance degradation
- Data integrity issues
- Edge cases no capturados en tests

---

## 📊 SCHEDULE DE CHECKS

```
T+0h  (HOY)      → Deploy + Initial Check
T+1h             → Quick Check
T+6h             → Extended Check
T+24h (MAÑANA)   → Full Health Check ✅
T+48h            → Full Health Check ✅
T+72h            → Final Health Check + Decision ✅
```

---

## ✅ CHECKLIST: T+0h (DEPLOY INICIAL)

### **Pre-Deploy**
- [ ] Backup de base de datos actual
- [ ] `git pull origin main` (asegurar código actualizado)
- [ ] `docker compose down` (limpiar servicios anteriores)
- [ ] Limpiar Redis (opcional): `docker compose exec redis redis-cli FLUSHALL`

### **Deploy**
```bash
cd /home/jhersonurpecanchanya/trading-system-gcp

# Build (si necesario)
docker compose build

# Start services
docker compose up -d

# Wait 30s for warm-up
sleep 30

# Run initial health check
python3 monitor_v21.3_health.py
```

### **Verificaciones Iniciales**
- [ ] Todos los servicios corriendo (9/9)
- [ ] Brain warm-up completado (< 60s)
- [ ] Redis keys creadas (`active_symbols`, `price:*`)
- [ ] Dashboard accesible: http://localhost:5000
- [ ] No errores críticos en logs

**Baseline Metrics (Guardar para comparar):**
```
Services Running: ____/9
Memory Usage (Brain): ______ MB
Memory Usage (Market Data): ______ MB
CPU Usage (Brain): ______%
Redis Keys Count: ______
Health Score: ____/100
```

---

## ✅ CHECKLIST: T+1h (QUICK CHECK)

### **Ejecutar:**
```bash
python3 monitor_v21.3_health.py
```

### **Verificar:**
- [ ] Servicios siguen corriendo (9/9)
- [ ] No hay memory leak (comparar con baseline)
- [ ] Signals generadas (Brain logs): `docker compose logs brain | grep "📊 SIGNAL"`
- [ ] Trades ejecutadas (Orders logs): `docker compose logs orders | grep "✅ ORDER"`

**Métricas T+1h:**
```
Memory Growth: ______ MB (vs baseline)
CPU Stable: YES / NO
New Signals: ______
New Trades: ______
Errors: ______
```

---

## ✅ CHECKLIST: T+6h (EXTENDED CHECK)

### **Ejecutar:**
```bash
python3 monitor_v21.3_health.py --save  # Save report
```

### **Análisis Profundo:**

#### **1. Memory Leak Detection**
```bash
# Check memory trend
docker stats --no-stream | grep trading-system

# Compare with baseline - should be stable, not growing linearly
```

Expected: Memory < 200MB per service, no growth > 10% per hour

#### **2. TradingSymbol Performance**
```bash
# Check Brain logs for conversion times
docker compose logs brain | grep "TradingSymbol" | tail -50

# Should not see "slow" or "timeout" messages
```

#### **3. Database Integrity**
```bash
# Check trades in DB
docker compose exec -T dashboard python3 -c "
from src.shared.database import SessionLocal, Trade
session = SessionLocal()
print(f'Total trades: {session.query(Trade).count()}')
session.close()
"
```

#### **4. Redis Key Consistency**
```bash
# Run audit
docker compose cp audit_redis_keys.py dashboard:/app/
docker compose exec dashboard python3 /app/audit_redis_keys.py
```

Expected: No discrepancies, all keys valid format

**Métricas T+6h:**
```
Memory Growth Rate: ______% per hour
Signals Generated: ______
Trades Executed: ______
Database Trades: ______
Redis Discrepancies: ______
Health Score: ____/100
```

---

## ✅ CHECKLIST: T+24h (FULL HEALTH CHECK) ⭐

**Fecha:** __________ (Mañana)

### **Ejecutar:**
```bash
cd /home/jhersonurpecanchanya/trading-system-gcp

# Full health check with report
python3 monitor_v21.3_health.py --save

# Check log file sizes (detect excessive logging)
docker compose logs brain --tail 0 | wc -l
docker compose logs market-data --tail 0 | wc -l
```

### **Verificaciones Críticas:**

#### **1. Stability Check**
- [ ] Todos los servicios corriendo sin restart (uptime > 24h)
- [ ] No core dumps o crashes
- [ ] Memory usage estable (< 10% growth en 24h)
- [ ] CPU usage promedio < 50%

#### **2. Data Integrity**
- [ ] Redis keys consistentes (`audit_redis_keys.py` sin errores)
- [ ] Database sin corrupción (todos los trades parseables)
- [ ] No missing data (all symbols have prices)

#### **3. Trading Performance**
- [ ] Signals generadas (> 10 en 24h esperado)
- [ ] Trades ejecutadas (si hay signals)
- [ ] Wallet balance coherente (no duplicates, no negative)

#### **4. Error Analysis**
```bash
# Count errors per service (last 24h)
for service in brain market-data dashboard orders; do
  echo "=== $service ==="
  docker compose logs $service --since 24h | grep -i "error\|exception" | wc -l
done
```

Expected: < 5 errors per service en 24h

**Métricas T+24h:**
```
Uptime: ______ hours
Memory Usage (Brain): ______ MB (Growth: ______%)
Memory Usage (Market Data): ______ MB (Growth: ______%)
CPU Average: ______%
Signals Generated: ______
Trades Executed: ______
Errors (Brain): ______
Errors (Market Data): ______
Errors (Dashboard): ______
Errors (Orders): ______
Health Score: ____/100
```

### **Decision Point 1:**
- ✅ **Si Health Score >= 90 y no errors críticos:** Continuar a T+48h
- ⚠️ **Si Health Score 70-89 o < 10 errors:** Investigar logs, continuar
- ❌ **Si Health Score < 70 o > 20 errors:** STOP, analizar y fix

---

## ✅ CHECKLIST: T+48h (FULL HEALTH CHECK) ⭐

**Fecha:** __________ (Pasado mañana)

### **Ejecutar:**
```bash
python3 monitor_v21.3_health.py --save
```

### **Análisis de Tendencias:**

#### **1. Compare T+24h vs T+48h**
- [ ] Memory growth lineal o estable (estable = good)
- [ ] No degradación de performance
- [ ] Error rate estable o decrece

#### **2. Longevity Test**
- [ ] Services corriendo > 48h sin restart
- [ ] Brain warm-up solo ocurrió 1 vez (al inicio)
- [ ] No database locks o conflicts

#### **3. Real-World Conditions**
- [ ] Sistema manejó diferentes market conditions (pump, dump, sideways)
- [ ] Stop-loss activado correctamente (si hubo pérdidas)
- [ ] Multi-symbol trading funciona (no solo BTC)

**Métricas T+48h:**
```
Uptime: ______ hours
Memory Growth (24h → 48h): ______%
Signals Generated (total): ______
Trades Executed (total): ______
Win Rate: ______% (profitable trades / total)
Errors (total 48h): ______
Health Score: ____/100
```

### **Decision Point 2:**
- ✅ **Si Health Score >= 85 y tendencias estables:** Continuar a T+72h (final)
- ⚠️ **Si Health Score < 85:** Revisar logs, considerar ajustes menores
- ❌ **Si errores crecientes o memory leak:** STOP, rollback a V21.2.1

---

## ✅ CHECKLIST: T+72h (FINAL HEALTH CHECK + DECISION) ⭐⭐⭐

**Fecha:** __________

### **Ejecutar:**
```bash
# Final comprehensive check
python3 monitor_v21.3_health.py --save

# Generate final report
docker compose logs --since 72h > full_logs_72h.txt
```

### **Final Analysis:**

#### **1. Stability Verdict**
- [ ] Services corriendo 72h sin crashes
- [ ] Memory usage < 500MB por servicio
- [ ] CPU promedio < 40%
- [ ] No performance degradation

#### **2. Functionality Verdict**
- [ ] Trading logic funciona (signals → trades → wallet updates)
- [ ] Type safety sin errores (TradingSymbol conversions OK)
- [ ] Dashboard muestra datos correctos (no $0.00)
- [ ] Stop-loss funciona (si aplicable)

#### **3. Quality Metrics**
- [ ] Total signals: ______ (esperado > 30 en 72h)
- [ ] Total trades: ______ (esperado > 10 en 72h)
- [ ] Win rate: ______% (esperado > 45%)
- [ ] Errors: ______ (esperado < 20 total)

**Métricas Finales T+72h:**
```
=== SYSTEM STABILITY ===
Uptime: 72 hours
Crashes: ______ (esperado: 0)
Restarts: ______ (esperado: 0)
Memory Leak: YES / NO (esperado: NO)

=== TRADING PERFORMANCE ===
Signals Generated: ______
Trades Executed: ______
Win Rate: ______%
Wallet Balance: $______ USDT
Total PnL: $______ (esperado: positivo o -2% max)

=== DATA INTEGRITY ===
Redis Discrepancies: ______ (esperado: 0)
Database Trades: ______
Symbol Parsing Errors: ______ (esperado: 0)

=== FINAL HEALTH SCORE ===
Score: ____/100
```

---

## 🎯 DECISION MATRIX (T+72h)

### **Scenario A: EXCELLENT (Score >= 90)**
✅ **ACCIÓN:** Deploy a GCP VM (Producción)

**Criterios cumplidos:**
- Zero crashes
- Memory stable
- Win rate > 50%
- < 10 errors total

**Próximo paso:**
1. Crear snapshot de DB actual (backup)
2. Deploy a GCP VM: `ssh vm-trading-bot && cd ~/trading-system-gcp && git pull origin main && ./deploy_prod.sh`
3. Monitorear producción: 24h, 48h, 72h (repetir checklist)

---

### **Scenario B: GOOD (Score 70-89)**
⚠️ **ACCIÓN:** Análisis de issues + Deploy con precaución

**Criterios:**
- 1-2 crashes (recuperables)
- Memory growth < 20%
- Win rate 40-50%
- 10-20 errors (no críticos)

**Próximo paso:**
1. Revisar logs de errores: `docker compose logs > all_logs.txt`
2. Fix issues menores (si identificables)
3. Repetir T+72h (extend a T+96h)
4. Si mejora → Deploy a producción
5. Si no mejora → Considerar rollback

---

### **Scenario C: DEGRADED (Score 50-69)**
⚠️ **ACCIÓN:** Investigación profunda + NO deploy

**Criterios:**
- 3-5 crashes
- Memory leak evidente
- Win rate < 40%
- > 20 errors

**Próximo paso:**
1. NO DEPLOY A PRODUCCIÓN
2. Análisis de root cause: revisar logs line-by-line
3. Identificar patrón de errores
4. Fix issues críticos
5. Restart test desde T+0h (nuevo ciclo 72h)

---

### **Scenario D: CRITICAL (Score < 50)**
❌ **ACCIÓN:** ROLLBACK a V21.2.1

**Criterios:**
- > 5 crashes
- Memory leak severo (> 1GB)
- Win rate < 30%
- > 50 errors

**Próximo paso:**
1. **STOP INMEDIATAMENTE**
2. Rollback: `git reset --hard [V21.2.1_COMMIT_HASH]`
3. Deploy V21.2.1: `docker compose down && docker compose build && docker compose up -d`
4. Postmortem analysis: documentar qué falló
5. Re-diseñar V21.3 con fixes
6. Reintentar cuando fixes aplicados

---

## 📝 LOGS & REPORTS

### **Archivos Generados:**
```
health_report_20260208_HHMMSS.json  (cada check)
full_logs_72h.txt                    (T+72h final)
```

### **Almacenar en:**
```
/home/jhersonurpecanchanya/trading-system-gcp/monitoring_reports/
```

### **Commit Reports:**
```bash
# Al finalizar T+72h
git add monitoring_reports/
git commit -m "chore: V21.3 72h monitoring complete - [RESULT]"
git push origin main
```

---

## 🎓 LESSONS LEARNED (Llenar al final)

### **¿Qué funcionó bien?**
- 
- 
- 

### **¿Qué necesita mejora?**
- 
- 
- 

### **¿Qué no esperábamos?**
- 
- 
- 

### **¿Recomendaciones para V22.1?**
- 
- 
- 

---

**IMPORTANTE:** Este es un proceso de **aprendizaje e iteración**. Los errores son bienvenidos en laboratorio, NO en producción.

---

**Checklist preparado:** 2026-02-08  
**Autor:** HFT Trading Bot Team  
**Status:** ⏳ PENDING EXECUTION
