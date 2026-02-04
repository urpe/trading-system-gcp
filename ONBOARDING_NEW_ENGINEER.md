# 👋 BIENVENIDO AL PROYECTO - HFT TRADING BOT V19

## Tu Primer Día: Guía de Onboarding

**Tiempo estimado**: 2-4 horas

---

## 📦 PASO 1: SETUP INICIAL (30 min)

### 1.1 Acceso al Servidor

```bash
# Conectar via SSH
ssh jhersonurpecanchanya@trading-bot-redis

# Verificar que tienes acceso
pwd
# Output esperado: /home/jhersonurpecanchanya
```

### 1.2 Navegar al Proyecto

```bash
cd trading-system-gcp
ls -la

# Deberías ver:
# - docker-compose.yml
# - src/
# - requirements.txt
# - SYSTEM_ARCHITECTURE_MASTER.md (LEE ESTO PRIMERO!)
# - AUDIT_REPORT_V19.md
# - V19_REGIME_SWITCHING_RELEASE.md
```

### 1.3 Verificar Docker

```bash
# Ver servicios corriendo
docker compose ps

# Deberías ver 10 servicios con estado "Up"
# Si no: lee sección "TROUBLESHOOTING" más abajo
```

---

## 📚 PASO 2: LEER DOCUMENTACIÓN (60 min)

### Documentos en ORDEN DE LECTURA:

1. **`V19_REGIME_SWITCHING_RELEASE.md`** (20 min)
   - Qué hace el sistema
   - Conceptos clave (Regime Switching)
   - Novedades de V19

2. **`SYSTEM_ARCHITECTURE_MASTER.md`** (30 min) ← **CRÍTICO**
   - Arquitectura completa
   - Flujo de datos
   - Detalles de cada microservicio

3. **`AUDIT_REPORT_V19.md`** (10 min)
   - Estado actual del sistema
   - Bugs conocidos
   - Recomendaciones

---

## 🔍 PASO 3: EXPLORAR EL CÓDIGO (60 min)

### 3.1 Estructura Principal

```
src/
├── services/
│   ├── brain/              ← EMPIEZA AQUÍ (corazón del sistema)
│   │   ├── main.py         ← Clase RegimeSwitchingBrain
│   │   └── strategies/     ← 9 estrategias de trading
│   │
│   ├── market_data/        ← Obtiene precios de Binance
│   ├── strategy_optimizer/ ← Torneo cada 12h
│   ├── orders/             ← Ejecuta trades
│   └── dashboard/          ← UI web (Flask)
│
├── shared/
│   ├── memory.py           ← Singleton Redis client
│   ├── database.py         ← SQLAlchemy setup (SQLite)
│   └── utils.py            ← Logging helpers
│
└── config/
    └── settings.py         ← Configuración central
```

### 3.2 Archivos Clave a Revisar

```bash
# 1. Brain principal
cat src/services/brain/main.py | head -100

# 2. Detector de régimen
cat src/services/brain/strategies/regime_detector.py | head -150

# 3. Optimizer (torneo)
cat src/services/strategy_optimizer/main.py | head -100

# 4. Una estrategia de ejemplo
cat src/services/brain/strategies/ichimoku_cloud.py | head -100
```

### 3.3 Ver Logs en Vivo

```bash
# Logs del Brain (generación de señales)
docker compose logs brain -f

# Ver SOLO señales
docker compose logs brain -f | grep "SIGNAL"

# Ver SOLO errores
docker compose logs brain -f | grep "ERROR"

# Ctrl+C para salir
```

---

## 🧪 PASO 4: HANDS-ON TESTING (30 min)

### 4.1 Ejecutar Diagnóstico

```bash
python check_brain_status.py

# Output esperado:
# - Market Regimes (puede estar "unknown" si sistema recién desplegado)
# - Active Strategies (RsiMeanReversion por defecto)
# - Next Optimization (en X horas)
# - System Health (todos ✅)
```

### 4.2 Inspeccionar Redis

