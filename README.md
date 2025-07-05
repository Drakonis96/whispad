<p align="center">
  <img src="logos/logo.png" alt="WhisPad Logo" width="120"/>
</p>

# WhisPad

WhisPad es una herramienta de transcripción y gestión de notas diseñada para que cualquier persona pueda pasar su voz a texto y organizar sus ideas fácilmente. La aplicación permite usar modelos en la nube (OpenAI, Google) o modelos locales de whisper.cpp para trabajar sin conexión.

## Tabla de contenido
1. [Características principales](#caracteristicas-principales)
2. [Instalación rápida](#instalacion-rapida)
3. [Instalación con Docker Desktop](#instalacion-con-docker-desktop)
4. [Instalación desde la terminal](#instalacion-desde-la-terminal)
5. [Configuración de claves API](#configuracion-de-claves-api)
6. [Guía de uso](#guia-de-uso)

## Características principales
- Transcripción de voz a texto en tiempo real desde el navegador.
- Compatibilidad con varios proveedores: OpenAI, Google y whisper.cpp local.
- Posibilidad de cargar modelos locales (.bin) para whisper.cpp directamente desde la interfaz.
- Mejora automática de texto mediante IA (OpenAI, Google o OpenRouter) con respuestas en streaming.
- Gestor de notas integrado: crear, buscar, etiquetar, guardar, restaurar y descargar en formato Markdown.
- Exportación de todas las notas en un ZIP con un solo clic.
- Interfaz moderna adaptada a móviles sin hacer zoom al escribir y con un marcador azul que indica dónde se insertará la transcripción.

## Instalación rápida
Si no tienes conocimientos de la terminal, la forma más sencilla es usando **Docker Desktop**. Solo necesitas instalar Docker, descargar este proyecto y ejecutarlo.

1. Descarga Docker Desktop desde <https://www.docker.com/products/docker-desktop/> e instálalo como cualquier otra aplicación.
2. Descarga este repositorio en formato ZIP desde la página de GitHub y descomprímelo en la carpeta que prefieras.
3. Abre Docker Desktop y selecciona **Open in Terminal** (o abre una terminal en esa carpeta). Escribe:
   ```bash
   docker compose up
   ```
4. Docker descargará las dependencias y mostrará el mensaje *"Iniciando servicios..."*. Cuando veas que todo está listo, abre tu navegador en `http://localhost:5037`.
5. Para detener la aplicación, pulsa `Ctrl+C` en la terminal o usa el botón *Stop* de Docker Desktop.

## Instalación con Docker Desktop
Esta opción es ideal si no quieres preocuparte por instalar Python o dependencias manualmente.

1. Instala **Docker Desktop**.
2. Abre una terminal y clona el repositorio:
   ```bash
   git clone https://github.com/tu_usuario/whispad.git
   cd whispad
   ```
   (Si lo prefieres, descarga el ZIP y descomprímelo).
3. Ejecuta la aplicación con:
   ```bash
   docker compose up
   ```
4. Accede a `http://localhost:5037` y empieza a usar WhisPad.
5. Para pararlo, usa `Ctrl+C` en la terminal o `docker compose down`.

## Instalación desde la terminal
Si prefieres no usar Docker, también puedes ejecutarlo directamente con Python:

1. Asegúrate de tener **Python 3.11** o superior y **pip** instalados.
2. Clona el repositorio o descarga el código y accede a la carpeta del proyecto:
   ```bash
   git clone https://github.com/tu_usuario/whispad.git
   cd whispad
   ```
3. Instala las dependencias de Python:
   ```bash
   pip install -r requirements.txt
   ```
4. (Opcional) Descarga un modelo de whisper.cpp con el script incluido:
   ```bash
   bash install-whisper-cpp.sh
   ```
   También puedes subir tus propios modelos `.bin` desde la interfaz.
5. Ejecuta el servidor:
   ```bash
   python backend.py
   ```
6. Abre `index.html` en tu navegador o sirve la carpeta con `python -m http.server 5037` y visita `http://localhost:5037`.

## Configuración de claves API
Copia `env.example` como `.env` y coloca tus claves de API:
```bash
cp env.example .env
```
Edita el archivo `.env` y rellena las variables `OPENAI_API_KEY`, `GOOGLE_API_KEY`, `DEEPSEEK_API_KEY` y `OPENROUTER_API_KEY` según los servicios que quieras usar. Estas claves permiten la transcripción en la nube y la mejora de texto.

## Guía de uso
1. Pulsa el botón del micrófono para grabar audio y obtén la transcripción en tiempo real.
2. Selecciona fragmentos de texto y aplica mejoras de estilo o claridad con un clic.
3. Organiza tus notas: ponles título, etiquetas y búscalas fácilmente.
4. Descarga cada nota en Markdown o todo el conjunto en un archivo ZIP.
5. Si dispones de modelos locales de whisper.cpp, cárgalos desde el menú **Upload models** y disfruta de transcripción sin conexión.
6. Utiliza el menú **Restore** para importar notas guardadas anteriormente.

Con estas instrucciones deberías tener WhisPad funcionando en pocos minutos tanto con Docker como sin él. ¡Disfruta de una transcripción rápida y de todas las ventajas de organizar tus ideas en un mismo lugar!

