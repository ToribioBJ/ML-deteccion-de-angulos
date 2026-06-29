class PostureTracker:
    """Clase para realizar el seguimiento de las mediciones posturales por frame del video."""
    def __init__(self):
        self.reset()

    def reset(self):
        """Reinicia el historial de frames analizados y el estado de la postura activa."""
        self.frames_data = []
        self.last_angles = None  # Tupla (tronco, cabeza, cuello, hombro, muñeca, lado_usado)
        self.current_posture_count = 0

    def update_pose(self, frame_idx, angulo_tronco, angulo_cabeza, angulo_cuello, angulo_hombro, lado_usado, fps=30.0, angulo_muneca=None,
                    p_cadera=None, p_hombro=None, p_oreja=None, p_codo=None, p_ojo=None, p_muneca=None, p_mano=None, p_cuello_manual=None):
        """Registra la postura medida en un frame del video y calcula la duración de la postura activa."""
        t_int = int(round(angulo_tronco)) if angulo_tronco is not None else None
        c_int = int(round(angulo_cabeza)) if angulo_cabeza is not None else None
        cu_int = int(round(angulo_cuello)) if angulo_cuello is not None else None
        h_int = int(round(angulo_hombro)) if angulo_hombro is not None else None
        m_int = int(round(angulo_muneca)) if angulo_muneca is not None else None
        
        current_angles = (t_int, c_int, cu_int, h_int, m_int, lado_usado)
        
        if self.last_angles == current_angles:
            self.current_posture_count += 1
        else:
            self.last_angles = current_angles
            self.current_posture_count = 1
            
        posture_duration = self.current_posture_count * (1.0 / fps)

        def round_coords(p):
            if p is None:
                return "--", "--"
            return int(round(p[0])), int(round(p[1]))

        cadera_x, cadera_y = round_coords(p_cadera)
        hombro_x, hombro_y = round_coords(p_hombro)
        oreja_x, oreja_y = round_coords(p_oreja)
        codo_x, codo_y = round_coords(p_codo)
        ojo_x, ojo_y = round_coords(p_ojo)
        muneca_x, muneca_y = round_coords(p_muneca)
        mano_x, mano_y = round_coords(p_mano)
        cuello_manual_x, cuello_manual_y = round_coords(p_cuello_manual)

        self.frames_data.append({
            "frame_idx": frame_idx,
            "angulo_tronco": t_int,
            "angulo_cabeza": c_int,
            "angulo_cuello": cu_int,
            "angulo_hombro": h_int,
            "angulo_muneca": m_int,
            "lado_usado": lado_usado,
            "tiempo_postura": posture_duration,
            "frames_acumulados": self.current_posture_count,
            # Coordenadas
            "cadera_x": cadera_x, "cadera_y": cadera_y,
            "hombro_x": hombro_x, "hombro_y": hombro_y,
            "oreja_x": oreja_x, "oreja_y": oreja_y,
            "codo_x": codo_x, "codo_y": codo_y,
            "ojo_x": ojo_x, "ojo_y": ojo_y,
            "muneca_x": muneca_x, "muneca_y": muneca_y,
            "mano_x": mano_x, "mano_y": mano_y,
            "cuello_manual_x": cuello_manual_x, "cuello_manual_y": cuello_manual_y
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
            "angulo_muneca": None,
            "lado_usado": "--",
            "tiempo_postura": 0.0,
            "frames_acumulados": 0,
            # Coordenadas como vacías
            "cadera_x": "--", "cadera_y": "--",
            "hombro_x": "--", "hombro_y": "--",
            "oreja_x": "--", "oreja_y": "--",
            "codo_x": "--", "codo_y": "--",
            "ojo_x": "--", "ojo_y": "--",
            "muneca_x": "--", "muneca_y": "--",
            "mano_x": "--", "mano_y": "--",
            "cuello_manual_x": "--", "cuello_manual_y": "--"
        })
        return 0.0

    def clear_history_after_save(self):
        """Limpia el historial después de haber sido guardado."""
        self.frames_data = []
