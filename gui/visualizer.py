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

    def mostrar_frame(self, frame, scaling, is_reference=False, alfa=None, beta=None):
        """Adapta la imagen OpenCV BGR para mostrarla centrada en el visor."""
        if frame is None:
            return
            
        # Convertir BGR a RGB
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb_image)
        
        if is_reference and alfa is not None and beta is not None:
            from PIL import ImageDraw, ImageFont
            img_w, img_h = pil_image.size
            
            # Calcular factor de escala basado en el ancho de la imagen para que sea responsivo
            base_scale = max(0.6, min(img_w / 800.0, 4.0))
            
            w_box = int(round(280 * base_scale))
            h_box = int(round(130 * base_scale))
            
            if img_w > w_box + 20 and img_h > h_box + 20:
                overlay = Image.new('RGBA', pil_image.size, (0, 0, 0, 0))
                draw_overlay = ImageDraw.Draw(overlay)
                
                pad = int(round(20 * base_scale))
                # Rectángulo con fondo oscuro de alta densidad y contorno morado neón grueso (4px)
                draw_overlay.rectangle(
                    [pad, pad, pad + w_box, pad + h_box], 
                    fill=(15, 12, 25, 225), 
                    outline=(168, 85, 247), 
                    width=max(2, int(round(4 * base_scale)))
                )
                
                pil_image = Image.alpha_composite(pil_image.convert('RGBA'), overlay).convert('RGB')
                draw = ImageDraw.Draw(pil_image)
                
                try:
                    font_title = ImageFont.truetype("arial.ttf", int(round(15 * base_scale)))
                    font_text = ImageFont.truetype("arial.ttf", int(round(20 * base_scale)))
                except IOError:
                    font_title = ImageFont.load_default()
                    font_text = ImageFont.load_default()
                
                title_y = pad + int(round(15 * base_scale))
                alfa_y = pad + int(round(48 * base_scale))
                beta_y = pad + int(round(82 * base_scale))
                
                # Título en tono lavanda brillante
                draw.text((pad + int(round(20 * base_scale)), title_y), "ÁNGULOS DE REFERENCIA", fill=(192, 132, 252), font=font_title)
                
                # Círculos (viñetas) decorativos morados para cada ángulo
                bullet_r = int(round(4 * base_scale))
                draw.ellipse([pad + int(round(20 * base_scale)), alfa_y + int(round(6 * base_scale)), pad + int(round(20 * base_scale)) + bullet_r * 2, alfa_y + int(round(6 * base_scale)) + bullet_r * 2], fill=(168, 85, 247))
                draw.ellipse([pad + int(round(20 * base_scale)), beta_y + int(round(6 * base_scale)), pad + int(round(20 * base_scale)) + bullet_r * 2, beta_y + int(round(6 * base_scale)) + bullet_r * 2], fill=(168, 85, 247))
                
                # Textos de los ángulos
                draw.text((pad + int(round(35 * base_scale)), alfa_y), f"Tronco (α) = {int(round(alfa))}°", fill=(255, 255, 255), font=font_text)
                draw.text((pad + int(round(35 * base_scale)), beta_y), f"Cabeza (β) = {int(round(beta))}°", fill=(255, 255, 255), font=font_text)

        
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
        
        # Guardar parámetros para el mapeo de clics
        self.last_scaling = scaling
        self.last_new_w = new_w
        self.last_new_h = new_h
        self.last_raw_w = img_w
        self.last_raw_h = img_h

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

    def get_click_coords(self, event):
        """Traduce la coordenada del evento clic a coordenadas reales de la imagen."""
        if self.raw_current_frame is None:
            return None
            
        try:
            scaling = getattr(self, "last_scaling", 1.0)
            new_w = getattr(self, "last_new_w", None)
            new_h = getattr(self, "last_new_h", None)
            raw_w = getattr(self, "last_raw_w", None)
            raw_h = getattr(self, "last_raw_h", None)
            
            if new_w is None or new_h is None or raw_w is None or raw_h is None:
                return None
                
            # Píxeles físicos ocupados por la imagen en la interfaz
            displayed_w = new_w * scaling
            displayed_h = new_h * scaling
            
            # El evento se enlaza a self.lbl_viewer._label (el widget interno tkinter.Label
            # de CustomTkinter), el cual se ajusta exactamente al tamaño físico de la imagen.
            # Por lo tanto, event.x y event.y ya están en el sistema de coordenadas de la imagen.
            click_x_img = event.x
            click_y_img = event.y
            
            # Verificar si el clic cae dentro de la imagen
            if 0 <= click_x_img <= displayed_w and 0 <= click_y_img <= displayed_h:
                # Mapear de píxeles físicos a resolución original de la imagen
                raw_x = int(round(click_x_img * (raw_w / displayed_w)))
                raw_y = int(round(click_y_img * (raw_h / displayed_h)))
                
                # Asegurar límites reales de la imagen
                raw_x = max(0, min(raw_w - 1, raw_x))
                raw_y = max(0, min(raw_h - 1, raw_y))
                return (raw_x, raw_y)
        except Exception as e:
            print(f"Error al calcular coordenadas de clic: {e}")
            
        return None

    def reset_visor(self):
        """Limpia el visor y restablece el mensaje predeterminado."""
        self.raw_current_frame = None
        try:
            self.lbl_viewer.image = None
            self.lbl_viewer._label.configure(image="")  # Limpiar imagen anterior en Tkinter
            self.lbl_viewer.configure(image=None, text="Carga un archivo para comenzar\n\nSoporta: .jpg, .png, .mp4, .avi, .mov")
        except Exception as e:
            print(f"Advertencia: No se pudo limpiar el visor ({e})")


