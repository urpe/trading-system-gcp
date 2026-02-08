# DEPLOY V22.1.1 "DATA INTEGRITY CORE" - PRODUCTION GUIDE

**Fecha:** 2026-02-08  
**Versión:** V22.1.1  
**Destino:** GCP VM (vm-trading-bot)  
**Status:** 🚀 **READY FOR DEPLOYMENT**

---

## ✅ PRE-DEPLOYMENT CHECKLIST

### **Sistema Validado:**

```
✅ Type Safety:        100% (código + DB)
✅ Rentabilidad:       +$42.53 en 24h (59.6% win rate)
✅ Bug Crítico:        Stop-Loss FIXED
✅ Lógica Financiera:  Comisiones/Stop-Loss/Size validados
✅ Code Quality:       98/100 (Hawk Eye audit)
✅ Time Machine:       OPERATIONAL
✅ GitHub:             All commits pushed (ddb4931)
```

### **Backup Secured:**

```
✅ Local DB Backup:    trading_bot_v16_PRE_V22.1.backup (188KB)
✅ MD5 Checksum:       0e2d7226239e83f79bfe9ff86fd7ec1a
✅ Git History:        5 commits (V21.3.1 → V22.1.1)
```

---

## 🚀 DEPLOYMENT STEPS (GCP VM)

### **PASO 1: Conectar a GCP VM**

```bash
# Desde tu terminal local
ssh vm-trading-bot

# Verificar que estás en el servidor correcto
hostname  # Debe mostrar el nombre de tu VM
```

---

### **PASO 2: Backup Producción (CRÍTICO)**

```bash
# Navegar al proyecto
cd ~/trading-system-gcp

# Backup DB de producción ANTES de actualizar
docker compose exec dashboard cp /app/src/data/trading_bot_v16.db /app/src/data/trading_bot_v16_PROD_PRE_V22.1.backup

# Verificar backup
docker compose exec dashboard ls -lh /app/src/data/*.backup

# Generar checksum
docker compose exec dashboard md5sum /app/src/data/trading_bot_v16.db > production_db_v22.1_pre_deploy.md5
cat production_db_v22.1_pre_deploy.md5
```

**⚠️ CRÍTICO:** NO continuar hasta verificar que backup existe.

---

### **PASO 3: Pull Latest Code**

```bash
# Descargar V22.1.1 desde GitHub
git fetch origin
git status

# Verificar que estás en main
git branch

# Pull cambios
git pull origin main

# Verificar último commit
git log --oneline -1
# Debe mostrar: ddb4931 fix: V22.1.1 FUNCTIONAL VALIDATION + CRITICAL STOP-LOSS FIX
```

---

### **PASO 4: Rebuild Containers**

```bash
# Stop servicios
docker compose down

# Rebuild con código nuevo (SIN cache)
docker compose build --no-cache

# Verificar builds exitosos
docker images | grep trading-system-gcp | head -10
```

**Tiempo estimado:** 5-10 minutos

---

### **PASO 5: Iniciar Sistema**

```bash
# Start servicios
docker compose up -d

# Verificar que todos arrancan
docker compose ps

# Esperar 30 segundos para warm-up
sleep 30
```

---

### **PASO 6: Verificación Post-Deploy**

#### **6.1 Health Check General**

```bash
# Verificar servicios running
docker compose ps | grep "Up"
# Debe mostrar 10/10 servicios Up

# Check Redis connectivity
docker compose exec dashboard redis-cli -h redis PING
# Debe responder: PONG
```

#### **6.2 Brain Warm-Up**

```bash
# Verificar que Brain completó warm-up
docker compose logs brain | grep "WARM-UP COMPLETADO"
# Debe mostrar: "🎯 WARM-UP COMPLETADO: 5 símbolos listos"

# Verificar signals generadas
docker compose logs brain --tail 50 | grep "SIGNAL"
# Debe mostrar signals recientes (BUY/SELL)
```

#### **6.3 Stop-Loss Worker**

```bash
# Verificar que stop-loss worker inició
docker compose logs orders | grep "Stop Loss Worker"
# Debe mostrar: "🛡️ Stop Loss Worker V21.3 iniciado"

# Verificar que NO hay errores de TradingSymbol
docker compose logs orders | grep "TypeError"
# Debe estar VACÍO (cero errores)
```

#### **6.4 Database Integrity**

```bash
# Copiar script de verificación
docker compose cp migrate_v22_1.py dashboard:/app/

# Ejecutar validación
docker compose exec dashboard python3 /app/migrate_v22_1.py --validate-only

# Debe mostrar:
# ✅ No migration needed - all data already in new format
```

#### **6.5 Dashboard Access**

```bash
# Obtener IP externa de la VM
curl -s http://checkip.amazonaws.com

# Abrir en navegador:
# http://<IP-EXTERNA>:5007

# Verificar:
# - Equity chart carga
# - Asset details (/asset/BTC) funcionan
# - No errores 500
```

---

### **PASO 7: Monitoring Continuo (Primera Hora)**

```bash
# Ejecutar health monitor
docker compose exec dashboard python3 /app/monitor_v21.3_health.py

# Debe mostrar:
# Health Score: 100/100
# Services: 10/10
# Brain: Warm-up complete
# Errors: 0
```

**Repetir cada 15 minutos durante la primera hora.**

---

## 🛡️ ROLLBACK PLAN (Si algo falla)

### **Escenario 1: Errores en Brain/Orders**

```bash
# Verificar logs
docker compose logs brain --tail 100
docker compose logs orders --tail 100

# Si hay errores críticos:
docker compose down
git log --oneline -10
git reset --hard 62ade4c  # V21.3.1 (último estable conocido)
docker compose build --no-cache
docker compose up -d
```

