import cv2
import mediapipe as mp
import numpy as np
import os
import math
import urllib.request
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# URL oficial del modelo Pose Landmarker Lite
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
MODEL_PATH = "pose_landmarker_lite.task"

def descargar_modelo_si_no_existe():
    """Descarga el modelo pose_landmarker_lite.task de Google si no está presente localmente."""
    if not os.path.exists(MODEL_PATH):
        print(f"El modelo '{MODEL_PATH}' no se encontró. Descargándolo de {MODEL_URL}...")
        try:
            # Crear un directorio temporal si es necesario, pero aquí lo guardamos en la carpeta actual
            urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
            print("Descarga completada exitosamente.")
        except Exception as e:
            print(f"Error al descargar el modelo: {e}")
            raise FileNotFoundError(f"No se pudo descargar el archivo del modelo desde {MODEL_URL}. Por favor, descárgalo manualmente.")

class PoseDetector:
    """Clase para manejar la detección de pose con MediaPipe de forma eficiente."""
    def __init__(self, confidence_threshold=0.5):
        descargar_modelo_si_no_existe()
        
        self.base_options = python.BaseOptions(
            model_asset_path=MODEL_PATH
        )
        self.options = vision.PoseLandmarkerOptions(
            base_options=self.base_options,
            running_mode=vision.RunningMode.IMAGE,
            num_poses=1,
            min_pose_detection_confidence=confidence_threshold,
            min_pose_presence_confidence=confidence_threshold
        )
        self.detector = vision.PoseLandmarker.create_from_options(self.options)

    def procesar_frame(self, frame):
        """Procesa un frame BGR de OpenCV y devuelve los landmarks detectados."""
        # MediaPipe requiere formato RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=rgb_frame
        )
        resultado = self.detector.detect(mp_image)
        
        if len(resultado.pose_landmarks) > 0:
            return resultado.pose_landmarks[0]
        return None

    def close(self):
        """Libera los recursos del detector."""
        self.detector.close()

def calcular_flexion_tronco(hombro, cadera):
    """
    Calcula el ángulo de flexión del tronco en grados con respecto a la vertical.
    hombro: [x, y] coordenadas en píxeles.
    cadera: [x, y] coordenadas en píxeles.
    """
    # Vector desde la cadera hasta el hombro
    vector_tronco = np.array([
        hombro[0] - cadera[0],
        hombro[1] - cadera[1]
    ])

    # Vector vertical hacia arriba (en coordenadas de imagen, y disminuye hacia arriba, por eso -1)
    vector_vertical = np.array([0, -1])

    # Producto punto y norma
    denominador = np.linalg.norm(vector_tronco) * np.linalg.norm(vector_vertical)
    if denominador == 0:
        return 0.0
        
    coseno = np.dot(vector_tronco, vector_vertical) / denominador
    coseno = np.clip(coseno, -1.0, 1.0)

    # Ángulo en grados
    angulo = np.degrees(np.arccos(coseno))
    return angulo

def obtener_landmarks_tronco(landmarks, lado, ancho, alto):
    """
    Obtiene los puntos de hombro y cadera según el lado seleccionado.
    lado: 'Izquierdo', 'Derecho' o 'Auto'
    """
    # Índices de landmarks de pose:
    # 11: hombro izquierdo, 12: hombro derecho
    # 23: cadera izquierda, 24: cadera derecha
    
    idx_hombro_izq, idx_cadera_izq = 11, 23
    idx_hombro_der, idx_cadera_der = 12, 24

    if lado == "Auto":
        # Se determina el lado según la visibilidad de los hombros en MediaPipe
        vis_izq = landmarks[idx_hombro_izq].visibility
        vis_der = landmarks[idx_hombro_der].visibility
        if vis_izq >= vis_der:
            hombro_lm = landmarks[idx_hombro_izq]
            cadera_lm = landmarks[idx_cadera_izq]
            lado_detectado = "Izquierdo"
        else:
            hombro_lm = landmarks[idx_hombro_der]
            cadera_lm = landmarks[idx_cadera_der]
            lado_detectado = "Derecho"
    elif lado == "Izquierdo":
        hombro_lm = landmarks[idx_hombro_izq]
        cadera_lm = landmarks[idx_cadera_izq]
        lado_detectado = "Izquierdo"
    else: # Derecho
        hombro_lm = landmarks[idx_hombro_der]
        cadera_lm = landmarks[idx_cadera_der]
        lado_detectado = "Derecho"

    p_hombro = [int(hombro_lm.x * ancho), int(hombro_lm.y * alto)]
    p_cadera = [int(cadera_lm.x * ancho), int(cadera_lm.y * alto)]
    
    return p_hombro, p_cadera, lado_detectado

