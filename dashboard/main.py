#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
DASHBOARD DE MONITOREO - Sistema de Trading Algorítmico v1.0
================================================================================
"""

import os
import logging
from typing import Dict, Any, List
from datetime import datetime

from flask import Flask, render_template, jsonify
from google.cloud import firestore

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuración de Flask
app = Flask(__name__)

# Constantes
DASHBOARD_VERSION = "1.0.0"
PROJECT_ID = os.environ.get('PROJECT_ID', 'mi-proyecto-trading-12345')

# Cliente de Firestore
db = firestore.Client(project=PROJECT_ID)


def get_recent_signals(limit: int = 10) -> List[Dict[str, Any]]:
    """Obtiene las señales más recientes de Firestore."""
    try:
        signals_ref = (
            db.collection('signals')
            .order_by('timestamp', direction=firestore.Query.DESCENDING)
            .limit(limit)
        )
        return [doc.to_dict() for doc in signals_ref.stream()]
    except Exception as e:
        logger.error(f"Error obteniendo señales: {e}")
        return []


def get_recent_orders(limit: int = 10) -> List[Dict[str, Any]]:
    """Obtiene las órdenes más recientes de Firestore."""
    try:
        orders_ref = (
            db.collection('orders')
            .order_by('timestamp', direction=firestore.Query.DESCENDING)
            .limit(limit)
        )
        return [doc.to_dict() for doc in orders_ref.stream()]
    except Exception as e:
        logger.error(f"Error obteniendo órdenes: {e}")
        return []


def get_performance_metrics() -> Dict[str, Any]:
    """Calcula métricas de rendimiento del sistema."""
    try:
        signals = [doc.to_dict() for doc in db.collection('signals').stream()]
        orders = [doc.to_dict() for doc in db.collection('orders').stream()]
        
        buy_signals = [s for s in signals if s.get('action') == 'BUY']
        sell_signals = [s for s in signals if s.get('action') == 'SELL']
        
        avg_buy_price = sum(float(s.get('price', 0)) for s in buy_signals) / len(buy_signals) if buy_signals else 0
        avg_sell_price = sum(float(s.get('price', 0)) for s in sell_signals) / len(sell_signals) if sell_signals else 0
        
        total_volume = sum(float(s.get('quantity', 0)) for s in signals)
        
        successful_orders = sum(1 for o in orders if o.get('order_status') == 'SUCCESS')
        total_orders = len(orders)
        win_rate = (successful_orders / total_orders * 100) if total_orders > 0 else 0
        
        pnl_percentage = ((avg_sell_price - avg_buy_price) / avg_buy_price * 100) if avg_buy_price > 0 and avg_sell_price > 0 else 0
        
        return {
            "total_signals": len(signals),
            "buy_count": len(buy_signals),
            "sell_count": len(sell_signals),
            "total_orders": total_orders,
            "successful_orders": successful_orders,
            "win_rate": round(win_rate, 2),
            "avg_buy_price": round(avg_buy_price, 2),
            "avg_sell_price": round(avg_sell_price, 2),
            "total_volume": round(total_volume, 6),
            "pnl_percentage": round(pnl_percentage, 2)
        }
    except Exception as e:
        logger.error(f"Error calculando métricas: {e}")
        return {
            "total_signals": 0, "buy_count": 0, "sell_count": 0,
            "total_orders": 0, "successful_orders": 0, "win_rate": 0,
            "avg_buy_price": 0, "avg_sell_price": 0, "total_volume": 0, "pnl_percentage": 0
        }


@app.route('/')
def index():
    """Página principal del dashboard."""
    try:
        signals = get_recent_signals()
        orders = get_recent_orders()
        metrics = get_performance_metrics()
        
        return render_template(
            'index.html',
            signals=signals,
            orders=orders,
            metrics=metrics,
            version=DASHBOARD_VERSION
        )
    except Exception as e:
        logger.error(f"Error renderizando dashboard: {e}")
        return f"Error: {e}", 500


@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "version": DASHBOARD_VERSION}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
