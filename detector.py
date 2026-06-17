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

def calcular_flexion_cuello(cadera, hombro, oreja):
    """
    Calcula el ángulo de flexión del cuello en grados relativo a la prolongación del tronco.
    cadera: [x, y] coordenadas en píxeles.
    hombro: [x, y] coordenadas en píxeles.
    oreja: [x, y] coordenadas en píxeles.
    """
    vector_tronco = np.array([hombro[0] - cadera[0], hombro[1] - cadera[1]])
    vector_cuello = np.array([oreja[0] - hombro[0], oreja[1] - hombro[1]])
    
    norm_tronco = np.linalg.norm(vector_tronco)
    norm_cuello = np.linalg.norm(vector_cuello)
    
    if norm_tronco == 0 or norm_cuello == 0:
        return 0.0
        
    coseno = np.dot(vector_tronco, vector_cuello) / (norm_tronco * norm_cuello)
    coseno = np.clip(coseno, -1.0, 1.0)
    
    return np.degrees(np.arccos(coseno))

def obtener_landmarks_analisis(landmarks, lado, ancho, alto):
    """
    Obtiene los puntos de cadera, hombro y oreja según el lado seleccionado.
    lado: 'Izquierdo', 'Derecho' o 'Auto'
    """
    # Índices de landmarks de pose:
    # 11: hombro izquierdo, 12: hombro derecho
    # 23: cadera izquierda, 24: cadera derecha
    # 7: oreja izquierda, 8: oreja derecha
    
    idx_hombro_izq, idx_cadera_izq, idx_oreja_izq = 11, 23, 7
    idx_hombro_der, idx_cadera_der, idx_oreja_der = 12, 24, 8

    if lado == "Auto":
        # Se determina el lado según la visibilidad de los hombros en MediaPipe
        vis_izq = landmarks[idx_hombro_izq].visibility
        vis_der = landmarks[idx_hombro_der].visibility
        if vis_izq >= vis_der:
            hombro_lm = landmarks[idx_hombro_izq]
            cadera_lm = landmarks[idx_cadera_izq]
            oreja_lm = landmarks[idx_oreja_izq]
            lado_detectado = "Izquierdo"
        else:
            hombro_lm = landmarks[idx_hombro_der]
            cadera_lm = landmarks[idx_cadera_der]
            oreja_lm = landmarks[idx_oreja_der]
            lado_detectado = "Derecho"
    elif lado == "Izquierdo":
        hombro_lm = landmarks[idx_hombro_izq]
        cadera_lm = landmarks[idx_cadera_izq]
        oreja_lm = landmarks[idx_oreja_izq]
        lado_detectado = "Izquierdo"
    else: # Derecho
        hombro_lm = landmarks[idx_hombro_der]
        cadera_lm = landmarks[idx_cadera_der]
        oreja_lm = landmarks[idx_oreja_der]
        lado_detectado = "Derecho"

    p_hombro = [int(hombro_lm.x * ancho), int(hombro_lm.y * alto)]
    p_cadera = [int(cadera_lm.x * ancho), int(cadera_lm.y * alto)]
    p_oreja = [int(oreja_lm.x * ancho), int(oreja_lm.y * alto)]
    
    return p_hombro, p_cadera, p_oreja, lado_detectado


