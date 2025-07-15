# Use multi-stage build to minimize final image size

# Stage 1: build whisper.cpp
FROM python:3.11-slim AS builder
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        git \
        git-lfs \
    && rm -rf /var/lib/apt/lists/*
RUN git lfs install
WORKDIR /build
COPY whisper.cpp-main ./whisper.cpp-main
RUN cd whisper.cpp-main \
    && mkdir -p build \
    && cmake -B build \
        -DCMAKE_BUILD_TYPE=Release \
        -DGGML_NATIVE=OFF \
        -DGGML_ACCELERATE=OFF \
        -DGGML_BLAS=OFF \
        -DGGML_METAL=OFF \
        -DGGML_CUDA=OFF \
        -DGGML_VULKAN=OFF \
        -DGGML_OPENMP=ON \
    && cmake --build build --config Release --parallel $(nproc)

# Stage 2: runtime image
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
        nginx \
        curl \
        ffmpeg \
        openssl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Install PyTorch for SenseVoice
RUN pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Copy application source
COPY . .
# Copy compiled whisper.cpp from builder stage
COPY --from=builder /build/whisper.cpp-main/build /app/whisper.cpp-main/build

# Configure nginx
COPY nginx.conf /etc/nginx/sites-available/default
RUN rm -f /etc/nginx/sites-enabled/default \
    && ln -s /etc/nginx/sites-available/default /etc/nginx/sites-enabled/

# Copy static files to nginx directory
RUN mkdir -p /usr/share/nginx/html \
    && cp index.html /usr/share/nginx/html/ \
    && cp style.css /usr/share/nginx/html/ \
    && cp app.js /usr/share/nginx/html/ \
    && cp backend-api.js /usr/share/nginx/html/ \
    && cp -r note-transcribe-ai /usr/share/nginx/html/ || true \
    && cp -r logos /usr/share/nginx/html/ || true

RUN chmod -R 755 /usr/share/nginx/html \
    && chown -R www-data:www-data /usr/share/nginx/html

# Prepare log and data directories
RUN mkdir -p /var/log/nginx \
    && touch /var/log/nginx/access.log \
    && touch /var/log/nginx/error.log \
    && chmod 666 /var/log/nginx/access.log \
    && chmod 666 /var/log/nginx/error.log

RUN mkdir -p /app/saved_notes /app/saved_audios \
    && chmod 777 /app/saved_notes /app/saved_audios

RUN chmod +x start.sh

EXPOSE 5037
CMD ["./start.sh"]