```bash
# Conectar a Redis
docker compose exec redis redis-cli

# Comandos a probar:
> KEYS *                      # Ver todas las keys
> GET active_symbols          # Ver monedas activas
> GET strategy_config:BTC     # Ver estrategia de BTC
> LRANGE recent_signals 0 4   # Ver últimas 5 señales
> GET market_regime:BTC       # Ver régimen de BTC
> quit
```

### 4.3 Inspeccionar SQLite

```bash
# Conectar a base de datos
sqlite3 src/data/trading_bot_v16.db

-- Comandos a probar:
.tables                       -- Ver tablas
.schema trade                 -- Ver esquema de tabla

SELECT * FROM trade 
ORDER BY timestamp DESC 
LIMIT 5;                      -- Últimos 5 trades

SELECT symbol, COUNT(*) as trades, 
       SUM(pnl) as total_pnl 
FROM trade 
WHERE status = 'CLOSED'
GROUP BY symbol;              -- Resumen por símbolo

.quit
```

### 4.4 Acceder al Dashboard

```bash
# En tu navegador local:
http://[SERVER_IP]:8050

# O si estás en el servidor:
curl http://localhost:8050

# Deberías ver:
# - Active Positions
# - PnL
# - Recent Signals
# - Market Scanner con 5 monedas
```

---

## 🛠️ PASO 5: HACER TU PRIMER CAMBIO (30 min)

### Ejercicio: Agregar un Log Personalizado

**Objetivo**: Agregar un log cuando se detecta un nuevo régimen.

**Archivo**: `src/services/brain/main.py`

**Cambio**:
```python
# Busca la función detect_market_regime()
def detect_market_regime(self, symbol):
    # ...
    regime, indicators = self.regime_detector.detect(price_hist)
    
    # AGREGAR ESTA LÍNEA:
    logger.info(f"🌡️ Régimen actualizado para {symbol}: {regime.value}")
    
    # ...
```

**Deploy del Cambio**:
```bash
# 1. Guardar el archivo (si usas vim: :wq)

# 2. Reiniciar solo el Brain (rápido, <10s)
docker compose restart brain

# 3. Ver logs para verificar
docker compose logs brain -f | grep "🌡️"

# Deberías ver tu nuevo log cada vez que se detecta régimen!
```

**Revertir**:
```bash
# Si algo sale mal, rebuild completo:
docker compose down
docker compose up -d
```

---

## 🎯 PASO 6: CONCEPTOS CLAVE A DOMINAR

### 6.1 Event-Driven Architecture

```
Market Data → PUBLISH 'market_data' → Brain SUBSCRIBES
Brain → PUBLISH 'signals' → Orders SUBSCRIBES
```

**Ventajas**:
- Desacoplamiento total
- Escalabilidad
- Fault tolerance

### 6.2 Hot-Swap de Estrategias

```
1. Optimizer guarda en Redis: strategy_config:BTC
2. Brain lee Redis cada 30 min
3. Brain usa nueva estrategia SIN RESTART
```

**Beneficio**: Cero downtime para cambios de estrategia.

### 6.3 Regime Detection

```
ADX + EMA(200) → Clasificación:
- BULL_TREND:   price > EMA200 AND ADX > 25
- BEAR_TREND:   price < EMA200 AND ADX > 25
- SIDEWAYS:     ADX < 20
- HIGH_VOL:     ATR > 8%
```

**Por qué importa**: Cada régimen necesita estrategias diferentes.

### 6.4 Rolling Validation

```
Backtest en 3 ventanas:
- Últimos 7d:  50% peso  ← MÁS IMPORTANTE
- Últimos 15d: 30% peso
- Últimos 30d: 20% peso

Solo aprueba si weighted_score > 0
```

**Por qué importa**: Evita overfitting al pasado.

---

## 🚨 TROUBLESHOOTING COMÚN

### Problema 1: "Contenedores no levantan"

```bash
# Ver logs de error
docker compose logs [service_name]

# Rebuild completo (solución universal)
docker compose down --volumes --remove-orphans
sleep 5
docker compose up --build -d
```

### Problema 2: "Brain no genera señales"

**Causas posibles**:
1. Market Data no está publicando
   ```bash
   docker compose logs market-data --tail 20
   # Debe ver: "Published X coins to market_data"
   ```