def dibujar_angulo_en_cadera(imagen, cadera, hombro, angulo, config=None):
    """
    Dibuja la vertical, la línea del tronco, el arco del ángulo sombreado y los puntos clave.
    config es un diccionario opcional para personalizar colores y grosores.
    """
    # Valores de configuración por defecto (BGR)
    default_config = {
        "color_vertical": (255, 100, 0),    # Azul vibrante / Celeste
        "color_tronco": (0, 255, 100),     # Verde brillante
        "color_arco": (0, 0, 255),         # Rojo/Naranja
        "color_puntos": (0, 255, 100),     # Verde para los círculos
        "color_texto": (255, 255, 255),    # Blanco
        "grosor_lineas": 4,
        "grosor_tronco": 6,
        "grosor_borde_arco": 3,
        "radio_hombro": 12,
        "radio_cadera": 38,
        "radio_arco": 90,
        "transparencia_arco": 0.35
    }
    
    if config is not None:
        default_config.update(config)
        
    cfg = default_config
    xc, yc = cadera
    xh, yh = hombro
    radio = cfg["radio_arco"]

    # 1. DIBUJAR LÍNEA VERTICAL DE REFERENCIA (Hacia arriba)
    # Hacemos la longitud proporcional a la distancia del tronco o fija
    dist_tronco = int(math.hypot(xh - xc, yh - yc))
    longitud_vertical = max(200, int(dist_tronco * 0.8))
    
    cv2.line(
        imagen,
        (xc, yc),
        (xc, yc - longitud_vertical),
        cfg["color_vertical"],
        cfg["grosor_lineas"]
    )

    # 2. DIBUJAR LÍNEA DEL TRONCO
    cv2.line(
        imagen,
        (xc, yc),
        (xh, yh),
        cfg["color_tronco"],
        cfg["grosor_tronco"]
    )

    # 3. DIBUJAR SOMBREADO DEL ÁNGULO (CON TRANSPARENCIA)
    overlay = imagen.copy()
    dx = xh - xc
    dy = yh - yc
    
    angulo_tronco = math.degrees(math.atan2(dy, dx))
    angulo_vertical = -90

    inicio = angulo_vertical
    fin = angulo_tronco

    if fin < inicio:
        inicio, fin = fin, inicio

    # Dibujar arco relleno en el overlay
    cv2.ellipse(
        overlay,
        (xc, yc),
        (radio, radio),
        0,
        inicio,
        fin,
        cfg["color_arco"],
        -1
    )

    # Mezclar imagen con transparencia
    cv2.addWeighted(
        overlay,
        cfg["transparencia_arco"],
        imagen,
        1 - cfg["transparencia_arco"],
        0,
        imagen
    )

    # 4. DIBUJAR BORDE DEL ÁNGULO
    cv2.ellipse(
        imagen,
        (xc, yc),
        (radio, radio),
        0,
        inicio,
        fin,
        cfg["color_arco"],
        cfg["grosor_borde_arco"]
    )

    # 5. DIBUJAR PUNTO DEL HOMBRO (Pequeño)
    cv2.circle(
        imagen,
        (xh, yh),
        cfg["radio_hombro"],
        cfg["color_puntos"],
        -1
    )

    # 6. DIBUJAR PUNTO DE LA CADERA (Grande, donde se coloca el texto)
    cv2.circle(
        imagen,
        (xc, yc),
        cfg["radio_cadera"],
        cfg["color_puntos"],
        -1
    )

    # 7. ESCRIBIR EL ÁNGULO DENTRO DE LA CADERA
    texto = f"{angulo:.1f}°"
    # Determinar el tamaño del texto para centrarlo
    (tw, th), _ = cv2.getTextSize(
        texto,
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        2
    )

    cv2.putText(
        imagen,
        texto,
        (
            int(xc - tw / 2),
            int(yc + th / 2)
        ),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        cfg["color_texto"],
        2,
        cv2.LINE_AA
    )
