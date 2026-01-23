from google.cloud import firestore
import os

# Configuración básica si no existe entorno
project_id = os.environ.get("PROJECT_ID", "mi-proyecto-trading-12345")
db = firestore.Client(project=project_id)

def delete_collection(coll_ref, batch_size):
    docs = coll_ref.limit(batch_size).stream()
    deleted = 0
    for doc in docs:
        print(f'Borrando doc {doc.id} => {coll_ref.id}')
        doc.reference.delete()
        deleted += 1
    if deleted >= batch_size:
        return delete_collection(coll_ref, batch_size)

collections = ['portfolio', 'orders', 'signals', 'wallet', 'pairs_status']

print(f"Conectando a Firestore Proyecto: {project_id}")

# 1. Borrar colecciones operativas
for coll in collections:
    print(f"Limpiando colección: {coll}...")
    delete_collection(db.collection(coll), 10)

# 2. Restaurar Wallet Inicial
print("Restaurando Billetera Principal...")
db.collection('wallet').document('main_account').set({
    'usdt_balance': 10000.0,
    'total_equity': 10000.0,
    'updated_at': firestore.SERVER_TIMESTAMP
})

print("✅ Limpieza completada exitosamente.")
