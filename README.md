# Sistema de Análisis de Flexión de Tronco y Cuello

Este es un sistema de escritorio interactivo diseñado para medir los ángulos de flexión de tronco y cuello en tiempo real a partir de imágenes estáticas y grabaciones de video, utilizando la tecnología de estimación de pose de **MediaPipe**. 

El software cuenta con una interfaz gráfica moderna, totalmente responsiva y adaptada a resoluciones de alta densidad (DPI), facilitando el registro clínico de los segmentos evaluados en planillas Excel.

---

## Stack Tecnológico

El sistema ha sido desarrollado utilizando las siguientes tecnologías y librerías:

* **Lenguaje de Programación**: Python 3.8 o superior.
* **Interfaz Gráfica (GUI)**: [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) (una envoltura moderna sobre Tkinter que proporciona un diseño oscuro responsivo nativo y soporte para escalado DPI).
* **Estimación de Pose (IA/ML)**: [MediaPipe](https://github.com/google-ai-edge/mediapipe) (modelo Pose Landmarker de Google para la detección de landmarks corporales en tiempo real).
* **Visión por Computadora**: [OpenCV](https://opencv.org/) (`opencv-python`) para la lectura y decodificación de secuencias de video, procesamiento de frames y dibujo geométrico de overlays analíticos.
* **Manejo de Imágenes**: [Pillow](https://python-pillow.org/) (`PIL`) para la conversión de formatos de color e integración de frames a widgets CustomTkinter.
* **Persistencia de Datos (Excel)**: [OpenPyXL](https://openpyxl.readthedocs.io/) para la creación, lectura y registro asíncrono de reportes clínicos en planillas `.xlsx`.

---

## Características Principales

* **Estimación de Pose Avanzada**: Detección y dibujo automático de los puntos clave del hombro, cadera y oreja usando el modelo Pose Landmarker de MediaPipe.
* **Cálculo de Ángulos Anatómicos**:
  * **Ángulo de Tronco**: Inclinación del tronco respecto a la vertical que pasa por la cadera.
  * **Ángulo de Cuello**: Inclinación del cuello respecto a la prolongación de la línea del tronco.
* **Seguimiento de Permanencia Postural**: Mide con precisión el tiempo que la persona evaluada mantiene una misma postura estable en segundos.
* **Visor Responsivo (DPI-Aware)**: Adaptación automática de la visualización al tamaño de la ventana sin deformar la relación de aspecto del video ni recortar bordes en pantallas con escalado DPI (Windows).
* **Registro Clínico Integrado**: Permite registrar las sesiones en una hoja de Excel (`registro_posturas.xlsx`), exportando los ángulos, el lado medido y los tiempos de permanencia agrupados por segmento de postura.
* **Arquitectura Modular**: Código desacoplado siguiendo principios de diseño MVC/MVVM que separan la interfaz (vistas), la lógica de negocio y procesamiento de hilos.

---

## Requisitos de Instalación

1. **Python**: Asegúrate de tener Python 3.8 o superior instalado en tu sistema.
2. **Dependencias**: Instala los paquetes requeridos ejecutando el siguiente comando en la terminal:
   ```bash
   pip install -r requirements.txt
   ```

*(Nota: La primera vez que inicies la aplicación, el modelo preentrenado `pose_landmarker_lite.task` se descargará automáticamente de forma interna).*

---

## Cómo Ejecutar la Aplicación

Para iniciar la aplicación, ejecuta el archivo principal `app.py`:
```bash
python app.py
```

### Instrucciones de Uso:
1. Presiona el botón **Seleccionar Imagen / Video** y carga un archivo multimedia (soporta `.jpg`, `.png`, `.mp4`, `.avi`, `.mov`).
2. Configura los parámetros en el panel lateral:
   * **Lado a medir**: Selecciona `"Auto"` (el detector elegirá el lado más visible), o fuérzalo a `"Izquierdo"` o `"Derecho"`.
   * **Confianza**: Ajusta la confianza mínima del detector para filtrar falsos positivos.
3. Si cargaste un video:
   * Usa los botones **Reproducir** y **Pausar** para controlar la reproducción.
   * La interfaz mostrará en tiempo real los ángulos medidos y el **tiempo estable** de permanencia de la postura.
4. Para registrar los datos del paciente:
   * Escribe el nombre en el campo **Nombre de la Persona**.
   * Presiona **Registrar en Excel** para anexar los datos al archivo local de registro.

---

## Arquitectura y Patrones de Diseño

El proyecto está diseñado bajo una arquitectura limpia que separa las responsabilidades de lógica de negocio, procesamiento asíncrono e interfaz de usuario, inspirada en el patrón **MVC (Modelo-Vista-Controlador)**:

### 1. Modelo (Model)
Contiene la lógica de negocio pura y la persistencia de datos, independiente de la GUI:
* **[tracker.py](file:///c:/Users/USER/Desktop/Detector%20de%20angulos/Detector-de-Angulos/tracker.py)**: Mantiene el estado del análisis (tiempos de permanencia y segmentos de postura). Escrito en **Python puro**.
* **[detector.py](file:///c:/Users/USER/Desktop/Detector%20de%20angulos/Detector-de-Angulos/detector.py)**: Realiza cálculos geométricos (trigonometría vectorial con **NumPy**) y carga el modelo de inferencia de **MediaPipe**.
* **[excel_exporter.py](file:///c:/Users/USER/Desktop/Detector%20de%20angulos/Detector-de-Angulos/excel_exporter.py)**: Gestiona la exportación y guardado de datos a Excel utilizando **OpenPyXL**.

### 2. Vista (View)
Implementa los elementos visuales de la interfaz de usuario en la carpeta `gui/`, utilizando **CustomTkinter** y **Pillow** para procesar e integrar imágenes responsivamente:
* **[gui/sidebar.py](file:///c:/Users/USER/Desktop/Detector%20de%20angulos/Detector-de-Angulos/gui/sidebar.py)**: Formulario lateral izquierdo para controles de entrada e interacción del usuario.
* **[gui/dashboard.py](file:///c:/Users/USER/Desktop/Detector%20de%20angulos/Detector-de-Angulos/gui/dashboard.py)**: Muestra en pantalla las métricas de ángulos y tiempos de forma dinámica.
* **[gui/visualizer.py](file:///c:/Users/USER/Desktop/Detector%20de%20angulos/Detector-de-Angulos/gui/visualizer.py)**: Canvas responsivo que adapta y escala el flujo de fotogramas según la resolución de pantalla DPI del usuario.

### 3. Controlador / Hilos Asíncronos (Controller & Workers)
Coordina la interacción entre el modelo y las vistas, y gestiona la ejecución en segundo plano:
* **[app.py](file:///c:/Users/USER/Desktop/Detector%20de%20angulos/Detector-de-Angulos/app.py)**: Clase principal que actúa como el **Controlador**. Instancia las vistas, responde a sus callbacks, actualiza el tracker de postura y reenvía los fotogramas procesados al visor.
* **[video_processor.py](file:///c:/Users/USER/Desktop/Detector%20de%20angulos/Detector-de-Angulos/video_processor.py)**: Hilo de fondo (**Worker** mediante `threading.Thread`) que lee y analiza los frames del video de forma asíncrona sin bloquear la interfaz de usuario, comunicándose con el controlador mediante una cola segura de subprocesos (`queue.Queue`).

### Estructura de Directorios del Código
```
Detector-de-Angulos/
├── app.py                      # Controlador principal y punto de entrada (GUI principal)
├── video_processor.py           # Worker: Procesa y decodifica frames en un hilo secundario
├── tracker.py                  # Modelo: Registra y agrupa segmentos y tiempos estables
├── excel_exporter.py           # Utilidad: Escritura limpia y manipulación del archivo Excel
├── detector.py                 # MediaPipe: Detector y cálculo geométrico de ángulos
├── requirements.txt            # Dependencias del proyecto
├── test_calculations.py        # Pruebas unitarias de las fórmulas de ángulos
├── test_tracker.py             # Pruebas unitarias del seguimiento de segmentos de postura
└── gui/                        # Vistas y componentes visuales de CustomTkinter
    ├── __init__.py
    ├── sidebar.py              # Panel lateral de configuración y controles
    ├── dashboard.py            # Tarjetas del dashboard de visualización de métricas
    └── visualizer.py           # Lienzo de renderizado y escalado responsivo del video
```

### Lenguajes y Paradigmas de Programación
* **Python 3**: Utilizado para el 100% del desarrollo del sistema.
* **Paradigma Orientado a Objetos (POO)**: Estructuración de componentes gráficos y modelos de negocio.
* **Programación Asíncrona / Multihilo**: Ejecución paralela del flujo de video y MediaPipe para prevenir congelamiento de la GUI.

### Desarrollo del Frontend (Interfaz de Usuario)
La interfaz de usuario (Frontend) de esta aplicación de escritorio está desarrollada utilizando:
* **CustomTkinter**: Para todos los widgets y componentes estilizados de la GUI (botones, menús de opciones, entradas de texto y controles deslizantes con tema oscuro nativo).
* **Tkinter (Biblioteca Estándar de Python)**: Controla el gestor de cuadrícula (`grid`), la asignación de pesos de filas/columnas para el comportamiento responsivo, y el manejo de eventos y ciclos de vida de ventanas (como el cierre de la ventana y el evento `<Configure>` de redimensionado).
* **Pillow (PIL)**: Se encarga de procesar los frames decodificados en memoria, convirtiéndolos a formatos compatibles y escalándolos en coordenadas lógicas para mantener la nitidez en pantallas de alta resolución.
* **OpenCV**: Dibuja dinámicamente y con precisión milimétrica los overlays biomecánicos (orejas, hombros, caderas, vectores de inclinación y arcos coloreados de flexión) directamente sobre la imagen original en alta definición.


---

## Pruebas de Calidad (Testing)

El sistema incluye pruebas automatizadas completas para validar las funciones matemáticas y la precisión del acumulador de posturas. Para ejecutarlas, corre:
```bash
python -m unittest discover -p "test_*.py"
```
