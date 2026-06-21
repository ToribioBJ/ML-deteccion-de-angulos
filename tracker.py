class PostureTracker:
    """Clase para realizar el seguimiento de las mediciones posturales por frame del video."""
    def __init__(self):
        self.reset()

    def reset(self):
        """Reinicia el historial de frames analizados y el estado de la postura activa."""
        self.frames_data = []
        self.last_angles = None  # Tupla (tronco, cabeza, cuello, hombro, lado_usado)
        self.current_posture_count = 0

    def update_pose(self, frame_idx, angulo_tronco, angulo_cabeza, angulo_cuello, angulo_hombro, lado_usado, fps=30.0):
        """Registra la postura medida en un frame del video y calcula la duración de la postura activa."""
        t_int = int(round(angulo_tronco))
        c_int = int(round(angulo_cabeza))
        cu_int = int(round(angulo_cuello))
        h_int = int(round(angulo_hombro))
        
        current_angles = (t_int, c_int, cu_int, h_int, lado_usado)
        
        if self.last_angles == current_angles:
            self.current_posture_count += 1
        else:
            self.last_angles = current_angles
            self.current_posture_count = 1
            
        posture_duration = self.current_posture_count * (1.0 / fps)

        self.frames_data.append({
            "frame_idx": frame_idx,
            "angulo_tronco": t_int,
            "angulo_cabeza": c_int,
            "angulo_cuello": cu_int,
            "angulo_hombro": h_int,
            "lado_usado": lado_usado,
            "tiempo_postura": posture_duration,
            "frames_acumulados": self.current_posture_count
        })
        return posture_duration

    def update_no_pose(self, frame_idx):
        """Registra un frame del video donde no se detectó postura y reinicia la postura activa."""
        self.last_angles = None
        self.current_posture_count = 0
        
        self.frames_data.append({
            "frame_idx": frame_idx,
            "angulo_tronco": None,
            "angulo_cabeza": None,
            "angulo_cuello": None,
            "angulo_hombro": None,
            "lado_usado": "--",
            "tiempo_postura": 0.0,
            "frames_acumulados": 0
        })
        return 0.0

    def clear_history_after_save(self):
        """Limpia el historial después de haber sido guardado."""
        self.frames_data = []
