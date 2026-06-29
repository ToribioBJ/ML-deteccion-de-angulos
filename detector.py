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

def calcular_flexion_tronco(punto_superior, cadera):
    """
    Calcula el ángulo de flexión del tronco en grados con respecto a la vertical.
    punto_superior: [x, y] coordenadas en píxeles (base del cuello manual).
    cadera: [x, y] coordenadas en píxeles.
    """
    vector_tronco = np.array([
        punto_superior[0] - cadera[0],
        punto_superior[1] - cadera[1]
    ])
    vector_vertical = np.array([0, -1])

    denominador = np.linalg.norm(vector_tronco) * np.linalg.norm(vector_vertical)
    if denominador == 0:
        return 0.0
        
    coseno = np.dot(vector_tronco, vector_vertical) / denominador
    coseno = np.clip(coseno, -1.0, 1.0)

    angulo = np.degrees(np.arccos(coseno))
    return angulo

def calcular_angulo_cabeza(oreja, ojo):
    """
    Calcula el ángulo de la cabeza en grados con respecto a la vertical que pasa por la oreja.
    oreja: [x, y] coordenadas en píxeles.
    ojo: [x, y] coordenadas en píxeles.
    """
    vector_cabeza = np.array([
        ojo[0] - oreja[0],
        ojo[1] - oreja[1]
    ])
    vector_vertical = np.array([0, -1])  # Vertical hacia arriba en la imagen

    denominador = np.linalg.norm(vector_cabeza) * np.linalg.norm(vector_vertical)
    if denominador == 0:
        return 0.0

    coseno = np.dot(vector_cabeza, vector_vertical) / denominador
    coseno = np.clip(coseno, -1.0, 1.0)

    angulo = np.degrees(np.arccos(coseno))
    return angulo

def calcular_flexion_hombro(hombro, codo, muneca):
    """
    Calcula el ángulo de flexión del codo/brazo en grados (vértice en el codo).
    hombro: [x, y] coordenadas en píxeles.
    codo: [x, y] coordenadas en píxeles.
    muneca: [x, y] coordenadas en píxeles.
    """
    vector_hombro = np.array([hombro[0] - codo[0], hombro[1] - codo[1]])
    vector_muneca = np.array([muneca[0] - codo[0], muneca[1] - codo[1]])
    
    norm_hombro = np.linalg.norm(vector_hombro)
    norm_muneca = np.linalg.norm(vector_muneca)
    
    if norm_hombro == 0 or norm_muneca == 0:
        return 0.0
        
    coseno = np.dot(vector_hombro, vector_muneca) / (norm_hombro * norm_muneca)
    coseno = np.clip(coseno, -1.0, 1.0)
    
    return np.degrees(np.arccos(coseno))

def calcular_flexion_muneca(codo, muneca, mano):
    """
    Calcula el ángulo de desviación de la muñeca en grados (desviación respecto a la línea recta del antebrazo).
    codo: [x, y] coordenadas en píxeles.
    muneca: [x, y] coordenadas en píxeles.
    mano: [x, y] coordenadas en píxeles.
    """
    vector_antebrazo = np.array([muneca[0] - codo[0], muneca[1] - codo[1]])
    vector_mano = np.array([mano[0] - muneca[0], mano[1] - muneca[1]])
    
    norm_antebrazo = np.linalg.norm(vector_antebrazo)
    norm_mano = np.linalg.norm(vector_mano)
    
    if norm_antebrazo == 0 or norm_mano == 0:
        return 0.0
        
    coseno = np.dot(vector_antebrazo, vector_mano) / (norm_antebrazo * norm_mano)
    coseno = np.clip(coseno, -1.0, 1.0)
    
    # Ángulo entre vectores (0 grados si están perfectamente alineados en línea recta)
    angulo = np.degrees(np.arccos(coseno))
    return angulo

