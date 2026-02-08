#!/bin/bash
###############################################################################
# V22.1.1 Production Deployment Script
# 
# Usage: ./deploy_v22.1.1_prod.sh
#
# Features:
#   - Automatic backup before deploy
#   - Git pull with verification
#   - Docker rebuild with progress
#   - Health checks post-deploy
#   - Rollback instructions if fails
#
# Author: HFT Trading Bot Team
# Version: V22.1.1
# Date: 2026-02-08
###############################################################################

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_header() {
    echo -e "\n${BLUE}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}\n"
}

log_section() {
    echo -e "\n${GREEN}>>> $1${NC}"
    echo -e "${GREEN}────────────────────────────────────────────────────────────────${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if running in correct directory
if [ ! -f "docker-compose.yml" ]; then
    log_error "docker-compose.yml not found!"
    echo "Please run this script from the trading-system-gcp directory"
    exit 1
fi

log_header "V22.1.1 PRODUCTION DEPLOYMENT"

echo "Deployment Info:"
echo "  Date: $(date '+%Y-%m-%d %H:%M:%S')"
echo "  Host: $(hostname)"
echo "  User: $(whoami)"
echo "  Path: $(pwd)"
echo ""

# Confirmation prompt
read -p "⚠️  Proceed with PRODUCTION deployment? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    log_error "Deployment cancelled by user"
    exit 1
fi

###############################################################################
# STEP 1: BACKUP
###############################################################################

log_section "STEP 1/6: Creating Production Backup"

# Check if containers are running
if ! docker compose ps | grep -q "Up"; then
    log_warning "Services not running, starting temporarily for backup..."
    docker compose up -d redis dashboard
    sleep 10
fi

# Create backup
BACKUP_FILE="trading_bot_v16_PROD_PRE_V22.1_$(date +%Y%m%d_%H%M%S).backup"

docker compose exec dashboard cp /app/src/data/trading_bot_v16.db /app/src/data/${BACKUP_FILE} 2>/dev/null || {
    log_error "Failed to create backup!"
    exit 1
}

# Verify backup
BACKUP_SIZE=$(docker compose exec dashboard ls -lh /app/src/data/${BACKUP_FILE} 2>/dev/null | awk '{print $5}')

if [ -z "$BACKUP_SIZE" ]; then
    log_error "Backup verification failed!"
    exit 1
fi

log_success "Backup created: ${BACKUP_FILE} (${BACKUP_SIZE})"

# Generate checksum
MD5=$(docker compose exec dashboard md5sum /app/src/data/trading_bot_v16.db | awk '{print $1}')
echo "$MD5" > "production_db_pre_v22.1.1_${MD5:0:8}.md5"
log_success "MD5 Checksum: ${MD5}"

###############################################################################
# STEP 2: GIT PULL
###############################################################################

log_section "STEP 2/6: Pulling Latest Code from GitHub"

# Check current commit
CURRENT_COMMIT=$(git rev-parse --short HEAD)
echo "Current commit: $CURRENT_COMMIT"

# Pull changes
git fetch origin
git pull origin main

# Verify new commit
NEW_COMMIT=$(git rev-parse --short HEAD)
echo "New commit: $NEW_COMMIT"

if [ "$CURRENT_COMMIT" == "$NEW_COMMIT" ]; then
    log_warning "No new commits (already up to date)"
else
    log_success "Updated: $CURRENT_COMMIT → $NEW_COMMIT"
fi

# Verify target commit
git log --oneline -1

###############################################################################
# STEP 3: STOP SERVICES
###############################################################################

log_section "STEP 3/6: Stopping Services"

docker compose down

log_success "All services stopped"

###############################################################################
# STEP 4: REBUILD CONTAINERS
###############################################################################

log_section "STEP 4/6: Rebuilding Docker Images"

echo "⏳ This may take 5-10 minutes..."
echo ""

# Rebuild all services
docker compose build --no-cache 2>&1 | grep -E "Built|Building|ERROR" || true

# Count successful builds
BUILT_COUNT=$(docker images | grep "trading-system-gcp" | wc -l)

if [ "$BUILT_COUNT" -lt 9 ]; then
    log_error "Only $BUILT_COUNT/10 images built successfully"
    echo "Check build logs: docker compose build --no-cache"
    exit 1
fi

log_success "Docker images rebuilt: $BUILT_COUNT/10"

###############################################################################
# STEP 5: START SERVICES
###############################################################################

log_section "STEP 5/6: Starting Services"

docker compose up -d

echo "⏳ Waiting 30s for services to initialize..."
sleep 30

# Check services
RUNNING_COUNT=$(docker compose ps | grep -c "Up" || echo "0")

if [ "$RUNNING_COUNT" -lt 9 ]; then
    log_error "Only $RUNNING_COUNT/10 services running"
    docker compose ps
    echo ""
    echo "Check logs: docker compose logs"
    exit 1
fi

log_success "Services started: $RUNNING_COUNT/10"

###############################################################################
# STEP 6: POST-DEPLOY VERIFICATION
###############################################################################

log_section "STEP 6/6: Post-Deploy Verification"

# 6.1: Redis connectivity
echo "Checking Redis..."
if docker compose exec redis redis-cli PING | grep -q "PONG"; then
    log_success "Redis: CONNECTED"
else
    log_error "Redis: FAILED"
    exit 1
fi

# 6.2: Brain warm-up
echo ""
echo "Checking Brain warm-up..."
sleep 10
if docker compose logs brain | grep -q "WARM-UP COMPLETADO"; then
    log_success "Brain: WARM-UP COMPLETE"
else
    log_warning "Brain: Still warming up (wait 2-3 minutes)"
fi

# 6.3: Stop-Loss worker
echo ""
echo "Checking Stop-Loss Worker..."
if docker compose logs orders | grep -q "Stop Loss Worker"; then
    log_success "Stop-Loss: OPERATIONAL"
else
    log_error "Stop-Loss: NOT FOUND"
fi

# 6.4: Check for errors
echo ""
echo "Checking for errors (last 5 min)..."
ERROR_COUNT=$(docker compose logs --since 5m 2>&1 | grep -c "ERROR" || echo "0")

if [ "$ERROR_COUNT" -lt 5 ]; then
    log_success "Errors: $ERROR_COUNT (acceptable)"
else
    log_warning "Errors: $ERROR_COUNT (investigate)"
fi

###############################################################################
# DEPLOYMENT COMPLETE
###############################################################################

log_header "DEPLOYMENT COMPLETE ✅"

echo "System Status:"
docker compose ps --format "table {{.Name}}\t{{.Status}}" | head -12

echo ""
echo "Next Steps:"
echo "  1. Monitor for 1 hour: python3 monitor_v21.3_health.py"
echo "  2. Check signals: docker compose logs brain | grep SIGNAL"
echo "  3. Verify trades: docker compose logs orders | grep 'SELL EXECUTED'"
echo ""
echo "Dashboard: http://$(curl -s http://checkip.amazonaws.com):5007"
echo ""
echo "Rollback (if needed):"
echo "  docker compose down"
echo "  docker compose exec dashboard cp /app/src/data/${BACKUP_FILE} /app/src/data/trading_bot_v16.db"
echo "  docker compose up -d"
echo ""

log_success "V22.1.1 deployed successfully! 🎊"