def dibujar_analisis_completo(imagen, cadera, hombro, oreja, angulo_tronco, angulo_cuello, config=None):
    """
    Dibuja las guías de flexión de tronco (en cadera) y de flexión de cuello (en hombro, relativo a la prolongación del tronco).
    """
    default_config = {
        "color_vertical": (255, 100, 0),    # Celeste / azul
        "color_tronco": (0, 255, 100),     # Verde brillante
        "color_cuello": (0, 230, 255),     # Amarillo o color personalizado
        "color_arco": (0, 0, 255),         # Rojo/Naranja
        "color_puntos": (0, 255, 100),     # Verde para los círculos
        "color_texto": (255, 255, 255),    # Blanco
        "grosor_lineas": 4,
        "grosor_tronco": 6,
        "grosor_cuello": 5,
        "grosor_borde_arco": 3,
        "radio_ear": 6,
        "radio_hombro": 22,                # Suficiente para que quepa el texto del ángulo
        "radio_cadera": 22,                # Suficiente para que quepa el texto del ángulo
        "radio_arco": 90,
        "radio_arco_cuello": 70,            # Un poco más pequeño
        "transparencia_arco": 0.35,
        "dibujar_texto": True
    }
    
    if config is not None:
        default_config.update(config)
        
    cfg = default_config
    xc, yc = cadera
    xh, yh = hombro
    xo, yo = oreja

    # --- 1. DIBUJAR TRONCO ---
    dist_tronco = int(math.hypot(xh - xc, yh - yc))
    longitud_vertical = max(200, int(dist_tronco * 0.8))
    
    # Vertical de la cadera
    cv2.line(imagen, (xc, yc), (xc, yc - longitud_vertical), cfg["color_vertical"], cfg["grosor_lineas"])
    # Línea del tronco
    cv2.line(imagen, (xc, yc), (xh, yh), cfg["color_tronco"], cfg["grosor_tronco"])

    # Arco del tronco
    overlay = imagen.copy()
    dx_t = xh - xc
    dy_t = yh - yc
    ang_tronco = math.degrees(math.atan2(dy_t, dx_t))
    inicio_t = -90
    fin_t = ang_tronco
    if fin_t < inicio_t:
        inicio_t, fin_t = fin_t, inicio_t

    cv2.ellipse(overlay, (xc, yc), (cfg["radio_arco"], cfg["radio_arco"]), 0, inicio_t, fin_t, cfg["color_arco"], -1)

    # --- 2. DIBUJAR CUELLO (Prolongación del Tronco) ---
    if dist_tronco > 0:
        u_dx = dx_t / dist_tronco
        u_dy = dy_t / dist_tronco
    else:
        u_dx = 0
        u_dy = -1

    dist_cuello = int(math.hypot(xo - xh, yo - yh))
    longitud_prolongacion = max(100, int(dist_cuello * 1.2))

    # Punto final de la prolongación de la espalda
    xp = int(xh + u_dx * longitud_prolongacion)
    yp = int(yh + u_dy * longitud_prolongacion)

    # Dibujar línea de prolongación (color celeste de referencia)
    cv2.line(imagen, (xh, yh), (xp, yp), cfg["color_vertical"], cfg["grosor_lineas"])
    # Línea del cuello
    cv2.line(imagen, (xh, yh), (xo, yo), cfg["color_cuello"], cfg["grosor_cuello"])

    # Arco del cuello (entre prolongación y cuello)
    ang_prolongacion = math.degrees(math.atan2(yp - yh, xp - xh))
    ang_cuello = math.degrees(math.atan2(yo - yh, xo - xh))
    
    inicio_c = ang_prolongacion
    fin_c = ang_cuello
    if fin_c < inicio_c:
        inicio_c, fin_c = fin_c, inicio_c

    # Evitar arco mayor de 180 (dibujar el camino más corto)
    diff = fin_c - inicio_c
    if diff > 180:
        inicio_c, fin_c = fin_c, inicio_c + 360

    cv2.ellipse(overlay, (xh, yh), (cfg["radio_arco_cuello"], cfg["radio_arco_cuello"]), 0, inicio_c, fin_c, cfg["color_arco"], -1)

    # Mezclar transparencia
    cv2.addWeighted(overlay, cfg["transparencia_arco"], imagen, 1 - cfg["transparencia_arco"], 0, imagen)

    # Bordes de arcos
    cv2.ellipse(imagen, (xc, yc), (cfg["radio_arco"], cfg["radio_arco"]), 0, inicio_t, fin_t, cfg["color_arco"], cfg["grosor_borde_arco"])
    cv2.ellipse(imagen, (xh, yh), (cfg["radio_arco_cuello"], cfg["radio_arco_cuello"]), 0, inicio_c, fin_c, cfg["color_arco"], cfg["grosor_borde_arco"])

    # --- 3. DIBUJAR PUNTOS CLAVE ---
    # Punto oreja (pequeño)
    cv2.circle(imagen, (xo, yo), cfg["radio_ear"], cfg["color_puntos"], -1)
    # Punto hombro (grande)
    cv2.circle(imagen, (xh, yh), cfg["radio_hombro"], cfg["color_puntos"], -1)
    # Punto cadera (grande)
    cv2.circle(imagen, (xc, yc), cfg["radio_cadera"], cfg["color_puntos"], -1)

    # --- 4. TEXTOS DE ÁNGULOS (con 2 decimales) ---
    if cfg.get("dibujar_texto", False):
        # Texto tronco en cadera
        texto_tronco = f"{angulo_tronco:.2f}"
        (tw_t, th_t), _ = cv2.getTextSize(texto_tronco, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 2)
        cv2.putText(imagen, texto_tronco, (int(xc - tw_t / 2), int(yc + th_t / 2)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, cfg["color_texto"], 2, cv2.LINE_AA)

        # Texto cuello en hombro
        texto_cuello = f"{angulo_cuello:.2f}"
        (tw_c, th_c), _ = cv2.getTextSize(texto_cuello, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 2)
        cv2.putText(imagen, texto_cuello, (int(xh - tw_c / 2), int(yh + th_c / 2)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, cfg["color_texto"], 2, cv2.LINE_AA)
