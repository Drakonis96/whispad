#!/bin/bash

# Script para iniciar tanto nginx como el backend de Python
set -e

echo "Iniciando servicios..."

# Crear directorios necesarios para nginx
mkdir -p /var/log/nginx
mkdir -p /var/lib/nginx

# Generar certificado SSL autofirmado si no existe
if [ ! -f /etc/nginx/certs/selfsigned.crt ]; then
    echo "Generando certificado SSL autofirmado..."
    mkdir -p /etc/nginx/certs
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout /etc/nginx/certs/selfsigned.key \
        -out /etc/nginx/certs/selfsigned.crt \
        -subj "/CN=localhost"
fi

# Crear y configurar directorios persistentes
mkdir -p /app/saved_notes
chmod 777 /app/saved_notes

mkdir -p /app/data
chmod 700 /app/data

# Ensure strict permissions on files
find /app/data -type f -exec chmod 600 {} \;

# Run one-shot migration if legacy users.json is present
if [ -f /app/data/users.json ]; then
    echo "Migrating legacy users.json..."
    python migrate_users.py || true
fi

# Ensure server_config.json exists so Docker doesn't create a directory
if [ ! -f /app/data/server_config.json ]; then
    echo '{}' > /app/data/server_config.json
fi
chmod 600 /app/data/server_config.json

# Asegurar que los archivos estáticos tengan los permisos correctos
echo "Configurando permisos de archivos estáticos..."
chmod -R 755 /usr/share/nginx/html
chown -R www-data:www-data /usr/share/nginx/html

# Verificar que nginx esté configurado correctamente
echo "Verificando configuración de nginx..."
nginx -t

echo "Iniciando nginx..."
# Iniciar nginx en background
nginx -g "daemon off;" &
NGINX_PID=$!

echo "Esperando a que nginx se inicie..."
sleep 2

echo "Iniciando backend Python..."
# Iniciar el backend de Python
python backend.py &
BACKEND_PID=$!

echo "Servicios iniciados. Nginx PID: $NGINX_PID, Backend PID: $BACKEND_PID"

# Función para manejar señales de terminación
cleanup() {
    echo "Deteniendo servicios..."
    kill $NGINX_PID $BACKEND_PID 2>/dev/null || true
    wait $NGINX_PID $BACKEND_PID 2>/dev/null || true
    echo "Servicios detenidos"
}

# Capturar señales de terminación
trap cleanup SIGTERM SIGINT

# Esperar a que ambos procesos terminen
wait
