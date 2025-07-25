#!/bin/bash

# Script para iniciar tanto nginx como el backend de Python
set -e

echo "Iniciando servicios..."

# Crear directorios necesarios para nginx
mkdir -p /var/log/nginx
mkdir -p /var/lib/nginx

# Rutas por defecto del certificado
CERT_PATH="/etc/nginx/certs/selfsigned.crt"
KEY_PATH="/etc/nginx/certs/selfsigned.key"

# Usar Let's Encrypt si se definen las variables
if [ -n "$LETSENCRYPT_DOMAIN" ] && [ -n "$LETSENCRYPT_EMAIL" ]; then
    CERT_PATH="/etc/letsencrypt/live/${LETSENCRYPT_DOMAIN}/fullchain.pem"
    KEY_PATH="/etc/letsencrypt/live/${LETSENCRYPT_DOMAIN}/privkey.pem"
    if [ ! -f "$CERT_PATH" ]; then
        echo "Obteniendo certificado de Let's Encrypt para $LETSENCRYPT_DOMAIN..."
        certbot certonly --standalone --non-interactive --agree-tos \
            -m "$LETSENCRYPT_EMAIL" -d "$LETSENCRYPT_DOMAIN"
    else
        # Renovar si queda menos de 30 días para el vencimiento
        EXP_DATE=$(openssl x509 -enddate -noout -in "$CERT_PATH" | cut -d= -f2)
        EXP_SEC=$(date -d "$EXP_DATE" +%s)
        NOW_SEC=$(date +%s)
        DAYS_LEFT=$(( (EXP_SEC - NOW_SEC) / 86400 ))
        if [ "$DAYS_LEFT" -le 30 ]; then
            echo "Renovando certificado de Let's Encrypt..."
            certbot certonly --standalone --non-interactive --agree-tos --force-renewal \
                -m "$LETSENCRYPT_EMAIL" -d "$LETSENCRYPT_DOMAIN"
        fi
    fi
fi

# Generar certificado SSL autofirmado si no existe el elegido
if [ ! -f "$CERT_PATH" ]; then
    echo "Generando certificado SSL autofirmado..."
    mkdir -p /etc/nginx/certs
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout /etc/nginx/certs/selfsigned.key \
        -out /etc/nginx/certs/selfsigned.crt \
        -subj "/CN=localhost"
    CERT_PATH="/etc/nginx/certs/selfsigned.crt"
    KEY_PATH="/etc/nginx/certs/selfsigned.key"
fi

# Crear y configurar directorios persistentes
mkdir -p /app/saved_notes /app/saved_audios
chmod 777 /app/saved_notes /app/saved_audios

# Note: Configuration is now stored in PostgreSQL database
# users.json and server_config.json will be migrated automatically if they exist
# from previous versions and then removed

# Asegurar que los archivos estáticos tengan los permisos correctos
echo "Configurando permisos de archivos estáticos..."
chmod -R 755 /usr/share/nginx/html
chown -R www-data:www-data /usr/share/nginx/html

# Preparar configuración de nginx con las rutas correctas
export SSL_CERT_PATH="$CERT_PATH"
export SSL_KEY_PATH="$KEY_PATH"
envsubst '$SSL_CERT_PATH $SSL_KEY_PATH' < /etc/nginx/nginx.conf.template > /etc/nginx/sites-available/default
ln -sf /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default

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
