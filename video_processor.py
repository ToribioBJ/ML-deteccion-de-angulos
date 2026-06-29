import cv2
import queue
import threading
import time
import math

class VideoProcessorThread(threading.Thread):
    """Hilo secundario para procesar video sin congelar la interfaz."""
    def __init__(self, file_path, detector, result_queue, punto_cuello_manual=None, 
                 u=0.0, v=0.0, lado_activo="Derecho", start_frame=0):
        super().__init__()
        self.file_path = file_path
        self.detector = detector
        self.result_queue = result_queue
        self.punto_cuello_manual = punto_cuello_manual
        
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

        # Parámetros de proyección local (Base Ortogonal)
        self.u = u
        self.v = v
        self.lado_activo = lado_activo
        self.start_frame = start_frame
        self.tracking_lost = False

    def set_offset(self, u, v, lado_activo, punto_cuello_manual):
        """Permite actualizar la relación del offset si se cambia el punto en pausa."""
        self.u = u
        self.v = v
        self.lado_activo = lado_activo
        self.punto_cuello_manual = punto_cuello_manual

    def run(self):
        if self.start_frame > 0:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.start_frame)
            frame_idx = self.start_frame
        else:
            frame_idx = 0
            
        while self.running:
            if self.paused:
                time.sleep(0.1)
                continue
                
            start_time = time.time()
            ret, frame = self.cap.read()
            if not ret:
                # Fin del video
                self.result_queue.put(("EOF", None, None, None, None))
                break
                
            # Procesar frame con MediaPipe primero
            landmarks = self.detector.procesar_frame(frame)

            # Seguimiento relativo a la silueta (MediaPipe Pose - Base Ortogonal)
            if landmarks is not None and self.punto_cuello_manual is not None:
                hombro_izq = landmarks[11]
                hombro_der = landmarks[12]
                
                x_izq, y_izq = hombro_izq.x * self.width, hombro_izq.y * self.height
                x_der, y_der = hombro_der.x * self.width, hombro_der.y * self.height
                
                # Centro del cuello estimado
                xn = (x_izq + x_der) / 2.0
                yn = (y_izq + y_der) / 2.0

                # Hombro activo
                xs = x_izq if self.lado_activo == "Izquierdo" else x_der
                ys = y_izq if self.lado_activo == "Izquierdo" else y_der
                
                # Vector V de cuello a hombro
                dx = xs - xn
                dy = ys - yn
                
                # Reconstruir la posición del punto manual usando la base local
                tx = xn + self.u * dx - self.v * dy
                ty = yn + self.u * dy + self.v * dx
                
                self.punto_cuello_manual = (tx, ty)
                self.tracking_lost = False
            elif self.punto_cuello_manual is None:
                self.tracking_lost = True
            
            # Colocar en la cola de resultados
            if self.result_queue.full():
                try:
                    self.result_queue.get_nowait()
                except queue.Empty:
                    pass
                    
            self.result_queue.put(("FRAME", frame, landmarks, frame_idx, self.punto_cuello_manual))
            frame_idx += 1
            
            # Calcular tiempo de procesamiento y dormir el resto
            elapsed = time.time() - start_time
            sleep_time = max(0.001, self.frame_delay - elapsed)
            time.sleep(sleep_time)
            
        self.cap.release()

    def stop(self):
        self.running = False
