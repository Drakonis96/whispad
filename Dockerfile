# Dockerfile unificado para nginx + python backend
FROM python:3.11-slim

ARG PUID=1000
ARG PGID=1000

RUN groupadd -g ${PGID} appgroup \
    && useradd -u ${PUID} -g appgroup -m appuser

# Instalar nginx, build tools y dependencias del sistema
RUN apt-get update && apt-get install -y \
    nginx \
    build-essential \
    cmake \
    git \
    git-lfs \
    curl \
    ffmpeg \
    openssl \
    && rm -rf /var/lib/apt/lists/*

# Configurar git-lfs
RUN git lfs install

# Crear directorio de trabajo
WORKDIR /app

# Copiar archivos de requirements y instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instalar PyTorch con torchaudio para SenseVoice
RUN pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Copiar todos los archivos de la aplicación
COPY . .

# Compilar whisper.cpp en el contenedor con configuración básica
RUN if [ -d "whisper.cpp-main" ]; then \
        cd whisper.cpp-main && \
        rm -rf build && \
        mkdir -p build && \
        cmake -B build \
            -DCMAKE_BUILD_TYPE=Release \
            -DGGML_NATIVE=OFF \
            -DGGML_ACCELERATE=OFF \
            -DGGML_BLAS=OFF \
            -DGGML_METAL=OFF \
            -DGGML_CUDA=OFF \
            -DGGML_VULKAN=OFF \
            -DGGML_OPENMP=ON && \
        cmake --build build --config Release --parallel $(nproc) && \
        echo "Whisper.cpp compiled successfully with basic configuration"; \
    else \
        echo "Whisper.cpp source not found, skipping compilation"; \
    fi

# Verificar que el binario fue compilado correctamente
RUN if [ -f "whisper.cpp-main/build/bin/whisper-cli" ]; then \
        echo "Whisper-cli binary found and ready"; \
        ls -la whisper.cpp-main/build/bin/whisper-cli; \
    else \
        echo "Warning: whisper-cli binary not found"; \
    fi

# Configurar nginx
COPY nginx.conf /etc/nginx/sites-available/default
RUN rm -f /etc/nginx/sites-enabled/default && \
    ln -s /etc/nginx/sites-available/default /etc/nginx/sites-enabled/

# Copiar archivos estáticos al directorio que nginx puede servir
RUN mkdir -p /usr/share/nginx/html && \
    cp index.html /usr/share/nginx/html/ && \
    cp style.css /usr/share/nginx/html/ && \
    cp app.js /usr/share/nginx/html/ && \
    cp backend-api.js /usr/share/nginx/html/ && \
    cp -r note-transcribe-ai /usr/share/nginx/html/ || true && \
    cp -r logos /usr/share/nginx/html/ || true

# Dar permisos correctos a los archivos estáticos
RUN chmod -R 755 /usr/share/nginx/html && \
    chown -R appuser:appgroup /usr/share/nginx/html

# Crear directorios para logs de nginx y notas guardadas
RUN mkdir -p /var/log/nginx && \
    touch /var/log/nginx/access.log && \
    touch /var/log/nginx/error.log && \
    chmod 640 /var/log/nginx/access.log && \
    chmod 640 /var/log/nginx/error.log && \
    chmod 700 /var/log/nginx && \
    chown -R appuser:appgroup /var/log/nginx
RUN mkdir -p /var/lib/nginx && \
    chmod 700 /var/lib/nginx && \
    chown -R appuser:appgroup /var/lib/nginx

# Crear directorio para datos y establecer permisos
RUN mkdir -p /app/data && \
    chown -R appuser:appgroup /app/data && \
    chmod 700 /app/data

# Crear directorio para notas guardadas con permisos apropiados
RUN mkdir -p /app/saved_notes && \
    chmod 700 /app/saved_notes && \
    chown -R appuser:appgroup /app/saved_notes

# Hacer ejecutable el script de inicio
RUN chmod +x start.sh

# Cambiar a usuario no root
USER appuser

# Exponer puerto
EXPOSE 5037

# Comando de inicio
CMD ["./start.sh"]