def obtener_landmarks_analisis(landmarks, lado, ancho, alto):
    """
    Obtiene los puntos de cadera, hombro, oreja, codo, ojo, muñeca y mano según el lado seleccionado.
    lado: 'Izquierdo', 'Derecho' o 'Auto'
    """
    idx_hombro_izq, idx_cadera_izq, idx_oreja_izq, idx_codo_izq, idx_ojo_izq, idx_muneca_izq, idx_dedo_izq, idx_meñique_izq = 11, 23, 7, 13, 2, 15, 19, 17
    idx_hombro_der, idx_cadera_der, idx_oreja_der, idx_codo_der, idx_ojo_der, idx_muneca_der, idx_dedo_der, idx_meñique_der = 12, 24, 8, 14, 5, 16, 20, 18

    if lado == "Auto":
        vis_izq = landmarks[idx_hombro_izq].visibility
        vis_der = landmarks[idx_hombro_der].visibility
        if vis_izq >= vis_der:
            hombro_lm = landmarks[idx_hombro_izq]
            cadera_lm = landmarks[idx_cadera_izq]
            oreja_lm = landmarks[idx_oreja_izq]
            codo_lm = landmarks[idx_codo_izq]
            ojo_lm = landmarks[idx_ojo_izq]
            muneca_lm = landmarks[idx_muneca_izq]
            dedo_lm = landmarks[idx_dedo_izq]
            meñique_lm = landmarks[idx_meñique_izq]
            lado_detectado = "Izquierdo"
        else:
            hombro_lm = landmarks[idx_hombro_der]
            cadera_lm = landmarks[idx_cadera_der]
            oreja_lm = landmarks[idx_oreja_der]
            codo_lm = landmarks[idx_codo_der]
            ojo_lm = landmarks[idx_ojo_der]
            muneca_lm = landmarks[idx_muneca_der]
            dedo_lm = landmarks[idx_dedo_der]
            meñique_lm = landmarks[idx_meñique_der]
            lado_detectado = "Derecho"
    elif lado == "Izquierdo":
        hombro_lm = landmarks[idx_hombro_izq]
        cadera_lm = landmarks[idx_cadera_izq]
        oreja_lm = landmarks[idx_oreja_izq]
        codo_lm = landmarks[idx_codo_izq]
        ojo_lm = landmarks[idx_ojo_izq]
        muneca_lm = landmarks[idx_muneca_izq]
        dedo_lm = landmarks[idx_dedo_izq]
        meñique_lm = landmarks[idx_meñique_izq]
        lado_detectado = "Izquierdo"
    else: # Derecho
        hombro_lm = landmarks[idx_hombro_der]
        cadera_lm = landmarks[idx_cadera_der]
        oreja_lm = landmarks[idx_oreja_der]
        codo_lm = landmarks[idx_codo_der]
        ojo_lm = landmarks[idx_ojo_der]
        muneca_lm = landmarks[idx_muneca_der]
        dedo_lm = landmarks[idx_dedo_der]
        meñique_lm = landmarks[idx_meñique_der]
        lado_detectado = "Derecho"

    p_hombro = [hombro_lm.x * ancho, hombro_lm.y * alto]
    p_cadera = [cadera_lm.x * ancho, cadera_lm.y * alto]
    p_oreja = [oreja_lm.x * ancho, oreja_lm.y * alto]
    p_codo = [codo_lm.x * ancho, codo_lm.y * alto]
    p_ojo = [ojo_lm.x * ancho, ojo_lm.y * alto]
    p_muneca = [muneca_lm.x * ancho, muneca_lm.y * alto]
    p_mano = [
        (dedo_lm.x + meñique_lm.x) / 2.0 * ancho,
        (dedo_lm.y + meñique_lm.y) / 2.0 * alto
    ]
    
    return p_hombro, p_cadera, p_oreja, p_codo, p_ojo, p_muneca, p_mano, lado_detectado

