class PostureTracker:
    """Clase para realizar el seguimiento del tiempo de permanencia y segmentos de postura."""
    def __init__(self):
        self.reset()

    def reset(self):
        """Reinicia el historial de segmentos y el segmento activo."""
        # Historial de segmentos independientes por cada ángulo
        self.tronco_segments = []
        self.cuello_segments = []
        self.hombro_segments = []
        
        # Segmento activo independiente por cada ángulo
        # Cada segmento tiene la forma: {"valor": int, "t_inicio": float, "t_fin": float}
        self.active_tronco = None
        self.active_cuello = None
        self.active_hombro = None
        
        # Lado activo actual
        self.active_lado = None
        
        # Tiempos de permanencia actuales
        self.tiempo_tronco = 0.0
        self.tiempo_cuello = 0.0
        self.tiempo_hombro = 0.0

    def update_pose(self, angulo_tronco, angulo_cuello, angulo_hombro, lado_usado, t):
        """Actualiza los segmentos activos de cada ángulo de manera independiente con los datos de una pose detectada."""
        angulo_tronco_int = int(round(angulo_tronco))
        angulo_cuello_int = int(round(angulo_cuello))
        angulo_hombro_int = int(round(angulo_hombro))
        
        self.active_lado = lado_usado

        # 1. Actualizar Tronco
        if self.active_tronco is None:
            self.active_tronco = {
                "valor": angulo_tronco_int,
                "t_inicio": t,
                "t_fin": t
            }
            self.tiempo_tronco = 0.0
        else:
            if self.active_tronco["valor"] == angulo_tronco_int:
                self.active_tronco["t_fin"] = t
                self.tiempo_tronco = t - self.active_tronco["t_inicio"]
            else:
                self.active_tronco["duracion"] = self.active_tronco["t_fin"] - self.active_tronco["t_inicio"]
                self.tronco_segments.append(self.active_tronco)
                self.active_tronco = {
                    "valor": angulo_tronco_int,
                    "t_inicio": self.active_tronco["t_fin"],
                    "t_fin": t
                }
                self.tiempo_tronco = t - self.active_tronco["t_inicio"]

        # 2. Actualizar Cuello
        if self.active_cuello is None:
            self.active_cuello = {
                "valor": angulo_cuello_int,
                "t_inicio": t,
                "t_fin": t
            }
            self.tiempo_cuello = 0.0
        else:
            if self.active_cuello["valor"] == angulo_cuello_int:
                self.active_cuello["t_fin"] = t
                self.tiempo_cuello = t - self.active_cuello["t_inicio"]
            else:
                self.active_cuello["duracion"] = self.active_cuello["t_fin"] - self.active_cuello["t_inicio"]
                self.cuello_segments.append(self.active_cuello)
                self.active_cuello = {
                    "valor": angulo_cuello_int,
                    "t_inicio": self.active_cuello["t_fin"],
                    "t_fin": t
                }
                self.tiempo_cuello = t - self.active_cuello["t_inicio"]

        # 3. Actualizar Hombro
        if self.active_hombro is None:
            self.active_hombro = {
                "valor": angulo_hombro_int,
                "t_inicio": t,
                "t_fin": t
            }
            self.tiempo_hombro = 0.0
        else:
            if self.active_hombro["valor"] == angulo_hombro_int:
                self.active_hombro["t_fin"] = t
                self.tiempo_hombro = t - self.active_hombro["t_inicio"]
            else:
                self.active_hombro["duracion"] = self.active_hombro["t_fin"] - self.active_hombro["t_inicio"]
                self.hombro_segments.append(self.active_hombro)
                self.active_hombro = {
                    "valor": angulo_hombro_int,
                    "t_inicio": self.active_hombro["t_fin"],
                    "t_fin": t
                }
                self.tiempo_hombro = t - self.active_hombro["t_inicio"]

    def update_no_pose(self, t):
        """Actualiza los segmentos cuando no se detecta pose."""
        self.active_lado = None
        
        # Tronco
        if self.active_tronco is None:
            self.active_tronco = {
                "valor": None,
                "t_inicio": t,
                "t_fin": t
            }
            self.tiempo_tronco = 0.0
        else:
            if self.active_tronco["valor"] is None:
                self.active_tronco["t_fin"] = t
                self.tiempo_tronco = t - self.active_tronco["t_inicio"]
            else:
                self.active_tronco["duracion"] = self.active_tronco["t_fin"] - self.active_tronco["t_inicio"]
                self.tronco_segments.append(self.active_tronco)
                self.active_tronco = {
                    "valor": None,
                    "t_inicio": self.active_tronco["t_fin"],
                    "t_fin": t
                }
                self.tiempo_tronco = t - self.active_tronco["t_inicio"]

        # Cuello
        if self.active_cuello is None:
            self.active_cuello = {
                "valor": None,
                "t_inicio": t,
                "t_fin": t
            }
            self.tiempo_cuello = 0.0
        else:
            if self.active_cuello["valor"] is None:
                self.active_cuello["t_fin"] = t
                self.tiempo_cuello = t - self.active_cuello["t_inicio"]
            else:
                self.active_cuello["duracion"] = self.active_cuello["t_fin"] - self.active_cuello["t_inicio"]
                self.cuello_segments.append(self.active_cuello)
                self.active_cuello = {
                    "valor": None,
                    "t_inicio": self.active_cuello["t_fin"],
                    "t_fin": t
                }
                self.tiempo_cuello = t - self.active_cuello["t_inicio"]

        # Hombro
        if self.active_hombro is None:
            self.active_hombro = {
                "valor": None,
                "t_inicio": t,
                "t_fin": t
            }
            self.tiempo_hombro = 0.0
        else:
            if self.active_hombro["valor"] is None:
                self.active_hombro["t_fin"] = t
                self.tiempo_hombro = t - self.active_hombro["t_inicio"]
            else:
                self.active_hombro["duracion"] = self.active_hombro["t_fin"] - self.active_hombro["t_inicio"]
                self.hombro_segments.append(self.active_hombro)
                self.active_hombro = {
                    "valor": None,
                    "t_inicio": self.active_hombro["t_fin"],
                    "t_fin": t
                }
                self.tiempo_hombro = t - self.active_hombro["t_inicio"]

    def get_all_segments(self):
        """Retorna todos los segmentos registrados en un diccionario por cada ángulo."""
        tronco_all = list(self.tronco_segments)
        if self.active_tronco is not None:
            seg_activo_copia = dict(self.active_tronco)
            seg_activo_copia["duracion"] = seg_activo_copia["t_fin"] - seg_activo_copia["t_inicio"]
            tronco_all.append(seg_activo_copia)

        cuello_all = list(self.cuello_segments)
        if self.active_cuello is not None:
            seg_activo_copia = dict(self.active_cuello)
            seg_activo_copia["duracion"] = seg_activo_copia["t_fin"] - seg_activo_copia["t_inicio"]
            cuello_all.append(seg_activo_copia)

        hombro_all = list(self.hombro_segments)
        if self.active_hombro is not None:
            seg_activo_copia = dict(self.active_hombro)
            seg_activo_copia["duracion"] = seg_activo_copia["t_fin"] - seg_activo_copia["t_inicio"]
            hombro_all.append(seg_activo_copia)

        return {
            "tronco": tronco_all,
            "cuello": cuello_all,
            "hombro": hombro_all,
            "lado": self.active_lado
        }

    def clear_history_after_save(self):
        """Limpia el historial de segmentos guardados y reinicia el inicio de los segmentos activos al tiempo de guardado."""
        self.tronco_segments = []
        self.cuello_segments = []
        self.hombro_segments = []
        
        if self.active_tronco is not None:
            self.active_tronco["t_inicio"] = self.active_tronco["t_fin"]
        if self.active_cuello is not None:
            self.active_cuello["t_inicio"] = self.active_cuello["t_fin"]
        if self.active_hombro is not None:
            self.active_hombro["t_inicio"] = self.active_hombro["t_fin"]

