# 🚀 INSTRUCCIONES PARA DEPLOYMENT EN PRODUCCIÓN V21.2

**Estado:** ✅ TODO LISTO EN GITHUB
**Commits:** 8 commits pusheados (último: b82b8d5)
**Scripts:** deploy_production_v21.2.sh (automatizado)
**Testing Local:** ✅ ALL PASS

---

## ⚠️ IMPORTANTE: DEBES EJECUTAR ESTOS COMANDOS TÚ

El asistente AI **NO tiene acceso SSH** a tu VM de GCP (`vm-trading-bot`).

**Tú necesitas:**
1. Abrir una terminal en tu máquina local
2. Conectarte a tu VM de GCP
3. Ejecutar los comandos abajo

---

## 🎯 OPCIÓN 1: DEPLOYMENT AUTOMATIZADO (RECOMENDADO)

### Paso 1: Conectar a la VM

Abre una terminal en tu PC y ejecuta:

```bash
ssh vm-trading-bot
```

Si te pide password o key, ingrésalo.

---

### Paso 2: Navegar al proyecto

```bash
cd trading-system-gcp
```

---

### Paso 3: Pull de cambios V21.2

```bash
git pull origin main
```

**Verificación:** Debe descargar los últimos 8 commits.

Ejecuta para confirmar:

```bash
git log --oneline -8
```

**Debes ver:**
```
b82b8d5 feat: Add automated production deployment script V21.2
9850f72 docs: Session complete summary V21.2
6feaf16 docs: Add comprehensive local testing results V21.2
f4c20f4 fix: Remove duplicate code in get_market_regimes (IndentationError)
1532a24 docs: V21.2 Implementation Complete Report
1883599 feat: V21.2 Additional Fixes + Production Tools
95339fb docs: Add V21.2 Executive Summary
e2ec024 feat: V21.2 SYNCHRONIZED ARCHITECTURE - Critical Fixes
```

---

### Paso 4: Ejecutar script automatizado

```bash
chmod +x deploy_production_v21.2.sh
./deploy_production_v21.2.sh
```

El script te guiará paso a paso:
- ✅ Verifica git status
- ✅ Ejecuta `./deploy_prod.sh`
- ✅ Verifica warm-up del Brain
- ✅ Ejecuta audit de Redis
- ✅ Verifica Dashboard API
- ✅ Muestra resumen final

**Duración estimada:** 10 minutos

---

## 🎯 OPCIÓN 2: COMANDOS MANUALES (SI PREFIERES CONTROL TOTAL)

Si prefieres ejecutar paso a paso manualmente:

### 1. Conectar a VM

```bash
ssh vm-trading-bot
cd trading-system-gcp
```

### 2. Pull de cambios

```bash
git pull origin main
```

### 3. Deployment

```bash
./deploy_prod.sh
```

Espera 2-3 minutos mientras rebuild los containers.

### 4. Verificar Warm-up

```bash
docker compose logs brain | grep "WARM-UP COMPLETADO"
```

**Debe mostrar:**
```
🎯 WARM-UP COMPLETADO: 5 símbolos listos para trading
   ⚡ Sistema operativo en <10 segundos
```

### 5. Auditoría de Redis

```bash
docker compose cp audit_redis_keys.py dashboard:/app/
docker compose exec dashboard python /app/audit_redis_keys.py
```

**Debe mostrar:**
```
🎉 ¡SISTEMA PERFECTO! Arquitectura V21.2 sincronizada correctamente
   ✅ active_symbols → price:* keys: SYNC
   ✅ active_symbols → market_regime:* keys: SYNC
```

### 6. Verificar Dashboard API

```bash
curl -s http://localhost:8050/api/dashboard-data | python3 -m json.tool | head -30
```

**Debe mostrar:**
- `total_equity`: (número > 0, NO $0.00)
- `scanner`: ["BTC", "ETH", "SOL", "TRX", "LINK"]

### 7. Estado de servicios

```bash
docker compose ps
```

**Debe mostrar:** 10 containers "Up"

---

## 📊 RESULTADO ESPERADO

Al final del deployment, debes ver:

```
════════════════════════════════════════════════════════════════
  🎉 DEPLOYMENT V21.2 COMPLETADO
════════════════════════════════════════════════════════════════

✅ FASE 1: Preparación ......................... COMPLETADO
✅ FASE 2: Pull cambios V21.2 .................. COMPLETADO
✅ FASE 3: Deployment (rebuild) ................ COMPLETADO
✅ FASE 4: Warm-up verification ................ VERIFICADO
✅ FASE 5: Redis audit ......................... EJECUTADO
✅ FASE 6: Dashboard API ....................... VERIFICADO
✅ FASE 7: Services status ..................... VERIFICADO

════════════════════════════════════════════════════════════════
     🚀 V21.2 SYNCHRONIZED ARCHITECTURE - PRODUCTION READY
════════════════════════════════════════════════════════════════
```

---

## 🔍 MONITOREO CONTINUO (OPCIONAL)

Una vez verificado que todo funciona, puedes iniciar el monitor 24/7:

```bash
screen -S redis-monitor
./continuous_redis_monitor.sh
```

Para detach: `Ctrl+A`, luego `D`

Para volver: `screen -r redis-monitor`

---

## ❓ TROUBLESHOOTING

### Problema: "git pull" no descarga nada

**Solución:**
```bash
git fetch origin
git reset --hard origin/main
```

### Problema: "deploy_prod.sh: Permission denied"

**Solución:**
```bash
chmod +x deploy_prod.sh deploy_production_v21.2.sh
```

### Problema: Container "dashboard" no sube

**Solución:**
```bash
docker compose logs dashboard
# Buscar error de sintaxis en app.py
```

### Problema: Redis audit muestra "DISCREPANCIAS"

**Solución:**
```bash
# Limpiar keys obsoletas
docker compose exec redis redis-cli KEYS "price:*" | grep -v -E "(BTC|ETH|SOL|TRX|LINK)" | xargs -I {} docker compose exec redis redis-cli DEL {}

# Re-ejecutar audit
docker compose exec dashboard python /app/audit_redis_keys.py
```

---

## 📞 DESPUÉS DEL DEPLOYMENT

Una vez completado el deployment, puedes:

1. **Acceder al Dashboard:**
   - Abre tu navegador
   - Ve a la IP de tu VM: `http://YOUR_VM_IP:8050`
   - Verifica que el equity NO sea $0.00

2. **Verificar logs en tiempo real:**
   ```bash
   docker compose logs -f brain
   docker compose logs -f orders
   ```

3. **Reportar resultados:**
   - Toma screenshots del Dashboard
   - Copia el output del audit de Redis
   - Comparte si hubo algún issue

---

## ✅ CHECKLIST FINAL

Marca cuando completes cada paso:

- [ ] Conectado a VM vía SSH
- [ ] `git pull origin main` ejecutado
- [ ] `./deploy_production_v21.2.sh` ejecutado (o comandos manuales)
- [ ] Warm-up verificado (1.5s)
- [ ] Redis audit PASS (PERFECT SYNC)
- [ ] Dashboard API verificado (equity > 0)
- [ ] 10/10 containers Up
- [ ] Dashboard accesible desde navegador
- [ ] Monitor continuo iniciado (opcional)

---

**Creado por:** Lead Software Architect  
**Fecha:** 2026-02-07  
**Estado:** ✅ LISTO PARA EJECUTAR  
**Duración estimada:** 10 minutos

---

**🎯 PRÓXIMO PASO:** Abre una terminal y ejecuta `ssh vm-trading-bot`
