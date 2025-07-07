# WhisPad Flutter App

Esta aplicación es un contenedor sencillo de la interfaz web de WhisPad. Permite introducir la URL del servidor y, opcionalmente, credenciales de autenticación basic (usuario y contraseña). Una vez conectados, se carga la interfaz web en un `WebView` y se pueden tomar notas y grabar audio igual que en la versión móvil del navegador.

## Uso

1. Instala Flutter en tu máquina siguiendo la documentación oficial.
2. Ejecuta `flutter pub get` dentro de esta carpeta para descargar las dependencias.
3. Conecta un dispositivo iOS o abre un simulador y ejecuta:

```bash
flutter run
```

Para generar un build de producción para iOS utiliza:

```bash
flutter build ios --release
```

Asegúrate de que en `ios/Runner/Info.plist` esté incluida la clave `NSMicrophoneUsageDescription` para permitir el acceso al micrófono.
