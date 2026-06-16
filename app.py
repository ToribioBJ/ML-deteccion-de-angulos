import os
import cv2
import queue
import threading
import time
import math
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image, ImageTk

# Importamos nuestro detector modular
from detector import PoseDetector, calcular_flexion_tronco, obtener_landmarks_tronco, dibujar_angulo_en_cadera

# Configuración estética global
ctk.set_appearance_mode("dark")  # Modo oscuro por defecto
ctk.set_default_color_theme("blue")  # Tema de color azul

# Mapeo de colores amigables (Nombre -> BGR para OpenCV y HEX para CustomTkinter)
COLOR_PALETTE = {
    "Celeste": {"bgr": (255, 191, 0), "hex": "#00bfff"},
    "Verde Neón": {"bgr": (0, 255, 100), "hex": "#00ff64"},
    "Rojo Coral": {"bgr": (80, 80, 255), "hex": "#ff5050"},
    "Naranja": {"bgr": (0, 140, 255), "hex": "#ff8c00"},
    "Amarillo": {"bgr": (0, 230, 255), "hex": "#ffe600"}
}

class VideoProcessorThread(threading.Thread):
    """Hilo secundario para procesar video sin congelar la interfaz."""
    def __init__(self, file_path, detector, config_getter, result_queue):
        super().__init__()
        self.file_path = file_path
        self.detector = detector
        self.config_getter = config_getter
        self.result_queue = result_queue
        
        self.running = True
        self.paused = False
        
        self.cap = cv2.VideoCapture(file_path)
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        if self.fps <= 0 or math.isnan(self.fps):
            self.fps = 30.0
            
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Limitador de FPS
        self.frame_delay = 1.0 / self.fps

    def run(self):
        frame_idx = 0
        while self.running:
            if self.paused:
                time.sleep(0.1)
                continue
                
            start_time = time.time()
            ret, frame = self.cap.read()
            if not ret:
                # Fin del video
                self.result_queue.put(("EOF", None, None, None))
                break
                
            # Clonar el frame original por seguridad
            processed_frame = frame.copy()
            h, w, _ = processed_frame.shape
            
            # Obtener configuración actual de la GUI (de forma segura)
            config = self.config_getter()
            
            # Procesar frame con MediaPipe
            landmarks = self.detector.procesar_frame(frame)
            
            angulo = None
            lado_usado = None
            
            if landmarks:
                # Obtener puntos del tronco
                p_hombro, p_cadera, lado_usado = obtener_landmarks_tronco(
                    landmarks, config["lado"], w, h
                )
                
                # Calcular flexión
                angulo = calcular_flexion_tronco(p_hombro, p_cadera)
                
                # Configuración de dibujo según paleta
                color_gui = COLOR_PALETTE[config["color_name"]]["bgr"]
                dibujo_config = {
                    "color_vertical": (255, 100, 0), # Celeste/azul fijo para la vertical
                    "color_tronco": color_gui,
                    "color_arco": (0, 0, 255), # Rojo transparente para el sector angular
                    "color_puntos": color_gui,
                    "grosor_lineas": config["grosor"],
                    "grosor_tronco": config["grosor"] + 2,
                    "radio_hombro": config["radio_puntos"],
                    "radio_cadera": int(config["radio_puntos"] * 3),
                    "radio_arco": config["radio_arco"]
                }
                
                # Dibujar en el frame
                dibujar_angulo_en_cadera(processed_frame, p_cadera, p_hombro, angulo, dibujo_config)
                
            # Colocar en la cola de resultados
            # Si la cola está llena, removemos el más viejo para no saturar memoria en videos largos
            if self.result_queue.full():
                try:
                    self.result_queue.get_nowait()
                except queue.Empty:
                    pass
                    
            self.result_queue.put(("FRAME", processed_frame, angulo, lado_usado))
            frame_idx += 1
            
            # Calcular tiempo de procesamiento y dormir el resto
            elapsed = time.time() - start_time
            sleep_time = max(0.001, self.frame_delay - elapsed)
            time.sleep(sleep_time)
            
        self.cap.release()

    def stop(self):
        self.running = False


