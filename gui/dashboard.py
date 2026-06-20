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
        self.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        # Tarjeta 1: Ángulo del Tronco
        self.card_tronco = ctk.CTkFrame(self, fg_color="#222222", corner_radius=8)
        self.card_tronco.grid(row=0, column=0, padx=8, pady=10, sticky="nsew")
        
        lbl_t1 = ctk.CTkLabel(self.card_tronco, text="ÁNGULO TRONCO", font=ctk.CTkFont(size=10, weight="bold"), text_color="gray")
        lbl_t1.pack(pady=(8, 0))
        self.lbl_val_tronco_act = ctk.CTkLabel(self.card_tronco, text="--°", font=ctk.CTkFont(size=28, weight="bold"), text_color="white")
        self.lbl_val_tronco_act.pack(pady=(2, 2))
        self.lbl_time_tronco = ctk.CTkLabel(self.card_tronco, text="0.0s", font=ctk.CTkFont(size=11), text_color="gray")
        self.lbl_time_tronco.pack(pady=(0, 8))

        # Tarjeta 2: Ángulo de la Cabeza
        self.card_cabeza = ctk.CTkFrame(self, fg_color="#222222", corner_radius=8)
        self.card_cabeza.grid(row=0, column=1, padx=8, pady=10, sticky="nsew")
        
        lbl_t2 = ctk.CTkLabel(self.card_cabeza, text="ÁNGULO CABEZA", font=ctk.CTkFont(size=10, weight="bold"), text_color="gray")
        lbl_t2.pack(pady=(8, 0))
        self.lbl_val_cabeza_act = ctk.CTkLabel(self.card_cabeza, text="--°", font=ctk.CTkFont(size=28, weight="bold"), text_color="white")
        self.lbl_val_cabeza_act.pack(pady=(2, 2))
        self.lbl_time_cabeza = ctk.CTkLabel(self.card_cabeza, text="0.0s", font=ctk.CTkFont(size=11), text_color="gray")
        self.lbl_time_cabeza.pack(pady=(0, 8))

        # Tarjeta 3: Ángulo del Cuello
        self.card_cuello = ctk.CTkFrame(self, fg_color="#222222", corner_radius=8)
        self.card_cuello.grid(row=0, column=2, padx=8, pady=10, sticky="nsew")
        
        lbl_t3 = ctk.CTkLabel(self.card_cuello, text="ÁNGULO CUELLO", font=ctk.CTkFont(size=10, weight="bold"), text_color="gray")
        lbl_t3.pack(pady=(8, 0))
        self.lbl_val_cuello_act = ctk.CTkLabel(self.card_cuello, text="--°", font=ctk.CTkFont(size=28, weight="bold"), text_color="white")
        self.lbl_val_cuello_act.pack(pady=(2, 2))
        self.lbl_time_cuello = ctk.CTkLabel(self.card_cuello, text="0.0s", font=ctk.CTkFont(size=11), text_color="gray")
        self.lbl_time_cuello.pack(pady=(0, 8))

        # Tarjeta 4: Ángulo del Hombro
        self.card_hombro = ctk.CTkFrame(self, fg_color="#222222", corner_radius=8)
        self.card_hombro.grid(row=0, column=3, padx=8, pady=10, sticky="nsew")
        
        lbl_t4 = ctk.CTkLabel(self.card_hombro, text="ÁNGULO HOMBRO", font=ctk.CTkFont(size=10, weight="bold"), text_color="gray")
        lbl_t4.pack(pady=(8, 0))
        self.lbl_val_hombro_act = ctk.CTkLabel(self.card_hombro, text="--°", font=ctk.CTkFont(size=28, weight="bold"), text_color="white")
        self.lbl_val_hombro_act.pack(pady=(2, 2))
        self.lbl_time_hombro = ctk.CTkLabel(self.card_hombro, text="0.0s", font=ctk.CTkFont(size=11), text_color="gray")
        self.lbl_time_hombro.pack(pady=(0, 8))

        # Tarjeta 5: Lado Detectado
        self.card_lado = ctk.CTkFrame(self, fg_color="#222222", corner_radius=8)
        self.card_lado.grid(row=0, column=4, padx=8, pady=10, sticky="nsew")
        
        lbl_t5 = ctk.CTkLabel(self.card_lado, text="LADO LEÍDO", font=ctk.CTkFont(size=10, weight="bold"), text_color="gray")
        lbl_t5.pack(pady=(8, 0))
        self.lbl_val_lado = ctk.CTkLabel(self.card_lado, text="--", font=ctk.CTkFont(size=22, weight="bold"), text_color="white")
        self.lbl_val_lado.pack(pady=(8, 8))

    def reset_valores(self):
        """Limpia las etiquetas del dashboard."""
        self.lbl_val_tronco_act.configure(text="--°", text_color="white")
        self.lbl_time_tronco.configure(text="0.0s")
        self.lbl_val_cabeza_act.configure(text="--°", text_color="white")
        self.lbl_time_cabeza.configure(text="0.0s")
        self.lbl_val_cuello_act.configure(text="--°", text_color="white")
        self.lbl_time_cuello.configure(text="0.0s")
        self.lbl_val_hombro_act.configure(text="--°", text_color="white")
        self.lbl_time_hombro.configure(text="0.0s")
        self.lbl_val_lado.configure(text="--")

    def actualizar_metricas(self, angulo_tronco, angulo_cabeza, angulo_cuello, angulo_hombro, lado, t_tronco, t_cabeza, t_cuello, t_hombro):
        """Actualiza las tarjetas de datos con el ángulo, color y tiempo correspondiente."""
        self.lbl_val_tronco_act.configure(text=f"{int(round(angulo_tronco))}°")
        self.lbl_time_tronco.configure(text=f"{t_tronco:.5f}s")
        
        self.lbl_val_cabeza_act.configure(text=f"{int(round(angulo_cabeza))}°")
        self.lbl_time_cabeza.configure(text=f"{t_cabeza:.5f}s")

        self.lbl_val_cuello_act.configure(text=f"{int(round(angulo_cuello))}°")
        self.lbl_time_cuello.configure(text=f"{t_cuello:.5f}s")
        
        self.lbl_val_hombro_act.configure(text=f"{int(round(angulo_hombro))}°")
        self.lbl_time_hombro.configure(text=f"{t_hombro:.5f}s")
        
        self.lbl_val_lado.configure(text=str(lado))
        
        # Lógica de color según inclinación de la espalda
        if angulo_tronco < 15.0:
            color_tronco = COLOR_PALETTE["Verde Neón"]["hex"]
        elif angulo_tronco < 40.0:
            color_tronco = COLOR_PALETTE["Naranja"]["hex"]
        else:
            color_tronco = COLOR_PALETTE["Rojo Coral"]["hex"]
        self.lbl_val_tronco_act.configure(text_color=color_tronco)

        # Cabeza se mantiene neutral o rosado/blanco (se configura a celeste para diferenciar)
        self.lbl_val_cabeza_act.configure(text_color="white")

        # Lógica de color según inclinación del cuello
        if angulo_cuello < 10.0:
            color_cuello = COLOR_PALETTE["Verde Neón"]["hex"]
        elif angulo_cuello < 20.0:
            color_cuello = COLOR_PALETTE["Naranja"]["hex"]
        else:
            color_cuello = COLOR_PALETTE["Rojo Coral"]["hex"]
        self.lbl_val_cuello_act.configure(text_color=color_cuello)

        # Lógica de color según inclinación del hombro
        if angulo_hombro < 20.0:
            color_hombro = COLOR_PALETTE["Verde Neón"]["hex"]
        elif angulo_hombro < 60.0:
            color_hombro = COLOR_PALETTE["Naranja"]["hex"]
        else:
            color_hombro = COLOR_PALETTE["Rojo Coral"]["hex"]
        self.lbl_val_hombro_act.configure(text_color=color_hombro)
