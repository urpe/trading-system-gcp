# 🚀 Guía: Workflow Git Dev-Local → Prod-Cloud

**Fecha:** 2026-02-07  
**Versión:** V21 Post-Blackout  
**Objetivo:** Desarrollar en PC local, deployar en VM de GCP sin editar código en la nube.

---

## 📋 ARQUITECTURA DE DESARROLLO

```
┌─────────────────┐           ┌──────────────┐           ┌────────────────┐
│  PC Local       │           │   GitHub     │           │  GCP VM        │
│  (Cursor IDE)   │  git push │  (Repo)      │  git pull │  (Producción)  │
│  + Docker Local │  ───────> │  main branch │  ───────> │  + Docker      │
└─────────────────┘           └──────────────┘           └────────────────┘
```

### Regla de Oro

> **NUNCA edites código directamente en la VM**. La VM es solo para correr el sistema en producción.

---

## 🛠️ SETUP INICIAL (Una sola vez)

### 1. Configurar Git en PC Local

```bash
# Clonar el repositorio (si no lo tienes)
cd ~/projects
git clone https://github.com/tu-usuario/trading-system-gcp.git
cd trading-system-gcp

# Configurar tu identidad
git config user.email "tu@email.com"
git config user.name "Tu Nombre"
```

### 2. Verificar Docker Local

```bash
# Instalar Docker Desktop (si no lo tienes)
# https://www.docker.com/products/docker-desktop/

# Verificar instalación
docker --version
docker compose --version
```

### 3. Crear archivo `.env` local (NO subirlo a Git)

```bash
# Crear .env con configuración de desarrollo
cat > .env << 'EOF'
PROJECT_ID=dev-local
REDIS_HOST=localhost
ENV=development
EOF
```

---

## 🔄 WORKFLOW DIARIO: Dev → Prod

### FASE A: Desarrollo en Local

```bash
# 1. Asegurarte de estar en la rama main actualizada
git checkout main
git pull origin main

# 2. (Opcional) Crear una rama para tu feature
git checkout -b feature/fix-dashboard-blackout

# 3. Editar código en Cursor IDE
#    - Los cambios se hot-reload automáticamente en Docker
#    - Probar en http://localhost:8050

# 4. Probar localmente
docker compose up -d
docker compose logs -f dashboard  # Ver logs en tiempo real

# 5. Verificar que todo funcione
curl http://localhost:8050/api/dashboard-data | jq
```

### FASE B: Commit y Push a GitHub

```bash
# 1. Revisar cambios
git status
git diff

# 2. Agregar archivos modificados
git add src/services/dashboard/app.py
git add .gitignore deploy_prod.sh  # Si creaste nuevos archivos

# 3. Commit con mensaje descriptivo
git commit -m "fix(dashboard): Implementar get_market_regimes() para V21 OHLCV

- Agregada función faltante que causaba NameError 500
- Dashboard ahora lee regímenes desde Redis correctamente
- Blackout resuelto: equity y posiciones cargando OK"

# 4. Push a GitHub
git push origin main  # O tu rama feature
```

### FASE C: Deploy en VM de GCP

```bash
# 1. Conectar a la VM por SSH
gcloud compute ssh [NOMBRE-VM] --zone=[ZONE]

# O con SSH directo:
ssh -i ~/.ssh/gcp_key usuario@IP_DE_TU_VM

# 2. Navegar al proyecto
cd ~/trading-system-gcp

# 3. Ejecutar el script de deployment
./deploy_prod.sh

# (Opcional) Full rebuild si hay cambios en dependencias
./deploy_prod.sh --full-rebuild

# 4. Verificar sistema operativo
docker compose ps
curl http://localhost:8050/api/dashboard-data | jq .regimes
```

---

## ⚡ COMANDOS RÁPIDOS

### En Local (PC)

```bash
# Ver logs de un servicio específico
docker compose logs -f brain

# Reiniciar un servicio
docker compose restart dashboard

# Detener todo
docker compose down

# Rebuild completo (si cambiaste requirements.txt)
docker compose up -d --build
```

