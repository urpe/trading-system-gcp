# TESTING LOCAL V21.2.1 - GUÍA EXHAUSTIVA

## 🎯 OBJETIVO

Verificar que TODAS las correcciones de "Integrity Hardening" funcionan correctamente en ambiente local antes de pasar a V21.3.

---

## ✅ PRE-REQUISITOS

```bash
cd ~/trading-system-gcp
git pull origin main  # Asegurar última versión
docker compose down   # Limpiar estado anterior
```

---

## 🧪 TEST SUITE 1: VERIFICATION SCRIPT

```bash
python3 verify_integrity_v21.2.1.py
```

**Resultado Esperado:** 5/5 tests PASSED

---

## 🧪 TEST SUITE 2: DOCKER BUILD

```bash
docker compose build --no-cache
docker compose up -d
docker compose ps
```

**Resultado Esperado:** 10/10 servicios "Up", Redis "healthy"

---

## 🧪 TEST SUITE 3: WARM-UP

```bash
docker compose logs brain | grep "WARM-UP"
```

**Resultado Esperado:** WARM-UP COMPLETADO en < 5 segundos

---

## 🧪 TEST SUITE 4: REDIS AUDIT

```bash
docker compose cp audit_redis_keys.py dashboard:/app/
docker compose exec dashboard python /app/audit_redis_keys.py
```

**Resultado Esperado:** BRAIN OK, normalización 5/5 PASS

---

## 🧪 TEST SUITE 5: DASHBOARD

```bash
curl http://localhost:8050/health
curl http://localhost:8050/api/dashboard_data | python3 -m json.tool
curl http://localhost:8050/asset/BTC
```

**Resultado Esperado:** Status 200, sin errores 500, equity > $0

---

## 📊 CHECKLIST

- [ ] Test 1: Verification script PASS
- [ ] Test 2: Docker 10/10 UP
- [ ] Test 3: Warm-up < 5s
- [ ] Test 4: Redis audit PASS  
- [ ] Test 5: Dashboard funcional

**Si 5/5 tests pasan, proceder a V21.3 "Canonical Core"**
