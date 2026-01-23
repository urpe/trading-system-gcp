#!/bin/bash
# RESET SYSTEM V2 (OPTIMIZADO)
# Restablece la billetera a $10,000 y limpia colecciones operativas usando BATCHES.
# NO borra datos históricos de mercado (para ahorrar API calls y tiempo).

echo "========================================================"
echo "🧨 RESETEO INTELIGENTE DEL SISTEMA (FAST MODE)"
echo "========================================================"
echo "ADVERTENCIA: Esto borrará:"
echo " - Posiciones abiertas (portfolio)"
echo " - Historial de órdenes (orders)"
echo " - Señales operativas (signals)"
echo " - Estado de pares (pairs_status)"
echo ""
echo "🛡️  NOTA: Se conservará 'historical_data' para el simulador."
echo ""

read -p "¿Confirmar reseteo rápido? (s/n): " confirm
if [[ "$confirm" != "s" ]]; then
    echo "Operación cancelada."
    exit 0
fi

echo ""
echo "[1/3] Deteniendo servicios para liberar la BD..."
docker-compose stop

echo "[2/3] Ejecutando limpieza por LOTES (Batch Delete)..."

cat <<EOF > reset_firestore_fast.py
from google.cloud import firestore
import os
import sys

# Configuración
project_id = os.environ.get("PROJECT_ID", "mi-proyecto-trading-12345")
db = firestore.Client(project=project_id)

def delete_collection_in_batches(coll_ref, batch_size=400):
    """Borra documentos en lotes para reducir operaciones de red"""
    deleted = 0
    while True:
        docs = list(coll_ref.limit(batch_size).stream())
        if not docs:
            break

        batch = db.batch()
        for doc in docs:
            batch.delete(doc.reference)
        
        batch.commit()
        deleted += len(docs)
        print(f"   ... Borrados {len(docs)} docs de {coll_ref.id} (Total: {deleted})")

collections_to_wipe = ['portfolio', 'orders', 'signals', 'wallet', 'pairs_status']
# NOTA: NO borramos 'historical_data' ni 'market_data' para no perder caché de Binance.

print(f"🔥 Conectando a Proyecto: {project_id}")

for coll_name in collections_to_wipe:
    print(f"🧹 Limpiando colección: {coll_name}...")
    delete_collection_in_batches(db.collection(coll_name))

# Restaurar Wallet
print("💰 Restaurando Billetera Principal a $10,000...")
db.collection('wallet').document('main_account').set({
    'usdt_balance': 10000.0,
    'total_equity': 10000.0,
    'updated_at': firestore.SERVER_TIMESTAMP
})

print("✅ Limpieza completada.")
EOF

# Ejecutar usando el contenedor dashboard que ya tiene las credenciales y librerías
docker-compose run --rm -v $(pwd)/reset_firestore_fast.py:/app/reset_firestore_fast.py dashboard python /app/reset_firestore_fast.py

rm reset_firestore_fast.py

echo "[3/3] Reactivando sistema..."
docker-compose up -d

echo ""
echo "✨ SISTEMA LISTO PARA NUEVA SIMULACIÓN"
echo "========================================================"
