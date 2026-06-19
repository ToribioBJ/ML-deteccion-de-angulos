import cv2
import queue
import threading
import time
import math

class VideoProcessorThread(threading.Thread):
    """Hilo secundario para procesar video sin congelar la interfaz."""
    def __init__(self, file_path, detector, result_queue):
        super().__init__()
        self.file_path = file_path
        self.detector = detector
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
                
            # Procesar frame con MediaPipe
            landmarks = self.detector.procesar_frame(frame)
            
            # Colocar en la cola de resultados
            if self.result_queue.full():
                try:
                    self.result_queue.get_nowait()
                except queue.Empty:
                    pass
                    
            self.result_queue.put(("FRAME", frame, landmarks, frame_idx))
            frame_idx += 1
            
            # Calcular tiempo de procesamiento y dormir el resto
            elapsed = time.time() - start_time
            sleep_time = max(0.001, self.frame_delay - elapsed)
            time.sleep(sleep_time)
            
        self.cap.release()

    def stop(self):
        self.running = False
