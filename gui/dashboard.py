import customtkinter as ctk

# Mapeo de colores amigables (HEX para CustomTkinter)
COLOR_PALETTE = {
    "Celeste": {"hex": "#00bfff"},
    "Verde Neón": {"hex": "#00ff64"},
    "Rojo Coral": {"hex": "#ff5050"},
    "Naranja": {"hex": "#ff8c00"},
    "Amarillo": {"hex": "#ffe600"}
}

class DashboardFrame(ctk.CTkFrame):
    """Componente para mostrar las métricas de análisis en tarjetas independientes."""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="#181818", height=140, **kwargs)
        self.grid_columnconfigure((0, 1, 2, 3, 4, 5, 6), weight=1)

        # Tarjeta 1: Ángulo del Tronco
        self.card_tronco = ctk.CTkFrame(self, fg_color="#222222", corner_radius=8)
        self.card_tronco.grid(row=0, column=0, padx=8, pady=10, sticky="nsew")
        
        lbl_t1 = ctk.CTkLabel(self.card_tronco, text="ÁNGULO TRONCO", font=ctk.CTkFont(size=10, weight="bold"), text_color="gray")
        lbl_t1.pack(pady=(15, 0))
        self.lbl_val_tronco_act = ctk.CTkLabel(self.card_tronco, text="--°", font=ctk.CTkFont(size=28, weight="bold"), text_color="white")
        self.lbl_val_tronco_act.pack(pady=(5, 15))

        # Tarjeta 2: Ángulo de la Cabeza
        self.card_cabeza = ctk.CTkFrame(self, fg_color="#222222", corner_radius=8)
        self.card_cabeza.grid(row=0, column=1, padx=8, pady=10, sticky="nsew")
        
        lbl_t2 = ctk.CTkLabel(self.card_cabeza, text="ÁNGULO CABEZA", font=ctk.CTkFont(size=10, weight="bold"), text_color="gray")
        lbl_t2.pack(pady=(15, 0))
        self.lbl_val_cabeza_act = ctk.CTkLabel(self.card_cabeza, text="--°", font=ctk.CTkFont(size=28, weight="bold"), text_color="white")
        self.lbl_val_cabeza_act.pack(pady=(5, 15))

        # Tarjeta 3: Ángulo del Cuello
        self.card_cuello = ctk.CTkFrame(self, fg_color="#222222", corner_radius=8)
        self.card_cuello.grid(row=0, column=2, padx=8, pady=10, sticky="nsew")
        
        lbl_t3 = ctk.CTkLabel(self.card_cuello, text="ÁNGULO CUELLO", font=ctk.CTkFont(size=10, weight="bold"), text_color="gray")
        lbl_t3.pack(pady=(15, 0))
        self.lbl_val_cuello_act = ctk.CTkLabel(self.card_cuello, text="--°", font=ctk.CTkFont(size=28, weight="bold"), text_color="white")
        self.lbl_val_cuello_act.pack(pady=(5, 15))

        # Tarjeta 4: Ángulo del Brazo
        self.card_hombro = ctk.CTkFrame(self, fg_color="#222222", corner_radius=8)
        self.card_hombro.grid(row=0, column=3, padx=8, pady=10, sticky="nsew")
        
        lbl_t4 = ctk.CTkLabel(self.card_hombro, text="ÁNGULO BRAZO", font=ctk.CTkFont(size=10, weight="bold"), text_color="gray")
        lbl_t4.pack(pady=(15, 0))
        self.lbl_val_hombro_act = ctk.CTkLabel(self.card_hombro, text="--°", font=ctk.CTkFont(size=28, weight="bold"), text_color="white")
        self.lbl_val_hombro_act.pack(pady=(5, 15))

        # Tarjeta 5: Ángulo de la Muñeca (Nueva)
        self.card_muneca = ctk.CTkFrame(self, fg_color="#222222", corner_radius=8)
        self.card_muneca.grid(row=0, column=4, padx=8, pady=10, sticky="nsew")
        
        lbl_t_muneca = ctk.CTkLabel(self.card_muneca, text="ÁNGULO MUÑECA", font=ctk.CTkFont(size=10, weight="bold"), text_color="gray")
        lbl_t_muneca.pack(pady=(15, 0))
        self.lbl_val_muneca_act = ctk.CTkLabel(self.card_muneca, text="--°", font=ctk.CTkFont(size=28, weight="bold"), text_color="white")
        self.lbl_val_muneca_act.pack(pady=(5, 15))

        # Tarjeta 6: Lado Detectado
        self.card_lado = ctk.CTkFrame(self, fg_color="#222222", corner_radius=8)
        self.card_lado.grid(row=0, column=5, padx=8, pady=10, sticky="nsew")
        
        lbl_t5 = ctk.CTkLabel(self.card_lado, text="LADO LEÍDO", font=ctk.CTkFont(size=10, weight="bold"), text_color="gray")
        lbl_t5.pack(pady=(15, 0))
        self.lbl_val_lado = ctk.CTkLabel(self.card_lado, text="--", font=ctk.CTkFont(size=22, weight="bold"), text_color="white")
        self.lbl_val_lado.pack(pady=(11, 15))

        # Tarjeta 7: Tiempo del conjunto / postura actual
        self.card_tiempo = ctk.CTkFrame(self, fg_color="#222222", corner_radius=8)
        self.card_tiempo.grid(row=0, column=6, padx=8, pady=10, sticky="nsew")
        
        lbl_t6 = ctk.CTkLabel(self.card_tiempo, text="TIEMPO POSTURA", font=ctk.CTkFont(size=10, weight="bold"), text_color="gray")
        lbl_t6.pack(pady=(15, 0))
        self.lbl_val_tiempo = ctk.CTkLabel(self.card_tiempo, text="0.00s", font=ctk.CTkFont(size=28, weight="bold"), text_color="white")
        self.lbl_val_tiempo.pack(pady=(5, 15))

    def reset_valores(self, tiempo_actual=0.0):
        """Limpia las etiquetas del dashboard."""
        self.lbl_val_tronco_act.configure(text="--°", text_color="white")
        self.lbl_val_cabeza_act.configure(text="--°", text_color="white")
        self.lbl_val_cuello_act.configure(text="--°", text_color="white")
        self.lbl_val_hombro_act.configure(text="--°", text_color="white")
        self.lbl_val_muneca_act.configure(text="--°", text_color="white")
        self.lbl_val_lado.configure(text="--")
        self.lbl_val_tiempo.configure(text=f"{tiempo_actual:.2f}s")

    def actualizar_metricas(self, angulo_tronco, angulo_cabeza, angulo_cuello, angulo_hombro, lado, tiempo_actual, angulo_muneca=None):
        """Actualiza las tarjetas de datos con el ángulo, color y tiempo correspondiente."""
        if angulo_tronco is not None:
            self.lbl_val_tronco_act.configure(text=f"{int(round(angulo_tronco))}°")
            # Lógica de color según inclinación de la espalda
            if angulo_tronco < 15.0:
                color_tronco = COLOR_PALETTE["Verde Neón"]["hex"]
            elif angulo_tronco < 40.0:
                color_tronco = COLOR_PALETTE["Naranja"]["hex"]
            else:
                color_tronco = COLOR_PALETTE["Rojo Coral"]["hex"]
            self.lbl_val_tronco_act.configure(text_color=color_tronco)
        else:
            self.lbl_val_tronco_act.configure(text="--°", text_color="white")

        if angulo_cabeza is not None:
            self.lbl_val_cabeza_act.configure(text=f"{int(round(angulo_cabeza))}°")
            self.lbl_val_cabeza_act.configure(text_color="white")
        else:
            self.lbl_val_cabeza_act.configure(text="--°", text_color="white")

        if angulo_cuello is not None:
            self.lbl_val_cuello_act.configure(text=f"{int(round(angulo_cuello))}°")
            # Lógica de color según inclinación del cuello
            if angulo_cuello < 10.0:
                color_cuello = COLOR_PALETTE["Verde Neón"]["hex"]
            elif angulo_cuello < 20.0:
                color_cuello = COLOR_PALETTE["Naranja"]["hex"]
            else:
                color_cuello = COLOR_PALETTE["Rojo Coral"]["hex"]
            self.lbl_val_cuello_act.configure(text_color=color_cuello)
        else:
            self.lbl_val_cuello_act.configure(text="--°", text_color="white")

        if angulo_hombro is not None:
            self.lbl_val_hombro_act.configure(text=f"{int(round(angulo_hombro))}°")
            # Lógica de color según inclinación del hombro
            if angulo_hombro < 20.0:
                color_hombro = COLOR_PALETTE["Verde Neón"]["hex"]
            elif angulo_hombro < 60.0:
                color_hombro = COLOR_PALETTE["Naranja"]["hex"]
            else:
                color_hombro = COLOR_PALETTE["Rojo Coral"]["hex"]
            self.lbl_val_hombro_act.configure(text_color=color_hombro)
        else:
            self.lbl_val_hombro_act.configure(text="--°", text_color="white")

        if angulo_muneca is not None:
            self.lbl_val_muneca_act.configure(text=f"{int(round(angulo_muneca))}°")
            # Lógica de color según la desviación de la muñeca (RULA-inspired)
            if angulo_muneca < 15.0:
                color_muneca = COLOR_PALETTE["Verde Neón"]["hex"]
            elif angulo_muneca < 25.0:
                color_muneca = COLOR_PALETTE["Naranja"]["hex"]
            else:
                color_muneca = COLOR_PALETTE["Rojo Coral"]["hex"]
            self.lbl_val_muneca_act.configure(text_color=color_muneca)
        else:
            self.lbl_val_muneca_act.configure(text="--°", text_color="white")

        self.lbl_val_lado.configure(text=str(lado) if lado is not None else "--")
        self.lbl_val_tiempo.configure(text=f"{tiempo_actual:.2f}s" if tiempo_actual is not None else "0.00s")
