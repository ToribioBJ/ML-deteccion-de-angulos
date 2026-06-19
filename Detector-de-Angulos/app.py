import os
import cv2
import queue
from tkinter import filedialog, messagebox
import customtkinter as ctk

# Importar detector modular
from detector import (
    PoseDetector, 
    calcular_flexion_tronco, 
    calcular_flexion_cuello,
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
MORADO = (128, 0, 128)
AZUL_OSCURO = (139, 0, 0)
BLANCO = (255, 255, 255)
VERDE = (0, 255, 0)

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
            on_lado_cambiado=self.actualizar_analisis_imagen,
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

        # Dashboard inferior
        self.dashboard = DashboardFrame(self.main_container)
        self.dashboard.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 20))

        # Visor de fotogramas (responsivo)
        self.visualizer = VisualizerFrame(
            self.main_container,
            dashboard_frame=self.dashboard,
            on_resize_callback=self.actualizar_analisis_imagen
        )
        self.visualizer.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)

    # --- MANEJADORES DE EVENTOS DE CONFIGURACIÓN ---
    def on_confianza_change(self, val):
        try:
            self.detector.close()
            self.detector = PoseDetector(confidence_threshold=val)
            
            # Re-detectar pose en el frame actual si está detenido/pausado
            is_playing = self.video_thread and self.video_thread.is_alive() and not self.video_thread.paused
            if self.raw_current_frame is not None and not is_playing:
                self.current_landmarks = self.detector.procesar_frame(self.raw_current_frame)
            self.actualizar_analisis_imagen()
        except Exception as e:
            print(f"Error al cambiar confianza: {e}")

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
        
        # Calcular tiempo de video/reproducción
        if self.file_type == "video" and frame_idx is not None and self.video_thread is not None:
            t = frame_idx / self.video_thread.fps
        else:
            t = 0.0

        if self.current_landmarks:
            p_hombro, p_cadera, p_oreja, p_codo, lado_usado = obtener_landmarks_analisis(self.current_landmarks, lado_config, w, h)
            angulo_tronco = calcular_flexion_tronco(p_hombro, p_cadera)
            angulo_cuello = calcular_flexion_cuello(p_cadera, p_hombro, p_oreja)
            angulo_hombro = calcular_flexion_hombro(p_cadera, p_hombro, p_codo)
            
            # Lógica de segmentos de postura
            if self.file_type == "video" and frame_idx is not None:
                self.tracker.update_pose(angulo_tronco, angulo_cuello, angulo_hombro, lado_usado, t)
            else:
                self.tracker.tiempo_tronco = 0.0
                self.tracker.tiempo_cuello = 0.0
                self.tracker.tiempo_hombro = 0.0

            dibujo_config = {
                "color_vertical": MORADO,
                "color_tronco": MORADO,
                "color_cuello": MORADO,
                "color_brazo": MORADO,
                "color_arco": VERDE,
                "color_puntos": AZUL_OSCURO,
                "color_texto": BLANCO,
                "grosor_lineas": 3,
                "grosor_tronco": 5,
                "grosor_cuello": 4,
                "grosor_brazo": 4,
                "grosor_borde_arco": 2,
                "radio_arco": 40,
                "radio_arco_cuello": 30,
                "radio_arco_hombro": 30,
                "radio_ear": 6,
                "radio_hombro": 22,
                "radio_cadera": 22,
                "radio_codo": 22,
                "transparencia_arco": 0.28,
                "dibujar_texto": True
            }
            
            dibujar_analisis_completo(
                frame_a_dibujar, p_cadera, p_hombro, p_oreja, p_codo, 
                angulo_tronco, angulo_cuello, angulo_hombro, config=dibujo_config
            )
            self.current_processed_frame = frame_a_dibujar
            
            # Actualizar dashboard
            self.dashboard.actualizar_metricas(
                angulo_tronco, 
                angulo_cuello, 
                angulo_hombro, 
                lado_usado, 
                self.tracker.tiempo_tronco,
                self.tracker.tiempo_cuello,
                self.tracker.tiempo_hombro
            )
        else:
            self.current_processed_frame = frame_a_dibujar
            self.dashboard.reset_valores()
            
            # Lógica de segmentos para frame sin pose
            if self.file_type == "video" and frame_idx is not None:
                self.tracker.update_no_pose(t)
            
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

        if self.current_landmarks is None or self.raw_current_frame is None:
            messagebox.showwarning("Sin Detección", "No hay datos de pose detectados para registrar. Asegúrese de cargar un archivo con una persona visible.", parent=self)
            return

        es_video = (self.file_type == "video")
        
        # Para videos, verificar que tengamos segmentos procesados para guardar
        todos_segmentos = self.tracker.get_all_segments()
        if es_video and not (todos_segmentos.get("tronco") or todos_segmentos.get("cuello") or todos_segmentos.get("hombro")):
            messagebox.showwarning("Sin Datos de Video", "No hay datos de video acumulados. Inicie la reproducción del video para analizar y medir los ángulos antes de registrar.", parent=self)
            return

        # Calcular los valores de la postura actual en pantalla (para estático)
        h, w, _ = self.raw_current_frame.shape
        lado_config = self.sidebar.get_lado()
        p_hombro, p_cadera, p_oreja, p_codo, lado_usado = obtener_landmarks_analisis(self.current_landmarks, lado_config, w, h)
        angulo_tronco = calcular_flexion_tronco(p_hombro, p_cadera)
        angulo_cuello = calcular_flexion_cuello(p_cadera, p_hombro, p_oreja)
        angulo_hombro = calcular_flexion_hombro(p_cadera, p_hombro, p_codo)

        archivo_origen = os.path.basename(self.current_filepath) if self.current_filepath else "Previsualización / Imagen"
        excel_path = "registro_posturas.xlsx"

        try:
            num_regs = registrar_posturas_excel(
                excel_path=excel_path,
                nombre=nombre,
                archivo_origen=archivo_origen,
                es_video=es_video,
                segmentos=todos_segmentos,
                angulo_tronco=angulo_tronco,
                angulo_cuello=angulo_cuello,
                angulo_hombro=angulo_hombro,
                lado_usado=lado_usado
            )
            
            # Limpiar historial tras guardar con éxito
            if es_video:
                self.tracker.clear_history_after_save()
                mensaje_exito = f"Se registraron exitosamente {num_regs} segmentos de postura del paciente '{nombre}' en:\n{os.path.abspath(excel_path)}"
            else:
                mensaje_exito = f"Datos del paciente '{nombre}' registrados correctamente en:\n{os.path.abspath(excel_path)}"

            self.sidebar.clear_nombre()
            messagebox.showinfo("Éxito", mensaje_exito, parent=self)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo escribir en el archivo de Excel:\n{e}\n\nAsegúrese de que el archivo no esté abierto en otra aplicación.", parent=self)

    def on_closing(self):
        self.stop_video_thread()
        self.visualizer.cancel_pending_resizes()
        try:
            self.detector.close()
        except:
            pass
        self.destroy()

if __name__ == "__main__":
    app = AngleDetectorApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
