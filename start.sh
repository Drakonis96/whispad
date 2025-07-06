#!/bin/bash

# Script para iniciar únicamente el backend de Python
set -e

echo "Iniciando backend Python..."

# Crear y configurar directorio para notas guardadas
mkdir -p /app/saved_notes
chmod 777 /app/saved_notes

# Ejecutar el backend de forma directa
python backend.py
