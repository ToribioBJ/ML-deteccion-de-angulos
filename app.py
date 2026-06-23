import os
import cv2
import queue
from tkinter import filedialog, messagebox
import customtkinter as ctk

# Importar detector modular
from detector import (
    PoseDetector, 
    calcular_flexion_tronco, 
    calcular_angulo_cabeza,
    calcular_flexion_hombro,
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
            on_pause=self.pause_video,
            on_guardar=self.guardar_captura
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

        # Dashboard inferior
        self.dashboard = DashboardFrame(self.main_container)
        self.dashboard.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 20))

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

    # --- MANEJADORES DE EVENTOS DE CONFIGURACIÓN ---
    def on_color_change(self, val):
        self.actualizar_analisis_imagen()
        self.actualizar_analisis_imagen_ref()

    def on_lado_cambiado(self, val):
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
            self.actualizar_analisis_imagen()

            # Re-detectar pose en la imagen de referencia
            if self.referencia_raw_frame is not None:
                self.referencia_landmarks = self.detector.procesar_frame(self.referencia_raw_frame)
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
                
            self.actualizar_analisis_imagen_ref()
        else:
            messagebox.showerror("Error", "No se pudo leer la imagen de referencia seleccionada.", parent=self)

    def actualizar_analisis_imagen_ref(self, *args):
        if self.referencia_raw_frame is None:
            return
            
        frame_a_dibujar = self.referencia_raw_frame.copy()
        h, w, _ = frame_a_dibujar.shape
        lado_config = self.sidebar.get_lado()
        color_nombre = self.sidebar.get_color_name()
        color_bgr = COLOR_PALETTE.get(color_nombre, ROSADO)
        
        if self.referencia_landmarks:
            p_hombro, p_cadera, p_oreja, p_codo, p_ojo, lado_usado = obtener_landmarks_analisis(
                self.referencia_landmarks, lado_config, w, h
            )
            # Calcular ángulos base de referencia
            self.alfa = calcular_flexion_tronco(p_hombro, p_cadera)
            self.beta = calcular_angulo_cabeza(p_oreja, p_ojo)
            
            # Configuración de dibujo estético para la referencia
            dibujo_config = {
                "color_vertical": color_bgr,
                "color_tronco": color_bgr,
                "color_cabeza": color_bgr,
                "color_brazo": color_bgr,
                "color_arco_borde": color_bgr,
                "color_arco": color_bgr,
                "color_puntos": color_bgr,
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
                "dibujar_brazo": False
            }
            
            dibujar_analisis_completo(
                frame_a_dibujar, p_cadera, p_hombro, p_oreja, p_codo, p_ojo,
                self.alfa, self.beta, self.beta - self.alfa, 0.0, config=dibujo_config
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
                self.actualizar_analisis_imagen()
            else:
                self.sidebar.set_nombre_archivo("Error al leer la imagen seleccionada.", "red")
        else:
            self.file_type = "video"
            self.sidebar.configurar_estados_archivo("video")
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
            self.actualizar_analisis_imagen()
        else:
            self.sidebar.set_nombre_archivo("Error al cargar la previsualización del video.", "red")

    def actualizar_analisis_imagen(self, *args, frame_idx=None):
        if self.raw_current_frame is None:
            return
            
        frame_a_dibujar = self.raw_current_frame.copy()
        h, w, _ = frame_a_dibujar.shape
        lado_config = self.sidebar.get_lado()
        color_nombre = self.sidebar.get_color_name()
        color_bgr = COLOR_PALETTE.get(color_nombre, ROSADO)
        
        # Calcular tiempo de video/reproducción y FPS
        if self.file_type == "video" and frame_idx is not None and self.video_thread is not None:
            fps = self.video_thread.fps
            t = frame_idx / fps
        else:
            fps = 30.0
            t = 0.0

        if self.current_landmarks:
            p_hombro, p_cadera, p_oreja, p_codo, p_ojo, lado_usado = obtener_landmarks_analisis(self.current_landmarks, lado_config, w, h)
            angulo_tronco = calcular_flexion_tronco(p_hombro, p_cadera)
            angulo_cabeza = calcular_angulo_cabeza(p_oreja, p_ojo)
            angulo_cuello = angulo_cabeza - angulo_tronco
            angulo_hombro = calcular_flexion_hombro(p_cadera, p_hombro, p_codo)
            
            # Lógica de segmentos de postura
            if self.file_type == "video" and frame_idx is not None:
                tiempo_postura = self.tracker.update_pose(frame_idx, angulo_tronco, angulo_cabeza, angulo_cuello, angulo_hombro, lado_usado, fps)
            else:
                tiempo_postura = 0.0

            dibujo_config = {
                "color_vertical": color_bgr,
                "color_tronco": color_bgr,
                "color_cabeza": color_bgr,
                "color_brazo": color_bgr,
                "color_arco_borde": color_bgr,
                "color_arco": color_bgr,
                "color_puntos": color_bgr,
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
                "dibujar_texto": True
            }
            
            dibujar_analisis_completo(
                frame_a_dibujar, p_cadera, p_hombro, p_oreja, p_codo, p_ojo,
                angulo_tronco, angulo_cabeza, angulo_cuello, angulo_hombro, config=dibujo_config
            )
            self.current_processed_frame = frame_a_dibujar
            
            # Actualizar dashboard
            self.dashboard.actualizar_metricas(
                angulo_tronco=angulo_tronco, 
                angulo_cabeza=angulo_cabeza,
                angulo_cuello=angulo_cuello, 
                angulo_hombro=angulo_hombro, 
                lado=lado_usado, 
                tiempo_actual=tiempo_postura
            )
        else:
            self.current_processed_frame = frame_a_dibujar
            
            # Lógica de segmentos para frame sin pose
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
            return
            
        # Limpiar cola de resultados
        while not self.result_queue.empty():
            try:
                self.result_queue.get_nowait()
            except queue.Empty:
                break
                
        # Iniciar hilo secundario
        self.video_thread = VideoProcessorThread(
            file_path=self.current_filepath,
            detector=self.detector,
            result_queue=self.result_queue
        )
        self.video_thread.start()
        self.sidebar.configurar_estados_reproduccion(is_playing=True)

    def pause_video(self):
        if self.video_thread and self.video_thread.is_alive():
            self.video_thread.paused = True
            self.sidebar.configurar_estados_reproduccion(is_playing=False)

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

    def poll_results(self):
        try:
            while True:
                item = self.result_queue.get_nowait()
                status = item[0]
                
                if status == "EOF":
                    self.stop_video_thread()
                    self.sidebar.configurar_estados_detenido()
                    break
                    
                if status == "FRAME":
                    _, frame, landmarks, frame_idx = item
                    if frame is not None:
                        self.raw_current_frame = frame
                        self.visualizer.raw_current_frame = frame
                        self.current_landmarks = landmarks
                        self.actualizar_analisis_imagen(frame_idx=frame_idx)
                        
        except queue.Empty:
            pass
            
        self.after(15, self.poll_results)

    # --- MÉTODOS AUXILIARES ---
    def guardar_captura(self):
        if self.current_processed_frame is None:
            return
            
        save_path = filedialog.asksaveasfilename(
            parent=self,
            title="Guardar Captura",
            defaultextension=".png",
            filetypes=[("Imagen PNG", "*.png"), ("Imagen JPEG", "*.jpg")]
        )
        
        if save_path:
            try:
                cv2.imwrite(save_path, self.current_processed_frame)
                messagebox.showinfo("Éxito", f"Captura guardada correctamente en:\n{save_path}", parent=self)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo guardar la imagen:\n{e}", parent=self)

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
            p_hombro, p_cadera, p_oreja, p_codo, p_ojo, lado_usado = obtener_landmarks_analisis(self.current_landmarks, lado_config, w, h)
            angulo_tronco = calcular_flexion_tronco(p_hombro, p_cadera)
            angulo_cabeza = calcular_angulo_cabeza(p_oreja, p_ojo)
            angulo_cuello = angulo_cabeza - angulo_tronco
            angulo_hombro = calcular_flexion_hombro(p_cadera, p_hombro, p_codo)
            
            frames_data = [{
                "angulo_tronco": int(round(angulo_tronco)),
                "angulo_cabeza": int(round(angulo_cabeza)),
                "angulo_cuello": int(round(angulo_cuello)),
                "angulo_hombro": int(round(angulo_hombro)),
                "lado_usado": lado_usado,
                "tiempo_postura": 0.0,
                "frames_acumulados": 1
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
            messagebox.showinfo("Éxito", mensaje_exito, parent=self)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo escribir en el archivo de Excel:\n{e}\n\nAsegúrese de que el archivo no esté abierto en otra aplicación.", parent=self)

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
