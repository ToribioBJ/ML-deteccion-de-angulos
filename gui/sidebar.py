import customtkinter as ctk

class SidebarFrame(ctk.CTkFrame):
    """Componente lateral izquierdo que agrupa los controles y configuraciones de la aplicación."""
    def __init__(
        self, 
        parent, 
        on_seleccionar, 
        on_lado_cambiado, 
        on_color_cambiado,
        on_confianza_cambiada, 
        on_registrar_excel, 
        on_play, 
        on_pause, 
        on_guardar, 
        **kwargs
    ):
        super().__init__(parent, width=320, corner_radius=0, **kwargs)
        self.grid_rowconfigure(11, weight=1)  # Espaciador al final

        # Título principal
        self.lbl_titulo = ctk.CTkLabel(
            self, 
            text="DETECTOR DE ÁNGULOS", 
            font=ctk.CTkFont(family="Helvetica", size=20, weight="bold"),
            text_color="#00bfff"
        )
        self.lbl_titulo.grid(row=0, column=0, padx=20, pady=(25, 5), sticky="w")
        
        self.lbl_subtitulo = ctk.CTkLabel(
            self, 
            text="Flexión de Tronco en Posturas", 
            font=ctk.CTkFont(family="Helvetica", size=12, slant="italic"),
            text_color="gray"
        )
        self.lbl_subtitulo.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="w")

        # --- SECCIÓN: CARGA DE ARCHIVO ---
        self.frm_archivo = ctk.CTkFrame(self, fg_color="transparent")
        self.frm_archivo.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        
        self.btn_seleccionar = ctk.CTkButton(
            self.frm_archivo, 
            text="Seleccionar Imagen / Video", 
            command=on_seleccionar,
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

        # Separador visual 1
        self.separador1 = ctk.CTkFrame(self, height=2, fg_color="#333333")
        self.separador1.grid(row=3, column=0, padx=20, pady=15, sticky="ew")

        # --- SECCIÓN: CONFIGURACIÓN DE ANÁLISIS ---
        self.lbl_seccion_conf = ctk.CTkLabel(
            self, 
            text="Configuración de Análisis", 
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.lbl_seccion_conf.grid(row=4, column=0, padx=20, pady=(0, 10), sticky="w")

        # Contenedor para la configuración
        self.frm_analisis = ctk.CTkFrame(self, fg_color="transparent")
        self.frm_analisis.grid(row=5, column=0, padx=20, pady=0, sticky="ew")

        # Lado del cuerpo
        self.lbl_lado = ctk.CTkLabel(self.frm_analisis, text="Lado del cuerpo a medir:")
        self.lbl_lado.pack(anchor="w", padx=5, pady=(0, 2))
        self.opt_lado = ctk.CTkOptionMenu(
            self.frm_analisis, 
            values=["Auto", "Izquierdo", "Derecho"],
            command=on_lado_cambiado
        )
        self.opt_lado.pack(fill="x", padx=5, pady=(0, 15))
        self.opt_lado.set("Auto")

        # Color de visualización
        self.lbl_color = ctk.CTkLabel(self.frm_analisis, text="Color de líneas y arcos:")
        self.lbl_color.pack(anchor="w", padx=5, pady=(0, 2))
        self.opt_color = ctk.CTkOptionMenu(
            self.frm_analisis, 
            values=["Rosado", "Celeste", "Verde Neón", "Naranja", "Amarillo"],
            command=on_color_cambiado
        )
        self.opt_color.pack(fill="x", padx=5, pady=(0, 15))
        self.opt_color.set("Rosado")

        # Confianza del detector
        self.lbl_confianza = ctk.CTkLabel(self.frm_analisis, text="Confianza mínima: 0.50")
        self.lbl_confianza.pack(anchor="w", padx=5, pady=(5, 2))
        self.sld_confianza = ctk.CTkSlider(
            self.frm_analisis, 
            from_=0.1, 
            to=0.9, 
            number_of_steps=16,
            command=self._on_slider_moved
        )
        self.sld_confianza.pack(fill="x", padx=5, pady=(0, 10))
        self.sld_confianza.set(0.5)
        self.on_confianza_cambiada_cb = on_confianza_cambiada

        # Separador visual 2
        self.separador_excel = ctk.CTkFrame(self, height=2, fg_color="#333333")
        self.separador_excel.grid(row=6, column=0, padx=20, pady=15, sticky="ew")

        # --- SECCIÓN: REGISTRO DE DATOS ---
        self.lbl_seccion_excel = ctk.CTkLabel(
            self, 
            text="Registro de Datos (Excel)", 
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.lbl_seccion_excel.grid(row=7, column=0, padx=20, pady=(0, 10), sticky="w")

        self.frm_excel = ctk.CTkFrame(self, fg_color="transparent")
        self.frm_excel.grid(row=8, column=0, padx=20, pady=0, sticky="ew")

        # Campo nombre
        self.lbl_nombre = ctk.CTkLabel(self.frm_excel, text="Nombre de la Persona:")
        self.lbl_nombre.pack(anchor="w", padx=5, pady=(0, 2))
        self.ent_nombre = ctk.CTkEntry(
            self.frm_excel, 
            placeholder_text="Ej. Juan Pérez"
        )
        self.ent_nombre.pack(fill="x", padx=5, pady=(0, 10))

        # Botón registrar
        self.btn_registrar_excel = ctk.CTkButton(
            self.frm_excel, 
            text="Registrar en Excel", 
            command=on_registrar_excel,
            fg_color="#00bfff", 
            hover_color="#008b8b",
            font=ctk.CTkFont(weight="bold")
        )
        self.btn_registrar_excel.pack(fill="x", padx=5, pady=(0, 5))

        # --- SECCIÓN: CONTROLES DE REPRODUCCIÓN (PARA VIDEO) ---
        self.frm_controles_video = ctk.CTkFrame(self, fg_color="transparent")
        self.frm_controles_video.grid(row=9, column=0, padx=20, pady=15, sticky="ew")
        
        self.btn_play = ctk.CTkButton(
            self.frm_controles_video, 
            text="Reproducir", 
            fg_color="#10b981", 
            hover_color="#059669",
            command=on_play,
            state="disabled",
            font=ctk.CTkFont(weight="bold")
        )
        self.btn_play.pack(side="left", expand=True, padx=(0, 5), fill="x")
        
        self.btn_pause = ctk.CTkButton(
            self.frm_controles_video, 
            text="Pausar", 
            fg_color="#f59e0b", 
            hover_color="#d97706",
            command=on_pause,
            state="disabled",
            font=ctk.CTkFont(weight="bold")
        )
        self.btn_pause.pack(side="left", expand=True, padx=(5, 0), fill="x")

        # Botón guardar captura
        self.btn_guardar = ctk.CTkButton(
            self, 
            text="Guardar Captura de Imagen", 
            fg_color="#4b5563",
            hover_color="#374151",
            command=on_guardar,
            state="disabled",
            font=ctk.CTkFont(weight="bold"),
            height=35
        )
        self.btn_guardar.grid(row=10, column=0, padx=20, pady=(0, 20), sticky="ew")

    def _on_slider_moved(self, value):
        """Maneja el movimiento local del slider para actualizar su etiqueta e invocar el callback."""
        self.lbl_confianza.configure(text=f"Confianza mínima: {value:.2f}")
        if self.on_confianza_cambiada_cb:
            self.on_confianza_cambiada_cb(value)

    # Métodos de interfaz pública
    def get_lado(self):
        return self.opt_lado.get()

    def get_color_name(self):
        return self.opt_color.get()

    def get_confianza(self):
        return self.sld_confianza.get()

    def get_nombre(self):
        return self.ent_nombre.get().strip()

    def clear_nombre(self):
        self.ent_nombre.delete(0, 'end')

    def set_nombre_archivo(self, text, color="white"):
        self.lbl_archivo.configure(text=text, text_color=color)

    def set_play_text(self, text):
        self.btn_play.configure(text=text)

    def configurar_estados_archivo(self, tipo_archivo):
        """Configura los estados iniciales de los botones según si es 'image' o 'video'."""
        if tipo_archivo == "image":
            self.btn_play.configure(state="disabled")
            self.btn_pause.configure(state="disabled")
            self.btn_guardar.configure(state="normal")
            self.sld_confianza.configure(state="normal")
        elif tipo_archivo == "video":
            self.btn_play.configure(state="normal", text="Reproducir")
            self.btn_pause.configure(state="disabled")
            self.btn_guardar.configure(state="disabled")
            self.sld_confianza.configure(state="normal")
        else: # Ninguno
            self.btn_play.configure(state="disabled")
            self.btn_pause.configure(state="disabled")
            self.btn_guardar.configure(state="disabled")
            self.sld_confianza.configure(state="normal")

    def configurar_estados_reproduccion(self, is_playing):
        """Configura los botones durante la reproducción o pausa de video."""
        if is_playing:
            self.btn_play.configure(state="disabled")
            self.btn_pause.configure(state="normal")
            self.btn_guardar.configure(state="disabled")
            self.sld_confianza.configure(state="disabled")
        else: # Pausado
            self.btn_play.configure(state="normal", text="Reanudar")
            self.btn_pause.configure(state="disabled")
            self.btn_guardar.configure(state="normal")
            self.sld_confianza.configure(state="normal")

    def configurar_estados_detenido(self):
        """Restablece los controles una vez finalizada la reproducción del video."""
        self.btn_play.configure(state="normal", text="Reproducir de nuevo")
        self.btn_pause.configure(state="disabled")
        self.btn_guardar.configure(state="disabled")
        self.sld_confianza.configure(state="normal")