### En la VM (Producción)

```bash
# Ver estado de servicios
docker compose ps

# Ver logs de los últimos 5 minutos
docker compose logs --since=5m

# Ver régimen actual de BTC
docker compose exec redis redis-cli GET market_regime:BTC | jq

# Reiniciar solo el servicio con problema
docker compose restart brain

# Detener y limpiar todo (CUIDADO: Borra Redis cache)
docker compose down
```

---

## 🚨 TROUBLESHOOTING

### Problema: Git pull en la VM falla con conflictos

**Causa:** Editaste código en la VM (mal hábito).

**Solución:**

```bash
# Hacer backup de cambios locales si son importantes
git stash

# O descartarlos (reset forzado)
git reset --hard origin/main

# Luego hacer pull limpio
git pull origin main
```

### Problema: Dashboard sigue mostrando código viejo después de git pull

**Causa:** Docker no detectó el cambio o usa imagen cacheada.

**Solución:**

```bash
# Reiniciar el servicio
docker compose restart dashboard

# Si no funciona, rebuild completo
docker compose up -d --build dashboard
```

### Problema: Redis data se pierde al hacer `docker compose down`

**Causa:** Redis AOF está desactivado o no sincronizó antes del shutdown.

**Solución:**

```bash
# NUNCA uses `docker compose down` en producción
# Usa en su lugar:
docker compose stop   # Detiene sin borrar volúmenes

# Para limpiar y recrear:
docker compose down
docker compose up -d
```

---

## 📊 VERIFICACIÓN POST-DEPLOYMENT

Después de cada deployment, ejecutar esta checklist:

```bash
# 1. Todos los servicios corriendo
docker compose ps | grep -c "Up"  # Debe ser 10 (o tu número total)

# 2. Dashboard responde OK
curl -I http://localhost:8050 | grep "200 OK"

# 3. API de datos funciona
curl http://localhost:8050/api/dashboard-data | jq .regimes

# 4. Brain está generando regímenes
docker compose exec redis redis-cli KEYS "market_regime:*"

# 5. Logs sin errores críticos
docker compose logs --tail=100 | grep -i error
```

---

## 💰 OPTIMIZACIÓN DE COSTOS (FinOps)

### Regla de Ahorro #1: Apaga la VM cuando no la uses

```bash
# Detener la VM (no la borra, solo la apaga)
gcloud compute instances stop [NOMBRE-VM] --zone=[ZONE]

# Reiniciar cuando la necesites
gcloud compute instances start [NOMBRE-VM] --zone=[ZONE]

# Costo de VM apagada: $0.50/mes (solo disco)
# Costo de VM corriendo 24/7: $45/mes
```

### Regla de Ahorro #2: Desarrolla 100% en local

**NUNCA edites en la VM**. Cada sesión SSH con Docker activo cuesta. Desarrolla en tu PC y solo sube a la VM para producción/demo.

### Regla de Ahorro #3: Rotación de logs

El `docker-compose.yml` ya está configurado con rotación de logs (ver abajo), pero verifica que esté activo:

```yaml
services:
  dashboard:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

Si no está configurado, los logs crecerán infinitamente y pagarás por el almacenamiento.

---

## 🎯 PRÓXIMOS PASOS

1. **Commit inicial**: Subir el fix del blackout a GitHub
2. **Probar el workflow**: Hacer un cambio pequeño (ej: agregar un log), commit, push, deploy en VM
3. **Automatizar CI/CD** (Opcional): GitHub Actions para test automáticos antes de merge

---

## 📚 RECURSOS

- [Docker Compose Docs](https://docs.docker.com/compose/)
- [Git Workflow](https://guides.github.com/introduction/flow/)
- [GCP VM Best Practices](https://cloud.google.com/compute/docs/instances/stopping-or-deleting-an-instance)

---

**¿Dudas?** Revisa los logs o abre un issue en el repo.
