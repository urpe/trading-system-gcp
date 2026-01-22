#!/bin/bash
OUTPUT_FILE="CODIGO_COMPLETO_PROYECTO.txt"

echo "==============================================================================" > $OUTPUT_FILE
echo " REPORTE COMPLETO DE CÓDIGO - FECHA: $(date)" >> $OUTPUT_FILE
echo "==============================================================================" >> $OUTPUT_FILE
echo "" >> $OUTPUT_FILE

echo "1. ESTRUCTURA DE ARCHIVOS:" >> $OUTPUT_FILE
find src -print | sed -e 's;[^/]*/;|____;g;s;____|; |;g' >> $OUTPUT_FILE
echo "" >> $OUTPUT_FILE
echo "==============================================================================" >> $OUTPUT_FILE
echo "" >> $OUTPUT_FILE

echo "2. CONTENIDO DE LOS ARCHIVOS:" >> $OUTPUT_FILE

# Busca todos los archivos .py, .html, .js, .css, .sh, .txt y .yml
find src -type f \( -name "*.py" -o -name "*.html" -o -name "*.js" -o -name "*.css" -o -name "*.sh" -o -name "*.txt" -o -name "*.yml" \) -print0 | while IFS= read -r -d '' file; do
    echo "------------------------------------------------------------------------------" >> $OUTPUT_FILE
    echo "ARCHIVO: $file" >> $OUTPUT_FILE
    echo "------------------------------------------------------------------------------" >> $OUTPUT_FILE
    cat "$file" >> $OUTPUT_FILE
    echo "" >> $OUTPUT_FILE
    echo "" >> $OUTPUT_FILE
done

echo "✅ EXPORTACIÓN COMPLETADA. Archivo generado: $OUTPUT_FILE"