class AngleDetectorApp(ctk.CTk):
    """Aplicación principal de escritorio."""
    def __init__(self):
        super().__init__()

        # Configuración de ventana
        self.title("Sistema de Análisis de Flexión del Tronco")
        self.geometry("1200x750")
        self.minsize(1050, 650)
        
        # Inicializar detector
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
        
        # Estadísticas de sesión
        self.max_angle = 0.0
        self.current_angle = 0.0
        
        # Frame actual en memoria para guardar
        self.current_processed_frame = None

        # Configurar la UI
        self.crear_interfaz()
        
        # Iniciar bucle de lectura de cola para videos
        self.poll_results()

    def crear_interfaz(self):
        # Configuración de Grid Layout principal (1 fila, 2 columnas)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # ---------------------------------------------------------------------
        # COLUMNA IZQUIERDA: SIDEBAR DE CONTROL
        # ---------------------------------------------------------------------
        self.sidebar = ctk.CTkFrame(self, width=320, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.sidebar.grid_rowconfigure(8, weight=1)  # Expandir el final para empujar hacia abajo

        # Título principal
        self.lbl_titulo = ctk.CTkLabel(
            self.sidebar, 
            text="DETECTOR DE ÁNGULOS", 
            font=ctk.CTkFont(family="Helvetica", size=20, weight="bold"),
            text_color="#00bfff"
        )
        self.lbl_titulo.grid(row=0, column=0, padx=20, pady=(25, 5), sticky="w")
        
        self.lbl_subtitulo = ctk.CTkLabel(
            self.sidebar, 
            text="Flexión de Tronco en Posturas", 
            font=ctk.CTkFont(family="Helvetica", size=12, slant="italic"),
            text_color="gray"
        )
        self.lbl_subtitulo.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="w")

        # --- SECCIÓN: CARGA DE ARCHIVO ---
        self.frm_archivo = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.frm_archivo.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        
        self.btn_seleccionar = ctk.CTkButton(
            self.frm_archivo, 
            text="Seleccionar Imagen / Video", 
            command=self.seleccionar_archivo,
            font=ctk.CTkFont(size=13, weight="bold"),
            height=38
        )
        self.btn_seleccionar.pack(fill="x", pady=(0, 5))
        
        self.lbl_archivo = ctk.CTkLabel(
            self.frm_archivo, 
            text="Ningún archivo cargado", 
            wraplength=260,
            text_color="gray",
            font=ctk.CTkFont(size=11)
        )
        self.lbl_archivo.pack(fill="x")

        # Separador visual
        self.separador1 = ctk.CTkFrame(self.sidebar, height=2, fg_color="#333333")
        self.separador1.grid(row=3, column=0, padx=20, pady=15, sticky="ew")

        # --- SECCIÓN: CONFIGURACIÓN DE ANÁLISIS ---
        self.lbl_seccion_conf = ctk.CTkLabel(
            self.sidebar, 
            text="Configuración de Análisis", 
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.lbl_seccion_conf.grid(row=4, column=0, padx=20, pady=(0, 10), sticky="w")

        # Contenedor para la configuración de análisis
        self.frm_analisis = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.frm_analisis.grid(row=5, column=0, padx=20, pady=0, sticky="ew")

        # Lado del cuerpo
        self.lbl_lado = ctk.CTkLabel(self.frm_analisis, text="Lado del cuerpo a medir:")
        self.lbl_lado.pack(anchor="w", padx=5, pady=(0, 2))
        self.opt_lado = ctk.CTkOptionMenu(
            self.frm_analisis, 
            values=["Auto", "Izquierdo", "Derecho"],
            command=self.actualizar_analisis_imagen
        )
        self.opt_lado.pack(fill="x", padx=5, pady=(0, 15))
        self.opt_lado.set("Auto")

        # Confianza del detector
        self.lbl_confianza = ctk.CTkLabel(self.frm_analisis, text="Confianza mínima: 0.50")
        self.lbl_confianza.pack(anchor="w", padx=5, pady=(5, 2))
        self.sld_confianza = ctk.CTkSlider(
            self.frm_analisis, 
            from_=0.1, 
            to=0.9, 
            number_of_steps=16,
            command=self.on_confianza_change
        )
        self.sld_confianza.pack(fill="x", padx=5, pady=(0, 10))
        self.sld_confianza.set(0.5)

        # Separador visual
        self.separador2 = ctk.CTkFrame(self.sidebar, height=2, fg_color="#333333")
        self.separador2.grid(row=6, column=0, padx=20, pady=15, sticky="ew")

        # --- SECCIÓN: ESTILO DE DIBUJO ---
        self.lbl_seccion_estilo = ctk.CTkLabel(
            self.sidebar, 
            text="Estilo de Visualización", 
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.lbl_seccion_estilo.grid(row=7, column=0, padx=20, pady=(0, 10), sticky="w")

        self.frm_estilos = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.frm_estilos.grid(row=8, column=0, padx=20, pady=0, sticky="nsew")

        # Selector de Color
        self.lbl_color = ctk.CTkLabel(self.frm_estilos, text="Color de Guías:")
        self.lbl_color.pack(anchor="w", padx=5, pady=(0, 2))
        self.opt_color = ctk.CTkOptionMenu(
            self.frm_estilos, 
            values=list(COLOR_PALETTE.keys()),
            command=self.actualizar_analisis_imagen
        )
        self.opt_color.pack(fill="x", padx=5, pady=(0, 10))
        self.opt_color.set("Verde Neón")

        # Grosor de línea
        self.lbl_grosor = ctk.CTkLabel(self.frm_estilos, text="Grosor de Línea: 4 px")
        self.lbl_grosor.pack(anchor="w", padx=5, pady=(5, 0))
        self.sld_grosor = ctk.CTkSlider(
            self.frm_estilos, 
            from_=1, 
            to=10, 
            number_of_steps=9,
            command=self.on_grosor_change
        )
        self.sld_grosor.pack(fill="x", padx=5, pady=(0, 10))
        self.sld_grosor.set(4)

        # Radio del arco
        self.lbl_arco = ctk.CTkLabel(self.frm_estilos, text="Radio del Arco: 90 px")
        self.lbl_arco.pack(anchor="w", padx=5, pady=(5, 0))
        self.sld_arco = ctk.CTkSlider(
            self.frm_estilos, 
            from_=40, 
            to=150, 
            number_of_steps=11,
            command=self.on_arco_change
        )
        self.sld_arco.pack(fill="x", padx=5, pady=(0, 15))
        self.sld_arco.set(90)

        # --- SECCIÓN: CONTROLES DE REPRODUCCIÓN (PARA VIDEO) ---
        self.frm_controles_video = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.frm_controles_video.grid(row=9, column=0, padx=20, pady=15, sticky="ew")
        
        self.btn_play = ctk.CTkButton(
            self.frm_controles_video, 
            text="Reproducir", 
            fg_color="#10b981", 
            hover_color="#059669",
            command=self.play_video,
            state="disabled",
            font=ctk.CTkFont(weight="bold")
        )
        self.btn_play.pack(side="left", expand=True, padx=(0, 5), fill="x")
        
        self.btn_pause = ctk.CTkButton(
            self.frm_controles_video, 
            text="Pausar", 
            fg_color="#f59e0b", 
            hover_color="#d97706",
            command=self.pause_video,
            state="disabled",
            font=ctk.CTkFont(weight="bold")
        )
        self.btn_pause.pack(side="left", expand=True, padx=(5, 0), fill="x")

        # Botón guardar captura
        self.btn_guardar = ctk.CTkButton(
            self.sidebar, 
            text="Guardar Captura de Imagen", 
            fg_color="#4b5563",
            hover_color="#374151",
            command=self.guardar_captura,
            state="disabled",
            font=ctk.CTkFont(weight="bold"),
            height=35
        )
        self.btn_guardar.grid(row=10, column=0, padx=20, pady=(0, 20), sticky="ew")

        # ---------------------------------------------------------------------
        # COLUMNA DERECHA: VISUALIZADOR Y MÉTRICAS
        # ---------------------------------------------------------------------
        self.visualizer_container = ctk.CTkFrame(self, fg_color="#101010")
        self.visualizer_container.grid(row=0, column=1, sticky="nsew", padx=15, pady=15)
        self.visualizer_container.grid_rowconfigure(0, weight=1)
        self.visualizer_container.grid_columnconfigure(0, weight=1)

        # Panel de visualización de imagen
        self.lbl_viewer = ctk.CTkLabel(
            self.visualizer_container, 
            text="Carga un archivo para comenzar\n\nSoporta: .jpg, .png, .mp4, .avi, .mov",
            font=ctk.CTkFont(family="Segoe UI", size=16),
            text_color="gray"
        )
        self.lbl_viewer.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)

        # --- PANEL DE ESTADÍSTICAS ---
        self.frm_dashboard = ctk.CTkFrame(self.visualizer_container, fg_color="#181818", height=140)
        self.frm_dashboard.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 20))
        self.frm_dashboard.grid_columnconfigure((0, 1, 2, 3), weight=1)

        # Tarjeta 1: Ángulo Actual
        self.card_actual = ctk.CTkFrame(self.frm_dashboard, fg_color="#222222", corner_radius=8)
        self.card_actual.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        lbl_t1 = ctk.CTkLabel(self.card_actual, text="ÁNGULO ACTUAL", font=ctk.CTkFont(size=10, weight="bold"), text_color="gray")
        lbl_t1.pack(pady=(8, 0))
        self.lbl_val_actual = ctk.CTkLabel(self.card_actual, text="--°", font=ctk.CTkFont(size=28, weight="bold"), text_color="white")
        self.lbl_val_actual.pack(pady=(2, 8))

        # Tarjeta 2: Ángulo Máximo
        self.card_max = ctk.CTkFrame(self.frm_dashboard, fg_color="#222222", corner_radius=8)
        self.card_max.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        
        lbl_t2 = ctk.CTkLabel(self.card_max, text="FLEXIÓN MÁXIMA", font=ctk.CTkFont(size=10, weight="bold"), text_color="gray")
        lbl_t2.pack(pady=(8, 0))
        self.lbl_val_max = ctk.CTkLabel(self.card_max, text="0.0°", font=ctk.CTkFont(size=28, weight="bold"), text_color="#00bfff")
        self.lbl_val_max.pack(pady=(2, 8))

        # Tarjeta 3: Lado Detectado
        self.card_lado = ctk.CTkFrame(self.frm_dashboard, fg_color="#222222", corner_radius=8)
        self.card_lado.grid(row=0, column=2, padx=10, pady=10, sticky="nsew")
        
        lbl_t3 = ctk.CTkLabel(self.card_lado, text="LADO LEÍDO", font=ctk.CTkFont(size=10, weight="bold"), text_color="gray")
        lbl_t3.pack(pady=(8, 0))
        self.lbl_val_lado = ctk.CTkLabel(self.card_lado, text="--", font=ctk.CTkFont(size=22, weight="bold"), text_color="white")
        self.lbl_val_lado.pack(pady=(8, 8))

        # Tarjeta 4: Estado de Postura
        self.card_estado = ctk.CTkFrame(self.frm_dashboard, fg_color="#222222", corner_radius=8)
        self.card_estado.grid(row=0, column=3, padx=10, pady=10, sticky="nsew")
        
        lbl_t4 = ctk.CTkLabel(self.card_estado, text="ESTADO DE POSTURA", font=ctk.CTkFont(size=10, weight="bold"), text_color="gray")
        lbl_t4.pack(pady=(8, 0))
        self.lbl_val_estado = ctk.CTkLabel(self.card_estado, text="Sin datos", font=ctk.CTkFont(size=16, weight="bold"), text_color="gray")
        self.lbl_val_estado.pack(pady=(12, 12))

    # --- MANEJADORES DE EVENTOS DE CONFIGURACIÓN ---
    def on_confianza_change(self, val):
        self.lbl_confianza.configure(text=f"Confianza mínima: {val:.2f}")
        # Re-inicializar detector con nueva confianza
        try:
            self.detector.close()
            self.detector = PoseDetector(confidence_threshold=val)
            self.actualizar_analisis_imagen()
        except Exception as e:
            print(f"Error al cambiar confianza: {e}")

    def on_grosor_change(self, val):
        self.lbl_grosor.configure(text=f"Grosor de Línea: {int(val)} px")
        self.actualizar_analisis_imagen()

    def on_arco_change(self, val):
        self.lbl_arco.configure(text=f"Radio del Arco: {int(val)} px")
        self.actualizar_analisis_imagen()

    # --- MANEJADORES DE ARCHIVOS ---
    def seleccionar_archivo(self):
        # Detener cualquier reproducción previa
        self.stop_video_thread()
        
        file_path = filedialog.askopenfilename(
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
        self.lbl_archivo.configure(text=file_name, text_color="white")
        
        # Determinar tipo de archivo por extensión
        ext = os.path.splitext(file_path)[1].lower()
        if ext in [".jpg", ".jpeg", ".png"]:
            self.file_type = "image"
            self.btn_play.configure(state="disabled")
            self.btn_pause.configure(state="disabled")
            self.btn_guardar.configure(state="normal")
            
            # Resetear estadísticas de sesión para nueva carga
            self.max_angle = 0.0
            self.lbl_val_max.configure(text="0.0°")
            
            self.actualizar_analisis_imagen()
        else:
            self.file_type = "video"
            self.btn_play.configure(state="normal")
            self.btn_pause.configure(state="disabled")
            self.btn_guardar.configure(state="disabled")
            
            # Mostrar primer frame como previsualización
            self.previsualizar_primer_frame()

    def previsualizar_primer_frame(self):
        """Muestra el primer frame del video como vista previa estática."""
        if not self.current_filepath:
            return
            
        cap = cv2.VideoCapture(self.current_filepath)
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            self.current_processed_frame = frame.copy()
            self.mostrar_frame_en_viewer(frame)
            
            # Reset estadísticas de video
            self.max_angle = 0.0
            self.current_angle = 0.0
            self.lbl_val_actual.configure(text="--°", text_color="white")
            self.lbl_val_max.configure(text="0.0°")
            self.lbl_val_lado.configure(text="--")
            self.lbl_val_estado.configure(text="Listo para reproducir", text_color="gray")
        else:
            self.lbl_viewer.configure(text="Error al cargar la previsualización del video.")

    def actualizar_analisis_imagen(self, *args):
        """Procesa y renderiza la imagen estática cargada usando los parámetros configurados."""
        if self.file_type != "image" or not self.current_filepath:
            return
            
        frame = cv2.imread(self.current_filepath)
        if frame is None:
            self.lbl_viewer.configure(text="Error al leer la imagen seleccionada.")
            return
            
        h, w, _ = frame.shape
        config = self.obtener_config_gui()
        
        # Procesar
        landmarks = self.detector.procesar_frame(frame)
        
        if landmarks:
            p_hombro, p_cadera, lado_usado = obtener_landmarks_tronco(landmarks, config["lado"], w, h)
            angulo = calcular_flexion_tronco(p_hombro, p_cadera)
            
            # Dibujar
            color_gui = COLOR_PALETTE[config["color_name"]]["bgr"]
            dibujo_config = {
                "color_vertical": (255, 100, 0), # Celeste/azul fijo
                "color_tronco": color_gui,
                "color_arco": (0, 0, 255),
                "color_puntos": color_gui,
                "grosor_lineas": config["grosor"],
                "grosor_tronco": config["grosor"] + 2,
                "radio_hombro": config["radio_puntos"],
                "radio_cadera": int(config["radio_puntos"] * 3),
                "radio_arco": config["radio_arco"]
            }
            
            dibujar_angulo_en_cadera(frame, p_cadera, p_hombro, angulo, dibujo_config)
            
            # Guardar frame procesado
            self.current_processed_frame = frame
            
            # Actualizar métricas
            self.actualizar_metricas_ui(angulo, lado_usado)
        else:
            self.current_processed_frame = frame
            self.mostrar_frame_en_viewer(frame)
            self.lbl_val_actual.configure(text="--°", text_color="white")
            self.lbl_val_lado.configure(text="--")
            self.lbl_val_estado.configure(text="No se detectó pose", text_color="#ff5050")
            
        self.mostrar_frame_en_viewer(self.current_processed_frame)

    # --- MÉTODOS DE REPRODUCCIÓN DE VIDEO ---
    def play_video(self):
        if self.file_type != "video" or not self.current_filepath:
            return
            
        # Si el hilo ya existe y está pausado, lo reanudamos
        if self.video_thread and self.video_thread.is_alive():
            if self.video_thread.paused:
                self.video_thread.paused = False
                self.btn_play.configure(state="disabled")
                self.btn_pause.configure(state="normal")
                self.btn_guardar.configure(state="disabled")
                self.lbl_val_estado.configure(text="Analizando...", text_color="#00bfff")
            return
            
        # Reiniciar estadísticas para la reproducción
        self.max_angle = 0.0
        self.lbl_val_max.configure(text="0.0°")
        
        # Limpiar cola
        while not self.result_queue.empty():
            try:
                self.result_queue.get_nowait()
            except queue.Empty:
                break
                
        # Crear y arrancar hilo procesador
        self.video_thread = VideoProcessorThread(
            file_path=self.current_filepath,
            detector=self.detector,
            config_getter=self.obtener_config_gui,
            result_queue=self.result_queue
        )
        self.video_thread.start()
        
        self.btn_play.configure(state="disabled")
        self.btn_pause.configure(state="normal")
        self.btn_guardar.configure(state="disabled")

    def pause_video(self):
        if self.video_thread and self.video_thread.is_alive():
            self.video_thread.paused = True
            self.btn_play.configure(state="normal", text="Reanudar")
            self.btn_pause.configure(state="disabled")
            self.btn_guardar.configure(state="normal")
            self.lbl_val_estado.configure(text="Pausado", text_color="gray")

    def stop_video_thread(self):
        """Detiene de forma segura el hilo de reproducción de video."""
        if self.video_thread:
            self.video_thread.stop()
            self.video_thread.join(timeout=1.0)
            self.video_thread = None
        self.btn_play.configure(text="Reproducir", state="disabled")
        self.btn_pause.configure(state="disabled")
        self.btn_guardar.configure(state="disabled")

    def poll_results(self):
        """Monitorea la cola de resultados en el hilo principal para actualizar la GUI."""
        try:
            # Intentar vaciar tantos frames listos como haya (para mantenerse al día)
            while True:
                status, frame, angulo, lado = self.result_queue.get_nowait()
                
                if status == "EOF":
                    # El video terminó
                    self.stop_video_thread()
                    self.lbl_val_estado.configure(text="Análisis finalizado", text_color="#10b981")
                    if self.current_filepath:
                        self.btn_play.configure(state="normal", text="Reproducir de nuevo")
                    break
                    
                if status == "FRAME" and frame is not None:
                    self.current_processed_frame = frame
                    self.mostrar_frame_en_viewer(frame)
                    
                    if angulo is not None:
                        self.actualizar_metricas_ui(angulo, lado)
                    else:
                        self.lbl_val_actual.configure(text="--°", text_color="white")
                        self.lbl_val_lado.configure(text="--")
                        self.lbl_val_estado.configure(text="Sin pose visible", text_color="gray")
                        
        except queue.Empty:
            pass
            
        # Programar la siguiente verificación en 15ms (~60 FPS de sondeo)
        self.after(15, self.poll_results)

    # --- MÉTODOS AUXILIARES ---
    def obtener_config_gui(self):
        """Retorna los parámetros de la interfaz gráfica de forma segura para los hilos."""
        return {
            "lado": self.opt_lado.get(),
            "color_name": self.opt_color.get(),
            "grosor": int(self.sld_grosor.get()),
            "radio_puntos": int(self.sld_grosor.get() * 3),  # Proporcional al grosor
            "radio_arco": int(self.sld_arco.get())
        }

    def actualizar_metricas_ui(self, angulo, lado):
        """Actualiza las tarjetas de datos con el ángulo, umbral de color y estado."""
        self.current_angle = angulo
        if angulo > self.max_angle:
            self.max_angle = angulo
            self.lbl_val_max.configure(text=f"{self.max_angle:.1f}°")
            
        self.lbl_val_actual.configure(text=f"{angulo:.1f}°")
        self.lbl_val_lado.configure(text=str(lado))
        
        # Lógica de color y evaluación según inclinación de la espalda
        # 0 - 15°: Postura Correcta (Verde)
        # 15 - 40°: Flexión Moderada (Naranja)
        # > 40°: Flexión Elevada / Riesgo (Rojo)
        if angulo < 15.0:
            color_alerta = COLOR_PALETTE["Verde Neón"]["hex"]
            estado_texto = "Postura Erguida"
        elif angulo < 40.0:
            color_alerta = COLOR_PALETTE["Naranja"]["hex"]
            estado_texto = "Flexión Moderada"
        else:
            color_alerta = COLOR_PALETTE["Rojo Coral"]["hex"]
            estado_texto = "Flexión Pronunciada"
            
        self.lbl_val_actual.configure(text_color=color_alerta)
        self.lbl_val_estado.configure(text=estado_texto, text_color=color_alerta)

    def mostrar_frame_en_viewer(self, frame):
        """Adapta la imagen OpenCV BGR para mostrarla centrada en el visor de CustomTkinter."""
        if frame is None:
            return
            
        # Convertir BGR a RGB
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb_image)
        
        # Obtener dimensiones del visor
        view_w = self.lbl_viewer.winfo_width()
        view_h = self.lbl_viewer.winfo_height()
        
        # Si el tamaño es 1x1 (antes de renderizar la ventana por primera vez), usar un valor por defecto
        if view_w <= 1 or view_h <= 1:
            view_w = 800
            view_h = 500
            
        # Escalar manteniendo la relación de aspecto
        img_w, img_h = pil_image.size
        aspect_ratio = img_w / img_h
        
        if view_w / view_h > aspect_ratio:
            new_h = view_h - 10
            new_w = int(new_h * aspect_ratio)
        else:
            new_w = view_w - 10
            new_h = int(new_w / aspect_ratio)
            
        # Asegurarse de que las dimensiones sean válidas
        new_w = max(10, new_w)
        new_h = max(10, new_h)
        
        # Redimensionar usando Pillow
        pil_image_resized = pil_image.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        # Convertir a CTkImage
        ctk_img = ctk.CTkImage(
            light_image=pil_image_resized,
            dark_image=pil_image_resized,
            size=(new_w, new_h)
        )
        
        # Actualizar widget
        self.lbl_viewer.configure(image=ctk_img, text="")
        self.lbl_viewer.image = ctk_img  # Mantener referencia

    def guardar_captura(self):
        """Guarda la imagen procesada actual en disco."""
        if self.current_processed_frame is None:
            return
            
        save_path = filedialog.asksaveasfilename(
            title="Guardar Captura",
            defaultextension=".png",
            filetypes=[("Imagen PNG", "*.png"), ("Imagen JPEG", "*.jpg")]
        )
        
        if save_path:
            try:
                cv2.imwrite(save_path, self.current_processed_frame)
                messagebox.showinfo("Éxito", f"Captura guardada correctamente en:\n{save_path}")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo guardar la imagen:\n{e}")

    def on_closing(self):
        """Maneja el cierre seguro de la ventana deteniendo los hilos."""
        self.stop_video_thread()
        try:
            self.detector.close()
        except:
            pass
        self.destroy()


if __name__ == "__main__":
    app = AngleDetectorApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