def dibujar_analisis_completo(
    imagen, cadera, hombro, oreja, codo, ojo,
    angulo_tronco, angulo_cabeza, angulo_cuello, angulo_hombro,
    config=None, punto_cuello_manual=None,
    muneca=None, mano=None, angulo_muneca=None
):
    """
    Dibuja las guías de flexión de tronco (en cadera, usando punto manual), ángulo de cabeza (en oreja),
    y flexión del hombro (entre cadera, hombro y codo, solo en video).
    """
    ROSADO = (180, 105, 255)
    default_config = {
        "color_vertical": ROSADO,
        "color_tronco": ROSADO,
        "color_cabeza": ROSADO,
        "color_brazo": ROSADO,
        "color_muneca": ROSADO,
        "color_arco_borde": ROSADO,
        "color_arco": ROSADO,
        "color_puntos": ROSADO,
        "color_texto": (255, 255, 255),
        "grosor_lineas": 4,
        "grosor_tronco": 6,
        "grosor_cabeza": 5,
        "grosor_brazo": 5,
        "grosor_borde_arco": 3,
        "radio_ear": 6,
        "radio_hombro": 22,
        "radio_cadera": 22,
        "radio_codo": 22,
        "radio_oreja": 22,
        "radio_arco": 90,
        "radio_arco_cabeza": 70,
        "radio_arco_hombro": 70,
        "transparencia_arco": 0.35,
        "dibujar_texto": True,
        "es_referencia": False,
        "mostrar_tronco": True,
        "mostrar_cabeza": True,
        "mostrar_brazo": True,
        "mostrar_muneca": True
    }
    
    if config is not None:
        default_config.update(config)
        
    cfg = default_config
    
    # Colores obtenidos de la configuración (paleta elegida por el usuario)
    col_t = cfg.get("color_tronco", ROSADO)
    col_c = cfg.get("color_cabeza", ROSADO)
    col_h = cfg.get("color_brazo", ROSADO)
    col_w = cfg.get("color_muneca", ROSADO)
    
    # Redondear coordenadas a enteros para las funciones de dibujo de OpenCV
    xc, yc = int(round(cadera[0])), int(round(cadera[1]))
    xh, yh = int(round(hombro[0])), int(round(hombro[1]))
    xo, yo = int(round(oreja[0])), int(round(oreja[1]))
    xe, ye = int(round(codo[0])), int(round(codo[1]))
    xojo, yojo = int(round(ojo[0])), int(round(ojo[1]))

    overlay = imagen.copy()

    # --- 1. DIBUJAR TRONCO ---
    # Solo se dibuja si hay punto manual y angulo_tronco no es None, y mostrar_tronco es True
    has_trunk = (punto_cuello_manual is not None and angulo_tronco is not None and cfg.get("mostrar_tronco", True))
    if has_trunk:
        xn, yn = int(round(punto_cuello_manual[0])), int(round(punto_cuello_manual[1]))
        dist_tronco = int(math.hypot(xn - xc, yn - yc))
        longitud_vertical = max(200, int(dist_tronco * 0.8))
        
        # Vertical de la cadera (usa Color Tronco - col_t)
        cv2.line(imagen, (xc, yc), (xc, yc - longitud_vertical), col_t, cfg["grosor_lineas"])
        # Línea del tronco: cadera a punto manual (usa Color Tronco - col_t)
        cv2.line(imagen, (xc, yc), (xn, yn), col_t, cfg["grosor_tronco"])
        
        # Arco del tronco (sombras en overlay) (usa Color Tronco - col_t)
        dx_t = xn - xc
        dy_t = yn - yc
        ang_tronco = math.degrees(math.atan2(dy_t, dx_t))
        inicio_t = -90
        fin_t = ang_tronco
        if fin_t < inicio_t:
            inicio_t, fin_t = fin_t, inicio_t
        cv2.ellipse(overlay, (xc, yc), (cfg["radio_arco"], cfg["radio_arco"]), 0, inicio_t, fin_t, col_t, -1)

    # --- 2. DIBUJAR CABEZA (Línea vertical y línea Oreja-Ojo) ---
    # Se dibuja si angulo_cabeza no es None y mostrar_cabeza es True
    has_head = (angulo_cabeza is not None and cfg.get("mostrar_cabeza", True))
    if has_head:
        dist_cabeza = int(math.hypot(xojo - xo, yojo - yo))
        longitud_vert_cabeza = max(100, int(dist_cabeza * 1.5))

        # Línea vertical de referencia desde la oreja hacia arriba (usa Color Cabeza - col_c)
        cv2.line(imagen, (xo, yo), (xo, yo - longitud_vert_cabeza), col_c, cfg["grosor_lineas"])
        # Línea de la cabeza: Oreja a Ojo (usa Color Cabeza - col_c)
        dx_cab = xojo - xo
        dy_cab = yojo - yo
        factor_prolongacion = 1.6
        x_end_cab = int(xo + dx_cab * factor_prolongacion)
        y_end_cab = int(yo + dy_cab * factor_prolongacion)
        cv2.line(imagen, (xo, yo), (x_end_cab, y_end_cab), col_c, cfg["grosor_cabeza"])

        # Arco de la cabeza (entre la vertical y la línea oreja-ojo en overlay) (usa Color Cabeza - col_c)
        ang_ojo = math.degrees(math.atan2(dy_cab, dx_cab))
        inicio_c = -90
        fin_c = ang_ojo
        if fin_c < inicio_c:
            inicio_c, fin_c = fin_c, inicio_c

        # Evitar arco mayor de 180 (camino más corto)
        diff = fin_c - inicio_c
        if diff > 180:
            inicio_c, fin_c = fin_c, inicio_c + 360
        cv2.ellipse(overlay, (xo, yo), (cfg["radio_arco_cabeza"], cfg["radio_arco_cabeza"]), 0, inicio_c, fin_c, col_c, -1)

    # --- 3. DIBUJAR BRAZO Y ÁNGULO DEL HOMBRO (Solo en video, no en referencia) ---
    es_referencia = cfg.get("es_referencia", False)
    has_arm = (not es_referencia and angulo_hombro is not None and muneca is not None and cfg.get("mostrar_brazo", True))
    if has_arm:
        # Arco del brazo con vértice en el codo (en overlay) (usa Color Brazo - col_h)
        xm, ym = int(round(muneca[0])), int(round(muneca[1]))
        ang_hombro_arc = math.degrees(math.atan2(yh - ye, xh - xe))
        ang_muneca_arc = math.degrees(math.atan2(ym - ye, xm - xe))
        
        inicio_h = ang_hombro_arc
        fin_h = ang_muneca_arc
        if fin_h < inicio_h:
            inicio_h, fin_h = fin_h, inicio_h
            
        diff_h = fin_h - inicio_h
        if diff_h > 180:
            inicio_h, fin_h = fin_h, inicio_h + 360
        cv2.ellipse(overlay, (xe, ye), (cfg["radio_arco_hombro"], cfg["radio_arco_hombro"]), 0, inicio_h, fin_h, col_h, -1)

    # --- 3.1 DIBUJAR MUÑECA Y MANO (Solo en video/imagen principal, no en referencia) ---
    has_wrist = (not es_referencia and angulo_muneca is not None and muneca is not None and mano is not None and cfg.get("mostrar_muneca", True))
    
    # Dibujar líneas de segmentos del brazo
    if has_arm:
        cv2.line(imagen, (xh, yh), (xe, ye), col_h, cfg["grosor_brazo"])
    if has_wrist:
        xm, ym = int(round(muneca[0])), int(round(muneca[1]))
        xma, yma = int(round(mano[0])), int(round(mano[1]))
        cv2.line(imagen, (xm, ym), (xma, yma), col_w, max(2, cfg["grosor_brazo"] - 1))
    if has_arm or has_wrist:
        xm, ym = int(round(muneca[0])), int(round(muneca[1]))
        # Si el brazo está visible, usamos col_h, de lo contrario col_w
        color_antebrazo = col_h if has_arm else col_w
        cv2.line(imagen, (xe, ye), (xm, ym), color_antebrazo, cfg["grosor_brazo"])

    # Mezclar transparencia
    cv2.addWeighted(overlay, cfg["transparencia_arco"], imagen, 1 - cfg["transparencia_arco"], 0, imagen)

    # Bordes de arcos
    if has_head:
        cv2.ellipse(imagen, (xo, yo), (cfg["radio_arco_cabeza"], cfg["radio_arco_cabeza"]), 0, inicio_c, fin_c, col_c, cfg["grosor_borde_arco"])
    if has_trunk:
        cv2.ellipse(imagen, (xc, yc), (cfg["radio_arco"], cfg["radio_arco"]), 0, inicio_t, fin_t, col_t, cfg["grosor_borde_arco"])
    if has_arm:
        cv2.ellipse(imagen, (xe, ye), (cfg["radio_arco_hombro"], cfg["radio_arco_hombro"]), 0, inicio_h, fin_h, col_h, cfg["grosor_borde_arco"])

    # --- 4. DIBUJAR PUNTOS CLAVE ---
    def dibujar_punto_estetico(img, centro, color_punto):
        cv2.circle(img, centro, 6, color_punto, -1, cv2.LINE_AA)
        cv2.circle(img, centro, 8, (255, 255, 255), 1, cv2.LINE_AA)

    def dibujar_circulo_grande(img, centro, color_borde):
        cv2.circle(img, centro, 24, (40, 30, 20), -1, cv2.LINE_AA)
        cv2.circle(img, centro, 26, color_borde, 2, cv2.LINE_AA)

    # Cabeza (oreja, ojo)
    if has_head:
        dibujar_punto_estetico(imagen, (xojo, yojo), col_c)
        dibujar_punto_estetico(imagen, (xo, yo), col_c)

    # Tronco (cadera)
    if has_trunk:
        dibujar_circulo_grande(imagen, (xc, yc), col_t)

    # Punto manual del cuello se muestra si existe y mostrar_tronco es True
    if punto_cuello_manual is not None and cfg.get("mostrar_tronco", True):
        xn, yn = int(round(punto_cuello_manual[0])), int(round(punto_cuello_manual[1]))
        cv2.circle(imagen, (xn, yn), 8, col_t, -1, cv2.LINE_AA)
        cv2.circle(imagen, (xn, yn), 10, (255, 255, 255), 1, cv2.LINE_AA)

    # Brazo (hombro, codo)
    if has_arm:
        dibujar_punto_estetico(imagen, (xh, yh), col_h)
        dibujar_circulo_grande(imagen, (xe, ye), col_h)
    elif has_wrist:
        # Codo como punto estético simple si el brazo está oculto pero muñeca visible
        dibujar_punto_estetico(imagen, (xe, ye), col_h)

    # Muñeca y mano (solo video)
    if has_wrist:
        xm, ym = int(round(muneca[0])), int(round(muneca[1]))
        xma, yma = int(round(mano[0])), int(round(mano[1]))
        dibujar_circulo_grande(imagen, (xm, ym), col_w)
        dibujar_punto_estetico(imagen, (xma, yma), col_w)
    elif has_arm:
        # Muñeca como punto estético simple si brazo está visible pero muñeca oculta
        xm, ym = int(round(muneca[0])), int(round(muneca[1]))
        dibujar_punto_estetico(imagen, (xm, ym), col_h)

    # --- 5. TEXTOS DE ÁNGULOS ---
    if cfg.get("dibujar_texto", False):
        # 1. Texto Tronco (dentro del círculo en la cadera)
        if has_trunk:
            texto_tronco = f"{int(round(angulo_tronco))}"
            (tw_t, th_t), _ = cv2.getTextSize(texto_tronco, cv2.FONT_HERSHEY_SIMPLEX, 0.58, 2)
            cv2.putText(imagen, texto_tronco, (int(xc - tw_t / 2), int(yc + th_t / 2)), cv2.FONT_HERSHEY_SIMPLEX, 0.58, col_t, 2, cv2.LINE_AA)

        # 2. Texto Cabeza (al costado de su arco sombreado)
        if has_head:
            ang_c_bis = (inicio_c + fin_c) / 2
            rad_c_bis = math.radians(ang_c_bis)
            dist_c = cfg["radio_arco_cabeza"] + 25
            pos_c = (int(xo + dist_c * math.cos(rad_c_bis)), int(yo + dist_c * math.sin(rad_c_bis)))
            texto_cabeza = f"{int(round(angulo_cabeza))}"
            (tw_cab, th_cab), _ = cv2.getTextSize(texto_cabeza, cv2.FONT_HERSHEY_SIMPLEX, 0.70, 2)
            org_c = (int(pos_c[0] - tw_cab / 2), int(pos_c[1] + th_cab / 2))
            cv2.putText(imagen, texto_cabeza, (org_c[0] + 1, org_c[1] + 1), cv2.FONT_HERSHEY_SIMPLEX, 0.70, (0, 0, 0), 4, cv2.LINE_AA)
            cv2.putText(imagen, texto_cabeza, org_c, cv2.FONT_HERSHEY_SIMPLEX, 0.70, col_c, 2, cv2.LINE_AA)

        # 3. Texto Brazo (dentro del círculo en el codo, solo video)
        if has_arm:
            texto_hombro = f"{int(round(angulo_hombro))}"
            (tw_h, th_h), _ = cv2.getTextSize(texto_hombro, cv2.FONT_HERSHEY_SIMPLEX, 0.58, 2)
            cv2.putText(imagen, texto_hombro, (int(xe - tw_h / 2), int(ye + th_h / 2)), cv2.FONT_HERSHEY_SIMPLEX, 0.58, col_h, 2, cv2.LINE_AA)

        # 4. Texto Muñeca (dentro del círculo en la muñeca, solo video)
        if has_wrist:
            xm, ym = int(round(muneca[0])), int(round(muneca[1]))
            texto_muneca = f"{int(round(angulo_muneca))}"
            (tw_m, th_m), _ = cv2.getTextSize(texto_muneca, cv2.FONT_HERSHEY_SIMPLEX, 0.58, 2)
            cv2.putText(imagen, texto_muneca, (int(xm - tw_m / 2), int(ym + th_m / 2)), cv2.FONT_HERSHEY_SIMPLEX, 0.58, col_w, 2, cv2.LINE_AA)
