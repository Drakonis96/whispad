# Dockerfile para servir la aplicación solo con Python
FROM python:3.11-slim

# Instalar herramientas de compilación y dependencias del sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    curl \
    ffmpeg \
    openssl \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /app

# Copiar archivos de requirements y instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

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


# Crear directorio para notas guardadas con permisos apropiados
RUN mkdir -p /app/saved_notes && \
    chmod 777 /app/saved_notes

# Hacer ejecutable el script de inicio
RUN chmod +x start.sh

# Exponer puerto
EXPOSE 5037

# Comando de inicio
CMD ["./start.sh"]
