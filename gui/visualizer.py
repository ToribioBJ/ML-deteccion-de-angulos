import customtkinter as ctk
from PIL import Image
import cv2

class VisualizerFrame(ctk.CTkFrame):
    """Componente para mostrar la imagen o fotograma del video analizado, con escalado responsivo."""
    def __init__(self, parent, dashboard_frame, on_resize_callback=None, **kwargs):
        super().__init__(parent, fg_color="#101010", width=800, height=500, **kwargs)
        self.dashboard_frame = dashboard_frame
        self.on_resize_callback = on_resize_callback
        self._resize_after_id = None
        self.raw_current_frame = None

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Panel de visualización de imagen
        self.lbl_viewer = ctk.CTkLabel(
            self, 
            text="Carga un archivo para comenzar\n\nSoporta: .jpg, .png, .mp4, .avi, .mov",
            font=ctk.CTkFont(family="Segoe UI", size=16),
            text_color="gray"
        )
        self.lbl_viewer.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.bind("<Configure>", self.on_resize)
        self.grid_propagate(False)

    def on_resize(self, event):
        """Maneja el evento de cambio de tamaño del contenedor para hacerlo responsivo."""
        if event.widget == self:
            if self.on_resize_callback and self.raw_current_frame is not None:
                if self._resize_after_id:
                    self.after_cancel(self._resize_after_id)
                self._resize_after_id = self.after(50, self.on_resize_callback)

    def cancel_pending_resizes(self):
        """Cancela cualquier callback de redimensionamiento pendiente."""
        if self._resize_after_id:
            try:
                self.after_cancel(self._resize_after_id)
            except:
                pass
            self._resize_after_id = None

    def mostrar_frame(self, frame, scaling):
        """Adapta la imagen OpenCV BGR para mostrarla centrada en el visor."""
        if frame is None:
            return
            
        # Convertir BGR a RGB
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb_image)
        
        # Obtener dimensiones reales del contenedor
        container_w = self.winfo_width()
        container_h = self.winfo_height()
        
        # Obtener la altura del dashboard
        dash_h = self.dashboard_frame.winfo_height()
        if dash_h <= 1:
            dash_h = 140
            
        # Calcular espacio disponible real para el visor en píxeles físicos, restando paddings
        view_w = container_w - 40
        view_h = container_h - dash_h - 60
        
        # Si las dimensiones son inválidas, usar valores por defecto en píxeles físicos
        if view_w <= 10 or view_h <= 10:
            view_w = 800
            view_h = 500
            
        # Ajustar las dimensiones físicas a coordenadas lógicas usando el factor de escala
        logical_view_w = int(view_w / scaling)
        logical_view_h = int(view_h / scaling)
            
        # Escalar manteniendo la relación de aspecto usando coordenadas lógicas
        img_w, img_h = pil_image.size
        aspect_ratio = img_w / img_h
        
        if logical_view_w / logical_view_h > aspect_ratio:
            new_h = logical_view_h - 10
            new_w = int(new_h * aspect_ratio)
        else:
            new_w = logical_view_w - 10
            new_h = int(new_w / aspect_ratio)
            
        # Asegurarse de que las dimensiones sean válidas
        new_w = max(10, new_w)
        new_h = max(10, new_h)
        
        # Convertir a CTkImage usando la imagen en resolución original
        # para mantener la nitidez (HD) al aplicar escala DPI
        ctk_img = ctk.CTkImage(
            light_image=pil_image,
            dark_image=pil_image,
            size=(new_w, new_h)
        )
        
        # Actualizar widget
        try:
            self.lbl_viewer.image = ctk_img  # Mantener referencia antes de la asignación
            self.lbl_viewer._label.configure(image="")  # Limpiar imagen anterior en Tkinter para evitar TclError
            self.lbl_viewer.configure(image=ctk_img, text="")
        except Exception as e:
            print(f"Advertencia: No se pudo renderizar el fotograma en la interfaz ({e})")

    def reset_visor(self):
        """Limpia el visor y restablece el mensaje predeterminado."""
        self.raw_current_frame = None
        try:
            self.lbl_viewer.image = None
            self.lbl_viewer._label.configure(image="")  # Limpiar imagen anterior en Tkinter
            self.lbl_viewer.configure(image=None, text="Carga un archivo para comenzar\n\nSoporta: .jpg, .png, .mp4, .avi, .mov")
        except Exception as e:
            print(f"Advertencia: No se pudo limpiar el visor ({e})")