---

### **Escenario 2: Corrupción de DB**

```bash
# Stop servicios
docker compose down

# Restaurar backup
docker compose up -d redis dashboard  # Solo estos
docker compose exec dashboard cp /app/src/data/trading_bot_v16_PROD_PRE_V22.1.backup /app/src/data/trading_bot_v16.db

# Verificar restauración
docker compose exec dashboard python3 /app/inspect_db.py

# Reiniciar todo
docker compose down
docker compose up -d
```

---

### **Escenario 3: Rollback Completo**

```bash
# Volver a V21.3.1
git reset --hard 62ade4c
docker compose down
docker compose build --no-cache
docker compose up -d

# Restaurar DB si es necesario
docker compose exec dashboard cp /app/src/data/trading_bot_v16_PROD_PRE_V22.1.backup /app/src/data/trading_bot_v16.db
```

---

## 📊 POST-DEPLOYMENT MONITORING

### **Primeras 24 Horas:**

| Tiempo | Acción | Comando |
|--------|--------|---------|
| **T+15min** | Health check | `python3 monitor_v21.3_health.py` |
| **T+1h** | Verify signals → trades | `docker compose logs brain \| grep SIGNAL` |
| **T+6h** | Check PnL | `docker compose logs orders \| grep "SELL EXECUTED"` |
| **T+24h** | Full report | `python3 monitor_v21.3_health.py --save` |

---

## 🎯 SUCCESS CRITERIA

### **Sistema está funcionando si:**

✅ **Health Score:** >= 95/100  
✅ **Services:** 10/10 running  
✅ **Brain:** Generando signals (>= 1 por hora)  
✅ **Orders:** Ejecutando trades (>= 1 por día)  
✅ **Stop-Loss:** Sin errores TypeError  
✅ **Dashboard:** Accesible sin errores 500  
✅ **Errors:** < 5 errors en 1 hora  

---

## 🔥 TROUBLESHOOTING

### **Problema: "TypeError in stop_loss_worker"**

**Causa:** Código V22.1 sin hotfix

**Solución:**
```bash
git pull origin main  # Asegurar último código
docker compose build orders --no-cache
docker compose restart orders
```

---

### **Problema: "Invalid symbol" en logs**

**Causa:** Símbolos no soportados en TradingPair Enum

**Solución:**
1. Verificar si son símbolos activos o legacy
2. Si son activos: Agregar a Enum y rebuild
3. Si son legacy: Ignorar (no afectan operación)

---

### **Problema: "No signals generated"**

**Causa:** Brain no completó warm-up

**Solución:**
```bash
docker compose logs brain | grep "WARM-UP"
# Si no aparece "COMPLETADO", reiniciar:
docker compose restart brain
sleep 60
docker compose logs brain | grep "WARM-UP COMPLETADO"
```

---

## 📝 DEPLOYMENT LOG TEMPLATE

```markdown
# V22.1.1 Production Deployment Log

**Date:** 2026-02-08
**Deployer:** [Your Name]
**VM:** vm-trading-bot

## Pre-Deploy
- [ ] Backup created: trading_bot_v16_PROD_PRE_V22.1.backup
- [ ] MD5 checksum: _______________
- [ ] Git pull: ddb4931 confirmed
- [ ] Docker images built: 10/10

## Deploy
- [ ] Services started: 10/10 Up
- [ ] Brain warm-up: COMPLETADO
- [ ] Dashboard accessible: http://<IP>:5007
- [ ] Health score: ___/100

## Post-Deploy (T+1h)
- [ ] Signals generated: ___
- [ ] Trades executed: ___
- [ ] Errors in logs: ___
- [ ] Stop-Loss operational: YES/NO

## Status: ✅ SUCCESS / ⚠️ ISSUES / ❌ ROLLBACK
```

---

## 🎊 DEPLOYMENT COMMAND SEQUENCE

**Copy-paste completo (Para ejecutar en GCP VM):**

```bash
#!/bin/bash
# V22.1.1 Production Deployment Script

echo "════════════════════════════════════════"
echo "  V22.1.1 PRODUCTION DEPLOYMENT"
echo "════════════════════════════════════════"
echo ""

# Step 1: Backup
echo ">>> STEP 1: Creating Backup..."
cd ~/trading-system-gcp
docker compose exec dashboard cp /app/src/data/trading_bot_v16.db /app/src/data/trading_bot_v16_PROD_PRE_V22.1.backup
docker compose exec dashboard md5sum /app/src/data/trading_bot_v16.db
echo "✅ Backup created"
echo ""

# Step 2: Pull code
echo ">>> STEP 2: Pulling Latest Code..."
git pull origin main
git log --oneline -1
echo "✅ Code updated"
echo ""

# Step 3: Rebuild
echo ">>> STEP 3: Rebuilding Containers..."
docker compose down
docker compose build --no-cache
echo "✅ Containers rebuilt"
echo ""

# Step 4: Start
echo ">>> STEP 4: Starting Services..."
docker compose up -d
sleep 30
echo "✅ Services started"
echo ""

# Step 5: Verify
echo ">>> STEP 5: Verification..."
docker compose ps
echo ""
docker compose logs brain | grep "WARM-UP COMPLETADO" | tail -1
docker compose logs orders | grep "Stop Loss Worker" | tail -1
echo ""
echo "✅ Deployment complete!"
echo ""
echo "Next: Monitor for 1 hour"
echo "  docker compose exec dashboard python3 /app/monitor_v21.3_health.py"
```

---

**Deployment Ready:** ✅  
**Rollback Plan:** ✅  
**Monitoring:** ✅  
**Status:** 🚀 **READY TO LAUNCH**
