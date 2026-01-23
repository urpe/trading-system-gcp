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
print("💰 Restaurando Billetera Principal a 0,000...")
db.collection('wallet').document('main_account').set({
    'usdt_balance': 10000.0,
    'total_equity': 10000.0,
    'updated_at': firestore.SERVER_TIMESTAMP
})

print("✅ Limpieza completada.")
