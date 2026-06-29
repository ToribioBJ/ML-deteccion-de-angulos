import os
import cv2
import queue
import math
from tkinter import filedialog, messagebox
import customtkinter as ctk

# Importar detector modular
from detector import (
    PoseDetector, 
    calcular_flexion_tronco, 
    calcular_angulo_cabeza,
    calcular_flexion_hombro,
    calcular_flexion_muneca,
    obtener_landmarks_analisis, 
    dibujar_analisis_completo
)

# Importar componentes de lógica de negocio y GUI refactorizados
from video_processor import VideoProcessorThread
from tracker import PostureTracker
from excel_exporter import registrar_posturas_excel
from gui.sidebar import SidebarFrame
from gui.dashboard import DashboardFrame
from gui.visualizer import VisualizerFrame

# Colores de análisis (BGR para OpenCV)
ROSADO = (180, 105, 255)
BLANCO = (255, 255, 255)

# Paleta de colores seleccionables
COLOR_PALETTE = {
    "Rosado": (180, 105, 255),
    "Celeste": (250, 206, 135),
    "Verde Neón": (57, 255, 20),
    "Naranja": (0, 165, 255),
    "Amarillo": (0, 255, 255)
}

# Configuración estética global
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class AngleDetectorApp(ctk.CTk):
    """Aplicación principal de escritorio (Controlador)."""
    def __init__(self):
        super().__init__()

        # Configuración de ventana
        self.title("Sistema de Análisis de Flexión del Tronco")
        self.geometry("1200x750")
        self.minsize(1050, 650)
        
        # Inicializar detector de pose
        try:
            self.detector = PoseDetector(confidence_threshold=0.5)
        except Exception as e:
            messagebox.showerror(
                "Error de Inicialización", 
                f"No se pudo inicializar MediaPipe:\n{e}\n\nAsegúrate de tener conexión a Internet para descargar el modelo la primera vez."
            )
            self.destroy()
            return
            
        # Variables de estado
        self.current_filepath = None
        self.file_type = None  # 'image' o 'video'
        self.video_thread = None
        self.result_queue = queue.Queue(maxsize=15)
        
        self.raw_current_frame = None
        self.current_landmarks = None
        self.current_processed_frame = None
        
        # Variables para imagen de referencia
        self.referencia_filepath = None
        self.referencia_raw_frame = None
        self.referencia_landmarks = None
        self.alfa = None
        self.beta = None

        # Variables de cuello manual y tracking
        self.punto_cuello_manual = None
        self.punto_cuello_manual_ref = None
        self.punto_cuello_manual_es_auto = True
        self.punto_cuello_manual_ref_es_auto = True
        self.tracking_lost = False
        
        # Parámetros de proyección del punto manual del cuello (Base Ortogonal Local u, v)
        self.punto_cuello_u = 0.0
        self.punto_cuello_v = 0.0
        self.punto_cuello_lado_activo = "Derecho"

        # Control de exportación única por video
        self.exported_current_video = False

        # Timeline del video
        self.video_total_frames = 0
        self._seeking = False
        
        # Inicializar trackers de sesión
        self.tracker = PostureTracker()

        # Configurar la UI
        self.crear_interfaz()
        
        # Iniciar bucle de lectura de cola para videos
        self.poll_results()

    def crear_interfaz(self):
        # Configuración de Grid Layout principal (1 fila, 2 columnas)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Panel lateral izquierdo de control
        self.sidebar = SidebarFrame(
            self,
            on_seleccionar=self.seleccionar_archivo,
            on_seleccionar_referencia=self.seleccionar_referencia,
            on_lado_cambiado=self.on_lado_cambiado,
            on_color_cambiado=self.on_color_change,
            on_confianza_cambiada=self.on_confianza_change,
            on_registrar_excel=self.registrar_en_excel,
            on_play=self.play_video,
            on_pause=self.pause_video
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

        # Contenedor de visualización y dashboard (Columna derecha)
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=15, pady=15)
        self.main_container.grid_rowconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)

        # Sub-contenedor para los dos visores (principal y referencia)
        self.vis_container = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.vis_container.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.vis_container.grid_rowconfigure(0, weight=1)
        self.vis_container.grid_columnconfigure((0, 1), weight=1)

        # Timeline / barra de progreso del video
        self.frm_timeline = ctk.CTkFrame(self.main_container, fg_color="transparent", height=30)
        self.frm_timeline.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 0))
        self.frm_timeline.grid_columnconfigure(1, weight=1)

        self.lbl_time = ctk.CTkLabel(self.frm_timeline, text="0:00 / 0:00", font=ctk.CTkFont(size=11))
        self.lbl_time.grid(row=0, column=0, padx=(0, 10))

        self.sld_timeline = ctk.CTkSlider(
            self.frm_timeline,
            from_=0,
            to=100,
            number_of_steps=100,
            command=self._on_timeline_seek
        )
        self.sld_timeline.grid(row=0, column=1, sticky="ew")
        self.sld_timeline.set(0)
        self.sld_timeline.configure(state="disabled")

        # Botones de reproducción en la línea de tiempo (Unicode: ▶ = Play, ⏸ = Pause, ■ = Stop)
        self.btn_timeline_play = ctk.CTkButton(
            self.frm_timeline,
            text="▶",
            width=30,
            height=26,
            command=self._on_timeline_play_click,
            font=ctk.CTkFont(size=14),
            state="disabled"
        )
        self.btn_timeline_play.grid(row=0, column=2, padx=(10, 5))

        self.btn_timeline_stop = ctk.CTkButton(
            self.frm_timeline,
            text="■",
            width=30,
            height=26,
            fg_color="#ef4444",
            hover_color="#dc2626",
            command=self._on_timeline_stop_click,
            font=ctk.CTkFont(size=14),
            state="disabled"
        )
        self.btn_timeline_stop.grid(row=0, column=3, padx=(0, 10))

        # Dashboard inferior
        self.dashboard = DashboardFrame(self.main_container)
        self.dashboard.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 20))

        # Visor de la imagen de referencia (página izquierda)
        self.visualizer_ref = VisualizerFrame(
            self.vis_container,
            dashboard_frame=self.dashboard,
            on_resize_callback=self.actualizar_analisis_imagen_ref
        )
        self.visualizer_ref.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.visualizer_ref.lbl_viewer.configure(
            text="Imagen de Referencia\n\nPresione 'Agregar Imagen de Referencia'\npara calcular alfa (α) y beta (β)",
            text_color="gray"
        )

        # Visor principal (Video/Imagen, página derecha)
        self.visualizer = VisualizerFrame(
            self.vis_container,
            dashboard_frame=self.dashboard,
            on_resize_callback=self.actualizar_analisis_imagen
        )
        self.visualizer.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

        # Enlazar eventos de clic del mouse para selección manual de cuello
        self.visualizer.lbl_viewer.bind("<Button-1>", self.on_visualizer_click)
        self.visualizer_ref.lbl_viewer.bind("<Button-1>", self.on_visualizer_ref_click)

    def calcular_punto_cuello_automatico(self, landmarks, lado, w, h):
        """
        Calcula automáticamente la posición inicial del punto manual del cuello.
        Se define como el punto medio entre:
          1. El cuello estimado (punto medio entre hombro izquierdo y derecho).
          2. El hombro activo (izquierdo o derecho según la configuración del lado).
        """
        if not landmarks or len(landmarks) < 33:
            return None
            
        # Landmarks de hombros (11 = izquierdo, 12 = derecho)
        idx_hombro_izq = 11
        idx_hombro_der = 12
        
        # Coordenadas en píxeles
        p_h_izq = (landmarks[idx_hombro_izq].x * w, landmarks[idx_hombro_izq].y * h)
        p_h_der = (landmarks[idx_hombro_der].x * w, landmarks[idx_hombro_der].y * h)
        
        # Cuello estimado (punto medio de los hombros)
        p_cuello_est = (
            (p_h_izq[0] + p_h_der[0]) / 2.0,
            (p_h_izq[1] + p_h_der[1]) / 2.0
        )
        
        # Determinar hombro activo
        if lado == "Auto":
            vis_izq = landmarks[idx_hombro_izq].visibility
            vis_der = landmarks[idx_hombro_der].visibility
            p_hombro_activo = p_h_izq if vis_izq >= vis_der else p_h_der
        elif lado == "Izquierdo":
            p_hombro_activo = p_h_izq
        else: # Derecho
            p_hombro_activo = p_h_der
            
        # Retornar el punto medio entre el cuello estimado y el hombro activo
        p_manual = (
            (p_cuello_est[0] + p_hombro_activo[0]) / 2.0,
            (p_cuello_est[1] + p_hombro_activo[1]) / 2.0
        )
        return p_manual

    def recalcular_offset_cuello(self):
        """Calcula las coordenadas locales u y v del punto manual con respecto a la línea de los hombros."""
        if not self.current_landmarks or self.punto_cuello_manual is None or self.raw_current_frame is None:
            return
            
        h, w, _ = self.raw_current_frame.shape
        lado_config = self.sidebar.get_lado()
        
        # Landmarks de hombros (11 = izquierdo, 12 = derecho)
        hombro_izq = self.current_landmarks[11]
        hombro_der = self.current_landmarks[12]
        
        x_izq, y_izq = hombro_izq.x * w, hombro_izq.y * h
        x_der, y_der = hombro_der.x * w, hombro_der.y * h
        
        # Centro de los hombros (estimación de cuello)
        xn = (x_izq + x_der) / 2.0
        yn = (y_izq + y_der) / 2.0
            
        if lado_config == "Auto":
            self.punto_cuello_lado_activo = "Izquierdo" if hombro_izq.visibility > hombro_der.visibility else "Derecho"
        else:
            self.punto_cuello_lado_activo = lado_config
            
        xs = x_izq if self.punto_cuello_lado_activo == "Izquierdo" else x_der
        ys = y_izq if self.punto_cuello_lado_activo == "Izquierdo" else y_der
        
        # Vector V de cuello a hombro
        dx = xs - xn
        dy = ys - yn
        
        D = dx*dx + dy*dy
        if D == 0:
            D = 1.0
            
        # Calcular coeficientes u y v resolviendo la base ortogonal local
        px_rel = self.punto_cuello_manual[0] - xn
        py_rel = self.punto_cuello_manual[1] - yn
        
        self.punto_cuello_u = (px_rel * dx + py_rel * dy) / D
        self.punto_cuello_v = (-px_rel * dy + py_rel * dx) / D

    def calcular_punto_cuello_desde_offset(self, landmarks, w, h):
        """Calcula las coordenadas (X, Y) del cuello usando u y v locales y los landmarks actuales."""
        if not landmarks or self.punto_cuello_manual is None or not hasattr(self, 'punto_cuello_u'):
            return self.punto_cuello_manual
            
        hombro_izq = landmarks[11]
        hombro_der = landmarks[12]
        
        x_izq, y_izq = hombro_izq.x * w, hombro_izq.y * h
        x_der, y_der = hombro_der.x * w, hombro_der.y * h
        
        # Centro de hombros
        xn = (x_izq + x_der) / 2.0
        yn = (y_izq + y_der) / 2.0
        
        xs = x_izq if self.punto_cuello_lado_activo == "Izquierdo" else x_der
        ys = y_izq if self.punto_cuello_lado_activo == "Izquierdo" else y_der
        
        # Vector V actual
        dx = xs - xn
        dy = ys - yn
        
        # Reconstruir posición usando base local
        tx = xn + self.punto_cuello_u * dx - self.punto_cuello_v * dy
        ty = yn + self.punto_cuello_u * dy + self.punto_cuello_v * dx
        return (tx, ty)

    # --- MANEJADORES DE EVENTOS DE CONFIGURACIÓN ---
    def on_color_change(self, val):
        self.actualizar_analisis_imagen()
        self.actualizar_analisis_imagen_ref()

    def on_lado_cambiado(self, val):
        # Si el punto manual actual es automático, recalcularlo con el nuevo lado
        if self.punto_cuello_manual_es_auto and self.current_landmarks and self.raw_current_frame is not None:
            h, w, _ = self.raw_current_frame.shape
            self.punto_cuello_manual = self.calcular_punto_cuello_automatico(
                self.current_landmarks, val, w, h
            )
            self.recalcular_offset_cuello()
            
        # Si el punto de referencia manual es automático, recalcularlo con el nuevo lado
        if self.punto_cuello_manual_ref_es_auto and self.referencia_landmarks and self.referencia_raw_frame is not None:
            h, w, _ = self.referencia_raw_frame.shape
            self.punto_cuello_manual_ref = self.calcular_punto_cuello_automatico(
                self.referencia_landmarks, val, w, h
            )
            
        self.actualizar_analisis_imagen()
        self.actualizar_analisis_imagen_ref()

    def on_confianza_change(self, val):
        try:
            self.detector.close()
            self.detector = PoseDetector(confidence_threshold=val)
            
            # Re-detectar pose en el frame actual si está detenido/pausado
            is_playing = self.video_thread and self.video_thread.is_alive() and not self.video_thread.paused
            if self.raw_current_frame is not None and not is_playing:
                self.current_landmarks = self.detector.procesar_frame(self.raw_current_frame)
                # Recalcular el punto si es automático
                if self.punto_cuello_manual_es_auto and self.current_landmarks:
                    h, w, _ = self.raw_current_frame.shape
                    lado_config = self.sidebar.get_lado()
                    self.punto_cuello_manual = self.calcular_punto_cuello_automatico(
                        self.current_landmarks, lado_config, w, h
                    )
                    self.recalcular_offset_cuello()
            self.actualizar_analisis_imagen()

            # Re-detectar pose en la imagen de referencia
            if self.referencia_raw_frame is not None:
                self.referencia_landmarks = self.detector.procesar_frame(self.referencia_raw_frame)
                # Recalcular el punto de referencia si es automático
                if self.punto_cuello_manual_ref_es_auto and self.referencia_landmarks:
                    h, w, _ = self.referencia_raw_frame.shape
                    lado_config = self.sidebar.get_lado()
                    self.punto_cuello_manual_ref = self.calcular_punto_cuello_automatico(
                        self.referencia_landmarks, lado_config, w, h
                    )
                self.actualizar_analisis_imagen_ref()
        except Exception as e:
            print(f"Error al cambiar confianza: {e}")

    # --- MANEJADORES DE IMAGEN DE REFERENCIA ---
    def seleccionar_referencia(self):
        file_path = filedialog.askopenfilename(
            parent=self,
            title="Seleccionar Imagen de Referencia",
            filetypes=[
                ("Imágenes", "*.jpg *.png *.jpeg")
            ]
        )
        if not file_path:
            return
            
        frame = cv2.imread(file_path)
        if frame is not None:
            self.referencia_filepath = file_path
            self.referencia_raw_frame = frame
            self.visualizer_ref.raw_current_frame = frame
            self.punto_cuello_manual_ref = None
            self.punto_cuello_manual_ref_es_auto = True
            
            # Procesar landmarks de pose para la imagen de referencia
            self.referencia_landmarks = self.detector.procesar_frame(frame)
            if self.referencia_landmarks is None:
                messagebox.showwarning(
                    "Sin silueta detectada",
                    "No se detectó ninguna pose o silueta en la imagen de referencia.\n"
                    "Asegúrese de que el cuerpo entero o los puntos clave (cadera, hombro, oreja, ojo) sean visibles.",
                    parent=self
                )
                self.referencia_raw_frame = None
                self.visualizer_ref.raw_current_frame = None
                self.alfa = None
                self.beta = None
                self.visualizer_ref.reset_visor()
                return
            
            # Calcular punto automático inicial para referencia
            h, w, _ = frame.shape
            lado_config = self.sidebar.get_lado()
            self.punto_cuello_manual_ref = self.calcular_punto_cuello_automatico(
                self.referencia_landmarks, lado_config, w, h
            )
                
            self.actualizar_analisis_imagen_ref()
        else:
            messagebox.showerror("Error", "No se pudo leer la imagen de referencia seleccionada.", parent=self)

    def actualizar_analisis_imagen_ref(self, *args):
        if self.referencia_raw_frame is None:
            return
            
        frame_a_dibujar = self.referencia_raw_frame.copy()
        h, w, _ = frame_a_dibujar.shape
        lado_config = self.sidebar.get_lado()
        color_tronco_bgr = COLOR_PALETTE.get(self.sidebar.get_color_tronco_name(), ROSADO)
        color_cabeza_bgr = COLOR_PALETTE.get(self.sidebar.get_color_cabeza_name(), ROSADO)
        color_brazo_bgr = COLOR_PALETTE.get(self.sidebar.get_color_brazo_name(), ROSADO)
        color_muneca_bgr = COLOR_PALETTE.get(self.sidebar.get_color_muneca_name(), ROSADO)
        
        mostrar_tronco = self.sidebar.get_mostrar_tronco()
        mostrar_cabeza = self.sidebar.get_mostrar_cabeza()
        mostrar_brazo = self.sidebar.get_mostrar_brazo()
        mostrar_muneca = self.sidebar.get_mostrar_muneca()
        
        if self.referencia_landmarks:
            p_hombro, p_cadera, p_oreja, p_codo, p_ojo, p_muneca_ref, p_mano_ref, lado_usado = obtener_landmarks_analisis(
                self.referencia_landmarks, lado_config, w, h
            )
            # Calcular ángulos base de referencia
            if self.punto_cuello_manual_ref is not None:
                self.alfa = calcular_flexion_tronco(self.punto_cuello_manual_ref, p_cadera)
            else:
                self.alfa = None
            self.beta = calcular_angulo_cabeza(p_oreja, p_ojo)
            
            # Configuración de dibujo estético para la referencia
            dibujo_config = {
                "color_vertical": color_tronco_bgr,
                "color_tronco": color_tronco_bgr,
                "color_cabeza": color_cabeza_bgr,
                "color_brazo": color_brazo_bgr,
                "color_muneca": color_muneca_bgr,
                "color_texto": BLANCO,
                "grosor_lineas": 3,
                "grosor_tronco": 5,
                "grosor_cabeza": 4,
                "grosor_brazo": 4,
                "grosor_borde_arco": 2,
                "radio_arco": 80,
                "radio_arco_cabeza": 65,
                "radio_arco_hombro": 70,
                "radio_ear": 6,
                "radio_hombro": 22,
                "radio_cadera": 22,
                "radio_codo": 22,
                "transparencia_arco": 0.28,
                "dibujar_texto": True,
                "dibujar_brazo": False,
                "es_referencia": True,
                "mostrar_tronco": mostrar_tronco,
                "mostrar_cabeza": mostrar_cabeza,
                "mostrar_brazo": mostrar_brazo,
                "mostrar_muneca": mostrar_muneca
            }
            
            angulo_cuello_ref = self.beta - self.alfa if self.alfa is not None else None
            
            dibujar_analisis_completo(
                frame_a_dibujar, p_cadera, p_hombro, p_oreja, p_codo, p_ojo,
                self.alfa, self.beta, angulo_cuello_ref, 0.0, config=dibujo_config,
                punto_cuello_manual=self.punto_cuello_manual_ref,
                muneca=p_muneca_ref, mano=p_mano_ref, angulo_muneca=None
            )
            
            # Mostrar la imagen con el overlay especial
            self.visualizer_ref.mostrar_frame(
                frame_a_dibujar, 
                self._get_window_scaling(), 
                is_reference=True, 
                alfa=self.alfa, 
                beta=self.beta
            )
        else:
            self.visualizer_ref.mostrar_frame(frame_a_dibujar, self._get_window_scaling())

    # --- MANEJADORES DE ARCHIVOS ---
    def seleccionar_archivo(self):
        self.stop_video_thread()
        self.tracker.reset()
        self.dashboard.reset_valores()
        self.visualizer.reset_visor()
        self.punto_cuello_manual = None
        self.punto_cuello_manual_es_auto = True
        self.tracking_lost = False
        self.exported_current_video = False
        self.sld_timeline.set(0)
        self.sld_timeline.configure(state="disabled")
        self.lbl_time.configure(text="0:00 / 0:00")
        self.btn_timeline_play.configure(state="disabled", text="▶")
        self.btn_timeline_stop.configure(state="disabled")
        
        file_path = filedialog.askopenfilename(
            parent=self,
            title="Seleccionar Imagen o Video",
            filetypes=[
                ("Archivos multimedia", "*.jpg *.png *.jpeg *.mp4 *.avi *.mov"),
                ("Imágenes", "*.jpg *.png *.jpeg"),
                ("Videos", "*.mp4 *.avi *.mov")
            ]
        )
        if not file_path:
            return
            
        self.current_filepath = file_path
        file_name = os.path.basename(file_path)
        self.sidebar.set_nombre_archivo(file_name, "white")
        
        # Determinar tipo de archivo por extensión
        ext = os.path.splitext(file_path)[1].lower()
        if ext in [".jpg", ".jpeg", ".png"]:
            self.file_type = "image"
            self.sidebar.configurar_estados_archivo("image")
            
            frame = cv2.imread(file_path)
            if frame is not None:
                self.raw_current_frame = frame
                self.visualizer.raw_current_frame = frame
                self.current_landmarks = self.detector.procesar_frame(frame)
                
                # Calcular punto del cuello automático para la imagen y calcular offset
                if self.current_landmarks:
                    h, w, _ = frame.shape
                    lado_config = self.sidebar.get_lado()
                    self.punto_cuello_manual = self.calcular_punto_cuello_automatico(
                        self.current_landmarks, lado_config, w, h
                    )
                    self.recalcular_offset_cuello()
                self.actualizar_analisis_imagen()
            else:
                self.sidebar.set_nombre_archivo("Error al leer la imagen seleccionada.", "red")
        else:
            self.file_type = "video"
            self.sidebar.configurar_estados_archivo("video")
            # Obtener total de frames del video para la timeline
            cap_info = cv2.VideoCapture(file_path)
            self.video_total_frames = int(cap_info.get(cv2.CAP_PROP_FRAME_COUNT))
            video_fps = cap_info.get(cv2.CAP_PROP_FPS)
            if video_fps <= 0 or math.isnan(video_fps):
                video_fps = 30.0
            cap_info.release()
            if self.video_total_frames > 0:
                self.sld_timeline.configure(state="normal", to=self.video_total_frames - 1, number_of_steps=max(1, self.video_total_frames - 1))
                total_secs = self.video_total_frames / video_fps
                t_min = int(total_secs) // 60
                t_sec = int(total_secs) % 60
                self.lbl_time.configure(text=f"0:00 / {t_min}:{t_sec:02d}")
                self.btn_timeline_play.configure(state="normal")
                self.btn_timeline_stop.configure(state="normal")
            self.previsualizar_primer_frame()

    def previsualizar_primer_frame(self):
        if not self.current_filepath:
            return
            
        cap = cv2.VideoCapture(self.current_filepath)
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            self.raw_current_frame = frame
            self.visualizer.raw_current_frame = frame
            self.current_landmarks = self.detector.procesar_frame(frame)
            
            # Calcular punto del cuello automático para el video previsualizado y calcular offset
            if self.current_landmarks:
                h, w, _ = frame.shape
                lado_config = self.sidebar.get_lado()
                self.punto_cuello_manual = self.calcular_punto_cuello_automatico(
                    self.current_landmarks, lado_config, w, h
                )
                self.recalcular_offset_cuello()
            self.actualizar_analisis_imagen()
        else:
            self.sidebar.set_nombre_archivo("Error al cargar la previsualización del video.", "red")

    def actualizar_analisis_imagen(self, *args, frame_idx=None):
        if self.raw_current_frame is None:
            return
            
        frame_a_dibujar = self.raw_current_frame.copy()
        h, w, _ = frame_a_dibujar.shape
        lado_config = self.sidebar.get_lado()
        color_tronco_bgr = COLOR_PALETTE.get(self.sidebar.get_color_tronco_name(), ROSADO)
        color_cabeza_bgr = COLOR_PALETTE.get(self.sidebar.get_color_cabeza_name(), ROSADO)
        color_brazo_bgr = COLOR_PALETTE.get(self.sidebar.get_color_brazo_name(), ROSADO)
        color_muneca_bgr = COLOR_PALETTE.get(self.sidebar.get_color_muneca_name(), ROSADO)
        
        mostrar_tronco = self.sidebar.get_mostrar_tronco()
        mostrar_cabeza = self.sidebar.get_mostrar_cabeza()
        mostrar_brazo = self.sidebar.get_mostrar_brazo()
        mostrar_muneca = self.sidebar.get_mostrar_muneca()
        
        # Calcular tiempo de video/reproducción y FPS
        if self.file_type == "video" and frame_idx is not None and self.video_thread is not None:
            fps = self.video_thread.fps
            t = frame_idx / fps
        else:
            fps = 30.0
            t = 0.0

        if self.current_landmarks and not self.tracking_lost:
            p_hombro, p_cadera, p_oreja, p_codo, p_ojo, p_muneca, p_mano, lado_usado = obtener_landmarks_analisis(self.current_landmarks, lado_config, w, h)
            if self.punto_cuello_manual is not None:
                angulo_tronco = calcular_flexion_tronco(self.punto_cuello_manual, p_cadera)
            else:
                angulo_tronco = None
            angulo_cabeza = calcular_angulo_cabeza(p_oreja, p_ojo)
            angulo_cuello = angulo_cabeza - angulo_tronco if angulo_tronco is not None else None
            angulo_hombro = calcular_flexion_hombro(p_hombro, p_codo, p_muneca)
            angulo_muneca = calcular_flexion_muneca(p_codo, p_muneca, p_mano)
            
            # Lógica de segmentos de postura
            if self.file_type == "video" and frame_idx is not None:
                tiempo_postura = self.tracker.update_pose(
                    frame_idx, angulo_tronco, angulo_cabeza, angulo_cuello, angulo_hombro, lado_usado, fps, angulo_muneca=angulo_muneca,
                    p_cadera=p_cadera, p_hombro=p_hombro, p_oreja=p_oreja, p_codo=p_codo, p_ojo=p_ojo, p_muneca=p_muneca, p_mano=p_mano,
                    p_cuello_manual=self.punto_cuello_manual
                )
            else:
                tiempo_postura = 0.0

            dibujo_config = {
                "color_vertical": color_tronco_bgr,
                "color_tronco": color_tronco_bgr,
                "color_cabeza": color_cabeza_bgr,
                "color_brazo": color_brazo_bgr,
                "color_muneca": color_muneca_bgr,
                "color_texto": BLANCO,
                "grosor_lineas": 3,
                "grosor_tronco": 5,
                "grosor_cabeza": 4,
                "grosor_brazo": 4,
                "grosor_borde_arco": 2,
                "radio_arco": 80,
                "radio_arco_cabeza": 65,
                "radio_arco_hombro": 70,
                "radio_ear": 6,
                "radio_hombro": 22,
                "radio_cadera": 22,
                "radio_codo": 22,
                "transparencia_arco": 0.28,
                "dibujar_texto": True,
                "es_referencia": False,
                "mostrar_tronco": mostrar_tronco,
                "mostrar_cabeza": mostrar_cabeza,
                "mostrar_brazo": mostrar_brazo,
                "mostrar_muneca": mostrar_muneca
            }
            
            dibujar_analisis_completo(
                frame_a_dibujar, p_cadera, p_hombro, p_oreja, p_codo, p_ojo,
                angulo_tronco, angulo_cabeza, angulo_cuello, angulo_hombro, config=dibujo_config,
                punto_cuello_manual=self.punto_cuello_manual,
                muneca=p_muneca, mano=p_mano, angulo_muneca=angulo_muneca
            )
            self.current_processed_frame = frame_a_dibujar
            
            # Actualizar dashboard
            self.dashboard.actualizar_metricas(
                angulo_tronco=angulo_tronco, 
                angulo_cabeza=angulo_cabeza,
                angulo_cuello=angulo_cuello, 
                angulo_hombro=angulo_hombro, 
                lado=lado_usado, 
                tiempo_actual=tiempo_postura,
                angulo_muneca=angulo_muneca
            )
        else:
            if self.tracking_lost:
                # Dibujar advertencia en rojo en la pantalla
                cv2.putText(
                    frame_a_dibujar, 
                    "ERROR: SEGUIMIENTO DEL CUELLO PERDIDO", 
                    (30, 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 
                    0.8, 
                    (0, 0, 255), 
                    2, 
                    cv2.LINE_AA
                )
            self.current_processed_frame = frame_a_dibujar
            
            # Lógica de segmentos para frame sin pose o seguimiento perdido
            if self.file_type == "video" and frame_idx is not None:
                tiempo_postura = self.tracker.update_no_pose(frame_idx)
            else:
                tiempo_postura = 0.0
                
            self.dashboard.reset_valores(tiempo_actual=tiempo_postura)
            
        # Pasar el frame procesado al visualizador
        self.visualizer.mostrar_frame(self.current_processed_frame, self._get_window_scaling())

    # --- MÉTODOS DE REPRODUCCIÓN DE VIDEO ---
    def play_video(self):
        if self.file_type != "video" or not self.current_filepath:
            return
            
        # Si está pausado, reanudamos
        if self.video_thread and self.video_thread.is_alive():
            if self.video_thread.paused:
                self.video_thread.paused = False
                self.sidebar.configurar_estados_reproduccion(is_playing=True)
                self.btn_timeline_play.configure(text="⏸")
            return
 
        # Validar selección de la base del cuello
        if self.punto_cuello_manual is None:
            messagebox.showwarning(
                "Selección Requerida", 
                "Por favor, seleccione el punto de la base del cuello en el visor haciendo clic con el mouse antes de iniciar el análisis del video.", 
                parent=self
            )
            return
            
        # Limpiar cola de resultados
        while not self.result_queue.empty():
            try:
                self.result_queue.get_nowait()
            except queue.Empty:
                break
                
        # Obtener el frame de inicio del slider
        start_frame = int(round(self.sld_timeline.get()))
        
        # Iniciar hilo secundario con el offset de cuello manual precalculado (u, v) y frame de inicio
        self.video_thread = VideoProcessorThread(
            file_path=self.current_filepath,
            detector=self.detector,
            result_queue=self.result_queue,
            punto_cuello_manual=self.punto_cuello_manual,
            u=self.punto_cuello_u,
            v=self.punto_cuello_v,
            lado_activo=self.punto_cuello_lado_activo,
            start_frame=start_frame
        )
        self.video_thread.start()
        self.sidebar.configurar_estados_reproduccion(is_playing=True)
        self.btn_timeline_play.configure(text="⏸")

    def pause_video(self):
        if self.video_thread and self.video_thread.is_alive():
            self.video_thread.paused = True
            self.sidebar.configurar_estados_reproduccion(is_playing=False)
            self.btn_timeline_play.configure(text="▶")
 
    def stop_video_thread(self):
        if self.video_thread:
            self.video_thread.stop()
            self.video_thread.join(timeout=1.0)
            self.video_thread = None
        # Limpiar cola de resultados para evitar procesamiento de frames residuales
        while not self.result_queue.empty():
            try:
                self.result_queue.get_nowait()
            except queue.Empty:
                break
        self.sidebar.configurar_estados_archivo(self.file_type)
        self.btn_timeline_play.configure(text="▶")

    def poll_results(self):
        try:
            while True:
                item = self.result_queue.get_nowait()
                status = item[0]
                
                if status == "EOF":
                    self.stop_video_thread()
                    self.sidebar.configurar_estados_detenido()
                    self.btn_timeline_play.configure(text="▶")
                    break
                    
                if status == "FRAME":
                    _, frame, landmarks, frame_idx, tracked_neck = item
                    if frame is not None:
                        self.raw_current_frame = frame
                        self.visualizer.raw_current_frame = frame
                        self.current_landmarks = landmarks
                        self.punto_cuello_manual = tracked_neck
                        if tracked_neck is None:
                            self.tracking_lost = True
                        self.actualizar_analisis_imagen(frame_idx=frame_idx)
                        
                        # Actualizar timeline del video
                        if self.video_thread and self.video_total_frames > 0:
                            self._seeking = True
                            self.sld_timeline.set(frame_idx)
                            self._seeking = False
                            fps = self.video_thread.fps
                            cur_secs = frame_idx / fps
                            tot_secs = self.video_total_frames / fps
                            c_min, c_sec = int(cur_secs) // 60, int(cur_secs) % 60
                            t_min, t_sec = int(tot_secs) // 60, int(tot_secs) % 60
                            self.lbl_time.configure(text=f"{c_min}:{c_sec:02d} / {t_min}:{t_sec:02d}")
                        
        except queue.Empty:
            pass
            
        self.after(15, self.poll_results)

    # --- MÉTODOS AUXILIARES ---

    def registrar_en_excel(self):
        nombre = self.sidebar.get_nombre()
        if not nombre:
            messagebox.showwarning("Campo Vacío", "Por favor, ingrese el nombre de la persona para realizar el registro.", parent=self)
            return

        if self.raw_current_frame is None:
            messagebox.showwarning("Sin Archivo", "No hay ningún archivo cargado para registrar.", parent=self)
            return

        # Validar que se haya cargado una imagen de referencia antes de exportar
        if self.alfa is None or self.beta is None:
            messagebox.showwarning("Imagen de Referencia Requerida", "Por favor, agregue una imagen de referencia con postura detectada antes de registrar los datos en Excel.", parent=self)
            return

        es_video = (self.file_type == "video")

        # Validar que tengamos el punto del cuello manual para la imagen principal si no es video
        if not es_video and self.punto_cuello_manual is None:
            messagebox.showwarning("Selección de Cuello Requerida", "Por favor, seleccione el punto de la base del cuello en la imagen principal haciendo clic con el mouse antes de registrar en Excel.", parent=self)
            return

        # Verificar exportación única por video/archivo
        if self.exported_current_video:
            messagebox.showwarning("Ya Exportado", "Los datos de este archivo ya fueron exportados.\nCargue un nuevo archivo o video para volver a exportar.", parent=self)
            return
        
        # Para videos, verificar que tengamos frames procesados para guardar
        if es_video and not self.tracker.frames_data:
            messagebox.showwarning("Sin Datos de Video", "No hay datos de video acumulados. Inicie la reproducción del video para analizar y medir los ángulos antes de registrar.", parent=self)
            return

        archivo_origen = os.path.basename(self.current_filepath) if self.current_filepath else "Previsualización / Imagen"
        excel_path = "registro_posturas.xlsx"

        # Construir la lista de datos a registrar
        if es_video:
            frames_data = self.tracker.frames_data
        else:
            if self.current_landmarks is None:
                messagebox.showwarning("Sin Detección", "No hay datos de pose detectados para registrar. Asegúrese de que una persona sea visible en la imagen.", parent=self)
                return
            h, w, _ = self.raw_current_frame.shape
            lado_config = self.sidebar.get_lado()
            p_hombro, p_cadera, p_oreja, p_codo, p_ojo, p_muneca, p_mano, lado_usado = obtener_landmarks_analisis(self.current_landmarks, lado_config, w, h)
            if self.punto_cuello_manual is not None:
                angulo_tronco = calcular_flexion_tronco(self.punto_cuello_manual, p_cadera)
            else:
                angulo_tronco = None
            angulo_cabeza = calcular_angulo_cabeza(p_oreja, p_ojo)
            angulo_cuello = angulo_cabeza - angulo_tronco if angulo_tronco is not None else None
            angulo_hombro = calcular_flexion_hombro(p_hombro, p_codo, p_muneca)
            angulo_muneca = calcular_flexion_muneca(p_codo, p_muneca, p_mano)
            
            def round_coords(p):
                if p is None:
                    return "--", "--"
                return int(round(p[0])), int(round(p[1]))

            cx, cy = round_coords(p_cadera)
            hx, hy = round_coords(p_hombro)
            ox, oy = round_coords(p_oreja)
            cox, coy = round_coords(p_codo)
            ojx, ojy = round_coords(p_ojo)
            mx, my = round_coords(p_muneca)
            manx, many = round_coords(p_mano)
            cux, cuy = round_coords(self.punto_cuello_manual)

            frames_data = [{
                "angulo_tronco": int(round(angulo_tronco)) if angulo_tronco is not None else "--",
                "angulo_cabeza": int(round(angulo_cabeza)) if angulo_cabeza is not None else "--",
                "angulo_cuello": int(round(angulo_cuello)) if angulo_cuello is not None else "--",
                "angulo_hombro": int(round(angulo_hombro)) if angulo_hombro is not None else "--",
                "angulo_muneca": int(round(angulo_muneca)) if angulo_muneca is not None else "--",
                "lado_usado": lado_usado,
                "tiempo_postura": 0.0,
                "frames_acumulados": 1,
                # Coordinates
                "cadera_x": cx, "cadera_y": cy,
                "hombro_x": hx, "hombro_y": hy,
                "oreja_x": ox, "oreja_y": oy,
                "codo_x": cox, "codo_y": coy,
                "ojo_x": ojx, "ojo_y": ojy,
                "muneca_x": mx, "muneca_y": my,
                "mano_x": manx, "mano_y": many,
                "cuello_manual_x": cux, "cuello_manual_y": cuy
            }]

        try:
            num_regs = registrar_posturas_excel(
                excel_path=excel_path,
                nombre=nombre,
                archivo_origen=archivo_origen,
                frames_data=frames_data,
                alfa=self.alfa,
                beta=self.beta
            )
            
            # Limpiar historial tras guardar con éxito
            if es_video:
                self.tracker.clear_history_after_save()
                mensaje_exito = f"Se registraron exitosamente {num_regs} frames de postura del paciente '{nombre}' en:\n{os.path.abspath(excel_path)}"
            else:
                mensaje_exito = f"Datos del paciente '{nombre}' registrados correctamente en:\n{os.path.abspath(excel_path)}"

            self.sidebar.clear_nombre()
            self.exported_current_video = True
            messagebox.showinfo("Éxito", mensaje_exito, parent=self)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo escribir en el archivo de Excel:\n{e}\n\nAsegúrese de que el archivo no esté abierto en otra aplicación.", parent=self)

    def on_visualizer_click(self, event):
        # Permitir clic solo si hay un archivo cargado y el video no se está reproduciendo activamente
        is_playing = self.video_thread and self.video_thread.is_alive() and not self.video_thread.paused
        if self.raw_current_frame is None or is_playing:
            return
            
        coords = self.visualizer.get_click_coords(event)
        if coords:
            self.punto_cuello_manual = coords
            self.punto_cuello_manual_es_auto = False
            self.tracking_lost = False
            
            # Recalcular el offset basado en este nuevo clic
            self.recalcular_offset_cuello()
            
            # Sincronizar el nuevo punto con el hilo si el video está pausado
            if self.video_thread:
                self.video_thread.set_offset(
                    self.punto_cuello_u,
                    self.punto_cuello_v,
                    self.punto_cuello_lado_activo,
                    coords
                )
                
            # Re-procesar para dibujar inmediatamente el punto en el visor
            self.actualizar_analisis_imagen()

    def on_visualizer_ref_click(self, event):
        if self.referencia_raw_frame is None:
            return
            
        coords = self.visualizer_ref.get_click_coords(event)
        if coords:
            self.punto_cuello_manual_ref = coords
            self.punto_cuello_manual_ref_es_auto = False
            self.actualizar_analisis_imagen_ref()

    def _on_timeline_play_click(self):
        if self.file_type != "video" or not self.current_filepath:
            return
        is_playing = self.video_thread and self.video_thread.is_alive() and not self.video_thread.paused
        if is_playing:
            self.pause_video()
            self.btn_timeline_play.configure(text="▶")
        else:
            self.play_video()
            self.btn_timeline_play.configure(text="⏸")

    def _on_timeline_stop_click(self):
        if self.file_type != "video":
            return
        self.stop_video_thread()
        self.tracker.reset()
        self.dashboard.reset_valores()
        self.sld_timeline.set(0)
        self.btn_timeline_play.configure(text="▶")
        self.previsualizar_primer_frame()

    def _on_timeline_seek(self, value):
        """Maneja el arrastre del slider de timeline para buscar un frame específico."""
        if self._seeking:
            return  # Ignore programmatic updates
        
        is_playing = self.video_thread and self.video_thread.is_alive() and not self.video_thread.paused
        if is_playing:
            return  # No permitir seek durante reproducción activa

        if self.file_type != "video" or not self.current_filepath:
            return

        target_frame = int(round(value))
        cap = cv2.VideoCapture(self.current_filepath)
        cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        ret, frame = cap.read()
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0 or math.isnan(fps):
            fps = 30.0
        cap.release()

        if ret:
            self.raw_current_frame = frame
            self.visualizer.raw_current_frame = frame
            self.current_landmarks = self.detector.procesar_frame(frame)
            
            # Recalcular el punto del cuello en el frame buscado si es automático
            if self.punto_cuello_manual_es_auto and self.current_landmarks:
                h, w, _ = frame.shape
                lado_config = self.sidebar.get_lado()
                self.punto_cuello_manual = self.calcular_punto_cuello_automatico(
                    self.current_landmarks, lado_config, w, h
                )
                self.recalcular_offset_cuello()
            elif self.current_landmarks:
                # Si es manual, aplicar el offset sobre el cuerpo en este nuevo frame para que se mueva en el visor
                h, w, _ = frame.shape
                self.punto_cuello_manual = self.calcular_punto_cuello_desde_offset(self.current_landmarks, w, h)
                
            self.actualizar_analisis_imagen()

            # Actualizar etiqueta de tiempo
            cur_secs = target_frame / fps
            tot_secs = self.video_total_frames / fps
            c_min, c_sec = int(cur_secs) // 60, int(cur_secs) % 60
            t_min, t_sec = int(tot_secs) // 60, int(tot_secs) % 60
            self.lbl_time.configure(text=f"{c_min}:{c_sec:02d} / {t_min}:{t_sec:02d}")

    def on_closing(self):
        self.stop_video_thread()
        self.visualizer.cancel_pending_resizes()
        if hasattr(self, 'visualizer_ref'):
            self.visualizer_ref.cancel_pending_resizes()
        try:
            self.detector.close()
        except:
            pass
        self.destroy()

if __name__ == "__main__":
    app = AngleDetectorApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
