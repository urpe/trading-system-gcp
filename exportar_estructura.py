import os

def generar_arbol(ruta_inicio='.'):
    # Carpetas que queremos IGNORAR (para que no salga basura)
    ignorar = {'.git', '__pycache__', 'venv', '.idea', '.vscode'}
    
    with open('estructura_proyecto.txt', 'w', encoding='utf-8') as f:
        f.write(f"Estructura del Proyecto: {os.path.basename(os.getcwd())}\n")
        f.write("="*40 + "\n")
        
        for root, dirs, files in os.walk(ruta_inicio):
            # Eliminar carpetas ignoradas de la búsqueda
            dirs[:] = [d for d in dirs if d not in ignorar]
            
            level = root.replace(ruta_inicio, '').count(os.sep)
            indent = '    ' * level
            f.write(f'{indent}{os.path.basename(root)}/\n')
            
            subindent = '    ' * (level + 1)
            for file in files:
                f.write(f'{subindent}{file}\n')

if __name__ == '__main__':
    generar_arbol()
    print("¡Listo! Se ha creado el archivo 'estructura_proyecto.txt'")