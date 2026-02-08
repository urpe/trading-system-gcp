#!/usr/bin/env python3
"""
V21.3 HEALTH MONITOR - Sistema de Observabilidad
=================================================
Monitorea el estado del sistema V21.3 "Canonical Core" en tiempo real.

Métricas monitoreadas:
1. Estado de servicios (Docker)
2. Memoria/CPU de contenedores
3. Redis keys integrity
4. TradingSymbol conversions performance
5. Brain warm-up status
6. Database integrity
7. Errors en logs

Uso:
    python3 monitor_v21.3_health.py          # Single check
    python3 monitor_v21.3_health.py --watch  # Continuous (every 5 min)
"""

import subprocess
import json
import time
import sys
from datetime import datetime
from typing import Dict, List, Tuple
import argparse

# Color codes para terminal
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text: str):
    """Print styled header."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text:^80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}\n")

def print_section(text: str):
    """Print section header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}>>> {text}{Colors.END}")
    print(f"{Colors.BLUE}{'-'*80}{Colors.END}")

def print_ok(text: str):
    """Print OK message."""
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")

def print_warning(text: str):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")

def print_error(text: str):
    """Print error message."""
    print(f"{Colors.RED}❌ {text}{Colors.END}")

def run_command(cmd: str, description: str = "") -> Tuple[int, str]:
    """Run shell command and return (exit_code, output)."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return -1, f"Command timeout: {cmd}"
    except Exception as e:
        return -1, f"Command error: {str(e)}"

def check_docker_services() -> Dict[str, bool]:
    """Check status of all Docker services."""
    print_section("1. DOCKER SERVICES STATUS")
    
    services = [
        'redis', 'brain', 'market-data', 'dashboard', 
        'orders', 'persistence', 'historical', 'simulator', 
        'strategy-optimizer', 'alerts'
    ]
    
    status = {}
    
    for service in services:
        exit_code, output = run_command(
            f"docker compose ps {service} --format json 2>/dev/null || echo '{{\"State\": \"not found\"}}'",
            f"Check {service}"
        )
        
        try:
            if output.strip():
                # Try to parse as JSON
                data = json.loads(output.strip().split('\n')[0])
                is_running = data.get('State', '').lower() == 'running'
                status[service] = is_running
                
                if is_running:
                    print_ok(f"{service:20} - Running")
                else:
                    print_error(f"{service:20} - {data.get('State', 'Unknown')}")
            else:
                status[service] = False
                print_error(f"{service:20} - Not found")
        except json.JSONDecodeError:
            # Fallback: check if "Up" is in output
            is_running = "up" in output.lower()
            status[service] = is_running
            if is_running:
                print_ok(f"{service:20} - Running")
            else:
                print_error(f"{service:20} - Stopped or error")
    
    running_count = sum(1 for v in status.values() if v)
    total_count = len(services)
    
    print(f"\n{Colors.BOLD}Summary: {running_count}/{total_count} services running{Colors.END}")
    
    return status

def check_container_resources() -> Dict[str, Dict]:
    """Check CPU/Memory usage of containers."""
    print_section("2. CONTAINER RESOURCES (CPU/Memory)")
    
    exit_code, output = run_command(
        "docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}' | grep trading-system",
        "Docker stats"
    )
    
    resources = {}
    
    if exit_code == 0 and output.strip():
        lines = output.strip().split('\n')
        for line in lines:
            parts = line.split()
            if len(parts) >= 3:
                name = parts[0].replace('trading-system-gcp-', '').replace('-1', '')
                cpu = parts[1]
                mem = ' '.join(parts[2:])
                
                resources[name] = {'cpu': cpu, 'mem': mem}
                
                # Parse CPU percentage
                try:
                    cpu_val = float(cpu.rstrip('%'))
                    if cpu_val > 80:
                        print_error(f"{name:20} - CPU: {cpu:8} Memory: {mem}")
                    elif cpu_val > 50:
                        print_warning(f"{name:20} - CPU: {cpu:8} Memory: {mem}")
                    else:
                        print_ok(f"{name:20} - CPU: {cpu:8} Memory: {mem}")
                except:
                    print(f"   {name:20} - CPU: {cpu:8} Memory: {mem}")
    else:
        print_warning("Could not retrieve container stats (is Docker running?)")
    
    return resources

def check_redis_integrity() -> Dict[str, any]:
    """Check Redis keys integrity."""
    print_section("3. REDIS KEYS INTEGRITY")
    
    integrity = {}
    
    # Check active_symbols
    exit_code, output = run_command(
        "docker compose exec -T redis redis-cli GET active_symbols 2>/dev/null",
        "Get active_symbols"
    )
    
    if exit_code == 0 and output.strip():
        try:
            symbols = json.loads(output.strip().strip('"').replace('\\"', '"'))
            integrity['active_symbols'] = symbols
            print_ok(f"active_symbols: {symbols}")
        except:
            print_warning(f"active_symbols: {output.strip()} (parse error)")
            integrity['active_symbols'] = None
    else:
        print_error("active_symbols: NOT FOUND")
        integrity['active_symbols'] = None
    
    # Check price:* keys count
    exit_code, output = run_command(
        "docker compose exec -T redis redis-cli --scan --pattern 'price:*' 2>/dev/null | wc -l",
        "Count price keys"
    )
    
    if exit_code == 0:
        count = int(output.strip())
        integrity['price_keys'] = count
        if count > 0:
            print_ok(f"price:* keys: {count}")
        else:
            print_warning(f"price:* keys: {count} (no data yet?)")
    else:
        integrity['price_keys'] = 0
        print_error("Could not count price:* keys")
    
    # Check market_regime:* keys count
    exit_code, output = run_command(
        "docker compose exec -T redis redis-cli --scan --pattern 'market_regime:*' 2>/dev/null | wc -l",
        "Count market_regime keys"
    )
    
    if exit_code == 0:
        count = int(output.strip())
        integrity['market_regime_keys'] = count
        if count > 0:
            print_ok(f"market_regime:* keys: {count}")
        else:
            print_warning(f"market_regime:* keys: {count} (Brain not warmed up yet?)")
    else:
        integrity['market_regime_keys'] = 0
        print_error("Could not count market_regime:* keys")
    
    return integrity

def check_brain_warmup() -> bool:
    """Check if Brain warm-up completed."""
    print_section("4. BRAIN WARM-UP STATUS")
    
    exit_code, output = run_command(
        "docker compose logs brain 2>/dev/null | grep 'WARM-UP COMPLETADO' | tail -1",
        "Check Brain warm-up"
    )
    
    if exit_code == 0 and output.strip():
        print_ok("Brain warm-up COMPLETED")
        print(f"   {Colors.CYAN}{output.strip()}{Colors.END}")
        return True
    else:
        # Check if Brain is running but not warmed up yet
        exit_code2, output2 = run_command(
            "docker compose logs brain 2>/dev/null | grep 'WARM-UP SYSTEM ACTIVADO' | tail -1",
            "Check if warm-up started"
        )
        
        if exit_code2 == 0 and output2.strip():
            print_warning("Brain warm-up IN PROGRESS (wait 30-60s)")
            return False
        else:
            print_error("Brain warm-up NOT STARTED (Brain service down?)")
            return False

def check_database_integrity() -> Dict[str, int]:
    """Check SQLite database integrity."""
    print_section("5. DATABASE INTEGRITY")
    
    integrity = {}
    
    # Check trades count
    exit_code, output = run_command(
        "docker compose exec -T dashboard python3 -c \"from src.shared.database import SessionLocal, Trade; session = SessionLocal(); print(session.query(Trade).count()); session.close()\" 2>/dev/null",
        "Count trades"
    )
    
    if exit_code == 0 and output.strip().isdigit():
        count = int(output.strip())
        integrity['trades_count'] = count
        print_ok(f"Trades in DB: {count}")
    else:
        integrity['trades_count'] = -1
        print_warning("Could not count trades (DB not accessible?)")
    
    # Check wallet exists
    exit_code, output = run_command(
        "docker compose exec -T dashboard python3 -c \"from src.shared.database import SessionLocal, Wallet; session = SessionLocal(); wallet = session.query(Wallet).first(); print(f'{wallet.usdt_balance:.2f}' if wallet else 'None'); session.close()\" 2>/dev/null",
        "Check wallet"
    )
    
    if exit_code == 0 and output.strip() != 'None':
        balance = output.strip()
        integrity['wallet_balance'] = balance
        print_ok(f"Wallet balance: ${balance} USDT")
    else:
        integrity['wallet_balance'] = None
        print_warning("Wallet not initialized or not accessible")
    
    return integrity

def check_logs_for_errors() -> Dict[str, int]:
    """Check logs for errors in last 5 minutes."""
    print_section("6. ERROR DETECTION (Last 5 minutes)")
    
    errors = {}
    
    services = ['brain', 'market-data', 'dashboard', 'orders']
    
    for service in services:
        exit_code, output = run_command(
            f"docker compose logs {service} --tail 100 2>/dev/null | grep -i 'error\\|exception\\|critical' | wc -l",
            f"Check {service} errors"
        )
        
        if exit_code == 0:
            count = int(output.strip())
            errors[service] = count
            
            if count == 0:
                print_ok(f"{service:20} - No errors")
            elif count < 5:
                print_warning(f"{service:20} - {count} errors (check logs)")
            else:
                print_error(f"{service:20} - {count} errors (CRITICAL)")
        else:
            errors[service] = -1
    
    return errors

def check_trading_activity() -> Dict[str, any]:
    """Check if system is generating signals/trades."""
    print_section("7. TRADING ACTIVITY")
    
    activity = {}
    
    # Check for signals in Brain logs
    exit_code, output = run_command(
        "docker compose logs brain --tail 100 2>/dev/null | grep '📊 SIGNAL' | tail -5",
        "Check signals"
    )
    
    if exit_code == 0 and output.strip():
        lines = output.strip().split('\n')
        activity['signals_count'] = len(lines)
        print_ok(f"Recent signals: {len(lines)}")
        for line in lines[-3:]:  # Show last 3
            print(f"   {Colors.CYAN}{line.strip()}{Colors.END}")
    else:
        activity['signals_count'] = 0
        print_warning("No recent signals (system too new or no opportunities)")
    
    # Check for trades in Orders logs
    exit_code, output = run_command(
        "docker compose logs orders --tail 100 2>/dev/null | grep '✅ ORDER' | tail -5",
        "Check trades"
    )
    
    if exit_code == 0 and output.strip():
        lines = output.strip().split('\n')
        activity['trades_count'] = len(lines)
        print_ok(f"Recent trades: {len(lines)}")
        for line in lines[-3:]:
            print(f"   {Colors.CYAN}{line.strip()}{Colors.END}")
    else:
        activity['trades_count'] = 0
        print_warning("No recent trades (no signals or balance insufficient)")
    
    return activity

def generate_health_score(checks: Dict) -> int:
    """Calculate overall health score (0-100)."""
    score = 100
    
    # Services down: -10 per service
    services_down = sum(1 for v in checks.get('services', {}).values() if not v)
    score -= services_down * 10
    
    # Redis integrity issues: -20
    if not checks.get('redis', {}).get('active_symbols'):
        score -= 20
    
    # Brain not warmed up: -15
    if not checks.get('brain_warmup', False):
        score -= 15
    
    # Database issues: -10
    if checks.get('database', {}).get('trades_count', 0) < 0:
        score -= 10
    
    # Errors detected: -5 per service with errors
    errors = checks.get('errors', {})
    services_with_errors = sum(1 for v in errors.values() if v > 0)
    score -= services_with_errors * 5
    
    return max(0, score)

def print_summary(checks: Dict, score: int):
    """Print final summary."""
    print_header("HEALTH SUMMARY")
    
    print(f"\n{Colors.BOLD}Overall Health Score: {score}/100{Colors.END}")
    
    if score >= 90:
        print_ok("Status: EXCELLENT - System running optimally")
    elif score >= 70:
        print_warning("Status: GOOD - Minor issues detected")
    elif score >= 50:
        print_warning("Status: DEGRADED - Multiple issues require attention")
    else:
        print_error("Status: CRITICAL - System needs immediate attention")
    
    print(f"\n{Colors.BOLD}Key Metrics:{Colors.END}")
    print(f"   Services Running: {sum(1 for v in checks.get('services', {}).values() if v)}/{len(checks.get('services', {}))}")
    print(f"   Redis Keys: {checks.get('redis', {}).get('price_keys', 0)} prices, {checks.get('redis', {}).get('market_regime_keys', 0)} regimes")
    print(f"   Brain Warm-up: {'✅ Complete' if checks.get('brain_warmup') else '⏳ Pending'}")
    print(f"   Trading Activity: {checks.get('activity', {}).get('signals_count', 0)} signals, {checks.get('activity', {}).get('trades_count', 0)} trades")
    
    print(f"\n{Colors.BOLD}Timestamp:{Colors.END} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Recommendations
    if score < 100:
        print(f"\n{Colors.BOLD}Recommendations:{Colors.END}")
        
        if sum(1 for v in checks.get('services', {}).values() if not v) > 0:
            print_warning("→ Start missing services: docker compose up -d")
        
        if not checks.get('brain_warmup'):
            print_warning("→ Wait for Brain warm-up (30-60s) or check Brain logs")
        
        if checks.get('redis', {}).get('price_keys', 0) == 0:
            print_warning("→ Check Market Data service: docker compose logs market-data")
        
        services_with_errors = [k for k, v in checks.get('errors', {}).items() if v > 5]
        if services_with_errors:
            print_warning(f"→ Check logs for: {', '.join(services_with_errors)}")

def save_report(checks: Dict, score: int):
    """Save health report to file."""
    report = {
        'timestamp': datetime.now().isoformat(),
        'health_score': score,
        'checks': checks
    }
    
    filename = f"health_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    try:
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\n{Colors.CYAN}📄 Report saved: {filename}{Colors.END}")
    except Exception as e:
        print_error(f"Could not save report: {e}")

def main():
    parser = argparse.ArgumentParser(description='V21.3 Health Monitor')
    parser.add_argument('--watch', action='store_true', help='Continuous monitoring (every 5 min)')
    parser.add_argument('--save', action='store_true', help='Save report to JSON file')
    args = parser.parse_args()
    
    if args.watch:
        print(f"{Colors.BOLD}Starting continuous monitoring (Ctrl+C to stop)...{Colors.END}\n")
    
    while True:
        print_header(f"V21.3 CANONICAL CORE - HEALTH CHECK")
        
        checks = {}
        
        # Run all checks
        checks['services'] = check_docker_services()
        checks['resources'] = check_container_resources()
        checks['redis'] = check_redis_integrity()
        checks['brain_warmup'] = check_brain_warmup()
        checks['database'] = check_database_integrity()
        checks['errors'] = check_logs_for_errors()
        checks['activity'] = check_trading_activity()
        
        # Calculate score
        score = generate_health_score(checks)
        
        # Print summary
        print_summary(checks, score)
        
        # Save report if requested
        if args.save:
            save_report(checks, score)
        
        if not args.watch:
            break
        
        # Wait 5 minutes
        print(f"\n{Colors.CYAN}Next check in 5 minutes...{Colors.END}")
        time.sleep(300)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Monitoring stopped by user{Colors.END}")
        sys.exit(0)
    except Exception as e:
        print_error(f"Fatal error: {e}")
        sys.exit(1)