2. Historial insuficiente
   ```bash
   docker compose logs brain | grep "Historial insuficiente"
   # Si ve esto: Esperar más tiempo (acumular precios)
   ```

3. Redis desconectado
   ```bash
   docker compose ps redis
   # Debe decir: Up X minutes (healthy)
   ```

### Problema 3: "Dashboard no muestra datos"

```bash
# 1. Verificar que Dashboard está corriendo
docker compose ps dashboard
# Debe estar "Up"

# 2. Verificar puerto
curl http://localhost:8050
# Debe retornar HTML

# 3. Verificar que Redis tiene datos
docker compose exec redis redis-cli GET active_symbols
# Debe retornar: ["btcusdt", ...]
```

### Problema 4: "Optimizer no ejecuta torneo"

```bash
# Ver logs de optimizer
docker compose logs strategy-optimizer --tail 50

# Verificar intervalo (12h)
# Si necesitas forzar torneo:
docker compose restart strategy-optimizer
# Ejecutará torneo en ~30 segundos
```

---

## 📖 RECURSOS ADICIONALES

### Documentación Interna:
- `SYSTEM_ARCHITECTURE_MASTER.md` - Referencia completa
- `AUDIT_REPORT_V19.md` - Estado del sistema
- `.cursorrules` - Estándares de código

### Comandos Útiles:
```bash
# Ver todos los contenedores
docker compose ps

# Logs de todos los servicios
docker compose logs -f

# Rebuild y redeploy completo
docker compose down --volumes --remove-orphans && sleep 5 && docker compose up --build -d

# Diagnóstico completo
python check_brain_status.py

# Backup de base de datos
cp src/data/trading_bot_v16.db backups/db_$(date +%Y%m%d).db
```

### Libros/Papers Recomendados:
- "New Concepts in Technical Trading Systems" - Welles Wilder (ADX, RSI)
- "Trading Systems and Methods" - Perry Kaufman (Adaptive trading)
- "Algorithmic Trading" - Ernest P. Chan

---

## ✅ CHECKLIST DE ONBOARDING

- [ ] ✅ Acceso SSH al servidor
- [ ] ✅ Leído V19_REGIME_SWITCHING_RELEASE.md
- [ ] ✅ Leído SYSTEM_ARCHITECTURE_MASTER.md
- [ ] ✅ Explorado estructura de código
- [ ] ✅ Ejecutado check_brain_status.py
- [ ] ✅ Inspeccionado Redis
- [ ] ✅ Inspeccionado SQLite
- [ ] ✅ Accedido al Dashboard
- [ ] ✅ Hecho primer cambio (log personalizado)
- [ ] ✅ Revisado troubleshooting

**Si completaste todo**: **¡ESTÁS LISTO!** 🎉

---

## 🎓 PRÓXIMOS PASOS

### Semana 1:
- Familiarízate con las 9 estrategias
- Ejecuta backtests manuales
- Monitorea el sistema 24h

### Semana 2:
- Implementa una nueva estrategia simple (ej: WMA Crossover)
- Agrégala al torneo
- Valida resultados

### Semana 3:
- Mejora el Dashboard (agregar gráfico de régimen)
- Implementa alertas (Telegram/Email)
- Optimiza performance

### Mes 2+:
- Implementa mejoras de V20 (ver ROADMAP)
- Machine Learning para regime prediction
- Deploy a producción real

---

## 📞 CONTACTOS

**Documentación**: Este archivo + carpeta docs/

**Logs**: `docker compose logs [service]`

**Diagnóstico**: `python check_brain_status.py`

**Preguntas**: Revisa SYSTEM_ARCHITECTURE_MASTER.md primero

---

## 🎯 TU MISIÓN

> "Mantener este sistema operando 24/7 con Win Rate > 55%"

**Recuerda**:
- El mercado nunca duerme
- Los logs son tu mejor amigo
- Cuando en duda: `docker compose restart [service]`
- Siempre haz backup antes de cambios grandes

**¡ÉXITO EN TU NUEVO ROL!** 🚀

---

**Documento de Onboarding V19**  
**Última actualización**: 2026-02-02  
**Próxima revisión**: 2026-03-02
